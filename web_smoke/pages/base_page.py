# -*- coding: utf-8 -*-
"""页面基类。"""
from __future__ import annotations

from pages import BASE_URL


class BasePage:
    def __init__(self, driver):
        self.driver = driver

    def open(self, path="/"):
        self.driver.get(BASE_URL + path)
        return self

    @property
    def page_title(self):
        return self.driver.title

    @property
    def page_source(self):
        return self.driver.page_source