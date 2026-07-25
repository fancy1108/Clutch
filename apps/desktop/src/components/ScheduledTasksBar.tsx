/**
 * Cap-D25 — scheduled / loop tasks panel (extension D25 scheduler).
 */
import React, { useCallback, useEffect, useState } from 'react';
import {
  createScheduledTask,
  deleteScheduledTask,
  listScheduledTasks,
  type ScheduledTask,
} from '../services/scheduledTasksApi';

export function ScheduledTasksBar({ t }: { t: (key: string) => string }) {
  const [tasks, setTasks] = useState<ScheduledTask[]>([]);
  const [open, setOpen] = useState(false);
  const [prompt, setPrompt] = useState('');
  const [intervalSec, setIntervalSec] = useState(120);

  const refresh = useCallback(async () => {
    const rows = await listScheduledTasks();
    setTasks(rows);
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

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

  return (
    <div data-testid="scheduled-tasks-bar" className="w-full max-w-3xl mx-auto px-3 pb-2">
      <button
        type="button"
        className="text-[10px] font-semibold text-primary hover:underline"
        onClick={() => setOpen((v) => !v)}
      >
        {t('Scheduled tasks')} ({tasks.length})
      </button>
      {open ? (
        <div className="mt-2 rounded-lg border border-border/60 bg-surface-container-low p-3 space-y-2">
          <div className="flex gap-2">
            <input
              data-testid="scheduled-task-prompt"
              className="flex-1 rounded border border-border/60 px-2 py-1 text-[11px]"
              placeholder={t('Reminder or agent prompt')}
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
            />
            <input
              data-testid="scheduled-task-interval"
              type="number"
              min={30}
              className="w-20 rounded border border-border/60 px-2 py-1 text-[11px]"
              value={intervalSec}
              onChange={(e) => setIntervalSec(Number(e.target.value) || 120)}
            />
            <button
              type="button"
              data-testid="scheduled-task-create"
              className="rounded bg-primary px-2 py-1 text-[10px] font-semibold text-on-primary"
              onClick={() => void handleCreate()}
            >
              {t('Add')}
            </button>
          </div>
          <ul className="space-y-1">
            {tasks.map((task) => (
              <li
                key={task.id}
                className="flex items-center justify-between text-[10px] text-on-surface-variant"
                data-testid={`scheduled-task-${task.id}`}
              >
                <span className="truncate">
                  {task.title} · {task.interval_sec}s
                  {task.enabled ? ` · ${t('on')}` : ` · ${t('off')}`}
                </span>
                <button
                  type="button"
                  className="text-rose-600 hover:underline"
                  onClick={() => void deleteScheduledTask(task.id).then(refresh)}
                >
                  {t('Delete')}
                </button>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
