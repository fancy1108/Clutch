import { describe, expect, it } from 'vitest';
import {
  humanizeActivityStep,
  parseAgentActivitySteps,
  toolStepsFromActivityLogs,
  verbGroupHeaderLabel,
} from './agentActivitySteps';

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
    ).toBe('Read 2 files, Searched 1 pattern');
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
    ).toBe('Searching 1 pattern, Listing 1 dir');
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
