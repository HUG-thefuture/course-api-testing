# -*- coding: utf-8 -*-
"""博客系统 Web 冒烟测试 — Page Object Model (POM)。

说明：
  - 使用 Selenium WebDriver。运行前需安装 selenium 与对应浏览器驱动。
  - 若本机未安装：`pip install selenium`，并确保驱动在 PATH
    （Selenium 4.6+ 内置 Selenium Manager 可自动下载驱动）。
  - 被测对象为本地博客 demo：`python blog_app.py`（默认 http://127.0.0.1:8001）
"""
from __future__ import annotations

import os

BASE_URL = os.environ.get("BLOG_BASE_URL", "http://127.0.0.1:8001")