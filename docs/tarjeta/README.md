# Tarjeta A5

`tarjeta_A5.pdf`: página 1 = lado A (trampa), página 2 = lado B (granos). Las versiones `.svg` son para editarla. Para regenerarla: `python docs/tarjeta/generar_tarjeta.py`.

## Imprimir (P4)

1. Imprimir **al 100 % ("tamaño real"; nunca "ajustar a la página")**, a doble cara o en dos hojas pegadas espalda con espalda.
2. Medir con una regla la línea gris de abajo: tiene que medir **10 cm**. Si no mide eso, la escala del contador queda mal.
3. Plastificar en mate si se puede (el brillo engaña al control de calidad) y recortar dejando el margen blanco.

## Geometría (la usan P1 y P2)

| Elemento | Medida |
|---|---|
| Marco (gris claro) | 100 × 100 mm, el mismo en los dos lados |
| Esquinas negras | Cuadrados de 10 × 10 mm **por fuera** del marco. El vértice de cada cuadrado que toca el marco es la esquina del marco, y es el punto que usa la homografía |
| Rectificado | Marco → 1216 × 1216 px (ver `contracts/modelo-io.md`) |
| Lado B | 20 círculos de 16 mm de diámetro, 5 columnas × 4 filas, centrados en celdas de 20 × 25 mm |

La tarjeta no lleva texto ni números para Noor. La única leyenda es la de control de impresión, en gris pequeño.
