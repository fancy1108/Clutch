import type { ChatMessage as SharedChatMessage } from '@clutch/shared-types';

export type {
  AgentRole,
  ClutchRunStatus,
  ClutchState,
  DiffLine,
  DispatchEdge,
  DispatchLaneSession,
  DispatchLogEntry,
  DispatchPreviewPayload,
  HybridExecutionData,
  HybridExecutionPayload,
  OutputEvent,
  OutputEventType,
  PendingHandoffDraft,
  PendingPtyInject,
  PlanCard,
  PlanCardStatus,
  PtyLane,
  PtyOutputData,
  PtySessionStatusData,
  QuestionCard,
  QuestionCardStatus,
  QuestionOption,
  RunStatus,
  StatePatchData,
  TodoItem,
  TodoItemStatus,
  ToolStep,
  ToolStepKind,
  ToolStepStatus,
  UncommittedFile,
  VerificationConclusion,
  VerificationReport,
  VerificationStep,
  VerificationStepStatus,
  DiffFileEntry,
  DiffFileStatus,
  DiffSummary,
  SubtaskCard,
  SubtaskCardStatus,
  SubtaskCardStep,
  SubtaskCardType,
  WebSocketEnvelope,
  WebSocketEvent,
  WorkflowDef,
  WorkflowNodeType,
  WorkflowStep,
  EdgeWhen,
} from '@clutch/shared-types';

export interface Deliverable {
  name: string;
  content: string;
}

export type AgentType = string;

export interface Agent {
  id: string;
  name: string;
  description: string;
  markdownDoc: string;
  lastModified: string;
  avatar: string;
  deliverables: Deliverable[];
  mcpTools?: string[];
  mcpServerIds?: string[];
  agentType?: AgentType;
  modelId?: string;
  ollamaModel?: string;
  /** @deprecated use agentType */
  aiEngine?: string;
  skills?: string[];
  builtin?: boolean;
}

export interface RepositoryItem {
  name: string;
  time: string;
  isActive?: boolean;
}

export interface RepositoryFolder {
  name: string;
  items: RepositoryItem[];
  collapsed: boolean;
}

/** Chat message with optional user-authored flag for UI. */
export interface ChatMessage extends Omit<SharedChatMessage, 'agent'> {
  agent: SharedChatMessage['agent'] | 'User';
  isUser?: boolean;
}

export type MainView =
  | 'chat'
  | 'workflows'
  | 'settings'
  | 'agents'
  | 'tools'
  | 'skills'
  | 'mcp'
  | 'models'
  | 'appearance';

/** Workspace surface mode — Header Coding | Design toggle (D36). */
export type AppWorkspaceMode = 'coding' | 'design';

export type RightTab = 'overview' | 'files' | 'flow' | 'changes' | 'terminal';
