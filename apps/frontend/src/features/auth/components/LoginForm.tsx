import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { AlertCircle, Eye, EyeOff, Lock, Mail } from 'lucide-react';

import { loginSchema, type LoginFormData } from '@/features/auth/schemas';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

interface LoginFormProps {
  onSubmit: (data: LoginFormData) => Promise<void>;
  isLoading?: boolean;
}

export function LoginForm({ onSubmit, isLoading = false }: LoginFormProps) {
  const [showPassword, setShowPassword] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: '',
      password: '',
    },
  });

  const handleFormSubmit = async (data: LoginFormData) => {
    setServerError(null);
    try {
      await onSubmit(data);
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'message' in err) {
        setServerError(String((err as { message: string }).message));
      } else {
        setServerError('Credenciales inválidas o error de conexión con el servidor.');
      }
    }
  };

  return (
    <form onSubmit={handleSubmit(handleFormSubmit)} className="space-y-4" noValidate>
      {serverError && (
        <div className="flex items-center gap-2 rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-xs text-destructive">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{serverError}</span>
        </div>
      )}

      {/* Email Field */}
      <div className="space-y-1.5 text-left">
        <label htmlFor="email" className="block text-xs font-semibold text-foreground">
          Correo Electrónico
        </label>
        <div className="relative">
          <Mail className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            id="email"
            type="email"
            autoComplete="email"
            placeholder="usuario@institucion.cl"
            className="pl-9"
            error={!!errors.email}
            disabled={isLoading}
            {...register('email')}
          />
        </div>
        {errors.email && (
          <p className="text-xs font-medium text-destructive">{errors.email.message}</p>
        )}
      </div>

      {/* Password Field */}
      <div className="space-y-1.5 text-left">
        <div className="flex items-center justify-between">
          <label htmlFor="password" className="block text-xs font-semibold text-foreground">
            Contraseña
          </label>
          <a
            href="#/recuperar"
            className="text-[11px] text-primary hover:underline"
            onClick={(e) => {
              e.preventDefault();
              alert('Por favor contacta al administrador de TI para restablecer tu contraseña.');
            }}
          >
            ¿Olvidaste tu contraseña?
          </a>
        </div>
        <div className="relative">
          <Lock className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            id="password"
            type={showPassword ? 'text' : 'password'}
            autoComplete="current-password"
            placeholder="••••••••"
            className="pl-9 pr-9"
            error={!!errors.password}
            disabled={isLoading}
            {...register('password')}
          />
          <button
            type="button"
            onClick={() => setShowPassword((prev) => !prev)}
            className="absolute right-3 top-2.5 text-muted-foreground hover:text-foreground"
            tabIndex={-1}
            aria-label={showPassword ? 'Ocultar contraseña' : 'Ver contraseña'}
          >
            {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </button>
        </div>
        {errors.password && (
          <p className="text-xs font-medium text-destructive">{errors.password.message}</p>
        )}
      </div>

      {/* Submit Button */}
      <Button type="submit" className="mt-2 h-10 w-full font-semibold" isLoading={isLoading}>
        Iniciar Sesión
      </Button>
    </form>
  );
}
