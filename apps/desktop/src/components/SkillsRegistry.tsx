import React, { useState, useEffect, useCallback } from 'react';
import {
  fetchSkillsRegistry,
  mountSkillsDirectory,
  unmountSkillsDirectory,
  toggleSkillActive,
  notifySkillsUpdated,
  type ScannedSkill,
} from '../services/skillsApi';

export type { ScannedSkill };

export const SkillsRegistry: React.FC = () => {
  const [scannedSkills, setScannedSkills] = useState<ScannedSkill[]>([]);
  const [mountedDirectories, setMountedDirectories] = useState<string[]>([]);
  const [newDirPath, setNewDirPath] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    setErrorMsg('');
    try {
      const data = await fetchSkillsRegistry();
      setMountedDirectories(data.mounted_directories);
      setScannedSkills(data.skills);
      notifySkillsUpdated();
    } catch {
      setErrorMsg('Sidecar unavailable — cannot load skills registry.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const handleToggleGlobalSkill = async (key: string) => {
    const skill = scannedSkills.find((item) => item.key === key);
    if (!skill) return;
    try {
      const data = await toggleSkillActive(key, !skill.isActiveGlobally);
      setScannedSkills(data.skills);
      notifySkillsUpdated();
    } catch {
      setErrorMsg('Failed to update skill — Sidecar may be offline.');
    }
  };

  const handleMountDirectory = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newDirPath.trim()) return;
    const path = newDirPath.trim();
    if (mountedDirectories.includes(path)) {
      setSuccessMsg('Directory is already mounted');
      setTimeout(() => setSuccessMsg(''), 2000);
      return;
    }

    try {
      const data = await mountSkillsDirectory(path);
      setMountedDirectories(data.mounted_directories);
      setScannedSkills(data.skills);
      setNewDirPath('');
      const count = data.skills.length;
      setSuccessMsg(
        count > 0
          ? `Mounted and discovered ${count} skill(s).`
          : 'Directory mounted. No SKILL.md files found yet.',
      );
      notifySkillsUpdated();
      setTimeout(() => setSuccessMsg(''), 4000);
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : 'Mount failed.');
    }
  };

  const handleUnmount = async (dir: string) => {
    try {
      const data = await unmountSkillsDirectory(dir);
      setMountedDirectories(data.mounted_directories);
      setScannedSkills(data.skills);
      notifySkillsUpdated();
    } catch {
      setErrorMsg('Failed to unmount directory.');
    }
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-white select-text">
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-[20px] text-neutral-800">school</span>
            <h2 className="text-base font-bold text-neutral-900 tracking-tight font-sans">Global Skills Registry</h2>
          </div>
          <p className="text-xs text-neutral-500 font-sans leading-relaxed">
            Mount directories that contain <code className="font-mono text-[10.5px] bg-neutral-100 text-neutral-800 px-1 py-0.5 rounded">SKILL.md</code> files.
            Clutch scans them via the Sidecar and syncs active skills to Agent configuration.
          </p>
        </div>

        {errorMsg && (
          <p className="text-xs text-amber-700 bg-amber-50 border border-amber-100 rounded-lg px-3 py-2">{errorMsg}</p>
        )}

        <div className="p-4 bg-neutral-50/50 border border-neutral-200/60 rounded-xl space-y-4">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <h3 className="text-[11px] font-extrabold text-[#111111] font-mono tracking-wider uppercase">Search Paths</h3>
              <p className="text-[9.5px]/snug text-neutral-400 font-sans">Paths stored in Application Support and scanned on refresh.</p>
            </div>
            <button
              type="button"
              onClick={() => void refresh()}
              disabled={loading}
              className="text-[10px] font-bold text-neutral-500 hover:text-neutral-800 disabled:opacity-50"
            >
              Rescan
            </button>
          </div>

          {loading ? (
            <p className="text-xs text-neutral-400 italic">Loading skills registry…</p>
          ) : mountedDirectories.length === 0 ? (
            <p className="text-xs text-neutral-400 italic">No skill directories mounted.</p>
          ) : (
            <div className="grid grid-cols-1 gap-2">
              {mountedDirectories.map((dir) => (
                <div
                  key={dir}
                  className="flex items-center justify-between p-2.5 bg-white border border-neutral-200 rounded-lg text-xs"
                >
                  <div className="flex items-center gap-2.5 overflow-hidden">
                    <span className="material-symbols-outlined text-[16px] text-neutral-400">folder_open</span>
                    <span className="font-mono text-neutral-700 truncate">{dir}</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => void handleUnmount(dir)}
                    className="text-neutral-400 hover:text-red-600 transition-colors p-1 hover:bg-neutral-50 rounded"
                    title="Unmount directory"
                  >
                    <span className="material-symbols-outlined text-[15px] font-bold">delete</span>
                  </button>
                </div>
              ))}
            </div>
          )}

          <form onSubmit={(e) => void handleMountDirectory(e)} className="pt-2 border-t border-dashed border-neutral-200 flex gap-2">
            <input
              type="text"
              required
              value={newDirPath}
              onChange={(e) => setNewDirPath(e.target.value)}
              placeholder="e.g. ~/.cursor/skills/"
              className="flex-1 px-3 py-1.5 text-xs border border-neutral-200 focus:outline-none focus:border-neutral-900 bg-white rounded-lg font-mono placeholder:text-neutral-400"
            />
            <button
              type="submit"
              className="px-3.5 py-1.5 bg-neutral-900 hover:bg-black text-white text-[11px] font-bold rounded-lg transition-all shadow-3xs cursor-pointer"
            >
              + Mount Root
            </button>
          </form>

          {successMsg && (
            <p className="text-[10px] text-emerald-600 font-sans font-medium select-none">
              {successMsg}
            </p>
          )}
        </div>

        <div className="space-y-3">
          <div className="flex items-center justify-between px-1">
            <h3 className="text-[11px] font-extrabold text-[#111111] font-mono tracking-wider uppercase">Discovered Skills</h3>
            <span className="text-[10px] text-neutral-400 font-semibold font-mono">{scannedSkills.length} FOUND</span>
          </div>

          {scannedSkills.length === 0 ? (
            <p className="text-xs text-neutral-400 italic px-1">No skills discovered yet.</p>
          ) : (
            <div className="border border-neutral-200/80 bg-white rounded-xl divide-y divide-neutral-100 overflow-hidden shadow-3xs">
              {scannedSkills.map(skill => (
                <div
                  key={skill.key}
                  className="p-3.5 flex items-start justify-between gap-4 hover:bg-neutral-50/20 transition-colors"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-xs font-bold text-neutral-800 font-mono">{skill.label}</span>
                      <span className="text-[8.5px] font-mono text-neutral-500 bg-neutral-100 px-1.5 py-0.2 rounded font-semibold">{skill.source}</span>
                    </div>
                    <p className="text-[11px] text-neutral-500 leading-relaxed font-normal">{skill.desc}</p>
                  </div>

                  <div className="flex flex-col items-end gap-1.5 flex-shrink-0">
                    <button
                      type="button"
                      onClick={() => void handleToggleGlobalSkill(skill.key)}
                      className={`w-9 h-5 rounded-full p-0.5 transition-all duration-300 relative cursor-pointer flex items-center ${
                        skill.isActiveGlobally ? 'bg-neutral-900 justify-end' : 'bg-neutral-200 justify-start'
                      }`}
                      title="Toggle global skill"
                    >
                      <span className="w-4 h-4 rounded-full bg-white shadow-3xs block" />
                    </button>
                    {skill.isActiveGlobally ? (
                      <span className="text-[7.5px] uppercase font-mono text-emerald-700 font-extrabold bg-emerald-50 border border-emerald-150 px-1 py-0.5 rounded">ACTIVE</span>
                    ) : (
                      <span className="text-[7.5px] uppercase font-mono text-neutral-400 bg-neutral-50 px-1 py-0.5 rounded border border-neutral-200/40">INACTIVE</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
