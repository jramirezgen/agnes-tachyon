#!/bin/bash
# oc_ollama_qwen_windows.sh
# Wrapper para prompts Qwen que pueden ejecutar acciones en Windows desde WSL
# Uso: oc_ollama_qwen_windows.sh "prompt"

LOGFILE="$HOME/.openclaw/logs/ollama_qwen_windows.log"
PROMPT="$1"

if [ -z "$PROMPT" ]; then
  echo "[ERROR] Debes proporcionar un prompt como argumento" | tee -a "$LOGFILE"
  exit 1
fi

# Consultar a Qwen
QWEN_OUT=$(ollama run qwen:latest "$PROMPT")
echo "[$(date)] PROMPT: $PROMPT" >> "$LOGFILE"
echo "QWEN: $QWEN_OUT" >> "$LOGFILE"

# Buscar si Qwen sugiere una acción Windows (ejemplo: abrir carpeta)
# Patrón simple: "Abrir carpeta C:\\..." o "Start-Process ..."
if [[ "$QWEN_OUT" =~ (Start-Process|explorer.exe|Abrir carpeta|Open folder) ]]; then
  # Extraer comando PowerShell sugerido
  # Busca línea con Start-Process o explorer.exe
  CMD=$(echo "$QWEN_OUT" | grep -Eo 'Start-Process [^\n]*|explorer.exe [^\n]*')
  if [ -n "$CMD" ]; then
    echo "Ejecutando en Windows: $CMD" | tee -a "$LOGFILE"
    $HOME/.local/bin/oc_windows_exec.sh "$CMD"
  else
    echo "No se detectó comando ejecutable claro en la respuesta de Qwen." | tee -a "$LOGFILE"
  fi
else
  echo "No se detectó acción Windows en la respuesta de Qwen." | tee -a "$LOGFILE"
fi

echo "$QWEN_OUT"
