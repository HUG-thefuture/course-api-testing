# 选课系统核心用例 —— 鉴权（认证/注册/token）

对应测试文件：`api_tests/test_auth.py`
（2026-09 同步：token 改为随机不透明串、密码 PBKDF2 哈希落库、注册禁止自授 admin 角色并新增管理员授予端点）

| 编号 | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 对应测试函数 |
|------|---------|---------|---------|---------|-------------|
| TC-AUTH-01 | 登录成功 | 已注册用户 alice | POST /api/login {alice, pass123} | 200，返回 ≥32 位随机 token + role=student | test_login_success |
| TC-AUTH-02 | 密码错误 | 用户 alice 存在 | POST /api/login {alice, wrong} | 401，detail「用户名或密码错误」 | test_login_failure[alice-wrong] |
| TC-AUTH-03 | 用户不存在 | — | POST /api/login {nobody, pass123} | 401 | test_login_failure[nobody-pass123] |
| TC-AUTH-04 | 空用户名/密码 | — | POST /api/login {"",""} | 401 | test_login_failure[-] |
| TC-AUTH-05 | 空密码 | 用户 alice 存在 | POST /api/login {alice, ""} | 401 | test_login_failure[alice-] |
| TC-AUTH-06 | 注册成功 | — | POST /api/register {new_student_1, pass123, student} | 200（2xx），role=student | test_register_success |
| TC-AUTH-07 | 重复注册 | 用户 dup_user 已注册 | 再次注册同用户名 | 409，detail「用户名已存在」 | test_register_duplicate_username |
| TC-AUTH-08 | 注册允许的角色 | — | 分别注册 student/teacher | 均 200，role 与请求一致 | test_register_allowed_roles[student/teacher] |
| TC-AUTH-09 | 非法角色 | — | 注册 role=superuser | 400，detail「非法角色」 | test_register_invalid_role |
| TC-AUTH-10 | 无 token 调用 | 未携带 Authorization | POST /api/enroll {3} | 401 | test_enroll_without_token |
| TC-AUTH-11 | 伪造 token | 携带不存在的 token | POST /api/enroll {3} | 401，detail「无效或过期 token」 | test_enroll_with_bad_token |
| TC-AUTH-12 | 自注册 admin 被拒 | — | POST /api/register {self_admin, pass123, admin} | 403，detail「admin 角色需由管理员授予」 | test_register_admin_forbidden |
| TC-AUTH-13 | 管理员授予角色 | 种子 admin 登录 | PATCH /api/admin/users/{name}/role → teacher；学生调用同端点 | admin 调用 200 role=teacher；学生调用 403 | test_admin_grant_role |
| TC-AUTH-14 | 密码哈希落库 | 种子用户 alice 存在 | 直查 course.db users.password | 以 pbkdf2_sha256$ 开头，不含明文 | test_password_stored_hashed |
| TC-AUTH-15 | 旧版可预测 token 失效 | — | 携带 token-alice（旧版格式）调 POST /api/enroll | 401 | test_enroll_with_legacy_forgeable_token |
