// Voz: audios grabados (audio/{quz,es}/CODIGO.opus). Si no hay archivo, la voz del sistema lee el texto en castellano.
import { MENSAJES, urlAudio } from './datos/contratos';

let actual: HTMLAudioElement | null = null;
let alTerminar: (() => void) | null = null;

// Quién quiere saber si la voz está sonando (el botón de voz anima sus ondas mientras habla).
const oyentes = new Set<(hablando: boolean) => void>();
let hablando = false;
let turno = 0; // un audio viejo que termina tarde no apaga las ondas del nuevo
function marcar(h: boolean) {
  if (h === hablando) return;
  hablando = h;
  for (const f of oyentes) f(h);
}
export function suscribirVoz(f: (hablando: boolean) => void): () => void {
  oyentes.add(f);
  f(hablando);
  return () => { oyentes.delete(f); };
}

export function detener() {
  actual?.pause();
  actual = null;
  if ('speechSynthesis' in globalThis) speechSynthesis.cancel();
  marcar(false);
  alTerminar?.();
  alTerminar = null;
}

/** Reproduce un mensaje. Resuelve al terminar (o enseguida si el navegador bloquea el autoplay). */
export function reproducir(codigo: string, idioma: string, repetir = false): Promise<void> {
  detener();
  const mio = ++turno;
  const empezo = () => { if (mio === turno) marcar(true); };
  return new Promise((fin) => {
    const listo = () => { if (mio === turno) marcar(false); fin(); };
    alTerminar = listo;
    const fuente = urlAudio(codigo, idioma);
    if (fuente) {
      const a = new Audio(fuente.url);
      actual = a;
      a.loop = repetir;
      a.onended = () => { if (actual === a) { actual = null; listo(); } };
      a.play().then(empezo, () => listo());
      return;
    }
    const texto = MENSAJES[codigo]?.texto_es;
    if (texto && 'speechSynthesis' in globalThis) {
      const u = new SpeechSynthesisUtterance(texto);
      u.lang = 'es-PE';
      u.rate = 0.9;
      u.onstart = empezo;
      u.onend = () => listo();
      u.onerror = () => listo();
      speechSynthesis.speak(u);
      return;
    }
    listo();
  });
}
