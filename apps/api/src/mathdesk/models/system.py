from datetime import datetime

from decimal import Decimal

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, enum_column

# 기준선 v3 (ADR-009): LlmAdapter 구현체와 1:1 대응한다.
LLM_PROVIDER = ("test", "anthropic", "openai_compat")

TASK_STATUS = ("queued", "running", "done", "failed")


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


class StoredFile(Base):
    __tablename__ = "stored_file"

    id: Mapped[int] = mapped_column(primary_key=True)
    campus_id: Mapped[int] = mapped_column(ForeignKey("campus.id"), index=True)
    kind: Mapped[str] = mapped_column(String(50), index=True)
    path: Mapped[str] = mapped_column(String(500))
    content_type: Mapped[str | None] = mapped_column(String(200))
    size: Mapped[int | None] = mapped_column(BigInteger)
    sha256: Mapped[str | None] = mapped_column(String(64), index=True)


class LlmCallLog(Base):
    """문항 분석 LLM 호출 기록. 공급자가 가변이므로 실비용 재구성에 필요한
    공급자와 캐시 토큰을 함께 남긴다(NFR-15, ADR-009)."""

    __tablename__ = "llm_call_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    campus_id: Mapped[int] = mapped_column(ForeignKey("campus.id"), index=True)
    purpose: Mapped[str] = mapped_column(String(50), index=True)
    provider: Mapped[str] = mapped_column(enum_column("llm_provider", *LLM_PROVIDER))
    model: Mapped[str] = mapped_column(String(100))
    exam_id: Mapped[int | None] = mapped_column(ForeignKey("exam.id"), index=True)
    prompt_tokens: Mapped[int] = mapped_column(default=0)
    completion_tokens: Mapped[int] = mapped_column(default=0)
    cache_read_tokens: Mapped[int] = mapped_column(default=0)
    cache_write_tokens: Mapped[int] = mapped_column(default=0)
    cost: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class BackgroundTask(Base):
    """오래 걸리는 작업의 상태(DES-18).

    프로세스 안에서 실행하지만 상태는 DB에 둔다. 재시작하면 메모리의 큐는 사라지지만
    이 행은 남아 `queued`부터 다시 시작할 수 있다(RISK-09 완화책).
    """

    __tablename__ = "background_task"

    id: Mapped[int] = mapped_column(primary_key=True)
    campus_id: Mapped[int] = mapped_column(ForeignKey("campus.id"), index=True)
    kind: Mapped[str] = mapped_column(String(50), index=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(
        enum_column("task_status", *TASK_STATUS), default="queued", index=True
    )
    progress: Mapped[int] = mapped_column(default=0)
    result: Mapped[dict | None] = mapped_column(JSON)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
