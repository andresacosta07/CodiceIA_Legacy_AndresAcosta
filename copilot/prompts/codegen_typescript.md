<!-- prompt: codegen_typescript@1.0.0 | agentes: Arquitecto + Desarrollador -->
TAREA: Arquitecto y Desarrollador. A partir del CATÁLOGO DE REGLAS APROBADO (fuente de verdad; ignora reglas rechazadas) y del io_contract, diseña y genera un proyecto TypeScript (Node.js) con Arquitectura Limpia/Hexagonal y DDD.

ESTRUCTURA OBLIGATORIA (rutas exactas):
- src/domain/...        entidades, value objects, servicios de dominio, specifications/strategies por regla, excepciones. NO importa de application ni infrastructure. Sin frameworks.
- src/application/...   casos de uso y PUERTOS (interfaces). Importa solo de domain.
- src/infrastructure/... adaptadores (p.ej. adaptador de entrada que mapea strings a tipos del dominio, puertos de salida simulados en memoria para auditoría). Puede importar de application y domain.
- src/index.ts          punto de entrada: `export function execute(input: Record<string, string>): Record<string, string>` — recibe y devuelve TODOS los valores como cadenas (decimales con su escala exacta, p.ej. "2075.35", "0.0899"). Compone dependencias (composition root) y delega al caso de uso. Sin lógica de negocio.
- package.json          {"name": "...", "version": "1.0.0", "type": "module", "scripts": {"test": "node --test"}}
- README.md breve.
NO generes src/domain/shared/decimal.ts: la plataforma lo provee. Impórtalo con `import { Decimal } from '../shared/decimal.ts'` (ajusta la ruta relativa). API: Decimal.of(string|integer), .plus .minus .times (exactos), .dividedBy(other, scale, mode), .pow(intExp) exacto, .setScale(scale, mode) (mode: 'HALF_UP' = COBOL ROUNDED, 'DOWN' = truncamiento sin ROUNDED), .truncateToPic(intDigits, scale), .compareTo/.equals/.lt/.lte/.gt/.gte, .isZero, .toInteger(), .toString() (conserva la escala).

REGLAS DE CÓDIGO (se validan automáticamente):
- SOLO sintaxis TypeScript "borrable" (se ejecuta con Node sin compilar): sin enum, sin namespace, sin parameter properties (declara los campos y asígnalos en el constructor), usa `import type` para tipos y SIEMPRE extensión .ts en los imports relativos. Usa `readonly` y clases/funciones.
- PROHIBIDO number/float/double para importes, tasas o cálculos (usa Decimal). Prohibido Math.round/parseFloat/Number() sobre decimales.
- PROHIBIDO: eval, Function, require, import dinámico, process, fs, child_process, http/net/fetch, variables globales mutables, console.log.
- Reproduce con exactitud la semántica del legacy: escalas intermedias (cada COMPUTE ROUNDED redondea a la escala del campo destino con HALF_UP; sin ROUNDED trunca con DOWN), truncamiento de divisiones enteras, límites inclusivos/exclusivos, valores por defecto de salida en rechazos.
- Los errores de negocio NO son excepciones: se devuelven como salida (status/error_code del io_contract). Usa objetos de resultado tipados.
- Cada función/método de dominio que implementa una regla lleva en su JSDoc la etiqueta `@rule R-001` (varias si aplica). Todas las reglas aprobadas deben quedar implementadas y etiquetadas.
- Métodos cortos: complejidad ciclomática ≤ 10 por método (descompón en specifications/estrategias).
- Nombres significativos del dominio, una responsabilidad por clase, SOLID.
- Inventa solo lo imprescindible; no agregues dependencias npm.

SALIDA: design (resumen, modelo de dominio, puertos, patrones, ADRs con contexto/decisión/consecuencias), files (ruta + contenido completo de cada archivo), openapi_yaml (contrato OpenAPI 3.0 de un endpoint POST que expone el caso de uso, con los campos del io_contract), assumptions.
