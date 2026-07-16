import React, { useState, useEffect, useCallback } from 'react';
import { fetchOpenSpecList, fetchOpenSpecStatus, type OpenSpecChange } from '../services/openspecApi';
import { LegacyIcon } from './ui/LegacyIcon';

const artifactStatusColor: Record<string, string> = {
  ready: 'text-emerald-600 bg-emerald-50 border-emerald-200',
  blocked: 'text-amber-600 bg-amber-50 border-amber-200',
  pending: 'text-neutral-400 bg-neutral-50 border-neutral-200',
};

export const OpenSpecPanel: React.FC = () => {
  const [changes, setChanges] = useState<OpenSpecChange[]>([]);
  const [available, setAvailable] = useState<boolean | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedChange, setSelectedChange] = useState<string | null>(null);
  const [changeDetail, setChangeDetail] = useState<Record<string, unknown> | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const loadList = useCallback(async () => {
    setLoading(true);
    setError(null);
    const result = await fetchOpenSpecList();
    setAvailable(result.available);
    if (result.error) setError(result.error);
    setChanges(result.changes || []);
    setLoading(false);
  }, []);

  useEffect(() => {
    void loadList();
  }, [loadList]);

  const handleSelectChange = async (name: string) => {
    setSelectedChange(name);
    setChangeDetail(null);
    setDetailLoading(true);
    const result = await fetchOpenSpecStatus(name);
    if (result.status) setChangeDetail(result.status);
    setDetailLoading(false);
  };

  const getArtifactStatusBadge = (status?: string) => {
    const color = artifactStatusColor[status ?? ''] || 'text-neutral-400 bg-neutral-50 border-neutral-200';
    return (
      <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded border ${color}`}>
        {status ?? 'unknown'}
      </span>
    );
  };

  return (
    <div className="flex flex-col h-full bg-neutral-50/30">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-neutral-100 shrink-0">
        <div className="flex items-center gap-2">
          <LegacyIcon name="description" className="text-[16px] text-neutral-600" />
          <span className="text-[10px] font-bold text-neutral-500 uppercase tracking-widest">
            OpenSpec
          </span>
          {available === true && (
            <span className="text-[8px] font-bold text-emerald-600 bg-emerald-50 border border-emerald-200 rounded px-1 py-0.5">
              CLI
            </span>
          )}
          {available === false && (
            <span className="text-[8px] font-bold text-rose-600 bg-rose-50 border border-rose-200 rounded px-1 py-0.5">
              N/A
            </span>
          )}
        </div>
        <button
          type="button"
          onClick={() => void loadList()}
          className="text-neutral-400 hover:text-neutral-700 transition-colors p-1"
          title="Refresh"
        >
          <LegacyIcon name="sync" className="text-[14px] text-neutral-400 hover:text-neutral-700 transition-colors" />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {loading && (
          <p className="text-[10px] text-neutral-400 font-mono text-center py-4">Loading...</p>
        )}

        {!loading && available === false && (
          <div className="text-center py-6">
            <LegacyIcon name="info" className="text-[20px] text-neutral-300 mb-2" />
            <p className="text-[10px] text-neutral-400 font-medium">
              OpenSpec CLI not available
            </p>
            {error && (
              <p className="text-[9px] text-neutral-400 font-mono mt-1 px-2 break-all">
                {error}
              </p>
            )}
            <p className="text-[9px] text-neutral-400 mt-2">
              Install: <code className="text-[8px] bg-neutral-100 px-1 py-0.5 rounded">npm install -g @fission-ai/openspec</code>
            </p>
          </div>
        )}

        {!loading && available === true && changes.length === 0 && (
          <div className="text-center py-6">
            <LegacyIcon name="add_circle" className="text-[20px] text-neutral-300 mb-2" />
            <p className="text-[10px] text-neutral-400 font-medium">
              No changes yet
            </p>
            <p className="text-[9px] text-neutral-400 mt-1">
              Run: <code className="text-[8px] bg-neutral-100 px-1 py-0.5 rounded">openspec new change &lt;name&gt;</code>
            </p>
          </div>
        )}

        {!loading && available === true && changes.map((ch) => {
          const name = ch.name ?? ch.id ?? 'unnamed';
          const isSelected = selectedChange === name;
          const chStatus = ch.status as string | undefined;
          return (
            <div key={name}>
              <button
                type="button"
                onClick={() => handleSelectChange(name)}
                className={`w-full text-left p-2.5 rounded-xl border transition-all ${
                  isSelected
                    ? 'border-neutral-400 bg-white shadow-sm ring-1 ring-neutral-200'
                    : 'border-neutral-200/50 bg-white hover:border-neutral-300 shadow-xs'
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="min-w-0 flex-1">
                    <p className="text-[11px] font-bold text-neutral-800 truncate">{name}</p>
                    <p className="text-[9px] text-neutral-400 font-mono mt-0.5">
                      {chStatus ?? 'unknown'}
                    </p>
                  </div>
                  <LegacyIcon name="chevron_right" className="text-[14px] text-neutral-300 shrink-0" />
                </div>
              </button>

              {/* Detail panel */}
              {isSelected && detailLoading && (
                <div className="ml-2 mt-1 p-2 bg-neutral-50 rounded-lg border border-neutral-100">
                  <p className="text-[9px] text-neutral-400 font-mono">Loading detail...</p>
                </div>
              )}

              {isSelected && changeDetail && !detailLoading && (
                <div className="ml-2 mt-1 p-2.5 bg-neutral-50 rounded-lg border border-neutral-100 space-y-1.5">
                  <p className="text-[9px] font-bold text-neutral-600 uppercase tracking-wider">Artifacts</p>
                  {(changeDetail.artifacts as Array<{ id: string; status: string }> | undefined)?.map((art) => (
                    <div key={art.id} className="flex items-center justify-between text-[10px]">
                      <span className="text-neutral-700 font-medium">{art.id}</span>
                      {getArtifactStatusBadge(art.status)}
                    </div>
                  ))}
                  {!changeDetail.artifacts && (
                    <p className="text-[9px] text-neutral-400">No artifact detail available</p>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Footer */}
      {available === true && (
        <div className="px-3 py-2 border-t border-neutral-100 shrink-0">
          <a
            href="https://github.com/Fission-AI/OpenSpec"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 text-[9px] text-neutral-400 hover:text-neutral-600 transition-colors"
          >
            <LegacyIcon name="bolt" className="text-[11px] text-neutral-400" />
            OpenSpec docs
          </a>
        </div>
      )}
    </div>
  );
};