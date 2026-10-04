# Sensibilidad de los LR ±50% (PLAN §10, prueba 1)

Generado con `npx vitest run validacion/sensibilidad.test.ts` · reglas 2026-10-03.1 · config 2026-10-03.1.

**4740 escenarios**: las 5 fichas × con y sin plantas viejas × 12 meses × tendencia de la trampa (sube, igual, baja, sin anterior; en lluvias, foto de hojas) × todas las respuestas posibles. 1080 son urgentes por la regla fija "granos 3+ con fruto atacable", que no depende de ningún LR; los porcentajes se calculan sobre los otros **3660**.

## Todos los LR a la vez (300 sorteos, cada LR × factor aleatorio en [0,5; 1,5])

- **60,8 %** de los escenarios mantienen su color en al menos el 95 % de los sorteos.
- **57,5 %** no cambian de color en ningún sorteo.

| Color sin perturbar | Escenarios | Estables (≥ 95 % de sorteos) |
|---|---|---|
| amarillo | 1075 | 38,6 % |
| verde | 310 | 0 % |
| tecnico | 2275 | 79,6 % |

Cambios más frecuentes:

- amarillo → tecnico: 5,4 % de las evaluaciones
- verde → tecnico: 2,5 % de las evaluaciones
- tecnico → verde: 2,3 % de las evaluaciones
- tecnico → amarillo: 1,6 % de las evaluaciones

## Una regla a la vez

% de escenarios que cambian de color al multiplicar solo esa regla.

| Regla | Tipo | LR × 1,5 | LR × 0,5 |
|---|---|---|---|
| R-GRANOS-01 | literatura | 7,1 % | 9 % |
| R-GRANOS-02 | literatura | 3,1 % | 14,2 % |
| R-GRANOS-03 | literatura | 0 % | 0 % |
| R-TRAMPA-01 | supuesto | 0 % | 0 % |
| R-TRAMPA-02 | supuesto | 2,9 % | 5,7 % |
| R-ROYA-01 | literatura | 3 % | 4,5 % |
| R-ROYA-02 | supuesto | 0,4 % | 0,8 % |
| R-LLUVIA-01 | supuesto | 0 % | 0 % |
| R-TEMP-01 | supuesto | 0 % | 0 % |
| R-FLOR-01 | supuesto | 0 % | 0 % |
| R-FLOR-02 | supuesto | 0 % | 0 % |
| R-CALOR-01 | supuesto | 0 % | 0 % |
| R-EDAD-01 | supuesto | 3,4 % | 7,4 % |
| R-ALERTA-01 | oficial | 0 % | 0 % |
| R-ALERTA-02 | oficial | 0 % | 0 % |

## Límites

- Los escenarios son todas las combinaciones de entradas, no casos reales: cada combinación pesa lo mismo.
- alertas_activas.json está vacío: R-ALERTA-01/02 no se activan en ningún escenario.
- Las 5 fichas comparten la celda de NASA POWER: el clima casi no varía entre fincas.
- No se perturban los umbrales de decisión ni los pesos por época, solo la magnitud de los LR.

Detalle (escenarios más frágiles y ejemplos por regla): `sensibilidad.json`.
