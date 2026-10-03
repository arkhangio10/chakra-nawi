// Voz: audios grabados (audio/{quz,es}/CODIGO.opus). Si no hay archivo, la voz del sistema lee el texto en castellano.
import { MENSAJES, urlAudio } from './datos/contratos';

let actual: HTMLAudioElement | null = null;
let alTerminar: (() => void) | null = null;

export function detener() {
  actual?.pause();
  actual = null;
  if ('speechSynthesis' in globalThis) speechSynthesis.cancel();
  alTerminar?.();
  alTerminar = null;
}

/** Reproduce un mensaje. Resuelve al terminar (o enseguida si el navegador bloquea el autoplay). */
export function reproducir(codigo: string, idioma: string, repetir = false): Promise<void> {
  detener();
  return new Promise((listo) => {
    alTerminar = listo;
    const fuente = urlAudio(codigo, idioma);
    if (fuente) {
      const a = new Audio(fuente.url);
      actual = a;
      a.loop = repetir;
      a.onended = () => { if (actual === a) { actual = null; listo(); } };
      a.play().catch(() => listo());
      return;
    }
    const texto = MENSAJES[codigo]?.texto_es;
    if (texto && 'speechSynthesis' in globalThis) {
      const u = new SpeechSynthesisUtterance(texto);
      u.lang = 'es-PE';
      u.rate = 0.9;
      u.onend = () => listo();
      u.onerror = () => listo();
      speechSynthesis.speak(u);
      return;
    }
    listo();
  });
}
