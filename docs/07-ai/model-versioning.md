# Versionado de modelos

Cada modelo entrenado (clasificador supervisado, modelo de embeddings) se
registra como una fila de `ModelVersion` (`app/models/knowledge.py`),
identificada por `(name, version)`, con un `status` que sigue el ciclo de
vida definido en `ModelLifecycleState` (`app/nlp/contracts.py`).

## Estados

| Estado | Significado |
| --- | --- |
| `draft` | Modelo entrenado y registrado, aún no evaluado para promoción. Estado inicial de toda `ModelVersion`. |
| `staging` | Candidato bajo evaluación — puede probarse contra tráfico de sombra o el Gold Dataset, pero no sirve predicciones de producción. |
| `production` | Versión activa que el pipeline usa para clasificar licitaciones reales. |
| `archived` | Superada o retirada. Terminal: un modelo archivado no vuelve a activarse; para reintroducir una idea de modelo se entrena y registra una `ModelVersion` nueva, que reingresa en `draft`. |

## Transiciones permitidas

`validate_model_transition(current, target)` (`app/nlp/contracts.py`) es la
función pura que fija qué transiciones son válidas:

```
draft      -> staging, archived
staging    -> production, draft, archived
production -> staging, archived      # staging = paso de rollback (democión)
archived   -> (ninguna, terminal)
```

Cualquier otra transición (por ejemplo `draft -> production` directo, o salir
de `archived`) lanza `ValueError`. Esto es intencional: ningún modelo llega a
producción sin pasar por `staging`, y un rollback siempre reutiliza el mismo
camino de promoción (`staging -> production`) en vez de un atajo especial.

## Promoción y rollback

- **Promoción**: `draft -> staging` cuando el modelo está listo para
  evaluación; `staging -> production` cuando cumple los criterios mínimos
  (6.23 "MLOps & Evaluation" define esos criterios — este documento solo fija
  el mecanismo de transición, no los umbrales de métricas).
- **Rollback**: se demueve la `ModelVersion` en producción a `staging`
  (`production -> staging`), y se vuelve a promover una versión anterior que
  siga en `staging` o que se reactive desde `archived` entrenando una fila
  nueva. No existe una transición directa `production -> production` entre
  dos filas: cada cambio de modelo activo es una democión seguida de una
  promoción, ambas auditables por separado.

## Invariante de unicidad (documentada, no forzada en DB todavía)

A lo más una `ModelVersion` por `(name, kind)` debe estar en `production` a la
vez. Hoy esto no está forzado por un constraint de base de datos — se aplicará
en la capa de repositorio cuando 6.6 "Knowledge Layer" implemente la
persistencia real (no existe todavía ninguna migración Alembic para el schema
`knowledge`).

## Trazabilidad histórica

Cada `Classification` persistida guarda su propio `model_version_id`
(`app/models/knowledge.py`). Promover o revertir un modelo cambia qué versión
se usa para *nuevas* clasificaciones; nunca reescribe el `model_version_id` de
una fila histórica. Esto es el mismo principio ya documentado en
`architecture.md`: "promover o revertir un artefacto selecciona otra versión y
nunca modifica una ejecución histórica".

## Por qué `status` sigue siendo `String`, no un tipo ENUM de Postgres

`ModelVersion.status` (`app/models/knowledge.py`) es un `String(32)` validado
en la capa de dominio, no un `CHECK`/`ENUM` de base de datos — el mismo patrón
que ya usan `Category.taxonomy_version` y `Keyword.dictionary_version`:
versión/estado como columna simple, validación en Python. Codificar esta regla
en DDL antes de que exista la capa de repositorio que la aplica (6.6)
introduciría dos lugares (el tipo de columna y `validate_model_transition`)
que podrían desalinearse, y un `ALTER TYPE` es más costoso de evolucionar que
una función pura. El acoplamiento entre el valor por defecto de la columna
(`"draft"`) y `ModelLifecycleState.DRAFT.value` está cubierto por un test
(`tests/models/test_knowledge.py::test_model_version_default_status_matches_draft_lifecycle_state`),
no por un import cruzado entre `app/models` y `app/nlp`.
