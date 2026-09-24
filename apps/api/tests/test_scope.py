import asyncio

from fastapi.routing import APIRoute
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from mathdesk.main import app
from mathdesk.models import AppUser, Student
from mathdesk.scope import Scope, ScopedRepository, current_scope

UNSCOPED_PATHS = {
    "/api/health",
    "/api/auth/login",
    "/api/auth/logout",
    "/api/auth/me",
    "/api/auth/password",
}


def _depends_on(dependant, target) -> bool:
    return any(
        child.call is target or _depends_on(child, target)
        for child in dependant.dependencies
    )


def test_every_api_route_enforces_campus_scope():
    unguarded = [
        route.path
        for route in app.routes
        if isinstance(route, APIRoute)
        and route.path.startswith("/api")
        and route.path not in UNSCOPED_PATHS
        and not _depends_on(route.dependant, current_scope)
    ]

    assert unguarded == []


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
