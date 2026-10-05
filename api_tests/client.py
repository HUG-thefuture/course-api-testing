# -*- coding: utf-8 -*-
"""API 客户端封装：统一 URL、鉴权头、常用方法，返回 requests.Response。

测试用例只面向业务方法（login/enroll/unenroll/...），不直接拼 URL。
"""
from __future__ import annotations

import requests


class ApiClient:
    """封装选课系统 HTTP 接口 + Bearer token。"""

    def __init__(self, session: requests.Session, base_url: str, token: str | None = None):
        self.session = session
        self.base_url = base_url.rstrip("/")
        self.token = token

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    # --- 公开接口 ---
    def register(self, username, password="pass123", role="student"):
        return self.session.post(f"{self.base_url}/api/register",
                                 json={"username": username, "password": password, "role": role})

    def login(self, username, password):
        return self.session.post(f"{self.base_url}/api/login",
                                 json={"username": username, "password": password})

    def list_courses(self):
        return self.session.get(f"{self.base_url}/api/courses", headers=self._headers())

    def get_course(self, course_id):
        return self.session.get(f"{self.base_url}/api/courses/{course_id}", headers=self._headers())

    def enroll(self, course_id):
        return self.session.post(f"{self.base_url}/api/enroll",
                                 json={"course_id": course_id}, headers=self._headers())

    def unenroll(self, course_id):
        return self.session.post(f"{self.base_url}/api/unenroll",
                                 json={"course_id": course_id}, headers=self._headers())

    def my_courses(self):
        return self.session.get(f"{self.base_url}/api/my-courses", headers=self._headers())

    # --- 管理员接口 ---
    def admin_create_course(self, name, capacity, start_time, end_time):
        return self.session.post(f"{self.base_url}/api/admin/courses",
                                 json={"name": name, "capacity": capacity,
                                       "start_time": start_time, "end_time": end_time},
                                 headers=self._headers())

    def admin_stats(self):
        return self.session.get(f"{self.base_url}/api/admin/stats", headers=self._headers())

    def grant_role(self, username, role):
        return self.session.patch(f"{self.base_url}/api/admin/users/{username}/role",
                                  json={"role": role}, headers=self._headers())


def make_client(http, base_url, token_info=None):
    """便捷构造：token_info 为 (username, token) 或 None。"""
    token = token_info[1] if token_info else None
    return ApiClient(http, base_url, token)