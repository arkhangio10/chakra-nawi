// Tipos que reflejan contracts/*.schema.json. Si un contrato cambia, este archivo cambia con él.

export type Causa = 'sin_problema' | 'broca' | 'roya' | 'clima_floracion' | 'plantas_viejas' | 'otra';
export const CAUSAS: readonly Causa[] = ['sin_problema', 'broca', 'roya', 'clima_floracion', 'plantas_viejas', 'otra'];

export type Temporada = 'cosecha' | 'fin_seca' | 'lluvias';
export type Tendencia = 'sube' | 'igual' | 'baja' | 'sin_dato';
export type Nivel = 'plena' | 'media' | 'baja' | 'ignorar';
export type Estado = 'verde' | 'amarillo' | 'tecnico' | 'tecnico_urgente';
export type Mensaje = 'R_VERDE' | 'R_BROCA' | 'R_ROYA' | 'R_CLIMA' | 'R_TECNICO' | 'R_TECNICO_URGENTE';

export type Evidencia =
  | 'E_TRAMPA_TENDENCIA' | 'E_GRANOS' | 'E_POLVO_NARANJA' | 'E_LLUVIA_DIAS' | 'E_TEMP_ROYA'
  | 'E_LLUVIA_FLORACION' | 'E_CALOR_FLORACION' | 'E_EDAD' | 'A_REGIONAL';

export interface Regla {
  id: string;
  evidencia: Evidencia;
  valor?: string | boolean;
  rango?: { min?: number; max?: number };
  aplica_como?: 'lr' | 'prior';
  lr: Partial<Record<Causa, number>>;
  fuente: string;
  tipo: 'oficial' | 'literatura' | 'supuesto';
  nota?: string;
}

export interface Reglas {
  version: string;
  reglas: Regla[];
}

export interface ConfigTemporada {
  meses: number[];
  foto: 'trampa' | 'hojas';
  pregunta_principal: 'granos' | 'polvo_naranja';
  pesos: Partial<Record<Evidencia, Nivel>>;
  lr_max_por_evidencia?: Partial<Record<Evidencia, number>>;
}

export interface Config {
  version: string;
  umbrales: { verde_p_sin_problema: number; amarillo_p_causa: number; amarillo_ventaja: number };
  tope_lr_por_causa: number;
  priors_base: Record<Causa, number>;
  niveles_peso: Record<Nivel, number>;
  temporadas: Record<Temporada, ConfigTemporada>;
  fruto_atacable_por_mes: boolean[];
  peso_sin_fruto_atacable: Partial<Record<Evidencia, Nivel>>;
  correccion_altitud_c_por_km: number;
  rango_temp_roya_c: { min: number; max: number };
  notas?: string[];
}

export interface Alerta {
  codigo: string;
  causa?: Causa;
  fuente: string;
  url: string;
  cita: string;
  provincia?: string;
  fecha: string; // YYYY-MM-DD
  vence: string; // YYYY-MM-DD
}

export interface Ficha {
  version: string;
  finca_id: string;
  ejemplo?: boolean;
  altitud_m?: number;
  idioma?: string;
  generado?: string;
  clima: {
    lluvia_floracion_anom_pct?: number;
    dias_lluvia_nov_abr?: number;
    dias_lluvia_nov_abr_anom?: number;
    dias_temp_roya_90d?: number;
    dias_temp_roya_90d_anom?: number;
    tmax_floracion_anom_c?: number;
    [otro: string]: unknown;
  };
  registro?: { edad_mas_20_sin_recepa?: boolean; cosecha_alta_ano_pasado?: boolean };
  alertas?: Alerta[];
}

export type RespuestaGranos = '0' | '1-2' | '3+' | 'no_se';
export type RespuestaPolvo = 'si' | 'no' | 'no_se';

export interface Respuestas {
  granos?: RespuestaGranos;
  polvo_naranja?: RespuestaPolvo;
}

export interface EntradaConteo {
  yolo: number;
  anterior: number | null;
  dudoso: boolean;
}

export interface Entrada {
  mes: number; // 1–12
  fecha: string; // YYYY-MM-DD, para saber qué alertas siguen vigentes
  ficha: Ficha;
  conteo: EntradaConteo | null; // null cuando la foto es de hojas
  respuestas: Respuestas;
}

export interface Resultado {
  estado: Estado;
  causa: Causa | null;
  probabilidades: Record<Causa, number>;
  reglas: string[];
  mensaje: Mensaje;
}

/** Detalle para el técnico y para los tests. No va al contrato `caso`. */
export interface Traza {
  temporada: Temporada;
  fruto_atacable: boolean;
  tendencia: Tendencia;
  aportes: { regla: string; evidencia: Evidencia; peso: number; log_lr: Partial<Record<Causa, number>> }[];
  log_lr_total: Record<Causa, number>;
  motivo: string;
}
