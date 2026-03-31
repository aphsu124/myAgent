#!/bin/bash
echo "🚀 啟動 Jarvis 守護進程 (每 5 秒硬重啟一次)..."
while true
do
    # 執行一次 Python 任務
    python3 scripts/telegram_single.py
    # 休息 5 秒後重啟
    sleep 5
done
