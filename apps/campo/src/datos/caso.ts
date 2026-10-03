import type { Ficha, Resultado, Respuestas, Temporada, Tendencia } from '@chakra/motor';
import { VERSION_APP } from './contratos';

export interface DatosConteo {
  yolo: number;
  clasico: number | null;
  anterior: number | null;
  tendencia: Tendencia;
  dudoso: boolean;
  modelo: string;
  cajas: [number, number, number, number][];
}

/** Arma el objeto que cumple contracts/caso.schema.json. */
export function armarCaso(p: {
  ficha: Ficha;
  mes: number;
  temporada: Temporada;
  tipoFoto: 'trampa' | 'hojas';
  calidadOk: boolean;
  reintentos: number;
  conteo: DatosConteo | null;
  respuestas: Respuestas;
  resultado: Resultado;
}) {
  const caso_id = crypto.randomUUID();
  return {
    caso_id,
    finca_id: p.ficha.finca_id,
    ficha_version: p.ficha.version,
    creado: new Date().toISOString(),
    mes: p.mes,
    temporada: p.temporada,
    foto: { tipo: p.tipoFoto, archivo: `${caso_id}.jpg`, calidad_ok: p.calidadOk, reintentos: p.reintentos },
    conteo: p.conteo,
    respuestas: p.respuestas,
    resultado: {
      estado: p.resultado.estado,
      causa: p.resultado.causa,
      probabilidades: p.resultado.probabilidades,
      reglas: p.resultado.reglas,
      mensaje: p.resultado.mensaje,
    },
    app_version: VERSION_APP,
  };
}
