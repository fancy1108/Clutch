import React, { useState } from 'react';

interface ModelItem {
  id: string;
  name: string;
  provider: string;
  contextWindow: string;
  temperature: number;
  description: string;
  isCustom?: boolean;
  endpoint?: string;
  apiKey?: string;
}

interface ModelsManagerProps {
  selectedModel: string;
  setSelectedModel: (modelName: string) => void;
  configuredModels: ModelItem[];
  setConfiguredModels: React.Dispatch<React.SetStateAction<ModelItem[]>>;
}

export const ModelsManager: React.FC<ModelsManagerProps> = ({
  selectedModel,
  setSelectedModel,
  configuredModels,
  setConfiguredModels,
}) => {
  const [showAddForm, setShowAddForm] = useState(false);
  const [newModel, setNewModel] = useState({
    name: '',
    provider: 'DeepSeek AI',
    customProvider: '',
    contextWindow: '128k context',
    temperature: 0.3,
    description: '',
    endpoint: '',
    apiKey: '',
  });

  const [apiKeysVisible, setApiKeysVisible] = useState<Record<string, boolean>>({});

  const providers = [
    'DeepSeek AI',
    'Google Gemini',
    'Anthropic Claude',
    'OpenAI GPT',
    'Groq Client',
    'Ollama (Local)',
    'OpenRouter',
    'Custom'
  ];

  const handleAddModel = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newModel.name.trim()) return;

    const actualProvider = newModel.provider === 'Custom' 
      ? (newModel.customProvider || 'Custom Provider') 
      : newModel.provider;

    const added: ModelItem = {
      id: `custom-${Date.now()}`,
      name: newModel.name.trim(),
      provider: actualProvider,
      contextWindow: newModel.contextWindow || '128k context',
      temperature: newModel.temperature,
      description: newModel.description.trim() || `Custom integrated model running via ${actualProvider}.`,
      isCustom: true,
      endpoint: newModel.endpoint.trim() || undefined,
      apiKey: newModel.apiKey.trim() || undefined,
    };

    setConfiguredModels(prev => [...prev, added]);
    setSelectedModel(added.name); // Auto-select newly added model
    setShowAddForm(false);
    
    // Reset form
    setNewModel({
      name: '',
      provider: 'DeepSeek AI',
      customProvider: '',
      contextWindow: '128k context',
      temperature: 0.3,
      description: '',
      endpoint: '',
      apiKey: '',
    });
  };

  const handleRemoveCustomModel = (id: string, name: string) => {
    if (selectedModel === name) {
      // Find another available model to select
      const remaining = configuredModels.filter(m => m.id !== id);
      if (remaining.length > 0) {
        setSelectedModel(remaining[0].name);
      }
    }
    setConfiguredModels(prev => prev.filter(m => m.id !== id));
  };

  const toggleApiKeyVisibility = (id: string) => {
    setApiKeysVisible(prev => ({
      ...prev,
      [id]: !prev[id]
    }));
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-surface-bright text-on-surface select-none leading-normal">
      {/* Scrollable Container */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        
        {/* Banner Headers */}
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-[20px] text-on-surface">layers</span>
            <h2 className="text-base font-bold text-on-surface tracking-tight font-sans">AI Workspace Models</h2>
          </div>
          <p className="text-xs text-on-surface-variant font-sans leading-relaxed">
            Monitor, connect, and configure Large Language Models for active agent execution, reasoning logic, and prompt engineering.
          </p>
        </div>

        {/* Form to Add Model */}
        {showAddForm ? (
          <form onSubmit={handleAddModel} className="p-4 bg-surface-container border border-outline rounded-xl space-y-4 animate-fade-in text-left">
            <div className="flex items-center justify-between pb-2 border-b border-outline/40">
              <span className="text-[10px] font-extrabold text-on-primary bg-primary border border-outline px-2 py-0.5 rounded font-mono tracking-wider uppercase">Integration Hub</span>
              <span className="text-[11px] font-extrabold text-on-surface font-mono tracking-wide uppercase">Connect External Model Provider</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-1">
                <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-wider block">Model Name / Identifier</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. DeepSeek-R1-Chat, Claude-3.5-Haiku"
                  value={newModel.name}
                  onChange={e => setNewModel(prev => ({ ...prev, name: e.target.value }))}
                  className="w-full text-xs border border-outline bg-surface rounded-lg px-3 py-2 text-on-surface focus:outline-hidden focus:border-on-surface placeholder:text-on-surface-variant/50"
                />
              </div>

              <div className="space-y-1">
                <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-wider block">Provider Platform</label>
                <select
                  value={newModel.provider}
                  onChange={e => {
                    const val = e.target.value;
                    let endpoint = '';
                    let name = newModel.name;
                    let desc = newModel.description;
                    if (val === 'Ollama (Local)') {
                      endpoint = 'http://localhost:11434';
                      if (!name) name = 'deepseek-r1:8b';
                      if (!desc) desc = 'Local Ollama endpoint running deepseek-r1 or similar light-weight model.';
                    } else if (val === 'DeepSeek AI') {
                      endpoint = 'https://api.deepseek.com/v1';
                    } else if (val === 'OpenRouter') {
                      endpoint = 'https://openrouter.ai/api/v1';
                    }
                    setNewModel(prev => ({
                      ...prev,
                      provider: val,
                      endpoint: endpoint || prev.endpoint,
                      name: name || prev.name,
                      description: desc || prev.description
                    }));
                  }}
                  className="w-full text-xs border border-outline bg-surface rounded-lg px-3 py-2 text-on-surface focus:outline-hidden focus:border-on-surface font-sans"
                >
                  {providers.map(p => (
                    <option key={p} value={p} className="bg-surface text-on-surface">{p}</option>
                  ))}
                </select>
              </div>

              {newModel.provider === 'Ollama (Local)' && (
                <div className="space-y-1 md:col-span-2 p-3 bg-surface-container-high border border-outline rounded-lg text-on-surface space-y-1 text-left">
                  <div className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider">
                    <span className="material-symbols-outlined text-[13px] text-on-surface-variant animate-pulse">terminal</span>
                    <span>Local Ollama Integration Guide</span>
                  </div>
                  <p className="text-[10px] text-on-surface-variant font-sans leading-relaxed">
                    Make sure Ollama is installed on your local system, then run this command in your terminal to enable browser cross-origin requests (CORS):
                  </p>
                  <pre className="text-[10.5px] font-mono bg-surface p-2 rounded-md border border-outline text-on-surface select-all overflow-x-auto">
                    OLLAMA_ORIGINS="*" ollama serve
                  </pre>
                  <p className="text-[10px] text-on-surface-variant font-sans leading-relaxed">
                    Then run your model, for example: <code className="bg-surface px-1 py-0.5 rounded font-mono border border-outline text-on-surface">ollama run deepseek-r1:8b</code>.
                  </p>
                </div>
              )}

              {newModel.provider === 'Custom' && (
                <div className="space-y-1 md:col-span-2">
                  <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-wider block">Custom Provider Name</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Private LLaMA Ingress, SiliconFlow"
                    value={newModel.customProvider}
                    onChange={e => setNewModel(prev => ({ ...prev, customProvider: e.target.value }))}
                    className="w-full text-xs border border-outline bg-surface rounded-lg px-3 py-2 text-on-surface focus:outline-hidden focus:border-on-surface placeholder:text-on-surface-variant/50"
                  />
                </div>
              )}

              <div className="space-y-1 md:col-span-2">
                <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-wider block">API Endpoint URL (Optional)</label>
                <input
                  type="url"
                  placeholder="e.g. https://api.deepseek.com/v1, http://localhost:11434/v1"
                  value={newModel.endpoint}
                  onChange={e => setNewModel(prev => ({ ...prev, endpoint: e.target.value }))}
                  className="w-full text-xs border border-outline bg-surface rounded-lg px-3 py-2 text-on-surface font-mono focus:outline-hidden focus:border-on-surface placeholder:text-on-surface-variant/50"
                />
              </div>

              <div className="space-y-1">
                <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-wider block">API Key / Credentials (Optional)</label>
                <input
                  type="password"
                  placeholder="sk-••••••••••••••••"
                  value={newModel.apiKey}
                  onChange={e => setNewModel(prev => ({ ...prev, apiKey: e.target.value }))}
                  className="w-full text-xs border border-outline bg-surface rounded-lg px-3 py-2 text-on-surface font-mono focus:outline-hidden focus:border-on-surface placeholder:text-on-surface-variant/50"
                />
              </div>

              <div className="space-y-1">
                <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-wider block">Context Window Spec</label>
                <input
                  type="text"
                  placeholder="e.g. 128k context, 32k context"
                  value={newModel.contextWindow}
                  onChange={e => setNewModel(prev => ({ ...prev, contextWindow: e.target.value }))}
                  className="w-full text-xs border border-outline bg-surface rounded-lg px-3 py-2 text-on-surface focus:outline-hidden focus:border-on-surface placeholder:text-on-surface-variant/50"
                />
              </div>

              <div className="space-y-1 md:col-span-2">
                <div className="flex justify-between items-center mb-1">
                  <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-wider block">Default Temperature</label>
                  <span className="text-[10px] font-mono font-bold bg-surface-container text-on-surface-variant px-1.5 py-0.2 rounded">{newModel.temperature.toFixed(2)}</span>
                </div>
                <input
                  type="range"
                  min="0.0"
                  max="1.5"
                  step="0.05"
                  value={newModel.temperature}
                  onChange={e => setNewModel(prev => ({ ...prev, temperature: parseFloat(e.target.value) }))}
                  className="w-full accent-primary cursor-pointer h-1.5 bg-outline rounded-lg appearance-none"
                />
              </div>

              <div className="space-y-1 md:col-span-2">
                <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-wider block">Model Notes / Purpose</label>
                <textarea
                  placeholder="e.g. Fine-tuned specialized model for private security sweeps."
                  rows={2}
                  value={newModel.description}
                  onChange={e => setNewModel(prev => ({ ...prev, description: e.target.value }))}
                  className="w-full text-xs border border-outline bg-surface rounded-lg p-2.5 text-on-surface focus:outline-hidden focus:border-on-surface placeholder:text-on-surface-variant/50"
                />
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setShowAddForm(false)}
                className="bg-surface-container hover:bg-surface-container-high border border-outline text-on-surface px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="bg-primary hover:opacity-90 text-on-primary px-4 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer shadow-xs"
              >
                Save & Connect Model
              </button>
            </div>
          </form>
        ) : (
          <div className="flex items-center justify-between p-3.5 bg-surface-container border border-outline rounded-xl">
            <div className="text-left">
              <h3 className="text-xs font-bold text-on-surface">Add External Model Provider</h3>
              <p className="text-[10.5px] text-on-surface-variant font-sans">Integrate local Ollama, Groq keys, OpenRouter, or private DeepSeek clusters easily.</p>
            </div>
            <button
              onClick={() => setShowAddForm(true)}
              className="bg-primary hover:opacity-90 text-on-primary px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 cursor-pointer shadow-xs"
            >
              <span className="material-symbols-outlined text-[15px]">add</span>
              <span>Connect Model</span>
            </button>
          </div>
        )}

        {/* Configured Models Grid */}
        <div className="space-y-3 text-left">
          <div className="flex items-center justify-between pb-1 border-b border-outline/40">
            <span className="text-[10px] font-extrabold text-on-surface-variant uppercase tracking-widest">Configured & Connected Models</span>
            <span className="text-[10px] font-mono text-on-surface-variant">{configuredModels.length} Installed</span>
          </div>

          <div className="grid grid-cols-1 gap-2.5">
            {configuredModels.map(model => {
              const isActive = selectedModel === model.name;
              return (
                <div
                  key={model.id}
                  onClick={() => setSelectedModel(model.name)}
                  className={`relative p-4 rounded-xl border transition-all cursor-pointer flex flex-col md:flex-row md:items-center justify-between gap-4 group ${
                    isActive
                      ? 'bg-surface-container border-primary shadow-xs'
                      : 'bg-surface hover:bg-surface-container-high/20 border-outline/65'
                  }`}
                >
                  {/* Left Column: Details */}
                  <div className="flex-1 space-y-1.5 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-xs font-bold text-on-surface truncate">
                        {model.name}
                      </span>
                      
                      <span className="text-[8.5px] uppercase font-mono bg-surface-container-high text-on-surface-variant border border-outline/60 px-1.5 py-0.2 rounded font-extrabold">
                        {model.provider}
                      </span>

                      {model.isCustom && (
                        <span className="text-[8.5px] uppercase font-mono bg-primary text-on-primary px-1.5 py-0.2 rounded font-bold">
                          Custom
                        </span>
                      )}

                      {isActive && (
                        <span className="text-[8.5px] uppercase font-mono bg-emerald-50 text-emerald-800 border border-emerald-200 px-1.5 py-0.2 rounded font-extrabold flex items-center gap-0.5">
                          <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 inline-block"></span>
                          Active
                        </span>
                      )}
                    </div>

                    <p className="text-[11.5px] text-on-surface-variant font-sans leading-relaxed pr-6">
                      {model.description}
                    </p>

                    <div className="flex items-center gap-3 text-[10px] text-on-surface-variant flex-wrap pt-0.5">
                      <div className="flex items-center gap-1 font-mono">
                        <span className="material-symbols-outlined text-[13px]">database</span>
                        <span>{model.contextWindow}</span>
                      </div>
                      <div className="flex items-center gap-1 font-mono">
                        <span className="material-symbols-outlined text-[13px]">tune</span>
                        <span>Temp: {model.temperature.toFixed(2)}</span>
                      </div>
                      {model.endpoint && (
                        <div className="flex items-center gap-1 font-mono text-[9px] bg-surface-container border border-outline rounded-sm px-1.5 py-0.2 truncate max-w-[240px]" title={model.endpoint}>
                          <span className="text-on-surface-variant">Endpoint:</span>
                          <span className="text-on-surface truncate">{model.endpoint}</span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Right Column: Active Check or Custom Management Controls */}
                  <div className="flex items-center gap-2 justify-end self-end md:self-center flex-shrink-0" onClick={e => e.stopPropagation()}>
                    {isActive ? (
                      <span className="material-symbols-outlined text-[20px] text-on-primary bg-primary p-1.5 rounded-full border border-outline/50">
                        check
                      </span>
                    ) : (
                      <button
                        onClick={() => setSelectedModel(model.name)}
                        className="bg-surface-container hover:bg-primary hover:text-on-primary border border-outline text-on-surface px-3 py-1.5 rounded-lg text-[10.5px] font-bold transition-all cursor-pointer"
                      >
                        Activate Mode
                      </button>
                    )}

                    {model.isCustom && (
                      <button
                        onClick={() => handleRemoveCustomModel(model.id, model.name)}
                        className="p-1.5 bg-rose-50 hover:bg-rose-600 border border-rose-200 text-rose-800 hover:text-white rounded-lg transition-all cursor-pointer flex items-center justify-center"
                        title="Delete connected model"
                      >
                        <span className="material-symbols-outlined text-[16px]">delete</span>
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

      </div>

      {/* Footer statistics bar */}
      <div className="h-10 bg-surface-container border-t border-outline flex items-center justify-between px-6 text-[10px] text-on-surface-variant select-none">
        <div className="flex items-center gap-1 font-mono font-bold uppercase tracking-wide">
          <span>Active LLM Orchestrator:</span>
          <span className="text-on-surface font-extrabold">{selectedModel}</span>
        </div>
        <div className="flex items-center gap-4 text-xs font-sans font-medium">
          <div className="flex items-center gap-1">
            <span className="h-2 w-2 rounded-full bg-emerald-500 inline-block"></span>
            <span className="font-mono text-on-surface-variant text-[9.5px]">PROVIDER SYNCED</span>
          </div>
        </div>
      </div>
    </div>
  );
};
