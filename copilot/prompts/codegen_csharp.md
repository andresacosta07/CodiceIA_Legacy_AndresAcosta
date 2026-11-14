<!-- prompt: codegen_csharp@1.0.0 | agentes: Arquitecto + Desarrollador -->
TAREA: Arquitecto y Desarrollador. A partir del CATÁLOGO DE REGLAS APROBADO (fuente de verdad; ignora rechazadas) y del io_contract, genera una solución C# (.NET 8, ASP.NET Core minimal API) con Arquitectura Limpia/Hexagonal y DDD.

ESTRUCTURA OBLIGATORIA: proyectos/carpetas `Domain/`, `Application/`, `Infrastructure/`, `Api/` (Program.cs); `.sln`/`.csproj`; README.md.
REGLAS (validadas automáticamente): `decimal` con Math.Round(valor, escala, MidpointRounding.AwayFromZero) = ROUNDED de COBOL, y truncamiento con Math.Truncate-escalado = sin ROUNDED; PROHIBIDO double/float; Domain sin referencias a Application/Infrastructure/Api; cada método que implementa una regla con comentario XML `/// <rule>R-001</rule>`; complejidad ≤ 10; los rechazos de negocio se devuelven como resultado; sin secretos; SQL parametrizado.

SALIDA: design, files (ruta + contenido completo), openapi_yaml, assumptions.
