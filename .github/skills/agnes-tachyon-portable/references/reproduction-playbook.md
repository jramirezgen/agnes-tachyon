# Reproduction Playbook

## 1. Desempaquetar

```bash
cd /ruta/al/repo/origen
bash .github/skills/agnes-tachyon-portable/scripts/restore_agnes_tachyon_bundle.sh /ruta/al/agnes-tachyon-YYYYMMDDTHHMMSSZ.tar.gz ~/restore-agnes
cd ~/restore-agnes/portable_bundle/repo/agnes
```

## 2. Reconstruir Entorno

- Revisar `portable_bundle/env/python-version.txt`.
- Revisar `portable_bundle/env/node-version.txt`.
- Revisar `portable_bundle/env/model-reference.txt` para rehidratar el modelo base esperado.
- Si existe, usar `portable_bundle/env/miniverse-gpu-pip-freeze.txt` para comparar paquetes.
- Si existen, usar `portable_bundle/env/miniverse-gpu-conda-env.yml` y `portable_bundle/env/miniverse-gpu-conda-explicit.txt` para reconstrucción exacta.
- Ajustar `MINIVERSE_PYTHON` si la ruta del entorno cambia.

## 3. Arranque Base

```bash
cd apps/miniverse/my-world
ENABLE_LIBRARIAN_LEARNER=0 ./start_operational_stack.sh
curl -fsS http://localhost:4331/api/agents
```

Validación mínima adicional de frontend:

```bash
curl -fsS http://localhost:4331/ >/dev/null && echo frontend-ok
```

## 4. Activar Bibliotecaria Optimizada

```bash
cd apps/miniverse/my-world
set -a
. ../../../.github/skills/agnes-tachyon-portable/assets/optimized-learner.env
set +a
./start_operational_stack.sh
```

## 5. Verificación

```bash
../../../.github/skills/agnes-tachyon-portable/scripts/verify_restored_stack.sh "$PWD/../../.."
ps aux | grep -E 'runtime.py|librarian_learn_swift.py|node server.js' | grep -v grep
tail -n 50 generated/librarian_learn.log
```

## 6. Si el Host es Menos Potente

- Mantener `ENABLE_LIBRARIAN_LEARNER=0` hasta estabilizar.
- Reducir pasos por tópico si hace falta.
- No habilitar export merged.