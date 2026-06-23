/** Shared contracts between desktop UI and Python orchestrator sidecar. */

export type RunStatus = 'failed' | 'running' | 'passed';

/** Sidecar run status including human-gate pause and pre-run idle. */
export type ClutchRunStatus = RunStatus | 'awaiting_human' | 'idle';

export type AgentRole = 'Orchestrator' | 'Builder' | 'Evaluator' | 'Supervisor';

export interface ChatMessage {
  id: string;
  agent: AgentRole;
  avatar: string;
  time: string;
  status?: 'COMPLETED' | 'FAILED' | 'RUNNING';
  text: string;
  executionTime?: string;
  tokens?: string;
  badgeText?: string;
  codeHighlight?: {
    file: string;
    lineCount: number;
  };
}

export interface WorkflowStep {
  id: string;
  name: string;
  agent: string;
  aiTool?: string;
  avatar?: string;
  description: string;
  nextSteps: string[];
  position?: { x: number; y: number };
}

export interface WorkflowDef {
  id: string;
  name: string;
  lastDeployed: string;
  isActive: boolean;
  icon: string;
  steps: WorkflowStep[];
  description?: string;
}

export interface DiffLine {
  lineNum: number;
  type: 'addition' | 'deletion' | 'normal';
  text: string;
}

export interface UncommittedFile {
  name: string;
  status: 'M' | 'A' | 'D';
  diffs: DiffLine[];
  active?: boolean;
}

/** WebSocket envelope: {"event": "...", "data": {...}} */
export interface WebSocketEnvelope<T = unknown> {
  event: string;
  data: T;
}

export type WebSocketEvent =
  | 'state_patch'
  | 'message'
  | 'log'
  | 'file_changed'
  | 'validation_result'
  | 'human_required'
  | 'run_completed';

/** LangGraph SSOT projected to the React UI. */
export interface ClutchState {
  run_id: string;
  workflow_id: string;
  current_instruction: string;
  active_node_id: string;
  active_agent: string;
  status: ClutchRunStatus;
  messages: ChatMessage[];
  terminal_logs: string[];
  changed_files: string[];
  session_tokens?: number;
  session_cost_usd?: number;
  token_input?: number;
  token_output?: number;
}

/** WebSocket `state_patch` payload (partial update). */
export interface StatePatchData {
  run_id: string;
  timestamp: string;
  patch: Partial<ClutchState>;
}
