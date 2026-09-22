from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class IntegrationSetting(Base):
    __tablename__ = "integration_setting"

    campus_id: Mapped[int] = mapped_column(ForeignKey("campus.id"), primary_key=True)
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value_encrypted: Mapped[str] = mapped_column(Text)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    campus_id: Mapped[int | None] = mapped_column(ForeignKey("campus.id"), index=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("app_user.id"))
    action: Mapped[str] = mapped_column(String(100))
    target: Mapped[str | None] = mapped_column(String(200))
    detail: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
