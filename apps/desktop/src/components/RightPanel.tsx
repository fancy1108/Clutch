import React from 'react';
import { RightTab, RunStatus, UncommittedFile } from '../types';
import { fileTreeNodes } from '../mockData';

export const getFullFileContent = (name: string): string => {
  switch (name) {
    case 'src/video-core/processor.ts':
      return `import { validate } from "./utils";\n\nexport async function processVideo(assets: string[]) {\n  console.info("Processing active video templates...");\n  const result = await validate(assets);\n  return result.status === 'ok';\n}`;
    case 'src/video-core/utils.ts':
      return `export function logExecutionStep(step: string) {\n  console.info(\`[ORCHESTRATION] [\${new Date().toLocaleTimeString()}] -> \${step}\`);\n}\n\nexport async function validate(assets: string[]) {\n  if (assets.length === 0) {\n    return { status: "error", reason: "empty_assets" };\n  }\n  return { status: "ok" };\n}`;
    case 'docs/verify.md':
      return `# 🤖 Librarian Protocol v2.0 (System Commander)\n\n## 📋 Operational Directives\n\nYou are currently the **Chief Auditor** of this knowledge base. When processing \`3_Resources/Wiki/raw/buffer/\`, you must strictly adhere to the following pipeline:\n\n### 1. Quarantine Rule\n\n- Check standard file formatting. If encrypted PDF, damaged markdown or large file exceeding 100k tokens is encountered, quarantine instantly to \`3_Resources/Wiki/raw/quarantine/\`.\n- Log failures within \`3_Resources/Wiki/meta/log.md\`.\n\n### 2. Claim-First Extraction\n\n- Prior to completing a summary, you must generate a corresponding \`Claim_[FileName].md\` inside \`3_Resources/Wiki/meta/claims/\`.\n- Every detail added to the Wiki must align to original citations.\n\n### 3. Logical Melting\n\n- **Concepts**: Place general theory in \`3_Resources/Wiki/pages/concepts/\`.\n- **Entities**: Place specific software in \`3_Resources/Wiki/pages/entities/\`.\n- Bidirectional metadata link density must exceed 2 links/paragraph.\n\n### 4. Chronological Archiving\n\n- Archive raw materials to \`3_Resources/Library/YYYY/MM/\`.\n- Rename standard files to \`YYYYMMDD_[FileName].md\`.\n\n## 🚫 Hard Constraints\n\n- Physical layer (Library/) forbids logical schema categorization.\n- Never modify raw input directory files directly.\n- Wiki search sources must point to the newest physical paths.`;
    default:
      return '';
  }
};

interface RightPanelProps {
  activeTab: RightTab;
  setActiveTab: (tab: RightTab) => void;
  runStatus: RunStatus;
  onReassign: () => void;
  uncommitted: UncommittedFile[];
  terminalLogs: string[];
  isOpen: boolean;
  setIsOpen: (val: boolean) => void;
  selectedSidebarWidth: number;
  rightSidebarWidth: number;
  onPreviewFile: (file: { name: string; content: string }) => void;
  isMultiAgent?: boolean;
}

export const RightPanel: React.FC<RightPanelProps> = ({
  activeTab,
  setActiveTab,
  runStatus,
  onReassign,
  uncommitted,
  terminalLogs,
  isOpen,
  setIsOpen,
  selectedSidebarWidth,
  rightSidebarWidth,
  onPreviewFile,
  isMultiAgent = true
}) => {
  const [selectedFile, setSelectedFile] = React.useState<string>('src/video-core/processor.ts');
  const [selectedAgentProfile, setSelectedAgentProfile] = React.useState<'orchestrator' | 'builder' | 'auditor'>('orchestrator');
  const [expandedFiles, setExpandedFiles] = React.useState<Record<string, boolean>>({
    'PARA': true,
    '.obsidian': false,
    '.claude': false
  });

  const toggleExpand = (dir: string) => {
    setExpandedFiles(prev => ({ ...prev, [dir]: !prev[dir] }));
  };

  const getActiveFileDiff = () => {
    const file = uncommitted.find(f => f.name === selectedFile);
    return file ? file.diffs : null;
  };

  return (
    <aside
      className={`fixed right-0 top-[64px] bottom-0 border-l border-outline-variant bg-white flex flex-col z-30 transition-all duration-300 ${
        isOpen ? 'w-[300px]' : 'w-[0px] border-l-0'
      }`}
      style={{ overflow: 'visible' }}
    >
      {/* Collapse Handle Button */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className={`absolute top-4 w-6 h-6 bg-white border border-neutral-300 rounded-full flex items-center justify-center z-50 shadow-md hover:shadow-lg hover:bg-neutral-50 hover:border-neutral-450 transition-all cursor-pointer text-neutral-600 hover:text-neutral-900 duration-200 hover:scale-110 active:scale-95 ${
          isOpen ? '-left-3' : '-left-6'
        }`}
        title={isOpen ? 'Collapse Panel' : 'Expand Panel'}
      >
        <span className="material-symbols-outlined text-[13px] font-bold">
          {isOpen ? 'chevron_right' : 'chevron_left'}
        </span>
      </button>

      {/* Main Content Area (Hidden when collapsed) */}
      <div className={`flex-grow flex flex-col h-full overflow-hidden ${!isOpen ? 'hidden' : ''}`}>
        {/* Tabs list */}
        <div className="flex border-b border-outline-variant overflow-x-auto sidebar-scroll select-none bg-surface-container-low/40">
          {(['overview', 'files', 'flow', 'changes', 'terminal'] as RightTab[])
            .filter(tab => isMultiAgent || tab !== 'flow')
            .map(tab => {
              const isActive = activeTab === tab;
              return (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`px-4 py-3 text-xs font-bold whitespace-nowrap tracking-wide capitalize transition-all ${
                    isActive
                      ? 'text-primary border-b-2 border-primary bg-white'
                      : 'text-on-surface-variant hover:text-on-surface'
                  }`}
                >
                  {tab}
                </button>
              );
            })}
        </div>

      {/* Tab Contents Area */}
      <div className="flex-1 overflow-y-auto sidebar-scroll p-5 select-none bg-white">
        
        {/* TAB 1: OVERVIEW */}
        {activeTab === 'overview' && (
          <div className="space-y-6 animate-fade-in text-xs">
            <section>
              <h4 className="text-[10px] font-bold text-on-surface-variant/75 uppercase tracking-widest mb-4">
                Session Token Analytics
              </h4>
              <div className="space-y-4">
                {/* Visual stats cards */}
                <div className="grid grid-cols-2 gap-3">
                  <div className="p-3 border border-neutral-200 bg-neutral-50/50 rounded-xl">
                    <p className="text-[9px] text-zinc-500 font-bold uppercase tracking-wider mb-1">Total Tokens</p>
                    <p className="text-base font-extrabold text-neutral-900 font-mono">52,480</p>
                    <p className="text-[8px] text-zinc-400 mt-0.5 font-medium">5.2% of 1M limit</p>
                  </div>
                  <div className="p-3 border border-neutral-200 bg-neutral-50/50 rounded-xl">
                    <p className="text-[9px] text-zinc-500 font-bold uppercase tracking-wider mb-1">Estimated Cost</p>
                    <p className="text-base font-extrabold text-neutral-900 font-mono">$0.0078</p>
                    <p className="text-[8px] text-emerald-600 mt-0.5 font-bold">100% Free Context</p>
                  </div>
                </div>

                {/* Horizontal Segmented Bar Chart */}
                <div className="p-3 border border-neutral-200 rounded-xl space-y-2">
                  <div className="flex items-center justify-between text-[10px] font-bold text-neutral-800">
                    <span>Token Distribution</span>
                    <span className="text-zinc-500 font-normal font-mono">Input vs Output</span>
                  </div>
                  
                  {/* Segmented Progress Bar */}
                  <div className="w-full h-3 rounded-full overflow-hidden flex bg-neutral-100 border border-neutral-200/50">
                    <div className="h-full bg-neutral-900 transition-all duration-300 hover:opacity-90" style={{ width: '82%' }} title="Input: 42,910 tokens (82%)" />
                    <div className="h-full bg-neutral-400 transition-all duration-300 hover:opacity-90" style={{ width: '18%' }} title="Output: 9,570 tokens (18%)" />
                  </div>

                  <div className="flex justify-between text-[9px] font-mono pt-1">
                    <div className="flex items-center gap-1.5 text-neutral-800">
                      <span className="w-1.5 h-1.5 rounded-full bg-neutral-900" />
                      <span>Input (82%): 42,910</span>
                    </div>
                    <div className="flex items-center gap-1.5 text-neutral-1000">
                      <span className="w-1.5 h-1.5 rounded-full bg-neutral-400" />
                      <span>Output (18%): 9,570</span>
                    </div>
                  </div>
                </div>

                {/* Simple Multi-Round Chart using structured interactive divs simulating bars */}
                <div className="p-3.5 border border-neutral-200 rounded-xl space-y-3">
                  <p className="text-[9.5px] font-bold uppercase tracking-wider text-neutral-800">Token Cost History</p>
                  
                  {/* Bar Chart Container */}
                  <div className="h-24 flex items-end gap-3 px-1.5 pt-4 border-b border-neutral-100">
                    {/* Round 1 */}
                    <div className="flex-1 flex flex-col items-center group cursor-pointer">
                      <div className="relative w-full flex flex-col justify-end h-16">
                        {/* Tooltip on hover */}
                        <div className="absolute -top-7 left-1/2 -translate-x-1/2 bg-neutral-800 text-white text-[8px] font-mono py-0.5 px-1 rounded opacity-0 group-hover:opacity-100 transition-opacity z-20 whitespace-nowrap shadow-xs">
                          12.4k
                        </div>
                        <div className="w-full bg-neutral-200 group-hover:bg-neutral-300 rounded-t-sm transition-all" style={{ height: '30%' }} />
                      </div>
                      <span className="text-[8px] font-bold text-neutral-400 mt-1.5 font-mono">R1</span>
                    </div>

                    {/* Round 2 */}
                    <div className="flex-1 flex flex-col items-center group cursor-pointer">
                      <div className="relative w-full flex flex-col justify-end h-16">
                        <div className="absolute -top-7 left-1/2 -translate-x-1/2 bg-neutral-800 text-white text-[8px] font-mono py-0.5 px-1 rounded opacity-0 group-hover:opacity-100 transition-opacity z-20 whitespace-nowrap shadow-xs">
                          15.6k
                        </div>
                        <div className="w-full bg-neutral-300 group-hover:bg-neutral-400 rounded-t-sm transition-all" style={{ height: '45%' }} />
                      </div>
                      <span className="text-[8px] font-bold text-neutral-400 mt-1.5 font-mono">R2</span>
                    </div>

                    {/* Round 3 (Active) */}
                    <div className="flex-1 flex flex-col items-center group cursor-pointer">
                      <div className="relative w-full flex flex-col justify-end h-16">
                        <div className="absolute -top-7 left-1/2 -translate-x-1/2 bg-neutral-800 text-white text-[8px] font-mono py-0.5 px-1 rounded opacity-0 group-hover:opacity-100 transition-opacity z-20 whitespace-nowrap shadow-xs">
                          24.4k
                        </div>
                        <div className="w-full bg-neutral-900 group-hover:bg-black rounded-t-sm transition-all animate-pulse" style={{ height: '75%' }} />
                      </div>
                      <span className="text-[8px] font-bold text-neutral-800 mt-1.5 font-mono">Active</span>
                    </div>
                  </div>

                  <div className="flex items-center justify-between text-[9px] text-zinc-400 font-medium">
                    <span>3 Execution Cycles</span>
                    <span className="text-zinc-500 font-bold">&#8901; Avg 17.4k / run</span>
                  </div>
                </div>

              </div>
            </section>

            {/* Active section depending on isMultiAgent mode */}
            {isMultiAgent ? (
              <section>
                <h4 className="text-[10px] font-bold text-on-surface-variant/75 uppercase tracking-widest mb-3">
                  Active Flow Workflow
                </h4>
                <div className="space-y-0 flex flex-col items-center">
                  
                  {/* Orchestrator node */}
                  <div className="flex flex-col items-center w-full">
                    <div className="flex items-center gap-3 w-full bg-surface p-2.5 rounded-xl border border-outline-variant/30">
                      <div className="w-9 h-9 rounded-full bg-surface-container border-2 border-white flex items-center justify-center shadow-xs overflow-hidden flex-shrink-0">
                        <img className="w-full h-full object-cover" src="https://lh3.googleusercontent.com/aida-public/AB6AXuA0yGh59QNLj5n0igNxMgu4lgaiNqZpcN29SpWM0JHNlAuFmOBx-Id67Zcd2NDCNBjBKrcffQrdrfoe-3XaSlveekLAP9SRis93uTk7XPPFO5y4Swos7NvATw6n7eZEm7nfAQuTiMAoWRSnxefAOJugUbZx3fCTNv4jGyjvT-UZznwKzp_HoXuStup_0juhBCZYamrV0Coil-k27d9Yi7il6NabIEG0FfbxwL5V5azpfZQOlBfpaganta2kP7n59BKPHd4K2uTOfZ5p" alt="Orchestrator" />
                      </div>
                      <div>
                        <p className="text-[11px] font-bold text-on-surface">Orchestrator</p>
                        <p className="text-[10px] text-green-600 font-medium font-mono">Completed</p>
                      </div>
                    </div>
                    <div className="h-4 flex flex-col items-center justify-center">
                      <div className="w-0.5 h-full bg-outline-variant/60 relative flex justify-center">
                        <span className="material-symbols-outlined absolute -bottom-2 text-[14px] text-on-surface-variant/60">arrow_drop_down</span>
                      </div>
                    </div>
                  </div>

                  {/* Builder node */}
                  <div className="flex flex-col items-center w-full">
                    <div className="flex items-center gap-3 w-full bg-surface p-2.5 rounded-xl border border-outline-variant/30">
                      <div className="w-9 h-9 rounded-full bg-surface-container border-2 border-white flex items-center justify-center shadow-xs overflow-hidden flex-shrink-0">
                        <img className="w-full h-full object-cover" src="https://lh3.googleusercontent.com/aida-public/AB6AXuBpRidttSGTIY-J-PGvnlcZX_oZSZoBXJY5vjZ9g1PKl_fq4EKoa2RXbcSCvvIdbPLdmfuzPKTxnR8TqV7skwsKlt-eKEzSzktv-TWbHu4c9uBEdP6Es_Fjek1EBQuGZeMtWsUi3fn0lyozFaZBLp9SpES3r0WalbqYY6gGiT1R_0J1kvU-D9rI_2q2f3sMGHuTjWyOZ5gImCLGHSGejtcKmToTSZYMrXfT_A5x1iw_f4q7WljP3FXjk64aQhLgh9nTXUDfPdkIzu0b" alt="Builder" />
                      </div>
                      <div>
                        <p className="text-[11px] font-bold text-on-surface">Builder</p>
                        <p className="text-[10px] text-green-600 font-medium font-mono">Completed</p>
                      </div>
                    </div>
                    <div className="h-4 flex flex-col items-center justify-center">
                      <div className="w-0.5 h-full bg-outline-variant/60 relative flex justify-center">
                        <span className="material-symbols-outlined absolute -bottom-2 text-[14px] text-on-surface-variant/60">arrow_drop_down</span>
                      </div>
                    </div>
                  </div>

                  {/* Evaluator node */}
                  <div className="flex flex-col items-center w-full">
                    <div className="flex items-center gap-3 w-full bg-surface p-2.5 rounded-xl border border-outline-variant/30">
                      <div className={`w-9 h-9 rounded-full border-2 border-white flex items-center justify-center shadow-xs overflow-hidden flex-shrink-0 ${runStatus === 'passed' ? 'bg-green-600' : 'bg-error-red'}`}>
                        <img className="w-full h-full object-cover" src="https://lh3.googleusercontent.com/aida-public/AB6AXuCmb7VGaQXE-4sYnIZR3VrcHVAPhv4Px14kMlkayJj8kVm8htTWITmPi26wsj8P6B9RrqykIWj81S2ilmGR0e8cXhA1gjc3U-Nw0DsgHV3HvVmBskuoUksIt6YM6Z3ORjFtRhBphqAXxRKf9ke-zYcPs0TcEFKxw_bwGXSDiAKV5CL7kZf9i6lSZDe91ccUNjaAIsgTMKEEvYc7bZpXYz3D5dClulRwbNru5SZB-1E5FM0A2qMPs-IAfiR8OB1-cUvFh3WYKx9qlGgN" alt="Evaluator" />
                      </div>
                      <div>
                        <p className="text-[11px] font-bold text-on-surface">Evaluator</p>
                        <p className={`text-[10px] font-bold font-mono ${runStatus === 'passed' ? 'text-green-600' : 'text-error-red'}`}>
                          {runStatus === 'passed' ? 'Passed' : 'Failed'}
                        </p>
                      </div>
                    </div>
                    {runStatus !== 'passed' && (
                      <div className="h-4 flex flex-col items-center justify-center">
                        <div className="w-0.5 h-full bg-outline-variant/60 relative flex justify-center">
                          <span className="material-symbols-outlined absolute -bottom-2 text-[14px] text-on-surface-variant/60">arrow_drop_down</span>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Builder running node shown when failing */}
                  {runStatus !== 'passed' && (
                    <div className="flex flex-col items-center w-full">
                      <div className="flex items-center gap-3 w-full bg-white p-2.5 rounded-xl border-2 border-primary shadow-xs">
                        <div className="w-9 h-9 rounded-full bg-surface-container border-2 border-primary flex items-center justify-center shadow-xs overflow-hidden flex-shrink-0 animate-pulse">
                          <img className="w-full h-full object-cover" src="https://lh3.googleusercontent.com/aida-public/AB6AXuBpRidttSGTIY-J-PGvnlcZX_oZSZoBXJY5vjZ9g1PKl_fq4EKoa2RXbcSCvvIdbPLdmfuzPKTxnR8TqV7skwsKlt-eKEzSzktv-TWbHu4c9uBEdP6Es_Fjek1EBQuGZeMtWsUi3fn0lyozFaZBLp9SpES3r0WalbqYY6gGiT1R_0J1kvU-D9rI_2q2f3sMGHuTjWyOZ5gImCLGHSGejtcKmToTSZYMrXfT_A5x1iw_f4q7WljP3FXjk64aQhLgh9nTXUDfPdkIzu0b" alt="Builder" />
                        </div>
                        <div>
                          <p className="text-[11px] font-bold text-on-surface">Builder</p>
                          <p className="text-[10px] text-primary font-bold animate-pulse font-mono">Running Round 2...</p>
                        </div>
                      </div>
                    </div>
                  )}

                </div>
              </section>
            ) : (
              /* Selected Agent Introduction profile for Single Agent mode */
              <section className="space-y-4">
                <div className="flex items-center justify-between">
                  <h4 className="text-[10px] font-bold text-on-surface-variant/75 uppercase tracking-widest">
                    Selected AI Agent
                  </h4>
                  <div className="flex gap-1.5">
                    <button
                      onClick={() => setSelectedAgentProfile('orchestrator')}
                      className={`px-2 py-1 rounded text-[10px] font-bold transition-all cursor-pointer border ${
                        selectedAgentProfile === 'orchestrator'
                          ? 'bg-neutral-900 border-neutral-900 text-white'
                          : 'bg-white border-neutral-200 text-neutral-500 hover:text-neutral-800'
                      }`}
                    >
                      Orchestrator
                    </button>
                    <button
                      onClick={() => setSelectedAgentProfile('builder')}
                      className={`px-2 py-1 rounded text-[10px] font-bold transition-all cursor-pointer border ${
                        selectedAgentProfile === 'builder'
                          ? 'bg-neutral-900 border-neutral-900 text-white'
                          : 'bg-white border-neutral-200 text-neutral-500 hover:text-neutral-800'
                      }`}
                    >
                      Builder
                    </button>
                    <button
                      onClick={() => setSelectedAgentProfile('auditor')}
                      className={`px-2 py-1 rounded text-[10px] font-bold transition-all cursor-pointer border ${
                        selectedAgentProfile === 'auditor'
                          ? 'bg-neutral-900 border-neutral-900 text-white'
                          : 'bg-white border-neutral-200 text-neutral-500 hover:text-neutral-800'
                      }`}
                    >
                      Auditor
                    </button>
                  </div>
                </div>

                {selectedAgentProfile === 'orchestrator' && (
                  <div className="p-4 bg-neutral-50/50 rounded-2xl border border-neutral-200/80 space-y-3.5 animate-fade-in">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full border border-neutral-250/20 overflow-hidden bg-neutral-100 flex-shrink-0">
                        <img className="w-full h-full object-cover" src="https://lh3.googleusercontent.com/aida-public/AB6AXuA0yGh59QNLj5n0igNxMgu4lgaiNqZpcN29SpWM0JHNlAuFmOBx-Id67Zcd2NDCNBjBKrcffQrdrfoe-3XaSlveekLAP9SRis93uTk7XPPFO5y4Swos7NvATw6n7eZEm7nfAQuTiMAoWRSnxefAOJugUbZx3fCTNv4jGyjvT-UZznwKzp_HoXuStup_0juhBCZYamrV0Coil-k27d9Yi7il6NabIEG0FfbxwL5V5azpfZQOlBfpaganta2kP7n59BKPHd4K2uTOfZ5p" alt="Orchestrator" />
                      </div>
                      <div>
                        <h5 className="text-[12px] font-bold text-neutral-800">Orchestrator Module (VobeSOP v2)</h5>
                        <p className="text-[10px] text-green-600 font-bold font-mono">Status: Active & Ready</p>
                      </div>
                    </div>
                    <p className="text-[11px] text-neutral-500 leading-relaxed font-medium">
                      Parses core instruction guidelines, establishes clean project file trees, and acts as the central coordinator for all requested file edits.
                    </p>
                    <div className="space-y-1.5 pt-1.5 border-t border-neutral-200/50">
                      <p className="text-[9px] font-bold text-neutral-400 uppercase tracking-wider">Key Directives</p>
                      <ul className="space-y-1 text-neutral-600 font-medium list-disc pl-4 text-[11px]">
                        <li><strong className="text-neutral-800">Context Triage</strong>: Constantly evaluates changes in project files.</li>
                        <li><strong className="text-neutral-800">Plan Generator</strong>: Crafts highly targeted work sequences.</li>
                        <li><strong className="text-neutral-800">Quality Gatekeeper</strong>: Locks down features to exact guidelines.</li>
                      </ul>
                    </div>
                  </div>
                )}

                {selectedAgentProfile === 'builder' && (
                  <div className="p-4 bg-neutral-50/50 rounded-2xl border border-neutral-200/80 space-y-3.5 animate-fade-in">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full border border-neutral-250/20 overflow-hidden bg-neutral-100 flex-shrink-0">
                        <img className="w-full h-full object-cover" src="https://lh3.googleusercontent.com/aida-public/AB6AXuBpRidttSGTIY-J-PGvnlcZX_oZSZoBXJY5vjZ9g1PKl_fq4EKoa2RXbcSCvvIdbPLdmfuzPKTxnR8TqV7skwsKlt-eKEzSzktv-TWbHu4c9uBEdP6Es_Fjek1EBQuGZeMtWsUi3fn0lyozFaZBLp9SpES3r0WalbqYY6gGiT1R_0J1kvU-D9rI_2q2f3sMGHuTjWyOZ5gImCLGHSGejtcKmToTSZYMrXfT_A5x1iw_f4q7WljP3FXjk64aQhLgh9nTXUDfPdkIzu0b" alt="Builder" />
                      </div>
                      <div>
                        <h5 className="text-[12px] font-bold text-neutral-800">Builder Module (JSX)</h5>
                        <p className="text-[10px] text-zinc-500 font-bold font-mono">Status: Idle</p>
                      </div>
                    </div>
                    <p className="text-[11px] text-neutral-500 leading-relaxed font-medium">
                      An execution engine optimized for generating pixel-perfect responsive Tailwind layouts, implementing robust states, and compiling flawless React components.
                    </p>
                    <div className="space-y-1.5 pt-1.5 border-t border-neutral-200/50">
                      <p className="text-[9px] font-bold text-neutral-400 uppercase tracking-wider">Key Directives</p>
                      <ul className="space-y-1 text-neutral-600 font-medium list-disc pl-4 text-[11px]">
                        <li><strong className="text-neutral-800">Responsive Designs</strong>: Mobile-first precision scaling.</li>
                        <li><strong className="text-neutral-800">Type-Safe States</strong>: Clean components without loops.</li>
                        <li><strong className="text-neutral-800">Inlined Utilities</strong>: Efficient use of pre-bundled helpers.</li>
                      </ul>
                    </div>
                  </div>
                )}

                {selectedAgentProfile === 'auditor' && (
                  <div className="p-4 bg-neutral-50/50 rounded-2xl border border-neutral-200/80 space-y-3.5 animate-fade-in">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full border border-neutral-250/20 overflow-hidden bg-neutral-100 flex-shrink-0">
                        <img className="w-full h-full object-cover" src="https://lh3.googleusercontent.com/aida-public/AB6AXuCmb7VGaQXE-4sYnIZR3VrcHVAPhv4Px14kMlkayJj8kVm8htTWITmPi26wsj8P6B9RrqykIWj81S2ilmGR0e8cXhA1gjc3U-Nw0DsgHV3HvVmBskuoUksIt6YM6Z3ORjFtRhBphqAXxRKf9ke-zYcPs0TcEFKxw_bwGXSDiAKV5CL7kZf9i6lSZDe91ccUNjaAIsgTMKEEvYc7bZpXYz3D5dClulRwbNru5SZB-1E5FM0A2qMPs-IAfiR8OB1-cUvFh3WYKx9qlGgN" alt="Auditor" />
                      </div>
                      <div>
                        <h5 className="text-[12px] font-bold text-neutral-800">Auditor Agent (Pipeline Compliance)</h5>
                        <p className="text-[10px] text-zinc-500 font-bold font-mono">Status: Idle</p>
                      </div>
                    </div>
                    <p className="text-[11px] text-neutral-500 leading-relaxed font-medium">
                      Runs quality checklist verification routines, performs structural layout evaluations, and guards context consistency across user inputs.
                    </p>
                    <div className="space-y-1.5 pt-1.5 border-t border-neutral-200/50">
                      <p className="text-[9px] font-bold text-neutral-400 uppercase tracking-wider">Key Directives</p>
                      <ul className="space-y-1 text-neutral-600 font-medium list-disc pl-4 text-[11px]">
                        <li><strong className="text-neutral-800">Quarantine Checks</strong>: Removes raw or oversized logs.</li>
                        <li><strong className="text-neutral-800">Claim Constraints</strong>: Syncs visual outputs to original files.</li>
                        <li><strong className="text-neutral-800">Bidirectional Links</strong>: Binds structural items reliably.</li>
                      </ul>
                    </div>
                  </div>
                )}
              </section>
            )}
          </div>
        )}

        {/* TAB 2: FILES TREE DUMP */}
        {activeTab === 'files' && (
          <div className="space-y-4 animate-fade-in text-xs select-none">
            <h4 className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest mb-3">
              Workspace Folder Structure
            </h4>
            
            <div className="space-y-1 font-mono font-medium text-xs text-on-surface-variant pl-1">
              {fileTreeNodes.map(node => {
                const isFolder = node.type === 'folder';
                const isExpanded = expandedFiles[node.name];

                return (
                  <div key={node.name} className="space-y-1">
                    <div
                      onClick={() => isFolder ? toggleExpand(node.name) : onPreviewFile({ name: node.name, content: (node as any).content || '' })}
                      className="flex items-center gap-2 p-1.5 hover:bg-surface-container-low rounded cursor-pointer transition-colors"
                    >
                      {isFolder ? (
                        <>
                          <span className={`material-symbols-outlined text-[16px] transition-transform ${isExpanded ? 'rotate-90' : ''}`}>
                            chevron_right
                          </span>
                          <span className="material-symbols-outlined text-[16px] text-on-surface-variant">
                            {isExpanded ? 'folder_open' : 'folder'}
                          </span>
                        </>
                      ) : (
                        <>
                          <span className="w-4" />
                          <span className="material-symbols-outlined text-[16px] text-on-surface-variant">
                            description
                          </span>
                        </>
                      )}
                      <span className={!isFolder ? "hover:text-primary transition-colors cursor-pointer" : ""}>{node.name}</span>
                    </div>

                    {isFolder && isExpanded && node.children && node.children.length > 0 && (
                      <div className="ml-4 pl-3 border-l border-outline-variant/30 space-y-1">
                        {node.children.map(child => (
                          <div
                            key={child.name}
                            onClick={() => {
                              onPreviewFile({ name: child.name, content: child.content || '' });
                            }}
                            className="flex items-center gap-2 p-1.5 hover:bg-surface-container-low rounded cursor-pointer transition-colors text-on-surface-variant"
                          >
                            <span className="material-symbols-outlined text-[16px] text-on-surface-variant/70">
                              description
                            </span>
                            <span className="hover:text-primary font-light text-[11px] truncate">{child.name}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* TAB 3: FLOW RETRY TIMELINE */}
        {activeTab === 'flow' && (
          <div className="space-y-5 animate-fade-in text-xs select-none">
            <h4 className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest mb-3">
              Agent Workflow Step Execution
            </h4>

            {/* Minimalistic Interactive Horizontal Node Link Flow */}
            <div className="py-6 px-3 bg-slate-50/70 border border-outline-variant/30 rounded-2xl flex flex-col items-center">
              
              <div className="relative w-full flex items-center justify-between max-w-[310px] min-h-[90px] mb-2">
                {/* SVG Connector Layer behind nodes */}
                <svg className="absolute inset-0 w-full h-[60px] pointer-events-none" style={{ zIndex: 0 }}>
                  <defs>
                    <marker
                      id="mini-arrow"
                      viewBox="0 0 10 10"
                      refX="8"
                      refY="5"
                      markerWidth="5"
                      markerHeight="5"
                      orient="auto-start-reverse"
                    >
                      <path d="M 0 1.5 L 7 5 L 0 8.5 z" fill="#cbd5e1" />
                    </marker>
                    <marker
                      id="mini-arrow-active"
                      viewBox="0 0 10 10"
                      refX="8"
                      refY="5"
                      markerWidth="5"
                      markerHeight="5"
                      orient="auto-start-reverse"
                    >
                      <path d="M 0 1.5 L 7 5 L 0 8.5 z" fill="#000000" />
                    </marker>
                    <marker
                      id="mini-arrow-stuck"
                      viewBox="0 0 10 10"
                      refX="8"
                      refY="5"
                      markerWidth="5"
                      markerHeight="5"
                      orient="auto-start-reverse"
                    >
                      <path d="M 0 1.5 L 7 5 L 0 8.5 z" fill="#71717a" />
                    </marker>
                  </defs>

                  {/* Line 1: Orchestrator -> Builder */}
                  <path
                    d="M 68 28 L 105 28"
                    fill="none"
                    stroke={runStatus === 'running' || runStatus === 'passed' ? '#000000' : '#cbd5e1'}
                    strokeWidth="1.5"
                    markerEnd={runStatus === 'running' || runStatus === 'passed' ? 'url(#mini-arrow-active)' : 'url(#mini-arrow)'}
                    strokeDasharray={runStatus === 'running' ? "4 3" : "none"}
                    className={runStatus === 'running' ? "animate-shimmer" : ""}
                  />

                  {/* Line 2: Builder -> Evaluator */}
                  <path
                    d="M 172 28 L 210 28"
                    fill="none"
                    stroke={runStatus === 'passed' ? '#000000' : runStatus === 'failed' ? '#71717a' : '#cbd5e1'}
                    strokeWidth="1.5"
                    markerEnd={runStatus === 'passed' ? 'url(#mini-arrow-active)' : runStatus === 'failed' ? 'url(#mini-arrow-stuck)' : 'url(#mini-arrow)'}
                  />
                </svg>

                {/* Node 1: Orchestrator */}
                <div className="flex flex-col items-center w-[76px] relative z-10">
                  <div className="w-[44px] h-[44px] bg-white border border-green-200 rounded-xl flex items-center justify-center shadow-xs relative hover:border-green-300 transition-all">
                    <img
                      className="w-8 h-8 rounded-lg object-cover"
                      src="https://lh3.googleusercontent.com/aida-public/AB6AXuA0yGh59QNLj5n0igNxMgu4lgaiNqZpcN29SpWM0JHNlAuFmOBx-Id67Zcd2NDCNBjBKrcffQrdrfoe-3XaSlveekLAP9SRis93uTk7XPPFO5y4Swos7NvATw6n7eZEm7nfAQuTiMAoWRSnxefAOJugUbZx3fCTNv4jGyjvT-UZznwKzp_HoXuStup_0juhBCZYamrV0Coil-k27d9Yi7il6NabIEG0FfbxwL5V5azpfZQOlBfpaganta2kP7n59BKPHd4K2uTOfZ5p"
                      alt="Orchestrator"
                    />
                    <span className="absolute -bottom-1 -right-1 w-4 h-4 bg-green-500 rounded-full border border-white flex items-center justify-center text-white shadow-xs">
                      <span className="material-symbols-outlined text-[10px] font-extrabold">check</span>
                    </span>
                  </div>
                  <span className="text-[10px] font-bold text-slate-700 mt-2 text-center truncate w-full">Orchestrator</span>
                  <span className="text-[8px] text-green-600 font-bold tracking-wide mt-0.5">Assigned</span>
                </div>

                {/* Node 2: Builder */}
                <div className="flex flex-col items-center w-[76px] relative z-10">
                  <div className={`w-[44px] h-[44px] bg-white rounded-xl flex items-center justify-center shadow-xs relative transition-all border ${
                    runStatus === 'running'
                      ? 'border-neutral-900 ring-2 ring-neutral-100 animate-pulse'
                      : runStatus === 'failed'
                      ? 'border-neutral-400 ring-2 ring-neutral-100'
                      : 'border-neutral-300'
                  }`}>
                    <img
                      className="w-8 h-8 rounded-lg object-cover"
                      src="https://lh3.googleusercontent.com/aida-public/AB6AXuBpRidttSGTIY-J-PGvnlcZX_oZSZoBXJY5vjZ9g1PKl_fq4EKoa2RXbcSCvvIdbPLdmfuzPKTxnR8TqV7skwsKlt-eKEzSzktv-TWbHu4c9uBEdP6Es_Fjek1EBQuGZeMtWsUi3fn0lyozFaZBLp9SpES3r0WalbqYY6gGiT1R_0J1kvU-D9rI_2q2f3sMGHuTjWyOZ5gImCLGHSGejtcKmToTSZYMrXfT_A5x1iw_f4q7WljP3FXjk64aQhLgh9nTXUDfPdkIzu0b"
                      alt="Builder"
                    />
                    {runStatus === 'running' && (
                      <span className="absolute -bottom-1 -right-1 w-4 h-4 bg-black rounded-full border border-white flex items-center justify-center text-white shadow-xs">
                        <span className="material-symbols-outlined text-[10px] animate-spin">progress_activity</span>
                      </span>
                    )}
                    {runStatus === 'failed' && (
                      <span className="absolute -bottom-1 -right-1 w-4 h-4 bg-neutral-500 rounded-full border border-white flex items-center justify-center text-white shadow-xs text-[9px] font-bold">
                        !
                      </span>
                    )}
                    {runStatus === 'passed' && (
                      <span className="absolute -bottom-1 -right-1 w-4 h-4 bg-black rounded-full border border-white flex items-center justify-center text-white shadow-xs">
                        <span className="material-symbols-outlined text-[10px] font-extrabold">check</span>
                      </span>
                    )}
                  </div>
                  <span className="text-[10px] font-bold text-slate-700 mt-2 text-center truncate w-full">Builder</span>
                  {runStatus === 'running' ? (
                    <span className="text-[8px] text-neutral-800 font-bold tracking-wide mt-0.5 animate-pulse">Running</span>
                  ) : runStatus === 'failed' ? (
                    <span className="text-[8px] text-neutral-500 font-extrabold tracking-wide mt-0.5 bg-neutral-50 px-1 rounded animate-pulse">Stuck here</span>
                  ) : (
                    <span className="text-[8px] text-neutral-600 font-bold tracking-wide mt-0.5">Committed</span>
                  )}
                </div>

                {/* Node 3: Evaluator */}
                <div className="flex flex-col items-center w-[76px] relative z-10">
                  <div className={`w-[44px] h-[44px] bg-white border rounded-xl flex items-center justify-center shadow-xs relative transition-all ${
                    runStatus === 'passed' ? 'border-neutral-900 ring-2 ring-neutral-100' : 'border-neutral-200 brightness-95 opacity-70'
                  }`}>
                    <img
                      className="w-8 h-8 rounded-lg object-cover"
                      src="https://lh3.googleusercontent.com/aida-public/AB6AXuCmb7VGaQXE-4sYnIZR3VrcHVAPhv4Px14kMlkayJj8kVm8htTWITmPi26wsj8P6B9RrqykIWj81S2ilmGR0e8cXhA1gjc3U-Nw0DsgHV3HvVmBskuoUksIt6YM6Z3ORjFtRhBphqAXxRKf9ke-zYcPs0TcEFKxw_bwGXSDiAKV5CL7kZf9i6lSZDe91ccUNjaAIsgTMKEEvYc7bZpXYz3D5dClulRwbNru5SZB-1E5FM0A2qMPs-IAfiR8OB1-cUvFh3WYKx9qlGgN"
                      alt="Evaluator"
                    />
                    {runStatus === 'passed' && (
                      <span className="absolute -bottom-1 -right-1 w-4 h-4 bg-black rounded-full border border-white flex items-center justify-center text-white shadow-xs">
                        <span className="material-symbols-outlined text-[10px] font-extrabold">check</span>
                      </span>
                    )}
                  </div>
                  <span className="text-[10px] font-bold text-slate-700 mt-2 text-center truncate w-full">Evaluator</span>
                  <span className="text-[8px] text-slate-400 font-bold tracking-wide mt-0.5">
                    {runStatus === 'passed' ? 'Success' : 'Pending'}
                  </span>
                </div>
              </div>

              {/* Precise details of currently stuck or active element */}
              <div className="w-full mt-3 pt-3 border-t border-slate-200/50 flex flex-col gap-1.5 text-center px-1">
                {runStatus === 'failed' && (
                  <>
                    <p className="text-[10px] font-extrabold text-neutral-800 uppercase tracking-widest flex items-center justify-center gap-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-neutral-600 animate-ping" />
                      BLOCKING STAGE REACHED
                    </p>
                    <p className="text-[10px] text-zinc-600 leading-normal">
                      The workflow loop has returned here. Address files using target actions above.
                    </p>
                  </>
                )}
                {runStatus === 'running' && (
                  <>
                    <p className="text-[10px] font-extrabold text-neutral-900 uppercase tracking-widest flex items-center justify-center gap-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-black animate-ping" />
                      COMPILATION ROUTINE ACTIVE
                    </p>
                    <p className="text-[10px] text-zinc-600 leading-normal animate-pulse">
                      Analyzing workspace reports, generating missing directories.
                    </p>
                  </>
                )}
                {runStatus === 'passed' && (
                  <>
                    <p className="text-[10px] font-extrabold text-black uppercase tracking-widest flex items-center justify-center gap-1">
                      ALL CHECKLISTS PASSED
                    </p>
                    <p className="text-[10px] text-zinc-600 leading-normal">
                      Workspace complies with specification requirements.
                    </p>
                  </>
                )}
              </div>
            </div>

            {/* Loop progress details */}
            <div className="p-3 bg-surface-container-low rounded-xl border border-outline-variant/30 relative shadow-xs">
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-[9px] font-bold text-on-surface-variant uppercase">Retry Loop Status</span>
                <span className="text-[9px] font-extrabold text-primary font-mono bg-primary/5 px-1.5 py-0.5 rounded">
                  {runStatus === 'passed' ? 'Pass (3/3)' : 'Round 2/3'}
                </span>
              </div>
              <div className="w-full bg-surface-container-highest h-1 rounded-full overflow-hidden">
                <div
                  className="bg-primary h-full transition-all duration-500"
                  style={{ width: runStatus === 'passed' ? '100%' : '66.6%' }}
                />
              </div>
            </div>
          </div>
        )}

        {/* TAB 4: UNCOMMITTED CHANGES DIFFS */}
        {activeTab === 'changes' && (
          <div className="space-y-4 animate-fade-in text-xs select-none">
            <div className="flex items-center justify-between">
              <h4 className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">
                Uncommitted Changes ({runStatus === 'passed' ? '0' : uncommitted.length})
              </h4>
              <span className="material-symbols-outlined text-[18px] text-on-surface-variant/70 cursor-pointer hover:text-primary">
                more_horiz
              </span>
            </div>

            {runStatus === 'passed' ? (
              <div className="py-8 text-center bg-surface-container-low/40 rounded-xl border border-dashed border-outline-variant mt-2 text-on-surface-variant/60">
                <span className="material-symbols-outlined text-[28px] mb-2">done_all</span>
                <p className="text-[11px] font-medium">All changes successfully committed</p>
              </div>
            ) : (
              <div className="space-y-1">
                {uncommitted.map(file => {
                  const isActive = file.name === selectedFile;
                  return (
                    <div
                      key={file.name}
                      onClick={() => setSelectedFile(file.name)}
                      className={`flex items-center justify-between p-2 rounded-lg transition-colors cursor-pointer group ${
                        isActive
                          ? 'bg-surface-container-low border border-outline-variant/30 font-bold'
                          : 'hover:bg-surface-container-low'
                      }`}
                    >
                      <div className="flex items-center gap-3 overflow-hidden">
                        <span
                          className={`text-[10px] font-bold w-4 text-center ${
                            file.status === 'A' ? 'text-green-500' : 'text-amber-500'
                          }`}
                        >
                          {file.status}
                        </span>
                        <span className="text-xs truncate text-on-surface">{file.name}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onPreviewFile({ name: file.name, content: getFullFileContent(file.name) });
                          }}
                          className="p-1 hover:bg-neutral-100 rounded text-neutral-500 hover:text-black transition-colors"
                          title="Preview full file"
                        >
                          <span className="material-symbols-outlined text-[15px]">visibility</span>
                        </button>
                        <span className="material-symbols-outlined text-[16px] opacity-0 group-hover:opacity-100 transition-opacity">
                          history
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {/* Diff Viewer representation */}
            {runStatus !== 'passed' && getActiveFileDiff() && (
              <div className="mt-6 border border-outline-variant/20 rounded-xl overflow-hidden bg-white shadow-xs">
                <div className="flex items-center justify-between px-3 py-2 bg-surface-container/30 border-b border-outline-variant/20">
                  <div className="flex items-center gap-2">
                    <span className="material-symbols-outlined text-[14px]">description</span>
                    <span className="font-mono text-[10px] font-bold text-on-surface-variant/90 truncate max-w-[140px]">{selectedFile}</span>
                  </div>
                  <button
                    onClick={() => onPreviewFile({ name: selectedFile, content: getFullFileContent(selectedFile) })}
                    className="flex items-center gap-1.5 px-2 py-1 bg-neutral-900 hover:bg-black text-white text-[9.5px] font-bold rounded-lg transition-all shadow-xs active:scale-95"
                  >
                    <span className="material-symbols-outlined text-[12px]">visibility</span>
                    Preview Full
                  </button>
                </div>
                
                <div className="font-mono text-[9px] leading-relaxed bg-white overflow-hidden text-on-surface select-text">
                  {getActiveFileDiff()?.map((diffLine, i) => {
                    let bgClass = '';
                    let indicator = ' ';
                    
                    if (diffLine.type === 'addition') {
                      bgClass = 'bg-green-50 text-green-800';
                      indicator = '+';
                    } else if (diffLine.type === 'deletion') {
                      bgClass = 'bg-red-50 text-red-800 line-through';
                      indicator = '-';
                    }

                    return (
                      <div key={i} className={`flex ${bgClass}`}>
                        <div className="w-7 pb-0.5 text-center text-[8px] text-on-surface-variant/40 border-r border-outline-variant/10 select-none bg-surface-container/20">
                          {diffLine.lineNum}
                        </div>
                        <div className="px-3 pb-0.5 select-all whitespace-pre tracking-wide">
                          {indicator} {diffLine.text}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        )}

        {/* TAB 5: COMPILER/INTEGRATION TERMINAL LOGS */}
        {activeTab === 'terminal' && (
          <div className="space-y-4 animate-fade-in h-full flex flex-col text-xs">
            <div className="flex items-center justify-between">
              <h4 className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">
                Automated Container Console
              </h4>
              <button
                onClick={() => alert("Terminal clears and restarts outputs logs.")}
                className="text-[9px] font-semibold text-on-surface bg-surface-container-high px-2 py-1 rounded"
              >
                Clear
              </button>
            </div>

            {/* Black monospace logs terminal container */}
            <div className="flex-1 bg-black text-green-400 font-mono text-[10px] p-4 rounded-xl space-y-1.5 h-[340px] overflow-y-auto terminal-scroll select-all border border-neutral-800 shadow-md">
              {terminalLogs.map((log, i) => {
                let colorClass = 'text-green-400/90';
                if (log.includes('WARNING') || log.includes('FAILED')) {
                  colorClass = 'text-red-400 font-semibold';
                } else if (log.includes('[ORCHESTRATOR]')) {
                  colorClass = 'text-neutral-400';
                } else if (log.includes('PASSED') || log.includes('SUCCESS')) {
                  colorClass = 'text-emerald-400 font-bold';
                }

                return (
                  <div key={i} className={`${colorClass} leading-normal`}>
                    <span className="text-white select-none mr-1.5">$</span>
                    {log}
                  </div>
                );
              })}
            </div>
          </div>
        )}

      </div>
      </div>
    </aside>
  );
};
