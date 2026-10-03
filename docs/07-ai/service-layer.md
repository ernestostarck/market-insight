# NLP Service Layer (Fase 6.18)

Capa de servicios de aplicación para el dominio de procesamiento de lenguaje natural (NLP) y clasificación de compras públicas.
Ubicada en `app/services/nlp/` y orquestada con contratos formales en `app/services/nlp/interfaces.py`.

## Objetivos y Principios de Diseño

1. **Separación de Responsabilidades**: Desacoplar la lógica pura de NLP (tokenización, matching léxico, inferencia semántica) de los controladores HTTP y la persistencia en base de datos.
2. **Contratos Formales (Protocols)**: Todos los servicios implementan interfaces definidas mediante `typing.Protocol` con `@runtime_checkable`, permitiendo verificación estática de tipos con `mypy` y testing mediante inyección de dependencias y fakes.
3. **Composición Modular**: Servicios de orden superior (ej. `ClassificationService`) coordinan servicios especializados (`PreprocessingService`, `RuleClassificationService`, `EmbeddingService`, `TaxonomyService`, `RelevanceService`).
4. **Compatibilidad Hacia Atrás**: Se mantiene la fachada `NLPService` (anteriormente en `app/services/nlp.py`), exportada directamente desde `app/services/nlp/__init__.py`.

---

## Contratos de Interfaz (`app/services/nlp/interfaces.py`)

Se definen 11 protocolos `@runtime_checkable`:
- `IPreprocessingService`
- `IDictionaryService`
- `ITaxonomyService`
- `IRuleClassificationService`
- `IEmbeddingService`
- `ISemanticSearchService`
- `IClassificationService`
- `IEntityExtractionService`
- `IProductExtractionService`
- `IRelevanceService`
- `IReviewService`

---

## Catálogo de los 11 Servicios

### 1. `PreprocessingService` (`app/services/nlp/preprocessing.py`)
- **Responsabilidad**: Limpieza unicode (NFKC), normalización léxica, unescape de entidades HTML, detección de idioma y partición en fragmentos (`Chunk`).
- **Métodos**:
  - `preprocess(text: str) -> PreprocessedText`
  - `build_tender_document(title, description, item_texts) -> PreprocessedText`
  - `build_consolidated_document(licitacion_id, title, description, item_texts) -> TenderDocument`
  - `async process_and_store_tender(...) -> Document`

### 2. `DictionaryService` (`app/services/nlp/dictionary.py`)
- **Responsabilidad**: Acceso y búsqueda sobre el diccionario semántico versionado (`DomainDictionary`), mapeo de sinónimos y abreviaturas especializadas en geriatría, discapacidad y ayudas técnicas.
- **Métodos**:
  - `find_matches(text: str) -> list[DictionaryMatch]`
  - `get_entry(term: str) -> DictionaryEntry | None`
  - `list_terms(theme: DomainTheme | None = None) -> list[DictionaryEntry]`
  - `get_version() -> str`

### 3. `TaxonomyService` (`app/services/nlp/taxonomy.py`)
- **Responsabilidad**: Gestión de la taxonomía jerárquica de 3 niveles (`Category` -> `Subcategory` -> `Concept`), validación de integridad referencial y resolución de códigos estables.
- **Métodos**:
  - `resolve_category(code: str) -> TaxonomyCategory | None`
  - `resolve_subcategory(category_code: str, subcategory_code: str) -> TaxonomySubcategory | None`
  - `locate_concept(concept_code: str) -> tuple[TaxonomyCategory, TaxonomySubcategory, DomainConcept] | None`
  - `get_hierarchy() -> dict[str, Any]`
  - `validate() -> list[str]`

### 4. `RuleClassificationService` (`app/services/nlp/rules.py`)
- **Responsabilidad**: Clasificación determinística y explicable basada en reglas de palabras clave y expresiones regulares (`RuleEngine`).
- **Métodos**:
  - `evaluate(text: str) -> RuleEvaluation`
  - `evaluate_tender(title: str, description: str | None, items: list[str]) -> RuleEvaluation`

### 5. `EmbeddingService` (`app/services/nlp/embeddings.py`)
- **Responsabilidad**: Wrapper del modelo de lenguaje (`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`) con generación de vectores de 384 dimensiones normalizados y cálculo de similitud coseno.
- **Métodos**:
  - `encode(texts: Iterable[str]) -> np.ndarray`
  - `compute_similarity(vector_a: np.ndarray, vector_b: np.ndarray) -> float`

### 6. `SemanticSearchService` (`app/services/nlp/semantic_search.py`)
- **Responsabilidad**: Búsqueda vectorial semántica sobre pgvector combinando embeddings de consultas con vectores precalculados de nodos taxonómicos y licitaciones históricas.
- **Métodos**:
  - `async search(query: str, top_k=10, min_similarity=0.0, category_code=None) -> list[SimilarLicitacion]`
  - `async find_similar_to_licitacion(licitacion_id: int, top_k=10, min_similarity=0.0) -> list[SimilarLicitacion]`
  - `async search_by_concept(concept_code: str, top_k=10, min_similarity=0.0) -> list[SimilarLicitacion]`
  - `async search_by_category(category_code: str, top_k=10, min_similarity=0.0) -> list[SimilarLicitacion]`

### 7. `ClassificationService` (`app/services/nlp/classification.py`)
- **Responsabilidad**: Clasificación híbrida coordinada. Combina la señal determinística por reglas, la señal semántica vectorial y la predicción del modelo supervisado mediante la política de resolución de conflictos (`combine_signals`).
- **Métodos**:
  - `async classify_text(text: str, still_open: bool = True) -> dict[str, Any]`
  - `async classify_and_store_tender(...) -> Classification`

### 8. `EntityExtractionService` (`app/services/nlp/entities.py`)
- **Responsabilidad**: Extracción de entidades nombradas estructuradas (organismo, región, comuna) y textuales (monto, cantidad, unidad, fecha, marca, modelo).
- **Métodos**:
  - `extract_entities(text: str, ...) -> list[ExtractedEntity]`
  - `async extract_and_store(licitacion_id: int, text: str, ...) -> list[Entity]`

### 9. `ProductExtractionService` (`app/services/nlp/products.py`)
- **Responsabilidad**: Identificación de conceptos de producto en ítems y extracción de atributos técnicos de ingeniería (materiales, dimensiones, capacidad de carga, características mecánicas/eléctricas).
- **Métodos**:
  - `extract_product_concepts(text: str) -> tuple[ProductConceptMatch, ...]`
  - `extract_product_attributes(text: str) -> ProductAttributes`
  - `process_item(licitacion_id, licitacion_item_id, item_nombre, ...) -> list[Product]`

### 10. `RelevanceService` (`app/services/nlp/relevance.py`)
- **Responsabilidad**: Cálculo de relevancia de mercado desacoplado de la confianza taxonómica. Diferencia relevancia temática (si coincide con nuestro nicho) de relevancia comercial (si la licitación se encuentra abierta y actionable).
- **Métodos**:
  - `compute(rule_score, similarity_score, model_score, still_open) -> RelevanceResult`
  - `assess_tender(rule_score, similarity_score, model_score, fecha_cierre) -> RelevanceResult`

### 11. `ReviewService` (`app/services/nlp/review.py`)
- **Responsabilidad**: Gestión del ciclo de vida de Human-in-the-Loop. Detección de incertidumbre y señales contradictorias, cola de revisión de baja confianza, registro de decisiones humanas (aceptar/modificar) y retroalimentación al Gold Dataset.
- **Métodos**:
  - `evaluate_confidence(confidence_score, ...) -> ConfidenceAssessment`
  - `get_queue(connection, threshold, limit, offset, only_unreviewed) -> list[ReviewQueueItem]`
  - `accept(connection, classification_id, reviewer_id, ...) -> uuid.UUID`
  - `modify(connection, classification_id, reviewer_id, category_code, ...) -> uuid.UUID`
  - `sync_gold_dataset(connection, dataset_version_id) -> dict[str, Any]`
  - `get_stats(connection) -> dict[str, Any]`

---

## Fachada y Compatibilidad

Para evitar roturas en los puntos de entrada existentes (`app/api/v1/endpoints/nlp.py`, `app/db/dependencies.py`):
```python
from app.services.nlp import NLPService
```
La fachada `NLPService` (`app/services/nlp/facade.py`) continúa exponiendo los endpoints sincrónicos `preprocess`, `classify_by_rules` y `submit` preservando la compatibilidad de firma y esquemas Pydantic (`NLPPreprocessResponse`, `RuleClassificationResponse`).

---

## Verificación y Tests

Cobertura unitaria completa en `tests/services/test_nlp_services.py` con 13 pruebas unitarias:
- Verificación de contratos mediante `isinstance(service, IService)` para los 11 servicios.
- Tests asíncronos y síncronos con aislamiento mediante mocks.
- Flujos de persistencia y serialización de modelos de conocimiento.
