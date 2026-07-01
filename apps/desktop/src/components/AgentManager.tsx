import React, { useState, useEffect, useMemo, useCallback } from 'react';

import { Deliverable, Agent } from '../types';
import { fetchAgents, saveAgents, generateAgentPrompt } from '../services/agentApi';
import { fetchSkillsRegistry, type ScannedSkill } from '../services/skillsApi';
import { BTN_GHOST, BTN_PRIMARY, BTN_SECONDARY, BTN_ICON } from './ui/buttonStyles';
import { BADGE_SUCCESS } from './ui/surfaceStyles';
import { LegacyIcon } from './ui/LegacyIcon';
import { fetchMcpStatus, type McpServer } from '../services/mcpApi';
import { getAgentDisplayName, isBuiltinAgent, mergeAgentsWithBuiltin, BUILTIN_AGENT_ID } from '../services/builtinAgent';
import {
  CLUTCH_AGENT_TYPE,
  agentTypeFromAgent,
  agentTypeLabel,
  buildSelectableAgentTypeOptions,
  type AgentTypeId,
} from '../services/agentTypes';
import { fetchModelsConfig, mapModelConfigToUi } from '../services/modelsApi';
import { useLanguage } from './LanguageContext';
import { fetchToolsStatus, type AiToolStatus } from '../services/toolsApi';
import { sidecarHttpUrl, sidecarFetch } from '../services/sidecarUrl';
import { clutchMarkUrl, resolveBrandLogoSrc } from '../services/brandLogos';
import { UnderDevelopmentNotice } from './ui/UnderDevelopmentNotice';

export function AgentLogo({
  name,
  description,
  className = 'w-10 h-10',
  agentType,
  toolId,
  logoSrc,
}: {
  name: string;
  description: string;
  className?: string;
  agentType?: AgentTypeId | string;
  toolId?: string;
  logoSrc?: string;
}) {
  const brandSrc = logoSrc ?? resolveBrandLogoSrc({ agentType, toolId });
  if (brandSrc) {
    const clutch = brandSrc === clutchMarkUrl;
    return (
      <div
        className={`${className} rounded-full flex items-center justify-center ${clutch ? 'bg-black' : 'bg-white'} relative overflow-hidden flex-shrink-0 select-none border border-neutral-200/40`}
      >
        <img
          src={brandSrc}
          alt={name}
          className={clutch ? 'w-full h-full object-cover' : 'w-[68%] h-[68%] object-contain'}
        />
      </div>
    );
  }

  const iconSize = className.includes('w-12') ? 'text-[22px]' : 'text-[18px]';
  return (
    <div
      className={`${className} rounded-full flex items-center justify-center bg-surface-container relative overflow-hidden flex-shrink-0 select-none border border-neutral-200/40`}
    >
      <LegacyIcon name="smart_toy" className={`${iconSize} text-on-surface-variant`} />
    </div>
  );
}

interface AgentManagerProps {
  selectedSidebarWidth?: number;
  isModalStyle?: boolean;
  activeAgentId?: string | null;
  onActivateAgent?: (agent: Agent) => void;
}

export function AgentManager({
  selectedSidebarWidth,
  isModalStyle,
  activeAgentId = null,
  onActivateAgent,
}: AgentManagerProps) {
  const { t } = useLanguage();
  const [agents, setAgents] = useState<Agent[]>([]);

  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [isPreviewDeliverable, setIsPreviewDeliverable] = useState<Deliverable | null>(null);
  
  // Modal state
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalMode, setModalMode] = useState<'create' | 'edit'>('create');
  
  // Form fields
  const [editingId, setEditingId] = useState<string>('');
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [markdownDoc, setMarkdownDoc] = useState('');
  const [deliverablesInput, setDeliverablesInput] = useState<{ name: string; content: string }[]>([]);
  const [newDelivName, setNewDelivName] = useState('');
  const [newDelivContent, setNewDelivContent] = useState('');
  const [selectedMcpTools, setSelectedMcpTools] = useState<string[]>([]);
  const [selectedMcpServerIds, setSelectedMcpServerIds] = useState<string[]>([]);
  const [mcpServers, setMcpServers] = useState<McpServer[]>([]);

  // Vibe workspace state extensions
  const [scannedSkills, setScannedSkills] = useState<ScannedSkill[]>([]);

  const [eligibleTools, setEligibleTools] = useState<AiToolStatus[]>([]);
  const [agentType, setAgentType] = useState<AgentTypeId>(CLUTCH_AGENT_TYPE);
  const [modelId, setModelId] = useState('');
  const [clutchModels, setClutchModels] = useState<Array<{ id: string; name: string; modelKind: string }>>([]);
  const [ollamaModels, setOllamaModels] = useState<string[]>([]);
  const [ollamaModel, setOllamaModel] = useState('');
  const [ollamaError, setOllamaError] = useState<{
    reason?: string;
    error?: string;
    app_installed?: boolean;
    binary_installed?: boolean;
  } | null>(null);
  const [isStartingOllama, setIsStartingOllama] = useState(false);

  const refreshConnectedTools = useCallback(() => {
    void fetchToolsStatus()
      .then((toolsList) => {
        setEligibleTools(toolsList.filter((tool) => tool.connected));
      })
      .catch(() => {
        setEligibleTools([]);
      });
  }, []);

  const agentTypeOptions = useMemo(
    () => buildSelectableAgentTypeOptions(eligibleTools, modalMode === 'edit' ? agentType : undefined),
    [eligibleTools, modalMode, agentType],
  );

  const getDefaultAgentType = (): AgentTypeId => CLUTCH_AGENT_TYPE;
  const [selectedSkills, setSelectedSkills] = useState<string[]>([]);
  const [isSkillsAttachOpen, setIsSkillsAttachOpen] = useState(false);
  const [skillsSearch, setSkillsSearch] = useState('');
  const [expandedModules, setExpandedModules] = useState<Record<number, boolean>>({
    3: false,
    4: false,
    5: false,
  });
  const [isGeneratingPrompt, setIsGeneratingPrompt] = useState(false);
  const [promptGenerateError, setPromptGenerateError] = useState<string | null>(null);

  const toggleModule = (moduleNumber: number) => {
    setExpandedModules((prev) => ({ ...prev, [moduleNumber]: !prev[moduleNumber] }));
  };

  const refreshScannedSkills = () => {
    void fetchSkillsRegistry()
      .then((data) => setScannedSkills(data.skills))
      .catch(() => setScannedSkills([]));
  };

  useEffect(() => {
    void fetchMcpStatus()
      .then((status) => setMcpServers(status.servers.filter((s) => s.enabled !== false)))
      .catch(() => setMcpServers([]));
    refreshConnectedTools();
  }, []);

  useEffect(() => {
    refreshScannedSkills();
    const handleUpdateSkills = () => refreshScannedSkills();
    window.addEventListener('clutch-skills-updated', handleUpdateSkills);
    window.addEventListener('vibe-skills-updated', handleUpdateSkills);
    return () => {
      window.removeEventListener('clutch-skills-updated', handleUpdateSkills);
      window.removeEventListener('vibe-skills-updated', handleUpdateSkills);
    };
  }, []);

  useEffect(() => {
    void fetchAgents()
      .then((list) => {
        setAgents(list);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    void fetchModelsConfig()
      .then((config) => {
        const mapped = mapModelConfigToUi(config);
        setClutchModels(
          mapped.models.map((model) => ({
            id: model.id,
            name: model.name,
            modelKind: model.modelKind ?? 'chat',
          })),
        );
      })
      .catch(() => setClutchModels([]));
  }, []);

  useEffect(() => {
    if (!isModalOpen || agentType !== 'clutch') return;
    void fetchModelsConfig()
      .then((config) => {
        const mapped = mapModelConfigToUi(config);
        setClutchModels(
          mapped.models.map((model) => ({
            id: model.id,
            name: model.name,
            modelKind: model.modelKind ?? 'chat',
          })),
        );
      })
      .catch(() => setClutchModels([]));
  }, [isModalOpen, agentType]);

  useEffect(() => {
    if (isModalOpen && agentType === 'ollama-cli') {
      setOllamaError(null);
      sidecarFetch(sidecarHttpUrl('/api/models/ollama'))
        .then((res) => res.json())
        .then((data) => {
          if (data.ok && data.models) {
            setOllamaModels(data.models);
            if (data.models.length > 0) {
              setOllamaModel((prev) =>
                prev && data.models.includes(prev) ? prev : data.models[0],
              );
            }
          } else {
            setOllamaModels([]);
            setOllamaError({
              reason: data.reason,
              error: data.error,
              app_installed: data.app_installed,
              binary_installed: data.binary_installed,
            });
          }
        })
        .catch((err) => {
          console.error('Failed to fetch Ollama models:', err);
          setOllamaModels([]);
          setOllamaError({ error: String(err) });
        });
    }
  }, [isModalOpen, agentType]);

  const handleStartOllama = () => {
    setIsStartingOllama(true);
    sidecarFetch(sidecarHttpUrl('/api/models/ollama/start'), { method: 'POST' })
      .then((res) => res.json())
      .then((data) => {
        if (data.ok) {
          let attempts = 0;
          const interval = setInterval(() => {
            sidecarFetch(sidecarHttpUrl('/api/models/ollama'))
              .then((res) => res.json())
              .then((statusData) => {
                attempts++;
                if (statusData.ok && statusData.models && statusData.models.length > 0) {
                  setOllamaModels(statusData.models);
                  setOllamaModel((prev) =>
                    prev && statusData.models.includes(prev) ? prev : statusData.models[0],
                  );
                  setOllamaError(null);
                  setIsStartingOllama(false);
                  clearInterval(interval);
                } else if (attempts >= 6) {
                  setIsStartingOllama(false);
                  clearInterval(interval);
                }
              })
              .catch(() => {
                attempts++;
                if (attempts >= 6) {
                  setIsStartingOllama(false);
                  clearInterval(interval);
                }
              });
          }, 1500);
        } else {
          setIsStartingOllama(false);
          alert(data.error || 'Failed to start Ollama');
        }
      })
      .catch((err) => {
        setIsStartingOllama(false);
        alert('Error starting Ollama: ' + err);
      });
  };

  const persistAgents = (next: Agent[]) => {
    const builtin = next.find((agent) => isBuiltinAgent(agent));
    const custom = next.filter((agent) => !isBuiltinAgent(agent));
    const normalized = builtin ? [builtin, ...custom] : mergeAgentsWithBuiltin(custom);
    setAgents(normalized);
    void saveAgents(normalized)
      .then(() => fetchAgents().then((list) => setAgents(list)))
      .catch((error) => {
        console.error('[Clutch] agents save failed:', error);
      });
  };

  const handleOpenCreate = () => {
    refreshConnectedTools();
    setModalMode('create');
    setEditingId('');
    setName('');
    setDescription('');
    setMarkdownDoc(`# Custom Agent Prompt\n\nDefine custom parameters or directives for this agent here.\n\n## 📋 Protocol\n- Task validation.\n- Process orchestration.`);
    setDeliverablesInput([]);
    setNewDelivName('');
    setNewDelivContent('');
    setSelectedMcpTools([]);
    setSelectedMcpServerIds([]);
    setAgentType(getDefaultAgentType());
    setModelId('');
    setOllamaModel('');
    setSelectedSkills([]);
    setIsSkillsAttachOpen(false);
    setExpandedModules({ 3: false, 4: false, 5: false });
    setPromptGenerateError(null);
    setIsModalOpen(true);
  };

  const handleOpenEdit = (agent: Agent, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    refreshConnectedTools();
    setModalMode('edit');
    setEditingId(agent.id);
    setName(agent.name);
    setDescription(agent.description);
    setMarkdownDoc(agent.markdownDoc);
    setDeliverablesInput([...agent.deliverables]);
    setNewDelivName('');
    setNewDelivContent('');
    setSelectedMcpTools(agent.mcpTools || []);
    setSelectedMcpServerIds(agent.mcpServerIds || []);
    setAgentType(agentTypeFromAgent(agent));
    setModelId(agent.modelId || '');
    setOllamaModel(agent.ollamaModel || '');
    setSelectedSkills(agent.skills || []);
    setIsSkillsAttachOpen(false);
    setExpandedModules({ 3: false, 4: false, 5: false });
    setPromptGenerateError(null);
    setIsModalOpen(true);
  };

  const handleDelete = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (isBuiltinAgent({ id })) return;
    if (window.confirm('Are you sure you want to delete this AI Agent?')) {
      const updated = agents.filter(a => a.id !== id);
      persistAgents(updated);
      if (selectedAgent && selectedAgent.id === id) {
        setSelectedAgent(null);
      }
    }
  };

  const handleAddDeliverable = () => {
    if (!newDelivName.trim()) return;
    setDeliverablesInput([
      ...deliverablesInput,
      { name: newDelivName.trim(), content: newDelivContent || '# Sample Content' }
    ]);
    setNewDelivName('');
    setNewDelivContent('');
  };

  const handleRemoveDeliverable = (index: number) => {
    setDeliverablesInput(deliverablesInput.filter((_, i) => i !== index));
  };

  const handleGeneratePrompt = async () => {
    if (!name.trim()) {
      setPromptGenerateError('Enter an agent name in Module 1 first.');
      return;
    }
    setPromptGenerateError(null);
    setIsGeneratingPrompt(true);
    try {
      const result = await generateAgentPrompt({
        name: name.trim(),
        description: description.trim(),
      });
      setMarkdownDoc(result.prompt);
    } catch (error) {
      setPromptGenerateError(error instanceof Error ? error.message : 'Prompt generation failed.');
    } finally {
      setIsGeneratingPrompt(false);
    }
  };

  const handleSave = () => {
    if (!name.trim()) {
      console.warn('Please enter Agent Name');
      return;
    }

    if (agentType === 'ollama-cli' && !ollamaModel.trim()) {
      console.warn('Please select an Ollama model');
      return;
    }

    const todayStr = new Date().toISOString().replace('T', ' ').substring(0, 16);

    const resolvedAgentType: AgentTypeId = editingId === BUILTIN_AGENT_ID ? CLUTCH_AGENT_TYPE : agentType;
    const resolvedModelId = resolvedAgentType === 'clutch' && modelId.trim() ? modelId.trim() : undefined;

    if (modalMode === 'create') {
      const newAgent: Agent = {
        id: `agent-${Date.now()}`,
        name: name.trim(),
        description: description.trim(),
        markdownDoc: markdownDoc.trim(),
        lastModified: todayStr,
        avatar: `https://api.dicebear.com/7.x/bottts/svg?seed=${encodeURIComponent(name)}`,
        deliverables: deliverablesInput,
        mcpTools: selectedMcpTools,
        mcpServerIds: selectedMcpServerIds,
        agentType: resolvedAgentType,
        modelId: resolvedModelId,
        ollamaModel: resolvedAgentType === 'ollama-cli' ? ollamaModel : undefined,
        skills: selectedSkills
      };
      persistAgents([newAgent, ...agents]);
    } else {
      const updated = agents.map(a => {
        if (a.id === editingId) {
          const updatedAgent = {
            ...a,
            name: name.trim(),
            description: description.trim(),
            markdownDoc: markdownDoc.trim(),
            lastModified: todayStr,
            deliverables: deliverablesInput,
            mcpTools: selectedMcpTools,
            mcpServerIds: selectedMcpServerIds,
            agentType: resolvedAgentType,
            modelId: resolvedModelId,
            ollamaModel: resolvedAgentType === 'ollama-cli' ? ollamaModel : undefined,
            skills: selectedSkills
          };
          if (selectedAgent && selectedAgent.id === editingId) {
            setSelectedAgent(updatedAgent);
          }
          return updatedAgent;
        }
        return a;
      });
      persistAgents(updated);
    }
    setIsModalOpen(false);
  };

  // Helper parser to render Markdown gracefully
  const renderMarkdownText = (text: string) => {
    if (!text) return null;
    return text.split('\n').map((line, i) => {
      if (line.startsWith('# ')) {
        return (
          <h1 key={i} className="text-[18px] font-extrabold text-neutral-900 border-b border-neutral-200 pb-2.5 mb-4 mt-2">
            {line.substring(2)}
          </h1>
        );
      }
      if (line.startsWith('## ')) {
        return (
          <h2 key={i} className="text-[14px] font-bold text-neutral-800 mt-5 mb-2 flex items-center gap-2">
            {line.substring(3)}
          </h2>
        );
      }
      if (line.startsWith('### ')) {
        return (
          <h3 key={i} className="text-[12.5px] font-bold text-neutral-800 mt-4 mb-2">
            {line.substring(4)}
          </h3>
        );
      }
      if (line.startsWith('- ')) {
        let content = line.substring(2);
        // Quick bold handling: **item**
        content = content.replace(/\*\*(.*?)\*\*/g, '<strong class="text-neutral-950 font-semibold">$1</strong>');
        // Backticks code formatting
        content = content.replace(/`([^`]+)`/g, '<code class="bg-neutral-100 text-neutral-900 px-1 py-0.5 rounded font-mono text-[11px] border border-neutral-200/50 mx-0.5">$1</code>');
        // Double brackets handling
        content = content.replace(/\[\[(.*?)\]\]/g, '<span class="text-[#897FDB] font-medium">[[ $1 ]]</span>');
        
        return (
          <div key={i} className="flex items-start gap-2 pl-1 my-1.5 text-neutral-600 text-[12.5px]">
            <span className="w-1 h-1.5 mt-2 rounded bg-neutral-400 flex-shrink-0" />
            <span dangerouslySetInnerHTML={{ __html: content }} />
          </div>
        );
      }
      if (line.startsWith('|') && line.includes('---')) {
        return null; // Skip markdown divider lines in simplified view
      }
      if (line.startsWith('|')) {
        // Render simple table support
        const cells = line.split('|').map(s => s.trim()).filter((_, index, arr) => index > 0 && index < arr.length - 1);
        const isHeader = i === 4; // approximate
        return (
          <div key={i} className="flex border-b border-neutral-100 py-1.5 px-2 bg-neutral-50/40 text-[11.5px] text-neutral-600 font-mono">
            {cells.map((cell, idx) => (
              <div key={idx} className="flex-1 overflow-hidden text-ellipsis whitespace-nowrap px-1.5">
                {cell}
              </div>
            ))}
          </div>
        );
      }

      const pContent = line
        .replace(/\*\*(.*?)\*\*/g, '<strong class="text-neutral-950 font-semibold">$1</strong>')
        .replace(/`([^`]+)`/g, '<code class="bg-neutral-100 text-neutral-900 px-1 py-0.5 rounded font-mono text-[11px] border border-neutral-200/50 mx-0.5">$1</code>');
      
      return (
        <p key={i} className={line.trim() ? "my-2 text-neutral-600 text-[12.5px] leading-relaxed" : "h-1"} dangerouslySetInnerHTML={{ __html: pContent }} />
      );
    });
  };

  return (
    <div 
      style={isModalStyle ? undefined : { paddingLeft: `${(selectedSidebarWidth || 0) + 32}px`, paddingTop: '76px' }} 
      className={`flex-1 flex flex-col overflow-hidden animate-fade-in relative transition-all duration-300 ${isModalStyle ? 'h-full' : 'h-screen bg-neutral-50'}`}
    >
      {selectedAgent ? (
        // ----------------- AGENT DETAIL PAGE -----------------
        <div className="flex-1 flex flex-col h-full overflow-hidden">
          {/* Breadcrumbs Action Header */}
          <div className={`h-14 border-b border-neutral-200 pl-6 flex items-center justify-between bg-white flex-shrink-0 ${isModalStyle ? 'pr-12' : 'pr-6'}`}>
            <div className="flex items-center gap-3">
              <button 
                onClick={() => setSelectedAgent(null)}
                className="flex items-center justify-center p-1.5 hover:bg-neutral-100 rounded-lg text-neutral-500 hover:text-neutral-900 transition-colors"
                title={t('Back to List')}
              >
                <LegacyIcon name="arrow_back" className="text-[18px]" />
              </button>
              <div className="h-4 w-[1px] bg-neutral-200" />
              <div className="flex items-center gap-1.5 text-[11px] font-semibold text-neutral-400 font-mono uppercase tracking-wider">
                <span>AI AGENTS</span>
                <span>/</span>
                <span className="text-neutral-800">{getAgentDisplayName(selectedAgent)}</span>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={(e) => handleOpenEdit(selectedAgent, e)}
                className="flex items-center gap-1.5 px-3 py-1.5 text-neutral-600 hover:text-neutral-900 hover:bg-neutral-100 rounded-lg text-[11.5px] font-semibold transition-colors border border-neutral-200 bg-white"
              >
                <LegacyIcon name="edit" className="text-[15px]" />
                {t('Edit Settings')}
              </button>
              {!isBuiltinAgent(selectedAgent) ? (
              <button
                onClick={(e) => handleDelete(selectedAgent.id, e)}
                className="flex items-center gap-1.5 px-3 py-1.5 text-red-600 hover:text-red-700 hover:bg-red-50 rounded-lg text-[11.5px] font-semibold transition-colors border border-red-100 bg-white"
              >
                <LegacyIcon name="delete" className="text-[15px]" />
                {t('Delete')}
              </button>
              ) : null}
            </div>
          </div>

          {/* Dual Column Layout */}
          <div className="flex-1 flex overflow-hidden min-h-0 bg-neutral-50/40">
            {/* Left Column: Markdown prompt viewer */}
            <div className="flex-1 overflow-y-auto p-8 border-r border-neutral-200">
              <div className="max-w-2xl mx-auto bg-white border border-neutral-200/70 p-8 rounded-xl shadow-xs leading-relaxed font-sans mt-2 mb-10">
                <div className="flex items-center gap-4 border-b border-neutral-100 pb-5 mb-5 select-none">
                  <AgentLogo
                    name={selectedAgent.name}
                    description={selectedAgent.description}
                    className="w-12 h-12 text-sm"
                    agentType={agentTypeFromAgent(selectedAgent)}
                  />
                  <div>
                    <h2 className="text-sm font-bold text-neutral-900 tracking-tight font-mono">{selectedAgent.name}</h2>
                    <p className="text-[11px] text-neutral-400 mt-0.5">{t('Role System Specifications')}</p>
                  </div>
                </div>

                <div className="space-y-1">
                  {renderMarkdownText(selectedAgent.markdownDoc)}
                </div>
              </div>
            </div>

            {/* Right Column: Metadata & Deliverables Panel */}
            <div className="w-80 flex flex-col bg-white overflow-y-auto flex-shrink-0 border-l border-neutral-100 p-6 space-y-6">
              <div>
                <h3 className="text-[11px] font-bold text-neutral-400 font-mono uppercase tracking-wider mb-2">{t('Agent Details')}</h3>
                <div className="bg-neutral-50 p-4 rounded-xl border border-neutral-200/50 space-y-3">
                  <div>
                    <p className="text-[10px] text-neutral-400 font-medium">{t('NAME')}</p>
                    <p className="text-[11.5px] text-neutral-800 font-semibold mt-0.5">{selectedAgent.name}</p>
                  </div>
                  <div>
                    <p className="text-[10px] text-neutral-400 font-medium">{t('DESCRIPTION')}</p>
                    <p className="text-[11px] text-neutral-600 font-normal mt-0.5 leading-relaxed">{selectedAgent.description}</p>
                  </div>
                  <div className="border-t border-neutral-200/50 pt-2.5">
                    <p className="text-[10px] text-neutral-400 font-medium">{t('AGENT TYPE')}</p>
                    <div className="flex items-center gap-1.5 mt-1 bg-neutral-100 border border-neutral-200 rounded-lg p-1.5">
                      <LegacyIcon name="bolt" className="text-[13px] text-neutral-700" />
                      <span className="text-[10.5px] font-mono font-bold text-neutral-900">
                        {agentTypeLabel(agentTypeFromAgent(selectedAgent), eligibleTools)}
                      </span>
                    </div>
                  </div>
                  {agentTypeFromAgent(selectedAgent) === 'clutch' && selectedAgent.modelId && (
                    <div className="border-t border-neutral-200/50 pt-2.5">
                      <p className="text-[10px] text-neutral-400 font-medium">{t('MODEL')}</p>
                      <div className="flex items-center gap-1.5 mt-1 bg-neutral-100 border border-neutral-200 rounded-lg p-1.5">
                        <LegacyIcon name="layers" className="text-[13px] text-neutral-700" />
                        <span className="text-[10.5px] font-mono font-bold text-neutral-900">
                          {clutchModels.find((m) => m.id === selectedAgent.modelId)?.name || selectedAgent.modelId}
                        </span>
                      </div>
                    </div>
                  )}
                  {agentTypeFromAgent(selectedAgent) === 'ollama-cli' && (
                    <div className="border-t border-neutral-200/50 pt-2.5">
                      <p className="text-[10px] text-neutral-400 font-medium">{t('OLLAMA MODEL')}</p>
                      <div className="flex items-center gap-1.5 mt-1 bg-neutral-100 border border-neutral-200 rounded-lg p-1.5">
                        <LegacyIcon name="memory" className="text-[13px] text-neutral-700" />
                        <span className="text-[10.5px] font-mono font-bold text-neutral-900">
                          {selectedAgent.ollamaModel || t('Auto-select best local model')}
                        </span>
                      </div>
                    </div>
                  )}
                  <div className="border-t border-neutral-200/50 pt-2.5 flex justify-between items-center">
                    <div>
                      <p className="text-[10px] text-neutral-400 font-medium">{t('LAST MODIFIED')}</p>
                      <p className="text-[10.5px] text-neutral-600 font-mono font-medium mt-0.5">{selectedAgent.lastModified}</p>
                    </div>
                    <span className="text-[10px] bg-neutral-200/50 text-neutral-600 px-2 py-0.5 rounded-full font-mono font-semibold">{t('ACTIVE')}</span>
                  </div>
                </div>
              </div>

              {/* Attached Skills Manuals */}
              <div>
                <h3 className="text-[11px] font-bold text-neutral-400 font-mono uppercase tracking-wider mb-2">{t('Attached Skills Manuals')}</h3>
                <div className="flex flex-wrap gap-1.5">
                  {selectedAgent.skills && selectedAgent.skills.length > 0 ? (
                    selectedAgent.skills.map(skillKey => {
                      const match = scannedSkills.find(s => s.key === skillKey) || { label: skillKey };
                      return (
                        <div key={skillKey} className="px-2.5 py-1 bg-neutral-100 border border-neutral-200 rounded-full text-[10px] font-mono font-bold text-neutral-700 flex items-center gap-1 shadow-3xs">
                          <span>🏷️ {match.label}</span>
                        </div>
                      );
                    })
                  ) : (
                    <p className="text-[10px] text-neutral-400 italic leading-snug">{t('No linked professional skills attached to this agent manual.')}</p>
                  )}
                </div>
              </div>

              {/* Mounted MCP Hub servers */}
              <div>
                <h3 className="text-[11px] font-bold text-neutral-400 font-mono uppercase tracking-wider mb-2">{t('MCP Hub Servers')}</h3>
                <div className="flex flex-col gap-1.5">
                  {selectedAgent.mcpServerIds && selectedAgent.mcpServerIds.length > 0 ? (
                    selectedAgent.mcpServerIds.map((serverId) => {
                      const server = mcpServers.find((s) => s.id === serverId);
                      const label = server?.name || serverId;
                      return (
                        <div key={serverId} className="px-2.5 py-1.5 border rounded-lg flex items-center justify-between font-mono text-[10px] font-bold bg-neutral-50 text-neutral-800 border-neutral-200/60">
                          <span className="flex items-center gap-1.5">
                            <LegacyIcon name="hub" className="text-[13px]" />
                            {label}
                          </span>
                          <span className="text-[7.5px] tracking-wider uppercase opacity-85">BOUND</span>
                        </div>
                      );
                    })
                  ) : (
                    <p className="text-[10px] text-neutral-400/80 italic">No MCP Hub servers bound. Clutch Agent uses MCP only when servers are linked here.</p>
                  )}
                </div>
              </div>

              <div className="flex-1 flex flex-col min-h-0">
                <h3 className="text-[11px] font-bold text-neutral-400 font-mono uppercase tracking-wider mb-2">Deliverables (Output Files)</h3>
                <div className="flex-1 space-y-2">
                  {selectedAgent.deliverables && selectedAgent.deliverables.length > 0 ? (
                    selectedAgent.deliverables.map((item, index) => (
                      <button
                        key={index}
                        onClick={() => setIsPreviewDeliverable(item)}
                        className="w-full flex items-center justify-between p-3 border border-neutral-200 hover:border-neutral-300 bg-neutral-50/30 hover:bg-neutral-50 rounded-xl text-left transition-all duration-150 group"
                      >
                        <div className="flex items-center gap-2.5 overflow-hidden">
                          <LegacyIcon
                            name={item.name.endsWith('.json') ? 'schema' : 'insert_drive_file'}
                            className="text-[17px] text-neutral-400 group-hover:text-neutral-600 font-mono"
                          />
                          <span className="text-[11.5px] font-mono text-neutral-800 font-bold truncate group-hover:text-black">
                            {item.name}
                          </span>
                        </div>
                        <LegacyIcon name="visibility" className="text-[15px] text-neutral-400 opacity-0 group-hover:opacity-100 transition-opacity" />
                      </button>
                    ))
                  ) : (
                    <p className="text-[11px] text-neutral-400 italic">{t('No associated deliverablesconfigured.')}</p>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      ) : (
        // ----------------- AGENT CATALOG LIST PAGE -----------------
        <div className="max-w-4xl mx-auto w-full p-8 space-y-6 overflow-y-auto">
          {/* List Header */}
          <div className={`flex items-center justify-between border-b border-neutral-100 pb-5 ${isModalStyle ? 'mr-12' : ''}`}>
            <div>
              <h2 className="text-base font-bold text-neutral-800 tracking-tight flex items-center gap-2">
                <LegacyIcon name="smart_toy" className="text-neutral-500 text-[20px]" />
                {t('AI Agent Controller')}
              </h2>
              <p className="text-[11.5px] text-neutral-400 mt-1">
                {t('Display the operational directive frameworks and output manifests loaded in the execution sandbox.')}
              </p>
            </div>
            
            <button
              onClick={handleOpenCreate}
              className={`${BTN_SECONDARY} gap-1.5`}
            >
              <LegacyIcon name="add" className="text-[16px]" />
              {t('Create Agent')}
            </button>
          </div>

          {/* Agents Grid List */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {agents.length === 0 ? (
              <p className="text-xs text-neutral-400 italic col-span-full">
                {t('No agents configured. Create one to define prompts, deliverables, and execution settings.')}
              </p>
            ) : null}
            {agents.map((agent) => (
              <div
                key={agent.id}
                onClick={() => onActivateAgent?.(agent)}
                className={`p-5 border hover:border-neutral-300/80 bg-white rounded-xl shadow-xs hover:shadow-sm cursor-pointer transition-all duration-200 relative group flex flex-col justify-between min-h-[148px] ${
                  agent.id === activeAgentId
                    ? 'border-primary ring-1 ring-primary/25'
                    : 'border-neutral-200/45'
                }`}
              >
                <div>
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <AgentLogo
                        name={agent.name}
                        description={agent.description}
                        className="w-10 h-10 text-[10px]"
                        agentType={agentTypeFromAgent(agent)}
                      />
                      <div>
                        <h3 className="text-xs font-bold text-neutral-900 font-mono tracking-tight text-left">
                          {getAgentDisplayName(agent)}
                        </h3>
                        {isBuiltinAgent(agent) ? (
                          <span className={`${BADGE_SUCCESS} text-[8px] font-mono mt-1 inline-block`}>
                            {t('builtin')}
                          </span>
                        ) : null}
                        <p className="text-[10px] text-neutral-400 font-mono font-medium mt-0.5">
                          {t('Edited:')} {agent.lastModified}
                        </p>
                      </div>
                    </div>
                  </div>

                  <p className="text-[11.5px] text-neutral-500 mt-3.5 leading-relaxed text-left line-clamp-3">
                    {agent.description}
                  </p>
                </div>

                <div className="mt-4 pt-3.5 border-t border-neutral-100 flex items-center justify-between">
                  <div className="flex flex-wrap items-center gap-3">
                    <span className="text-[9.5px] font-mono text-neutral-400 flex items-center gap-1">
                      <LegacyIcon name="insert_drive_file" className="text-[13px]" />
                      {agent.deliverables ? agent.deliverables.length : 0} {t('Deliverables')}
                    </span>
                    {agent.skills && agent.skills.length > 0 && (
                      <span className="text-[9.5px] font-mono text-neutral-400 flex items-center gap-1">
                        <LegacyIcon name="school" className="text-[13px]" />
                        {agent.skills.length} {t('Skills')}
                      </span>
                    )}
                    {agentTypeFromAgent(agent) && (
                      <span className="text-[9.5px] font-mono text-neutral-800 bg-neutral-100 border border-neutral-200 px-1.5 py-0.2 rounded-md tracking-tight font-extrabold uppercase inline-flex items-center gap-1">
                        {resolveBrandLogoSrc({ agentType: agentTypeFromAgent(agent) }) ? (
                          <img
                            src={resolveBrandLogoSrc({ agentType: agentTypeFromAgent(agent) })}
                            alt=""
                            className="w-3 h-3 object-contain"
                          />
                        ) : null}
                        {agentTypeLabel(agentTypeFromAgent(agent), eligibleTools)}
                      </span>
                    )}
                    {agent.mcpTools && agent.mcpTools.length > 0 && (
                      <div className="flex items-center gap-1">
                        {agent.mcpTools.map(toolKey => {
                          const icon = {
                            'git_write_permission': 'terminal',
                            'figma_api_connect': 'palette',
                            'cmd_exec_permission': 'code',
                            'slack_webhook': 'forum',
                            'google_sheets_sync': 'table_chart'
                          }[toolKey] || 'extension';
                          const title = {
                            'git_write_permission': 'Local Git Access',
                            'figma_api_connect': 'Figma Design Schema',
                            'cmd_exec_permission': 'CLI Command Engine',
                            'slack_webhook': 'Slack Channel Webhook',
                            'google_sheets_sync': 'Google Sheets Sync'
                          }[toolKey] || toolKey;
                          return (
                            <span key={toolKey} className="w-4.5 h-4.5 rounded-full border border-neutral-200/60 bg-neutral-50 flex items-center justify-center text-neutral-500 font-mono shadow-3xs" title={title}>
                              <LegacyIcon name={icon} className="text-[10px]" />
                            </span>
                          );
                        })}
                      </div>
                    )}
                  </div>
                  
                  <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedAgent(agent);
                      }}
                      className={BTN_ICON}
                      title={t('View details')}
                      aria-label={t('View details')}
                    >
                      <LegacyIcon name="visibility" className="text-[16px]" />
                    </button>
                    <button
                      onClick={(e) => handleOpenEdit(agent, e)}
                      className={BTN_ICON}
                      title={t('Edit settings')}
                      aria-label={t('Edit settings')}
                    >
                      <LegacyIcon name="edit" className="text-[16px]" />
                    </button>
                    {!isBuiltinAgent(agent) ? (
                    <button
                      onClick={(e) => handleDelete(agent.id, e)}
                      className={`${BTN_ICON} hover:bg-red-50 text-red-500 hover:text-red-700`}
                      title={t('Delete agent')}
                      aria-label={t('Delete agent')}
                    >
                      <LegacyIcon name="delete" className="text-[16px]" />
                    </button>
                    ) : null}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ----------------- CREATE/EDIT AGENT DIAOG MODAL ----------------- */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-neutral-900/40 backdrop-blur-xs flex items-center justify-center z-50 animate-fade-in p-4 select-none">
          <div className="bg-white rounded-xl shadow-lg border border-neutral-200 max-w-xl w-full max-h-[85vh] flex flex-col overflow-hidden">
            
            {/* Modal Header */}
            <div className="h-14 border-b border-neutral-100 px-5 flex items-center justify-between flex-shrink-0 bg-neutral-50/50">
              <h3 className="text-[12.5px] font-extrabold text-neutral-900 font-mono tracking-tight uppercase flex items-center gap-2">
                <LegacyIcon name="smart_toy" className="text-[18px]" />
                {modalMode === 'create' ? t('Create New AI Agent') : t('Edit Agent Settings')}
              </h3>
              <button
                type="button"
                onClick={() => setIsModalOpen(false)}
                className={BTN_ICON}
                aria-label={t('Close')}
              >
                <LegacyIcon name="close" className="text-[18px]" />
              </button>
            </div>

            {/* Modal Body: Split into the designated 5 sections */}
            <div className="flex-1 overflow-y-auto p-5 space-y-5 select-text">

              {/* 🧩 MODULE 1: Identity & Engine */}
              <div className="p-4 bg-neutral-50/30 border border-neutral-200/60 rounded-xl space-y-3.5 animate-fade-in">
                <div className="flex items-center gap-1.5 pb-2 border-b border-neutral-200/40">
                  <span className="text-[9.5px] font-extrabold text-neutral-800 bg-neutral-100 border border-neutral-200 px-1.5 py-0.2 rounded font-mono tracking-wider uppercase">{t('Module 1')}</span>
                  <span className="text-[10.5px] font-extrabold text-[#111111] font-mono tracking-wide uppercase">{t('Identity & Driving Engine')}</span>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pb-1">
                  <div className="space-y-1">
                    <label className="text-[10px] font-bold text-neutral-500 tracking-wider uppercase font-mono block">{t('Agent Name')}</label>
                    <input
                      type="text"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder={t('e.g. Orchestration Dispatcher v2.0')}
                      className="w-full px-3 py-1.5 text-xs border border-neutral-200 focus:outline-none focus:border-neutral-900 focus:ring-1 focus:ring-neutral-900/20 bg-white rounded-lg font-mono"
                    />
                  </div>
                  
                  <div className="space-y-1">
                    <label className="text-[10px] font-bold text-neutral-500 tracking-wider uppercase font-mono block">{t('Agent Type')}</label>
                    {modalMode === 'edit' && editingId === BUILTIN_AGENT_ID ? (
                      <div>
                        <div className="flex items-center gap-1.5 px-3 py-1.5 border border-neutral-200 bg-neutral-100 rounded-lg">
                          <LegacyIcon name="bolt" className="text-[14px] text-neutral-700" />
                          <span className="text-xs font-mono font-bold text-neutral-900">Clutch</span>
                        </div>
                        <p className="text-[9.5px] text-neutral-400 mt-1.5 leading-relaxed">
                          {t('Built-in agent uses Clutch models. Pick a default model below or switch at runtime in chat.')}
                        </p>
                      </div>
                    ) : (
                      <select
                        value={agentType}
                        onChange={(e) => setAgentType(e.target.value as AgentTypeId)}
                        className="w-full px-3 py-1.5 text-xs border border-neutral-200 focus:outline-none focus:border-neutral-900 focus:ring-1 focus:ring-neutral-900/20 bg-white rounded-lg font-sans text-neutral-800"
                      >
                        {agentTypeOptions.map((option) => (
                          <option key={option.id} value={option.id}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                    )}
                    {modalMode !== 'edit' && agentTypeOptions.length === 1 && (
                      <p className="text-[9.5px] text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 mt-2 leading-relaxed">
                        {t('No CLI tools are connected yet. Open Settings → AI Tools, connect a tool, and run Auto-configure to add more agent types here.')}
                      </p>
                    )}
                  </div>
                </div>

                {agentType === 'clutch' && (
                  <div className="space-y-1">
                    <label className="text-[10px] font-bold text-neutral-500 tracking-wider uppercase font-mono block">
                      {t('Model')}
                    </label>
                    {clutchModels.length === 0 ? (
                      <p className="text-[10px] text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 leading-relaxed">
                        {t('No models configured yet. Add API keys or image/video models under Settings → Models first.')}
                      </p>
                    ) : (
                      <select
                        value={modelId}
                        onChange={(e) => setModelId(e.target.value)}
                        className="w-full px-3 py-1.5 text-xs border border-neutral-200 focus:outline-none focus:border-neutral-900 focus:ring-1 focus:ring-neutral-900/20 bg-white rounded-lg font-mono text-neutral-800"
                      >
                        <option value="">{t('Use global default model')}</option>
                        {clutchModels.map((model) => (
                          <option key={model.id} value={model.id}>
                            {model.name}
                            {model.modelKind === 'image' ? ` (${t('Image')})` : ''}
                            {model.modelKind === 'video' ? ` (${t('Video')})` : ''}
                          </option>
                        ))}
                      </select>
                    )}
                    <p className="text-[9.5px] text-neutral-400 leading-relaxed">
                      {t('Clutch agents run on Sidecar models (chat, image, or video). Leave empty to follow the global model in chat.')}
                    </p>
                  </div>
                )}

                 {agentType === 'ollama-cli' && (
                   <div className="space-y-1">
                     <label className="text-[10px] font-bold text-neutral-500 tracking-wider uppercase font-mono block">
                       {t('Ollama Model')}
                     </label>
                     {ollamaModels.length === 0 ? (
                       <div className="text-[10px] text-amber-700 bg-amber-50/50 border border-amber-200/60 rounded-xl p-3 space-y-2">
                         {ollamaError?.reason === 'connection_refused' ? (
                           <>
                             <p className="leading-relaxed font-sans">
                               <strong>{t('Ollama is not running.')}</strong> {t('Make sure the Ollama desktop application is open or that the Ollama daemon is running in the background.')}
                             </p>
                             {(ollamaError?.app_installed || ollamaError?.binary_installed) && (
                               <button
                                 type="button"
                                 onClick={handleStartOllama}
                                 disabled={isStartingOllama}
                                 className="px-3 py-1.5 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-[10px] font-bold font-mono transition-colors disabled:opacity-50 inline-flex items-center gap-1.5"
                               >
                                 {isStartingOllama ? (
                                   <>
                                     <span className="w-2.5 h-2.5 rounded-full border-2 border-white border-t-transparent animate-spin inline-block" />
                                     {t('Starting Ollama...')}
                                   </>
                                 ) : (
                                   t('Launch Ollama Service')
                                 )}
                               </button>
                             )}
                           </>
                         ) : (
                           <p className="leading-relaxed font-sans">
                             {t('No local models found. Ensure Ollama is running and run ollama pull <model> first (e.g., ollama pull qwen2.5-coder).')}
                           </p>
                         )}
                       </div>
                     ) : (
                       <select
                         value={ollamaModel}
                         onChange={(e) => setOllamaModel(e.target.value)}
                         className="w-full px-3 py-1.5 text-xs border border-neutral-200 focus:outline-none focus:border-neutral-900 focus:ring-1 focus:ring-neutral-900/20 bg-white rounded-lg font-mono text-neutral-800"
                       >
                         {ollamaModels.map((model) => (
                           <option key={model} value={model}>
                             {model}
                           </option>
                         ))}
                       </select>
                     )}
                     <p className="text-[9.5px] text-neutral-400 leading-relaxed">
                       {t('Select which locally installed Ollama model this agent uses at runtime.')}
                     </p>
                   </div>
                 )}

                <div className="space-y-1">
                  <label className="text-[10px] font-bold text-neutral-500 tracking-wider uppercase font-mono block">{t('Short Description')}</label>
                  <textarea
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    rows={2}
                    placeholder={t('Summarize the core execution task of this operational entity...')}
                    className="w-full px-3 py-2 text-xs border border-neutral-200 focus:outline-none focus:border-neutral-900 focus:ring-1 focus:ring-neutral-900/20 bg-white rounded-lg font-sans resize-none text-neutral-700"
                  />
                </div>
              </div>

              {/* 🧩 MODULE 2: Persona & Soul (System Prompt) */}
              <div className="p-4 bg-neutral-50/30 border border-neutral-200/60 rounded-xl space-y-2.5">
                <div className="flex items-center gap-1.5 pb-2 border-b border-neutral-200/40">
                  <span className="text-[9.5px] font-extrabold text-neutral-800 bg-neutral-100 border border-neutral-200 px-1.5 py-0.2 rounded font-mono tracking-wider uppercase">{t('Module 2')}</span>
                  <span className="text-[10.5px] font-extrabold text-[#111111] font-mono tracking-wide uppercase">{t('System Persona & Soul')}</span>
                </div>
                
                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold text-neutral-500 tracking-wider uppercase font-mono block">{t('System Prompt / Directive Summary')}</label>
                  <textarea
                    value={markdownDoc}
                    onChange={(e) => setMarkdownDoc(e.target.value)}
                    rows={2}
                    placeholder={t('Enter basic setup persona details...')}
                    className="w-full px-3 py-1.5 border border-neutral-200 focus:outline-none focus:border-neutral-900 focus:ring-1 focus:ring-neutral-900/20 bg-white rounded-lg font-mono text-xs leading-relaxed text-neutral-700"
                  />
                  <p className="text-[9.5px]/relaxed text-neutral-400 font-sans">
                    💡 <strong>{t('Tips')}:</strong> {t('Agent persona tips')}
                  </p>
                </div>
              </div>

              {/* 🧩 MODULE 3: Attach Agent Skills (Professional Manual) */}
              <div className="p-4 bg-neutral-50/30 border border-neutral-200/60 rounded-xl space-y-4">
                <div className="flex items-center justify-between pb-2 border-b border-neutral-200/40">
                  <div className="flex items-center gap-1.5">
                    <span className="text-[9.5px] font-extrabold text-neutral-800 bg-neutral-100 border border-neutral-200 px-1.5 py-0.2 rounded font-mono tracking-wider uppercase">{t('Module 3')}</span>
                    <span className="text-[10.5px] font-extrabold text-[#111111] font-mono tracking-wide uppercase">{t('Attach Agent Skills')}</span>
                  </div>
                  <span className="text-[8.5px] uppercase font-mono bg-neutral-100 text-neutral-700 border border-neutral-200/60 px-2 py-0.5 rounded">{t('Local-First')}</span>
                </div>

                <UnderDevelopmentNotice variant="compact" />

                {/* Sub-section 3A: Attach Skills Pill arrangement */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <label className="text-[10px] font-bold text-neutral-500 tracking-wider uppercase font-mono block">{t('Linked Agent Skills Manuals')}</label>
                      <span className="text-[9px] text-neutral-400 block font-normal">{t('Only active skills from your global directory are available below.')}</span>
                    </div>
                    <button
                      type="button"
                      onClick={() => setIsSkillsAttachOpen(!isSkillsAttachOpen)}
                      className="px-2.5 py-1 bg-white hover:bg-neutral-50 text-neutral-750 hover:text-black border border-neutral-200 rounded-lg text-[10.5px] font-bold flex items-center gap-1 transition-all shadow-3xs cursor-pointer select-none"
                    >
                      <LegacyIcon name="bookmark_add" className="text-[13px]" />
                      {t('Attach Skills')}
                    </button>
                  </div>

                  {isSkillsAttachOpen && (
                    <div className="bg-white border border-neutral-200 rounded-lg p-3 space-y-2.5 animate-fade-in shadow-sm">
                      <div className="text-[10px] font-bold text-neutral-400 uppercase font-mono pb-1 border-b border-neutral-105 flex items-center justify-between">
                        <span>{t('Fuzzy Search Active Specs')}</span>
                        <button type="button" onClick={() => setIsSkillsAttachOpen(false)} className="text-neutral-500 hover:text-neutral-800 font-mono text-[10.5px] font-bold">{t('Done')}</button>
                      </div>

                      {/* Fuzzy search input filtering selection candidates */}
                      <div className="relative">
                        <input
                          type="text"
                          value={skillsSearch}
                          onChange={(e) => setSkillsSearch(e.target.value)}
                          placeholder={t('Fuzzy search active skills (e.g. secure, performance)...')}
                          className="w-full px-2.5 py-1.5 border border-neutral-200 focus:outline-none focus:border-neutral-900 focus:ring-1 focus:ring-neutral-900/20 bg-neutral-50 focus:bg-white rounded-md text-xs font-mono"
                        />
                      </div>

                      <div className="max-h-36 overflow-y-auto space-y-1">
                        {(() => {
                          const activeSkills = scannedSkills.filter(s => s.isActiveGlobally);
                          const filtered = activeSkills.filter(s =>
                            s.label.toLowerCase().includes(skillsSearch.toLowerCase()) ||
                            s.key.toLowerCase().includes(skillsSearch.toLowerCase()) ||
                            s.desc.toLowerCase().includes(skillsSearch.toLowerCase())
                          );

                          if (activeSkills.length === 0) {
                            return (
                              <div className="text-[10px] text-neutral-400 font-sans p-2 bg-neutral-50 border border-neutral-150 rounded leading-relaxed">
                                ⚠️ {t('No globally active skills found. Please navigate to the left-side settings Skills Registry pane and activate some SKILL.md rules first!')}
                              </div>
                            );
                          }

                          if (filtered.length === 0) {
                            return (
                              <div className="text-[10px] text-neutral-450 italic p-2 text-center">
                                {t('No matching active skills found.')}
                              </div>
                            );
                          }

                          return filtered.map(skill => {
                            const isAttached = selectedSkills.includes(skill.key);
                            return (
                              <button
                                key={skill.key}
                                type="button"
                                onClick={() => {
                                  if (isAttached) {
                                    setSelectedSkills(selectedSkills.filter(k => k !== skill.key));
                                  } else {
                                    setSelectedSkills([...selectedSkills, skill.key]);
                                  }
                                }}
                                className={`w-full text-left p-2 rounded text-[11px] flex items-center justify-between transition-colors ${
                                  isAttached ? 'bg-neutral-100 text-neutral-900 font-medium' : 'hover:bg-neutral-100 text-neutral-600'
                                }`}
                              >
                                <div className="flex flex-col">
                                  <div className="flex items-center gap-1.5 font-bold">
                                    <LegacyIcon name="label" className="text-[12px] text-neutral-500" />
                                    <span>{skill.label}</span>
                                  </div>
                                  <span className="text-[9.5px] text-neutral-400 font-sans ml-4">{skill.desc}</span>
                                </div>
                                <LegacyIcon
                                  name={isAttached ? 'check_box' : 'check_box_outline_blank'}
                                  className="text-[15px] text-neutral-600 flex-shrink-0"
                                />
                              </button>
                            );
                          });
                        })()}
                      </div>
                    </div>
                  )}

                  {/* Attachment capsule pill labels list */}
                  <div className="flex flex-wrap gap-1.5 min-h-6 p-2 bg-white border border-neutral-150 rounded-lg items-center">
                    {selectedSkills.length > 0 ? (
                      selectedSkills.map(skillKey => {
                        const match = scannedSkills.find(s => s.key === skillKey) || { label: skillKey };
                        return (
                          <div
                            key={skillKey}
                            className="px-2.5 py-0.8 bg-neutral-100 text-neutral-700 border border-neutral-200 rounded-full text-[10px] font-bold font-mono tracking-tight flex items-center gap-1 hover:border-neutral-350 transition-colors"
                          >
                            <span>🏷️ {match.label}</span>
                            <button
                              type="button"
                              onClick={() => setSelectedSkills(selectedSkills.filter(k => k !== skillKey))}
                              className="hover:bg-neutral-250 text-neutral-450 hover:text-rose-700 rounded-full w-3.5 h-3.5 flex items-center justify-center font-sans text-[10px] font-extrabold focus:outline-none transition-colors"
                            >
                              ×
                            </button>
                          </div>
                        );
                      })
                    ) : (
                      <span className="text-[10px] text-neutral-400 italic">{t('No manual skills attached. Click \"Attach Skills\" to pick dynamic specifications.')}</span>
                    )}
                  </div>
                </div>
              </div>

              {/* 🧩 MODULE 4: Bind MCP Hub Servers */}
              <div className="p-4 bg-neutral-50/30 border border-neutral-200/60 rounded-xl space-y-3">
                <div className="flex items-center gap-1.5 pb-2 border-b border-neutral-200/40">
                  <span className="text-[9.5px] font-extrabold text-neutral-800 bg-neutral-100 border border-neutral-200 px-1.5 py-0.2 rounded font-mono tracking-wider uppercase">{t('Module 4')}</span>
                  <span className="text-[10.5px] font-extrabold text-[#111111] font-mono tracking-wide uppercase">{t('MCP Hub Server Bindings')}</span>
                </div>

                <UnderDevelopmentNotice variant="compact" />

                {agentType === 'clutch' ? (
                  <>
                    <p className="text-[10px] text-neutral-400 leading-normal">
                      {t('Bind MCP servers from Settings → MCP Hub. Used when this agent runs on Clutch models.')}
                    </p>
                    <div className="flex flex-col gap-1.5 border border-neutral-200 bg-white p-3 rounded-xl max-h-62 overflow-y-auto">
                      {mcpServers.length === 0 ? (
                        <p className="text-[10px] text-neutral-400 italic p-2">
                          {t('No enabled MCP servers in Hub. Add servers under Settings → MCP Hub first.')}
                        </p>
                      ) : (
                        mcpServers.map((server) => {
                          const isSelected = selectedMcpServerIds.includes(server.id);
                          return (
                            <button
                              key={server.id}
                              type="button"
                              onClick={() => {
                                if (isSelected) {
                                  setSelectedMcpServerIds(selectedMcpServerIds.filter((id) => id !== server.id));
                                } else {
                                  setSelectedMcpServerIds([...selectedMcpServerIds, server.id]);
                                }
                              }}
                              className={`p-2.5 border text-left rounded-lg transition-all flex items-start justify-between gap-2 cursor-pointer ${
                                isSelected
                                  ? 'bg-neutral-900/95 text-white border-neutral-900 shadow-2xs'
                                  : 'bg-white text-neutral-600 border-neutral-200/85 hover:bg-neutral-50 hover:text-neutral-800'
                              }`}
                            >
                              <div className="flex items-start gap-2.5 min-w-0">
                                <LegacyIcon
                                  name="hub"
                                  className={`text-[16px] p-1 rounded-md mt-0.5 ${
                                    isSelected ? 'bg-neutral-800 text-white' : 'bg-neutral-100 text-neutral-500'
                                  }`}
                                />
                                <div className="min-w-0">
                                  <div className="text-[10.5px] font-bold font-sans truncate">{server.name}</div>
                                  <div className={`text-[9.5px]/1.3 mt-0.5 truncate ${
                                    isSelected ? 'text-neutral-300' : 'text-neutral-400'
                                  }`}>
                                    {server.transport} · {server.toolsCount} {t('tools')}
                                  </div>
                                </div>
                              </div>
                              {isSelected && (
                                <span className="text-[7.5px] uppercase font-mono px-1.5 py-0.2 rounded-sm tracking-wider bg-neutral-700 text-white">
                                  {t('Bound')}
                                </span>
                              )}
                            </button>
                          );
                        })
                      )}
                    </div>
                  </>
                ) : (
                  <p className="text-[10px] text-neutral-500 leading-relaxed">
                    {t('Claude Code (Local CLI) agents use Skills and MCP installed in your local Claude Code environment — not Clutch MCP Hub bindings.')}
                  </p>
                )}
              </div>

              {/* 🧩 MODULE 5: Deliverables Output Constraints */}
              <div className="p-4 bg-neutral-50/30 border border-neutral-200/60 rounded-xl space-y-3">
                <div className="flex items-center gap-1.5 pb-2 border-b border-neutral-200/40">
                  <span className="text-[9.5px] font-extrabold text-neutral-800 bg-neutral-100 border border-neutral-200 px-1.5 py-0.2 rounded font-mono tracking-wider uppercase">{t('Module 5')}</span>
                  <span className="text-[10.5px] font-extrabold text-[#111111] font-mono tracking-wide uppercase">{t('Deliverables Config & State Update Rules')}</span>
                </div>

                <UnderDevelopmentNotice variant="compact" />

                <p className="text-[10px] text-neutral-400 block pb-1">
                  {t('Define the scheduled file assets produced by this agent. If orchestrators find these assets absent, rejection alerts trigger:')}
                </p>

                {/* File Template Insertion Field */}
                <div className="bg-white border border-neutral-200 p-3 rounded-lg space-y-2 flex flex-col justify-start">
                  <div className="grid grid-cols-3 gap-2">
                    <input
                      type="text"
                      placeholder={t('File name (e.g. results.json)')}
                      value={newDelivName}
                      onChange={(e) => setNewDelivName(e.target.value)}
                      className="col-span-2 px-2.5 py-1.5 text-xs border border-neutral-200 focus:outline-none focus:border-neutral-900 bg-neutral-50/20 rounded-lg font-mono placeholder:text-neutral-400"
                    />
                    <button
                      type="button"
                      onClick={handleAddDeliverable}
                      className="px-2.5 py-1.5 bg-neutral-900 hover:bg-black text-white text-[10px] font-bold rounded-lg transition-colors"
                    >
                      {t('+ Add List File')}
                    </button>
                  </div>
                  <textarea
                    placeholder={t('Enter file template specification markup inside...')}
                    value={newDelivContent}
                    onChange={(e) => setNewDelivContent(e.target.value)}
                    rows={2}
                    className="w-full px-2 py-1.5 border border-neutral-200 focus:outline-none focus:border-neutral-900 bg-neutral-50/10 rounded-lg font-mono text-[10px] placeholder:text-neutral-400"
                  />
                </div>

                {/* Connected list records items */}
                {deliverablesInput.length > 0 && (
                  <div className="space-y-1.5 pt-1 max-h-[148px] overflow-y-auto">
                    {deliverablesInput.map((deliv, index) => (
                      <div key={index} className="flex items-center justify-between p-2 border border-neutral-200/70 bg-white hover:bg-neutral-50/30 rounded-lg">
                        <div className="flex items-center gap-2 overflow-hidden">
                          <LegacyIcon name="insert_drive_file" className="text-[16px] text-neutral-400 font-mono" />
                          <span className="text-[11px] font-mono text-neutral-700 font-semibold truncate">{deliv.name}</span>
                        </div>
                        <button
                          type="button"
                          onClick={() => handleRemoveDeliverable(index)}
                          className={`${BTN_ICON} hover:bg-red-50 text-red-500 hover:text-red-700 animate-pulse`}
                          aria-label={t('Remove deliverable')}
                        >
                          <LegacyIcon name="close" className="text-[15px]" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Modal Actions */}
            <div className="h-14 border-t border-neutral-100 flex items-center justify-end px-5 gap-2.5 bg-neutral-50/30 flex-shrink-0">
              <button
                onClick={() => setIsModalOpen(false)}
                className={BTN_GHOST}
              >
                {t('Cancel')}
              </button>
              <button
                onClick={handleSave}
                className={BTN_PRIMARY}
              >
                {modalMode === 'create' ? t('Create AI Agent') : t('Save Configuration')}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ----------------- DELIVERABLE PREVIEW DIALOG MODAL ----------------- */}
      {isPreviewDeliverable && (
        <div className="fixed inset-0 bg-neutral-900/40 backdrop-blur-xs flex items-center justify-center z-50 animate-fade-in p-4 select-none">
          <div className="bg-white rounded-xl shadow-lg border border-neutral-200 max-w-2xl w-full max-h-[80vh] flex flex-col overflow-hidden">
            
            {/* Modal Header */}
            <div className="h-14 border-b border-neutral-100 px-5 flex items-center justify-between flex-shrink-0 bg-neutral-50/50">
              <div className="flex items-center gap-2">
                <LegacyIcon
                  name={isPreviewDeliverable.name.endsWith('.json') ? 'schema' : 'insert_drive_file'}
                  className="text-[17px] text-neutral-500 font-mono"
                />
                <span className="text-[11.5px] font-mono text-neutral-900 font-bold">{isPreviewDeliverable.name}</span>
              </div>
              <button
                type="button"
                onClick={() => setIsPreviewDeliverable(null)}
                className={BTN_ICON}
                aria-label={t('Close')}
              >
                <LegacyIcon name="close" className="text-[18px]" />
              </button>
            </div>

            {/* Modal Body: Code Display */}
            <div className="flex-1 overflow-auto p-5 select-text bg-[#FAF9F5] font-mono text-[11px] leading-relaxed border-b border-neutral-150">
              <div className="bg-neutral-950 text-neutral-200 p-5 rounded-xl border border-neutral-800 text-[11px] font-mono shadow-inner select-text max-w-full overflow-x-auto">
                <table className="w-full">
                  <tbody>
                    {isPreviewDeliverable.content.split('\n').map((line, idx) => (
                      <tr key={idx} className="hover:bg-neutral-900/60 leading-relaxed">
                        <td className="text-neutral-500 text-right pr-4 select-none w-8 border-r border-[#333333] text-[10px] font-semibold">{idx + 1}</td>
                        <td className="pl-4 whitespace-pre font-mono text-neutral-300">{line || ' '}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Modal Actions */}
            <div className="h-13 flex items-center justify-end px-5 gap-2 bg-neutral-50/30 flex-shrink-0">
              <button
                onClick={() => setIsPreviewDeliverable(null)}
                className={BTN_SECONDARY}
              >
                {t('Dismiss View')}
              </button>
            </div>

          </div>
        </div>
      )}
    </div>
  );
}
