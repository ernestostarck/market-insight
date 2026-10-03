# Knowledge Layer

Esquema `knowledge` (Postgres) — persiste lo que las fases 6.1-6.5 diseñaron
como código/JSON. Modelos en `app/models/knowledge.py`, migración en
`alembic/versions/20260821_0008_create_knowledge_schema.py`.

## Las 14 tablas

**Taxonomía (3 niveles, persistidos)**: `categories` → `subcategories` →
`concepts`. Cada nivel lleva `taxonomy_version` propio — una fila no se
edita al publicar una versión nueva, se agrega otra con el mismo `code` y
distinto `taxonomy_version` (append-only, igual que `app/nlp/taxonomy.py`).
`concepts.code` es donde vive el puente formal con `DomainTheme.value`
(`app/nlp/dictionary.py`) documentado en [`taxonomy.md`](taxonomy.md).

**Diccionario y reglas**: `keywords` (persistencia de `DictionaryEntry`,
con `taxonomy_version` + `dictionary_version` propios) y `rules` (Fase 6.7).
Ambas opcionalmente ligadas a `category_id`/`subcategory_id` — no a
`concept_id` todavía (ver "Fuera de alcance").

**Versionado de artefactos**: `model_versions`, `dataset_versions` —
persistencia de `ArtifactVersions`/`ModelLifecycleState` (`app/nlp/contracts.py`).

**Documentos**: `documents` → `chunks` — persistencia de `TenderDocument`/
`DocumentChunk` (`app/nlp/document.py`, Fase 6.2).

**Resultados de NLP**: `embeddings` (pgvector, `VECTOR(384)`),
`classifications`, `entities`, `relationships`, `human_reviews` — todavía
sin productores (Fases 6.7-6.17), pero la estructura y sus FKs a
`core.licitacion` ya están listas.

## `Relationship` — diseño

No tenía especificación previa en el TODO. Se modela como una arista entre
dos filas de `Entity` (`subject_entity_id` → `predicate` → `object_entity_id`),
con `confidence_score` y scopeada a `licitacion_id`. Pensada para cuando
6.11 (NER) y 6.12 (extracción de producto/atributos) generen relaciones
entre entidades extraídas del mismo documento (ej. "silla de ruedas"
`tiene_atributo` "plegable").

## Fuera de alcance de 6.6 (explícito)

- **Seed de la taxonomía real**: la migración crea la *estructura* de
  `categories`/`subcategories`/`concepts` — no carga las filas de
  `taxonomy-2026.2.json`. Eso es de un `TaxonomyService` (6.18) o un loader
  dedicado.
- **`keywords.concept_id` / `rules.concept_id`**: 6.7 posee explícitamente
  "Implementar asociación término -> concepto" como ítem propio; la
  asociación real (código de tabla o resolución en runtime vía
  `DomainTheme`/`DomainConcept.code`) se decide ahí.

## Migración y estado de la base de datos

Al construir 6.6 se encontró que la base de datos dev de Docker estaba 6
migraciones atrás del head del repo (solo `staging` aplicado) — el esquema
`core`/`dw`/datamarts/`users` nunca se había aplicado a una base real. Se
corrieron y depuraron todas, exponiendo 5 bugs preexistentes de Fase 4/5
(ninguno de esta fase) que bloqueaban `alembic upgrade head`:

1. `dw.fact_licitacion_partitioned.licitacion_id` (VARCHAR) comparado sin
   cast contra `core.licitacion.id` (INTEGER) en 2 vistas materializadas
   (`20260807_0006`).
2. Mismo problema con `fact_adjudicacion_partitioned.adjudicacion_id` (1 vista).
3. `mv_market_monthly` (`b642bda69c3d`) referenciaba una columna
   `licitacion_key` inexistente en `fact_licitacion_partitioned`.
4. `v_disability_contracts` (`b642bda69c3d`) usaba una columna
   `fa.licitacion_id` inexistente en `fact_adjudicacion_partitioned`.
5. `5df623f8d1b8` recreaba las mismas vistas que `b642bda69c3d` sin
   `OR REPLACE`/`DROP ... IF EXISTS` (fallaba por "ya existe"), referenciaba
   `core.licitaciones` (no existe, es `core.licitacion`) y usaba `do` como
   alias de tabla (palabra reservada en Postgres).

Todos corregidos con el mínimo cambio posible (casts, `OR REPLACE`, rename
de alias) — ninguno se había aplicado nunca a una base real, así que no hay
historial de despliegue que romper. Además, `20260819_0007` (tabla `users`)
se hizo idempotente (`IF NOT EXISTS` vía inspección) porque la base dev ya
tenía una tabla `users` creada fuera de Alembic (con datos de prueba reales
que se preservaron).

Con eso, `alembic upgrade head` corre limpio de punta a punta contra
Postgres real, y se validó con un script transaccional (insert + read +
rollback) que insertó y leyó una fila encadenada por FK en las 14 tablas de
`knowledge` (incluyendo `core.licitacion`/`core.organismo`/`users`), sin
dejar datos de prueba.

## Ver también

- [`taxonomy.md`](taxonomy.md) — jerarquía de 3 niveles en `app/nlp/taxonomy.py`.
- [`semantic-dictionary.md`](semantic-dictionary.md) — `DomainDictionary`/`DictionaryEntry`.
- [`document-processing.md`](document-processing.md) — `TenderDocument`/`DocumentChunk`.
- [`model-versioning.md`](model-versioning.md) — `ArtifactVersions`/`ModelLifecycleState`.
