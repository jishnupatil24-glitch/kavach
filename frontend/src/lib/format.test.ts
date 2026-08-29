import { describe, expect, it } from 'vitest';
import {
  formatNumber,
  formatPercent,
  formatRate,
  formatSigned,
  isMissing,
  valueOrDash,
} from './format';

describe('format helpers — missing values never become 0/blank', () => {
  it('isMissing catches null, undefined, NaN only', () => {
    expect(isMissing(null)).toBe(true);
    expect(isMissing(undefined)).toBe(true);
    expect(isMissing(NaN)).toBe(true);
    expect(isMissing(0)).toBe(false);
    expect(isMissing(-1.5)).toBe(false);
  });

  it('formatNumber returns null for missing, not "0"', () => {
    expect(formatNumber(null)).toBeNull();
    expect(formatNumber(undefined)).toBeNull();
    expect(formatNumber(0)).toBe('0');
    expect(formatNumber(1234.5678, 2)).toBe('1,234.57');
  });

  it('valueOrDash renders an em-dash for missing', () => {
    expect(valueOrDash(null)).toBe('—');
    expect(valueOrDash(3.14159, 2)).toBe('3.14');
  });

  it('formatSigned keeps the sign', () => {
    expect(formatSigned(2.5)).toBe('+2.5');
    expect(formatSigned(-2.5)).toBe('-2.5');
    expect(formatSigned(0)).toBe('0');
    expect(formatSigned(null)).toBeNull();
  });

  it('formatRate appends the backend unit verbatim', () => {
    expect(formatRate(0.8, 'pp/day')).toBe('+0.8 pp/day');
    expect(formatRate(null, 'pp/day')).toBeNull();
  });

  it('formatPercent', () => {
    expect(formatPercent(-30.0000001)).toBe('-30%');
    expect(formatPercent(null)).toBeNull();
  });
});
