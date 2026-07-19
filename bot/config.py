import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    bot_token: str
    allowed_chat_id: int
    db_path: str
    log_level: str

    @classmethod
    def from_env(cls) -> "Config":
        token = os.environ.get("BOT_TOKEN", "").strip()
        if not token:
            raise ValueError("BOT_TOKEN environment variable is required")

        raw_chat_id = os.environ.get("ALLOWED_CHAT_ID", "").strip()
        if not raw_chat_id:
            raise ValueError("ALLOWED_CHAT_ID environment variable is required")
        try:
            allowed_chat_id = int(raw_chat_id)
        except ValueError:
            raise ValueError(f"ALLOWED_CHAT_ID must be an integer, got: {raw_chat_id!r}")

        return cls(
            bot_token=token,
            allowed_chat_id=allowed_chat_id,
            db_path=os.environ.get("DB_PATH", "data/ziotackus.db").strip(),
            log_level=os.environ.get("LOG_LEVEL", "INFO").strip().upper(),
        )
