"""메시징 어댑터. 문자와 알림톡을 한 계약으로 다룬다([ADR-005])."""

import os
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

import httpx

SMS_BYTE_LIMIT = 90  # 알리고 기준: 90바이트 이하 단문(SMS), 초과 장문(LMS)


@dataclass(frozen=True)
class Recipient:
    phone: str
    kind: str  # student | guardian


@dataclass(frozen=True)
class SendResult:
    recipient_phone: str
    recipient_type: str
    status: str  # test | sent | failed | fallback_sent
    result_code: str | None = None
    error: str | None = None
    cost_unit: int | None = None


@dataclass(frozen=True)
class Balance:
    mode: str
    sms: int | None
    lms: int | None
    mms: int | None
    checked_at: str


def choose_channel(body: str, has_attachment: bool = False) -> str:
    if has_attachment:
        return "mms"
    return "sms" if len(body.encode("euc-kr", errors="replace")) <= SMS_BYTE_LIMIT else "lms"


class MessagingAdapter(Protocol):
    async def send(
        self, channel: str, recipients: list[Recipient], body: str
    ) -> list[SendResult]: ...

    async def send_alimtalk(
        self, template_code: str, recipients: list[Recipient], body: str, fallback: bool
    ) -> list[SendResult]: ...

    async def balance(self) -> Balance: ...


class TestModeMessaging:
    """외부로 나가지 않는다. 기본 모드이며 발송 로그만 남긴다(FR-23)."""

    mode = "test"

    async def send(
        self, channel: str, recipients: list[Recipient], body: str
    ) -> list[SendResult]:
        return [
            SendResult(
                recipient_phone=recipient.phone,
                recipient_type=recipient.kind,
                status="test",
                result_code="TEST",
                cost_unit=0,
            )
            for recipient in recipients
        ]

    async def send_alimtalk(
        self, template_code: str, recipients: list[Recipient], body: str, fallback: bool
    ) -> list[SendResult]:
        return await self.send("alimtalk", recipients, body)

    async def balance(self) -> Balance:
        return Balance(
            mode=self.mode,
            sms=None,
            lms=None,
            mms=None,
            checked_at=datetime.now(UTC).isoformat(),
        )


class AligoMessaging:
    """알리고 문자 API. 실발송 모드에서만 쓰인다."""

    mode = "live"
    BASE_URL = "https://apis.aligo.in"
    KAKAO_URL = "https://kakaoapi.aligo.in"

    def __init__(self, api_key: str, user_id: str, sender: str, sender_key: str | None = None) -> None:
        self.api_key, self.user_id, self.sender = api_key, user_id, sender
        self.sender_key = sender_key  # 카카오 발신프로필 키. 없으면 알림톡만 실패한다

    def _credentials(self) -> dict[str, str]:
        return {"key": self.api_key, "user_id": self.user_id}

    async def send(
        self, channel: str, recipients: list[Recipient], body: str
    ) -> list[SendResult]:
        results: list[SendResult] = []
        async with httpx.AsyncClient(base_url=self.BASE_URL, timeout=20) as client:
            for recipient in recipients:
                data = self._credentials() | {
                    "sender": self.sender,
                    "receiver": recipient.phone,
                    "msg": body,
                    "msg_type": channel.upper(),
                }
                try:
                    response = await client.post("/send/", data=data)
                    payload = response.json()
                except (httpx.HTTPError, ValueError) as error:
                    results.append(
                        SendResult(
                            recipient_phone=recipient.phone,
                            recipient_type=recipient.kind,
                            status="failed",
                            error=str(error),
                        )
                    )
                    continue
                succeeded = str(payload.get("result_code")) == "1"
                results.append(
                    SendResult(
                        recipient_phone=recipient.phone,
                        recipient_type=recipient.kind,
                        status="sent" if succeeded else "failed",
                        result_code=str(payload.get("result_code")),
                        error=None if succeeded else payload.get("message"),
                        cost_unit=1 if succeeded else 0,
                    )
                )
        return results

    async def send_alimtalk(
        self, template_code: str, recipients: list[Recipient], body: str, fallback: bool
    ) -> list[SendResult]:
        """알리고 알림톡 API. `body`는 승인 템플릿에 변수만 채운 문구여야 한다(아니면 카카오가 거절한다).

        응답 `code == 0`은 **접수**다. 전달 단계의 실패(카카오톡 미사용자 등)는 나중에야 알 수 있어
        폴백이 켜져 있으면 알리고의 대체 발송(`failover`)도 켠다. 접수 자체가 거절되면 알리고는
        아무것도 보내지 않으므로, 그때의 문자 대체는 호출한 쪽이 한다(두 시도를 모두 로그에 남긴다).
        """
        if not self.sender_key:
            return [
                SendResult(r.phone, r.kind, "failed", error="카카오 발신프로필 키(ALIGO_SENDER_KEY)가 없습니다.")
                for r in recipients
            ]
        results: list[SendResult] = []
        async with httpx.AsyncClient(base_url=self.KAKAO_URL, timeout=20) as client:
            for recipient in recipients:
                data = {
                    "apikey": self.api_key,
                    "userid": self.user_id,
                    "senderkey": self.sender_key,
                    "tpl_code": template_code,
                    "sender": self.sender,
                    "receiver_1": recipient.phone,
                    "subject_1": "알림",
                    "message_1": body,
                    "failover": "Y" if fallback else "N",
                }
                if fallback:
                    data |= {"fsubject_1": "알림", "fmessage_1": body}
                try:
                    response = await client.post("/akv10/alimtalk/send/", data=data)
                    payload = response.json()
                except (httpx.HTTPError, ValueError) as error:
                    results.append(SendResult(recipient.phone, recipient.kind, "failed", error=str(error)))
                    continue
                accepted = str(payload.get("code")) == "0"
                results.append(
                    SendResult(
                        recipient_phone=recipient.phone,
                        recipient_type=recipient.kind,
                        status="sent" if accepted else "failed",
                        result_code=str(payload.get("code")),
                        error=None if accepted else payload.get("message"),
                        cost_unit=1 if accepted else 0,
                    )
                )
        return results

    async def balance(self) -> Balance:
        async with httpx.AsyncClient(base_url=self.BASE_URL, timeout=20) as client:
            response = await client.post("/remain/", data=self._credentials())
            payload = response.json()
        return Balance(
            mode=self.mode,
            sms=int(payload.get("SMS_CNT", 0)),
            lms=int(payload.get("LMS_CNT", 0)),
            mms=int(payload.get("MMS_CNT", 0)),
            checked_at=datetime.now(UTC).isoformat(),
        )


def build_adapter() -> MessagingAdapter:
    """기본은 테스트 모드다. 실발송은 자격 증명이 모두 있을 때만 선택된다."""
    if os.environ.get("MATHDESK_MESSAGING_MODE", "test").lower() != "live":
        return TestModeMessaging()
    key = os.environ.get("ALIGO_API_KEY", "")
    user_id = os.environ.get("ALIGO_USER_ID", "")
    sender = os.environ.get("ALIGO_SENDER", "")
    if not (key and user_id and sender):
        raise RuntimeError("실발송 모드에는 ALIGO_API_KEY·ALIGO_USER_ID·ALIGO_SENDER가 필요합니다.")
    return AligoMessaging(key, user_id, sender, os.environ.get("ALIGO_SENDER_KEY") or None)
