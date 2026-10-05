# -*- coding: utf-8 -*-
"""博客主页对象：发布 / 搜索 / 编辑 / 删除。"""
from __future__ import annotations

from pages.base_page import BasePage


class BlogPage(BasePage):
    def publish(self, title, content):
        self.driver.find_element("id", "title").send_keys(title)
        self.driver.find_element("id", "content").send_keys(content)
        self.driver.find_element("id", "publish-btn").click()
        # 发布是真实 POST 导航：等待列表出现新文章，避免读到旧页面。
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        WebDriverWait(self.driver, 8).until(
            EC.text_to_be_present_in_element(("id", "list"), title)
        )
        return self

    def search(self, keyword):
        self.driver.find_element("id", "q").send_keys(keyword)
        self.driver.execute_script("search()")
        # 搜索会触发页面导航（location.href='/?q=...'）：显式等待 URL 变化，
        # 避免在导航完成前读到旧页面（与 publish/edit 的等待策略保持一致）。
        from selenium.webdriver.support.ui import WebDriverWait
        WebDriverWait(self.driver, 8).until(
            lambda d: "q=" in d.current_url
        )
        return self

    def has_post(self, title):
        return title in self.driver.page_source

    def click_edit(self, title):
        self.driver.find_element(
            "xpath",
            f"//div[contains(@class,'post')][.//h3[contains(.,'{title}')]]//a[contains(@href,'edit')]",
        ).click()
        return self

    def edit_and_save(self, new_title, new_content):
        t = self.driver.find_element("id", "title")
        t.clear(); t.send_keys(new_title)
        c = self.driver.find_element("id", "content")
        c.clear(); c.send_keys(new_content)
        self.driver.find_element("id", "save-btn").click()
        # 保存是真实 POST 导航：等待列表页出现新标题，避免读到旧页面。
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        WebDriverWait(self.driver, 8).until(
            EC.text_to_be_present_in_element(("id", "list"), new_title)
        )
        return self

    def click_delete(self, title):
        # 博客删除用的是 JS 链接：<a href="javascript:del(id)">删除</a>，
        # 因此不能用 [contains(@href,'delete')]（不匹配），需定位 javascript:del 链接。
        self.driver.find_element(
            "xpath",
            f"//div[contains(@class,'post')][.//h3[contains(.,'{title}')]]"
            f"//a[contains(@href,'javascript:del')]",
        ).click()
        # 点击删除会弹 confirm 对话框，需处理 alert。Alert 出现需要等待。
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        WebDriverWait(self.driver, 8).until(EC.alert_is_present())
        self.driver.switch_to.alert.accept()
        # 接受后页面跳转，等待列表刷新到不含该文章
        WebDriverWait(self.driver, 8).until(
            lambda d: title not in d.page_source
        )
        return self