# -*- coding: utf-8 -*-
"""容量边界精确用例：通过管理员创建 capacity=N 的课程，验证 N-1/N/N+1 边界。"""
from __future__ import annotations

import pytest

from client import make_client
from utils.assertions import assert_status, assert_success, assert_error_detail
from utils import db_check


@pytest.fixture
def student(http, base_url, student_token):
    return make_client(http, base_url, student_token), student_token[0]


@pytest.fixture
def admin(http, base_url, admin_token):
    return make_client(http, base_url, admin_token)


@pytest.fixture
def capacity_one_course(admin):
    """创建 capacity=1 的课程。"""
    r = admin.admin_create_course(
        name="单人课", capacity=1,
        start_time="2026-04-01T09:00:00", end_time="2026-04-01T10:00:00",
    )
    assert r.status_code == 201
    return r.json()["id"]


def test_capacity_one_first_seat_full_after(student, capacity_one_course):
    """capacity=1：第一个学生选上后 enrolled=1，已满。"""
    client, _ = student
    cid = capacity_one_course
    assert_success(client.enroll(cid))
    assert db_check.course_enrolled(cid) == 1


def test_capacity_one_second_student_rejected(http, base_url, capacity_one_course, student_token):
    """capacity=1：第二名（新注册）学生再选应 409 容量已满。"""
    # 第一名学生占满
    c1 = make_client(http, base_url, student_token)
    assert_success(c1.enroll(capacity_one_course))
    # 第二名新学生
    r = http.post(f"{base_url}/api/register",
                  json={"username": "second_student", "password": "pass123", "role": "student"})
    assert r.status_code == 200
    token = r.json()["token"]
    c2 = make_client(http, base_url, ("second_student", token))
    r2 = c2.enroll(capacity_one_course)
    assert_status(r2, 409, "第二个学生应容量已满")
    assert_error_detail(r2, "容量已满")


def test_capacity_zero_rejected(admin):
    """capacity 必须 >=1，创建 capacity=0 应 422（pydantic 校验）。"""
    r = admin.admin_create_course(
        name="零容量课", capacity=0,
        start_time="2026-04-01T09:00:00", end_time="2026-04-01T10:00:00",
    )
    assert r.status_code == 422


def test_create_course_invalid_time_range(admin):
    """结束时间早于开始时间应 400。"""
    r = admin.admin_create_course(
        name="非法时间", capacity=10,
        start_time="2026-04-01T10:00:00", end_time="2026-04-01T09:00:00",
    )
    assert_status(r, 400, "结束时间早于开始时间")


def test_concurrent_enroll_no_oversell(http, base_url, capacity_one_course):
    """并发选课不超卖（2026-09 修复回归）。

    修复前：容量判断与 enrolled+1 是 check-then-act，并发下会超卖且从未被
    串行用例发现。修复后：原子条件 UPDATE（enrolled < capacity 才 +1）。
    """
    import concurrent.futures

    import requests as _requests

    tokens = []
    for i in range(8):
        r = http.post(f"{base_url}/api/register",
                      json={"username": f"race_{i}", "password": "pass123", "role": "student"})
        assert r.status_code == 200, r.text
        tokens.append(r.json()["token"])

    def try_enroll(token: str) -> int:
        s = _requests.Session()
        s.headers["Host"] = "127.0.0.1"
        r = s.post(f"{base_url}/api/enroll",
                   json={"course_id": capacity_one_course},
                   headers={"Authorization": f"Bearer {token}"}, timeout=30)
        return r.status_code

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        codes = list(pool.map(try_enroll, tokens))

    assert codes.count(200) == 1, f"capacity=1 应恰好 1 人成功，实际 {codes}"
    assert codes.count(409) == 7, f"其余应 409 容量已满，实际 {codes}"
    assert db_check.course_enrolled(capacity_one_course) == 1, "enrolled 不得超卖"