/** tauri-playwright uses (expression, timeoutMs) — not Playwright's options object. */
export const delay = (ms: number): Promise<void> =>
  new Promise((resolve) => {
    setTimeout(resolve, ms);
  });

type TauriEvalPage = {
  evaluate: (script: string) => Promise<unknown>;
};

/** tauri-playwright fill/type only supports HTMLInputElement; chat uses textarea. */
export async function setTextareaValue(
  page: TauriEvalPage,
  selector: string,
  value: string,
): Promise<void> {
  await page.evaluate(`
    (function() {
      const el = document.querySelector(${JSON.stringify(selector)});
      if (!el) throw new Error('element not found: ${selector}');
      el.focus();
      const tracker = el._valueTracker;
      if (tracker) tracker.setValue('');
      const proto = el.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
      const setter = Object.getOwnPropertyDescriptor(proto, 'value')?.set;
      if (!setter) throw new Error('no value setter');
      setter.call(el, ${JSON.stringify(value)});
      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
    })()
  `);
}

export async function authorizeSandboxWorkspace(page: {
  locator: (selector: string) => { count: () => Promise<number>; click: () => Promise<void> };
  click: (selector: string) => Promise<void>;
  waitForSelector: (selector: string, timeout?: number) => Promise<void>;
}): Promise<void> {
  const chatAuthorize = page.locator('[data-testid="chat-authorize-workspace"]');
  if ((await chatAuthorize.count()) > 0) {
    await chatAuthorize.click();
  } else {
    await page.click('[data-testid="nav-add-workspace"]');
  }
  await page.waitForSelector('[data-testid="chat-input"]', 30_000);
}
