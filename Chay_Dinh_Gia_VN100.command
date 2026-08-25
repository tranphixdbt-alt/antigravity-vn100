#!/bin/bash
# Script tự động khởi chạy Hệ thống Định giá VN100 (Nhấp đúp là chạy)
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "============================================================"
echo "   📈 HỆ THỐNG ĐỊNH GIÁ CỔ PHIẾU TỰ ĐỘNG VN100 (STANDALONE)   "
echo "============================================================"
echo "-> Đang kiểm tra môi trường và khởi động hệ thống..."

if [ ! -d "venv" ]; then
    echo "-> Đang tạo môi trường ảo Python..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Tự động mở trình duyệt web sau 2 giây
(sleep 2 && open "http://localhost:8502") &

# Khởi chạy ứng dụng Streamlit
python3 -m streamlit run streamlit_app.py --server.port 8502 --server.headless true
