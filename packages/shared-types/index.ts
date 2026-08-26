/** Shared contracts between desktop UI and Python orchestrator sidecar. */

export type RunStatus = 'failed' | 'running' | 'passed';

/** Sidecar run status including human-gate pause and pre-run idle. */
export type ClutchRunStatus = RunStatus | 'awaiting_human' | 'refining' | 'idle';

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

/** Structured Chat/MCP tool step (D46 — Grok/Cursor-style verb_group transcript). */
export type ToolStepKind =
  | 'read'
  | 'fetch'
  | 'search'
  | 'list'
  | 'edit'
  | 'execute'
  | 'other';

export type ToolStepStatus = 'running' | 'completed' | 'failed' | 'awaiting';

export interface ToolStep {
  id: string;
  kind: ToolStepKind;
  /** Short tool name, e.g. read_file */
  tool: string;
  status: ToolStepStatus;
  /** One-liner, e.g. "Read README.md" / "Fetched shanghai.disney.com" */
  title: string;
  /**
   * Expand body: primary target (URL/path/query) plus optional result preview
   * (Cursor/Grok: collapse for density, expand for supervise).
   */
  detail?: string;
  /** D6 Cursor-style: per-edit file hunk attached when an edit tool completes. */
  fileDiff?: DiffFileEntry;
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
  /** Persisted MCP/builtin tool trail for this assistant turn (D46). */
  toolSteps?: ToolStep[];
  /** Workspace-relative paths written this turn (D47) — clickable chips → D42 preview. */
  filesChanged?: string[];
  /** D2/D49 plan card sealed onto the assistant turn (Approve / revise / Cancel). */
  planCard?: PlanCard;
  /** D3/D49 todo checklist for this turn (also mirrored on ClutchState.agent_todos). */
  todoList?: TodoItem[];
  /** D4/D49 multiple-choice question card. */
  questionCard?: QuestionCard;
  /** D5/D50 self-check verification report. */
  verificationReport?: VerificationReport;
  /** D6/D50 diff review card (file list + readable hunks). */
  diffSummary?: DiffSummary;
  /** D10/D48 nested subtask cards from delegate_subtask. */
  subtaskCards?: SubtaskCard[];
  /** D11 — finished background job card sealed onto the Supervisor monitor turn. */
  bgJob?: BackgroundJob;
  codeHighlight?: {
    file: string;
    lineCount: number;
  };
}

export type SubtaskCardStatus = 'running' | 'done' | 'failed';
export type SubtaskCardType = 'explore' | 'implement';

export interface SubtaskCardStep {
  name: string;
  status: string;
}

export interface SubtaskCard {
  id: string;
  type: SubtaskCardType;
  title: string;
  summary?: string;
  status: SubtaskCardStatus;
  toolSteps?: SubtaskCardStep[];
  error?: string;
}

export type BackgroundJobStatus = 'running' | 'done' | 'failed' | 'killed';

/** D11 — background shell job tracked per Chat run. */
export interface BackgroundJob {
  id: string;
  command: string;
  title: string;
  status: BackgroundJobStatus;
  output?: string;
  exit_code?: number | null;
}

export type PlanCardStatus = 'pending' | 'approved' | 'cancelled' | 'revised';

export interface PlanCard {
  title: string;
  steps: string[];
  summary?: string;
  status: PlanCardStatus;
  note?: string;
  /** D31 — per-step reviewer comments (parallel to steps). */
  stepComments?: string[];
}

export type TodoItemStatus = 'pending' | 'in_progress' | 'completed';

export interface TodoItem {
  id: string;
  content: string;
  status: TodoItemStatus;
}

/** D29 — session goal tracked via goal_write. */
export interface AgentGoal {
  title: string;
  progress: number;
  done: boolean;
}

export type QuestionCardStatus = 'pending' | 'answered' | 'cancelled';

export interface QuestionOption {
  id: string;
  label: string;
}

export interface QuestionCard {
  question: string;
  options: QuestionOption[];
  status: QuestionCardStatus;
  allowCustom?: boolean;
  selectedId?: string;
  selectedLabel?: string;
  note?: string;
  kind?: 'question' | 'notify';
}

export type VerificationConclusion = 'passed' | 'failed';
export type VerificationStepStatus = 'passed' | 'failed' | 'skipped';

export interface VerificationStep {
  id: string;
  name: string;
  status: VerificationStepStatus;
  detail?: string;
}

export interface VerificationReport {
  title: string;
  conclusion: VerificationConclusion;
  steps: VerificationStep[];
  summary?: string;
  nextActions?: string[];
  changedFiles?: string[];
}

export type DiffFileStatus = 'A' | 'M' | 'D';

export interface DiffFileEntry {
  path: string;
  status: DiffFileStatus;
  summary?: string;
  /** Unified diff text (optional when `diffs` is present). */
  patch?: string;
  diffs?: DiffLine[];
}

export interface DiffSummary {
  title: string;
  summary?: string;
  files: DiffFileEntry[];
  /** True when streamed mid-turn as a per-edit Cursor-style card. */
  inline?: boolean;
}

/** Supported node types in the visual canvas editor. */
export type WorkflowNodeType = 'agent_task' | 'human_gate' | 'check';

/** Conditional routing value on edges (set by check/human_gate nodes). */
export type EdgeWhen = 'approve' | 'reject' | 'retry' | 'passed' | 'failed';

export interface WorkflowStep {
  id: string;
  name: string;
  /** Node type — defaults to 'agent_task' for backward compatibility. */
  nodeType?: WorkflowNodeType;
  /** Agent instance id (required for agent_task, ignored for gate/check). */
  agent: string;
  aiTool?: string;
  avatar?: string;
  description: string;
  nextSteps: string[];
  /** Per-outgoing-edge conditional values (multi-select), keyed by target step id. */
  edgeWhen?: Record<string, EdgeWhen[]>;
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

export type PtyLaneStatus = 'booting' | 'running' | 'completed' | 'queued';

export interface PtyLane {
  lane_id: string;
  agent_type: string;
  label: string;
  status: PtyLaneStatus;
  focused: boolean;
  collapsed: boolean;
  run_id: string;
  /** User-configured agent instance (e.g. Opencode vs Opencode2 sharing opencode-cli). */
  configured_agent_id?: string;
  configured_agent_name?: string;
  /** CLI conversation session id (Clutch-assigned; used for --resume in native terminal). */
  cli_session_id?: string;
}

export interface DispatchLogEntry {
  id: string;
  time: string;
  sources_label: string;
  target: string;
  prompt: string;
  handoff_file: string;
  handoff_path: string;
  input_mode?: 'natural' | 'graph';
  dispatch_mode?: 'switch' | 'handoff';
  file_refs?: string[];
  /** Snapshot of lane CLI session ids involved in this dispatch. */
  lane_sessions?: DispatchLaneSession[];
}

export interface DispatchLaneSession {
  lane_id: string;
  label: string;
  agent_type: string;
  cli_session_id: string;
  /** Workspace directory where the PTY session ran (required for native --resume). */
  workspace_path?: string;
}

export interface DispatchEdge {
  sources: string[];
  target: string;
  handoff_file: string;
  source_lane_ids: string[];
  target_lane_id: string;
}

export interface PendingPtyInject {
  lane_id: string;
  prompt: string;
  handoff_path?: string;
}

export interface PendingHandoffDraft {
  id: string;
  label: string;
  text: string;
  suggested_target?: string;
  handoff_path?: string;
}

export interface DispatchPreviewPayload {
  sources: string[];
  target: string;
  task: string;
  handoff_path: string;
  handoff_file: string;
  file_refs: string[];
  input_mode: 'natural' | 'graph';
  dispatch_mode?: 'switch' | 'handoff';
  chips: Array<{
    id: string;
    label: string;
    on: boolean;
    source_name: string;
  }>;
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
  | 'run_completed'
  | 'pty_output'
  | 'pty_session_status';

/** WebSocket `pty_output` payload — raw PTY bytes for embedded terminal mode. */
export interface PtyOutputData {
  run_id: string;
  lane_id?: string;
  node_id?: string;
  source?: string;
  level?: string;
  message?: string;
  timestamp?: string;
  chunk: string;
  encoding?: 'utf8';
}

/** WebSocket `pty_session_status` payload. */
export interface PtySessionStatusData {
  run_id: string;
  lane_id?: string;
  node_id?: string;
  source?: string;
  level?: string;
  message?: string;
  timestamp?: string;
  status: 'booting' | 'ready' | 'detached' | 'exited' | 'blocked' | string;
}

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
  /** In-flight tool steps for the current Chat turn (D46); sealed onto the assistant message when idle. */
  pending_tool_steps?: ToolStep[];
  /** Live session todos for multi-step work (D3); updates via todo_write. */
  agent_todos?: TodoItem[];
  /** D29 — current session goal; updates via goal_write. */
  agent_goal?: AgentGoal;
  /** D5/D50 latest verification report (also sealed on ChatMessage.verificationReport). */
  verification_report?: VerificationReport;
  /** D6/D50 latest diff summary (also sealed on ChatMessage.diffSummary). */
  diff_summary?: DiffSummary;
  session_tokens?: number;
  session_cost_usd?: number;
  token_input?: number;
    token_output?: number;
    /** Q-USAGE-1: true when meters used word-count (or mixed) instead of provider usage. */
    usage_estimated?: boolean;
    /** D9: Chat-visible step/token counters (live while running). */
  run_stats?: {
    tool_steps?: number;
    max_steps?: number;
    session_tokens?: number;
    fuse_triggered?: boolean;
    consecutive_failures?: number;
  };
  /** D9: show Continue after Stop / loop fuse / max-steps. */
  awaiting_continue?: boolean;
  /** D19: model reasoning stream for the in-flight Chat turn. */
  live_reasoning?: string;
  /** D10/D48: live nested subtask cards while parent turn runs. */
  pending_subtasks?: SubtaskCard[];
  /** D11: background shell jobs for this Chat session. */
  bg_jobs?: BackgroundJob[];
    /** D34: active foreground shell command (transfer to bg_jobs). */
    foreground_shell?: {
        command: string;
        title: string;
        cwd?: string;
    } | null;
    /** D32: optional git worktree isolation for Agent edits. */
    worktree_isolation?: {
        id: string;
        path: string;
        branch: string;
        enabled: boolean;
        dirty?: boolean;
        workspace_root?: string;
    } | null;
    /** D24: pending code diagnostics for Chat issues strip. */
    chat_diagnostics?: Array<{
        tool: string;
        path: string;
        line: string;
        message: string;
    }>;
  /** CLI provider session id (`claude --resume` / `agy --conversation`). */
  cli_session_id?: string;
  /** Agent id that owns `cli_session_id` (reset when user switches agent). */
  cli_session_agent_id?: string;
  /** Hybrid shell execution details keyed by chat message id. */
  hybrid_executions?: Record<string, HybridExecutionPayload>;
  /** Long-lived bash PTY status for hybrid runtime (ready / recovering). */
  shell_session_status?: string;
  /** run_ids holding busy Hybrid shells while this run waits in the global pool queue. */
  shell_pool_blocker_run_ids?: string[];
  /** Blocker session metadata for pool queue UI. */
  shell_pool_blockers?: Array<{ run_id: string; title?: string; agent_name?: string }>;
  /** 1-based position in the global pool FIFO for this run (0 when not queued). */
  shell_pool_queue_position?: number;
  /** Total turns waiting in the global pool queue. */
  shell_pool_queue_depth?: number;
  /** Workflow node under human refine after pause. */
  refining_node_id?: string;
  /** Latest agent draft while refining (committed before auto-continue). */
  refine_draft_output?: string;
  refine_agent_id?: string;
  /** D34 terminal orchestra — parallel PTY lanes. */
  pty_lanes?: PtyLane[];
  dispatch_log?: DispatchLogEntry[];
  dispatch_edges?: DispatchEdge[];
  pending_handoff_drafts?: PendingHandoffDraft[];
  pending_pty_inject?: PendingPtyInject | null;
  focused_lane_id?: string | null;
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
