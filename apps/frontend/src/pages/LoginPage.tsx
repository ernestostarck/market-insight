import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { AlertCircle, KeyRound, Shield, ShieldCheck } from 'lucide-react';
import { useAuth, type LoginFormData } from '@/features/auth';
import { LoginForm } from '@/features/auth/components/LoginForm';
import { preferredLandingPage } from '@/features/auth/preferences';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

interface LoginPageProps {
  onLoginSuccess?: (token: string) => void;
}

export function LoginPage({ onLoginSuccess }: LoginPageProps) {
  const { login, verifyMfa, isLoading, token } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [mfaToken, setMfaToken] = useState<string | null>(null);
  const [mfaCode, setMfaCode] = useState('');
  const [mfaError, setMfaError] = useState<string | null>(null);

  const goToApp = () => {
    if (onLoginSuccess && token) onLoginSuccess(token);
    const from = (location.state as { from?: { pathname?: string } })?.from?.pathname;
    navigate(from || preferredLandingPage(), { replace: true });
  };

  const handleLoginSubmit = async (data: LoginFormData) => {
    const result = await login(data);
    if (result.status === 'mfa_required') {
      setMfaToken(result.mfaToken);
      return;
    }
    goToApp();
  };

  const handleMfaSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!mfaToken) return;
    setMfaError(null);
    try {
      await verifyMfa(mfaToken, mfaCode);
      goToApp();
    } catch (err) {
      setMfaCode('');
      const message = (err as { message?: string })?.message;
      setMfaError(message || 'Código incorrecto. Inténtalo de nuevo.');
      if ((err as { status?: number })?.status === 401 && message?.includes('expiró'))
        setMfaToken(null);
    }
  };

  return (
    <div className="relative flex min-h-screen w-full items-center justify-center bg-gradient-to-br from-slate-900 via-slate-950 to-blue-950 p-4">
      {/* Subtle Background Glow Elements */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -right-40 -top-40 h-96 w-96 rounded-full bg-primary/15 blur-3xl" />
        <div className="absolute -bottom-40 -left-40 h-96 w-96 rounded-full bg-blue-600/10 blur-3xl" />
      </div>

      {/* Main Login Card */}
      <div className="relative w-full max-w-md rounded-2xl border border-white/10 bg-card/95 p-8 shadow-2xl backdrop-blur-xl">
        {/* Brand Header */}
        <div className="mb-6 text-center">
          <div className="mb-3 inline-flex h-12 w-12 items-center justify-center rounded-xl bg-primary text-xl font-black text-primary-foreground shadow-lg">
            MI
          </div>
          <p className="text-[11px] font-bold uppercase tracking-widest text-primary">
            Market Insight ChileCompra
          </p>
          <h1 className="mt-1 text-2xl font-black tracking-tight text-foreground">
            Plataforma de Inteligencia
          </h1>
          <p className="mx-auto mt-1.5 max-w-xs text-xs text-muted-foreground">
            Ingresa tus credenciales autorizadas para acceder al monitor de compras públicas y
            licitaciones críticas.
          </p>
        </div>

        {mfaToken ? (
          <form onSubmit={handleMfaSubmit} className="space-y-4" noValidate>
            <div className="flex items-start gap-3 rounded-lg border border-primary/20 bg-primary/5 p-3 text-xs text-foreground">
              <KeyRound className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
              <span>
                Tu cuenta tiene verificación en dos pasos. Ingresa el código de 6 dígitos de tu app
                de autenticación.
              </span>
            </div>
            {mfaError && (
              <div className="flex items-center gap-2 rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-xs text-destructive">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{mfaError}</span>
              </div>
            )}
            <Input
              autoFocus
              inputMode="numeric"
              autoComplete="one-time-code"
              pattern="[0-9]*"
              maxLength={6}
              placeholder="000000"
              value={mfaCode}
              onChange={(e) => setMfaCode(e.target.value.replace(/\D/g, ''))}
              className="h-12 text-center font-mono text-xl tracking-[0.5em]"
              aria-label="Código de verificación"
            />
            <Button
              type="submit"
              className="h-10 w-full font-semibold"
              isLoading={isLoading}
              disabled={mfaCode.length !== 6}
            >
              Verificar
            </Button>
            <button
              type="button"
              onClick={() => {
                setMfaToken(null);
                setMfaCode('');
                setMfaError(null);
              }}
              className="w-full text-center text-xs text-muted-foreground hover:text-primary"
            >
              Volver al inicio de sesión
            </button>
          </form>
        ) : (
          <LoginForm onSubmit={handleLoginSubmit} isLoading={isLoading} />
        )}

        {/* Security & System Indicators Footer */}
        <div className="mt-8 flex items-center justify-between border-t border-border/60 pt-4 text-[11px] text-muted-foreground">
          <div className="flex items-center gap-1">
            <Shield className="h-3 w-3 text-emerald-500" />
            <span>Conexión cifrada · sesión protegida</span>
          </div>
          <div className="flex items-center gap-1">
            <ShieldCheck className="h-3 w-3 text-primary" />
            <span>Verificación en dos pasos</span>
          </div>
        </div>
      </div>
    </div>
  );
}
