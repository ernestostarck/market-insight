import { useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';

export interface GlobalFilterValues {
  startDate?: string;
  endDate?: string;
  categoria?: string;
  region?: string;
  organismo?: string;
  proveedor?: string;
  estado?: string;
  montoMin?: number;
  montoMax?: number;
}

export function useGlobalFilters() {
  const [searchParams, setSearchParams] = useSearchParams();

  const filters: GlobalFilterValues = useMemo(() => {
    return {
      startDate: searchParams.get('startDate') || undefined,
      endDate: searchParams.get('endDate') || undefined,
      categoria: searchParams.get('categoria') || undefined,
      region: searchParams.get('region') || undefined,
      organismo: searchParams.get('organismo') || undefined,
      proveedor: searchParams.get('proveedor') || undefined,
      estado: searchParams.get('estado') || undefined,
      montoMin: searchParams.get('montoMin') ? Number(searchParams.get('montoMin')) : undefined,
      montoMax: searchParams.get('montoMax') ? Number(searchParams.get('montoMax')) : undefined,
    };
  }, [searchParams]);

  const activeFilterCount = useMemo(() => {
    return Object.values(filters).filter((v) => v !== undefined && v !== '').length;
  }, [filters]);

  const setFilter = (key: keyof GlobalFilterValues, value: string | number | undefined) => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      if (value === undefined || value === '') {
        next.delete(key);
      } else {
        next.set(key, String(value));
      }
      return next;
    });
  };

  const setFilters = (newValues: Partial<GlobalFilterValues>) => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      Object.entries(newValues).forEach(([k, v]) => {
        if (v === undefined || v === '') {
          next.delete(k);
        } else {
          next.set(k, String(v));
        }
      });
      return next;
    });
  };

  const clearFilters = () => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      const keysToDelete: (keyof GlobalFilterValues)[] = [
        'startDate',
        'endDate',
        'categoria',
        'region',
        'organismo',
        'proveedor',
        'estado',
        'montoMin',
        'montoMax',
      ];
      keysToDelete.forEach((k) => next.delete(k));
      return next;
    });
  };

  const applyQuickPreset = (
    preset: 'last-30-days' | 'year-2026',
  ) => {
    switch (preset) {
      case 'last-30-days': {
        const today = new Date();
        const past30 = new Date(today);
        past30.setDate(today.getDate() - 30);
        setFilters({
          startDate: past30.toISOString().split('T')[0],
          endDate: today.toISOString().split('T')[0],
        });
        break;
      }
      case 'year-2026':
        setFilters({
          startDate: '2026-01-01',
          endDate: '2026-12-31',
        });
        break;
    }
  };

  return {
    filters,
    activeFilterCount,
    setFilter,
    setFilters,
    clearFilters,
    applyQuickPreset,
  };
}
