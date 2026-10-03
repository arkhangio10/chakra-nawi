// Las tres pantallas de Noor (PLAN §4). Regla de oro: cero cifras y cero porcentajes (lo vigila un test).
import { useEffect, useRef, type ReactNode } from 'react';
import type { Causa, Estado, RespuestaGranos, RespuestaPolvo } from '@chakra/motor';
import type { Caja, Img } from '../vision/tipos';
import { LADO_MARCO } from '../vision/tipos';
import {
  Altavoz, Camara, Clima, Granos, Hoja, HojasEnTarjeta, NoSe, PlantaSana, RecogerGranos, Tarjeta, Tecnico,
} from './Dibujos';

function BotonEscuchar({ alEscuchar, texto = 'Escuchar' }: { alEscuchar: () => void; texto?: string }) {
  return (
    <button type="button" className="boton-escuchar" onClick={alEscuchar}>
      <Altavoz /> <span>{texto}</span>
    </button>
  );
}

// ─── 1. Foto ──────────────────────────────────────────────────────────────────

export function PantallaFoto(p: { tipo: 'trampa' | 'hojas'; otraVez: boolean; alFoto: (f: File) => void; alEscuchar: () => void }) {
  const entrada = useRef<HTMLInputElement>(null);
  return (
    <section className="pantalla">
      <div className="ilustracion">{p.tipo === 'trampa' ? <Tarjeta /> : <HojasEnTarjeta />}</div>
      <p className="subtitulo">
        {p.otraVez ? 'Otra vez, con más luz' : p.tipo === 'trampa' ? 'Que se vean las cuatro esquinas' : 'Hojas volteadas'}
      </p>
      <BotonEscuchar alEscuchar={p.alEscuchar} />
      <button type="button" className="boton-principal" onClick={() => entrada.current?.click()}>
        <Camara /> <span>Tomar foto</span>
      </button>
      <input
        ref={entrada}
        id="foto"
        type="file"
        accept="image/*"
        capture="environment"
        hidden
        onChange={(e) => {
          const f = e.target.files?.[0];
          e.target.value = '';
          if (f) p.alFoto(f);
        }}
      />
    </section>
  );
}

// ─── Procesando: las cajas aparecen sobre cada broca ──────────────────────────

export function PantallaContando({ marco, cajas }: { marco: Img | null; cajas: Caja[] }) {
  const lienzo = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const c = lienzo.current;
    if (!c || !marco) return;
    c.width = marco.width; c.height = marco.height;
    const ctx = c.getContext('2d')!;
    ctx.putImageData(new ImageData(marco.data as Uint8ClampedArray<ArrayBuffer>, marco.width, marco.height), 0, 0);
    ctx.lineWidth = 4;
    ctx.strokeStyle = '#e8710a';
    const s = marco.width / LADO_MARCO;
    for (const k of cajas) ctx.strokeRect((k.cx - k.w / 2 - 3) * s, (k.cy - k.h / 2 - 3) * s, (k.w + 6) * s, (k.h + 6) * s);
  }, [marco, cajas]);
  return (
    <section className="pantalla">
      <div className="ilustracion marco">{marco ? <canvas ref={lienzo} aria-label="Foto de la trampa" /> : <Tarjeta />}</div>
      <p className="subtitulo"><span className="puntos" aria-hidden="true" /> Contando</p>
    </section>
  );
}

// ─── 2. Pregunta ──────────────────────────────────────────────────────────────

interface Opcion<V> { valor: V; dibujo: ReactNode; texto: string }

const OPCIONES_GRANOS: Opcion<RespuestaGranos>[] = [
  { valor: '0', dibujo: <Granos tipo="sano" />, texto: 'Sanos' },
  { valor: '1-2', dibujo: <Granos tipo="pocos" />, texto: 'Pocos con huequito' },
  { valor: '3+', dibujo: <Granos tipo="muchos" />, texto: 'Muchos con huequito' },
  { valor: 'no_se', dibujo: <NoSe />, texto: 'No sé' },
];

const OPCIONES_POLVO: Opcion<RespuestaPolvo>[] = [
  { valor: 'si', dibujo: <Hoja polvo />, texto: 'Sí, hay polvo' },
  { valor: 'no', dibujo: <Hoja polvo={false} />, texto: 'No hay' },
  { valor: 'no_se', dibujo: <NoSe />, texto: 'No sé' },
];

export function PantallaPregunta(p: {
  pregunta: 'granos' | 'polvo_naranja';
  alResponder: (v: string) => void;
  alEscuchar: () => void;
}) {
  const opciones: Opcion<string>[] = p.pregunta === 'granos' ? OPCIONES_GRANOS : OPCIONES_POLVO;
  return (
    <section className="pantalla">
      <p className="subtitulo">{p.pregunta === 'granos' ? '¿Granos con huequito?' : '¿Polvo naranja debajo?'}</p>
      <BotonEscuchar alEscuchar={p.alEscuchar} />
      <div className={`opciones opciones-${opciones.length}`}>
        {opciones.map((o) => (
          <button key={o.valor} type="button" className="opcion" onClick={() => p.alResponder(o.valor)}>
            {o.dibujo}
            <span>{o.texto}</span>
          </button>
        ))}
      </div>
    </section>
  );
}

// ─── 3. Resultado: semáforo + dibujo + voz ────────────────────────────────────

const VISTA: Record<Estado, { clase: string; titulo: string }> = {
  verde: { clase: 'verde', titulo: 'Todo bien' },
  amarillo: { clase: 'amarillo', titulo: 'Atención' },
  tecnico: { clase: 'tecnico', titulo: 'El técnico lo verá' },
  tecnico_urgente: { clase: 'urgente', titulo: 'Aviso al técnico' },
};

function dibujoResultado(estado: Estado, causa: Causa | null) {
  if (estado === 'verde') return <PlantaSana />;
  if (estado === 'tecnico') return <Tecnico />;
  if (estado === 'tecnico_urgente') return <Tecnico urgente />;
  if (causa === 'broca') return <RecogerGranos />;
  if (causa === 'roya') return <Hoja polvo />;
  return <Clima />;
}

const ACCION: Partial<Record<Causa, string>> = {
  broca: 'Recoge los granos caídos',
  roya: 'Puede ser roya',
  clima_floracion: 'Fue el clima',
};

export function PantallaResultado(p: { estado: Estado; causa: Causa | null; alEscuchar: () => void; alTerminar: () => void }) {
  const v = VISTA[p.estado];
  const accion = p.estado === 'amarillo' && p.causa ? ACCION[p.causa] : null;
  return (
    <section className={`pantalla resultado ${v.clase}`}>
      <div className="semaforo" aria-label={v.titulo}>
        <span className="luz" />
        <strong>{v.titulo}</strong>
      </div>
      <div className="ilustracion">{dibujoResultado(p.estado, p.causa)}</div>
      {accion && <p className="subtitulo">{accion}</p>}
      <BotonEscuchar alEscuchar={p.alEscuchar} texto="Escuchar otra vez" />
      <button type="button" className="boton-secundario" onClick={p.alTerminar}>Terminar</button>
    </section>
  );
}
