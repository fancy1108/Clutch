import React, { useState, useRef, useEffect } from 'react';
import { ChevronDown } from 'lucide-react';
import { useLanguage } from './LanguageContext';

interface StateControllerProps {
  state: string;
  setState: (s: string) => void;
}

export default function StateController({ state, setState }: StateControllerProps) {
  const { t } = useLanguage();
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const options = [
    { key: 'Normal', label: t('Normal'), dotColor: 'bg-emerald-500' },
    { key: 'Warning', label: t('Warning'), dotColor: 'bg-amber-500' },
    { key: 'Critical', label: t('Critical'), dotColor: 'bg-rose-500' },
    { key: 'DataOverflow', label: t('Data Overflow'), dotColor: 'bg-purple-500' }
  ];

  const activeOption = options.find(opt => opt.key === state) || options[0];

  // Close dropdown on click outside
  useEffect(() => {
    function clickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', clickOutside);
    return () => document.removeEventListener('mousedown', clickOutside);
  }, []);

  return (
    <div className="inline-flex items-center gap-2 select-none relative" ref={containerRef}>
      <span className="text-[10px] font-medium text-on-surface-variant/75 shrink-0">
        {t('Prototype State:')}
      </span>
      
      <div className="relative">
        <button
          type="button"
          onClick={() => setIsOpen(!isOpen)}
          className="bg-surface border border-outline/40 hover:border-outline-variant/60 rounded-lg px-2.5 py-1.5 text-[10px] text-on-surface flex items-center justify-between gap-2.5 cursor-pointer font-semibold shadow-2xs select-none min-w-[120px]"
        >
          <span className="flex items-center gap-1.5">
            <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${activeOption.dotColor}`} />
            <span>{activeOption.label}</span>
          </span>
          <ChevronDown size={10} className={`text-on-surface-variant/60 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} />
        </button>

        {isOpen && (
          <div className="absolute right-0 top-full mt-1 z-50 bg-surface border border-outline rounded-lg shadow-md py-1 overflow-hidden min-w-[120px]">
            {options.map((opt) => {
              const isActive = state === opt.key;
              return (
                <button
                  key={opt.key}
                  type="button"
                  onClick={() => {
                    setState(opt.key);
                    setIsOpen(false);
                  }}
                  className={`w-full text-left px-2.5 py-1.5 text-[10px] flex items-center gap-1.5 cursor-pointer transition-colors font-medium ${
                    isActive
                      ? 'bg-surface-container text-on-surface font-semibold'
                      : 'text-on-surface-variant/80 hover:text-on-surface hover:bg-surface-container-high/40'
                  }`}
                >
                  <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${opt.dotColor}`} />
                  <span>{opt.label}</span>
                </button>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
