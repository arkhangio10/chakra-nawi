# packages/motor/ · Motor de triaje (TypeScript)

`score(c) = log prior(c | alertas) + Σ w_mes(e)·log LR(e|c)`, tope de LR combinado por causa, softmax y decisión de PLAN §5.2.
Responsable: P1 (los 20 casos independientes de prueba los escribe P4). Lo usan la PWA y los tests.
Consume `rules.json` y `config.json` (copias de `contracts/*.example.json` al empezar) y la `ficha`; produce el bloque `resultado` de `caso`.
