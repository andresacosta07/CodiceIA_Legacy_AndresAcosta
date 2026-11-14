# Aprenda a usar la aplicación en 30 minutos

**Para quién es:** una persona **no técnica** que va a presentar la demostración del Copiloto de Modernización. No necesita saber programar. Esta guía le enseña, haciendo, a manejar la pantalla, a explicar lo que ve y a salir bien parada si algo falla.

**Cómo usarla:** tenga la aplicación abierta en el navegador (doble clic en `iniciar.bat`, o `py run.py`, y se abre sola en http://127.0.0.1:8000) y vaya haciendo cada ejercicio. Cada ejercicio indica el tiempo aproximado. Todo el recorrido usa un programa de ejemplo con **datos ficticios**.

| Bloque | Tiempo |
|---|---|
| A. Mapa de la pantalla | 3 min |
| B. Ejercicio 1: la demo completa, clic a clic | 10 min |
| C. Ejercicio 2: atajos, guía y ayudas «ⓘ» | 5 min |
| D. Ejercicio 3: provocar y explicar errores | 5 min |
| E–I. Guion, preguntas, errores, checklists y autoevaluación | 7 min de lectura |

---

## A. Mapa de la pantalla (qué es cada zona)

Imagine la pantalla dividida en cinco zonas, de arriba abajo:

1. **Cabecera azul.** Aquí están, de izquierda a derecha: el nombre de la aplicación y su logotipo; el selector **«Motor»** (quién hace el trabajo); una etiqueta de color que repite el motor activo («Sin IA», «Claude» o «Pregrabado»); la lista de **proyectos** ya creados; el botón **«+ Nuevo proyecto»** (vuelve a la portada) y el botón **««?» (botón flotante)»** (inicia el recorrido guiado de la pantalla en la que esté).
2. **Menú de pasos numerados.** Seis casillas: **1 Ingesta · 2 Descubrimiento · 3 Reglas · 4 Código · 5 Equivalencia · 6 Entrega**. Cada una muestra su número; cuando el paso está terminado aparece una ✔. Los pasos que todavía no se pueden abrir se ven atenuados: la aplicación le avisa «Primero complete el paso anterior».
3. **Tarjeta amarilla «🧭 Paso N».** Es su **asistente**. Dice qué está viendo, por qué importa y **«Qué hacer ahora»**. Tiene el botón **«▶ Recorrido de esta pantalla»**, que enmarca cada zona de la pantalla y se la explica.
4. **Contenido del paso.** Cifras en cuadros (con una **ⓘ** junto a las técnicas), tablas, el código antiguo y el nuevo.
5. **Barra inferior fija.** A la izquierda **«← Paso anterior: …»**; a la derecha **«Siguiente: … →»**. Si todavía no puede avanzar, en lugar del botón verá un aviso **«🔒 …»** que dice qué falta (por ejemplo, «Decida todas las reglas y pulse "Aprobar catálogo y generar código →"»). En el último paso aparece **«Empezar de nuevo»**.

**Regla de oro:** si no sabe qué hacer, lea la tarjeta amarilla o la barra inferior. Siempre dicen el siguiente paso.

**Colores:** verde = bien / aprobado; ámbar = atención o pendiente; rojo = problema o rechazado; azul = acción principal; gris = información.

---

## B. Ejercicio 1: la demo completa, clic a clic (10 min)

> Objetivo: llegar al paso 6 y entender qué muestra cada pantalla. Haga el ejercicio con el motor **«⚙ Motor local determinista (sin IA)»** (es el predeterminado sin clave: tarda segundos y no necesita internet).

### Pantalla de inicio
- **Verá:** el título «Del código legacy a software moderno, verificado», tres tarjetas numeradas (1 Cargue un programa antiguo · 2 Usted aprueba las reglas · 3 Vea la prueba), un botón pequeño y opcional **«▶ Probar con un ejemplo (opcional)»** (la guía está en el botón flotante **?** de la esquina inferior izquierda). Si es la primera vez, arriba aparece la tarjeta **«👋 ¿Primera vez aquí?»**.
- **Haga:** pulse **«▶ Empezar recorrido»** (1 minuto) para ver el recorrido de la portada. Con **«Siguiente →»** avanza, con **«← Anterior»** retrocede, con **«Salir de la guía»** (o la tecla Esc) cierra. También sirven las flechas ← y →.
- **Por qué importa:** demuestra que cualquier persona puede aprender la herramienta sin manual.
- Ahora pulse **«▶ Probar con un ejemplo (opcional)»**. Carga un programa COBOL de ejemplo (cálculo de cuotas de préstamo) y **los casos de prueba aportados** (evidencia E2).

### Paso 1 · Ingesta («Carga y datos tapados»)
- **Verá:** 2 archivos y 156 líneas, lenguaje «cobol», 1 secreto enmascarado y **0 residuos**, y el «Informe de enmascarado» con una contraseña convertida en `<SECRET_001>`.
- **Qué significa:** antes de que nada se analice, la aplicación **tapó** una contraseña ficticia incrustada en el programa. La etiqueta verde «Compuerta superada» indica que no quedó ningún secreto.
- **Haga:** pulse **«Analizar y extraer reglas →»**. La barra inferior mostrará «🔒 Pulse "Analizar y extraer reglas →" para continuar» hasta que termine.
- **Por qué importa:** responde la primera preocupación de cualquier cliente: «¿qué pasa con mis datos?».

### Paso 2 · Descubrimiento («Mapa del programa»)
- **Verá:** cuadros con líneas de código, número de partes, complejidad, **código muerto**; la tabla «Unidades de análisis» con etiquetas verdes («business») y grises («infrastructure»); el «Grafo de dependencias» (quién llama a quién); mapa de riesgos; y el «Contrato de entrada/salida».
- **Qué significa:** es el **mapa** del programa. Verde = decisiones y cálculos que se migran como reglas. Gris = lo técnico de la plataforma antigua (leer archivos, guardar en base de datos). «Código muerto» es una parte que nunca se ejecuta y no se migra.
- **Haga:** pulse **«Siguiente: Reglas →»** (o espere: la aplicación avanza sola al paso 3 cuando termina de extraer las reglas).
- **Por qué importa:** convierte la «caja negra» en algo visible y ordenado.

### Paso 3 · Reglas («Usted decide»)
- **Verá:** arriba, una **barra de progreso** («0 de 11 reglas decididas») con contadores (pendientes, aprobadas, rechazadas, trazabilidad 100 %) y dos botones: **«Aprobar todas las verificadas»** y **«Aprobar catálogo y generar código →»** (apagado todavía). Debajo: a la izquierda el **código antiguo** con líneas resaltadas; a la derecha, pestañas **Todas · Pendientes · Aprobadas · Rechazadas** y una lista con **una línea por regla**.
- **Qué significa:** cada línea es una **regla de negocio** que estaba escondida en el código (por ejemplo, «Monto entre 1,000.00 y 500,000.00»). Las líneas resaltadas a la izquierda son **las que la respaldan**: así se comprueba que no es inventada. Los chips de cada fila dicen la categoría, la confianza (%) y «✓ cita» (la cita fue verificada).
- **Haga:** 
  1. Haga clic en la primera regla: se abre su detalle (descripción, condiciones, acciones, origen).
  2. Pulse **«Aprobar y seguir»**: la regla queda aprobada y la lista pasa sola a la siguiente pendiente.
  3. En otra regla pulse **«Ajustar»**, cambie una palabra de la descripción y pulse **«Guardar y aprobar»**.
  4. En otra, pulse **«Rechazar y seguir»** (por ejemplo, para mostrar que usted manda).
  5. Para el resto, pulse **«Aprobar todas las verificadas»**.
  6. Cuando la barra diga «11 de 11 reglas decididas», pulse **«Aprobar catálogo y generar código →»**.
- **Por qué importa:** aquí está el **control humano**: nada pasa al código nuevo sin la aprobación de una persona, y queda registrado quién aprobó.

### Paso 4 · Código («Código por capas»)
- **Verá:** número de archivos generados, capas (application / domain / infrastructure), 0 hallazgos críticos; el «Diseño de arquitectura»; la «Vista comparativa legacy ↔ moderno».
- **Haga:** elija una regla en la lista desplegable: a la izquierda verá su línea en el programa antiguo y a la derecha el archivo nuevo que la implementa, con la etiqueta `@rule` resaltada.
- **Por qué importa:** muestra la **trazabilidad**: de una línea antigua a un archivo nuevo, sin saltos.

### Paso 5 · Equivalencia («Prueba de que funciona igual»)
- **Verá:** Equivalencia **100 %**, casos probados (por ejemplo 65/65 o 67/67), **0 diferencias en cálculos**, cobertura de pruebas, 0 hallazgos críticos, y la tabla de casos con las etiquetas **E2** y **E3**.
- **Qué significa:** se probaron decenas de casos, incluidos los límites, en el sistema nuevo y se compararon con los resultados de referencia. **E2** = casos de referencia aportados por una persona. **E3** = resultados calculados por un segundo traductor del código antiguo. **No se ejecutó el programa COBOL original**: la pantalla lo declara.
- **Por qué importa:** es la prueba central de la demostración: «da exactamente lo mismo».

### Paso 6 · Entrega («Descarga e informe»)
- **Verá:** el tablero final, el **resumen ejecutivo**, el botón **«⬇ Descargar paquete de migración (.zip)»**, la **comparación contra el proceso manual**, la **calculadora «de una rutina a toda la cartera»**, el panel **«¿Qué nos diferencia?»**, la matriz de trazabilidad y el registro de auditoría.
- **Haga:** pulse el botón de descarga; cambie el número de rutinas de 50 a 200 en la calculadora y observe cómo cambia el ahorro estimado.
- **Por qué importa:** cierra con **valor de negocio**. Recuerde decir que el ahorro es una **estimación con supuestos visibles**, no una medición.

---

## C. Ejercicio 2: atajos, guía y ayudas «ⓘ» (5 min)

1. **Guía en cualquier pantalla.** Pulse **««?» (botón flotante)»** (cabecera) o **«▶ Recorrido de esta pantalla»** (tarjeta amarilla). Hay recorridos de 6 pasos en la portada, 3 en Ingesta, 4 en Descubrimiento, 7 en Reglas, 3 en Código, 3 en Equivalencia y 5 en Entrega. Cierre con **Esc**.
2. **Ayudas «ⓘ».** Junto a las cifras técnicas hay una **ⓘ**. Púlsela: aparece un globo con la explicación en lenguaje simple (hay 20 términos: motor de IA, enmascarado, regla, trazabilidad, confianza, equivalencia, diferencias, cobertura, hallazgos, complejidad, nivel de evidencia, escenario Gherkin, ahorro, auditoría, tokens, líneas de código, código muerto «negocio vs. infraestructura», rigor e inventario). Pulse **«Entendido»** o Esc para cerrar.
3. **Atajos de la lista de reglas.** En cada fila, ✔ aprueba y ✖ rechaza sin abrir el detalle. Las pestañas **Pendientes / Aprobadas / Rechazadas** filtran. «Aprobar catálogo…» está apagado hasta decidir todas: pase el cursor y verá «Decida primero todas las reglas pendientes».
4. **Navegación.** Use la barra inferior **«Siguiente: … →»** o el menú numerado. Un paso atenuado se abrirá cuando complete el anterior.
5. **Proyectos anteriores.** La lista «Proyectos…» de la cabecera reabre cualquier corrida previa (útil como respaldo en la demo).

---

## D. Ejercicio 3: provocar y explicar errores (5 min)

Hacer esto **a propósito** es una de las mejores partes de la demo: muestra que la aplicación se protege.

1. **Entradas inválidas.** En la portada, baje a «Cargar su código» y abra **«Demostrar el manejo de entradas inválidas»**. Pulse **«Archivo .exe»**, **«Archivo binario»** y **«Código vacío»**. Cada botón recibe un aviso claro («Tipo de archivo no admitido: .exe…», «El archivo parece binario…», «No se recibió ningún archivo ni código…») y **no se guarda nada**. Diga: «ante una entrada incorrecta se rechaza con un mensaje y una acción sugerida, sin exponer datos».
2. **Rechazar una regla.** En el paso 3 rechace una regla y muestre que queda tachada y contada como «rechazada». Diga: «la persona manda; la herramienta propone».
3. **Cambiar el motor.** En «Motor» elija otro modo **solo antes de empezar un proyecto** y explique la diferencia: «Sin IA» (determinista, segundos), «Claude vía suscripción» (IA para cualquier lenguaje, unos 6 minutos) o «Contingencia (pregrabado)» (repite una corrida real).
4. **Qué NO tocar durante la demo:**
   - **No cambie de motor** con un proyecto a mitad: el motor es **global** (lo ven todos los navegadores abiertos).
   - No suba archivos reales ni datos de clientes: solo la muestra.
   - No use el modo «Claude vía suscripción» en vivo (tarda ~6 min) salvo que lo haya ensayado.
   - No cierre la terminal donde corre la aplicación.
   - No abra la misma aplicación en dos pantallas aprobando reglas a la vez.

---

## E. Guion adaptado a la interfaz

### Versión corta (5 minutos)

| Min | Qué hacer | Frase lista para decir |
|---|---|---|
| 0:00 | Portada | «Esta herramienta convierte un programa antiguo en reglas claras, código nuevo y una prueba de que funciona igual. Y el que decide es usted.» |
| 0:30 | **«▶ Probar con un ejemplo (opcional)»** | «Cargo un programa COBOL de ejemplo, con datos ficticios.» |
| 1:00 | Paso 1: señalar «<SECRET_001>» y «0 residuos» | «Antes de analizar, tapa los secretos.» Pulse **«Analizar y extraer reglas →»**. |
| 1:30 | Paso 3: clic en una regla y **«Aprobar y seguir»**; luego **«Aprobar todas las verificadas»** | «Cada regla muestra la línea original que la respalda. Aquí decide la persona.» |
| 2:30 | **«Aprobar catálogo y generar código →»**, luego «Siguiente: Equivalencia →» | «Se genera código moderno por capas.» |
| 3:00 | Paso 5: 100 %, 0 diferencias | «Se probaron decenas de casos, incluidos los límites: da exactamente lo mismo.» |
| 4:00 | Paso 6: calculadora (50 → 200) | «Horas contra segundos; los supuestos están a la vista.» |
| 4:45 | Cierre | «De semanas a minutos, con control humano y evidencia.» |

### Versión larga (10 minutos)

| Min | Pantalla | Qué hacer | Frase lista para decir |
|---|---|---|---|
| 0:00–1:00 | Portada | Mostrar «Motor» y los 3 pasos | «Caja negra, semanas de análisis, riesgo de regresión. Esto lo hace visible y verificable. Hoy usamos el motor “Sin IA”: determinista y en segundos.» |
| 1:00–2:00 | Portada | «Demostrar el manejo de entradas inválidas» | «Primero, qué pasa cuando algo sale mal: se rechaza con un mensaje claro y no se guarda nada.» |
| 2:00–3:00 | Ingesta | **«▶ Probar con un ejemplo»**; señalar el enmascarado | «Los secretos se tapan antes de cualquier análisis; si quedara uno, se bloquea el envío.» |
| 3:00–4:00 | Descubrimiento | Mapa, código muerto, negocio vs. infraestructura | «Un análisis automático separa lo que es negocio de lo que es técnica.» |
| 4:00–5:45 | Reglas | Clic en regla, ✔, «Ajustar», «Rechazar y seguir», «Aprobar catálogo…» | «Cada regla cita líneas reales; una regla sin respaldo no se puede aprobar. Nada pasa al código sin esta aprobación.» |
| 5:45–6:45 | Código | Vista comparativa | «Arquitectura por capas; cada archivo nuevo lleva la etiqueta de la regla que implementa.» |
| 6:45–8:15 | Equivalencia | Tiles, tabla E2/E3, un caso límite (plazo de 361 meses) | «Tolerancia cero. E2 son casos aportados; E3 son resultados de un segundo traductor. No se ejecutó el programa original y la pantalla lo dice.» |
| 8:15–9:30 | Entrega | Tablero, «¿Qué nos diferencia?», calculadora, descarga | «Estimación de ahorro con supuestos visibles; el paquete incluye código, pruebas, documentos e informe.» |
| 9:30–10:00 | — | Cierre | «Control humano, evidencia verificable y seguridad desde el diseño.» |

---

## F. Quince preguntas difíciles del jurado (con respuestas honestas)

1. **¿Esto es inteligencia artificial?** Depende del motor. «Sin IA» es un programa determinista (analiza el código y aplica reglas fijas). «Claude vía suscripción» usa IA de Claude. La etiqueta de la cabecera dice siempre cuál está activo.
2. **¿Ejecutaron el programa COBOL original?** No. No hay un ejecutor de COBOL en esta máquina. La equivalencia se demuestra con casos aportados (E2) y con un segundo traductor (E3), y la pantalla lo declara.
3. **¿Entonces cómo saben que da lo mismo?** Se comparan, con tolerancia cero, los resultados del sistema nuevo contra casos de referencia (algunos escritos a mano y otros calculados), incluidos los límites. Es evidencia fuerte, pero no es ejecutar el original.
4. **¿Qué pasa si la IA inventa una regla?** Cada regla debe citar líneas reales y un verificador automático lo comprueba; una regla sin respaldo se marca y no se puede aprobar.
5. **¿Funciona con cualquier lenguaje?** El motor «Sin IA» solo con COBOL de formato fijo dentro de un subconjunto. Con Claude está pensado para cualquier lenguaje, pero **solo lo probamos con COBOL**.
6. **¿Y Java o C#?** Solo con IA (Claude), y se generan con validación estática, **sin compilar** aquí. «Sin IA» solo genera TypeScript.
7. **¿Mis datos salen de mi equipo?** Con «Sin IA», no. Con «Claude vía suscripción», el código **ya enmascarado** viaja a Anthropic por su sesión de Claude Code. Revise la política de su organización.
8. **¿Y si hay datos personales?** Se tapan antes de cualquier análisis, pero la demo usa **solo datos ficticios**. No lo probamos con datos reales.
9. **¿Cuánto tarda?** Con «Sin IA», segundos. Con Claude, unos 6 minutos por programa. Por eso la demo principal usa «Sin IA» o el modo pregrabado.
10. **¿Los resultados de la IA son siempre iguales?** No: una IA puede variar. Por eso cada resultado pasa por verificaciones automáticas, no por confianza.
11. **¿El ahorro es real?** Es una **estimación** con supuestos visibles (horas por línea de código, costo por hora, minutos de revisión). No es una medición.
12. **¿Escala a un banco entero?** Hoy es un prototipo de un solo equipo (base SQLite, sin inicio de sesión, límite de tamaño por programa). El manual técnico tiene una hoja de ruta a producción.
13. **¿Quién aprueba y queda registrado?** La persona que usa la aplicación; queda en un registro de auditoría encadenado. Hoy no hay control de roles ni inicio de sesión.
14. **¿Qué no hace todavía?** Conexión a repositorios Git, compilar Java/C#, ejecutar el COBOL original, otros lenguajes con garantías, autenticación y despliegue en la nube.
15. **¿Probaron todo?** Hay 121 pruebas automáticas y 49 criterios de aceptación en verde. Pero no se probó el modo con clave de API, ni el modelo local opcional contra un servidor real, ni la usabilidad con una persona externa.

---

## G. Errores comunes y cómo recuperarse

| Qué pasa | Qué hacer |
|---|---|
| La página no carga | Compruebe que la terminal sigue abierta; ejecute `iniciar.bat` otra vez. Si el puerto 8000 está ocupado, la aplicación usa el siguiente y lo escribe en la terminal. |
| El selector de motor muestra «no disponible» | Esa opción no está instalada o no hay sesión/clave. Use «Sin IA» o «Pregrabado». |
| Franja roja con un error y botón «Reintentar» | Lea el mensaje (dice la acción sugerida) y pulse **«Reintentar»**. Si persiste, cambie a «Sin IA». |
| «Primero complete el paso anterior» | Está intentando abrir un paso bloqueado. Mire la barra inferior: dice qué falta. |
| «Aprobar catálogo…» está apagado | Aún quedan reglas pendientes. Use la pestaña «Pendientes» o «Aprobar todas las verificadas». |
| Una regla no se puede aprobar | Está marcada «✖ sin respaldo»: no tiene cita verificada. Recházela. |
| El motor «Sin IA» rechaza el programa | Solo entiende COBOL de formato fijo. Use la muestra o cambie a Claude. |
| Claude tarda mucho o falla | Es normal (~6 min) o se agotó el límite del plan: cambie a «Sin IA» o «Pregrabado». |
| Se ve distinto en otro navegador abierto | El motor y los proyectos son compartidos. Cierre los otros navegadores durante la demo. |
| Se cerró la guía sin querer | Pulse **««?» (botón flotante)»** otra vez. |

---

## H. Checklists

### 15 minutos antes
- [ ] Doble clic en `iniciar.bat` (o `py run.py`); abra http://127.0.0.1:8000.
- [ ] Compruebe la etiqueta de la cabecera: «Sin IA» (o el motor que haya decidido).
- [ ] Haga una corrida completa con la muestra COBOL (paso 1 → 6) y deje el proyecto como respaldo en la lista «Proyectos…».
- [ ] Cierre todas las demás pestañas y programas con datos reales; zoom del navegador al 100 %, pantalla completa.
- [ ] Tenga a mano este documento, `docs/GUION_DEMO.md` y capturas de la corrida (plan C).
- [ ] Si usará IA de Claude: confirme que `claude` tiene la sesión iniciada **y** que acepta que el código enmascarado salga hacia Anthropic.

### 1 minuto antes
- [ ] Portada visible, sin proyecto abierto; motor correcto.
- [ ] La tarjeta «👋 ¿Primera vez aquí?» cerrada con «No, gracias» (o úsela como apertura).
- [ ] Notificaciones del equipo silenciadas.
- [ ] Respire: la tarjeta amarilla y la barra inferior le dicen siempre qué hacer.

---

## I. Autoevaluación (10 preguntas)

1. **¿Qué hace el botón «▶ Probar con un ejemplo (opcional)»?** Carga el programa COBOL de ejemplo con los casos de referencia (E2); todavía no lo analiza.
2. **¿Qué significa `<SECRET_001>`?** Que un secreto (por ejemplo, una contraseña) fue tapado antes de analizar.
3. **¿Cómo sabe qué le falta para avanzar?** Por la tarjeta amarilla («Qué hacer ahora») y el aviso «🔒» de la barra inferior.
4. **¿Para qué sirven las líneas resaltadas del paso 3?** Para comprobar que la regla está respaldada por el código antiguo.
5. **¿Qué diferencia hay entre ✔ y «Aprobar todas las verificadas»?** ✔ aprueba una regla; el botón aprueba de una vez todas las pendientes con respaldo comprobado.
6. **¿Por qué «Aprobar catálogo y generar código →» puede estar apagado?** Porque quedan reglas pendientes por decidir.
7. **¿Qué quiere decir 100 % de equivalencia con 0 diferencias?** Que, en todos los casos probados, el sistema nuevo da exactamente los mismos resultados de referencia.
8. **¿Qué es E3 y qué NO es?** Resultados calculados por un segundo traductor del código antiguo; **no** es ejecutar el programa original.
9. **¿Qué NO debe hacer durante la demo con el «Motor»?** Cambiarlo a mitad de un proyecto (es global y afecta a todos).
10. **¿Es una medición el ahorro de la calculadora?** No, es una estimación con supuestos visibles.

> Si acierta 8 o más, está listo/a. Si no, repita el ejercicio 1 con la guía interactiva y vuelva a leer las preguntas del bloque F.

## Cabecera de la aplicación (actualizada)
- **Motor** (lista desplegable): «Sin IA (rápido, en este equipo)», «Con IA» y «Pregrabado (sin conexión)». Solo aparecen los motores disponibles; el de clave de API no se muestra si no está configurado.
- **📁 Proyectos:** abre un panel lateral con sus proyectos agrupados en *En curso o esperando su acción*, *En cola (sin iniciar)*, *Finalizados* y *Con error*. Desde ahí se abre o elimina un proyecto y está el botón **＋ Nuevo proyecto**, que vuelve a la pantalla de inicio para cargar otro programa. Pulsar el nombre «Copiloto de Modernización» también vuelve al inicio.
- **🌙 / ☀️:** cambia entre modo oscuro y claro (se recuerda en este navegador).
- **Botón flotante «?» (abajo a la izquierda):** abre la guía de la pantalla en que esté. Siempre disponible, sin ocupar espacio en la cabecera.