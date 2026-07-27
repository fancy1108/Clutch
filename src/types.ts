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

export interface ThoughtStep {
  id?: string;
  type: 'search' | 'file' | 'folder' | 'thought' | 'command';
  action: string; // e.g. 'Searched', 'Analyzed', 'Thought for'
  target: string; // e.g. 'clutch-tools', 'AiToolsManager.tsx'
  details?: string; // e.g. '2 results', '#L1-150', '1s'
}

export interface ChatMessage {
  id: string;
  agent: string;
  avatar: string;
  time: string;
  status?: 'COMPLETED' | 'FAILED' | 'RUNNING';
  text: string;
  workedTime?: string;
  summarySteps?: {
    filesCount?: number;
    foldersCount?: number;
    searchesCount?: number;
  };
  steps?: ThoughtStep[];
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

export type RunStatus = 'failed' | 'running' | 'passed';
export type MainView = 'chat' | 'workflows' | 'settings' | 'agents' | 'tools';
export type RightTab = 'overview' | 'files' | 'flow' | 'changes' | 'terminal';

export interface ClientEnvironmentContext {
  currentTime: string;
  formattedDateTime: string;
  timeZone: string;
  devicePlatform: string;
  userLocale: string;
}

