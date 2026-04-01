import os
import html
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from .config import CHINESE_FONT

# 註冊字體
MEDIUM_FONT = '/System/Library/Fonts/STHeiti Medium.ttc'
pdfmetrics.registerFont(TTFont('Chinese', MEDIUM_FONT))

def _convert_md_table_to_data(table_lines):
    """安全轉換 Markdown 表格"""
    data = []
    for line in table_lines:
        if '|' in line and '---' not in line:
            cells = [c.strip().replace('**', '') for c in line.split('|') if c.strip()]
            if cells: data.append(cells)
    return data

def generate_pdf_report(filename, title, date, ffb, cpo, content, table_data=None):
    """產出 PDF (精緻排版版：修正符號誤傷與換行)"""
    try:
        doc = SimpleDocTemplate(filename, pagesize=A4, rightMargin=45, leftMargin=45, topMargin=40, bottomMargin=40)
        
        # 樣式設定
        t_s = ParagraphStyle('T', fontName='Chinese', fontSize=22, leading=30, alignment=1, spaceAfter=20, textColor=colors.HexColor("#1A5276"))
        h_s = ParagraphStyle('H', fontName='Chinese', fontSize=11, leading=16, alignment=0, spaceAfter=5, textColor=colors.darkgrey)
        h1_style = ParagraphStyle('H1', fontName='Chinese', fontSize=15, leading=22, spaceBefore=12, spaceAfter=8, textColor=colors.HexColor("#2E86C1"))
        h2_style = ParagraphStyle('H2', fontName='Chinese', fontSize=12, leading=18, spaceBefore=8, spaceAfter=4, textColor=colors.black)
        body_style = ParagraphStyle('B', fontName='Chinese', fontSize=11, leading=17, spaceAfter=6)
        
        story = [Paragraph(f"<b>{html.escape(title)}</b>", t_s)]
        header_txt = f"報告日期: {date} | FFB: {ffb} | CPO: {cpo}" if ffb != "N/A" else f"報告日期: {date}"
        story.append(Paragraph(html.escape(header_txt), h_s))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey, spaceAfter=15))

        lines = content.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                story.append(Spacer(1, 8)); i += 1; continue
            
            # 1. 偵測表格
            if line.startswith('|') and i + 1 < len(lines) and '---' in lines[i+1]:
                table_lines = []
                while i < len(lines) and '|' in lines[i]:
                    table_lines.append(lines[i]); i += 1
                t_data = _convert_md_table_to_data(table_lines)
                if t_data:
                    t = Table(t_data, colWidths=[150, 100, 100])
                    t.setStyle(TableStyle([
                        ('FONTNAME', (0,0), (-1,-1), 'Chinese'),
                        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#F2F4F4")),
                        ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
                        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                        ('FONTSIZE', (0,0), (-1,-1), 10),
                    ]))
                    story.append(t); story.append(Spacer(1, 12))
                continue

            # 2. 標題處理
            if line.startswith('##') or line.startswith('一、') or line.startswith('二、') or line.startswith('三、'):
                txt = html.escape(line.replace('#', '').strip())
                story.append(Paragraph(f"<b>{txt}</b>", h1_style))
            elif line.startswith('1.') or line.startswith('2.') or line.startswith('3.') or line.startswith('4.') or (line.endswith('：') and len(line) < 30):
                story.append(Paragraph(f"<b>{html.escape(line)}</b>", h2_style))
            
            # 3. 內文處理 (精準替換行首符號，不影響行中橫線)
            else:
                clean_txt = line
                if clean_txt.startswith('- '): clean_txt = '· ' + clean_txt[2:]
                elif clean_txt.startswith('・'): clean_txt = '· ' + clean_txt[1:]
                elif clean_txt.startswith('•'): clean_txt = '· ' + clean_txt[1:]
                
                # 移除 Markdown 裝飾符
                clean_txt = clean_txt.replace('*', '').replace('`', '')
                story.append(Paragraph(html.escape(clean_txt), body_style))
            
            i += 1
            
        doc.build(story)
        return True
    except Exception as e:
        print(f"PDF 產出失敗: {e}"); return False
