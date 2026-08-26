import React, { useEffect, useState } from 'react';
import { SIDECAR_BASE as BASE, sidecarFetch } from '../services/sidecarUrl';
import { BTN_SECONDARY } from './ui/buttonStyles';
import { useLanguage } from './LanguageContext';
import { SettingsSelect } from './ui/SettingsSelect';

type Rule = { pattern: string; action: 'allow' | 'ask' | 'deny' };

export const ExecPolicyPanel: React.FC = () => {
  const { t } = useLanguage();
  const [rules, setRules] = useState<Rule[]>([]);
  const [pattern, setPattern] = useState('');
  const [action, setAction] = useState<Rule['action']>('ask');

  const reload = async () => {
    const res = await sidecarFetch(`${BASE}/api/preferences/permission-rules`);
    if (!res.ok) return;
    const body = (await res.json()) as { rules?: Rule[] };
    setRules(body.rules ?? []);
  };

  useEffect(() => {
    void reload().catch(() => setRules([]));
  }, []);

  const persist = async (next: Rule[]) => {
    const res = await sidecarFetch(`${BASE}/api/preferences/permission-rules`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ rules: next }),
    });
    if (!res.ok) return;
    const body = (await res.json()) as { rules?: Rule[] };
    setRules(body.rules ?? next);
  };

  return (
    <div className="space-y-3" data-testid="exec-policy-panel">
      <h3 className="text-xs font-bold uppercase tracking-wider text-on-surface-variant">
        {t('Command policy')}
      </h3>
      <p className="text-[11px] text-on-surface-variant/80">
        {t('Allow, ask, or deny shell commands matching a pattern. Dangerous commands still force-ask.')}
      </p>
      <div className="flex flex-wrap items-center gap-2">
        <input
          data-testid="exec-policy-pattern"
          value={pattern}
          onChange={(e) => setPattern(e.target.value)}
          placeholder="rm -rf"
          className="flex-1 min-w-[140px] bg-surface border border-outline/40 rounded-xl px-3 py-2 text-xs"
        />
        <div className="w-28">
          <SettingsSelect
            id="exec-policy-action"
            value={action}
            options={[
              { value: 'allow', label: t('Allow') },
              { value: 'ask', label: t('Ask') },
              { value: 'deny', label: t('Deny') },
            ]}
            onChange={(next) => setAction(next as Rule['action'])}
          />
        </div>
        <button
          type="button"
          data-testid="exec-policy-add"
          className={`${BTN_SECONDARY} px-3 py-1.5 text-xs font-semibold`}
          onClick={() => {
            const token = pattern.trim();
            if (!token) return;
            void persist([...rules, { pattern: token, action }]);
            setPattern('');
          }}
        >
          {t('Add rule')}
        </button>
      </div>
      <ul className="space-y-1">
        {rules.map((rule, index) => (
          <li
            key={`${rule.pattern}-${index}`}
            className="flex items-center justify-between gap-2 text-xs bg-surface-container/40 rounded-lg px-3 py-2"
          >
            <span className="font-mono truncate">{rule.pattern}</span>
            <span className="uppercase text-[10px] text-on-surface-variant">{rule.action}</span>
            <button
              type="button"
              className="text-[10px] text-on-surface-variant hover:text-on-surface"
              onClick={() => void persist(rules.filter((_, i) => i !== index))}
            >
              {t('Remove')}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
};
