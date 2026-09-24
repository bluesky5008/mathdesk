import re
from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .daily import _session_for_write, _enrolled_students
from .db import get_session
from .messaging_adapter import Recipient, SendResult, build_adapter, choose_channel
from .models import (
    AppUser,
    Campus,
    Guardian,
    MessageLog,
    ClassSession,
    ClassSessionProgress,
    GradeComment,
    IntegrationSetting,
    Klass,
    MessageTemplate,
    Student,
    StudentDailyRecord,
)
from .models.daily import HOMEWORK_GRADE
from .scope import CurrentScope

Db = Annotated[AsyncSession, Depends(get_session)]

router = APIRouter(prefix="/api/messages", tags=["messages"])

WEEKDAYS = ("월", "화", "수", "목", "금", "토", "일")
ATTENDANCE_LABEL = {
    "present": "출석",
    "late": "지각",
    "absent": "결석",
    "early_leave": "조퇴",
}


class MessageContext(BaseModel):
    """본문 렌더에 필요한 값만 담는다. 저장하지 않고 요청마다 만든다(FR-18)."""

    student_name: str
    campus_name: str
    teacher_name: str
    session_date: date
    attendance: str | None = None
    progress: list[tuple[int, str | None]] = Field(default_factory=list)
    homework_grade: str | None = None
    grade_comment: str | None = None
    test_name: str | None = None
    test_score: str | None = None
    class_average: float | None = None
    homework: str | None = None
    video_url: str | None = None


def render_daily_message(context: MessageContext) -> str:
    day = context.session_date
    blocks: list[str] = [
        f"**{context.student_name}학생 학습피드백**\n"
        f"{context.campus_name} {context.teacher_name}T입니다.\n"
        f"{day.month}월 {day.day}일({WEEKDAYS[day.weekday()]}) 수업 내용 및 과제피드백 안내드립니다."
    ]

    attendance = ATTENDANCE_LABEL.get(context.attendance or "")
    if attendance:
        blocks.append(f"■ 출결: {attendance}")

    lines = [f"[{period}교시] {content}" for period, content in context.progress if content]
    if lines:
        blocks.append("■ 수업진도\n" + "\n".join(lines))

    if context.homework_grade:
        feedback = f"■ 과제피드백: {context.homework_grade}"
        if context.grade_comment:
            feedback += f"\n{context.grade_comment}"
        blocks.append(feedback)

    if context.test_name and context.test_score is not None:
        test = f"■ 테스트: {context.test_name}\n   학생점수: {context.test_score}점"
        if context.class_average is not None:
            test += f"\n   반평균: {context.class_average}점"
        blocks.append(test)

    if context.homework:
        blocks.append(f"■ 오늘의 과제\n{context.homework}")

    if context.video_url:
        blocks.append(f"■ 수업 영상 링크\n{context.video_url}")

    return "\n\n".join(blocks)


# ── 알림톡 템플릿(FR-37) ─────────────────────────────────────────────

# 템플릿 변수(`#{이름}`)에 넣을 수 있는 값. 일일 피드백 문구와 같은 값을 같은 모양으로 쓴다
ALIMTALK_FIELDS: dict[str, tuple[str, object]] = {
    "student_name": ("학생 이름", lambda c: c.student_name),
    "campus_name": ("학원명", lambda c: c.campus_name),
    "teacher_name": ("담당 강사", lambda c: c.teacher_name),
    "session_date": ("수업일", lambda c: f"{c.session_date.month}월 {c.session_date.day}일"),
    "attendance": ("출결", lambda c: ATTENDANCE_LABEL.get(c.attendance or "", "")),
    "progress": ("수업 진도", lambda c: "\n".join(f"[{p}교시] {t}" for p, t in c.progress if t)),
    "homework_grade": ("과제 등급", lambda c: c.homework_grade),
    "grade_comment": ("등급 문구", lambda c: c.grade_comment),
    "test_name": ("테스트명", lambda c: c.test_name),
    "test_score": ("학생 점수", lambda c: c.test_score),
    "class_average": ("반 평균", lambda c: c.class_average),
    "homework": ("오늘의 과제", lambda c: c.homework),
    "video_url": ("수업 영상 링크", lambda c: c.video_url),
    "daily_message": ("일일 피드백 전체", render_daily_message),
}
VARIABLE = re.compile(r"#\{([^}]+)\}")
FALLBACK_KEY = "alimtalk_fallback"


def render_alimtalk(body: str, variables: dict[str, str], context: MessageContext) -> str:
    """승인 템플릿의 `#{변수}`만 채운다. 나머지 글자를 바꾸면 카카오가 템플릿 불일치로 거절한다."""

    def value(match: re.Match) -> str:
        filled = ALIMTALK_FIELDS[variables[match.group(1)]][1](context)
        return "" if filled is None else str(filled)

    return VARIABLE.sub(value, body)


class AlimtalkTemplateIn(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    body: str = Field(min_length=1, max_length=1000)
    variables: dict[str, str] = Field(default_factory=dict)

    @field_validator("variables")
    @classmethod
    def known_fields(cls, variables: dict[str, str]) -> dict[str, str]:
        unknown = sorted(set(variables.values()) - set(ALIMTALK_FIELDS))
        if unknown:
            raise ValueError(f"알 수 없는 값입니다: {', '.join(unknown)}")
        return variables

    def model_post_init(self, _context) -> None:
        missing = sorted(set(VARIABLE.findall(self.body)) - set(self.variables))
        if missing:
            raise ValueError(f"값을 지정하지 않은 변수가 있습니다: {', '.join(missing)}")


class TemplatesIn(BaseModel):
    fallback_to_sms: bool = True
    alimtalk: list[AlimtalkTemplateIn] = Field(default_factory=list)

    @field_validator("alimtalk")
    @classmethod
    def unique_codes(cls, templates: list[AlimtalkTemplateIn]) -> list[AlimtalkTemplateIn]:
        codes = [template.code for template in templates]
        if len(codes) != len(set(codes)):
            raise ValueError("템플릿 코드가 겹칩니다.")
        return templates


class FieldOut(BaseModel):
    key: str
    label: str


class TemplatesOut(BaseModel):
    fallback_to_sms: bool
    alimtalk: list[AlimtalkTemplateIn]
    fields: list[FieldOut]


class GradeCommentIn(BaseModel):
    grade: str = Field(pattern="^(%s)$" % "|".join(g.replace("+", r"\+") for g in HOMEWORK_GRADE))
    comment_text: str


class GradeCommentsIn(BaseModel):
    comments: list[GradeCommentIn]


class PreviewOut(BaseModel):
    body: str


class SendIn(BaseModel):
    session_id: int
    student_id: int
    recipients: list[str] = Field(min_length=1)
    template_code: str | None = None  # 주면 알림톡으로, 없으면 문자로 보낸다


class SendResultOut(BaseModel):
    channel: str
    recipient_phone: str
    recipient_type: str
    status: str
    result_code: str | None = None
    error: str | None = None


class SendOut(BaseModel):
    channel: str
    results: list[SendResultOut]


class MessageLogOut(BaseModel):
    id: int
    student_id: int | None
    recipient_type: str
    recipient_phone: str
    channel: str
    status: str
    body_snapshot: str
    is_test: bool
    requested_at: str
    result_code: str | None
    error: str | None


def _format_score(value: Decimal | None, text: str | None) -> str | None:
    if value is not None:
        return str(int(value)) if value == value.to_integral_value() else str(value)
    return text


@router.get("/grade-comments")
async def list_grade_comments(scope: CurrentScope, session: Db) -> list[GradeCommentIn]:
    rows = await session.scalars(
        select(GradeComment).where(GradeComment.campus_id == scope.campus_id)
    )
    return [GradeCommentIn(grade=row.grade, comment_text=row.comment_text) for row in rows]


@router.put("/grade-comments")
async def save_grade_comments(
    payload: GradeCommentsIn, scope: CurrentScope, session: Db
) -> list[GradeCommentIn]:
    scope.require_director()
    existing = {
        row.grade: row
        for row in await session.scalars(
            select(GradeComment).where(GradeComment.campus_id == scope.campus_id)
        )
    }
    for item in payload.comments:
        if item.grade in existing:
            existing[item.grade].comment_text = item.comment_text
        else:
            session.add(
                GradeComment(
                    campus_id=scope.campus_id,
                    grade=item.grade,
                    comment_text=item.comment_text,
                )
            )
    await session.commit()
    return await list_grade_comments(scope, session)


async def _context(
    session_id: int, student_id: int, scope, session: AsyncSession
) -> MessageContext:
    row = await _session_for_write(session, scope, session_id)
    klass = await session.get(Klass, row.class_id)

    enrolled = await _enrolled_students(session, klass.id, row.session_date)
    student = next((s for s in enrolled if s.id == student_id), None)
    if student is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "접근 권한이 없습니다.")

    records = {
        record.student_id: record
        for record in await session.scalars(
            select(StudentDailyRecord).where(StudentDailyRecord.session_id == row.id)
        )
    }
    record = records.get(student_id)

    progress = await session.scalars(
        select(ClassSessionProgress)
        .where(ClassSessionProgress.session_id == row.id)
        .order_by(ClassSessionProgress.period)
    )
    campus = await session.get(Campus, scope.campus_id)
    teacher = await session.get(AppUser, klass.teacher_id) if klass.teacher_id else None
    comments = {
        item.grade: item.comment_text
        for item in await session.scalars(
            select(GradeComment).where(GradeComment.campus_id == scope.campus_id)
        )
    }

    scores = [
        float(other.test_score_num)
        for other in records.values()
        if other.test_score_num is not None
    ]

    context = MessageContext(
        student_name=student.name,
        campus_name=campus.name,
        teacher_name=teacher.display_name if teacher else "담당",
        session_date=row.session_date,
        attendance=record.attendance_status if record else None,
        progress=[(item.period, item.content) for item in progress],
        homework_grade=record.homework_grade if record else None,
        grade_comment=comments.get(record.homework_grade) if record else None,
        test_name=row.test_name,
        test_score=_format_score(
            record.test_score_num if record else None,
            record.test_score_text if record else None,
        ),
        class_average=round(sum(scores) / len(scores), 1) if scores else None,
        homework=row.homework,
        video_url=row.video_url,
    )
    return context


async def _fallback_on(session: AsyncSession, campus_id: int) -> bool:
    row = await session.get(IntegrationSetting, (campus_id, FALLBACK_KEY))
    return row is None or row.value_encrypted == "sms"  # 기본은 대체 발송(ADR-005 결정 4)


@router.get("/templates")
async def list_templates(scope: CurrentScope, session: Db) -> TemplatesOut:
    rows = await session.scalars(
        select(MessageTemplate)
        .where(MessageTemplate.campus_id == scope.campus_id, MessageTemplate.kind == "alimtalk")
        .order_by(MessageTemplate.id)
    )
    return TemplatesOut(
        fallback_to_sms=await _fallback_on(session, scope.campus_id),
        alimtalk=[AlimtalkTemplateIn(code=r.code, body=r.body, variables=r.variables or {}) for r in rows],
        fields=[FieldOut(key=key, label=label) for key, (label, _) in ALIMTALK_FIELDS.items()],
    )


@router.put("/templates")
async def save_templates(payload: TemplatesIn, scope: CurrentScope, session: Db) -> TemplatesOut:
    """알림톡 템플릿 목록을 통째로 바꾼다. 템플릿은 발송 로그가 참조하지 않는다(로그는 본문 스냅샷)."""
    scope.require_director()
    for row in await session.scalars(
        select(MessageTemplate).where(
            MessageTemplate.campus_id == scope.campus_id, MessageTemplate.kind == "alimtalk"
        )
    ):
        await session.delete(row)
    for template in payload.alimtalk:
        session.add(MessageTemplate(
            campus_id=scope.campus_id, kind="alimtalk", code=template.code,
            body=template.body, variables=template.variables,
        ))
    setting = await session.get(IntegrationSetting, (scope.campus_id, FALLBACK_KEY))
    value = "sms" if payload.fallback_to_sms else "off"
    if setting is None:
        session.add(IntegrationSetting(campus_id=scope.campus_id, key=FALLBACK_KEY, value_encrypted=value))
    else:
        setting.value_encrypted = value
    await session.commit()
    return await list_templates(scope, session)


async def _alimtalk_template(session: AsyncSession, campus_id: int, code: str) -> MessageTemplate:
    template = await session.scalar(
        select(MessageTemplate).where(
            MessageTemplate.campus_id == campus_id,
            MessageTemplate.kind == "alimtalk",
            MessageTemplate.code == code,
        )
    )
    if template is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "등록되지 않은 알림톡 템플릿입니다.")
    return template


@router.get("/preview")
async def preview(
    session_id: int, student_id: int, scope: CurrentScope, session: Db,
    template_code: str | None = None,
) -> PreviewOut:
    """템플릿을 주면 알림톡으로 나갈 문구를, 아니면 일일 피드백 문자를 보여준다."""
    context = await _context(session_id, student_id, scope, session)
    if template_code:
        template = await _alimtalk_template(session, scope.campus_id, template_code)
        return PreviewOut(body=render_alimtalk(template.body, template.variables or {}, context))
    return PreviewOut(body=render_daily_message(context))


@router.get("/report-image")
async def report_image(
    request: Request, session_id: int, student_id: int, scope: CurrentScope, session: Db
) -> Response:
    from .branding import load_brand

    context = await _context(session_id, student_id, scope, session)
    colour, logo = await load_brand(session, scope.campus_id)
    renderer = request.app.state.report_renderer
    return Response(
        await renderer.render_png(context, brand_colour=colour, logo_data_url=logo),
        media_type="image/png",
    )


async def _recipients_for(
    session: AsyncSession, student: Student, kinds: list[str]
) -> list[Recipient]:
    recipients: list[Recipient] = []
    if "student" in kinds and student.phone:
        recipients.append(Recipient(phone=student.phone, kind="student"))
    if "guardian" in kinds:
        guardians = await session.scalars(
            select(Guardian).where(
                Guardian.student_id == student.id, Guardian.is_notify_target
            )
        )
        recipients.extend(
            Recipient(phone=guardian.phone, kind="guardian")
            for guardian in guardians
            if guardian.phone
        )
    return recipients


@router.post("/send")
async def send_message(payload: SendIn, scope: CurrentScope, session: Db) -> SendOut:
    context = await _context(payload.session_id, payload.student_id, scope, session)
    student = await session.get(Student, payload.student_id)
    recipients = await _recipients_for(session, student, payload.recipients)
    if not recipients:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "보낼 수 있는 연락처가 없습니다."
        )

    adapter = build_adapter()
    attempts: list[tuple[str, SendResult]] = []
    if payload.template_code:
        template = await _alimtalk_template(session, scope.campus_id, payload.template_code)
        channel = "alimtalk"
        body = render_alimtalk(template.body, template.variables or {}, context)
        fallback = await _fallback_on(session, scope.campus_id)
        attempts += [("alimtalk", r) for r in await adapter.send_alimtalk(template.code, recipients, body, fallback)]
        failed = [Recipient(r.recipient_phone, r.recipient_type) for _, r in attempts if r.status == "failed"]
        if fallback and failed:
            # 알림톡 접수가 거절된 수신자만 같은 문구를 문자로 다시 보낸다(ADR-005 결정 4, AC-26)
            sms = choose_channel(body)
            for result in await adapter.send(sms, failed, body):
                if result.status == "sent":
                    result = SendResult(**{**vars(result), "status": "fallback_sent"})
                attempts.append((sms, result))
    else:
        body = render_daily_message(context)
        channel = choose_channel(body)
        attempts += [(channel, r) for r in await adapter.send(channel, recipients, body)]

    for used, result in attempts:
        session.add(
            MessageLog(
                campus_id=scope.campus_id,
                student_id=payload.student_id,
                recipient_type=result.recipient_type,
                recipient_phone=result.recipient_phone,
                channel=used,
                status=result.status,
                body_snapshot=body,
                cost_unit=result.cost_unit,
                is_test=result.status == "test",
                result_code=result.result_code,
                error=result.error,
            )
        )
    await session.commit()

    return SendOut(
        channel=channel,
        results=[
            SendResultOut(
                channel=used,
                recipient_phone=result.recipient_phone,
                recipient_type=result.recipient_type,
                status=result.status,
                result_code=result.result_code,
                error=result.error,
            )
            for used, result in attempts
        ],
    )


@router.get("/logs")
async def list_logs(scope: CurrentScope, session: Db, limit: int = 50) -> list[MessageLogOut]:
    rows = await session.scalars(
        select(MessageLog)
        .where(MessageLog.campus_id == scope.campus_id)
        .order_by(MessageLog.id.desc())
        .limit(limit)
    )
    return [
        MessageLogOut(
            id=row.id,
            student_id=row.student_id,
            recipient_type=row.recipient_type,
            recipient_phone=row.recipient_phone,
            channel=row.channel,
            status=row.status,
            body_snapshot=row.body_snapshot,
            is_test=row.is_test,
            requested_at=row.requested_at.isoformat(),
            result_code=row.result_code,
            error=row.error,
        )
        for row in rows
    ]


@router.get("/balance")
async def balance(scope: CurrentScope) -> dict:
    return vars(await build_adapter().balance())
