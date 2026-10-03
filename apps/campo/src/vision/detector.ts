// Inferencia del contador de broca con onnxruntime-web (WASM), mosaico por mosaico (contracts/modelo-io.md).
import * as ort from 'onnxruntime-web/wasm';
import { decodificar, nms } from './posproceso';
import { LADO_MARCO, LADO_MOSAICO, ORIGENES_MOSAICO, type Caja, type Img } from './tipos';

const BASE = import.meta.env.BASE_URL;
ort.env.wasm.wasmPaths = `${BASE}ort/`;
// Hilos solo si la página está aislada (COOP/COEP); si no, un hilo.
ort.env.wasm.numThreads = globalThis.crossOriginIsolated ? Math.min(4, navigator.hardwareConcurrency || 2) : 1;

let sesion: ort.InferenceSession | null = null;
let modeloActual = '';

export interface EstadoModelo {
  nombre: string;
  ok: boolean;
  msCarga: number;
  hilos: number;
  error?: string;
}

export async function cargarModelo(nombre: string): Promise<EstadoModelo> {
  const t0 = performance.now();
  const hilos = ort.env.wasm.numThreads as number;
  if (sesion && modeloActual === nombre) return { nombre, ok: true, msCarga: 0, hilos };
  try {
    sesion = await ort.InferenceSession.create(`${BASE}models/${nombre}.onnx`, { executionProviders: ['wasm'] });
    modeloActual = nombre;
    return { nombre, ok: true, msCarga: performance.now() - t0, hilos };
  } catch (e) {
    sesion = null;
    modeloActual = '';
    return { nombre, ok: false, msCarga: performance.now() - t0, hilos, error: String(e) };
  }
}

export const modeloListo = () => sesion !== null;
export const nombreModelo = () => modeloActual;

function tensorMosaico(marco: Img, ox: number, oy: number): ort.Tensor {
  const n = LADO_MOSAICO * LADO_MOSAICO;
  const datos = new Float32Array(3 * n);
  const d = marco.data;
  for (let y = 0; y < LADO_MOSAICO; y++) {
    let j = ((oy + y) * LADO_MARCO + ox) * 4;
    let i = y * LADO_MOSAICO;
    for (let x = 0; x < LADO_MOSAICO; x++, i++, j += 4) {
      datos[i] = d[j] / 255;
      datos[n + i] = d[j + 1] / 255;
      datos[2 * n + i] = d[j + 2] / 255;
    }
  }
  return new ort.Tensor('float32', datos, [1, 3, LADO_MOSAICO, LADO_MOSAICO]);
}

/**
 * Cuenta brocas en el marco rectificado de 1216 px: 4 mosaicos de 640 con 64 px de solape y NMS global.
 * `alMosaico` se llama después de cada mosaico con las cajas acumuladas, para dibujarlas mientras suena G_ESPERA.
 */
export async function detectar(marco: Img, alMosaico?: (cajas: Caja[], ms: number) => void): Promise<{ cajas: Caja[]; msPorMosaico: number[] }> {
  if (!sesion) throw new Error('El modelo no está cargado');
  const brutas: Caja[] = [];
  const msPorMosaico: number[] = [];
  for (const oy of ORIGENES_MOSAICO) for (const ox of ORIGENES_MOSAICO) {
    const t0 = performance.now();
    const salida = await sesion.run({ [sesion.inputNames[0]]: tensorMosaico(marco, ox, oy) });
    const datos = salida[sesion.outputNames[0]].data as Float32Array;
    brutas.push(...decodificar(datos, ox, oy));
    const ms = performance.now() - t0;
    msPorMosaico.push(ms);
    alMosaico?.(nms(brutas), ms);
    await new Promise((r) => setTimeout(r, 0)); // deja respirar a la interfaz
  }
  return { cajas: nms(brutas), msPorMosaico };
}
