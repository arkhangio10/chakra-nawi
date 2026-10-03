"""Convierte una foto a RGBA crudo para scripts/probar-foto.test.ts (Node no tiene canvas).

Uso: python apps/campo/scripts/a-rgba.py docs/demo/foto_tarjeta_sintetica.jpg /tmp/foto.rgba
"""
import sys
from PIL import Image

im = Image.open(sys.argv[1]).convert("RGBA")
open(sys.argv[2], "wb").write(im.tobytes())
open(sys.argv[2] + ".dim", "w").write(f"{im.width}x{im.height}")
