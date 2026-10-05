# 选课系统核心用例 —— 选课 / 退课（含数据库校验）

对应测试文件：`api_tests/test_enrollment.py`

| 编号 | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 对应测试函数 |
|------|---------|---------|---------|---------|-------------|
| TC-ENROLL-01 | 选课成功 + 落库 | 学生 token，课程3 空闲 | POST /api/enroll {3} | 200；DB 中 enrollments 新增 1 条；courses.enrolled +1 | test_enroll_success_and_db |
| TC-ENROLL-02 | 选课后查询我的课程 | 已选课程3 | GET /api/my-courses | 200，返回列表含课程3 | test_enroll_then_list_my_courses |
| TC-ENROLL-03 | 重复选课 | 已选课程3 | 再次 POST /api/enroll {3} | 409「已选过」；容量不变、记录仍 1 条 | test_enroll_duplicate |
| TC-ENROLL-04 | 选不存在的课程 | 学生 token | POST /api/enroll {99999} | 404「课程不存在」 | test_enroll_nonexistent_course |
| TC-ENROLL-05 | 重复选课不重复计数 | 已选课程3 | 重复选课被拒后查 DB | 记录仅 1 条，enrolled 不变 | test_enroll_duplicate_does_not_double_count |
| TC-ENROLL-06 | 退课成功 + 回滚 | 已选课程3 | POST /api/unenroll {3} | 200；记录删除；enrolled -1 | test_unenroll_success_and_db |
| TC-ENROLL-07 | 未选却退 | 未选课程3 | POST /api/unenroll {3} | 404「未选」 | test_unenroll_not_enrolled |
| TC-ENROLL-08 | 重复退课 | 已退课 | 再次退课 | 404 | test_unenroll_twice |
| TC-ENROLL-09 | 课程容量已满 | 课程1 (cap30/enrolled30) | POST /api/enroll {1} | 409「容量已满」 | test_enroll_capacity_full |
| TC-ENROLL-10 | 容量恰剩 1 席 | 课程2 (cap2) | 选 1 次后查 DB | enrolled==1（还剩 1 席） | test_enroll_capacity_exactly_one_seat |