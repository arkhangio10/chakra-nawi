// Modo técnico (oculto: mantener presionado el logo). Aquí SÍ hay números: es para el técnico y para el demo.
import { useEffect, useState } from 'react';
import type { Resultado, Traza } from '@chakra/motor';
import { FICHAS } from '../datos/contratos';
import type { UmbralesCalidad } from '../vision/calidad';

export interface Ajustes {
  finca: string;
  idioma: 'quz' | 'es';
  mesForzado: number | null;
  api: string;
  modelo: string;
  calidad: UmbralesCalidad;
}

export interface Diagnostico {
  aislado: boolean;
  hilos: number;
  modeloOk: boolean;
  modeloError?: string;
  msCargaModelo?: number;
  msPorMosaico: number[];
  msFoto?: number;
  ultimoConteo?: { yolo: number; clasico: number | null; dudoso: boolean; brillo: number; saturados: number; nitidez: number };
  ultimoResultado?: Resultado & { traza: Traza };
  pendientes: number;
  ultimoEnvio?: string;
}

const MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];
const mb = (b: number) => `${(b / 1048576).toFixed(1)} MB`;

async function tamanoPrecache(): Promise<{ total: number; detalle: [string, number][] }> {
  const detalle: [string, number][] = [];
  for (const nombre of await caches.keys()) {
    const cache = await caches.open(nombre);
    for (const req of await cache.keys()) {
      const r = await cache.match(req);
      if (r) detalle.push([new URL(req.url).pathname, (await r.blob()).size]);
    }
  }
  return { total: detalle.reduce((a, [, s]) => a + s, 0), detalle: detalle.sort((a, b) => b[1] - a[1]) };
}

export function ModoTecnico(p: {
  ajustes: Ajustes;
  diag: Diagnostico;
  modelos: string[];
  alCambiar: (a: Ajustes) => void;
  alEnviar: () => void;
  alBorrarHistorial: () => void;
  alCerrar: () => void;
}) {
  const [a, setA] = useState(p.ajustes);
  const [precache, setPrecache] = useState<{ total: number; detalle: [string, number][] } | null>(null);
  useEffect(() => { tamanoPrecache().then(setPrecache).catch(() => setPrecache(null)); }, []);
  const cambiar = (n: Partial<Ajustes>) => { const nuevo = { ...a, ...n }; setA(nuevo); p.alCambiar(nuevo); };
  const d = p.diag;
  const r = d.ultimoResultado;

  return (
    <div className="tecnico-fondo" role="dialog" aria-modal="true" aria-labelledby="titulo-tecnico">
      <div className="tecnico">
        <header>
          <h2 id="titulo-tecnico">Modo técnico</h2>
          <button type="button" onClick={p.alCerrar}>Cerrar</button>
        </header>

        <fieldset>
          <legend>Inscripción y demo</legend>
          <label htmlFor="t-finca">Finca</label>
          <select id="t-finca" value={a.finca} onChange={(e) => cambiar({ finca: e.target.value })}>
            {Object.values(FICHAS).map((f) => <option key={f.finca_id} value={f.finca_id}>{f.finca_id} · {f.altitud_m} m</option>)}
          </select>
          <label htmlFor="t-idioma">Idioma de la voz</label>
          <select id="t-idioma" value={a.idioma} onChange={(e) => cambiar({ idioma: e.target.value as Ajustes['idioma'] })}>
            <option value="quz">Quechua cusqueño (respaldo: castellano)</option>
            <option value="es">Castellano</option>
          </select>
          <label htmlFor="t-mes">Mes del triaje</label>
          <select id="t-mes" value={a.mesForzado ?? ''} onChange={(e) => cambiar({ mesForzado: e.target.value ? Number(e.target.value) : null })}>
            <option value="">Fecha real del teléfono</option>
            {MESES.map((m, i) => <option key={m} value={i + 1}>Caso de {m}</option>)}
          </select>
        </fieldset>

        <fieldset>
          <legend>Conexión</legend>
          <label htmlFor="t-api">Dirección de la API</label>
          <input id="t-api" value={a.api} onChange={(e) => cambiar({ api: e.target.value })} />
          <p>Casos en espera de señal: <b>{d.pendientes}</b>{d.ultimoEnvio ? ` · ${d.ultimoEnvio}` : ''}</p>
          <button type="button" onClick={p.alEnviar}>Enviar ahora</button>
        </fieldset>

        <fieldset>
          <legend>Modelo y rendimiento</legend>
          <label htmlFor="t-modelo">Modelo</label>
          <select id="t-modelo" value={a.modelo} onChange={(e) => cambiar({ modelo: e.target.value })}>
            {[...new Set([a.modelo, ...p.modelos])].map((m) => <option key={m} value={m}>{m}</option>)}
          </select>
          <ul className="datos">
            <li>Modelo: {d.modeloOk ? `cargado en ${Math.round(d.msCargaModelo ?? 0)} ms` : `no disponible (${d.modeloError ?? '—'}); se usa el contador clásico`}</li>
            <li>Aislamiento de origen cruzado: {d.aislado ? 'sí' : 'no'} · hilos WASM: {d.hilos}</li>
            <li>Foto → marco rectificado: {d.msFoto ? `${Math.round(d.msFoto)} ms` : '—'}</li>
            <li>Ms por mosaico: {d.msPorMosaico.length ? d.msPorMosaico.map((m) => Math.round(m)).join(' · ') : '—'}
              {d.msPorMosaico.length ? ` (total ${Math.round(d.msPorMosaico.reduce((x, y) => x + y, 0))} ms)` : ''}</li>
            <li>Tamaño total guardado en el teléfono: {precache ? mb(precache.total) : '—'}</li>
          </ul>
          {precache && (
            <details>
              <summary>Detalle del precache</summary>
              <ul className="datos">{precache.detalle.slice(0, 8).map(([ruta, s]) => <li key={ruta}>{ruta}: {mb(s)}</li>)}</ul>
            </details>
          )}
        </fieldset>

        <fieldset>
          <legend>Calidad de la foto</legend>
          {(['brilloMin', 'saturadosMax', 'nitidezMin'] as const).map((k) => (
            <div key={k} className="fila">
              <label htmlFor={`t-${k}`}>{{ brilloMin: 'Brillo medio mínimo', saturadosMax: 'Fracción máx. de píxeles quemados', nitidezMin: 'Nitidez mínima' }[k]}</label>
              <input id={`t-${k}`} type="number" step="any" value={a.calidad[k]} onChange={(e) => cambiar({ calidad: { ...a.calidad, [k]: Number(e.target.value) } })} />
            </div>
          ))}
          {d.ultimoConteo && (
            <p>Última foto: brillo {Math.round(d.ultimoConteo.brillo)}, quemados {Math.round(d.ultimoConteo.saturados * 100)} %, nitidez {Math.round(d.ultimoConteo.nitidez)} ·
              YOLO {d.ultimoConteo.yolo}, clásico {d.ultimoConteo.clasico ?? '—'}{d.ultimoConteo.dudoso ? ' · DUDOSO' : ''}</p>
          )}
          <button type="button" onClick={p.alBorrarHistorial}>Borrar conteos anteriores de esta finca</button>
        </fieldset>

        {r && (
          <fieldset>
            <legend>Último triaje</legend>
            <p><b>{r.estado}</b> · causa {r.causa ?? '—'} · {r.traza.temporada}{r.traza.fruto_atacable ? '' : ' · sin fruto atacable'} · trampa {r.traza.tendencia}</p>
            <p>{r.traza.motivo}</p>
            <ul className="datos">
              {Object.entries(r.probabilidades).sort((x, y) => y[1] - x[1]).map(([c, v]) => <li key={c}>{c}: {(v * 100).toFixed(0)} %</li>)}
            </ul>
            <p>Reglas: {r.reglas.join(', ') || '—'}</p>
          </fieldset>
        )}
      </div>
    </div>
  );
}
