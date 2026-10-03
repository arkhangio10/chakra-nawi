import Dexie, { type EntityTable } from 'dexie';

export interface CasoGuardado {
  caso_id: string;
  finca_id: string;
  creado: string;
  enviado: 0 | 1;
  caso: unknown; // objeto que cumple contracts/caso.schema.json
  foto: Blob | null;
}

export interface ConteoPrevio {
  finca_id: string;
  yolo: number;
  fecha: string;
}

export interface Ajuste {
  clave: string;
  valor: unknown;
}

// Base local: la cola de casos sobrevive sin señal, cierres de la app y reinicios del teléfono.
export const db = new Dexie('chakra-nawi') as Dexie & {
  casos: EntityTable<CasoGuardado, 'caso_id'>;
  conteos: EntityTable<ConteoPrevio, 'finca_id'>;
  ajustes: EntityTable<Ajuste, 'clave'>;
};

db.version(1).stores({
  casos: 'caso_id, finca_id, creado, enviado',
  conteos: 'finca_id',
  ajustes: 'clave',
});

export async function leerAjuste<T>(clave: string, porDefecto: T): Promise<T> {
  const a = await db.ajustes.get(clave);
  return (a?.valor as T) ?? porDefecto;
}

export const guardarAjuste = (clave: string, valor: unknown) => db.ajustes.put({ clave, valor });

/** Pide al navegador que no borre la base ni el caché cuando falte espacio (Android). */
export async function pedirPersistencia(): Promise<boolean> {
  try {
    return (await navigator.storage?.persist?.()) ?? false;
  } catch {
    return false;
  }
}
