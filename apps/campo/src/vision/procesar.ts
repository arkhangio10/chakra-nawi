// Foto nativa → esquinas → marco rectificado de 1216 px → calidad. Solo navegador (usa canvas).
import { medirCalidad, type Calidad, type UmbralesCalidad } from './calidad';
import { detectarEsquinas } from './esquinas';
import { rectificar } from './homografia';
import { aGris, LADO_MARCO, type Img } from './tipos';

const LADO_MAX_FOTO = 2600; // suficiente para que el marco tenga ≥ 1216 px sin saturar la memoria del teléfono
const LADO_BUSQUEDA = 1000;

function lienzo(w: number, h: number) {
  const c = document.createElement('canvas');
  c.width = w; c.height = h;
  return c;
}

async function leerFoto(archivo: Blob): Promise<Img> {
  const bmp = await createImageBitmap(archivo, { imageOrientation: 'from-image' });
  const s = Math.min(1, LADO_MAX_FOTO / Math.max(bmp.width, bmp.height));
  const c = lienzo(Math.round(bmp.width * s), Math.round(bmp.height * s));
  const ctx = c.getContext('2d', { willReadFrequently: true })!;
  ctx.drawImage(bmp, 0, 0, c.width, c.height);
  bmp.close();
  return ctx.getImageData(0, 0, c.width, c.height);
}

/** Gris reducido para buscar las esquinas rápido. */
function grisReducido(img: Img): { gris: Uint8Array; w: number; h: number; escala: number } {
  const escala = Math.min(1, LADO_BUSQUEDA / Math.max(img.width, img.height));
  const w = Math.round(img.width * escala), h = Math.round(img.height * escala);
  const gris = new Uint8Array(w * h);
  const d = img.data;
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    const j = (Math.min(img.height - 1, Math.floor(y / escala)) * img.width + Math.min(img.width - 1, Math.floor(x / escala))) * 4;
    gris[y * w + x] = (d[j] * 299 + d[j + 1] * 587 + d[j + 2] * 114) / 1000;
  }
  return { gris, w, h, escala };
}

export interface FotoProcesada {
  marco: Img; // 1216×1216 si se encontraron las esquinas; si no, la foto reducida
  rectificada: boolean;
  calidad: Calidad;
  ms: number;
}

export async function procesarFoto(archivo: Blob, umbrales: UmbralesCalidad): Promise<FotoProcesada> {
  const t0 = performance.now();
  const foto = await leerFoto(archivo);
  const { gris, w, h, escala } = grisReducido(foto);
  const esquinas = detectarEsquinas(gris, w, h);
  if (!esquinas) {
    // Sin las 4 esquinas no hay escala: la foto no sirve para contar.
    const reducida = reducir(foto, LADO_MARCO);
    return { marco: reducida, rectificada: false, calidad: { brillo: 0, nitidez: 0, ok: false, motivo: 'movida' }, ms: performance.now() - t0 };
  }
  const marco = rectificar(foto, esquinas.map((p) => ({ x: p.x / escala, y: p.y / escala })), LADO_MARCO);
  const calidad = medirCalidad(aGris(marco), LADO_MARCO, umbrales);
  return { marco, rectificada: true, calidad, ms: performance.now() - t0 };
}

/** Foto de hojas (época de lluvias): no se analiza, solo se guarda para el técnico. */
export async function reducirFoto(archivo: Blob): Promise<Img> {
  return reducir(await leerFoto(archivo), LADO_MARCO);
}

function reducir(img: Img, lado: number): Img {
  const s = Math.min(1, lado / Math.max(img.width, img.height));
  const origen = lienzo(img.width, img.height);
  origen.getContext('2d')!.putImageData(new ImageData(img.data as Uint8ClampedArray<ArrayBuffer>, img.width, img.height), 0, 0);
  const c = lienzo(Math.round(img.width * s), Math.round(img.height * s));
  const ctx = c.getContext('2d', { willReadFrequently: true })!;
  ctx.drawImage(origen, 0, 0, c.width, c.height);
  return ctx.getImageData(0, 0, c.width, c.height);
}

export function aJpeg(img: Img, calidad = 0.85): Promise<Blob> {
  const c = lienzo(img.width, img.height);
  c.getContext('2d')!.putImageData(new ImageData(img.data as Uint8ClampedArray<ArrayBuffer>, img.width, img.height), 0, 0);
  return new Promise((ok, mal) => c.toBlob((b) => (b ? ok(b) : mal(new Error('No se pudo crear el JPEG'))), 'image/jpeg', calidad));
}
