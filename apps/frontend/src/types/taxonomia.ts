export interface TaxonomiaConcepto {
  code: string;
  name: string;
  description: string;
}

export interface TaxonomiaSubcategoria {
  code: string;
  name: string;
  description: string;
  concepts: TaxonomiaConcepto[];
}

export interface TaxonomiaCategoria {
  code: string;
  name: string;
  description: string;
  subcategories: TaxonomiaSubcategoria[];
}

export interface Taxonomia {
  version: string;
  categories: TaxonomiaCategoria[];
}
