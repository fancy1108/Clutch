import React, { useState, useMemo, useCallback, useEffect } from 'react';
import { WorkflowStep, WorkflowDef } from '../types';
import {
  ReactFlow,
  Controls,
  Background,
  applyNodeChanges,
  applyEdgeChanges,
  addEdge,
  Handle,
  Position,
  Node,
  Edge,
  NodeChange,
  EdgeChange,
  Connection,
  MarkerType
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { WorkflowJsonPanel } from './WorkflowJsonPanel';
import {
  canvasToCompiler,
  compilerToCanvas,
  formatCompilerJson,
  isCanvasCompatible,
  parseCompilerJson,
  type CompilerWorkflow,
} from '../services/workflowFormat';
import {
  deleteUserWorkflow,
  listWorkflowItems,
  loadTemplateWorkflow,
  loadUserWorkflow,
  saveUserWorkflow,
  validateWorkflow,
  type WorkflowListItem,
} from '../services/workflowApi';

type EditorViewMode = 'canvas' | 'json';

interface WorkflowOrchestrationProps {
  onClose: () => void;
  isModalStyle?: boolean;
}

const DEFAULT_AVATAR = 'https://lh3.googleusercontent.com/aida-public/AB6AXuCdbGLlsb3N3uOkfOjw1Q1_yDEdGIJRGnmhLu-FVragfIKdNByQw1J1dUhUyD0bhtU68_IQlwgYzvIetQ2bY0YH_lZtUPtQ34nuKBxaxPyS3e2_NiWBHxGCtDAanZ14d9Jj74bIX1CMvh__wE2web2l3_MmMZ3M6VbcAyIQ32DmLoC1ZxOulFXqko_7SDi7dj4UYhiz2GZJT9mIeqNcXO-z24SVjGrZaOr-FBsXxb6cUVkNht5QSQLvRy955U1VtJCFXs670Vt4hbki';

const CustomNode = ({ data }: { data: any }) => {
  return (
    <div className="group min-w-[220px] max-w-xs p-3 bg-white border border-neutral-300 rounded-xl shadow-sm relative hover:border-neutral-400 transition-colors">
      <Handle 
        type="target" 
        position={Position.Top} 
        className="!bg-neutral-400 hover:!bg-neutral-700 !w-3 !h-3 border-2 border-white rounded-full transition-colors cursor-crosshair" 
        style={{ transform: 'translateY(-2px)' }}
      />
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg overflow-hidden flex-shrink-0 flex items-center justify-center bg-neutral-100">
            {data.avatar ? (
              <img className="w-5 h-5 object-contain" src={data.avatar} alt={data.agent} />
            ) : (
              <span className="material-symbols-outlined text-[15px] text-neutral-500">smart_toy</span>
            )}
          </div>
          <div className="overflow-hidden text-left flex-1 max-w-[130px]">
            <p className="text-xs font-bold text-neutral-900 truncate">{data.name}</p>
            <p className="text-[9px] font-medium text-neutral-400 font-mono truncate">
              {data.agent} {data.aiTool ? `| ${data.aiTool}` : ''}
            </p>
          </div>
        </div>
        <div className="flex gap-1">
          <button 
            type="button"
            onClick={() => data.onEdit(data.id)}
            className="text-neutral-300 hover:text-neutral-900 transition-colors"
          >
            <span className="material-symbols-outlined text-[15px]">edit</span>
          </button>
          <button 
            type="button"
            onClick={() => data.onDelete(data.id)}
            className="text-neutral-300 hover:text-red-600 transition-colors"
          >
            <span className="material-symbols-outlined text-[15px]">delete</span>
          </button>
        </div>
      </div>
      <Handle 
        type="source" 
        position={Position.Bottom} 
        className="!bg-neutral-400 hover:!bg-neutral-700 !w-3 !h-3 border-2 border-white rounded-full transition-colors cursor-crosshair" 
        style={{ transform: 'translateY(2px)' }}
      />
    </div>
  );
};

const nodeTypes = {
  custom: CustomNode,
};

export const WorkflowOrchestration: React.FC<WorkflowOrchestrationProps> = ({ onClose, isModalStyle }) => {
  const [listItems, setListItems] = useState<WorkflowListItem[]>([]);
  const [activeItem, setActiveItem] = useState<WorkflowListItem | null>(null);
  const [workflows, setWorkflows] = useState<WorkflowDef[]>([]);
  const [activeWorkflowId, setActiveWorkflowId] = useState<string>('');
  const [viewMode, setViewMode] = useState<EditorViewMode>('json');
  const [jsonText, setJsonText] = useState('');
  const [canvasCompatible, setCanvasCompatible] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveStatus, setSaveStatus] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  // Nodes and edges states
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);

  // Modals state
  const [editingNodeId, setEditingNodeId] = useState<string | null>(null);
  const [nodeForm, setNodeForm] = useState<Partial<WorkflowStep>>({});

  // New workflow creation states
  const [isCreatingWorkflow, setIsCreatingWorkflow] = useState(false);
  const [newWorkflowName, setNewWorkflowName] = useState('');
  const [newWorkflowDesc, setNewWorkflowDesc] = useState('');
  const [newWorkflowIcon, setNewWorkflowIcon] = useState('account_tree');

  const activeWorkflow = workflows.find(wf => wf.id === activeWorkflowId);

  const refreshList = useCallback(async () => {
    const items = await listWorkflowItems();
    setListItems(items);
    return items;
  }, []);

  const applyCompilerWorkflow = useCallback((item: WorkflowListItem, workflow: CompilerWorkflow) => {
    setActiveItem(item);
    setJsonText(formatCompilerJson(workflow));
    setSaveError(null);
    setSaveStatus(null);
    const compatible = isCanvasCompatible(workflow);
    setCanvasCompatible(compatible);
    if (compatible) {
      const canvas = compilerToCanvas(workflow, item.source === 'template' ? 'movie' : 'account_tree');
      setWorkflows((prev) => {
        const rest = prev.filter((w) => w.id !== canvas.id);
        return [...rest, canvas];
      });
      setActiveWorkflowId(canvas.id);
    } else {
      setViewMode('json');
    }
  }, []);

  const selectWorkflow = useCallback(async (item: WorkflowListItem) => {
    try {
      setLoadError(null);
      const workflow =
        item.source === 'template'
          ? await loadTemplateWorkflow(item.id)
          : await loadUserWorkflow(item.id);
      applyCompilerWorkflow(item, workflow);
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : '加载失败');
    }
  }, [applyCompilerWorkflow]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        setLoading(true);
        const items = await refreshList();
        if (!cancelled && items.length > 0) {
          await selectWorkflow(items[0]);
        }
      } catch (err) {
        if (!cancelled) {
          setLoadError(err instanceof Error ? err.message : '无法连接 Sidecar');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [refreshList, selectWorkflow]);

  const handleSaveWorkflow = async () => {
    setIsSaving(true);
    setSaveError(null);
    setSaveStatus(null);
    try {
      let compiler: CompilerWorkflow;
      if (viewMode === 'canvas' && canvasCompatible && activeWorkflow) {
        compiler = canvasToCompiler(activeWorkflow);
      } else {
        compiler = parseCompilerJson(jsonText);
      }

      if (activeItem?.readOnly) {
        compiler = {
          ...compiler,
          id: compiler.id.endsWith('-custom') ? compiler.id : `${compiler.id}-custom`,
          name: `${compiler.name} (副本)`,
        };
      }

      await validateWorkflow(compiler);
      await saveUserWorkflow(compiler);
      setSaveStatus('已保存到本机工作流目录');
      const items = await refreshList();
      const saved = items.find((i) => i.id === compiler.id && i.source === 'user');
      if (saved) await selectWorkflow(saved);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : '保存失败');
    } finally {
      setIsSaving(false);
    }
  };

  const syncJsonFromCanvas = () => {
    if (!activeWorkflow) return;
    const compiler = canvasToCompiler(activeWorkflow);
    setJsonText(formatCompilerJson(compiler));
  };

  // Layout conversion
  React.useEffect(() => {
    if (activeWorkflow) {
      const newNodes: Node[] = activeWorkflow.steps.map((step, idx) => ({
        id: step.id.toString(),
        type: 'custom',
        position: step.position || { x: 250, y: idx * 100 + 50 },
        data: {
          ...step,
          onEdit: (id: string) => openNodeEditor(id),
          onDelete: (id: string) => deleteNode(id),
        }
      }));

      const newEdges: Edge[] = [];
      activeWorkflow.steps.forEach(step => {
        if (step.nextSteps) {
          step.nextSteps.forEach(nextId => {
            newEdges.push({
              id: `e-${step.id}-${nextId}`,
              source: step.id.toString(),
              target: nextId.toString(),
              type: 'smoothstep',
              animated: true,
              style: { stroke: '#a3a3a3', strokeWidth: 2 },
              markerEnd: { type: MarkerType.ArrowClosed, color: '#a3a3a3' },
            });
          });
        }
      });
      setNodes(newNodes);
      setEdges(newEdges);
    }
  }, [activeWorkflowId, workflows]); // Also update when workflows changes

  const onNodesChange = useCallback((changes: NodeChange[]) => {
    setNodes((nds) => applyNodeChanges(changes, nds));
    
    // Save to global state only at the end of the drag to prevent heavy re-renders
    const positionDropChanges = changes.filter(c => c.type === 'position' && (c as any).position && (c as any).dragging === false);
    if (positionDropChanges.length > 0) {
      setWorkflows(prev => prev.map(wf => {
        if (wf.id !== activeWorkflowId) return wf;
        return {
          ...wf,
          steps: wf.steps.map(s => {
            const dragChange = positionDropChanges.find(c => (c as any).id === s.id);
            if (dragChange && dragChange.type === 'position' && (dragChange as any).position) {
              return { ...s, position: (dragChange as any).position };
            }
            return s;
          })
        };
      }));
    }
  }, [activeWorkflowId]);
  const onEdgesChange = useCallback((changes: EdgeChange[]) => setEdges((eds) => applyEdgeChanges(changes, eds)), []);
  const onConnect = useCallback((connection: Connection) => {
    // Add connection
    const newEdge: Edge = {
      ...connection,
      id: `e-${connection.source}-${connection.target}`,
      type: 'smoothstep',
      animated: true,
      style: { stroke: '#a3a3a3', strokeWidth: 2 },
      markerEnd: { type: MarkerType.ArrowClosed, color: '#a3a3a3' }
    } as Edge;
    
    setEdges((eds) => addEdge(newEdge, eds));

    // Update underlying workflow steps
    setWorkflows(prev => prev.map(wf => {
      if (wf.id !== activeWorkflowId) return wf;
      return {
        ...wf,
        steps: wf.steps.map(step => {
          if (step.id.toString() === connection.source) {
            return {
              ...step,
              nextSteps: [...(step.nextSteps || []), connection.target]
            }
          }
          return step;
        })
      }
    }));
  }, [activeWorkflowId]);

  const handleCreateWorkflow = () => {
    setIsCreatingWorkflow(true);
    setNewWorkflowName('');
    setNewWorkflowDesc('');
    setNewWorkflowIcon('account_tree');
  };

  const saveNewWorkflow = async () => {
    if (!newWorkflowName.trim()) return;
    const slug = newWorkflowName
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-|-$/g, '') || `flow-${Date.now()}`;
    const empty: CompilerWorkflow = {
      id: slug,
      name: newWorkflowName.trim(),
      version: 1,
      nodes: [
        {
          id: 'n1',
          type: 'agent_task',
          position: { x: 250, y: 80 },
          data: {
            label: '第一步',
            agent: 'Builder',
            instruction: newWorkflowDesc.trim() || '在此填写任务说明',
          },
        },
        { id: 'end', type: 'end', position: { x: 250, y: 220 }, data: { label: '完成' } },
      ],
      edges: [
        { id: 'e1', source: 'start', target: 'n1' },
        { id: 'e2', source: 'n1', target: 'end' },
      ],
    };
    try {
      await validateWorkflow(empty);
      await saveUserWorkflow(empty);
      setIsCreatingWorkflow(false);
      const items = await refreshList();
      const created = items.find((i) => i.id === slug);
      if (created) await selectWorkflow(created);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : '创建工作流失败');
    }
  };

  const deleteWorkflow = async (id: string, source: 'template' | 'user') => {
    if (source === 'template') return;
    if (!confirm('确定删除此工作流？')) return;
    try {
      await deleteUserWorkflow(id);
      const items = await refreshList();
      if (items.length > 0) await selectWorkflow(items[0]);
      else {
        setActiveItem(null);
        setActiveWorkflowId('');
        setJsonText('');
      }
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : '删除失败');
    }
  };

  const deleteNode = (nodeId: string) => {
    setWorkflows(prev => prev.map(wf => {
      if (wf.id !== activeWorkflowId) return wf;
      return {
        ...wf,
        steps: wf.steps
          .filter(s => s.id.toString() !== nodeId)
          .map(s => ({
            ...s,
            nextSteps: (s.nextSteps || []).filter(n => n.toString() !== nodeId)
          }))
      }
    }));
  };

  const addNode = () => {
    const newNodeId = `step-${Date.now()}`;
    setEditingNodeId(newNodeId);
    setNodeForm({
      name: 'New Step',
      agent: 'Orchestrator',
      aiTool: '',
      description: '',
      nextSteps: [],
      fromSteps: []
    } as any);
  };

  const openNodeEditor = (nodeId: string) => {
    const node = activeWorkflow?.steps.find(s => s.id.toString() === nodeId);
    if (node) {
      // Find all steps that have nodeId in their nextSteps
      const incomingSteps = activeWorkflow?.steps
        .filter(s => (s.nextSteps || []).includes(nodeId))
        .map(s => s.id.toString()) || [];

      setEditingNodeId(nodeId);
      setNodeForm({ 
        ...node,
        nextSteps: node.nextSteps || [],
        fromSteps: incomingSteps
      } as any);
    }
  };

  const saveNode = () => {
    if (!editingNodeId) return;

    setWorkflows(prev => prev.map(wf => {
      if (wf.id !== activeWorkflowId) return wf;
      
      const formFromSteps = (nodeForm as any).fromSteps || [];
      const formNextSteps = nodeForm.nextSteps || [];

      let updatedSteps = [...wf.steps];
      const existingStepIndex = updatedSteps.findIndex(s => s.id.toString() === editingNodeId);

      const targetStep: WorkflowStep = {
        id: editingNodeId,
        name: nodeForm.name || 'New Step',
        agent: nodeForm.agent || 'Orchestrator',
        aiTool: nodeForm.aiTool || '',
        description: nodeForm.description || '',
        avatar: nodeForm.avatar || DEFAULT_AVATAR,
        nextSteps: formNextSteps,
        position: nodeForm.position || (existingStepIndex >= 0 ? updatedSteps[existingStepIndex].position : { x: 250, y: wf.steps.length * 100 + 50 })
      };

      if (existingStepIndex >= 0) {
        updatedSteps[existingStepIndex] = targetStep;
      } else {
        updatedSteps.push(targetStep);
      }

      // Sync incoming connections (fromSteps)
      updatedSteps = updatedSteps.map(s => {
        if (s.id.toString() === editingNodeId) {
          return s; // Target node is kept as is
        }
        const isFromSelected = formFromSteps.includes(s.id.toString());
        const alreadyConnected = (s.nextSteps || []).includes(editingNodeId);

        if (isFromSelected && !alreadyConnected) {
          return {
            ...s,
            nextSteps: [...(s.nextSteps || []), editingNodeId]
          };
        } else if (!isFromSelected && alreadyConnected) {
          return {
            ...s,
            nextSteps: (s.nextSteps || []).filter(id => id !== editingNodeId)
          };
        }
        return s;
      });

      return {
        ...wf,
        steps: updatedSteps
      };
    }));

    setEditingNodeId(null);
  };

  const onEdgesDelete = useCallback((edgesToDelete: Edge[]) => {
    const edgeMap = edgesToDelete.reduce((acc, edge) => {
      if (!acc[edge.source]) acc[edge.source] = [];
      acc[edge.source].push(edge.target);
      return acc;
    }, {} as Record<string, string[]>);

    setWorkflows(prev => prev.map(wf => {
      if (wf.id !== activeWorkflowId) return wf;
      return {
        ...wf,
        steps: wf.steps.map(s => {
          if (edgeMap[s.id.toString()]) {
            return {
              ...s,
              nextSteps: (s.nextSteps || []).filter(target => !edgeMap[s.id.toString()].includes(target.toString()))
            }
          }
          return s;
        })
      };
    }));
  }, [activeWorkflowId]);


  const contentElement = (
    <div className="flex-1 h-full flex flex-col bg-white overflow-hidden">
      <header className={`flex-shrink-0 z-20 bg-white/95 backdrop-blur py-5 flex items-center justify-between border-b border-neutral-100 pl-8 ${isModalStyle ? 'pr-14' : 'pr-8'}`}>
        <div className="text-left">
          <h2 className="text-sm font-bold text-neutral-800 tracking-tight font-sans">Workflow Orchestration</h2>
          <p className="text-[11px] text-neutral-400 mt-0.5">
            Design and manage cooperative multi-agent state pipelines.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {saveStatus && (
            <span className="text-[10px] font-mono text-emerald-700 bg-emerald-50 border border-emerald-200/80 px-2 py-1 rounded-lg">
              {saveStatus}
            </span>
          )}
          <button
            type="button"
            onClick={handleSaveWorkflow}
            disabled={isSaving || loading}
            className="flex items-center gap-1.5 px-4 py-2 bg-neutral-900 hover:bg-neutral-800 text-white border border-neutral-900 rounded-xl text-xs font-bold transition-all shadow-sm disabled:opacity-40 cursor-pointer"
          >
            <span className="material-symbols-outlined text-[15px]">save</span>
            {activeItem?.readOnly ? '另存为副本' : '保存'}
          </button>
          <button
            onClick={handleCreateWorkflow}
            className="flex items-center gap-1.5 px-4 py-2 bg-neutral-50 hover:bg-neutral-100 text-neutral-800 border border-neutral-200 rounded-xl text-xs font-bold transition-all cursor-pointer"
          >
            <span className="material-symbols-outlined text-[15px]">add</span>
            Create Flow
          </button>
        </div>
      </header>

      <div className="flex flex-1 min-h-0">
        {/* Left sidebar for workflows */}
        <div className="w-[280px] border-r border-neutral-100 bg-neutral-50/30 overflow-y-auto flex flex-col p-4 gap-3 overflow-x-hidden">
          <h3 className="text-[10px] font-bold text-neutral-400 uppercase tracking-widest pl-2 mb-1 text-left">
            Active SOP Workflows
          </h3>
          {loading && (
            <p className="text-[10px] text-neutral-400 pl-2 font-mono">加载中…</p>
          )}
          {loadError && (
            <p className="text-[10px] text-rose-700 bg-rose-50 border border-rose-200/80 rounded-lg px-2 py-1.5 mx-1">
              {loadError}
            </p>
          )}
          {listItems.map(item => (
            <div
              key={`${item.source}-${item.id}`}
              onClick={() => selectWorkflow(item)}
              className={`p-3 border rounded-xl flex items-center justify-between cursor-pointer transition-all bg-white relative ${
                activeItem?.id === item.id && activeItem?.source === item.source
                  ? 'border-neutral-300 bg-neutral-50 shadow-sm'
                  : 'border-neutral-200/50 hover:border-neutral-300 shadow-xs'
              }`}
            >
              <div className="flex items-center gap-3 overflow-hidden">
                <div className="w-8 h-8 rounded-lg bg-neutral-100/70 flex flex-shrink-0 items-center justify-center">
                  <span className="material-symbols-outlined text-neutral-600 text-[18px]">
                    {item.source === 'template' ? 'movie' : 'account_tree'}
                  </span>
                </div>
                <div className="overflow-hidden text-left">
                  <h4 className="text-[11px] font-bold text-neutral-800 truncate">{item.name}</h4>
                  <p className="text-[9px] text-neutral-400 font-mono mt-0.5 truncate">
                    {item.source === 'template' ? '内置模板 · 只读' : '用户工作流'}
                  </p>
                </div>
              </div>
              {!item.readOnly && (
                <button
                  type="button"
                  onClick={(e) => { e.stopPropagation(); deleteWorkflow(item.id, item.source); }}
                  className="text-neutral-300 hover:text-red-500 transition-colors ml-2 flex-shrink-0"
                >
                  <span className="material-symbols-outlined text-[14px]">delete</span>
                </button>
              )}
            </div>
          ))}
        </div>

        <div className="flex-1 flex flex-col relative min-h-0">
          {activeItem ? (
            <>
              <div className="flex-shrink-0 flex items-center justify-between px-6 py-3 border-b border-neutral-100 bg-white/95">
                <div className="text-left">
                  <span className="text-xs font-extrabold text-neutral-800 font-sans tracking-tight block uppercase">
                    {activeItem.name}
                  </span>
                  <span className="text-[10px] text-neutral-400 font-mono mt-0.5 block">
                    {canvasCompatible ? '支持画布编辑（简单线性流程）' : '仅 JSON 模式（含检查/审批/分支）'}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="flex rounded-lg border border-neutral-200 overflow-hidden text-[11px] font-bold">
                    <button
                      type="button"
                      disabled={!canvasCompatible}
                      onClick={() => { syncJsonFromCanvas(); setViewMode('canvas'); }}
                      className={`px-3 py-1.5 transition-colors ${
                        viewMode === 'canvas'
                          ? 'bg-neutral-900 text-white'
                          : 'bg-white text-neutral-600 hover:bg-neutral-50 disabled:opacity-40'
                      }`}
                    >
                      画布
                    </button>
                    <button
                      type="button"
                      onClick={() => setViewMode('json')}
                      className={`px-3 py-1.5 transition-colors ${
                        viewMode === 'json'
                          ? 'bg-neutral-900 text-white'
                          : 'bg-white text-neutral-600 hover:bg-neutral-50'
                      }`}
                    >
                      JSON
                    </button>
                  </div>
                  {viewMode === 'canvas' && canvasCompatible && (
                    <button
                      type="button"
                      onClick={addNode}
                      className="flex items-center gap-1.5 px-3 py-1.5 bg-neutral-50 hover:bg-neutral-100 text-neutral-700 rounded-lg text-xs font-bold border border-neutral-200/80 cursor-pointer"
                    >
                      <span className="material-symbols-outlined text-[15px]">add</span>
                      Add Node
                    </button>
                  )}
                </div>
              </div>

              {viewMode === 'json' ? (
                <WorkflowJsonPanel
                  value={jsonText}
                  onChange={setJsonText}
                  readOnly={false}
                  error={saveError}
                  hint={
                    !canvasCompatible
                      ? '复杂流程：请用 JSON 编辑'
                      : activeItem.readOnly
                        ? '内置模板：编辑后请「另存为副本」'
                        : null
                  }
                />
              ) : activeWorkflow ? (
                <div className="flex-1 relative bg-neutral-50/20 min-h-0">
                  <ReactFlow
                    nodes={nodes}
                    edges={edges}
                    onNodesChange={onNodesChange}
                    onEdgesChange={onEdgesChange}
                    onConnect={onConnect}
                    onEdgesDelete={onEdgesDelete}
                    nodeTypes={nodeTypes}
                    fitView
                  >
                    <Background />
                    <Controls />
                  </ReactFlow>
                </div>
              ) : null}
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center flex-col text-neutral-400">
              <span className="material-symbols-outlined text-[32px] mb-2 font-light">account_tree</span>
              <p className="text-xs font-medium">Select or create a workflow</p>
            </div>
          )}
        </div>
      </div>

      {/* Node Edit Modal */}
      {editingNodeId && (
        <div className="absolute inset-0 bg-neutral-900/40 backdrop-blur-sm z-[100] flex items-center justify-center p-6 animate-fade-in">
          <div className="bg-white rounded-2xl w-full max-w-sm shadow-2xl border border-neutral-200 overflow-hidden flex flex-col text-left">
            <div className="px-5 py-4 border-b border-neutral-100 flex items-center justify-between bg-neutral-50/50">
              <h3 className="text-sm font-bold text-neutral-900">
                {activeWorkflow?.steps.find(s => s.id.toString() === editingNodeId) ? 'Edit Node' : 'New Node'}
              </h3>
              <button 
                onClick={() => setEditingNodeId(null)}
                className="text-neutral-400 hover:text-neutral-800 transition-colors"
              >
                <span className="material-symbols-outlined text-[18px]">close</span>
              </button>
            </div>
            
            <div className="p-5 space-y-4 text-xs">
              <div className="space-y-1.5">
                <label className="font-bold text-neutral-700">Node Name</label>
                <input 
                  type="text" 
                  value={nodeForm.name || ''}
                  onChange={e => setNodeForm({...nodeForm, name: e.target.value})}
                  className="w-full border border-neutral-200 rounded-lg px-3 py-2 text-xs focus:outline-none focus:border-neutral-400 focus:ring-2 focus:ring-neutral-200/50 transition-all font-medium"
                  placeholder="e.g. Asset Gathering"
                />
              </div>

              <div className="space-y-1.5">
                <label className="font-bold text-neutral-700">Assigned Agent</label>
                <select 
                  value={nodeForm.agent || 'Orchestrator'}
                  onChange={e => setNodeForm({...nodeForm, agent: e.target.value})}
                  className="w-full border border-neutral-200 rounded-lg px-3 py-2 text-xs bg-white focus:outline-none focus:border-neutral-400 transition-all font-medium"
                >
                  <option value="Orchestrator">Orchestrator</option>
                  <option value="Builder">Builder</option>
                  <option value="Evaluator">Evaluator</option>
                </select>
              </div>

              <div className="space-y-1.5">
                <label className="font-bold text-neutral-700">AI Tool (Optional)</label>
                <select 
                  value={nodeForm.aiTool || ''}
                  onChange={e => setNodeForm({...nodeForm, aiTool: e.target.value})}
                  className="w-full border border-neutral-200 rounded-lg px-3 py-2 text-xs bg-white focus:outline-none focus:border-neutral-400 transition-all font-medium text-neutral-600"
                >
                  <option value="">None</option>
                  <option value="Claude Code CLI">Claude Code CLI</option>
                  <option value="Antigravity CLI">Antigravity CLI</option>
                  <option value="Cursor">Cursor</option>
                  <option value="Code X">Code X</option>
                </select>
              </div>

              <div className="space-y-1.5">
                <label className="font-bold text-neutral-700">Description / Instructions</label>
                <textarea 
                  value={nodeForm.description || ''}
                  onChange={e => setNodeForm({...nodeForm, description: e.target.value})}
                  className="w-full border border-neutral-200 rounded-lg px-3 py-2 text-xs focus:outline-none focus:border-neutral-400 focus:ring-2 focus:ring-neutral-200/50 transition-all min-h-[80px] resize-none"
                  placeholder="Task instructions..."
                />
              </div>

              <div className="space-y-3 pt-2 border-t border-neutral-100/70">
                <div>
                  <label className="font-bold text-neutral-700 text-[11px] block mb-1">Source Flows (Incoming Upstream Nodes)</label>
                  <div className="max-h-[110px] overflow-y-auto border border-neutral-200 rounded-lg p-2 bg-neutral-50/50 space-y-1.5">
                    {(activeWorkflow?.steps || [])
                      .filter(s => s.id.toString() !== editingNodeId)
                      .map(s => {
                        const isIncoming = ((nodeForm as any).fromSteps || []).includes(s.id.toString());
                        return (
                          <label key={s.id} className="flex items-center gap-2 cursor-pointer hover:text-neutral-900 leading-none select-none py-0.5">
                            <input 
                              type="checkbox"
                              checked={isIncoming}
                              onChange={(e) => {
                                const checked = e.target.checked;
                                setNodeForm(prev => {
                                  const currentFrom = (prev as any).fromSteps || [];
                                  const updatedFrom = checked 
                                    ? [...currentFrom, s.id.toString()]
                                    : currentFrom.filter((id: string) => id !== s.id.toString());
                                  return { ...prev, fromSteps: updatedFrom };
                                });
                              }}
                              className="rounded border-neutral-300 text-neutral-800 focus:ring-neutral-400 w-3.5 h-3.5"
                            />
                            <span className="text-[11px] truncate font-medium text-neutral-700">
                              {s.name} <span className="text-[9px] text-neutral-400 font-normal">({s.agent})</span>
                            </span>
                          </label>
                        );
                      })}
                    {(activeWorkflow?.steps || []).filter(s => s.id.toString() !== editingNodeId).length === 0 && (
                      <p className="text-[10px] text-neutral-400 italic font-medium p-1">No other steps in this workflow yet.</p>
                    )}
                  </div>
                </div>

                <div>
                  <label className="font-bold text-neutral-700 text-[11px] block mb-1">Next Flows (Connected Downstream Nodes)</label>
                  <div className="max-h-[110px] overflow-y-auto border border-neutral-200 rounded-lg p-2 bg-neutral-50/50 space-y-1.5">
                    {activeWorkflow?.steps
                      .filter(s => s.id.toString() !== editingNodeId)
                      .map(s => {
                        const isConnected = (nodeForm.nextSteps || []).includes(s.id.toString());
                        return (
                          <label key={s.id} className="flex items-center gap-2 cursor-pointer hover:text-neutral-900 leading-none select-none py-0.5">
                            <input 
                              type="checkbox"
                              checked={isConnected}
                              onChange={(e) => {
                                const checked = e.target.checked;
                                setNodeForm(prev => {
                                  const currentNext = prev.nextSteps || [];
                                  const updatedNext = checked 
                                    ? [...currentNext, s.id.toString()]
                                    : currentNext.filter(id => id !== s.id.toString());
                                  return { ...prev, nextSteps: updatedNext };
                                });
                              }}
                              className="rounded border-neutral-300 text-neutral-800 focus:ring-neutral-400 w-3.5 h-3.5"
                            />
                            <span className="text-[11px] truncate font-medium text-neutral-700">
                              {s.name} <span className="text-[9px] text-neutral-400 font-normal">({s.agent})</span>
                            </span>
                          </label>
                        );
                      })}
                    {(activeWorkflow?.steps || []).filter(s => s.id.toString() !== editingNodeId).length === 0 && (
                      <p className="text-[10px] text-neutral-400 italic font-medium p-1">No other steps in this workflow yet.</p>
                    )}
                  </div>
                </div>
                
                <p className="text-[10px] text-neutral-400">
                  Tip: Toggle checks above or drag lines directly on the workflow canvas.
                </p>
              </div>
            </div>

            <div className="p-4 border-t border-neutral-100 bg-neutral-50/50 flex justify-end gap-3">
              <button 
                onClick={() => setEditingNodeId(null)}
                className="px-4 py-2 rounded-lg text-xs font-bold text-neutral-600 hover:bg-neutral-200/50 transition-colors"
              >
                Cancel
              </button>
              <button 
                onClick={saveNode}
                className="px-4 py-2 rounded-lg bg-neutral-900 hover:bg-neutral-800 text-white text-xs font-bold transition-all shadow-sm"
              >
                Save Node
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Create Workflow Modal */}
      {isCreatingWorkflow && (
        <div className="absolute inset-0 bg-neutral-900/40 backdrop-blur-sm z-[100] flex items-center justify-center p-6 animate-fade-in">
          <div className="bg-white rounded-2xl w-full max-w-sm shadow-2xl border border-neutral-200 overflow-hidden flex flex-col text-left">
            <div className="px-5 py-4 border-b border-neutral-100 flex items-center justify-between bg-neutral-50/50">
              <h3 className="text-sm font-bold text-neutral-900">
                Create New Workflow Flow
              </h3>
              <button 
                type="button"
                onClick={() => setIsCreatingWorkflow(false)}
                className="text-neutral-400 hover:text-neutral-800 transition-colors"
              >
                <span className="material-symbols-outlined text-[18px]">close</span>
              </button>
            </div>
            
            <div className="p-5 space-y-4 text-xs">
              <div className="space-y-1.5">
                <label className="font-bold text-neutral-700">Flow Name</label>
                <input 
                  type="text" 
                  value={newWorkflowName}
                  onChange={e => setNewWorkflowName(e.target.value)}
                  className="w-full border border-neutral-200 rounded-lg px-3 py-2 text-xs focus:outline-none focus:border-neutral-400 focus:ring-2 focus:ring-neutral-200/50 transition-all font-medium"
                  placeholder="e.g. Design & Prototype SOP"
                  autoFocus
                />
              </div>

              <div className="space-y-1.5">
                <label className="font-bold text-neutral-700">Description</label>
                <textarea 
                  value={newWorkflowDesc}
                  onChange={e => setNewWorkflowDesc(e.target.value)}
                  className="w-full border border-neutral-200 rounded-lg px-3 py-2 text-xs focus:outline-none focus:border-neutral-400 focus:ring-2 focus:ring-neutral-200/50 transition-all min-h-[80px] resize-none"
                  placeholder="Briefly state the goal of this pipeline..."
                />
              </div>

              <div className="space-y-1.5">
                <label className="font-bold text-neutral-700 block">Flow Icon Representation</label>
                <div className="grid grid-cols-4 gap-1.5">
                  {[
                    { key: 'account_tree', name: 'Tree' },
                    { key: 'code', name: 'Code' },
                    { key: 'sync', name: 'Sync' },
                    { key: 'movie', name: 'Video' },
                    { key: 'deployed_code', name: 'Deploy' },
                    { key: 'terminal', name: 'Console' },
                    { key: 'api', name: 'API' },
                    { key: 'schema', name: 'SOP Mapping' }
                  ].map(iconOpt => (
                    <button
                      key={iconOpt.key}
                      type="button"
                      onClick={() => setNewWorkflowIcon(iconOpt.key)}
                      className={`p-2 border rounded-xl flex flex-col items-center gap-1 justify-center transition-all cursor-pointer ${
                        newWorkflowIcon === iconOpt.key
                          ? 'border-neutral-800 bg-neutral-900 text-white'
                          : 'border-neutral-200 hover:border-neutral-350 text-neutral-600 bg-neutral-50/50'
                      }`}
                    >
                      <span className="material-symbols-outlined text-[16px]">{iconOpt.key}</span>
                      <span className="text-[8px] font-bold leading-tight truncate w-full text-center">{iconOpt.name}</span>
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <div className="p-4 border-t border-neutral-100 bg-neutral-50/50 flex justify-end gap-3">
              <button 
                type="button"
                onClick={() => setIsCreatingWorkflow(false)}
                className="px-4 py-2 rounded-lg text-xs font-bold text-neutral-600 hover:bg-neutral-200/50 transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button 
                type="button"
                onClick={saveNewWorkflow}
                disabled={!newWorkflowName.trim()}
                className="px-4 py-2 rounded-lg bg-neutral-900 hover:bg-neutral-800 text-white text-xs font-bold transition-all shadow-sm disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
              >
                Save Flow
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );

  if (isModalStyle) {
    return contentElement;
  }

  return (
    <div className="fixed inset-0 bg-neutral-900/10 backdrop-blur-xs z-50 flex items-center justify-center p-6 md:p-12 transition-all">
      <main 
        className="w-full max-w-[1240px] h-full bg-white rounded-2xl border border-outline-variant flex overflow-hidden shadow-2xl animate-fade-in"
      >
        {contentElement}
      </main>
    </div>
  );
};

