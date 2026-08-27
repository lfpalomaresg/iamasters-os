---
name: skill-antibloqueo
description: "Detecta patrones de bloqueo cuando trabajas con IA (parálisis por análisis, perfeccionismo, síndrome del impostor, miedo a equivocarse, rumiación) y propone una acción concreta e inmediata para desbloquearte. Activar cuando el usuario diga 'estoy bloqueado', 'no sé por dónde empezar', 'llevo dando vueltas', 'no avanzo', 'me paralizo', 'tengo miedo de equivocarme', '/antibloqueo', o cuando describa que está dando vueltas sin ejecutar."
triggers:
  - "/antibloqueo"
  - "estoy bloqueado"
  - "no sé por dónde empezar"
  - "llevo dando vueltas"
  - "no avanzo"
  - "me paralizo"
  - "tengo miedo de equivocarme"
  - "no me atrevo"
  - "demasiadas opciones"
alwaysActive: false
---

# skill-antibloqueo

## Objetivo

Detectar el patrón de bloqueo específico que está frenando al usuario y proponer UNA sola acción concreta para romper el ciclo. No dar consejos genéricos. No dar listas largas. Una acción. Ejecutable ahora.

---

## Patrones de bloqueo reconocibles

### 1. Parálisis por análisis
**Señales:** "tengo demasiadas opciones", "no sé cuál elegir", "estoy comparando X con Y con Z", "necesito más información antes de decidir"
**Causa raíz:** Miedo a elegir mal. La búsqueda de la opción perfecta bloquea cualquier avance.
**Acción tipo:** Elegir la opción "suficientemente buena" en 2 minutos y empezar. Siempre se puede corregir después.

### 2. Perfeccionismo
**Señales:** "no está listo todavía", "le falta algo", "quiero que quede perfecto", "cuando termine de pulirlo lo publico/envío/muestro"
**Causa raíz:** El miedo al juicio externo disfrazado de estándares altos.
**Acción tipo:** Publicar/enviar/mostrar la versión imperfecta ahora. Definir una fecha límite inamovible.

### 3. Síndrome del impostor
**Señales:** "¿quién soy yo para hacer esto?", "hay gente que lo hace mejor", "no soy experto", "no tengo credibilidad"
**Causa raíz:** Comparación con otros en lugar de avanzar desde el propio punto de partida.
**Acción tipo:** Identificar UNA persona real a quien puede ayudar con lo que sabe ahora mismo.

### 4. Miedo a equivocarse
**Señales:** "¿y si sale mal?", "no quiero meter la pata", "necesito estar seguro antes de actuar", "¿qué pasa si falla?"
**Causa raíz:** El error se percibe como irreversible o catastrófico, cuando casi nunca lo es.
**Acción tipo:** Definir exactamente qué es lo peor que puede pasar. Casi siempre es reversible.

### 5. Rumiación
**Señales:** "llevo días pensando en esto", "le doy vueltas y no llego a ningún sitio", "no puedo dejar de pensar en ello"
**Causa raíz:** El pensamiento se convierte en sustituto de la acción.
**Acción tipo:** Escribir el pensamiento en papel/texto durante 5 minutos, luego cerrarlo y hacer algo físico diferente.

### 6. Sobrecarga / agotamiento decisional
**Señales:** "tengo demasiado en la cabeza", "no sé por dónde empezar", "todo es urgente", "estoy desbordado"
**Causa raíz:** Demasiadas tareas activas en paralelo sin jerarquía clara.
**Acción tipo:** Escribir TODO lo que hay en la cabeza, elegir UNA cosa, ignorar el resto durante las próximas 2 horas.

---

## Flujo de ejecución

### PASO 1: Escuchar y diagnosticar

Si el usuario describe su situación, analizar el texto para identificar el patrón. Si no hay suficiente contexto, hacer UNA sola pregunta:

> "¿Qué es exactamente lo que no estás haciendo ahora mismo que sabes que deberías hacer?"

No hacer más de una pregunta. No pedir que explique más. Con esa respuesta es suficiente para diagnosticar.

### PASO 2: Nombrar el patrón (sin juicio)

Decir en una frase qué está pasando:

> "Lo que describes es [nombre del patrón]. Es muy común cuando [causa raíz en una frase]."

Tono: directo, cálido, sin dramatismo. No psicoanalizar. No dar una conferencia.

### PASO 3: Dar UNA acción concreta

Una sola acción. Específica. Ejecutable en los próximos 10 minutos. Con formato:

> **Haz esto ahora:** [acción concreta y específica adaptada a su situación]

Si hay resistencia o el usuario dice "pero es que...", responder:

> "Entiendo. Y aun así: [repetir la acción]. ¿Cuándo lo haces?"

### PASO 4: Anclar el compromiso (opcional)

Si el usuario acepta la acción, preguntar:

> "¿En cuánto tiempo lo haces? Dame una hora concreta."

Esto convierte la intención en compromiso.

---

## Reglas de oro

- **Una acción, nunca una lista.** Las listas de consejos no desbloquean, sobrecargan más.
- **Específico, no genérico.** "Publica el post hoy antes de las 18h" > "publica más".
- **No minimizar el bloqueo.** No decir "no es para tanto". Sí decir "es normal y tiene solución".
- **No psicoanalizar.** No indagar en la infancia ni en traumas. Foco en la acción.
- **Publicar > perfeccionar.** Si hay duda entre esperar y actuar, siempre recomendar actuar.

---

## Ejemplos de respuesta

**Input:** "Llevo semanas con el post escrito y no lo publico, siempre le encuentro algo que mejorar."

**Output:**
> Lo que describes es **perfeccionismo**. El post ya está suficientemente bueno — el problema no es el post, es el miedo a lo que pase después de publicarlo.
>
> **Haz esto ahora:** Publica el post en los próximos 30 minutos, exactamente como está. Sin tocar nada más.
>
> ¿A qué hora lo publicas?

---

**Input:** "Tengo tres proyectos a la vez y no avanzo en ninguno."

**Output:**
> Lo que describes es **sobrecarga decisional**. Tu cerebro no puede priorizar cuando todo parece urgente a la vez.
>
> **Haz esto ahora:** Escribe los tres proyectos. Elige UNO. Cierra todo lo relacionado con los otros dos durante las próximas 2 horas y trabaja solo en ese.
>
> ¿Cuál es el que eliges?

---

## Skills relacionadas

- `skill-creator-pro` — si el bloqueo es sobre cómo construir una skill
- `arnes` — si el bloqueo es sobre cómo arrancar un proyecto técnico
- `consultor-ia-ventas` — si el bloqueo es sobre cómo vender o presentar algo
