import { SIDECAR_BASE as BASE, sidecarFetch } from './sidecarUrl';

export type DesignSpec = {
  name?: string;
  rationale?: string;
  colors?: Record<string, string[]>;
  typography?: {
    fontFamily?: string;
    samples?: Array<{ label?: string; size?: string; weight?: string }>;
  };
  components?: string[];
};

export type DesignProcessEntry = {
  role: string;
  text: string;
  status?: string;
  at?: string;
  /** Step-by-step model reasoning (e.g. big-pickle free models). */
  reasoning_content?: string;
  /** 1-based round index when provided by the session manifest. */
  round_index?: number;
};

/** One user instruction round and its assistant follow-ups. */
export type DesignRound = {
  /** 0-based round index (matches versioned screen paths `main_r{N}.html`). */
  index: number;
  user_prompt: string;
  entries: DesignProcessEntry[];
  reasoning_content?: string;
};

export type DesignRoundHistoryEntry = {
  round_index: number;
  screen_id: string;
  html_path?: string;
  prompt?: string;
  reasoning_content?: string | null;
  process_log?: DesignProcessEntry[];
  at?: string;
};

export type DesignScreen = {
  id: string;
  name: string;
  position?: { x: number; y: number };
  html_path?: string;
  html?: string;
};

export type DesignSession = {
  id: string;
  run_id: string;
  name: string;
  prompt: string;
  phase: string;
  status: string;
  device?: string;
  process_log?: DesignProcessEntry[];
  /** Optional manifest rounds (backend); derived from process_log when absent. */
  rounds?: DesignRound[];
  round_count?: number;
  round_history?: DesignRoundHistoryEntry[];
  spec?: DesignSpec | null;
  screens: DesignScreen[];
  design_md: string;
  path: string;
  prototype_approved?: boolean;
  react_approved?: boolean;
  react_ready?: boolean;
  preview_url?: string | null;
  react_path?: string;
  generate_source?: string;
  error?: string | null;
  reference_image?: string | null;
  reference_image_url?: string | null;
  reference_md_name?: string | null;
  reference_md_text?: string | null;
  reference_url?: string | null;
  url_snapshot?: {
    url?: string;
    host?: string;
    title?: string;
    description?: string;
  } | null;
  thumbnail_url?: string | null;
  ui_preview_url?: string | null;
  last_iterate_action?: string | null;
  last_iterate_screen_id?: string | null;
  artifact_paths?: string[];
};

export type CodingHandoff = {
  run_id?: string;
  project_id: string;
  name: string;
  instruction: string;
  design_md_path: string;
  react_path: string;
  workspace_relative: string;
};

/** Strip iterate metadata appended by the backend (`[Selected:…]`). */
export function stripDesignIterateMeta(text: string): string {
  return text.replace(/\s*\[Selected:[^\]]*\]\s*$/i, '').trim();
}

/** Group process_log entries into user-prompt rounds for history switching. */
export function parseDesignRounds(
  processLog: DesignProcessEntry[] | undefined,
  manifestRounds?: DesignRound[],
  roundHistory?: DesignRoundHistoryEntry[],
): DesignRound[] {
  if (roundHistory && roundHistory.length > 0) {
    return roundHistory.map((entry) => ({
      index: entry.round_index,
      user_prompt: stripDesignIterateMeta(entry.prompt || ''),
      entries: entry.process_log || [],
      reasoning_content:
        entry.reasoning_content ||
        entry.process_log?.find((e) => e.reasoning_content)?.reasoning_content ||
        undefined,
    }));
  }
  if (manifestRounds && manifestRounds.length > 0) {
    return manifestRounds.map((round, i) => ({
      index: round.index ?? i,
      user_prompt: stripDesignIterateMeta(round.user_prompt || ''),
      entries: round.entries || [],
      reasoning_content:
        round.reasoning_content ||
        round.entries?.find((e) => e.reasoning_content)?.reasoning_content,
    }));
  }
  const log = processLog || [];
  const rounds: DesignRound[] = [];
  let current: DesignRound | null = null;
  let autoIndex = -1;

  for (const entry of log) {
    if (entry.role === 'user') {
      if (current) rounds.push(current);
      autoIndex += 1;
      current = {
        index: entry.round_index ?? autoIndex,
        user_prompt: stripDesignIterateMeta(entry.text),
        entries: [],
        reasoning_content: undefined,
      };
      continue;
    }
    if (!current) {
      autoIndex += 1;
      current = {
        index: entry.round_index ?? autoIndex,
        user_prompt: '',
        entries: [],
        reasoning_content: undefined,
      };
    }
    current.entries.push(entry);
    if (entry.reasoning_content) {
      current.reasoning_content = entry.reasoning_content;
    }
  }
  if (current) rounds.push(current);
  return rounds;
}

/** Versioned screen file id, e.g. `main` + round 2 → `main_r2`. */
export function versionedDesignScreenId(screenId: string, roundIndex: number): string {
  const base = (screenId || 'main').replace(/_r\d+$/i, '');
  return `${base}_r${roundIndex}`;
}

/** Sidecar path for a versioned HTML screen preview. */
export function designScreenVersionPath(
  runId: string,
  screenId: string,
  roundIndex: number,
): string {
  const versioned = versionedDesignScreenId(screenId, roundIndex);
  return `/api/design/sessions/${encodeURIComponent(runId)}/screens/${encodeURIComponent(versioned)}`;
}

async function parseJson<T>(response: Response): Promise<T> {
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = (data as { detail?: { message?: string } | string }).detail;
    const message =
      typeof detail === 'object' && detail?.message
        ? detail.message
        : typeof detail === 'string'
          ? detail
          : response.statusText;
    throw new Error(message || `Design API ${response.status}`);
  }
  return data as T;
}

export async function ensureDesignSession(input: {
  run_id: string;
  title?: string;
  prompt?: string;
}): Promise<DesignSession> {
  const response = await sidecarFetch(`${BASE}/api/design/sessions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  });
  return parseJson<DesignSession>(response);
}

export async function getDesignSession(runId: string): Promise<DesignSession> {
  const response = await sidecarFetch(`${BASE}/api/design/sessions/${encodeURIComponent(runId)}`);
  return parseJson<DesignSession>(response);
}

/** Raw screen HTML (same endpoint as sidebar live thumb) — used when session JSON omits/ lags html. */
export async function getDesignScreenHtml(runId: string, screenId: string): Promise<string> {
  const response = await sidecarFetch(
    `${BASE}/api/design/sessions/${encodeURIComponent(runId)}/screens/${encodeURIComponent(screenId)}`,
  );
  if (!response.ok) {
    throw new Error(`Design screen ${response.status}`);
  }
  return response.text();
}

export async function generateDesignSession(
  runId: string,
  body: {
    prompt: string;
    device?: string;
    reference_image?: string | null;
    reference_md?: string | null;
    reference_md_name?: string | null;
    reference_url?: string | null;
  },
): Promise<DesignSession> {
  const response = await sidecarFetch(
    `${BASE}/api/design/sessions/${encodeURIComponent(runId)}/generate`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    },
  );
  return parseJson<DesignSession>(response);
}

export async function iterateDesignSession(
  runId: string,
  instruction: string,
  options?: {
    target_kind?: string | null;
    target_id?: string | null;
    element_path?: string | null;
    element_label?: string | null;
    mode?: 'modify' | 'add' | 'auto' | null;
  },
): Promise<DesignSession> {
  const response = await sidecarFetch(
    `${BASE}/api/design/sessions/${encodeURIComponent(runId)}/iterate`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        instruction,
        target_kind: options?.target_kind ?? null,
        target_id: options?.target_id ?? null,
        element_path: options?.element_path ?? null,
        element_label: options?.element_label ?? null,
        mode: options?.mode ?? 'auto',
      }),
    },
  );
  return parseJson<DesignSession>(response);
}

export async function approveDesignPrototype(runId: string): Promise<DesignSession> {
  const response = await sidecarFetch(
    `${BASE}/api/design/sessions/${encodeURIComponent(runId)}/approve-prototype`,
    { method: 'POST' },
  );
  return parseJson<DesignSession>(response);
}

export async function generateDesignReact(runId: string): Promise<DesignSession> {
  const response = await sidecarFetch(
    `${BASE}/api/design/sessions/${encodeURIComponent(runId)}/generate-react`,
    { method: 'POST' },
  );
  return parseJson<DesignSession>(response);
}

export async function startDesignPreview(
  runId: string,
): Promise<{ url: string; port: number; status: string }> {
  const response = await sidecarFetch(
    `${BASE}/api/design/sessions/${encodeURIComponent(runId)}/preview/start`,
    { method: 'POST' },
  );
  return parseJson(response);
}

export async function stopDesignPreview(runId: string): Promise<void> {
  const response = await sidecarFetch(
    `${BASE}/api/design/sessions/${encodeURIComponent(runId)}/preview/stop`,
    { method: 'POST' },
  );
  await parseJson(response);
}

export async function approveDesignReact(runId: string): Promise<DesignSession> {
  const response = await sidecarFetch(
    `${BASE}/api/design/sessions/${encodeURIComponent(runId)}/approve-react`,
    { method: 'POST' },
  );
  return parseJson<DesignSession>(response);
}

export async function sendDesignToCoding(runId: string): Promise<CodingHandoff> {
  const response = await sidecarFetch(
    `${BASE}/api/design/sessions/${encodeURIComponent(runId)}/send-to-coding`,
    { method: 'POST' },
  );
  return parseJson<CodingHandoff>(response);
}
