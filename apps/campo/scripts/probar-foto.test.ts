// Prueba manual (no corre en `npm test`): pasa una foto JPEG real por esquinas → rectificado → calidad → clásico.
//   python scripts/a-rgba.py ../../docs/demo/foto_tarjeta_sintetica.jpg /tmp/foto.rgba
//   RGBA=/tmp/foto.rgba SALIDA=/tmp/marco.rgba npx vitest run scripts/probar-foto.test.ts --environment node
// Necesita la foto convertida a RGBA crudo por scripts/a-rgba.py (sin dependencias de canvas en Node).
import { readFileSync, writeFileSync } from 'node:fs';
import { it, expect } from 'vitest';
import { medirCalidad } from '../src/vision/calidad';
import { contarClasico } from '../src/vision/clasico';
import { detectarEsquinas } from '../src/vision/esquinas';
import { rectificar } from '../src/vision/homografia';
import { aGris, LADO_MARCO } from '../src/vision/tipos';

it.runIf(process.env.RGBA)('foto real → marco rectificado', () => {
  const ruta = process.env.RGBA!;
  const [w, h] = readFileSync(`${ruta}.dim`, 'utf-8').trim().split('x').map(Number);
  const data = new Uint8ClampedArray(readFileSync(ruta));
  const img = { data, width: w, height: h };
  const escala = Math.min(1, 1000 / Math.max(w, h));
  const sw = Math.round(w * escala), sh = Math.round(h * escala);
  const gris = new Uint8Array(sw * sh);
  for (let y = 0; y < sh; y++) for (let x = 0; x < sw; x++) {
    const j = (Math.floor(y / escala) * w + Math.floor(x / escala)) * 4;
    gris[y * sw + x] = (data[j] * 299 + data[j + 1] * 587 + data[j + 2] * 114) / 1000;
  }
  const t0 = performance.now();
  const esq = detectarEsquinas(gris, sw, sh);
  expect(esq).not.toBeNull();
  const marco = rectificar(img, esq!.map((p) => ({ x: p.x / escala, y: p.y / escala })), LADO_MARCO);
  const g = aGris(marco);
  const calidad = medirCalidad(g, LADO_MARCO);
  const clasico = contarClasico(g, LADO_MARCO);
  const resultado = { esquinas: esq!.map((p) => [Math.round(p.x / escala), Math.round(p.y / escala)]), calidad, clasico, ms: Math.round(performance.now() - t0) };
  writeFileSync(`${ruta}.resultado.json`, JSON.stringify(resultado, null, 1));
  if (process.env.SALIDA) writeFileSync(process.env.SALIDA, Buffer.from(marco.data.buffer));
});
