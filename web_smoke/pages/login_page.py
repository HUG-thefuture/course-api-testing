# -*- coding: utf-8 -*-
"""登录页对象。"""
from __future__ import annotations

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from pages.base_page import BasePage


class LoginPage(BasePage):
    def login(self, username, password):
        """填写表单并提交（成功与失败路径都适用：本方法不做成功断言）。"""
        self.open("/")
        self.driver.find_element("name", "username").send_keys(username)
        self.driver.find_element("name", "password").send_keys(password)

        self.driver.find_element("xpath", "//form[@action='/login']//button").click()
        return self

    def wait_logged_in(self, timeout: float = 8.0):
        """表单是真实的 POST 导航：提交后必须「显式等待」新页面出现，
        否则立刻读取可能得到提交前的旧页面，导致断言不稳定。"""
        WebDriverWait(self.driver, timeout).until(
            EC.text_to_be_present_in_element(("id", "auth"), "已登录")
        )
        return self

    def wait_login_failed(self, timeout: float = 8.0):
        """等待登录失败页（401 返回体）出现。失败场景同样需要显式等待导航完成。"""
        WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located(("xpath", "//h1[contains(.,'登录失败')]"))
        )
        return self

    def is_logged_in(self):
        return "已登录" in self.driver.page_source