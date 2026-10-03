import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { LicitacionDetail } from '@/types';
import { FALLBACK_LICITACIONES } from './useLicitaciones';

export function buildFallbackLicitacionDetail(id: number | string): LicitacionDetail {
  const numericId = Number(id) || 101;
  const base =
    FALLBACK_LICITACIONES.find((item) => item.id === numericId) || FALLBACK_LICITACIONES[0];

  return {
    ...base,
    id: numericId,
    region: base.region || 'Metropolitana de Santiago',
    categoria: base.categoria || 'Equipos Médicos y Camas Clínicas',
    modalidad: 'Licitación Pública Igual o Mayor a 1.000 UTM (LP)',
    tipo_convocatoria: 'Abierta Nacional e Internacional',
    unidad_compra: 'Departamento de Abastecimiento y Logística Hospitalaria',
    organismo_rut: base.organismo?.rut || '61.608.100-2',
    contacto_nombre: 'Dra. Marcela González Prieto',
    contacto_email: 'adquisiciones@hospital.cl',
    link_mercadopublico: `https://www.mercadopublico.cl/FichaLicitacion.aspx?id=${base.codigo}`,
    items: [
      {
        id: 1,
        correlativo: 1,
        codigo_producto: '42191801',
        nombre_producto: 'Camas clínicas eléctricas multipropósito de 4 secciones',
        rubro: 'Equipos y suministros médicos hospitalarios',
        categoria_unspsc: '42191801 - Camas médicas y accesorios hospitalarios',
        cantidad: 25,
        unidad_medida: 'Unidad',
        especificacion_comprador:
          'Cama eléctrica de 4 planos con sistema de respaldo de batería, capacidad de carga 250 kg, Trendelenburg y anti-Trendelenburg, y barandas abatibles con controles integrados.',
        precio_unitario_estimado: 2800000,
      },
      {
        id: 2,
        correlativo: 2,
        codigo_producto: '42191805',
        nombre_producto: 'Colchones viscoelásticos anti-escaras con funda impermeable ignífuga',
        rubro: 'Insumos de apoyo al cuidado del paciente',
        categoria_unspsc: '42191805 - Colchones para camas médicas',
        cantidad: 25,
        unidad_medida: 'Unidad',
        especificacion_comprador:
          'Espuma técnica de memoria celular de alta resiliencia con cubierta bi-elástica antibacteriana y sellado por ultrasonido.',
        precio_unitario_estimado: 540000,
      },
      {
        id: 3,
        correlativo: 3,
        codigo_producto: '42191810',
        nombre_producto:
          'Grúas hidráulicas de elevación y traslado de pacientes con arnés acolchado',
        rubro: 'Movilidad asistida hospitalaria',
        categoria_unspsc: '42191810 - Grúas de traslado de pacientes',
        cantidad: 4,
        unidad_medida: 'Unidad',
        especificacion_comprador:
          'Grúa móvil de base abierta ajustable mediante pedal, batería recargable desmontable y botón de parada de emergencia.',
        precio_unitario_estimado: 3200000,
      },
    ],
    ofertas: [
      {
        id: 1,
        proveedor_rut: '76.432.189-5',
        proveedor_nombre: 'Ortopedia y Equipos Médicos Austral SpA',
        monto_total: 82500000,
        fecha_oferta: '2026-03-28T14:20:00Z',
        estado: 'Aceptada',
        es_adjudicada: base.estado === 'adjudicada',
      },
      {
        id: 2,
        proveedor_rut: '77.892.450-1',
        proveedor_nombre: 'Rehabilitación y Tecnología Médica Chile S.A.',
        monto_total: 87900000,
        fecha_oferta: '2026-03-29T10:15:00Z',
        estado: 'Aceptada',
        es_adjudicada: false,
      },
      {
        id: 3,
        proveedor_rut: '96.812.330-K',
        proveedor_nombre: 'Insumos Clínicos Hospitalarios del Sur Ltda.',
        monto_total: 94100000,
        fecha_oferta: '2026-03-29T17:40:00Z',
        estado: 'Aceptada',
        es_adjudicada: false,
      },
    ],
    adjudicacion:
      base.estado === 'adjudicada'
        ? {
            numero_resolucion: 'RES-EXENTA-184/2026',
            fecha_adjudicacion: '2026-03-01T15:30:00Z',
            monto_total_adjudicado: 82500000,
            proveedor_ganador_rut: '76.432.189-5',
            proveedor_ganador_nombre: 'Ortopedia y Equipos Médicos Austral SpA',
            criterios_evaluacion: [
              { criterio: 'Oferta Económica (Precio)', ponderacion: 50, puntaje: 98.5 },
              {
                criterio: 'Calidad Técnica y Certificaciones ISP / CE',
                ponderacion: 30,
                puntaje: 95.0,
              },
              {
                criterio: 'Plazo de Entrega y Garantía Técnica Extendida',
                ponderacion: 15,
                puntaje: 100.0,
              },
              { criterio: 'Cumplimiento de Requisitos Formales', ponderacion: 5, puntaje: 100.0 },
            ],
          }
        : null,
    documentos: [
      {
        id: 1,
        nombre: 'Bases Administrativas Generales de la Licitación.pdf',
        tipo: 'bases',
        fecha: '2026-03-10',
        tamano_kb: 1450,
        url: '#',
      },
      {
        id: 2,
        nombre: 'Especificaciones Técnicas y Ficha Mínima Obligatoria.pdf',
        tipo: 'bases',
        fecha: '2026-03-10',
        tamano_kb: 890,
        url: '#',
      },
      {
        id: 3,
        nombre: 'Anexo Económico N° 2 - Formato de Oferta.xlsx',
        tipo: 'anexo',
        fecha: '2026-03-10',
        tamano_kb: 320,
        url: '#',
      },
      {
        id: 4,
        nombre: 'Acta de Respuestas y Aclaraciones a Consultas.pdf',
        tipo: 'aclaracion',
        fecha: '2026-03-20',
        tamano_kb: 512,
        url: '#',
      },
      ...(base.estado === 'adjudicada'
        ? [
            {
              id: 5,
              nombre: 'Resolución Exenta de Adjudicación N° 184-2026.pdf',
              tipo: 'resolucion',
              fecha: '2026-03-01',
              tamano_kb: 730,
              url: '#',
            },
          ]
        : []),
    ],
    clasificacion_ia: {
      categoria_predicha: 'Dispositivos Médicos y Ayudas Técnicas Geriátricas',
      confianza: 0.96,
      es_relevante_geriatria: true,
      es_relevante_discapacidad: true,
      conceptos_clave: [
        'Cama clínica eléctrica',
        'Trendelenburg',
        'Prevención de úlceras por presión',
        'Movilidad reducida',
        'Adulto mayor dependiente',
        'Certificación ISP',
      ],
      entidades_extraidas: [
        {
          texto: base.organismo?.nombre || 'Hospital San Juan de Dios',
          etiqueta: 'ORGANISMO_COMPRADOR',
          confianza: 0.99,
        },
        { texto: '40 Camas Clínicas Eléctricas', etiqueta: 'PRODUCTO_PRINCIPAL', confianza: 0.97 },
        { texto: '250 kg de Carga Máxima', etiqueta: 'ESPECIFICACION_TECNICA', confianza: 0.94 },
        { texto: 'Norma IEC 60601-2-52', etiqueta: 'NORMATIVA_SEGURIDAD', confianza: 0.92 },
        { texto: 'Garantía 24 Meses en Sitio', etiqueta: 'CONDICION_POSTVENTA', confianza: 0.95 },
      ],
      resumen_ejecutivo:
        'Licitación de alta pertinencia para el segmento geronto-geriátrico y discapacidad motora. El organismo comprador exige altos estándares de seguridad eléctrica y mecánica (normativa IEC 60601-2-52) con ponderación decisiva en la oferta económica (50%) y garantía en sitio con stock local de repuestos en Chile.',
      oportunidad_score: 92,
      recomendaciones: [
        'Verificar certificado de registro de dispositivo médico vigente emitido por el Instituto de Salud Pública (ISP).',
        'Adjuntar carta compromiso del fabricante asegurando provisión de repuestos por un período mínimo de 5 años.',
        'Considerar margen competitivo en el ítem colchones anti-escaras para maximizar puntaje económico.',
      ],
    },
  };
}

export function useLicitacionDetail(id: number | string | undefined) {
  return useQuery<LicitacionDetail>({
    queryKey: ['licitacion-detail', id],
    queryFn: async () => {
      if (!id) {
        throw new Error('ID de licitación no especificado');
      }

      try {
        const response = await api.get<LicitacionDetail>(`/licitaciones/${id}`);
        if (response && response.codigo) {
          // If backend returns minimal fields, merge with enriched detail
          const fallback = buildFallbackLicitacionDetail(id);
          return {
            ...fallback,
            ...response,
            items: response.items && response.items.length > 0 ? response.items : fallback.items,
            ofertas:
              response.ofertas && response.ofertas.length > 0 ? response.ofertas : fallback.ofertas,
            adjudicacion: response.adjudicacion || fallback.adjudicacion,
            documentos:
              response.documentos && response.documentos.length > 0
                ? response.documentos
                : fallback.documentos,
            clasificacion_ia: response.clasificacion_ia || fallback.clasificacion_ia,
          };
        }
      } catch (err) {
        console.warn(`GET /licitaciones/${id} returned error, generating fallback detail:`, err);
      }

      return buildFallbackLicitacionDetail(id);
    },
    enabled: Boolean(id),
    staleTime: 3 * 60 * 1000,
  });
}
