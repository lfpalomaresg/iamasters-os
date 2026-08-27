---
name: contenido-social
description: "Pipeline completo de idea o fuente de contenido (URL, PDF, audio, idea en texto) a publicación en LinkedIn y Meta. Genera carrusel o post, adapta a la voz del perfil seleccionado, crea imágenes con FAL.ai y publica vía Upload Post. Activar cuando el usuario diga '/contenido-social', 'crea contenido para LinkedIn', 'hazme un carrusel', 'publica esto en redes', 'convierte esto en contenido', 'genera un post de', o cuando proporcione una fuente (URL, PDF, transcripción, idea) con intención de publicar en redes sociales."
triggers:
  - "/contenido-social"
  - "crea contenido para LinkedIn"
  - "hazme un carrusel"
  - "publica esto en redes"
  - "convierte esto en contenido"
  - "genera un post de"
  - "quiero publicar en LinkedIn"
  - "crea un post sobre"
alwaysActive: false
---

# contenido-social

## Objetivo

Transformar cualquier fuente de contenido en una publicación lista para LinkedIn (y Meta en fase 2). El pipeline completo va de la fuente al botón de publicar:

```
FUENTE → EXTRACCIÓN → ESTRUCTURA → VOZ → IMÁGENES (FAL.ai) → PUBLICACIÓN (Upload Post)
```

---

## Perfiles de voz disponibles

La skill trabaja con perfiles de voz. El predefinido es **Capa 2**, pero el usuario puede cargar otro o crear uno nuevo.

### Perfil predefinido: Capa 2 — Evangelista IA Hotelero

**Quién es:** Profesional hotelero que lleva años en la trinchera. No es directivo ni consultor. Es el que tiene que resolver los problemas reales del día a día con IA.

**A quién habla:** Equipos hoteleros, directores de hotel de escala media, propietarios de hoteles boutique. NO habla a inversores ni a directivos de grandes cadenas.

**Tono:** Cálido, directo, sin humo. Comparte lo que aprende, no lo que vende. Usa ejemplos concretos del hotel. Nada de frases corporativas.

**Frases que SÍ usa:**
- "Lo probamos en el Soho esta semana y..."
- "No hace falta ser técnico para esto"
- "El truco está en..."
- "Te lo cuento sin filtros:"
- "Esto sí me ha funcionado"

**Frases que NUNCA usa:**
- "Transformación digital"
- "Sinergias"
- "Disruptivo"
- "El futuro del hospitality"
- "Potenciar el ROI"

**Estructura favorita:** Problema real → Lo que intenté → Lo que funcionó → Cómo lo aplicas tú

### Cómo cargar un perfil diferente

El usuario puede decir: "usa el perfil de [nombre]" o "carga este perfil: [descripción]". La skill adapta todo el contenido a ese perfil en lugar del predefinido.

---

## Flujo de ejecución

### PASO 1: Fuente y formato

Preguntar (si no se ha dado):

1. **¿Cuál es la fuente del contenido?**
   - URL de artículo, vídeo, podcast
   - PDF o documento
   - Transcripción (Fathom, Wispr Flow)
   - Idea en texto libre
   - Ninguna (brainstorm desde cero)

2. **¿Qué formato quieres?**
   - **Carrusel** (5-10 slides, ideal para LinkedIn)
   - **Post texto** (post largo LinkedIn, 1.200-2.000 caracteres)
   - **Post corto** (menos de 700 caracteres, alta legibilidad)
   - Si no sabe, proponer según la fuente

3. **¿Qué perfil de voz?** (por defecto: Capa 2)

### PASO 2: Extracción y análisis

Según la fuente:

**Si es URL:**
- Extraer el contenido principal (ignorar ads y navegación)
- Identificar: tesis principal, 3-5 ideas clave, datos o cifras relevantes, anécdotas o ejemplos concretos

**Si es transcripción:**
- Identificar el tema central
- Extraer momentos de valor: insight sorprendente, error revelador, consejo accionable
- Ignorar relleno, saludos, divagaciones

**Si es idea en texto:**
- Expandir con preguntas: ¿cuál es el gancho?, ¿qué aprende el lector?, ¿qué tiene de diferente este punto de vista?

### PASO 3: Estructura del contenido

#### Para CARRUSEL (LinkedIn):

```
SLIDE 1 — GANCHO (lo más importante)
┌─────────────────────────┐
│ [Frase que para el scroll]│
│ [Promesa concreta]       │
│ "Sigue leyendo →"        │
└─────────────────────────┘

SLIDES 2-8 — DESARROLLO
┌─────────────────────────┐
│ [Número o emoji]        │
│ [Idea en 1 título]      │
│ [Explicación en 2-3 líneas] │
│ [Ejemplo o dato concreto] │
└─────────────────────────┘

SLIDE FINAL — CTA
┌─────────────────────────┐
│ [Resumen en 1 frase]   │
│ [Pregunta para comentarios] │
│ [Guardar / Compartir]   │
└─────────────────────────┘
```

**Reglas del carrusel:**
- Slide 1 = el hook. Sin él no hay nada
- Máximo 30 palabras por slide (en el texto del slide)
- Números concretos > afirmaciones genéricas
- Cada slide debe poder entenderse solo
- Siempre terminar con pregunta o CTA

#### Para POST TEXTO (LinkedIn):

```
LÍNEA 1-2: GANCHO (aparece sin "ver más")
↓
BREAK DE LÍNEA (separación visual)
↓
DESARROLLO (3-5 párrafos cortos, máx 3 líneas cada uno)
↓
CONCLUSIÓN o LECCIÓN (1-2 líneas)
↓
PREGUNTA AL LECTOR (fomenta comentarios)
↓
HASHTAGS (3-5, nada más)
```

**Reglas del post:**
- Primera línea = todo. Si no para el scroll, nada más importa
- Párrafos cortos (2-3 líneas máx)
- Espacios en blanco = oxígeno
- Voz activa siempre
- Sin emojis de relleno. Solo si añaden significado

### PASO 4: Adaptación a la voz

Aplicar el perfil de voz seleccionado:
- Reescribir en el tono del perfil
- Sustituir palabras prohibidas
- Añadir frases características
- Verificar que suena humano, no a IA

Si el texto suena a IA, reescribir con estas técnicas:
- Añadir una anécdota específica ("En el Soho tuvimos un caso...")
- Usar imperfecto narrativo ("Lo estaba probando cuando...")
- Romper una creencia ("Aquí te cuento por qué me equivocaba")

### PASO 5: Prompts de imagen (FAL.ai)

Para cada slide del carrusel o para el post, generar prompts de imagen:

**Formato del prompt:**
```
[Estilo visual]: [descripción concreta de la imagen]
No incluir texto en la imagen.
Mood: [adjetivos del mood]
Color palette: [colores dominantes]
```

**Estilos según perfil Capa 2:**
- Fotografía de hotel real, ambiente de trabajo, equipos en acción
- Sin stock photos genéricas
- Sin personas sonriendo forzadamente
- Atmósfera cálida, real, cotidiana

**Llamada a FAL.ai (cuando esté configurada la API):**
- Modelo: `fal-ai/flux/schnell` (rápido) o `fal-ai/flux-pro` (calidad)
- Aspect ratio: 1:1 para LinkedIn post / 4:5 para LinkedIn carrusel
- Generar opción A y opción B para cada imagen, dejar elegir

### PASO 6: Publicación vía Upload Post

Una vez aprobado el contenido e imágenes:

**Para LinkedIn:**
```
POST_TYPE: linkedin_post o linkedin_document (carrusel)
PROFILE: [perfil LinkedIn del usuario]
CONTENT: [texto del post]
IMAGES: [URLs de imágenes generadas]
SCHEDULE: ahora / [fecha y hora específica]
```

**Flujo:**
1. Mostrar preview completo al usuario
2. Pedir confirmación: "¿Publicamos ahora o programamos?"
3. Si programa: pedir fecha y hora
4. Llamar a Upload Post API
5. Confirmar URL del post publicado

**API Upload Post:**
- Endpoint: `https://app.upload-post.com/api/v1/post`
- Auth: Bearer token (API key del usuario)
- La skill pide la API key si no está en el entorno

---

## Configuración de APIs

### FAL.ai
```
FAL_KEY=fal-xxxxx
```
- Documentación: https://fal.ai/docs
- Modelo por defecto: `fal-ai/flux/schnell`

### Upload Post
```
UPLOAD_POST_API_KEY=up-xxxxx
```
- Endpoint base: `https://app.upload-post.com/api/v1`
- La cuenta debe tener LinkedIn conectado

---

## Formatos de output

### Carrusel — output completo
```markdown
# CARRUSEL: [Título del contenido]
**Perfil:** [voz usada]
**Formato:** Carrusel LinkedIn (X slides)

---
## SLIDE 1 — GANCHO
[Texto del slide]
**Prompt imagen:** [prompt para FAL.ai]

## SLIDE 2
[Texto]
**Prompt imagen:** [prompt]

[...]

## SLIDE FINAL — CTA
[Texto]
**Prompt imagen:** [prompt]

---
## TEXTO DEL POST (descripción del carrusel)
[Texto para poner en LinkedIn al subir el carrusel]

## HASHTAGS
[lista]
```

### Post texto — output completo
```markdown
# POST LINKEDIN
**Perfil:** [voz usada]
**Longitud:** X caracteres

---
[TEXTO COMPLETO DEL POST]

---
**Imagen sugerida:**
**Prompt FAL.ai:** [prompt]
```

---

## Edge cases

- **Fuente en inglés, post en español**: traducir y adaptar culturalmente, no solo traducir literal
- **Contenido muy técnico**: simplificar sin perder precisión — usar analogías del sector
- **Sin acceso a FAL.ai**: generar prompts igualmente para que el usuario los use manualmente
- **Sin Upload Post configurado**: entregar el contenido listo para copiar-pegar
- **Contenido muy largo**: seleccionar las 5 ideas más potentes, no resumir todo
- **Perfil diferente a Capa 2**: pedir descripción del perfil en 5 líneas si no está guardado

---

## Skills relacionadas

- `tool-transcribe-social` — para transcribir vídeos/audios antes de procesar
- `marketing-content-repurposing` — para distribuir el mismo contenido en múltiples formatos
- `skill-antibloqueo` — si el usuario se bloquea con el ángulo o el gancho
