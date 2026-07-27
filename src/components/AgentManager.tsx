import React, { useState, useEffect } from 'react';

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
}

const DEFAULT_AGENTS: Agent[] = [
  {
    id: 'agent-orchestrator',
    name: 'Orchestrator Module (VobeSOP v2)',
    description: 'Parses system instructions, establishes project file trees, and assigns granular code files to modular subtask units.',
    lastModified: '2026-06-21 14:30',
    avatar: 'https://lh3.googleusercontent.com/aida-public/AB6AXuA0yGh59QNLj5n0igNxMgu4lgaiNqZpcN29SpWM0JHNlAuFmOBx-Id67Zcd2NDCNBjBKrcffQrdrfoe-3XaSlveekLAP9SRis93uTk7XPPFO5y4Swos7NvATw6n7eZEm7nfAQuTiMAoWRSnxefAOJugUbZx3fCTNv4jGyjvT-UZznwKzp_HoXuStup_0juhBCZYamrV0Coil-k27d9Yi7il6NabIEG0FfbxwL5V5azpfZQOlBfpaganta2kP7n59BKPHd4K2uTOfZ5p',
    markdownDoc: `# Orchestrator Module (VobeSOP v2)

The Orchestrator is the central dispatcher and runtime monitor of the AI multi-agent workflow. It structures human requirements into explicit technical specifications.

## 🎯 Key Responsibilities
- **Context Triage**: Evaluates changes in specifications and user goals.
- **Plan Synthesizer**: Generates highly targeted \`plan.md\` tasks prioritizing modularized structure.
- **Dispatch & Guard**: Spawns subtask agents (Builder, Auditor) and configures quality gates.

## ⚙️ Operating Procedures
1. Reads workspace repository files on activation.
2. Generates initial orchestration manifest files.
3. Watches output streams to verify alignment with strict technical standards.
`,
    deliverables: [
      {
        name: 'plan.md',
        content: `# Action Plan: Video Pipeline Orchestration

This plan directs current subprocess agents for validating visual assets and running smoke testing protocols.

## 📋 Required Actions
- [x] Gather layout constraints for index/compositions.
- [x] Establish the clean environment configurations.
- [ ] Compile final video render components using JSX.
`
      },
      {
        name: 'handoff-status.json',
        content: `{
  "pipelineState": "ORCHESTRATED",
  "gatesPassed": ["Gate_1_Initiated", "Gate_2_Syntax_Verify"],
  "mp4Path": "out/Video_Production_v2.mp4",
  "activeAgent": "Builder",
  "timestamp": "2026-06-21T07:38:43Z"
}`
      }
    ]
  },
  {
    id: 'agent-builder',
    name: 'Builder Module (JSX VibeCoder)',
    description: 'Generates responsive Tailwind layouts, writes clean TypeScript classes, resolves directory schema constraints, and executes local debug suites.',
    lastModified: '2026-06-20 09:15',
    avatar: 'https://lh3.googleusercontent.com/aida-public/AB6AXuBpRidttSGTIY-J-PGvnlcZX_oZSZoBXJY5vjZ9g1PKl_fq4EKoa2RXbcSCvvIdbPLdmfuzPKTxnR8TqV7skwsKlt-eKEzSzktv-TWbHu4c9uBEdP6Es_Fjek1EBQuGZeMtWsUi3fn0lyozFaZBLp9SpES3r0WalbqYY6gGiT1R_0J1kvU-D9rI_2q2f3sMGHuTjWyOZ5gImCLGHSGejtcKmToTSZYMrXfT_A5x1iw_f4q7WljP3FXjk64aQhLgh9nTXUDfPdkIzu0b',
    markdownDoc: `# Builder Module (JSX VibeCoder)

The execution engine responsible for writing production-ready React modules, schema bindings, and custom user styles.

## 🛠️ Main Capabilities
- **Responsive Layout Design**: Strict adherence to mobile-first + desktop-precision styling systems.
- **Type-safe State Machines**: Implements robust state flows without excessive rendering side-effects.
- **Zero-Dependency Core**: Avoids heavy third-party bloat, relying on streamlined inline hooks.

## 🛡️ Coding Directives
- Always declare Types in \`src/types.ts\`.
- Keep component imports crisp, modular, and cleanly separated.
- Style with direct Tailwind CSS values rather than complex custom CSS rules.
`,
    deliverables: [
      {
        name: 'src/App.tsx',
        content: `import React, { useState } from 'react';

export default function App() {
  const [activeTab, setActiveTab] = useState('chat');
  return (
    <div className="flex h-screen bg-neutral-50">
      <header className="h-14 border-b border-neutral-200">
        <h1 className="text-sm font-bold">Vibe Workspace</h1>
      </header>
    </div>
  );
}`
      },
      {
        name: 'src/mockData.ts',
        content: `export const initialData = {
  status: "ready",
  version: "2.4.1",
  lastCommit: "2026-06-21T07:38:43Z"
};`
      }
    ]
  },
  {
    id: 'agent-auditor',
    name: 'Auditor Agent (Pipeline Quality Audit)',
    description: 'Examines workflow and product quality pipelines, performing pixel-precise visually verification, extracting keyframes, and enforcing regression compliance.',
    lastModified: '2026-06-21 15:00',
    avatar: 'https://lh3.googleusercontent.com/aida-public/AB6AXuCmb7VGaQXE-4sYnIZR3VrcHVAPhv4Px14kMlkayJj8kVm8htTWITmPi26wsj8P6B9RrqykIWj81S2ilmGR0e8cXhA1gjc3U-Nw0DsgHV3HvVmBskuoUksIt6YM6Z3ORjFtRhBphqAXxRKf9ke-zYcPs0TcEFKxw_bwGXSDiAKV5CL7kZf9i6lSZDe91ccUNjaAIsgTMKEEvYc7bZpXYz3D5dClulRwbNru5SZB-1E5FM0A2qMPs-IAfiR8OB1-cUvFh3WYKx9qlGgN',
    markdownDoc: `# Auditor Agent (Pipeline Quality Audit)

This quality containment unit ensures compliance and visual elegance across all generated pipeline assets.

## 📋 Auditor Guidelines
1. **Quarantine Rule**: Automatically flags large or damaged elements and moves them to secure buffers.
2. **Claim-First**: Formally aligns facts with direct textual citations.
3. **Double links**: Enforces bidirectional metadata link patterns with a density > 2 links/para.

## 🚫 Critical Constraints
- Keep physical outputs entirely distinct from logical groupings.
- Never modify raw baseline input records directly.
`,
    deliverables: [
      {
        name: '.claude/agents/auditor.md',
        content: `# Auditor Agent Configuration Override

- Evaluates: Design system layout constraints
- Verification tool: Headless engine keyframes
- Regression tolerance: 0% layout shift permitted`
      },
      {
        name: 'runs/audit-system-actions.md',
        content: `# System Actions — Audit Round #4

## Systemic Issues Identified
- **SA-01: Auto-scaling overflow under 1280x720 canvas**
  - *Evidence:* Layout truncation on scene 3 screenshot.
  - *Correction:* Adjusted \`scale-css-px.ts\` multiplier parameters.`
      },
      {
        name: 'runs/auditor-report.md',
        content: `# Auditor Report: Smoke Spec 14 Fast

## Visual Verification Outcomes
| SceneID | Screenshot | Visual Result | Layout Match |
|---|---|---|---|
| scene1 | \`screenshots/scene1-lastframe.png\` | PASS | YES |
| scene2 | \`screenshots/scene2-lastframe.png\` | PASS | YES |
| scene3 | \`screenshots/scene3-lastframe.png\` | FAIL | NO (truncated) |`
      }
    ]
  },
  {
    id: 'agent-evaluator',
    name: 'Evaluator Module (Automated QA Compliance)',
    description: 'Validates visual layout parameters against design wireframes, compliance contrast benchmarks, and checks list artifacts for exits.',
    lastModified: '2026-06-19 18:22',
    avatar: 'https://lh3.googleusercontent.com/aida-public/AB6AXuA1WfXo6Scl9tL9vT3yG0tYyL9K2zE3O9_4O_4A_5o9S1vP5T5_4O_4A_5o9S1vP5T5_4O_4A_5',
    markdownDoc: `# Evaluator Module (Automated QA Compliance)

Automated system for verifying lint rules, syntax compilation, and functional assertions across all components.

## 🔍 Validation Checklist
- **Lint Compliance**: Asserts strict compliance with project parameters.
- **Artifact Auditing**: Verifies that required files exist and contain appropriate configurations.
- **Type-Safety Audits**: Disallows loose structures, implicit any types, or hanging references.
`,
    deliverables: [
      {
        name: 'verify.md',
        content: `# Verification Logs - QA Complete

Linter successfully verified no unused types or missing imports.

## Status Checklist
- [x] Linter diagnostics: SUCCESS
- [x] Unused dependencies check: COMPLETE
- [x] Production build artifact checks: MATCHED`
      },
      {
        name: 'evaluator-verdict.json',
        content: `{
  "engineeringPass": true,
  "visualAuditPass": true,
  "userSignoff": true,
  "buildDuration": "2.42s"
}`
      }
    ]
  }
];

export function AgentLogo({ name, description, className = "w-10 h-10" }: { name: string; description: string; className?: string }) {
  // Let's create a deterministic hash from name
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  
  // Deterministic gradients
  const gradients = [
    { from: '#4F46E5', to: '#06B6D4' }, // Indigo to Cyan
    { from: '#7C3AED', to: '#EC4899' }, // Violet to Pink
    { from: '#10B981', to: '#3B82F6' }, // Emerald to Blue
    { from: '#EF4444', to: '#F59E0B' }, // Red to Amber
    { from: '#020617', to: '#3B82F6' }, // Dark Slate to Blue
    { from: '#2563EB', to: '#8B5CF6' }  // Blue to Purple
  ];
  const grad = gradients[Math.abs(hash) % gradients.length];
  
  // Select first letters
  const cleaned = name.replace(/[^a-zA-Z]/g, '');
  const initial = cleaned.slice(0, 2).toUpperCase() || name.slice(0, 1).toUpperCase();
  
  // Patterns based on descriptor triggers
  const isOrchestrator = name.toLowerCase().includes('orchestra') || description.toLowerCase().includes('parse') || description.toLowerCase().includes('dispatch');
  const isBuilder = name.toLowerCase().includes('build') || name.toLowerCase().includes('code') || description.toLowerCase().includes('write') || description.toLowerCase().includes('generat');
  const isAuditor = name.toLowerCase().includes('audit') || description.toLowerCase().includes('pixel') || description.toLowerCase().includes('quality');
  const isEvaluator = name.toLowerCase().includes('eval') || name.toLowerCase().includes('qa') || description.toLowerCase().includes('validat');
  
  return (
    <div className={`${className} rounded-full flex items-center justify-center text-white relative overflow-hidden shadow-inner flex-shrink-0 select-none border border-neutral-200/20`} style={{ background: `linear-gradient(135deg, ${grad.from}, ${grad.to})` }}>
      {/* Background Graphic Lines representing systemic pipelines */}
      <svg className="absolute inset-0 w-full h-full opacity-25 pointer-events-none" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 40">
        {isOrchestrator && (
          <>
            <circle cx="10" cy="10" r="2" fill="white" />
            <circle cx="30" cy="10" r="2" fill="white" />
            <circle cx="20" cy="30" r="3" fill="white" />
            <line x1="10" y1="10" x2="20" y2="30" stroke="white" strokeWidth="1" />
            <line x1="30" y1="10" x2="20" y2="30" stroke="white" strokeWidth="1" />
          </>
        )}
        {isBuilder && (
          <>
            <rect x="12" y="12" width="16" height="16" rx="2" fill="none" stroke="white" strokeWidth="1.5" />
            <line x1="12" y1="20" x2="28" y2="20" stroke="white" strokeWidth="1" />
            <line x1="20" y1="12" x2="20" y2="28" stroke="white" strokeWidth="1" strokeDasharray="1 1" />
          </>
        )}
        {isAuditor && (
          <>
            <circle cx="20" cy="20" r="10" fill="none" stroke="white" strokeWidth="1.2" strokeDasharray="2 2" />
            <line x1="20" y1="8" x2="20" y2="32" stroke="white" strokeWidth="0.8" />
          </>
        )}
        {isEvaluator && (
          <>
            <path d="M 12 20 L 18 26 L 28 14" fill="none" stroke="white" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
          </>
        )}
        {!isOrchestrator && !isBuilder && !isAuditor && !isEvaluator && (
          <circle cx="20" cy="20" r="8" fill="none" stroke="white" strokeWidth="0.8" />
        )}
      </svg>
      
      {/* Initials Text */}
      <span className="font-mono text-[10px] font-extrabold tracking-wider z-10 drop-shadow-md">
        {initial}
      </span>
    </div>
  );
}

interface AgentManagerProps {
  selectedSidebarWidth?: number;
  isModalStyle?: boolean;
}

export function AgentManager({ selectedSidebarWidth, isModalStyle }: AgentManagerProps) {
  const [agents, setAgents] = useState<Agent[]>(() => {
    const saved = localStorage.getItem('vibe-workspace-agents');
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch (e) {
        return DEFAULT_AGENTS;
      }
    }
    return DEFAULT_AGENTS;
  });

  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [isPreviewDeliverable, setIsPreviewDeliverable] = useState<Deliverable | null>(null);
  
  // Modal state
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalMode, setModalMode] = useState<'create' | 'edit'>('create');
  
  // Form fields
  const [editingId, setEditingId] = useState<string>('');
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [markdownDoc, setMarkdownDoc] = useState('');
  const [deliverablesInput, setDeliverablesInput] = useState<{ name: string; content: string }[]>([]);
  const [newDelivName, setNewDelivName] = useState('');
  const [newDelivContent, setNewDelivContent] = useState('');

  useEffect(() => {
    localStorage.setItem('vibe-workspace-agents', JSON.stringify(agents));
  }, [agents]);

  const handleOpenCreate = () => {
    setModalMode('create');
    setEditingId('');
    setName('');
    setDescription('');
    setMarkdownDoc(`# Custom Agent Prompt\n\nDefine custom parameters or directives for this agent here.\n\n## 📋 Protocol\n- Task validation.\n- Process orchestration.`);
    setDeliverablesInput([
      { name: 'instructions.md', content: '# Custom instructions\n- Rule 1: Compile cleanly\n- Rule 2: Adhere to guidelines.' }
    ]);
    setNewDelivName('');
    setNewDelivContent('');
    setIsModalOpen(true);
  };

  const handleOpenEdit = (agent: Agent, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    setModalMode('edit');
    setEditingId(agent.id);
    setName(agent.name);
    setDescription(agent.description);
    setMarkdownDoc(agent.markdownDoc);
    setDeliverablesInput([...agent.deliverables]);
    setNewDelivName('');
    setNewDelivContent('');
    setIsModalOpen(true);
  };

  const handleDelete = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (window.confirm('Are you sure you want to delete this AI Agent?')) {
      const updated = agents.filter(a => a.id !== id);
      setAgents(updated);
      if (selectedAgent && selectedAgent.id === id) {
        setSelectedAgent(null);
      }
    }
  };

  const handleAddDeliverable = () => {
    if (!newDelivName.trim()) return;
    setDeliverablesInput([
      ...deliverablesInput,
      { name: newDelivName.trim(), content: newDelivContent || '# Sample Content' }
    ]);
    setNewDelivName('');
    setNewDelivContent('');
  };

  const handleRemoveDeliverable = (index: number) => {
    setDeliverablesInput(deliverablesInput.filter((_, i) => i !== index));
  };

  const handleSave = () => {
    if (!name.trim()) {
      alert('Please enter Agent Name');
      return;
    }

    const todayStr = new Date().toISOString().replace('T', ' ').substring(0, 16);

    if (modalMode === 'create') {
      const newAgent: Agent = {
        id: `agent-${Date.now()}`,
        name: name.trim(),
        description: description.trim(),
        markdownDoc: markdownDoc.trim(),
        lastModified: todayStr,
        avatar: `https://api.dicebear.com/7.x/bottts/svg?seed=${encodeURIComponent(name)}`,
        deliverables: deliverablesInput
      };
      setAgents([newAgent, ...agents]);
    } else {
      const updated = agents.map(a => {
        if (a.id === editingId) {
          const updatedAgent = {
            ...a,
            name: name.trim(),
            description: description.trim(),
            markdownDoc: markdownDoc.trim(),
            lastModified: todayStr,
            deliverables: deliverablesInput
          };
          if (selectedAgent && selectedAgent.id === editingId) {
            setSelectedAgent(updatedAgent);
          }
          return updatedAgent;
        }
        return a;
      });
      setAgents(updated);
    }
    setIsModalOpen(false);
  };

  // Helper parser to render Markdown gracefully
  const renderMarkdownText = (text: string) => {
    if (!text) return null;
    return text.split('\n').map((line, i) => {
      if (line.startsWith('# ')) {
        return (
          <h1 key={i} className="text-[18px] font-extrabold text-neutral-900 border-b border-neutral-200 pb-2.5 mb-4 mt-2">
            {line.substring(2)}
          </h1>
        );
      }
      if (line.startsWith('## ')) {
        return (
          <h2 key={i} className="text-[14px] font-bold text-neutral-800 mt-5 mb-2 flex items-center gap-2">
            {line.substring(3)}
          </h2>
        );
      }
      if (line.startsWith('### ')) {
        return (
          <h3 key={i} className="text-[12.5px] font-bold text-neutral-800 mt-4 mb-2">
            {line.substring(4)}
          </h3>
        );
      }
      if (line.startsWith('- ')) {
        let content = line.substring(2);
        // Quick bold handling: **item**
        content = content.replace(/\*\*(.*?)\*\*/g, '<strong class="text-neutral-950 font-semibold">$1</strong>');
        // Backticks code formatting
        content = content.replace(/`([^`]+)`/g, '<code class="bg-neutral-100 text-neutral-900 px-1 py-0.5 rounded font-mono text-[11px] border border-neutral-200/50 mx-0.5">$1</code>');
        // Double brackets handling
        content = content.replace(/\[\[(.*?)\]\]/g, '<span class="text-[#897FDB] font-medium">[[ $1 ]]</span>');
        
        return (
          <div key={i} className="flex items-start gap-2 pl-1 my-1.5 text-neutral-600 text-[12.5px]">
            <span className="w-1 h-1.5 mt-2 rounded bg-neutral-400 flex-shrink-0" />
            <span dangerouslySetInnerHTML={{ __html: content }} />
          </div>
        );
      }
      if (line.startsWith('|') && line.includes('---')) {
        return null; // Skip markdown divider lines in simplified view
      }
      if (line.startsWith('|')) {
        // Render simple table support
        const cells = line.split('|').map(s => s.trim()).filter((_, index, arr) => index > 0 && index < arr.length - 1);
        const isHeader = i === 4; // approximate
        return (
          <div key={i} className="flex border-b border-neutral-100 py-1.5 px-2 bg-neutral-50/40 text-[11.5px] text-neutral-600 font-mono">
            {cells.map((cell, idx) => (
              <div key={idx} className="flex-1 overflow-hidden text-ellipsis whitespace-nowrap px-1.5">
                {cell}
              </div>
            ))}
          </div>
        );
      }

      const pContent = line
        .replace(/\*\*(.*?)\*\*/g, '<strong class="text-neutral-950 font-semibold">$1</strong>')
        .replace(/`([^`]+)`/g, '<code class="bg-neutral-100 text-neutral-900 px-1 py-0.5 rounded font-mono text-[11px] border border-neutral-200/50 mx-0.5">$1</code>');
      
      return (
        <p key={i} className={line.trim() ? "my-2 text-neutral-600 text-[12.5px] leading-relaxed" : "h-1"} dangerouslySetInnerHTML={{ __html: pContent }} />
      );
    });
  };

  return (
    <div 
      style={isModalStyle ? undefined : { paddingLeft: `${(selectedSidebarWidth || 0) + 32}px`, paddingTop: '76px' }} 
      className={`flex-1 flex flex-col overflow-hidden animate-fade-in relative transition-all duration-300 ${isModalStyle ? 'h-full' : 'h-screen bg-neutral-50'}`}
    >
      {selectedAgent ? (
        // ----------------- AGENT DETAIL PAGE -----------------
        <div className="flex-1 flex flex-col h-full overflow-hidden">
          {/* Breadcrumbs Action Header */}
          <div className={`h-14 border-b border-neutral-200 pl-6 flex items-center justify-between bg-white flex-shrink-0 ${isModalStyle ? 'pr-12' : 'pr-6'}`}>
            <div className="flex items-center gap-3">
              <button 
                onClick={() => setSelectedAgent(null)}
                className="flex items-center justify-center p-1.5 hover:bg-neutral-100 rounded-lg text-neutral-500 hover:text-neutral-900 transition-colors"
                title="Back to List"
              >
                <span className="material-symbols-outlined text-[18px]">arrow_back</span>
              </button>
              <div className="h-4 w-[1px] bg-neutral-200" />
              <div className="flex items-center gap-1.5 text-[11px] font-semibold text-neutral-400 font-mono uppercase tracking-wider">
                <span>AI AGENTS</span>
                <span>/</span>
                <span className="text-neutral-800">{selectedAgent.name.split(' (')[0]}</span>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={(e) => handleOpenEdit(selectedAgent, e)}
                className="flex items-center gap-1.5 px-3 py-1.5 text-neutral-600 hover:text-neutral-900 hover:bg-neutral-100 rounded-lg text-[11.5px] font-semibold transition-colors border border-neutral-200 bg-white"
              >
                <span className="material-symbols-outlined text-[15px]">edit</span>
                Edit Settings
              </button>
              <button
                onClick={(e) => handleDelete(selectedAgent.id, e)}
                className="flex items-center gap-1.5 px-3 py-1.5 text-red-600 hover:text-red-700 hover:bg-red-50 rounded-lg text-[11.5px] font-semibold transition-colors border border-red-100 bg-white"
              >
                <span className="material-symbols-outlined text-[15px]">delete</span>
                Delete
              </button>
            </div>
          </div>

          {/* Dual Column Layout */}
          <div className="flex-1 flex overflow-hidden min-h-0 bg-neutral-50/40">
            {/* Left Column: Markdown prompt viewer */}
            <div className="flex-1 overflow-y-auto p-8 border-r border-neutral-200">
              <div className="max-w-2xl mx-auto bg-white border border-neutral-200/70 p-8 rounded-xl shadow-xs leading-relaxed font-sans mt-2 mb-10">
                <div className="flex items-center gap-4 border-b border-neutral-100 pb-5 mb-5 select-none">
                  <AgentLogo name={selectedAgent.name} description={selectedAgent.description} className="w-12 h-12 text-sm" />
                  <div>
                    <h2 className="text-sm font-bold text-neutral-900 tracking-tight font-mono">{selectedAgent.name}</h2>
                    <p className="text-[11px] text-neutral-400 mt-0.5">Role System Specifications</p>
                  </div>
                </div>

                <div className="space-y-1">
                  {renderMarkdownText(selectedAgent.markdownDoc)}
                </div>
              </div>
            </div>

            {/* Right Column: Metadata & Deliverables Panel */}
            <div className="w-80 flex flex-col bg-white overflow-y-auto flex-shrink-0 border-l border-neutral-100 p-6 space-y-6">
              <div>
                <h3 className="text-[11px] font-bold text-neutral-400 font-mono uppercase tracking-wider mb-2">Agent Details</h3>
                <div className="bg-neutral-50 p-4 rounded-xl border border-neutral-200/50 space-y-3">
                  <div>
                    <p className="text-[10px] text-neutral-400 font-medium">NAME</p>
                    <p className="text-[11.5px] text-neutral-800 font-semibold mt-0.5">{selectedAgent.name}</p>
                  </div>
                  <div>
                    <p className="text-[10px] text-neutral-400 font-medium">DESCRIPTION</p>
                    <p className="text-[11px] text-neutral-600 font-normal mt-0.5 leading-relaxed">{selectedAgent.description}</p>
                  </div>
                  <div className="border-t border-neutral-200/50 pt-2.5 flex justify-between items-center">
                    <div>
                      <p className="text-[10px] text-neutral-400 font-medium">LAST MODIFIED</p>
                      <p className="text-[10.5px] text-neutral-600 font-mono font-medium mt-0.5">{selectedAgent.lastModified}</p>
                    </div>
                    <span className="text-[10px] bg-neutral-200/50 text-neutral-600 px-2 py-0.5 rounded-full font-mono font-semibold">ACTIVE</span>
                  </div>
                </div>
              </div>

              <div className="flex-1 flex flex-col min-h-0">
                <h3 className="text-[11px] font-bold text-neutral-400 font-mono uppercase tracking-wider mb-2">Deliverables (Output Files)</h3>
                <div className="flex-1 space-y-2">
                  {selectedAgent.deliverables && selectedAgent.deliverables.length > 0 ? (
                    selectedAgent.deliverables.map((item, index) => (
                      <button
                        key={index}
                        onClick={() => setIsPreviewDeliverable(item)}
                        className="w-full flex items-center justify-between p-3 border border-neutral-200 hover:border-neutral-300 bg-neutral-50/30 hover:bg-neutral-50 rounded-xl text-left transition-all duration-150 group"
                      >
                        <div className="flex items-center gap-2.5 overflow-hidden">
                          <span className="material-symbols-outlined text-[17px] text-neutral-400 group-hover:text-neutral-600 font-mono">
                            {item.name.endsWith('.json') ? 'schema' : 'insert_drive_file'}
                          </span>
                          <span className="text-[11.5px] font-mono text-neutral-800 font-bold truncate group-hover:text-black">
                            {item.name}
                          </span>
                        </div>
                        <span className="material-symbols-outlined text-[15px] text-neutral-400 opacity-0 group-hover:opacity-100 transition-opacity">
                          visibility
                        </span>
                      </button>
                    ))
                  ) : (
                    <p className="text-[11px] text-neutral-400 italic">No associated deliverablesconfigured.</p>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      ) : (
        // ----------------- AGENT CATALOG LIST PAGE -----------------
        <div className="max-w-4xl mx-auto w-full p-8 space-y-6 overflow-y-auto">
          {/* List Header */}
          <div className={`flex items-center justify-between border-b border-neutral-100 pb-5 ${isModalStyle ? 'mr-12' : ''}`}>
            <div>
              <h2 className="text-base font-bold text-neutral-800 tracking-tight flex items-center gap-2">
                <span className="material-symbols-outlined text-neutral-500 text-[20px]">smart_toy</span>
                AI Agent Controller
              </h2>
              <p className="text-[11.5px] text-neutral-400 mt-1">
                Display the operational directive frameworks and output manifests loaded in the execution sandbox.
              </p>
            </div>
            
            <button
              onClick={handleOpenCreate}
              className="flex items-center gap-1.5 px-4 py-2 bg-neutral-50 hover:bg-neutral-100 text-neutral-700 hover:text-neutral-950 border border-neutral-200/60 rounded-xl text-xs font-bold transition-all shadow-2xs active:scale-97 cursor-pointer"
            >
              <span className="material-symbols-outlined text-[16px]">add</span>
              Create Agent
            </button>
          </div>

          {/* Agents Grid List */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {agents.map((agent) => (
              <div
                key={agent.id}
                onClick={() => setSelectedAgent(agent)}
                className="p-5 border border-neutral-200/45 hover:border-neutral-300/80 bg-white rounded-xl shadow-xs hover:shadow-sm cursor-pointer transition-all duration-200 relative group flex flex-col justify-between min-h-[148px]"
              >
                <div>
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <AgentLogo name={agent.name} description={agent.description} className="w-10 h-10 text-[10px]" />
                      <div>
                        <h3 className="text-xs font-bold text-neutral-900 font-mono tracking-tight text-left">
                          {agent.name}
                        </h3>
                        <p className="text-[10px] text-neutral-400 font-mono font-medium mt-0.5">
                          Edited: {agent.lastModified}
                        </p>
                      </div>
                    </div>
                  </div>

                  <p className="text-[11.5px] text-neutral-500 mt-3.5 leading-relaxed text-left line-clamp-3">
                    {agent.description}
                  </p>
                </div>

                <div className="mt-4 pt-3.5 border-t border-neutral-100 flex items-center justify-between">
                  <span className="text-[9.5px] font-mono text-neutral-400 flex items-center gap-1">
                    <span className="material-symbols-outlined text-[13px]">insert_drive_file</span>
                    {agent.deliverables ? agent.deliverables.length : 0} Deliverables
                  </span>
                  
                  <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      onClick={(e) => handleOpenEdit(agent, e)}
                      className="p-1 hover:bg-neutral-100 text-neutral-500 hover:text-neutral-800 rounded-md transition-colors"
                      title="Edit settings"
                    >
                      <span className="material-symbols-outlined text-[16px]">edit</span>
                    </button>
                    <button
                      onClick={(e) => handleDelete(agent.id, e)}
                      className="p-1 hover:bg-red-50 text-red-500 hover:text-red-700 rounded-md transition-colors"
                      title="Delete agent"
                    >
                      <span className="material-symbols-outlined text-[16px]">delete</span>
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ----------------- CREATE/EDIT AGENT DIAOG MODAL ----------------- */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-neutral-900/40 backdrop-blur-xs flex items-center justify-center z-50 animate-fade-in p-4 select-none">
          <div className="bg-white rounded-xl shadow-lg border border-neutral-200 max-w-xl w-full max-h-[85vh] flex flex-col overflow-hidden">
            
            {/* Modal Header */}
            <div className="h-14 border-b border-neutral-100 px-5 flex items-center justify-between flex-shrink-0 bg-neutral-50/50">
              <h3 className="text-[12.5px] font-extrabold text-neutral-900 font-mono tracking-tight uppercase flex items-center gap-2">
                <span className="material-symbols-outlined text-[18px]">smart_toy</span>
                {modalMode === 'create' ? 'Create New AI Agent' : 'Edit Agent Settings'}
              </h3>
              <button
                onClick={() => setIsModalOpen(false)}
                className="p-1.5 hover:bg-neutral-200/70 text-neutral-400 hover:text-neutral-700 rounded-lg transition-colors"
              >
                <span className="material-symbols-outlined text-[18px]">close</span>
              </button>
            </div>

            {/* Modal Body */}
            <div className="flex-1 overflow-y-auto p-5 space-y-4 select-text">
              <div className="space-y-1">
                <label className="text-[10px] font-bold text-neutral-500 tracking-wider uppercase font-mono">Agent Name</label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Orchestration Dispatcher v2.0"
                  className="w-full px-3 py-2 text-xs border border-neutral-200 focus:outline-none focus:border-neutral-900 focus:ring-1 focus:ring-neutral-900/20 bg-neutral-50/50 rounded-lg font-mono"
                />
              </div>

              <div className="space-y-1">
                <label className="text-[10px] font-bold text-neutral-500 tracking-wider uppercase font-mono">Short Description</label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={2}
                  placeholder="Summarize the core execution task of this operational entity..."
                  className="w-full px-3 py-2 text-xs border border-neutral-200 focus:outline-none focus:border-neutral-900 focus:ring-1 focus:ring-neutral-900/20 bg-neutral-50/50 rounded-lg font-sans resize-none"
                />
              </div>

              <div className="space-y-1">
                <label className="text-[10px] font-bold text-neutral-500 tracking-wider uppercase font-mono">System Prompt / Markdown Document</label>
                <textarea
                  value={markdownDoc}
                  onChange={(e) => setMarkdownDoc(e.target.value)}
                  rows={6}
                  placeholder="Enter system prompt settings or specifications in standard markdown format..."
                  className="w-full px-3  py-2 border border-neutral-200 focus:outline-none focus:border-neutral-900 focus:ring-1 focus:ring-neutral-900/20 bg-neutral-50/30 rounded-lg font-mono text-[11px] leading-relaxed"
                />
              </div>

              {/* Deliverables Sub-form */}
              <div className="border-t border-neutral-150/65 pt-3.5 space-y-2">
                <label className="text-[10px] font-bold text-neutral-500 tracking-wider uppercase font-mono block">Configure Deliverables (Output Files)</label>
                
                {/* Addition fields */}
                <div className="bg-neutral-50/50 border border-neutral-200 p-3 rounded-xl space-y-2 flex flex-col justify-start">
                  <div className="grid grid-cols-3 gap-2">
                    <input
                      type="text"
                      placeholder="File name (e.g. results.json)"
                      value={newDelivName}
                      onChange={(e) => setNewDelivName(e.target.value)}
                      className="col-span-2 px-2 py-1.5 text-[11px] border border-neutral-200 focus:outline-none focus:border-neutral-900 focus:ring-1 focus:ring-neutral-900/20 bg-white rounded-md font-mono"
                    />
                    <button
                      type="button"
                      onClick={handleAddDeliverable}
                      className="px-2.5 py-1.5 bg-neutral-900 hover:bg-black text-white text-[10.5px] font-semibold rounded-md transition-colors"
                    >
                      + Add List Record
                    </button>
                  </div>
                  <textarea
                    placeholder="Enter file contents here..."
                    value={newDelivContent}
                    onChange={(e) => setNewDelivContent(e.target.value)}
                    rows={2}
                    className="w-full px-2 py-1.5 border border-neutral-200 focus:outline-none focus:border-neutral tracking-normal focus:ring-1 focus:ring-neutral-900/20 bg-white rounded-md font-mono text-[10px]"
                  />
                </div>

                {/* List items configured */}
                {deliverablesInput.length > 0 && (
                  <div className="space-y-1.5 pt-1.5 max-h-[148px] overflow-y-auto">
                    {deliverablesInput.map((deliv, index) => (
                      <div key={index} className="flex items-center justify-between p-2 border border-neutral-200/70 bg-white hover:bg-neutral-50/30 rounded-lg">
                        <div className="flex items-center gap-2 overflow-hidden">
                          <span className="material-symbols-outlined text-[16px] text-neutral-400 font-mono">insert_drive_file</span>
                          <span className="text-[11px] font-mono text-neutral-700 font-semibold truncate">{deliv.name}</span>
                        </div>
                        <button
                          type="button"
                          onClick={() => handleRemoveDeliverable(index)}
                          className="p-1 hover:bg-red-50 text-red-500 hover:text-red-700 rounded-md transition-colors"
                        >
                          <span className="material-symbols-outlined text-[15px]">close</span>
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Modal Actions */}
            <div className="h-14 border-t border-neutral-100 flex items-center justify-end px-5 gap-2.5 bg-neutral-50/30 flex-shrink-0">
              <button
                onClick={() => setIsModalOpen(false)}
                className="px-4 py-1.5 text-neutral-500 hover:text-neutral-800 hover:bg-neutral-100 border border-neutral-200 rounded-lg text-xs font-semibold transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                className="px-4 py-1.5 bg-[#f8f9fa] hover:bg-neutral-100/80 text-neutral-800 border border-neutral-250/70 rounded-lg text-xs font-bold transition-all shadow-2xs active:scale-97"
              >
                {modalMode === 'create' ? 'Create Entity' : 'Save Config'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ----------------- DELIVERABLE PREVIEW DIALOG MODAL ----------------- */}
      {isPreviewDeliverable && (
        <div className="fixed inset-0 bg-neutral-900/40 backdrop-blur-xs flex items-center justify-center z-50 animate-fade-in p-4 select-none">
          <div className="bg-white rounded-xl shadow-lg border border-neutral-200 max-w-2xl w-full max-h-[80vh] flex flex-col overflow-hidden">
            
            {/* Modal Header */}
            <div className="h-14 border-b border-neutral-100 px-5 flex items-center justify-between flex-shrink-0 bg-neutral-50/50">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-[17px] text-neutral-500 font-mono">
                  {isPreviewDeliverable.name.endsWith('.json') ? 'schema' : 'insert_drive_file'}
                </span>
                <span className="text-[11.5px] font-mono text-neutral-900 font-bold">{isPreviewDeliverable.name}</span>
              </div>
              <button
                onClick={() => setIsPreviewDeliverable(null)}
                className="p-1.5 hover:bg-neutral-200/70 text-neutral-400 hover:text-neutral-700 rounded-lg transition-colors"
              >
                <span className="material-symbols-outlined text-[18px]">close</span>
              </button>
            </div>

            {/* Modal Body: Code Display */}
            <div className="flex-1 overflow-auto p-5 select-text bg-[#FAF9F5] font-mono text-[11px] leading-relaxed border-b border-neutral-150">
              <div className="bg-neutral-950 text-neutral-200 p-5 rounded-xl border border-neutral-800 text-[11px] font-mono shadow-inner select-text max-w-full overflow-x-auto">
                <table className="w-full">
                  <tbody>
                    {isPreviewDeliverable.content.split('\n').map((line, idx) => (
                      <tr key={idx} className="hover:bg-neutral-900/60 leading-relaxed">
                        <td className="text-neutral-500 text-right pr-4 select-none w-8 border-r border-[#333333] text-[10px] font-semibold">{idx + 1}</td>
                        <td className="pl-4 whitespace-pre font-mono text-neutral-300">{line || ' '}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Modal Actions */}
            <div className="h-13 flex items-center justify-end px-5 gap-2 bg-neutral-50/30 flex-shrink-0">
              <button
                onClick={() => setIsPreviewDeliverable(null)}
                className="px-4 py-1.5 bg-[#f8f9fa] hover:bg-neutral-100/80 text-neutral-800 border border-neutral-250/70 rounded-lg text-[11px] font-bold transition-all shadow-2xs active:scale-97"
              >
                Dismiss View
              </button>
            </div>

          </div>
        </div>
      )}
    </div>
  );
}
