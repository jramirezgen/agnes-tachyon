# Portability Checklist

## Antes de Exportar

- Confirmar que el stack base arranca.
- Confirmar que `start_operational_stack.sh` y `stop_operational_stack.sh` funcionan.
- Confirmar espacio libre suficiente para el bundle.
- Confirmar si se incluirán datasets o modelos.

## Exportación

- Ejecutar el script con el perfil correcto.
- Verificar presencia de:
  - archivo `.tar.gz`
  - `file-manifest.txt`
  - `SHA256SUMS.txt`
  - `portable_bundle/env/optimized-learner.env`
  - `portable_bundle/env/model-reference.txt`
  - snapshot Conda si el host lo soporta

## Antes de Restaurar

- Confirmar versión de Linux o WSL destino.
- Confirmar disponibilidad de Node, Python y entorno GPU si aplica.
- Confirmar rutas equivalentes o plan de remapeo.

## Validación Post-Restauración

- Arrancar primero sin learner.
- Verificar `curl http://localhost:4331/api/agents`.
- Verificar `curl http://localhost:4331/`.
- Revisar logs en `generated/`.
- Activar learner solo después del healthcheck.
- Verificar que el loop continuo no exporte modelos merged por defecto.

## Cierre de Calidad

- API responde.
- Runtime permanece vivo.
- Bibliotecaria aprende sin crecer sin límite.
- No aparecen procesos huérfanos de export intensivo.