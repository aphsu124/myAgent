import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, KeepTogether, Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from .config import CHINESE_FONT

# 優先使用 Medium 版本以支援粗體
MEDIUM_FONT = '/System/Library/Fonts/STHeiti Medium.ttc'
pdfmetrics.registerFont(TTFont('Chinese', MEDIUM_FONT))

def _convert_md_table_to_data(lines):
    """將 Markdown 格式的表格行轉換為 Table 數據列表"""
    data = []
    for line in lines:
        if '|' in line and '---' not in line:
            cells = [c.strip().replace('**', '') for c in line.split('|') if c.strip()]
            if cells: data.append(cells)
    return data

def generate_pdf_report(filename, title, date, ffb, cpo, content, table_data=None):
    """產出專業 PDF (支援自動識別 Markdown 表格與強力格式化)"""
    try:
        doc = SimpleDocTemplate(filename, pagesize=A4, rightMargin=45, leftMargin=45, topMargin=40, bottomMargin=40)
        
        title_style = ParagraphStyle('T', fontName='Chinese', fontSize=22, leading=30, alignment=1, spaceAfter=25, textColor=colors.HexColor("#1A5276"))
        header_style = ParagraphStyle('H', fontName='Chinese', fontSize=11, leading=16, alignment=0, spaceAfter=5, textColor=colors.darkgrey)
        h1_style = ParagraphStyle('H1', fontName='Chinese', fontSize=15, leading=22, spaceBefore=12, spaceAfter=8, textColor=colors.HexColor("#2E86C1"))
        h2_style = ParagraphStyle('H2', fontName='Chinese', fontSize=12, leading=18, spaceBefore=10, spaceAfter=4, textColor=colors.black)
        body_style = ParagraphStyle('B', fontName='Chinese', fontSize=11, leading=17, spaceAfter=6)
        
        story = [Paragraph(f"<b>{title}</b>", title_style)]
        
        # 標頭資訊
        header_txt = f"報告日期: {date}" if ffb == "N/A" else f"報告日期: {date} | FFB: {ffb} | CPO: {cpo}"
        story.append(Paragraph(header_txt, header_style))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey, spaceAfter=15))

        lines = [l.strip() for l in content.split('\n') if l.strip()]
        temp_group = []
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # 偵測並處理 Markdown 表格 (如數據快報)
            if line.startswith('|') and i + 1 < len(lines) and '| ---' in lines[i+1]:
                if temp_group: story.append(KeepTogether(temp_group)); temp_group = []
                
                # 收集表格行
                table_lines = []
                while i < len(lines) and '|' in lines[i]:
                    if '---' not in lines[i]: table_lines.append(lines[i])
                    i += 1
                
                t_data = _convert_md_table_to_data(table_lines)
                if t_data:
                    t = Table(t_data, colWidths=[150, 100, 100])
                    t.setStyle(TableStyle([
                        ('FONTNAME', (0,0), (-1,-1), 'Chinese'),
                        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#F2F4F4")),
                        ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
                        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                    ]))
                    story.append(t); story.append(Spacer(1, 15))
                continue

            # 處理大標題
            if line.startswith('一、') or line.startswith('二、') or line.startswith('三、') or line.startswith('四、') or line.startswith('##'):
                if temp_group: story.append(KeepTogether(temp_group)); temp_group = []
                clean_line = line.replace('#', '').strip()
                story.append(Paragraph(f"<b>{clean_line}</b>", h1_style))
            
            # 處理中標題
            elif line.startswith('1.') or line.startswith('2.') or line.startswith('3.') or line.endswith('：'):
                if temp_group: story.append(KeepTogether(temp_group)); temp_group = []
                story.append(Paragraph(f"<b>{line}</b>", h2_style))
            
            # 處理內容
            else:
                clean_text = line.replace('-', '· ').replace('・', '· ').replace('•', '· ').replace('·', '· ')
                clean_text = clean_text.replace('#','').replace('*','').replace('`','')
                temp_group.append(Paragraph(clean_text, body_style))
            i += 1
            
        if temp_group: story.append(KeepTogether(temp_group))
        
        # 處理尾部傳入的特定 table_data (如攝影機部署)
        if table_data:
            story.append(Spacer(1, 15))
            t = Table(table_data, colWidths=[100, 50, 320])
            t.setStyle(TableStyle([('FONTNAME', (0,0), (-1,-1), 'Chinese'), ('GRID', (0,0), (-1,-1), 0.5, colors.grey)]))
            story.append(t)

        doc.build(story)
        return True
    except Exception as e:
        print(f"PDF 產出失敗: {e}"); return False
