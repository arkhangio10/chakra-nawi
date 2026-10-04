// Dibujos simples, de trazo uniforme (Medhi et al.: los dibujos estáticos se entienden mejor que fotos o íconos).
// Ninguno contiene números ni texto.
import type { ReactNode } from 'react';

const T = { stroke: 'var(--trazo)', strokeWidth: 4, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const };

function Lienzo({ children, titulo, vb = '0 0 200 200' }: { children: ReactNode; titulo: string; vb?: string }) {
  return (
    <svg viewBox={vb} role="img" aria-label={titulo} className="dibujo">
      {children}
    </svg>
  );
}

const BROCAS: [number, number, number][] = [
  [70, 78, 20], [96, 70, -30], [120, 92, 60], [84, 104, 10], [110, 120, -50],
  [74, 128, 80], [132, 130, 15], [98, 140, -10], [126, 72, 40], [62, 100, -70],
];

/** La tarjeta con lo que se vació de la trampa: marco gris y cuatro esquinas negras por fuera. */
export function Tarjeta() {
  return (
    <Lienzo titulo="Tarjeta con lo que cayó en la trampa">
      <rect x="22" y="22" width="156" height="156" rx="10" fill="#fff" {...T} />
      <rect x="44" y="44" width="112" height="112" fill="none" stroke="#b9bcb4" strokeWidth="3" />
      {[[32, 32], [156, 32], [156, 156], [32, 156]].map(([x, y]) => (
        <rect key={`${x}-${y}`} x={x} y={y} width="12" height="12" fill="#151515" />
      ))}
      {BROCAS.map(([x, y, r]) => (
        <ellipse key={`${x}-${y}`} cx={x} cy={y} rx="5.5" ry="3" transform={`rotate(${r} ${x} ${y})`} fill="#3a2418" />
      ))}
    </Lienzo>
  );
}

/** Tres hojas volteadas sobre la tarjeta (época de lluvias). */
export function HojasEnTarjeta() {
  return (
    <Lienzo titulo="Tres hojas volteadas sobre la tarjeta">
      <rect x="22" y="22" width="156" height="156" rx="10" fill="#fff" {...T} />
      {[[-25, 70, 92], [5, 100, 100], [30, 128, 104]].map(([r, x, y]) => (
        <g key={x} transform={`rotate(${r} ${x} ${y})`}>
          <path d={`M${x} ${y - 46} C${x + 26} ${y - 26} ${x + 22} ${y + 26} ${x} ${y + 46} C${x - 22} ${y + 26} ${x - 26} ${y - 26} ${x} ${y - 46} Z`} fill="#9cc58a" {...T} strokeWidth={3} />
          <path d={`M${x} ${y - 40} L${x} ${y + 42}`} {...T} strokeWidth={2} fill="none" />
        </g>
      ))}
    </Lienzo>
  );
}

/**
 * Cereza vista de frente, con la corona (el ombligo) hacia quien mira.
 * Sana: corona ocre con su estrellita. Con huequito: un hoyo negro grande con borde claro y aserrín,
 * para que se distinga a simple vista aun en un celular chico.
 */
function Cereza({ x, y, s = 1, hueco = false }: { x: number; y: number; s?: number; hueco?: boolean }) {
  return (
    <g transform={`translate(${x} ${y}) scale(${s})`}>
      <ellipse cx="0" cy="0" rx="30" ry="33" fill="#b0322a" {...T} />
      <ellipse cx="-14" cy="-6" rx="6" ry="11" fill="#e07a6e" opacity=".75" />
      <ellipse cx="2" cy="-4" rx="14" ry="12" fill="#d9a05b" {...T} strokeWidth={3} />
      {hueco ? (
        <>
          <circle cx="2" cy="-4" r="8.5" fill="#fff4dc" />
          <circle cx="2" cy="-4" r="6.5" fill="#120a08" />
          {[[-12, 14], [14, 12], [20, -16]].map(([dx, dy]) => <circle key={dx} cx={dx} cy={dy} r="2.4" fill="#f3dfb8" />)}
        </>
      ) : (
        <path d="M2 -4 L2 -11 M2 -4 L9 -6 M2 -4 L6 3 M2 -4 L-2 3 M2 -4 L-5 -6" stroke="#7a4a1e" strokeWidth={2.6} strokeLinecap="round" />
      )}
    </g>
  );
}

/** Grano de café: sano, con huequito en la corona, o un montón con huequitos. */
export function Granos({ tipo }: { tipo: 'sano' | 'pocos' | 'muchos' }) {
  const titulo = { sano: 'Granos sanos', pocos: 'Pocos granos con huequito', muchos: 'Muchos granos con huequito' }[tipo];
  return (
    <Lienzo titulo={titulo} vb="22 26 160 160">
      {tipo === 'sano' && <><Cereza x={66} y={104} s={1.15} /><Cereza x={136} y={104} s={1.15} /></>}
      {tipo === 'pocos' && <><Cereza x={66} y={104} s={1.15} hueco /><Cereza x={136} y={104} s={1.15} /></>}
      {tipo === 'muchos' && (
        <>
          <Cereza x={58} y={72} s={0.85} hueco /><Cereza x={142} y={72} s={0.85} hueco /><Cereza x={100} y={100} s={0.85} hueco />
          <Cereza x={58} y={136} s={0.85} hueco /><Cereza x={142} y={136} s={0.85} hueco />
        </>
      )}
    </Lienzo>
  );
}

/** Hoja vista por debajo; con roya tiene polvo naranja. */
export function Hoja({ polvo }: { polvo: boolean }) {
  return (
    <Lienzo titulo={polvo ? 'Hoja con polvo naranja por debajo' : 'Hoja limpia por debajo'}>
      <path d="M100 26 C150 56 152 140 100 176 C48 140 50 56 100 26 Z" fill="#a8cf96" {...T} />
      <path d="M100 34 L100 170 M100 70 L74 56 M100 70 L126 56 M100 104 L70 90 M100 104 L130 90 M100 136 L76 124 M100 136 L124 124" {...T} strokeWidth={2.5} fill="none" />
      {polvo && [[80, 78], [118, 96], [86, 118], [114, 136], [92, 150], [124, 70]].map(([x, y]) => (
        <g key={`${x}-${y}`}>
          <circle cx={x} cy={y} r="10" fill="#f08a24" />
          <circle cx={x + 4} cy={y - 3} r="3" fill="#ffc06b" />
        </g>
      ))}
    </Lienzo>
  );
}

/** No sé: un signo de pregunta grande, en el mismo estilo de trazo que el resto. */
export function NoSe() {
  return (
    <Lienzo titulo="No sé">
      <circle cx="100" cy="100" r="66" fill="#e3ebe4" {...T} />
      <path d="M76 80 Q76 52 100 52 Q124 52 124 76 Q124 94 106 102 Q100 106 100 118 L100 124" {...T} strokeWidth={14} stroke="var(--acento)" fill="none" />
      <circle cx="100" cy="148" r="9" fill="var(--acento)" />
    </Lienzo>
  );
}

/** Verde: planta sana con cerezas. */
export function PlantaSana() {
  return (
    <Lienzo titulo="Planta de café sana">
      <g className="mece">
      <path d="M100 180 L100 70" {...T} fill="none" />
      {[[-1, 150], [1, 128], [-1, 106], [1, 86]].map(([lado, y]) => (
        <path key={y} d={`M100 ${y} q${lado * 30} -20 ${lado * 62} -6 q${lado * -30} 24 ${lado * -62} 6 Z`} fill="#5f9e4c" {...T} strokeWidth={3} />
      ))}
      <path d="M100 70 q-14 -30 0 -48 q14 18 0 48 Z" fill="#5f9e4c" {...T} strokeWidth={3} />
      {[[78, 140], [124, 118], [84, 98]].map(([x, y]) => <circle key={x} cx={x} cy={y} r="8" fill="#b0322a" {...T} strokeWidth={2.5} />)}
      </g>
    </Lienzo>
  );
}

/** Broca: recoger los granos caídos del suelo y echarlos al balde. */
export function RecogerGranos() {
  return (
    <Lienzo titulo="Recoger los granos caídos del suelo">
      <path d="M10 170 Q100 160 190 170" {...T} fill="none" />
      {[[26, 164], [50, 167], [74, 164]].map(([x, y]) => <ellipse key={x} cx={x} cy={y} rx="8" ry="6.5" fill="#7b2a1e" {...T} strokeWidth={2.5} />)}
      {/* balde con granos */}
      <path d="M118 110 L178 110 L170 166 L126 166 Z" fill="#6f8fa8" {...T} />
      <path d="M118 110 Q148 92 178 110" {...T} fill="none" strokeWidth={3} />
      {[[134, 108], [148, 104], [162, 108], [141, 100], [156, 99]].map(([x, y]) => <circle key={`${x}-${y}`} cx={x} cy={y} r="6.5" fill="#7b2a1e" {...T} strokeWidth={2.5} />)}
      {/* mano que pellizca un grano */}
      <path d="M50 62 Q58 46 76 50 L102 58 Q112 62 108 70 Q104 76 94 74 L84 72 L92 90 Q96 100 88 104 Q80 106 76 98 L60 92 Q46 86 50 62 Z" fill="#e8b98c" {...T} strokeWidth={3} />
      <path d="M84 72 L74 74" {...T} strokeWidth={3} />
      <circle cx="88" cy="112" r="7" fill="#7b2a1e" {...T} strokeWidth={2.5} />
      {/* recorrido: del suelo al balde */}
      <path d="M58 150 Q62 122 84 120" {...T} strokeWidth={3} strokeDasharray="2 9" fill="none" stroke="var(--acento)" />
      <path d="M100 100 Q116 78 136 86" {...T} strokeWidth={3} strokeDasharray="2 9" fill="none" stroke="var(--acento)" />
      <path d="M128 78 L138 86 L127 92" {...T} strokeWidth={3.5} fill="none" stroke="var(--acento)" />
      {/* el grano que viaja (solo con movimiento; ver .grano-viaje en estilos.css) */}
      <circle className="grano-viaje" r="6.5" fill="#7b2a1e" {...T} strokeWidth={2.5} />
    </Lienzo>
  );
}

/** Clima: sol tapado y lluvia fuera de tiempo. */
export function Clima() {
  return (
    <Lienzo titulo="Fue el clima">
      <circle cx="70" cy="70" r="28" fill="#f6c443" {...T} />
      {[0, 45, 90, 135, 180, 225, 270, 315].map((a) => (
        <path key={a} d="M70 28 L70 16" transform={`rotate(${a} 70 70)`} {...T} />
      ))}
      <path d="M70 118 Q70 92 96 92 Q104 70 128 74 Q152 74 154 98 Q176 100 176 120 Q176 138 156 138 L88 138 Q70 138 70 118 Z" fill="#e9eef2" {...T} />
      {[[92, 156], [118, 164], [144, 156]].map(([x, y]) => <path key={x} d={`M${x} ${y - 6} l-6 16`} {...T} stroke="#3a7bd5" />)}
    </Lienzo>
  );
}

/** Técnico de la cooperativa (cara del promotor con gorra). Urgente: con aviso. */
export function Tecnico({ urgente = false }: { urgente?: boolean }) {
  return (
    <Lienzo titulo={urgente ? 'El técnico, con urgencia' : 'El técnico de la cooperativa'}>
      <path d="M44 186 Q44 140 100 136 Q156 140 156 186" fill="#3d5a80" {...T} />
      <circle cx="100" cy="92" r="40" fill="#d9a77c" {...T} />
      <path d="M58 82 Q60 44 100 44 Q140 44 142 82 Z" fill="#1f5135" {...T} />
      <path d="M58 82 L162 82" {...T} />
      <circle cx="86" cy="98" r="4.5" fill="var(--trazo)" />
      <circle cx="114" cy="98" r="4.5" fill="var(--trazo)" />
      <path d="M86 116 Q100 126 114 116" {...T} fill="none" />
      {urgente && (
        <g className="late">
          <circle cx="160" cy="46" r="24" fill="var(--urgente)" {...T} />
          <path d="M160 32 L160 50" {...T} stroke="#fff" strokeWidth={6} />
          <circle cx="160" cy="60" r="3.6" fill="#fff" />
        </g>
      )}
    </Lienzo>
  );
}

export function Altavoz() {
  return (
    <svg viewBox="0 0 48 48" aria-hidden="true" className="icono">
      <path d="M8 18 L16 18 L26 9 L26 39 L16 30 L8 30 Z" fill="currentColor" />
      <path className="onda onda-1" d="M32 17 Q37 24 32 31" stroke="currentColor" strokeWidth="3.5" fill="none" strokeLinecap="round" />
      <path className="onda onda-2" d="M36 12 Q45 24 36 36" stroke="currentColor" strokeWidth="3.5" fill="none" strokeLinecap="round" />
    </svg>
  );
}

export function Camara() {
  return (
    <svg viewBox="0 0 48 48" aria-hidden="true" className="icono">
      <path d="M6 16 Q6 12 10 12 L16 12 L20 7 L28 7 L32 12 L38 12 Q42 12 42 16 L42 36 Q42 40 38 40 L10 40 Q6 40 6 36 Z" fill="currentColor" />
      <circle cx="24" cy="25" r="8.5" fill="var(--fondo)" />
      <circle cx="24" cy="25" r="4.5" fill="currentColor" />
    </svg>
  );
}

export function Visto() {
  return (
    <svg viewBox="0 0 48 48" aria-hidden="true" className="icono">
      <circle cx="24" cy="24" r="21" fill="currentColor" />
      <path d="M14 25 L21 32 L34 17" stroke="var(--visto-trazo, var(--fondo))" strokeWidth="5" fill="none" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

/** Estado del envío: nube con visto (ya llegó) o con flecha y borde punteado (guardado, se enviará con señal). */
export function Nube({ esperando }: { esperando: boolean }) {
  return (
    <svg viewBox="0 0 48 48" className={`nube ${esperando ? 'esperando' : 'al-dia'}`} aria-hidden="true">
      <path d="M14 36 Q5 36 5 28 Q5 20 13 19 Q15 10 25 10 Q35 10 37 19 Q44 20 44 28 Q44 36 36 36 Z" />
      {esperando
        ? <path d="M24 31 L24 19 M18 24 L24 18 L30 24" className="signo" />
        : <path d="M17 24 L22 29 L31 19" className="signo" />}
    </svg>
  );
}
