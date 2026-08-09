---
name: session-end
description: >
  Cierra la sesión documentando automáticamente lo que se hizo, lo que queda pendiente
  y las decisiones tomadas. Guarda el resumen en memory/session-logs/ y actualiza MEMORY.md
  si hubo cambios estructurales. USAR cuando el usuario diga "cerramos", "hasta luego",
  "fin de sesión", "session-end", "guarda donde estamos", o cualquier intent de cerrar sesión.
---

# Session End — Documentación automática de sesión

> **Nota**: Este comando extiende `/eod`. Primero ejecuta el flujo EOD (save daily summary),
> luego añade el session log detallado y actualiza MEMORY.md si procede.
> Para solo guardar el contexto multi-proyecto sin session log, usa `/eod` directamente.

Al ejecutar este comando, haz lo siguiente SIN preguntar:

## 1. Generar resumen de sesión

Analiza toda la conversación actual y genera un markdown con esta estructura:

```markdown
# Sesión [FECHA] — [Título descriptivo breve]

## Lo que se hizo
- [Lista de cada tarea completada con detalle suficiente para retomar]

## Pendiente para próxima sesión
- [Lista priorizada de lo que quedó sin hacer]
- [Incluir contexto suficiente para no tener que re-explicar]

## Decisiones tomadas
- [Decisiones técnicas, estratégicas o de producto tomadas en esta sesión]

## Skills/archivos creados o modificados
- [Lista de archivos nuevos o editados con path completo]

## Notas
- [Cualquier contexto relevante que la próxima sesión necesite saber]
```

## 1.5 Compliance Check — Verificación de instincts y reglas pasivas

Antes de guardar, verificar que no se incumplieron reglas aprendidas durante la sesión.

### Pasos

1. Leer `~/.claude/skills/_instincts-index.json` y `~/.claude/skills/_passive-rules.json`
2. Filtrar solo instincts con confidence `confirmed` o `permanent`, y todas las passive rules activas
3. Para cada regla, evaluar: "En esta sesión hice algo que debería haber activado esta regla? Si sí, la cumplí?"
4. Focos de revisión:
   - **Deliverables**: HTML twins generados, imágenes de marca incluidas, formato correcto
   - **Code patterns**: Supabase RLS aplicado, commit conventions seguidas, env vars correctas
   - **Documentación**: MEMORY.md actualizado cuando corresponde, session logs completos

### Si hay violaciones

- Listar cada violación con el `id` de la regla y qué se omitió:
  ```
  INCUMPLIMIENTO: [rule-id] — [descripción breve de lo que faltó]
  ```
- Si el fix es pequeño (ej: falta un HTML twin, falta un header de seguridad):
  ofrecer corregirlo AHORA antes de cerrar la sesión
- Si el `inject` text de la regla es demasiado vago para actuar:
  proponer una versión más específica y actualizar el instinct en `_instincts-index.json`

### Si no hay violaciones

No imprimir nada — pasar directamente al paso 2.

## 2. Guardar el archivo

Detectar el directorio de memory del proyecto actual. Buscar en este orden:
1. `~/.claude/projects/{project-id}/memory/session-logs/`
2. Si no existe session-logs/, crearlo

Nombre del archivo: `YYYY-MM-DD-HHmm.md` (fecha y hora actual)

## 3. Actualizar MEMORY.md (solo si aplica)

Si durante la sesión se crearon skills nuevas, se modificó la estructura del proyecto,
se tomaron decisiones que afectan a futuras sesiones, o se cambió algo del sistema
Skills on Demand — actualizar la sección correspondiente de MEMORY.md.

NO reescribir todo MEMORY.md. Solo añadir o actualizar las secciones afectadas.

## 3.8 Git status de los repos de código tocados en la sesión

**Nunca dejar que se acumulen días de commits sin avisar** (pasó con AI_OS, hasta 2026-08-05 sin
commit varias sesiones seguidas). Para CADA repo con `.git` que se haya tocado en esta sesión:

1. `git status --short` en ese repo.
2. Si está limpio, anotar "✅ sin cambios pendientes" para el resumen del paso 4 — no omitir la
   línea aunque no haya nada, la ausencia de aviso no debe confundirse con "no lo comprobé".
3. Si hay cambios sin commitear:
   - Si el repo tiene el gate `conclave` instalado (`.git/hooks/pre-commit` lo referencia, o
     existe `.conclave/`) y los cambios tocan código (no solo `.md`), el commit directo lo
     bloqueará. **No forzarlo.** Reportar los archivos pendientes y ofrecer explícitamente:
     "¿Corro conclave/careo ahora para cerrarlo, o lo dejamos para la próxima sesión?" — nunca
     lanzar un conclave completo sin que el operador lo pida (multi-agente, coste real).
   - **Ojo con "es solo documentación":** la excepción del gate cubre commits compuestos
     EXCLUSIVAMENTE por `*.md`. Un `.gitignore`, un JSON o un YAML **también lo bloquean**, aunque
     no lleven lógica. Así que: si el commit es solo Markdown, proponer commit directo (mensaje
     conventional) con el mismo criterio de aprobación explícita que ya aplica al AI_OS en el paso
     ## 3.6 de más arriba. Si entra cualquier fichero que no sea `.md`, hace falta el sello de
     conclave o un override autorizado — **nunca commitear código sin ese OK.**

## 4. Confirmar al usuario

Mostrar un resumen breve:
```
📋 Sesión documentada en: [path al archivo]
📝 MEMORY.md: [actualizado / sin cambios]
🗂️ Repos de código: [una línea por repo tocado — commiteado / pendiente (con motivo) / limpio]
🔜 Próxima sesión: [1-2 líneas de lo más urgente pendiente]
```

## Reglas

- NO preguntar nada — ejecutar directamente
- Ser conciso pero con suficiente detalle para retomar sin contexto
- Incluir paths completos de archivos creados/modificados
- Si no hubo cambios estructurales, no tocar MEMORY.md
- El título del archivo debe ser descriptivo (no genérico)
