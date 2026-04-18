"""Persistent Conversation Memory — JSON-backed with summarization."""
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

from . import config

log = logging.getLogger("tachyon.memory")


@dataclass
class Message:
    role: str        # "user" | "assistant" | "system"
    content: str
    timestamp: float = field(default_factory=time.time)
    state: str = ""  # personality state at the time


class ConversationMemory:
    """Manages conversation history with persistence."""

    def __init__(self, path: Path = None):
        self.path = path or config.MEMORY_FILE
        self.messages: list[dict] = []
        self.summaries: list[str] = []
        self._load()

    def _load(self):
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text())
                self.messages = data.get("messages", [])
                self.summaries = data.get("summaries", [])
                log.info("Loaded %d messages, %d summaries from memory.",
                         len(self.messages), len(self.summaries))
            except (json.JSONDecodeError, KeyError):
                log.warning("Corrupted memory file, starting fresh.")
                self.messages = []
                self.summaries = []

    def save(self):
        self.path.write_text(json.dumps({
            "messages": self.messages,
            "summaries": self.summaries,
        }, ensure_ascii=False, indent=1))

    def add(self, role: str, content: str, state: str = ""):
        msg = {
            "role": role,
            "content": content,
            "ts": time.time(),
            "state": state,
        }
        self.messages.append(msg)

        # Auto-trim: keep only recent messages in active memory
        if len(self.messages) > config.MAX_MEMORY_MESSAGES * 2:
            # Archive old messages as summary
            old = self.messages[:config.MAX_MEMORY_MESSAGES]
            self.messages = self.messages[config.MAX_MEMORY_MESSAGES:]
            summary = self._summarize_batch(old)
            if summary:
                self.summaries.append(summary)

        self.save()

    def get_context(self, n: int = 20) -> list[dict]:
        """Return last N messages formatted for LLM context."""
        return [
            {"role": m["role"], "content": m["content"]}
            for m in self.messages[-n:]
        ]

    def get_history_texts(self, n: int = 10) -> list[str]:
        """Return last N user message texts for novelty detection."""
        return [
            m["content"] for m in self.messages[-n:]
            if m["role"] == "user"
        ]

    def get_memory_context(self) -> str:
        """Build memory context string from summaries."""
        if not self.summaries:
            return ""
        recent = self.summaries[-3:]
        return "\n[Resumen de conversaciones previas]\n" + "\n---\n".join(recent)

    def _summarize_batch(self, messages: list[dict]) -> str:
        """Create a simple extractive summary of a batch of messages."""
        if not messages:
            return ""
        user_msgs = [m["content"][:100] for m in messages if m["role"] == "user"]
        assistant_msgs = [m["content"][:100] for m in messages if m["role"] == "assistant"]
        ts_start = messages[0].get("ts", 0)
        ts_end = messages[-1].get("ts", 0)
        return (
            f"Sesión ({time.strftime('%Y-%m-%d %H:%M', time.localtime(ts_start))} - "
            f"{time.strftime('%H:%M', time.localtime(ts_end))}): "
            f"{len(user_msgs)} mensajes del Entrenador, {len(assistant_msgs)} respuestas de Tachyon. "
            f"Temas: {'; '.join(user_msgs[:5])}"
        )

    def clear(self):
        self.messages = []
        self.summaries = []
        self.save()

    @property
    def count(self) -> int:
        return len(self.messages)
