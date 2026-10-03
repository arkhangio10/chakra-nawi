"""Tabla binomial de los 20 granos (PLAN §5.3, prueba 2 de §10).

python validacion/binomial.py      → imprime la tabla en Markdown y el límite superior con 0 de 20
"""
from math import comb

N = 20


def p_k(k: int, p: float) -> float:
    return comb(N, k) * p**k * (1 - p) ** (N - k)


def limite_superior_cero(confianza: float = 0.95) -> float:
    """Clopper-Pearson con 0 éxitos: 1 − (α/2)^(1/n) (bilateral al 95%)."""
    return 1 - ((1 - confianza) / 2) ** (1 / N)


def fmt(x: float) -> str:
    return "< 1%" if x < 0.01 else f"{100 * x:.0f}%"


if __name__ == "__main__":
    print(f"Muestra de {N} granos\n")
    print("| Infestación real | P(0 con huequito) | P(1–2) | P(3+) |")
    print("|---|---|---|---|")
    for p, etiqueta in [(0.02, "2%"), (0.05, "5% (umbral INIA)"), (0.10, "10%"), (0.15, "15%")]:
        p0 = p_k(0, p)
        p12 = p_k(1, p) + p_k(2, p)
        print(f"| {etiqueta} | {fmt(p0)} | {fmt(p12)} | {fmt(1 - p0 - p12)} |")
    print(f"\nCon 0 de {N}, límite superior al 95% (Clopper-Pearson bilateral): {100 * limite_superior_cero():.1f}%")
    print(f"(unilateral al 95%: {100 * (1 - 0.05 ** (1 / N)):.1f}%)")
