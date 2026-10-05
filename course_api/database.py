# -*- coding: utf-8 -*-
"""数据库访问辅助（供测试直接校验选课记录与容量变化）。"""
from __future__ import annotations

from course_api.main import Base, Course, Enrollment, User, engine, SessionLocal


def reset_db() -> None:
    """删除全部表后重建，得到干净的确定性环境。"""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def query_course(course_id: int) -> Course | None:
    db = SessionLocal()
    try:
        return db.query(Course).filter(Course.id == course_id).first()
    finally:
        db.close()


def count_enrollments(student_id: int, course_id: int) -> int:
    db = SessionLocal()
    try:
        return (
            db.query(Enrollment)
            .filter(Enrollment.student_id == student_id, Enrollment.course_id == course_id)
            .count()
        )
    finally:
        db.close()


def seek_user_id(username: str) -> int | None:
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.username == username).first()
        return u.id if u else None
    finally:
        db.close()