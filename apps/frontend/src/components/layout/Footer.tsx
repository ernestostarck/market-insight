import { Link } from 'react-router-dom';
import { Database, ExternalLink, ShieldCheck } from 'lucide-react';
import { APP_CONFIG } from '@/lib/constants';

const PRODUCT_LINKS = [
  { label: 'Dashboard', to: '/dashboard' },
  { label: 'Mercado', to: '/mercado' },
  { label: 'Rubros', to: '/rubros' },
  { label: 'Analytics', to: '/analytics' },
];

const DATA_LINKS = [
  { label: 'Licitaciones', to: '/licitaciones' },
  { label: 'Proveedores', to: '/proveedores' },
  { label: 'Organismos', to: '/organismos' },
  { label: 'Búsqueda', to: '/search' },
];

function FooterLinks({ title, links }: { title: string; links: { label: string; to: string }[] }) {
  return (
    <div>
      <p className="text-[11px] font-semibold uppercase tracking-wider text-foreground">{title}</p>
      <ul className="mt-2.5 space-y-1.5">
        {links.map((link) => (
          <li key={link.to}>
            <Link
              to={link.to}
              className="text-xs text-muted-foreground transition-colors hover:text-primary"
            >
              {link.label}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function Footer() {
  const year = new Date().getFullYear();

  return (
    <footer className="mt-10 border-t border-border/70 bg-card/40">
      <div className="mx-auto max-w-7xl px-4 py-8 md:px-8">
        <div className="grid grid-cols-2 gap-8 md:grid-cols-[2fr_1fr_1fr_1.4fr]">
          {/* Brand */}
          <div className="col-span-2 md:col-span-1">
            <div className="flex items-center gap-2.5">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-blue-600 to-indigo-600 text-xs font-bold text-white shadow-sm">
                MI
              </div>
              <div>
                <p className="text-sm font-bold leading-tight text-foreground">Market Insight</p>
                <p className="text-[11px] leading-tight text-muted-foreground">
                  ChileCompra Analytics
                </p>
              </div>
            </div>
            <p className="mt-3 max-w-sm text-xs leading-relaxed text-muted-foreground">
              {APP_CONFIG.description}. Captura, normaliza y analiza licitaciones, adjudicaciones y
              actores del Mercado Público.
            </p>
          </div>

          <FooterLinks title="Plataforma" links={PRODUCT_LINKS} />
          <FooterLinks title="Datos" links={DATA_LINKS} />

          {/* Data source */}
          <div className="col-span-2 md:col-span-1">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-foreground">
              Fuente de datos
            </p>
            <a
              href="https://www.mercadopublico.cl"
              target="_blank"
              rel="noopener noreferrer"
              className="mt-2.5 inline-flex items-center gap-1.5 text-xs text-muted-foreground transition-colors hover:text-primary"
            >
              <Database className="h-3.5 w-3.5" />
              Mercado Público · API ChileCompra
              <ExternalLink className="h-3 w-3" />
            </a>
            <p className="mt-2 flex items-start gap-1.5 text-[11px] leading-relaxed text-muted-foreground">
              <ShieldCheck className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-600 dark:text-emerald-400" />
              Información pública de compras del Estado de Chile, procesada con fines de análisis.
            </p>
          </div>
        </div>

        <div className="mt-8 flex flex-col items-center justify-between gap-2 border-t border-border/60 pt-5 text-[11px] text-muted-foreground sm:flex-row">
          <p>
            © {year} {APP_CONFIG.name}. Todos los derechos reservados.
          </p>
          <p className="font-mono">v{APP_CONFIG.version}</p>
        </div>
      </div>
    </footer>
  );
}
