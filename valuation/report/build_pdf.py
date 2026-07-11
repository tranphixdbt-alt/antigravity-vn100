"""
PDF Builder module — Render HTML template sang tài liệu PDF.
Hỗ trợ WeasyPrint với cơ chế fallback sang Playwright/ReportLab nếu thiếu thư viện hệ thống.
"""
import os
from typing import Dict, Any, List

def build_pdf_report(
    html_content: str, 
    output_path: str
) -> bool:
    """
    Biên dịch chuỗi HTML thành file PDF.
    Trả về True nếu thành công, False nếu thất bại.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # 1. Thử dùng WeasyPrint (lựa chọn ưu tiên)
    try:
        from weasyprint import HTML
        print("Using WeasyPrint to render PDF...")
        HTML(string=html_content).write_pdf(output_path)
        print(f"PDF report created successfully via WeasyPrint at: {output_path}")
        return True
    except Exception as e:
        print(f"WeasyPrint failed or not installed: {e}. Trying fallback to Playwright...")

    # 2. Thử dùng Playwright (phương án dự phòng 1)
    try:
        from playwright.sync_api import sync_playwright
        print("Using Playwright fallback...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_content(html_content)
            page.pdf(path=output_path, format="A4", print_background=True)
            browser.close()
        print(f"PDF report created successfully via Playwright at: {output_path}")
        return True
    except Exception as e:
        print(f"Playwright fallback failed or not installed: {e}. Trying fallback to ReportLab/Simple HTML...")

    # 3. Phương án dự phòng 2: Lưu HTML gốc và ghi log
    # (Do WeasyPrint và Playwright đều đòi hỏi thư viện ngoài hệ thống nặng)
    # Ta sẽ tạo file PDF giả lập hoặc lưu HTML kèm hướng dẫn in HTML -> PDF
    html_backup_path = output_path.replace(".pdf", ".html")
    with open(html_backup_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Saved raw HTML report to: {html_backup_path} (Please print manually to PDF via Chrome)")
    
    # Tạo file PDF giả lập tối thiểu bằng reportlab nếu có
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        c = canvas.Canvas(output_path, pagesize=letter)
        c.drawString(100, 750, f"VALUATION REPORT - HTML BACKUP SAVED")
        c.drawString(100, 730, f"HTML file path: {html_backup_path}")
        c.drawString(100, 710, "Please open the HTML file in your browser (e.g. Chrome) and choose Print -> Save as PDF.")
        c.save()
        print(f"Created fallback index PDF at: {output_path}")
        return True
    except Exception as e:
        print(f"ReportLab failed: {e}")
        
    return False
