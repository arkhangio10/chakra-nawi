"""Genera la tarjeta A5 (PLAN §3): lado A = marco de 10×10 cm para lo capturado en la trampa,
lado B = 20 círculos para los granos. Los dos lados tienen las mismas 4 esquinas negras.

Uso:  python docs/tarjeta/generar_tarjeta.py   (requiere reportlab)
Salida: tarjeta_A5.pdf (2 páginas), tarjeta_A5_ladoA.svg, tarjeta_A5_ladoB.svg
"""
from pathlib import Path

from reportlab.lib.colors import Color, black
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

AQUI = Path(__file__).resolve().parent

# Geometría en mm, origen arriba a la izquierda (como en SVG)
ANCHO, ALTO = 148, 210            # A5
MARCO = 100                       # marco de 10×10 cm
X0, Y0 = (ANCHO - MARCO) / 2, 40  # esquina superior izquierda del marco
ESQ = 10                          # lado de cada esquina negra (por fuera del marco)
GRIS = 0.6                        # gris del borde del marco y de los círculos
CIRC_D = 16                       # diámetro de cada círculo (un grano de café cabe holgado)
COLS, FILAS = 5, 4                # 20 círculos
CONTROL_Y = 196                   # línea de control de impresión


def esquinas():
    """Cuadrados negros pegados por fuera a cada esquina del marco.
    El vértice que toca el marco es el punto que usa la homografía."""
    return [
        (X0 - ESQ, Y0 - ESQ), (X0 + MARCO, Y0 - ESQ),
        (X0 - ESQ, Y0 + MARCO), (X0 + MARCO, Y0 + MARCO),
    ]


def circulos():
    paso_x, paso_y = MARCO / COLS, MARCO / FILAS
    return [(X0 + paso_x * (c + 0.5), Y0 + paso_y * (f + 0.5)) for f in range(FILAS) for c in range(COLS)]


def svg(lado: str) -> str:
    g = f"rgb({int(GRIS * 255)},{int(GRIS * 255)},{int(GRIS * 255)})"
    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{ANCHO}mm" height="{ALTO}mm" viewBox="0 0 {ANCHO} {ALTO}">',
        f'<rect width="{ANCHO}" height="{ALTO}" fill="white"/>',
        f'<rect x="{X0}" y="{Y0}" width="{MARCO}" height="{MARCO}" fill="none" stroke="{g}" stroke-width="0.4"/>',
    ]
    p += [f'<rect x="{x}" y="{y}" width="{ESQ}" height="{ESQ}" fill="black"/>' for x, y in esquinas()]
    if lado == "B":
        p += [f'<circle cx="{x}" cy="{y}" r="{CIRC_D / 2}" fill="none" stroke="{g}" stroke-width="0.6"/>'
              for x, y in circulos()]
    p += [
        f'<line x1="{X0}" y1="{CONTROL_Y}" x2="{X0 + MARCO}" y2="{CONTROL_Y}" stroke="{g}" stroke-width="0.3"/>',
        f'<text x="{ANCHO / 2}" y="{CONTROL_Y + 5}" font-size="3" fill="{g}" text-anchor="middle" font-family="sans-serif">'
        f'Lado {lado} · imprimir al 100 %: esta línea debe medir 10 cm</text>',
        "</svg>",
    ]
    return "\n".join(p) + "\n"


def pdf(ruta: Path):
    c = canvas.Canvas(str(ruta), pagesize=(ANCHO * mm, ALTO * mm))
    c.setTitle("Chakra Ñawi · tarjeta A5")
    gris = Color(GRIS, GRIS, GRIS)

    def y(v):  # SVG (arriba→abajo) a PDF (abajo→arriba)
        return (ALTO - v) * mm

    for lado in ("A", "B"):
        c.setStrokeColor(gris)
        c.setLineWidth(0.4 * mm)
        c.rect(X0 * mm, y(Y0 + MARCO), MARCO * mm, MARCO * mm, stroke=1, fill=0)
        c.setFillColor(black)
        for x, yy in esquinas():
            c.rect(x * mm, y(yy + ESQ), ESQ * mm, ESQ * mm, stroke=0, fill=1)
        if lado == "B":
            c.setLineWidth(0.6 * mm)
            for x, yy in circulos():
                c.circle(x * mm, y(yy), CIRC_D / 2 * mm, stroke=1, fill=0)
        c.setLineWidth(0.3 * mm)
        c.line(X0 * mm, y(CONTROL_Y), (X0 + MARCO) * mm, y(CONTROL_Y))
        c.setFillColor(gris)
        c.setFont("Helvetica", 8.5)
        c.drawCentredString(ANCHO / 2 * mm, y(CONTROL_Y + 5),
                            f"Lado {lado} · imprimir al 100 %: esta línea debe medir 10 cm")
        c.showPage()
    c.save()


if __name__ == "__main__":
    pdf(AQUI / "tarjeta_A5.pdf")
    for lado in ("A", "B"):
        (AQUI / f"tarjeta_A5_lado{lado}.svg").write_text(svg(lado), encoding="utf-8")
    print("listo:", *sorted(p.name for p in AQUI.glob("tarjeta_A5*")))
