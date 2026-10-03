# Chakra Ñawi · Plan de ejecución

Versión 1.0 · 3 oct 2026 · Resultado de un debate en dos rondas entre cuatro roles: juez del World Bank, tech lead de hackathon, especialista en UX para baja alfabetización y agrónomo/científico de datos.

**Este documento manda.** Si algo de `ARCHITECTURE.md` lo contradice, gana este plan.

---

## 1. Objetivo

> **Chakra Ñawi es un triaje que prioriza las visitas del técnico, no un diagnóstico autónomo.** Cada dos semanas, sin internet, convierte la foto de la trampa y una pregunta con dibujos en un semáforo con voz en quechua para Noor. Los casos que necesitan una persona van al técnico de la cooperativa.

La decisión que mejora: **¿qué hago esta semana en mi chacra: nada, repase y recojo, o llamar al técnico?**

### Brújula anti-desvío

Antes de empezar cualquier tarea, responder las cinco preguntas. Si alguna da "no", la tarea va a `docs/LO_QUE_SIGUE.md` y **no se construye**.

1. ¿Aparece en el demo o en el video?
2. ¿Lo necesita Noor, o el técnico para atenderla?
3. ¿Respeta el modo offline del teléfono?
4. ¿Está en la lista de "dentro" (sección 3)?
5. ¿Cabe antes del feature freeze (H12)?

---

## 2. Decisiones del debate

| Tema | Decisión | Origen | Por qué |
|---|---|---|---|
| Rol del producto | Triaje para el técnico, no diagnóstico | Agrónomo | Es lo que se puede defender ante un panel experto |
| Evidencia de broca | **Opción C**: la trampa (YOLO) da solo la *tendencia*; la pregunta "de 20 granos, ¿cuántos con huequito?" es la evidencia fuerte | Consenso de los 4 | **No existe un umbral de SENASA por trampa.** La trampa mide vuelo, no infestación. El indicador oficial es el % de frutos brocados (INIA: 5% de daño económico) |
| Opciones de la pregunta de granos | **0 / 1–2 / 3 o más**, con dibujos y "no sé" | Agrónomo y UX (el tech lead proponía 0/1/2+) | 1 de 20 tiene mucho ruido de muestreo (ver §5.3). Los dibujos de UX encajan con estos cortes |
| Estacionalidad | `config.json` por mes que cambia **el peso** de cada evidencia, nunca apaga causas. Mismas 3 pantallas | Consenso | El 3 de octubre las trampas se están retirando, y un jurado agrónomo lo notaría. El demo se presenta como "caso de agosto" |
| Causas | 4 causas + "otra causa" → técnico. Sin alternancia ni abono como causas | Juez y UX (el agrónomo pedía más) | Cada causa sin datos agrega supuestos. La edad y la alternancia se preguntan una vez, en la inscripción |
| NASA y satélite | En el motor: **CHIRPS v3** (lluvia) + **NASA POWER solo temperatura** corregida por altitud (actualización: la anomalía de días de lluvia también usa `PRECTOTCORR` de NASA POWER, ver §5.1). Fuera del motor: NDVI. Opcional: MODIS (NASA) para la lámina de 2013 | Consenso | Cumple "cruzar NASA y satélite" de forma defendible. La humedad de NASA POWER (celdas de ~55 km) no se sostiene, y el NDVI bajo sombra con 80–90% de nubes tampoco |
| Noticias | `alertas_activas.json` **hecho a mano**: 3–5 alertas oficiales con URL y cita literal. Sin extractor LLM | Consenso | Saca un LLM del sistema y una semana de trabajo del camino crítico. La idea de usar noticias se conserva |
| Llamada al teléfono básico | **Obligatoria**, en su forma mínima: un `<Play>` disparado por un botón. Cuenta de Twilio pagada en H0 | Consenso (el tech lead la subió de extra a obligatoria) | Es el único canal que llega directo a Noor. Sin ella, la usuaria real es la hija |
| Cámara | `<input capture="environment">` + **tarjeta A5 con 4 esquinas negras** | Tech lead y UX | Foto nativa a resolución completa (la broca mide 1,7 mm). Las esquinas dan escala, recorte y control de calidad |
| Datos del contador | Fotos propias de **escarabajos oscuros pequeños sobre la tarjeta blanca** (gorgojos de granos almacenados) + sintéticos. Yellow Sticky Traps solo para probar el pipeline. Wadhwani queda fuera | Agrónomo, con ajuste del tech lead | Yellow Sticky Traps tiene el contraste invertido y Wadhwani son polillas 10 veces más grandes. **El error de conteo con un sustituto no se presenta como desempeño en broca** |
| Contador clásico de manchas | Se usa como métrica de comparación. La regla "si difiere >30% → técnico" solo se activa si se calibra | Juez | Sin calibrar podría mandar al técnico la mitad de los casos |
| Pregunta adaptativa | "La segunda pregunta solo si puede cambiar el color" | UX y juez | Es simple y honesta. **No se vende como IA** |
| Latencia | Meta ≤ 10 s, aceptable ≤ 15 s. Suena `G_ESPERA` y las cajas aparecen sobre cada broca a medida que se procesa cada mosaico | Tech lead y UX | Sin silencio para Noor, y la IA queda a la vista en el video |
| Recomendaciones | En amarillo, **solo acciones culturales** (repase, recojo de granos caídos, raspa). Lo químico o biológico, siempre a través del técnico | UX y agrónomo | Guardrail. Una falsa alarma cuesta poco |
| Validación | Error de conteo · curva cobertura–precisión con casos independientes · sensibilidad ±50% · tabla binomial · usabilidad · prueba de "cero cifras". **Sin backtest de MIDAGRI** | Consenso | Evita la validación circular. Cabe en 24 h |

---

## 3. Alcance cerrado

### Dentro (MVP)

- [ ] PWA offline de 3 pantallas, instalable, que funciona en modo avión en un Android barato real
- [ ] Contador YOLO de broca (ONNX) por mosaicos, con cajas que aparecen y `G_ESPERA`
- [ ] Control de calidad de la foto (esquinas, brillo, nitidez), con 2 reintentos como máximo
- [ ] Motor TypeScript: 4 causas + "otra", pesos por temporada, tope de LR, reglas con fuente y tipo
- [ ] Preguntas con dibujos: sí / no / no sé, y 0 / 1–2 / 3+ granos
- [ ] Semáforo: verde · amarillo (broca, roya o clima) · técnico (duda) · técnico (urgente)
- [ ] 14 audios grabados por personas (quechua cusqueño y castellano), validados por un segundo hablante
- [ ] Ficha de 5 fincas de ejemplo: CHIRPS v3 + NASA POWER T2M + alertas manuales
- [ ] Cola offline → `POST /casos` idempotente → panel de 1 página
- [ ] Panel: lista por prioridad, foto con cajas, reglas que se aplicaron con su fuente, botón "llamar a Noor"
- [ ] Llamada real a un teléfono básico con el audio en quechua
- [ ] Tarjeta A5 impresa: marco de 10×10 cm por un lado y 20 círculos por el otro
- [ ] README, `FUENTES.md`, `LIMITES_DE_DATOS.md`, video de 4 minutos

### Fuera (va a `LO_QUE_SIGUE.md` y al pitch)

NDVI de Sentinel-2 en el motor · extractor de noticias con LLM · backtest de MIDAGRI · Leaflet y mapas · scheduler y horarios de llamada · Background Sync · ETag · modo de registro en la app · precio de referencia · clasificador de hojas · foto de frutos (dataset de Chaullay) · suelo y altitud · varias regiones o cultivos.

### Prohibido durante el hackathon

Cambiar los contratos después de H1 sin acuerdo de los cuatro · agregar pantallas · mostrar números en las pantallas de Noor · agregar causas · presentar resultados del sustituto como desempeño en broca.

---

## 4. Flujo final del usuario

**Inscripción** (una vez, en la cooperativa, la hace el técnico):
- Finca precargada, idioma de los audios y número de Noor (solo en el servidor).
- Edad de las plantas y si el año pasado cosechó mucho.
- **Consentimiento oral de Noor** en quechua, grabado.
- Se guarda "COOPERATIVA" en los contactos de su teléfono y se hace una llamada de prueba para que conozca la voz.

**Kit del sábado:** el frasco con lo capturado en la trampa, 20 granos (2 por planta, en 10 plantas, recorriendo en X) y la tarjeta A5.

| Pantalla | Época seca (may–oct) | Lluvias (nov–abr) |
|---|---|---|
| 1. Foto | Audio: "Vacía la trampa en el cuadrado; que se vean las 4 esquinas". Cámara nativa → control de calidad → `G_ESPERA` → cajas sobre cada broca | Audio: foto de 3 hojas por debajo. **No la analiza la IA**; queda como evidencia para el técnico |
| 2. Pregunta | "Pon un grano en cada círculo. ¿Cuántos tienen huequito?" → [sano] [1–2] [montón] [no sé] | "¿Ves polvo naranja debajo de las hojas?" → [sí] [no] [no sé] |
| | La segunda pregunta aparece solo si puede cambiar el color | |
| 3. Resultado | Semáforo + dibujo + audio automático + botón "otra vez". Sin cifras ni historial | Igual |

**Después:** el caso queda guardado y se envía cuando hay señal. El técnico lo ve en el panel y llama a Noor; en el demo, con el botón. La llamada dice "Cooperativa X, para Noor", repite el mensaje dos veces y dura 25 s como máximo. Si el resultado es verde, también hay llamada corta, para que Noor sepa que todo funcionó.

---

## 5. Motor de diagnóstico

### 5.1 Evidencias y peso según la época

| Evidencia | Fuente | Causa | May–jul (cosecha) | Ago–oct (fin de la seca) | Nov–abr (lluvias) |
|---|---|---|---|---|---|
| `E_TRAMPA_TENDENCIA` (conteo frente al anterior) | YOLO | broca | media | **plena**, con LR ≤ 2 | ≈ 1 (ignorar) |
| `E_GRANOS` (0 / 1–2 / 3+) | Pregunta | broca | plena | plena si hay fruto atacable | plena desde ene |
| `E_POLVO_NARANJA` | Pregunta | roya | media | baja | **plena** |
| `E_LLUVIA_DIAS` (anomalía de días ≥ 1 mm en nov–abr frente a 1991–2020) | NASA POWER `PRECTOTCORR` | roya | baja | baja | plena |
| `E_TEMP_ROYA` (anomalía de días con T2M corregida por altitud en 17–25 °C, últimos 90, frente a la misma ventana en 1991–2020) | NASA POWER | roya | media | media | plena |
| `E_LLUVIA_FLORACION` (anomalía sep–nov de la campaña anterior, por falta o por exceso) | CHIRPS v3 | clima | plena | plena | media |
| `E_CALOR_FLORACION` (Tmax en floración) | NASA POWER | clima | plena | plena | media |
| `E_EDAD` (> 20 años y sin recepa; dato de la inscripción) | Registro | plantas viejas | prior | prior | prior |
| `A_REGIONAL` | `alertas_activas.json` | según la alerta | solo prior | solo prior | solo prior |

- **Tope de LR combinado por causa: 10**, para no contar dos veces evidencias que dependen entre sí.
- Corrección por altitud: −6,5 °C por km desde la cota de la celda de NASA POWER.
- La roya usa **anomalías, no valores absolutos**: La Convención es húmeda todos los años (140–156 días ≥ 1 mm en las 5 fincas), así que lo que informa es si este año se sale de lo normal. Cada anomalía compara una serie consigo misma; cortes de ≈ +1 desviación estándar interanual (`rules.json`, `python -m pipeline.ficha.historico`). Es una **señal regional del año**: las 5 fincas comparten una celda de NASA POWER.
- Floración y cosecha de La Convención según literatura regional (±1 mes por altitud). Hay que confirmarlo con COCLA.

### 5.2 Decisión

| Estado | Condición | Audio |
|---|---|---|
| 🟢 Verde | `P(sin_problema) ≥ 0,6` **y** granos ≠ "no sé" (0 granos con huequito nunca da verde por sí solo) | `R_VERDE` |
| 🟡 Amarillo | Causa principal ≥ 0,5 con ventaja ≥ 0,15, y la causa es broca, roya o clima | `R_BROCA`, `R_ROYA` o `R_CLIMA` |
| 👤 Técnico (urgente) | Granos 3+ en etapa de fruto atacable | `R_TECNICO_URGENTE` |
| 👤 Técnico | Cualquier otro caso: duda, plantas viejas, "otra causa" o conteo dudoso | `R_TECNICO` |

### 5.3 Por qué 0 / 1–2 / 3+ (honestidad estadística)

Muestra de 20 granos, distribución binomial:

| Infestación real | P(0 con huequito) | P(1–2) | P(3+) |
|---|---|---|---|
| 2% | 67% | 33% | < 1% |
| 5% (umbral INIA) | 36% | 57% | 8% |
| 15% | 4% | 37% | 60% |

Con 0 de 20, la infestación real todavía puede llegar al **16,8%** (límite superior de Clopper-Pearson, bilateral al 95%; el unilateral al 95% da 13,9%). **Por eso "0" nunca da verde solo.** Esta tabla va tal cual en el README y en una lámina.

---

## 6. Datos y modelos

| Pieza | Plan A | Plan B | Licencia |
|---|---|---|---|
| Contador | YOLOv8n/11n (no YOLO26: su salida es distinta), mosaicos de 640, ONNX | Solo el contador clásico de manchas | AGPL-3.0 → repositorio público |
| Datos de entrenamiento | Fotos propias de gorgojos sobre la tarjeta, contados a mano, + montajes sintéticos | Pipeline probado con Yellow Sticky Traps (CC0), declarado como prueba del pipeline | Propias / CC0 |
| Prueba con broca real | 3 fotos completas de CATIE (con CIRAD; GitHub SVMendoza), **solo con permiso** | Solo resultados con el sustituto, declarados como tales | Pedir por correo en H0 |
| Contactos para el futuro | CATIE (con CIRAD); laboratorio TESLA de UNSAAC (dataset de frutos de Chaullay) | — | — |
| Lluvia | CHIRPS v3, COG mensuales, leyendo solo el recorte de Cusco. Anomalía de días de lluvia: NASA POWER `PRECTOTCORR` (CHIRPS diario no tiene una climatología 1991–2020 que se pueda leer a tiempo) | PISCO de SENAMHI | Pública |
| Temperatura | NASA POWER API diaria `T2M`, `T2M_MAX`, `T2M_MIN` | — | Pública |
| Alertas | 3–5 alertas oficiales a mano (SENASA, SENAMHI, ENFEN) con URL y cita literal | Ninguna; el motor funciona igual | Citadas |
| Voz | Grabación humana | `mms-tts-quz`, rotulado "sintético" | CC-BY-NC (uso no comercial) |

---

## 7. Audios (14, de 8 s como máximo cada uno)

| Código | Uso |
|---|---|
| `G_FOTO_TRAMPA` | Instrucción de la foto en época seca |
| `G_FOTO_HOJAS` | Instrucción de la foto en lluvias |
| `G_OTRA_VEZ` | Foto oscura o movida ("acércate a la puerta, hay más luz") |
| `G_ESPERA` | "Estoy contando, espera un ratito" |
| `P_GRANOS` | Pregunta de los 20 granos |
| `P_ROYA` | Pregunta del polvo naranja |
| `R_VERDE` | Todo bien |
| `R_BROCA` | Broca: repase y recojo de granos caídos |
| `R_ROYA` | Posible roya: el técnico confirmará |
| `R_CLIMA` | "No es tu chacra, fue el clima; no gastes en remedios" |
| `R_TECNICO` | "Esto lo tiene que ver el técnico. Ya le mandé tu caso; él te llamará" |
| `R_TECNICO_URGENTE` | "Hay mucha broca. Ya avisé al técnico. Mientras tanto, recoge los granos caídos" |
| `L_INTRO` | "Cooperativa X, para Noor" (abre cada llamada) |
| `C_CONSENTIMIENTO` | Consentimiento en la inscripción |

El guion se **congela en H2** y se envía al hablante, que manda notas de voz por WhatsApp antes de H8. Luego se convierten a Opus, y en `mensajes.json` cada audio lleva el campo `revisado_por`.

---

## 8. Equipo y plan por horas

Roles: **P1 App** (PWA + motor) · **P2 ML** (contador) · **P3 Datos/API** (ficha, API, panel, Twilio) · **P4 Producto** (audio, tarjeta, dibujos, evidencia, casos independientes, usabilidad, video).
Con 3 personas: P2 hace la ficha mientras entrena el modelo, y P4 se queda con Twilio.

| Bloque | P1 App | P2 ML | P3 Datos/API | P4 Producto | Hecho cuando… |
|---|---|---|---|---|---|
| **H0–1** | Contratos (con P3) | Elegir datos; conseguir gorgojos | Contratos; **Twilio pagado + Perú habilitado** | Correos a CATIE (con CIRAD) y UNSAAC; buscar el dato de la ENA; ubicar al hablante | `contracts/` con ejemplos válidos; entrada y salida del ONNX congeladas |
| **H1–4** | PWA de 3 pantallas + `onnxruntime-web` con YOLO COCO de prueba; COOP/COEP; límite de precache aumentado | Fotos sobre la tarjeta + conteo manual + sintéticos; mosaicos | Ficha de 5 fincas (CHIRPS v3 + POWER) | Tarjeta A5 y dibujos; guion de audios congelado (H2) | **El Android real infiere en modo avión y muestra ms por mosaico** |
| **H4–8** | Motor TS + `rules.json` + `config.json` de temporadas + tests | Entrenar (Colab/Kaggle T4) → ONNX → error de conteo | API de 2 endpoints desplegada; `alertas_activas.json` | Audios → Opus, `mensajes.json`; escribir 20 casos independientes | Tests del motor en verde · modelo exportado con su error · **el teléfono básico ya sonó (≤ H6)** |
| **H8–12** | Integrar modelo, mosaicos, NMS, cajas progresivas, cola y audio | Contador clásico; medir cuánto difiere del YOLO; umbral de "dudoso" | Panel de 1 página + botón de llamada | README, FUENTES, LIMITES; agendar la prueba de usabilidad | **Flujo completo: offline → sincroniza → panel → teléfono suena. FEATURE FREEZE** |
| **H12–16** | Bugs; prueba de "cero cifras"; selector de fecha en modo técnico | Figuras: error de conteo, cajas, 3 fallos | Sensibilidad ±50%; curva cobertura–precisión. Lámina NDVI/MODIS **solo si queda listo antes de H14** | Prueba de usabilidad grabada | Los 4 estados funcionan 3 veces seguidas. **CODE FREEZE H16, tag v1.0** |
| **H16–22** | Grabar el demo (con P4) | Lámina de datos y límites | Despliegue final, enlace público | Edición, subtítulos, voz en off | Video de 4 min subido · repositorio público · enlace funcionando |
| **H22–24** | Reserva | Reserva | Reserva | Envío | Entregado |

**Turnos para dormir:** P2 duerme mientras entrena el modelo (H5–H7). P3 duerme 3 h después de H16. Nadie duerme entre H8 y H12.

---

## 9. Lo no negociable en el demo y el video

1. Android barato real con el **modo avión visible**: foto → cajas → resultado en ≤ 15 s.
2. El **tamaño total medido** en pantalla: modelo + runtime + audios.
3. El **fail-safe en vivo**: foto mala o caso dudoso → audio del técnico → el caso aparece en el panel cuando vuelve la señal.
4. Voz en quechua **grabada por una persona**, con subtítulos.
5. Un **teléfono básico real** que suena y reproduce el mensaje.
6. La frase del problema exacta, con evidencia peruana verificada (§12).
7. La lámina de datos: licencias, límites, error de conteo (separando sustituto y broca), cuántas reglas son supuestos y la tabla binomial.
8. El cambio de época: "caso de agosto" frente a "caso de enero", con el selector de fecha.
9. Nuestra mirada sobre localizar la IA, con sus contrapartes: variantes del quechua, que el modelo no ha visto broca peruana y que dependemos del teléfono de la hija.

### Guion del video (4:00)

| Tiempo | Bloque |
|---|---|
| 0:00–0:20 | Frase del problema |
| 0:20–0:50 | El día de Noor: sábado con la hija, miércoles con la llamada |
| 0:50–2:30 | Demo: modo avión → foto → cajas → granos → semáforo y audio → fail-safe → panel → el teléfono suena |
| 2:30–3:05 | Qué hace la IA y por qué un SMS de calendario no alcanza; guardrails |
| 3:05–3:35 | Datos, límites y validación (curva cobertura–precisión, error de conteo, tabla binomial) |
| 3:35–4:00 | Qué significa localizar la IA para nosotros, y lo que sigue |

---

## 10. Validación (orden por valor y costo)

| # | Prueba | Responsable | Costo | Qué se muestra |
|---|---|---|---|---|
| 1 | Sensibilidad: LR ±50% → ¿cambia la causa o el color? | P3 | 1 h | % de casos estables |
| 2 | Tabla binomial de los 20 granos | P4 | 15 min | Tabla §5.3 |
| 3 | Error del contador frente al conteo manual (sustituto y fotos propias), y frente al contador clásico | P2 | 2 h | Error medio por densidad + 3 fallos |
| 4 | 20 casos escritos por P4 (que no programa el motor) → curva cobertura–precisión | P3 + P4 | 2 h | Curva: % derivado al técnico frente a aciertos |
| 5 | Prueba de usabilidad (1–2 parejas: persona mayor + familiar joven) | P4 | 1 h | x/n completan sin ayuda, tiempo mediano, repetición correcta del mensaje |
| 6 | Prueba automática de "cero % y cero cifras" en las pantallas de Noor | P1 | 20 min | Test en verde |
| 7 | *Opcional:* lámina de 2013 (producción en La Convención, anomalía CHIRPS, NDVI de MODIS), rotulada como "consistente o no consistente" | P3 | Solo si está lista antes de H14 | Una figura |

---

## 11. Riesgos y planes B

| Riesgo | Señal de alarma | Plan B |
|---|---|---|
| No hay insectos para fotografiar | Sin fotos propias en H3 | Solo sintéticos + pipeline con Yellow Sticky Traps, declarado como tal |
| WASM lento en gama baja | > 15 s por foto en H3 | Menos mosaicos, comparar int8 y fp32, bajar resolución. Último recurso: contador clásico |
| La app no funciona offline | Falla en modo avión en H4 | Revisar el límite de precache y servir el `.wasm` desde el propio dominio |
| No llegan los audios en quechua | Sin notas de voz en H8 | `mms-tts-quz` rotulado "sintético" + castellano grabado por el equipo |
| Twilio falla | El teléfono no sonó en H6 | Llamada con `curl` grabada. Último recurso: llamada desde un chip peruano, rotulada "simulado" |
| La integración se atrasa | Sin flujo completo en H12 | Se corta el panel antes que la llamada. El panel queda como lista JSON |
| Desvío de alcance | Alguien construye algo fuera de §3 | Aplicar la brújula de §1 |

---

## 12. Correcciones a lo dicho antes

| Antes | Corrección | Fuente |
|---|---|---|
| "48,7% de los hablantes de lengua originaria no lee" | **Falso.** La alfabetización con lengua materna originaria es de ≈84%. El dato fuerte es **33% de analfabetismo en mujeres rurales de lengua nativa frente a 9,3% en hombres**. Además, casi nadie lee quechua escrito | INEI, Censo 2017 |
| "Umbral de SENASA por trampa" | **No existe.** SENASA mide % de frutos brocados. La trampa solo indica tendencia y funciona en época seca | SENASA 2017, INIA |
| "Dataset de broca de *Sensors* 2026" | Son **frutos**, no trampas, y **no es público** | PMC13075308 |
| "NDVI detecta roya o envejecimiento" | No es defendible bajo sombra; nubes del 79–90% de noviembre a marzo | Medición propia en Planetary Computer |
| "Plantas > 15 años" | No discrimina: el 70–75% del área cafetalera ya supera esa edad. Se usa "> 20 años y sin recepa" | Junta Nacional del Café |
| "Humedad de NASA POWER" | Celda de ~55 km: no sirve para el microclima. Solo se usan la temperatura y, para la anomalía de días de lluvia de la región, `PRECTOTCORR` | NASA POWER |
| "Días de lluvia ≥ 100 y días en 17–25 °C ≥ 45 → roya" | Se activaban en las 5 fincas todos los años. Ahora se usa la anomalía frente a 1991–2020 | `pipeline/ficha/historico.py` |

**Frase del problema (borrador):**

> *Because of this tool, a coffee farmer in La Convención will start sanitation harvesting or get a call from her co-op technician within two weeks of broca rising in her own plot, which she otherwise discovers only at sale, when the buyer discounts bored beans; we know because [X% de productores sin asistencia técnica, ENA/INEI], [broca en Cusco, SENASA] and because technicians reach each farm only once or twice a year.*

Los corchetes los llena P4 en H0–1 con fuentes verificadas.

---

## 13. Pendientes de la hora 0

| Pendiente | Responsable | Bloquea |
|---|---|---|
| Pagar Twilio (≈20 USD) y habilitar Perú en los permisos geográficos | P3 | La llamada |
| Correos a CATIE (con CIRAD) (permiso para las fotos y los pesos) y a TESLA-UNSAAC | P4 | La prueba con broca real |
| Conseguir escarabajos pequeños oscuros (gorgojos de arroz, harina o menestras) | P2 | Los datos |
| Imprimir la tarjeta A5 (marco 10×10 cm + 20 círculos + 4 esquinas) | P4 | Las fotos |
| Ubicar a un hablante de quechua cusqueño y a un segundo validador | P4 | Los audios |
| Dato de la ENA/INEI sobre asistencia técnica | P4 | La frase del problema |
| Confirmar meses de floración y cosecha con COCLA o una cooperativa (si es posible) | P4 | El calendario del motor |
| Android barato y teléfono básico disponibles para el demo | P1 | Las pruebas reales |

---

## 14. Preguntas difíciles del jurado

**"¿Por qué no basta un SMS de calendario de SENASA a todos los socios?"**
Porque lo que falta no es el consejo, sino el monitoreo por finca. Nadie cuenta a ojo cientos de insectos de 2 mm cada quince días, y sin conteo no hay tendencia. La foto convierte eso en 30 segundos, y el técnico, que llega una o dos veces al año, visita primero donde la broca sube. El calendario le dice lo mismo a todos; nosotros decimos a quién y cuándo, y cuando no sabemos, lo decimos.

**"Wadhwani no mostró un beneficio significativo en su evaluación de 2021–22."**
Lo citamos con ese matiz. Por eso proponemos medir el piloto con dos indicadores: el % de socias que hacen repase en ≤ 2 semanas y el % de grano brocado en el acopio.

**"¿Su modelo ha visto broca peruana?"**
No. Lo declaramos, y pedimos los datos a CATIE (con CIRAD) y a UNSAAC. Mientras tanto, el conteo solo marca la tendencia y la pregunta de los granos es la que decide.
