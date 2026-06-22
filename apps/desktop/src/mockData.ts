import { ChatMessage, RepositoryFolder, UncommittedFile, WorkflowStep } from './types';

export const initialFolders: RepositoryFolder[] = [
  {
    name: 'obsidian',
    collapsed: false,
    items: [
      { name: 'Clutch workspace...', time: '6h', isActive: true },
      { name: 'Missing bug fix in AI a...', time: '2d' }
    ]
  },
  {
    name: 'info2video',
    collapsed: false,
    items: [
      { name: "Today's video delete ...", time: '19h' },
      { name: 'GitHub branch creati...', time: '19h' }
    ]
  },
  {
    name: 'Home',
    collapsed: true,
    items: [] // No agents yet
  },
  {
    name: 'my-video',
    collapsed: false,
    items: [
      { name: 'Video Intro Script', time: '8h' },
      { name: 'Precision Voice Tuning', time: '9h' }
    ]
  }
];

export const initialChatMessages: ChatMessage[] = [
  {
    id: 'msg-1',
    agent: 'Orchestrator',
    avatar: 'https://lh3.googleusercontent.com/aida-public/AB6AXuA0yGh59QNLj5n0igNxMgu4lgaiNqZpcN29SpWM0JHNlAuFmOBx-Id67Zcd2NDCNBjBKrcffQrdrfoe-3XaSlveekLAP9SRis93uTk7XPPFO5y4Swos7NvATw6n7eZEm7nfAQuTiMAoWRSnxefAOJugUbZx3fCTNv4jGyjvT-UZznwKzp_HoXuStup_0juhBCZYamrV0Coil-k27d9Yi7il6NabIEG0FfbxwL5V5azpfZQOlBfpaganta2kP7n59BKPHd4K2uTOfZ5p',
    time: '10:45 AM',
    text: 'Beginning task: Video Production Pipeline. Assigning initial asset gathering to Builder module.',
    executionTime: '0.4s execution',
    tokens: '840 tokens'
  },
  {
    id: 'msg-2',
    agent: 'Builder',
    avatar: 'https://lh3.googleusercontent.com/aida-public/AB6AXuBpRidttSGTIY-J-PGvnlcZX_oZSZoBXJY5vjZ9g1PKl_fq4EKoa2RXbcSCvvIdbPLdmfuzPKTxnR8TqV7skwsKlt-eKEzSzktv-TWbHu4c9uBEdP6Es_Fjek1EBQuGZeMtWsUi3fn0lyozFaZBLp9SpES3r0WalbqYY6gGiT1R_0J1kvU-D9rI_2q2f3sMGHuTjWyOZ5gImCLGHSGejtcKmToTSZYMrXfT_A5x1iw_f4q7WljP3FXjk64aQhLgh9nTXUDfPdkIzu0b',
    time: '10:46 AM',
    text: 'Task completed. I have updated the core modules and prepared the build environment.',
    executionTime: '2.8s execution',
    tokens: '2,150 tokens',
    codeHighlight: {
      file: '/src/video-core',
      lineCount: 12
    }
  },
  {
    id: 'msg-3',
    agent: 'Evaluator',
    avatar: 'https://lh3.googleusercontent.com/aida-public/AB6AXuCmb7VGaQXE-4sYnIZR3VrcHVAPhv4Px14kMlkayJj8kVm8htTWITmPi26wsj8P6B9RrqykIWj81S2ilmGR0e8cXhA1gjc3U-Nw0DsgHV3HvVmBskuoUksIt6YM6Z3ORjFtRhBphqAXxRKf9ke-zYcPs0TcEFKxw_bwGXSDiAKV5CL7kZf9i6lSZDe91ccUNjaAIsgTMKEEvYc7bZpXYz3D5dClulRwbNru5SZB-1E5FM0A2qMPs-IAfiR8OB1-cUvFh3WYKx9qlGgN',
    time: '10:47 AM',
    status: 'FAILED',
    text: 'Validation failed due to missing documentation artifacts in the root directory: missing: verify.md',
    executionTime: '1.2s execution',
    tokens: '1,420 tokens',
    badgeText: 'CRITICAL FINDING: NEEDS_WORK'
  }
];

export const secondaryChatMessages: ChatMessage[] = [
  {
    id: 'msg-rec-1',
    agent: 'Evaluator',
    avatar: 'https://lh3.googleusercontent.com/aida-public/AB6AXuB9jPZCMFF4Qz3iRAPro4W7I4wiIKiBIDqw0oP7CCRgQAqYCn9pn2PkuB2EIuF4hYUuB--rYLdcGHwSiBw_D7dZu2VZuB0QRRqY-rpu4bXrRTHyFufhz6Lv24uNq7g4EI4y-FoyFEK0H6B3Iuswbmh7P4QGseFq8Fown4hZFW8FRKMIKsTLFSS6x-QAxrfLsMo5OkjGeq-ophaad4hjm2e3fIv_-lRwHpFeZEU6ajRy0swzD_dQ9Bot4JOKn63NfoPmfvBurUMZfogs',
    time: '10:40 AM',
    status: 'COMPLETED',
    text: 'Initial layout validation passed. All structural elements align with the wireframe specifications.',
    executionTime: '0.8s execution',
    tokens: '1,200 tokens'
  },
  {
    id: 'msg-rec-2',
    agent: 'Evaluator',
    avatar: 'https://lh3.googleusercontent.com/aida-public/AB6AXuB9jPZCMFF4Qz3iRAPro4W7I4wiIKiBIDqw0oP7CCRgQAqYCn9pn2PkuB2EIuF4hYUuB--rYLdcGHwSiBw_D7dZu2VZuB0QRRqY-rpu4bXrRTHyFufhz6Lv24uNq7g4EI4y-FoyFEK0H6B3Iuswbmh7P4QGseFq8Fown4hZFW8FRKMIKsTLFSS6x-QAxrfLsMo5OkjGeq-ophaad4hjm2e3fIv_-lRwHpFeZEU6ajRy0swzD_dQ9Bot4JOKn63NfoPmfvBurUMZfogs',
    time: '10:43 AM',
    status: 'COMPLETED',
    text: 'Color palette and typography audit successful. Contrast ratios meet WCAG AA standards.',
    executionTime: '1.1s execution',
    tokens: '1,500 tokens'
  },
  {
    id: 'msg-rec-3',
    agent: 'Evaluator',
    avatar: 'https://lh3.googleusercontent.com/aida-public/AB6AXuB9jPZCMFF4Qz3iRAPro4W7I4wiIKiBIDqw0oP7CCRgQAqYCn9pn2PkuB2EIuF4hYUuB--rYLdcGHwSiBw_D7dZu2VZuB0QRRqY-rpu4bXrRTHyFufhz6Lv24uNq7g4EI4y-FoyFEK0H6B3Iuswbmh7P4QGseFq8Fown4hZFW8FRKMIKsTLFSS6x-QAxrfLsMo5OkjGeq-ophaad4hjm2e3fIv_-lRwHpFeZEU6ajRy0swzD_dQ9Bot4JOKn63NfoPmfvBurUMZfogs',
    time: '10:47 AM',
    status: 'FAILED',
    text: 'CRITICAL FINDING: UI/UX Mismatch. The "Switch Agent" button does not align with the minimalist design spec.',
    executionTime: '1.4s execution',
    tokens: '1,800 tokens',
    badgeText: 'NEEDS WORK'
  }
];

export const uncommittedFiles: UncommittedFile[] = [
  {
    name: 'src/video-core/processor.ts',
    status: 'M',
    active: true,
    diffs: [
      { lineNum: 41, type: 'normal', text: 'function processVideo(assets: string[]) {' },
      { lineNum: 42, type: 'deletion', text: '  return validate(assets);' },
      { lineNum: 42, type: 'addition', text: '  const result = await validate(assets);' },
      { lineNum: 43, type: 'addition', text: "  return result.status === 'ok';" },
      { lineNum: 44, type: 'normal', text: '}' }
    ]
  },
  {
    name: 'src/video-core/utils.ts',
    status: 'M',
    diffs: [
      { lineNum: 10, type: 'normal', text: 'export function logExecutionStep(step: string) {' },
      { lineNum: 11, type: 'deletion', text: "  console.log('Beginning step: ' + step);" },
      { lineNum: 11, type: 'addition', text: "  console.info(`[ORCHESTRATION] [${new Date().toLocaleTimeString()}] -> ${step}`);" },
      { lineNum: 12, type: 'normal', text: '}' }
    ]
  },
  {
    name: 'docs/verify.md',
    status: 'A',
    diffs: [
      { lineNum: 1, type: 'addition', text: '# Verification Artifact' },
      { lineNum: 2, type: 'addition', text: 'This file contains the automated check logs for the Video Production Pipeline.' },
      { lineNum: 3, type: 'addition', text: '- Layout audit: PASS' },
      { lineNum: 4, type: 'addition', text: '- Accessibility contrast compliance: PASS' },
      { lineNum: 5, type: 'addition', text: '- Artifact checklist: ATTACHED' }
    ]
  }
];

export const workflowSteps: WorkflowStep[] = [
  { id: 'step-1', name: 'Find Problem & Direction', agent: 'Orchestrator', aiTool: 'Code X', avatar: 'https://lh3.googleusercontent.com/aida-public/AB6AXuCdbGLlsb3N3uOkfOjw1Q1_yDEdGIJRGnmhLu-FVragfIKdNByQw1J1dUhUyD0bhtU68_IQlwgYzvIetQ2bY0YH_lZtUPtQ34nuKBxaxPyS3e2_NiWBHxGCtDAanZ14d9Jj74bIX1CMvh__wE2web2l3_MmMZ3M6VbcAyIQ32DmLoC1ZxOulFXqko_7SDi7dj4UYhiz2GZJT9mIeqNcXO-z24SVjGrZaOr-FBsXxb6cUVkNht5QSQLvRy955U1VtJCFXs670Vt4hbki', description: 'Explores current repo status and parses user intent.', nextSteps: ['step-2'] },
  { id: 'step-2', name: 'Write Proposal', agent: 'Builder', aiTool: 'Claude Code CLI', avatar: 'https://lh3.googleusercontent.com/aida-public/AB6AXuDmaRLi3irRTkuzp5k7fHmK2YfMAmLw7p51bV98-DQqqF3sv--U5P_quS1s0WdKEebiVYvBSSjPAYuJhGlnki1W13ZkUAg8rL-TFuicNYYQSlJBSkcIY02JvPtawyr4_0q5ieuaMMMXrtTSGc8H-JJshhU1tMpQAfRocOJZ53QKBvq8b34o3RzhgsmPeQoLPz4-t0o6MiS8RAuAr5o3b6SCnTsYNoyrhX_J6Th_xxoXJbKs3RkMwP3XYAAmhSlZvoYdayuVqZO9KCxK', description: 'Creates architectural proposal files for consent.', nextSteps: ['step-3'] },
  { id: 'step-3', name: 'Init Project', agent: 'Orchestrator', aiTool: 'Antigravity CLI', avatar: 'https://lh3.googleusercontent.com/aida-public/AB6AXuCdbGLlsb3N3uOkfOjw1Q1_yDEdGIJRGnmhLu-FVragfIKdNByQw1J1dUhUyD0bhtU68_IQlwgYzvIetQ2bY0YH_lZtUPtQ34nuKBxaxPyS3e2_NiWBHxGCtDAanZ14d9Jj74bIX1CMvh__wE2web2l3_MmMZ3M6VbcAyIQ32DmLoC1ZxOulFXqko_7SDi7dj4UYhiz2GZJT9mIeqNcXO-z24SVjGrZaOr-FBsXxb6cUVkNht5QSQLvRy955U1VtJCFXs670Vt4hbki', description: 'Bootstraps folders and basic setups.', nextSteps: ['step-4'] },
  { id: 'step-4', name: 'Visual Design', agent: 'Builder', avatar: 'https://lh3.googleusercontent.com/aida-public/AB6AXuDmaRLi3irRTkuzp5k7fHmK2YfMAmLw7p51bV98-DQqqF3sv--U5P_quS1s0WdKEebiVYvBSSjPAYuJhGlnki1W13ZkUAg8rL-TFuicNYYQSlJBSkcIY02JvPtawyr4_0q5ieuaMMMXrtTSGc8H-JJshhU1tMpQAfRocOJZ53QKBvq8b34o3RzhgsmPeQoLPz4-t0o6MiS8RAuAr5o3b6SCnTsYNoyrhX_J6Th_xxoXJbKs3RkMwP3XYAAmhSlZvoYdayuVqZO9KCxK', description: 'Designs interface mockup layouts and presets.', nextSteps: ['step-5'] },
  { id: 'step-5', name: 'Demo & Contract', agent: 'Evaluator', avatar: 'https://lh3.googleusercontent.com/aida-public/AB6AXuDwJnNbp2raVLqd_mC4d5YtdShmwCCjMsV4fmcXOm7L3h-W2yQazezAP32i5IJQ9Nyp4pWuPNTiBWlE9SocUZcx5vVYH_EDAY9A4-Vq-ODoKD9DivyySpUXz6xut0EZdtNWGv-vFyqNhGYPAMJ231yj_e69p0-h9sEXHdFQJ1dn0ZM9t65mkpHWNhptugyXS3vpe4FMS-IHU_INcO81RZs_CPC_cgUbvUhtbpgqs2NSSpGQkHnrUi2pdivziGk0SbaHTSJYZHaKKypb', description: 'Verifies visually using multi-agent compliance checklists.', nextSteps: ['step-6'] },
  { id: 'step-6', name: 'Architecture & Breakdown', agent: 'Orchestrator', avatar: 'https://lh3.googleusercontent.com/aida-public/AB6AXuCdbGLlsb3N3uOkfOjw1Q1_yDEdGIJRGnmhLu-FVragfIKdNByQw1J1dUhUyD0bhtU68_IQlwgYzvIetQ2bY0YH_lZtUPtQ34nuKBxaxPyS3e2_NiWBHxGCtDAanZ14d9Jj74bIX1CMvh__wE2web2l3_MmMZ3M6VbcAyIQ32DmLoC1ZxOulFXqko_7SDi7dj4UYhiz2GZJT9mIeqNcXO-z24SVjGrZaOr-FBsXxb6cUVkNht5QSQLvRy955U1VtJCFXs670Vt4hbki', description: 'Breaks down implementation into granular file edits.', nextSteps: ['step-7'] },
  { id: 'step-7', name: 'Write Code', agent: 'Builder', avatar: 'https://lh3.googleusercontent.com/aida-public/AB6AXuDmaRLi3irRTkuzp5k7fHmK2YfMAmLw7p51bV98-DQqqF3sv--U5P_quS1s0WdKEebiVYvBSSjPAYuJhGlnki1W13ZkUAg8rL-TFuicNYYQSlJBSkcIY02JvPtawyr4_0q5ieuaMMMXrtTSGc8H-JJshhU1tMpQAfRocOJZ53QKBvq8b34o3RzhgsmPeQoLPz4-t0o6MiS8RAuAr5o3b6SCnTsYNoyrhX_J6Th_xxoXJbKs3RkMwP3XYAAmhSlZvoYdayuVqZO9KCxK', description: 'Writes components, state management, and tests.', nextSteps: ['step-8'] },
  { id: 'step-8', name: 'Truth Alignment', agent: 'Evaluator', avatar: 'https://lh3.googleusercontent.com/aida-public/AB6AXuDwJnNbp2raVLqd_mC4d5YtdShmwCCjMsV4fmcXOm7L3h-W2yQazezAP32i5IJQ9Nyp4pWuPNTiBWlE9SocUZcx5vVYH_EDAY9A4-Vq-ODoKD9DivyySpUXz6xut0EZdtNWGv-vFyqNhGYPAMJ231yj_e69p0-h9sEXHdFQJ1dn0ZM9t65mkpHWNhptugyXS3vpe4FMS-IHU_INcO81RZs_CPC_cgUbvUhtbpgqs2NSSpGQkHnrUi2pdivziGk0SbaHTSJYZHaKKypb', description: 'Cross-checks live state against wireframe specs.', nextSteps: ['step-9'] },
  { id: 'step-9', name: 'Test', agent: 'Evaluator', avatar: 'https://lh3.googleusercontent.com/aida-public/AB6AXuDwJnNbp2raVLqd_mC4d5YtdShmwCCjMsV4fmcXOm7L3h-W2yQazezAP32i5IJQ9Nyp4pWuPNTiBWlE9SocUZcx5vVYH_EDAY9A4-Vq-ODoKD9DivyySpUXz6xut0EZdtNWGv-vFyqNhGYPAMJ231yj_e69p0-h9sEXHdFQJ1dn0ZM9t65mkpHWNhptugyXS3vpe4FMS-IHU_INcO81RZs_CPC_cgUbvUhtbpgqs2NSSpGQkHnrUi2pdivziGk0SbaHTSJYZHaKKypb', description: 'Runs unit, system integration, and interface visual tests.', nextSteps: ['step-10', 'step-7'] },
  { id: 'step-10', name: 'Release & Iterate', agent: 'Orchestrator', avatar: 'https://lh3.googleusercontent.com/aida-public/AB6AXuCdbGLlsb3N3uOkfOjw1Q1_yDEdGIJRGnmhLu-FVragfIKdNByQw1J1dUhUyD0bhtU68_IQlwgYzvIetQ2bY0YH_lZtUPtQ34nuKBxaxPyS3e2_NiWBHxGCtDAanZ14d9Jj74bIX1CMvh__wE2web2l3_MmMZ3M6VbcAyIQ32DmLoC1ZxOulFXqko_7SDi7dj4UYhiz2GZJT9mIeqNcXO-z24SVjGrZaOr-FBsXxb6cUVkNht5QSQLvRy955U1VtJCFXs670Vt4hbki', description: 'Tags the final workflow branch and triggers the automated deployment pipeline.', nextSteps: [] }
];

export const mockWorkflows: import('./types').WorkflowDef[] = [
  {
    id: 'wf-1',
    name: 'Clutch Coding Schema',
    lastDeployed: '2h ago',
    isActive: true,
    icon: 'code',
    steps: workflowSteps,
  },
  {
    id: 'wf-2',
    name: 'Video Production Pipeline',
    lastDeployed: '14h ago',
    isActive: false,
    icon: 'movie',
    steps: [
      { id: 'v-1', name: 'Asset Gathering', agent: 'Builder', aiTool: 'Antigravity CLI', description: 'Gathers images and clips.', nextSteps: ['v-2'] },
      { id: 'v-2', name: 'Render Content', agent: 'Builder', description: 'Renders the content based on assets.', nextSteps: ['v-3'] },
      { id: 'v-3', name: 'Review', agent: 'Evaluator', description: 'Reviews the content.', nextSteps: ['v-4', 'v-2'] },
      { id: 'v-4', name: 'Publish', agent: 'Orchestrator', description: 'Publishes to destination.', nextSteps: [] },
    ],
  }
];

export const fileTreeNodes = [
  { name: '.aider.tags.cache.v4', type: 'folder', collapsed: true, children: [] },
  { name: '.claude', type: 'folder', collapsed: true, children: [] },
  { name: '.obsidian', type: 'folder', collapsed: true, children: [] },
  { name: '.reasonix', type: 'folder', collapsed: true, children: [] },
  {
    name: 'PARA',
    type: 'folder',
    collapsed: false,
    children: [
      { name: 'AGENTS.md', type: 'file', content: '# 🤖 Librarian Protocol v2.0 (System Commander)\n\n## 📋 Operational Directives\n\nYou are currently the **Chief Auditor** of this knowledge base. When processing `3_Resources/Wiki/raw/buffer/`, you must strictly adhere to the following pipeline:\n\n### 1. Quarantine Rule\n\n- Check standard file formatting. If encrypted PDF, damaged markdown or large file exceeding 100k tokens is encountered, quarantine instantly to `3_Resources/Wiki/raw/quarantine/`.\n- Log failures within `3_Resources/Wiki/meta/log.md`.\n\n### 2. Claim-First Extraction\n\n- Prior to completing a summary, you must generate a corresponding `Claim_[FileName].md` inside `3_Resources/Wiki/meta/claims/`.\n- Every detail added to the Wiki must align to original citations.\n\n### 3. Logical Melting\n\n- **Concepts**: Place general theory in `3_Resources/Wiki/pages/concepts/`.\n- **Entities**: Place specific software in `3_Resources/Wiki/pages/entities/`.\n- Bidirectional metadata link density must exceed 2 links/paragraph.\n\n### 4. Chronological Archiving\n\n- Archive raw materials to `3_Resources/Library/YYYY/MM/`.\n- Rename standard files to `YYYYMMDD_[FileName].md`.\n\n## 🚫 Hard Constraints\n\n- Physical layer (Library/) forbids logical schema categorization.\n- Never modify raw input directory files directly.\n- Wiki search sources must point to the newest physical paths.' },
      { name: 'CLAUDE.md', type: 'file', content: '# Claude Custom Instructions\nConfigures visual, layout, structural guidelines, and quality bars for frontends.' },
      { name: 'CONTEXT_LIFECYCLE.md', type: 'file', content: '# Lifecycle Guidelines\nEnsures standard container persistence, background hooks, and cache configurations.' }
    ]
  }
];

export const initialTerminalLogs = [
  '[ORCHESTRATOR] Initializing run id: run_vid_prod_f8423',
  '[ORCHESTRATOR] Spawning dynamic multi-agent workflow: Flow: Video Production',
  '[ORCHESTRATOR] Validating repository structure...',
  '[ORCHESTRATOR] Assigned step (1/10): Find Problem & Direction... Done in 0.4s',
  '[BUILDER] Received contract request: prep video environment',
  '[BUILDER] Writing 12 structural modules in /src/video-core...',
  '[BUILDER] Code generated successfully. Done in 2.8s',
  '[EVALUATOR] Running automated validation on round 1 output...',
  '[EVALUATOR] CRITICAL WARNING: missing expected verify.md file inside workspace root.',
  '[EVALUATOR] Execution failed. Pipeline gate status: FAILED (Exit Code 1)',
  '-- PENDING HUMAN INTERVENSION --',
  'Waiting for user command to re-assign or repair project...'
];
