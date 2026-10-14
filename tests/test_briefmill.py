import json
import tempfile
import unittest
from pathlib import Path

from briefmill.issues import load_issue, validate
from briefmill.render import render_inline, render_markdown, render_site


ISSUE = """---
date: 2026-10-14
title: 样本标题
summary: 样本摘要
product: 样本产品
---

## 信号

- 一条 [来源](https://example.com/a)

## 本周产品

做一个小东西。

## 谁付钱

会导出表格的人。

## 最小范围

- 导入文件
- 回答合计

## 不做什么

不登录银行。

## 定价

69 元一次。

## 来源

- <script>alert(1)</script>
"""


class RenderTests(unittest.TestCase):
    def test_inline_escapes_html_and_keeps_links(self):
        html = render_inline("见 [例子](https://example.com/a) 与 <b>")
        self.assertIn('<a href="https://example.com/a">例子</a>', html)
        self.assertIn("&lt;b&gt;", html)
        self.assertNotIn("<b>", html)

    def test_markdown_list_and_heading(self):
        html = render_markdown("## 信号\n\n- 第一项\n")
        self.assertIn("<h3>信号</h3>", html)
        self.assertIn("<li>第一项</li>", html)

    def test_site_rejects_missing_section_and_renders_valid_issue(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "issues").mkdir()
            (root / "config.json").write_text(
                json.dumps({"product_name": "本周可做", "payment_url": "https://xiaobot.net/p/example"}),
                encoding="utf-8",
            )
            path = root / "issues" / "2026-10-14.md"
            path.write_text(ISSUE, encoding="utf-8")
            broken = load_issue(path)
            broken_body = broken.body.replace("## 定价\n\n69 元一次。\n", "")
            path.write_text(ISSUE.replace("## 定价\n\n69 元一次。\n", ""), encoding="utf-8")
            with self.assertRaises(ValueError):
                validate(load_issue(path))
            path.write_text(ISSUE, encoding="utf-8")
            home = render_site(root)
            page = home.read_text(encoding="utf-8")
            self.assertIn("样本标题", page)
            self.assertIn("https://xiaobot.net/p/example", page)
            self.assertIn("&lt;script&gt;", page)
            self.assertNotIn("<script>alert", page)
            self.assertIn("本周产品：样本产品", page)
            self.assertTrue(broken_body)


if __name__ == "__main__":
    unittest.main()
