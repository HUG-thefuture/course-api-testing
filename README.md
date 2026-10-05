# 测试开发 项目合集（求职简历）

![CI](https://github.com/HUG-thefuture/course-api-testing/actions/workflows/ci.yml/badge.svg)

面向「软件测试 / 测试开发实习生」岗位的两个真实可运行测试项目。

- **项目一（重点）**：选课系统接口自动化测试（FastAPI 后端 + pytest + requests）
- **项目二（精简）**：博客系统 Web 冒烟测试（Selenium + POM）

---

## 目录结构
```
project/
├── requirements.txt            # 依赖清单
├── vendor/                     # 已安装依赖（pip --target，见下方说明）
├── run_tests.ps1               # 接口测试一键回归（Windows）
├── run_tests.sh                # 接口测试一键回归（Linux/macOS）
├── course_api/                 # 【项目一】选课系统后端
│   ├── main.py                 # FastAPI 应用（鉴权/选课/退课/容量/冲突/权限）
│   └── database.py             # DB 校验辅助（切 MySQL 说明）
├── api_tests/                  # 【项目一】接口自动化测试套件
│   ├── conftest.py             # 启动后端 + 数据隔离 + 报告钩子
│   ├── client.py               # HTTP 请求封装
│   ├── report_builder.py       # 自写 HTML 报告生成器
│   ├── utils/                  # 断言封装 + 数据库校验
│   └── test_*.py               # 鉴赏/选课/退课/冲突/容量/权限用例
├── web_smoke/                  # 【项目二】博客 Web 冒烟测试
│   ├── blog_app.py             # 博客 demo（纯标准库）
│   ├── pages/                  # POM 页面对象
│   ├── tests/                  # Selenium 冒烟用例
│   └── README.md               # 运行说明（需装 selenium）
├── docs/
│   ├── test_plan.md            # 测试计划（简版）
│   ├── testcases/              # 核心用例表 42 行（testcase_*.md，参数化执行 43 例）
│   └── defect_template.md      # 缺陷单模板
└── README.md                   # 本文档
```

---

## 环境说明
- 本机：Python 3.14.7 + pip 26。项目已通过 `pip install ... --target vendor/`
  将依赖安装到项目内 `vendor/`，**不污染系统、规避系统级写权限问题**。
- 启动/运行脚本会自动设置 `PYTHONPATH=vendor`，无需手动 pip install。

---

## 项目一：选课系统接口自动化测试

### 1. 启动后端
```powershell
cd course_api
# 方式 A：直接跑（依赖已在 vendor，需先设 PYTHONPATH）
$env:PYTHONPATH = "..\vendor"
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```
或（Windows，在项目根目录）：
```powershell
$env:PYTHONPATH = "$((Get-Location).Path)\vendor"
python -m uvicorn course_api.main:app --host 127.0.0.1 --port 8000
```
启动后访问 `http://127.0.0.1:8000/docs` 可看 Swagger 交互文档。

### 2. 运行接口测试（一键回归）
```powershell
# Windows
.\run_tests.ps1
```
```bash
# Linux/macOS/Windows Git Bash
bash run_tests.sh
```
> conftest 会自动启动后端子进程、按用例重建数据、生成 HTML 报告。

**实际运行结果（本机验证，2026-09 复验）**：
```
43 passed in 7.77s
```
报告生成于 `reports/report.html`（汇总卡含跳过数与通过率）。

### 3. 测试报告
- **默认（自写，零依赖）**：`reports/report.html` —— 单文件 HTML，
  含每个用例结果与耗时，失败用例附「期望/实际状态码 + 响应正文」的断言详情，便于缺陷定位。
- **可选 allure**（需先设 `PYTHONPATH`，PowerShell 示例；Git Bash 用 `PYTHONPATH=vendor python -m pytest ...`）：
  ```
  pip install allure-pytest
  $env:PYTHONPATH = "vendor"
  python -m pytest api_tests --alluredir=reports/allure-results
  allure serve reports/allure-results
  ```
- **可选 pytest-html**（同样先设 `$env:PYTHONPATH = "vendor"`）：
  ```
  pip install pytest-html
  python -m pytest api_tests --html=reports/report_pytest.html --self-contained-html
  ```

### 4. 切换 MySQL
`course_api/main.py` 顶部：
```python
DATABASE_URL = "mysql+pymysql://root:123456@127.0.0.1:3306/course_db?charset=utf8mb4"
```
并 `pip install pymysql`。其余 SQLAlchemy ORM 代码无需改动。

---

## 项目二：博客系统 Web 冒烟测试

详见 [`web_smoke/README.md`](web_smoke/README.md)。

**运行前提**：需安装 `pip install selenium` 且本机有 Chrome/Edge（Selenium Manager 自动下驱动）。
五条关键路径：登录 / 发布 / 搜索 / 编辑 / 删除，失败自动截图到 `screenshots/`。

---

## 用例与文档
- 测试计划：`docs/test_plan.md`
- 核心用例表：`docs/testcases/testcase_*.md`，共 42 行（鉴权 15 + 选课/退课 10 + 冲突 4 + 边界 5 + 权限 8），
  参数化展开后 pytest 实际执行 43 例
- 缺陷单模板：`docs/defect_template.md`

---

## 产品视角（面试可讲）

- **目标用户**：测试团队与后端开发——回归慢、越权用例易漏、报告靠手工整理。
- **解决的问题**：把核心业务回归做成"一键、可重复、有报告"的质量资产。
- **核心场景**：起被测系统 → 39 例接口回归（角色/权限/容量/冲突）→ HTML 报告与失败留证；Selenium 冒烟覆盖关键用户路径。
- **成功指标（实测）**：45 个测试函数全绿（本机）；失败截图与报告工件随仓。
- **未来计划**：CI 常态化（已接入 GitHub Actions）；容量边界与数据隔离专项；覆盖率门禁。
