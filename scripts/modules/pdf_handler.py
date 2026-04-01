import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, KeepTogether, Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from .config import CHINESE_FONT

# 優先使用 Medium 版本以支援粗體 (Bold)
MEDIUM_FONT = '/System/Library/Fonts/STHeiti Medium.ttc'
pdfmetrics.registerFont(TTFont('Chinese', MEDIUM_FONT))

def generate_pdf_report(filename, title, date, ffb, cpo, content, table_data=None):
    """產出 ReportLab 專業中文 PDF (具備真正粗體效果)"""
    try:
        doc = SimpleDocTemplate(filename, pagesize=A4, rightMargin=45, leftMargin=45, topMargin=40, bottomMargin=40)
        
        # 定義樣式
        title_style = ParagraphStyle('T', fontName='Chinese', fontSize=22, leading=30, alignment=1, spaceAfter=25, textColor=colors.HexColor("#1A5276"))
        header_style = ParagraphStyle('H', fontName='Chinese', fontSize=11, leading=16, alignment=0, spaceAfter=5, textColor=colors.darkgrey)
        h1_style = ParagraphStyle('H1', fontName='Chinese', fontSize=15, leading=22, spaceBefore=12, spaceAfter=8, textColor=colors.HexColor("#2E86C1"))
        h2_style = ParagraphStyle('H2', fontName='Chinese', fontSize=12, leading=18, spaceBefore=10, spaceAfter=4, textColor=colors.HexColor("#333333"))
        body_style = ParagraphStyle('B', fontName='Chinese', fontSize=11, leading=17, spaceAfter=6)
        table_header_style = ParagraphStyle('TH', fontName='Chinese', fontSize=11, textColor=colors.HexColor("#1A5276"), leading=14)
        table_body_style = ParagraphStyle('TB', fontName='Chinese', fontSize=10, leading=14)
        
        story = [Paragraph(f"<b>{title}</b>", title_style)]
        
        # 標頭與橫線
        header_txt = f"報告日期: {date}" if ffb == "N/A" else f"報告日期: {date} | FFB: {ffb} | CPO: {cpo}"
        story.append(Paragraph(header_txt, header_style))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey, spaceAfter=15))

        lines = [l.strip() for l in content.split('\n') if l.strip()]
        temp_group = []
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # 處理大標題 (一、二...)
            if line.startswith('一、') or line.startswith('二、') or line.startswith('三、') or line.startswith('四、'):
                if temp_group: story.append(KeepTogether(temp_group)); temp_group = []
                story.append(Spacer(1, 8))
                story.append(Paragraph(f"<b>{line}</b>", h1_style))
                
                # 如果是「影像監控網部署規劃」且有表格數據，則插入表格
                if "影像監控網部署規劃" in line and table_data:
                    story.append(Paragraph(lines[i+1], body_style)) 
                    i += 1
                    
                    formatted_table = []
                    for row_idx, row in enumerate(table_data):
                        formatted_row = []
                        for col_idx, cell in enumerate(row):
                            style = table_header_style if row_idx == 0 else table_body_style
                            formatted_row.append(Paragraph(f"<b>{cell}</b>" if row_idx == 0 else cell, style))
                        formatted_table.append(formatted_row)

                    t = Table(formatted_table, colWidths=[110, 50, 310])
                    t.setStyle(TableStyle([
                        ('FONTNAME', (0,0), (-1,-1), 'Chinese'),
                        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#F2F4F4")),
                        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                        ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
                        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                        ('TOPPADDING', (0,0), (-1,-1), 6),
                    ]))
                    story.append(Spacer(1, 10))
                    story.append(t)
                    story.append(Spacer(1, 15))
                    while i + 1 < len(lines) and (lines[i+1].endswith('：') or lines[i+1].startswith('·') or lines[i+1].startswith('-')):
                        i += 1
            
            # 處理中標題 (1. 2. 3.) 與 帶冒號的小標
            elif line.startswith('1.') or line.startswith('2.') or line.startswith('3.') or line.endswith('：') or line.endswith(')：'):
                if temp_group: story.append(KeepTogether(temp_group)); temp_group = []
                temp_group.append(Paragraph(f"<b>{line}</b>", h2_style))
            
            # 處理內容
            else:
                clean_text = line.replace('-', '· ').replace('・', '· ').replace('•', '· ').replace('·', '· ')
                clean_text = clean_text.replace('#','').replace('*','').replace('`','')
                temp_group.append(Paragraph(clean_text, body_style))
            
            i += 1
        
        if temp_group: story.append(KeepTogether(temp_group))
            
        doc.build(story)
        return True
    except Exception as e:
        print(f"PDF 產出失敗: {e}"); return False
