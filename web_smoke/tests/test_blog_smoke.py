# -*- coding: utf-8 -*-
"""博客系统五条关键用户路径冒烟测试（POM + Selenium）。

路径：登录 → 发布 → 搜索 → 编辑 → 删除。
运行前提：`pip install selenium` + 本机有 Chrome/Edge（Selenium Manager 自动下驱动）。
"""
from __future__ import annotations

import pytest

from pages.login_page import LoginPage
from pages.blog_page import BlogPage


@pytest.fixture
def logged_in_browser(browser):
    """登录后返回 driver。"""
    LoginPage(browser).login("admin", "admin123").wait_logged_in()
    return browser


def test_01_login(browser):
    """路径1：登录。"""
    page = LoginPage(browser)
    page.login("admin", "admin123").wait_logged_in()
    assert page.is_logged_in(), "登录后页面应显示已登录"


def test_02_login_failure(browser):
    """登录失败（附带负向路径）。"""
    page = LoginPage(browser)
    page.login("admin", "wrongpass").wait_login_failed()
    assert "登录失败" in browser.page_source


def test_03_publish(logged_in_browser):
    """路径2：发布文章。"""
    page = BlogPage(logged_in_browser)
    page.publish("Smoke测试文章_发布", "这是冒烟测试发布的内容")
    assert page.has_post("Smoke测试文章_发布"), "发布后列表应出现新文章"


def test_04_search(logged_in_browser):
    """路径3：搜索。"""
    page = BlogPage(logged_in_browser)
    page.publish("Smoke搜索目标文章", "用于搜索验证")
    page.search("Smoke搜索目标")
    assert page.has_post("Smoke搜索目标文章"), "搜索结果应包含目标文章"


def test_05_edit(logged_in_browser):
    """路径4：编辑文章。"""
    page = BlogPage(logged_in_browser)
    page.publish("Smoke编辑原文章", "原始内容")
    page.click_edit("Smoke编辑原文章")
    page.edit_and_save("Smoke编辑改后文章", "修改后的内容")
    assert page.has_post("Smoke编辑改后文章"), "编辑保存后应显示新标题"


def test_06_delete(logged_in_browser):
    """路径5：删除文章。"""
    page = BlogPage(logged_in_browser)
    page.publish("Smoke删除目标文章", "将被删除")
    page.click_delete("Smoke删除目标文章")
    assert not page.has_post("Smoke删除目标文章"), "删除后文章应消失"