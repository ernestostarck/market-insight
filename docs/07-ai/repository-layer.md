# Knowledge Repository Layer (Fase 6.19)

Capa de acceso a datos (`AsyncSession` de SQLAlchemy) para el esquema `knowledge.*`.
Ubicada en `app/repositories/knowledge.py` y exportada a través de `app/repositories/__init__.py`.

## Arquitectura y Principios de Diseño

1. **Persistencia asíncrona dedicada**: Cada repositorio recibe una instancia de `sqlalchemy.ext.asyncio.AsyncSession`.
2. **Encapsulamiento de consultas**: Toda consulta SELECT, JOIN, INSERT o UPDATE sobre tablas de `knowledge.*` se centraliza en su respectivo repositorio, aislando los servicios de las particularidades de SQL/ORM.
3. **Manejo de claves y relaciones**:
   - Tablas con UUID primario (`documents`, `chunks`, `classifications`, `embeddings`, `entities`, `relationships`, `human_reviews`, `model_versions`, `dataset_versions`) gestionan `uuid.UUID` nativo.
   - Tablas con ID serial (`categories`, `subcategories`, `concepts`, `keywords`, `rules`) gestionan identificadores enteros e indexación por códigos de versión.
4. **Desacoplamiento transaccional**: Los repositorios realizan `flush()` o `commit()` según la operación, permitiendo coordinar transacciones externas cuando se componen múltiples operaciones.

---

## Los 11 Repositorios

### 1. `DocumentRepository`
- **Tabla objetivo**: `knowledge.documents`
- **Métodos clave**:
  - `get_by_id(id: uuid.UUID) -> Document | None`
  - `get_by_licitacion_id(licitacion_id: int) -> list[Document]`
  - `get_by_content_hash(licitacion_id: int, content_hash: str) -> Document | None`: Detección de duplicados e idempotencia en ingesta.
  - `create(document: Document) -> Document`
  - `delete(id: uuid.UUID) -> bool`

### 2. `ChunkRepository`
- **Tabla objetivo**: `knowledge.chunks`
- **Métodos clave**:
  - `get_by_id(id: uuid.UUID) -> Chunk | None`
  - `get_by_document_id(document_id: uuid.UUID) -> list[Chunk]`: Recupera chunks ordenados por `sequence ASC`.
  - `create(chunk: Chunk) -> Chunk`
  - `create_many(chunks: list[Chunk]) -> list[Chunk]`: Inserción eficiente en lote.
  - `delete_by_document_id(document_id: uuid.UUID) -> int`

### 3. `EntityRepository`
- **Tabla objetivo**: `knowledge.entities`
- **Métodos clave**:
  - `get_by_id(id: uuid.UUID) -> Entity | None`
  - `get_by_licitacion_id(licitacion_id: int, entity_type: str | None = None) -> list[Entity]`
  - `get_by_classification_id(classification_id: uuid.UUID) -> list[Entity]`
  - `create(entity: Entity) -> Entity`
  - `create_many(entities: list[Entity]) -> list[Entity]`
  - `delete_by_licitacion_id(licitacion_id: int) -> int`

### 4. `ConceptRepository`
- **Tabla objetivo**: `knowledge.concepts`
- **Métodos clave**:
  - `get_by_id(id: int) -> Concept | None`
  - `get_by_code(code: str, taxonomy_version: str | None = None) -> Concept | None`
  - `list_by_subcategory(subcategory_id: int) -> list[Concept]`
  - `create(concept: Concept) -> Concept`

### 5. `ClassificationRepository`
- **Tabla objetivo**: `knowledge.classifications`
- **Métodos clave**:
  - `get_by_id(id: uuid.UUID) -> Classification | None`
  - `get_latest_by_licitacion_id(licitacion_id: int) -> Classification | None`: Última clasificación generada por fecha (`created_at DESC`).
  - `list_by_licitacion_id(licitacion_id: int) -> list[Classification]`
  - `list_by_category(category_id: int, limit: int = 50, offset: int = 0) -> list[Classification]`
  - `create(classification: Classification) -> Classification`

### 6. `EmbeddingRepository`
- **Tabla objetivo**: `knowledge.embeddings`
- **Métodos clave**:
  - `get_by_id(id: uuid.UUID) -> Embedding | None`
  - `get_latest_by_licitacion_id(licitacion_id: int) -> Embedding | None`
  - `get_by_document_id(document_id: uuid.UUID) -> Embedding | None`
  - `create(embedding: Embedding) -> Embedding`

### 7. `RelationshipRepository`
- **Tabla objetivo**: `knowledge.relationships`
- **Métodos clave**:
  - `get_by_id(id: uuid.UUID) -> Relationship | None`
  - `get_by_licitacion_id(licitacion_id: int) -> list[Relationship]`
  - `get_by_subject(subject_id: uuid.UUID) -> list[Relationship]`
  - `get_by_object(object_id: uuid.UUID) -> list[Relationship]`
  - `create(relationship: Relationship) -> Relationship`
  - `create_many(relationships: list[Relationship]) -> list[Relationship]`

### 8. `TaxonomyRepository`
- **Tablas objetivo**: `knowledge.categories`, `knowledge.subcategories`, `knowledge.concepts`
- **Métodos clave**:
  - `get_category_by_code(code: str, version: str | None = None) -> Category | None`
  - `get_subcategory_by_code(code: str, category_id: int | None = None) -> Subcategory | None`
  - `list_categories(version: str | None = None) -> list[Category]`
  - `list_subcategories(category_id: int) -> list[Subcategory]`
  - `create_category(category: Category) -> Category`
  - `create_subcategory(subcategory: Subcategory) -> Subcategory`

### 9. `DictionaryRepository`
- **Tablas objetivo**: `knowledge.keywords`, `knowledge.rules`
- **Métodos clave**:
  - `get_keyword_by_id(id: int) -> Keyword | None`
  - `list_keywords(dictionary_version: str | None = None) -> list[Keyword]`
  - `create_keyword(keyword: Keyword) -> Keyword`
  - `get_rule_by_id(id: int) -> Rule | None`
  - `list_rules(active_only: bool = True) -> list[Rule]`
  - `create_rule(rule: Rule) -> Rule`

### 10. `ModelRepository`
- **Tablas objetivo**: `knowledge.model_versions`, `knowledge.dataset_versions`
- **Métodos clave**:
  - `get_model_version(id: uuid.UUID) -> ModelVersion | None`
  - `get_active_model_version(name: str) -> ModelVersion | None`: Busca el modelo en estado `promoted` o `champion`.
  - `list_model_versions(name: str | None = None) -> list[ModelVersion]`
  - `create_model_version(version: ModelVersion) -> ModelVersion`
  - `get_dataset_version(id: uuid.UUID) -> DatasetVersion | None`
  - `create_dataset_version(version: DatasetVersion) -> DatasetVersion`

### 11. `HumanReviewRepository`
- **Tabla objetivo**: `knowledge.human_reviews`
- **Métodos clave**:
  - `get_by_id(id: uuid.UUID) -> HumanReview | None`
  - `get_by_classification_id(classification_id: uuid.UUID) -> HumanReview | None`
  - `list_by_reviewer(reviewer_id: uuid.UUID, limit: int = 50, offset: int = 0) -> list[HumanReview]`
  - `create(review: HumanReview) -> HumanReview`

---

## Verificación y Tests

Se cuenta con cobertura unitaria completa en `tests/repositories/test_knowledge_repositories.py`:
- 11 pruebas unitarias usando `AsyncMock` para simular la sesión de SQLAlchemy.
- Validación de parámetros de consulta, filtrado por versión y ordenamiento.
