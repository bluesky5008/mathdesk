from datetime import date, time

from sqlalchemy import Boolean, Date, ForeignKey, String, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, enum_column


class Campus(Base):
    __tablename__ = "campus"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class AppUser(Base):
    __tablename__ = "app_user"

    id: Mapped[int] = mapped_column(primary_key=True)
    login_id: Mapped[str] = mapped_column(String(50), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(50))
    role: Mapped[str] = mapped_column(enum_column("user_role", "director", "teacher"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class AppUserCampus(Base):
    __tablename__ = "app_user_campus"

    user_id: Mapped[int] = mapped_column(ForeignKey("app_user.id"), primary_key=True)
    campus_id: Mapped[int] = mapped_column(ForeignKey("campus.id"), primary_key=True)


class Student(Base):
    __tablename__ = "student"
    __table_args__ = (UniqueConstraint("campus_id", "omr_number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    campus_id: Mapped[int] = mapped_column(ForeignKey("campus.id"), index=True)
    name: Mapped[str] = mapped_column(String(50))
    school: Mapped[str | None] = mapped_column(String(100))
    grade: Mapped[str | None] = mapped_column(String(20))
    phone: Mapped[str | None] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(
        enum_column("student_status", "enrolled", "paused", "withdrawn"),
        default="enrolled",
    )
    omr_number: Mapped[str | None] = mapped_column(String(8))


class Guardian(Base):
    __tablename__ = "guardian"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("student.id"), index=True)
    relation: Mapped[str] = mapped_column(String(20))
    name: Mapped[str] = mapped_column(String(50))
    phone: Mapped[str] = mapped_column(String(20))
    is_notify_target: Mapped[bool] = mapped_column(Boolean, default=True)


class Klass(Base):
    __tablename__ = "class"

    id: Mapped[int] = mapped_column(primary_key=True)
    campus_id: Mapped[int] = mapped_column(ForeignKey("campus.id"), index=True)
    name: Mapped[str] = mapped_column(String(50))
    grade: Mapped[str | None] = mapped_column(String(20))
    teacher_id: Mapped[int | None] = mapped_column(ForeignKey("app_user.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class ClassSchedule(Base):
    __tablename__ = "class_schedule"

    id: Mapped[int] = mapped_column(primary_key=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("class.id"), index=True)
    weekday: Mapped[int] = mapped_column()
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)


class Enrollment(Base):
    __tablename__ = "enrollment"

    id: Mapped[int] = mapped_column(primary_key=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("class.id"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("student.id"), index=True)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
