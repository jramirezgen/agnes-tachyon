#!/bin/bash
# oc_ollama_qwen.sh
# Wrapper seguro para invocar Qwen en Ollama desde OpenClaw
# Uso: oc_ollama_qwen.sh "prompt"

LOGFILE="$HOME/.openclaw/logs/ollama_qwen.log"
PROMPT="$1"

if [ -z "$PROMPT" ]; then
  echo "[ERROR] Debes proporcionar un prompt como argumento" | tee -a "$LOGFILE"
  exit 1
fi

# Ejecutar el modelo Qwen en Ollama
{
  echo "[$(date)] PROMPT: $PROMPT" >> "$LOGFILE"
  ollama run qwen:latest "$PROMPT" | tee -a "$LOGFILE"
}