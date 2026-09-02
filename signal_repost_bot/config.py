"""Configuration loader supporting YAML files and Environment variables."""

import os
from pathlib import Path
from typing import List, Optional
import yaml
from pydantic import BaseModel, Field


class FilterConfig(BaseModel):
    require_photo: bool = True
    require_text: bool = True
    allow_videos: bool = True
    allow_gifs: bool = True
    ignore_replies: bool = False
    ignore_bot_messages: bool = True
    whitelisted_senders: List[str] = Field(default_factory=list)
    blacklisted_senders: List[str] = Field(default_factory=list)


class FormattingConfig(BaseModel):
    prepend_group_name: bool = True
    prepend_sender_name: bool = True
    include_sender_number: bool = False
    include_dm_link: bool = False
    header_template: str = "📸 [{group_name}] {sender_name}:\n\n"
    show_timestamp: bool = False


class StorageConfig(BaseModel):
    db_path: str = "data/bot_state.db"
    dedup_ttl_days: int = 30


class RouteConfig(BaseModel):
    """Represents a single routing rule from source groups to a spectator group."""
    name: str = "Default Route"
    spectator_group_id: str
    source_group_ids: List[str] = Field(default_factory=lambda: ["*"])
    filters: FilterConfig = Field(default_factory=FilterConfig)
    formatting: FormattingConfig = Field(default_factory=FormattingConfig)


class AppConfig(BaseModel):
    signal_account: str
    spectator_group_id: Optional[str] = None
    source_group_ids: List[str] = Field(default_factory=lambda: ["*"])
    routes: List[RouteConfig] = Field(default_factory=list)
    client_mode: str = "jsonrpc_socket"  # "jsonrpc_socket", "jsonrpc_stdio", "rest_api"
    endpoint: str = "127.0.0.1:7583"
    filters: FilterConfig = Field(default_factory=FilterConfig)
    formatting: FormattingConfig = Field(default_factory=FormattingConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    log_level: str = "INFO"

    @classmethod
    def load(cls, config_path: Optional[str] = None) -> "AppConfig":
        """Load configuration from YAML file and apply environment variable overrides."""
        data = {}

        # 1. Load from file if provided or default exists
        file_to_check = config_path or os.environ.get("CONFIG_PATH", "config.yaml")
        if Path(file_to_check).exists():
            with open(file_to_check, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}

        # 2. Environment variable overrides
        if os.environ.get("SIGNAL_ACCOUNT"):
            data["signal_account"] = os.environ["SIGNAL_ACCOUNT"]
        if os.environ.get("SPECTATOR_GROUP_ID"):
            data["spectator_group_id"] = os.environ["SPECTATOR_GROUP_ID"]
        if os.environ.get("SOURCE_GROUP_IDS"):
            sources = os.environ["SOURCE_GROUP_IDS"].split(",")
            data["source_group_ids"] = [s.strip() for s in sources if s.strip()]
        if os.environ.get("CLIENT_MODE"):
            data["client_mode"] = os.environ["CLIENT_MODE"]
        if os.environ.get("SIGNAL_ENDPOINT"):
            data["endpoint"] = os.environ["SIGNAL_ENDPOINT"]
        if os.environ.get("LOG_LEVEL"):
            data["log_level"] = os.environ["LOG_LEVEL"]
        if os.environ.get("DB_PATH"):
            data.setdefault("storage", {})["db_path"] = os.environ["DB_PATH"]

        return cls(**data)

    def model_post_init(self, __context):
        """Ensure single-route configuration is wrapped in routes if routes is empty."""
        if not self.routes and self.spectator_group_id:
            default_route = RouteConfig(
                name="Default Route",
                spectator_group_id=self.spectator_group_id,
                source_group_ids=self.source_group_ids,
                filters=self.filters,
                formatting=self.formatting,
            )
            self.routes.append(default_route)
