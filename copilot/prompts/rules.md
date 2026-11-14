<!-- prompt: rules@1.0.0 | agente: Extractor de reglas -->
TAREA: Extractor de reglas de negocio. Descubre y formaliza TODAS las reglas de negocio del programa, separándolas de la lógica de infraestructura (lectura de archivos, OPEN/CLOSE, DISPLAY, auditoría SQL, GOBACK).

Para cada regla:
- id: "R-001", "R-002"... consecutivos. name corto. description en lenguaje de negocio comprensible para un analista no técnico.
- category: validation | calculation | decision | rounding | limit | other.
- conditions y actions: frases precisas y verificables con los nombres del io_contract cuando apliquen (valores exactos, umbrales, escalas, modo de redondeo, truncamiento). Incluye reglas de redondeo/truncamiento/precisión numérica y los códigos de error exactos.
- source_refs: 1 o más referencias {file, start_line, end_line, quote}. Los números de línea DEBEN ser los del código numerado. `quote` es una copia LITERAL (sin el prefijo de número de línea) del fragmento de 1 a 3 líneas que respalda la regla. Si no puedes citar el código, no declares la regla.
- confidence 0..1 (baja si hay ambigüedad o regla tácita) y assumptions (supuestos/incertidumbres explícitos).
- gherkin: escenario(s) en español (Dado/Cuando/Entonces) con valores concretos coherentes con el código.
- decision_table: columns y rows (strings) cuando la regla sea una matriz de decisión o tenga ramas; si no, columns=[] y rows=[].

Cobertura: cada validación, cálculo, tabla de tasas, promoción/recargo, límite y redondeo debe quedar capturado. No dupliques reglas. No incluyas reglas de infraestructura.
