---
name: agnes-tachyon-portable-frozen
description: 'Versión congelada de referencia para portabilidad de Agnes/Tachyon. Define un baseline fijo: code-only, sin modelos entrenados, con referencias del modelo base actual, Linux/WSL como núcleo backend y soporte del frontend local. Úsala como estándar inmutable o punto de comparación frente a la skill editable.'
argument-hint: 'Comparar contra baseline portable congelado o usarlo como estándar de migración'
user-invocable: true
disable-model-invocation: false
---

# Agnes Tachyon Portable Frozen

Esta skill es la copia congelada del flujo portable. No se debe mutar salvo que se quiera redefinir explícitamente el baseline.

## Baseline Fijo

- Bundle base: code-only.
- Modelos entrenados: excluidos.
- Referencias del modelo base actual: incluidas.
- Target principal: Linux/WSL como backend.
- Frontend local de Miniverse: incluido en el código y validado en restauración.
- Bibliotecaria: aprendizaje continuo permitido solo con parámetros optimizados.

## Artefactos de Referencia

- Skill editable: [agnes/.github/skills/agnes-tachyon-portable/SKILL.md](agnes/.github/skills/agnes-tachyon-portable/SKILL.md)
- Exportador: [agnes/.github/skills/agnes-tachyon-portable/scripts/export_agnes_tachyon_bundle.sh](agnes/.github/skills/agnes-tachyon-portable/scripts/export_agnes_tachyon_bundle.sh)
- Playbook: [agnes/.github/skills/agnes-tachyon-portable/references/reproduction-playbook.md](agnes/.github/skills/agnes-tachyon-portable/references/reproduction-playbook.md)
- Checklist: [agnes/.github/skills/agnes-tachyon-portable/references/portability-checklist.md](agnes/.github/skills/agnes-tachyon-portable/references/portability-checklist.md)

## Cuándo Usarla

- Cuando quieras comparar una variante futura contra una base estable.
- Cuando quieras una política fija de exportación que no arrastre entrenamientos.
- Cuando quieras reconstrucción reproducible en otra máquina sin ambigüedad operativa.

## Política Congelada

1. No incluir modelos entrenados.
2. Sí incluir referencias del modelo base actual.
3. Sí incluir backend y frontend operativo.
4. Sí validar primero API y luego learner.
5. No activar export merged por defecto.

## Ejecución Base

```bash
cd /ruta/a/agnes
bash .github/skills/agnes-tachyon-portable/scripts/export_agnes_tachyon_bundle.sh --profile code-only
```

## Criterio de Cumplimiento

La exportación cumple si produce:

- tarball portable
- manifiesto
- checksums
- snapshot de entorno
- referencia de modelo base

Para personalizaciones futuras, partir de la skill editable y preservar esta como baseline.