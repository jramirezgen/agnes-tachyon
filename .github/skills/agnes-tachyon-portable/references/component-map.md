# Component Map

## Código Operativo Crítico

- `apps/miniverse/my-world/start_operational_stack.sh`
- `apps/miniverse/my-world/stop_operational_stack.sh`
- `apps/miniverse/my-world/server.js`
- `apps/miniverse/my-miniverse/agents/runtime.py`
- `apps/miniverse/my-miniverse/agents/librarian_learn.py`
- `apps/miniverse/my-miniverse/agents/librarian_learn_swift.py`
- `tachyon/trainer.py`
- `tachyon/config.py`
- `tachyon/persona_dataset.py`

## Datos y Estado

- `data/models/` contiene artefactos entrenados y checkpoints.
- `data/models/librarian_swift/runs/` puede crecer sin control si no se aplica retención.
- `data/models/librarian_swift/merged/` contiene modelos exportados fusionados.

## Configuración Operativa Relevante

- `ENABLE_LIBRARIAN_LEARNER`
- `LIBRARIAN_SWIFT_MAX_ROUNDS`
- `LIBRARIAN_SWIFT_KEEP_RUNS`
- `LIBRARIAN_SWIFT_KEEP_MERGED`
- `LIBRARIAN_SWIFT_EXPORT_MERGED`
- `MINIVERSE_PYTHON`
- `AGNES_HOME`
- `AGNES_DATA_DIR`
- `TACHYON_URL`

## Riesgos Operativos ya Identificados

- Export merged con ms-swift puede disparar RAM y swap.
- Retención laxa provoca crecimiento de disco en `runs/`.
- Arrancar learner por defecto sin límites puede recrear saturación.

## Configuración Estable Actual

- Bibliotecaria continua activada solo cuando se solicita.
- Export merged desactivado por defecto para minimizar memoria.
- Retención agresiva: 3 runs, 2 merged.
- Portabilidad base: code-only sin modelos entrenados, pero con referencias del modelo base actual.