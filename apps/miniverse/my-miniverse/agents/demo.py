#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys

TASKS = [
    "Analiza flujo de caja trimestral con ingresos 15000 y gastos 12800, con plan de mejora.",
    "Aprende metodo 50/30/20 y crea guia practica para negocio pequeno.",
]


def main() -> int:
    for task in TASKS:
        subprocess.Popen([sys.executable, "agents/submit_task.py", task])
    print("Demo enviada: 2 tareas en paralelo")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
