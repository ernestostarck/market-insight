import React, { useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Building2,
  FileText,
  Package,
  Users,
  Award,
  Download,
  Sparkles,
  ExternalLink,
  Mail,
  MapPin,
  Clock,
  ShieldCheck,
} from 'lucide-react';
import { formatCLP, formatDate, formatRUT } from '@/lib/formatters';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardTitle } from '@/components/ui/card';
import { useLicitacionDetail, LicitacionAiInsights } from '@/features/licitaciones';

type DetailTab = 'general' | 'items' | 'ofertas' | 'adjudicacion' | 'documentos' | 'ia';

export const LicitacionDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<DetailTab>('general');

  const { data: licitacion, isLoading, isError } = useLicitacionDetail(id);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="h-6 w-32 animate-pulse rounded bg-muted/60" />
        <div className="h-36 animate-pulse rounded-xl border border-border/80 bg-card" />
        <div className="h-96 animate-pulse rounded-xl border border-border/80 bg-card" />
      </div>
    );
  }

  if (isError || !licitacion) {
    return (
      <div className="rounded-xl border border-destructive/30 bg-destructive/10 p-8 text-center text-destructive">
        <h2 className="text-lg font-bold text-foreground">Licitación no encontrada</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          No se pudo recuperar la información del proceso de compra solicitado.
        </p>
        <Button
          variant="outline"
          size="sm"
          onClick={() => navigate('/licitaciones')}
          className="mt-4 border-border/80 bg-background text-foreground hover:bg-muted"
        >
          Volver al catálogo
        </Button>
      </div>
    );
  }

  const getStatusBadge = (estado?: string | null) => {
    const s = (estado || '').toLowerCase();
    if (s.includes('public') || s.includes('vigente') || s.includes('activ')) {
      return (
        <Badge
          variant="outline"
          className="border-emerald-500/20 bg-emerald-50 font-semibold text-xs text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300"
        >
          Publicada / Vigente
        </Badge>
      );
    }
    if (s.includes('adjud')) {
      return (
        <Badge variant="outline" className="border-blue-500/20 bg-blue-50 font-semibold text-xs text-blue-700 dark:bg-blue-950/40 dark:text-blue-300">
          Adjudicada
        </Badge>
      );
    }
    if (s.includes('desiert')) {
      return (
        <Badge variant="outline" className="border-destructive/20 bg-destructive/10 font-semibold text-xs text-destructive">
          Desierta
        </Badge>
      );
    }
    return (
      <Badge variant="outline" className="border-amber-500/20 bg-amber-50 font-semibold text-xs text-amber-700 dark:bg-amber-950/40 dark:text-amber-300">
        {estado || 'Cerrada'}
      </Badge>
    );
  };

  return (
    <div className="space-y-6">
      {/* Back button */}
      <div>
        <Link
          to="/licitaciones"
          className="inline-flex items-center gap-2 text-xs font-medium text-muted-foreground transition-colors hover:text-primary"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          <span>Volver al explorador de licitaciones</span>
        </Link>
      </div>

      {/* Hero / Header Card */}
      <div className="rounded-xl border border-border/80 bg-card p-6 shadow-sm">
        <div className="flex flex-col justify-between gap-4 md:flex-row md:items-start">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2.5">
              <span className="font-mono text-xs font-bold text-primary">
                {licitacion.codigo}
              </span>
              {getStatusBadge(licitacion.estado)}
              {licitacion.categoria && (
                <span className="rounded-md border border-border/80 bg-muted/60 px-2 py-0.5 text-xs font-medium text-muted-foreground">
                  {licitacion.categoria}
                </span>
              )}
            </div>

            <h1 className="max-w-4xl text-xl font-bold leading-snug tracking-tight text-foreground sm:text-2xl">
              {licitacion.nombre}
            </h1>

            <div className="flex flex-wrap items-center gap-4 pt-1 text-xs text-muted-foreground">
              <div className="flex items-center gap-1.5">
                <Building2 className="h-4 w-4 text-muted-foreground" />
                <span className="font-medium text-foreground">
                  {licitacion.organismo?.nombre || 'Organismo Comprador'}
                </span>
                {licitacion.organismo_rut && (
                  <span className="text-muted-foreground">({formatRUT(licitacion.organismo_rut)})</span>
                )}
              </div>

              {licitacion.region && (
                <div className="flex items-center gap-1.5 text-muted-foreground">
                  <MapPin className="h-3.5 w-3.5 text-muted-foreground" />
                  <span>{licitacion.region}</span>
                </div>
              )}
            </div>
          </div>

          {/* Amount Box & External Link */}
          <div className="flex flex-col items-start gap-2 md:items-end">
            <div className="rounded-xl border border-border/80 bg-muted/40 px-4 py-3 text-right">
              <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
                Monto Estimado
              </span>
              <p className="font-mono text-xl font-bold text-emerald-600 dark:text-emerald-400">
                {licitacion.monto_estimado ? formatCLP(licitacion.monto_estimado) : 'No informado'}
              </p>
            </div>

            {licitacion.link_mercadopublico && (
              <a
                href={licitacion.link_mercadopublico}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
              >
                <span>Ficha oficial MercadoPúblico</span>
                <ExternalLink className="h-3 w-3" />
              </a>
            )}
          </div>
        </div>

        {/* Milestone dates bar */}
        <div className="mt-6 grid grid-cols-2 gap-3 border-t border-border/60 pt-4 sm:grid-cols-4">
          <div>
            <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Publicación</span>
            <p className="mt-0.5 text-xs font-semibold text-foreground">
              {licitacion.fecha_publicacion ? formatDate(licitacion.fecha_publicacion) : '—'}
            </p>
          </div>
          <div>
            <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
              Cierre de Ofertas
            </span>
            <p className="mt-0.5 text-xs font-semibold text-amber-600 dark:text-amber-400">
              {licitacion.fecha_cierre ? formatDate(licitacion.fecha_cierre) : '—'}
            </p>
          </div>
          <div>
            <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Modalidad</span>
            <p className="mt-0.5 text-xs font-semibold text-foreground">
              {licitacion.modalidad || 'Licitación Pública'}
            </p>
          </div>
          <div>
            <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
              Adjudicación Estimada
            </span>
            <p className="mt-0.5 text-xs font-semibold text-foreground">
              {licitacion.adjudicacion?.fecha_adjudicacion
                ? formatDate(licitacion.adjudicacion.fecha_adjudicacion)
                : 'En evaluación'}
            </p>
          </div>
        </div>
      </div>

      {/* Tabs navigation */}
      <div className="flex gap-1 overflow-x-auto border-b border-border/80 pb-1">
        <button
          onClick={() => setActiveTab('general')}
          className={`flex items-center gap-2 whitespace-nowrap border-b-2 px-4 py-2.5 text-xs font-semibold transition-colors ${
            activeTab === 'general'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          <FileText className="h-4 w-4" />
          <span>Ficha General</span>
        </button>

        <button
          onClick={() => setActiveTab('items')}
          className={`flex items-center gap-2 whitespace-nowrap border-b-2 px-4 py-2.5 text-xs font-semibold transition-colors ${
            activeTab === 'items'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          <Package className="h-4 w-4" />
          <span>Ítems Demandados ({licitacion.items?.length || 0})</span>
        </button>

        <button
          onClick={() => setActiveTab('ofertas')}
          className={`flex items-center gap-2 whitespace-nowrap border-b-2 px-4 py-2.5 text-xs font-semibold transition-colors ${
            activeTab === 'ofertas'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          <Users className="h-4 w-4" />
          <span>Ofertas Presentadas ({licitacion.ofertas?.length || 0})</span>
        </button>

        <button
          onClick={() => setActiveTab('adjudicacion')}
          className={`flex items-center gap-2 whitespace-nowrap border-b-2 px-4 py-2.5 text-xs font-semibold transition-colors ${
            activeTab === 'adjudicacion'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          <Award className="h-4 w-4" />
          <span>Cuadro de Adjudicación</span>
        </button>

        <button
          onClick={() => setActiveTab('documentos')}
          className={`flex items-center gap-2 whitespace-nowrap border-b-2 px-4 py-2.5 text-xs font-semibold transition-colors ${
            activeTab === 'documentos'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          <Download className="h-4 w-4" />
          <span>Documentos y Bases ({licitacion.documentos?.length || 0})</span>
        </button>

        <button
          onClick={() => setActiveTab('ia')}
          className={`flex items-center gap-2 whitespace-nowrap border-b-2 px-4 py-2.5 text-xs font-semibold transition-colors ${
            activeTab === 'ia'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          <Sparkles className="h-4 w-4 text-primary" />
          <span>Inteligencia Artificial</span>
        </button>
      </div>

      {/* Tab Contents */}
      <div className="pt-2">
        {/* TAB 1: FICHA GENERAL */}
        {activeTab === 'general' && (
          <div className="space-y-6">
            <Card className="rounded-xl border border-border/80 bg-card p-5 shadow-sm">
              <CardTitle className="mb-3 text-xs font-bold uppercase tracking-wider text-muted-foreground">
                Descripción Oficial del Proceso
              </CardTitle>
              <p className="whitespace-pre-line text-sm leading-relaxed text-foreground">
                {licitacion.descripcion || 'Sin descripción detallada informada en las bases.'}
              </p>
            </Card>

            <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
              <Card className="rounded-xl border border-border/80 bg-card p-5 shadow-sm">
                <CardTitle className="mb-4 flex items-center gap-2 text-sm font-semibold text-foreground">
                  <Building2 className="h-4 w-4 text-primary" />
                  <span>Unidad Compradora y Contacto</span>
                </CardTitle>
                <div className="space-y-3 text-xs text-muted-foreground">
                  <div>
                    <span className="block text-muted-foreground/80">Organismo</span>
                    <p className="font-semibold text-foreground">{licitacion.organismo?.nombre}</p>
                  </div>
                  <div>
                    <span className="block text-muted-foreground/80">Unidad de Compra</span>
                    <p className="text-foreground">
                      {licitacion.unidad_compra || 'Departamento de Adquisiciones'}
                    </p>
                  </div>
                  <div>
                    <span className="block text-muted-foreground/80">Responsable de Proceso</span>
                    <p className="text-foreground">
                      {licitacion.contacto_nombre || 'Comisión Evaluadora'}
                    </p>
                  </div>
                  <div>
                    <span className="block text-muted-foreground/80">Email de Contacto</span>
                    <p className="flex items-center gap-1 text-foreground">
                      <Mail className="h-3.5 w-3.5 text-muted-foreground" />
                      <span>{licitacion.contacto_email || 'contacto@organismo.cl'}</span>
                    </p>
                  </div>
                </div>
              </Card>

              <Card className="rounded-xl border border-border/80 bg-card p-5 shadow-sm">
                <CardTitle className="mb-4 flex items-center gap-2 text-sm font-semibold text-foreground">
                  <ShieldCheck className="h-4 w-4 text-primary" />
                  <span>Condiciones Administrativas y Legales</span>
                </CardTitle>
                <div className="space-y-3 text-xs text-muted-foreground">
                  <div>
                    <span className="block text-muted-foreground/80">Tipo de Convocatoria</span>
                    <p className="text-foreground">
                      {licitacion.tipo_convocatoria || 'Pública Nacional'}
                    </p>
                  </div>
                  <div>
                    <span className="block text-muted-foreground/80">Moneda de Licitación</span>
                    <p className="font-semibold text-foreground">Peso Chileno (CLP)</p>
                  </div>
                  <div>
                    <span className="block text-muted-foreground/80">Fuente de Financiamiento</span>
                    <p className="text-foreground">
                      Presupuesto del Sector Público (FONASA / MINSAL)
                    </p>
                  </div>
                  <div>
                    <span className="block text-muted-foreground/80">Vigencia del Contrato</span>
                    <p className="text-foreground">
                      12 a 24 meses renovable según cumplimiento de SLA
                    </p>
                  </div>
                </div>
              </Card>
            </div>
          </div>
        )}

        {/* TAB 2: ITEMS DEMANDADOS */}
        {activeTab === 'items' && (
          <Card className="overflow-hidden rounded-xl border border-border/80 bg-card shadow-sm">
            <div className="border-b border-border/80 px-5 py-3.5">
              <h3 className="text-sm font-semibold text-foreground">
                Líneas de Productos y Servicios Licitados
              </h3>
              <p className="text-xs text-muted-foreground">
                Especificaciones técnicas mínimas exigidas por el comprador público.
              </p>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-foreground">
                <thead className="border-b border-border/80 bg-muted/40 text-xs font-bold uppercase tracking-wider text-muted-foreground">
                  <tr>
                    <th className="px-4 py-3">#</th>
                    <th className="px-4 py-3">Código UNSPSC</th>
                    <th className="px-4 py-3">Producto / Servicio</th>
                    <th className="px-4 py-3">Cantidad</th>
                    <th className="px-4 py-3 text-right">P. Unit. Estimado</th>
                    <th className="px-4 py-3 text-right">Total Estimado</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/60 bg-card">
                  {(licitacion.items || []).map((item, idx) => {
                    const totalItem = (item.cantidad || 0) * (item.precio_unitario_estimado || 0);
                    return (
                      <tr key={item.id} className="group transition-colors hover:bg-muted/40">
                        <td className="px-4 py-3.5 font-semibold text-muted-foreground">
                          {item.correlativo || idx + 1}
                        </td>
                        <td className="px-4 py-3.5 font-mono text-primary font-semibold">
                          {item.codigo_producto || '42191801'}
                        </td>
                        <td className="max-w-sm px-4 py-3.5">
                          <p className="font-semibold text-foreground">{item.nombre_producto}</p>
                          {item.especificacion_comprador && (
                            <p className="mt-1 line-clamp-2 text-[11px] text-muted-foreground">
                              {item.especificacion_comprador}
                            </p>
                          )}
                        </td>
                        <td className="whitespace-nowrap px-4 py-3.5">
                          <span className="font-semibold text-foreground">{item.cantidad}</span>{' '}
                          <span className="text-muted-foreground">{item.unidad_medida || 'Unidades'}</span>
                        </td>
                        <td className="px-4 py-3.5 text-right font-mono text-foreground">
                          {item.precio_unitario_estimado
                            ? formatCLP(item.precio_unitario_estimado)
                            : '—'}
                        </td>
                        <td className="px-4 py-3.5 text-right font-mono font-semibold text-emerald-600 dark:text-emerald-400">
                          {totalItem > 0 ? formatCLP(totalItem) : '—'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </Card>
        )}

        {/* TAB 3: OFERTAS PRESENTADAS */}
        {activeTab === 'ofertas' && (
          <Card className="overflow-hidden rounded-xl border border-border/80 bg-card shadow-sm">
            <div className="border-b border-border/80 px-5 py-3.5">
              <h3 className="text-sm font-semibold text-foreground">
                Ofertas Económicas y Técnicas Recibidas
              </h3>
              <p className="text-xs text-muted-foreground">
                Proveedores del Estado que han formalizado postulación a esta licitación.
              </p>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-foreground">
                <thead className="border-b border-border/80 bg-muted/40 text-xs font-bold uppercase tracking-wider text-muted-foreground">
                  <tr>
                    <th className="px-4 py-3">Proveedor</th>
                    <th className="px-4 py-3">RUT</th>
                    <th className="px-4 py-3">Fecha de Envío</th>
                    <th className="px-4 py-3 text-right">Monto Ofertado (CLP)</th>
                    <th className="px-4 py-3 text-center">Estado</th>
                    <th className="px-4 py-3 text-center">Resultado</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/60 bg-card">
                  {(licitacion.ofertas || []).map((of) => (
                    <tr key={of.id} className="group transition-colors hover:bg-muted/40">
                      <td className="px-4 py-3.5 font-semibold text-foreground">
                        {of.proveedor_nombre}
                      </td>
                      <td className="px-4 py-3.5 font-mono text-muted-foreground">
                        {formatRUT(of.proveedor_rut)}
                      </td>
                      <td className="px-4 py-3.5 text-muted-foreground">
                        {of.fecha_oferta ? formatDate(of.fecha_oferta) : '—'}
                      </td>
                      <td className="px-4 py-3.5 text-right font-mono font-bold text-emerald-600 dark:text-emerald-400">
                        {formatCLP(of.monto_total)}
                      </td>
                      <td className="px-4 py-3.5 text-center">
                        <span className="rounded-md border border-border/80 bg-muted/60 px-2 py-0.5 text-[11px] font-medium text-muted-foreground">
                          {of.estado || 'Aceptada'}
                        </span>
                      </td>
                      <td className="px-4 py-3.5 text-center">
                        {of.es_adjudicada ? (
                          <Badge
                            variant="outline"
                            className="border-emerald-500/20 bg-emerald-50 font-semibold text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300"
                          >
                            Adjudicada
                          </Badge>
                        ) : (
                          <span className="text-xs text-muted-foreground">—</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        )}

        {/* TAB 4: ADJUDICACION */}
        {activeTab === 'adjudicacion' && (
          <div className="space-y-6">
            {licitacion.adjudicacion ? (
              <>
                <Card className="rounded-xl border border-border/80 bg-card p-5 shadow-sm">
                  <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
                    <div>
                      <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                        Proveedor Ganador
                      </span>
                      <h3 className="mt-0.5 text-lg font-bold text-foreground">
                        {licitacion.adjudicacion.proveedor_ganador_nombre}
                      </h3>
                      <p className="mt-0.5 font-mono text-xs font-semibold text-primary">
                        RUT: {formatRUT(licitacion.adjudicacion.proveedor_ganador_rut || '')}
                      </p>
                    </div>

                    <div className="text-left sm:text-right">
                      <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                        Monto Adjudicado Total
                      </span>
                      <p className="font-mono text-2xl font-bold text-emerald-600 dark:text-emerald-400">
                        {formatCLP(licitacion.adjudicacion.monto_total_adjudicado || 0)}
                      </p>
                      <p className="mt-0.5 text-xs text-muted-foreground">
                        Resolución: {licitacion.adjudicacion.numero_resolucion}
                      </p>
                    </div>
                  </div>
                </Card>

                {licitacion.adjudicacion.criterios_evaluacion && (
                  <Card className="rounded-xl border border-border/80 bg-card p-5 shadow-sm">
                    <CardTitle className="mb-3 text-sm font-semibold text-foreground">
                      Puntajes Obtenidos en la Matriz de Evaluación
                    </CardTitle>
                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-xs text-foreground">
                        <thead className="border-b border-border/80 bg-muted/40 text-xs font-bold uppercase tracking-wider text-muted-foreground">
                          <tr>
                            <th className="px-4 py-2.5">Criterio Evaluado</th>
                            <th className="px-4 py-2.5 text-center">Ponderación (%)</th>
                            <th className="px-4 py-2.5 text-right">Puntaje Obtenido</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-border/60 bg-card">
                          {licitacion.adjudicacion.criterios_evaluacion.map((c, i) => (
                            <tr key={i} className="group transition-colors hover:bg-muted/40">
                              <td className="px-4 py-3 font-medium text-foreground">{c.criterio}</td>
                              <td className="px-4 py-3 text-center text-muted-foreground">
                                {c.ponderacion}%
                              </td>
                              <td className="px-4 py-3 text-right font-mono font-bold text-emerald-600 dark:text-emerald-400">
                                {c.puntaje.toFixed(1)} / 100
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </Card>
                )}
              </>
            ) : (
              <Card className="rounded-xl border border-border/80 bg-card p-8 text-center text-muted-foreground shadow-sm">
                <Clock className="mx-auto mb-2 h-8 w-8 text-amber-500" />
                <h4 className="font-semibold text-foreground">Proceso en Fase de Evaluación</h4>
                <p className="mx-auto mt-1 max-w-md text-xs text-muted-foreground">
                  La comisión evaluadora aún no ha emitido el acta ni la resolución definitiva de
                  adjudicación para esta licitación.
                </p>
              </Card>
            )}
          </div>
        )}

        {/* TAB 5: DOCUMENTOS Y BASES */}
        {activeTab === 'documentos' && (
          <Card className="overflow-hidden rounded-xl border border-border/80 bg-card shadow-sm">
            <div className="border-b border-border/80 px-5 py-3.5">
              <h3 className="text-sm font-semibold text-foreground">
                Bases, Resoluciones y Anexos de la Convocatoria
              </h3>
              <p className="text-xs text-muted-foreground">
                Descarga oficial de documentos técnicos y administrativos asociados.
              </p>
            </div>

            <div className="divide-y divide-border/60">
              {(licitacion.documentos || []).map((doc) => (
                <div
                  key={doc.id}
                  className="flex items-center justify-between px-5 py-3.5 transition-colors hover:bg-muted/40"
                >
                  <div className="flex items-center gap-3">
                    <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-border/80 bg-muted text-primary">
                      <FileText className="h-4 w-4" />
                    </div>
                    <div>
                      <p className="text-xs font-semibold text-foreground">{doc.nombre}</p>
                      <p className="text-[11px] text-muted-foreground">
                        {doc.fecha ? formatDate(doc.fecha) : '—'} • {doc.tamano_kb || 250} KB
                      </p>
                    </div>
                  </div>

                  <Button
                    variant="outline"
                    size="sm"
                    className="h-8 gap-1.5 border-border/80 bg-background text-xs text-foreground hover:bg-muted"
                    onClick={() => alert(`Descargando archivo: ${doc.nombre}`)}
                  >
                    <Download className="h-3.5 w-3.5" />
                    <span>Descargar</span>
                  </Button>
                </div>
              ))}
            </div>
          </Card>
        )}

        {/* TAB 6: INTELIGENCIA ARTIFICIAL */}
        {activeTab === 'ia' && <LicitacionAiInsights insights={licitacion.clasificacion_ia} />}
      </div>
    </div>
  );
};
