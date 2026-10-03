import { createTheme } from '@mui/material/styles';

// Mirrors the CSS custom properties in index.css so the few remaining MUI-driven
// pieces of the app (CssBaseline reset, legacy KpiCard) don't clash with the rest
// of the (Tailwind-driven) design system.
export const appTheme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#4f46e5', // indigo-600
    },
    secondary: {
      main: '#334155', // slate-700
    },
    success: {
      main: '#059669', // emerald-600
    },
    error: {
      main: '#e11d48', // rose-600
    },
    warning: {
      main: '#f59e0b', // amber-500
    },
    info: {
      main: '#0ea5e9', // sky-500
    },
    background: {
      default: '#f6f7fb',
      paper: '#ffffff',
    },
  },
  typography: {
    fontFamily: [
      'system-ui',
      '-apple-system',
      'Segoe UI',
      'Roboto',
      'Helvetica Neue',
      'Arial',
      'sans-serif',
    ].join(','),
  },
  shape: {
    borderRadius: 10,
  },
});

