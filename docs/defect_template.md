# 缺陷单模板（Bug Report Template）

> 复制下方模板填写，一份缺陷一张单。提交前确认「复现步骤」可独立复现。

---

## 缺陷标题
> 【模块】一句话描述现象（如：【选课】课程容量已满时仍返回 200 而非 409）

| 字段 | 内容 |
|------|------|
| **缺陷编号** | BUG-YYYYMMDD-XXX |
| **所属项目** | 选课系统接口自动化测试 |
| **模块** | 鉴权 / 选课 / 退课 / 时间冲突 / 权限 |
| **严重程度** | 致命 / 严重 / 一般 / 轻微 |
| **优先级** | P0 / P1 / P2 / P3 |
| **发现版本** | 如 v0.1 |
| **测试环境** | Python 3.14 / FastAPI 0.141 / SQLite |
| **报告人** | 姓名 |
| **报告日期** | YYYY-MM-DD |
| **指派给** | 开发负责人 |

---

## 复现步骤
1. 前置条件：...
2. 操作：...
3. 请求示例：
   ```
   POST /api/enroll
   { "course_id": 1 }
   Authorization: Bearer token-student
   ```

## 预期结果
> 如：返回 409，detail=「课程容量已满」

## 实际结果
> 如：返回 200，enrolled 变为 31（超出 capacity=30）

## 关联证据
- 请求/响应：
  ```
  状态码：xxx
  响应体：{...}
  ```
- 关联 SQL / 数据库状态：
  ```sql
  SELECT id, capacity, enrolled FROM courses WHERE id=1;
  -- course 1: capacity=30, enrolled=31  <-- 越界
  ```
- 截图 / 日志路径：
  `reports/report.html`

## 根本原因（开发填写）
> ...

## 修复方案（开发填写）
> ...

## 回归验证（测试填写）
- [ ] 缺陷已修复
- [ ] 回归用例：TC-ENROLL-09 通过
- 验证日期 / 验证人：