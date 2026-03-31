import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from .config import CHINESE_FONT

# 註冊字體
pdfmetrics.registerFont(TTFont('Chinese', CHINESE_FONT))

def generate_pdf_report(filename, title, date, ffb, cpo, content):
    """產出 ReportLab 專業中文 PDF"""
    try:
        doc = SimpleDocTemplate(filename, pagesize=A4)
        styles = getSampleStyleSheet()
        p_s = ParagraphStyle('CN', fontName='Chinese', fontSize=12, leading=18, spaceAfter=10)
        t_s = ParagraphStyle('T', fontName='Chinese', fontSize=18, leading=24, alignment=1, spaceAfter=20)
        
        story = [Paragraph(title, t_s), Paragraph(f"日期: {date} | FFB: {ffb} | CPO: {cpo}", p_s), Spacer(1, 12)]
        
        # 清除 Markdown 符號
        clean_text = content.replace('#','').replace('*','').replace('`','')
        for line in clean_text.split('\n'):
            if line.strip(): story.append(Paragraph(line, p_s))
            
        doc.build(story)
        return True
    except Exception as e:
        print(f"PDF 產出失敗: {e}"); return False
