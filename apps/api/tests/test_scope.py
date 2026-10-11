import asyncio

from fastapi.routing import APIRoute
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from mathdesk.main import app
from mathdesk.models import AppUser, Student
from mathdesk.scope import Scope, ScopedRepository, current_portal_scope, current_scope

UNSCOPED_PATHS = {
    "/api/health",
    "/api/auth/login",
    "/api/auth/logout",
    "/api/auth/me",
    "/api/auth/password",
}
PORTAL_PREFIX = "/api/portal"


def _depends_on(dependant, target) -> bool:
    return any(
        child.call is target or _depends_on(child, target)
        for child in dependant.dependencies
    )


def _api_routes():
    return [
        route
        for route in app.routes
        if isinstance(route, APIRoute) and route.path.startswith("/api") and route.path not in UNSCOPED_PATHS
    ]


def test_every_api_route_enforces_campus_scope():
    unguarded = [
        route.path
        for route in _api_routes()
        if not route.path.startswith(PORTAL_PREFIX) and not _depends_on(route.dependant, current_scope)
    ]

    assert unguarded == []


def test_every_portal_route_uses_the_portal_scope_only():
    """포털 역할은 기본 거부(ADR-014): 포털 경로는 포털 의존성만, 나머지는 기존 의존성만 쓴다."""
    wrong = [
        route.path
        for route in _api_routes()
        if route.path.startswith(PORTAL_PREFIX)
        and (not _depends_on(route.dependant, current_portal_scope) or _depends_on(route.dependant, current_scope))
    ]
    leaked = [
        route.path
        for route in _api_routes()
        if not route.path.startswith(PORTAL_PREFIX) and _depends_on(route.dependant, current_portal_scope)
    ]

    assert wrong == [] and leaked == []


def test_portal_and_staff_roles_are_rejected_across_the_boundary(api, klass):
    """NFR-07 양방향: 포털 계정은 포털 외 GET 전부 403, 원장은 포털 API 403(AC-51 ④)."""
    student = klass["student_ids"][0]
    api.patch(f"/api/students/{student}", json={"name": "김나윤", "phone": "010-5555-0000"})
    api.post(f"/api/students/{student}/portal-accounts", json={"kind": "student"})
    assert api.get("/api/portal/students").status_code == 403

    api.cookies.clear()
    assert api.post("/api/auth/login", json={"login_id": "01055550000", "password": "01055550000"}).status_code == 200
    api.post("/api/auth/password", json={"current_password": "01055550000", "new_password": "student-pw-1"})
    assert api.get("/api/portal/students").status_code == 200
    rejected = {}
    for route in _api_routes():
        if route.path.startswith(PORTAL_PREFIX) or "GET" not in route.methods:
            continue
        path = route.path.replace("{", "").replace("}", "")
        import re

        path = re.sub(r"/[a-z_]+_id(/|$)", r"/1\1", path).replace("/api/", "/api/")
        rejected[route.path] = api.get(path).status_code
    assert {p for p, code in rejected.items() if code != 403} == set()


def test_campus_list_only_returns_accessible_campuses(api):
    api.sign_in("director_a")

    response = api.get("/api/campuses")

    assert response.status_code == 200
    assert [campus["id"] for campus in response.json()] == [api.ids["campus_a"]]


def test_request_for_another_campus_is_forbidden(api):
    api.sign_in("director_a")

    response = api.get("/api/users", headers={"X-Campus-Id": str(api.ids["campus_b"])})

    assert response.status_code == 403
    assert "중등관" not in response.text


def test_teacher_cannot_manage_users(api):
    api.sign_in("teacher_a")

    assert api.get("/api/users").status_code == 403
    assert (
        api.post(
            "/api/users",
            json={
                "login_id": "new_teacher",
                "display_name": "새 강사",
                "role": "teacher",
                "password": "another-secret-pw",
            },
        ).status_code
        == 403
    )


def test_director_manages_users_within_own_campus(api):
    api.sign_in("director_a")

    created = api.post(
        "/api/users",
        json={
            "login_id": "new_teacher",
            "display_name": "새 강사",
            "role": "teacher",
            "password": "another-secret-pw",
        },
    )
    assert created.status_code == 201

    listed = api.get("/api/users")
    assert {user["login_id"] for user in listed.json()} == {
        "director_a",
        "teacher_a",
        "new_teacher",
    }


def test_scoped_repository_filters_by_campus(world, migrated_database):
    async def run() -> list[str]:
        engine = create_async_engine(migrated_database)
        async with async_sessionmaker(engine, expire_on_commit=False)() as session:
            session.add_all(
                [
                    Student(campus_id=world["campus_a"], name="A반 학생"),
                    Student(campus_id=world["campus_b"], name="B반 학생"),
                ]
            )
            await session.commit()

            user = await session.get(AppUser, world["director_a"])
            repository = ScopedRepository(
                session, Scope(user=user, campus_id=world["campus_a"])
            )
            students = await session.scalars(repository.select(Student))
            names = [student.name for student in students]
        await engine.dispose()
        return names

    assert asyncio.run(run()) == ["A반 학생"]
