<!-- prompt: docs@1.0.0 | agente: Documentador -->
TAREA: Documentador. Redacta la documentación técnica y funcional del sistema legacy (as-is) y del nuevo (to-be) para equipos técnicos, de negocio y de auditoría.

Entregas:
- overview_md: visión general en Markdown (propósito de negocio, flujo as-is, qué hace cada unidad relevante, riesgos y lógica de infraestructura que NO se migra, y cómo se resolvió en el to-be). Sin repetir el catálogo de reglas completo (se adjunta aparte); referencia reglas por ID.
- data_dictionary: diccionario de datos (nombre, tipo legacy, tipo moderno, descripción).
- architecture_mermaid: diagrama Mermaid `flowchart LR` de componentes del sistema nuevo (domain / application / infrastructure, puertos y adaptadores) con la regla de dependencias. Solo sintaxis Mermaid válida, sin caracteres especiales en los identificadores.
- sequence_mermaid: diagrama Mermaid `sequenceDiagram` del caso de uso principal (entrada -> validaciones -> tasa -> cálculo -> resultado).
- glossary: términos de dominio.
- executive_summary: máximo 120 palabras orientadas a negocio (valor, riesgo mitigado).
- assumptions: supuestos asumidos durante la traducción.
