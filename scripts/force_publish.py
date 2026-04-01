import os
import markdown
import subprocess
from modules import config, pdf_handler, line_handler

# 讀取完整內容
with open("data/DEBUG_CONTENT.txt", "r") as f:
    content = f.read()

date_ds = "2026-04-01"
date_fn = "20260401"
title = "📰 泰國棕櫚油晨間新聞"
suffix = "M_report"

# 產出 PDF
pdf_path = os.path.join(config.ICLOUD_BASE, f"{date_fn}_{suffix}.pdf")
pdf_handler.generate_pdf_report(pdf_path, title, date_ds, "8.1", "45.5", content)

# 產出 HTML
html_body = markdown.markdown(content, extensions=['tables'])
web_content = f"<html><body style='background:#121212;color:#e0e0e0;padding:40px;font-family:sans-serif;'><h1>{title}</h1>{html_body}</body></html>"
html_path = os.path.join(config.REPORT_DIR, f"{date_fn}_{suffix}.html")

with open(html_path, "w") as f: f.write(web_content)
with open("docs/index.html", "w") as f: f.write(web_content)

# 同步
subprocess.run(["git", "add", "."], check=True)
subprocess.run(["git", "commit", "-m", "📊 Force Recover Morning Report"], check=True)
subprocess.run(["git", "push", "origin", "main"], check=True)

print("✅ 晨報救援內容已強制發布。")
