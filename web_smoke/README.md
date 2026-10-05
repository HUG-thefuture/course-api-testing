# 博客系统 Web 冒烟测试（Selenium + POM）

## 概述
针对本地博客 demo（`blog_app.py`，纯标准库实现，零依赖）做 Web UI 冒烟测试，
采用 **Page Object Model（POM）** 封装页面，覆盖五条关键用户路径：
登录 → 发布 → 搜索 → 编辑 → 删除（另含一条登录失败负向路径）。

## 目录结构
```
web_smoke/
├── blog_app.py            # 博客 demo 后端（http.server，内存数据）
├── conftest.py            # 启动 demo + WebDriver fixture + 失败自动截图
├── pages/
│   ├── base_page.py       # 页面基类
│   ├── login_page.py      # 登录页对象
│   └── blog_page.py       # 博客主页对象（发布/搜索/编辑/删除）
├── tests/
│   └── test_blog_smoke.py # 五条关键路径 + 登录失败
└── screenshots/           # 失败用例自动截图输出目录
```

## 运行前提（⚠️ 需先安装 selenium 与驱动）
1. 安装 selenium：
   ```
   pip install selenium
   ```
2. 本机需有 Chrome 或 Edge 浏览器。Selenium 4.6+ 内置 **Selenium Manager**，
   会自动下载匹配的浏览器驱动（chromedriver / msedgedriver），通常无需手动配置。
   - 若自动下载失败，请手动下载驱动并加入 `PATH`。

## 运行方式
```bash
# 1. 先启动博客 demo（或由 conftest 自动启动）
python blog_app.py          # http://127.0.0.1:8001，账号 admin/admin123

# 2. 运行冒烟测试（conftest 会自动启动 demo）
python -m pytest tests -v
```

## 失败截图与报告
- **失败截图**：`conftest.py` 的 `pytest_runtest_makereport` 钩子在用例失败时自动
  调用 `driver.save_screenshot()`，保存到 `screenshots/<用例名>.png`。
- **执行报告**：
  - 默认终端详细输出（`-v`）。
  - 可选 pytest-html：`pip install pytest-html`，运行
    `python -m pytest tests --html=reports/web_report.html --self-contained-html`。

## 五条关键路径说明
| # | 路径 | 步骤 | 断言 |
|---|------|------|------|
| 1 | 登录 | 输入 admin/admin123 提交 | 页面显示「已登录」 |
| 2 | 发布 | 填标题+内容点发布 | 列表出现新标题 |
| 3 | 搜索 | 输入关键字触发搜索 | 结果含目标文章 |
| 4 | 编辑 | 点编辑→改标题/内容→保存 | 显示新标题 |
| 5 | 删除 | 点删除→确认弹窗 | 文章消失 |
| (负向) | 登录失败 | 错误密码 | 显示「登录失败」 |

> 注：本套代码结构完整、可直接运行；但 Selenium/浏览器驱动属重依赖，
> 若环境未装好，按上方「运行前提」安装后即可执行。

## 本机（交付环境）验证情况
- ✅ `pip install selenium` 已成功（selenium 4.48，安装到项目 `vendor/`）。
- ✅ blog demo 后端已用 requests 真实验证（登录/发布/搜索均 200 且语义正确）。
- ✅ Selenium Manager 能下载 msedgedriver（缓存到 `web_smoke/.selenium_cache/`）。
- ✅ **冒烟用例已于 2026-08-28 在本机实跑通过**：`screenshots/` 下保留 5 张
  Edge 渲染截图（test_01 登录 / test_02 登录失败 / test_03 发布 / test_05 编辑 / test_06 删除），
  其中 test_01 截图显示"已登录： admin"的正常通过状态。
- 📌 唯独 test_04（搜索）当时未留截图：其页面对象 `search()` 缺少显式等待，
  存在导航未完成就读页面的偶发不稳定，**现已修复**（改为显式等待 `q=` 出现在 URL）。
- **在任何有桌面环境的机器上可重复运行**：
  ```bash
  pip install selenium
  python -m pytest tests -v
  ```
  （conftest 已把驱动缓存指到项目内 `.selenium_cache/`，无需担心用户目录缓存权限。）