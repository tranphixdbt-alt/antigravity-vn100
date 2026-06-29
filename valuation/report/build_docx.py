"""
Word Builder module — Tạo tài liệu báo cáo MS Word (.docx) chuyên nghiệp bằng python-docx.
"""
import os
from typing import Dict, Any, List

def build_docx_report(
    data: Dict[str, Any], 
    proj_headers: List[str],
    proj_rows: List[Dict[str, Any]],
    chart_football_path: str = None,
    chart_heatmap_path: str = None,
    output_path: str = None
) -> bool:
    """
    Tạo tài liệu Word (.docx) từ dữ liệu định giá.
    """
    if output_path is None:
        return False
        
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    try:
        from docx import Document
        from docx.shared import Inches, Pt, RGBColor
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.oxml import OxmlElement, parse_xml
        from docx.oxml.ns import nsdecls, qn
        
        doc = Document()
        
        # 1. Header & Title
        title_p = doc.add_paragraph()
        title_run = title_p.add_run("BÁO CÁO PHÂN TÍCH & ĐỊNH GIÁ DOANH NGHIỆP")
        title_run.font.name = "Arial"
        title_run.font.size = Pt(20)
        title_run.font.bold = True
        title_run.font.color.rgb = RGBColor(15, 23, 42)
        title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        meta_p = doc.add_paragraph()
        meta_run = meta_p.add_run(
            f"Mã cổ phiếu: {data['ticker']} | Ngày lập: {data['date']} | Nhà phân tích: {data['analyst']}"
        )
        meta_run.font.name = "Arial"
        meta_run.font.size = Pt(10)
        meta_run.font.italic = True
        meta_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # 2. Khuyến nghị Card (Table 1 ô)
        rec_table = doc.add_table(rows=1, cols=1)
        rec_table.autofit = False
        rec_cell = rec_table.cell(0, 0)
        
        # Set background cell sang Slate
        shading_xml = f'<w:shd {nsdecls("w")} w:fill="F8FAFC"/>'
        rec_cell._tc.get_or_add_tcPr().append(parse_xml(shading_xml))
        
        # Viết nội dung trong card
        rec_p = rec_cell.paragraphs[0]
        rec_title_run = rec_p.add_run("KHUYẾN NGHỊ ĐẦU TƯ\n")
        rec_title_run.font.size = Pt(11)
        rec_title_run.font.bold = True
        rec_title_run.font.color.rgb = RGBColor(100, 116, 139)
        
        rec_val_run = rec_p.add_run(f"{data['recommendation']}\n")
        rec_val_run.font.size = Pt(28)
        rec_val_run.font.bold = True
        # Gán màu cho khuyến nghị
        rec_color_rgb = RGBColor(16, 185, 129) if data['recommendation'] == "MUA" else (RGBColor(245, 158, 11) if data['recommendation'] == "HOLD" else RGBColor(239, 68, 68))
        rec_val_run.font.color.rgb = rec_color_rgb
        
        target_run = rec_p.add_run(
            f"Giá mục tiêu hợp lý: {data['target_price']} VND (Upside: {data['upside']}%)\n"
            f"Thị giá hiện tại: {data['current_price']} VND"
        )
        target_run.font.size = Pt(12)
        target_run.font.color.rgb = RGBColor(15, 23, 42)
        
        # 3. Sections
        def add_section(text):
            p = doc.add_paragraph()
            r = p.add_run(text)
            r.font.size = Pt(14)
            r.font.bold = True
            r.font.color.rgb = RGBColor(15, 23, 42)
            p.paragraph_format.space_before = Pt(18)
            p.paragraph_format.space_after = Pt(6)

        # 2.5. AI Narrative
        if data.get("ai_narrative"):
            add_section("0. Tóm tắt Đầu tư (Executive Summary)")
            ai_text = data["ai_narrative"]
            # Basic markdown stripping for docx
            ai_text = ai_text.replace("**", "").replace("#", "")
            paragraphs = ai_text.split("\n\n")
            for para in paragraphs:
                if para.strip():
                    p = doc.add_paragraph(para.strip())
                    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            
        add_section("1. Tổng quan doanh nghiệp")
        doc.add_paragraph(
            f"Doanh nghiệp phân tích: {data['name']} (Ngành: {data['sector']}). "
            f"Cổ phiếu đang được giao dịch ở mức giá {data['current_price']} VND/cổ phiếu "
            f"với số lượng cổ phiếu lưu hành đạt {data['shares']} triệu cổ phiếu."
        )
        
        add_section("2. Phương pháp định giá")
        doc.add_paragraph(
            f"Báo cáo áp dụng mô hình định giá pha trộn bao gồm định giá nội tại "
            f"({data['weight_intrinsic']}% - {data['intrinsic_method']}) "
            f"và định giá so sánh multiples ({data['weight_relative']}% - {data['relative_method']})."
        )
        
        # Bảng pha trộn
        blend_table = doc.add_table(rows=4, cols=3)
        blend_table.style = 'Table Grid'
        
        headers = ["Phương pháp", "Trọng số", "Giá trị định giá (VND)"]
        for col_idx, text in enumerate(headers):
            blend_table.cell(0, col_idx).paragraphs[0].add_run(text).font.bold = True
            
        # Row 1
        blend_table.cell(1, 0).paragraphs[0].add_run(data['intrinsic_method'])
        blend_table.cell(1, 1).paragraphs[0].add_run(f"{data['weight_intrinsic']}%")
        blend_table.cell(1, 2).paragraphs[0].add_run(data['intrinsic_price'])
        
        # Row 2
        blend_table.cell(2, 0).paragraphs[0].add_run(data['relative_method'])
        blend_table.cell(2, 1).paragraphs[0].add_run(f"{data['weight_relative']}%")
        blend_table.cell(2, 2).paragraphs[0].add_run(data['relative_price'])
        
        # Row 3
        r3_c0 = blend_table.cell(3, 0).paragraphs[0].add_run("Giá mục tiêu Blended")
        r3_c0.font.bold = True
        r3_c1 = blend_table.cell(3, 1).paragraphs[0].add_run("100%")
        r3_c1.font.bold = True
        r3_c2 = blend_table.cell(3, 2).paragraphs[0].add_run(data['target_price'])
        r3_c2.font.bold = True
        
        # Chèn biểu đồ football field
        if chart_football_path and os.path.exists(chart_football_path):
            doc.add_paragraph().paragraph_format.space_before = Pt(12)
            doc.add_picture(chart_football_path, width=Inches(6))
            
        add_section("3. Bảng dự phóng tài chính chi tiết (5 năm)")
        
        # Bảng dự phóng
        proj_table = doc.add_table(rows=len(proj_rows) + 1, cols=len(proj_headers) + 1)
        proj_table.style = 'Table Grid'
        
        # Header
        proj_table.cell(0, 0).paragraphs[0].add_run("Chỉ tiêu (Tỷ VND)").font.bold = True
        for col_idx, h in enumerate(proj_headers):
            proj_table.cell(0, col_idx + 1).paragraphs[0].add_run(str(h)).font.bold = True
            
        # Data
        for row_idx, r in enumerate(proj_rows):
            proj_table.cell(row_idx + 1, 0).paragraphs[0].add_run(r["label"])
            for col_idx, val in enumerate(r["values"]):
                proj_table.cell(row_idx + 1, col_idx + 1).paragraphs[0].add_run(str(val))
                
        # Chèn biểu đồ heatmap độ nhạy
        if chart_heatmap_path and os.path.exists(chart_heatmap_path):
            add_section("4. Bảng phân tích độ nhạy 2 chiều")
            doc.add_picture(chart_heatmap_path, width=Inches(6.2))
            
        add_section("5. Ghi chú kịch bản & Luận điểm đầu tư")
        doc.add_paragraph(data.get("notes", "Không có ghi chú thêm."))
        
        # Footer disclaimer
        doc.add_paragraph().paragraph_format.space_before = Pt(30)
        footer_p = doc.add_paragraph()
        footer_r = footer_p.add_run(
            "Báo cáo được lập tự động bởi Hệ thống định giá VN100. "
            "Thông tin mang tính chất tham khảo, không cấu thành khuyến nghị giao dịch trực tiếp."
        )
        footer_r.font.size = Pt(8)
        footer_r.font.color.rgb = RGBColor(148, 163, 184)
        footer_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        doc.save(output_path)
        print(f"Word report created successfully at: {output_path}")
        return True
    except Exception as e:
        print(f"Error creating Word report: {e}")
        return False
