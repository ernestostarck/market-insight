# Manual de IA — MercadoInsight AI

Este documento constituye el manual de referencia técnico y conceptual de **MercadoInsight AI**, explicando su arquitectura, capacidades, mecanismos de consulta, salvaguardas y limitaciones.

---

## Principio Rector Fundamental

> [!IMPORTANT]
> **La IA no es ni debe presentarse como la fuente primaria de información.**
> La fuente primaria e inmutable de verdad continúa siendo la información de contratación pública oficial de ChileCompra / Mercado Público, almacenada, normalizada y auditada en MercadoInsight. La IA actúa estrictamente como una interfaz analítica y de síntesis sobre dicha evidencia.

---

## 1. ¿Qué Puede Hacer?

MercadoInsight AI está diseñado para:
1. **Búsqueda Semántica**: Identificar compras públicas por significado e intención conceptual, superando la limitación de palabras clave exactas.
2. **Síntesis y Resumen de Bases**: Extraer requisitos técnicos, plazos de entrega, garantías y criterios de evaluación a partir de bases extensas.
3. **Análisis Cuantitativo en Lenguaje Natural**: Traducir preguntas de gasto, montos acumulados y comparativas de precios a consultas analíticas determinísticas.
4. **Comparativa de Proveedores**: Analizar perfiles de oferentes, tasas de adjudicación y cuotas de mercado en licitaciones afines.
5. **Detección de Oportunidades**: Evaluar y priorizar procesos de compra según el nicho especializado de accesibilidad y geriatría.

---

## 2. ¿Qué Datos Utiliza?

La IA opera **exclusivamente** sobre los datos estructurados y no estructurados procesados en la base de datos de MercadoInsight:
- **Esquema Canónico (`core`)**: Licitaciones, ítems, ofertas económicas, adjudicaciones, proveedores y organismos compradores.
- **Esquema Semántico (`knowledge`)**: Representaciones vectoriales (`pgvector`), extracciones de entidades nombradas (NER) y taxonomías de dominio.
- **Esquema Analítico (`dw` y `marts`)**: Tablas de hechos históricos y agregaciones de gasto público por período, rubro y geografía.

La IA **no tiene acceso a datos privados de los usuarios**, conversaciones de otros analistas ni información que no haya sido publicada formalmente por los organismos del Estado.

---

## 3. ¿Cómo Realiza una Búsqueda?

La búsqueda no es un simple prompt enviado a un LLM. Sigue un pipeline estructurado de recuperación:
1. **Preprocesamiento**: Normalización lingüística, eliminación de ruido y extracción de términos clave.
2. **Generación de Embeddings**: Conversión del texto de consulta a un vector denso de 384 dimensiones mediante `sentence-transformers` (`all-MiniLM-L6-v2`).
3. **Búsqueda Vectorial HNSW**: Consulta de similitud coseno sobre los índices vectoriales de `knowledge.embeddings`.
4. **Búsqueda Full-Text (FTS)**: Consulta léxica paralela con `tsvector` en español para capturar nombres exactos de marcas o modelos.
5. **Fusión Recíproca de Rangos (RRF)**: Combinación de ambos ordenamientos mediante la fórmula:
   $$\text{Score}(d) = \frac{1}{60 + \text{rank}_{\text{FTS}}(d)} + \frac{1}{60 + \text{rank}_{\text{Vector}}(d)}$$

---

## 4. ¿Cuándo Utiliza SQL?

La IA utiliza la estrategia **Text-to-SQL** cuando la intención de la consulta es cuantitativa o agregada:
- Preguntas que involucran sumatorias, promedios, conteos o comparativas numéricas (ej. *"¿Cuánto gastó el Ministerio de Salud en 2024?"*).
- Consultas con filtros categóricos directos sobre atributos relacionales (ej. *"Top 5 proveedores por monto adjudicado en la Región del Maule"*).
- En estos casos, la consulta es ejecutada por el motor PostgreSQL sobre el Data Warehouse, garantizando una exactitud matemática del 100%, libre de alucinaciones numéricas.

---

## 5. ¿Cuándo Utiliza RAG?

La IA utiliza la estrategia **Retrieval-Augmented Generation (RAG)** cuando la consulta es conceptual, cualitativa o de síntesis:
- Búsqueda de licitaciones por descripción técnica (ej. *"Licitaciones que exijan certificación ISO 13485"*).
- Explicación de requisitos o condiciones de adjudicación.
- Análisis temático de bases donde la respuesta requiere resumir fragmentos de texto recuperados.

---

## 6. ¿Cómo Calcula Indicadores?

Los indicadores y KPIs **nunca son calculados internamente por el modelo de lenguaje**. El flujo es:
1. El backend ejecuta consultas estructuradas sobre las vistas precalculadas (`marts.*`).
2. El resultado tabular exacto (ejemplo: `{"total_monto": 45000000, "licitaciones_count": 12}`) se inyecta como dato factual en el contexto del LLM.
3. El LLM únicamente redacta la respuesta en lenguaje natural utilizando los números provistos.

---

## 7. ¿Qué Significa una Fuente?

Una **Fuente** (*Source*) es una tarjeta de trazabilidad vinculada a un registro concreto de la base de datos oficial. Toda afirmación cuantitativa o factual en la respuesta está respaldada por una fuente con:
- **Código de Licitación / Identificador Oficial**: Enlace directo a la ficha del proceso.
- **RUT y Razón Social**: Del organismo comprador o del proveedor adjudicado.
- **Monto y Fecha Oficial**: Extraídos de las actas de adjudicación.
- **Fragmento de Evidencia**: Párrafo exacto de las bases técnicas de donde se extrajo el requisito.

---

## 8. ¿Qué Sucede Cuando No Encuentra Información?

Si la búsqueda en la base de datos no devuelve registros coincidentes con los filtros o la consulta solicitada:
- El sistema **no inventa información ni genera datos ficticios**.
- Responde de forma transparente:
  > *"No se encontraron registros de licitaciones u órdenes de compra que coincidan con los criterios consultados en la base de datos oficial de MercadoInsight."*
- Sugiere al usuario flexibilizar los filtros de fecha, ampliar el rango geográfico o probar términos más generales.

---

## 9. ¿Cuáles Son Sus Limitaciones?

- **Ventana de Ingesta**: La información disponible refleja los datos sincronizados por el pipeline ETL hasta la última ejecución programada.
- **Sin Capacidad Transaccional Externa**: La IA no puede enviar preguntas en foros de licitaciones ni postular ofertas en el portal de ChileCompra.
- **No Emite Opinión Legal**: La síntesis de bases técnicas tiene carácter informativo de referencia y no sustituye la asesoría jurídica o la lectura directa de las resoluciones administrativas.

---

## 10. ¿Cómo Se Protege Contra Prompt Injection?

MercadoInsight implementa una defensa multicapa:
1. **Aislamiento de Mensajes**: Las instrucciones del sistema (*System Prompt*) no son modificables por el usuario ni por los textos de las licitaciones.
2. **Delimitación XML de Contexto**: Todo texto externo se encapsula dentro de etiquetas XML (`<evidence_document>`), instruyendo al modelo a tratarlo estrictamente como dato no ejecutable.
3. **Guardrails SQL Determinísticos**: Las consultas SQL generadas por la IA son validadas sintácticamente con analizadores AST, bloqueando cualquier comando que no sea `SELECT` de solo lectura.
4. **Permisos de Base de Datos**: El usuario de base de datos asignado a la IA (`ai_analyst`) posee únicamente el permiso `pg_read_all_data`, imposibilitando escrituras, alteraciones o borrados.

---

## 11. ¿Cómo Se Evalúa?

La calidad de MercadoInsight AI es monitoreada de forma continua mediante:
- **Grounding Faithfulness Score**: Mide qué porcentaje de las frases de la respuesta derivan de fuentes reales provistas en el prompt. Umbral mínimo: $80\%$.
- **Benchmarking sobre Gold Dataset**: Suite de 20 licitaciones representativas evaluada en cada commit, asegurando un $F_1$ Macro $\ge 90\%$ y exactitud de relevancia $\ge 95\%$.
- **Monitoreo de Data Drift**: Medición de divergencia estadística (Kullback-Leibler) en las distribuciones de texto de compras públicas para detectar cambios en el vocabulario oficial.
- **Telemetría de Costos**: Registro granular de tokens de entrada/salida y costo en USD por cada interacción.
