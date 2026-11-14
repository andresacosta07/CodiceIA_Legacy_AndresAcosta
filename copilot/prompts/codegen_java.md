<!-- prompt: codegen_java@1.0.0 | agentes: Arquitecto + Desarrollador -->
TAREA: Arquitecto y Desarrollador. A partir del CATÁLOGO DE REGLAS APROBADO (fuente de verdad; ignora rechazadas) y del io_contract, genera un proyecto Java 21 + Spring Boot 3 (Maven) con Arquitectura Limpia/Hexagonal y DDD.

ESTRUCTURA OBLIGATORIA (paquete base `com.example.<dominio>`):
- src/main/java/.../domain/...          modelo, value objects (records), servicios de dominio, specifications/strategies. Sin Spring ni JPA.
- src/main/java/.../application/...     casos de uso y puertos (port.in / port.out). Solo depende de domain.
- src/main/java/.../infrastructure/...  adaptadores (adapter.in.web con @RestController + DTOs, adapter.out.*) y configuración Spring.
- pom.xml (Java 21, spring-boot-starter-web, spring-boot-starter-validation, junit-jupiter, archunit-junit5), README.md.
- Una prueba ArchUnit (src/test/java/.../ArchitectureTest.java) que verifique: domain no depende de application/infrastructure, application no depende de infrastructure, controladores sin lógica de negocio.

REGLAS (validadas automáticamente): BigDecimal con MathContext/RoundingMode explícitos (RoundingMode.HALF_UP = ROUNDED de COBOL, DOWN = truncamiento); PROHIBIDO double/float; sin GO TO/flujo no estructurado; excepciones de dominio tipadas solo para errores técnicos (los rechazos de negocio se devuelven como resultado); cada método que implementa una regla con Javadoc `@rule R-001`; complejidad ≤ 10; sin secretos; SQL (si lo hubiera) siempre parametrizado; validación de entradas en el controlador (Bean Validation).

SALIDA: design, files (ruta + contenido completo), openapi_yaml (contrato OpenAPI 3.0), assumptions.
