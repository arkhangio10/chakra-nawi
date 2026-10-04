// Sensibilidad del motor a la magnitud de los LR (PLAN §10, prueba 1).
//
//   npx vitest run validacion/sensibilidad.test.ts      (desde la raíz del repo)
//
// Pregunta: si los LR que pusimos están errados en ±50%, ¿cambia el color que oye Noor?
// 1. Uno a la vez: cada LR de cada regla ×1,5 y ×0,5.
// 2. Todos a la vez: cada LR multiplicado por un factor aleatorio en [0,5; 1,5] (Monte Carlo, semilla fija).
// Escribe validacion/resultados/sensibilidad.json y sensibilidad.md. No lo corre `npm test`.

import { mkdirSync, readFileSync, readdirSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { expect, test } from 'vitest';
import {
  evaluar, temporadaDeMes,
  type Config, type Entrada, type EntradaConteo, type Ficha, type Reglas, type RespuestaGranos, type RespuestaPolvo,
} from '../packages/motor/src';

const RAIZ = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const leer = <T>(ruta: string): T => JSON.parse(readFileSync(resolve(RAIZ, ruta), 'utf-8')) as T;

const reglas = leer<Reglas>('contracts/rules.example.json');
const config = leer<Config>('contracts/config.example.json');
const fichas = readdirSync(resolve(RAIZ, 'fichas')).filter((f) => f.endsWith('.json')).map((f) => leer<Ficha>(`fichas/${f}`));

const FACTOR = 0.5;
const SORTEOS = 300;

// ---------- Escenarios: todo lo que la app puede mandarle al motor ----------

const CONTEOS: Record<string, EntradaConteo> = {
  sube: { yolo: 40, anterior: 20, dudoso: false },
  igual: { yolo: 20, anterior: 20, dudoso: false },
  baja: { yolo: 10, anterior: 30, dudoso: false },
  sin_anterior: { yolo: 20, anterior: null, dudoso: false },
};
const GRANOS: (RespuestaGranos | undefined)[] = ['0', '1-2', '3+', 'no_se', undefined];
const POLVO: (RespuestaPolvo | undefined)[] = ['si', 'no', 'no_se', undefined];

interface Escenario { id: string; entrada: Entrada }

function escenarios(): Escenario[] {
  const lista: Escenario[] = [];
  for (const base of fichas) {
    for (const edad of [false, true]) {
      const ficha: Ficha = { ...base, registro: { ...base.registro, edad_mas_20_sin_recepa: edad } };
      for (let mes = 1; mes <= 12; mes++) {
        const temp = config.temporadas[temporadaDeMes(mes, config)];
        // Época seca: foto de la trampa. Lluvias: foto de hojas, sin conteo.
        const conteos = temp.foto === 'trampa' ? Object.entries(CONTEOS) : [['hojas', null] as const];
        for (const [nombreConteo, conteo] of conteos) {
          for (const granos of GRANOS) {
            for (const polvo of POLVO) {
              // La pregunta principal de la época siempre se responde; la otra puede no hacerse.
              if (temp.pregunta_principal === 'granos' && granos === undefined) continue;
              if (temp.pregunta_principal === 'polvo_naranja' && polvo === undefined) continue;
              lista.push({
                id: `${ficha.finca_id}|edad=${edad}|mes=${mes}|${nombreConteo}|granos=${granos ?? '-'}|polvo=${polvo ?? '-'}`,
                entrada: {
                  mes, fecha: `2026-${String(mes).padStart(2, '0')}-15`, ficha,
                  conteo: conteo ? { ...conteo } : null,
                  respuestas: { ...(granos && { granos }), ...(polvo && { polvo_naranja: polvo }) },
                },
              });
            }
          }
        }
      }
    }
  }
  return lista;
}

// ---------- Perturbaciones ----------

function conLr(transformar: (lr: number, reglaId: string) => number): Reglas {
  return {
    ...reglas,
    reglas: reglas.reglas.map((r) => ({
      ...r,
      lr: Object.fromEntries(Object.entries(r.lr).map(([c, lr]) => [c, transformar(lr as number, r.id)])),
    })),
  };
}

/** Generador con semilla (mulberry32): mismo resultado en cada corrida. */
function azar(semilla: number) {
  return () => {
    semilla = (semilla + 0x6d2b79f5) | 0;
    let t = Math.imul(semilla ^ (semilla >>> 15), 1 | semilla);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const pct = (n: number, d: number) => (d === 0 ? 0 : Math.round((1000 * n) / d) / 10);
const fmt = (x: number) => `${String(x).replace('.', ',')} %`;

test('sensibilidad de los LR ±50%', { timeout: 120_000 }, () => {
  const lista = escenarios();
  const base = lista.map((e) => evaluar(e.entrada, reglas, config));
  // El urgente (granos 3+ con fruto atacable) no depende de ningún LR: se reporta aparte.
  const dependeDeLr = base.map((r) => r.traza.motivo !== 'granos 3+ con fruto atacable');
  const nLr = dependeDeLr.filter(Boolean).length;

  // 1. Uno a la vez
  const unoAUno = reglas.reglas.map((regla) => {
    const fila: Record<string, unknown> = { regla: regla.id, tipo: regla.tipo, evidencia: regla.evidencia };
    for (const [nombre, f] of [['x1.5', 1 + FACTOR], ['x0.5', 1 - FACTOR]] as const) {
      const pert = conLr((lr, id) => (id === regla.id ? lr * f : lr));
      let color = 0, causa = 0;
      const ejemplos: string[] = [];
      lista.forEach((e, i) => {
        const r = evaluar(e.entrada, pert, config);
        if (r.estado !== base[i].estado) {
          color++;
          if (ejemplos.length < 3) ejemplos.push(`${e.id}: ${base[i].estado} → ${r.estado}`);
        }
        if (r.causa !== base[i].causa) causa++;
      });
      fila[nombre] = { cambia_color: color, cambia_color_pct: pct(color, nLr), cambia_causa: causa, ejemplos };
    }
    return fila;
  });

  // 2. Todos a la vez (Monte Carlo)
  const rnd = azar(20261004);
  const cambiosPorEscenario = new Array(lista.length).fill(0);
  const transiciones: Record<string, number> = {};
  for (let s = 0; s < SORTEOS; s++) {
    const factores = new Map<string, number>();
    const pert = conLr((lr, id) => {
      const k = `${id}`;
      if (!factores.has(k)) factores.set(k, 1 - FACTOR + 2 * FACTOR * rnd());
      return lr * factores.get(k)!;
    });
    lista.forEach((e, i) => {
      const r = evaluar(e.entrada, pert, config);
      if (r.estado !== base[i].estado) {
        cambiosPorEscenario[i]++;
        const t = `${base[i].estado} → ${r.estado}`;
        transiciones[t] = (transiciones[t] ?? 0) + 1;
      }
    });
  }
  const idx = lista.map((_, i) => i).filter((i) => dependeDeLr[i]);
  const nunca = idx.filter((i) => cambiosPorEscenario[i] === 0).length;
  const estable95 = idx.filter((i) => cambiosPorEscenario[i] <= 0.05 * SORTEOS).length;
  const fragiles = idx
    .filter((i) => cambiosPorEscenario[i] > 0.05 * SORTEOS)
    .sort((a, b) => cambiosPorEscenario[b] - cambiosPorEscenario[a]);

  // Fragilidad por estado de partida
  const porEstado: Record<string, { n: number; estables95: number }> = {};
  for (const i of idx) {
    const s = (porEstado[base[i].estado] ??= { n: 0, estables95: 0 });
    s.n++;
    if (cambiosPorEscenario[i] <= 0.05 * SORTEOS) s.estables95++;
  }

  const resumen = {
    generado: new Date().toISOString().slice(0, 10),
    reglas: reglas.version, config: config.version,
    escenarios: lista.length,
    escenarios_que_dependen_de_lr: nLr,
    urgentes_por_regla_fija: lista.length - nLr,
    perturbacion: `cada LR × factor en [${1 - FACTOR}; ${1 + FACTOR}]`,
    sorteos: SORTEOS,
    todos_a_la_vez: {
      nunca_cambia_color_pct: pct(nunca, nLr),
      estable_en_95pct_de_sorteos_pct: pct(estable95, nLr),
      por_estado_base: Object.fromEntries(Object.entries(porEstado).map(([k, v]) => [k, { n: v.n, estables95_pct: pct(v.estables95, v.n) }])),
      transiciones_mas_frecuentes: Object.entries(transiciones).sort((a, b) => b[1] - a[1]).slice(0, 6)
        .map(([t, n]) => ({ transicion: t, pct_de_evaluaciones: pct(n, nLr * SORTEOS) })),
      escenarios_mas_fragiles: fragiles.slice(0, 10).map((i) => ({ escenario: lista[i].id, base: base[i].estado, cambia_en_pct_de_sorteos: pct(cambiosPorEscenario[i], SORTEOS) })),
    },
    uno_a_la_vez: unoAUno,
    limites: [
      'Los escenarios son todas las combinaciones de entradas, no casos reales: cada combinación pesa lo mismo.',
      'alertas_activas.json está vacío: R-ALERTA-01/02 no se activan en ningún escenario.',
      'Las 5 fichas comparten la celda de NASA POWER: el clima casi no varía entre fincas.',
      'No se perturban los umbrales de decisión ni los pesos por época, solo la magnitud de los LR.',
    ],
  };

  const dir = resolve(RAIZ, 'validacion/resultados');
  mkdirSync(dir, { recursive: true });
  writeFileSync(resolve(dir, 'sensibilidad.json'), JSON.stringify(resumen, null, 2) + '\n');

  const filas = unoAUno.map((f) => {
    const a = f['x1.5'] as { cambia_color_pct: number }, b = f['x0.5'] as { cambia_color_pct: number };
    return `| ${f.regla} | ${f.tipo} | ${fmt(a.cambia_color_pct)} | ${fmt(b.cambia_color_pct)} |`;
  });
  const md = [
    '# Sensibilidad de los LR ±50% (PLAN §10, prueba 1)',
    '',
    `Generado con \`npx vitest run validacion/sensibilidad.test.ts\` · reglas ${reglas.version} · config ${config.version}.`,
    '',
    `**${lista.length} escenarios**: las 5 fichas × con y sin plantas viejas × 12 meses × tendencia de la trampa (sube, igual, baja, sin anterior; en lluvias, foto de hojas) × todas las respuestas posibles. ` +
      `${lista.length - nLr} son urgentes por la regla fija "granos 3+ con fruto atacable", que no depende de ningún LR; los porcentajes se calculan sobre los otros **${nLr}**.`,
    '',
    `## Todos los LR a la vez (${SORTEOS} sorteos, cada LR × factor aleatorio en [0,5; 1,5])`,
    '',
    `- **${fmt(pct(estable95, nLr))}** de los escenarios mantienen su color en al menos el 95 % de los sorteos.`,
    `- **${fmt(pct(nunca, nLr))}** no cambian de color en ningún sorteo.`,
    '',
    '| Color sin perturbar | Escenarios | Estables (≥ 95 % de sorteos) |',
    '|---|---|---|',
    ...Object.entries(resumen.todos_a_la_vez.por_estado_base).map(([k, v]) => `| ${k} | ${v.n} | ${fmt(v.estables95_pct)} |`),
    '',
    'Cambios más frecuentes:',
    '',
    ...resumen.todos_a_la_vez.transiciones_mas_frecuentes.map((t) => `- ${t.transicion}: ${fmt(t.pct_de_evaluaciones)} de las evaluaciones`),
    '',
    '## Una regla a la vez',
    '',
    '% de escenarios que cambian de color al multiplicar solo esa regla.',
    '',
    '| Regla | Tipo | LR × 1,5 | LR × 0,5 |',
    '|---|---|---|---|',
    ...filas,
    '',
    '## Límites',
    '',
    ...resumen.limites.map((l) => `- ${l}`),
    '',
    'Detalle (escenarios más frágiles y ejemplos por regla): `sensibilidad.json`.',
    '',
  ].join('\n');
  writeFileSync(resolve(dir, 'sensibilidad.md'), md);
  console.log(md);

  expect(lista.length).toBeGreaterThan(0);
});
