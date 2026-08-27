---
name: web-express
description: "De idea a web publicada en menos de 30 minutos. Hace preguntas estratégicas y de estilo para definir el proyecto; si el estilo no está claro, propone 3 opciones visuales concretas para elegir. Construye la web y la despliega en Vercel con URL pública. Activar cuando el usuario diga '/web-express', 'necesito una web rápido', 'crea una landing', 'quiero una web para mi proyecto', 'haz una página web de', 'necesito una landing page', o cuando describa la necesidad de publicar algo en internet."
triggers:
  - "/web-express"
  - "necesito una web rápido"
  - "crea una landing"
  - "quiero una web para mi proyecto"
  - "haz una página web de"
  - "necesito una landing page"
  - "quiero publicar algo en internet"
  - "hazme una web"
alwaysActive: false
---

# web-express

## Objetivo

Publicar una web funcional en menos de 30 minutos, desde la idea hasta la URL pública. Sin frameworks, sin complejidad innecesaria. El usuario describe qué quiere, la skill pregunta lo justo, construye y despliega.

---

## Flujo de ejecución

### FASE 1: ESTRATEGIA — Entender el proyecto

Hacer estas preguntas **de una en una**, de forma conversacional. No hacer todas a la vez.

**1. ¿Para qué es la web?**
Opciones comunes (ofrecer si no sabe):
- Landing de captación (email/contacto)
- Página de producto o servicio
- Portfolio o presentación profesional
- Página de evento o lanzamiento
- Página de precios / comparativa
- Web informativa / empresa

**2. ¿A quién va dirigida?**
- Quién es el visitante ideal
- Qué problema tiene que la web debe resolver
- Qué quieres que haga al visitar la web (CTA principal)

**3. ¿Tienes ya algún contenido preparado?**
- Logo, textos, imágenes, colores de marca
- Si no tiene nada: la skill genera todo desde cero

**4. ¿Hay webs de referencia que te gusten?**
- URLs de webs con el estilo que te inspira
- O describir el feeling: "moderno", "minimalista", "cálido", "profesional"...

**5. ¿Necesita capturar emails o formularios?**
- Sí → integrar con Mailchimp / Brevo / Resend (preguntar preferencia)
- No → web estática pura

### FASE 2: ESTILO — Definir la identidad visual

Si el usuario tiene marca definida (colores, tipografía), usar esa.

Si NO tiene estilo definido, proponer **3 opciones visuales**:

---

#### Opción A: LIMPIO Y PROFESIONAL
```
Paleta: Blanco + negro + un acento (azul marino o verde oscuro)
Tipografía: Sans-serif moderna (Inter, DM Sans)
Layout: Mucho espacio en blanco, contenido centrado
Mood: Confianza, seriedad, calidad
Ideal para: Servicios B2B, consultoras, portfolios profesionales
```

#### Opción B: CÁLIDO Y CERCANO
```
Paleta: Crema + marrón cacao + terracota o verde salvia
Tipografía: Serif para títulos + sans para cuerpo
Layout: Asimétrico, texturas sutiles, fotos reales
Mood: Humano, auténtico, artesanal
Ideal para: Restaurantes, hoteles boutique, marcas personales, creativos
```

#### Opción C: MODERNO Y BOLD
```
Paleta: Negro puro + blanco + 1 color muy saturado (amarillo, rojo, morado)
Tipografía: Display grande, letras grandes y llamativas
Layout: Contrastes fuertes, hover effects, interactividad
Mood: Impacto, energía, innovación
Ideal para: Startups, eventos, lanzamientos, marcas jóvenes
```

---

Preguntar: "¿Cuál te representa más, A, B o C? ¿O algún mix?"

### FASE 3: INVESTIGACIÓN (opcional, si el contexto lo requiere)

Si el proyecto lo merece (negocio real, no demo), hacer una investigación rápida:
- Buscar 2-3 webs de competidores directos
- Identificar qué funciona en el sector
- Detectar qué está haciendo diferente la propuesta del usuario

Esto mejora el copy y la estructura de la web.

### FASE 4: CONSTRUCCIÓN — Generar la web

Construir la web con esta estructura técnica:

**Stack:**
- HTML5 semántico
- CSS con variables personalizadas (no Tailwind, no frameworks)
- JavaScript vanilla solo si es necesario para interactividad
- Un único archivo `index.html` o estructura mínima de archivos

**Estructura de la web (adaptar según tipo):**

```
SECCIÓN 1: HERO
- Título principal (H1) — qué es y para quién
- Subtítulo — qué problema resuelve
- CTA principal (botón)
- Imagen o visual de apoyo

SECCIÓN 2: PROPUESTA DE VALOR
- 3 beneficios clave (iconos + texto corto)

SECCIÓN 3: DETALLE / CÓMO FUNCIONA
- Pasos, proceso o características

SECCIÓN 4: PRUEBA SOCIAL (si hay)
- Testimonios, clientes, casos de éxito

SECCIÓN 5: CTA FINAL
- Repetir el call to action principal
- Formulario de contacto o captura de email

FOOTER
- Info básica, links, legal
```

**Reglas de construcción:**
- Mobile-first siempre
- CTA visible en todas las pantallas (sticky si es necesario)
- Velocidad de carga < 1 segundo (sin imágenes pesadas)
- Copy en el idioma del usuario (español por defecto)
- Favicon incluido (emoji como favicon si no hay logo)

### FASE 5: DESPLIEGUE — Publicar en Vercel

**Opción A: Via MCP Vercel (si disponible)**
```
- Crear proyecto en Vercel
- Subir archivos
- Obtener URL pública
```

**Opción B: Instrucciones paso a paso**
```bash
# 1. Guardar los archivos en una carpeta
mkdir mi-web && cd mi-web
# [pegar index.html y otros archivos]

# 2. Subir a GitHub
git init
git add .
git commit -m "feat: web express"
gh repo create mi-web --public --source=.

# 3. Conectar con Vercel
# Ir a vercel.com → Add New → Import Git Repository
# Seleccionar el repo → Deploy
# En 2 minutos: URL pública lista
```

**Configuración de dominio (opcional):**
- Vercel da un dominio `.vercel.app` gratis
- Si el usuario tiene dominio propio: instrucciones para apuntar los DNS

---

## Outputs de la skill

Al terminar, entregar:

1. **Archivos de la web** — listos para desplegar
2. **URL pública** — tras el despliegue
3. **Snippet de embed** — si necesita embeber en otra web
4. **Instrucciones de actualización** — cómo cambiar textos e imágenes sin tocar código

---

## Tipos de web y tiempos estimados

| Tipo | Complejidad | Tiempo |
|---|---|---|
| Landing de captación (1 página) | Baja | 10-15 min |
| Web de servicio o producto (3-5 secciones) | Media | 20-30 min |
| Portfolio (múltiples páginas) | Media-Alta | 30-45 min |
| Web con formulario y backend | Alta | 45-60 min |

---

## Edge cases

- **Sin logo**: usar texto como logo o generar un favicon emoji hasta tener uno
- **Sin textos**: la skill genera el copy desde la descripción del negocio
- **Sin imágenes**: usar gradientes, iconos SVG o generar prompts para FAL.ai
- **Con dominio ya comprado**: instrucciones para configurar DNS en Vercel
- **Web en inglés**: cambiar toda la interfaz y el copy al inglés si el usuario lo pide
- **Necesita formulario funcional**: usar Formspree o similar (sin backend propio)

---

## Skills relacionadas

- `arnes` — para proyectos web que necesitan backend o son más complejos
- `consultor-ia-ventas` — si la web debe incluir un consultor conversacional
- `contenido-social` — para crear contenido para anunciar el lanzamiento de la web
- `skill-antibloqueo` — si el usuario se bloquea con el copy o el estilo
