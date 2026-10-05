# -*- coding: utf-8 -*-
"""鉴权相关用例：登录 / 注册 / token 校验。"""
from __future__ import annotations

import pytest

from client import make_client
from utils.assertions import assert_status, assert_error_detail, assert_success


# ---------------------------------------------------------------------------
# 登录
# ---------------------------------------------------------------------------
def test_login_success(http, base_url):
    r = make_client(http, base_url).login("alice", "pass123")
    assert_status(r, 200, "登录成功")
    body = r.json()
    # 2026-09 起 token 为随机不透明串（服务端只存 SHA-256 摘要），不再可预测
    assert len(body["token"]) >= 32, f"token 应为足够长的随机串: {body['token']!r}"
    assert body["role"] == "student"


@pytest.mark.parametrize("username,password", [
    ("alice", "wrong"),      # 密码错误
    ("nobody", "pass123"),   # 用户不存在
    ("", ""),                # 空用户名/空密码
    ("alice", ""),           # 空密码
])
def test_login_failure(http, base_url, username, password):
    r = make_client(http, base_url).login(username, password)
    assert_status(r, 401, "登录失败场景")


# ---------------------------------------------------------------------------
# 注册
# ---------------------------------------------------------------------------
def test_register_success(http, base_url):
    c = make_client(http, base_url)
    r = c.register("new_student_1", "pass123", "student")
    assert_success(r, "注册成功")
    assert r.json()["role"] == "student"


def test_register_duplicate_username(http, base_url):
    c = make_client(http, base_url)
    assert_success(c.register("dup_user", "pass123", "student"))
    r = c.register("dup_user", "pass123", "student")
    assert_status(r, 409, "重复注册")
    assert_error_detail(r, "用户名已存在")


@pytest.mark.parametrize("role", ["student", "teacher"])
def test_register_allowed_roles(http, base_url, role):
    c = make_client(http, base_url)
    r = c.register(f"role_{role}", "pass123", role)
    assert_success(r, f"注册角色 {role}")
    assert r.json()["role"] == role


def test_register_admin_forbidden(http, base_url):
    """2026-09 修复回归：任何人可自注册 admin 是提权漏洞，必须 403。"""
    c = make_client(http, base_url)
    r = c.register("self_admin", "pass123", "admin")
    assert_status(r, 403, "自注册 admin 应被拒绝")
    assert_error_detail(r, "管理员")


def test_admin_grant_role(http, base_url, admin_token):
    """admin 可经专用端点授予角色；学生无权调用（403）。"""
    admin = make_client(http, base_url, admin_token)
    uname, _ = _mk_student(http, base_url)
    r = admin.grant_role(uname, "teacher")
    assert r.status_code == 200, r.text
    assert r.json()["role"] == "teacher"
    # 学生调授予接口应 403（客户端凭据用第二个学生自己的用户名+token 正确配对）
    uname2, stu_token = _mk_student(http, base_url)
    stu = make_client(http, base_url, (uname2, stu_token))
    r2 = stu.grant_role("alice", "admin")
    assert_status(r2, 403)


def test_password_stored_hashed(http, base_url):
    """2026-09 修复回归：密码必须以 PBKDF2 哈希落库，不得明文。

    注意：断言读的是本地 course.db，仅本地子进程模式有效；
    USE_EXTERNAL=1 对接远程后端时本地库不代表被测端。
    """
    import sqlite3
    from pathlib import Path
    db_file = Path(__file__).resolve().parent.parent / "course.db"
    with sqlite3.connect(db_file) as con:
        row = con.execute(
            "select password from users where username='alice'"
        ).fetchone()
    assert row, "种子用户 alice 应存在"
    assert row[0].startswith("pbkdf2_sha256$"), f"密码应已哈希: {row[0][:30]}..."
    assert "pass123" not in row[0]


def _mk_student(http, base_url) -> tuple[str, str]:
    import uuid as _uuid
    uname = f"g_{_uuid.uuid4().hex[:10]}"
    r = http.post(f"{base_url}/api/register",
                  json={"username": uname, "password": "pass123", "role": "student"})
    assert r.status_code == 200, r.text
    return uname, r.json()["token"]


def test_register_invalid_role(http, base_url):
    c = make_client(http, base_url)
    r = c.register("bad_role_user", "pass123", "superuser")
    assert_status(r, 400, "非法角色")
    assert_error_detail(r, "非法角色")


# ---------------------------------------------------------------------------
# token 校验（无 token / 伪造 token）
# ---------------------------------------------------------------------------
def test_enroll_without_token(http, base_url):
    r = make_client(http, base_url).enroll(3)
    # vendor FastAPI 的 HTTPBearer 对缺失凭据固定返回 401（伪造 token 同为 401），
    # 收紧为精确断言以锁定状态码约定
    assert_status(r, 401, "无 token 调用受保护接口")


def test_enroll_with_bad_token(http, base_url):
    r = make_client(http, base_url, ("x", "token-not-exist-user")).enroll(3)
    assert_status(r, 401, "伪造 token")


def test_enroll_with_legacy_forgeable_token(http, base_url):
    """2026-09 修复回归：旧版可预测 token（token-<username>）必须失效。"""
    r = make_client(http, base_url, ("alice", "token-alice")).enroll(3)
    assert_status(r, 401, "旧版可预测 token 应失效")