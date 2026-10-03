// Motor de triaje (PLAN §5, ARCHITECTURE §3.3).
//
//   score(c) = log prior_base(c) + clamp( Σ prior-reglas log LR + Σ w_mes(e)·log LR(e|c), ±log tope )
//   P(c)     = softmax(score)
//
// Después, la decisión de PLAN §5.2. Todo es determinista y sin red: corre igual en el teléfono y en los tests.

import {
  CAUSAS, type Causa, type Config, type Entrada, type Estado, type Evidencia, type Mensaje,
  type Regla, type Reglas, type Resultado, type Temporada, type Tendencia, type Traza,
} from './tipos';

/** Cambio mínimo para hablar de tendencia: evita que 3 → 4 brocas se lea como "sube". */
const TENDENCIA_FACTOR = 1.25;
const TENDENCIA_MIN_ABS = 5;

export function temporadaDeMes(mes: number, config: Config): Temporada {
  const t = (Object.keys(config.temporadas) as Temporada[]).find((k) => config.temporadas[k].meses.includes(mes));
  if (!t) throw new Error(`El mes ${mes} no pertenece a ninguna temporada de config.json`);
  return t;
}

export function frutoAtacable(mes: number, config: Config): boolean {
  return config.fruto_atacable_por_mes[mes - 1];
}

/** Tendencia de la trampa frente al conteo anterior de la misma finca (solo tendencia: no hay umbral oficial por trampa). */
export function tendencia(actual: number, anterior: number | null): Tendencia {
  if (anterior === null) return 'sin_dato';
  if (actual >= anterior * TENDENCIA_FACTOR && actual - anterior >= TENDENCIA_MIN_ABS) return 'sube';
  if (actual <= anterior / TENDENCIA_FACTOR && anterior - actual >= TENDENCIA_MIN_ABS) return 'baja';
  return 'igual';
}

/** Valor observado de cada evidencia; `undefined` = no hay dato (no aporta). */
function observar(entrada: Entrada, t: Tendencia): Partial<Record<Evidencia, string | number | boolean | string[]>> {
  const { ficha, respuestas, conteo, fecha } = entrada;
  const c = ficha.clima ?? {};
  const obs: Partial<Record<Evidencia, string | number | boolean | string[]>> = {};
  if (conteo && t !== 'sin_dato') obs.E_TRAMPA_TENDENCIA = t;
  if (respuestas.granos && respuestas.granos !== 'no_se') obs.E_GRANOS = respuestas.granos;
  if (respuestas.polvo_naranja && respuestas.polvo_naranja !== 'no_se') obs.E_POLVO_NARANJA = respuestas.polvo_naranja;
  // Clima: se usan ANOMALÍAS frente a 1991–2020 (señal regional del año, ver LIMITES_DE_DATOS.md).
  if (typeof c.dias_lluvia_nov_abr_anom === 'number') obs.E_LLUVIA_DIAS = c.dias_lluvia_nov_abr_anom;
  if (typeof c.dias_temp_roya_90d_anom === 'number') obs.E_TEMP_ROYA = c.dias_temp_roya_90d_anom;
  if (typeof c.lluvia_floracion_anom_pct === 'number') obs.E_LLUVIA_FLORACION = c.lluvia_floracion_anom_pct;
  if (typeof c.tmax_floracion_anom_c === 'number') obs.E_CALOR_FLORACION = c.tmax_floracion_anom_c;
  if (typeof ficha.registro?.edad_mas_20_sin_recepa === 'boolean') obs.E_EDAD = ficha.registro.edad_mas_20_sin_recepa;
  const vigentes = (ficha.alertas ?? []).filter((a) => a.fecha <= fecha && fecha <= a.vence).map((a) => a.codigo);
  if (vigentes.length) obs.A_REGIONAL = vigentes;
  return obs;
}

function seActiva(regla: Regla, valor: string | number | boolean | string[]): boolean {
  if (regla.rango) {
    if (typeof valor !== 'number') return false;
    const { min = -Infinity, max = Infinity } = regla.rango;
    return valor >= min && valor <= max;
  }
  if (Array.isArray(valor)) return valor.includes(regla.valor as string);
  return valor === regla.valor;
}

function nivelDe(e: Evidencia, mes: number, config: Config): number {
  const temp = config.temporadas[temporadaDeMes(mes, config)];
  let nivel = temp.pesos[e] ?? 'plena';
  if (!frutoAtacable(mes, config) && config.peso_sin_fruto_atacable[e]) nivel = config.peso_sin_fruto_atacable[e]!;
  return config.niveles_peso[nivel];
}

function lrAcotado(lr: number, e: Evidencia, mes: number, config: Config): number {
  const max = config.temporadas[temporadaDeMes(mes, config)].lr_max_por_evidencia?.[e];
  return max ? Math.min(Math.max(lr, 1 / max), max) : lr;
}

/** Probabilidades por causa + traza. No decide el estado. */
export function puntuar(entrada: Entrada, reglas: Reglas, config: Config) {
  const t = entrada.conteo ? tendencia(entrada.conteo.yolo, entrada.conteo.anterior) : 'sin_dato';
  const obs = observar(entrada, t);
  const logLr = Object.fromEntries(CAUSAS.map((c) => [c, 0])) as Record<Causa, number>;
  const aportes: Traza['aportes'] = [];

  for (const regla of reglas.reglas) {
    const valor = obs[regla.evidencia];
    if (valor === undefined || !seActiva(regla, valor)) continue;
    const esPrior = regla.aplica_como === 'prior';
    const peso = esPrior ? 1 : nivelDe(regla.evidencia, entrada.mes, config);
    if (peso === 0) continue;
    const aporte: Partial<Record<Causa, number>> = {};
    for (const [causa, lr] of Object.entries(regla.lr) as [Causa, number][]) {
      const l = esPrior ? lr : lrAcotado(lr, regla.evidencia, entrada.mes, config);
      aporte[causa] = peso * Math.log(l);
      logLr[causa] += aporte[causa]!;
    }
    aportes.push({ regla: regla.id, evidencia: regla.evidencia, peso, log_lr: aporte });
  }

  // Tope del LR combinado por causa: evita contar dos veces evidencias que dependen entre sí.
  const tope = Math.log(config.tope_lr_por_causa);
  for (const c of CAUSAS) logLr[c] = Math.min(Math.max(logLr[c], -tope), tope);

  const score = CAUSAS.map((c) => Math.log(config.priors_base[c]) + logLr[c]);
  const m = Math.max(...score);
  const ex = score.map((s) => Math.exp(s - m));
  const z = ex.reduce((a, b) => a + b, 0);
  const probabilidades = Object.fromEntries(CAUSAS.map((c, i) => [c, ex[i] / z])) as Record<Causa, number>;

  return { probabilidades, tendencia: t, aportes, logLr };
}

const MENSAJE_AMARILLO: Partial<Record<Causa, Mensaje>> = {
  broca: 'R_BROCA', roya: 'R_ROYA', clima_floracion: 'R_CLIMA',
};

/** Triaje completo: probabilidades + estado + mensaje (PLAN §5.2). */
export function evaluar(entrada: Entrada, reglas: Reglas, config: Config): Resultado & { traza: Traza } {
  const { probabilidades, tendencia: t, aportes, logLr } = puntuar(entrada, reglas, config);
  const temporada = temporadaDeMes(entrada.mes, config);
  const atacable = frutoAtacable(entrada.mes, config);
  const { umbrales } = config;
  const r = entrada.respuestas;

  const ordenadas = [...CAUSAS].sort((a, b) => probabilidades[b] - probabilidades[a]);
  const problemas = ordenadas.filter((c) => c !== 'sin_problema');
  const principal = problemas[0];

  const salida = (estado: Estado, causa: Causa | null, mensaje: Mensaje, motivo: string) => ({
    estado, causa, probabilidades, mensaje,
    reglas: aportes.map((a) => a.regla),
    traza: { temporada, fruto_atacable: atacable, tendencia: t, aportes, log_lr_total: logLr, motivo },
  });

  // 1. Granos 3+ con fruto atacable: urgente, sin importar el resto.
  if (r.granos === '3+' && atacable) {
    return salida('tecnico_urgente', 'broca', 'R_TECNICO_URGENTE', 'granos 3+ con fruto atacable');
  }
  // 2. Conteo dudoso: no decidimos.
  if (entrada.conteo?.dudoso) {
    return salida('tecnico', principal, 'R_TECNICO', 'conteo dudoso');
  }
  // 3. Verde: sin problema probable y no apoyado solo en "0 granos" (PLAN §5.2: un 0 nunca da verde solo).
  const favorables = [
    r.granos === '0' && nivelDe('E_GRANOS', entrada.mes, config) > 0 ? 'granos' : null,
    t === 'igual' || t === 'baja' ? 'trampa' : null,
    r.polvo_naranja === 'no' ? 'polvo' : null,
  ].filter(Boolean) as string[];
  const principalNoSe = r[config.temporadas[temporada].pregunta_principal] === 'no_se';
  const soloCeroGranos = favorables.length === 1 && favorables[0] === 'granos';
  if (
    probabilidades.sin_problema >= umbrales.verde_p_sin_problema &&
    favorables.length > 0 && !soloCeroGranos && !principalNoSe
  ) {
    return salida('verde', 'sin_problema', 'R_VERDE', `sin problema; apoyado en ${favorables.join(' + ')}`);
  }
  // 4. Amarillo: una causa clara entre broca, roya o clima.
  const segunda = ordenadas.find((c) => c !== principal)!;
  const ventaja = probabilidades[principal] - probabilidades[segunda];
  const msg = MENSAJE_AMARILLO[principal];
  if (msg && probabilidades[principal] >= umbrales.amarillo_p_causa && ventaja >= umbrales.amarillo_ventaja) {
    return salida('amarillo', principal, msg, `${principal} con ventaja ${ventaja.toFixed(2)}`);
  }
  // 5. Todo lo demás: el técnico decide (duda, plantas viejas, otra causa).
  return salida('tecnico', principal, 'R_TECNICO', 'sin causa clara');
}

/**
 * "La segunda pregunta solo si puede cambiar el color" (PLAN §4). Devuelve la pregunta a hacer o null.
 * Se simulan todas las respuestas posibles de la pregunta que falta; si alguna cambia el estado, vale la pena preguntarla.
 */
export function segundaPregunta(entrada: Entrada, reglas: Reglas, config: Config): 'granos' | 'polvo_naranja' | null {
  const temporada = temporadaDeMes(entrada.mes, config);
  const principal = config.temporadas[temporada].pregunta_principal;
  const otra = principal === 'granos' ? 'polvo_naranja' : 'granos';
  if (entrada.respuestas[otra] !== undefined) return null;
  if (otra === 'granos' && nivelDe('E_GRANOS', entrada.mes, config) === 0) return null;

  const actual = evaluar(entrada, reglas, config).estado;
  if (actual === 'tecnico_urgente') return null;
  const opciones = otra === 'granos' ? (['0', '1-2', '3+'] as const) : (['si', 'no'] as const);
  const cambia = opciones.some((o) =>
    evaluar({ ...entrada, respuestas: { ...entrada.respuestas, [otra]: o } }, reglas, config).estado !== actual,
  );
  return cambia ? otra : null;
}
