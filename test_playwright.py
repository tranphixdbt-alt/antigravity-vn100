from playwright.sync_api import sync_playwright
import os
def test_pdf():
    try:
        print("Testing playwright pdf generation...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_content("<h1>Test</h1><p>This is a test PDF</p>")
            page.pdf(path="test_playwright.pdf", format="A4", print_background=True)
            browser.close()
        print("Success! File size:", os.path.getsize("test_playwright.pdf"))
    except Exception as e:
        print("Error:", e)
test_pdf()
