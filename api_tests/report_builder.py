# -*- coding: utf-8 -*-
"""HTML 测试报告生成器（自写，零第三方依赖）。

用法：
  1. pytest 运行时通过 conftest 的 hook 收集用例结果与失败详情；
  2. 本模块把收集结果渲染为单文件 HTML 报告，保存到 reports/ 目录。

失败详情包含：用例名、结果、耗时、以及断言失败消息（含期望/实际状态码与响应正文），
便于缺陷定位。也可选择接入 allure（见 docs/test_plan.md）。
"""
from __future__ import annotations

import html
from datetime import datetime
from pathlib import Path

REPORT_DIR = Path(__file__).resolve().parent.parent / "reports"


class ReportCollector:
    """会话级单例，收集测试结果。"""

    def __init__(self):
        self.results = []  # list[dict]

    def add(self, item: dict):
        self.results.append(item)

    def summary(self) -> dict:
        passed = sum(1 for r in self.results if r["outcome"] == "passed")
        # error（setup/teardown 阶段报错）同样计入失败，避免"退出码非 0 报告近全绿"
        failed = sum(1 for r in self.results if r["outcome"] in ("failed", "error"))
        skipped = sum(1 for r in self.results if r["outcome"] == "skipped")
        total = len(self.results)
        # 通过率以总收集数为分母（含 skipped）；空会话显示 N/A 防除零
        rate = f"{passed / total * 100:.1f}%" if total else "N/A"
        return {"total": total, "passed": passed, "failed": failed,
                "skipped": skipped, "pass_rate": rate}


collector = ReportCollector()


def _status_color(outcome: str) -> str:
    return {"passed": "#28a745", "failed": "#dc3545", "skipped": "#6c757d"}.get(outcome, "#ffc107")


def render_report(output_path: Path | None = None) -> Path:
    """渲染 HTML 报告，返回报告文件路径。"""
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    out = output_path or (REPORT_DIR / "report.html")
    s = collector.summary()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    rows = []
    for i, r in enumerate(collector.results, 1):
        detail = r.get("detail", "")
        detail_html = f'<pre class="detail">{html.escape(detail)}</pre>' if detail else ""
        rows.append(f"""
        <tr>
          <td>{i}</td>
          <td class="name">{html.escape(r.get("name", ""))}</td>
          <td><span class="badge" style="background:{_status_color(r['outcome'])}">{r['outcome']}</span></td>
          <td>{html.escape(str(r.get("duration", "")))}s</td>
          <td>{detail_html}</td>
        </tr>""")

    html_doc = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>选课系统接口自动化测试报告</title>
<style>
body{{font-family:-apple-system,'Segoe UI',Arial,sans-serif;margin:24px;color:#222}}
h1{{border-bottom:2px solid #333;padding-bottom:8px}}
.summary{{display:flex;gap:16px;margin:16px 0}}
.card{{padding:12px 20px;border-radius:8px;color:#fff;font-weight:600}}
table{{border-collapse:collapse;width:100%;margin-top:12px}}
th,td{{border:1px solid #ddd;padding:8px;text-align:left;font-size:13px;vertical-align:top}}
th{{background:#f5f5f5}}
.name{{font-family:monospace}}
.badge{{color:#fff;padding:2px 10px;border-radius:12px;font-size:12px}}
.detail{{white-space:pre-wrap;background:#fafafa;border-left:3px solid #dc3545;padding:6px;font-size:12px;margin:0;max-width:640px}}
</style></head><body>
<h1>选课系统接口自动化测试报告</h1>
<p>生成时间：{ts}</p>
<div class="summary">
  <div class="card" style="background:#333">总计 {s['total']}</div>
  <div class="card" style="background:#17a2b8">通过 {s['passed']}</div>
  <div class="card" style="background:#dc3545">失败 {s['failed']}</div>
  <div class="card" style="background:#6c757d">跳过 {s['skipped']}</div>
  <div class="card" style="background:#28a745">通过率 {s['pass_rate']}</div>
</div>
<table>
<thead><tr><th>#</th><th>用例</th><th>结果</th><th>耗时</th><th>失败详情(断言信息/响应正文)</th></tr></thead>
<tbody>{''.join(rows)}</tbody>
</table>
</body></html>"""

    out.write_text(html_doc, encoding="utf-8")
    return out


if __name__ == "__main__":
    # 独立运行：无结果时生成空报告示例
    p = render_report()
    print(f"报告已生成：{p}")