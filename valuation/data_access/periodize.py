"""
Periodize utility — Chuyển đổi dữ liệu quý sang năm.
Quy tắc:
- Flow items (Doanh thu, LNST, Chi phí...): cộng 4 quý (TTM) hoặc sum 4 quý cùng năm (FY).
- Stock items (Tài sản, Nợ, Vốn CSH...): lấy giá trị cuối kỳ của quý gần nhất.
"""
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import desc
from valuation.db.models import FinancialsQuarterly

# Danh sách phân loại các line_items thông dụng
# Mọi line_item chứa các từ khóa này sẽ được phân loại tương ứng.
# Mặc định nếu không match sẽ coi là Flow (cho an toàn) hoặc Stock tùy ngữ cảnh.
# Nhưng tốt nhất ta định nghĩa rõ ràng.

STOCK_KEYWORDS = [
    "tài sản", "vốn", "nợ", "cho vay", "tiền gửi", "tiền và", "đầu tư tài chính",
    "phải thu", "tồn kho", "phải trả", "assets", "equity", "loans", "deposits",
    "cash", "borrowings", "investments", "receivable", "inventories", "payable"
]

def is_stock_item(line_item: str, statement: Optional[str] = None) -> bool:
    """Kiểm tra line item là stock hay flow.

    Khi có loại báo cáo, dùng nó làm nguồn sự thật: BS là stock, IS/CF là
    flow. Keyword chỉ là fallback cho dữ liệu cũ chưa lưu ``statement``.
    """
    statement_code = (statement or "").strip().upper()
    if statement_code == "BS":
        return True
    if statement_code in {"IS", "CF"}:
        return False

    item_lower = line_item.lower()
    
    # Loại trừ một số khoản mục đặc thù của Lưu chuyển tiền tệ (Cash flow)
    # Vì chúng chứa từ "cash" hoặc "assets" nhưng lại là Flow item (cần được cộng dồn).
    if any(x in item_lower for x in [
        "cash_flow", "cash_inflow", "cash_outflow", "lưu chuyển", "payments",
        "purchases", "proceeds", "acquisition", "disposal", "tiền chi", "chi trả",
        "thu nhập",
    ]):
        return False
        
    for kw in STOCK_KEYWORDS:
        if kw in item_lower:
            return True
    return False

def get_latest_quarters_for_ticker(db: Session, ticker: str, limit: int = 4) -> List[Tuple[int, int]]:
    """Lấy danh sách các quý gần nhất có dữ liệu của ticker (bỏ qua Q0)."""
    rows = (
        db.query(
            FinancialsQuarterly.fiscal_year,
            FinancialsQuarterly.fiscal_quarter,
        )
        .filter(
            FinancialsQuarterly.ticker == ticker,
            FinancialsQuarterly.fiscal_quarter > 0,
        )
        .distinct()
        .order_by(
            desc(FinancialsQuarterly.fiscal_year),
            desc(FinancialsQuarterly.fiscal_quarter),
        )
        .limit(limit)
        .all()
    )
    return [(r[0], r[1]) for r in rows]

def periodize_quarters_to_annual(
    df_quarterly: pd.DataFrame, 
    target_year: int, 
    mode: str = "TTM", 
    latest_quarter: int = None
) -> Dict[str, float]:
    """
    Quy đổi dữ liệu quý sang năm cho một năm mục tiêu.
    df_quarterly: DataFrame có các cột ['fiscal_year', 'fiscal_quarter', 'line_item', 'value']
    mode: 'TTM' hoặc 'FY'
    target_year: Năm tài chính hoặc năm kết thúc TTM
    latest_quarter: Quý kết thúc TTM (chỉ dùng khi mode == 'TTM')
    
    Trả về Dict[line_item, value] đã được quy đổi.
    """
    if df_quarterly.empty:
        return {}

    # Lọc dữ liệu theo chế độ
    if mode == "FY":
        # Ưu tiên lấy dữ liệu đã được tính sẵn cho cả năm (Q0)
        df_fy = df_quarterly[(df_quarterly["fiscal_year"] == target_year) & (df_quarterly["fiscal_quarter"] == 0)]
        if not df_fy.empty:
            result = {}
            df_fy = df_fy.copy()
            df_fy["_restated_rank"] = (
                df_fy["is_restated"].fillna(False).astype(bool).astype(int)
                if "is_restated" in df_fy.columns
                else 0
            )
            df_fy["_published_rank"] = (
                pd.to_datetime(df_fy["published_at"], errors="coerce")
                if "published_at" in df_fy.columns
                else pd.NaT
            )
            df_fy = df_fy.sort_values(
                by=["line_item", "_restated_rank", "_published_rank"],
                ascending=[True, True, True],
                na_position="first",
            )
            rows = []
            for _, df_item in df_fy.groupby("line_item", sort=False):
                if "statement" in df_item.columns:
                    statements = {
                        str(value).strip().upper()
                        for value in df_item["statement"].dropna().unique()
                        if str(value).strip()
                    }
                    if len(statements) > 1:
                        statement = next(
                            code for code in ("BS", "IS", "CF") if code in statements
                        )
                        df_item = df_item[
                            df_item["statement"].astype(str).str.upper() == statement
                        ]
                rows.append(df_item.iloc[-1])
            df_fy = pd.DataFrame(rows)
            for _, r in df_fy.iterrows():
                val = r["value"]
                result[r["line_item"]] = float(val) if val is not None and not pd.isna(val) else 0.0
            return result
            
        # Fallback: Lấy cả 4 quý của năm target_year
        df_target = df_quarterly[df_quarterly["fiscal_year"] == target_year]
        # Bỏ qua Q0 nếu có
        df_target = df_target[df_target["fiscal_quarter"] > 0]
        quarters_in_period = [(target_year, q) for q in sorted(df_target["fiscal_quarter"].unique())]
        if not quarters_in_period:
            return {}
        latest_yr, latest_q = target_year, max(q for _, q in quarters_in_period)
    else:  # TTM
        # Nếu không truyền latest_quarter, tìm quý lớn nhất của target_year có trong df
        if latest_quarter is None:
            sub_year = df_quarterly[df_quarterly["fiscal_year"] == target_year]
            if not sub_year.empty:
                latest_q = sub_year["fiscal_quarter"].max()
            else:
                latest_q = 4
            latest_yr = target_year
        else:
            latest_yr = target_year
            latest_q = latest_quarter

        # Xác định 4 quý liên tiếp kết thúc tại (latest_yr, latest_q)
        quarters_in_period = []
        cy, cq = latest_yr, latest_q
        for _ in range(4):
            quarters_in_period.append((cy, cq))
            cq -= 1
            if cq == 0:
                cq = 4
                cy -= 1

    # Tạo tập hợp dữ liệu trong kỳ
    df_period = df_quarterly[
        df_quarterly.apply(
            lambda r: (int(r["fiscal_year"]), int(r["fiscal_quarter"])) in quarters_in_period, 
            axis=1
        )
    ]
    
    if df_period.empty:
        return {}

    result = {}
    # Lấy danh sách các khoản mục
    line_items = df_period["line_item"].unique()

    # Xác định số lượng quý thực tế tìm thấy trong period để làm trọng số cho Flow items
    # (Nếu thiếu quý thì annualize lên)
    actual_quarters_count = len(df_period[["fiscal_year", "fiscal_quarter"]].drop_duplicates())
    weight = 4.0 / actual_quarters_count if actual_quarters_count > 0 else 1.0

    for item in line_items:
        df_item = df_period[df_period["line_item"] == item]
        statement = None
        if "statement" in df_item.columns:
            statements = {
                str(value).strip().upper()
                for value in df_item["statement"].dropna().unique()
                if str(value).strip()
            }
            if len(statements) > 1:
                # Một số provider dùng cùng item_id cho BS và IS, điển hình
                # minority_interest. Chọn xác định theo ưu tiên BS > IS > CF
                # thay vì phụ thuộc thứ tự trả về của DB.
                statement = next(
                    code for code in ("BS", "IS", "CF") if code in statements
                )
                df_item = df_item[
                    df_item["statement"].astype(str).str.upper() == statement
                ]
            else:
                statement = next(iter(statements), None)

        # Cùng một kỳ có thể tồn tại cả bản ban đầu và bản đã soát xét/restated.
        # Chỉ giữ một dòng mỗi quý, ưu tiên bản restated rồi tới ngày công bố mới.
        df_item = df_item.copy()
        df_item["_restated_rank"] = (
            df_item["is_restated"].fillna(False).astype(bool).astype(int)
            if "is_restated" in df_item.columns
            else 0
        )
        df_item["_published_rank"] = (
            pd.to_datetime(df_item["published_at"], errors="coerce")
            if "published_at" in df_item.columns
            else pd.NaT
        )
        df_item = df_item.sort_values(
            by=[
                "fiscal_year",
                "fiscal_quarter",
                "_restated_rank",
                "_published_rank",
            ],
            ascending=[True, True, True, True],
            na_position="first",
        ).drop_duplicates(
            subset=["fiscal_year", "fiscal_quarter"], keep="last"
        )

        if is_stock_item(item, statement=statement):
            # Stock item: lấy giá trị của quý mới nhất trong kỳ
            # Sắp xếp theo year, quarter giảm dần
            df_sorted = df_item.sort_values(
                by=["fiscal_year", "fiscal_quarter"], 
                ascending=[False, False]
            )
            val = df_sorted.iloc[0]["value"]
            result[item] = float(val) if val is not None else 0.0
        else:
            # Flow item: cộng tổng 4 quý
            total = df_item["value"].sum()
            # Nếu thiếu quý, nhân trọng số annualize
            result[item] = float(total) * weight if total is not None else 0.0

    return result
