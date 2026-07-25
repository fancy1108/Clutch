import { describe, expect, it } from 'vitest';
import { formatPlanRevisePayload, hasPlanStepComments, stripPlanStepIndex } from './PlanCardView';

describe('stripPlanStepIndex', () => {
  it('removes leading numeric markers', () => {
    expect(stripPlanStepIndex('1. Create health.py')).toBe('Create health.py');
    expect(stripPlanStepIndex('2) Update README')).toBe('Update README');
    expect(stripPlanStepIndex('3、Run import')).toBe('Run import');
    expect(stripPlanStepIndex('1. 1. Create clutch_ping.py')).toBe('Create clutch_ping.py');
  });

  it('leaves plain steps alone', () => {
    expect(stripPlanStepIndex('Create health.py')).toBe('Create health.py');
  });
});

describe('formatPlanRevisePayload', () => {
  it('serializes per-step comments', () => {
    const raw = formatPlanRevisePayload(
      'Revise please',
      ['Add route', 'Wire auth'],
      ['', 'Use OAuth'],
    );
    const parsed = JSON.parse(raw) as {
      note: string;
      stepComments: { step: number; comment: string }[];
    };
    expect(parsed.note).toBe('Revise please');
    expect(parsed.stepComments).toHaveLength(1);
    expect(parsed.stepComments[0].step).toBe(2);
    expect(parsed.stepComments[0].comment).toBe('Use OAuth');
  });

  it('detects non-empty step comments', () => {
    expect(hasPlanStepComments(['', 'x'])).toBe(true);
    expect(hasPlanStepComments(['', ''])).toBe(false);
  });
});
