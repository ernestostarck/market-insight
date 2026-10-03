import { LogOut, Settings, User, ShieldCheck } from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Button } from '@/components/ui/button';
import { useNavigate } from 'react-router-dom';

interface UserMenuProps {
  userName?: string;
  userEmail?: string;
  userRole?: string;
  onLogout?: () => void;
}

export function UserMenu({
  userName = 'Usuario',
  userEmail = '',
  userRole = 'Analista',
  onLogout,
}: UserMenuProps) {
  const navigate = useNavigate();
  const initials = userName
    .split(' ')
    .map((n) => n[0])
    .join('')
    .substring(0, 2)
    .toUpperCase();

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          className="relative flex h-10 items-center gap-2.5 rounded-lg px-2 hover:bg-accent/60"
        >
          <Avatar className="h-8 w-8 border border-border">
            <AvatarFallback className="bg-primary/10 text-xs font-bold text-primary">
              {initials}
            </AvatarFallback>
          </Avatar>
          <div className="hidden flex-col text-left leading-none md:flex">
            <span className="text-xs font-semibold text-foreground">{userName}</span>
            <span className="mt-0.5 text-[10px] text-muted-foreground">{userRole}</span>
          </div>
        </Button>
      </DropdownMenuTrigger>

      <DropdownMenuContent className="w-56" align="end" forceMount>
        <DropdownMenuLabel className="font-normal">
          <div className="flex flex-col space-y-1">
            <p className="text-sm font-semibold leading-none text-foreground">{userName}</p>
            <p className="text-xs leading-none text-muted-foreground">{userEmail}</p>
            <div className="mt-1 flex items-center gap-1 text-[11px] font-medium text-emerald-600 dark:text-emerald-400">
              <ShieldCheck className="h-3 w-3" />
              <span>Rol: {userRole}</span>
            </div>
          </div>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />

        <DropdownMenuGroup>
          <DropdownMenuItem className="cursor-pointer gap-2" onClick={() => navigate('/perfil')}>
            <User className="h-4 w-4 text-muted-foreground" />
            <span>Mi Perfil</span>
          </DropdownMenuItem>
          <DropdownMenuItem
            className="cursor-pointer gap-2"
            onClick={() => navigate('/configuracion')}
          >
            <Settings className="h-4 w-4 text-muted-foreground" />
            <span>Configuración</span>
          </DropdownMenuItem>
        </DropdownMenuGroup>
        <DropdownMenuSeparator />

        <DropdownMenuItem
          className="cursor-pointer gap-2 text-destructive focus:bg-destructive/10 focus:text-destructive"
          onClick={onLogout}
        >
          <LogOut className="h-4 w-4" />
          <span>Cerrar sesión</span>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
