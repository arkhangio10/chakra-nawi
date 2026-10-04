// Las tres pantallas de Noor (PLAN §4). Regla de oro: cero cifras y cero porcentajes (lo vigila un test).
import { useEffect, useRef, useState, type ReactNode } from 'react';
import type { Causa, Estado, RespuestaGranos, RespuestaPolvo } from '@chakra/motor';
import type { Caja, Img } from '../vision/tipos';
import { LADO_MARCO } from '../vision/tipos';
import { suscribirVoz } from '../audio';
import { useTextos, type Textos } from '../textos';
import {
  Altavoz, Camara, Clima, Granos, Hoja, HojasEnTarjeta, NoSe, Nube, PlantaSana, RecogerGranos, Tarjeta, Tecnico, Visto,
} from './Dibujos';

/** true mientras la voz suena: las ondas del altavoz se mueven y la frase se resalta. */
function useHablando() {
  const [hablando, setHablando] = useState(false);
  useEffect(() => suscribirVoz(setHablando), []);
  return hablando;
}

/** El texto de la pantalla con su botón de voz al lado: la voz acompaña al texto, no compite con la acción. */
function TituloConVoz({ texto, alEscuchar, clase = '' }: { texto: string; alEscuchar: () => void; clase?: string }) {
  const hablando = useHablando();
  const t = useTextos();
  return (
    <div className={`titulo-voz ${clase} ${hablando ? 'hablando' : ''}`}>
      <p className="subtitulo">{texto}</p>
      <button type="button" className="boton-voz" onClick={alEscuchar} aria-label={t.escuchar}>
        <Altavoz />
      </button>
    </div>
  );
}

// ─── 1. Foto ──────────────────────────────────────────────────────────────────

export function PantallaFoto(p: { tipo: 'trampa' | 'hojas'; otraVez: boolean; alFoto: (f: File) => void; alEscuchar: () => void }) {
  const entrada = useRef<HTMLInputElement>(null);
  const t = useTextos();
  return (
    <section className="pantalla">
      <div className="ilustracion">{p.tipo === 'trampa' ? <Tarjeta /> : <HojasEnTarjeta />}</div>
      <TituloConVoz
        texto={p.otraVez ? t.fotoOtraVez : p.tipo === 'trampa' ? t.fotoTrampa : t.fotoHojas}
        alEscuchar={p.alEscuchar}
      />
      <div className="acciones">
        <button type="button" className="boton-principal" onClick={() => entrada.current?.click()}>
          <Camara /> <span>{t.tomarFoto}</span>
        </button>
      </div>
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
  const t = useTextos();
  return (
    <section className="pantalla">
      <div className="ilustracion marco">{marco ? <canvas ref={lienzo} aria-label="Foto de la trampa" /> : <Tarjeta />}</div>
      <p className="subtitulo"><span className="puntos" aria-hidden="true" /> {t.contando}</p>
    </section>
  );
}

// ─── 2. Pregunta ──────────────────────────────────────────────────────────────

interface Opcion<V> { valor: V; dibujo: ReactNode; texto: string }

const opcionesGranos = (t: Textos): Opcion<RespuestaGranos>[] => [
  { valor: '0', dibujo: <Granos tipo="sano" />, texto: t.sanos },
  { valor: '1-2', dibujo: <Granos tipo="pocos" />, texto: t.pocos },
  { valor: '3+', dibujo: <Granos tipo="muchos" />, texto: t.muchos },
  { valor: 'no_se', dibujo: <NoSe />, texto: t.noSe },
];

const opcionesPolvo = (t: Textos): Opcion<RespuestaPolvo>[] => [
  { valor: 'si', dibujo: <Hoja polvo />, texto: t.siPolvo },
  { valor: 'no', dibujo: <Hoja polvo={false} />, texto: t.noPolvo },
  { valor: 'no_se', dibujo: <NoSe />, texto: t.noSe },
];

export function PantallaPregunta(p: {
  pregunta: 'granos' | 'polvo_naranja';
  alResponder: (v: string) => void;
  alEscuchar: () => void;
}) {
  const t = useTextos();
  const opciones: Opcion<string>[] = p.pregunta === 'granos' ? opcionesGranos(t) : opcionesPolvo(t);
  return (
    <section className="pantalla">
      <TituloConVoz texto={p.pregunta === 'granos' ? t.preguntaGranos : t.preguntaPolvo} alEscuchar={p.alEscuchar} />
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

const VISTA: Record<Estado, { clase: string; titulo: keyof Textos }> = {
  verde: { clase: 'verde', titulo: 'estadoVerde' },
  amarillo: { clase: 'amarillo', titulo: 'estadoAmarillo' },
  tecnico: { clase: 'tecnico', titulo: 'estadoTecnico' },
  tecnico_urgente: { clase: 'urgente', titulo: 'estadoUrgente' },
};

function dibujoResultado(estado: Estado, causa: Causa | null) {
  if (estado === 'verde') return <PlantaSana />;
  if (estado === 'tecnico') return <Tecnico />;
  // Urgente: lo que Noor hace mientras tanto es lo principal; que el técnico ya sabe lo dice la fila del aviso.
  if (estado === 'tecnico_urgente' || causa === 'broca') return <RecogerGranos />;
  if (causa === 'roya') return <Hoja polvo />;
  return <Clima />;
}

const ACCION: Partial<Record<Causa, keyof Textos>> = {
  broca: 'accionBroca',
  roya: 'accionRoya',
  clima_floracion: 'accionClima',
};

/** Lo que Noor tiene que hacer, como titular. Sin acción concreta, una frase que cierra (lo mismo que dice la voz). */
function frase(t: Textos, estado: Estado, causa: Causa | null): string {
  if (estado === 'amarillo' && causa && ACCION[causa]) return t[ACCION[causa]!];
  if (estado === 'verde') return t.accionVerde;
  if (estado === 'tecnico_urgente') return t.accionBroca;
  return t.accionTecnico;
}

/** Hay algo que Noor puede hacer con sus manos: recoger los granos caídos. */
const hayTarea = (estado: Estado, causa: Causa | null) => estado === 'tecnico_urgente' || (estado === 'amarillo' && causa === 'broca');
/** El caso va al técnico: técnico, urgente y posible roya (la voz dice "ya le mandé tu caso"). */
const vaAlTecnico = (estado: Estado, causa: Causa | null) => estado === 'tecnico' || estado === 'tecnico_urgente' || causa === 'roya';

/** Si el caso ya le llegó al técnico o sigue guardado en el teléfono hasta que haya señal. */
function AvisoTecnico({ enviado }: { enviado: boolean }) {
  const t = useTextos();
  return (
    <p className={`aviso-tecnico ${enviado ? 'enviado' : ''}`} role="status">
      <Nube esperando={!enviado} />
      <span>{enviado ? t.llegoTecnico : t.guardadoSinSenal}</span>
    </p>
  );
}

export function PantallaResultado(p: {
  estado: Estado; causa: Causa | null; enviado?: boolean; alEscuchar: () => void; alTerminar: () => void;
}) {
  const t = useTextos();
  const v = VISTA[p.estado];
  const titulo = t[v.titulo];
  const [hecho, setHecho] = useState(false);
  const tarea = hayTarea(p.estado, p.causa);
  return (
    <section className={`pantalla resultado ${v.clase}`}>
      <div className="tarjeta-resultado">
        <div className="semaforo" aria-label={titulo}>
          <span className="luz" aria-hidden="true" />
          <strong>{titulo}</strong>
        </div>
        <div className="ilustracion">{dibujoResultado(p.estado, p.causa)}</div>
        <TituloConVoz texto={frase(t, p.estado, p.causa)} alEscuchar={p.alEscuchar} clase="accion" />
      </div>
      {vaAlTecnico(p.estado, p.causa) && <AvisoTecnico enviado={p.enviado ?? false} />}
      <div className="acciones">
        {tarea && (hecho
          ? <p className="tarea-hecha" role="status"><Visto /> <span>{t.muyBien}</span></p>
          : <button type="button" className="boton-principal" onClick={() => setHecho(true)}><Visto /> <span>{t.yaLoHice}</span></button>)}
        <button type="button" className="boton-secundario" onClick={p.alTerminar}>{t.terminar}</button>
      </div>
    </section>
  );
}
