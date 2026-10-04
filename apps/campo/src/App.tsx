import { useCallback, useEffect, useRef, useState } from 'react';
import {
  evaluar, segundaPregunta, temporadaDeMes, tendencia,
  type Entrada, type Respuestas, type Resultado, type Traza,
} from '@chakra/motor';
import { reproducir, detener } from './audio';
import { armarCaso, type DatosConteo } from './datos/caso';
import { CONFIG, FICHAS, REGLAS } from './datos/contratos';
import { db, guardarAjuste, leerAjuste, pedirPersistencia } from './datos/db';
import { contarPendientes, enviarPendientes } from './datos/sync';
import { CALIDAD_POR_DEFECTO } from './vision/calidad';
import { contarClasico } from './vision/clasico';
import { cargarModelo, detectar, modeloListo, nombreModelo } from './vision/detector';
import { contables, esDudoso, normalizar } from './vision/posproceso';
import { aJpeg, procesarFoto, reducirFoto } from './vision/procesar';
import { aGris, LADO_MARCO, type Caja, type Img } from './vision/tipos';
import { ModoTecnico, type Ajustes, type Diagnostico } from './ui/ModoTecnico';
import { PantallaContando, PantallaFoto, PantallaPregunta, PantallaResultado } from './ui/Pantallas';
import { Nube } from './ui/Dibujos';
import { IdiomaContexto, TEXTOS } from './textos';

const MAX_REINTENTOS = 2;
const MODELO_POR_DEFECTO = 'broca-y8n-v0-semireal-int8';

type Paso =
  | { tipo: 'foto'; otraVez: boolean }
  | { tipo: 'contando' }
  | { tipo: 'pregunta'; pregunta: 'granos' | 'polvo_naranja' }
  | { tipo: 'resultado'; resultado: Resultado & { traza: Traza } };

const AJUSTES_INICIALES: Ajustes = {
  finca: Object.keys(FICHAS).sort()[0] ?? 'LC-001',
  // Castellano por defecto: coincide con el texto de la pantalla. El quechua se elige con el botón de la barra.
  idioma: 'es',
  mesForzado: null,
  api: import.meta.env.VITE_API_URL ?? '/api',
  modelo: MODELO_POR_DEFECTO,
  calidad: CALIDAD_POR_DEFECTO,
};

const hoy = () => new Date().toISOString().slice(0, 10);

/** Dos globos de diálogo: el botón cambia el idioma de la voz y de la pantalla. */
function CambiarIdioma() {
  return (
    <svg viewBox="0 0 48 48" aria-hidden="true" className="icono">
      <path d="M6 10 Q6 6 10 6 L26 6 Q30 6 30 10 L30 20 Q30 24 26 24 L16 24 L9 30 L10 24 Q6 24 6 20 Z" fill="currentColor" />
      <path d="M34 18 L38 18 Q42 18 42 22 L42 32 Q42 36 38 36 L37 36 L38 42 L31 36 L22 36 Q18 36 18 32 L18 29" fill="none" stroke="currentColor" strokeWidth="3.5" strokeLinejoin="round" />
    </svg>
  );
}

/** Foto (y contando) → pregunta → resultado: tres puntitos, sin números. */
const indicePaso = (p: Paso) => (p.tipo === 'resultado' ? 2 : p.tipo === 'pregunta' ? 1 : 0);

export default function App() {
  const [ajustes, setAjustes] = useState<Ajustes>(AJUSTES_INICIALES);
  const [paso, setPaso] = useState<Paso>({ tipo: 'foto', otraVez: false });
  const [marco, setMarco] = useState<Img | null>(null);
  const [cajas, setCajas] = useState<Caja[]>([]);
  const [tecnico, setTecnico] = useState(false);
  const [modelos, setModelos] = useState<string[]>([MODELO_POR_DEFECTO]);
  const [diag, setDiag] = useState<Diagnostico>({
    aislado: globalThis.crossOriginIsolated ?? false, hilos: 1, modeloOk: false, msPorMosaico: [], pendientes: 0,
  });

  // Datos del triaje en curso
  const sesion = useRef({ reintentos: 0, foto: null as Blob | null, conteo: null as DatosConteo | null, calidadOk: true, respuestas: {} as Respuestas });

  const mes = ajustes.mesForzado ?? new Date().getMonth() + 1;
  const fecha = ajustes.mesForzado ? `${new Date().getFullYear()}-${String(ajustes.mesForzado).padStart(2, '0')}-15` : hoy();
  const temporada = temporadaDeMes(mes, CONFIG);
  const conf = CONFIG.temporadas[temporada];
  const ficha = FICHAS[ajustes.finca];
  const decir = useCallback((codigo: string) => reproducir(codigo, ajustes.idioma), [ajustes.idioma]);

  // ── Arranque: ajustes guardados, persistencia, modelo, envío pendiente ──
  useEffect(() => {
    (async () => {
      const guardados = await leerAjuste<Partial<Ajustes>>('ajustes', {});
      // Un modelo guardado que ya no viene en el catálogo (p. ej. tras reemplazarlo) pasa al preferido,
      // antes de aplicar los ajustes: así nunca se intenta cargar un .onnx que ya no existe.
      try {
        const r = await fetch(`${import.meta.env.BASE_URL}models/modelos.json`);
        if (r.ok) {
          const cat: { preferido?: string; modelos: { nombre: string }[] } = await r.json();
          const nombres = cat.modelos.map((m) => m.nombre);
          setModelos(nombres);
          if (guardados.modelo && !nombres.includes(guardados.modelo)) {
            guardados.modelo = cat.preferido ?? nombres[0] ?? MODELO_POR_DEFECTO;
          }
        }
      } catch { /* sin catálogo: se queda el modelo guardado o el por defecto */ }
      setAjustes((a) => ({ ...a, ...guardados, calidad: { ...a.calidad, ...guardados.calidad } }));
      await pedirPersistencia();
    })();
  }, []);

  useEffect(() => {
    let vigente = true;
    cargarModelo(ajustes.modelo).then((e) => {
      if (vigente) setDiag((d) => ({ ...d, hilos: e.hilos, modeloOk: e.ok, modeloError: e.error, msCargaModelo: e.msCarga }));
    });
    return () => { vigente = false; };
  }, [ajustes.modelo]);

  // El caso que Noor está viendo en el resultado y si ESE caso ya llegó a la API (no basta con "no hay pendientes":
  // un envío que ya estaba en curso pudo terminar antes de que este caso se guardara).
  const casoActual = useRef<string | null>(null);
  const [casoEnviado, setCasoEnviado] = useState(false);

  const sincronizar = useCallback(async () => {
    const r = await enviarPendientes(ajustes.api);
    setDiag((d) => ({
      ...d,
      pendientes: r.pendientes,
      ultimoEnvio: r.error ?? (r.enviados ? `${r.enviados} enviado(s) ${new Date().toLocaleTimeString()}` : d.ultimoEnvio),
    }));
    const id = casoActual.current;
    if (id) {
      const enviado = (await db.casos.get(id))?.enviado === 1;
      if (casoActual.current === id) setCasoEnviado(enviado);
    }
  }, [ajustes.api]);

  useEffect(() => {
    sincronizar();
    window.addEventListener('online', sincronizar);
    return () => window.removeEventListener('online', sincronizar);
  }, [sincronizar]);

  // Voz al entrar a cada pantalla
  useEffect(() => {
    if (tecnico) return;
    if (paso.tipo === 'foto') decir(paso.otraVez ? 'G_OTRA_VEZ' : conf.foto === 'trampa' ? 'G_FOTO_TRAMPA' : 'G_FOTO_HOJAS');
    if (paso.tipo === 'contando') decir('G_ESPERA');
    if (paso.tipo === 'pregunta') decir(paso.pregunta === 'granos' ? 'P_GRANOS' : 'P_ROYA');
    if (paso.tipo === 'resultado') decir(paso.resultado.mensaje);
    return () => detener();
  }, [paso, conf.foto, decir, tecnico]);

  // El lector de pantalla y el navegador saben en qué idioma está la página.
  useEffect(() => { document.documentElement.lang = ajustes.idioma === 'quz' ? 'qu' : 'es'; }, [ajustes.idioma]);

  const cambiarAjustes = (a: Ajustes) => { setAjustes(a); guardarAjuste('ajustes', a); };

  const entradaMotor = (respuestas: Respuestas): Entrada => {
    const c = sesion.current.conteo;
    return { mes, fecha, ficha, respuestas, conteo: c ? { yolo: c.yolo, anterior: c.anterior, dudoso: c.dudoso } : null };
  };

  // ── 1. Foto ──
  async function alFoto(archivo: File) {
    const s = sesion.current;
    if (conf.foto === 'hojas') {
      // En lluvias la foto de hojas no se analiza: queda como evidencia para el técnico.
      const img = await reducirFoto(archivo);
      s.foto = await aJpeg(img);
      s.conteo = null;
      s.calidadOk = true;
      setPaso({ tipo: 'pregunta', pregunta: conf.pregunta_principal });
      return;
    }
    setMarco(null); setCajas([]);
    setPaso({ tipo: 'contando' });
    const proc = await procesarFoto(archivo, ajustes.calidad);
    setDiag((d) => ({ ...d, msFoto: proc.ms }));
    if (!proc.calidad.ok && s.reintentos < MAX_REINTENTOS) {
      s.reintentos++;
      setPaso({ tipo: 'foto', otraVez: true });
      return;
    }
    s.calidadOk = proc.calidad.ok;
    setMarco(proc.marco);

    const clasico = proc.rectificada ? contarClasico(aGris(proc.marco), LADO_MARCO) : null;
    let detectadas: Caja[] = [];
    let msPorMosaico: number[] = [];
    if (proc.rectificada && modeloListo()) {
      const r = await detectar(proc.marco, (parciales) => setCajas(contables(parciales)));
      detectadas = r.cajas; msPorMosaico = r.msPorMosaico;
    }
    const anterior = (await db.conteos.get(ajustes.finca))?.yolo ?? null;
    const usaYolo = modeloListo() && proc.rectificada;
    const brocas = contables(detectadas);
    const yolo = usaYolo ? brocas.length : clasico ?? 0;
    s.conteo = {
      yolo,
      clasico,
      anterior,
      tendencia: tendencia(yolo, anterior),
      // Sin modelo, sin esquinas o con la foto aún mala tras dos reintentos: no decidimos solos.
      dudoso: !usaYolo || !proc.calidad.ok || esDudoso(detectadas),
      modelo: usaYolo ? nombreModelo() : 'clasico-v0',
      cajas: brocas.map(normalizar),
    };
    s.foto = await aJpeg(proc.marco);
    setDiag((d) => ({
      ...d, msPorMosaico,
      ultimoConteo: { yolo, clasico, dudoso: s.conteo!.dudoso, brillo: proc.calidad.brillo, saturados: proc.calidad.saturados, nitidez: proc.calidad.nitidez },
    }));
    await new Promise((r) => setTimeout(r, 1200)); // que se vean las cajas
    setPaso({ tipo: 'pregunta', pregunta: conf.pregunta_principal });
  }

  // ── 2. Preguntas (la segunda solo si puede cambiar el color) ──
  function alResponder(pregunta: 'granos' | 'polvo_naranja', valor: string) {
    const s = sesion.current;
    s.respuestas = { ...s.respuestas, [pregunta]: valor };
    const otra = segundaPregunta(entradaMotor(s.respuestas), REGLAS, CONFIG);
    if (otra) setPaso({ tipo: 'pregunta', pregunta: otra });
    else terminarTriaje();
  }

  // ── 3. Resultado: decidir, guardar, enviar ──
  async function terminarTriaje() {
    const s = sesion.current;
    const resultado = evaluar(entradaMotor(s.respuestas), REGLAS, CONFIG);
    const caso = armarCaso({
      ficha, mes, temporada, tipoFoto: conf.foto, calidadOk: s.calidadOk, reintentos: s.reintentos,
      conteo: s.conteo, respuestas: s.respuestas, resultado,
    });
    casoActual.current = caso.caso_id;
    setCasoEnviado(false);
    setPaso({ tipo: 'resultado', resultado });
    setDiag((d) => ({ ...d, ultimoResultado: resultado }));
    await db.casos.add({ caso_id: caso.caso_id, finca_id: caso.finca_id, creado: caso.creado, enviado: 0, caso, foto: s.foto });
    if (s.conteo && !s.conteo.dudoso) await db.conteos.put({ finca_id: ficha.finca_id, yolo: s.conteo.yolo, fecha: caso.creado });
    setDiag((d) => ({ ...d, pendientes: d.pendientes + 1 }));
    await sincronizar();
    // Si se sumó a un envío que ya estaba en curso, este caso pudo quedar fuera: un intento más, ya con él guardado.
    if (casoActual.current === caso.caso_id && (await db.casos.get(caso.caso_id))?.enviado !== 1) await sincronizar();
  }

  function reiniciar() {
    sesion.current = { reintentos: 0, foto: null, conteo: null, calidadOk: true, respuestas: {} };
    casoActual.current = null;
    setMarco(null); setCajas([]);
    setPaso({ tipo: 'foto', otraVez: false });
  }

  // Modo técnico: mantener presionado el logo
  const presion = useRef<number>(0);
  const abrirTecnico = () => { presion.current = window.setTimeout(() => {
    setDiag((d) => ({ ...d, aislado: globalThis.crossOriginIsolated ?? false }));
    contarPendientes().then((n) => setDiag((d) => ({ ...d, pendientes: n })));
    setTecnico(true);
  }, 1200); };
  const soltar = () => clearTimeout(presion.current);

  const t = TEXTOS[ajustes.idioma];

  return (
    <IdiomaContexto.Provider value={ajustes.idioma}>
    <div className="app">
      <header className="barra">
        <button type="button" className="logo" aria-label="Chakra Ñawi" onPointerDown={abrirTecnico} onPointerUp={soltar} onPointerLeave={soltar}
          onContextMenu={(e) => e.preventDefault()}>
          <img src={`${import.meta.env.BASE_URL}logo-cabecera.svg`} alt="" />
          <span>Chakra Ñawi</span>
        </button>
        <div className="barra-derecha">
          {/* Un solo idioma para todo: la voz y los textos de la pantalla cambian juntos. */}
          <button type="button" className="idioma" onClick={() => cambiarAjustes({ ...ajustes, idioma: ajustes.idioma === 'quz' ? 'es' : 'quz' })}
            aria-label={t.cambiarIdioma}>
            <CambiarIdioma /> <span>{t.idioma}</span>
          </button>
          <span title={diag.pendientes ? t.seEnviara : t.todoEnviado}><Nube esperando={diag.pendientes > 0} /></span>
        </div>
      </header>
      <ol className="pasos" aria-hidden="true">
        {[0, 1, 2].map((i) => <li key={i} className={i <= indicePaso(paso) ? 'hecho' : ''} />)}
      </ol>

      <main>
        {paso.tipo === 'foto' && (
          <PantallaFoto key={paso.otraVez ? 'foto-otra' : 'foto'} tipo={conf.foto} otraVez={paso.otraVez} alFoto={alFoto}
            alEscuchar={() => decir(paso.otraVez ? 'G_OTRA_VEZ' : conf.foto === 'trampa' ? 'G_FOTO_TRAMPA' : 'G_FOTO_HOJAS')} />
        )}
        {paso.tipo === 'contando' && <PantallaContando marco={marco} cajas={cajas} />}
        {paso.tipo === 'pregunta' && (
          <PantallaPregunta key={paso.pregunta} pregunta={paso.pregunta} alResponder={(v) => alResponder(paso.pregunta, v)}
            alEscuchar={() => decir(paso.pregunta === 'granos' ? 'P_GRANOS' : 'P_ROYA')} />
        )}
        {paso.tipo === 'resultado' && (
          <PantallaResultado estado={paso.resultado.estado} causa={paso.resultado.causa} enviado={casoEnviado}
            alEscuchar={() => decir(paso.resultado.mensaje)} alTerminar={reiniciar} />
        )}
      </main>

      {tecnico && (
        <ModoTecnico ajustes={ajustes} diag={diag} modelos={modelos} alCambiar={cambiarAjustes}
          alEnviar={sincronizar}
          alBorrarHistorial={() => db.conteos.delete(ajustes.finca)}
          alCerrar={() => { setTecnico(false); reiniciar(); }} />
      )}
    </div>
    </IdiomaContexto.Provider>
  );
}
