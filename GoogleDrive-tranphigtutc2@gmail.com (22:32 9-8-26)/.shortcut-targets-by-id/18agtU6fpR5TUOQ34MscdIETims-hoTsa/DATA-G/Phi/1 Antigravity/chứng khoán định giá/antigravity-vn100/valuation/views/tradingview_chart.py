"""Component hiển thị biểu đồ TradingView Advanced Chart với đầy đủ công cụ vẽ kỹ thuật & chỉ báo.
"""
import streamlit.components.v1 as components
import streamlit as st


def get_clean_ticker(ticker: str) -> str:
    """Loại bỏ tiền tố sàn nếu có để lấy mã cổ phiếu gốc."""
    t = str(ticker).upper().strip()
    if ":" in t:
        return t.split(":")[-1]
    return t


def render_tradingview_widget(ticker: str, height: int = 700, theme: str = "dark", key_suffix: str = "") -> None:
    """Render Biểu đồ Kỹ thuật Interactive.
    
    ĐỔI CÁCH LÀM: Sử dụng Native Plotly thay vì iframe nhúng TradingView.
    - Plotly tích hợp sẵn Candlestick + Khối lượng + MA20 + RSI(14).
    - Cấu hình ModeBar hỗ trợ các công cụ vẽ (drawline, drawrect, eraseshape) y như TradingView.
    - Tránh hoàn toàn 100% lỗi bản quyền, lỗi cross-origin iframe từ trình duyệt.
    """
    clean_ticker = get_clean_ticker(ticker)
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"📌 Phân tích kỹ thuật: **`{clean_ticker}`** *(Nền tảng Tự thân Không phụ thuộc Iframe)*")
    with col2:
        widget_key = f"tv_sym_input_{clean_ticker}_{height}_{key_suffix}" if key_suffix else f"tv_sym_input_{clean_ticker}_{height}"
        custom_ticker = st.text_input("Đổi mã cổ phiếu:", value=clean_ticker, key=widget_key)
        if custom_ticker:
            clean_ticker = custom_ticker.strip().upper()

    with st.spinner("Đang tải dữ liệu giá lịch sử từ vnstock..."):
        try:
            import pandas as pd
            from datetime import datetime, timedelta
            from vnstock_data.explorer.asean.quote import Quote
            import plotly.graph_objects as go
            from plotly.subplots import make_subplots
            
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
            q = Quote(symbol=clean_ticker)
            df = q.history(start=start_date, to_df=True)
            
            if df is None or df.empty:
                st.error(f"Không lấy được dữ liệu lịch sử cho mã {clean_ticker}.")
                return
                
            # Đảm bảo index datetime
            df['time'] = pd.to_datetime(df['time'])
            df.sort_values('time', inplace=True)
            
            # Tính MA20
            df['MA20'] = df['close'].rolling(window=20).mean()
            
            # Tính RSI 14
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))

            # Tính MACD (12, 26, 9)
            exp1 = df['close'].ewm(span=12, adjust=False).mean()
            exp2 = df['close'].ewm(span=26, adjust=False).mean()
            df['MACD'] = exp1 - exp2
            df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
            df['MACD_Hist'] = df['MACD'] - df['Signal']

            # Tạo Plotly figure (3 hàng: Nến+MA, Volume+MACD, RSI)
            fig = make_subplots(
                rows=4, cols=1, shared_xaxes=True, 
                vertical_spacing=0.03, subplot_titles=(f'Giá & MA20', 'Khối lượng', 'MACD', 'RSI (14)'),
                row_width=[0.15, 0.15, 0.2, 0.5]
            )
            
            # Row 1: Candlestick & MA20
            fig.add_trace(go.Candlestick(
                x=df['time'], open=df['open'], high=df['high'], low=df['low'], close=df['close'],
                name="Giá"
            ), row=1, col=1)
            
            fig.add_trace(go.Scatter(
                x=df['time'], y=df['MA20'], line=dict(color='orange', width=1.5), name="MA20"
            ), row=1, col=1)
            
            # Row 2: Volume
            colors_vol = ['#EF4444' if row['close'] < row['open'] else '#10B981' for idx, row in df.iterrows()]
            fig.add_trace(go.Bar(
                x=df['time'], y=df['volume'], marker_color=colors_vol, name="Khối lượng"
            ), row=2, col=1)
            
            # Row 3: MACD
            colors_macd = ['#EF4444' if val < 0 else '#10B981' for val in df['MACD_Hist']]
            fig.add_trace(go.Bar(
                x=df['time'], y=df['MACD_Hist'], marker_color=colors_macd, name="MACD Hist"
            ), row=3, col=1)
            fig.add_trace(go.Scatter(
                x=df['time'], y=df['MACD'], line=dict(color='blue', width=1.5), name="MACD"
            ), row=3, col=1)
            fig.add_trace(go.Scatter(
                x=df['time'], y=df['Signal'], line=dict(color='orange', width=1.5), name="Signal"
            ), row=3, col=1)
            
            # Row 4: RSI
            fig.add_trace(go.Scatter(
                x=df['time'], y=df['RSI'], line=dict(color='purple', width=1.5), name="RSI"
            ), row=4, col=1)
            
            fig.add_hline(y=70, line_dash="dot", row=4, col=1, line_color="red")
            fig.add_hline(y=30, line_dash="dot", row=4, col=1, line_color="green")
            
            # Format
            fig.update_layout(
                height=height,
                paper_bgcolor="#0F172A",
                plot_bgcolor="#1E293B",
                font=dict(color="#F8FAFC", family="Inter"),
                margin=dict(l=40, r=40, t=40, b=40),
                xaxis_rangeslider_visible=False,
                showlegend=False,
                hovermode="x unified",
                dragmode="drawline"
            )
            
            fig.update_xaxes(showgrid=True, gridcolor='#334155')
            fig.update_yaxes(showgrid=True, gridcolor='#334155')
            
            # Cấu hình thanh công cụ vẽ kỹ thuật của Plotly
            PLOTLY_DRAWING_CONFIG = {
                "displayModeBar": True,
                "displaylogo": False,
                "modeBarButtonsToAdd": [
                    "drawline",
                    "drawopenpath",
                    "drawclosedpath",
                    "drawcircle",
                    "drawrect",
                    "eraseshape",
                ],
                "toImageButtonOptions": {
                    "format": "png",
                    "filename": f"{clean_ticker}_technical_chart"
                }
            }
            
            st.plotly_chart(fig, use_container_width=True, config=PLOTLY_DRAWING_CONFIG)
            st.info("💡 Hướng dẫn: Bạn có thể di chuột lên thanh công cụ góc trên bên phải biểu đồ để dùng công cụ vẽ đường (Draw Line), khối hộp, hình tròn và cục tẩy.")
            
        except Exception as e:
            st.error(f"Lỗi khi xử lý biểu đồ kỹ thuật: {e}")

