import type { MainView } from '../../types';

/** Shared nav metadata — change icons/labels here for both platforms. */
export const NAV_CONFIG = {
  chat: {
    icon: 'chat',
    labelKey: 'New Chat',
    shortLabelKey: 'Chat',
    testId: 'nav-new-chat',
    view: 'chat' as MainView,
  },
  agents: {
    icon: 'smart_toy',
    labelKey: 'AI Agents',
    shortLabelKey: 'Agent',
    testId: 'nav-agents',
    view: 'agents' as MainView,
  },
  workflows: {
    icon: 'fork_right',
    labelKey: 'Workflows SOP',
    shortLabelKey: 'Flow',
    testId: 'nav-workflows',
    view: 'workflows' as MainView,
  },
  addWorkspace: {
    icon: 'create_new_folder',
    labelKey: 'Add project folder',
    shortLabelKey: 'Project',
    testId: 'nav-add-workspace',
  },
  settings: {
    icon: 'settings',
    labelKey: 'Settings',
    shortLabelKey: 'Set',
    testId: 'nav-settings',
    view: 'settings' as MainView,
  },
} as const;

export type NavConfigKey = keyof typeof NAV_CONFIG;
