import React from 'react';
import ReactDOM from 'react-dom/client';
import { CssBaseline, ThemeProvider } from '@mui/material';

import App from './App';
import { appTheme } from './theme';
import { sentry } from './lib/sentry';
import { ErrorBoundary } from './components/feedback/ErrorBoundary';
import './index.css';

sentry.init();

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <ErrorBoundary>
      <ThemeProvider theme={appTheme}>
        <CssBaseline />
        <App />
      </ThemeProvider>
    </ErrorBoundary>
  </React.StrictMode>,
);
