# -*- coding: utf-8 -*-
"""Web 冒烟测试 conftest：启动 blog demo + 提供 WebDriver + 失败自动截图。"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
# 注意：vendor 路径必须先于 requests/pytest 等第三方导入加入 sys.path，
# 这样即使忘记设置 PYTHONPATH，直接 `python -m pytest tests` 也能找到依赖。
# 默认启用 vendor（与 api_tests 一致）；设 USE_BUNDLED_VENDOR=0 改用当前环境。
if os.environ.get("USE_BUNDLED_VENDOR", "1") == "1":
    sys.path.insert(0, str(PROJECT / "vendor"))
sys.path.insert(0, str(ROOT))

import pytest  # noqa: E402
import requests  # noqa: E402

SCREENSHOT_DIR = ROOT / "screenshots"
SCREENSHOT_DIR.mkdir(exist_ok=True)

_proc = None


@pytest.fixture(scope="function")
def blog_server():
    """函数级启动博客 demo 后端：每个用例一个全新进程。

    学习要点：被测系统往往有全局状态（这里的 SESSION 登录态、posts 列表）。
    若一个进程服务多个用例，全局状态会在用例间传递、让断言互相影响。
    最稳的隔离方案是「每用例一台全新 SUT」——这里同理，服务按函数级重建，
    确保每个用例从无登录、两篇种子文章 的干净状态开始。
    """
    global _proc
    env = dict(os.environ)
    _proc = subprocess.Popen(
        [sys.executable, str(ROOT / "blog_app.py")],
        cwd=str(ROOT), env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    for _ in range(20):
        try:
            if requests.get("http://127.0.0.1:8001/", timeout=1).status_code == 200:
                break
        except Exception:
            time.sleep(0.3)
    yield "http://127.0.0.1:8001"
    try:
        _proc.terminate()
        _proc.wait(timeout=5)
    except Exception:
        _proc.kill()


@pytest.fixture(autouse=True)
def reset_server_state(blog_server):
    """每个测试前重置后端登录态，保证用例相互隔离。

    学习要点：被测系统的「全局状态」（如这里的 SESSION）会让用例互相污染。
    冒烟套件必须在每个用例前把 SUT 恢复到干净状态，否则用例顺序一变，
    结果就不同（这里 test_01 登录后，后面的"登录失败"用例就找不到登录表单了）。
    """
    try:
        requests.get("http://127.0.0.1:8001/logout", timeout=2)
    except Exception:
        pass  # 服务刚启动尚未就绪等情况忽略
    yield


@pytest.fixture
def browser(blog_server):
    """提供 Selenium WebDriver（优先 Edge，其次 Chrome，Selenium Manager 自动下驱动）。

    注意：运行前需要 `pip install selenium` 且本机有 Chrome/Edge 浏览器。
    """
    selenium = pytest.importorskip("selenium", reason="需安装 selenium 才能运行 Web 冒烟测试")
    from selenium import webdriver
    from selenium.webdriver.edge.options import Options as EdgeOptions
    from selenium.webdriver.chrome.options import Options as ChromeOptions

    # 让 Selenium Manager 把驱动缓存到项目内（规避用户目录 .cache 不可写的问题）
    _driver_cache = ROOT / ".selenium_cache"
    _driver_cache.mkdir(exist_ok=True)
    os.environ.setdefault("SE_CACHE_PATH", str(_driver_cache))
    os.environ.setdefault("SELENIUM_MANAGER_CACHE", str(_driver_cache))

    # 优先 Edge（本机常见、驱动易得），其次 Chrome
    driver = None
    last_err = None
    for name, opts in (
        ("Edge", EdgeOptions()),
        ("Chrome", ChromeOptions()),
    ):
        opts.add_argument("--headless=new")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--window-size=1280,800")
        try:
            driver = getattr(webdriver, name)(options=opts)
            break
        except Exception as e:
            last_err = e
    if driver is None:
        raise RuntimeError(f"未能启动浏览器(Edge/Chrome)：{last_err}")
    driver.implicitly_wait(5)
    yield driver
    driver.quit()


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """失败时自动截图，保存到 screenshots/ 便于缺陷定位。"""
    outcome = yield
    rep = outcome.get_result()
    if rep.when == "call" and rep.failed:
        driver = item.funcargs.get("browser")
        if driver is not None:
            name = item.name.replace("/", "_").replace("::", "_")
            path = SCREENSHOT_DIR / f"{name}.png"
            try:
                driver.save_screenshot(str(path))
                print(f"\n[截图] 失败截图已保存: {path}")
            except Exception:
                pass
