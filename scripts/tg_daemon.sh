#!/bin/bash
# Jarvis Telegram 暴力守護腳本
echo "🚀 啟動 Jarvis 暴力守護模式..."
while true
do
    python3 scripts/tg_worker.py
    # 每 3 秒強制重新發起一次連線
    sleep 3
done
