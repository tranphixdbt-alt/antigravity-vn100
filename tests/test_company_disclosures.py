"""Tin công bố doanh nghiệp (D89): phân loại theo luật cố định, rút số từ văn bản, cảnh báo thiếu lịch, cache."""

from __future__ import annotations

import datetime as dt
from types import SimpleNamespace

import pytest

from valuation.analysis.company_disclosures import (
    classify_disclosure,
    describe_disclosure,
    disclosure_facts,
    uncalendared_payouts,
)
from valuation.ingest import company_disclosures as ingest

# Mẫu thật FPT (VCI news detail, 29/10/2026), rút gọn.
FPT_DIV = {
    "id": "a1",
    "title": "FPT chốt danh sách cổ đông tạm ứng cổ tức đợt 1/2026",
    "content": (
        "Công ty Cổ phần FPT (mã FPT) công bố Nghị quyết HĐQT số 02.10-2026 ngày 27/10/2026 về việc "
        "tạm ứng cổ tức đợt 1/2026. Theo đó, HĐQT FPT thông qua phương án tạm ứng cổ tức năm 2026 bằng "
        "tiền với tỷ lệ 10%/cổ phiếu (1 cổ phiếu nhận 1.000 đồng). Ngày chốt danh sách cổ đông là ngày "
        "30/11 và ngày thực hiện chi trả là 10/12/2026."
    ),
    "publish_time": "2026-10-29T07:35:00",
    "source": "VNE",
    "url": "https://vneconomy.vn/fpt-chot-danh-sach-co-dong-tam-ung-co-tuc-dot-12026.htm",
    "category": "Dividend",
}
FPT_HOSE = {
    "id": "a2",
    "title": "FPT: Quyết định về việc thay đổi đăng ký niêm yết",
    "content": "Tài liệu đính kèm 20261027FPTQDthaydoidangkyNYCP.pdf",
    "publish_time": "2026-10-28T18:16:00",
    "source": "HOSE",
    "url": "https://www.hsx.vn/vi/tin-tuc/fpt-quyet-dinh-ve-viec-thay-doi-dang-ky-niem-yet/2509009",
    "category": "AddS",
}


@pytest.mark.parametrize(
    ("title", "label"),
    [
        ("FPT chốt danh sách cổ đông tạm ứng cổ tức đợt 1/2026", "Cổ tức tiền"),
        (
            "FPT: Thông báo phát hành cổ phiếu để tăng vốn cổ phần từ NVCSH",
            "Cổ phiếu thưởng / cổ tức CP",
        ),
        (
            "ABC: Phát hành cổ phiếu để trả cổ tức năm 2025",
            "Cổ phiếu thưởng / cổ tức CP",
        ),
        ("ABC: Thông báo chào bán cổ phiếu cho cổ đông hiện hữu", "Quyền mua"),
        ("ABC: Phát hành cổ phiếu theo chương trình ESOP", "Phát hành thêm"),
        ("Nguyễn Văn A - Đăng kí Mua 428,368 FPT", "Lãnh đạo / cổ đông lớn giao dịch"),
        ("FPT: Kết quả kinh doanh 9 tháng năm 2026", "Kết quả kinh doanh"),
        ("FPT: Nghị quyết HĐQT số 01.10-2026 ngày 06/10/2026", "Quản trị / nhân sự"),
        ("FPT: Quyết định về việc thay đổi đăng ký niêm yết", "Thủ tục"),
        ("FPT: Giấy chứng nhận đăng ký doanh nghiệp thay đổi lần thứ 62", "Thủ tục"),
        ("FPT ký hợp đồng với đối tác Nhật", "Khác"),
    ],
)
def test_classify_by_title(title: str, label: str) -> None:
    assert classify_disclosure(title)[0] == label


def test_facts_from_fpt_dividend_text_checked_by_hand() -> None:
    # Tính tay từ văn bản: 1.000 đ/cp, tỷ lệ 10%, chốt 30/11 (năm theo ngày đăng tin 2026), trả 10/12/2026.
    facts = disclosure_facts(FPT_DIV["content"], published=dt.date(2026, 10, 29))
    assert facts == {
        "cash_vnd_per_share": 1000.0,
        "ratio_pct": 10.0,
        "record_date": dt.date(2026, 11, 30),
        "payment_date": dt.date(2026, 12, 10),
    }


def test_record_date_without_year_rolls_to_next_year() -> None:
    facts = disclosure_facts(
        "Ngày chốt danh sách cổ đông là ngày 05/01.", published=dt.date(2026, 12, 20)
    )
    assert facts["record_date"] == dt.date(2027, 1, 5)


def test_describe_official_shows_full_text_press_only_excerpt() -> None:
    hose = describe_disclosure(FPT_HOSE, press_excerpt_chars=60)
    assert hose["official"] is True and hose["label"] == "Thủ tục"
    assert hose["attachments"] == ["20261027FPTQDthaydoidangkyNYCP.pdf"]
    assert hose["url"].startswith("https://www.hsx.vn/")
    press = describe_disclosure(FPT_DIV, press_excerpt_chars=60)
    assert press["official"] is False
    assert len(press["body"]) <= 61  # đoạn đầu + "…": không đăng lại nguyên bài báo
    assert (
        press["summary"] == "1.000 đ/cp · tỷ lệ 10% · chốt 30/11/2026 · trả 10/12/2026"
    )


def test_unsafe_link_dropped() -> None:
    assert (
        describe_disclosure({**FPT_HOSE, "url": "javascript:alert(1)"}, 60)["url"]
        is None
    )


def _ca(event_type: str, record: dt.date | None, announced: dt.date) -> SimpleNamespace:
    return SimpleNamespace(
        event_type=event_type,
        record_date=record,
        ex_right_date=None,
        announcement_date=announced,
    )


def test_alert_when_dividend_news_missing_from_calendar() -> None:
    today = dt.date(2026, 11, 4)
    rows = [_ca("BONUS_SHARE", dt.date(2026, 9, 22), dt.date(2026, 9, 16))]
    alerts = uncalendared_payouts([FPT_DIV, FPT_HOSE], rows, today=today, alert_days=45)
    assert [(a["label"], a["record_date"]) for a in alerts] == [
        ("Cổ tức tiền", dt.date(2026, 11, 30))
    ]


def test_no_alert_when_calendar_has_same_record_date_or_news_old() -> None:
    today = dt.date(2026, 11, 4)
    rows = [_ca("CASH_DIVIDEND", dt.date(2026, 11, 30), dt.date(2026, 10, 27))]
    assert uncalendared_payouts([FPT_DIV], rows, today=today, alert_days=45) == []
    assert (
        uncalendared_payouts([FPT_DIV], [], today=dt.date(2027, 1, 30), alert_days=45)
        == []
    )


def test_refresh_writes_cache_and_respects_ttl(tmp_path) -> None:
    calls = []

    def fetcher(ticker, *, days, limit):
        calls.append(ticker)
        return [FPT_HOSE, FPT_DIV]

    now = dt.datetime(2026, 11, 4, 9, 0)
    first = ingest.refresh_disclosures("FPT", now=now, fetcher=fetcher, store=tmp_path)
    assert first["status"] == "OK" and first["seen"] == 2
    cached = ingest.load_cached_disclosures("FPT", store=tmp_path)
    assert [i["id"] for i in cached["items"]] == ["a1", "a2"]  # mới nhất lên đầu
    again = ingest.refresh_disclosures(
        "FPT", now=now + dt.timedelta(hours=1), fetcher=fetcher, store=tmp_path
    )
    assert again["status"] == "FRESH" and calls == ["FPT"]


def test_refresh_retries_once_then_keeps_old_cache_on_error(tmp_path) -> None:
    attempts = iter([ConnectionError("timeout"), [FPT_HOSE]])

    def flaky(ticker, *, days, limit):
        result = next(attempts)
        if isinstance(result, Exception):
            raise result
        return result

    now = dt.datetime(2026, 11, 4, 9, 0)
    assert (
        ingest.refresh_disclosures("FPT", now=now, fetcher=flaky, store=tmp_path)[
            "status"
        ]
        == "OK"
    )

    def down(ticker, *, days, limit):
        raise ConnectionError("timeout")

    later = now + dt.timedelta(days=2)
    result = ingest.refresh_disclosures("FPT", now=later, fetcher=down, store=tmp_path)
    assert result == {"status": "ERROR", "checked": True, "error": "ConnectionError"}
    cached = ingest.load_cached_disclosures("FPT", store=tmp_path)
    assert [i["id"] for i in cached["items"]] == ["a2"] and cached[
        "error"
    ] == "ConnectionError"
    # Vừa lỗi → chưa gọi lại trong error_retry_minutes (tránh mỗi lần rerun lại gọi VCI).
    assert (
        ingest.disclosures_stale(
            "FPT", now=later + dt.timedelta(minutes=5), store=tmp_path
        )
        is False
    )


def test_invalid_ticker_rejected(tmp_path) -> None:
    with pytest.raises(ValueError):
        ingest.load_cached_disclosures("../etc", store=tmp_path)


def test_market_price_in_bonus_article_not_shown_as_cash_payout() -> None:
    # Bài báo thật 10/09/2026: "90.300 đồng/cổ phiếu" là giá đóng cửa, không phải tiền chia.
    item = {
        **FPT_DIV,
        "title": "FPT phát hành 171 triệu cổ phiếu thưởng, vốn điều lệ tăng mạnh",
        "content": "Tỷ lệ 10%. Chốt phiên, cổ phiếu FPT đóng cửa ở 90.300 đồng/cổ phiếu.",
        "publish_time": "2026-09-10T15:34:00",
    }
    view = describe_disclosure(item, press_excerpt_chars=400)
    assert view["label"] == "Cổ phiếu thưởng / cổ tức CP"
    assert view["summary"] == "tỷ lệ 10%"
