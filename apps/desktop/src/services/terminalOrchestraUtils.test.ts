import { describe, expect, it } from 'vitest';
import {
  agentDisplayName,
  computeLaneGridPageCount,
  computeLaneLayout,
  orderLanesForGrid,
  expandedLanes,
  collapsedLanes,
  laneGridPageIndex,
  sliceLanesForGridPage,
  resolveAgentTypeFromDispatchTarget,
  findLaneIdForAgentType,
  collectHandoffLaneTranscripts,
  findLaneForDispatchSource,
  findLaneForDispatchTarget,
  isDispatchEntryTargetPending,
  laneHeaderAgentName,
  parseInputAgentMention,
  resolveAgentFromDispatchTarget,
  resolveDispatchTargetAgent,
  resolvePtyInjectWarmupMs,
  isPtyOutputReadyForInject,
  buildOptimisticDispatchEntry,
  buildHandoffSendToBarText,
  mergeDispatchLogs,
  OPTIMISTIC_DISPATCH_ID_PREFIX,
  sessionHasTerminalHistory,
  sessionHasPersistableContent,
  sessionHasActiveTerminalLanes,
  isArchivedTerminalHistoryView,
  normalizeTerminalSessionForResume,
  shouldConfirmLeavingTerminal,
  shouldConfirmLeavingTerminalForNewChat,
  orchestratorInputHasUserTask,
  isHandoffDispatchEntry,
} from './terminalOrchestraUtils';
import type { PtyLane } from '../types';

const sampleLane = (overrides: Partial<PtyLane> = {}): PtyLane => ({
  lane_id: 'lane_a',
  agent_type: 'claude-cli',
  label: 'Task',
  status: 'running',
  focused: true,
  collapsed: false,
  run_id: 'run_1',
  ...overrides,
});

describe('terminalOrchestraUtils', () => {
  it('maps agent types to display names', () => {
    expect(agentDisplayName('claude-cli')).toBe('Claude Code');
    expect(agentDisplayName('opencode-cli')).toBe('OpenCode');
    expect(agentDisplayName('codex-cli')).toBe('Codex CLI');
    expect(agentDisplayName('claude-cli', '主开发')).toBe('主开发');
  });

  it('prefers configured agent name for lane headers', () => {
    const lane = sampleLane({ agent_type: 'claude-cli' });
    const agents = [{ id: 'a1', name: '主开发', agentType: 'claude-cli' }];
    expect(laneHeaderAgentName(lane, agents)).toBe('主开发');
    expect(laneHeaderAgentName(lane, [])).toBe('Claude Code');
  });

  it('resolves @OpenCode to the configured agent via dispatchTarget when name differs', () => {
    const agents = [
      { id: 'oc-1', name: 'Opencode', dispatchTarget: 'OpenCode' },
      { id: 'oc-2', name: 'Opencode2', dispatchTarget: 'OpenCode' },
    ];
    expect(parseInputAgentMention('@OpenCode 总结项目', agents)).toEqual({
      agentId: 'oc-1',
      name: 'Opencode',
    });
    expect(parseInputAgentMention('@Opencode2 继续', agents)).toEqual({
      agentId: 'oc-2',
      name: 'Opencode2',
    });
  });

  it('resolves canonical dispatch target when only one agent matches', () => {
    const agents = [{ id: 'oc-2', name: 'Opencode2', dispatchTarget: 'OpenCode' }];
    expect(parseInputAgentMention('@OpenCode 总结项目', agents)).toEqual({
      agentId: 'oc-2',
      name: 'Opencode2',
    });
    expect(resolveAgentFromDispatchTarget('OpenCode', agents)).toEqual({
      agentId: 'oc-2',
      name: 'Opencode2',
    });
  });

  it('resolves @Mimo via dispatch target', () => {
    const agents = [{ id: 'mimo-1', name: 'Mimo', dispatchTarget: 'Mimo' }];
    expect(parseInputAgentMention('@Mimo 你好', agents)).toEqual({
      agentId: 'mimo-1',
      name: 'Mimo',
    });
  });

  it('does not guess when multiple agents share the same dispatch target', () => {
    const agents = [
      { id: 'oc-1', name: 'Alpha', dispatchTarget: 'OpenCode' },
      { id: 'oc-2', name: 'Beta', dispatchTarget: 'OpenCode' },
    ];
    expect(parseInputAgentMention('@OpenCode task', agents)).toBeNull();
    expect(resolveAgentFromDispatchTarget('OpenCode', agents)).toBeNull();
  });

  it('resolves dispatch target from footer selection when @OpenCode is ambiguous', () => {
    const agents = [
      { id: 'oc-1', name: 'Opencode', dispatchTarget: 'OpenCode' },
      { id: 'oc-2', name: 'Opencode2', dispatchTarget: 'OpenCode' },
    ];
    expect(
      resolveDispatchTargetAgent('@OpenCode task', 'OpenCode', agents, 'oc-2'),
    ).toEqual({ agentId: 'oc-2', name: 'Opencode2' });
  });

  it('finds opencode source lane by configured agent name', () => {
    const lanes = [
      sampleLane({
        lane_id: 'lane_oc1',
        agent_type: 'opencode-cli',
        configured_agent_id: 'oc-1',
        configured_agent_name: 'Opencode',
      }),
      sampleLane({
        lane_id: 'lane_oc2',
        agent_type: 'opencode-cli',
        configured_agent_id: 'oc-2',
        configured_agent_name: 'Opencode2',
      }),
    ];
    expect(findLaneForDispatchSource(lanes, 'Opencode2')?.lane_id).toBe('lane_oc2');
  });

  it('uses lane configured_agent_id when multiple agents share a CLI type', () => {
    const lane = sampleLane({
      agent_type: 'opencode-cli',
      configured_agent_id: 'oc-2',
      configured_agent_name: 'Opencode2',
    });
    const agents = [
      { id: 'oc-1', name: 'Opencode', agentType: 'opencode-cli' },
      { id: 'oc-2', name: 'Opencode2', agentType: 'opencode-cli' },
    ];
    expect(laneHeaderAgentName(lane, agents)).toBe('Opencode2');
    expect(
      laneHeaderAgentName(
        { ...lane, configured_agent_name: undefined, configured_agent_id: 'oc-1' },
        agents,
      ),
    ).toBe('Opencode');
  });

  it('resolves dispatch target from preview for graph syntax (@Target from @Source)', () => {
    const agents = [
      { id: 'claude-1', name: 'Claude Code', dispatchTarget: 'Claude Code' },
      { id: 'codex-1', name: 'Codex CLI', dispatchTarget: 'Codex CLI' },
    ];
    const text = '@Codex CLI from @Claude Code：继续';
    expect(
      resolveDispatchTargetAgent(text, 'Codex CLI', agents, 'claude-1'),
    ).toEqual({ agentId: 'codex-1', name: 'Codex CLI' });
  });

  it('uses preview target for graph handoff when footer selected agent is the source', () => {
    const agents = [
      { id: 'claude-1', name: 'Claude Code', dispatchTarget: 'Claude Code' },
      { id: 'oc-1', name: 'Opencode', dispatchTarget: 'OpenCode' },
    ];
    const text = '@Claude Code from @Opencode 总结成一句话';
    expect(
      resolveDispatchTargetAgent(text, 'Claude Code', agents, 'oc-1'),
    ).toEqual({ agentId: 'claude-1', name: 'Claude Code' });
  });

  it('computes grid layout from expanded lane count', () => {
    expect(computeLaneLayout(1)).toBe('single');
    expect(computeLaneLayout(2)).toBe('pair');
    expect(computeLaneLayout(3)).toBe('split-3');
    expect(computeLaneLayout(4)).toBe('quad');
  });

  it('places focused lane in large bottom slot for split-3', () => {
    const lanes = [
      sampleLane({ lane_id: 'a', focused: false }),
      sampleLane({ lane_id: 'b', focused: false }),
      sampleLane({ lane_id: 'c', focused: true }),
    ];
    expect(orderLanesForGrid(lanes, 'split-3').map((l) => l.lane_id)).toEqual(['a', 'b', 'c']);
  });

  it('splits expanded and collapsed lanes', () => {
    const lanes = [
      sampleLane({ lane_id: 'a' }),
      sampleLane({ lane_id: 'b', collapsed: true }),
      sampleLane({ lane_id: 'c', status: 'queued' }),
    ];
    expect(expandedLanes(lanes).map((l) => l.lane_id)).toEqual(['a']);
    expect(collapsedLanes(lanes).map((l) => l.lane_id)).toEqual(['b', 'c']);
  });

  it('collects handoff transcripts for source lanes', () => {
    const lanes = [
      sampleLane({ lane_id: 'lane_claude', agent_type: 'claude-cli' }),
      sampleLane({ lane_id: 'lane_oc', agent_type: 'opencode-cli' }),
    ];
    expect(findLaneForDispatchSource(lanes, 'Claude Code')?.lane_id).toBe('lane_claude');
    const transcripts = collectHandoffLaneTranscripts(
      ['Claude Code'],
      lanes,
      (laneId) => (laneId === 'lane_claude' ? 'summary output' : ''),
      'OpenCode',
    );
    expect(transcripts).toEqual([
      { lane_id: 'lane_claude', agent: 'Claude Code', transcript: 'summary output' },
    ]);
  });

  it('falls back to all upstream lanes when source chips miss', () => {
    const lanes = [
      sampleLane({ lane_id: 'lane_claude', agent_type: 'claude-cli' }),
      sampleLane({ lane_id: 'lane_oc', agent_type: 'opencode-cli' }),
    ];
    const transcripts = collectHandoffLaneTranscripts(
      ['工作区'],
      lanes,
      (laneId) => (laneId === 'lane_claude' ? 'summary output' : ''),
      'OpenCode',
    );
    expect(transcripts).toEqual([
      { lane_id: 'lane_claude', agent: 'Claude Code', transcript: 'summary output' },
    ]);
  });

  it('treats only dispatch log as session terminal history', () => {
    expect(sessionHasTerminalHistory({ dispatch_log: [{ id: 'd1' }] })).toBe(true);
    expect(sessionHasTerminalHistory({ dispatch_log: [] })).toBe(false);
    expect(sessionHasTerminalHistory({})).toBe(false);
  });

  it('treats messages or dispatch log as persistable session content', () => {
    expect(sessionHasPersistableContent({ messages: [{ id: 'm1' }] })).toBe(true);
    expect(sessionHasPersistableContent({ dispatch_log: [{ id: 'd1' }] })).toBe(true);
    expect(sessionHasPersistableContent({ messages: [], dispatch_log: [] })).toBe(false);
    expect(sessionHasPersistableContent({})).toBe(false);
  });

  it('detects active terminal lanes and leave confirmation', () => {
    const agents = [{ id: 'a1', name: 'Claude Code', dispatchTarget: 'Claude Code' }];
    expect(
      sessionHasActiveTerminalLanes({ pty_lanes: [{ status: 'running' }, { status: 'completed' }] }),
    ).toBe(true);
    expect(
      sessionHasActiveTerminalLanes({ pty_lanes: [{ status: 'completed' }] }),
    ).toBe(false);
    expect(shouldConfirmLeavingTerminal({ dispatch_log: [] }, 'chat')).toBe(false);
    expect(
      shouldConfirmLeavingTerminal({ dispatch_log: [{ id: 'd1' }] }, 'terminal'),
    ).toBe(true);
    expect(
      shouldConfirmLeavingTerminal({ pty_lanes: [{ status: 'running' }] }, 'terminal'),
    ).toBe(false);
    expect(
      shouldConfirmLeavingTerminal({}, 'terminal', '@Claude Code fix the bug', agents),
    ).toBe(true);
  });

  it('skips leave confirm for preview-only terminal sessions', () => {
    const agents = [{ id: 'a1', name: 'Claude Code', dispatchTarget: 'Claude Code' }];
    const previewOnlyState = {
      dispatch_log: [],
      pty_lanes: [{ status: 'running' }],
    };
    expect(
      shouldConfirmLeavingTerminal(previewOnlyState, 'terminal'),
    ).toBe(false);
    expect(
      shouldConfirmLeavingTerminal(previewOnlyState, 'terminal', '@Claude Code ', agents),
    ).toBe(false);
    expect(
      shouldConfirmLeavingTerminal(
        previewOnlyState,
        'terminal',
        '@Claude Code fix the bug',
        agents,
      ),
    ).toBe(true);
  });

  it('archives terminal history only after leaving live terminal session', () => {
    const withHistory = { dispatch_log: [{ id: 'd1' }] };
    const live = { ...withHistory, pty_lanes: [{ status: 'running' }] };
    const archived = { ...withHistory, pty_lanes: [{ status: 'completed' }] };

    expect(isArchivedTerminalHistoryView(live, 'terminal')).toBe(false);
    expect(isArchivedTerminalHistoryView(live, 'chat')).toBe(false);
    expect(isArchivedTerminalHistoryView(archived, 'terminal')).toBe(false);
    expect(isArchivedTerminalHistoryView(archived, 'chat')).toBe(true);
    expect(isArchivedTerminalHistoryView({ dispatch_log: [] }, 'chat')).toBe(false);
  });

  it('normalizes stale running lanes when resuming terminal history', () => {
    const stale = {
      dispatch_log: [{ id: 'd1' }],
      pty_lanes: [{ status: 'running' }],
    };
    const normalized = normalizeTerminalSessionForResume(stale);
    expect(normalized.pty_lanes).toEqual([]);
    expect(isArchivedTerminalHistoryView(normalized, 'chat')).toBe(true);
    expect(normalizeTerminalSessionForResume({ dispatch_log: [] })).toEqual({ dispatch_log: [] });
  });

  it('skips new-chat confirm for preview-only terminal sessions', () => {
    const agents = [{ id: 'a1', name: 'Claude Code', dispatchTarget: 'Claude Code' }];
    expect(orchestratorInputHasUserTask('', agents)).toBe(false);
    expect(orchestratorInputHasUserTask('@Claude Code ', agents)).toBe(false);
    expect(orchestratorInputHasUserTask('@Claude Code fix the bug', agents)).toBe(true);
    expect(orchestratorInputHasUserTask('summarize the repo', agents)).toBe(true);

    const previewOnlyState = {
      dispatch_log: [],
      pty_lanes: [{ status: 'running' }],
    };
    expect(
      shouldConfirmLeavingTerminal(previewOnlyState, 'terminal'),
    ).toBe(false);
    expect(
      shouldConfirmLeavingTerminalForNewChat(previewOnlyState, 'terminal', '@Claude Code ', agents),
    ).toBe(false);
    expect(
      shouldConfirmLeavingTerminalForNewChat(
        { dispatch_log: [{ id: 'd1' }], pty_lanes: [{ status: 'running' }] },
        'terminal',
        '@Claude Code ',
        agents,
      ),
    ).toBe(true);
    expect(
      shouldConfirmLeavingTerminalForNewChat(
        previewOnlyState,
        'terminal',
        '@Claude Code fix the bug',
        agents,
      ),
    ).toBe(true);
  });

  it('detects handoff vs first-round switch dispatch entries', () => {
    expect(
      isHandoffDispatchEntry({
        dispatch_mode: 'switch',
        handoff_file: '',
        handoff_path: '',
      }),
    ).toBe(false);
    expect(
      isHandoffDispatchEntry({
        dispatch_mode: 'handoff',
        handoff_file: 'handoff-a→b.md',
        handoff_path: '.clutch/handoffs/handoff-a→b.md',
      }),
    ).toBe(true);
  });

  it('resolves dispatch target display names to agent types and lanes', () => {
    expect(resolveAgentTypeFromDispatchTarget('OpenCode')).toBe('opencode-cli');
    expect(resolveAgentTypeFromDispatchTarget('Codex CLI')).toBe('codex-cli');
    expect(resolveAgentTypeFromDispatchTarget('Cursor')).toBe('cursor-cli');
    const lanes = [
      sampleLane({ lane_id: 'lane_oc', agent_type: 'opencode-cli' }),
      sampleLane({ lane_id: 'lane_done', agent_type: 'claude-cli', status: 'completed' }),
    ];
    expect(findLaneIdForAgentType(lanes, 'opencode-cli')).toBe('lane_oc');
    expect(findLaneIdForAgentType(lanes, 'claude-cli')).toBeNull();
  });

  it('computes lane grid page count for carousel pagination', () => {
    expect(computeLaneGridPageCount(4)).toBe(1);
    expect(computeLaneGridPageCount(5)).toBe(2);
    expect(computeLaneGridPageCount(9)).toBe(3);
    expect(laneGridPageIndex(0)).toBe(0);
    expect(laneGridPageIndex(4)).toBe(1);
    expect(sliceLanesForGridPage(['a', 'b', 'c', 'd', 'e'], 1)).toEqual(['e']);
  });

  it('uses longer PTY inject warmup for OpenCode TUIs', () => {
    expect(resolvePtyInjectWarmupMs('claude-cli')).toBe(2800);
    expect(resolvePtyInjectWarmupMs('opencode-cli')).toBe(2800);
    expect(resolvePtyInjectWarmupMs('antigravity-cli')).toBe(3200);
    expect(resolvePtyInjectWarmupMs('ollama-cli')).toBe(3500);
    expect(resolvePtyInjectWarmupMs('opencode-cli', { attempt: 1 })).toBe(1200);
    expect(resolvePtyInjectWarmupMs('opencode-cli', { isHandoff: true })).toBe(3400);
  });

  it('detects agy and ollama PTY output ready for inject', () => {
    expect(isPtyOutputReadyForInject('antigravity-cli', 'Antigravity CLI 1.0\n? for shortcuts')).toBe(true);
    expect(isPtyOutputReadyForInject('antigravity-cli', 'booting…')).toBe(false);
    expect(isPtyOutputReadyForInject('ollama-cli', '>>> hello')).toBe(true);
    expect(isPtyOutputReadyForInject('claude-cli', 'x'.repeat(24))).toBe(false);
    expect(isPtyOutputReadyForInject('claude-cli', '> Ask a question')).toBe(true);
    expect(isPtyOutputReadyForInject('dummy-cli', 'x'.repeat(24))).toBe(true);
  });

  it('builds optimistic handoff dispatch entry from preview', () => {
    const entry = buildOptimisticDispatchEntry({
      prompt: '@Claude Code from @OpenCode review summary',
      preview: {
        sources: ['OpenCode'],
        target: 'Claude Code',
        task: 'review summary',
        handoff_path: 'handoffs/pending.md',
        handoff_file: 'pending.md',
        file_refs: [],
        input_mode: 'graph',
        dispatch_mode: 'handoff',
        chips: [],
      },
      activeSources: ['OpenCode'],
      targetLabel: 'Claude Code',
    });
    expect(entry.id.startsWith(OPTIMISTIC_DISPATCH_ID_PREFIX)).toBe(true);
    expect(entry.sources_label).toBe('OpenCode');
    expect(entry.target).toBe('Claude Code');
    expect(entry.dispatch_mode).toBe('handoff');
    expect(entry.handoff_file).toBe('pending.md');
  });

  it('builds handoff send-to-bar text with graph file reference', () => {
    expect(
      buildHandoffSendToBarText({
        target: 'Claude Code',
        sourcesLabel: 'OpenCode',
        handoffFile: '20260703-Opencode-ClaudeCode.md',
        inputMode: 'graph',
      }),
    ).toBe('@Claude Code from @OpenCode @20260703-Opencode-ClaudeCode.md');
  });

  it('uses longer warmup for ollama PTY inject', () => {
    expect(resolvePtyInjectWarmupMs('ollama-cli', { isHandoff: true, attempt: 0 })).toBe(4700);
    expect(resolvePtyInjectWarmupMs('ollama-cli', { attempt: 0 })).toBe(3500);
  });

  it('detects dispatch target pending from PTY status, not lane booting label', () => {
    const entry = {
      id: 'd1',
      time: '10:00',
      sources_label: 'OpenCode',
      target: 'Ollama',
      prompt: 'task',
      handoff_file: '',
      handoff_path: '',
      lane_sessions: [{ lane_id: 'lane_b', label: 'Ollama', agent_type: 'ollama-cli', cli_session_id: 's1' }],
    };
    const bootingLane = sampleLane({
      lane_id: 'lane_b',
      agent_type: 'ollama-cli',
      status: 'booting',
      configured_agent_name: 'Ollama',
    });
    expect(isDispatchEntryTargetPending(entry, [bootingLane], null, () => '')).toBe(true);
    expect(isDispatchEntryTargetPending(entry, [bootingLane], null, () => 'booting')).toBe(true);
    expect(isDispatchEntryTargetPending(entry, [bootingLane], null, () => 'ready')).toBe(false);
    expect(
      isDispatchEntryTargetPending(
        entry,
        [sampleLane({ lane_id: 'lane_b', agent_type: 'ollama-cli', status: 'running', configured_agent_name: 'Ollama' })],
        null,
        () => 'ready',
      ),
    ).toBe(false);
  });

  it('resolves dispatch target lane from lane_sessions', () => {
    const lanes = [
      sampleLane({ lane_id: 'lane_b', agent_type: 'ollama-cli', configured_agent_name: 'Ollama' }),
    ];
    const lane = findLaneForDispatchTarget(lanes, 'Ollama', [
      { lane_id: 'lane_b', label: 'Ollama', agent_type: 'ollama-cli', cli_session_id: 's1' },
    ]);
    expect(lane?.lane_id).toBe('lane_b');
  });

  it('replaces optimistic dispatch row when server confirms same prompt', () => {
    const optimistic = buildOptimisticDispatchEntry({
      prompt: 'task text',
      preview: {
        sources: ['OpenCode'],
        target: 'Claude Code',
        task: 'task',
        handoff_path: 'handoffs/a.md',
        handoff_file: 'a.md',
        file_refs: [],
        input_mode: 'graph',
        dispatch_mode: 'handoff',
        chips: [],
      },
      activeSources: ['OpenCode'],
      targetLabel: 'Claude Code',
    });
    const current = [optimistic];
    const server = [{
      id: 'dispatch_server_1',
      time: '02:17',
      sources_label: 'OpenCode',
      target: 'Claude Code',
      prompt: 'task text',
      handoff_file: 'a.md',
      handoff_path: 'handoffs/a.md',
      input_mode: 'graph' as const,
      dispatch_mode: 'handoff' as const,
    }];
    const merged = mergeDispatchLogs(current, server);
    expect(merged).toHaveLength(1);
    expect(merged[0].id).toBe('dispatch_server_1');
  });
});
