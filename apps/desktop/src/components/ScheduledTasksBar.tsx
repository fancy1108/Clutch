/**
 * Cap-D25 — scheduled / loop tasks panel (opened from composer + menu).
 */
import React, { useCallback, useEffect, useState } from 'react';
import {
  createScheduledTask,
  deleteScheduledTask,
  listScheduledTasks,
  type ScheduledTask,
} from '../services/scheduledTasksApi';

type ScheduledTasksBarProps = {
  t: (key: string) => string;
  /** Controlled open (composer + menu). */
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

export function ScheduledTasksBar({ t, open, onOpenChange }: ScheduledTasksBarProps) {
  const [tasks, setTasks] = useState<ScheduledTask[]>([]);
  const [prompt, setPrompt] = useState('');
  const [intervalSec, setIntervalSec] = useState(120);

  const refresh = useCallback(async () => {
    const rows = await listScheduledTasks();
    setTasks(rows);
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    if (open) void refresh();
  }, [open, refresh]);

  const handleCreate = async () => {
    if (!prompt.trim()) return;
    await createScheduledTask({
      prompt: prompt.trim(),
      interval_sec: intervalSec,
      enabled: false,
    });
    setPrompt('');
    await refresh();
  };

  if (!open) {
    return <div data-testid="scheduled-tasks-bar" className="hidden" aria-hidden />;
  }

  return (
    <div data-testid="scheduled-tasks-bar" className="absolute bottom-full left-0 right-0 mb-2 z-50 px-0">
      <div className="rounded-xl border border-outline-variant/50 bg-white p-3 shadow-xl space-y-2">
        <div className="flex items-center justify-between gap-2">
          <span className="text-[11px] font-semibold text-on-surface">
            {t('Scheduled tasks')} ({tasks.length})
          </span>
          <button
            type="button"
            className="text-[10px] text-on-surface-variant hover:text-on-surface"
            onClick={() => onOpenChange(false)}
          >
            {t('Close')}
          </button>
        </div>
        <div className="flex gap-2">
          <input
            data-testid="scheduled-task-prompt"
            className="flex-1 rounded-lg border border-outline-variant/50 px-2 py-1 text-[11px] bg-surface-container-low"
            placeholder={t('Reminder or agent prompt')}
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
          />
          <input
            data-testid="scheduled-task-interval"
            type="number"
            min={30}
            className="w-16 rounded-lg border border-outline-variant/50 px-2 py-1 text-[11px] bg-surface-container-low"
            value={intervalSec}
            onChange={(e) => setIntervalSec(Number(e.target.value) || 120)}
          />
          <button
            type="button"
            data-testid="scheduled-task-create"
            className="rounded-lg bg-neutral-900 px-2 py-1 text-[10px] font-semibold text-white hover:bg-black"
            onClick={() => void handleCreate()}
          >
            {t('Add')}
          </button>
        </div>
        <ul className="space-y-1 max-h-36 overflow-y-auto">
          {tasks.length === 0 ? (
            <li className="text-[10px] text-on-surface-variant/70 py-1">
              {t('No scheduled tasks yet')}
            </li>
          ) : (
            tasks.map((task) => (
              <li
                key={task.id}
                className="flex items-center justify-between gap-2 text-[10px] text-on-surface-variant"
                data-testid={`scheduled-task-${task.id}`}
              >
                <span className="truncate">
                  {task.title} · {task.interval_sec}s
                  {task.enabled ? ` · ${t('on')}` : ` · ${t('off')}`}
                </span>
                <button
                  type="button"
                  className="shrink-0 text-rose-600 hover:underline"
                  onClick={() => void deleteScheduledTask(task.id).then(refresh)}
                >
                  {t('Delete')}
                </button>
              </li>
            ))
          )}
        </ul>
      </div>
    </div>
  );
}
