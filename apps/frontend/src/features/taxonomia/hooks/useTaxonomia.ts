import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { Taxonomia } from '@/types';

// Mirrors app/nlp/data/taxonomy-2026.3.json — used only if /nlp/taxonomy is unreachable,
// so the sector tree (incl. "Vestuario") still renders offline/on error.
export const FALLBACK_TAXONOMIA: Taxonomia = {
  version: 'taxonomy-2026.3',
  categories: [
    {
      code: 'technology',
      name: 'Tecnología',
      description: 'Software, hardware, comunicaciones y servicios digitales.',
      subcategories: [
        { code: 'hardware', name: 'Hardware', description: 'Computadores, periféricos y equipamiento tecnológico.', concepts: [] },
        { code: 'software', name: 'Software', description: 'Licencias, plataformas y desarrollo de software.', concepts: [] },
      ],
    },
    {
      code: 'health',
      name: 'Salud',
      description: 'Equipamiento, insumos y servicios destinados a la salud.',
      subcategories: [
        { code: 'medical-equipment', name: 'Equipamiento médico', description: 'Dispositivos y equipamiento clínico.', concepts: [] },
        { code: 'medical-supplies', name: 'Insumos médicos', description: 'Materiales y consumibles clínicos.', concepts: [] },
        {
          code: 'geriatric-care',
          name: 'Atención geriátrica y adulto mayor',
          description: 'Servicios y equipamiento orientados a la atención de personas mayores.',
          concepts: [
            { code: 'geriatria', name: 'Geriatría', description: 'Atención médica especializada en personas mayores.' },
            { code: 'adultos_mayores', name: 'Adultos mayores', description: 'Bienes y servicios dirigidos a personas de la tercera edad.' },
          ],
        },
        {
          code: 'assistive-technology',
          name: 'Ayudas técnicas y rehabilitación',
          description: 'Dispositivos de asistencia y servicios de rehabilitación para personas con discapacidad o movilidad reducida.',
          concepts: [
            { code: 'discapacidad', name: 'Discapacidad', description: 'Bienes y servicios dirigidos a personas en situación de discapacidad.' },
            { code: 'movilidad_reducida', name: 'Movilidad reducida', description: 'Ayudas de movilidad para personas con desplazamiento limitado.' },
            { code: 'ayudas_tecnicas', name: 'Ayudas técnicas', description: 'Dispositivos de asistencia para personas con discapacidad.' },
            { code: 'rehabilitacion', name: 'Rehabilitación', description: 'Servicios y terapias de rehabilitación física y funcional.' },
          ],
        },
      ],
    },
    {
      code: 'construction',
      name: 'Construcción',
      description: 'Obras, mantención de infraestructura y materiales de construcción.',
      subcategories: [
        { code: 'civil-works', name: 'Obras civiles', description: 'Construcción, reparación y mejoramiento de infraestructura.', concepts: [] },
        { code: 'construction-materials', name: 'Materiales de construcción', description: 'Materiales y suministros para obras.', concepts: [] },
        {
          code: 'accessibility-adaptation',
          name: 'Accesibilidad y adaptación de espacios',
          description: 'Obras y adaptaciones para mejorar la accesibilidad física de espacios.',
          concepts: [
            { code: 'accesibilidad', name: 'Accesibilidad', description: 'Condiciones y adaptaciones que permiten el acceso universal a espacios y servicios.' },
            { code: 'prevencion_caidas', name: 'Prevención de caídas', description: 'Adaptaciones orientadas a reducir el riesgo de caídas.' },
            { code: 'adaptacion_espacios', name: 'Adaptación de espacios', description: 'Modificaciones de infraestructura para adecuarla a necesidades de accesibilidad.' },
          ],
        },
      ],
    },
    {
      code: 'transport',
      name: 'Transporte',
      description: 'Vehículos, logística, movilidad y sus servicios asociados.',
      subcategories: [
        { code: 'vehicles', name: 'Vehículos', description: 'Vehículos, repuestos y accesorios.', concepts: [] },
        { code: 'logistics', name: 'Logística', description: 'Transporte de carga, distribución y servicios logísticos.', concepts: [] },
      ],
    },
    {
      code: 'professional-services',
      name: 'Servicios profesionales',
      description: 'Consultorías, asesorías y servicios especializados.',
      subcategories: [
        { code: 'consulting', name: 'Consultoría', description: 'Asesorías y estudios especializados.', concepts: [] },
        { code: 'training', name: 'Capacitación', description: 'Formación, talleres y entrenamiento.', concepts: [] },
      ],
    },
    {
      code: 'general-supplies',
      name: 'Suministros generales',
      description: 'Bienes de consumo y suministros operacionales.',
      subcategories: [
        { code: 'office-supplies', name: 'Útiles de oficina', description: 'Papelería y artículos de oficina.', concepts: [] },
        { code: 'cleaning-supplies', name: 'Aseo', description: 'Productos y materiales de limpieza.', concepts: [] },
      ],
    },
    {
      code: 'apparel',
      name: 'Vestuario',
      description: 'Prendas de vestir y textiles, ajenos al mercado de geriatría/accesibilidad/discapacidad.',
      subcategories: [
        {
          code: 'shapewear',
          name: 'Vestimenta moldeadora',
          description: 'Fajas y prendas reductoras/moldeadoras de uso corporal.',
          concepts: [
            { code: 'faja_reductora', name: 'Faja reductora', description: 'Prenda moldeadora de compresión corporal con fines estéticos, sin uso ortopédico ni clínico.' },
            { code: 'faja_moldeadora_short', name: 'Faja moldeadora tipo short', description: 'Faja body moldeadora tipo short sin costuras.' },
            { code: 'faja_moldeadora_colaless', name: 'Faja moldeadora tipo colaless', description: 'Faja body moldeadora tipo colaless (tanga) con cierre frontal.' },
          ],
        },
      ],
    },
  ],
};

export function useTaxonomia() {
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  const query = useQuery({
    queryKey: ['taxonomia'],
    queryFn: async (): Promise<Taxonomia> => {
      try {
        const response = await api.get<Taxonomia>('/nlp/taxonomy');
        if (response?.categories?.length) return response;
      } catch (err) {
        console.warn('API /nlp/taxonomy returned error, using fallback taxonomy:', err);
      }
      return FALLBACK_TAXONOMIA;
    },
    staleTime: 10 * 60 * 1000,
  });

  const categories = useMemo(() => query.data?.categories ?? [], [query.data]);

  const toggleCategory = (code: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(code)) next.delete(code);
      else next.add(code);
      return next;
    });
  };

  return {
    version: query.data?.version,
    categories,
    isLoading: query.isLoading,
    isFetching: query.isFetching,
    refetch: query.refetch,
    expanded,
    toggleCategory,
  };
}
