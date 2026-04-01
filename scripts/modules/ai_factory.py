import os
import anthropic
from openai import OpenAI
from google import genai
from dotenv import load_dotenv

load_dotenv()

class AIFactory:
    def __init__(self):
        self.gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"), http_options={'api_version': 'v1'})
        # 修正為實測成功的 Claude 4 系列名稱
        self.claude_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def ask_gemini(self, prompt):
        try:
            resp = self.gemini_client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
            return resp.text
        except Exception as e: return f"Gemini Error: {e}"

    def ask_claude(self, prompt):
        try:
            resp = self.claude_client.messages.create(
                model="claude-sonnet-4-6", # 這裡使用實測成功的名稱
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}]
            )
            return resp.content[0].text
        except Exception as e: return f"Claude Error: {e}"

    def ask_chatgpt(self, prompt):
        try:
            resp = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}]
            )
            return resp.choices[0].message.content
        except Exception as e: return f"ChatGPT Error: {e}"
