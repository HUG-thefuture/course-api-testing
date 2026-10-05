# -*- coding: utf-8 -*-
"""断言封装：把状态码/业务错误码/响应结构断言统一收口。

好处：
  1. 失败信息更可读（带上实际响应内容，便于缺陷定位）。
  2. 业务语义统一，测试用例代码更聚焦。
"""
from __future__ import annotations


def assert_status(resp, expected: int, msg: str = ""):
    """断言 HTTP 状态码，失败时携带响应正文。"""
    assert resp.status_code == expected, (
        f"{msg} 期望状态码 {expected}，实际 {resp.status_code}，"
        f"响应: {_body(resp)}"
    )


def assert_success(resp, msg: str = ""):
    """断言 2xx 成功。"""
    assert 200 <= resp.status_code < 300, (
        f"{msg} 期望成功(2xx)，实际 {resp.status_code}，响应: {_body(resp)}"
    )


def assert_error_detail(resp, keyword: str):
    """断言错误响应 detail 中包含关键字（如 '容量已满'）。"""
    body = _json(resp)
    detail = body.get("detail", "")
    assert keyword in str(detail), (
        f"期望错误信息包含 '{keyword}'，实际 detail='{detail}'，"
        f"状态码 {resp.status_code}，响应: {body}"
    )


def _json(resp):
    try:
        return resp.json()
    except Exception:
        return {}


def _body(resp):
    try:
        return resp.json()
    except Exception:
        return resp.text[:500]