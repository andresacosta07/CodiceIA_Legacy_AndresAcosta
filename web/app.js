'use strict';
// Portal del Copiloto. Todo el contenido dinámico se inserta como nodos de texto (nunca como HTML) para evitar XSS con código legacy hostil.
const S = { pid: null, p: null, step: 'home', selRule: null, file: null, mfile: null, status: null, sig: '', timer: null, editing: null };
const $ = (s) => document.querySelector(s);
const STEPS = [
  ['ingest', '1 · Ingesta', 'Carga y datos tapados'], ['analyze', '2 · Descubrimiento', 'Mapa del programa'],
  ['rules', '3 · Reglas', 'Usted decide'], ['code', '4 · Código', 'Código por capas'],
  ['verify', '5 · Equivalencia', 'Prueba de que funciona igual'], ['package', '6 · Entrega', 'Descarga e informe'],
];
const RUNNING = { analyze: 'Analizando estructura y dependencias…', rules: 'Extrayendo reglas de negocio con trazabilidad…', generate: 'Diseñando y generando código…',
  verify: 'Verificando equivalencia funcional y calidad (puede incluir autocorrección)…', docs: 'Generando documentación y matriz de trazabilidad…', package: 'Empaquetando entrega…' };

function h(tag, attrs, ...kids) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (k === 'class') e.className = v; else if (k.startsWith('on')) e.addEventListener(k.slice(2), v);
    else if (v !== false && v != null) e.setAttribute(k, v === true ? '' : v);
  }
  for (const k of kids.flat()) if (k != null && k !== false) e.append(k.nodeType ? k : document.createTextNode(String(k)));
  return e;
}
const chip = (t, c = '') => h('span', { class: 'chip ' + c }, t);
const toast = (m) => { const t = $('#toast'); t.textContent = m; t.hidden = false; clearTimeout(t._t); t._t = setTimeout(() => (t.hidden = true), 6000); };
async function api(path, opts = {}) {
  const r = await fetch('/api' + path, opts);
  let data = null; try { data = await r.json(); } catch (e) { /* sin cuerpo */ }
  if (!r.ok) { const msg = (data && data.error) || 'Error inesperado'; toast(msg + (data && data.hint ? ' — ' + data.hint : '')); throw new Error(msg); }
  return data;
}
const post = (path, body) => api(path, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Reviewer': 'Ingeniero revisor' }, body: JSON.stringify(body || {}) });
const fmt = (n, d = 1) => (n == null ? '—' : Number(n).toLocaleString('es', { maximumFractionDigits: d }));

// ---------------------------------------------------------------- estado / sondeo
const stg = (n) => (S.p && S.p.stages[n]) || { status: 'pending' };
function stepState(id) {
  const m = { ingest: ['ingest'], analyze: ['analyze'], rules: ['rules', 'review'], code: ['generate'], verify: ['verify'], package: ['docs', 'package'] }[id];
  const st = m.map((x) => stg(x).status);
  if (st.includes('failed')) return 'fail'; if (st.includes('running')) return 'run';
  if (st.every((x) => x === 'done' || x === 'gate_failed')) return st.includes('gate_failed') ? 'warn' : 'done';
  return '';
}
function anyRunning() { return S.p && Object.values(S.p.stages).some((s) => s.status === 'running'); }
async function refresh(force) {
  if (!S.pid) return;
  const p = await api('/projects/' + S.pid);
  const sig = JSON.stringify([p.stages, (p.rules || []).map((r) => [r.id, r.status, r.adjusted])]);
  S.p = p;
  if (force || sig !== S.sig) { S.sig = sig; autoStep(); render(); } else renderBanner();
}
function startPolling() { clearInterval(S.timer); S.timer = setInterval(() => refresh().catch(() => {}), 1500); }
let lastRun = {};
function autoStep() {
  // al terminar una etapa, avanza a la vista correspondiente
  // Avanza cuando una etapa pasa a terminada (aunque haya sido tan rápida que nunca se vio «en curso»).
  // Antes de la aprobación se aterriza en la última etapa del grupo (reglas, donde decide el usuario);
  // después, en la primera (código), para poder recorrer los pasos 4, 5 y 6 uno a uno.
  const map = { analyze: 'analyze', rules: 'rules', generate: 'code', verify: 'verify', package: 'package' };
  const fresh = [];
  for (const [s, step] of Object.entries(map)) {
    const st = stg(s).status;
    if (lastRun[s] !== undefined && lastRun[s] !== st && st !== 'running' && st !== 'pending') fresh.push([s, step]);
    lastRun[s] = st;
  }
  const after = fresh.filter(([s]) => ['generate', 'verify', 'package'].includes(s));
  if (after.length) S.step = after[0][1]; else if (fresh.length) S.step = fresh[fresh.length - 1][1];
}

// ---------------------------------------------------------------- vistas
function render() {
  document.body.classList.toggle('has-nav', !(S.step === 'home' || !S.p));
  renderStepper(); renderBanner(); const v = $('#view');
  if (S.step === 'home' || !S.p) { v.replaceChildren(home()); return; }
  v.replaceChildren(helpCard(), ({ ingest: viewIngest, analyze: viewAnalyze, rules: viewRules, code: viewCode, verify: viewVerify, package: viewPackage }[S.step])(), navBar());
}
// Ayuda guiada («¿qué hago ahora?») para que una persona no técnica complete el flujo sin asistencia.
function helpCard() {
  const run = anyRunning(); const st = (n) => stg(n).status;
  const T = {
    ingest: ['Paso 1 · Ingesta', 'Aquí se cargó el código antiguo. Revise que el idioma sea correcto y que los secretos (claves, correos, cuentas) aparezcan como <SECRET_001>: se ocultan ANTES de usar cualquier inteligencia.',
      st('analyze') === 'pending' ? 'Pulse «Analizar y extraer reglas →».' : run ? 'Espere: la aplicación está trabajando.' : 'Pase al paso 2 con el menú superior.'],
    analyze: ['Paso 2 · Descubrimiento', 'Es el «mapa» del programa: qué partes tiene, quién llama a quién, qué es negocio y qué es infraestructura, y dónde hay riesgos.', 'Revise el mapa y pase al paso 3 para ver las reglas.'],
    rules: ['Paso 3 · Reglas (usted decide)', 'Cada fila es una regla de negocio encontrada en el código; a la izquierda se resalta la línea original que la respalda. Una regla «✖ sin respaldo» es sospechosa y no se puede aprobar.',
      st('review') === 'done' ? 'Catálogo aprobado. Pase al paso 4.' : 'Revise cada regla con ✔ (aprobar) o ✖ (rechazar): la lista avanza sola a la siguiente. Use «Ajustar» para corregir un texto, o «Aprobar todas las verificadas». Al terminar pulse «Aprobar catálogo y generar código →».'],
    code: ['Paso 4 · Código moderno', 'Aquí está el código nuevo ordenado por capas. Elija una regla arriba y vea a la izquierda su línea original y a la derecha dónde quedó implementada.', 'Revise y pase al paso 5 para ver la prueba de que funciona igual.'],
    verify: ['Paso 5 · Equivalencia', 'Se ejecutan decenas de casos (incluidos los límites) y se compara el resultado del sistema antiguo con el nuevo. Debe coincidir al 100 % y con cero diferencias en los cálculos.', 'Si todo está en verde, pase al paso 6.'],
    package: ['Paso 6 · Entrega', 'Aquí está el resultado final: tablero, comparación contra hacerlo a mano, trazabilidad y el paquete descargable.', 'Descargue el paquete (.zip) y use la calculadora de ahorro.'],
  }[S.step];
  return h('div', { class: 'card help' }, h('div', { class: 'row', style: 'justify-content:space-between' }, h('b', {}, '🧭 ' + T[0])), h('p', {}, T[1]), h('p', {}, h('b', {}, 'Qué hacer ahora: '), T[2]));
}
function renderStepper() {
  const n = $('#stepper'); n.replaceChildren();
  if (!S.p || S.step === 'home') { n.hidden = true; return; } n.hidden = false;
  const ids = STEPS.map((s) => s[0]); const cur = ids.indexOf(S.step);
  const ready = { ingest: true, analyze: true, rules: stg('analyze').status !== 'pending', code: stg('rules').status !== 'pending', verify: stg('generate').status !== 'pending', package: stg('verify').status !== 'pending' };
  STEPS.forEach(([id, t, sub], k) => {
    const st = stepState(id); const icon = { done: '✔', warn: '!', run: '…', fail: '✖' }[st] || String(k + 1);
    const reachable = ready[id] || k <= cur;
    n.append(h('button', { class: 'step ' + st + (S.step === id ? ' active' : '') + (reachable ? '' : ' todo'), 'aria-current': S.step === id ? 'step' : null, title: reachable ? sub : 'Complete el paso anterior para abrir este',
      onclick: () => { if (!reachable) { toast('Primero complete el paso anterior.'); return; } S.step = id; render(); } },
      h('span', { class: 'sn' }, icon), h('span', { class: 'sl' }, h('b', {}, t.replace(/^\d · /, '')), h('small', {}, sub))));
  });
}
function renderBanner() {
  const b = $('#banner'); b.hidden = true; if (!S.p) return;
  const failed = Object.entries(S.p.stages).find(([, s]) => s.status === 'failed');
  if (failed) { b.className = 'banner err'; b.replaceChildren(h('span', {}, `Error en "${failed[0]}": ${failed[1].error || ''} — ${failed[1].hint || ''}`), h('button', { class: 'btn sm', onclick: () => retry(failed[0]) }, 'Reintentar')); b.hidden = false; return; }
  const run = Object.entries(S.p.stages).find(([, s]) => s.status === 'running');
  if (run) { b.className = 'banner'; const el = Math.round(Date.now() / 1000 - run[1].started); b.replaceChildren(h('span', { class: 'spin' }), h('span', {}, `${RUNNING[run[0]] || run[0]} ${el}s`)); b.hidden = false; }
}
async function retry(stage) {
  if (stage === 'analyze' || stage === 'rules') await post(`/projects/${S.pid}/start`); else await post(`/projects/${S.pid}/continue`);
  await refresh(true);
}

function home() {
  const form = { target: 'typescript' };
  const samples = h('div', { class: 'samples' }, 'Cargando muestras…');
  api('/samples').then((list) => samples.replaceChildren(...list.map((s) => h('div', { class: 'sample' }, h('b', {}, s.title), h('p', { class: 'mute' }, s.description),
    (S.status && S.status.mode === 'local' && s.language !== 'cobol')
      ? h('span', { class: 'chip warn', title: 'El motor sin IA solo analiza COBOL. Elija un motor con IA para otros lenguajes.' }, 'Requiere un motor con IA (cambie el «Motor»)')
      : h('button', { class: 'btn sm', onclick: () => createSample(s.name, form.target, $('#cases-cb') && $('#cases-cb').checked) }, 'Usar esta muestra')))));
  const fileIn = h('input', { type: 'file', multiple: true, id: 'files' });
  const text = h('textarea', { id: 'code', placeholder: 'Pegue aquí código COBOL / PL/SQL / RPG / Java…' });
  const how = [['1', 'Cargue un programa antiguo', 'La aplicación tapa los datos sensibles y lo estudia.'], ['2', 'Usted aprueba las reglas', 'Cada regla de negocio se muestra con la línea que la respalda.'], ['3', 'Vea la prueba', 'El sistema nuevo se compara con el antiguo, caso por caso.']];
  const welcome = firstTimeSeen() ? null : h('div', { class: 'card help' }, h('b', {}, '👋 ¿Primera vez aquí?'), h('p', {}, 'Haga el recorrido guiado de 1 minuto: le muestra para qué sirve cada zona de la pantalla.'),
    h('div', { class: 'row' }, h('button', { class: 'btn', onclick: () => { markTourSeen(); startTour('home'); } }, '▶ Empezar recorrido'), h('button', { class: 'btn sec', onclick: () => { markTourSeen(); render(); } }, 'No, gracias')));
  return h('div', {}, welcome, h('div', { class: 'hero' }, h('h1', {}, 'Del código legacy a software moderno, verificado'), h('p', { class: 'lead' }, 'Convierte un programa antiguo en reglas de negocio claras, código nuevo y una prueba de que funciona igual.'),
    h('ol', { class: 'howto' }, how.map(([n, t, d]) => h('li', {}, h('span', { class: 'hn' }, n), h('div', {}, h('b', {}, t), h('p', {}, d))))),
    h('p', { class: 'mute demo-hint' }, '¿Quiere verlo sin cargar nada? ', h('button', { class: 'btn sm sec', id: 'btn-demo', onclick: () => createSample('cobol_amortizacion', 'typescript', true) }, '▶ Probar con un ejemplo (opcional)'),
      ' Usa un COBOL ficticio de cálculo de cuotas; tarda menos de un minuto con «Sin IA».')),
    h('h2', { class: 'sect' }, 'Otras opciones'),
    h('div', { class: 'grid g2' },
      h('div', { class: 'card' }, h('h2', {}, 'Elegir otra muestra'), samples,
        h('label', {}, h('input', { type: 'checkbox', id: 'cases-cb' }), ' Incluir casos esperados aportados (evidencia E2)'),
        h('label', {}, 'Stack destino'), targetSelect((v) => (form.target = v))),
      h('div', { class: 'card' }, h('h2', {}, 'Cargar su código'),
        h('label', {}, 'Archivos o ZIP (COBOL, copybooks, PL/SQL, RPG, Java…)'), fileIn,
        h('label', {}, 'O pegue el código'), text,
        h('fieldset', { class: 'repo-box' }, h('legend', {}, 'O traiga el código desde un repositorio Git'),
          h('label', { for: 'repo-url' }, 'URL del repositorio (público)'),
          h('input', { class: 'full', id: 'repo-url', type: 'url', placeholder: 'https://github.com/organización/repositorio', autocomplete: 'off' }),
          h('div', { class: 'row' }, h('div', { style: 'flex:1' }, h('label', { for: 'repo-ref' }, 'Rama o etiqueta (opcional)'), h('input', { class: 'full', id: 'repo-ref', placeholder: 'Por defecto: la principal' })),
            h('div', { style: 'flex:1' }, h('label', { for: 'repo-dir' }, 'Carpeta con el código (opcional)'), h('input', { class: 'full', id: 'repo-dir', placeholder: 'Ej. src/cobol' }))),
          h('p', { class: 'mute' }, '🔒 Solo lectura: se descarga una copia del código (GitHub, GitLab, Bitbucket o Codeberg). No se clona, no se hace pull ni se modifica el repositorio. Solo repositorios públicos; no escriba usuarios ni claves.'),
          h('button', { class: 'btn sec', onclick: () => createRepo(form) }, 'Importar desde el repositorio')),
        h('div', { class: 'row' }, h('div', { style: 'flex:1' }, h('label', {}, 'Nombre del proyecto'), h('input', { class: 'full', id: 'pname', placeholder: 'Ej. Cálculo de cuota' })),
          h('div', { style: 'flex:1' }, h('label', {}, 'Dominio funcional'), h('input', { class: 'full', id: 'pdomain', placeholder: 'Ej. Tarificación de seguros' }))),
        h('label', {}, 'Stack destino'), targetSelect((v) => (form.target = v)),
        h('p', { class: 'mute' }, '🔒 Los secretos y datos personales se enmascaran antes de cualquier envío al modelo. Use solo datos sintéticos.'),
        h('button', { class: 'btn', onclick: () => createUpload(form) }, 'Cargar y analizar'),
        h('details', {}, h('summary', {}, 'Demostrar el manejo de entradas inválidas'),
          h('p', { class: 'mute' }, 'Cada botón envía una entrada incorrecta. La aplicación debe rechazarla con un mensaje claro y sin guardar ni mostrar datos.'),
          h('div', { class: 'row' }, h('button', { class: 'btn sm sec', onclick: () => demoInvalid('exe') }, 'Archivo .exe'), h('button', { class: 'btn sm sec', onclick: () => demoInvalid('binary') }, 'Archivo binario'),
            h('button', { class: 'btn sm sec', onclick: () => demoInvalid('empty') }, 'Código vacío'))))));
}
function targetSelect(on) {
  const local = S.status && ['local', 'replay'].includes(S.status.mode);
  const note = local ? ' — requiere un motor con IA' : '';
  const s = h('select', {}, h('option', { value: 'typescript' }, 'Node.js / TypeScript (ejecutado y verificado)'),
    h('option', { value: 'java', disabled: local }, 'Java 21 + Spring Boot (generado; validación estática)' + note), h('option', { value: 'csharp', disabled: local }, 'C# .NET (generado; validación estática)' + note));
  s.addEventListener('change', () => on(s.value)); return s;
}
// Demostración del manejo de entradas inválidas (criterio Funcional): mensaje claro, acción sugerida y sin exponer datos.
async function demoInvalid(kind) {
  const fd = new FormData(); fd.append('target', 'typescript');
  if (kind === 'exe') fd.append('files', new Blob([new Uint8Array([77, 90, 144, 0])]), 'programa.exe');
  else if (kind === 'binary') fd.append('files', new Blob([new Uint8Array([0, 1, 2, 3, 0, 255])]), 'datos.cbl');
  else fd.append('code_text', '   ');
  try { await api('/projects', { method: 'POST', body: fd }); } catch (e) { /* api() ya muestra el aviso con la acción sugerida */ }
}
async function createSample(name, target, withCases) { const r = await post('/projects/sample', { name, target, with_cases: !!withCases }); await openProject(r.id, 'ingest'); }
async function createUpload(form) {
  const fd = new FormData(); const files = $('#files').files; for (const f of files) fd.append('files', f);
  fd.append('code_text', $('#code').value); fd.append('name', $('#pname').value); fd.append('domain', $('#pdomain').value); fd.append('target', form.target);
  const r = await api('/projects', { method: 'POST', body: fd }); await openProject(r.id, 'ingest');
}
// Importa el código de un repositorio Git público (solo lectura; el servidor descarga el ZIP, no clona).
let importing = false;
async function createRepo(form) {
  if (importing) return;
  importing = true; toast('Descargando el código del repositorio…');
  try {
    const r = await post('/projects/repo', { url: $('#repo-url').value, ref: $('#repo-ref').value, subdir: $('#repo-dir').value,
      name: $('#pname').value, domain: $('#pdomain').value, target: form.target });
    const s = r.source; const extra = s.skipped_other ? ` (${s.skipped_other} archivos que no son código se omitieron)` : '';
    toast(`Importados ${s.files} archivos de ${s.repo}${extra}.`);
    await openProject(r.id, 'ingest');
  } finally { importing = false; }
}
async function openProject(pid, step) { S.pid = pid; S.step = step || 'ingest'; S.selRule = null; S.file = null; lastRun = {}; await refresh(true); startPolling(); await loadProjects(); }

function tile(label, value, cls = '') { return h('div', { class: 'tile ' + cls }, h('b', {}, value), h('span', {}, label, infoBtn(glossKey(label)))); }
function table(head, rows) { return h('table', {}, h('thead', {}, h('tr', {}, head.map((x) => h('th', {}, x)))), h('tbody', {}, rows.map((r) => h('tr', {}, r.map((c) => h('td', {}, c)))))); }

function viewIngest() {
  const r = S.p.ingest_report; const ok = r.gate_no_secrets;
  const running = anyRunning(); const started = stg('analyze').status !== 'pending';
  return h('div', {},
    h('div', { class: 'tiles' }, tile('Archivos', r.files), tile('Líneas', fmt(r.total_lines, 0)), tile('Lenguajes', r.languages.join(', ') || '—'),
      tile('Secretos/PII enmascarados', r.masked_total, r.masked_total ? 'warn' : 'ok'), tile('Residuos tras enmascarar', r.residual_secrets, ok ? 'ok' : 'bad'),
      tile('Includes/copybooks', r.includes.complete ? 'completos' : 'faltan ' + r.includes.missing.length, r.includes.complete ? 'ok' : 'warn')),
    (r.skipped_binary && r.skipped_binary.length) ? h('div', { class: 'card help' }, h('b', {}, '⚠ Se omitieron ' + r.skipped_binary.length + ' archivo(s) binario(s)'),
      h('p', {}, 'No son texto, así que no se pueden analizar como código: ' + r.skipped_binary.slice(0, 8).join(', ') + (r.skipped_binary.length > 8 ? '…' : '') + '. Si alguno era código fuente (por ejemplo, un programa con datos empaquetados), súbalo por separado como texto.')) : null,
    h('div', { class: 'grid g2' },
      h('div', { class: 'card' }, h('h3', {}, 'Artefactos normalizados'), table(['Archivo', 'Lenguaje', 'Dialecto', 'Codificación', 'Líneas', 'Enmascarados'],
        S.p.artifacts.map((a) => [a.path, chip(a.language, 'brand'), a.dialect || '—', a.encoding, a.lines, a.masked_count]))),
      h('div', { class: 'card' }, h('h3', {}, 'Informe de enmascarado (compuerta: 0 secretos)'),
        r.mask_findings.length ? table(['Archivo', 'Línea', 'Tipo', 'Reemplazo'], r.mask_findings.map((f) => [f.file, f.line, f.kind, f.token])) : h('p', { class: 'mute' }, 'No se detectaron secretos.'),
        h('p', { class: 'mute' }, 'El código mostrado en la plataforma y enviado al modelo es la versión enmascarada.'))),
    h('div', { class: 'card' }, h('div', { class: 'row' }, ok ? chip('Compuerta superada', 'ok') : chip('Compuerta fallida', 'bad'),
      h('button', { class: 'btn', disabled: !ok || running || started, onclick: async () => { await post(`/projects/${S.pid}/start`); await refresh(true); } }, started ? 'Análisis iniciado' : 'Analizar y extraer reglas →'))));
}

function viewAnalyze() {
  const a = S.p.analysis, s = S.p.static;
  if (!a) return h('div', { class: 'card' }, 'Aún no hay análisis. Inicie el análisis desde la fase 1.');
  const edges = s.edges.filter((e) => e.kind !== 'COPY');
  return h('div', {},
    h('div', { class: 'tiles' }, tile('Líneas de código (LOC)', fmt(s.loc, 0)), tile('Unidades inventariadas', a.units.length), tile('Complejidad máx.', s.max_cyclomatic), tile('Código muerto', s.dead_units.length, s.dead_units.length ? 'warn' : 'ok'),
      tile('Tablas/archivos', s.tables.length), tile('Rigor', s.rigor), tile('Inventario', a.inventory_recall_pct + ' %', a.inventory_recall_pct >= 100 ? 'ok' : 'warn')),
    h('div', { class: 'card' }, h('h3', {}, 'Resumen de negocio'), h('p', {}, a.domain_summary), h('p', { class: 'mute' }, `Lenguaje: ${a.language} · ${a.dialect}. Puntos de entrada: ${a.entry_points.join(', ') || '—'}`)),
    h('div', { class: 'grid g2' },
      h('div', { class: 'card' }, h('h3', {}, 'Unidades de análisis'), table(['Unidad', 'Tipo', 'Clasificación', 'Líneas', 'Resumen'],
        a.units.map((u) => [u.name, u.kind, chip(u.classification, u.classification === 'business' ? 'ok' : u.classification === 'infrastructure' ? '' : 'warn'), `${u.start_line}‑${u.end_line}` + (u.verified ? '' : ' ⚠'), u.summary]))),
      h('div', { class: 'card' }, h('h3', {}, 'Grafo de dependencias'), edges.length ? table(['Desde', 'Relación', 'Hacia'], edges.map((e) => [e.from, chip(e.kind), e.to])) : h('p', { class: 'mute' }, 'Sin dependencias detectadas por el analizador determinista.'),
        s.dead_units.length ? h('p', {}, '⚠ Código muerto: ', s.dead_units.join(', ')) : null)),
    h('div', { class: 'grid g2' },
      h('div', { class: 'card' }, h('h3', {}, 'Mapa de riesgo de migración'), table(['Unidad', 'Nivel', 'Motivo'], a.risks.map((r) => [r.unit, chip(r.level, r.level === 'high' ? 'bad' : r.level === 'medium' ? 'warn' : 'ok'), r.reason]))),
      h('div', { class: 'card' }, h('h3', {}, 'Hallazgos de seguridad del legacy'), a.security_findings.length ? table(['Ubicación', 'Categoría', 'Detalle'], a.security_findings.map((f) => [`${f.file}:${f.line}`, chip(f.category, 'bad'), f.description])) : h('p', { class: 'mute' }, 'Ninguno.'))),
    h('div', { class: 'card' }, h('h3', {}, 'Contrato de entrada/salida (la lógica de negocio como función pura)'), h('p', { class: 'mute' }, a.io_contract.description),
      h('div', { class: 'grid g2' }, table(['Entrada', 'Tipo', 'Escala'], a.io_contract.inputs.map((f) => [f.name, f.type, f.scale])), table(['Salida', 'Tipo', 'Escala'], a.io_contract.outputs.map((f) => [f.name, f.type, f.scale])))));
}

function codeView(text, hl, id) {
  const pre = h('pre', { class: 'code', id }); const lines = text.split('\n');
  lines.forEach((ln, i) => { const n = i + 1; pre.append(h('span', { class: 'ln' + (hl.some(([s, e]) => n >= s && n <= e) ? ' hl' : ''), 'data-n': n }, h('i', {}, n), ln)); });
  setTimeout(() => { const f = pre.querySelector('.hl'); if (f) pre.scrollTop = Math.max(0, f.offsetTop - 80); }, 0);
  return pre;
}
// ---- Paso 3: lista compacta de reglas (una línea por regla; el detalle solo de la seleccionada) ----
const FILTERS = [['all', 'Todas'], ['proposed', 'Pendientes'], ['approved', 'Aprobadas'], ['rejected', 'Rechazadas']];
async function decideRule(r, status, edits, comment) {
  try {
    await post(`/projects/${S.pid}/rules/${r.id}/review`, { status, comment: comment || '', edits });
    const all = (await api('/projects/' + S.pid)).rules;               // avanza solo a la siguiente regla pendiente
    const i = all.findIndex((x) => x.id === r.id);
    const next = [...all.slice(i + 1), ...all.slice(0, i)].find((x) => x.status === 'proposed');
    S.editing = null; if (next) { S.selRule = next.id; S.file = null; }
    await refresh(true); scrollRuleIntoView();
  } catch (e) { /* api() ya mostró el aviso con la acción sugerida */ }
}
function scrollRuleIntoView() { setTimeout(() => { const el = document.querySelector('.rrow.sel'); if (el) el.scrollIntoView({ block: 'nearest', behavior: 'smooth' }); }, 60); }
function viewRules() {
  if (!S.p.rules) return h('div', { class: 'card' }, 'Aún no hay reglas. Inicie el análisis.');
  const rules = S.p.rules; const sel = rules.find((r) => r.id === S.selRule) || rules.find((r) => r.status === 'proposed') || rules[0];
  const ref = sel.source_refs[0]; const art = S.p.artifacts.find((a) => a.path === (S.file || (ref && ref.file))) || S.p.artifacts[0];
  const hl = sel.source_refs.filter((r) => r.file === art.path).map((r) => [r.start_line, r.end_line]);
  const cnt = { proposed: 0, approved: 0, rejected: 0 }; rules.forEach((r) => cnt[r.status]++); const decided = rules.length - cnt.proposed;
  const done = stg('review').status === 'done'; const locked = done && stg('generate').status !== 'pending';
  const gate = stg('rules').gate; const filter = S.filter || 'all';
  const shown = rules.filter((r) => filter === 'all' || r.status === filter);
  const fileSel = h('select', { onchange: (e) => { S.file = e.target.value; render(); } }, S.p.artifacts.map((a) => h('option', { value: a.path, selected: a.path === art.path }, a.path)));
  const bar = h('div', { class: 'rules-bar card' },
    h('div', { class: 'rb-left' },
      h('b', {}, `${decided} de ${rules.length} reglas decididas`), h('div', { class: 'meter' }, h('i', { style: `width:${Math.round(100 * decided / rules.length)}%` })),
      h('div', { class: 'row' }, chip(`${cnt.proposed} pendientes`, cnt.proposed ? 'warn' : 'ok'), chip(`${cnt.approved} aprobadas`, 'ok'), chip(`${cnt.rejected} rechazadas`, cnt.rejected ? 'bad' : ''),
        chip(`Trazabilidad ${gate ? gate.traceability_pct : '—'} %`, gate && gate.passed ? 'ok' : 'warn'))),
    h('div', { class: 'rb-right' },
      h('button', { class: 'btn sec', disabled: locked || !cnt.proposed, onclick: async () => { const r = await post(`/projects/${S.pid}/rules/approve-verified`); toast(`${r.approved} reglas aprobadas`); await refresh(true); } }, 'Aprobar todas las verificadas'),
      h('button', { class: 'btn ok', disabled: locked || done || cnt.proposed > 0, title: cnt.proposed ? 'Decida primero todas las reglas pendientes' : '', onclick: approveAndGo },
        done ? 'Catálogo aprobado v' + S.p.catalog.version : 'Aprobar catálogo y generar código →')));
  const tabs = h('div', { class: 'tabs' }, FILTERS.map(([k, label]) => h('button', { class: 'tab' + (filter === k ? ' on' : ''), onclick: () => { S.filter = k; render(); } },
    label + ' ', h('span', { class: 'n' }, k === 'all' ? rules.length : cnt[k]))));
  const list = h('div', { class: 'rlist' }, shown.length ? shown.map((r) => ruleRow(r, r.id === sel.id, locked)) : h('p', { class: 'mute', style: 'padding:14px' }, 'No hay reglas en este filtro.'));
  return h('div', {}, bar,
    h('div', { class: 'rsplit' },
      h('div', { class: 'card rcode' }, h('div', { class: 'row' }, h('h3', {}, 'Código legacy'), fileSel), codeView(art.text, hl, 'legacy-code'),
        h('p', { class: 'mute' }, `Las líneas resaltadas respaldan la regla ${sel.id}.`)),
      h('div', { class: 'rright' }, tabs, list)));
}
async function approveAndGo() { try { await post(`/projects/${S.pid}/approve`); await post(`/projects/${S.pid}/continue`); S.step = 'code'; await refresh(true); } catch (e) { /* toast ya mostrado */ } }
function ruleRow(r, selected, locked) {
  const icon = { approved: '✔', rejected: '✖', proposed: '○' }[r.status];
  const tshort = { verified: ['✓ cita', 'ok'], corrected: ['⚠ línea corregida', 'warn'], failed: ['✖ sin respaldo', 'bad'] }[r.trace_status];
  const quick = locked ? null : h('span', { class: 'qa' },
    h('button', { class: 'qbtn ok', title: 'Aprobar', disabled: r.trace_status === 'failed', onclick: (e) => { e.stopPropagation(); decideRule(r, 'approved'); } }, '✔'),
    h('button', { class: 'qbtn bad', title: 'Rechazar', onclick: (e) => { e.stopPropagation(); decideRule(r, 'rejected'); } }, '✖'));
  const head = h('div', { class: 'rhead', onclick: () => { S.selRule = r.id; S.file = null; S.editing = null; render(); scrollRuleIntoView(); } },
    h('span', { class: 'st ' + r.status, title: { approved: 'aprobada', rejected: 'rechazada', proposed: 'pendiente' }[r.status] }, icon),
    h('span', { class: 'rname' }, h('b', {}, r.id), ' · ', r.name), r.adjusted ? chip('ajustada', 'warn') : null,
    h('span', { class: 'rmeta' }, chip(r.category), chip(Math.round(r.confidence * 100) + ' %'), chip(tshort[0], tshort[1])), quick);
  return h('div', { class: 'rrow' + (selected ? ' sel' : '') + ' ' + r.status }, head, selected ? ruleDetail(r, locked) : null);
}
function ruleDetail(r, locked) {
  const comment = h('input', { class: 'full', placeholder: 'Comentario (opcional)', value: r.comment || '' });
  const ta = h('textarea', { style: 'min-height:80px' }, r.description);
  const edit = S.editing === r.id;
  return h('div', { class: 'rdetail' },
    h('p', {}, r.description),
    r.conditions.length ? h('div', {}, h('b', {}, 'Condiciones'), h('ul', {}, r.conditions.slice(0, 6).map((c) => h('li', {}, c)))) : null,
    r.actions.length ? h('div', {}, h('b', {}, 'Acciones'), h('ul', {}, r.actions.slice(0, 6).map((c) => h('li', {}, c)))) : null,
    h('p', { class: 'mute' }, 'Origen: ' + r.source_refs.map((x) => `${x.file}:${x.start_line}-${x.end_line}`).join(', ') + ' · ' + r.assumptions.join(' · ')),
    h('details', {}, h('summary', {}, 'Escenario Gherkin / tabla de decisión'), h('pre', { class: 'code', style: 'padding:8px 12px' }, r.gherkin),
      r.decision_table.columns.length ? table(r.decision_table.columns, r.decision_table.rows) : null),
    locked ? null : edit
      ? h('div', {}, h('label', {}, 'Ajustar descripción'), ta, h('div', { class: 'row' }, h('button', { class: 'btn sm ok', onclick: () => decideRule(r, 'approved', { description: ta.value }, comment.value) }, 'Guardar y aprobar'),
        h('button', { class: 'btn sm sec', onclick: () => { S.editing = null; render(); } }, 'Cancelar')))
      : h('div', {}, comment, h('div', { class: 'row', style: 'margin-top:8px' },
        h('button', { class: 'btn sm ok', disabled: r.trace_status === 'failed', onclick: () => decideRule(r, 'approved', undefined, comment.value) }, 'Aprobar y seguir'),
        h('button', { class: 'btn sm sec', onclick: () => { S.editing = r.id; render(); } }, 'Ajustar'),
        h('button', { class: 'btn sm bad', onclick: () => decideRule(r, 'rejected', undefined, comment.value) }, 'Rechazar y seguir'))));
}

function viewCode() {
  const g = S.p.generation;
  if (!g) return h('div', { class: 'card' }, stg('generate').status === 'running' ? 'Generando código…' : 'Aún no se ha generado código. Apruebe el catálogo de reglas en la fase 3.');
  const files = g.files.map((f) => f.path).concat(g.target === 'typescript' ? ['src/domain/shared/decimal.ts (plataforma)'] : []);
  const rid = S.selRule || (S.p.rules.find((r) => r.status === 'approved') || {}).id;
  const rule = S.p.rules.find((r) => r.id === rid); const art = S.p.artifacts.find((a) => rule && rule.source_refs[0] && a.path === rule.source_refs[0].file) || S.p.artifacts[0];
  const tagged = Object.keys((g.scan.rule_tags) || {}); const filesWithRule = (g.scan.rule_tags || {})[rid] || [];
  // archivo moderno por defecto: el que implementa la regla elegida (si no, el punto de entrada)
  const sel = g.files.find((f) => f.path === S.mfile) || g.files.find((f) => f.path === filesWithRule[0]) || g.files.find((f) => /src\/index\.ts$/.test(f.path)) || g.files[0];
  const modernHl = sel.content.split('\n').map((ln, i) => (ln.includes('@rule') && ln.includes(rid || '\u0000') ? [i + 1, i + 1] : null)).filter(Boolean);
  const ruleSel = h('select', { onchange: (e) => { S.selRule = e.target.value; S.mfile = null; render(); } }, S.p.rules.filter((r) => r.status === 'approved').map((r) => h('option', { value: r.id, selected: r.id === rid }, `${r.id} — ${r.name}`)));
  return h('div', {},
    h('div', { class: 'tiles' }, tile('Archivos generados', g.files.length), tile('Capas', g.scan.layers.join(' / '), g.scan.layers.length === 3 ? 'ok' : 'bad'), tile('Complejidad máx.', g.scan.max_cc, g.scan.max_cc <= 10 ? 'ok' : 'bad'),
      tile('Hallazgos críticos', g.scan.blocking, g.scan.blocking === 0 ? 'ok' : 'bad'), tile('Reglas etiquetadas en código', tagged.length), tile('Autocorrecciones', g.autofix.length)),
    h('div', { class: 'card' }, h('h3', {}, 'Diseño de arquitectura'), h('p', {}, g.design.summary), h('div', { class: 'row' }, g.design.patterns.map((p) => chip(p, 'brand')))),
    h('div', { class: 'card' }, h('div', { class: 'row' }, h('b', {}, 'Vista comparativa legacy ↔ moderno · regla:'), ruleSel, filesWithRule.length ? chip('implementada en ' + filesWithRule.length + ' archivo(s)', 'ok') : chip('sin etiqueta en código', 'warn'))),
    h('div', { class: 'split' },
      h('div', { class: 'card' }, h('h3', {}, 'Legacy: ' + art.path), codeView(art.text, rule ? rule.source_refs.filter((x) => x.file === art.path).map((x) => [x.start_line, x.end_line]) : [], 'cmp-legacy')),
      h('div', { class: 'card' }, h('h3', {}, 'Moderno: ' + sel.path), h('div', { class: 'mcols' }, h('div', { class: 'tree' }, files.map((f) => h('button', { class: sel.path === f ? 'on' : '', onclick: () => { S.mfile = f.endsWith('(plataforma)') ? S.mfile : f; render(); } }, (filesWithRule.includes(f) ? '● ' : '') + f))),
        codeView(sel.content, modernHl, 'cmp-modern')))),
    h('div', { class: 'card' }, h('h3', {}, 'Decisiones de arquitectura (ADRs)'), g.design.adrs.map((a) => h('details', {}, h('summary', {}, a.title), h('p', {}, h('b', {}, 'Contexto: '), a.context), h('p', {}, h('b', {}, 'Decisión: '), a.decision), h('p', {}, h('b', {}, 'Consecuencias: '), a.consequences)))));
}

function viewVerify() {
  const v = S.p.verification, g = S.p.generation;
  if (!v) return h('div', { class: 'card' }, stg('verify').status === 'running' ? 'Verificando…' : 'La verificación se ejecuta tras generar el código.');
  const e = v.equivalence, u = v.unit_tests || {}; const sc = g.scan;
  const notExec = !v.executed;
  const evid = v.evidence_note || {};
  return h('div', {},
    notExec ? h('div', { class: 'banner' }, v.note) : null,
    h('div', { class: 'tiles' },
      tile('Equivalencia legacy ↔ moderno', e ? e.pct + ' %' : 'n/d', e && e.pct === 100 ? 'ok' : 'bad'), tile('Casos', e ? `${e.passed}/${e.total}` : '—'), tile('Diferencias en cálculos', e ? e.numeric_differences : '—', e && e.numeric_differences === 0 ? 'ok' : 'bad'),
      tile('Cobertura líneas', u.line_coverage != null ? u.line_coverage + ' %' : '—', u.line_coverage >= 80 ? 'ok' : 'bad'), tile('Cobertura ramas', u.branch_coverage != null ? u.branch_coverage + ' %' : '—', u.branch_coverage >= 70 ? 'ok' : 'bad'),
      tile('Hallazgos críticos', sc.blocking, sc.blocking === 0 ? 'ok' : 'bad'), tile('Complejidad máx.', sc.max_cc, sc.max_cc <= 10 ? 'ok' : 'bad')),
    e ? h('div', { class: 'card' }, h('div', { class: 'row' }, h('b', {}, 'Nivel de evidencia: '), (v.evidence || '').split('+').map((k) => chip(`${k}: ${evid[k] || ''}`, k === 'E3' ? 'warn' : 'ok'))),
      h('p', { class: 'mute' }, 'E3 = segundo traductor derivado del código legacy (no se ejecutó el legacy; comparte el análisis con el generador). E2 = casos esperados aportados por el cliente. Nunca se presenta E3 como ejecución del legacy.'),
      v.rules_untested.length ? h('p', {}, '⚠ Reglas sin caso de prueba: ' + v.rules_untested.join(', ')) : h('p', {}, '✔ Todas las reglas aprobadas tienen casos de prueba.')) : null,
    e ? h('div', { class: 'card' }, h('h3', {}, `Casos de equivalencia (tolerancia 0) · ${e.passed} de ${e.total} equivalentes`), h('div', { class: 'scrollbox' }, table(['Caso', 'Evidencia', 'Resultado', 'Entrada (' + ((v.cases[0] && Object.keys(v.cases[0].input).join(', ')) || '') + ')'],
      e.cases.map((c) => { const inp = (v.cases.find((x) => x.name === c.name) || {}).input || {}; return [c.name, chip(c.evidence, c.evidence === 'E2' ? 'ok' : ''), c.equivalent ? chip('equivalente', 'ok') : chip('DIFERENCIA ' + JSON.stringify(c.diffs).slice(0, 140), 'bad'), Object.values(inp).join(' · ')]; })))) : null,
    h('div', { class: 'grid g2' },
      h('div', { class: 'card' }, h('h3', {}, 'Guardrails de arquitectura y seguridad'), sc.findings.length ? table(['Sev.', 'Categoría', 'Archivo', 'Detalle'], sc.findings.map((f) => [chip(f.severity, f.severity === 'critical' || f.severity === 'high' ? 'bad' : 'warn'), f.category, f.file, f.message])) : h('p', {}, '✔ Sin hallazgos: regla de dependencias, precisión numérica y SAST ligero en verde.')),
      h('div', { class: 'card' }, h('h3', {}, 'Ciclo de autocorrección'), g.autofix.length ? g.autofix.map((a) => h('p', {}, `Iteración ${a.iteration}: ${a.explanation || a.problems.join(' | ')}`)) : h('p', {}, (S.p.verification && S.p.verification.equivalence) ? 'No fue necesaria: el código pasó a la primera.' : 'No se ejecutó: la verificación se detuvo antes de comparar resultados (' + ((S.p.verification && S.p.verification.evidence) || 'sin detalle') + '). Revise los hallazgos de la izquierda.'))));
}

function viewPackage() {
  const m = S.p.metrics || {}; const d = S.p.docs; const t = S.p.trace;
  if (!S.p.package) return h('div', { class: 'card' }, anyRunning() ? 'Generando documentación y paquete…' : 'El paquete se genera al finalizar la verificación.');
  const manual = m.manual_hours_estimate * 3600, auto = Math.max(m.pipeline_seconds, 1); const max = Math.max(manual, auto);
  return h('div', {},
    h('div', { class: 'tiles' }, tile('Reglas aprobadas', `${m.rules_approved}/${m.rules_total}`), tile('Trazabilidad', m.traceability_pct + ' %', 'ok'), tile('Equivalencia', m.equivalence_pct != null ? m.equivalence_pct + ' %' : 'n/d', m.equivalence_pct === 100 ? 'ok' : 'warn'),
      tile('Cobertura (líneas/ramas)', `${fmt(m.line_coverage, 0)}/${fmt(m.branch_coverage, 0)} %`), tile('Hallazgos críticos', m.blocking_findings, m.blocking_findings === 0 ? 'ok' : 'bad'), tile('Secretos sin enmascarar enviados', 0, 'ok'),
      tile('Tiempo de máquina', fmt(m.pipeline_seconds, 0) + ' s'), tile('Costo de IA', '$' + fmt(m.cost_usd, 3)), tile('Tokens', `${fmt(m.tokens_in, 0)} / ${fmt(m.tokens_out, 0)}`)),
    h('div', { class: 'card' }, h('h3', {}, 'Resumen ejecutivo'), h('p', {}, d.executive_summary),
      h('div', { class: 'row' }, h('a', { class: 'btn', href: `/api/projects/${S.pid}/download` }, '⬇ Descargar paquete de migración (.zip)'))),
    h('div', { class: 'card' }, h('h3', {}, 'Comparación frente al proceso manual'),
      h('div', { class: 'cmp' }, h('span', { class: 'lbl' }, 'Manual (estimado)'), h('div', { class: 'b m', style: `width:${Math.max(4, 100 * manual / max)}%` }, `${m.manual_hours_estimate} h (~${m.manual_days_estimate} días)`)),
      h('div', { class: 'cmp' }, h('span', { class: 'lbl' }, 'Copiloto'), h('div', { class: 'b', style: `width:${Math.max(4, 100 * auto / max)}%` }, `${fmt(m.pipeline_seconds, 0)} s + revisión humana`)),
      h('p', { class: 'mute' }, `Supuestos parametrizables (no son mediciones): ${m.estimates.analysis_loc_per_hour} LOC/h análisis, ${m.estimates.migration_and_tests_loc_per_hour} LOC/h migración y pruebas, $${m.estimates.hourly_rate_usd}/h. Ahorro estimado: ~$${fmt(m.manual_cost_usd, 0)}.`)),
    businessCase(m),
    h('div', { class: 'card' }, h('h3', {}, '¿Qué nos diferencia?'), h('ul', {},
      h('li', {}, h('b', {}, 'Reglas que no se inventan: '), 'cada regla cita líneas reales y un verificador automático lo comprueba (no depende de la confianza en la IA).'),
      h('li', {}, h('b', {}, 'Equivalencia demostrada, con honestidad: '), 'casos de borde con tolerancia cero y el nivel de evidencia declarado (E2 aportado / E3 derivado); nunca se hace pasar por ejecución del legacy.'),
      h('li', {}, h('b', {}, 'El humano decide: '), 'ninguna regla llega al código sin aprobación explícita y queda en una auditoría a prueba de manipulación.'),
      h('li', {}, h('b', {}, 'Seguro por diseño: '), 'los secretos se ocultan antes de usar IA, el código se ejecuta aislado y las entradas maliciosas se rechazan.'),
      h('li', {}, h('b', {}, 'Híbrido determinista + IA: '), 'el análisis estático da la base verificable; la IA (o el motor local sin clave) trabaja sobre estructura, no sobre texto suelto.'))),
    traceCard(t),
    h('div', { class: 'grid' },
      h('div', { class: 'card' }, h('h3', {}, 'Costos por etapa'), table(['Etapa', 'Modelo', 'Llamadas', 'Tokens ent./sal.', 'USD cobrado', 'Equivale en API (est.)', 'Fuente'],
          (m.llm_by_stage || []).map((s) => [s.stage, s.model, s.calls, `${s.tokens_in}/${s.tokens_out}`, s.cost_usd ? '$' + fmt(s.cost_usd, 2) : '$0 (sin cargo)', s.reference_usd ? '~$' + fmt(s.reference_usd, 2) : '—', s.source])),
        h('p', { class: 'mute' }, `Total equivalente en la API de Claude: ~$${fmt(m.reference_cost_usd, 2)}. «USD cobrado» es 0 cuando la fuente es la suscripción, el modo pregrabado o el motor sin IA (no cobran por uso); «Equivale en API» es lo que costaría con la API según los precios de config/models.json (estimación).`),
        h('p', { class: 'mute' }, `Auditoría encadenada por hash: ${m.audit_chain_ok ? '✔ íntegra' : '✖ alterada'}`), h('button', { class: 'btn sm sec', id: 'btn-audit', onclick: showAudit }, 'Ver registro de auditoría'))),
    h('div', { class: 'card' }, h('details', {}, h('summary', {}, `Contenido del paquete (${S.p.package.files.length} archivos)`), h('p', { class: 'mute' }, S.p.package.files.join(' · ')))));
}
// Matriz de trazabilidad: tarjeta a todo el ancho; las rutas largas se muestran como «archivo:líneas» (la ruta completa, al pasar el cursor).
function refChip(path) {
  const m = /^(.*?)(?::(\d+)-(\d+))?$/.exec(path); const file = m[1].split('/').pop();
  return h('div', { class: 'tr-ref', title: path }, m[2] ? `${file}:${m[2]}‑${m[3]}` : file);
}
function traceCard(t) {
  const dead = (t.dead_code_rules || []).length;
  const state = (r) => (r.dead ? chip('código muerto', '') : r.complete ? chip('✔ completa', 'ok') : chip('⚠ incompleta', 'warn'));
  const rows = t.rows.map((r) => [state(r), h('div', {}, h('b', {}, r.rule), ' ', r.name), h('div', {}, r.legacy_lines.length ? r.legacy_lines.map(refChip) : '—'),
    h('div', {}, r.code.length ? r.code.map(refChip) : (r.dead ? 'no se migra' : '⚠ sin código')), h('span', { class: 'nowrap' }, r.dead ? 'n/a' : String(r.tests.length))]);
  return h('div', { class: 'card' }, h('h3', {}, `Matriz de trazabilidad extremo a extremo · ${t.complete_pct} % completa`),
    dead ? h('p', { class: 'mute' }, `${dead} regla(s) describen código sin uso: se documentan pero no se migran ni cuentan en el porcentaje.`) : null,
    h('div', { class: 'scrollbox tall' }, table(['Estado', 'Regla', 'Líneas legacy', 'Código nuevo', 'Casos'], rows)));
}
// Caso de negocio interactivo: extrapola el ahorro de esta rutina a una cartera de rutinas (supuestos parametrizables).
function businessCase(m) {
  const est = m.estimates; const out = h('div', {}); const input = h('input', { type: 'number', min: 1, max: 100000, value: 50, style: 'width:110px' });
  const draw = () => {
    const n = Math.max(1, Math.min(100000, Number(input.value) || 1));
    const manualH = m.manual_hours_estimate * n; const autoH = (m.pipeline_seconds / 3600 + est.human_review_minutes_per_routine / 60) * n;
    const saved = (manualH - autoH) * est.hourly_rate_usd; const pct = manualH ? Math.round(100 * (1 - autoH / manualH)) : 0;
    out.replaceChildren(h('div', { class: 'tiles' }, tile('Esfuerzo manual', fmt(manualH, 0) + ' h', 'bad'), tile('Con el copiloto (incl. revisión humana)', fmt(autoH, 0) + ' h', 'ok'),
      tile('Ahorro estimado', '$' + fmt(saved, 0), 'ok'), tile('Reducción de esfuerzo', pct + ' %', 'ok'), tile('Equivale a (días hábiles)', fmt((manualH - autoH) / est.hours_per_day, 0))));
  };
  input.addEventListener('input', draw); draw();
  return h('div', { class: 'card' }, h('h3', {}, 'Caso de negocio: de una rutina a toda la cartera'),
    h('div', { class: 'row' }, h('span', {}, 'Rutinas legacy a migrar:'), input),
    out, h('p', { class: 'mute' }, `Supuestos (config/estimates.json, no son mediciones): revisión humana de ${est.human_review_minutes_per_routine} min por rutina, $${est.hourly_rate_usd}/h, ${est.hours_per_day} h/día; esfuerzo manual y tiempo de máquina tomados de esta ejecución.`));
}
// Registro de auditoría: un solo panel, junto al botón, que se abre y se cierra (antes se apilaba una tarjeta nueva en cada clic).
async function showAudit(ev) {
  const btn = ev.currentTarget; const open = $('#audit-box');
  if (open) { open.remove(); btn.textContent = 'Ver registro de auditoría'; return; }
  const a = await api(`/projects/${S.pid}/audit`);
  const box = h('div', { id: 'audit-box', class: 'audit-box' },
    h('div', { class: 'row', style: 'justify-content:space-between' }, h('b', {}, 'Registro de auditoría (' + (a.chain_ok ? 'íntegro' : 'ALTERADO') + ') · ' + a.events.length + ' eventos'),
      h('button', { class: 'btn sm sec', onclick: () => { box.remove(); btn.textContent = 'Ver registro de auditoría'; } }, '✕ Cerrar')),
    h('div', { class: 'scrollbox' }, table(['#', 'Actor', 'Acción', 'Detalle'], a.events.map((e) => [e.seq, e.actor, e.action, JSON.stringify(e.detail).slice(0, 120)]))));
  btn.after(box); btn.textContent = 'Ocultar registro de auditoría';
}

// ---------------------------------------------------------------- motor (selector): nombres genéricos, solo modos disponibles
const MODE_LABELS = { local: 'Sin IA (rápido, en este equipo)', 'claude-code': 'Con IA', live: 'Con IA (clave de API)', replay: 'Pregrabado (sin conexión)' };
const MODE_HINTS = {
  local: 'Sin inteligencia artificial: el análisis, las reglas, el código y las pruebas se derivan del programa de forma automática y determinista. Solo COBOL; es instantáneo y no usa internet.',
  'claude-code': 'Con inteligencia artificial: sirve para cualquier lenguaje y redacta las reglas en lenguaje de negocio. Es más lento (varios minutos) y depende de su sesión y de los límites de su plan.',
  live: 'Con inteligencia artificial a través de una clave de API (pago por uso).', replay: 'Repite una corrida real ya grabada. No usa internet ni inteligencia artificial.' };
async function refreshMode() { S.status = await api('/status'); paintMode(); }
function paintMode() {
  const st = S.status; const sel = $('#mode-select');
  const shown = Object.entries(st.available_modes).filter(([k, ok]) => ok || k === st.mode);   // los no disponibles no se muestran
  sel.replaceChildren(...shown.map(([k]) => h('option', { value: k, selected: k === st.mode, title: MODE_HINTS[k] }, MODE_LABELS[k])));
  sel.title = MODE_HINTS[st.mode] || 'Quién hace el análisis';
}
// ---------------------------------------------------------------- panel de proyectos (actuales · en cola · finalizados)
const GROUPS = [['actual', 'En curso o esperando su acción'], ['cola', 'En cola (sin iniciar)'], ['finalizado', 'Finalizados'], ['error', 'Con error']];
function ago(ts) { const s = Math.max(0, Date.now() / 1000 - ts); if (s < 60) return 'hace un momento'; if (s < 3600) return `hace ${Math.round(s / 60)} min`; if (s < 86400) return `hace ${Math.round(s / 3600)} h`; return `hace ${Math.round(s / 86400)} d`; }
async function loadProjects() { S.projects = await api('/projects'); $('#proj-count').textContent = S.projects.length; if (!$('#drawer').hidden) renderDrawer(); }
function openDrawer() { $('#drawer').hidden = false; $('#scrim').hidden = false; renderDrawer(); loadProjects().catch(() => {}); const c = $('#drawer button'); if (c) c.focus(); }
function closeDrawer() { $('#drawer').hidden = true; $('#scrim').hidden = true; }
// «Nuevo proyecto»: vuelve al inicio y lleva el cursor al formulario «Cargar su código» (resaltado un instante).
function newProject() {
  closeDrawer(); S.step = 'home'; render();
  const card = byText('.card h2', 'Cargar su código'); const box = card && card.closest('.card');
  if (box) { box.scrollIntoView({ block: 'center' }); box.classList.add('flash'); setTimeout(() => box.classList.remove('flash'), 1600); }
  const t = $('#pname'); if (t) t.focus({ preventScroll: true });
}
function stepForProject(p) { return p.group === 'finalizado' ? 'package' : /decisión/.test(p.label) ? 'rules' : /Generando/.test(p.label) ? 'code' : 'ingest'; }
async function removeProject(p) {
  if (!confirm(`¿Eliminar «${p.name}»? Se borran sus datos y no se puede deshacer.`)) return;
  await api('/projects/' + p.id, { method: 'DELETE' }); if (S.pid === p.id) { S.pid = null; S.p = null; S.step = 'home'; render(); } await loadProjects();
}
function projItem(p) {
  const tone = { finalizado: 'ok', error: 'bad', cola: '', actual: 'warn' }[p.group];
  return h('div', { class: 'pitem' + (p.id === S.pid ? ' cur' : '') },
    h('button', { class: 'pmain', onclick: () => { closeDrawer(); openProject(p.id, stepForProject(p)); } }, h('span', { class: 'pname', title: p.name }, p.name), h('span', { class: 'pmeta' }, chip(p.label, tone), ago(p.created))),
    h('button', { class: 'pdel', title: 'Eliminar este proyecto', 'aria-label': 'Eliminar ' + p.name, onclick: () => removeProject(p) }, '🗑'));
}
function renderDrawer() {
  const list = S.projects || [];
  $('#drawer').replaceChildren(
    h('div', { class: 'dr-head' }, h('h2', {}, 'Sus proyectos'), h('button', { class: 'btn sm sec', onclick: closeDrawer }, '✕ Cerrar')),
    h('div', { class: 'dr-new' }, h('b', {}, 'Cargar otro programa'), h('p', {}, 'Vuelve a la pantalla de inicio para elegir una muestra o subir su propio código.'),
      h('button', { class: 'btn', onclick: newProject }, '＋ Nuevo proyecto')),
    ...GROUPS.flatMap(([g, title]) => { const items = list.filter((p) => p.group === g); if (g === 'error' && !items.length) return [];
      return [h('div', { class: 'dr-group' }, h('span', {}, title), h('span', {}, String(items.length))), ...(items.length ? items.map(projItem) : [h('p', { class: 'dr-empty' }, 'Ninguno por ahora.')])]; }));
}
// ---------------------------------------------------------------- modo claro / oscuro
function effectiveTheme() { return document.documentElement.dataset.theme || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'); }
function paintThemeButton() { const dark = effectiveTheme() === 'dark'; const b = $('#btn-theme'); b.textContent = dark ? '☀️' : '🌙'; b.title = dark ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro'; b.setAttribute('aria-label', b.title); }
function toggleTheme() { const next = effectiveTheme() === 'dark' ? 'light' : 'dark'; document.documentElement.dataset.theme = next; try { localStorage.setItem('copilot_theme', next); } catch (e) { /* sin almacenamiento */ } paintThemeButton(); }
// ---------------------------------------------------------------- arranque
(async function init() {
  try { const t = localStorage.getItem('copilot_theme'); if (t === 'dark' || t === 'light') document.documentElement.dataset.theme = t; } catch (e) { /* sin almacenamiento */ }
  paintThemeButton();
  $('#btn-home').addEventListener('click', () => { S.step = 'home'; render(); scrollTo(0, 0); });
  $('#btn-guide').addEventListener('click', () => startTour(currentTourName()));
  $('#btn-projects').addEventListener('click', openDrawer); $('#scrim').addEventListener('click', closeDrawer); $('#btn-theme').addEventListener('click', toggleTheme);
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeDrawer(); });
  await refreshMode();
  $('#mode-select').addEventListener('change', async (e) => { try { S.status = await post('/mode', { mode: e.target.value }); } catch (err) { /* toast */ } paintMode(); render(); });
  await loadProjects(); render();
  const q = new URLSearchParams(location.search);  // enlaces directos: /?p=<id>&step=rules
  if (/^[0-9a-f]{32}$/.test(q.get('p') || '')) await openProject(q.get('p'), q.get('step') || 'ingest');
})();
