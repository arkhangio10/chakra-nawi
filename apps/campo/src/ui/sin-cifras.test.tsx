// PLAN §10, prueba 6: cero cifras y cero porcentajes en las pantallas de Noor.
import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render } from '@testing-library/react';
import type { Causa, Estado } from '@chakra/motor';
import { PantallaContando, PantallaFoto, PantallaPregunta, PantallaResultado } from './Pantallas';

const nada = () => {};
const SIN_CIFRAS = /[0-9%]/;

afterEach(cleanup);

function textoVisible(contenedor: HTMLElement): string {
  // Texto + etiquetas accesibles (lo que lee un lector de pantalla también cuenta).
  const etiquetas = [...contenedor.querySelectorAll('[aria-label]')].map((e) => e.getAttribute('aria-label'));
  return `${contenedor.textContent} ${etiquetas.join(' ')}`;
}

describe('pantallas de Noor sin cifras', () => {
  it.each(['trampa', 'hojas'] as const)('foto (%s)', (tipo) => {
    for (const otraVez of [false, true]) {
      const { container } = render(<PantallaFoto tipo={tipo} otraVez={otraVez} alFoto={nada} alEscuchar={nada} />);
      expect(textoVisible(container)).not.toMatch(SIN_CIFRAS);
      cleanup();
    }
  });

  it('contando', () => {
    const { container } = render(<PantallaContando marco={null} cajas={[]} />);
    expect(textoVisible(container)).not.toMatch(SIN_CIFRAS);
  });

  it.each(['granos', 'polvo_naranja'] as const)('pregunta %s', (pregunta) => {
    const { container } = render(<PantallaPregunta pregunta={pregunta} alResponder={nada} alEscuchar={nada} />);
    expect(textoVisible(container)).not.toMatch(SIN_CIFRAS);
  });

  const casos: [Estado, Causa | null][] = [
    ['verde', 'sin_problema'], ['amarillo', 'broca'], ['amarillo', 'roya'], ['amarillo', 'clima_floracion'],
    ['tecnico', 'plantas_viejas'], ['tecnico', null], ['tecnico_urgente', 'broca'],
  ];
  it.each(casos)('resultado %s / %s', (estado, causa) => {
    const { container } = render(<PantallaResultado estado={estado} causa={causa} alEscuchar={nada} alTerminar={nada} />);
    expect(textoVisible(container)).not.toMatch(SIN_CIFRAS);
  });
});
