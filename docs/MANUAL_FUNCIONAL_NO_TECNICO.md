# Manual funcional (para personas no técnicas)

**Para quién es:** personas de negocio, auditoría, riesgos, producto y dirección que van a ver o usar la demostración. No necesita saber programar.
**Otros manuales:** [Manual técnico](MANUAL_TECNICO.md) · [Manual combinado](MANUAL_DE_USUARIO.md) · [Guion de la demo](GUION_DEMO.md).

---

## 1. ¿Qué es y qué problema resuelve?

Muchos bancos y aseguradoras calculan cuotas, primas e indemnizaciones con programas escritos hace décadas (por ejemplo en COBOL). Funcionan, pero nadie recuerda con certeza **qué reglas** aplican (están escondidas en el código), quienes los conocían se jubilan y cambiarlos a mano toma semanas y puede romper un cálculo sin que nadie lo note.

La aplicación funciona como un **traductor + auditor** de programas antiguos: **traduce** el programa antiguo a uno moderno y, antes, **escribe las reglas en palabras**, muestra **de qué línea salió cada una** y espera a que **una persona las apruebe**. Después **demuestra** que el programa nuevo da los mismos resultados. La IA (o el motor automático) ayuda, pero **no decide por usted**.

## 2. ¿Qué obtengo al final?

- **Catálogo de reglas de negocio:** las reglas del programa en español, cada una con la línea original que la respalda.
- **Código nuevo:** ordenado por capas, con cada regla identificada.
- **Prueba de que da lo mismo:** decenas de casos, incluidos los límites, comparados con tolerancia cero.
- **Paquete descargable (.zip)** con código, pruebas, documentación y reportes, más un **informe ejecutivo** de una página.
- **Ahorro estimado** frente a hacerlo a mano (estimaciones con supuestos visibles).

## 3. Antes de empezar

**Qué necesita:** un computador con el programa instalado y un navegador (Edge, Chrome, Firefox).

**Cómo abrir la aplicación:**

1. Haga doble clic en el archivo **`iniciar.bat`** de la carpeta del proyecto. (Quien prepara la demostración también puede usar `py run.py`.)
2. Espere unos segundos: el navegador se abre solo con la aplicación. **No cierre la ventana negra**: si la cierra, la aplicación se detiene.

**El selector «Motor» (arriba a la derecha).** Indica *quién hace el trabajo de entender el programa*:

- **Motor local determinista (sin IA):** reglas fijas, sin inteligencia artificial y sin enviar nada fuera del equipo; solo entiende un tipo concreto de COBOL. Ideal para una demo rápida y estable.
- **Claude vía suscripción:** una IA lee el código ya enmascarado y propone las reglas; admite más lenguajes pero tarda unos 6 minutos.
- **Contingencia (pregrabado):** repite una corrida real ya guardada, sin internet y sin IA en ese momento.

Si una opción aparece «no disponible», no está configurada en ese equipo; elija otra.

## 4. Recorrido guiado paso a paso

En cada pantalla hay una **tarjeta amarilla** con el título del paso y la frase **«Qué hacer ahora»**. Si duda, léala: le dice el siguiente clic.

### Novedades que le facilitan el uso
- **Portada de un solo botón:** pulse **«▶ Probar con un ejemplo (opcional)»** y la aplicación carga un programa de ejemplo por usted. Debajo hay tres tarjetas que explican el proceso en tres frases.
- **Guía interactiva:** el botón **««?» (botón flotante)»** (arriba a la derecha) o **«▶ Recorrido de esta pantalla»** (tarjeta amarilla) oscurece la pantalla, enmarca cada zona y la explica con palabras sencillas. Con **«Siguiente →»** avanza, con **«← Anterior»** retrocede y con **Esc** o **«Salir de la guía»** cierra. La primera vez, la tarjeta **«👋 ¿Primera vez aquí?»** se lo ofrece.
- **Ayudas «ⓘ»:** junto a las cifras técnicas hay una **ⓘ**; púlsela y aparece una explicación corta. Hay 20 términos (equivalencia, trazabilidad, cobertura, E2/E3…).
- **Pasos numerados:** el menú superior muestra **1 Ingesta · 2 Descubrimiento · 3 Reglas · 4 Código · 5 Equivalencia · 6 Entrega**. Una ✔ indica que el paso está hecho; un paso atenuado se abrirá cuando complete el anterior.
- **Barra inferior fija:** **«← Paso anterior»** y **«Siguiente: … →»**. Si aún no puede avanzar, aparece **«🔒 …»** con lo que falta (por ejemplo, decidir todas las reglas). En el último paso verá **«Empezar de nuevo»**.

Para practicar paso a paso: [GUIA_ENTRENAMIENTO_DEMO.md](GUIA_ENTRENAMIENTO_DEMO.md).

### Pantalla de inicio
- **«▶ Probar con un ejemplo (opcional)»:** el camino más fácil; carga la muestra COBOL con los casos de referencia (E2). Después pulse «Analizar y extraer reglas →».
- **Otras muestras («Elegir otra muestra»):** pulse **«Usar esta muestra»** en la de COBOL (amortización francesa). Son datos inventados, sin información real.
- **Incluir casos esperados aportados (evidencia E2):** marque la casilla si quiere que la comprobación use resultados esperados entregados por una persona (más abajo se explica).
- **«Cargar su código»:** permite subir un archivo, un ZIP, pegar código o **traerlo desde un repositorio Git público** escribiendo su dirección (la aplicación solo lee una copia; no modifica el repositorio ni necesita claves).
- **«Demostrar el manejo de entradas inválidas»:** tres botones (**Archivo .exe**, **Archivo binario**, **Código vacío**). Muestran que, ante algo incorrecto, la aplicación responde con un mensaje claro y **no guarda ni muestra datos**.

### Paso 1 · Ingesta (carga y ocultamiento de secretos)
- **Qué ve:** los archivos cargados, el lenguaje detectado y un informe de **enmascarado**.
- **Qué significa:** claves, correos, cuentas bancarias u otros datos sensibles se reemplazan por marcas como `<SECRET_001>` **antes** de que el código sea analizado por cualquier IA. Si quedara alguno sin ocultar, la aplicación **detiene** el proceso.
- **Qué hacer:** compruebe que el lenguaje sea el esperado y pulse **«Analizar y extraer reglas →»**. Espere: puede tardar de segundos a minutos según el motor.

### Paso 2 · Descubrimiento (el «mapa» del programa)
- **Qué ve:** cuántas líneas tiene, qué partes lo componen, quién llama a quién, **código muerto** (partes que nunca se ejecutan), qué es **negocio** y qué es **infraestructura** (leer archivos, auditoría) y un mapa de riesgos.
- **Qué hacer:** revise y pase al paso 3 con el menú superior.

### Paso 3 · Reglas (aquí decide usted)
- **Qué ve:** a la izquierda, el programa antiguo con la línea resaltada; a la derecha, tarjetas con cada regla, su **confianza** (porcentaje) y su estado.
- **Etiquetas de respaldo (importante):**
  - **cita verificada** (verde): la línea citada existe y dice lo que la regla afirma.
  - **línea corregida** (ámbar): la regla era correcta pero apuntaba a una línea cercana equivocada; el sistema la corrigió solo.
  - **SIN respaldo en el código** (rojo): no se encontró en el programa. Es sospechosa y **no se puede aprobar**: recházela.
  - **requiere revisión** (ámbar): la confianza es baja; léala con más atención.
- **Estados:** pendiente, aprobada, rechazada, ajustada.
- **Qué hacer:** use **«Aprobar todas las verificadas»** para aceptar de una vez las reglas bien respaldadas, y revise las demás una por una con **Aprobar / Ajustar / Rechazar**. Al terminar, pulse **«Aprobar catálogo y generar código →»**.

### Paso 4 · Código (el programa nuevo)
- **Qué ve:** el código nuevo por capas y una **vista comparativa**: elija una regla arriba y vea a la izquierda su línea original y a la derecha dónde quedó en el código nuevo.
- **Qué hacer:** no necesita leer el código; verifique que cada regla aprobada aparezca implementada.

### Paso 5 · Equivalencia (la prueba)
- **Qué ve:** **Equivalencia 100 %**, **Diferencias en cálculos 0**, cobertura de pruebas, **hallazgos críticos 0** y una tabla con cada caso. Verde = cumple; rojo = hay una diferencia (muestra lo esperado y lo obtenido). Se prueban los bordes (por ejemplo 999,99 frente a 1.000,00), donde suelen aparecer los errores.
- **«Nivel de evidencia» sin siglas:** **E2 = casos aportados** (los resultados esperados los entregó una persona o el cliente; la evidencia más fuerte disponible). **E3 = casos derivados** (los calculó la propia herramienta con un segundo traductor; es un control de consistencia, **pero no se ejecutó el programa antiguo real**, y la pantalla lo dice).

### Paso 6 · Entrega
- **Qué ve:** el tablero (reglas aprobadas, trazabilidad, equivalencia, cobertura, tiempo y costo), el **resumen ejecutivo**, la comparación frente al proceso manual, «¿Qué nos diferencia?» y la matriz de trazabilidad.
- **Qué hacer:** pulse **«Descargar paquete de migración (.zip)»**. Con **«Ver registro de auditoría»** consulta quién aprobó qué y cuándo (se abre justo debajo del botón y se oculta pulsándolo otra vez o con «✕ Cerrar»); la tabla **«Costos por etapa»** muestra «USD cobrado» (0 si la fuente es la suscripción, el modo pregrabado o el motor sin IA) y «Equivale en API», una estimación de lo que costaría con la API de Claude; el registro avisa si alguien intentara alterarlo.

## 5. Cómo decidir sobre las reglas (con ejemplos reales)

Su decisión importa porque **lo que usted aprueba es lo que se programa y se prueba**. Ejemplos de la muestra de amortización (los textos exactos pueden variar según el motor):

| Regla | Qué dice | Qué mirar al decidir |
|---|---|---|
| Monto permitido | Entre 1.000,00 y 500.000,00; fuera de ese rango se rechaza (código E01). | ¿Coincide con la política vigente? |
| Plazo permitido | Entre 6 y 360 meses; si no, rechazo E02. | ¿Los extremos están incluidos? |
| Edad máxima al vencimiento | Edad del cliente + años enteros del plazo no puede pasar de 75 (rechazo E03). | Los años se **truncan** (143 meses = 11 años). |
| Tasa por puntaje | Desde 750: 8,99 %; desde 650: 12,99 %; desde 550: 18,99 %; menos de 550: rechazo E04. | ¿Los tramos son los del negocio? |
| Promoción | Puntaje de 800 o más y plazo de 60 meses o menos: la tasa baja 0,25 puntos. | Ambas condiciones a la vez. |
| Recargo | Plazo mayor a 120 meses: la tasa sube 0,50 puntos. | «Mayor a 120» no incluye 120. |
| Seguro por edad | 0,035 % (menos de 40 años), 0,055 % (menos de 60), 0,095 % (60 o más) del monto, redondeado a 2 decimales. | ¿Se aplica sobre el monto inicial? |

**Cuándo usar cada botón:**
- **Aprobar:** la regla es correcta y refleja la política.
- **Ajustar:** la idea es correcta pero la redacción no; edite el texto y guarde (cambia la descripción, no el código ni la cita).
- **Rechazar:** es incorrecta, no aplica o aparece «SIN respaldo en el código». Puede dejar un comentario.

## 6. Cómo leer el tablero y la calculadora de ahorro

- **Reglas aprobadas** (p. ej. 14/14), **Trazabilidad 100 %** (cada regla enlaza con su línea, su código y sus pruebas), **Equivalencia 100 % y 0 diferencias**, **Cobertura** (parte del código ejercitada por las pruebas).
- **Costo de IA y tiempo:** con el motor local el costo es cero; con Claude vía suscripción no hay cobro por API, pero sí límites del plan.
- **Calculadora «Caso de negocio: de una rutina a toda la cartera»:** escriba en **«Rutinas legacy a migrar»** cuántos programas tiene y verá esfuerzo manual, esfuerzo con la aplicación (incluyendo 20 minutos de revisión humana por rutina), ahorro estimado y reducción porcentual.
  - **Importante:** son **estimaciones con supuestos visibles** (productividad por hora, tarifa por hora). **No son mediciones.** Cámbielos por los de su organización antes de usarlos en una decisión.

## 7. Glosario

- **Legacy:** programa antiguo que sigue en uso (COBOL, PL/SQL, RPG).
- **Regla de negocio:** una política escrita dentro del código (por ejemplo, «el plazo máximo es 360 meses»).
- **Catálogo de reglas:** la lista de reglas aprobadas.
- **Trazabilidad:** seguir una regla desde su línea original hasta el código nuevo y su prueba.
- **Enmascarado:** ocultar datos sensibles antes de analizarlos.
- **Infraestructura:** partes que no son negocio (archivos, mensajes, auditoría).
- **Código muerto:** partes que nunca se ejecutan.
- **Rigor (determinista / heurístico):** con qué firmeza se midió la estructura del programa. *Determinista* = un lector automático conoce el lenguaje (hoy solo COBOL) y las cifras son exactas y repetibles. *Heurístico* = el lenguaje no tiene lector propio y las cifras (líneas, complejidad) son aproximadas, sin mapa de partes ni código muerto. Con lenguajes mezclados la cifra muestra «determinista» si al menos un archivo lo es.
- **Inventario:** porcentaje de las partes encontradas por el lector automático que quedaron listadas en el análisis; debe ser 100 %.
- **Equivalencia:** el programa nuevo da los mismos resultados que el antiguo.
- **Caso límite:** valor justo en el borde de una regla.
- **Tolerancia cero:** no se acepta ni un centavo de diferencia.
- **Redondeo / truncamiento:** redondear sube o baja el decimal; truncar lo corta.
- **Cobertura:** porcentaje del código que las pruebas ejercitan.
- **Arquitectura limpia:** orden del código que separa el negocio de la tecnología.
- **Auditoría encadenada:** registro de acciones a prueba de alteraciones.

## 8. Preguntas frecuentes de negocio

**¿Es seguro mi código y qué pasa con los datos personales?** Antes de usar cualquier IA se **enmascaran** secretos y datos sensibles (correos, cuentas, tarjetas…); si queda alguno, el proceso se detiene. Ningún detector es perfecto. El código que usted sube **nunca se ejecuta**. Con **Claude vía suscripción** el código ya enmascarado **sale hacia Anthropic**; con el motor local y el pregrabado no sale nada. **Use solo datos sintéticos en la demostración** y consulte a seguridad antes de usar código real.

**¿Puede equivocarse la IA?** Sí. Por eso existen controles que no dependen de ella: cada regla debe citar una línea real, las pruebas comparan resultados con tolerancia cero y **una persona aprueba** el catálogo. Una regla inventada se marca «SIN respaldo en el código» y no se puede aprobar.

**¿Quién decide?** Usted. La herramienta propone; el ingeniero o analista aprueba, ajusta o rechaza, y queda registrado.

**¿Cuánto tarda?** Motor local: segundos o pocos minutos. Claude vía suscripción: unos 6 minutos (corrida de prueba). Pregrabado: segundos.

**¿Funciona con cualquier lenguaje?** No todavía. El **motor local** solo cubre un tipo concreto de COBOL; con Claude se pueden analizar otros, pero aquí solo se probó COBOL. Java y C# se generan solo con IA y **no se compilan** aquí.

**¿Demuestra que el programa antiguo y el nuevo son iguales?** Demuestra que el nuevo cumple los casos probados; **no se ejecutó el programa antiguo real**, por eso se indica el nivel de evidencia. La validación con una persona externa que complete el flujo sin ayuda requiere un usuario real y un registro firmado.

## 9. Mini guía para presentar la demo en 10 minutos

Frases clave:
- «Este programa antiguo es una caja negra: nadie sabe con certeza qué reglas aplica.»
- «Aquí están sus reglas, en palabras, cada una con la línea de donde salió.»
- «Usted aprueba o rechaza; nada pasa al código sin su decisión.»
- «Aquí comprobamos decenas de casos, incluidos los límites, y da lo mismo en el sistema nuevo.»
- «Y esta calculadora muestra el ahorro para toda la cartera, con supuestos que usted puede cambiar.»

Qué mostrar, en orden: (1) el selector **«Motor»**; (2) **«Demostrar el manejo de entradas inválidas»** → **Archivo .exe**; (3) **«Usar esta muestra»** (COBOL) y el informe de enmascarado; (4) **«Analizar y extraer reglas →»**; (5) paso 3: una regla con su línea resaltada, **«Aprobar todas las verificadas»**, rechazar o ajustar una y **«Aprobar catálogo y generar código →»**; (6) paso 5: **100 %**, **0 diferencias** y un caso límite; (7) paso 6: tablero, calculadora y **«Descargar paquete de migración (.zip)»**. Si algo falla, cambie a **Contingencia (pregrabado)**.

**Más detalle:** [Guion de la demo](GUION_DEMO.md) (minuto a minuto), [Manual técnico](MANUAL_TECNICO.md) y [Manual combinado](MANUAL_DE_USUARIO.md).

## Cabecera de la aplicación (actualizada)
- **Motor** (lista desplegable): «Sin IA (rápido, en este equipo)», «Con IA» y «Pregrabado (sin conexión)». Solo aparecen los motores disponibles; el de clave de API no se muestra si no está configurado.
- **📁 Proyectos:** abre un panel lateral con sus proyectos agrupados en *En curso o esperando su acción*, *En cola (sin iniciar)*, *Finalizados* y *Con error*. Desde ahí se abre o elimina un proyecto y está el botón **＋ Nuevo proyecto**, que vuelve a la pantalla de inicio para cargar otro programa. Pulsar el nombre «Copiloto de Modernización» también vuelve al inicio.
- **🌙 / ☀️:** cambia entre modo oscuro y claro (se recuerda en este navegador).
- **Botón flotante «?» (abajo a la izquierda):** abre la guía de la pantalla en que esté. Siempre disponible, sin ocupar espacio en la cabecera.

- **Matriz de trazabilidad (paso 6):** cada fila es una regla con su estado («✔ completa», «⚠ incompleta» o «código muerto»), las líneas del programa antiguo que la respaldan (se muestra `archivo:líneas`; la ruta completa aparece al pasar el cursor), el código nuevo y cuántos casos de prueba la cubren. Las reglas que describen código sin uso se documentan pero no se migran ni cuentan en el porcentaje.
- **Si el equivalente no coincide en un caso:** el sistema intenta corregir el código y, si concluye que el código sí sigue al programa antiguo, pide al segundo traductor (el «oráculo») una nueva lectura; nunca se «corrigen» así los casos que aportó el cliente.
- **Si el ZIP trae archivos «binarios»:** la aplicación los omite y los lista en una tarjeta amarilla de la pantalla de Ingesta (no son texto, por ejemplo archivos de datos o copias de macOS). Solo se rechaza la carga si **todos** los archivos son binarios; el mensaje dice cuáles.
