# -*- coding: utf-8 -*-
"""时间冲突用例：选课时段重叠必须拒绝。

说明：通过管理员创建课程来精确控制时间，验证冲突判定逻辑。
"""
from __future__ import annotations

import pytest

from client import make_client
from utils.assertions import assert_status, assert_success, assert_error_detail


@pytest.fixture
def student(http, base_url, student_token):
    return make_client(http, base_url, student_token), student_token[0]


@pytest.fixture
def admin(http, base_url, admin_token):
    return make_client(http, base_url, admin_token)


@pytest.fixture
def conflict_course(admin):
    """创建一个 9:00-10:00 的课程，与种子课程 id=2 同时段。返回 course_id。"""
    r = admin.admin_create_course(
        name="冲突测试课", capacity=10,
        start_time="2026-03-01T09:00:00", end_time="2026-03-01T10:00:00",
    )
    assert r.status_code == 201, f"创建课程失败 {r.text}"
    return r.json()["id"]


def test_enroll_time_conflict(student, conflict_course):
    client, _ = student
    # 先选 id=2（9:00-10:00），再选同为 9:00-10:00 的冲突课程应 409
    assert_success(client.enroll(2))
    r = client.enroll(conflict_course)
    assert_status(r, 409, "时间冲突")
    assert_error_detail(r, "冲突")


def test_enroll_partial_overlap(student, admin):
    """部分重叠（9:30-10:30 与已选的 9:00-10:00 重叠半小时）也应冲突。"""
    client, _ = student
    assert_success(client.enroll(2))  # 9:00-10:00
    r = admin.admin_create_course(
        name="部分重叠课", capacity=10,
        start_time="2026-03-01T09:30:00", end_time="2026-03-01T10:30:00",
    )
    assert r.status_code == 201, f"创建课程失败 {r.text}"
    cid = r.json()["id"]
    r2 = client.enroll(cid)
    assert_status(r2, 409)
    assert_error_detail(r2, "冲突")


def test_enroll_no_conflict_adjacent(student, admin):
    """相邻不重叠时段可正常选课（9:00-10:00 与 10:00-11:00）。"""
    client, _ = student
    assert_success(client.enroll(2))  # 9:00-10:00
    r = admin.admin_create_course(
        name="相邻课", capacity=10,
        start_time="2026-03-01T10:00:00", end_time="2026-03-01T11:00:00",
    )
    cid = r.json()["id"]
    r2 = client.enroll(cid)
    assert_status(r2, 200, "相邻时段不冲突")


def test_enroll_same_time_no_conflict_across_users(student, http, base_url, conflict_course):
    """不同学生选同一时段课程互不影响（冲突仅针对同一学生）。

    2026-09 修复回归：原用例只构造了一个学生，断言在任何实现下恒真（假测试）；
    现在同时验证"本人冲突 409"与"他人同时段 200"两个方向。
    """
    client_a, _ = student
    # 学生 A 先占满 9:00-10:00（种子课程 id=2），再选同时段的冲突课程应 409
    assert_success(client_a.enroll(2))
    r = client_a.enroll(conflict_course)
    assert_status(r, 409, "同一学生同时段应冲突")

    # 学生 B 没选过 9:00-10:00 的任何课程，选同一门冲突课程应成功
    import uuid as _uuid
    uname_b = f"b_{_uuid.uuid4().hex[:10]}"
    rb = http.post(f"{base_url}/api/register",
                   json={"username": uname_b, "password": "pass123", "role": "student"})
    assert rb.status_code == 200, rb.text
    client_b = make_client(http, base_url, (uname_b, rb.json()["token"]))
    r2 = client_b.enroll(conflict_course)
    assert_status(r2, 200, "不同学生选同一时段互不影响")