# -*- coding: utf-8 -*-
"""接口自动化测试全局配置 (pytest conftest)。

设计要点：
  1. session 级启动真实 uvicorn 后端（子进程），测试用 requests 打真实 HTTP，
     而不是 TestClient —— 满足「pytest + requests」的工程要求。
  2. function 级 fixture 为每个用例生成隔离用户，测试可重复、互不干扰。
  3. 通过环境变量控制后端地址，便于对接真机/CI：
        API_BASE_URL  -> 默认 http://127.0.0.1:8000
        USE_EXTERNAL  -> 1 时不启动子进程，连接已存在的后端

  依赖目录：项目根 vendor/ 下通过 PYTHONPATH 提供（见 run_tests.ps1）。
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent          # api_tests/
PROJECT = ROOT.parent                            # project/
# vendor 依赖优先 —— 必须在 import pytest / requests 之前插入，
# 否则直接 `python -m pytest` 时这两条 import 会先于 vendor 生效而 ImportError。
# 默认启用 vendor（教程口径：依赖已 vendor 化，无需 pip install 即可跑）；
# 已在虚拟环境装好依赖时可设 USE_BUNDLED_VENDOR=0 改用当前环境。
if os.environ.get("USE_BUNDLED_VENDOR", "1") == "1":
    sys.path.insert(0, str(PROJECT / "vendor"))
sys.path.insert(0, str(PROJECT))                 # 让 course_api 可 import
sys.path.insert(0, str(ROOT))                    # 让 client/utils 可 import

import pytest
import requests

BASE_URL = os.environ.get("API_BASE_URL", "http://127.0.0.1:8000")
USE_EXTERNAL = os.environ.get("USE_EXTERNAL", "0") == "1"
if USE_EXTERNAL:
    raise pytest.UsageError("本套件会重建表，禁止对外部服务执行。请取消 USE_EXTERNAL；套件自动创建临时 SQLite 和本地服务。")
# 在任何测试模块 import course_api 前绑定隔离库；子进程继承同一地址。
_test_database = tempfile.TemporaryDirectory(prefix="course-api-tests-")
os.environ["COURSE_DATABASE_URL"] = "sqlite:///" + (Path(_test_database.name) / "course.db").as_posix()

_port = None
_proc = None


def _free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture(scope="session")
def base_url():
    """会话级：启动后端并返回 base_url。"""
    global _proc, _port
    if USE_EXTERNAL:
        yield BASE_URL
        return
    # 启动真实 uvicorn 子进程
    _port = _free_port()
    url = f"http://127.0.0.1:{_port}"
    env = dict(os.environ)
    # 子进程起 uvicorn 同样需要 vendor 依赖：sys.path 只对本进程生效，
    # 传给子进程必须经 PYTHONPATH（USE_BUNDLED_VENDOR=0 时沿用当前环境）。
    if os.environ.get("USE_BUNDLED_VENDOR", "1") == "1":
        env["PYTHONPATH"] = str(PROJECT / "vendor") + os.pathsep + env.get("PYTHONPATH", "")
    # 每次会话使用独立 SQLite，确保数据干净且不污染手工运行的数据
    cmd = [sys.executable, "-m", "uvicorn", "course_api.main:app", "--host", "127.0.0.1", "--port", str(_port)]
    # 子进程输出落临时文件：原先 DEVNULL 会吞掉启动报错，失败时只能看到连接超时
    _server_log = PROJECT / "reports" / "uvicorn.log"
    _server_log.parent.mkdir(exist_ok=True)
    with open(_server_log, "w", encoding="utf-8", errors="replace") as log_fh:
        _proc = subprocess.Popen(
            cmd, cwd=str(PROJECT), env=env,
            stdout=log_fh, stderr=subprocess.STDOUT,
        )
        # 轮询等待就绪
        deadline = time.time() + 20
        while time.time() < deadline:
            try:
                r = requests.get(f"{url}/api/courses", timeout=1)
                if r.status_code == 200:
                    break
            except Exception:
                time.sleep(0.3)
        else:
            _proc.terminate()
            raise RuntimeError(
                f"后端启动超时，uvicorn 日志见 {_server_log}")
    yield url
    _proc.terminate()
    _proc.wait(timeout=5)


@pytest.fixture
def http(base_url):
    """每个测试独立的 requests.Session。"""
    s = requests.Session()
    s.headers["Host"] = "127.0.0.1"
    yield s
    s.close()


@pytest.fixture(autouse=True)
def _reset_db_before_each():
    """每个用例前把数据库重置到种子状态，保证用例互相隔离、可重复执行。

    （后端在子进程运行，共享同一 SQLite 文件；此处直接在测试进程内重建。）
    """
    from course_api.main import Base, engine, seed_data
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    seed_data()
    yield


# ---------------------------------------------------------------------------
# 用户/token fixture：注册隔离用户，返回 (用户名, token)
# ---------------------------------------------------------------------------
def _register_user(http: requests.Session, base_url: str, role: str) -> tuple[str, str]:
    uname = f"u_{uuid.uuid4().hex[:10]}"
    r = http.post(f"{base_url}/api/register",
                  json={"username": uname, "password": "pass123", "role": role})
    assert r.status_code == 200, f"注册失败: {r.status_code} {r.text}"
    return uname, r.json()["token"]


@pytest.fixture
def student_token(http, base_url):
    """每个用例一个全新学生（username, token），天然数据隔离。"""
    return _register_user(http, base_url, "student")


@pytest.fixture
def teacher_token(http, base_url):
    return _register_user(http, base_url, "teacher")


@pytest.fixture
def admin_token(http, base_url):
    """种子管理员（admin/pass123）登录获取 token。

    2026-09 起 /api/register 禁止自助注册 admin（提权漏洞），
    管理员一律用种子账号登录，或经 /api/admin/users/{name}/role 授予。
    """
    r = http.post(f"{base_url}/api/login",
                  json={"username": "admin", "password": "pass123"})
    assert r.status_code == 200, f"种子管理员登录失败: {r.status_code} {r.text}"
    return "admin", r.json()["token"]


# ---------------------------------------------------------------------------
# HTML 报告收集（自写，零依赖；若需要 allure 见 docs/test_plan.md）
# ---------------------------------------------------------------------------
def pytest_runtest_makereport(item, call):
    """收集单个用例结果与失败详情（含请求/响应/断言消息）。

    2026-09 修复：原先只收集 call 阶段，fixture/teardown 报错时用例为
    error 但报告整行缺失，summary 少计且"退出码非 0 报告近全绿"。
    现在 setup 失败与 teardown 报错一并入报告（outcome=error）。
    """
    if call.when == "teardown" and call.excinfo is None:
        return  # 正常 teardown 不产生报告行
    if call.when not in ("call", "setup", "teardown"):
        return
    from report_builder import collector

    outcome = "passed"
    detail = ""
    if call.excinfo is not None:
        if call.excinfo.errisinstance(pytest.skip.Exception):
            outcome = "skipped"
        else:
            outcome = "failed" if call.when == "call" else "error"
            # 断言消息已包含「期望/实际状态码 + 响应正文」，直接作为失败详情
            try:
                detail = str(call.excinfo.value)
            except Exception:
                detail = repr(call.excinfo)
            if call.when != "call":
                detail = f"[{call.when} 阶段报错] {detail}"

    if call.when == "call" or call.excinfo is not None:
        # 同一 nodeid 去重：call 失败且 teardown 再报错时会写两行，报告会双计
        existing = next((r for r in collector.results if r["name"] == item.nodeid), None)
        record = {
            "name": item.nodeid,
            "outcome": outcome,
            "duration": round(call.duration, 3),
            "detail": detail,
        }
        if existing is not None:
            if call.when == "call":
                # 同名记录已存在（setup 阶段曾记录过，防御性覆盖为 call 结果）
                collector.results.remove(existing)
                collector.add(record)
            elif existing["outcome"] == "passed":
                # call 通过但 teardown 报错：整体应记 error，不能静默丢失
                existing["outcome"] = "error"
                existing["detail"] = detail
            # call 失败后 teardown 再报错：保留 call 的 failed 记录（主要事实），不双计
            return
        collector.add(record)


def pytest_sessionfinish(session, exitstatus):
    """会话结束渲染 HTML 报告。"""
    from report_builder import render_report
    try:
        path = render_report()
        print(f"\n[报告] HTML 测试报告已生成: {path}")
    except Exception as e:  # 报告失败不影响测试结果
        print(f"\n[报告] 生成失败(忽略): {e}")
    if "course_api.main" in sys.modules:
        sys.modules["course_api.main"].engine.dispose()
    _test_database.cleanup()
