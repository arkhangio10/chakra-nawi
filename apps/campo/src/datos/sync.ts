// Guardar y enviar después: los casos esperan en IndexedDB hasta que haya señal.
// POST /casos es idempotente por caso_id, así que reintentar nunca duplica.
import { db } from './db';

export interface ResultadoEnvio {
  enviados: number;
  pendientes: number;
  error?: string;
}

let enCurso: Promise<ResultadoEnvio> | null = null;

export function enviarPendientes(api: string): Promise<ResultadoEnvio> {
  enCurso ??= enviar(api).finally(() => (enCurso = null));
  return enCurso;
}

async function enviar(api: string): Promise<ResultadoEnvio> {
  const pendientes = await db.casos.where('enviado').equals(0).sortBy('creado');
  let enviados = 0;
  for (const p of pendientes) {
    const form = new FormData();
    form.append('caso', JSON.stringify(p.caso));
    if (p.foto) form.append('foto', p.foto, (p.caso as { foto: { archivo: string } }).foto.archivo);
    try {
      const r = await fetch(`${api.replace(/\/$/, '')}/casos`, { method: 'POST', body: form });
      if (r.status === 201 || r.status === 200) {
        await db.casos.update(p.caso_id, { enviado: 1 });
        enviados++;
      } else {
        return { enviados, pendientes: pendientes.length - enviados, error: `La API respondió ${r.status}: ${(await r.text()).slice(0, 200)}` };
      }
    } catch (e) {
      return { enviados, pendientes: pendientes.length - enviados, error: `Sin conexión con la API (${String(e)})` };
    }
  }
  return { enviados, pendientes: 0 };
}

export const contarPendientes = () => db.casos.where('enviado').equals(0).count();
