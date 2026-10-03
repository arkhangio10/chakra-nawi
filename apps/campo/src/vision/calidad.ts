// Control de calidad sin ML (PLAN §2): exposición y nitidez del marco rectificado.
// La tarjeta es papel blanco: una foto bien expuesta tiene brillo medio alto (≈ 230–245), así que
// "quemada" se mide por píxeles saturados, no por el promedio. Umbrales provisionales hasta medirlos
// con fotos reales; se ajustan en el modo técnico.

export interface UmbralesCalidad {
  brilloMin: number; // brillo medio mínimo (0–255)
  saturadosMax: number; // fracción máxima de píxeles ≥ 252
  nitidezMin: number; // varianza del Laplaciano
}

export const CALIDAD_POR_DEFECTO: UmbralesCalidad = { brilloMin: 70, saturadosMax: 0.35, nitidezMin: 25 };

export interface Calidad {
  brillo: number;
  saturados: number;
  nitidez: number;
  ok: boolean;
  motivo: 'ok' | 'oscura' | 'quemada' | 'movida';
}

/** `gris` del marco rectificado. Se mide sobre una versión a la mitad para que sea rápido. */
export function medirCalidad(gris: Uint8Array, lado: number, u: UmbralesCalidad = CALIDAD_POR_DEFECTO): Calidad {
  const m = lado >> 1;
  const g = new Float32Array(m * m);
  let suma = 0, saturados = 0;
  for (let y = 0; y < m; y++) for (let x = 0; x < m; x++) {
    const v = gris[(2 * y) * lado + 2 * x];
    g[y * m + x] = v;
    suma += v;
    if (v >= 252) saturados++;
  }
  const n2 = m * m;
  const brillo = suma / n2;
  let s = 0, s2 = 0, n = 0;
  for (let y = 1; y < m - 1; y++) for (let x = 1; x < m - 1; x++) {
    const i = y * m + x;
    const lap = g[i - 1] + g[i + 1] + g[i - m] + g[i + m] - 4 * g[i];
    s += lap; s2 += lap * lap; n++;
  }
  const nitidez = s2 / n - (s / n) ** 2;
  const fraccion = saturados / n2;
  const motivo = brillo < u.brilloMin ? 'oscura' : fraccion > u.saturadosMax ? 'quemada' : nitidez < u.nitidezMin ? 'movida' : 'ok';
  return { brillo, saturados: fraccion, nitidez, ok: motivo === 'ok', motivo };
}
