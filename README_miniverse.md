# Agnes Miniverse Runtime

Este arbol ejecuta Miniverse desde Agnes con copia sincronizada del codigo fuente.

## Comandos

- Iniciar: `/home/kaitokid/agnes/bin/agnes_miniverse_start.sh`
- Detener: `/home/kaitokid/agnes/bin/agnes_miniverse_stop.sh`

## Que sincroniza

- `/home/kaitokid/skills/miniverse/my-world` -> `/home/kaitokid/agnes/apps/miniverse/my-world`
- `/home/kaitokid/skills/miniverse/my-miniverse` -> `/home/kaitokid/agnes/apps/miniverse/my-miniverse`
- Wrappers de herramientas desde `~/.local/bin` -> `/home/kaitokid/agnes/tools/bin`

## Persistencia

- Modelos y artefactos en: `/home/kaitokid/agnes/data/models`
- En el runtime clonado, `models` es symlink a ese data dir.
