import React, { useRef, useEffect, useState } from 'react';
import { ChatMessage, RunStatus } from '../types';

interface ChatFeedProps {
  messages: ChatMessage[];
  inputValue: string;
  setInputValue: (val: string) => void;
  onSendMessage: (text: string) => void;
  runStatus: RunStatus;
  currentFlowName: string;
  selectedSidebarWidth: number;
  rightSidebarWidth: number;
  onStopRun?: () => void;
  isMultiAgent?: boolean;
  onApprove?: () => void;
  onReject?: () => void;
  onRetryWithInstructions?: (instructions: string) => void;
}

export const ChatFeed: React.FC<ChatFeedProps> = ({
  messages,
  inputValue,
  setInputValue,
  onSendMessage,
  runStatus,
  currentFlowName,
  selectedSidebarWidth,
  rightSidebarWidth,
  onStopRun,
  isMultiAgent = true,
  onApprove,
  onReject,
  onRetryWithInstructions
}) => {
  const bottomRef = useRef<HTMLDivElement>(null);
  const [hillInstructions, setHillInstructions] = useState('');

  // Auto-scroll to bottom of messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, runStatus]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (inputValue.trim()) {
        onSendMessage(inputValue);
        setInputValue('');
      }
    }
  };

  const handleSendClick = () => {
    if (inputValue.trim()) {
      onSendMessage(inputValue);
      setInputValue('');
    }
  };

  return (
    <section 
      style={{
        paddingLeft: `${selectedSidebarWidth + 30}px`,
        paddingRight: `${rightSidebarWidth + 30}px`
      }}
      className="mt-[64px] flex-1 overflow-y-auto py-10 pb-40 flex flex-col items-center px-6 transition-all duration-300 bg-background"
    >
      <div className="w-full max-w-2xl mx-auto space-y-8 py-4">
        {messages.map(msg => {
          const isErrorMsg = msg.status === 'FAILED' || msg.badgeText?.includes('FAILED') || msg.badgeText?.includes('NEEDS');
          const isCompletedMsg = msg.status === 'COMPLETED';

          return (
            <div key={msg.id} className="flex gap-4 group hover:bg-surface-container-low/35 p-2 rounded-xl transition-colors">
              {/* Agent Avatar */}
              <div className="w-9 h-9 rounded-full overflow-hidden flex-shrink-0 flex items-center justify-center bg-surface-container">
                <img
                  className="w-full h-full object-cover"
                  src={msg.avatar}
                  alt={msg.agent}
                />
              </div>

              {/* Message Content */}
              <div className="flex-1 space-y-1.5 overflow-hidden">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-on-surface">{msg.agent}</span>
                  <span className="text-[10px] text-on-surface-variant/60">{msg.time}</span>
                </div>

                {isErrorMsg ? (
                  /* Simplified Critical Finding Card - clean, high-contrast, without repetitive headers or metrics */
                  <div className="p-4 bg-neutral-50/50 rounded-2xl rounded-tl-none border border-neutral-200/80 transition-all shadow-xs">
                    <div className="flex items-center gap-1.5 mb-2 text-neutral-800 font-bold text-[11px]">
                      <span className="material-symbols-outlined text-[16px]">error</span>
                      <span>VALIDATION FAILED</span>
                    </div>

                    <p className="text-[13px] text-on-surface select-text leading-relaxed">
                      {msg.text}
                    </p>
                  </div>
                ) : (
                  /* Standard Card */
                  <div className="p-4 bg-surface-container-low rounded-2xl rounded-tl-none border border-outline-variant/30 transition-all shadow-sm">
                    {isCompletedMsg && (
                      <div className="flex items-center gap-1.5 mb-2 text-green-600 font-bold text-[11px]">
                        <span className="material-symbols-outlined text-[16px]">check_circle</span>
                        <span>COMPLETED</span>
                      </div>
                    )}

                    <p className="text-[13px] text-on-surface select-text leading-relaxed">
                      {msg.text}
                    </p>

                    {/* File changed alert badge inside Builder completed card */}
                    {msg.codeHighlight && (
                      <div className="mt-3 flex items-center gap-2 py-2 px-3 bg-white/60 rounded-xl border border-outline-variant/30">
                        <span className="material-symbols-outlined text-green-500 text-[18px]">check_circle</span>
                        <span className="text-[11px] font-semibold text-on-surface">
                          {msg.codeHighlight.lineCount} files updated in {msg.codeHighlight.file}
                        </span>
                      </div>
                    )}

                    {/* execution parameters */}
                    <div className="mt-3 pt-3 border-t border-outline-variant/10 flex items-center justify-between">
                      <div className="flex gap-4 text-[9px] text-on-surface-variant/60 font-mono">
                        {msg.executionTime && (
                          <span className="flex items-center gap-1">
                            <span className="material-symbols-outlined text-[13px]">history</span> {msg.executionTime}
                          </span>
                        )}
                        {msg.tokens && (
                          <span className="flex items-center gap-1">
                            <span className="material-symbols-outlined text-[13px]">database</span> {msg.tokens}
                          </span>
                        )}
                      </div>
                      <button 
                        onClick={() => alert(`Direct deliverables for ${msg.agent}:\nAll schema checks verified.`)}
                        className="text-[9px] font-bold text-on-surface-variant/70 hover:text-primary transition-colors flex items-center gap-1"
                      >
                        <span className="material-symbols-outlined text-[13px]">visibility</span> View Deliverables
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          );
        })}

        {/* Builder Running Node animates dynamically in 'running' state */}
        {runStatus === 'failed' && (
          <div className="flex gap-4 p-4 bg-gradient-to-r from-amber-50/60 via-white to-amber-50/30 border border-amber-200/50 rounded-2xl shadow-sm animate-[pulse_4s_infinite_ease-in-out] relative overflow-hidden">
            {/* Soft background glow */}
            <div className="absolute -right-20 -top-20 w-40 h-40 bg-amber-200/5 rounded-full blur-2xl" />
            
            {/* Builder Avatar with pulse effect */}
            <div className="relative flex-shrink-0">
              <div className="w-9 h-9 rounded-full overflow-hidden border border-amber-400/40 flex items-center justify-center bg-amber-50 shadow-sm">
                <img
                  className="w-full h-full object-cover"
                  src="https://lh3.googleusercontent.com/aida-public/AB6AXuBpRidttSGTIY-J-PGvnlcZX_oZSZoBXJY5vjZ9g1PKl_fq4EKoa2RXbcSCvvIdbPLdmfuzPKTxnR8TqV7skwsKlt-eKEzSzktv-TWbHu4c9uBEdP6Es_Fjek1EBQuGZeMtWsUi3fn0lyozFaZBLp9SpES3r0WalbqYY6gGiT1R_0J1kvU-D9rI_2q2f3sMGHuTjWyOZ5gImCLGHSGejtcKmToTSZYMrXfT_A5x1iw_f4q7WljP3FXjk64aQhLgh9nTXUDfPdkIzu0b"
                  alt="Builder"
                />
              </div>
              <span className="absolute -bottom-0.5 -right-0.5 w-3 h-3 bg-amber-500 rounded-full flex items-center justify-center text-[8px] text-white font-bold animate-pulse shadow-sm">
                ⚡
              </span>
            </div>

            <div className="flex-1 space-y-2 relative z-10">
              <div className="flex items-center gap-2.5">
                <span className="text-xs font-bold text-slate-800">Builder</span>
                <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[9px] font-bold bg-amber-500 text-white animate-pulse">
                  <span className="w-1 h-1 rounded-full bg-white animate-ping" />
                  REPAIR ROUTINE IDLE
                </span>
              </div>

              <div className="p-3 bg-white/80 backdrop-blur-[1px] rounded-xl border border-amber-100/50 flex gap-3 shadow-inner">
                <div className="flex items-center gap-1 mt-1 flex-shrink-0">
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-subtle-pulse"></span>
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-subtle-pulse" style={{ animationDelay: '0.2s' }}></span>
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-subtle-pulse" style={{ animationDelay: '0.4s' }}></span>
                </div>
                <div className="space-y-1">
                  <p className="text-xs text-slate-700 font-medium select-text leading-relaxed">
                    Awaiting trigger command. Ready to begin <strong className="text-amber-800">Round 2 Automatic Repair</strong>. Will address the missing <code className="bg-amber-50 text-amber-700 px-1 py-0.5 rounded font-mono text-[10px]">verify.md</code> artifact.
                  </p>
                  <p className="text-[10px] text-zinc-500 flex items-center gap-1">
                    <span className="material-symbols-outlined text-[13px] text-amber-500">info</span>
                    Click <strong className="text-amber-700 font-semibold bg-amber-50 px-1 rounded">Re-assign to Builder</strong> in right panel to start.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {runStatus === 'running' && (
          <div className="flex gap-4 p-2 rounded-xl transition-colors">
            {/* Agent Avatar */}
            <div className="w-9 h-9 rounded-full overflow-hidden flex-shrink-0 flex items-center justify-center bg-surface-container">
              <img
                className="w-full h-full object-cover"
                src="https://lh3.googleusercontent.com/aida-public/AB6AXuA0yGh59QNLj5n0igNxMgu4lgaiNqZpcN29SpWM0JHNlAuFmOBx-Id67Zcd2NDCNBjBKrcffQrdrfoe-3XaSlveekLAP9SRis93uTk7XPPFO5y4Swos7NvATw6n7eZEm7nfAQuTiMAoWRSnxefAOJugUbZx3fCTNv4jGyjvT-UZznwKzp_HoXuStup_0juhBCZYamrV0Coil-k27d9Yi7il6NabIEG0FfbxwL5V5azpfZQOlBfpaganta2kP7n59BKPHd4K2uTOfZ5p"
                alt="Orchestrator"
              />
            </div>

            {/* Message Content */}
            <div className="flex-1 space-y-1.5 overflow-hidden">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-on-surface">Orchestrator</span>
                  <span className="text-[10px] text-on-surface-variant/60">Just now</span>
                </div>
                {/* Right: Running Status Badge */}
                <div className="flex items-center gap-1.5 text-[10px] font-bold text-neutral-800 tracking-wider">
                  <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-black opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-black"></span>
                  </span>
                  <span>RUNNING</span>
                </div>
              </div>

              {/* Standard Card Styled Container matching above lists */}
              <div className="p-4 bg-surface-container-low rounded-2xl rounded-tl-none border border-outline-variant/30 transition-all shadow-sm">
                <div className="flex items-center gap-1.5 mb-2 text-neutral-800 font-bold text-[11px]">
                  <span className="material-symbols-outlined text-[16px] animate-spin">progress_activity</span>
                  <span>ACTIVE REPAIR WORKFLOW</span>
                </div>

                <p className="text-[13px] text-on-surface select-text leading-relaxed">
                  Builder module compiling active changes... Validating <code className="bg-neutral-100 text-neutral-800 px-1 py-0.5 rounded font-mono text-[10px]">verify.md</code> checklist and parsing structural syntax test reports.
                </p>

                {/* Nice clean custom progress bar */}
                <div className="mt-3 w-full h-1.5 bg-neutral-100 rounded-full overflow-hidden relative">
                  <div className="h-full bg-black rounded-full animate-progress-loading" style={{ width: '40%' }} />
                </div>

                {/* Clean log block */}
                <div className="mt-4 bg-neutral-50/70 rounded-xl p-3 border border-neutral-100 space-y-1.5 font-mono text-[10.5px] text-neutral-700">
                  <div className="flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-black animate-ping" />
                    <span className="text-neutral-900 font-semibold">[1/3] Compiling TSX templates inside source directory...</span>
                  </div>
                  <div className="flex items-center gap-2 pl-3 text-neutral-500">
                    <span className="material-symbols-outlined text-[12px] text-neutral-400">check_circle</span>
                    <span>Loaded 12/12 validation nodes</span>
                  </div>
                  <div className="flex items-center gap-2 pl-3 text-neutral-500">
                    <span className="material-symbols-outlined text-[12px] text-neutral-400">hourglass_empty</span>
                    <span>Compliance test runner evaluation pending...</span>
                  </div>
                </div>

                {/* execution parameters */}
                <div className="mt-4 pt-3 border-t border-outline-variant/10 flex items-center justify-between">
                  <div className="flex gap-4 text-[9px] text-on-surface-variant/60 font-mono">
                    <span className="flex items-center gap-1">
                      <span className="material-symbols-outlined text-[13px]">history</span> Round 2 active
                    </span>
                    <span className="flex items-center gap-1">
                      <span className="material-symbols-outlined text-[13px]">database</span> 1,280 tokens
                    </span>
                  </div>
                  <button 
                    onClick={() => alert(`Active Orchestrator validation step inside Round 2.`)}
                    className="text-[9px] font-bold text-on-surface-variant/70 hover:text-black transition-colors flex items-center gap-1"
                  >
                    <span className="material-symbols-outlined text-[13px]">visibility</span> View Workspace State
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Floating Chat Input Bar */}
      <div 
        style={{
          left: `${selectedSidebarWidth + 24}px`,
          right: `${rightSidebarWidth + 24}px`
        }}
        className="fixed bottom-8 flex justify-center px-6 z-40 transition-all duration-300 select-none"
      >
        {runStatus === 'running' ? (
          /* Active Workflow in-progress banner with a Stop button - perfectly aligned with the clean high-contrast theme */
          <div className="w-full max-w-2xl bg-white border border-outline-variant p-3 shadow-xl transition-all rounded-xl flex items-center justify-between select-none">
            <div className="flex items-center gap-3">
              <span className="relative flex h-2.5 w-2.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-black opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-black"></span>
              </span>
              <div className="text-left">
                <p className="text-[10px] font-bold tracking-wider text-on-surface-variant uppercase">WORKFLOW ACTIVE &bull; ROUND 2 OF 3</p>
                <p className="text-xs text-on-surface mt-0.5 font-medium">Automatic Repair: Builder correcting missing expected verify.md artifact...</p>
              </div>
            </div>
            <button 
              onClick={onStopRun}
              className="px-3.5 py-1.5 bg-neutral-900 hover:bg-black active:scale-95 text-white font-bold rounded-lg text-[10px] uppercase tracking-wider flex items-center gap-1.5 shadow-sm transition-all border border-neutral-950"
              title="Stop current execution workflow run"
            >
              <span className="material-symbols-outlined text-[13px]">cancel</span>
              Stop
            </button>
          </div>
        ) : runStatus === 'failed' ? (
          /* Human-in-the-loop — see UI_UX_GUIDELINES.md */
          <div className="w-full max-w-2xl bg-white border border-rose-200/90 p-5 p-r-6 shadow-xl hover:shadow-2xl transition-all rounded-2xl flex flex-col gap-4 select-text text-left">
            <div className="flex items-center justify-between border-b border-neutral-100 pb-3">
              <div className="flex items-center gap-2.5">
                <span className="w-8 h-8 rounded-full bg-rose-550 text-white flex items-center justify-center font-mono text-sm shadow-sm" style={{ backgroundColor: '#ba1a1a' }}>
                  <span className="material-symbols-outlined text-[18px]">gavel</span>
                </span>
                <div>
                  <h4 className="text-[11.5px] font-bold tracking-wider text-rose-800 font-sans uppercase">Human-In-The-Loop Intervention</h4>
                  <p className="text-[10.5px] text-on-surface-variant/80 mt-0.5 font-medium">Evaluator reported validation failures. Override standard compiler protocols:</p>
                </div>
              </div>
              <span className="text-[8.5px] font-mono tracking-wider bg-rose-50 border border-rose-200/60 text-rose-700 px-2.5 py-1 rounded-md font-bold uppercase">STUCK_GATE</span>
            </div>

            {/* Actions layout */}
            <div className="flex flex-col sm:flex-row gap-3 items-stretch sm:items-center justify-between">
              {/* Left: Quick overriding options matching human buttons */}
              <div className="flex items-center gap-2 flex-wrap">
                <button
                  type="button"
                  onClick={onApprove}
                  className="px-3.5 py-2 bg-emerald-50 hover:bg-emerald-600 border border-emerald-200 hover:border-emerald-600 text-emerald-800 hover:text-white font-bold rounded-lg text-[10px] uppercase tracking-wider flex items-center gap-1.5 shadow-2xs transition-all cursor-pointer active:scale-95"
                  title="Force allow deployment and bypass constraints"
                >
                  <span className="material-symbols-outlined text-[13px]">done</span>
                  Bypass & Approve
                </button>
                <button
                  type="button"
                  onClick={onReject}
                  className="px-3.5 py-2 bg-rose-550/5 hover:bg-rose-650 border border-rose-200 hover:border-rose-650 text-rose-800 hover:text-white font-bold rounded-lg text-[10px] uppercase tracking-wider flex items-center gap-1.5 shadow-2xs transition-all cursor-pointer active:scale-95 hover:bg-red-600"
                  title="Reject workspace status and return to draft sandbox"
                >
                  <span className="material-symbols-outlined text-[13px]">close</span>
                  Reject & Redo
                </button>
              </div>

              {/* Right: Quick instruction presets */}
              <div className="flex items-center gap-2 text-[10px] text-on-surface-variant">
                <span className="font-mono text-[9px] uppercase font-bold text-on-surface-variant/70">Quick Directives:</span>
                <div className="flex items-center gap-1">
                  <button
                    type="button"
                    onClick={() => setHillInstructions('Bypass validation, package directly')}
                    className="px-2.5 py-1 bg-neutral-50 hover:bg-neutral-100 border border-neutral-200 rounded-md text-[9.5px] text-neutral-600 hover:text-neutral-900 font-sans transition-colors cursor-pointer font-medium"
                  >
                    Bypass Check
                  </button>
                  <button
                    type="button"
                    onClick={() => setHillInstructions('Force override configuration')}
                    className="px-2.5 py-1 bg-neutral-50 hover:bg-neutral-100 border border-neutral-200 rounded-md text-[9.5px] text-neutral-600 hover:text-neutral-900 font-sans transition-colors cursor-pointer font-medium"
                  >
                    Force Overwrite
                  </button>
                </div>
              </div>
            </div>

            {/* Instruction input area with soft modern look */}
            <div className="flex items-center gap-2 bg-neutral-50 border border-neutral-200/80 p-1.5 rounded-xl focus-within:ring-2 focus-within:ring-rose-500/10 focus-within:border-rose-300 transition-all">
              <span className="material-symbols-outlined text-neutral-400 text-[18px] pl-2">edit_note</span>
              <input
                type="text"
                value={hillInstructions}
                onChange={e => setHillInstructions(e.target.value)}
                onKeyDown={e => {
                  if (e.key === 'Enter' && hillInstructions.trim()) {
                    onRetryWithInstructions?.(hillInstructions.trim());
                    setHillInstructions('');
                  }
                }}
                placeholder='Add specific directive, e.g. "Bypass syntax validation & compile"...'
                className="w-full bg-transparent border-none text-[11px] text-on-surface placeholder:text-neutral-400 focus:ring-0 focus:outline-none py-1.5 px-1 font-sans"
              />
              <button
                type="button"
                disabled={!hillInstructions.trim()}
                onClick={() => {
                  if (hillInstructions.trim()) {
                    onRetryWithInstructions?.(hillInstructions.trim());
                    setHillInstructions('');
                  }
                }}
                className={`px-3.5 py-1.8 text-[10px] uppercase font-mono font-bold rounded-lg transition-all flex items-center gap-1 flex-shrink-0 ${
                  hillInstructions.trim()
                    ? 'bg-neutral-900 text-white hover:bg-black active:scale-95 cursor-pointer'
                    : 'bg-neutral-100 text-neutral-400 border border-neutral-200 cursor-not-allowed'
                }`}
              >
                Retry with Directive
                <span className="material-symbols-outlined text-[13px]">replay</span>
              </button>
            </div>
          </div>
        ) : (
          <div className="w-full max-w-2xl bg-white border border-outline-variant p-2 shadow-xl focus-within:ring-2 focus-within:ring-primary/5 transition-all rounded-xl">
            <div className="flex items-end gap-2 px-2 py-1">
              <button 
                onClick={() => {
                  const f = prompt("Type file name to request verification (e.g., config.yaml):");
                  if (f) onSendMessage(`Analyze this workspace file reference: ${f}`);
                }}
                className="w-10 h-10 flex items-center justify-center text-on-surface-variant hover:bg-surface-container rounded-full transition-colors flex-shrink-0 mb-0.5"
                title="Add attachment / reference folder"
              >
                <span className="material-symbols-outlined text-[22px]">add</span>
              </button>
              
              <textarea
                value={inputValue}
                onChange={e => setInputValue(e.target.value)}
                onKeyDown={handleKeyDown}
                className="w-full border-none focus:ring-0 text-xs text-on-surface bg-transparent p-2 resize-none min-h-[40px] max-h-[140px] placeholder:text-on-surface-variant/70 outline-none"
                placeholder={isMultiAgent ? "Ask @Builder, @Orchestrator or trigger @Workflow..." : "Ask your AI Agent anything..."}
                rows={1}
              />

              <div className="flex items-center gap-1 flex-shrink-0 mb-0.5">
                <button 
                  onClick={() => alert("Simulated mic active. Talk to prompt the agents.")}
                  className="w-10 h-10 flex items-center justify-center text-on-surface-variant hover:bg-surface-container rounded-full transition-colors"
                  title="Voice input"
                >
                  <span className="material-symbols-outlined text-[21px]">mic</span>
                </button>
                <button
                  onClick={handleSendClick}
                  disabled={!inputValue.trim()}
                  className={`w-10 h-10 flex items-center justify-center rounded-full transition-all active:scale-95 ${
                    inputValue.trim()
                      ? 'bg-primary text-white hover:opacity-90'
                      : 'bg-surface-container text-on-surface-variant/40 cursor-not-allowed'
                  }`}
                  title="Submit to active agent"
                >
                  <span className="material-symbols-outlined text-[18px]">arrow_upward</span>
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </section>
  );
};
