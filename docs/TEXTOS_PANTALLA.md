# Textos de pantalla en quechua (para validar)

La app de campo muestra la pantalla en el mismo idioma que la voz: el botón de la barra cambia las dos cosas.
Los textos en quechua de abajo son un **borrador del equipo, sin validar** por un hablante nativo. Se armaron
con las frases de los audios (`audio/mensajes.json`, también borrador) o se escribieron nuevos.

Fuente en el código: `apps/campo/src/textos.ts`. Si se corrige un texto aquí, se corrige también allí.
Reglas: frases cortas (caben en un botón de celular), sin cifras, quechua cusqueño como en los audios.

**Para quien revise:** en cada fila, ¿se entiende? ¿se diría así en la chacra? Escribe la corrección en la última columna.

| Dónde aparece | Castellano | Quechua (borrador) | De dónde sale | Corrección |
|---|---|---|---|---|
| Botón de idioma | Castellano | Runasimi | — | |
| Botón de voz (lector de pantalla) | Escuchar | Uyariy | nuevo | |
| Foto, época seca | Que se vean las cuatro esquinas | Tawantin k'uchukuna rikhurichun | `G_FOTO_TRAMPA` | |
| Foto, lluvias | Hojas volteadas | Kimsa raphita tikray | `G_FOTO_HOJAS` | |
| Foto oscura | Otra vez, con más luz | Watiqmanta, aswan k'anchaypi | `G_OTRA_VEZ` + nuevo | |
| Botón de la foto | Tomar foto | Fotota hurquy | `G_OTRA_VEZ` | |
| Mientras cuenta | Contando | Yupashani | `G_ESPERA` | |
| Pregunta | ¿Granos con huequito? | ¿T'uquyuq rurukuna? | `P_GRANOS` | |
| Pregunta | ¿Polvo naranja debajo? | ¿Uranpi naranha ñut'u kanchu? | `P_ROYA` | |
| Opción | Sanos | Qhali | nuevo | |
| Opción | Pocos con huequito | Pisi t'uquyuq | nuevo | |
| Opción | Muchos con huequito | Achka t'uquyuq | nuevo | |
| Opción | No sé | Mana yachanichu | nuevo | |
| Opción | Sí, hay polvo | Arí, kanmi | nuevo | |
| Opción | No hay | Manam kanchu | nuevo | |
| Semáforo verde | Todo bien | Tukuy allin | `R_VERDE` | |
| Semáforo amarillo | Atención | ¡Qhawariy! | nuevo | |
| Semáforo técnico | El técnico lo verá | Técnicon qhawanqa | `R_TECNICO` | |
| Semáforo urgente | Aviso al técnico | Técnicoman willasqa | `R_TECNICO_URGENTE` | |
| Acción broca y urgente | Recoge los granos caídos | Urmasqa rurukunata pallay | `R_TECNICO_URGENTE` | |
| Acción roya | Puede ser roya | Royachá kanman | `R_ROYA` | |
| Acción clima | Fue el clima | Timpun karqan | `R_CLIMA` | |
| Acción verde | Sigue cuidando tu chacra | Hinallata qhawarillay | `R_VERDE` | |
| Acción técnico | Ya le mandé tu caso | Casoykita apachiniña | `R_TECNICO` | |
| Aviso enviado | Ya le llegó al técnico | Técnicomanña chayan | nuevo | |
| Aviso sin señal | Guardado. Le llegará al técnico cuando haya señal | Waqaychasqa. Señal kaqtin técnicoman chayanqa | nuevo | |
| Botón de tarea | Ya lo hice | Ruwaniña | nuevo | |
| Tarea hecha | ¡Muy bien! | ¡Allinmi! | nuevo | |
| Botón final | Terminar | Tukuchiy | nuevo | |
| Nube (lector de pantalla) | Todo enviado | Tukuy apachisqa | nuevo | |
| Nube (lector de pantalla) | Guardado; se enviará con señal | Waqaychasqa; señal kaqtin apachikunqa | nuevo | |
| Botón de idioma (lector de pantalla) | Idioma: castellano. Tocar para cambiar a quechua | Simi: runasimi. Ñit'iy castellanoman tikranapaq | nuevo | |

Pendiente: las descripciones de los dibujos para lector de pantalla (`ui/Dibujos.tsx`) siguen solo en castellano.

Revisado por: ______________________ Fecha: __________
