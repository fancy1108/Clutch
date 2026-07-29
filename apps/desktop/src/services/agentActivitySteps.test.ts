import { describe, expect, it } from 'vitest';
import {
  collapseRedundantTodoSteps,
  humanizeActivityStep,
  isGenericToolTitle,
  normalizeToolStepForDisplay,
  normalizeToolStepsForDisplay,
  parseAgentActivitySteps,
  parseToolStepDetail,
  classifyDeliverableIntent,
  decomposeUserGoals,
  pickPrimaryHtmlPath,
  resolveLiveActivitySteps,
  titleFromTodoDetail,
  toolStepsFromActivityLogs,
  wantsBrowserPreview,
  verbGroupHeaderLabel,
} from './agentActivitySteps';
import type { ToolStep } from '../types';

describe('pickPrimaryHtmlPath', () => {
  it('returns null when no html paths', () => {
    expect(pickPrimaryHtmlPath(['src/a.ts', 'README.md'])).toBeNull();
  });

  it('prefers index.html over other html files', () => {
    expect(pickPrimaryHtmlPath(['report.html', 'dist/index.html', 'notes.htm'])).toBe(
      'dist/index.html',
    );
  });

  it('falls back to the last html path', () => {
    expect(pickPrimaryHtmlPath(['a.md', 'page.html', 'other.htm'])).toBe('other.htm');
  });
});

describe('deliverable intent (need → kind)', () => {
  it('infers image without the user naming a file type', () => {
    const text = '搜索一下关于金华的介绍，总结一下，再画一张好看的';
    const goals = decomposeUserGoals(text);
    expect(goals.has('search')).toBe(true);
    expect(goals.has('visualize')).toBe(true);
    expect(classifyDeliverableIntent(text)).toBe('image');
    expect(wantsBrowserPreview(text)).toBe(false);
  });

  it('treats infographic / 信息图 as image intent', () => {
    expect(classifyDeliverableIntent('搜索 AI Agent 知识点并生成信息图可视化')).toBe(
      'image',
    );
    expect(classifyDeliverableIntent('Generate an infographic of the architecture')).toBe(
      'image',
    );
  });

  it('infers present/html from browsable-page language', () => {
    expect(classifyDeliverableIntent('帮我做个能打开看的金华介绍')).toBe('html');
    expect(wantsBrowserPreview('做个落地页展示产品')).toBe(true);
    expect(wantsBrowserPreview('Create a webpage about Jinhua')).toBe(true);
  });

  it('keeps answer/code from becoming browser preview', () => {
    expect(classifyDeliverableIntent('金华怎么样')).toBe('answer');
    expect(wantsBrowserPreview('写一段 Python 代码')).toBe(false);
    expect(wantsBrowserPreview('总结一下金华')).toBe(false);
  });

  it('supports mixed page + poster', () => {
    expect(classifyDeliverableIntent('做个介绍站并配海报')).toBe('mixed');
    expect(wantsBrowserPreview('生成一个网页，并配一张封面图')).toBe(true);
  });
});

describe('parseToolStepDetail', () => {
  it('keeps plain target without result marker', () => {
    expect(parseToolStepDetail('https://example.com/a')).toEqual({
      target: 'https://example.com/a',
      body: null,
      isError: false,
      meta: null,
    });
  });

  it('splits target and result preview', () => {
    const parsed = parseToolStepDetail(
      'https://example.com/a\n\n── result (1,204 chars) ──\nHello events',
    );
    expect(parsed.target).toBe('https://example.com/a');
    expect(parsed.body).toBe('Hello events');
    expect(parsed.isError).toBe(false);
    expect(parsed.meta).toBe('1,204 chars');
  });

  it('extracts url from raw args JSON', () => {
    expect(
      parseToolStepDetail(
        '{"url":"https://m.weibo.cn/search?q=1","timeout_sec":20}',
      ).target,
    ).toBe('https://m.weibo.cn/search?q=1');
  });
});

describe('normalizeToolStepForDisplay', () => {
  it('rewrites legacy web fetch titles and kind', () => {
    expect(isGenericToolTitle('web fetch web_fetch', 'web_fetch')).toBe(true);
    const step = normalizeToolStepForDisplay({
      id: '1',
      kind: 'other',
      tool: 'web_fetch',
      status: 'completed',
      title: 'web fetch web_fetch',
      detail: '{"url":"https://www.shanghai.disney.com/events","timeout_sec":20}',
    });
    expect(step.kind).toBe('fetch');
    expect(step.title.toLowerCase()).toContain('fetched');
    expect(step.title.toLowerCase()).toContain('disney');
  });
});

describe('parseAgentActivitySteps', () => {
  it('extracts CHAT tool steps and humanizes tool names', () => {
    const steps = parseAgentActivitySteps([
      '2026-07-24T00:00:00Z [CHAT] Step 1: clutch-tools__read_file args={"path": "README.md"}',
      '2026-07-24T00:00:01Z [CHAT] Tool response length: 12 chars',
      '2026-07-24T00:00:02Z [CHAT] Step 2: clutch-tools__grep args={"pattern": "foo"}',
    ]);
    expect(steps).toHaveLength(2);
    expect(steps[0].shortTool).toBe('read_file');
    expect(steps[0].verb).toBe('Reading');
    expect(steps[0].focus).toBe('README.md');
    expect(steps[1].shortTool).toBe('grep');
    expect(steps[1].verb).toBe('Searching');
    expect(steps[1].focus).toContain('foo');
  });

  it('keeps only the last maxSteps', () => {
    const logs = Array.from({ length: 20 }, (_, i) =>
      `[CHAT] Step ${i + 1}: clutch-tools__read_file args={"path":"f${i}.txt"}`,
    );
    const steps = parseAgentActivitySteps(logs, { maxSteps: 3 });
    expect(steps).toHaveLength(3);
    expect(steps[0].step).toBe(18);
    expect(steps[2].step).toBe(20);
  });

  it('collapses consecutive duplicate tool+focus', () => {
    const steps = parseAgentActivitySteps([
      '[CHAT] Step 1: clutch-tools__grep args={"pattern":"Clutch"}',
      '[CHAT] Step 2: clutch-tools__grep args={"pattern":"Clutch"}',
      '[CHAT] Step 3: clutch-tools__read_file args={"path":"README.md"}',
    ]);
    expect(steps).toHaveLength(2);
    expect(steps[0].shortTool).toBe('grep');
    expect(steps[1].shortTool).toBe('read_file');
  });

  it('scopes to the latest Step 1 wave (current turn)', () => {
    const steps = parseAgentActivitySteps([
      '[CHAT] Step 1: clutch-tools__list_dir args={"path":"."}',
      '[CHAT] Step 2: clutch-tools__run_terminal_cmd args={"command":"echo hi"}',
      '[CHAT] Step 1: clutch-tools__apply_patch args={"patch":"*** Delete File: teste.txt"}',
    ]);
    expect(steps).toHaveLength(1);
    expect(steps[0].verb).toBe('Deleting');
    expect(steps[0].focus).toBe('teste.txt');
  });
});

describe('humanizeActivityStep', () => {
  it('maps list_dir and shell', () => {
    expect(humanizeActivityStep('list_dir', '{"path":"."}')).toMatchObject({
      verb: 'Listing',
      focus: '.',
    });
    expect(
      humanizeActivityStep('run_terminal_cmd', '{"command":"echo hi"}'),
    ).toMatchObject({
      verb: 'Running',
      focus: 'echo hi',
    });
  });

  it('maps web_fetch host and web_search query', () => {
    expect(
      humanizeActivityStep(
        'web_fetch',
        '{"url":"https://www.shanghai.disney.com/events"}',
      ),
    ).toMatchObject({
      verb: 'Fetched',
      detail: 'https://www.shanghai.disney.com/events',
    });
    const search = humanizeActivityStep('web_search', '{"query":"迪士尼 活动"}');
    expect(search.verb).toBe('Searched');
    expect(search.focus).toContain('迪士尼');
  });

  it('maps todo_write to in_progress content, not Update N todos', () => {
    const human = humanizeActivityStep(
      'todo_write',
      JSON.stringify({
        todos: [
          { id: '1', content: '整理中国古代著名皇帝及事件', status: 'completed' },
          { id: '2', content: '生成包含皇帝和事件的HTML页面', status: 'in_progress' },
        ],
      }),
    );
    expect(human.verb).toBe('Todos');
    expect(human.focus).toContain('生成包含皇帝和事件的HTML页面');
    expect(human.detail).toContain('[in_progress]');
  });
});

describe('todo step display cleanup', () => {
  it('titleFromTodoDetail prefers in_progress target', () => {
    expect(
      titleFromTodoDetail(
        '[completed] 整理皇帝\n[in_progress] 生成HTML页面',
      ),
    ).toBe('Todos · 生成HTML页面');
  });

  it('collapses consecutive todo_write steps into one', () => {
    const steps: ToolStep[] = [
      {
        id: 'a',
        kind: 'other',
        tool: 'todo_write',
        status: 'completed',
        title: 'Update 2 todos',
        detail: '[pending] a\n[pending] b',
      },
      {
        id: 'b',
        kind: 'other',
        tool: 'todo_write',
        status: 'completed',
        title: 'Update 2 todos',
        detail: '[completed] a\n[in_progress] b',
      },
      {
        id: 'c',
        kind: 'other',
        tool: 'todo_write',
        status: 'completed',
        title: 'Update 2 todos',
        detail: '[completed] a\n[completed] b',
      },
    ];
    const collapsed = collapseRedundantTodoSteps(steps);
    expect(collapsed).toHaveLength(1);
    expect(collapsed[0]?.id).toBe('c');
  });

  it('normalizeToolStepsForDisplay hides todo_write by default (Todo card is SSOT)', () => {
    const out = normalizeToolStepsForDisplay([
      {
        id: '1',
        kind: 'other',
        tool: 'todo_write',
        status: 'completed',
        title: 'Update 2 todos',
        detail: '[completed] 整理皇帝\n[in_progress] 生成HTML',
      },
      {
        id: '2',
        kind: 'fetch',
        tool: 'web_fetch',
        status: 'completed',
        title: 'Fetched zhihu.com',
        detail: 'https://zhihu.com/search',
      },
    ]);
    expect(out).toHaveLength(1);
    expect(out[0]?.tool).toBe('web_fetch');
  });

  it('normalizeToolStepsForDisplay can keep todos when includeTodos', () => {
    const out = normalizeToolStepsForDisplay(
      [
        {
          id: '1',
          kind: 'other',
          tool: 'todo_write',
          status: 'completed',
          title: 'Update 2 todos',
          detail: '[completed] 整理皇帝\n[in_progress] 生成HTML',
        },
      ],
      { includeTodos: true },
    );
    expect(out).toHaveLength(1);
    expect(out[0]?.title).toMatch(/Todos/);
    expect(out[0]?.title).not.toMatch(/Update 2 todos/i);
  });
});

describe('verbGroupHeaderLabel', () => {
  it('groups completed kinds like Grok', () => {
    expect(
      verbGroupHeaderLabel([
        {
          id: '1',
          kind: 'read',
          tool: 'read_file',
          status: 'completed',
          title: 'Read a',
        },
        {
          id: '2',
          kind: 'read',
          tool: 'read_file',
          status: 'completed',
          title: 'Read b',
        },
        {
          id: '3',
          kind: 'search',
          tool: 'grep',
          status: 'completed',
          title: 'Search x',
        },
      ]),
    ).toBe('Read 2 files, Searched 1 query');
  });

  it('groups fetch pages like Cursor/Grok', () => {
    expect(
      verbGroupHeaderLabel([
        {
          id: '1',
          kind: 'fetch',
          tool: 'web_fetch',
          status: 'completed',
          title: 'Fetched a.example',
        },
        {
          id: '2',
          kind: 'fetch',
          tool: 'web_fetch',
          status: 'completed',
          title: 'Fetched b.example',
        },
      ]),
    ).toBe('Fetched 2 pages');
  });

  it('uses progressive verbs while running', () => {
    expect(
      verbGroupHeaderLabel([
        {
          id: '1',
          kind: 'list',
          tool: 'list_dir',
          status: 'completed',
          title: 'List .',
        },
        {
          id: '2',
          kind: 'search',
          tool: 'grep',
          status: 'running',
          title: 'Search Clutch',
        },
      ]),
    ).toBe('Searching 1 query, Listing 1 dir');
  });
});

describe('toolStepsFromActivityLogs', () => {
  it('maps log steps into ToolStep shapes', () => {
    const steps = toolStepsFromActivityLogs([
      '[CHAT] Step 1: clutch-tools__read_file args={"path":"README.md"}',
    ]);
    expect(steps).toHaveLength(1);
    expect(steps[0].kind).toBe('read');
    expect(steps[0].status).toBe('running');
    expect(steps[0].title).toContain('Reading');
  });
});

describe('resolveLiveActivitySteps', () => {
  const priorWave = [
    '[CHAT] Step 1: clutch-tools__list_dir args={"path":"."}',
    '[CHAT] Step 2: clutch-tools__todo_write args={"todos":[]}',
  ];

  it('prefers structured pending steps', () => {
    const pending = [
      {
        id: 't1',
        kind: 'edit' as const,
        tool: 'apply_patch',
        status: 'running' as const,
        title: 'Patching',
      },
    ];
    expect(resolveLiveActivitySteps(pending, priorWave, { awaiting: false })).toEqual(pending);
  });

  it('does not resurrect prior log wave while thinking (empty pending)', () => {
    expect(resolveLiveActivitySteps([], priorWave, { awaiting: false })).toEqual([]);
    expect(resolveLiveActivitySteps(undefined, priorWave, { awaiting: false })).toEqual([]);
  });

  it('falls back to logs only while awaiting approval without pending', () => {
    const steps = resolveLiveActivitySteps([], priorWave, { awaiting: true });
    expect(steps.length).toBeGreaterThan(0);
    expect(steps[steps.length - 1].status).toBe('awaiting');
  });
});
