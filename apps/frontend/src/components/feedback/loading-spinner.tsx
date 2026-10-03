import { Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

interface LoadingSpinnerProps {
  size?: 'sm' | 'default' | 'lg';
  message?: string;
  className?: string;
}

const sizeMap = {
  sm: 'h-4 w-4',
  default: 'h-8 w-8',
  lg: 'h-12 w-12',
};

export function LoadingSpinner({ size = 'default', message, className }: LoadingSpinnerProps) {
  return (
    <div className={cn('flex flex-col items-center justify-center space-y-3 p-6', className)}>
      <Loader2 className={cn('animate-spin text-primary', sizeMap[size])} />
      {message && <p className="animate-pulse text-sm text-muted-foreground">{message}</p>}
    </div>
  );
}
