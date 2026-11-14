'use strict';
// Guía interactiva para personas no técnicas: recorrido con foco sobre la pantalla real, ayudas «ⓘ» con lenguaje simple
// y barra de navegación «Anterior / Siguiente». Todo el texto se inserta como nodos de texto (nunca como HTML).

// ---------------------------------------------------------------- glosario en lenguaje simple
const GLOSS = {
  motor: ['Motor', 'Decide quién hace el trabajo. «Sin IA»: un programa automático, instantáneo, solo para COBOL. «Con IA»: una inteligencia artificial que sirve para cualquier lenguaje y tarda varios minutos. «Pregrabado»: repite una corrida real ya hecha, sin internet.'],
  enmascarado: ['Enmascarado', 'Antes de usar cualquier inteligencia, la aplicación tapa claves, correos, cuentas y datos personales. Aparecen como <SECRET_001>. Si quedara alguno sin tapar, el envío se bloquea.'],
  regla: ['Regla de negocio', 'Una política escrita dentro del código antiguo. Ejemplo: «el monto del préstamo debe estar entre 1,000 y 500,000».'],
  trazabilidad: ['Trazabilidad', 'Cada regla señala las líneas exactas del programa antiguo que la respaldan. Así cualquiera (por ejemplo, auditoría) puede comprobar de dónde salió.'],
  confianza: ['Confianza', 'Qué tan segura está la herramienta de haber entendido bien la regla. Más alto = más seguro. Las reglas con confianza baja piden su revisión con más cuidado.'],
  equivalencia: ['Equivalencia', 'Se prueban decenas de casos (incluidos los límites) en el sistema antiguo y en el nuevo y se comparan los resultados. 100 % significa que dan exactamente lo mismo.'],
  diferencias: ['Diferencias en cálculos', 'Cuántos resultados difieren aunque sea por un centavo o un redondeo. Debe ser 0.'],
  cobertura: ['Cobertura de pruebas', 'Qué porcentaje del código nuevo fue ejecutado por las pruebas. Más alto = menos riesgo de errores escondidos. Meta: 80 % de líneas y 70 % de ramas.'],
  hallazgos: ['Hallazgos críticos', 'Problemas graves de calidad o de seguridad detectados automáticamente en el código nuevo. Debe ser 0.'],
  complejidad: ['Complejidad', 'Qué tan enredado está el código. Con 10 o menos es fácil de mantener y probar.'],
  evidencia: ['Nivel de evidencia', 'E2 = casos de prueba aportados por el cliente. E3 = resultados calculados por un segundo traductor del código antiguo (no se ejecutó el programa original). La pantalla siempre dice cuál se usó; nunca se hace pasar uno por otro.'],
  gherkin: ['Escenario (Gherkin)', 'La regla contada con un ejemplo en palabras: «Dado… Cuando… Entonces…». Sirve para que negocio y tecnología entiendan lo mismo.'],
  ahorro: ['Ahorro estimado', 'Es una estimación con supuestos visibles (horas por línea de código, costo por hora), no una medición. Puede cambiarlos en config/estimates.json.'],
  auditoria: ['Auditoría', 'Registro de cada acción (quién aprobó qué y cuándo). Está encadenado: si alguien lo altera, se detecta.'],
  tokens: ['Tokens', 'Unidades de texto que procesa una inteligencia artificial. Sirven para medir el uso y el costo.'],
  loc: ['Líneas de código', 'Cuántas líneas tiene el programa (sin contar comentarios ni líneas vacías).'],
  codigoMuerto: ['Código muerto', 'Partes del programa que nunca se ejecutan. No se migran, para no heredar basura.'],
  rigor: ['Rigor del análisis', 'Dice con qué firmeza se midió la estructura del programa. «Determinista»: un lector automático conoce las reglas de ese lenguaje (hoy solo COBOL) y obtiene partes, llamadas, tablas y código muerto con exactitud; el mismo programa siempre da el mismo resultado. «Heurístico»: el lenguaje no tiene lector propio (PL/SQL, RPG, Java…) y solo se estiman líneas y complejidad por patrones de texto, sin mapa de partes ni código muerto; trate esas cifras como aproximadas y revise con más cuidado. Si el análisis mezcla lenguajes, la cifra muestra «determinista» aunque haya archivos heurísticos: mire la columna de lenguajes.'],
  inventario: ['Inventario', 'De todas las partes que el lector automático encontró en el programa, qué porcentaje quedó listado en el análisis. Debe ser 100 %: si es menos, faltó alguna parte y no se puede seguir.'],
  infra: ['Negocio vs. infraestructura', '«Negocio» son las decisiones y cálculos (se migran como reglas). «Infraestructura» es lo técnico de la plataforma antigua (leer archivos, mensajes, guardar en base de datos) y se resuelve distinto en el sistema nuevo.'],
};
const GLOSS_BY_LABEL = [
  [/Motor de IA/i, 'motor'], [/Equivalencia/i, 'equivalencia'], [/Diferencias/i, 'diferencias'], [/Cobertura/i, 'cobertura'], [/Hallazgos/i, 'hallazgos'],
  [/Complejidad/i, 'complejidad'], [/Trazabilidad/i, 'trazabilidad'], [/enmascarad|Residuos|Secretos/i, 'enmascarado'], [/Tokens/i, 'tokens'], [/Líneas de código|LOC/i, 'loc'],
  [/^Rigor$/i, 'rigor'], [/^Inventario$/i, 'inventario'], [/Código muerto/i, 'codigoMuerto'], [/Reglas aprobadas|Reglas etiquetadas/i, 'regla'], [/Ahorro/i, 'ahorro'],
];
function glossKey(label) { const m = GLOSS_BY_LABEL.find(([rx]) => rx.test(label)); return m ? m[1] : null; }

// ---------------------------------------------------------------- globo de ayuda «ⓘ»
function infoBtn(key) {
  const g = GLOSS[key]; if (!g) return null;
  return h('button', { class: 'info', type: 'button', 'aria-label': 'Qué significa: ' + g[0], title: 'Qué significa', onclick: (e) => { e.stopPropagation(); showPop(e.currentTarget, g[0], g[1]); } }, 'ⓘ');
}
function closePop() { const p = document.querySelector('#pop'); if (p) p.hidden = true; }
function showPop(anchor, title, text) {
  const p = document.querySelector('#pop'); p.replaceChildren(h('b', {}, title), h('p', {}, text), h('button', { class: 'btn sm sec', onclick: closePop }, 'Entendido'));
  p.hidden = false; const r = anchor.getBoundingClientRect(); const w = Math.min(340, innerWidth - 24);
  p.style.width = w + 'px'; p.style.left = Math.max(12, Math.min(innerWidth - w - 12, r.left - 20)) + 'px';
  const below = r.bottom + 8 + p.offsetHeight < innerHeight; p.style.top = (below ? r.bottom + 8 : Math.max(12, r.top - p.offsetHeight - 8)) + 'px';
}
document.addEventListener('click', (e) => { if (!e.target.closest('#pop') && !e.target.closest('.info')) closePop(); });
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') { closePop(); closeTour(); } });

// ---------------------------------------------------------------- recorridos guiados (foco sobre la pantalla real)
const q = (sel) => document.querySelector(sel);
const byText = (sel, text) => [...document.querySelectorAll(sel)].find((e) => e.textContent.includes(text)) || null;
const cardWith = (text) => { const e = byText('.card h2, .card h3, .card b', text); return e ? e.closest('.card') : null; };
const TOURS = {
  home: () => [
    { el: () => q('#btn-demo'), t: 'Ejemplo opcional', d: 'Si solo quiere ver cómo funciona, este botón carga un programa de ejemplo (COBOL ficticio) y le lleva paso a paso. No es obligatorio: también puede cargar su propio código más abajo.' },
    { el: () => q('#mode-select'), t: 'Motor', d: 'Elige quién hace el trabajo. Para la demostración deje «Sin IA» (rápido, no necesita internet). Si quiere ver la inteligencia artificial en acción, elija «Con IA» (más lento).' },
    { el: () => q('#btn-projects'), t: 'Sus proyectos', d: 'Aquí encuentra los programas que ya cargó, agrupados en: en curso, en cola y finalizados. Desde aquí también puede cargar otro programa con «＋ Nuevo proyecto».' },
    { el: () => q('#btn-theme'), t: 'Modo claro u oscuro', d: 'Cambia los colores de la pantalla. Úselo si la sala está oscura o si le resulta más cómodo para leer.' },
    { el: () => q('#btn-guide'), t: 'Esta guía', d: 'Este botón flotante (abajo a la izquierda) está siempre disponible: púlselo en cualquier pantalla para ver su recorrido.' },
    { el: () => byText('.sample', 'COBOL - Amortización'), t: 'Muestras de ejemplo', d: 'Aquí puede elegir otro ejemplo. Todos son ficticios: nunca use datos reales de clientes.' },
    { el: () => q('#cases-cb'), t: 'Casos aportados (opcional)', d: 'Si marca esta casilla, además de las pruebas que genera la herramienta se usan casos de referencia escritos por una persona. Hace la prueba de equivalencia más sólida.' },
    { el: () => cardWith('Cargar su código'), t: 'Su propio código', d: 'Para probar con su programa: suba el archivo, péguelo o escriba la URL de un repositorio Git público (solo se lee una copia; no se modifica). Los secretos y datos personales se tapan antes de cualquier análisis.' },
    { el: () => byText('summary', 'entradas inválidas'), t: 'Qué pasa si algo sale mal', d: 'Abra esta sección y pulse un botón: la aplicación rechaza el archivo incorrecto con un mensaje claro y sin guardar nada.' },
  ],
  ingest: () => [
    { el: () => q('.tiles'), t: 'Resumen de la carga', d: 'Cuántos archivos y líneas se recibieron, en qué lenguaje están y cuántos secretos se taparon. «Residuos tras enmascarar» debe ser 0.' },
    { el: () => cardWith('Informe de enmascarado'), t: 'Informe de enmascarado', d: 'Lista de lo que se tapó (por ejemplo, una contraseña). Lo que ve en la aplicación y lo que se envía a cualquier inteligencia es la versión tapada.' },
    { el: () => byText('button', 'Analizar y extraer reglas'), t: 'Siguiente acción', d: 'Pulse este botón para que la aplicación estudie el programa y encuentre sus reglas de negocio. Con el motor «Sin IA» tarda segundos.' },
  ],
  analyze: () => [
    { el: () => q('.tiles'), t: 'Cifras del programa', d: 'Tamaño, número de partes, complejidad y si hay código muerto. Son datos objetivos calculados por la herramienta.' },
    { el: () => byText('.tile', 'Rigor'), t: 'Rigor: qué tan exacto es el análisis', d: '«Determinista» = un lector automático conoce ese lenguaje (hoy solo COBOL) y las cifras son exactas y repetibles. «Heurístico» = el lenguaje no tiene lector propio y las cifras son aproximadas: revise con más cuidado. Pulse el ⓘ de la cifra para ver el detalle.' },
    { el: () => cardWith('Unidades de análisis'), t: 'Las partes del programa', d: 'Cada fila es una parte del programa. Verde = lógica de negocio (se migra como regla). Gris = infraestructura técnica (se resuelve distinto en el sistema nuevo).' },
    { el: () => cardWith('Grafo de dependencias'), t: 'Quién llama a quién', d: 'Muestra el orden en que se ejecutan las partes. Si aparece «Código muerto», es una parte que nunca se usa y no se migra.' },
    { el: () => cardWith('Contrato de entrada'), t: 'Datos de entrada y salida', d: 'Qué datos recibe el cálculo (por ejemplo, monto y plazo) y qué resultados entrega. Con esto se prueba que el sistema nuevo se comporta igual.' },
  ],
  rules: () => [
    { el: () => q('.rules-bar'), t: 'Su progreso', d: 'Aquí ve cuántas reglas ha decidido. Cuando todas estén decididas se activa el botón verde para continuar.' },
    { el: () => q('.tabs'), t: 'Filtros', d: 'Vea solo las pendientes, las aprobadas o las rechazadas. «Pendientes» es útil para no olvidar ninguna.' },
    { el: () => q('.rcode'), t: 'Código antiguo', d: 'A la izquierda está el programa original. Las líneas resaltadas son las que respaldan la regla seleccionada: así comprueba que la regla no es inventada.' },
    { el: () => q('.rrow.sel') || q('.rlist'), t: 'La regla seleccionada', d: 'Lea la descripción, las condiciones y las acciones. Si coincide con lo que usted sabe del negocio, apruébela.' },
    { el: () => q('.qa') || q('.rlist'), t: 'Aprobar o rechazar', d: '✔ aprueba y ✖ rechaza. Después de decidir, la lista pasa sola a la siguiente regla pendiente. Con «Ajustar» puede corregir el texto de una regla.' },
    { el: () => byText('button', 'Aprobar todas las verificadas'), t: 'Atajo', d: 'Aprueba de una vez todas las reglas pendientes que tienen respaldo comprobado en el código. Úselo solo después de haberlas revisado.' },
    { el: () => byText('button', 'Aprobar catálogo'), t: 'Continuar', d: 'Cuando decidió todas, pulse este botón. Queda registrado quién aprobó y la aplicación genera el código moderno.' },
  ],
  code: () => [
    { el: () => q('.tiles'), t: 'Calidad del código nuevo', d: 'Cuántos archivos se generaron, que estén separados en capas (dominio, aplicación, infraestructura) y que no haya hallazgos críticos.' },
    { el: () => byText('.card', 'Vista comparativa'), t: 'Elija una regla', d: 'Escoja una regla en la lista: a la izquierda verá su línea en el programa antiguo y a la derecha el código nuevo que la implementa (marcado con @rule).' },
    { el: () => q('.mcols') || q('.split'), t: 'Antiguo ↔ nuevo', d: 'Izquierda: el programa original. Derecha: los archivos nuevos. Puede abrir cualquier archivo con la lista.' },
  ],
  verify: () => [
    { el: () => q('.tiles'), t: 'La prueba de que funciona igual', d: 'Equivalencia 100 % y 0 diferencias significa que, para todos los casos probados, el sistema nuevo da exactamente los mismos resultados que el antiguo.' },
    { el: () => cardWith('Nivel de evidencia') || q('.tiles'), t: 'De dónde salen los casos', d: 'Aquí se declara con honestidad cómo se obtuvieron los resultados de referencia (E2 o E3). Nunca se presenta uno como si fuera el otro.' },
    { el: () => q('.scrollbox'), t: 'Todos los casos', d: 'Cada fila es un caso probado, con sus datos de entrada. Incluye casos límite, como el monto mínimo o un plazo de 361 meses (debe rechazarse).' },
  ],
  package: () => [
    { el: () => q('.tiles'), t: 'Resultado final', d: 'Resumen de todo el proceso: reglas aprobadas, equivalencia, cobertura, tiempo y costo.' },
    { el: () => byText('a.btn', 'Descargar paquete'), t: 'El paquete', d: 'Descargue un archivo .zip con el código nuevo, las pruebas, la documentación, la matriz de trazabilidad y el informe ejecutivo.' },
    { el: () => cardWith('Comparación frente al proceso manual'), t: 'Frente a hacerlo a mano', d: 'Compara el tiempo estimado de una persona contra el de la herramienta. Son estimaciones con supuestos visibles, no mediciones.' },
    { el: () => cardWith('Caso de negocio'), t: 'Calculadora de ahorro', d: 'Cambie el número de programas a migrar y vea el ahorro estimado de toda una cartera.' },
    { el: () => cardWith('¿Qué nos diferencia?'), t: 'Lo que nos diferencia', d: 'Reglas con respaldo comprobable, equivalencia demostrada con honestidad, decisión humana, seguridad desde el diseño y un enfoque híbrido determinista + IA.' },
  ],
};
let TOUR = null;
function startTour(name) {
  const make = TOURS[name]; if (!make) return;
  TOUR = { name, i: 0, steps: make().filter((s) => s.el()) }; if (!TOUR.steps.length) { TOUR = null; return; } drawTour();
}
function closeTour() { TOUR = null; const t = document.querySelector('#tour'); if (t) t.replaceChildren(); }
function drawTour() {
  const box = document.querySelector('#tour'); if (!TOUR) { box.replaceChildren(); return; }
  const s = TOUR.steps[TOUR.i]; const el = s.el(); if (!el) { closeTour(); return; }
  el.scrollIntoView({ block: 'center', behavior: 'instant' });
  const r = el.getBoundingClientRect(); const pad = 6;
  const hole = h('div', { class: 'tour-hole', style: `left:${r.left - pad}px;top:${r.top - pad}px;width:${r.width + pad * 2}px;height:${r.height + pad * 2}px` });
  const last = TOUR.i === TOUR.steps.length - 1;
  const card = h('div', { class: 'tour-card', role: 'dialog', 'aria-label': 'Guía: ' + s.t },
    h('div', { class: 'tour-n' }, `Paso ${TOUR.i + 1} de ${TOUR.steps.length}`), h('b', {}, s.t), h('p', {}, s.d),
    h('div', { class: 'tour-dots' }, TOUR.steps.map((_, k) => h('i', { class: k === TOUR.i ? 'on' : '' }))),
    h('div', { class: 'row' },
      h('button', { class: 'btn sm sec', disabled: TOUR.i === 0, onclick: () => { TOUR.i--; drawTour(); } }, '← Anterior'),
      h('button', { class: 'btn sm', onclick: () => { if (last) closeTour(); else { TOUR.i++; drawTour(); } } }, last ? 'Terminar ✔' : 'Siguiente →'),
      h('button', { class: 'tour-skip', onclick: closeTour }, 'Salir de la guía')));
  box.replaceChildren(h('div', { class: 'tour-block', onclick: closeTour }), hole, card);
  const w = Math.min(360, innerWidth - 24); card.style.width = w + 'px';
  const below = r.bottom + pad + 12 + card.offsetHeight < innerHeight;
  card.style.top = (below ? r.bottom + pad + 12 : Math.max(12, r.top - pad - 12 - card.offsetHeight)) + 'px';
  card.style.left = Math.max(12, Math.min(innerWidth - w - 12, r.left)) + 'px';
  card.querySelector('.btn:not(:disabled):not(.sec)').focus();
}
addEventListener('resize', () => { if (TOUR) drawTour(); });
// Mientras la guía está abierta, el scroll manual se bloquea: la guía mueve la página sola a cada elemento,
// así el marco y la tarjeta nunca se desalinean del elemento explicado.
const noScroll = (e) => { if (TOUR) e.preventDefault(); };
document.addEventListener('wheel', noScroll, { passive: false });
document.addEventListener('touchmove', noScroll, { passive: false });
document.addEventListener('keydown', (e) => { if (TOUR && [' ', 'PageDown', 'PageUp', 'Home', 'End', 'ArrowUp', 'ArrowDown'].includes(e.key) && !(e.target instanceof HTMLButtonElement && e.key === ' ')) e.preventDefault(); });
document.addEventListener('keydown', (e) => { if (!TOUR) return; if (e.key === 'ArrowRight' && TOUR.i < TOUR.steps.length - 1) { TOUR.i++; drawTour(); } if (e.key === 'ArrowLeft' && TOUR.i > 0) { TOUR.i--; drawTour(); } });
function currentTourName() { return (!S.p || S.step === 'home') ? 'home' : S.step; }
function tourButton(label) { return h('button', { class: 'btn sm sec', onclick: () => startTour(currentTourName()) }, label || '▶ Recorrido de esta pantalla'); }
function firstTimeSeen() { try { return localStorage.getItem('copilot_tour_seen') === '1'; } catch (e) { return false; } }
function markTourSeen() { try { localStorage.setItem('copilot_tour_seen', '1'); } catch (e) { /* sin almacenamiento */ } }

// ---------------------------------------------------------------- barra «Anterior / Siguiente» al pie de cada paso
function navBar() {
  const ids = STEPS.map((s) => s[0]); const i = ids.indexOf(S.step); const prev = STEPS[i - 1]; const next = STEPS[i + 1];
  const ready = { analyze: ['analyze'], rules: ['rules'], code: ['generate'], verify: ['verify'], package: ['package'] };
  const ok = (id) => (ready[id] || []).every((s) => ['done', 'gate_failed'].includes(stg(s).status));
  const need = { ingest: 'Pulse «Analizar y extraer reglas →» para continuar.', analyze: 'Espere a que termine la extracción de reglas.', rules: 'Decida todas las reglas y pulse «Aprobar catálogo y generar código →».',
    code: 'Espere a que termine la verificación.', verify: 'Espere a que termine el empaquetado.' }[S.step];
  const left = prev ? h('button', { class: 'btn sec', onclick: () => { S.step = prev[0]; render(); scrollTo(0, 0); } }, '← ' + prev[1].replace(/^\d · /, 'Paso anterior: ')) : h('span');
  let right;
  if (next) right = ok(next[0])
    ? h('button', { class: 'btn big', onclick: () => { S.step = next[0]; render(); scrollTo(0, 0); } }, 'Siguiente: ' + next[1].replace(/^\d · /, '') + ' →')
    : h('span', { class: 'mute navhint' }, '🔒 ' + (need || 'Complete este paso para continuar.'));
  else right = h('div', { class: 'row' }, h('span', { class: 'mute' }, '🎉 Terminó el recorrido. Descargue el paquete o pruebe otra muestra.'), h('button', { class: 'btn', onclick: () => { S.step = 'home'; render(); scrollTo(0, 0); } }, 'Empezar de nuevo'));
  return h('nav', { class: 'navbar card', 'aria-label': 'Navegación entre pasos' }, left, right);
}
