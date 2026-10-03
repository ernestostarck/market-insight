# Monitoreo de NLP y Distinción entre Cambio de Distribución y Model Drift (Fase 8.9.14)

## 1. Contexto

En MercadoInsight, el pipeline de Procesamiento de Lenguaje Natural (NLP) clasifica automáticamente licitaciones públicas y genera representaciones vectoriales (embeddings) para búsqueda híbrida y recomendación.

El sistema supervisa de manera continua:
- **`nlp_documents_processed_total`**: Volumen de documentos procesados por etapa.
- **`nlp_classifications_total`**: Conteo de clasificaciones por categoría y método (`rules`, `semantic`, `classifier`, `hybrid`).
- **`nlp_low_confidence_total`**: Cantidad de inferencias con confianza inferior a 0.70.
- **`nlp_processing_duration_seconds`**: Latencia por etapa (P50, P95, P99).
- **`nlp_category_distribution_total`**: Distribución de frecuencias de categorías asignadas.
- **`nlp_data_drift_kl_divergence`**: Divergencia Kullback-Leibler calculada entre la ventana reciente y la distribución histórica de referencia.

---

## 2. Principio Operacional: Cambio de Distribución vs. Model Drift

> [!IMPORTANT]
> **Principio Clave:** Un cambio en la distribución de categorías observadas (`nlp_category_distribution_total` o aumento en `nlp_data_drift_kl_divergence`) **NO implica automáticamente una degradación o descalibración del modelo (Model Drift)**.

### Causas Normales de Cambio en la Distribución de Compras Públicas
Las compras y contrataciones del Estado en ChileCompra presentan estacionalidad y dinamismo intrínseco debido a:
1. **Estacionalidad Sectorial:** 
   - Aumento considerable de licitaciones de salud y medicamentos durante invierno.
   - Incremento de licitaciones de obras públicas y vialidad en primavera/verano.
   - Cierre de año fiscal y presupuestario en noviembre/diciembre (alza en tecnología y suministros generales).
2. **Eventos y Emergencias Nacionales:**
   - Catástrofes naturales (inundaciones, incendios forestales) que concentran transitoriamente las compras en maquinaria y ayuda social.
3. **Cambios Normativos y Políticas Públicas:**
   - Creación de nuevos convenios marco o fondos concursables extraordinarios.

---

## 3. Criterios de Diagnóstico y Toma de Decisión

Para diferenciar entre variación normal del mercado y verdadero **Model Drift**, los operadores deben evaluar la combinación de tres factores:

| Escenario | Confianza Promedio | Tasa de Aprobación Humana (HitL) | Interpretación | Acción Recomendada |
| :--- | :--- | :--- | :--- | :--- |
| **Variación del Mercado** | Estable ($\ge 0.85$) | Alta ($\ge 90\%$) | La economía pública está comprando rubros diferentes pero el modelo los clasifica con precisión. | **Ninguna.** Mantener monitoreo. No reentrenar. |
| **Nueva Terminología / Vocabulario Emergente** | Reducida en categoría específica | Media ($\approx 75\%$) | Han aparecido términos técnicos novedosos no presentes en el dataset de entrenamiento. | Incorporar nuevos términos al vocabulario o reglas y etiquetar lote de muestra. |
| **Verdadero Model Drift** | Caída generalizada ($< 0.70$) | Baja ($< 70\%$) | El clasificador supervisado y el espacio semántico ya no discriminan adecuadamente. | **Planificar reentrenamiento** con la última versión de dataset etiquetado (`dataset_version`). |

---

## 4. Reglas de Alerta Operacionales

- **`NLPLowConfidenceSurge`**: Se dispara únicamente si la proporción de documentos con confianza $< 0.70$ supera el **30% del total** durante más de 30 minutos.
- **`NLPHighErrorRate`**: Se dispara si los fallos en inferencia o extracción superan el **5%**.
- **`NLPEmbeddingModelFailure`**: Alerta crítica inmediata si la API de embeddings o el modelo local deja de generar representaciones.
