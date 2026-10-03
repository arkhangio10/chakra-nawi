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

function Cereza({ x, y, s = 1, hueco = false }: { x: number; y: number; s?: number; hueco?: boolean }) {
  return (
    <g transform={`translate(${x} ${y}) scale(${s})`}>
      <ellipse cx="0" cy="0" rx="26" ry="30" fill="#b0322a" {...T} />
      <ellipse cx="-9" cy="-10" rx="6" ry="9" fill="#e07a6e" opacity=".7" />
      <circle cx="0" cy="-24" r="7" fill="#7d1f19" {...T} strokeWidth={3} />
      {hueco && <circle cx="0" cy="-24" r="3.6" fill="#120a08" />}
    </g>
  );
}

/** Grano de café: sano, con huequito en la corona, o un montón con huequitos. */
export function Granos({ tipo }: { tipo: 'sano' | 'pocos' | 'muchos' }) {
  const titulo = { sano: 'Granos sanos', pocos: 'Pocos granos con huequito', muchos: 'Muchos granos con huequito' }[tipo];
  return (
    <Lienzo titulo={titulo}>
      {tipo === 'sano' && <><Cereza x={72} y={110} /><Cereza x={130} y={104} /></>}
      {tipo === 'pocos' && <><Cereza x={72} y={110} hueco /><Cereza x={130} y={104} /></>}
      {tipo === 'muchos' && (
        <>
          <Cereza x={60} y={84} s={0.8} hueco /><Cereza x={102} y={70} s={0.8} hueco /><Cereza x={144} y={88} s={0.8} hueco />
          <Cereza x={78} y={136} s={0.8} hueco /><Cereza x={124} y={138} s={0.8} hueco />
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

export function NoSe() {
  return (
    <Lienzo titulo="No sé">
      <circle cx="100" cy="100" r="62" fill="#f1d9b5" {...T} />
      <path d="M76 78 Q84 70 92 78 M108 78 Q116 70 124 78" {...T} fill="none" />
      <circle cx="84" cy="94" r="5" fill="var(--trazo)" />
      <circle cx="116" cy="94" r="5" fill="var(--trazo)" />
      <path d="M84 128 Q100 120 116 128" {...T} fill="none" />
      <path d="M150 52 Q150 34 166 34 Q182 34 182 50 Q182 62 168 66 L168 76" {...T} fill="none" stroke="var(--acento)" />
      <circle cx="168" cy="90" r="4" fill="var(--acento)" />
    </Lienzo>
  );
}

/** Verde: planta sana con cerezas. */
export function PlantaSana() {
  return (
    <Lienzo titulo="Planta de café sana">
      <path d="M100 180 L100 70" {...T} fill="none" />
      {[[-1, 150], [1, 128], [-1, 106], [1, 86]].map(([lado, y]) => (
        <path key={y} d={`M100 ${y} q${lado * 30} -20 ${lado * 62} -6 q${lado * -30} 24 ${lado * -62} 6 Z`} fill="#5f9e4c" {...T} strokeWidth={3} />
      ))}
      <path d="M100 70 q-14 -30 0 -48 q14 18 0 48 Z" fill="#5f9e4c" {...T} strokeWidth={3} />
      {[[78, 140], [124, 118], [84, 98]].map(([x, y]) => <circle key={x} cx={x} cy={y} r="8" fill="#b0322a" {...T} strokeWidth={2.5} />)}
    </Lienzo>
  );
}

/** Broca: recoger los granos caídos del suelo. */
export function RecogerGranos() {
  return (
    <Lienzo titulo="Recoger los granos caídos del suelo">
      <path d="M14 164 Q100 152 186 164" {...T} fill="none" />
      {[[48, 156], [72, 160], [132, 158], [156, 155]].map(([x, y]) => <ellipse key={x} cx={x} cy={y} rx="9" ry="7" fill="#7b2a1e" {...T} strokeWidth={2.5} />)}
      <path d="M86 46 L86 104 Q86 128 104 132 L122 132 Q140 128 140 106 L140 76 Q140 68 132 68 Q124 68 124 76 L124 92 L124 60 Q124 52 116 52 Q108 52 108 60 L108 90 L108 50 Q108 42 100 42 Q92 42 92 50 L92 94 L92 62 Q92 54 86 54 Z" fill="#e8b98c" {...T} strokeWidth={3} />
      <ellipse cx="114" cy="146" rx="10" ry="8" fill="#7b2a1e" {...T} strokeWidth={2.5} />
      <path d="M114 134 L114 140" {...T} strokeWidth={3} />
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
        <g>
          <circle cx="160" cy="46" r="24" fill="#e8710a" {...T} />
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
      <path d="M32 17 Q37 24 32 31 M36 12 Q45 24 36 36" stroke="currentColor" strokeWidth="3.5" fill="none" strokeLinecap="round" />
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
