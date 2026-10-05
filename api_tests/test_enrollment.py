# -*- coding: utf-8 -*-
"""选课 / 退课核心用例（含数据库级校验容量变化与选课记录）。"""
from __future__ import annotations

import pytest

from client import make_client
from utils.assertions import assert_status, assert_success, assert_error_detail
from utils import db_check


@pytest.fixture
def student(http, base_url, student_token):
    """返回 (client, username)。"""
    return make_client(http, base_url, student_token), student_token[0]


# ---------------------------------------------------------------------------
# 正常选课
# ---------------------------------------------------------------------------
def test_enroll_success_and_db(student):
    client, uname = student
    # id=3 计算机网络 capacity=50，初始 enrolled=0
    before = db_check.course_enrolled(3)
    r = client.enroll(3)
    assert_status(r, 200, "选课成功")
    assert r.json()["enrolled"] == before + 1
    # 数据库断言：选课记录存在，容量 +1
    db_check.assert_enrollment_row_exists(uname, 3, expect=True)
    db_check.assert_capacity_delta(3, before, before + 1)


def test_enroll_then_list_my_courses(student):
    client, _ = student
    assert_success(client.enroll(3))
    r = client.my_courses()
    assert_success(r)
    ids = [c["id"] for c in r.json()]
    assert 3 in ids


# ---------------------------------------------------------------------------
# 异常选课
# ---------------------------------------------------------------------------
def test_enroll_duplicate(student):
    client, uname = student
    assert_success(client.enroll(3))
    r = client.enroll(3)
    assert_status(r, 409, "重复选课")
    assert_error_detail(r, "已选过")
    # 重复失败不应产生第二条记录，容量不变
    db_check.assert_capacity_delta(3, 1, 1)


def test_enroll_nonexistent_course(student):
    client, _ = student
    r = client.enroll(99999)
    assert_status(r, 404, "课程不存在")
    assert_error_detail(r, "课程不存在")


def test_enroll_duplicate_does_not_double_count(student):
    """重复选课被拒绝后，仅一条记录、容量仅 +1。"""
    client, uname = student
    assert_success(client.enroll(3))
    before = db_check.course_enrolled(3)
    assert_status(client.enroll(3), 409)
    assert db_check.course_enrolled(3) == before
    db_check.assert_enrollment_row_exists(uname, 3, expect=True)


# ---------------------------------------------------------------------------
# 退课
# ---------------------------------------------------------------------------
def test_unenroll_success_and_db(student):
    client, uname = student
    assert_success(client.enroll(3))
    before = db_check.course_enrolled(3)
    r = client.unenroll(3)
    assert_status(r, 200, "退课成功")
    assert r.json()["enrolled"] == before - 1
    # 数据库断言：记录删除，容量 -1
    db_check.assert_enrollment_row_exists(uname, 3, expect=False)
    db_check.assert_capacity_delta(3, before, before - 1)


def test_unenroll_not_enrolled(student):
    client, _ = student
    r = client.unenroll(3)
    assert_status(r, 404, "未选却退")
    assert_error_detail(r, "未选")


def test_unenroll_twice(student):
    client, _ = student
    assert_success(client.enroll(3))
    assert_success(client.unenroll(3))
    r = client.unenroll(3)
    assert_status(r, 404, "重复退课")


# ---------------------------------------------------------------------------
# 边界：课程容量已满
# ---------------------------------------------------------------------------
def test_enroll_capacity_full(student):
    client, _ = student
    # id=1 数据结构 capacity=30 enrolled=30，已满
    r = client.enroll(1)
    assert_status(r, 409, "容量已满")
    assert_error_detail(r, "容量已满")


def test_enroll_capacity_exactly_one_seat(student):
    """容量 boundary：id=2 capacity=2，当前学生选 1 次后 enrolled=1，还剩 1 席。"""
    client, _ = student
    assert_success(client.enroll(2))
    assert db_check.course_enrolled(2) == 1