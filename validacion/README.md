# validacion/

Pruebas de PLAN §10: sensibilidad ±50% de LR, tabla binomial, error de conteo (sustituto y broca por separado), curva cobertura–precisión con 20 casos independientes, usabilidad.
Responsables: P3 + P4 (P2 para el error de conteo). Consume `caso`, `rules` y `config`; produce figuras y tablas para el README y el video.

## Prueba 1 · Sensibilidad de los LR ±50% (3 oct 2026)

`npx vitest run validacion/sensibilidad.test.ts` (desde la raíz; no lo corre `npm test`) → `resultados/sensibilidad.md` y `resultados/sensibilidad.json`.

4 740 escenarios: las 5 fichas × con y sin plantas viejas × 12 meses × tendencia de la trampa × todas las respuestas. 1 080 son urgentes por la regla fija "granos 3+ con fruto atacable" y no dependen de ningún LR. Sobre los otros 3 660, con todos los LR movidos a la vez entre ×0,5 y ×1,5 (300 sorteos):

- **El 60,8 % mantiene su color** en al menos el 95 % de los sorteos. Técnico es el más estable (79,6 %), amarillo queda en 38,6 % y **verde en 0 %**.
- **Cuando el color cambia, casi siempre es hacia el técnico**: amarillo → técnico (5,4 % de las evaluaciones) y verde → técnico (2,5 %). Hacia menos cautela: técnico → verde (2,3 %) y técnico → amarillo (1,6 %). Un LR mal puesto cuesta sobre todo **visitas de más**, no casos perdidos.
- **El verde es frágil por diseño.** Los verdes quedan con P(sin problema) de 0,65 a 0,69, apenas sobre el umbral de 0,60, y dependen sobre todo de R-GRANOS-01 ("0 granos", LR 1,5). Con ese LR a la mitad, pasan a técnico. Es coherente con "un 0 nunca da verde solo", pero significa que el verde es la decisión que más necesita calibrarse con datos de campo.
- **El cambio de riesgo** (técnico → verde) aparece sobre todo en fincas con plantas viejas, cuando se debilitan R-EDAD-01 o R-ROYA-02. Son las primeras reglas a revisar con el agrónomo.
- **Reglas que no se pusieron a prueba**: las de clima (R-LLUVIA-01, R-TEMP-01, R-FLOR-01/02, R-CALOR-01) no se activan con las anomalías actuales de las 5 fichas, y las de alertas tampoco, porque `alertas_activas.json` está vacío. R-TRAMPA-01 no cambia nada porque su LR está acotado a 2 en fin de la seca.

Límites: los escenarios son combinaciones de entradas, no casos reales, y todas pesan lo mismo. No se perturban los umbrales ni los pesos por época. Cualquier ajuste de LR o de umbrales es un cambio de contrato y necesita el acuerdo del equipo (PLAN §3).
