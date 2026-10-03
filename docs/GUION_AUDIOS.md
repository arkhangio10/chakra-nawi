# Guion de los 14 audios

Versión para congelar en **H2** (PLAN §7). Responsable: P4. Fuente de los textos: `contracts/mensajes.example.json`. Si cambia un texto aquí, cambia también allí.

**Antes de enviarlo, falta decidir:** el nombre de la cooperativa que va en `L_INTRO` (hoy dice "Cooperativa X").

---

## Mensaje para el hablante (copiar y pegar en WhatsApp)

> Hola, gracias por ayudarnos. Somos un equipo que hace una aplicación para que las productoras de café de La Convención reciban avisos de la cooperativa **con voz, en quechua**. Necesitamos 14 mensajes cortos grabados por una persona, no por una máquina.
>
> Cómo grabar:
> - Una nota de voz de WhatsApp por mensaje, en un lugar sin ruido (sin radio, sin gallinas cerca 🙂).
> - Habla despacio y con calma, como le hablarías a una tía o una vecina mayor. Cada mensaje dura **8 segundos como máximo**.
> - **No traduzcas palabra por palabra**: dilo como se diría en quechua cusqueño en la chacra. Lo importante es que se entienda.
> - Antes de cada nota, di el código (por ejemplo "R_VERDE"), espera un segundo y luego di el mensaje.
> - Si te equivocas, vuelve a grabar esa nota completa.
>
> Después, otra persona que habla quechua escuchará los audios para confirmar que se entienden. Necesitamos las notas antes de [hora H8]. Los audios se usarán en un prototipo sin fines comerciales y en un video del concurso; si quieres que aparezca tu nombre en los créditos, avísanos.

---

## Los 14 mensajes

| Código | Cuándo suena | Texto en castellano (≤ 8 s) | Intención (para el hablante) |
|---|---|---|---|
| `G_FOTO_TRAMPA` | Antes de la foto, época seca | Vacía la trampa en el cuadrado. Que se vean las cuatro esquinas negras. | Instrucción tranquila, paso a paso |
| `G_FOTO_HOJAS` | Antes de la foto, lluvias | Voltea tres hojas y tómales foto por debajo, sobre la tarjeta. | Instrucción |
| `G_OTRA_VEZ` | Foto oscura o movida | No se ve bien. Acércate a la puerta, hay más luz, y toma la foto otra vez. | Amable; la culpa no es de ella |
| `G_ESPERA` | Mientras el modelo cuenta | Estoy contando, espera un ratito. | Cercano, sin prisa |
| `P_GRANOS` | Pregunta de los granos | Pon un grano en cada círculo. ¿Cuántos tienen huequito? | Pregunta clara; "huequito" = el agujero de la broca |
| `P_ROYA` | Pregunta de la roya | ¿Ves polvo naranja debajo de las hojas? | Pregunta clara |
| `R_VERDE` | Resultado verde | Todo está bien en tu chacra. Sigue cuidándola así. | Tranquilizador |
| `R_BROCA` | Amarillo, broca | Hay broca. Haz repase y recoge los granos caídos al suelo. | Firme pero sin alarma; solo acciones culturales |
| `R_ROYA` | Amarillo, posible roya | Puede ser roya. Ya le mandé tu caso al técnico; él lo confirmará. | Sin asustar; el técnico decide |
| `R_CLIMA` | Amarillo, clima | No es tu chacra, fue el clima. No gastes en remedios. | Quita la culpa y evita un gasto |
| `R_TECNICO` | Técnico (duda) | Esto lo tiene que ver el técnico. Ya le mandé tu caso; él te llamará. | Seguro; no es una mala noticia |
| `R_TECNICO_URGENTE` | Técnico (urgente) | Hay mucha broca. Ya avisé al técnico. Mientras tanto, recoge los granos caídos. | Urgente pero sereno, con una acción concreta |
| `L_INTRO` | Abre cada llamada | Cooperativa X, para Noor. | Para que sepa quién llama y que es para ella |
| `C_CONSENTIMIENTO` | Inscripción | La cooperativa guardará tus fotos y respuestas para que el técnico te ayude. ¿Estás de acuerdo? | Respetuoso; se puede decir que no |

## Reglas del guion

- Ningún mensaje lleva números ni porcentajes (PLAN §3).
- En amarillo solo hay acciones culturales: repase, recojo y raspa. Nada químico ni biológico (PLAN §2).
- Cada audio en quechua lleva en `mensajes.json` el nombre de quien lo validó (`revisado_por`). Sin validación no entra al demo.
- Los audios en castellano los graba el equipo.
- Si en H8 no llegaron las notas: `mms-tts-quz` con `sintetico: true`, rotulado "sintético" en el video (PLAN §11).

## Después de recibirlas (P4)

1. Recortar el código hablado y los silencios.
2. Convertir a Opus: `ffmpeg -i entrada.ogg -ac 1 -c:a libopus -b:a 24k audio/quz/R_VERDE.opus`
3. Llenar `texto_quz`, `revisado_por` y `duracion_s` en `mensajes.json`, y correr `python scripts/validar_contratos.py`.
