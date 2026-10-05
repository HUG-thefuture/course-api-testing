# -*- coding: utf-8 -*-
# 选课系统接口自动化测试 —— 一键回归脚本 (Windows PowerShell)
# 用法：在项目根目录执行  .\run_tests.ps1
$ErrorActionPreference = "Stop"
$Base = Split-Path -Parent $MyInvocation.MyCommand.Path

# 依赖默认走 project/vendor（conftest 会自动插入 sys.path，无需 PYTHONPATH）。
# 若已在虚拟环境装好依赖，可先 $env:USE_BUNDLED_VENDOR="0" 改用当前环境。
# 测试在临时库中执行，不删除手工 course.db 或历史报告。

# 3. 运行 pytest（conftest 会自行启动后端；-p no:cacheprovider 避免缓存目录写失败）
Write-Host "==> 运行接口自动化测试 ..."
python -m pytest "$Base\api_tests" -v --tb=short -p no:cacheprovider

Write-Host ""
Write-Host "==> 完成。HTML 报告：$Base\reports\report.html"

# 透传 pytest 退出码：失败时脚本必须非 0（2026-09 修复 CI 假绿）
exit $LASTEXITCODE
