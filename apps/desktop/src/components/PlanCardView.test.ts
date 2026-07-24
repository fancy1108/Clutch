import { describe, expect, it } from 'vitest';
import { stripPlanStepIndex } from './PlanCardView';

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
