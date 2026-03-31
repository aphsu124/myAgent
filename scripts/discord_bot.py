import discord
import logging
import sys
import os
import subprocess
from discord.ext import commands
from dotenv import load_dotenv

# 日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s:%(levelname)s:%(name)s: %(message)s', stream=sys.stdout)
logger = logging.getLogger('discord')

# 載入 .env
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(base_dir, '.env'))
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

intents = discord.Intents.all() # 暴力開啟所有權限
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    logger.info(f'✅ Jarvis 已重新上線: {bot.user}')

@bot.event
async def on_message(message):
    if message.author == bot.user: return
    logger.info(f"📩 收到內容: [{message.content}] 來自: {message.author}")
    if "!日報" in message.content:
        await message.channel.send("📊 收到指令，開始執行...")
        subprocess.run(["python3", os.path.join(base_dir, "scripts/daily_palm_report.py")])
        await message.channel.send("✅ 完成！")
    elif "!ping" in message.content:
        await message.channel.send("🏓 Pong!")
    await bot.process_commands(message)

if __name__ == "__main__":
    # 使用 reconnect=True 確保斷線自動重連
    bot.run(TOKEN, reconnect=True)
