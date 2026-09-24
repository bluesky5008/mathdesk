"""VER-35 — 좁은 화면에서 조회·발송 화면에 페이지 본문 가로 넘침이 없는지 실측한다(AC-35).

jsdom은 레이아웃을 계산하지 않아 vitest로는 잴 수 없다. 실제 브라우저로 잰다.
API는 가로채서 고정 응답을 주므로 백엔드도 자격 증명도 필요 없다.

실행:
    cd apps/web && npm run build
    cd ../api && uv run python ../../ops/verify/responsive.py

CI에 넣지 않았다. 웹 빌드 산출물과 Chromium이 함께 필요해 단위 테스트 체계와 결합도가 높다.
웹 레이아웃을 바꾼 뒤에는 이 스크립트를 돌려 AC-35를 확인한다.

폭은 VER35_WIDTHS로 바꾼다(기본 390,768,1280). 390px는 NFR-14의 최소 지원 폭이다.
"""
import asyncio, json, os, subprocess, sys, time
from pathlib import Path
from playwright.async_api import async_playwright

DIST = Path(os.environ.get("VER35_DIST", Path(__file__).resolve().parents[2] / "apps/web/dist")).resolve()
PORT = 8799
WIDTHS = [int(w) for w in os.environ.get("VER35_WIDTHS", "390,768,1280").split(",")]

BROWSE = [("종합 대시보드", "/"), ("알림문자", "/messages"),
          ("학생/반 관리", "/students"), ("성적 통계", "/stats"),
          ("시험지 분석", "/exams"), ("학원 설정", "/settings")]
DESKTOP_ONLY = [("일일 입력", "/daily")]

USER = {"id": 1, "login_id": "director", "display_name": "원장", "role": "director"}
CLASSES = [{"id": i, "name": n, "grade": "고2", "teacher_id": 1, "is_active": True,
            "schedules": [{"weekday": 4, "start_time": "18:00:00", "end_time": "22:00:00"}]}
           for i, n in enumerate(["고3 윤A", "고2 윤B", "고2 윤C", "고1 윤D"], 1)]
STUDENTS = [{"id": i, "name": f"학생{i:02d}", "school": "한영고등학교", "grade": "고2",
             "phone": None, "status": "enrolled", "omr_number": f"1000{i:02d}00"}
            for i in range(1, 48)]
RECORDS = [{"student_id": i, "name": f"학생{i:02d}", "attendance_status": "present",
            "attendance_reason": None, "homework_grade": "B",
            "recheck": {"target": False, "prev_grade": None, "prev_date": None, "result": None},
            "test_score_num": 70 + i, "test_score_text": None} for i in range(1, 14)]
DAILY = {"session": {"id": 9, "class_id": 1, "session_date": "2026-09-23",
                     "progress": [{"period": 1, "content": "2024 광문고 기출 시행"}],
                     "homework": "기출 풀어오기", "video_url": None, "teacher_note": None,
                     "test_name": "4차연합고사", "test_max_score": 100,
                     "attendance_confirmed_at": None},
         "records": RECORDS,
         "summary": {"enrolled": 13, "attending": 13, "test_average": 77.5, "test_count": 13}}
DASHBOARD = {"campus": {"enrolled_students": 47, "active_classes": 4},
             "attendance": {"attending": 13, "enrolled": 13},
             "homework": {"completion_rate": 93.8, "delta_points": 2.4, "missing": 0,
                          "recheck_targets": 1},
             "test": {"average": 82.6, "count": 84, "max": 100, "max_count": 4, "min": 58},
             "last_session": {"session_date": "2026-09-22",
                              "progress": [{"period": 1, "content": "2024 광문고 기출 시행"}],
                              "homework": "기출 풀어오기"}}
STAT_ROWS = [{"student_id": i, "name": f"학생{i:02d}", "test_average": 70.0 + i,
              "homework_completion": 90.0, "attendance_rate": 100.0} for i in range(1, 14)]
CLASS_STATS = {"klass": {"id": 1, "name": "고2 윤B"},
               "period": {"start": "2026-07-27", "end": "2026-09-23", "students": STAT_ROWS,
                          "test": {"average": 77.0, "count": 39,
                                   "distribution": [{"bucket": f"{b}~{100 if b == 90 else b + 9}", "count": c}
                                                    for b, c in [(50, 2), (60, 5), (70, 12),
                                                                 (80, 14), (90, 6)]]},
                          "homework": {"completion_rate": 90.0,
                                       "distribution": {"A": 12, "B": 20, "C": 7}},
                          "attendance_rate": 96.2},
               "compare": None}
HISTORY = {"student": {"id": 1, "name": "학생01"}, "klass": {"id": 1, "name": "고2 윤B"},
           "weeks": [{"week_start": f"2026-0{7 + i // 4}-{1 + (i % 4) * 7:02d}",
                      "test_average": 70.0 + i * 3, "class_test_average": 75.0 + i,
                      "homework_grades": ["B"], "homework_completion": 100.0,
                      "class_homework_completion": 90.0, "attendance_rate": 100.0}
                     for i in range(8)]}
EXAMS = [{"id": i, "name": f"강K {i}회 확통", "source_file_id": i, "class_id": None,
          "exam_date": "2026-09-19", "question_count": 30, "status": "draft", "needs_review": 2}
         for i in range(1, 6)]
EXAM = {**EXAMS[0], "max_score": 100, "answer_key_odd": None, "answer_key_even": None,
        "difficulty": {"low": 13, "mid": 9, "high": 6, "top": 2}}
QUESTIONS = [{"no": n, "unit": "함수의 극한과 연속", "sub_type": f"공통 객관식 {n}번 — 사차함수의 음의 실근 개수",
              "difficulty": "mid", "rationale": "극점에서의 함숫값을 구하고 부호 변화를 조사한다",
              "points": 4, "confidence": 0.9, "needs_review": n % 7 == 0} for n in range(1, 31)]
OMR_SCANS = [{"id": i, "file_id": 1, "page_no": i, "status": "needs_review" if i % 4 == 0 else "read",
              "student": {"id": i, "name": f"학생{i:02d}"}, "exam_number": f"1000{i:02d}00", "form": "odd",
              "answers": {str(q): 1 for q in range(1, 31)},
              "flags": [{"field": "3", "code": "multi"}, {"field": "22", "code": "blank"}] if i % 4 == 0 else [],
              "error": None} for i in range(1, 13)]
RESULTS = {"score_basis": "points",
           "summary": {"attempts": 8, "enrolled": 8, "average": 63.6, "highest": 80, "lowest": 52,
                       "average_correct_rate": 68.3, "focus_questions": [9, 14, 15, 21, 22, 28, 29, 30, 13]},
           "students": [{"student": {"id": i, "name": f"학생{i:02d}"}, "form": "odd", "source": "omr",
                         "score": 50 + i * 3, "correct": 15 + i, "answers": []} for i in range(1, 9)]}
QSTATS = {"questions": [{"no": n, "answer": n % 5 + 1, "answer_even": (n + 2) % 5 + 1,
                         "correct_rate": 30.0 + n * 2, "choices": {"1": 2, "2": 1, "3": 3, "4": 1, "5": 1},
                         "unit": "함수의 극한과 연속", "sub_type": None, "difficulty": "mid"} for n in range(1, 31)],
          "units": [{"unit": "함수의 극한과 연속", "questions": 12, "wrong_rate": 38.5},
                    {"unit": "수열", "questions": 10, "wrong_rate": 25.0}]}
CONSULTS = [{"id": i, "student_id": 1, "consulted_on": f"2026-09-{20 - i:02d}",
             "content": "모의고사 결과 상담. 수열 단원 오답이 많아 개념 복습 계획을 함께 세웠다.",
             "follow_up": "다음 주 오답 노트 확인" if i % 2 else None, "author": {"id": 1, "name": "원장"}}
            for i in range(1, 4)]
ALIMTALK = {"fallback_to_sms": True,
            "alimtalk": [{"code": "TPL_DAILY_01",
                          "body": "#{학생명} 학생 #{수업일} 수업 안내\n출결: #{출결}\n오늘의 과제: #{과제}",
                          "variables": {"학생명": "student_name", "수업일": "session_date",
                                        "출결": "attendance", "과제": "homework"}}],
            "fields": [{"key": "student_name", "label": "학생 이름"}, {"key": "session_date", "label": "수업일"},
                       {"key": "attendance", "label": "출결"}, {"key": "homework", "label": "오늘의 과제"}]}
LOGS = [{"id": i, "requested_at": "2026-09-23T18:30:00", "recipient_phone": "010-1234-5678",
         "channel": "sms", "status": "sent", "is_test": True} for i in range(1, 6)]
BRAND = {"campus_name": "전병훈 수학학원 고등관", "brand_colour": "#C3457F", "logo_data_url": None}


def body_for(path: str):
    if "/auth/me" in path: return USER
    if "/omr/scans" in path: return OMR_SCANS
    if path.endswith("/results"): return RESULTS
    if "/question-stats" in path: return QSTATS
    if "/questions" in path: return QUESTIONS
    if "/api/exams/" in path: return EXAM
    if path.endswith("/api/exams"): return EXAMS
    if "/stats/export" in path: return {}
    if "/stats/students" in path: return HISTORY
    if "/stats/classes" in path: return CLASS_STATS
    if "/consults" in path: return CONSULTS
    if "/classes" in path: return CLASSES
    if "/students" in path: return STUDENTS
    if "/dashboard" in path: return DASHBOARD
    if "/daily" in path: return DAILY
    if "/messages/preview" in path: return {"body": "김나윤학생 학습피드백\n\n■ 출결: 출석"}
    if "/messages/logs" in path: return LOGS
    if "/messages/templates" in path: return ALIMTALK
    if "/settings/brand" in path: return BRAND
    return {}


async def main() -> int:
    server = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "-d", str(DIST)],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.0)
    failures = []
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(args=["--no-sandbox"])
            for width in WIDTHS:
                page = await browser.new_page(viewport={"width": width, "height": 844})
                await page.route("**/api/**", lambda route: asyncio.ensure_future(
                    route.fulfill(status=200, content_type="application/json",
                                  body=json.dumps(body_for(route.request.url)))))
                print(f"\n{width}px\n{'화면':<20}{'본문폭':>8}{'뷰포트':>8}   판정")
                for name, path in BROWSE + DESKTOP_ONLY:
                    # SPA이므로 루트로 들어가 해시 없는 경로를 직접 연다
                    await page.goto(f"http://localhost:{PORT}/index.html", wait_until="load")
                    await page.evaluate(f"history.pushState({{}}, '', '{path}')")
                    await page.evaluate("window.dispatchEvent(new PopStateEvent('popstate'))")
                    await page.wait_for_timeout(700)
                    scroll, client = await page.evaluate(
                        "[document.documentElement.scrollWidth, document.documentElement.clientWidth]")
                    over = scroll - client
                    target = any(name == n for n, _ in BROWSE)
                    mark = "통과" if over <= 0 else f"넘침 {over}px"
                    if not target:
                        mark += " (데스크톱 전제)"
                    elif over > 0:
                        failures.append(f"{width}px {name} {over}px")
                    print(f"{name:<18}{scroll:>8}{client:>8}   {mark}")
                await page.close()
            await browser.close()
    finally:
        server.terminate()
    print("\nVER-35:", "통과" if not failures else "실패 — " + ", ".join(failures))
    return 0 if not failures else 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
