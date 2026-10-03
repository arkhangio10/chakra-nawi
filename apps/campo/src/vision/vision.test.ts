import { describe, expect, it } from 'vitest';
import { contarClasico } from './clasico';
import { detectarEsquinas, ordenar } from './esquinas';
import { aplicar, homografia, rectificar } from './homografia';
import { decodificar, esDudoso, nms, normalizar } from './posproceso';
import { aGris, LADO_MARCO, type Img, type Punto } from './tipos';

/** Foto sintética: papel blanco, cuatro cuadrados negros por fuera de un marco, con perspectiva leve. */
function fotoTarjeta(w: number, h: number, marco: Punto[]): Uint8Array {
  const g = new Uint8Array(w * h).fill(225);
  // Cuadrados de 10 mm por fuera de cada esquina del marco de 100 mm (coordenadas en mm del marco).
  const cuadros = [[-10, -10], [100, -10], [100, 100], [-10, 100]];
  const fotoAMarco = homografia(marco, [{ x: 0, y: 0 }, { x: 100, y: 0 }, { x: 100, y: 100 }, { x: 0, y: 100 }]);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    const m = aplicar(fotoAMarco, { x: x + 0.5, y: y + 0.5 });
    if (cuadros.some(([cx, cy]) => m.x >= cx && m.x < cx + 10 && m.y >= cy && m.y < cy + 10)) g[y * w + x] = 20;
  }
  return g;
}

describe('homografía', () => {
  it('lleva cada esquina a su destino', () => {
    const de = [{ x: 0, y: 0 }, { x: 1216, y: 0 }, { x: 1216, y: 1216 }, { x: 0, y: 1216 }];
    const a = [{ x: 103, y: 87 }, { x: 905, y: 120 }, { x: 880, y: 930 }, { x: 90, y: 890 }];
    const H = homografia(de, a);
    de.forEach((p, i) => {
      const q = aplicar(H, p);
      expect(q.x).toBeCloseTo(a[i].x, 6);
      expect(q.y).toBeCloseTo(a[i].y, 6);
    });
  });

  it('rectifica un cuadrado de una imagen al tamaño pedido', () => {
    const w = 40, h = 40;
    const data = new Uint8ClampedArray(w * h * 4).fill(255);
    for (let y = 10; y < 30; y++) for (let x = 10; x < 30; x++) data.set([0, 0, 0, 255], (y * w + x) * 4);
    const out = rectificar({ data, width: w, height: h }, [{ x: 10, y: 10 }, { x: 30, y: 10 }, { x: 30, y: 30 }, { x: 10, y: 30 }], 64);
    expect(out.width).toBe(64);
    expect(out.data[(32 * 64 + 32) * 4]).toBeLessThan(20); // centro negro
  });
});

describe('esquinas de la tarjeta', () => {
  it('ordena puntos sin importar el orden de entrada', () => {
    const p = ordenar([{ x: 90, y: 90 }, { x: 10, y: 10 }, { x: 10, y: 90 }, { x: 90, y: 10 }]);
    expect(p).toEqual([{ x: 10, y: 10 }, { x: 90, y: 10 }, { x: 90, y: 90 }, { x: 10, y: 90 }]);
  });

  it('encuentra el vértice interior de los cuatro cuadrados negros, con perspectiva', () => {
    const w = 800, h = 700;
    const marco = [{ x: 210, y: 140 }, { x: 600, y: 160 }, { x: 590, y: 560 }, { x: 190, y: 540 }];
    const g = fotoTarjeta(w, h, marco);
    const esq = detectarEsquinas(g, w, h);
    expect(esq).not.toBeNull();
    esq!.forEach((p, i) => {
      expect(Math.abs(p.x - marco[i].x)).toBeLessThan(4);
      expect(Math.abs(p.y - marco[i].y)).toBeLessThan(4);
    });
  });

  it('sin tarjeta devuelve null', () => {
    expect(detectarEsquinas(new Uint8Array(400 * 300).fill(200), 400, 300)).toBeNull();
  });
});

describe('posprocesado del modelo (contracts/modelo-io.md)', () => {
  it('decodifica [1,5,8400], suma el origen del mosaico y descarta < 0,25', () => {
    const n = 8400, s = new Float32Array(5 * n);
    s.set([100, 0], 0); s.set([200, 0], n); s.set([20, 0], 2 * n); s.set([10, 0], 3 * n); s.set([0.9, 0.1], 4 * n);
    const c = decodificar(s, 576, 0);
    expect(c).toHaveLength(1);
    expect(c[0]).toMatchObject({ cx: 676, cy: 200, w: 20, h: 10 });
  });

  it('NMS funde las cajas repetidas en el solape de los mosaicos', () => {
    const a = { cx: 600, cy: 300, w: 20, h: 10, score: 0.9 };
    const b = { cx: 601, cy: 300, w: 20, h: 10, score: 0.8 };
    const c = { cx: 700, cy: 300, w: 20, h: 10, score: 0.7 };
    expect(nms([a, b, c])).toHaveLength(2);
  });

  it('normaliza al marco de 1216 px y marca dudoso con > 30 % de detecciones débiles', () => {
    expect(normalizar({ cx: 608, cy: 1216, w: 24.32, h: 12.16, score: 1 })).toEqual([0.5, 1, 0.02, 0.01]);
    const fuerte = { cx: 0, cy: 0, w: 1, h: 1, score: 0.9 }, debil = { ...fuerte, score: 0.3 };
    expect(esDudoso([fuerte, fuerte, debil])).toBe(true);
    expect(esDudoso([fuerte, fuerte, fuerte, debil])).toBe(false);
    expect(esDudoso([])).toBe(false);
  });
});

describe('contador clásico', () => {
  it('cuenta manchas del tamaño de una broca sobre papel', () => {
    const lado = LADO_MARCO;
    const data = new Uint8ClampedArray(lado * lado * 4).fill(230);
    const puntos = [[100, 100], [300, 120], [500, 700], [900, 900], [1100, 200]];
    for (const [px, py] of puntos) for (let y = -5; y <= 5; y++) for (let x = -10; x <= 10; x++) {
      if ((x / 10) ** 2 + (y / 5) ** 2 <= 1) data.set([40, 30, 25, 255], ((py + y) * lado + px + x) * 4);
    }
    const img: Img = { data, width: lado, height: lado };
    expect(contarClasico(aGris(img), lado)).toBe(puntos.length);
  });
});
