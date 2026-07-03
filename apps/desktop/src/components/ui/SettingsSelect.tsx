import React, { useEffect, useId, useRef, useState } from 'react';
import { BTN_FOCUS } from './buttonStyles';
import { LegacyIcon } from './LegacyIcon';

export type SettingsSelectOption = {
  value: string;
  label: string;
};

type SettingsSelectProps = {
  id?: string;
  value: string;
  options: SettingsSelectOption[];
  onChange: (value: string) => void;
};

const TRIGGER_CLASS =
  'w-full flex items-center justify-between gap-2 bg-surface border border-outline/40 rounded-xl px-4 py-2.5 text-xs text-on-surface transition-colors';

export const SettingsSelect: React.FC<SettingsSelectProps> = ({
  id,
  value,
  options,
  onChange,
}) => {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const listboxId = useId();
  const selected = options.find((option) => option.value === value) ?? options[0];

  useEffect(() => {
    if (!open) return;
    const handlePointerDown = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handlePointerDown);
    return () => document.removeEventListener('mousedown', handlePointerDown);
  }, [open]);

  return (
    <div ref={rootRef} className="relative flex-1">
      <button
        type="button"
        id={id}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={listboxId}
        onClick={() => setOpen((current) => !current)}
        className={`${TRIGGER_CLASS} ${BTN_FOCUS} hover:border-outline-variant/80 ${
          open ? 'border-primary/60 ring-2 ring-primary/10' : ''
        }`}
      >
        <span className="truncate text-left font-medium">{selected?.label}</span>
        <LegacyIcon
          name="keyboard_arrow_down"
          className={`text-[18px] text-on-surface-variant flex-shrink-0 transition-transform duration-200 ${
            open ? 'rotate-180' : ''
          }`}
        />
      </button>

      {open ? (
        <div
          id={listboxId}
          role="listbox"
          className="absolute left-0 right-0 top-full z-50 mt-1 overflow-hidden rounded-xl border border-outline-variant bg-surface-bright py-1 shadow-lg"
        >
          {options.map((option) => {
            const isSelected = option.value === value;
            return (
              <button
                key={option.value}
                type="button"
                role="option"
                aria-selected={isSelected}
                onClick={() => {
                  onChange(option.value);
                  setOpen(false);
                }}
                className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs hover:bg-surface-container-low transition-colors"
              >
                <LegacyIcon
                  name="check"
                  className={`w-4 flex-shrink-0 text-[14px] ${
                    isSelected ? 'text-primary opacity-100' : 'opacity-0'
                  }`}
                />
                <span className={isSelected ? 'font-semibold text-primary' : 'text-on-surface'}>
                  {option.label}
                </span>
              </button>
            );
          })}
        </div>
      ) : null}
    </div>
  );
};
