---
name: skill-creator-pro
description: "Convierte cualquier proceso, reunión grabada o idea en una skill instalable para Claude Code. Toma como entrada una transcripción (Fathom, Whispr Flow, texto libre) o descripción de un proceso repetitivo y genera la skill completa lista para instalar. Activar cuando el usuario diga 'crea una skill', 'quiero convertir esto en skill', 'skill de esto', '/crear-skill', o cuando describa un proceso que quiere automatizar."
triggers:
  - "/crear-skill"
  - "crea una skill"
  - "quiero convertir esto en skill"
  - "skill de esto"
  - "hazme una skill"
alwaysActive: false
---

# skill-creator-pro

## Objetivo

Transformar cualquier proceso repetitivo, reunión grabada o idea en una skill instalable en Claude Code. El resultado es una carpeta con `SKILL.md` completo, lista para instalar con un solo comando.

## Fuentes de entrada aceptadas

- **Transcripción Fathom** — pegar el texto directamente o indicar la reunión
- **Dictado Whispr Flow** — ideas en voz → texto
- **Descripción manual** — el usuario describe el proceso en lenguaje natural
- **Proceso existente** — flujo de trabajo que ya hace manualmente

---

## Flujo de ejecución

### FASE 1: ENTENDER — Entrevista guiada

Antes de escribir nada, hacer estas preguntas (no todas a la vez — ir una a una si el usuario no ha dado el contexto):

1. **¿Cuál es el proceso o problema que quieres resolver?**
   - Si hay transcripción: extraer el proceso descrito en ella
   - Si es descripción manual: tomar nota literal

2. **¿Cuándo debe activarse la skill?**
   - ¿Qué dice o hace el usuario para invocarla?
   - ¿Tiene trigger natural (/comando) o se activa por contexto?

3. **¿Qué recibe como entrada?**
   - Texto, URL, archivo, datos estructurados, nada (solo contexto)

4. **¿Qué entrega como salida?**
   - Documento, código, análisis, instrucciones, contenido publicable...

5. **¿Hay pasos intermedios importantes?**
   - Preguntas que hace al usuario, decisiones, bifurcaciones

6. **¿Para quién es?**
   - Solo para ti (puede usar contexto de tu AI_OS)
   - Genérica (para compartir con la comunidad)

7. **¿Hay herramientas o integraciones específicas?**
   - Apps, APIs, plataformas que debe usar o mencionar

### FASE 2: CONFIRMAR — Resumen antes de crear

Antes de escribir el SKILL.md, presentar un resumen de lo que se va a crear:

```
📦 Skill propuesta: [nombre-kebab-case]

¿Qué hace?: [1 línea]
Trigger: /[comando] o [contexto de activación]
Entrada: [qué recibe]
Salida: [qué entrega]
Flujo: [3-5 pasos clave]
Audiencia: [personal / genérica]

¿Lo creamos así o ajustamos algo?
```

No continuar hasta que el usuario confirme.

### FASE 3: CREAR — Generar la skill

Una vez confirmado, crear la carpeta y archivos:

#### Estructura mínima
```
[nombre-skill]/
├── SKILL.md          ← obligatorio
└── references/       ← opcional, si hay plantillas o ejemplos
    └── ejemplo.md
```

#### Plantilla SKILL.md
```markdown
---
name: [nombre-kebab-case]
description: "[Una línea precisa de qué hace y cuándo activarla. Incluir ejemplos de frases trigger]"
triggers:
  - "[trigger 1]"
  - "[trigger 2]"
alwaysActive: false
---

# [Nombre de la Skill]

## Objetivo
[Qué problema resuelve y para quién]

## Entrada
[Qué necesita para funcionar]

## Flujo de ejecución

### FASE 1: [Nombre]
[Pasos detallados]

### FASE 2: [Nombre]
[Pasos detallados]

[...]

## Salida
[Qué entrega exactamente y en qué formato]

## Edge cases
[Qué hacer si falta información, hay ambigüedad, etc.]

## Skills relacionadas
[Otras skills del ecosistema que complementan esta]
```

### FASE 4: INSTALAR — Copiar al ecosistema

Después de crear los archivos, copiar automáticamente a `~/.claude/skills/`:

```bash
cp -r ~/iamasters-os/skills-library/[categoria]/[nombre-skill] ~/.claude/skills/
```

Confirmar al usuario:
- Path donde quedó guardada
- Cómo invocarla
- Si necesita reiniciar Claude Code

---

## Reglas de calidad

- El `description` del frontmatter debe incluir frases de activación naturales — es lo que Claude lee para decidir si activar la skill
- Los flujos deben ser **accionables**, no genéricos — cada paso debe decir exactamente qué hacer
- Si la skill es genérica (para compartir), no hardcodear nombres, rutas ni contexto personal
- Si la skill es personal, puede referenciar `~/claude_workspace/AI_OS/` para cargar contexto
- Máximo 2 niveles de carpetas dentro de la skill
- Siempre incluir edge cases — qué pasa si falta información o el input es ambiguo

---

## Flujo express desde Fathom

Cuando el input es una transcripción de reunión (Fathom u otro):

1. Leer la transcripción completa
2. Extraer: **el proceso descrito**, **las herramientas mencionadas**, **el resultado esperado**
3. Identificar los pasos del flujo de trabajo
4. Hacer solo las preguntas de la Fase 1 que no estén respondidas en la transcripción
5. Crear la skill directamente sin entrevista larga si el contexto es suficiente

**Objetivo:** De transcripción a skill instalada en menos de 5 minutos.

---

## Categorías disponibles en skills-library

Al guardar en `~/iamasters-os/skills-library/`, elegir la carpeta correcta:

| Carpeta | Para qué |
|---|---|
| `tools/` | Herramientas de uso general |
| `marketing/` | Contenido, redes, copywriting |
| `strategy/` | Análisis, decisiones, estrategia |
| `automation/` | Flujos automáticos, integraciones |
| `visualization/` | Diagramas, HTML visual, dashboards |

---

## Skills relacionadas

- `arnes` — para arrancar proyectos completos (más amplio que una skill)
- `tool-zoom-summary` — ejemplo de skill compleja bien estructurada (referencia de calidad)
- `anthropic-skills:skill-creator` — versión oficial de Anthropic (más genérica)
