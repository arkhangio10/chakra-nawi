// Panel del técnico · Chakra Ñawi (ARCHITECTURE §3.6). JS sin frameworks ni build.
// Lee GET /casos, GET /reglas y /audio/mensajes.json; llama con POST /llamadas/{caso_id}.
// API: la misma que sirve la página (GET /panel/). Para otra, abrir con ?api=https://mi-api.example.com
'use strict';

(() => {
  const params = new URLSearchParams(location.search);
  const API = (params.get('api') || (location.protocol === 'file:' ? 'http://localhost:8000' : '')).replace(/\/+$/, '');

  const ESTADOS = {
    tecnico_urgente: { orden: 0, etiqueta: 'Técnico · urgente', cuenta: ['urgente', 'urgentes'] },
    tecnico: { orden: 1, etiqueta: 'Técnico', cuenta: ['para técnico', 'para técnico'] },
    amarillo: { orden: 2, etiqueta: 'Amarillo', cuenta: ['amarillo', 'amarillos'] },
    verde: { orden: 3, etiqueta: 'Verde', cuenta: ['verde', 'verdes'] },
  };
  const CAUSAS = {
    sin_problema: 'Sin problema', broca: 'Broca', roya: 'Roya', clima_floracion: 'Clima en la floración',
    plantas_viejas: 'Plantas viejas', otra: 'Otra causa',
  };
  const TEMPORADAS = { cosecha: 'Cosecha (may–jul)', fin_seca: 'Fin de la seca (ago–oct)', lluvias: 'Lluvias (nov–abr)' };
  const MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre',
    'noviembre', 'diciembre'];
  const TENDENCIA = { sube: '↑ sube', igual: '→ igual', baja: '↓ baja', sin_dato: 'sin dato' };
  const GRANOS = { '0': 'Ninguno con huequito', '1-2': '1 o 2 con huequito', '3+': '3 o más con huequito', no_se: 'No sabe' };
  const POLVO = { si: 'Sí, ve polvo naranja', no: 'No', no_se: 'No sabe' };
  const IDIOMAS = { es: 'castellano', quz: 'quechua' };
  const EVIDENCIAS = {
    E_TRAMPA_TENDENCIA: 'Tendencia de la trampa (YOLO)', E_GRANOS: 'Granos con huequito (pregunta)',
    E_POLVO_NARANJA: 'Polvo naranja (pregunta)', E_LLUVIA_DIAS: 'Días con lluvia nov–abr (CHIRPS v3)',
    E_TEMP_ROYA: 'Días de temperatura para roya (NASA POWER)', E_LLUVIA_FLORACION: 'Lluvia en la floración (CHIRPS v3)',
    E_CALOR_FLORACION: 'Calor en la floración (NASA POWER)', E_EDAD: 'Plantas > 20 años sin recepa (inscripción)',
    A_REGIONAL: 'Alerta regional (alertas_activas.json)',
  };
  const ZONA = 'America/Lima';
  const fmtFecha = new Intl.DateTimeFormat('es-PE', { dateStyle: 'medium', timeStyle: 'short', timeZone: ZONA });
  const fmtCorta = new Intl.DateTimeFormat('es-PE', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit', timeZone: ZONA });
  const fmtHora = new Intl.DateTimeFormat('es-PE', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  const fmtMes = new Intl.DateTimeFormat('en-US', { month: 'numeric', timeZone: ZONA });
  const fmtNum = new Intl.NumberFormat('es-PE', { maximumFractionDigits: 2 });
  const fmtPct = new Intl.NumberFormat('es-PE', { style: 'percent', maximumFractionDigits: 0 });
  const anchoGrande = matchMedia('(min-width: 900px)');

  const $ = (id) => document.getElementById(id);
  const ui = {
    lista: $('lista'), casos: $('casos'), resumen: $('resumen'), detalle: $('detalle'),
    actualizar: $('actualizar'), sello: $('sello'), aviso: $('aviso'), origen: $('origen-api'),
  };
  const st = { casos: [], reglas: null, mensajes: null, sel: idDelHash(), ampliada: false, cajas: true, cargado: false };

  // ---------- utilidades ----------
  function h(tag, props, ...hijos) {
    const el = document.createElement(tag);
    for (const [k, v] of Object.entries(props || {})) {
      if (v == null || v === false) continue;
      if (k === 'class') el.className = v;
      else if (k.startsWith('on')) el.addEventListener(k.slice(2), v);
      else el.setAttribute(k, v === true ? '' : v);
    }
    for (const c of hijos.flat(Infinity)) if (c != null && c !== false) el.append(c instanceof Node ? c : String(c));
    return el;
  }
  function svg(tag, attrs) {
    const el = document.createElementNS('http://www.w3.org/2000/svg', tag);
    for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
    return el;
  }
  const fecha = (iso) => (iso ? fmtFecha.format(new Date(iso)) : '—');
  const corta = (iso) => (iso ? fmtCorta.format(new Date(iso)) : '—');
  function idDelHash() { return decodeURIComponent(location.hash.slice(1)) || null; }
  const seccion = (titulo, ...hijos) => h('section', { class: 'seccion' }, h('h3', {}, titulo), ...hijos);
  const datos = (pares) => h('dl', { class: 'datos' },
    pares.filter(Boolean).map(([dt, dd]) => [h('dt', {}, dt), h('dd', {}, dd)]));

  function chip(estado, texto, grande) {
    return h('span', { class: `chip e-${estado}${grande ? ' grande' : ''}` },
      h('span', { class: 'forma', 'aria-hidden': 'true' }), texto ?? ESTADOS[estado]?.etiqueta ?? estado);
  }
  function etiquetaEstado(r) {
    const base = ESTADOS[r.estado]?.etiqueta ?? r.estado;
    return r.estado === 'amarillo' && r.causa ? `${base} · ${CAUSAS[r.causa] ?? r.causa}` : base;
  }

  async function pedir(ruta, opciones) {
    let r;
    try {
      r = await fetch(API + ruta, { headers: { Accept: 'application/json' }, cache: 'no-store', ...opciones });
    } catch (e) {
      const err = new Error(`no hay conexión con la API (${API || location.origin})`);
      err.status = 0;
      throw err;
    }
    let cuerpo = null;
    try { cuerpo = await r.json(); } catch { /* sin cuerpo JSON */ }
    if (!r.ok) {
      const d = cuerpo?.detail ?? cuerpo;
      const err = new Error(typeof d === 'string' ? d : d ? JSON.stringify(d) : `HTTP ${r.status}`);
      err.status = r.status;
      throw err;
    }
    return cuerpo;
  }

  function avisar(texto) {
    ui.aviso.textContent = texto;
    ui.aviso.hidden = !texto;
  }

  // ---------- carga ----------
  async function cargar() {
    ui.actualizar.disabled = true;
    ui.sello.textContent = 'Actualizando…';
    try {
      const [casos, reglas, mensajes] = await Promise.all([
        pedir('/casos'),
        pedir('/reglas').catch(() => null),
        pedir('/audio/mensajes.json').catch(() => null),
      ]);
      st.casos = casos.slice().sort((a, b) =>
        (ESTADOS[a.resultado.estado]?.orden ?? 9) - (ESTADOS[b.resultado.estado]?.orden ?? 9)
        || String(b.creado).localeCompare(String(a.creado)));
      st.reglas = reglas ?? st.reglas;
      st.mensajes = mensajes ?? st.mensajes;
      st.cargado = true;
      avisar(reglas ? '' : 'No pude leer GET /reglas: las reglas se muestran solo con su código.');
      ui.sello.textContent = `Actualizado ${fmtHora.format(new Date())}`;
    } catch (e) {
      avisar(`No pude leer los casos: ${e.message}.`);
      ui.sello.textContent = '';
    } finally {
      ui.actualizar.disabled = false;
    }
    if (!st.sel && anchoGrande.matches && st.casos.length) st.sel = st.casos[0].caso_id;
    pintarLista();
    pintarDetalle();
  }

  // ---------- lista ----------
  function pintarLista() {
    const n = st.casos.length;
    const cuenta = Object.keys(ESTADOS)
      .map((e) => [e, st.casos.filter((c) => c.resultado.estado === e).length])
      .filter(([, k]) => k)
      .map(([e, k]) => `${k} ${ESTADOS[e].cuenta[k === 1 ? 0 : 1]}`);
    ui.resumen.textContent = st.cargado ? `${n} ${n === 1 ? 'caso' : 'casos'}${cuenta.length ? ' · ' + cuenta.join(' · ') : ''}` : '';

    if (!n) {
      ui.casos.replaceChildren(h('li', { class: 'vacio' }, st.cargado
        ? 'No hay casos todavía. Llegan cuando el teléfono de campo tiene señal.' : ''));
      return;
    }
    ui.casos.replaceChildren(...st.casos.map((c) => {
      const r = c.resultado;
      const ultima = c.llamadas?.[0];
      const marcas = [
        c.conteo?.dudoso && h('span', { class: 'marca-alerta' }, 'conteo dudoso'),
        c.foto?.tipo === 'hojas' && h('span', {}, 'foto de hojas'),
        !c.foto_url && h('span', {}, 'sin foto'),
        ultima ? h('span', {}, `${ultima.simulada ? 'llamada simulada' : 'llamada'} ${corta(ultima.fecha)}`)
          : h('span', {}, 'sin llamar'),
      ];
      return h('li', {}, h('button', {
        type: 'button', class: `caso e-${r.estado}`, 'aria-current': c.caso_id === st.sel ? 'true' : null,
        onclick: () => seleccionar(c.caso_id),
      },
      h('span', { class: 'fila' }, chip(r.estado, etiquetaEstado(r)), h('span', { class: 'tenue' }, corta(c.creado))),
      h('span', { class: 'fila' }, h('span', { class: 'finca' }, `Finca ${c.finca_id}`),
        h('span', { class: 'tenue' }, TEMPORADAS[c.temporada] ?? c.temporada)),
      h('span', { class: 'marcas' }, marcas)));
    }));
  }

  function seleccionar(id) {
    st.sel = id;
    st.ampliada = false;
    history.replaceState(null, '', `${location.pathname}${location.search}#${encodeURIComponent(id)}`);
    pintarLista();
    pintarDetalle();
    if (!anchoGrande.matches) {
      ui.detalle.scrollIntoView({ behavior: 'smooth', block: 'start' });
      ui.detalle.focus({ preventScroll: true });
    }
  }

  // ---------- detalle ----------
  function pintarDetalle() {
    const c = st.casos.find((x) => x.caso_id === st.sel);
    if (!c) {
      ui.detalle.className = 'detalle';
      ui.detalle.replaceChildren(h('p', { class: 'vacio' }, st.cargado
        ? (st.casos.length ? 'Elige un caso de la lista.' : 'Sin casos.') : 'Cargando casos…'));
      return;
    }
    const r = c.resultado;
    ui.detalle.className = `detalle e-${r.estado}`;
    ui.detalle.replaceChildren(
      h('button', {
        type: 'button', class: 'boton chico volver',
        onclick: () => { ui.lista.scrollIntoView({ behavior: 'smooth' }); },
      }, '← Lista de casos'),
      h('header', { class: 'det-cab' },
        h('div', { class: 'det-titulo' }, chip(r.estado, etiquetaEstado(r), true), h('h2', {}, `Finca ${c.finca_id}`)),
        h('p', { class: 'tenue' }, fecha(c.creado), ' · ', TEMPORADAS[c.temporada] ?? c.temporada, mesSimulado(c))),
      seccionLlamada(c),
      h('div', { class: 'dos-columnas' },
        seccionFoto(c),
        h('div', {}, seccionConteo(c), seccionRespuestas(c))),
      seccionResultado(c),
      seccionReglas(c),
      h('p', { class: 'meta' },
        `Caso ${c.caso_id} · app ${c.app_version} · ficha ${c.ficha_version} · recibido ${fecha(c.recibido)}`));
  }

  function mesSimulado(c) {
    const real = Number(fmtMes.format(new Date(c.creado)));
    if (!c.mes || c.mes === real) return null;
    return h('span', { class: 'mes-simulado' }, ` · el motor usó ${MESES[c.mes - 1]} (fecha del modo técnico)`);
  }

  function seccionLlamada(c) {
    const salida = h('div', { class: 'llamada-resultado', 'aria-live': 'polite' });
    const historial = h('p', { class: 'tenue' });
    const pintarHistorial = () => {
      historial.textContent = c.llamadas?.length
        ? `Llamadas por este caso: ${c.llamadas.map((l) => `${corta(l.fecha)} (${l.simulada ? 'simulada' : 'real'})`).join(' · ')}`
        : 'Todavía no se la llamó por este caso.';
    };
    pintarHistorial();
    const boton = h('button', { type: 'button', class: 'boton primario' }, 'Llamar a Noor');
    boton.addEventListener('click', () => llamar(c, boton, salida, pintarHistorial));
    return h('section', { class: 'seccion llamada' },
      h('div', { class: 'llamada-fila' }, boton,
        h('span', {}, 'Escuchará ', h('code', {}, 'L_INTRO'), ' y ', h('code', {}, c.resultado.mensaje), ' dos veces (≤ 30 s).')),
      salida, historial);
  }

  async function llamar(c, boton, salida, pintarHistorial) {
    boton.disabled = true;
    boton.textContent = 'Llamando…';
    salida.className = 'llamada-resultado';
    salida.replaceChildren('Enviando la llamada…');
    try {
      const r = await pedir(`/llamadas/${encodeURIComponent(c.caso_id)}`, { method: 'POST' });
      const usados = [...new Set(Object.values(r.idioma_audio || {}))].map((i) => IDIOMAS[i] ?? i).join(' y ');
      const audio = r.respaldo
        ? `Audio en ${usados}: respaldo, porque falta el audio en ${IDIOMAS[r.idioma_finca] ?? r.idioma_finca}.`
        : `Audio en ${usados}.`;
      salida.classList.add(r.simulada ? 'simulada' : 'real');
      salida.replaceChildren(
        h('strong', {}, r.simulada ? 'Llamada SIMULADA' : 'Llamada REAL enviada a Twilio'),
        r.simulada
          ? ' · el servidor no tiene credenciales de Twilio; ningún teléfono sonó.'
          : ` · SID ${r.sid}. El teléfono de Noor debería sonar en unos segundos.`,
        h('br'), h('span', { class: 'tenue' }, audio),
        h('details', {}, h('summary', {}, 'Ver TwiML'), h('pre', {}, r.twiml)));
      c.llamadas = [{ fecha: new Date().toISOString(), simulada: r.simulada, mensaje: c.resultado.mensaje }, ...(c.llamadas || [])];
      pintarHistorial();
      pintarLista();
    } catch (e) {
      salida.classList.add('error');
      const motivo = e.status === 502 ? `Twilio respondió con error: ${e.message}` : e.message;
      salida.replaceChildren(h('strong', {}, 'No se pudo llamar'), ` · ${motivo}`);
    } finally {
      boton.disabled = false;
      boton.textContent = 'Llamar a Noor';
    }
  }

  function seccionFoto(c) {
    const f = c.foto || {};
    const titulo = f.tipo === 'hojas' ? 'Foto de hojas' : 'Foto de la trampa';
    if (!c.foto_url) return seccion(titulo, h('p', { class: 'vacio' }, 'El caso llegó sin foto.'));
    const cajas = (f.tipo === 'trampa' && c.conteo?.cajas) || [];
    const img = h('img', {
      src: API + c.foto_url, decoding: 'async',
      alt: f.tipo === 'hojas' ? `Hojas por debajo, finca ${c.finca_id}` : `Marco de la trampa, finca ${c.finca_id}`,
      width: f.tipo === 'trampa' ? 1216 : null, height: f.tipo === 'trampa' ? 1216 : null,
    });
    const figura = h('figure', { class: 'foto' }, img);
    if (cajas.length) {
      // Cajas [xc, yc, w, h] normalizadas 0–1 sobre el marco rectificado de 1216×1216 px, que es la foto subida
      const capa = svg('svg', { viewBox: '0 0 1 1', preserveAspectRatio: 'none', 'aria-hidden': 'true' });
      for (const [xc, yc, w, hh] of cajas) {
        capa.append(svg('rect', { x: xc - w / 2, y: yc - hh / 2, width: w, height: hh }));
      }
      capa.style.display = st.cajas ? '' : 'none';
      figura.append(capa);
    }
    const marco = h('div', { class: `foto-marco${st.ampliada ? ' ampliada' : ''}` }, figura);
    img.addEventListener('error', () => marco.replaceChildren(
      h('p', { class: 'vacio' }, `La foto no está en el servidor (${c.foto_url}).`)), { once: true });

    const controles = h('div', { class: 'foto-controles' });
    if (cajas.length) {
      const casilla = h('input', { type: 'checkbox', checked: st.cajas });
      casilla.addEventListener('change', () => {
        st.cajas = casilla.checked;
        const capa = figura.querySelector('svg');
        if (capa) capa.style.display = st.cajas ? '' : 'none';
      });
      controles.append(h('label', {}, casilla, `Mostrar cajas (${cajas.length})`));
    }
    const ampliar = h('button', { type: 'button', class: 'boton chico' }, st.ampliada ? 'Reducir' : 'Ampliar');
    ampliar.addEventListener('click', () => {
      st.ampliada = !st.ampliada;
      marco.classList.toggle('ampliada', st.ampliada);
      ampliar.textContent = st.ampliada ? 'Reducir' : 'Ampliar';
    });
    controles.append(ampliar, h('a', { href: API + c.foto_url, target: '_blank', rel: 'noopener' }, 'Abrir original'));

    const pie = f.tipo === 'hojas'
      ? 'Época de lluvias: la IA no analiza esta foto; es evidencia para que la revises.'
      : `Marco de 10 × 10 cm rectificado a 1216 × 1216 px. Cajas del modelo ${c.conteo?.modelo ?? '—'}.`;
    return seccion(titulo, marco, controles,
      h('p', { class: 'nota' }, pie, ' Calidad: ', f.calidad_ok ? 'aceptada' : h('span', { class: 'alerta' }, 'no aceptada'),
        ` · reintentos: ${f.reintentos ?? 0}.`));
  }

  function seccionConteo(c) {
    const k = c.conteo;
    if (!k) return seccion('Conteo', h('p', { class: 'vacio' }, 'Sin conteo: la foto es de hojas (época de lluvias).'));
    const dif = k.anterior != null ? k.yolo - k.anterior : null;
    const clasico = k.clasico != null
      ? `${k.clasico}${k.yolo ? ` (difiere ${fmtPct.format(Math.abs(k.clasico - k.yolo) / k.yolo)} del YOLO; solo comparación)` : ''}`
      : '—';
    return seccion('Conteo de la trampa', datos([
      ['Conteo YOLO', h('span', { class: 'grande-num' }, String(k.yolo))],
      ['Conteo anterior', k.anterior != null ? String(k.anterior) : 'sin dato'],
      ['Tendencia', `${TENDENCIA[k.tendencia] ?? k.tendencia}${dif != null ? ` (${dif >= 0 ? '+' : ''}${dif})` : ''}`],
      ['Contador clásico', clasico],
      ['Conteo dudoso', k.dudoso ? h('span', { class: 'alerta' }, 'Sí: revisar la foto') : 'No'],
      k.cajas.length !== k.yolo && ['Cajas recibidas', String(k.cajas.length)],
      ['Modelo', h('code', {}, k.modelo)],
    ]), h('p', { class: 'nota' }, 'La trampa mide vuelo, no infestación: solo marca la tendencia (SENASA). La evidencia fuerte son los granos.'));
  }

  function seccionRespuestas(c) {
    const r = c.respuestas || {};
    const pares = [
      r.granos != null && ['Granos (de 20)', GRANOS[r.granos] ?? r.granos],
      r.polvo_naranja != null && ['Polvo naranja', POLVO[r.polvo_naranja] ?? r.polvo_naranja],
    ].filter(Boolean);
    return seccion('Respuestas de Noor', pares.length ? datos(pares) : h('p', { class: 'vacio' }, 'Sin respuestas.'));
  }

  function seccionResultado(c) {
    const r = c.resultado;
    const probs = Object.entries(r.probabilidades || {}).sort((a, b) => b[1] - a[1]);
    const m = st.mensajes?.mensajes?.[r.mensaje];
    const tabla = h('div', { class: 'tabla-env' }, h('table', {},
      h('caption', {}, 'Probabilidades del motor: para el técnico, nunca se muestran a la productora.'),
      h('thead', {}, h('tr', {}, h('th', { scope: 'col' }, 'Causa'), h('th', { scope: 'col', class: 'num' }, 'Probabilidad'))),
      h('tbody', {}, probs.map(([causa, p]) => h('tr', { class: causa === r.causa ? 'principal' : null },
        h('td', {}, CAUSAS[causa] ?? causa, causa === r.causa ? ' (principal)' : ''),
        h('td', { class: 'num' }, fmtPct.format(p)))))));
    const mensaje = h('div', { class: 'mensaje' },
      h('span', {}, 'Lo que escuchó Noor: ', h('code', {}, r.mensaje),
        m?.sintetico ? [' ', h('span', { class: 'sintetico', title: m.nota || '' }, 'AUDIO SINTÉTICO')] : null),
      m ? h('blockquote', {}, `«${m.texto_es}»`) : null,
      h('audio', { controls: true, preload: 'none', src: `${API}/audio/es/${r.mensaje}.mp3` }));
    return seccion('Resultado del motor',
      datos([['Causa principal', r.causa ? (CAUSAS[r.causa] ?? r.causa) : 'Sin causa clara']]), mensaje, tabla);
  }

  function condicion(regla) {
    if ('valor' in regla) {
      if (regla.valor === true) return 'sí';
      if (regla.valor === false) return 'no';
      return `= ${regla.valor}`;
    }
    const { min, max } = regla.rango || {};
    if (min != null && max != null) return `entre ${fmtNum.format(min)} y ${fmtNum.format(max)}`;
    return min != null ? `≥ ${fmtNum.format(min)}` : `≤ ${fmtNum.format(max)}`;
  }

  function seccionReglas(c) {
    const ids = c.resultado.reglas || [];
    if (!ids.length) return seccion('Reglas aplicadas', h('p', { class: 'vacio' }, 'El motor no aplicó ninguna regla.'));
    const mapa = new Map((st.reglas?.reglas || []).map((r) => [r.id, r]));
    const usadas = ids.map((id) => mapa.get(id)).filter(Boolean);
    const conteo = ['oficial', 'literatura', 'supuesto']
      .map((t) => [t, usadas.filter((r) => r.tipo === t).length]).filter(([, n]) => n)
      .map(([t, n]) => `${n} ${t}`).join(' · ');
    const tarjetas = ids.map((id) => {
      const r = mapa.get(id);
      if (!r) {
        return h('li', { class: 'regla' }, h('div', { class: 'regla-cab' }, h('code', {}, id)),
          h('p', { class: 'tenue' }, st.reglas ? `No está en ${st.reglas.origen} (versión ${st.reglas.version}).` : 'Sin datos de reglas.'));
      }
      const lr = Object.entries(r.lr).map(([causa, v]) => `${CAUSAS[causa] ?? causa} ×${fmtNum.format(v)}`).join(' · ');
      return h('li', { class: 'regla' },
        h('div', { class: 'regla-cab' }, h('code', {}, r.id), h('span', { class: `tipo tipo-${r.tipo}` }, r.tipo),
          h('span', {}, `${EVIDENCIAS[r.evidencia] ?? r.evidencia} ${condicion(r)}`)),
        h('p', { class: 'lr' }, r.aplica_como === 'prior' ? 'Multiplica el prior: ' : 'Razón de verosimilitud: ', lr),
        h('p', {}, h('strong', {}, 'Fuente: '), r.fuente),
        r.nota ? h('p', { class: 'tenue' }, r.nota) : null);
    });
    return seccion('Reglas aplicadas',
      h('p', { class: 'nota' }, `${ids.length} ${ids.length === 1 ? 'regla' : 'reglas'}${conteo ? ': ' + conteo : ''}.`),
      h('ol', { class: 'reglas' }, tarjetas),
      st.reglas ? h('p', { class: 'nota' }, `Reglas de ${st.reglas.origen} (versión ${st.reglas.version}).`) : null);
  }

  // ---------- arranque ----------
  ui.actualizar.addEventListener('click', cargar);
  window.addEventListener('hashchange', () => {
    const id = idDelHash();
    if (id && id !== st.sel) seleccionar(id);
  });
  if (API) ui.origen.textContent = ` API: ${API}`;
  cargar();
})();
