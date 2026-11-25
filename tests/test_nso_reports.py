"""D121: đọc CPI, bán lẻ, GDP từ báo cáo kinh tế – xã hội của Cục Thống kê. Không gọi mạng: trang giả viết theo
đúng mẫu câu của các bài tháng 6–10/2026 (số trong câu là số thật đã đối chiếu tradingeconomics 26/11/2026).
"""

import datetime as dt
import unicodedata

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from valuation.db.models import MacroSeries
from valuation.db.session import Base
from valuation.ingest import nso_reports as nso

LIST = "https://www.nso.gov.vn/bao-cao-tinh-hinh-kinh-te-xa-hoi-hang-thang/"
OCT = "https://www.nso.gov.vn/bai-top/2026/11/bao-cao-tinh-hinh-kinh-te-xa-hoi-thang-muoi-va-10-thang-nam-2026/"
Q3 = "https://www.nso.gov.vn/tin-tuc-thong-ke/2026/10/bao-cao-tinh-hinh-kinh-te-xa-hoi-quy-iii-va-9-thang-nam-2026/"
DEC = "https://www.nso.gov.vn/bai-top/2027/01/bao-cao-tinh-hinh-kinh-te-xa-hoi-thang-muoi-hai-va-nam-2026/"
CFG = nso.NsoConfig(
    list_url=LIST,
    reports_to_read=2,
    timeout_sec=5,
    sane_range_pct={
        "CPI_YOY": (-5.0, 30.0),
        "RETAIL_SALES_YOY": (-50.0, 90.0),
        "GDP_YOY": (-15.0, 25.0),
    },
)
PAGES = {
    LIST: f'<a href="{Q3}">quý III</a><a href="{OCT}">tháng Mười</a><a href="{OCT}">lặp</a>'
    '<a href="https://www.nso.gov.vn/wp-content/uploads/2020/10/favicon.png">x</a>',
    # Trang thật không ở dạng NFC → viết dạng NFD để kiểm bước chuẩn hóa
    OCT: unicodedata.normalize(
        "NFD",
        (
            "<p>Tổng mức bán lẻ hàng hóa và doanh thu dịch vụ tiêu dùng theo giá hiện hành tháng Mười ước đạt 695,5 "
            "nghìn tỷ đồng, tăng 1,0% so với tháng trước và tăng 14,7% so với cùng kỳ năm trước.</p>"
            "<p>Chỉ số giá tiêu dùng (CPI) tháng Mười tăng 0,20% so với tháng trước; tăng 4,41% so với tháng 12/2025 "
            "và tăng 5,09% so với cùng kỳ năm trước.</p>"
        ),
    ),
    Q3: (
        "<p>Tổng sản phẩm trong nước (GDP) quý III/2026 ước tính tăng 9,95% so với cùng kỳ năm trước, cao hơn "
        "mức tăng 8,15% của quý I và 8,81% của quý II.</p><p>Tổng mức bán lẻ hàng hóa và doanh thu dịch vụ tiêu "
        "dùng theo giá hiện hành tháng Chín năm 2026 ước đạt 690,6 nghìn tỷ đồng, tăng 1,7% so với tháng trước và "
        "tăng 14,1% so với cùng kỳ năm trước.</p><p>Chỉ số giá tiêu dùng (CPI ) tháng Chín tăng 0,62% so với tháng "
        "trước; tăng 4,20% so với tháng 12/2025 và tăng 5,08% so với cùng kỳ năm trước.</p>"
    ),
}


def test_parse_report_quarter_and_q2_wording():
    q2 = (
        "Tổng sản phẩm trong nước (GDP) quý II/2026 đạt mức tăng trưởng khá, với tốc độ tăng ước đạt 8,39% so với "
        "cùng kỳ năm trước [1] . Chỉ số giá tiêu dùng (CPI ) tháng Sáu giảm 0,39% so với tháng trước; tăng 3,21% "
        "so với tháng 12/2025 và tăng 4,69% so với cùng kỳ năm trước."
    )
    assert nso.parse_report(q2, 2026, 7) == [
        ("CPI_YOY", dt.date(2026, 6, 30), 4.69),
        ("GDP_YOY", dt.date(2026, 6, 30), 8.39),
    ]


def test_parse_report_december_published_next_year_and_negative_and_thousands():
    text = (
        "Tổng mức bán lẻ hàng hóa và doanh thu dịch vụ tiêu dùng theo giá hiện hành tháng Mười hai ước đạt "
        "1.005,2 nghìn tỷ đồng, tăng 2,0% so với tháng trước và tăng 12,3% so với cùng kỳ năm trước. Chỉ số giá "
        "tiêu dùng (CPI) tháng Mười hai giảm 0,10% so với tháng trước và giảm 0,50% so với cùng kỳ năm trước."
    )
    # bài tháng 12 đăng 01/2027 → kỳ là 12/2026; "tháng Mười hai" không bị đọc thành "tháng Mười"
    assert nso.parse_report(text, 2027, 1) == [
        ("CPI_YOY", dt.date(2026, 12, 31), -0.5),
        ("RETAIL_SALES_YOY", dt.date(2026, 12, 31), 12.3),
    ]
    assert nso.parse_report("Không có câu nào theo mẫu.", 2026, 11) == []


def test_report_links_newest_first_unique():
    assert nso.report_links(PAGES[LIST] + f'<a href="{DEC}">x</a>') == [
        (2027, 1, DEC),
        (2026, 11, OCT),
        (2026, 10, Q3),
    ]


@pytest.fixture
def mem_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    db.add_all(
        [
            MacroSeries(
                indicator_code="CPI_YOY",
                date=dt.date(2026, 9, 30),
                value=0.0508,
                source="nso.gov.vn",
            ),
            MacroSeries(
                indicator_code="GDP_YOY",
                date=dt.date(2026, 9, 30),
                value=0.0990,
                source="tay",
            ),  # số cũ khác
        ]
    )
    db.commit()
    yield db
    db.close()


def test_run_adds_only_new_periods_and_reports_revisions(mem_db):
    res = nso.run_nso_update(mem_db, fetch=PAGES.__getitem__, cfg=CFG)
    assert res["error"] is None and res["read"] == [OCT, Q3]
    assert res["points"] == [
        ("CPI_YOY", "2026-10-31", 0.0509),
        ("RETAIL_SALES_YOY", "2026-09-30", 0.141),
        ("RETAIL_SALES_YOY", "2026-10-31", 0.147),
    ]
    assert res["written"] == 3
    # GDP quý III đã có số khác trong DB → không ghi đè, chỉ báo
    assert res["revisions"] == [
        {"code": "GDP_YOY", "date": "2026-09-30", "db": 0.099, "nso": 0.0995, "url": Q3}
    ]
    assert (
        float(mem_db.query(MacroSeries).filter_by(indicator_code="GDP_YOY").one().value)
        == 0.099
    )
    again = nso.run_nso_update(
        mem_db, fetch=PAGES.__getitem__, cfg=CFG
    )  # chạy lại: không thêm gì
    assert again["points"] == [] and again["written"] == 0


def test_run_rejects_out_of_range_and_writes_nothing(mem_db):
    bad = dict(PAGES)
    bad[OCT] = PAGES[OCT].replace("5,09%", "50,9%")
    res = nso.run_nso_update(mem_db, fetch=bad.__getitem__, cfg=CFG)
    assert (
        res["error"] and "ngoài khoảng hợp lý" in res["error"] and res["written"] == 0
    )


def test_run_refuses_host_outside_allowlist(mem_db):
    cfg = nso.NsoConfig("https://evil.example/list", 2, 5, CFG.sane_range_pct)
    res = nso.run_nso_update(mem_db, fetch=lambda u: 1 / 0, cfg=cfg)
    assert res["error"] and "allowed_domains" in res["error"] and res["read"] == []
