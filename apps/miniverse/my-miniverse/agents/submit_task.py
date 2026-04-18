#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import urllib.request

SERVER = os.getenv("MINIVERSE_SERVER_URL", "http://localhost:4341")
EXTERNAL_ID = "external-user"
BOSS_ID = "boss-agent"


def post(path: str, payload: dict) -> None:
    req = urllib.request.Request(
        f"{SERVER}{path}",
        method="POST",
        headers={"Content-Type": "application/json"},
        data=json.dumps(payload).encode("utf-8"),
    )
    with urllib.request.urlopen(req, timeout=10):
        pass


def main() -> int:
    text = " ".join(sys.argv[1:]).strip()
    if not text:
        print('Uso: python3 agents/submit_task.py "tu tarea"')
        return 1

    post("/api/heartbeat", {
        "agent": EXTERNAL_ID,
        "name": "Usuario Externo",
        "state": "speaking",
        "task": "Enviando tarea",
    })

    post("/api/act", {
        "agent": EXTERNAL_ID,
        "action": {
            "type": "message",
            "to": BOSS_ID,
            "message": text,
        },
    })

    print(f"Tarea enviada a {BOSS_ID}: {text}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
