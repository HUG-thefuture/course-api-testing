#!/usr/bin/env bash
# 选课系统接口自动化测试 —— 一键回归脚本 (Linux/macOS/Windows Git Bash)
# 用法：在项目根目录执行  bash run_tests.sh
set -e
Base="$(cd "$(dirname "$0")" && pwd)"

# 依赖默认走 project/vendor（conftest 会自动插入 sys.path，无需 PYTHONPATH）。
# 若已在虚拟环境装好依赖，可先 export USE_BUNDLED_VENDOR=0 改用当前环境。
# 由 conftest 创建临时数据库，不清理用户数据。

# 3. 运行 pytest（conftest 会自行启动后端；-p no:cacheprovider 避免缓存目录写失败）
echo "==> 运行接口自动化测试 ..."
# 兼容不同平台：Linux/macOS 用 python3；Windows（含 Git Bash）只有 python，
# 且 python3 可能是 Microsoft Store 的空壳别名（能找到但运行即报错），故逐个实测可用性
PY=""
for cand in python3 python; do
  if "$cand" -c "import sys" >/dev/null 2>&1; then PY="$cand"; break; fi
done
[ -n "$PY" ] || { echo "错误：未找到可用的 Python 解释器" >&2; exit 1; }
"$PY" -m pytest "$Base/api_tests" -v --tb=short -p no:cacheprovider

echo ""
echo "==> 完成。HTML 报告：$Base/reports/report.html"
