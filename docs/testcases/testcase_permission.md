# 选课系统核心用例 —— 角色权限（越权 403）

对应测试文件：`api_tests/test_permission.py`

| 编号 | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 对应测试函数 |
|------|---------|---------|---------|---------|-------------|
| TC-PERM-01 | 教师不能选课 | 教师 token | POST /api/enroll {3} | 403 | test_teacher_cannot_enroll |
| TC-PERM-02 | 教师不能退课 | 教师 token | POST /api/unenroll {3} | 403 | test_teacher_cannot_unenroll |
| TC-PERM-03 | 学生访问管理统计 | 学生 token | GET /api/admin/stats | 403 | test_student_cannot_access_admin_stats |
| TC-PERM-04 | 教师访问管理统计 | 教师 token | GET /api/admin/stats | 403 | test_teacher_cannot_access_admin_stats |
| TC-PERM-05 | 学生创建课程 | 学生 token | POST /api/admin/courses | 403 | test_student_cannot_create_course |
| TC-PERM-06 | 管理员访问统计 | 管理员 token | GET /api/admin/stats | 200，含 users/courses | test_admin_can_access_stats |
| TC-PERM-07 | 管理员创建课程 | 管理员 token | POST /api/admin/courses | 201，enrolled=0 | test_admin_can_create_course |
| TC-PERM-08 | 管理员不能选课 | 管理员 token | POST /api/enroll {3} | 403（管理员≠学生） | test_admin_can_enroll |

---

## 用例汇总（30 条核心）

| 模块 | 条数 | 编号范围 |
|------|------|---------|
| 鉴权 | 11 | TC-AUTH-01 ~ 11 |
| 选课/退课 | 10 | TC-ENROLL-01 ~ 10 |
| 时间冲突 | 4 | TC-CONFLICT-01 ~ 04 |
| 边界(容量/参数) | 5 | TC-CAP-01 ~ 05 |
| 角色权限 | 8 | TC-PERM-01 ~ 08 |

合计 **42 条**（实际 pytest 收集 43 条，含参数化展开；2026-09 同步鉴权安全修复与并发用例）。