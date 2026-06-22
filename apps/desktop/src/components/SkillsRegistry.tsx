import React, { useState, useEffect } from 'react';

export interface ScannedSkill {
  key: string;
  label: string;
  source: string;
  isActiveGlobally: boolean;
  desc: string;
}

export const SkillsRegistry: React.FC = () => {
  const [scannedSkills, setScannedSkills] = useState<ScannedSkill[]>(() => {
    const saved = localStorage.getItem('vibe-scanned-skills');
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch (e) {}
    }
    return [
      { key: 'React-Lint-Rules', label: 'React Performance Rules', source: './.agents/skills/', isActiveGlobally: true, desc: 'Enforces clean dependency arrays and stable handler functions.' },
      { key: 'Secure-Code-Checklist', label: 'Security & Token Audits', source: '~/.agents/skills/', isActiveGlobally: false, desc: 'Prevents exposing live tokens and enforces server-side proxies.' },
      { key: 'GraphQL-Schema-Audit', label: 'GraphQL Schema Validator', source: '~/.agents/skills/', isActiveGlobally: false, desc: 'Ensures structured query definitions match relational models.' },
      { key: 'Mock-Data-Generator', label: 'Simulated Data Autogen', source: './.agents/skills/', isActiveGlobally: false, desc: 'Seeds local database states with consistent mock records.' },
      { key: 'Markdown-Verification', label: 'Markdown Spec Compliance', source: '~/.agents/skills/', isActiveGlobally: false, desc: 'Enforces standard structural tags and header checks.' }
    ];
  });

  const [mountedDirectories, setMountedDirectories] = useState<string[]>(() => {
    const saved = localStorage.getItem('vibe-mounted-dirs');
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch (e) {}
    }
    return ['~/.agents/skills/', './.agents/skills/'];
  });

  const [newDirPath, setNewDirPath] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  useEffect(() => {
    localStorage.setItem('vibe-scanned-skills', JSON.stringify(scannedSkills));
    // Dispatch custom event to notify other modules of skills registry change
    window.dispatchEvent(new Event('vibe-skills-updated'));
  }, [scannedSkills]);

  useEffect(() => {
    localStorage.setItem('vibe-mounted-dirs', JSON.stringify(mountedDirectories));
    window.dispatchEvent(new Event('vibe-skills-updated'));
  }, [mountedDirectories]);

  const handleToggleGlobalSkill = (key: string) => {
    setScannedSkills(prev =>
      prev.map(skill =>
        skill.key === key ? { ...skill, isActiveGlobally: !skill.isActiveGlobally } : skill
      )
    );
  };

  const handleMountDirectory = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newDirPath.trim()) return;
    const path = newDirPath.trim();
    if (mountedDirectories.includes(path)) {
      setSuccessMsg('Directory is already mounted');
      setTimeout(() => setSuccessMsg(''), 2000);
      return;
    }
    
    setMountedDirectories(prev => [...prev, path]);
    
    // Simulate finding a new skill file from the newly mounted root
    const formattedName = path.replace(/[.~/]/g, ' ').trim();
    const capitalizedName = formattedName.split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join('-');
    const newSkillKey = `${capitalizedName || 'Custom'}-Manual`;
    const newSkillName = `${capitalizedName || 'Custom'} Validation Manual`;
    
    setScannedSkills(prev => [
      ...prev,
      {
        key: newSkillKey,
        label: newSkillName,
        source: path,
        isActiveGlobally: false,
        desc: `Auto-discovered operational manual at the mounted path ${path}. Includes custom structural validations.`
      }
    ]);
    
    setNewDirPath('');
    setSuccessMsg('Successfully mounted skill directory! Discovered SKILL.md');
    setTimeout(() => setSuccessMsg(''), 3000);
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-white select-text">
      {/* Scrollable Container */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        
        {/* Banner Headers */}
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-[20px] text-neutral-800">school</span>
            <h2 className="text-base font-bold text-neutral-900 tracking-tight font-sans">Global Skills Registry</h2>
          </div>
          <p className="text-xs text-neutral-500 font-sans leading-relaxed">
            Configure system directories that auto-publish professional manuals (<code className="font-mono text-[10.5px] bg-neutral-100 text-neutral-800 px-1 py-0.5 rounded">SKILL.md</code>) to your Workspace routing pipeline.
          </p>
        </div>

        {/* Section 1: Directory Mounting */}
        <div className="p-4 bg-neutral-50/50 border border-neutral-200/60 rounded-xl space-y-4">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <h3 className="text-[11px] font-extrabold text-[#111111] font-mono tracking-wider uppercase">Active Search Paths</h3>
              <p className="text-[9.5px]/snug text-neutral-400 font-sans">Directories recursively scanned for YAML specification headers.</p>
            </div>
            <span className="text-[8.5px] font-mono uppercase bg-neutral-100 text-neutral-700 border border-neutral-200 px-2 py-0.5 rounded font-extrabold">Auto-Discovery</span>
          </div>

          <div className="grid grid-cols-1 gap-2">
            {mountedDirectories.map((dir, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between p-2.5 bg-white border border-neutral-200 rounded-lg text-xs"
              >
                <div className="flex items-center gap-2.5 overflow-hidden">
                  <span className="material-symbols-outlined text-[16px] text-neutral-400">folder_open</span>
                  <span className="font-mono text-neutral-700 truncate">{dir}</span>
                </div>
                {/* Prevent deleting default folders */}
                {idx > 1 ? (
                  <button
                    onClick={() => {
                      setMountedDirectories(prev => prev.filter((_, i) => i !== idx));
                      // Untrack skills belonging to this source
                      setScannedSkills(prev => prev.filter(s => s.source !== dir));
                    }}
                    className="text-neutral-400 hover:text-red-600 transition-colors p-1 hover:bg-neutral-50 rounded"
                    title="Unmount directory"
                  >
                    <span className="material-symbols-outlined text-[15px] font-bold">delete</span>
                  </button>
                ) : (
                  <span className="text-[9px] text-neutral-400 font-mono tracking-tight font-semibold bg-neutral-100/70 px-1.5 py-0.5 rounded">System Root</span>
                )}
              </div>
            ))}
          </div>

          <form onSubmit={handleMountDirectory} className="pt-2 border-t border-dashed border-neutral-200 flex gap-2">
            <input
              type="text"
              required
              value={newDirPath}
              onChange={(e) => setNewDirPath(e.target.value)}
              placeholder="Enter system absolute or relative directory..."
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
            <p className="text-[10px] text-emerald-600 font-sans font-medium select-none animate-pulse">
              ✓ {successMsg}
            </p>
          )}
        </div>

        {/* Section 2: YAML header files list */}
        <div className="space-y-3">
          <div className="flex items-center justify-between px-1">
            <h3 className="text-[11px] font-extrabold text-[#111111] font-mono tracking-wider uppercase">Scanned Manual Specifications</h3>
            <span className="text-[10px] text-neutral-400 font-semibold font-mono">{scannedSkills.length} SKILLS FOUND</span>
          </div>

          <div className="border border-neutral-200/80 bg-white rounded-xl divide-y divide-neutral-100 overflow-hidden shadow-3xs">
            {scannedSkills.map(skill => (
              <div
                key={skill.key}
                className="p-3.5 flex items-start justify-between gap-4 hover:bg-neutral-50/20 transition-colors"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs font-bold text-neutral-800 font-mono">🏷️ {skill.label}</span>
                    <span className="text-[8.5px] font-mono text-neutral-500 bg-neutral-100 px-1.5 py-0.2 rounded font-semibold">{skill.source}</span>
                  </div>
                  <p className="text-[11px] text-neutral-500 leading-relaxed font-normal">{skill.desc}</p>
                </div>

                {/* Right hand toggle and indicator status */}
                <div className="flex flex-col items-end gap-1.5 flex-shrink-0">
                  <button
                    type="button"
                    onClick={() => handleToggleGlobalSkill(skill.key)}
                    className={`w-9 h-5 rounded-full p-0.5 transition-all duration-300 relative cursor-pointer flex items-center ${
                      skill.isActiveGlobally ? 'bg-neutral-900 justify-end' : 'bg-neutral-200 justify-start'
                    }`}
                    title="Toggle global workspace validation inject"
                  >
                    <span className="w-4 h-4 rounded-full bg-white shadow-3xs block" />
                  </button>
                  {skill.isActiveGlobally ? (
                    <span className="text-[7.5px] uppercase font-mono text-emerald-700 font-extrabold bg-emerald-50 border border-emerald-150 px-1 py-0.5 rounded">GLOBAL ACTIVE</span>
                  ) : (
                    <span className="text-[7.5px] uppercase font-mono text-neutral-400 bg-neutral-50 px-1 py-0.5 rounded border border-neutral-200/40">INACTIVE</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

      </div>
    </div>
  );
};
