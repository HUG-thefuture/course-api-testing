# -*- coding: utf-8 -*-
"""极简博客 Demo 后端（零第三方依赖，纯标准库 http.server）。

为「博客系统 Web 冒烟测试」提供本地可启动的被测页面，覆盖五条关键路径：
  登录 / 文章发布 / 搜索 / 编辑 / 删除。

启动：
  python blog_app.py  (默认 http://127.0.0.1:8001)

登录账号：admin / admin123  （内存中的固定用户）
"""
from __future__ import annotations

import html
import json
import re
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

PORT = 8001
posts = []          # list[dict] : {id, title, content}
_next_id = 1
SESSION = None      # 登录后存 username，简化鉴权（冒烟用途）


def seed():
    global _next_id
    if not posts:
        posts.append({"id": _next_id, "title": "欢迎使用博客", "content": "这是第一篇示例文章，欢迎！"}); _next_id += 1
        posts.append({"id": _next_id, "title": "测试开发入门", "content": "pytest、Selenium、接口自动化……"}); _next_id += 1


PAGE = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>博客 Demo</title>
<style>body{{font-family:sans-serif;margin:24px}} input,textarea,button{{margin:4px;padding:6px}} .post{{border:1px solid #ccc;padding:8px;margin:8px 0}}</style>
</head><body>
<h1>博客 Demo</h1>
<div id="auth">{auth}</div>
<div id="publish">{publish}</div>
<div id="search"><input id="q" placeholder="搜索标题"><button onclick="search()">搜索</button></div>
<div id="list">{list}</div>
<script>
function search(){{ var q=document.getElementById('q').value; location.href='/?q='+encodeURIComponent(q); }}
function del(id){{ if(confirm('确认删除?')) location.href='/delete?id='+id; }}
</script>
</body></html>"""


def render_page(q=None):
    auth = '<form method="post" action="/login">用户名<input name="username"><input name="password" type="password" placeholder="密码"><button>登录</button></form>' if not SESSION \
        else f'已登录：{SESSION} <a href="/logout">退出</a>'
    publish = '''<form method="post" action="/publish">
    <input id="title" name="title" placeholder="标题"><br>
    <textarea id="content" name="content" placeholder="内容"></textarea><br>
    <button id="publish-btn">发布</button></form>''' if SESSION else '<p>请先登录才能发布文章</p>'
    vis = [p for p in posts if (not q) or (q.lower() in p["title"].lower())]
    items = ""
    for p in vis:
        edit = f' <a href="/edit?id={p["id"]}">编辑</a> <a href="javascript:del({p["id"]})">删除</a>' if SESSION else ''
        # html.escape：标题/内容转义后再拼接，避免存储型 XSS（工程习惯展示）
        items += (f'<div class="post" id="post-{p["id"]}"><h3>{html.escape(p["title"])}</h3>'
                  f'<p>{html.escape(p["content"])}</p>{edit}</div>')
    return PAGE.format(auth=auth, publish=publish, list=items or '<p>无文章</p>')


def render_edit(pid):
    p = next((x for x in posts if x["id"] == pid), None)
    if not p:
        return '<h1>文章不存在</h1><a href="/">返回</a>'
    return f"""<h1>编辑文章</h1>
<form method="post" action="/update"><input type="hidden" name="id" value="{p['id']}">
标题<input id="title" name="title" value="{html.escape(p['title'])}"><br>
内容<textarea id="content" name="content">{html.escape(p['content'])}</textarea><br>
<button id="save-btn">保存</button></form><a href="/">返回</a>"""


class Handler(BaseHTTPRequestHandler):
    def _send(self, body, code=200, ctype="text/html; charset=utf-8"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body.encode("utf-8"))))
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def do_GET(self):
        global SESSION
        u = urlparse(self.path)
        if u.path == "/":
            q = parse_qs(u.query).get("q", [None])[0]
            self._send(render_page(q))
        elif u.path == "/edit":
            # 与 /publish /update 保持一致：编辑需登录态
            if not SESSION:
                self._send('<h1>未登录</h1>', 401); return
            pid = int(parse_qs(u.query).get("id", ["0"])[0])
            self._send(render_edit(pid))
        elif u.path == "/logout":
            SESSION = None
            self._send(render_page())
        elif u.path == "/delete":
            # 删除同理：未登录不允许删除文章
            if not SESSION:
                self._send('<h1>未登录</h1>', 401); return
            pid = int(parse_qs(u.query).get("id", ["0"])[0])
            global posts
            posts = [p for p in posts if p["id"] != pid]
            self._send(render_page())
        else:
            self._send("<h1>Not Found</h1>", 404)

    def do_POST(self):
        global SESSION, _next_id
        u = urlparse(self.path)
        n = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(n).decode("utf-8")
        params = parse_qs(body)
        if u.path == "/login":
            username = params.get("username", [""])[0]
            password = params.get("password", [""])[0]
            if username == "admin" and password == "admin123":
                SESSION = username
                self._send(render_page())
            else:
                self._send('<h1>登录失败</h1><a href="/">返回</a>', 401)
        elif u.path == "/publish":
            if not SESSION:
                self._send('<h1>未登录</h1>', 401); return
            posts.append({"id": _next_id, "title": params.get("title", [""])[0],
                          "content": params.get("content", [""])[0]}); _next_id += 1
            self._send(render_page())
        elif u.path == "/update":
            if not SESSION:
                self._send('<h1>未登录</h1>', 401); return
            pid = int(params.get("id", ["0"])[0])
            for p in posts:
                if p["id"] == pid:
                    p["title"] = params.get("title", [""])[0]
                    p["content"] = params.get("content", [""])[0]
            self._send(render_page())
        else:
            self._send("Not Found", 404)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    seed()
    print(f"博客 Demo 已启动: http://127.0.0.1:{PORT}  (账号 admin / admin123)")
    HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()