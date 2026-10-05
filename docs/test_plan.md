# 选课系统接口自动化测试 —— 测试计划（简版）

## 1. 目标与范围
- **目标**：验证「校园选课系统」后端接口在正常、异常、边界、越权四类场景下的正确性与数据一致性。
- **被测系统**：`course_api/main.py`（FastAPI + SQLAlchemy + SQLite，本地可运行）。
- **测试范围**：
  - 鉴权：注册 / 登录 / token 校验
  - 选课：校验角色、容量、重复、时间冲突
  - 退课：容量回滚、记录删除
  - 权限：学生 / 教师 / 管理员角色隔离（403 越权）
  - 数据库一致性：`enrollments` 记录与 `courses.enrolled` 容量联动
  - 并发容量：多线程并发选课不超卖（2026-09 新增，配套原子条件 UPDATE 修复）

## 2. 测试策略
| 维度 | 策略 |
|------|------|
| 测试框架 | pytest + requests（打真实 HTTP） |
| 被测端启动 | conftest 会话级启动 uvicorn 子进程，测试用 requests 访问 |
| 数据隔离 | 每个用例 autouse fixture 重建数据库种子数据，保证可重复执行 |
| 断言封装 | `utils/assertions.py`（状态码 / 业务错误 detail） |
| 数据库校验 | `utils/db_check.py`（绕过 HTTP 直查 SQLite，校验落库与容量变化） |
| 参数化 | 登录失败、角色注册、角色枚举等用 `@pytest.mark.parametrize` |

## 3. 测试环境
- Python 3.14、pytest 9.1、fastapi 0.141、sqlalchemy 2.0、requests 2.34
- 依赖已安装到项目 `vendor/`（避免污染全局、规避系统级权限问题）
- 数据库：SQLite（零外部依赖）；切 MySQL 仅改 `DATABASE_URL` + `pip install pymysql`

## 4. 用例概览（与 docs/testcases/ 对应，共 30+ 条核心）
- 鉴权：登录成功 / 密码错 / 用户不存在 / 空参 / 注册成功 / 重复注册 / 非法角色 / 无 token / 伪造 token
- 选课：成功(含 DB 校验) / 重复 / 课程不存在 / 容量已满 / 容量恰 1 席
- 退课：成功(含 DB 回滚) / 未选却退 / 重复退
- 时间冲突：完全重叠 / 部分重叠 / 相邻不冲突 / 跨用户不冲突
- 权限：教师选课 403 / 教师退课 403 / 学生访问管理 403 / 教师访问管理 403 / 学生建课 403 / 管理员访问 200 / 管理员建课 201 / 管理员选课 403
- 边界：capacity=0 422 / 结束时间早于开始 400

## 5. 执行与报告
- **一键回归**：`.\run_tests.ps1`（Windows）/ `bash run_tests.sh`（Linux）
- **报告**：
  - 默认自写单文件 HTML 报告 `reports/report.html`（含失败用例的断言详情；2026-09 起同时收录 fixture/teardown 阶段报错）
  - 可选接入 allure：`pip install allure-pytest`，运行 `pytest api_tests --alluredir=reports/allure-results` 后 `allure serve reports/allure-results`
  - 可选 pytest-html：`pip install pytest-html`，运行 `pytest api_tests --html=reports/report_pytest.html --self-contained-html`

## 6. 缺陷单模板
见 `docs/defect_template.md`。

## 7. 出口准则
- 全部核心用例通过（当前 43/43，含参数化展开与并发安全用例）
- 报告生成且可定位失败详情
- 数据一致性断言覆盖容量增减与选课记录增删