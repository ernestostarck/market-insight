import { describe, expect, it } from 'vitest';
import { cn } from '@/lib/utils';
import {
  formatCLP,
  formatUF,
  formatCompactCurrency,
  formatRUT,
  validateRUT,
  formatPercentage,
} from '@/lib/formatters';

describe('Frontend Utilities & Formatters', () => {
  describe('cn (Classname merger)', () => {
    it('merges class names and resolves tailwind collisions', () => {
      expect(cn('p-4', 'text-center')).toBe('p-4 text-center');
      expect(cn('p-2', 'p-4')).toBe('p-4');
      expect(cn('text-red-500', false && 'text-blue-500', 'font-bold')).toBe(
        'text-red-500 font-bold',
      );
    });
  });

  describe('Chilean Financial Formatters', () => {
    it('formats CLP currency correctly', () => {
      // Intl in Node/jsdom es-CL uses $ or non-breaking spaces
      const formatted = formatCLP(1500000);
      expect(formatted).toContain('1.500.000');
      expect(formatCLP(null)).toContain('0');
    });

    it('formats UF currency correctly', () => {
      const formatted = formatUF(1250.75);
      expect(formatted).toContain('1.250,75');
      expect(formatted).toContain('UF');
    });

    it('formats compact amounts for KPI cards', () => {
      expect(formatCompactCurrency(15400000)).toBe('$15,4M');
      expect(formatCompactCurrency(1200000000)).toBe('$1,2B');
      expect(formatCompactCurrency(450000)).toBe('$450K');
    });

    it('formats percentages correctly', () => {
      expect(formatPercentage(0.125)).toBe('12,5%');
      expect(formatPercentage(0.5)).toBe('50,0%');
    });
  });

  describe('Chilean RUT Formatter & Validator', () => {
    it('formats raw RUTs with dots and dash', () => {
      expect(formatRUT('12345678k')).toBe('12.345.678-K');
      expect(formatRUT('761920839')).toBe('76.192.083-9');
    });

    it('validates Chilean RUT using modulo 11 algorithm', () => {
      // Valid known Chilean RUTs
      expect(validateRUT('12.345.678-5')).toBe(true);
      expect(validateRUT('11111111-1')).toBe(true);
      expect(validateRUT('76.192.083-9')).toBe(true);

      // Invalid RUTs
      expect(validateRUT('12.345.678-9')).toBe(false);
      expect(validateRUT('123')).toBe(false);
      expect(validateRUT('')).toBe(false);
    });
  });
});
