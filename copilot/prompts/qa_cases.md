<!-- prompt: qa_cases@1.0.0 | agente: QA -->
TAREA: QA. Genera casos de prueba de caracterización y equivalencia (entradas) para el io_contract, usando el catálogo de reglas aprobado. NO calcules salidas esperadas (las calcula el oráculo).

Requisitos:
- Entre 24 y 40 casos con datos REALISTAS del dominio bancario/asegurador (sintéticos).
- Cubre TODAS las reglas aprobadas (rule_ids) y, para cada una: caso nominal, ambos lados de cada umbral (límite exacto, justo debajo, justo arriba), y casos de redondeo (valores que dejen el decimal en exactamente .5 en el último dígito retenido cuando sea posible), truncamientos por división entera, signos/cero, máximos y mínimos de rango y rechazos por cada código de error.
- category: nominal | boundary | rounding | truncation | error | sign | overflow.
- input: lista de {name, value} con TODOS los inputs del io_contract; value siempre cadena (decimales con punto, p.ej. "100000.00").
- name: identificador snake_case único y descriptivo; rationale: por qué el caso es relevante.
