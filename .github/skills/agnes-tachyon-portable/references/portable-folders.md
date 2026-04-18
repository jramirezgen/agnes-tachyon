# Portable Folders

## Carpetas de la Skill

- `.github/skills/agnes-tachyon-portable/`
- `.github/skills/agnes-tachyon-portable-frozen/`

## Carpetas Operativas que se Exportan

- `apps/miniverse/my-world/`
- `apps/miniverse/my-miniverse/`
- `tachyon/`
- `docs/`
- `bin/`
- `tools/`

## Carpetas de Datos

- `data/` solo si el perfil no es `code-only`
- `data/models/` excluida por defecto
- `data/models/librarian_swift/runs/` excluida
- `data/models/librarian_swift/merged/` excluida

## Carpetas Generadas por la Portabilidad

- `dist/portable/` contiene los bundles generados
- Dentro de cada bundle:
  - `portable_bundle/repo/agnes/`
  - `portable_bundle/env/`
  - `portable_bundle/meta/`

## Carpetas Clave en Destino

- carpeta donde extraigas el bundle, por ejemplo `~/restore-agnes/`
- `portable_bundle/repo/agnes/apps/miniverse/my-world/`
- `portable_bundle/repo/agnes/apps/miniverse/my-miniverse/`
- `portable_bundle/repo/agnes/tachyon/`

## Carpetas a Vigilar

- `generated/` dentro de `apps/miniverse/my-world/`
- `data/models/` si luego rehidratas modelos o reanudas aprendizaje