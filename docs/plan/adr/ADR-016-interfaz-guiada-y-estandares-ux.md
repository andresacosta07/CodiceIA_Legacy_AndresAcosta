# ADR-016: Interfaz guiada para personas no técnicas y estándares de UX verificados

**Estado:** Aceptado
**Fecha:** 2026-11-13

## Contexto
La rúbrica de Visión de Cliente y Negocio pondera con 33,33 % el criterio **«Interactivo y fácil de usar»** (navegación intuitiva, flujo guiado, vista legacy vs. moderno y un usuario externo que completa la tarea sin ayuda). Quien presenta y usa la demostración es una persona **funcional, no técnica**. Una primera revisión de la interfaz con Playwright mostró un flujo correcto pero poco autoexplicativo: había que saber qué pulsar, varias cifras eran jerga (equivalencia, trazabilidad, E2/E3, cobertura), las pantallas largas (reglas, casos, matriz) obligaban a desplazarse mucho y no había nada que indicara qué faltaba para avanzar. Además, una auditoría de contraste detectó incumplimientos del nivel AA (4,5:1): `--ok` sobre fondo ok (4,37), `--mute` sobre la línea (4,49) y texto blanco sobre los botones azules en modo oscuro (2,88).

## Decisión
1. **Guía propia, sin librerías** (`web/guide.js`, JavaScript puro): recorrido con foco sobre la pantalla real (oscurece, enmarca el elemento y explica en lenguaje simple; Anterior / Siguiente / Salir; teclas ←, →, Esc), con recorridos por pantalla (9 pasos en la portada, 3 en Ingesta, 5 en Descubrimiento, 7 en Reglas, 3 en Código, 3 en Equivalencia, 5 en Entrega), accesible desde un botón flotante «?» (abajo a la izquierda, en todas las pantallas). Invitación única de primera vez, recordada en `localStorage` (con degradación si no hay almacenamiento).
2. **Glosario «ⓘ»**: 20 términos técnicos explicados en lenguaje simple, adjuntos automáticamente a las cifras por coincidencia de etiqueta.
3. **Navegación por pasos explícita**: menú de pasos numerados (✔ si están hechos, atenuados y con aviso si aún están bloqueados) y barra inferior fija «← Paso anterior / Siguiente: <paso> →» con el aviso «🔒 qué falta para continuar»; «Empezar de nuevo» en el último paso.
4. **Portada con ejemplo opcional**: tres pasos explicados y «▶ Probar con un ejemplo (opcional)».
5. **Paso 3 compacto**: lista de una línea por regla con ✔/✖ rápidos, filtros, barra de progreso y avance automático a la siguiente pendiente; tablas largas en cuadros con desplazamiento.
6. **Estándares verificados por prueba**, no por inspección: `tests/test_ui_standards.py` (6 pruebas) comprueba contraste WCAG AA (texto y botones ≥ 4,5:1 en claro y oscuro), favicon y metadatos, accesibilidad básica (enlace «Saltar al contenido», `:focus-visible`, `aria-live`, `aria-current`, `prefers-reduced-motion`, `prefers-color-scheme`, adaptación a móvil, base de 16 px, objetivos táctiles ≥ 42 px), existencia de la guía y ausencia de sumideros XSS (`innerHTML`, `eval`…). Se corrigieron los tokens (`--ok`, `--mute`) y se introdujeron `--btn`, `--okbtn`, `--badbtn` para los botones.
7. **Marca**: favicon SVG propio (`web/favicon.svg`) y `theme-color`.

## Consecuencias
- (+) Una persona no técnica puede completar el flujo sin asistencia y explicarlo: cada pantalla dice qué ve, qué hacer y qué significa cada cifra.
- (+) Cero dependencias nuevas, funciona sin internet y bajo la CSP estricta (`script-src 'self'`); sin `innerHTML`.
- (+) El cumplimiento de contraste queda protegido contra regresiones por pruebas automáticas.
- (−) Mantenimiento propio: si cambian los textos de la interfaz, los selectores del recorrido (basados en texto de botones y títulos de tarjetas) deben actualizarse; los pasos cuyo elemento no existe se omiten sin fallar.
- (−) La guía no sustituye la prueba con un usuario externo real: el criterio manual `AC-F6-MANUAL-01` sigue pendiente de evidencia firmada.
- (−) No se mide la usabilidad (solo estándares y presencia de elementos); no hay pruebas de lector de pantalla ni de todos los navegadores.

## Alternativas descartadas
- **Librería de tours (Shepherd, Intro.js, Driver.js):** añade una dependencia externa (o una copia local) y estilos propios que había que adaptar a modo claro/oscuro y a la CSP; para siete recorridos cortos, el motor propio de unas 100 líneas es suficiente y más fácil de auditar.
- **Video tutorial:** no se mantiene sincronizado con la interfaz, no sirve sin reproducir y no guía sobre la pantalla viva; se mantiene solo como respaldo opcional de la demostración (capturas/video de una corrida completa).
- **Solo manual escrito:** necesario (ver `docs/MANUAL_FUNCIONAL_NO_TECNICO.md` y `docs/GUIA_ENTRENAMIENTO_DEMO.md`), pero no suficiente para el criterio «fácil de usar»: la ayuda debe estar en la propia pantalla.
