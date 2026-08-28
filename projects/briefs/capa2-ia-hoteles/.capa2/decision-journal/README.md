# Diario de decisiones de Capa 2 (FR-053)

Diseño aprobado: `AI_OS/PROJECTS/capa2-ia-hoteles-diseno-fr053.md` (léelo primero — este
README es la chuleta operativa, no la fuente de verdad del diseño).

Registro append-only, local a este repo, de las decisiones materiales del proyecto
`capa2-ia-hoteles` (orden/cadencia de publicación, formato, nivel de firma de marca,
experimentos y su criterio de éxito, cambios de reglas del loop). `content-log.md` sigue
siendo la única fuente del estado editorial — este diario nunca lo toca.

## Qué es cada cosa

```
projects/briefs/capa2-ia-hoteles/
  knowledge/decisions/           # notas de fuente breves y versionadas (con encabezado de contexto)
  .capa2/decision-journal/
    decisions/                   # registros OPEN, inmutables, create-once (motor base)
    closures/                    # cierres inmutables, create-once (motor base)
    derived/                     # status.json / STATUS.md — REGENERABLE, gitignored, nunca se edita a mano
    capa2_decisions/             # adaptador de Capa 2 (este paquete)
    tests/                       # pruebas del adaptador + fixtures
    README.md                    # este archivo
```

- El motor (`DecisionJournal`, en `knowledge_ingest.decision_journal`) vive en el repo
  privado `~/MAIN_PROYECTOS/knowledge-ingest`. No está copiado aquí: `capa2_decisions`
  lo importa en tiempo de ejecución (ver `capa2_decisions/engine_path.py`). Si ese repo
  vive en otra ruta en este equipo, define `CAPA2_KNOWLEDGE_INGEST_SRC=/ruta/a/src` antes
  de ejecutar cualquier comando.
- `capa2_decisions` **no** reimplementa `due`/`close` — esos siguen siendo, literalmente,
  `python -m knowledge_ingest.decision_journal ...`. `add` es la única excepción: vive en
  `capa2_decisions add` porque es el punto donde hay que garantizar que una fuente con
  Soho/PII no pueda entrar nunca — validar y persistir son una sola operación, sin ventana
  intermedia para saltarse la validación (ver "Flujo para registrar una decisión nueva").
  El resto de lo que añade este adaptador es: el encabezado de contexto de Capa 2, el
  filtro de Soho, y la vista derivada.

## Preparar el entorno

Desde `projects/briefs/capa2-ia-hoteles/`:

```bash
export PYTHONPATH="$HOME/MAIN_PROYECTOS/knowledge-ingest/src:.capa2/decision-journal"
```

Con eso funcionan a la vez `python -m knowledge_ingest.decision_journal ...` y
`python -m capa2_decisions ...`. (Si solo vas a usar `capa2_decisions`, basta con la
segunda ruta — internamente resuelve la primera sola.)

## Flujo para registrar una decisión nueva

1. Escribe la nota en `knowledge/decisions/D-NNN-titulo-corto.md` con el encabezado:

   ```yaml
   ---
   scope: content|cadence|format|brand|loop
   content_ids: [S9]
   metric_code: engagement_rate
   baseline: "mediana S6-S7"
   target: ">= baseline"
   owner: luisfran
   ---
   ```

   `supersedes: D-001` es un campo opcional (extensión de este adaptador, no del motor
   base) para encadenar una decisión `ADJUST` con la que sustituye.

2. (Opcional, solo diagnóstico) valida la nota mientras la escribes, sin darla de alta
   todavía:

   ```bash
   python -m capa2_decisions validate-source knowledge/decisions/D-NNN-titulo-corto.md
   ```

   Este paso es solo para iterar rápido sobre la nota. **No sustituye ni es un
   prerrequisito separable del paso 3** — nada obliga a ejecutarlo, así que no es la
   puerta real de seguridad.

3. Da de alta la decisión con el comando único del adaptador. Esta es la ÚNICA vía
   soportada para registrar una decisión: valida el encabezado de contexto + el filtro de
   Soho + el filtro de datos personales de la fuente, calcula su hash, y solo si todo pasa
   llama al motor base (create-once; un ID repetido falla sin sobrescribir nada). Si la
   validación falla, no se escribe nada en el almacén — no hay ventana intermedia en la que
   una fuente con Soho/PII pueda colarse saltándose el paso 2:

   ```bash
   python -m capa2_decisions --project-root . add \
     --id D-NNN \
     --title "..." \
     --source-document "knowledge/decisions/D-NNN-titulo-corto.md" \
     --friction FR-053 \
     --hypothesis "..." \
     --expected-outcome "..." \
     --review-on YYYY-MM-DD
   ```

   (Llamar directamente a `python -m knowledge_ingest.decision_journal ... add` sigue
   siendo posible a nivel de motor — no se ha tocado su lógica — pero ya no es el flujo
   documentado ni soportado para este adaptador, precisamente porque se salta la
   validación de Capa 2.)

4. Regenera la vista y confirma que todo sigue íntegro:

   ```bash
   python -m capa2_decisions status --format markdown
   python -m capa2_decisions check
   ```

## Revisar decisiones vencidas

```bash
python -m knowledge_ingest.decision_journal .capa2/decision-journal --project-root . due --as-of $(date +%F)
```

Con evidencia real en la mano, cerrar (esto también es inmutable — no se puede reabrir):

```bash
python -m knowledge_ingest.decision_journal .capa2/decision-journal --project-root . close \
  --id D-NNN \
  --actual-outcome "..." \
  --decision ADOPT|ADJUST|DISCARD
```

Si el veredicto es `ADJUST`, la decisión sucesora se registra como una decisión NUEVA
(pasos de arriba) cuya nota de fuente incluye `supersedes: D-NNN` en el encabezado — el
diario nunca muta un registro existente.

## Comandos de `capa2_decisions`

| Comando | Qué hace |
|---|---|
| `add --id ... --title ... --source-document ... --friction ... --hypothesis ... --expected-outcome ... --review-on ...` | ÚNICA vía soportada para dar de alta una decisión. Valida la fuente (encabezado + Soho + PII), calcula su hash, y solo si todo pasa llama al motor base. Sin ventana entre validar y persistir. |
| `status --format markdown\|json [--as-of YYYY-MM-DD]` | Regenera `derived/status.json` y `derived/STATUS.md`, imprime uno de los dos. Determinista: mismos datos + mismo `--as-of` ⇒ misma salida. Corre el mismo barrido que `check`: cualquier decisión con un hallazgo de integridad se excluye de las tablas normales y solo aparece en "Errores de integridad". |
| `check` | Barrido de solo lectura: revalida hash/fuente de cada decisión, la forma del propio almacén (symlinks, ficheros sueltos, closures huérfanos), su encabezado de contexto, y filtra Soho/PII tanto en la fuente como en los campos guardados — incluido `actual_outcome` de los cierres. Sale con código 1 si encuentra algo. |
| `validate-source <ruta>` | Diagnóstico SIN tocar el almacén y SIN dar de alta nada — útil mientras escribes la nota, pero no es la puerta de seguridad real (esa es `add`). |

## Qué lee el loop de contenido

`~/.claude/scheduled-tasks/loop-contenido-capa2-borrador/SKILL.md` lee
`.capa2/decision-journal/derived/STATUS.md` en modo solo lectura para avisar de
decisiones vencidas o próximas en su mensaje de cierre. Si ese archivo no existe (por
ejemplo, nadie ha corrido `status` todavía), el loop sigue funcionando exactamente igual
— la integración es un añadido, no una dependencia dura (criterio de aceptación 8 del
diseño). El loop nunca escribe en este diario ni lo usa para decidir nada por sí mismo.

## Recuperación y cambio de equipo (Mac ↔ HP)

- Los registros (`decisions/`, `closures/`) y las fuentes (`knowledge/decisions/`) están
  versionados en Git — ver la excepción específica en `.gitignore` (busca "FR-053"). El
  resto de esta carpeta de brief sigue siendo privado y gitignored como cualquier otro.
- `derived/` es regenerable y está gitignored a propósito: nunca se recupera desde Git, se
  reconstruye con `python -m capa2_decisions status`.
- Para recuperar el almacén desde cero (equipo nuevo o incidente): `git pull`, ejecutar
  `check` para confirmar integridad, luego `status` para regenerar `derived/`.
- Si `knowledge-ingest` no está clonado en la ruta por defecto del equipo, exporta
  `CAPA2_KNOWLEDGE_INGEST_SRC` apuntando a su `src/` antes de cualquier comando.
- Este diario no tiene ejecución periódica propia ni scheduler: es local, manual y de
  solo lectura para el loop. No hay nada que instalar en HP salvo clonar ambos repos y
  exportar la variable de entorno si la ruta difiere.

## Pruebas

```bash
cd .capa2/decision-journal
python3 -m unittest tests.test_capa2_decisions -v
```

Estas pruebas cubren solo lo que añade este adaptador (encabezado de contexto, filtro
Soho, vista derivada, barrido de integridad). Las invariantes del motor base (escritura
atómica create-once, symlinks inseguros, travesía de rutas, vínculo de hash) ya están
cubiertas por la suite propia de `knowledge-ingest`
(`PYTHONPATH=src python3 -m unittest tests.test_decision_journal -v` desde ese repo) y no
se duplican aquí.
