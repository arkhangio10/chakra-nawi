# API + panel del técnico de Chakra Ñawi (FastAPI + SQLite). Se construye desde la raíz del repo:
#   docker build -t chakra-nawi-api .
#   docker run -p 8000:8000 -v chakra-datos:/data --env-file api/.env chakra-nawi-api
# Lo que cambia (SQLite, fotos y, si se usa, fincas_privadas.json con los teléfonos) vive en el volumen /data.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CHAKRA_DB=/data/chakra.sqlite \
    CHAKRA_FOTOS=/data/uploads \
    CHAKRA_FINCAS_PRIVADAS=/data/fincas_privadas.json

WORKDIR /app
COPY api/requirements.txt api/requirements.txt
RUN pip install --no-cache-dir -r api/requirements.txt

# Solo lectura: contratos (validación de casos), fichas, audios (.mp3 para Twilio), panel y reglas del motor
COPY contracts/ contracts/
COPY fichas/ fichas/
COPY audio/ audio/
COPY apps/panel/ apps/panel/
COPY packages/motor/ packages/motor/
COPY api/ api/

# Corre como root a propósito: los discos de Render y los volúmenes de Fly se montan como root
RUN mkdir -p /data
VOLUME ["/data"]
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
    CMD python -c "import os,urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\",\"8000\")}/salud', timeout=4)"
# Render y Fly pasan el puerto en $PORT; --proxy-headers para que las redirecciones salgan en https
CMD ["sh", "-c", "exec uvicorn api.app:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
