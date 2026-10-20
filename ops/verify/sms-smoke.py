"""TASK-96 — 클라이언트 알리고 계정의 연결 확인(FR-23, Q-02).

자격은 환경변수로만 받는다(저장소·메신저에 두지 않는다). 발송 서버 IP 가 알리고에 등록된 곳에서 돌린다.

    cd apps/api
    ALIGO_API_KEY=… ALIGO_USER_ID=… ALIGO_SENDER=01012345678 uv run python ../../ops/verify/sms-smoke.py balance
    ALIGO_API_KEY=… ALIGO_USER_ID=… ALIGO_SENDER=01012345678 uv run python ../../ops/verify/sms-smoke.py send 01012345678

balance: /remain/ 원본 응답(result_code·message·잔여 건수). 비용 없음. 키·아이디·IP 등록이 틀리면 여기서 드러난다.
send:    받는 번호 1개에 SMS 1건(건당 8.4원+VAT). 제품 코드의 AligoMessaging.send 를 그대로 탄다.
"""
import asyncio
import json
import os
import sys
from datetime import datetime

import httpx

from mathdesk.messaging_adapter import AligoMessaging, Recipient


def credentials() -> AligoMessaging:
    key, user_id, sender = (os.environ.get(k, "") for k in ("ALIGO_API_KEY", "ALIGO_USER_ID", "ALIGO_SENDER"))
    if not (key and user_id and sender):
        sys.exit("ALIGO_API_KEY·ALIGO_USER_ID·ALIGO_SENDER 환경변수가 필요합니다.")
    return AligoMessaging(key, user_id, sender)


async def balance(aligo: AligoMessaging) -> int:
    async with httpx.AsyncClient(base_url=aligo.BASE_URL, timeout=20) as client:
        response = await client.post("/remain/", data=aligo._credentials())
    payload = response.json()
    print(json.dumps(payload, ensure_ascii=False))
    ok = str(payload.get("result_code")) == "1"
    print("연결 OK" if ok else "연결 실패 — 키·아이디·발송 서버 IP 등록을 확인")
    return 0 if ok else 1


async def send(aligo: AligoMessaging, phone: str) -> int:
    body = f"[mathdesk] 문자 연결 확인 {datetime.now():%m-%d %H:%M}. 이 문자가 보이면 연결이 끝난 것입니다."
    results = await aligo.send("sms", [Recipient(phone=phone, kind="student")], body)
    for r in results:
        print(f"{r.recipient_phone} {r.status} code={r.result_code} error={r.error}")
    return 0 if all(r.status == "sent" for r in results) else 1


if __name__ == "__main__":
    aligo = credentials()
    if len(sys.argv) >= 2 and sys.argv[1] == "balance":
        sys.exit(asyncio.run(balance(aligo)))
    if len(sys.argv) == 3 and sys.argv[1] == "send":
        sys.exit(asyncio.run(send(aligo, sys.argv[2])))
    sys.exit(__doc__)
