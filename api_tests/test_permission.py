# -*- coding: utf-8 -*-
"""角色权限 / 越权用例（403）。"""
from __future__ import annotations

import pytest

from client import make_client
from utils.assertions import assert_status, assert_success


@pytest.fixture
def teacher(http, base_url, teacher_token):
    return make_client(http, base_url, teacher_token)


@pytest.fixture
def admin(http, base_url, admin_token):
    return make_client(http, base_url, admin_token)


@pytest.fixture
def student(http, base_url, student_token):
    return make_client(http, base_url, student_token)


def test_teacher_cannot_enroll(teacher):
    """教师不是学生，不能选课 -> 403。"""
    r = teacher.enroll(3)
    assert_status(r, 403, "教师选课应越权")


def test_teacher_cannot_unenroll(teacher):
    r = teacher.unenroll(3)
    assert_status(r, 403, "教师退课应越权")


def test_student_cannot_access_admin_stats(student):
    r = student.admin_stats()
    assert_status(r, 403, "学生访问管理接口应越权")


def test_teacher_cannot_access_admin_stats(teacher):
    r = teacher.admin_stats()
    assert_status(r, 403, "教师访问管理接口应越权")


def test_student_cannot_create_course(student):
    r = student.admin_create_course(
        name="越权建课", capacity=5,
        start_time="2026-05-01T09:00:00", end_time="2026-05-01T10:00:00",
    )
    assert_status(r, 403, "学生创建课程应越权")


def test_admin_can_access_stats(admin):
    r = admin.admin_stats()
    assert_success(r)
    body = r.json()
    assert "users" in body and "courses" in body


def test_admin_can_create_course(admin):
    r = admin.admin_create_course(
        name="管理员建课", capacity=10,
        start_time="2026-05-01T09:00:00", end_time="2026-05-01T10:00:00",
    )
    assert_status(r, 201, "管理员建课成功")
    assert r.json()["enrolled"] == 0


def test_admin_can_enroll(admin):
    """管理员本质上非 student，选课应被拒（管理员权限≠学生权限）。"""
    r = admin.enroll(3)
    assert_status(r, 403, "管理员选课应越权（非学生）")