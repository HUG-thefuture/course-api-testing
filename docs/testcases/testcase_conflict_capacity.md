# 选课系统核心用例 —— 时间冲突

对应测试文件：`api_tests/test_conflict.py`

| 编号 | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 对应测试函数 |
|------|---------|---------|---------|---------|-------------|
| TC-CONFLICT-01 | 时段完全重叠 | 已选课程2(9-10点) | 选同时段课程(9-10点) | 409「冲突」 | test_enroll_time_conflict |
| TC-CONFLICT-02 | 时段部分重叠 | 已选课程2(9-10点) | 选 9:30-10:30 课程 | 409「冲突」 | test_enroll_partial_overlap |
| TC-CONFLICT-03 | 相邻不重叠 | 已选课程2(9-10点) | 选 10:00-11:00 课程 | 200 选课成功 | test_enroll_no_conflict_adjacent |
| TC-CONFLICT-04 | 跨用户不冲突 | 学生未选其他课 | 直接选 9-10 点课程 | 200（冲突仅针对同一学生） | test_enroll_same_time_no_conflict_across_users |

## 边界（容量 / 参数校验）

对应测试文件：`api_tests/test_capacity.py`

| 编号 | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 对应测试函数 |
|------|---------|---------|---------|---------|-------------|
| TC-CAP-01 | capacity=1 首位选满 | 管理员建 capacity=1 课程 | 第一名学生选课 | 200，DB enrolled==1 | test_capacity_one_first_seat_full_after |
| TC-CAP-02 | capacity=1 第二人被拒 | 已被第一人占满 | 第二名学生选课 | 409「容量已满」 | test_capacity_one_second_student_rejected |
| TC-CAP-03 | capacity=0 非法 | 管理员 token | 建 capacity=0 课程 | 422（pydantic 校验） | test_capacity_zero_rejected |
| TC-CAP-04 | 结束早于开始 | 管理员 token | 建课 end < start | 400 | test_create_course_invalid_time_range |
| TC-CAP-05 | 并发选课不超卖 | capacity=1 课程 | 8 线程并发抢选 | 恰 1 个成功、7 个 409，DB enrolled==1 | test_concurrent_enroll_no_oversell |