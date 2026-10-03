// Todo lo que el triaje necesita viaja DENTRO de la app (se precachea): reglas, config, fichas y audios.
import type { Config, Ficha, Reglas } from '@chakra/motor';
import reglasJson from '../../../../contracts/rules.example.json';
import configJson from '../../../../contracts/config.example.json';
import mensajesEjemplo from '../../../../contracts/mensajes.example.json';

export const REGLAS = reglasJson as unknown as Reglas;
export const CONFIG = configJson as unknown as Config;

const fichasMod = import.meta.glob<Ficha>('../../../../fichas/*.json', { eager: true, import: 'default' });
export const FICHAS: Record<string, Ficha> = Object.fromEntries(Object.values(fichasMod).map((f) => [f.finca_id, f]));

export interface Mensaje {
  uso: string;
  archivos: Record<string, string>;
  texto_es: string;
  texto_quz: string;
  revisado_por: string;
  sintetico: boolean;
}

// audio/mensajes.json es el catálogo real (lo genera audio/); si todavía no existe, se usa el ejemplo del contrato.
const real = import.meta.glob<{ mensajes: Record<string, Mensaje> }>('../../../../audio/mensajes.json', { eager: true, import: 'default' });
export const MENSAJES: Record<string, Mensaje> =
  Object.values(real)[0]?.mensajes ?? (mensajesEjemplo as unknown as { mensajes: Record<string, Mensaje> }).mensajes;

// Audios .opus que existan en el repositorio: audio/{es,quz}/CODIGO.opus → URL del build.
const urls = import.meta.glob<string>('../../../../audio/*/*.opus', { eager: true, query: '?url', import: 'default' });
const AUDIOS: Record<string, string> = Object.fromEntries(
  Object.entries(urls).map(([ruta, url]) => {
    const m = ruta.match(/audio\/(\w+)\/(\w+)\.opus$/)!;
    return [`${m[1]}/${m[2]}`, url];
  }),
);

/** URL del audio en el idioma pedido; si falta en quechua, cae al castellano. */
export function urlAudio(codigo: string, idioma: string): { url: string; idioma: string } | null {
  if (AUDIOS[`${idioma}/${codigo}`]) return { url: AUDIOS[`${idioma}/${codigo}`], idioma };
  if (AUDIOS[`es/${codigo}`]) return { url: AUDIOS[`es/${codigo}`], idioma: 'es' };
  return null;
}

export const HAY_AUDIOS = Object.keys(AUDIOS).length > 0;
export const VERSION_APP = '0.1.0';
