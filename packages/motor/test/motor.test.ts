import { describe, expect, it } from 'vitest';
import { evaluar, segundaPregunta, temporadaDeMes, tendencia, type Ficha } from '../src';
import { config, entrada, fichaNeutra, reglas } from './comun';

const AGOSTO = 8; // fin de la seca: trampa con peso pleno
const NOVIEMBRE = 11; // lluvias, sin fruto atacable
const FEBRERO = 2; // lluvias, con fruto atacable

describe('temporada y tendencia', () => {
  it('asigna cada mes a su época', () => {
    expect(temporadaDeMes(6, config)).toBe('cosecha');
    expect(temporadaDeMes(AGOSTO, config)).toBe('fin_seca');
    expect(temporadaDeMes(1, config)).toBe('lluvias');
  });

  it('la tendencia exige un cambio real, no ruido', () => {
    expect(tendencia(143, null)).toBe('sin_dato');
    expect(tendencia(143, 61)).toBe('sube');
    expect(tendencia(4, 3)).toBe('igual'); // +33 % pero solo 1 broca más
    expect(tendencia(30, 61)).toBe('baja');
    expect(tendencia(65, 61)).toBe('igual');
  });
});

describe('decisión (PLAN §5.2)', () => {
  it('granos 3+ con fruto atacable → técnico urgente', () => {
    const r = evaluar(entrada({ mes: AGOSTO, respuestas: { granos: '3+' } }), reglas, config);
    expect(r.estado).toBe('tecnico_urgente');
    expect(r.mensaje).toBe('R_TECNICO_URGENTE');
  });

  it('sin fruto atacable (noviembre) los granos 3+ no cuentan', () => {
    const r = evaluar(entrada({ mes: NOVIEMBRE, respuestas: { granos: '3+', polvo_naranja: 'no' } }), reglas, config);
    expect(r.estado).not.toBe('tecnico_urgente');
    expect(r.reglas.some((id) => id.startsWith('R-GRANOS'))).toBe(false);
  });

  it('broca: granos 1–2 y trampa que sube → amarillo broca', () => {
    const r = evaluar(
      entrada({ mes: AGOSTO, conteo: { yolo: 143, anterior: 61, dudoso: false }, respuestas: { granos: '1-2' } }),
      reglas, config,
    );
    expect(r.estado).toBe('amarillo');
    expect(r.causa).toBe('broca');
    expect(r.mensaje).toBe('R_BROCA');
    expect(r.reglas).toEqual(expect.arrayContaining(['R-GRANOS-02', 'R-TRAMPA-01']));
  });

  it('un 0 de 20 granos nunca da verde por sí solo', () => {
    const e = entrada({ mes: AGOSTO, conteo: { yolo: 20, anterior: null, dudoso: false }, respuestas: { granos: '0' } });
    const r = evaluar(e, reglas, config);
    expect(r.estado).not.toBe('verde');
    // …y por eso vale la pena hacer la segunda pregunta
    expect(segundaPregunta(e, reglas, config)).toBe('polvo_naranja');
  });

  it('0 granos + sin polvo naranja → verde', () => {
    const r = evaluar(entrada({ mes: AGOSTO, respuestas: { granos: '0', polvo_naranja: 'no' } }), reglas, config);
    expect(r.estado).toBe('verde');
    expect(r.mensaje).toBe('R_VERDE');
  });

  it('0 granos + trampa estable → verde sin segunda pregunta', () => {
    const e = entrada({ mes: AGOSTO, conteo: { yolo: 58, anterior: 61, dudoso: false }, respuestas: { granos: '0' } });
    expect(evaluar(e, reglas, config).estado).toBe('verde');
  });

  it('"no sé" en la pregunta principal nunca da verde', () => {
    const r = evaluar(entrada({ mes: AGOSTO, respuestas: { granos: 'no_se', polvo_naranja: 'no' } }), reglas, config);
    expect(r.estado).not.toBe('verde');
  });

  it('conteo dudoso → técnico', () => {
    const r = evaluar(
      entrada({ mes: AGOSTO, conteo: { yolo: 300, anterior: 40, dudoso: true }, respuestas: { granos: '1-2' } }),
      reglas, config,
    );
    expect(r.estado).toBe('tecnico');
    expect(r.mensaje).toBe('R_TECNICO');
  });

  it('roya en lluvias: polvo naranja + alerta regional vigente → amarillo roya', () => {
    const ficha: Ficha = {
      ...fichaNeutra,
      alertas: [{
        codigo: 'ROYA_ALERTA_REGION', causa: 'roya', fuente: 'SENASA', url: 'https://example.org',
        cita: 'prueba', fecha: '2026-02-01', vence: '2026-03-02',
      }],
    };
    const r = evaluar(entrada({ mes: FEBRERO, ficha, respuestas: { polvo_naranja: 'si' } }), reglas, config);
    expect(r.estado).toBe('amarillo');
    expect(r.causa).toBe('roya');
    expect(r.reglas).toContain('R-ALERTA-02');
  });

  it('una alerta vencida no cuenta', () => {
    const ficha: Ficha = {
      ...fichaNeutra,
      alertas: [{
        codigo: 'ROYA_ALERTA_REGION', fuente: 'SENASA', url: 'https://example.org',
        cita: 'prueba', fecha: '2025-12-01', vence: '2025-12-31',
      }],
    };
    const r = evaluar(entrada({ mes: FEBRERO, ficha, respuestas: { polvo_naranja: 'si' } }), reglas, config);
    expect(r.reglas).not.toContain('R-ALERTA-02');
  });

  it('plantas viejas no tiene amarillo propio: va al técnico', () => {
    const ficha: Ficha = { ...fichaNeutra, registro: { edad_mas_20_sin_recepa: true } };
    const r = evaluar(entrada({ mes: AGOSTO, ficha, respuestas: { granos: 'no_se' } }), reglas, config);
    expect(r.mensaje).not.toBe('R_VERDE');
    if (r.causa === 'plantas_viejas') expect(r.estado).toBe('tecnico');
  });

  it('en lluvias la trampa no pesa', () => {
    const r = evaluar(
      entrada({ mes: FEBRERO, conteo: { yolo: 300, anterior: 10, dudoso: false }, respuestas: { polvo_naranja: 'no' } }),
      reglas, config,
    );
    expect(r.reglas).not.toContain('R-TRAMPA-01');
  });

  it('el tope de LR combinado se respeta', () => {
    const r = evaluar(
      entrada({ mes: AGOSTO, conteo: { yolo: 400, anterior: 50, dudoso: false }, respuestas: { granos: '1-2', polvo_naranja: 'no' } }),
      reglas, config,
    );
    for (const v of Object.values(r.traza.log_lr_total)) expect(Math.abs(v)).toBeLessThanOrEqual(Math.log(config.tope_lr_por_causa) + 1e-9);
  });
});
