[Ttulo1] Copiloto de Modernización y Descubrimiento de Código Legacy
[] Propuesta para acelerar la extracción de reglas de negocio y la migración hacia arquitecturas modernas mediante IA
[Ttulo2] Resumen ejecutivo
[] En sectores altamente regulados como la banca y los seguros, los sistemas centrales (core business) continúan operando sobre bases de código heredadas (legacy) escritas en lenguajes como Cobol, PL/SQL, RPG o versiones desactualizadas de Java. Estos componentes albergan décadas de lógica de negocio crítica, pero carecen de documentación actualizada y de especialistas disponibles en el mercado. Modernizar o documentar estas aplicaciones demanda meses de análisis manual y expone a las organizaciones a riesgos operativos severos.
[] La propuesta para este reto consiste en desarrollar un Copiloto de Modernización y Descubrimiento de Código Legacy: una solución impulsada por Inteligencia Artificial que actúe como un traductor y arquitecto de software inteligente. El sistema ingiere fragmentos o rutinas complejas de código antiguo, descubre y formaliza las reglas de negocio subyacentes, traduce la lógica a un stack tecnológico moderno (como Java Spring Boot o Node.js/TypeScript), aplica guardrails de arquitectura limpia y genera automáticamente la documentación técnica junto con su correspondiente suite de pruebas unitarias.
[Ttulo2] 1. Problemática: el laberinto de los sistemas legacy en banca y seguros
[Ttulo3] 1.1 Contexto
[] Durante décadas, las entidades financieras y aseguradoras construyeron sus ventajas competitivas sobre motores transaccionales robustos. Con el paso del tiempo, estos sistemas se han convertido en estructuras monolíticas monolenguaje que soportan cálculos esenciales: amortización de créditos, tasación de pólizas, validaciones antifraude y liquidación de siniestros.
[] A pesar de su estabilidad, estos activos presentan una barrera estructural frente a las demandas de agilidad digital, integración vía APIs y adopción de la nube. La falta de documentación funcional confiable y la gradual jubilación de los expertos originales convierten cualquier iniciativa de cambio en un proyecto de alta incertidumbre y prolongada duración.
[Ttulo3] 1.2 Principales impactos
[] Efecto "Caja Negra" y pérdida de conocimiento: Las especificaciones funcionales originales ya no reflejan la realidad del código debido a años de parches y ajustes directos. La lógica reside únicamente en las líneas de código heredado.
[] Tiempos y costos excesivos de modernización: Un análisis manual preliminar para entender una sola rutina transaccional puede demorar semanas por parte de ingenieros senior, retrasando lanzamientos al mercado (Time-to-Market).
[] Escasez crítica de talento: La brecha generacional hace que encontrar ingenieros capacitados para mantener o descifrar lenguajes como Cobol o RPG sea cada vez más costoso y escaso.
[] Alto riesgo de regresión: Traducir manualmente rutinas complejas de miles de líneas incrementa la probabilidad de omitir reglas tácitas o casos de borde (edge cases), provocando inconsistencias financieras en producción.
[] Deuda técnica acumulada: La imposibilidad de desacoplar la lógica de negocio impide la transición hacia arquitecturas modernas de microservicios o soluciones orientadas a eventos en la nube.
[Ttulo2] 2. Solución esperada: Copiloto de Modernización y Descubrimiento de Código Legacy
[] Los equipos participantes deberán diseñar e implementar un prototipo funcional con calidad de demostración para cliente, que resuelva de forma tangible los impactos descritos en la problemática: convertir la "caja negra" del código legacy en conocimiento explícito, reducir semanas de análisis manual a minutos y entregar código moderno cuya equivalencia funcional esté demostrada mediante pruebas automatizadas. Se utilizarán tecnologías de Inteligencia Artificial generativa y agentes de software, sin restricciones de stack: se admiten soluciones con código personalizado (Python, LangChain, LlamaIndex, Semantic Kernel, Model Context Protocol - MCP) o enfoques Low-Code / No-Code integrados con LLMs y orquestadores.
[Ttulo3] 2.1 Enfoque: del problema a la solución
[] Problema
[] Capacidad del copiloto
[] Resultado verificable
[] Efecto "caja negra" y pérdida de conocimiento
[] Descubrimiento y formalización de reglas de negocio con trazabilidad a las líneas de origen
[] Catálogo de reglas aprobado y matriz de trazabilidad
[] Tiempos y costos excesivos de modernización
[] Análisis y transformación asistidos por agentes de IA
[] Reducción medible del tiempo de análisis y migración por rutina
[] Escasez crítica de talento
[] Explicación del código legado en lenguaje natural para perfiles modernos
[] Documentación funcional comprensible para negocio y auditoría
[] Alto riesgo de regresión
[] Pruebas de caracterización y verificación de equivalencia funcional
[] Reporte de equivalencia legacy vs. moderno sin diferencias
[] Deuda técnica acumulada
[] Generación de código con Clean/Hexagonal Architecture y quality gates
[] Código desacoplado, listo para contenedores, sin hallazgos críticos
[Ttulo3] 2.2 Capacidades funcionales del copiloto
[] El copiloto actuará como el cerebro de modernización del desarrollador:
[Prrafodelista] Comprensión semántica: Interpretará la sintaxis y el contexto operacional del código fuente legado, incluyendo sus dependencias (copybooks, paquetes, tablas y archivos).
[Prrafodelista] Extracción y desacoplamiento: Separará la lógica de negocio pura de las instrucciones operativas dependientes de la plataforma (como lecturas de archivos secuenciales o comandos de terminal).
[Prrafodelista] Validación humana: Permitirá revisar, ajustar y aprobar las reglas descubiertas antes de generar el código, asegurando control y explicabilidad.
[Prrafodelista] Transformación gobernada: Producirá código fuente moderno siguiendo estándares de ingeniería de software empresarial, respaldado por pruebas automatizadas y especificaciones legibles tanto para humanos como para auditorías.
[Prrafodelista] Verificación de equivalencia funcional: Demostrará que el código moderno produce los mismos resultados que el legado para un conjunto representativo de casos, incluidos casos borde.
[Prrafodelista] Entrega empaquetada: Generará un paquete listo para ejecutar y presentar: código, pruebas, documentación, reportes de calidad e informe ejecutivo.
[Ttulo3] 2.3 Arquitectura de referencia de la solución
[] Se espera una arquitectura modular por capas, con responsabilidades claramente separadas y orquestación multiagente:
[Prrafodelista] Capa de experiencia: Portal web, extensión de IDE o bot conversacional con vista comparativa (código legado vs. moderno), revisión de reglas y tablero de calidad.
[Prrafodelista] Capa de orquestación multiagente: Agentes especializados (Analista, Extractor de reglas, Arquitecto, Desarrollador, QA/Tester y Documentador) coordinados por un orquestador con estado y puntos de aprobación humana.
[Prrafodelista] Capa de análisis estático: Parsers o herramientas que generan el árbol sintáctico (AST), el grafo de dependencias y métricas de complejidad, reduciendo la dependencia exclusiva del LLM.
[Prrafodelista] Capa de conocimiento (RAG): Base de conocimiento con estándares de codificación, patrones de arquitectura, glosario del dominio bancario/asegurador y mapeos de tipos legacy a tipos modernos.
[Prrafodelista] Capa de verificación: Entorno aislado (sandbox) para compilar, ejecutar pruebas, comparar resultados y aplicar análisis estático y de seguridad.
[Prrafodelista] Capa de gobierno y observabilidad: Enmascaramiento de datos sensibles, registro de prompts y decisiones, trazabilidad de versiones y métricas de uso, costo y tiempo por ejecución.
[Ttulo3] 2.4 Atributos de calidad de la solución
[Prrafodelista] Fidelidad funcional: Equivalencia comprobada de cálculos, redondeos y validaciones frente al código original.
[Prrafodelista] Confiabilidad: Resultados consistentes y reproducibles entre ejecuciones, con nivel de confianza explícito por regla extraída.
[Prrafodelista] Mantenibilidad: Código legible, modular y alineado con Clean Code y principios SOLID.
[Prrafodelista] Seguridad: Ausencia de secretos y datos reales en el flujo; análisis de vulnerabilidades sobre el código generado.
[Prrafodelista] Explicabilidad y auditabilidad: Cada regla y decisión de diseño enlazada a su origen y justificada.
[Prrafodelista] Usabilidad: Flujo guiado, transparente y comprensible tanto para desarrolladores como para usuarios de negocio.
[Ttulo3] 2.5 Entregable con calidad de demo para cliente
[] El prototipo debe poder presentarse ante un cliente del sector financiero o asegurador. Para ello, el entregable debe incluir:
[Prrafodelista] Caso de negocio realista: Un artefacto legacy representativo del dominio (ej. amortización francesa en Cobol o liquidación de siniestros en PL/SQL) con datos de prueba sintéticos.
[Prrafodelista] Guion de demostración: Recorrido de extremo a extremo en máximo 10 minutos, con narrativa orientada al valor de negocio.
[Prrafodelista] Ejecución en vivo: Carga del artefacto, aprobación de reglas, generación de código y ejecución de pruebas visibles en pantalla.
[Prrafodelista] Tablero de resultados: Reglas descubiertas, equivalencia funcional, cobertura de pruebas, hallazgos de calidad y tiempo total del proceso.
[Prrafodelista] Informe ejecutivo: Resumen de una página con beneficios, riesgos mitigados y ahorro estimado frente al análisis manual.
[Prrafodelista] Reproducibilidad: Solución ejecutable en un entorno contenerizado con un solo comando y un README claro, incluyendo un plan de contingencia (ejecución pregrabada) ante fallas de conectividad.
[Ttulo2] 3. Flujo funcional de extremo a extremo: del código legacy a la migración funcional verificada
[] El flujo se organiza en ocho fases secuenciales. Cada fase produce un artefacto trazable y solo avanza a la siguiente al superar su quality gate (criterio de salida), garantizando que la migración sea funcional, verificable y auditable.
[] Fase
[] Objetivo
[] Salida principal
[] Quality gate
[] 1. Ingesta y preparación
[] Recibir, sanitizar y normalizar el artefacto
[] Artefacto normalizado e inventario de dependencias
[] 0 secretos o datos sensibles; lenguaje identificado
[] 2. Análisis estático y descubrimiento
[] Comprender estructura, flujo y complejidad
[] AST, grafo de dependencias y mapa de riesgo
[] 100% de rutinas y dependencias inventariadas
[] 3. Extracción de reglas de negocio
[] Formalizar la lógica de negocio
[] Catálogo de reglas y tablas de decisión
[] Cada regla con referencia a líneas de origen y nivel de confianza
[] 4. Validación humana (HITL)
[] Aprobar la interpretación del modelo
[] Especificación aprobada y versionada
[] Aprobación explícita del ingeniero
[] 5. Diseño de arquitectura destino
[] Definir la estructura moderna
[] Modelo de dominio, contratos API y ADRs
[] Alineación con Clean/Hexagonal Architecture
[] 6. Transformación y generación de código
[] Producir código moderno
[] Código fuente compilable
[] Compilación exitosa; 0 hallazgos críticos
[] 7. Verificación funcional y calidad
[] Demostrar equivalencia y calidad
[] Suite de pruebas, reporte de equivalencia y de calidad
[] 100% de casos de equivalencia aprobados; umbrales de calidad cumplidos
[] 8. Empaquetado y entrega
[] Entregar un paquete listo para demo
[] Repositorio, documentación, contenedor e informe ejecutivo
[] Ejecución reproducible con un solo comando
[Ttulo3] 3.1 Fase 1 – Ingesta y preparación del artefacto legacy
[] El flujo comienza cuando el desarrollador o arquitecto carga o introduce un artefacto de código antiguo a través de una interfaz interactiva (portal web, extensión de IDE, bot conversacional o endpoint).
[Prrafodelista] Tipos de entrada admitidos: Scripts en Cobol (rutinas de la Procedure Division), procedimientos almacenados y paquetes en PL/SQL, programas RPG o clases en Java legado (versiones pre-generics o monolitos EJB).
[Prrafodelista] Parámetros contextuales opcionales: Selección del stack moderno de destino (ej. Java 21 con Spring Boot 3, TypeScript/Node.js, C# .NET Core), nombre del dominio funcional (ej. "Tarificación de Seguros de Vida") y estilo de arquitectura preferido.
[Prrafodelista] Sanitización y seguridad: Detección y enmascaramiento automático de secretos, credenciales, cadenas de conexión y datos personales antes de cualquier envío a los modelos fundacionales.
[Prrafodelista] Normalización: Identificación del lenguaje y dialecto, resolución de copybooks, includes y paquetes dependientes, y verificación de codificación (EBCDIC/ASCII) y completitud del artefacto.
[Ttulo3] 3.2 Fase 2 – Análisis estático y descubrimiento
[Prrafodelista] Representación estructural: Generación del árbol sintáctico (AST) o representación intermedia del código para un análisis determinista.
[Prrafodelista] Grafo de dependencias y flujo de control: Identificación de rutinas invocadas, tablas, archivos VSAM, cursores y puntos de entrada y salida.
[Prrafodelista] Métricas de línea base: Líneas de código, complejidad ciclomática, código muerto o inalcanzable y duplicidades.
[Prrafodelista] Clasificación de la lógica: Distinción clara entre reglas de negocio (políticas de crédito, validaciones de edad, penalizaciones) y lógica de infraestructura legacy (manejo de punteros, comandos EXEC SQL, sentencias PERFORM, manejo de archivos VSAM).
[Prrafodelista] Mapa de riesgo de migración: Priorización de componentes según complejidad, criticidad de negocio y nivel de acoplamiento.
[Ttulo3] 3.3 Fase 3 – Descubrimiento y extracción de reglas de negocio
[] El motor de IA, apoyado en el análisis estático previo, procesa el código legado para formalizar la lógica de negocio:
[Prrafodelista] Identificación de lógica: Variables, condiciones lógicas, matrices de decisión, bucles y fórmulas financieras o actuariales (ej. escalonamiento de tasas de interés según score crediticio).
[Prrafodelista] Formalización: Expresión de cada regla en formato condición/acción, tablas de decisión y escenarios en lenguaje Gherkin (Dado/Cuando/Entonces).
[Prrafodelista] Trazabilidad: Referencia de cada regla a las líneas exactas del código origen.
[Prrafodelista] Nivel de confianza: Indicador por regla que señala ambigüedades, supuestos o reglas tácitas que requieren revisión humana.
[Ttulo3] 3.4 Fase 4 – Validación humana (Human-in-the-Loop)
[Prrafodelista] Revisión comparativa: Vista lado a lado del fragmento legado y la regla interpretada.
[Prrafodelista] Decisión sobre cada regla: Aprobar, ajustar o rechazar, con registro de comentarios y supuestos.
[Prrafodelista] Especificación como fuente de verdad: El catálogo aprobado se versiona y se convierte en la especificación que guía la generación de código y pruebas (Spec-Driven Development).
[Ttulo3] 3.5 Fase 5 – Diseño de la arquitectura destino
[Prrafodelista] Modelo de dominio: Definición de entidades, objetos de valor y servicios de dominio siguiendo Domain-Driven Design (DDD).
[Prrafodelista] Arquitectura hexagonal / limpia: Puertos y adaptadores para aislar la lógica de negocio de bases de datos, archivos, colas y servicios externos.
[Prrafodelista] Patrones de diseño: Aplicación de Strategy, Factory o Specification para reglas de negocio complejas.
[Prrafodelista] Contratos de integración: Definición de APIs (OpenAPI) que habiliten la coexistencia con el sistema legado mediante el patrón Strangler Fig.
[Prrafodelista] Registros de decisión de arquitectura (ADRs): Justificación documentada de cada decisión de diseño relevante.
[Ttulo3] 3.6 Fase 6 – Transformación y generación de código moderno
[Prrafodelista] Traducción y refactorización: Conversión de la lógica de procesamiento procedimental a un diseño moderno orientado a objetos o funcional.
[Prrafodelista] Flujo de control moderno: Reestructuración para eliminar prácticas obsoletas (como saltos incondicionales GO TO).
[Prrafodelista] Precisión numérica: Mapeo fiel de tipos legacy (ej. PIC y COMP-3) a tipos decimales exactos, conservando escalas y reglas de redondeo.
[Prrafodelista] Guardrails de arquitectura: Principios Clean Code, manejo canónico de excepciones, validación de tipos fuertes y desacoplamiento de dependencias externas para permitir despliegues en contenedores o funciones serverless.
[Prrafodelista] Ciclo de autocorrección: El agente compila, ejecuta análisis estático y corrige automáticamente los errores detectados antes de pasar a verificación.
[Ttulo3] 3.7 Fase 7 – Verificación funcional y aseguramiento de calidad
[Prrafodelista] Pruebas de caracterización (Golden Master): Definición de entradas representativas y resultados esperados del sistema legado (o de un oráculo de valores conocidos) como referencia de comportamiento.
[Prrafodelista] Pruebas diferenciales de equivalencia: Ejecución de los mismos casos sobre el código moderno y comparación automática de resultados, redondeos y mensajes de validación.
[Prrafodelista] Pruebas unitarias y de comportamiento: Casos con JUnit 5, Mockito, Jest o pytest que cubren flujos exitosos, caminos de error y condiciones de frontera, junto con escenarios BDD derivados del catálogo de reglas.
[Prrafodelista] Análisis estático y de seguridad: Revisión de calidad (ej. SonarQube), análisis SAST y verificación de dependencias vulnerables.
[Prrafodelista] Robustez de las pruebas (opcional): Pruebas de mutación (ej. PIT o Stryker) para comprobar que la suite detecta cambios en la lógica.
[] Criterios de calidad y umbrales sugeridos
[] Dimensión
[] Métrica
[] Umbral sugerido
[] Funcionalidad
[] Casos de equivalencia legacy vs. moderno aprobados
[] 100%
[] Precisión financiera
[] Diferencias en cálculos y redondeos
[] 0
[] Trazabilidad
[] Reglas con referencia al código origen
[] 100%
[] Cobertura de pruebas
[] Cobertura de líneas / ramas
[] ≥ 80% / ≥ 70%
[] Calidad de código
[] Hallazgos bloqueantes o críticos
[] 0
[] Mantenibilidad
[] Complejidad ciclomática por método
[] ≤ 10
[] Seguridad
[] Vulnerabilidades críticas y secretos expuestos
[] 0
[] Eficiencia
[] Tiempo de extremo a extremo por rutina
[] Minutos frente a semanas del proceso manual
[Ttulo3] 3.8 Fase 8 – Empaquetado y entrega del paquete de migración
[] El prototipo genera y presenta un conjunto estructurado y listo para descargar o inspeccionar, compuesto por:
[Prrafodelista] Código fuente moderno: Módulos, clases o microservicios funcionales en el lenguaje meta seleccionado, organizados en un repositorio con estructura estándar.
[Prrafodelista] e de pruebas unitarias automatizadas: Casos de prueba exhaustivos (usando frameworks como JUnit 5, Mockito, Jest o pytest) que cubren flujos exitosos, caminos de error y condiciones de frontera identificadas en el código original.Suit
[Prrafodelista] Documentación técnica y funcional: Especificación en lenguaje natural estructurado (Markdown) que incluye el catálogo de reglas de negocio descubiertas (condición/acción o tablas de decisión), el mapeo de correspondencia (traceability matrix) entre las líneas del código original y los métodos del código moderno, los supuestos asumidos durante la traducción, y los diagramas de arquitectura y registros de decisión (ADRs).
[Prrafodelista] Reportes de verificación: Reporte de equivalencia funcional, cobertura de pruebas y resultados del análisis de calidad y seguridad.
[Prrafodelista] Paquete ejecutable: Contenedor (Dockerfile o docker-compose) y README que permiten compilar, probar y ejecutar la solución con un solo comando.
[Prrafodelista] Informe ejecutivo: Resumen orientado a negocio con reglas descubiertas, riesgos mitigados, métricas de calidad y tiempo ahorrado frente al análisis manual.
[Ttulo3] 3.9 Metodologías y buenas prácticas aplicadas
[] Metodología / práctica
[] Aplicación en el flujo
[] Spec-Driven Development
[] El catálogo de reglas aprobado es la especificación que guía la generación de código y pruebas.
[] Characterization Testing / TDD
[] Las pruebas se definen a partir del comportamiento legado antes de aceptar el código moderno.
[] BDD (Gherkin)
[] Las reglas se expresan como escenarios comprensibles para negocio y ejecutables como pruebas.
[] Domain-Driven Design
[] El código destino se organiza alrededor del lenguaje y los conceptos del dominio financiero o asegurador.
[] Clean / Hexagonal Architecture
[] La lógica de negocio queda aislada de la infraestructura mediante puertos y adaptadores.
[] Strangler Fig
[] Migración incremental que permite la coexistencia controlada del sistema legado y el moderno.
[] DevSecOps y quality gates
[] Compilación, pruebas, análisis de calidad y seguridad automatizados en cada fase.
[] IA Responsable
[] Supervisión humana, explicabilidad, trazabilidad y protección de datos sensibles en todo el proceso.
[Ttulo2] 4. Reglas funcionales, de seguridad y arquitectura
[] Fidelidad matemática y de negocio: La lógica traducida debe mantener equivalencia estricta en el resultado de cálculos financieros, redondeos y validaciones con respecto al código fuente original.
[] Seguridad y privacidad del código: No incluir ni enviar secretos en duro, credenciales, datos de clientes reales o llaves de API durante la interacción con los modelos fundacionales.
[] Explicabilidad y trazabilidad: Toda decisión de diseño o regla interpretada debe estar respaldada por su referencia en el código origen para facilitar la auditoría técnica.
[] Generación de pruebas no triviales: Las pruebas unitarias generadas no deben ser meros esqueletos vacíos; deben incluir aserciones explícitas con datos de prueba realistas representativos del dominio bancario/asegurador.
[] Supervisión humana (Human-in-the-Loop): El prototipo debe permitir al ingeniero revisar las reglas extraídas antes de aprobar la generación final del código, posibilitando ajustes o correcciones a la interpretación del modelo.
[Ttulo2] 5. Resultado esperado del prototipo
[] El equipo debe presentar una demostración en vivo que evidencie la ejecución completa del flujo: desde la carga de un fragmento de código legacy realista (ej. cálculo de amortización francesa en Cobol o liquidación de siniestro en PL/SQL) hasta la obtención del paquete final refactorizado y verificado.
[] No es obligatorio conectarse a repositorios o pipelines corporativos reales; el foco está en la demostración verificable de la equivalencia funcional, la calidad de la arquitectura y del código resultante, la seguridad del proceso y la calidad de los entregables.
[Ttulo3] Criterios de éxito para la evaluación
[] La evaluación prioriza la evidencia verificable sobre la presentación. Cada criterio se califica a partir de lo demostrado en vivo y de lo incluido en el paquete entregado; el mayor peso corresponde a las pruebas de funcionalidad, porque demostrar que el código moderno se comporta igual que el legado es la condición indispensable para una migración confiable.
[] Criterio
[] Peso
[] Qué se evalúa
[] Evidencia mínima esperada
[] 1. Pruebas de funcionalidad y equivalencia
[] 25%
[] Equivalencia funcional entre el código legado y el moderno mediante pruebas de caracterización (Golden Master) y diferenciales; pruebas unitarias y escenarios BDD con aserciones explícitas, datos realistas del dominio, casos borde y caminos de error; ejecución automatizada de la suite.
[] 100% de casos de equivalencia aprobados; 0 diferencias en cálculos y redondeos; cobertura ≥ 80% de líneas y ≥ 70% de ramas; suite ejecutada en vivo.
[] 2. Precisión en la extracción de reglas
[] 15%
[] Capacidad para aislar y describir con claridad las reglas de negocio reales ocultas en la sintaxis antigua, separándolas de la lógica de infraestructura, con nivel de confianza y supuestos explícitos.
[] Catálogo de reglas aprobado con validación humana; 100% de reglas trazadas a las líneas de origen.
[] 3. Arquitectura
[] 15%
[] Diseño modular y orquestación multiagente del copiloto; aplicación de Clean/Hexagonal Architecture y DDD en el código destino; desacoplamiento de la lógica de negocio frente a la infraestructura; contratos de integración y decisiones justificadas.
[] Diagrama de arquitectura, modelo de dominio, contratos OpenAPI y registros de decisión (ADRs).
[] 4. Calidad de código (Clean Code)
[] 15%
[] Legibilidad, nombres significativos, responsabilidad única, principios SOLID, eliminación de prácticas obsoletas, manejo canónico de excepciones, tipado fuerte y precisión numérica con tipos decimales exactos.
[] Compilación exitosa; reporte de análisis estático con 0 hallazgos bloqueantes o críticos; complejidad ciclomática ≤ 10 por método.
[] 5. Seguridad e IA Responsable
[] 10%
[] Enmascaramiento de secretos y datos sensibles antes del envío a los modelos; uso exclusivo de datos sintéticos; análisis SAST y de dependencias; registro y trazabilidad de prompts y decisiones.
[] Demostración del enmascaramiento; 0 vulnerabilidades críticas y 0 secretos expuestos.
[] 6. Calidad de entregables y documentación
[] 10%
[] Completitud, claridad y utilidad del paquete de migración para equipos técnicos, de negocio y de auditoría.
[] Repositorio estructurado, README, ejecución con un solo comando, matriz de trazabilidad, reportes de verificación e informe ejecutivo de una página.
[] 7. Experiencia de usuario y calidad de la demo
[] 10%
[] Simplicidad, fluidez y transparencia del flujo para el desarrollador; narrativa orientada al valor de negocio y preparación para presentarse ante un cliente.
[] Recorrido de extremo a extremo en máximo 10 minutos con tablero de resultados y plan de contingencia.
[] Criterios de Visión de Cliente y Negocio
[] 8. Funcional
[] 33,33%
[] Que la solución resuelva el problema planteado y permita completar las tareas principales de principio a fin: carga del artefacto legacy, extracción y aprobación de reglas, generación de código moderno y ejecución de pruebas. Se valida la exactitud de los resultados con casos representativos y el manejo de errores sin comprometer la información del usuario.
[] Flujo completo ejecutado en vivo sin intervención manual fuera del prototipo; resultados correctos en al menos un caso representativo y un caso borde; manejo controlado de al menos una entrada inválida o error, sin pérdida ni exposición de datos.
[] 9. Interactivo y fácil de usar
[] 33,33%
[] Claridad y fluidez de la interacción: navegación intuitiva, instrucciones comprensibles y respuestas oportunas a las acciones del usuario. Se valida que usuarios representativos (desarrolladores y perfiles de negocio) completen las tareas sin ayuda y reciban orientación para corregir errores.
[] Interfaz con flujo guiado y vista comparativa legacy vs. moderno; indicadores de progreso o estado por fase; mensajes de error con acción sugerida; al menos un usuario no involucrado en el desarrollo completa la tarea principal sin asistencia.
[] 10. Innovador
[] 33,33%
[] Mejora diferenciada frente a la forma actual de resolver el problema (análisis y migración manual del código legacy). Se valida cómo el enfoque novedoso aporta utilidad real para clientes o negocio y si su ventaja está sustentada con una comparación o prueba.
[] Comparación cuantificada frente al proceso actual (tiempo, esfuerzo o calidad); identificación explícita del elemento diferenciador de la solución; caso de uso de negocio que evidencie el beneficio para el cliente.
[] Condiciones habilitantes
[Prrafodelista] El flujo completo, desde la carga del artefacto legacy hasta la entrega del paquete, debe ejecutarse en la demostración.
[Prrafodelista] Si las pruebas de funcionalidad no se ejecutan exitosamente o no se demuestra la equivalencia funcional, la calificación máxima en los criterios 3 a 7 será de 3 sobre 5.
[Prrafodelista] El uso de datos reales de clientes, secretos o credenciales en el flujo implica la descalificación del equipo.
[] Escala de calificación: cada criterio se califica de 1 a 5 (1 = no evidenciado, 3 = cumple parcialmente con evidencia, 5 = cumple totalmente con evidencia verificable) y se pondera según su peso para obtener la nota final.
[Ttulo2] 6. Diagramas conceptuales de referencia
