# apps/campo/ · PWA de campo

Vite + React + TS + `vite-plugin-pwa` + Dexie. Tres pantallas sin menú: foto → pregunta → resultado. **Cero cifras en pantalla.**
Responsable: P1. Consume `ficha.schema.json`, `mensajes.schema.json`, el ONNX según `contracts/modelo-io.md` y el motor de `packages/motor`.
Produce `caso.schema.json` (cola en IndexedDB → `POST /casos`, idempotente por `caso_id`).
