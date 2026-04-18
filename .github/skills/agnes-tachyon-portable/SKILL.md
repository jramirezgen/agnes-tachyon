---
name: agnes-tachyon-portable
description: 'Versión editable de la skill para empaquetar, migrar y reproducir Agnes/Tachyon y el stack Miniverse en otra máquina de forma portable, autocontenida e independiente. Prioriza code-only, Linux/WSL como núcleo backend, y preserva referencias del modelo base actual sin incluir modelos entrenados. Cubre backend y frontend operativo. Triggers: agnes portable, tachyon portable, migrate agnes, export miniverse stack, backup tachyon, reproducir en otra máquina, bundle autocontenido.'
argument-hint: 'Objetivo de portabilidad: code-only por defecto; opcionalmente con datasets; host Linux/WSL destino'
user-invocable: true
disable-model-invocation: false
---

# Agnes Tachyon Portable

Esta es la versión editable de la skill. La copia congelada de referencia vive en [agnes/.github/skills/agnes-tachyon-portable-frozen/SKILL.md](agnes/.github/skills/agnes-tachyon-portable-frozen/SKILL.md).

Skill para convertir Agnes/Tachyon en un bundle reproducible y trasladable a otra máquina sin arrastrar artefactos temporales ni saturación de recursos.

## Qué Produce

- Un bundle comprimido con el código operativo de Agnes/Tachyon.
- Un manifiesto de archivos incluidos y checksums.
- Un snapshot del entorno Python y Node relevante.
- Un snapshot exacto del entorno Conda cuando esté disponible.
- Un archivo de variables de entorno optimizadas para la bibliotecaria.
- Un snapshot de referencias del modelo base actual para reconstrucción posterior sin depender de modelos entrenados exportados.
- Una guía de restauración y validación en la máquina destino.
- Scripts para restaurar y verificar el stack ya migrado.

## Cuándo Usarla

- Cuando quieras mover Agnes/Tachyon a otra workstation.
- Cuando necesites un backup reproducible del stack.
- Cuando quieras clonar la configuración estable de aprendizaje continuo sin copiar basura de entrenamiento.
- Cuando necesites reconstruir el sistema en un entorno nuevo con el mismo comportamiento operativo.

## Alcance y Reglas

- El bundle incluye el código del repositorio, scripts de operación y snapshots de entorno.
- Por defecto excluye modelos entrenados, modelos pesados, logs, checkpoints, caches y artefactos efímeros.
- Por defecto conserva solo referencias del modelo base actual y de los modelos lógicos del sistema.
- Los datasets se incluyen solo si se solicitan explícitamente.
- Los modelos entrenados no se incluyen salvo decisión manual futura fuera del flujo base.
- La exportación prioriza reproducibilidad y estabilidad antes que volumen máximo de datos.

## Flujo

1. Identifica el objetivo de portabilidad.
2. Decide el nivel del bundle.
3. Exporta el bundle con [scripts/export_agnes_tachyon_bundle.sh](./scripts/export_agnes_tachyon_bundle.sh).
4. Revisa el resultado con [references/portability-checklist.md](./references/portability-checklist.md).
5. Restaura en destino con [scripts/restore_agnes_tachyon_bundle.sh](./scripts/restore_agnes_tachyon_bundle.sh).
6. Configura la máquina destino siguiendo [references/reproduction-playbook.md](./references/reproduction-playbook.md).
7. Valida arranque, API y loop de bibliotecaria con [scripts/verify_restored_stack.sh](./scripts/verify_restored_stack.sh).

## Niveles de Bundle

### 1. Code-only

Usar cuando:
- Solo necesitas el código y la configuración reproducible.
- La máquina destino reconstruirá datasets y entornos.

Incluye:
- Repositorio Agnes completo sin artefactos pesados.
- Scripts de arranque y parada.
- Configuración del trainer y learner.
- Snapshot del entorno.

### 2. Code + datasets

Usar cuando:
- También necesitas datasets locales pequeños o curados.
- Quieres reducir trabajo manual en la restauración.

Incluye además:
- Datos no pesados dentro de data, excluyendo modelos y runs.

### 3. Code + datasets + referencias de modelo

Usar cuando:
- Necesitas reconstrucción rápida apoyada en el modelo base actual.
- No quieres arrastrar modelos entrenados ni artefactos pesados.

Incluye además:
- Referencias textuales del modelo base de ms-swift y del modelo base/local de Ollama-Tachyon.

## Decisiones y Ramas

### Si el destino tiene GPU compatible

- Mantén el flujo ms-swift con QLoRA.
- Usa el entorno de Python GPU del stack.
- Activa aprendizaje continuo solo tras pasar validación base.

### Si el destino no tiene GPU compatible

- Migra en modo code-only o code + datasets.
- Deja la bibliotecaria desactivada o limita entrenamiento.
- Usa el bundle como base estructural, no como réplica completa de entrenamiento.

### Si buscas máxima estabilidad

- Exporta sin modelos pesados ni entrenados.
- Mantén `LIBRARIAN_SWIFT_EXPORT_MERGED=0`.
- Mantén retención agresiva: 3 runs, 2 merged.

### Si buscas réplica funcional inmediata

- Usa el bundle code-only con referencias del modelo base actual.
- Rehidrata el modelo en destino a partir de esas referencias, no desde pesos entrenados copiados.
- Verifica compatibilidad de CUDA, PyTorch y ms-swift antes de arrancar el learner.

### Si el host destino también servirá frontend

- Conserva `server.js`, assets web y el flujo Node del Miniverse.
- Valida backend y frontend juntos: API en `4331` y render del frontend local.
- Mantén Linux/WSL como núcleo backend aunque el navegador viva fuera de WSL.

## Procedimiento Operativo

### A. Exportar en la máquina origen

1. Sitúate en el repositorio Agnes.
2. Ejecuta el exportador con el nivel deseado.
3. Verifica que existan el `.tar.gz`, el manifiesto y el archivo de checksums.
4. Copia el bundle al destino.

Ejemplos:

```bash
cd /ruta/a/agnes
bash .github/skills/agnes-tachyon-portable/scripts/export_agnes_tachyon_bundle.sh --profile code-only
bash .github/skills/agnes-tachyon-portable/scripts/export_agnes_tachyon_bundle.sh --profile with-datasets
bash .github/skills/agnes-tachyon-portable/scripts/export_agnes_tachyon_bundle.sh --profile full-portable
```

### B. Restaurar en la máquina destino

1. Descomprime el bundle en la ruta deseada.
2. Revisa `portable_bundle/env/` para reconstruir el entorno.
3. Ajusta `AGNES_HOME`, `AGNES_DATA_DIR` y `MINIVERSE_PYTHON` si cambian las rutas.
4. Arranca primero el stack sin learner.
5. Verifica healthcheck.
6. Activa la bibliotecaria solo cuando el sistema base esté estable.

## Criterios de Calidad

La skill se considera completada cuando:

- Existe un bundle comprimido válido.
- Existe un manifiesto con los archivos incluidos.
- Existen checksums verificables.
- Existe snapshot de entorno Python/Node.
- Existen referencias del modelo base actual.
- El destino puede arrancar el stack y responder en API.
- Si se activa la bibliotecaria, lo hace con parámetros optimizados y sin exportación merged por defecto.

## Configuración Operativa Recomendada

Usa [assets/optimized-learner.env](./assets/optimized-learner.env) como base.

Parámetros recomendados:
- `ENABLE_LIBRARIAN_LEARNER=1`
- `LIBRARIAN_SWIFT_MAX_ROUNDS=999`
- `LIBRARIAN_SWIFT_KEEP_RUNS=3`
- `LIBRARIAN_SWIFT_KEEP_MERGED=2`
- `LIBRARIAN_SWIFT_EXPORT_MERGED=0`

## Componentes Críticos Cubiertos

Ver [references/component-map.md](./references/component-map.md).

## Carpetas Implicadas

Ver [references/portable-folders.md](./references/portable-folders.md).

## Scope Objetivo

- Linux/WSL como núcleo backend principal.
- También cubre la pieza frontend servida por Node/Miniverse.
- El navegador o shell visual pueden vivir fuera de WSL; la lógica y operación quedan en backend Linux/WSL.

## Decisiones Congeladas para Esta Línea

- Bundle base: code-only.
- Modelos entrenados: excluidos.
- Referencias de modelo: incluidas.
- Scope: proyecto.
- Host objetivo: Linux/WSL backend con soporte del frontend local.