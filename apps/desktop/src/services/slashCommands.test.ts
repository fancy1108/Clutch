import { describe, expect, it } from 'vitest';
import {
  filterSlashCommands,
  matchExactSlashCommand,
  SLASH_COMMANDS,
} from './slashCommands';

describe('slashCommands (D18)', () => {
  it('lists plan/compact/todos/help', () => {
    expect(SLASH_COMMANDS.map((c) => c.token)).toEqual([
      'plan',
      'compact',
      'todos',
      'help',
    ]);
  });

  it('filters by prefix', () => {
    expect(filterSlashCommands('pl').map((c) => c.id)).toEqual(['plan']);
    expect(filterSlashCommands('co').map((c) => c.id)).toEqual(['compact']);
    expect(filterSlashCommands('').length).toBe(4);
  });

  it('matches exact send of /plan', () => {
    expect(matchExactSlashCommand('/plan')?.id).toBe('plan');
    expect(matchExactSlashCommand('  /compact  ')?.id).toBe('compact');
    expect(matchExactSlashCommand('/skill:foo')).toBeNull();
    expect(matchExactSlashCommand('/plan please')).toBeNull();
    expect(matchExactSlashCommand('hello')).toBeNull();
  });
});
