import React, { useState, useEffect } from 'react';
import { useLanguage } from './LanguageContext';
import { BTN_GHOST, BTN_PRIMARY } from './ui/buttonStyles';

export interface PromptModalProps {
  isOpen: boolean;
  title: string;
  message?: string;
  hasInput?: boolean;
  placeholder?: string;
  defaultValue?: string;
  onConfirm: (value: string) => void;
  onCancel: () => void;
}

export const PromptModal: React.FC<PromptModalProps> = ({
  isOpen,
  title,
  message = '',
  hasInput = false,
  placeholder = '',
  defaultValue = '',
  onConfirm,
  onCancel,
}) => {
  const [value, setValue] = useState(defaultValue);
  const { t } = useLanguage();

  useEffect(() => {
    if (isOpen) {
      setValue(defaultValue);
    }
  }, [isOpen, defaultValue]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-[2px] flex items-center justify-center z-[1000] select-none">
      <div className="bg-surface-bright border border-outline-variant w-full max-w-sm rounded-xl shadow-xl p-4 space-y-3">
        <h3 className="text-[11px] font-bold uppercase tracking-wider text-on-surface">{title}</h3>
        
        {message && (
          <p className="text-[13px] text-on-surface-variant leading-relaxed select-text">
            {message}
          </p>
        )}

        {hasInput && (
          <input
            type="text"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder={placeholder}
            className="w-full rounded-lg border border-outline-variant/60 bg-surface px-2.5 py-1.5 text-[11px] text-on-surface placeholder:text-on-surface-variant/50 focus:outline-none focus:border-primary/50"
            autoFocus
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                onConfirm(value);
              } else if (e.key === 'Escape') {
                onCancel();
              }
            }}
          />
        )}

        <div className="flex justify-end gap-2 pt-1">
          <button type="button" onClick={onCancel} className={BTN_GHOST}>
            {t('Cancel')}
          </button>
          <button type="button" onClick={() => onConfirm(value)} className={BTN_PRIMARY}>
            {t('Confirm')}
          </button>
        </div>
      </div>
    </div>
  );
};
