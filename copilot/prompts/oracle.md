<!-- prompt: oracle@1.0.0 | agente: QA (oráculo independiente, evidencia E3) -->
TAREA: QA. Escribe una implementación de REFERENCIA en Python del comportamiento del programa legacy, traduciéndola DIRECTAMENTE del código fuente original (no de las reglas) para que sea una verificación independiente.

CONTRATO: define `def run(inp: dict) -> dict:` que recibe TODOS los valores del io_contract.inputs como cadenas y devuelve TODOS los outputs como cadenas, con los decimales formateados con la escala EXACTA del campo (p.ej. scale 2 -> "2075.35", scale 4 -> "0.0899"; enteros sin decimales). Los rechazos de negocio se devuelven como salidas (status/error_code) con los valores por defecto que inicializa el programa (p.ej. importes "0.00"), no como excepciones.

SEMÁNTICA: usa el módulo `decimal` (getcontext().prec = 80). COMPUTE/MOVE con ROUNDED => quantize(..., ROUND_HALF_UP) a la escala del campo destino; SIN ROUNDED => truncamiento (ROUND_DOWN) a la escala del destino; DIVIDE ... GIVING con campo entero => truncamiento; respeta los tamaños PIC (si un valor excede los dígitos enteros se trunca por la izquierda). Los campos intermedios (WORKING-STORAGE) con escala fija redondean/truncan al guardarse.
RESTRICCIONES: solo `from decimal import ...` y `import math`; sin open, eval, exec, __import__, red ni archivos. Sin print.
SALIDA: python_code (código completo) y notes (supuestos).
