# Flujo de uso

Basado en PLAN §4 y §5.2. GitHub dibuja los diagramas Mermaid.

## 1. El recorrido completo (personas y canales)

```mermaid
flowchart TD
  subgraph INS["Una vez · en la cooperativa · lo hace el técnico"]
    I1["Inscribe la finca: idioma, edad de las plantas, cosecha del año pasado"] --> I2["Consentimiento oral de Noor en quechua (grabado)"]
    I2 --> I3["Guarda COOPERATIVA en el teléfono básico de Noor + llamada de prueba"]
  end
  subgraph SAB["Cada dos semanas · sábado en la chacra · sin internet"]
    K["Kit: frasco de la trampa, 20 granos, tarjeta A5"] --> P1["Pantalla 1 · Foto"]
    P1 --> P2["Pantalla 2 · Pregunta con dibujos"]
    P2 --> P3["Pantalla 3 · Semáforo + dibujo + audio, sin cifras"]
  end
  I3 --> K
  P3 --> G["El caso queda guardado en el teléfono"]
  G --> S{"¿Hay señal?"}
  S -- "No" --> W["Espera en la cola; se reintenta al volver la señal o con un botón"] --> S
  S -- "Sí" --> API["Se envía a la cooperativa (POST /casos, sin duplicados)"]
  API --> PAN["Panel del técnico: urgente → técnico → amarillo → verde"]
  PAN --> REV["Ve la foto con cajas, las respuestas y las reglas con su fuente"]
  REV --> CALL["Botón: llamar a Noor"]
  CALL --> TEL["Suena su teléfono básico: Cooperativa X, para Noor + mensaje dos veces, 25 s como máximo"]
  TEL --> ACT["Noor actúa: nada, repase y recojo, o espera la visita"]
  REV --> VIS["El técnico visita primero los casos urgentes"]
```

## 2. Las tres pantallas, con sus decisiones

```mermaid
flowchart TD
  A(["Abrir la app"]) --> E{"¿Qué época es?"}
  E -- "Seca, may–oct" --> FT["Audio G_FOTO_TRAMPA: vaciar la trampa en el cuadrado"]
  E -- "Lluvias, nov–abr" --> FH["Audio G_FOTO_HOJAS: foto de 3 hojas por debajo"]
  FT --> QC{"¿Se ven las 4 esquinas, hay luz y no está movida?"}
  FH --> QC
  QC -- "No, hasta 2 veces" --> OV["Audio G_OTRA_VEZ"] --> E
  QC -- "No, tras 2 reintentos" --> DUD["Se marca conteo dudoso"]
  QC -- "Sí" --> T{"¿Es foto de trampa?"}
  T -- "Sí" --> CNT["Audio G_ESPERA · el modelo cuenta por mosaicos y las cajas aparecen sobre cada broca"]
  T -- "No, son hojas" --> PR["Audio P_ROYA: ¿polvo naranja debajo de las hojas? sí · no · no sé"]
  CNT --> PG["Audio P_GRANOS: ¿cuántos granos con huequito? sano · 1–2 · montón · no sé"]
  DUD --> PG
  PG --> M["Motor: respuesta + tendencia de la trampa + clima de la ficha + época"]
  PR --> M
  M --> SQ{"¿Una segunda pregunta puede cambiar el color?"}
  SQ -- "Sí" --> Q2["Segunda pregunta"] --> R
  SQ -- "No" --> R{"Semáforo"}
  R --> V["Verde · R_VERDE"]
  R --> AM["Amarillo · R_BROCA, R_ROYA o R_CLIMA · solo acciones culturales"]
  R --> TE["Técnico · R_TECNICO · duda, plantas viejas, otra causa o conteo dudoso"]
  R --> TU["Técnico urgente · R_TECNICO_URGENTE · 3 o más granos con fruto atacable"]
```

Reglas que el diagrama no muestra: un "0 granos" nunca da verde por sí solo, y "no sé" en los granos tampoco (PLAN §5.2).
