# Đăng nhập chung *.btinvest.vn bằng tài khoản coin (D98, 18/11/2026)

chungkhoan.btinvest.vn (VN100; tên cũ chungkhoang.btinvest.vn chuyển hướng sang) và chungquyen.btinvest.vn (chứng quyền) không còn tài khoản `admin` dùng chung (basic_auth).
Ai có tài khoản coin.btinvest.vn (tự tạo, đã xác minh email) đều vào được cả hai trang — người dùng chọn « mọi tài khoản coin ».

## Cách chạy
- **Caddy** (`/srv/web/conf/Caddyfile`, snippet `(coin_login)`), mỗi trang `import coin_login <upstream> <đường dẫn công khai...>`:
  - `/api/v1/auth/*` → `coin-check-api-1:8090` (đăng nhập / làm mới / đăng xuất gọi từ chính tên miền đó);
  - `/dang-nhap` → `/srv/web/sites/dang-nhap/index.html` (file này; `?next=/duong-dan`, `?dang-xuat=1`);
  - đường dẫn công khai (tệp tĩnh khung web, không có dữ liệu) → app thẳng;
  - còn lại: `forward_auth` hỏi coin `GET /api/v1/auth/me` (bỏ `Upgrade`/`Connection` để websocket Streamlit không bị
    socket.io của coin cắt); 401/403 → 302 về `/dang-nhap?next=<đường dẫn>`; 2xx → app (`lb_try_duration 30s`).
- **coin-check** (`/srv/apps/coin-check`, mã KHÔNG phải git; sao lưu bản gốc `src-backup-sso-20261118-065459/`):
  - `api/src/helpers/auth-cookie.helper.ts`: có `AUTH_COOKIE_DOMAIN` → cookie `Domain=.btinvest.vn`, luôn `Secure`;
  - `api/src/use-cases/auth/auth.service.ts`: `clearHostOnlyCookies` xóa cookie kiểu cũ (chỉ gắn coin.btinvest.vn) khi
    đăng nhập/đăng xuất để không che cookie dùng chung;
  - `api/src/use-cases/auth/auth.controller.ts`: `/me` giới hạn 600 lượt/phút/IP (mặc định 60 → 429 vì Caddy hỏi `/me`
    ở mỗi yêu cầu, cả nhà dùng chung một IP);
  - `.env`: `AUTH_COOKIE_DOMAIN=.btinvest.vn`. Build: `docker compose build api && docker compose up -d api worker`.
  - Nếu coin được triển khai lại từ nguồn khác: chép lại 3 thay đổi trên, nếu không đăng nhập sẽ thành từng trang riêng.

## Rủi ro đã biết
- API coin sập/khởi động lại (tự huấn luyện mô hình khi bật, ~1 phút) → chungkhoan/chungquyen không vào được lúc đó.
- Ai tạo tài khoản coin cũng xem/sửa được danh mục chứng quyền và dùng AI (DeepSeek, tốn tiền). Muốn giới hạn: thêm
  danh sách email (cần một cổng nhỏ đọc `/me`, Caddy không đọc được JSON).

## Quay lui
1. `sudo cp -p /srv/web/conf/Caddyfile.bak-sso-<giờ> /srv/web/conf/Caddyfile` rồi
   `docker exec web-caddy-1 caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile` (về basic_auth admin).
2. coin: chép 3 file từ `src-backup-sso-*` về chỗ cũ, xóa dòng `AUTH_COOKIE_DOMAIN` trong `.env`, build lại api.
