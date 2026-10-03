/**
 * Chilean Market & International Data Formatters
 */

/**
 * Format currency in Chilean Pesos (CLP)
 * Example: 15450000 -> "$15.450.000"
 */
export function formatCLP(amount: number | null | undefined): string {
  if (amount === null || amount === undefined || Number.isNaN(amount)) {
    return '$0';
  }
  return new Intl.NumberFormat('es-CL', {
    style: 'currency',
    currency: 'CLP',
    maximumFractionDigits: 0,
  }).format(amount);
}

/**
 * Format Unidad de Fomento (UF)
 * Example: 1250.75 -> "1.250,75 UF"
 */
export function formatUF(amount: number | null | undefined): string {
  if (amount === null || amount === undefined || Number.isNaN(amount)) {
    return '0 UF';
  }
  return `${new Intl.NumberFormat('es-CL', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount)} UF`;
}

/**
 * Format compact amounts for KPI cards
 * Example: 15400000 -> "$15,4M CLP"
 */
export function formatCompactCurrency(amount: number | null | undefined): string {
  if (amount === null || amount === undefined || Number.isNaN(amount)) {
    return '$0';
  }

  if (Math.abs(amount) >= 1_000_000_000) {
    return `$${(amount / 1_000_000_000).toFixed(1).replace('.', ',')}B`;
  }
  if (Math.abs(amount) >= 1_000_000) {
    return `$${(amount / 1_000_000).toFixed(1).replace('.', ',')}M`;
  }
  if (Math.abs(amount) >= 1_000) {
    return `$${(amount / 1_000).toFixed(0)}K`;
  }
  return formatCLP(amount);
}

/**
 * Format percentage
 * Example: 0.125 -> "12,5%"
 */
export function formatPercentage(value: number | null | undefined, decimals: number = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return '0%';
  }
  return `${(value * 100).toFixed(decimals).replace('.', ',')}%`;
}

/**
 * Format Date to Chilean standard (DD/MM/YYYY)
 */
export function formatDate(date: string | Date | null | undefined): string {
  if (!date) return '-';
  const d = typeof date === 'string' ? new Date(date) : date;
  if (Number.isNaN(d.getTime())) return '-';

  return new Intl.DateTimeFormat('es-CL', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  }).format(d);
}

/**
 * Format Date with time (DD/MM/YYYY HH:mm)
 */
export function formatDateTime(date: string | Date | null | undefined): string {
  if (!date) return '-';
  const d = typeof date === 'string' ? new Date(date) : date;
  if (Number.isNaN(d.getTime())) return '-';

  return new Intl.DateTimeFormat('es-CL', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(d);
}

/**
 * Relative time description in Spanish
 * Example: "hace 2 horas", "hace 3 días"
 */
export function formatRelativeTime(date: string | Date | null | undefined): string {
  if (!date) return '-';
  const d = typeof date === 'string' ? new Date(date) : date;
  if (Number.isNaN(d.getTime())) return '-';

  const now = new Date();
  const diffSeconds = Math.round((d.getTime() - now.getTime()) / 1000);
  const rtf = new Intl.RelativeTimeFormat('es-CL', { numeric: 'auto' });

  const absSec = Math.abs(diffSeconds);
  if (absSec < 60) return rtf.format(diffSeconds, 'second');
  const diffMinutes = Math.round(diffSeconds / 60);
  if (Math.abs(diffMinutes) < 60) return rtf.format(diffMinutes, 'minute');
  const diffHours = Math.round(diffMinutes / 60);
  if (Math.abs(diffHours) < 24) return rtf.format(diffHours, 'hour');
  const diffDays = Math.round(diffHours / 24);
  if (Math.abs(diffDays) < 30) return rtf.format(diffDays, 'day');
  const diffMonths = Math.round(diffDays / 30);
  if (Math.abs(diffMonths) < 12) return rtf.format(diffMonths, 'month');
  const diffYears = Math.round(diffDays / 365);
  return rtf.format(diffYears, 'year');
}

/**
 * Format Chilean RUT
 * Example: "12345678k" -> "12.345.678-K"
 */
export function formatRUT(rut: string | null | undefined): string {
  if (!rut) return '-';
  const clean = rut.replace(/[^0-9kK]/g, '').toUpperCase();
  if (clean.length < 2) return clean;

  const dv = clean.slice(-1);
  const body = clean.slice(0, -1);
  const formattedBody = body.replace(/\B(?=(\d{3})+(?!\d))/g, '.');

  return `${formattedBody}-${dv}`;
}

/**
 * Validate Chilean RUT
 */
export function validateRUT(rut: string | null | undefined): boolean {
  if (!rut) return false;
  const clean = rut.replace(/[^0-9kK]/g, '').toUpperCase();
  if (clean.length < 8) return false;

  const body = clean.slice(0, -1);
  const dv = clean.slice(-1);

  let sum = 0;
  let multiplier = 2;

  for (let i = body.length - 1; i >= 0; i--) {
    sum += parseInt(body.charAt(i), 10) * multiplier;
    multiplier = multiplier === 7 ? 2 : multiplier + 1;
  }

  const expectedDV = 11 - (sum % 11);
  let computedDV = '';
  if (expectedDV === 11) computedDV = '0';
  else if (expectedDV === 10) computedDV = 'K';
  else computedDV = expectedDV.toString();

  return dv === computedDV;
}
