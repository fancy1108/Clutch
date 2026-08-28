import { describe, expect, it } from 'vitest';
import { footerIdleHiddenClass } from './FooterMenu';

describe('footer chrome', () => {
  it('only marks idle chips for compact hiding', () => {
    expect(footerIdleHiddenClass(true)).toContain('@max-');
    expect(footerIdleHiddenClass(true)).toContain('/footer:hidden');
    expect(footerIdleHiddenClass(false)).toBe('');
  });
});
