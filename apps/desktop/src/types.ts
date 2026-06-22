import type { ChatMessage as SharedChatMessage } from '@clutch/shared-types';

export type {
  AgentRole,
  ClutchRunStatus,
  ClutchState,
  DiffLine,
  RunStatus,
  StatePatchData,
  UncommittedFile,
  WebSocketEnvelope,
  WebSocketEvent,
  WorkflowDef,
  WorkflowStep,
} from '@clutch/shared-types';

export interface Deliverable {
  name: string;
  content: string;
}

export interface Agent {
  id: string;
  name: string;
  description: string;
  markdownDoc: string;
  lastModified: string;
  avatar: string;
  deliverables: Deliverable[];
  mcpTools?: string[];
  aiEngine?: string;
  skills?: string[];
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

/** UI prototype extends shared contract with user-authored messages. */
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

export type RightTab = 'overview' | 'files' | 'flow' | 'changes' | 'terminal';
