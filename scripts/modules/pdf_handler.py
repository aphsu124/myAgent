import os
import re
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
        # 層次由大到小：報告大標題 > 章節標題(市場概覽/對本油廠) > 編號子項目(1.2.3.) > 內文
        h1_style = ParagraphStyle('H1', fontName='Chinese', fontSize=15, leading=22, spaceBefore=14, spaceAfter=8, textColor=colors.HexColor("#1A5276"))
        h2_style = ParagraphStyle('H2', fontName='Chinese', fontSize=13, leading=20, spaceBefore=14, spaceAfter=6, textColor=colors.HexColor("#2C3E50"))
        h3_style = ParagraphStyle('H3', fontName='Chinese', fontSize=11, leading=17, spaceBefore=8, spaceAfter=3, textColor=colors.HexColor("#444444"))
        body_style = ParagraphStyle('B', fontName='Chinese', fontSize=10, leading=15, spaceAfter=5, textColor=colors.black)
        body_indent_style = ParagraphStyle('BI', fontName='Chinese', fontSize=10, leading=15, spaceAfter=5, spaceBefore=0, leftIndent=16, textColor=colors.black)
        
        story = [Paragraph(f"<b>{html.escape(title)}</b>", t_s)]
        header_txt = f"報告日期: {date} | FFB: {ffb} | CPO: {cpo}" if ffb != "N/A" else f"報告日期: {date}"
        story.append(Paragraph(html.escape(header_txt), h_s))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey, spaceAfter=15))

        lines = content.split('\n')
        i = 0
        under_numbered_heading = False  # 追蹤是否在編號小節內文中
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

            # 先去除 ** 後再做判斷（AI 常以 **文字：** 格式輸出）
            line_clean = line.replace('**', '').replace('*', '').strip()

            # 2. 標題處理
            if line.startswith('## '):
                # 最高層：報告大區塊標題（## 前綴，藍色）
                under_numbered_heading = False
                txt = html.escape(line.replace('#', '').strip().rstrip('：').rstrip(':'))
                story.append(Paragraph(f"<b>{txt}</b>", h1_style))
            elif (line_clean.endswith('：') and len(line_clean) < 28) \
                    or line_clean.startswith('一、') or line_clean.startswith('二、') or line_clean.startswith('三、') \
                    or line_clean.startswith('四、') or line_clean.startswith('五、'):
                # 章節標題（市場概覽、一、二、三 等）：深色，去除 ：
                under_numbered_heading = False
                txt = line_clean.rstrip('：').rstrip(':')
                story.append(Paragraph(f"<b>{html.escape(txt)}</b>", h2_style))
            elif line.startswith('### '):
                # 編號子項目（1. 2. 3.）：比章節標題小，下方內文縮排
                under_numbered_heading = True
                content_part = line[4:].strip().replace('**', '').replace('*', '')
                split_match = re.search(r'^(.{2,20})[：:](.+)$', content_part)
                if split_match:
                    heading_txt = split_match.group(1).strip()
                    body_txt = split_match.group(2).strip().replace('*', '').replace('`', '')
                    story.append(Paragraph(f"<b>{html.escape(heading_txt)}</b>", h3_style))
                    story.append(Paragraph(html.escape(body_txt), body_indent_style))
                else:
                    txt = content_part.rstrip('：').rstrip(':')
                    story.append(Paragraph(f"<b>{html.escape(txt)}</b>", h3_style))

            # 3. 內文處理
            else:
                clean_txt = line
                if clean_txt.startswith('- '): clean_txt = '· ' + clean_txt[2:]
                elif clean_txt.startswith('・'): clean_txt = '· ' + clean_txt[1:]
                elif clean_txt.startswith('•'): clean_txt = '· ' + clean_txt[1:]
                clean_txt = clean_txt.replace('*', '').replace('`', '')
                # 編號小節底下的內文縮排，其餘正常排版
                cur_style = body_indent_style if under_numbered_heading else body_style
                story.append(Paragraph(html.escape(clean_txt), cur_style))
            
            i += 1
            
        doc.build(story)
        return True
    except Exception as e:
        print(f"PDF 產出失敗: {e}"); return False
