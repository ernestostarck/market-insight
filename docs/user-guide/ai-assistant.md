# Guía de Uso del Asistente IA Conversacional

El **Asistente IA de MercadoInsight** te permite interactuar con la base de datos de compras públicas utilizando lenguaje natural, formulando preguntas como si hablaras con un analista sénior de mercado.

---

## 1. ¿Cómo Funciona el Asistente?

A diferencia de chatbots genéricos de Internet, el Asistente de MercadoInsight **no inventa respuestas ni adivina cifras**:
1. **Analiza tu pregunta**: Determina si estás solicitando un cálculo numérico (ej. montos de gasto) o una búsqueda conceptual (ej. licitaciones afines).
2. **Consulta la base de datos oficial**: Ejecuta consultas SQL seguras sobre datos de compras públicas o busca por similitud semántica con `pgvector`.
3. **Responde con Fuentes Citadas**: Redacta una respuesta clara y concisa donde cada cifra o afirmación incluye una **tarjeta de fuente** vinculada a la licitación o resolución oficial.

---

## 2. Ejemplos de Preguntas que Puedes Hacer

### Consultas Cuantitativas y de Gasto
- *"¿Cuánto gastó el Hospital San José en insumos de traumatología durante el primer semestre de 2025?"*
- *"Compara las 3 principales empresas adjudicadas en Senadis por monto total en 2024."*
- *"¿Cuál fue el precio promedio adjudicado de camas clínicas eléctricas el año pasado?"*

### Búsquedas Semánticas y Conceptuales
- *"Busca licitaciones vigentes orientadas a la inclusión de personas con discapacidad visual."*
- *"¿Qué municipalidades de la Región de Valparaíso han comprado ayudas técnicas recientemente?"*
- *"Resume los requisitos técnicos principales de la licitación 1058-12-LR26."*

---

## 3. Cómo Interpretar las Fuentes Citadas

Debajo de cada respuesta del asistente verás una sección titulada **Fuentes de Evidencia**:
- Cada tarjeta contiene el **código oficial de la licitación**, el **organismo comprador**, el **monto involucrado** y la fecha.
- Haz clic en cualquier tarjeta para abrir directamente la ficha oficial en MercadoInsight y verificar el documento original.

> [!TIP]
> Si una respuesta no incluye fuentes citadas, el sistema te advertirá que no cuenta con evidencia suficiente en los registros públicos para responder con certeza.

---

## 4. Retroalimentación y Mejora Continua

Junto a cada respuesta del asistente encontrarás dos botones:
- 👍 **Útil**: Indica que la respuesta fue precisa y resolvió tu consulta.
- 👎 **No útil / Error**: Si detectas una discrepancia o consideras que faltó información, haz clic aquí y déjanos un comentario breve. Un analista revisará el caso para mejorar los algoritmos del sistema.

---

## 5. Limitaciones Importantes

- El Asistente IA **no puede postular a licitaciones en tu nombre** en el portal de Mercado Público.
- El asistente no tiene acceso a información confidencial o no publicada en las actas oficiales de ChileCompra.
- Para decisiones legales o contractuales vinculantes, siempre debes consultar las bases oficiales y resoluciones firmadas por el organismo comprador.
