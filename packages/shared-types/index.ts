/** Shared contracts between desktop UI and Python orchestrator sidecar. */

export type RunStatus = 'failed' | 'running' | 'passed';

/** Sidecar run status including human-gate pause and pre-run idle. */
export type ClutchRunStatus = RunStatus | 'awaiting_human' | 'idle';

export type AgentRole = 'Orchestrator' | 'Builder' | 'Evaluator' | 'Supervisor';

export type OutputEventType =
  | 'assistant'
  | 'tool'
  | 'shell_echo'
  | 'system_prompt'
  | 'boundary_marker'
  | 'ansi'
  | 'debug'
  | 'stderr';

export interface OutputEvent {
  type: OutputEventType;
  visible: boolean;
  content: string;
}

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
  /** Actual execution backend for this reply (e.g. Claude CLI, DeepSeek V4 Pro). */
  runtimeEngine?: string;
  /** Full hybrid shell PTY capture for debug/export. */
  rawOutput?: string;
  /** Structured hybrid execution segments (shell echo, system prompt, marker, etc.). */
  outputEvents?: OutputEvent[];
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

/** Structured hybrid execution payload keyed by chat message id. */
export interface HybridExecutionPayload {
  rawOutput?: string;
  outputEvents?: OutputEvent[];
}

/** WebSocket `hybrid_execution` payload — attaches debug fields to a chat message. */
export interface HybridExecutionData {
  run_id: string;
  messageId: string;
  rawOutput?: string;
  outputEvents?: OutputEvent[];
}

/** WebSocket envelope: {"event": "...", "data": {...}} */
export interface WebSocketEnvelope<T = unknown> {
  event: string;
  data: T;
}

export type WebSocketEvent =
  | 'state_patch'
  | 'message'
  | 'hybrid_execution'
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
  /** CLI provider session id (`claude --resume` / `agy --conversation`). */
  cli_session_id?: string;
  /** Agent id that owns `cli_session_id` (reset when user switches agent). */
  cli_session_agent_id?: string;
  /** Hybrid shell execution details keyed by chat message id. */
  hybrid_executions?: Record<string, HybridExecutionPayload>;
  /** Long-lived bash PTY status for hybrid runtime (ready / recovering). */
  shell_session_status?: string;
  /** @deprecated use cli_session_id — still read from older persisted runs */
  claude_session_id?: string;
  /** @deprecated use cli_session_agent_id */
  claude_session_agent_id?: string;
}

/** WebSocket `state_patch` payload (partial update). */
export interface StatePatchData {
  run_id: string;
  timestamp: string;
  patch: Partial<ClutchState>;
}
