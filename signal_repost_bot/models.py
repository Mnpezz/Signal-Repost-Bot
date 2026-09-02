"""Data models for Signal envelopes, messages, and attachments."""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class Attachment(BaseModel):
    """Represents a Signal message attachment."""
    model_config = ConfigDict(populate_by_name=True)

    id: Optional[str] = None
    contentType: Optional[str] = Field(default=None, alias="contentType")
    filename: Optional[str] = None
    size: Optional[int] = None
    customFilename: Optional[str] = None
    storedFilename: Optional[str] = None
    path: Optional[str] = None

    @property
    def is_image(self) -> bool:
        """Return True if attachment is an image (JPEG, PNG, WebP, etc.)."""
        if not self.contentType:
            return False
        ct = self.contentType.lower()
        return ct.startswith("image/") and not ct.endswith("gif")

    @property
    def is_gif(self) -> bool:
        """Return True if attachment is an animated GIF."""
        if not self.contentType:
            return False
        return self.contentType.lower() == "image/gif"

    @property
    def is_video(self) -> bool:
        """Return True if attachment is a video (MP4, WebM, QuickTime, etc.)."""
        if not self.contentType:
            return False
        return self.contentType.lower().startswith("video/")


class GroupInfo(BaseModel):
    """Represents Signal Group information."""
    model_config = ConfigDict(populate_by_name=True)

    groupId: str
    name: Optional[str] = None
    type: Optional[str] = None


class QuoteInfo(BaseModel):
    """Represents quoted message info (a reply to another message)."""
    id: Optional[int] = None
    author: Optional[str] = None
    text: Optional[str] = None


class DataMessage(BaseModel):
    """Represents dataMessage payload inside a Signal envelope."""
    model_config = ConfigDict(populate_by_name=True)

    timestamp: Optional[int] = None
    message: Optional[str] = None
    expiresInSeconds: Optional[int] = 0
    groupInfo: Optional[GroupInfo] = Field(default=None, alias="groupInfo")
    attachments: List[Attachment] = Field(default_factory=list)
    quote: Optional[QuoteInfo] = None


class SignalEnvelope(BaseModel):
    """Represents a top-level Signal envelope from signal-cli JSON output."""
    model_config = ConfigDict(populate_by_name=True)

    source: Optional[str] = None
    sourceNumber: Optional[str] = Field(default=None, alias="sourceNumber")
    sourceUuid: Optional[str] = Field(default=None, alias="sourceUuid")
    sourceName: Optional[str] = Field(default=None, alias="sourceName")
    sourceUsername: Optional[str] = Field(default=None, alias="sourceUsername")
    username: Optional[str] = None
    sourceDevice: Optional[int] = Field(default=None, alias="sourceDevice")
    timestamp: Optional[int] = None
    dataMessage: Optional[DataMessage] = Field(default=None, alias="dataMessage")

    @property
    def sender_number(self) -> str:
        """Return best available sender identifier (sourceNumber or source)."""
        return self.sourceNumber or self.source or "Unknown"

    @property
    def sender_phone(self) -> Optional[str]:
        """Return sender phone number if available (e.g. +15551234567)."""
        if self.sourceNumber and self.sourceNumber.startswith("+"):
            return self.sourceNumber
        if self.source and self.source.startswith("+"):
            return self.source
        return None

    @property
    def sender_username(self) -> Optional[str]:
        """Return Signal username if available (e.g. username.01)."""
        uname = self.sourceUsername or self.username
        if uname:
            return uname.lstrip("@")
        return None

    @property
    def sender_uuid(self) -> Optional[str]:
        """Return sender UUID if available."""
        if self.sourceUuid:
            return self.sourceUuid
        if self.source and "-" in self.source and not self.source.startswith("+"):
            return self.source
        return None

    @property
    def signal_dm_link(self) -> Optional[str]:
        """Return clickable Signal direct message link (username link or phone link)."""
        if self.sender_username:
            return f"https://signal.me/#u/{self.sender_username}"
        if self.sender_phone:
            return f"https://signal.me/#p/{self.sender_phone}"
        return None

    @property
    def sender_name(self) -> str:
        """Return display name of sender."""
        return self.sourceName or self.sender_phone or self.sender_number

    @property
    def group_id(self) -> Optional[str]:
        """Return group ID if envelope belongs to a group message."""
        if self.dataMessage and self.dataMessage.groupInfo:
            return self.dataMessage.groupInfo.groupId
        return None

    @property
    def group_name(self) -> Optional[str]:
        """Return group name if envelope belongs to a group message."""
        if self.dataMessage and self.dataMessage.groupInfo:
            return self.dataMessage.groupInfo.name or self.dataMessage.groupInfo.groupId
        return None

    @property
    def text(self) -> Optional[str]:
        """Return message body text."""
        if self.dataMessage:
            return self.dataMessage.message
        return None

    @property
    def attachments(self) -> List[Attachment]:
        """Return list of attachments."""
        if self.dataMessage:
            return self.dataMessage.attachments
        return []

    @property
    def is_group_message(self) -> bool:
        """Return True if this is a group message."""
        return self.group_id is not None

    def has_image(self) -> bool:
        """Return True if message has at least one image attachment."""
        return any(att.is_image for att in self.attachments)

    def has_gif(self) -> bool:
        """Return True if message has at least one GIF attachment."""
        return any(att.is_gif for att in self.attachments)

    def has_video(self) -> bool:
        """Return True if message has at least one video attachment."""
        return any(att.is_video for att in self.attachments)

    def has_media(self, allow_videos: bool = True, allow_gifs: bool = True) -> bool:
        """Return True if message has eligible media attachments."""
        for att in self.attachments:
            if att.is_image:
                return True
            if allow_gifs and att.is_gif:
                return True
            if allow_videos and att.is_video:
                return True
        return False


class JsonRpcResponse(BaseModel):
    """Represents a generic JSON-RPC response or notification from signal-cli."""
    jsonrpc: str = "2.0"
    method: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[Any] = None
