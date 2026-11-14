# 03 — Guardrails y estándares

Aplica al **código generado** (stack destino) y, donde se indica, al código de la propia app.

## 1. Arquitectura limpia / hexagonal

Capas y regla de dependencias (siempre hacia adentro):

```
infrastructure ──► application ──► domain
(adapters: REST, JPA, files, queues)   (casos de uso, puertos)   (entidades, VO, servicios de dominio, specifications)
```

Reglas obligatorias:
1. `domain` no depende de ninguna otra capa ni de frameworks (sin Spring, JPA ni Jackson en el dominio).
2. `application` depende solo de `domain`; define **puertos** (interfaces) de entrada y salida.
3. `infrastructure` implementa puertos; los controladores solo adaptan HTTP ↔ caso de uso, sin lógica de negocio.
4. Los repositorios solo persisten; sin reglas de negocio.
5. Reglas de negocio expresadas con patrones Strategy / Specification / Factory cuando haya variantes o condiciones compuestas.
6. Sin dependencias cíclicas entre paquetes.
7. Importes y tasas: solo tipos decimales exactos (`BigDecimal` + `MathContext`/`RoundingMode` explícitos; `Decimal`/`decimal.js` en TS). Prohibido `float`/`double`.
8. Sin saltos incondicionales; flujo estructurado.
9. Excepciones de dominio tipadas; manejador global en infraestructura; sin `catch` vacíos ni `Exception` genérica.
10. Cada método de dominio que implementa una regla se anota/etiqueta con su ID de regla (`@BusinessRule("R-014")`) para la trazabilidad.

## 2. Estructura de paquetes del código generado

Java 21 + Spring Boot 3 (Maven):

```
com.<org>.<dominio>
 ├─ domain
 │   ├─ model            (entidades, value objects: Money, Rate, Term)
 │   ├─ service          (servicios de dominio)
 │   ├─ rule             (specifications / strategies por regla)
 │   └─ exception
 ├─ application
 │   ├─ port.in          (casos de uso)
 │   ├─ port.out         (repositorios, gateways)
 │   └─ usecase
 └─ infrastructure
     ├─ adapter.in.web   (controladores REST, DTOs)
     ├─ adapter.out.persistence
     └─ config
```

TypeScript (NestJS): `src/domain`, `src/application` (`ports`, `use-cases`), `src/infrastructure` (`http`, `persistence`, `config`), mismos criterios.
Artefactos extra: `docs/` (catálogo, matriz de trazabilidad, ADRs), `openapi.yaml`, `Dockerfile`, `README`.

## 3. Convenciones de código

- Nombres de negocio (idioma del dominio) y significativos; una responsabilidad por clase; métodos cortos; CC ≤ 10 por método.
- Inyección por constructor; inmutabilidad en value objects (`record` en Java).
- Validación de tipos fuertes en fronteras (Bean Validation / class-validator / zod).
- Sin secretos en código; configuración por variables de entorno.
- SQL solo parametrizado (JPA/Spring Data o `PreparedStatement`); prohibido concatenar entradas.
- Formateo automático: Spotless/google-java-format; Prettier + ESLint.

## 4. Validación automática

| Regla | Java | TypeScript |
|---|---|---|
| Dependencias entre capas, ausencia de ciclos | ArchUnit | dependency-cruiser / eslint-plugin-boundaries |
| Sin lógica en controladores/repositorios | ArchUnit (reglas por nombre/capas) + lint propio | eslint-plugin-boundaries + reglas propias |
| Estilo | Checkstyle + Spotless | ESLint + Prettier |
| Bugs y seguridad | SpotBugs + FindSecBugs | eslint-plugin-security + Semgrep |
| CC ≤ 10 | Checkstyle `CyclomaticComplexity` / PMD | eslint `complexity: 10` |
| Sin `double`/`float` monetario, sin `GO TO` | regla ArchUnit/Semgrep propia | regla Semgrep/eslint propia |
| Cobertura ≥ 80 % líneas / ≥ 70 % ramas | JaCoCo | Istanbul/c8 |
| Dependencias vulnerables | OWASP Dependency-Check | `npm audit` |
| Análisis global | SonarQube (opcional en CI) | ídem |

Estas comprobaciones corren en el sandbox (F4) y alimentan los criterios AC-F4-xx y AC-F5-xx.

## 5. Guardrails de la propia app (Python/TS)

ruff + mypy (estricto) + pytest-cov; eslint + tsc + Vitest; pre-commit con gitleaks; CC ≤ 10; `import-linter` para forzar que `packages/core` no dependa de `apps/*`; SQL solo vía SQLAlchemy con parámetros (regla Semgrep que prohíbe f-strings en `text()`/`execute`).
