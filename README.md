# 本周可做

每周把公开信号收成一份付费专栏：一个小产品、谁付钱、做到哪一步停止。

出刊用 Cursor 里的 Grok 额度。页面只卖这份专栏，不转售模型接口。

```powershell
python -m briefmill fetch
python -m briefmill check
python -m briefmill render
python -m briefmill serve
```

浏览器打开 http://127.0.0.1:8765 。收款链接写在 `config.json` 的 `payment_url`，只接受 `https://`。

下一期按 `prompts/weekly.md` 写。来源快照在 `data/sources.json`。
