import discord
import os
import subprocess
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GUILD_ID = 1488194051214807132

class FinalJarvis(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.all())
        self.tree = discord.app_commands.CommandTree(self)

    async def setup_hook(self):
        guild = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)

    async def on_ready(self):
        print(f"🚀 [系統報告] 機器人 {self.user} 已完全接通網關。")
        print(f"📍 正在監聽伺服器: {GUILD_ID}")

    async def on_interaction(self, interaction):
        # 這是最底層的監聽，只要您按了按鈕，這裡一定會有反應
        print(f"🔔 [偵測到訊號] 動作類型: {interaction.type} | 來自用戶: {interaction.user}")
        if interaction.type == discord.InteractionType.application_command:
            command_name = interaction.data['name']
            print(f"🎯 指令名稱: {command_name}")
            
            if command_name == "ping":
                await interaction.response.send_message("✅ **Jarvis 收到！** 訊號傳輸正常。")
            elif command_name == "report":
                await interaction.response.send_message("📊 **啟動日報生成程式...**")
                subprocess.run(["python3", "scripts/daily_palm_report.py"])
                await interaction.followup.send("🏁 報告已發布！")

client = FinalJarvis()

if __name__ == "__main__":
    if TOKEN:
        print("--- 正在啟動最終除錯服務 ---")
        client.run(TOKEN)
    else:
        print("❌ 找不到 Token")
