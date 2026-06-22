export type {
  AgentRole,
  ChatMessage,
  DiffLine,
  RunStatus,
  UncommittedFile,
  WebSocketEnvelope,
  WebSocketEvent,
  WorkflowDef,
  WorkflowStep,
} from '@clutch/shared-types';

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

export type MainView = 'chat' | 'workflows' | 'settings' | 'agents' | 'tools' | 'skills' | 'mcp';
export type RightTab = 'overview' | 'files' | 'flow' | 'changes' | 'terminal';
