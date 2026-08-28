import React from 'react';
import { describe, expect, it } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import {
  isTableSeparatorRow,
  looksLikeTableRow,
  renderChatMarkdown,
  splitTableCells,
  tryParseGfmTable,
} from './chatContentRender';

describe('splitTableCells', () => {
  it('splits pipe rows with optional leading/trailing pipes', () => {
    expect(splitTableCells('| 类别 | 代表技能 |')).toEqual(['类别', '代表技能']);
    expect(splitTableCells('A | B')).toEqual(['A', 'B']);
  });
});

describe('isTableSeparatorRow', () => {
  it('accepts dash and alignment markers', () => {
    expect(isTableSeparatorRow('|-------|----------|')).toBe(true);
    expect(isTableSeparatorRow('| :--- | ---: |')).toBe(true);
    expect(isTableSeparatorRow('| :---: | --- |')).toBe(true);
  });

  it('rejects ordinary text rows', () => {
    expect(isTableSeparatorRow('| 类别 | 代表技能 |')).toBe(false);
    expect(isTableSeparatorRow('not a table')).toBe(false);
  });
});

describe('looksLikeTableRow', () => {
  it('requires at least two columns', () => {
    expect(looksLikeTableRow('| a | b |')).toBe(true);
    expect(looksLikeTableRow('| alone |')).toBe(false);
    expect(looksLikeTableRow('use | as a pipe')).toBe(true);
  });
});

describe('tryParseGfmTable', () => {
  it('parses header, separator, and body rows', () => {
    const lines = [
      '| 类别 | 代表技能 |',
      '|-------|----------|',
      '| 用户调用 | `grill-me` |',
      '| 模型调用 | `tdd` |',
      '',
      'after',
    ];
    const parsed = tryParseGfmTable(lines, 0);
    expect(parsed).not.toBeNull();
    expect(parsed!.header).toEqual(['类别', '代表技能']);
    expect(parsed!.body).toEqual([
      ['用户调用', '`grill-me`'],
      ['模型调用', '`tdd`'],
    ]);
    expect(parsed!.end).toBe(3);
  });

  it('returns null without a separator row', () => {
    expect(tryParseGfmTable(['| a | b |', '| c | d |'], 0)).toBeNull();
  });
});

describe('renderChatMarkdown tables', () => {
  it('renders a GFM table as <table> with inline code cells', () => {
    const md = [
      '### 技能分类',
      '',
      '| 类别 | 代表技能 |',
      '|-------|----------|',
      '| 用户调用 | `grill-me` 、 `tdd` |',
      '| 模型调用 | `research` |',
    ].join('\n');

    const html = renderToStaticMarkup(renderChatMarkdown(md) as React.ReactElement);
    expect(html).toContain('<table');
    expect(html).toContain('<th');
    expect(html).toContain('<td');
    expect(html).toContain('类别');
    expect(html).toContain('grill-me');
    expect(html).toContain('<code');
    expect(html).not.toContain('|-------');
    expect(html).not.toContain('| 类别 |');
  });

  it('does not treat a lone pipe sentence as a table', () => {
    const html = renderToStaticMarkup(
      renderChatMarkdown('Use A | B as alternatives.') as React.ReactElement,
    );
    expect(html).not.toContain('<table');
    expect(html).toContain('Use A | B as alternatives.');
  });

  it('honors alignment separator markers in class names', () => {
    const md = ['| L | C | R |', '| :--- | :---: | ---: |', '| a | b | c |'].join('\n');
    const html = renderToStaticMarkup(renderChatMarkdown(md) as React.ReactElement);
    expect(html).toContain('text-left');
    expect(html).toContain('text-center');
    expect(html).toContain('text-right');
  });
});
