---
name: consultor-ia-ventas
description: "Genera un consultor conversacional IA personalizado para cualquier negocio: cualifica clientes, detecta oportunidades de automatización, calcula impacto económico y produce un informe comercial listo para cierre. Activar cuando el usuario diga '/consultor-ventas', 'quiero crear un consultor IA para mi negocio', 'necesito cualificar clientes con IA', 'chatbot de ventas', 'consultor conversacional', o cuando describa la necesidad de automatizar la captación o cualificación de leads."
triggers:
  - "/consultor-ventas"
  - "quiero crear un consultor IA para mi negocio"
  - "necesito cualificar clientes con IA"
  - "chatbot de ventas"
  - "consultor conversacional"
  - "automatizar captación de leads"
  - "crear mi propio consultor"
alwaysActive: false
---

# consultor-ia-ventas

## Objetivo

Crear un consultor conversacional IA a medida de un negocio concreto. El consultor:
1. Cualifica leads de forma autónoma (detecta si son un buen cliente potencial)
2. Identifica oportunidades de automatización o mejora en su operación
3. Calcula el impacto económico de implementar IA (ahorro, ingresos extra, eficiencia)
4. Genera un informe comercial profesional listo para cerrar la venta o enviar al cliente

El output final es código de una app de chat embebible en cualquier web, lista para desplegar en Vercel.

---

## Flujo de ejecución

### FASE 1: CONTEXTO — Entender el negocio

Al activarse, preguntar primero el idioma si no está claro:

> "¿Trabajamos en español o in English?"

Luego recoger contexto del negocio con estas preguntas (de una en una, conversacional):

1. **¿Cuál es tu negocio o sector?**
   - Ejemplo: hotel boutique, clínica dental, agencia de marketing, ecommerce de moda, restaurante
   - Si el usuario ya lo ha dado, no preguntar

2. **¿Cuál es el perfil de tu cliente ideal?**
   - A quién quieres vender, qué problema tienen, qué presupuesto suelen manejar

3. **¿Cuál es tu oferta principal?** (servicio, producto, precio aproximado)

4. **¿Tienes ya algún proceso de cualificación de leads o lo hace todo manualmente?**
   - Para detectar dónde está el mayor dolor

5. **¿Dónde quieres embeber el consultor?**
   - Web propia / landing page / ninguna todavía (se crea una)

6. **¿Dónde quieres que vayan los leads cualificados?**
   - CRM (indicar cuál) / Google Sheets / Supabase / solo email

Nota: si el negocio es Blindbeds Supply (hoteles, pedidos, recepciones), usar ese contexto directamente sin preguntar.

### FASE 2: DISEÑO — Arquitectura del consultor

Con el contexto recogido, diseñar el flujo conversacional del consultor:

#### Flujo de conversación del consultor
```
SALUDO → CUALIFICACIÓN → DIAGNÓSTICO → IMPACTO ECONÓMICO → PROPUESTA → CAPTURA DE DATOS
```

**Bloque CUALIFICACIÓN** — preguntas para filtrar al lead:
- ¿Cuántos [clientes/pedidos/pacientes/reservas] gestionas al mes? (volumen)
- ¿Cuánto tiempo dedica tu equipo a [proceso clave]? (eficiencia)
- ¿Tienes algún sistema actual para [proceso]? (contexto técnico)
- ¿Cuál es tu mayor reto ahora mismo en [área]? (pain point)

**Bloque DIAGNÓSTICO** — el consultor identifica:
- Proceso con mayor impacto para automatizar
- Nivel de madurez digital del lead
- Encaje o no encaje con la oferta

**Bloque IMPACTO ECONÓMICO** — cálculo en vivo:
- Horas ahorradas × coste hora = ahorro mensual
- Conversiones extra × ticket medio = ingresos extra
- ROI estimado de implementar IA

**Bloque PROPUESTA** — el consultor propone:
- Solución concreta (sin vender directamente)
- Próximo paso claro (llamada, demo, propuesta)

**Bloque CAPTURA** — recoge:
- Nombre, email, empresa, teléfono (lo que sea relevante)
- Envía resumen al operador

### FASE 3: CÓDIGO — Generar la app de chat

Generar el código de la aplicación con este stack:
- **Frontend**: HTML/CSS/JS vanilla (sin frameworks) — embebible como burbuja de chat
- **Backend**: API calls a Claude (claude-haiku-4-5 por coste) vía Vercel Serverless Functions
- **Sistema prompt**: personalizado con el contexto del negocio
- **Almacenamiento**: envío a webhook o Google Sheets (según lo que dijo el usuario)

#### Estructura de archivos
```
consultor-[negocio]/
├── index.html          ← interfaz de chat (burbuja embebible)
├── api/
│   └── chat.js         ← Vercel serverless function (llama a Claude)
├── vercel.json         ← config de despliegue
└── .env.example        ← variables necesarias
```

#### Sistema prompt del consultor (plantilla)
```
Eres un consultor experto en [sector/negocio]. Tu misión es:
1. Entender la situación actual del cliente en [área de mejora]
2. Identificar sus mayores cuellos de botella o ineficiencias
3. Calcular el impacto económico real de resolverlos con IA
4. Proponer el siguiente paso concreto (sin presionar)

Perfil del cliente ideal: [ICP definido]
Tu oferta: [servicio/producto]
Precio orientativo: [rango]

Estilo: conversacional, empático, experto pero cercano. No uses jerga técnica. Sé directo y concreto.

Cuando tengas suficiente contexto para hacer un diagnóstico, calcula el ROI con números reales y propón el siguiente paso.
```

### FASE 4: EXPORTACIÓN — Configurar destino de leads

Según lo que eligió el usuario:

**Opción A: Google Sheets**
- Crear webhook con Google Apps Script
- Instrucciones paso a paso para conectar

**Opción B: Supabase**
- Esquema de tabla SQL para los leads
- Instrucciones de conexión con API key

**Opción C: Solo email**
- Envío vía API de correo (Resend / EmailJS)
- Configuración en vercel.json

**Opción D: CRM (HubSpot, Pipedrive, etc.)**
- Webhook al CRM correspondiente
- Instrucciones de creación del webhook

### FASE 5: DESPLIEGUE — Publicar en Vercel

Instrucciones de despliegue:

```bash
# 1. Inicializar proyecto
git init
git add .
git commit -m "feat: consultor ia ventas [negocio]"

# 2. Subir a GitHub
gh repo create consultor-[negocio] --public --source=.

# 3. Conectar con Vercel (vía MCP Vercel o CLI)
vercel deploy --prod

# 4. Variables de entorno en Vercel
ANTHROPIC_API_KEY=sk-...
[otras variables según destino de leads]
```

Después del despliegue, entregar:
- URL pública del consultor
- Snippet de código para embeberlo como burbuja en cualquier web
- Instrucciones para cambiar colores/textos sin tocar código

---

## Informe comercial (output secundario)

Al terminar el consultor, generar opcionalmente un informe comercial en markdown:

```markdown
# Informe de Oportunidad IA — [Nombre del negocio]

## Diagnóstico
[3-4 líneas sobre la situación actual]

## Oportunidades detectadas
1. [Proceso 1] → ahorro estimado: X€/mes
2. [Proceso 2] → ingresos extra estimados: X€/mes

## ROI proyectado
- Inversión estimada en implementación: X€
- Ahorro/ingresos extra primer año: X€
- Retorno de inversión: X meses

## Próximo paso recomendado
[Llamada de 30 min / Demo / Propuesta técnica]

## Contacto capturado
[Nombre, email, empresa, teléfono]
```

Este informe se puede enviar automáticamente al operador o guardar en Google Drive.

---

## Notas estratégicas

### Aplicación a Blindbeds Supply
Este consultor es directamente aplicable para cualificar hoteles interesados en el sistema de pedidos Blindbeds Supply:
- Preguntas de cualificación: número de habitaciones, proveedores actuales, proceso actual de pedidos
- Diagnóstico: ineficiencias en gestión de pedidos a proveedores
- Impacto económico: horas de administración ahorradas × coste hora
- Propuesta: demo del sistema + piloto en Soho

### Producto monetizable
Este mismo flujo (personalizar → código → desplegar) es vendible como servicio:
- **Precio orientativo servicio**: 800-2.500€ (creación y despliegue del consultor)
- **Precio mantenimiento/actualización**: 150-300€/mes
- **Target**: negocios locales, agencias, consultores que quieren su propio consultor IA
- La skill automatiza ~80% del trabajo de creación

---

## Edge cases

- **Sin web del cliente**: ofrecer crear una landing page mínima con la skill `web-express`
- **Sin presupuesto para API**: calcular coste real de Claude Haiku (muy bajo, <5€/mes para uso normal) y mostrar al usuario
- **Cliente no técnico**: las instrucciones de despliegue deben ser paso a paso, sin asumir conocimiento técnico
- **Sin idioma definido**: preguntar al inicio, mantener en todo el flujo

---

## Skills relacionadas

- `web-express` — si el cliente no tiene web donde embeberlo
- `arnes` — para proyectos de mayor complejidad que necesitan backend robusto
- `skill-antibloqueo` — si el usuario se bloquea decidiendo qué preguntas hacer al lead
