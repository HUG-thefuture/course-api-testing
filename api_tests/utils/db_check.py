# -*- coding: utf-8 -*-
"""数据库校验工具：绕过 HTTP 直接查 SQLite，校验选课记录与容量变化。

用于「数据库级」断言，证明接口不仅返回正确状态码，而且真实落库。
若切换 MySQL，仅需把 course_api.database 的 DATABASE_URL 改为 MySQL 即可，
本模块调用的是 SQLAlchemy ORM，无需改动。
"""
from __future__ import annotations

from course_api.database import count_enrollments, query_course, seek_user_id


def course_enrolled(course_id: int) -> int:
    """返回某课程当前已选人数（courses.enrolled 字段）。"""
    c = query_course(course_id)
    assert c is not None, f"课程 {course_id} 不存在"
    return c.enrolled


def assert_enrollment_row_exists(student_username: str, course_id: int, expect: bool = True):
    """断言选课记录(enrollments 表)是否存在/不存在。"""
    uid = seek_user_id(student_username)
    assert uid is not None, f"用户 {student_username} 不存在"
    n = count_enrollments(uid, course_id)
    if expect:
        assert n == 1, f"期望存在选课记录(student={student_username}, course={course_id})，实际 {n} 条"
    else:
        assert n == 0, f"期望不存在选课记录(student={student_username}, course={course_id})，实际 {n} 条"


def assert_capacity_delta(course_id: int, before: int, after: int):
    """断言容量(enrolled 字段)从 before 变化到 after。"""
    cur = course_enrolled(course_id)
    assert cur == after, (
        f"课程 {course_id} 容量变化断言失败：初始 {before}，期望 {after}，实际 {cur}"
    )