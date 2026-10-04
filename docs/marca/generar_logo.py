"""Logo "Ojo de andenes": redibujo vectorial del boceto de Gemini. `python generar_logo.py` reescribe los SVG de esta carpeta.

completo(): con la greca escalonada (ícono de la app, 192/512 px, lienzo).
simple():   sin greca y con el ojo más grande (favicon y cabeceras, <= 48 px).
"""
import os

CREMA, HOJA, CEREZA, TERRACOTA, SOL = '#f4f1e8', '#1f5135', '#b0322a', '#b4471e', '#f2b705'


def _greca_lado():
    """Un lado de la greca: esquina redondeada y cinco pirámides escalonadas que miran hacia adentro."""
    d = ['M10 22 Q10 10 22 10']
    x = 22.0
    for _ in range(5):  # cada unidad mide 15.2 px: llano, baja dos escalones, fondo, sube dos
        for dx, dy in ((3.6, 0), (0, 2.6), (2.4, 0), (0, 2.6), (3.2, 0), (0, -2.6), (2.4, 0), (0, -2.6), (3.6, 0)):
            x += dx
            d.append(f'h{dx:g}' if dx else f'v{dy:g}')
    d.append('L98 10')
    return ' '.join(d)


def _greca(pid):
    lado = _greca_lado()
    return (f'<g fill="none" stroke="{TERRACOTA}" stroke-width="2.2" stroke-linejoin="round" stroke-linecap="round">'
            f'<path id="{pid}-lado" d="{lado}"></path>'
            f'<use href="#{pid}-lado" transform="rotate(90 60 60)"></use>'
            f'<use href="#{pid}-lado" transform="rotate(180 60 60)"></use>'
            f'<use href="#{pid}-lado" transform="rotate(270 60 60)"></use></g>')


def _sol(cx, cy, r):
    rayos = ''.join(
        f'<path d="M{cx} {cy - r - 3} L{cx} {cy - r - 7}" transform="rotate({a} {cx} {cy})"></path>' for a in range(0, 360, 45))
    return (f'<g stroke="#e0a106" stroke-width="2.4" stroke-linecap="round">{rayos}</g>'
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{SOL}"></circle>'
            f'<path d="M{cx - 4} {cy - 1} q1.5 -2 3 0 M{cx + 1} {cy - 1} q1.5 -2 3 0 M{cx - 3} {cy + 2.5} q3 3 6 0" '
            'stroke="#9a5a00" stroke-width="1.4" fill="none" stroke-linecap="round"></path>')


def _brote(x, y, s=1.0):
    return (f'<g transform="translate({x} {y}) scale({s})">'
            '<path d="M0 0 V-7" stroke="#2e6b31" stroke-width="1.4" stroke-linecap="round"></path>'
            '<path d="M0 -4 Q-4 -7 -5 -3 Q-2 -2 0 -4 Z M0 -5 Q4 -8 5 -4 Q2 -3 0 -5 Z" fill="#4f9a45"></path>'
            f'<circle cx="-2" cy="-8" r="1.2" fill="{CEREZA}"></circle><circle cx="2" cy="-8.5" r="1.2" fill="{CEREZA}"></circle></g>')


def _ojo(pid, brotes=True):
    contorno = 'M21 62 Q60 26 99 62 C99 86 84 101 60 101 C36 101 21 86 21 62 Z'
    return (f'<defs><clipPath id="{pid}-ojo"><path d="{contorno}"></path></clipPath></defs>'
            f'<path d="{contorno}" fill="#fffdf6"></path>'
            f'<g clip-path="url(#{pid}-ojo)">'
            '<rect x="0" y="62" width="120" height="60" fill="#3e8e41"></rect>'
            '<path d="M26 62 H30 V70 H36 V78 H43 V87 H77 V78 H84 V70 H90 V62 Z" fill="#8cc063"></path>'
            '<path d="M36 62 H41 V68 H47 V74 H53 V79 H67 V74 H73 V68 H79 V62 Z" fill="#c4e29b"></path>'
            '</g>'
            + ((_brote(30, 61) + _brote(90, 61) + _brote(40, 77, .8) + _brote(80, 77, .8)) if brotes else '') +
            f'<path d="{contorno}" fill="none" stroke="{HOJA}" stroke-width="3" stroke-linejoin="round"></path>'
            f'<circle cx="60" cy="57" r="14.5" fill="{CEREZA}" stroke="#7d1f19" stroke-width="1.8"></circle>'
            '<path d="M49.5 53 Q52 47 58 45.5" stroke="#ffffff" stroke-width="2.2" fill="none" stroke-linecap="round" opacity=".55"></path>'
            '<path d="M66 47 L67.2 51 L71 52.2 L67.2 53.4 L66 57.4 L64.8 53.4 L61 52.2 L64.8 51 Z" fill="#ffffff"></path>')


def completo(size=None, pid='ca', label='Chakra Ñawi'):
    wh = f' width="{size}" height="{size}"' if size else ''
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120"{wh} role="img" aria-label="{label}">'
            f'<rect width="120" height="120" rx="26" fill="{CREMA}"></rect>'
            + _greca(pid) + _sol(60, 30, 7.5) + _ojo(pid) + '</svg>')


def simple(size=None, pid='cs', label='Chakra Ñawi', fondo=CREMA):
    """Para tamaños chicos: sin greca ni brotes, el ojo llena el cuadro."""
    wh = f' width="{size}" height="{size}"' if size else ''
    rect = f'<rect width="120" height="120" rx="26" fill="{fondo}"></rect>' if fondo else ''
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120"{wh} role="img" aria-label="{label}">{rect}'
            '<g transform="translate(60 60) scale(1.17) translate(-60 -56.75)">' + _sol(60, 27, 7.5) + _ojo(pid, brotes=False) + '</g></svg>')


if __name__ == '__main__':
    salida = os.path.dirname(os.path.abspath(__file__))
    open(os.path.join(salida, 'logo-completo.svg'), 'w', encoding='utf-8').write(completo())
    open(os.path.join(salida, 'logo-simple.svg'), 'w', encoding='utf-8').write(simple())
    # Sin fondo, para la barra de la app (apps/campo/public/logo-cabecera.svg)
    open(os.path.join(salida, 'logo-cabecera.svg'), 'w', encoding='utf-8').write(simple(fondo=None, pid='cab'))
    print('ok')
