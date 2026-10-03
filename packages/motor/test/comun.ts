import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';
import type { Config, Entrada, Ficha, Reglas } from '../src';

const RAIZ = resolve(dirname(fileURLToPath(import.meta.url)), '../../..');
export const leer = <T>(ruta: string): T => JSON.parse(readFileSync(resolve(RAIZ, ruta), 'utf-8')) as T;

export const reglas = leer<Reglas>('contracts/rules.example.json');
export const config = leer<Config>('contracts/config.example.json');

/** Ficha con clima "normal" (anomalías en 0): las reglas de clima no se activan y el test prueba solo la lógica. */
export const fichaNeutra: Ficha = {
  version: 'test',
  finca_id: 'LC-001',
  clima: {
    lluvia_floracion_anom_pct: 0,
    dias_lluvia_nov_abr_anom: 0,
    dias_temp_roya_90d_anom: 0,
    tmax_floracion_anom_c: 0,
  },
  registro: { edad_mas_20_sin_recepa: false, cosecha_alta_ano_pasado: false },
  alertas: [],
};

export function entrada(parcial: Partial<Entrada> & { mes: number }): Entrada {
  return {
    fecha: `2026-${String(parcial.mes).padStart(2, '0')}-15`,
    ficha: fichaNeutra,
    conteo: null,
    respuestas: {},
    ...parcial,
  };
}
