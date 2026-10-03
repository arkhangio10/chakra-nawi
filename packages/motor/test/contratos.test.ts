// El motor contra los contratos reales: recorre todos los meses, respuestas, tendencias y fichas,
// y exige que cada resultado sea válido según caso.schema.json. También informa qué estados son alcanzables.
import { readdirSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import Ajv2020 from 'ajv/dist/2020';
import addFormats from 'ajv-formats';
import { CAUSAS, evaluar, type Entrada, type Estado, type Ficha, type RespuestaGranos, type RespuestaPolvo } from '../src';
import { config, entrada, fichaNeutra, leer, reglas } from './comun';

const ajv = new Ajv2020({ allErrors: true, strict: false });
addFormats(ajv);
for (const n of ['caso', 'rules', 'config']) ajv.addSchema(leer(`contracts/${n}.schema.json`));
const BASE = 'https://chakra-nawi.dev/contracts';
const validarResultado = ajv.compile({ $ref: `${BASE}/caso.schema.json#/properties/resultado` });

const fichasReales = readdirSync(new URL('../../../fichas', import.meta.url))
  .filter((f) => f.endsWith('.json'))
  .map((f) => leer<Ficha>(`fichas/${f}`));

const GRANOS: (RespuestaGranos | undefined)[] = [undefined, '0', '1-2', '3+', 'no_se'];
const POLVO: (RespuestaPolvo | undefined)[] = [undefined, 'si', 'no', 'no_se'];
const CONTEOS: Entrada['conteo'][] = [
  null,
  { yolo: 40, anterior: null, dudoso: false },
  { yolo: 143, anterior: 61, dudoso: false },
  { yolo: 30, anterior: 61, dudoso: false },
  { yolo: 200, anterior: 60, dudoso: true },
];

function* escenarios() {
  for (const ficha of [fichaNeutra, ...fichasReales])
    for (let mes = 1; mes <= 12; mes++)
      for (const granos of GRANOS)
        for (const polvo_naranja of POLVO)
          for (const conteo of CONTEOS)
            yield entrada({ mes, ficha, conteo, respuestas: { ...(granos && { granos }), ...(polvo_naranja && { polvo_naranja }) } });
}

describe('contratos', () => {
  it('rules.example.json y config.example.json cumplen sus esquemas', () => {
    expect(ajv.validate(`${BASE}/rules.schema.json`, reglas), JSON.stringify(ajv.errors)).toBe(true);
    expect(ajv.validate(`${BASE}/config.schema.json`, config), JSON.stringify(ajv.errors)).toBe(true);
  });

  it('cada resultado es válido, suma 1 y respeta los invariantes de PLAN §5.2', () => {
    const conteo: Record<Estado, number> = { verde: 0, amarillo: 0, tecnico: 0, tecnico_urgente: 0 };
    let n = 0;
    for (const e of escenarios()) {
      const { traza, ...resultado } = evaluar(e, reglas, config);
      n++;
      conteo[resultado.estado]++;
      expect(validarResultado(resultado), JSON.stringify(validarResultado.errors)).toBe(true);
      const suma = CAUSAS.reduce((a, c) => a + resultado.probabilidades[c], 0);
      expect(Math.abs(suma - 1)).toBeLessThan(1e-9);
      if (e.respuestas.granos === '3+' && config.fruto_atacable_por_mes[e.mes - 1]) expect(resultado.estado).toBe('tecnico_urgente');
      if (e.conteo?.dudoso && resultado.estado !== 'tecnico_urgente') expect(resultado.estado).toBe('tecnico');
      if (resultado.estado === 'verde') expect(e.respuestas.granos !== '0' || e.respuestas.polvo_naranja === 'no' || traza.tendencia === 'igual' || traza.tendencia === 'baja').toBe(true);
    }
    console.info(`escenarios: ${n}`, conteo);
    for (const estado of Object.keys(conteo) as Estado[]) expect(conteo[estado], `estado inalcanzable: ${estado}`).toBeGreaterThan(0);
  });
});
