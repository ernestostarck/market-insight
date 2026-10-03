import React, { Component, type ErrorInfo, type ReactNode } from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';
import { sentry } from '@/lib/sentry';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  override componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    sentry.captureException(error, {
      componentStack: errorInfo.componentStack,
    });
  }

  handleReset = (): void => {
    this.setState({ hasError: false, error: null });
    window.location.reload();
  };

  override render(): ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="flex min-h-[400px] w-full items-center justify-center p-6">
          <Card className="max-w-md border-red-500/30 bg-card/60 shadow-lg backdrop-blur-md">
            <CardHeader className="text-center">
              <div className="mx-auto mb-2 flex h-12 w-12 items-center justify-center rounded-full bg-red-500/10 text-red-500">
                <AlertCircle className="h-6 w-6" />
              </div>
              <CardTitle className="text-xl text-foreground">Algo salió mal</CardTitle>
              <CardDescription>
                Se ha producido un error inesperado en la interfaz. El incidente ha sido registrado
                automáticamente.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {this.state.error?.message && (
                <div className="rounded-md bg-muted p-3 text-xs font-mono text-muted-foreground break-all">
                  {this.state.error.message}
                </div>
              )}
              <Button
                onClick={this.handleReset}
                variant="default"
                className="w-full flex items-center justify-center gap-2"
              >
                <RefreshCw className="h-4 w-4" />
                Recargar página
              </Button>
            </CardContent>
          </Card>
        </div>
      );
    }

    return this.props.children;
  }
}
