import React from 'react';

interface WorkflowJsonPanelProps {
  value: string;
  onChange: (value: string) => void;
  readOnly: boolean;
  error: string | null;
  hint: string | null;
}

/** Raw compiler JSON editor (D9 advanced mode). */
export const WorkflowJsonPanel: React.FC<WorkflowJsonPanelProps> = ({
  value,
  onChange,
  readOnly,
  error,
  hint,
}) => (
  <div className="flex-1 flex flex-col p-4 gap-3 bg-surface-container-low/30">
    <div className="flex items-start justify-between gap-4">
      <div>
        <p className="text-xs font-bold text-neutral-800 uppercase tracking-wider font-sans">
          执行格式 JSON
        </p>
        <p className="text-[10px] text-on-surface-variant mt-1 leading-relaxed max-w-xl">
          复杂流程（检查节点、人工审批、条件分支、循环）请在此编辑；保存前会经 Sidecar 校验。
        </p>
      </div>
      {hint && (
        <span className="text-[10px] font-mono text-amber-800 bg-amber-50 border border-amber-200/80 px-2 py-1 rounded-lg shrink-0">
          {hint}
        </span>
      )}
    </div>
    <textarea
      value={value}
      onChange={(e) => onChange(e.target.value)}
      readOnly={readOnly}
      spellCheck={false}
      className={`flex-1 min-h-[320px] w-full rounded-xl border px-4 py-3 text-[12px] font-mono leading-relaxed resize-none focus:outline-none focus:ring-2 focus:ring-neutral-200/50 transition-all ${
        readOnly
          ? 'bg-neutral-50 text-neutral-600 border-neutral-200'
          : 'bg-white text-neutral-900 border-neutral-200 focus:border-neutral-400'
      }`}
    />
    {error && (
      <div className="text-[11px] text-rose-800 bg-rose-50 border border-rose-200/80 rounded-xl px-3 py-2 font-medium">
        {error}
      </div>
    )}
  </div>
);
