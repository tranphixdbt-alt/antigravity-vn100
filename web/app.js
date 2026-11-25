// Web hợp nhất btinvest.vn (docs/PLAN_WEB_HOP_NHAT.md mục 12, 13): cổ phiếu (lát 1 đến 3), chứng quyền, ETF, phái sinh (lát 4),
// tài khoản được duyệt (lát 5a), danh mục 4 loại của từng người (lát 5b), cảnh báo trong web (lát 5c).
// Mọi con số lấy từ API chỉ đọc (valuation/api/web_main.py; chứng quyền, ETF, phái sinh do dịch vụ cw_scanner tính);
// trang này không tự tính chỉ số nào.
(() => {
"use strict";
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const itChuyenDong = matchMedia("(prefers-reduced-motion: reduce)").matches;
const rong = matchMedia("(min-width: 960px)");
const chuotThat = matchMedia("(hover: hover) and (pointer: fine)");
const KY_TU = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => KY_TU[c]);
const thieu = (v) => v === null || v === undefined;
// số kiểu Việt Nam; số âm dùng dấu trừ "−" thay cho gạch nối để thẳng hàng với cột có dấu cộng
const so = (n, d = 0) => (thieu(n) ? "—" : Number(n).toLocaleString("vi-VN", { minimumFractionDigits: d, maximumFractionDigits: d }).replace("-", "−"));
const dau = (n, d = 1) => (thieu(n) ? "—" : (n > 0 ? "+" : n < 0 ? "−" : "") + so(Math.abs(n), d));
const ty = (v, d = 0) => (thieu(v) ? "—" : `${dau(v / 1e9, d)} tỷ`);
const ngay = (iso) => (iso ? `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}` : "chưa có");
const boDau = (s) => String(s ?? "").normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/đ/g, "d").replace(/Đ/g, "D").toLowerCase();
const DANG_NHAP = "/dang-nhap"; // trang đăng nhập chung của *.btinvest.vn (D98)
// `than` có giá trị thì gửi POST dạng JSON (yêu cầu ghi); không có thì GET
async function api(duong, than) {
  const dau = { Accept: "application/json" };
  const r = await fetch(duong, than === undefined ? { headers: dau } : { method: "POST", headers: { ...dau, "Content-Type": "application/json" }, body: JSON.stringify(than) });
  if (!r.ok) {
    let t = `Máy chủ trả lỗi ${r.status}.`; try { const j = await r.json(); if (typeof j.detail === "string") t = j.detail; } catch (e) { /* giữ câu mặc định */ }
    const loi = new Error(t); loi.ma = r.status;
    // hết phiên đăng nhập: về trang đăng nhập rồi quay lại đúng chỗ đang xem
    if (r.status === 401) { loi.daChuyen = true; location.href = `${DANG_NHAP}?next=${encodeURIComponent(location.pathname + location.search + location.hash)}`; }
    // đang dùng thì bị khóa hoặc bị rút duyệt: hỏi lại trạng thái để hiện màn hình chắn
    else if (r.status === 403 && daBatDau && duong !== "/api/toi" && !duong.startsWith("/api/tai-khoan")) vaoCong();
    throw loi;
  }
  return r.json();
}
const app = $("#app"), trang = $("#trang"), tab = $("#tab"), to = $("#to"), man = $("#man");

const HINH = {
  homNay: "M4 11l8-7 8 7v8a1 1 0 0 1-1 1h-4v-6H9v6H5a1 1 0 0 1-1-1z",
  coPhieu: "M7 4v3M7 15v5M5 7h4v8H5zM17 3v5M17 14v6M15 8h4v6h-4z",
  chungQuyen: "M4 8a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v2a2 2 0 0 0 0 4v2a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-2a2 2 0 0 0 0-4zM14 6v12",
  etf: "M12 4l8 4-8 4-8-4zM4 12l8 4 8-4M4 16l8 4 8-4",
  phaiSinh: "M3 17c4.5 0 4.5-10 9-10s4.5 10 9 10",
  lui: "M15 5l-7 7 7 7", xuong: "M6 9l6 6 6-6",
  canh: "M12 4l9 16H3zM12 10v4M12 17.3v.2", tin: "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM12 8v.2M12 11v5",
};
const hinh = (ten, lop = "bt") => `<svg class="${lop}" viewBox="0 0 24 24" aria-hidden="true"><path d="${HINH[ten]}"/></svg>`;
const TAB = [["hom-nay", "Hôm nay", "homNay"], ["co-phieu", "Cổ phiếu", "coPhieu"], ["chung-quyen", "Chứng quyền", "chungQuyen"], ["etf", "ETF", "etf"], ["phai-sinh", "Phái sinh", "phaiSinh"]];
const LOP_NHAN = { gom: "re", noi_gom: "re", xa: "dat", noi_xa: "dat", trung_tinh: "tt", chua_du: "mo" };
const THU_TU = { gom: 0, noi_gom: 1, trung_tinh: 2, noi_xa: 3, xa: 4, chua_du: 5 };
const TEN_PHIEU = [["foreign", "Khối ngoại"], ["pv", "Giá và khối lượng"], ["prop", "Tự doanh"]];
const gp = (v) => (v === 1 ? `<i class="pg re">▲</i>` : v === -1 ? `<i class="pg dat">▼</i>` : v === 0 ? `<i class="pg tt">–</i>` : `<i class="pg mo">○</i>`);
const docPhieu = (v) => (v === 1 ? "gom" : v === -1 ? "xả" : v === 0 ? "trung tính" : "chưa đủ dữ liệu");
// Trạng thái của trang: chế độ loại/gồm thỏa thuận, tổng quan, danh sách mã, bộ lọc, mã đang mở, lựa chọn biểu đồ
const S = { cheDo: "loai", tq: null, ds: [], loc: { nhan: "tat", nganh: null }, ma: null, bd: null, xem: "dt", xh: null, tt: null, vm: null,
  loai: null, cq: null, cqLoc: "NÊN XEM XÉT", cqTim: "", cqHien: 0, etf: null, etfXem: "ck", ps: null, trangCu: null,
  dm: null, cb: null, tin: null, tinLoi: null };
const tenMa = (ma) => { const r = S.ds.find((x) => x.ma === ma); return r ? [r.ten, r.nganh].filter(Boolean).join(" · ") : ""; };
const dangToi = () => { const t = document.documentElement.dataset.theme; return t ? t === "dark" : matchMedia("(prefers-color-scheme: dark)").matches; };

/* ---------- Các tab ---------- */
let dangXem = 1;
const nut = TAB.map(([, ten, h], i) => { const b = document.createElement("button"); b.className = "tab-nut"; b.type = "button"; b.dataset.tab = i; b.innerHTML = hinh(h) + `<span>${ten}</span>`; tab.appendChild(b); return b; });
const pane = TAB.map(([id, ten]) => { const s = document.createElement("section"); s.className = "pane"; s.id = `pane-${id}`; s.setAttribute("aria-label", ten); s.innerHTML = `<div class="pane-trong"><div class="dang-ve le">Đang nạp dữ liệu…</div></div>`; trang.appendChild(s); return s; });
const vach = $("#tab-vach");
const datVach = (x) => { vach.style.transform = rong.matches ? `translateY(${Math.round(x) * 48}px)` : `translateX(${x * 100}%)`; };
function datDangXem(i, cuon) {
  dangXem = i; nut.forEach((b, k) => (k === i ? b.setAttribute("aria-current", "page") : b.removeAttribute("aria-current")));
  pane.forEach((p, k) => p.classList.toggle("dang-xem", k === i)); $("#dau-ten").textContent = TAB[i][1];
  if (rong.matches) datVach(i); else if (cuon) trang.scrollTo({ left: i * trang.clientWidth, behavior: itChuyenDong ? "auto" : "smooth" });
  if (TAB[i][0] === "phai-sinh") napPS();
  ghiDiaChi();
}
function ghiDiaChi() { try { history.replaceState(null, "", `${location.pathname}${S.ma ? `?ma=${S.ma}` : ""}#${TAB[dangXem][0]}`); } catch (e) { /* trình duyệt không cho đổi địa chỉ thì bỏ qua */ } }
tab.addEventListener("click", (e) => { const b = e.target.closest(".tab-nut"); if (b) datDangXem(+b.dataset.tab, true); });
let choCuon = 0;
trang.addEventListener("scroll", () => { if (rong.matches) return; cancelAnimationFrame(choCuon); choCuon = requestAnimationFrame(() => { const x = trang.scrollLeft / Math.max(trang.clientWidth, 1); datVach(x); const i = Math.round(x); if (i !== dangXem) datDangXem(i, false); }); }, { passive: true });
rong.addEventListener("change", () => { datVach(dangXem); if (!rong.matches) trang.scrollTo({ left: dangXem * trang.clientWidth }); });

/* ---------- Tab cổ phiếu: tóm tắt, bản đồ ngành, danh sách mã ---------- */
function dongDT(r) {
  const c = r.cot || {}, kN = Object.keys(c).find((k) => k.startsWith("Ngoại")), up = c["Upside (%)"];
  const so3 = [[kN ? kN.replace(" (tỷ)", "") : "Ngoại", kN && !thieu(c[kN]) ? `${dau(c[kN], 1)} tỷ` : "—"], ["CMF20", thieu(c.CMF20) ? "—" : dau(c.CMF20, 2)], ["Giữ nhãn từ", c["Giữ nhãn từ"] || "—"]];
  return `<li><button class="dong le" type="button" data-ma="${esc(r.ma)}"><span class="dong-ma">${esc(r.ma)}</span><span class="phieu-3" role="img" aria-label="Ba phiếu: khối ngoại ${docPhieu(r.phieu[0])}, giá và khối lượng ${docPhieu(r.phieu[1])}, tự doanh ${docPhieu(r.phieu[2])}">${r.phieu.map(gp).join("")}</span><span class="dong-kl ${LOP_NHAN[r.nhan] || "tt"}">${esc(S.tq.ten_nhan[r.nhan] || r.nhan)}</span><span class="dong-phu">${esc(r.nganh)} · ${esc(r.boi_canh)}</span><span class="dong-nho">${thieu(up) ? "" : `Upside ${dau(up, 1)}%`}</span><span class="dong-so">${so3.map(([a, b]) => `<span>${esc(a)}<b>${esc(b)}</b></span>`).join("")}</span></button></li>`;
}
function veDs() {
  const ds = S.tq.ma.filter((r) => (S.loc.nhan === "tat" || r.nhan === S.loc.nhan) && (!S.loc.nganh || r.nganh === S.loc.nganh))
    .sort((a, b) => (THU_TU[a.nhan] ?? 9) - (THU_TU[b.nhan] ?? 9) || a.ma.localeCompare(b.ma));
  $("#ds-cp").innerHTML = ds.map(dongDT).join("");
  const trong = $("#cp-trong"); trong.hidden = ds.length > 0;
  $("#dem-ds").textContent = `${ds.length} mã${S.loc.nganh ? `, ngành ${S.loc.nganh}` : ""}`;
}
const chonXem = () => `<div class="dk le"><div class="chon-2" role="group" aria-label="Chọn cách xem cổ phiếu"><button type="button" data-xem="dt" aria-pressed="${S.xem === "dt"}">Dòng tiền</button><button type="button" data-xem="xh" aria-pressed="${S.xem === "xh"}">Xếp hạng VN100</button></div></div>`;
function veCoPhieu() {
  if (S.xem === "xh") { veXepHang(); return; }
  const q = S.tq, W = String(q.meta.window), t = q.tong[W] || {}, maxR = Math.max(...q.nganh.map((r) => Math.abs(r.r_f || 0)), 1e-9);
  const nganh = q.nganh.map((r) => `<li><button class="ng le" type="button" data-nganh="${esc(r.sector)}" aria-pressed="${S.loc.nganh === r.sector}"><span class="ng-ten">${esc(r.sector)}<small>${so(r.n)} mã</small></span><span class="ng-thanh ${(r.f || 0) >= 0 ? "re" : "dat"}"><i style="width:${Math.max((Math.abs(r.r_f || 0) / maxR) * 50, 0.8).toFixed(1)}%"></i></span><span class="ng-so ${(r.f || 0) >= 0 ? "re" : "dat"}">${ty(r.f, Math.abs(r.f || 0) < 1e11 ? 1 : 0)}</span><span class="ng-phu">${so(r.breadth_pos)}/${so(r.breadth_n)} mã ngoại mua ròng · ${esc(r.label_count)} · tự doanh ${ty(r.p, 1)}${r.dominant ? ` · ${esc(r.dominant)} chiếm ${so((r.dominant_share || 0) * 100)}%` : ""}</span></button></li>`).join("");
  const loc = [["tat", "Tất cả", q.ma.length], ...Object.entries(q.ten_nhan).filter(([k]) => q.dem_nhan[k]).map(([k, ten]) => [k, ten, q.dem_nhan[k]])];
  $("#pane-co-phieu").innerHTML = `<div class="pane-trong"><div class="pane-dau le"><h1>Cổ phiếu</h1><p>Dòng tiền ${esc(W)} phiên của ${so(q.meta.universe)} mã VN100. Giá đến ${ngay(q.meta.price_date)}, dòng tiền đến ${ngay(q.meta.flow_date)}.</p></div>${chonXem()}
    <div class="dk le"><div class="chon-2" role="group" aria-label="Phiên thỏa thuận"><button type="button" data-chedo="loai" aria-pressed="${S.cheDo === "loai"}">Loại thỏa thuận</button><button type="button" data-chedo="gom" aria-pressed="${S.cheDo === "gom"}">Gồm thỏa thuận</button></div></div>
    <div class="tom le"><div class="tom-chinh"><b class="${(t.f || 0) >= 0 ? "re" : "dat"}">${so(Math.abs(t.f || 0) / 1e9)} tỷ</b><span>khối ngoại ${(t.f || 0) >= 0 ? "mua" : "bán"} ròng trong ${esc(W)} phiên</span></div>
      <div class="tom-3"><div><b class="re">${so(q.dem_nhan.gom || 0)}</b><span>mã có dấu hiệu gom</span></div><div><b class="dat">${so(q.dem_nhan.xa || 0)}</b><span>mã có dấu hiệu xả</span></div><div><b>${ty(t.p)}</b><span>tự doanh ròng</span></div></div></div>
    <div class="ghi le"><p>${esc(q.ket_luan)}.</p><p>${esc(q.chi_tiet)}.</p></div>
    <div class="phu-de le">Bản đồ ngành<small>khối ngoại ròng ${esc(W)} phiên; bấm một ngành để lọc danh sách mã</small></div>
    <ul class="ds-ng" id="ds-ng">${nganh}</ul>
    <div class="phu-de le">Danh sách mã<small id="dem-ds"></small><small>ba phiếu: khối ngoại, giá và khối lượng, tự doanh</small></div>
    <div class="loc le" role="group" aria-label="Lọc theo nhãn dòng tiền">${loc.map(([k, ten, n]) => `<button type="button" data-loc="${esc(k)}" aria-pressed="${S.loc.nhan === k}">${esc(ten)}<b>${so(n)}</b></button>`).join("")}</div>
    <ul class="ds" id="ds-cp"></ul><p class="trong le" id="cp-trong" hidden>Không có mã nào khớp bộ lọc này.</p>
    <p class="chan le">${esc(q.trang_thai)}. ${esc(q.meta.disclaimer || "")}</p></div>`;
  veDs();
}
/* ---------- Xếp hạng VN100 và tab Hôm nay (lát 3) ---------- */
function veXepHang() {
  const pane = $("#pane-co-phieu"), dau1 = `<div class="pane-dau le"><h1>Cổ phiếu</h1><p>Xếp hạng VN100 theo mô hình định giá.</p></div>${chonXem()}`;
  if (!S.xh) {
    pane.innerHTML = `<div class="pane-trong">${dau1}<div class="dang-ve le">Đang nạp xếp hạng…</div></div>`;
    api("/api/xep-hang").then((d) => { S.xh = d; if (S.xem === "xh") veXepHang(); }).catch((e) => { if (S.xem === "xh") pane.innerHTML = `<div class="pane-trong">${dau1}<p class="loi le">Không nạp được xếp hạng. ${esc(e.message)}</p></div>`; });
    return;
  }
  const d = S.xh;
  if (!d.co) { pane.innerHTML = `<div class="pane-trong">${dau1}<p class="trong le">Chưa có đợt định giá VN100 nào.</p></div>`; return; }
  pane.innerHTML = `<div class="pane-trong">${dau1}
    <div class="ghi le"><p>Giá trị hợp lý của đợt ${ngay(d.dot)}, giá đến ${ngay(d.gia_den)}. ${so(d.so_dinh_gia)}/${so(d.so_ma)} mã định giá được. Upside = giá trị hợp lý ÷ giá − 1.</p>${d.cu ? `<p class="dat">Giá trị hợp lý đã cũ, nên cập nhật xếp hạng trước khi dùng.</p>` : ""}${d.quy_doi.length ? `<p>Giá trị hợp lý đã quy về thang giá hiện tại do cổ tức hoặc chia tách sau đợt định giá: ${d.quy_doi.map((x) => `${esc(x.ma)} ×${so(x.he_so, 3)}`).join(", ")}.</p>` : ""}</div>
    <div class="phu-de le">Ứng viên tích sản<small>upside cao nhất sau khi loại lỗi dữ liệu, upside trên ${so(d.bo_loc.upside_toi_da)}% và thanh khoản dưới ${so(d.bo_loc.thanh_khoan_toi_thieu_ty)} tỷ mỗi phiên; tối đa ${so(d.bo_loc.toi_da_moi_nganh)} mã mỗi ngành</small></div>
    <div class="le">${d.tich_san.length ? bang(d.tich_san) : `<p class="trong">Đợt này chưa có mã qua đủ bộ lọc.</p>`}</div>
    <div class="phu-de le">Xếp hạng ${so(d.so_ma)} mã</div><div class="le">${bang(d.bang)}</div>
    <p class="chan le">Sàng lọc theo mô hình, không phải khuyến nghị đầu tư.</p></div>`;
}
const damChu = (x) => esc(x).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>");
// Bản tin vĩ mô đã lưu có biểu tượng cờ và emoji ở đầu mục; giao diện này không dùng emoji nên bỏ đi, giữ nguyên chữ
const boBieuTuong = (t) => String(t || "").replace(/[\u{1F1E6}-\u{1F1FF}\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}\u{FE0F}]/gu, "").replace(/^(\s*[-*•]?\s*)\*\*\s+/gm, "$1**");
const DAU_TRU = { 1: `<i class="pg re">✓</i>`, 0: `<i class="pg tt">–</i>`, "-1": `<i class="pg dat">✗</i>` };
const lietKe = (ds) => `<ul class="huy">${ds.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>`;
function veHomNay() {
  const t = S.tt, v = S.vm, cs = t.chi_so, MUI = { 1: "↑", "-1": "↓" }, nt = t.nhan_tin;
  const dai = `<div class="bang"><div class="bang-trong le"><div class="bang-nhan">${cs ? `VN-Index, giá đến ${ngay(t.gia_den)}` : "Chưa có dữ liệu VN-Index"}${t.cu ? ". Dữ liệu giá đã cũ." : ""}</div>${cs ? `<div class="bang-so"><strong>${esc(cs.diem_chu)}</strong>${cs.thay_doi.map((c) => `<span class="${c.ty_le >= 0 ? "bs-tang" : ""}">${so(c.phien)} phiên ${esc(c.chu)}</span>`).join("")}</div>` : ""}<p class="bang-cau">${damChu(t.tieu_de)}</p></div></div>`;
  const tru = t.tru_cot.map((p) => mr(`${DAU_TRU[p.diem] || `<i class="pg mo">·</i>`}<b>${esc(p.ten)}</b>: ${esc(p.tom_tat)}`, p.chi_tiet.length ? lietKe(p.chi_tiet) : "<p>Thiếu dữ liệu.</p>", false)).join("");
  const sapToi = cs ? `<section class="khoi"><h3 class="le">VN-Index sắp tới<small>kịch bản, không phải dự báo</small></h3><div class="nb le"><p>Xu hướng: ${cs.xu_huong.map((x) => `${esc(x.khung)} ${MUI[x.huong] || "–"}`).join(" · ")}${thieu(cs.rsi) ? "" : ` · RSI ${so(cs.rsi)}`}.${cs.khang_cu ? ` Kháng cự ${esc(cs.khang_cu.muc)} (${esc(cs.khang_cu.nguon)}).` : ""}${cs.ho_tro ? ` Hỗ trợ ${esc(cs.ho_tro.muc)} (${esc(cs.ho_tro.nguon)}).` : ""}</p>${lietKe(cs.sap_toi)}</div></section>` : "";
  const noiBat = `<section class="khoi sau"><h3 class="le">Nổi bật ${so(t.so_phien)} phiên</h3><div class="nb le"><p><b>Ngành mạnh:</b> ${esc(t.nganh_manh.join(", ") || "chưa có")}. <b>Ngành yếu:</b> ${esc(t.nganh_yeu.join(", ") || "chưa có")}.</p><div><b>Mã có lực (giá và khối ngoại)</b><div class="the-ma">${t.ma_co_luc.map((m) => `<button type="button" class="o-ma" data-ma="${esc(m)}">${esc(m)}</button>`).join("") || "chưa có"}</div></div>${nt ? `<p><b>Tin tích cực:</b> ${esc(nt.tich_cuc.join(", ") || "chưa có")}. <b>Tin tiêu cực:</b> ${esc(nt.tieu_cuc.join(", ") || "chưa có")}.</p>` : ""}</div>
    ${mr("Ngành: đà giá so với trung vị VN100 và khối ngoại", bang(t.bang_nganh.map((r) => ({ "Ngành": r.nganh, "Đà giá (%)": thieu(r.rel) ? null : r.rel * 100, "Khối ngoại (tỷ)": thieu(r.flow) ? null : r.flow / 1e9 }))) || "<p>Chưa có số.</p>", false)}
    ${mr("Mã mạnh nhất", bang(t.ma_manh.map((r) => ({ "Mã": r.ma, "Tăng giá (%)": thieu(r.ret) ? null : r.ret * 100, "Khối ngoại (tỷ)": thieu(r.flow) ? null : r.flow / 1e9, "Có lực": r.co_luc }))) || "<p>Chưa có số.</p>", false)}</section>`;
  const viMo = v ? `<section class="khoi sau"><h3 class="le">Vĩ mô</h3><div class="vm le">${v.chi_so.map((r) => `<div><span>${esc(r.ten)}</span><b>${esc(r.gia_tri ?? "—")}</b><small>${r.thay_doi ? `${esc(r.thay_doi)} · ` : ""}${r.cu ? "cũ · " : ""}${r.ngay ? ngay(r.ngay) : "chưa có dữ liệu"}</small></div>`).join("")}</div>${v.nhan_dinh.length ? `<div class="le">${lietKe(v.nhan_dinh)}</div>` : ""}<p class="ghi le">Nhận định suy ra từ số liệu trên theo quy tắc cố định; không phải khuyến nghị đầu tư.</p>
    ${mr(`Bản tin vĩ mô do AI tóm tắt${thieu(v.ban_tin_tuoi_gio) ? "" : `, lưu ${so(v.ban_tin_tuoi_gio)} giờ trước`}`, `<div class="vb">${mdNho(boBieuTuong(v.ban_tin))}</div>`, false)}
    ${mrNap("Lịch cổ tức và quyền mua VN100 sắp tới", "/api/lich-quyen")}</section>` : "";
  $("#pane-hom-nay").innerHTML = `${dai}<div class="pane-trong"><section class="khoi"><h3 class="le">Bốn trụ cột</h3>${tru}</section>${sapToi}${noiBat}<section class="khoi sau" id="hn-khac" hidden></section>${viMo}
    <p class="chan le">Chấm điều kiện hiện tại theo quy tắc cố định; không dự báo giá, không phải khuyến nghị đầu tư. Hợp đồng tương lai xem ở tab Phái sinh.</p></div>`;
  veHnKhac();
}
function veLich(d) {
  return d.su_kien.length ? `<p>Các mốc trong ${so(d.so_ngay)} ngày tới.</p>${bang(d.su_kien.map((r) => ({ "Mã": r.ma, "Ngày": ngayHoac(r.ngay), "Mốc": r.moc, "Nội dung": r.noi_dung, "Tiền mặt (đ)": r.tien_mat })))}` : `<p>Không có mốc cổ tức hay quyền mua nào trong ${so(d.so_ngay)} ngày tới.</p>`;
}
async function napHomNay() {
  try { [S.tt, S.vm] = await Promise.all([api("/api/thi-truong"), api("/api/vi-mo")]); veHomNay(); }
  catch (e) { $("#pane-hom-nay").innerHTML = `<div class="pane-trong"><p class="loi le">Không nạp được tổng quan thị trường. ${esc(e.message)}</p></div>`; }
}
async function napTongQuan() {
  try { S.tq = await api(`/api/dong-tien?che_do=${S.cheDo}`); if (!S.bd) { const b = S.tq.bieu_do; S.bd = { khung: b.khung_mac_dinh, tang: new Set(rong.matches ? b.tang_mac_dinh : b.tang_dien_thoai), hoSo: false }; } veCoPhieu(); }
  catch (e) { $("#pane-co-phieu").innerHTML = `<div class="pane-trong"><p class="loi le">Không nạp được dữ liệu dòng tiền. ${esc(e.message)}</p></div>`; }
}

/* ---------- Trang một mã ---------- */
let demMr = 0;
function mr(tieuDe, than, moSan) {
  const id = `mr-${++demMr}`;
  return `<div class="mr${moSan ? " mo" : ""}"><button class="mr-nut le" type="button" aria-expanded="${moSan ? "true" : "false"}" aria-controls="${id}"><span>${tieuDe}</span>${hinh("xuong", "bt mui")}</button><div class="mr-than" id="${id}"><div class="mr-trong le"><div>${than}</div></div></div></div>`;
}
const dauTo = (ma, phu, nhan) => `<div class="to-dau"><div class="to-nam" aria-hidden="true"></div><div class="to-dau-trong le"><button class="nut-tron" type="button" id="to-lui" aria-label="Quay lại">${hinh("lui")}</button><div><div class="to-ma">${esc(ma)}</div><div class="to-phu">${esc(phu)}</div></div><span style="margin-left:auto">${nhan || ""}</span></div></div>`;
function bang(rs) {
  if (!rs || !rs.length) return "";
  // số lẻ theo tên cột: tiền đồng không lẻ, phần trăm một số lẻ, còn lại hai số lẻ; cột "Mã" bấm được để mở trang mã
  const cot = Object.keys(rs[0]), le = (c, v) => (/\(đ\)|đ\/cp/.test(c) ? 0 : /%/.test(c) ? 1 : Number.isInteger(v) ? 0 : 2);
  const o = (c, v) => (thieu(v) || v === "" ? "—" : v === true ? "có" : v === false ? "không" : c === "Mã" ? `<button type="button" class="o-ma" data-ma="${esc(v)}">${esc(v)}</button>` : typeof v === "number" ? so(v, le(c, v)) : esc(v));
  return `<div class="cuon"><table><thead><tr>${cot.map((c, i) => `<th${i ? "" : ' class="trai"'}>${esc(c)}</th>`).join("")}</tr></thead><tbody>${rs.map((r) => `<tr>${cot.map((c) => `<td${typeof r[c] === "number" ? "" : ' class="trai"'}>${o(c, r[c])}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
}
function tia(giaTri) {
  const d = giaTri.map((v) => (thieu(v) ? 0 : v)), m = Math.max(...d.map(Math.abs), 1), w = d.length * 10;
  return `<svg class="tia-20" viewBox="0 0 ${w} 46" role="img" aria-label="Khối ngoại mua bán ròng từng phiên, ${d.length} phiên gần nhất, cũ đến mới">${d.map((v, i) => { const h = Math.max((Math.abs(v) / m) * 21, thieu(giaTri[i]) ? 0 : 1); return `<rect x="${i * 10 + 1.5}" y="${(v >= 0 ? 23 - h : 23).toFixed(1)}" width="7" height="${h.toFixed(1)}" fill="${v >= 0 ? "var(--tang-dam)" : "var(--giam-dam)"}"/>`; }).join("")}<rect x="0" y="22.6" width="${w}" height=".8" fill="var(--muc-3)"/></svg>`;
}
function khoiBieuDo() {
  const b = S.tq.bieu_do;
  return `<section class="khoi"><h3 class="le">Biểu đồ giá và dòng tiền</h3>
    <div class="dk le"><div class="chon-2" role="group" aria-label="Khung thời gian">${b.khung.map((k) => `<button type="button" data-khung="${esc(k)}" aria-pressed="${k === S.bd.khung}">${esc(k)}</button>`).join("")}</div>
      <div class="loc" role="group" aria-label="Các tầng của biểu đồ">${b.tang.map((t, i) => `<button type="button" data-tang="${i}" aria-pressed="${S.bd.tang.has(i)}">${esc(t)}</button>`).join("")}<button type="button" data-hoso aria-pressed="${S.bd.hoSo}">Volume profile</button></div></div>
    <div class="le"><div id="cho-bd" class="dang-ve">Đang vẽ biểu đồ…</div></div><p class="ghi le" id="ghi-bd"></p></section>`;
}
async function veBieuDo() {
  const cho = $("#cho-bd", to), ma = S.ma; if (!cho || !ma) return;
  cho.className = "dang-ve"; cho.textContent = "Đang vẽ biểu đồ…";
  try {
    const d = await api(`/api/co-phieu/${encodeURIComponent(ma)}/bieu-do?che_do=${S.cheDo}&khung=${encodeURIComponent(S.bd.khung)}&tang=${[...S.bd.tang].sort((a, b) => a - b).join(",")}&ho_so=${S.bd.hoSo}&toi=${dangToi()}`);
    if (S.ma !== ma || !cho.isConnected) return;
    if (!d.html) { cho.textContent = d.chu_thich; return; }
    cho.className = ""; cho.innerHTML = `<iframe class="khung-bd" title="Biểu đồ giá và dòng tiền của ${esc(ma)}" sandbox="allow-scripts"></iframe>`;
    const khung = cho.firstElementChild; khung.style.height = `${Number(d.cao) || 600}px`; khung.srcdoc = d.html;
    $("#ghi-bd", to).textContent = d.chu_thich + (d.ho_so ? ` Volume profile: POC ${so(d.ho_so.poc)} · VAH ${so(d.ho_so.vah)} · VAL ${so(d.ho_so.val)} · tổng KL khớp ${so(d.ho_so.total)} cp.` : "");
  } catch (e) { cho.className = "loi"; cho.textContent = `Không vẽ được biểu đồ. ${e.message}`; }
}
function veMa(d) {
  demMr = 0;
  const lop = LOP_NHAN[d.nhan.code] || "tt", phieu = TEN_PHIEU.map(([k, ten]) => `<li>${gp(d.phieu[k].vote)}<div><b>${ten}</b><span>${esc(d.phieu[k].chip)}</span></div></li>`).join("");
  const them = [];
  if (d.giu_tu) them.push(`Giữ nhãn từ ${d.giu_tu_cat ? "trước hoặc bằng " : ""}${ngay(d.giu_tu)}`);
  if (d.che_do === "gom") them.push(`Gồm thỏa thuận ${d.cua_so} phiên: khối ngoại ${ty(d.gom_thoa_thuan.f, 1)}, tự doanh ${ty(d.gom_thoa_thuan.p, 1)}`);
  const up = d.upside && !thieu(d.upside.upside) ? `Upside mô hình (phụ): ${dau(d.upside.upside * 100, 1)}%, ${esc(d.upside_nguon || "")}${d.upside.note ? `. ${esc(d.upside.note)}` : ""}.` : "Upside mô hình (phụ): chưa có từ đợt định giá VN100.";
  return dauTo(d.ma, tenMa(d.ma) || d.nganh, `<span class="muc ${lop}">${esc(d.nhan.text)}</span>`) + `<div class="to-than">
    <div class="dt-kl le"><h2>${esc(d.nhan.text)}, ${esc(d.boi_canh)}</h2><p class="ly-do">${esc(d.nhan.reason)}</p>
      <div>${tia(d.tia)}<p>Khối ngoại mua ròng (xanh) và bán ròng (đỏ) từng phiên, ${d.tia.length} phiên gần nhất, cũ đến mới.</p></div>
      <p>Cửa sổ ${esc(d.cua_so)} phiên. Giá đến ${ngay(d.gia_den)}, dòng tiền đến ${ngay(d.dong_tien_den)}.${them.length ? ` ${esc(them.join(". "))}.` : ""}</p></div>
    <section class="khoi"><h3 class="le">Ba phiếu làm bằng chứng</h3><ul class="phieu le">${phieu}</ul>
      <div class="ghi le"><p>${esc(d.phieu.rvol.chip || "")}</p>${d.huy_hieu.length ? `<ul class="huy">${d.huy_hieu.map((h) => `<li>${esc(h)}</li>`).join("")}</ul>` : ""}</div></section>
    ${khoiBieuDo()}
    <section class="khoi sau"><h3 class="le">Số liệu chi tiết</h3>
      ${mr("Bảng phiếu", bang(d.bang_phieu) || "<p>Chưa có số.</p>", false)}
      ${mr("Dòng tiền theo cửa sổ 5, 20, 60 phiên", bang(d.bang_cua_so) || "<p>Chưa có số.</p>", false)}
      ${mr("Phiên thỏa thuận", bang(d.thoa_thuan) || "<p>Không có phiên thỏa thuận nào trong dữ liệu đã nạp.</p>", false)}</section>
    <section class="khoi sau" id="khoi-dg"><h3 class="le">Định giá</h3><div class="dang-ve">Đang định giá ${esc(d.ma)}… Mã ngân hàng có thể mất hơn 10 giây ở lần đầu.</div></section>
    <div class="ghi le"><p>${up}</p></div></div>`;
}

/* ---------- Định giá, báo cáo tài chính, công ty chứng khoán, cổ tức, AI (lát 2) ---------- */
// Số đã định dạng sẵn kiểu "9,124.0" của report_data → kiểu Việt Nam "9.124,0"; "N/A" → gạch
const vn = (v) => { const s = String(v ?? ""); if (s === "N/A" || s === "") return "—"; return /^-?[\d,]*\.?\d+(%|x)?$/.test(s) ? s.replace(/[.,]/g, (c) => (c === "," ? "." : ",")).replace(/^-/, "−") : s; };
const ngayHoac = (iso) => (iso ? ngay(String(iso)) : "—");
function thuoc(lech, bien) {
  const a = Math.min(Math.abs(lech) / bien, 1), chieu = a < 0.004 ? "tt" : lech < 0 ? "re" : "dat"; // "tt": lệch dưới 0,4% độ rộng thước thì coi như trùng vạch
  return `<span class="thuoc ${chieu}" style="--a:${a.toFixed(3)}" aria-hidden="true"><i class="t-day"></i><i class="t-doan"></i><i class="t-vach"></i><i class="t-cham"></i></span>`;
}
function bangNhan(headers, rows) {
  return `<div class="cuon"><table><thead><tr><th class="trai"></th>${headers.map((h) => `<th>${esc(h)}</th>`).join("")}</tr></thead><tbody>${rows.map((r) => `<tr><td class="trai">${esc(r.label)}</td>${(r.values || []).map((v) => `<td>${esc(vn(v))}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
}
const dl = (rows) => `<dl class="dl">${rows.map((r) => `<dt>${esc(r.label)}</dt><dd>${esc(vn(r.value))}</dd>`).join("")}</dl>`;
const khongApDung = (o) => `<p>Không áp dụng cho mã này.${o && o.ly_do ? ` ${esc(o.ly_do)}` : ""}</p>`;
const mrNap = (tieuDe, loai) => mr(tieuDe, `<p>Đang nạp…</p>`, false).replace('<div class="mr">', `<div class="mr" data-nap="${loai}">`);
function mdNho(t) {
  const o = [], dam = (x) => esc(x).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>"); let ds = false;
  for (const dong of String(t || "").split(/\r?\n/)) {
    const s = dong.trim();
    if (/^[-*•]\s+/.test(s)) { if (!ds) { o.push("<ul>"); ds = true; } o.push(`<li>${dam(s.replace(/^[-*•]\s+/, ""))}</li>`); continue; }
    if (ds) { o.push("</ul>"); ds = false; }
    if (!s) continue;
    const h = s.match(/^#{1,6}\s+(.*)$/); o.push(h ? `<h4>${dam(h[1])}</h4>` : `<p>${dam(s)}</p>`);
  }
  if (ds) o.push("</ul>");
  return o.join("");
}
function bangNhiet(n) {
  if (!n || !n.ap_dung) return khongApDung(n);
  const tat = n.bang.flat(), lo = Math.min(...tat), hi = Math.max(...tat), gx = Math.floor(n.x.length / 2), gy = Math.floor(n.y.length / 2);
  return `<p>Hàng là ${esc(n.nhan_y)}, cột là ${esc(n.nhan_x)}. Ô có viền là giả định gốc; ô càng đậm giá trị càng cao. Đơn vị: đồng mỗi cổ phiếu.</p><div class="cuon"><table class="nhiet"><thead><tr><th class="trai">g</th>${n.x.map((v) => `<th>${so(v * 100, 2)}%</th>`).join("")}</tr></thead><tbody>${n.bang.map((hang, i) => `<tr><th class="trai">${so(n.y[i] * 100, 2)}%</th>${hang.map((v, j) => `<td class="${i === gy && j === gx ? "giua" : ""}" style="background:color-mix(in srgb, var(--s1) ${(hi > lo ? ((v - lo) / (hi - lo)) * 34 : 0).toFixed(0)}%, transparent)">${so(v)}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
}
const NHAN_HT = { NOT_RATED: "Chưa xếp hạng" };
// Cột của bảng dự phóng: tên hiển thị → trường trong `projections` của bộ máy (doanh nghiệp: DCF; ngân hàng: forecast_bank)
const DP_DOANH_NGHIEP = [["Doanh thu", "revenue"], ["EBIT", "ebit"], ["NOPAT", "nopat"], ["FCFF", "fcff"], ["Lợi nhuận sau thuế", "net_income"]];
const DP_NGAN_HANG = [["Thu nhập lãi thuần", "net_interest_income"], ["Thu nhập ngoài lãi", "non_interest_income"], ["Tổng thu nhập hoạt động", "total_operating_income"], ["Chi phí hoạt động", "operating_expenses"], ["Lợi nhuận trước dự phòng", "pre_provision_profit"], ["Chi phí dự phòng", "provision_expense"], ["Lợi nhuận trước thuế", "pretax_income"], ["Lợi nhuận sau thuế", "net_income"], ["Vốn chủ sở hữu", "total_equity"]];
function veDinhGia(d) {
  const coFV = !thieu(d.fv) && d.fv > 0 && !thieu(d.gia) && d.gia > 0, nhan = NHAN_HT[d.khuyen_nghi] || d.khuyen_nghi || "Chưa có";
  const dau1 = coFV
    ? `<div class="kl le"><h2>Giá trị hợp lý ${so(d.fv)} đ, ${d.upside >= 0 ? "cao hơn" : "thấp hơn"} thị giá ${so(Math.abs(d.upside), 1)}%</h2><div class="kl-thuoc">${thuoc((d.gia / d.fv - 1) * 100, 50)}<div class="kl-hai"><div><b>${so(d.gia)} đ</b>Thị giá</div><div><b>${so(d.fv)} đ</b>Giá trị hợp lý</div></div></div><p class="kl-gio">Nhãn của hệ thống: <b>${esc(nhan)}</b>${d.duoc_cong_bo ? "" : " (chưa được công bố, xem các cờ bên dưới)"}. ${esc(d.phuong_phap_chu || "")}${d.phuong_phap_chu ? "." : ""} Chế độ ${esc(d.che_do)}.</p></div>`
    : `<p class="trong le">Bộ máy chưa ra giá trị hợp lý cho mã này. Nhãn của hệ thống: ${esc(nhan)}.</p>`;
  const THU = { error: 0, warning: 1, info: 2 }, co = [...(d.co || [])].sort((a, b) => (THU[a.level] ?? 3) - (THU[b.level] ?? 3));
  const dongCo = (c) => `<li class="${c.level === "error" ? "muc-loi" : c.level === "warning" ? "muc-canh" : "muc-tin"}">${hinh(c.level === "info" ? "tin" : "canh")}<div><b>${c.level === "error" ? "Chặn" : c.level === "warning" ? "Cảnh báo" : "Ghi chú"} · ${esc(c.code)}</b>${esc(c.message)}</div></li>`;
  const khoiCo = co.length ? `<ul class="co le">${co.slice(0, 3).map(dongCo).join("")}</ul>${co.length > 3 ? mr(`Xem cả ${co.length} cờ`, `<ul class="co">${co.slice(3).map(dongCo).join("")}</ul>`, false) : ""}` : "";
  const rieng = d.phuong_phap === "BROKER_SYNTH" ? `<p>Kịch bản và độ nhạy tính trên mô hình riêng của hệ thống${thieu(d.fv_mo_hinh_rieng) ? "" : ` (giá trị ${so(d.fv_mo_hinh_rieng)} đ)`}; giá trị hợp lý ở trên lấy từ mô hình tổng hợp công ty chứng khoán.</p>` : "";
  const kb = d.kich_ban && d.kich_ban.rows && d.kich_ban.applicable !== false ? bang(d.kich_ban.rows.map((r) => ({ "Kịch bản": r.scenario, "Giá trị (đ)": r.target, "So với thị giá (%)": thieu(r.upside) ? null : r.upside * 100 }))) : khongApDung(d.kich_ban);
  const r0 = d.du_phong && d.du_phong[0], cotDP = !r0 ? null : "revenue" in r0 ? DP_DOANH_NGHIEP : "net_interest_income" in r0 ? DP_NGAN_HANG : null;
  const dp = !r0 ? "<p>Phương pháp hiện tại không có dòng tiền dự phóng chi tiết.</p>"
    : cotDP ? `<p>Đơn vị: tỷ đồng.</p>${bang(d.du_phong.map((r) => Object.fromEntries([["Năm", r.year > 1900 ? String(r.year) : `Năm ${r.year}`], ...cotDP.map(([ten, k]) => [ten, thieu(r[k]) ? null : r[k] / 1e9])])))}`
    : bang(d.du_phong);
  const g = d.gia_dinh, gd = !g || g.ap_dung === false ? khongApDung(g) : `${g.schedule_rows && g.schedule_rows.length ? bangNhan(g.schedule_rows[0].values.map((_, i) => `Năm ${i + 1}`), g.schedule_rows) : ""}${g.single_rows ? dl(g.single_rows) : ""}`;
  const wacc = Array.isArray(d.wacc) && d.wacc.length ? dl(d.wacc) : khongApDung(d.wacc);
  return `<h3 class="le">Định giá</h3>${dau1}${khoiCo}
    ${mr("Kịch bản", rieng + kb, false)}${mr("Độ nhạy", rieng + bangNhiet(d.do_nhay), false)}${mr("Dự phóng 5 năm", dp, false)}${mr("Giả định dự phóng", gd, false)}${mr("Chi phí vốn", wacc, false)}
    ${mrNap("Báo cáo tài chính", "tai-chinh")}${mrNap("Công ty chứng khoán", "ctck")}${mrNap("Cổ tức và quyền mua", "co-tuc")}${mrNap("Phân tích AI", "ai")}`;
}
async function napDinhGia(ma) {
  const khoi = $("#khoi-dg", to); if (!khoi) return;
  try { const d = await api(`/api/co-phieu/${encodeURIComponent(ma)}/dinh-gia`); if (S.ma !== ma || !khoi.isConnected) return; khoi.innerHTML = veDinhGia(d); }
  catch (e) { if (S.ma === ma && khoi.isConnected) khoi.innerHTML = `<h3 class="le">Định giá</h3><p class="loi le">Không định giá được ${esc(ma)}. ${esc(e.message)}</p>`; }
}
const TEN_BANG = { income_statement: "Kết quả kinh doanh", balance_sheet: "Bảng cân đối kế toán", cash_flow: "Lưu chuyển tiền tệ" };
function veTaiChinh(d) {
  const o = [`<p>Đơn vị: ${esc(d.don_vi)}. Cột cuối là 4 quý gần nhất (TTM) khi năm chưa kết thúc.</p>`], ls = d.lich_su, pl = d.phu_luc;
  if (ls && ls.rows) o.push(`<h4 class="tb">Chỉ tiêu chính</h4>`, bangNhan(ls.headers, ls.rows));
  if (pl && pl.headers) for (const [k, v] of Object.entries(pl)) if (Array.isArray(v) && v.length && v[0] && Array.isArray(v[0].values)) o.push(`<h4 class="tb">${esc(TEN_BANG[k] || k)}</h4>`, bangNhan(pl.headers, v));
  return o.length > 1 ? o.join("") : "<p>Chưa có báo cáo tài chính cho mã này.</p>";
}
function daiCTCK(s) {
  const gt = s.broker_rows.map((r) => r.target_price).filter((v) => !thieu(v)), tat = [...gt, s.current_price, s.our_target].filter((v) => !thieu(v));
  if (!gt.length) return "";
  const lo = Math.min(...tat), hi = Math.max(...tat), W = 360, L = 10, R = 10, x = (v) => L + (W - L - R) * ((v - lo) / (hi - lo || 1));
  return `<svg class="bieu" viewBox="0 0 ${W} 70" role="img" aria-label="Giá mục tiêu của ${gt.length} báo cáo từ ${so(Math.min(...gt))} đến ${so(Math.max(...gt))} đồng; mô hình ${so(s.our_target)}; thị giá ${so(s.current_price)}"><line x1="${L}" x2="${W - R}" y1="24" y2="24" stroke="var(--ke)" stroke-width="2"/>${gt.map((v) => `<circle cx="${x(v).toFixed(1)}" cy="24" r="4.5" fill="var(--muc-3)"/>`).join("")}<rect x="${(x(s.our_target) - 1.5).toFixed(1)}" y="11" width="3" height="26" fill="var(--vang)"/><circle cx="${x(s.current_price).toFixed(1)}" cy="24" r="6.5" fill="var(--muc)"/><text x="${x(s.current_price).toFixed(1)}" y="58" font-size="11.5" fill="var(--muc)" text-anchor="${x(s.current_price) < 70 ? "start" : "middle"}">Thị giá ${so(s.current_price)}</text><text x="${x(s.our_target).toFixed(1)}" y="58" font-size="11.5" fill="var(--muc)" text-anchor="${x(s.our_target) > W - 80 ? "end" : "middle"}">Mô hình ${so(s.our_target)}</text></svg>`;
}
function veCTCK(d) {
  const s = d.so_sanh, t = d.tong_hop, o = [];
  if (!s || s.ap_dung === false || !Array.isArray(s.broker_rows) || !s.broker_rows.length) o.push("<p>Chưa có báo cáo công ty chứng khoán cho mã này, hoặc mã chưa có giá trị hợp lý để so sánh.</p>");
  else o.push(`<p>Trung vị ${so(s.consensus_median)} đ từ ${so(s.n_reports)} báo cáo. Mô hình ${so(s.our_target)} đ, ${(s.deviation || 0) >= 0 ? "cao hơn" : "thấp hơn"} trung vị ${so(Math.abs(s.deviation || 0) * 100, 1)}%.${s.consensus_thin ? " Ít báo cáo, độ tin cậy thấp." : ""}${s.consensus_stale ? " Phần lớn báo cáo đã cũ." : ""}</p>`, daiCTCK(s), bang(s.broker_rows.map((r) => ({ "Công ty": r.broker, "Ngày": r.report_date, "Giá mục tiêu (đ)": r.target_price, "Khuyến nghị": r.rating, "Mô hình so với CTCK (%)": thieu(r.vs_model) ? null : r.vs_model * 100, "Tuổi (ngày)": r.age_days }))));
  const ds = (ten, arr) => (Array.isArray(arr) && arr.length ? `<h4 class="tb">${ten}</h4><ul class="huy">${arr.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>` : "");
  if (t) o.push(`<h4 class="tb">Tổng hợp luận điểm bằng AI</h4><p>Từ ${so(t.n_reports)} báo cáo (${esc(t.brokers || "")}). Sinh lúc ${esc(String(t.generated_at || "").slice(0, 16))}${t.model ? ` bằng ${esc(t.model)}` : ""}.</p>`, ds("Điểm chung", t.diem_chung), ds("Điểm riêng", t.diem_rieng), ds("Điểm mấu chốt", t.diem_mau_chot), t.doi_chieu_noi_bo ? `<h4 class="tb">Đối chiếu với mô hình</h4><p>${esc(t.doi_chieu_noi_bo)}</p>` : "");
  else o.push("<p>Chưa có bản AI tổng hợp luận điểm cho mã này.</p>");
  return o.join("");
}
function veCoTuc(d) {
  return d.su_kien && d.su_kien.length ? bang(d.su_kien.map((r) => ({ "Nội dung": r.title || r.event_type, "Công bố": ngayHoac(r.announcement_date), "Không hưởng quyền": ngayHoac(r.ex_right_date), "Thanh toán": ngayHoac(r.payment_date), "Tiền mặt (đ/cp)": r.cash_amount_vnd_per_share, "Tỷ lệ": r.exercise_ratio }))) : "<p>Không có sự kiện cổ tức hay quyền mua nào đã công bố trong dữ liệu.</p>";
}
function veAI(d) {
  return d.co ? `<p>Bản lưu lúc ${esc(String(d.tao_luc || "").slice(0, 16).replace("T", " "))}${d.mo_hinh ? `, mô hình ${esc(d.mo_hinh)}` : ""}. Có thể cũ hơn số liệu đang hiện ở trên.</p><div class="vb">${mdNho(d.van_ban)}</div>`
    : "<p>Chưa có báo cáo AI nào được lưu cho mã này. Báo cáo AI hiện sinh ở web cũ; web này chỉ đọc bản đã lưu vì mỗi lần sinh mới tốn tiền API.</p>";
}
const VE_MUC = { "tai-chinh": veTaiChinh, ctck: veCTCK, "co-tuc": veCoTuc, ai: veAI, "/api/lich-quyen": veLich };
async function napMuc(hop, loai) {
  // `loai` bắt đầu bằng "/" là đường dẫn chung (không theo mã); còn lại là phần đuôi của /api/co-phieu/{mã}/
  const ma = S.ma, chung = loai.startsWith("/"), cho = $(".mr-trong > div", hop);
  try { const d = await api(chung ? loai : `/api/co-phieu/${encodeURIComponent(ma)}/${loai}`); if ((!chung && S.ma !== ma) || !cho.isConnected) return; cho.innerHTML = VE_MUC[loai](d); }
  catch (e) { delete hop.dataset.xong; if (cho.isConnected) cho.innerHTML = `<p class="loi">Không nạp được. ${esc(e.message)}</p>`; }
}
async function moMa(ma, tu) {
  S.ma = ma; S.loai = "cp"; ghiDiaChi();
  moTo(`${dauTo(ma, tenMa(ma), "")}<div class="to-than"><div class="dang-ve">Đang nạp ${esc(ma)}…</div></div>`, tu);
  try {
    const d = await api(`/api/co-phieu/${encodeURIComponent(ma)}/dong-tien?che_do=${S.cheDo}`);
    if (S.ma !== ma) return;
    $(".to-trong", to).innerHTML = veMa(d); veBieuDo(); napDinhGia(ma);
  } catch (e) { if (S.ma === ma) $(".to-than", to).innerHTML = `<p class="loi le">Không nạp được ${esc(ma)}. ${esc(e.message)}</p>`; }
}

/* ---------- Chứng quyền, ETF, phái sinh (lát 4) ---------- */
// Số do dịch vụ chứng quyền (repo cw_scanner) tính và trả qua /api/chung-quyen, /api/etf, /api/phai-sinh; ở đây chỉ trình bày.
const BIEN_THUOC = { cw: 50, etf: 5, ps: 2 }; // độ rộng thước (± %): chứng quyền như cổ phiếu; ETF so với NAV và hợp đồng so với chỉ số lệch nhỏ hơn nhiều
const SO_DONG = 60; // số dòng chứng quyền vẽ mỗi lượt; danh sách đủ có vài trăm dòng
const SO_THE = 6; // số mã nêu ở tab Hôm nay cho mỗi loại
const GOI_Y_DU_PHONG = 12; // số gợi ý tìm kiếm khi API cổ phiếu lỗi nên không có giới hạn từ cấu hình
const CW_CU = "https://chungquyen.btinvest.vn"; // trang hướng dẫn vẫn nằm ở web chứng quyền cũ
const LOP_NHOM = { "NÊN XEM XÉT": "xx", "THEO DÕI": "td", "BỎ QUA": "bq" };
const tenNhom = (k) => ((S.cq && S.cq.nhom.find((n) => n.ma === k)) || {}).ten || k;
const ct = (chu) => (chu ? `<button class="ct" type="button" aria-label="Giải thích" aria-expanded="false" data-ct="${esc(chu)}">!</button>` : "");
const lopDR = (c) => (c.lop_dat_re === "duong" ? "re" : c.lop_dat_re === "am" ? "dat" : "tt");
const dauCanh = (chu) => (chu ? `<span class="canh" role="img" aria-label="Có cảnh báo">${hinh("canh")}</span>` : "");
const gioPhut = (iso) => (iso ? String(iso).slice(11, 19) : "");
const pt = (v, d = 1) => (thieu(v) ? "—" : `${dau(v, d)}%`);
// thước trung tính cho hợp đồng tương lai: chưa có giá hợp lý nên không tô màu rẻ / đắt, chỉ cho thấy giá nằm dưới hay trên chỉ số
const thuocTT = (lech, bien) => `<span class="thuoc ${lech < 0 ? "duoi" : lech > 0 ? "tren" : ""}" style="--a:${Math.min(Math.abs(lech) / bien, 1).toFixed(3)}" aria-hidden="true"><i class="t-day"></i><i class="t-doan"></i><i class="t-vach"></i><i class="t-cham"></i></span>`;
const loiPane = (id, ten, e) => { $(`#pane-${id}`).innerHTML = `<div class="pane-trong"><div class="pane-dau le"><h1>${ten}</h1></div><p class="loi le">Không nạp được dữ liệu ${ten.toLowerCase()}. ${esc(e.message)}</p></div>`; };

/* Chứng quyền */
function dongCQ(c) {
  const nguon = c.nguon_gia && c.nguon_gia !== "ask" ? ` (${c.nguon_gia === "tham chiếu" ? "tham chiếu" : esc(c.nguon_gia)})` : "";
  const so6 = [["Giá mua", so(c.gia_mua) + nguon], ["Hợp lý", so(c.hop_ly)], ["IV − HV", thieu(c.iv_hv) ? "—" : dau(c.iv_hv, 1)], ["Hòa vốn", pt(c.hoa_von)], ["Đòn bẩy", `${so(c.don_bay, 1)}x`], ["KL khớp", so(c.kl)]];
  return `<li><button class="dong rong le" type="button" data-cw="${esc(c.ma)}"><span class="dong-ma">${esc(c.ma)}${c.moi ? `<span class="nho-the">Mới</span>` : ""}${dauCanh(c.canh_bao)}</span>${thieu(c.dat_re) ? "<span></span>" : thuoc(c.dat_re, BIEN_THUOC.cw)}<span class="dong-kl ${lopDR(c)}">${esc(c.chu_dat_re)}</span><span class="dong-phu">${esc(c.cs)} · ${esc(c.tcph)} · còn ${so(c.con_ngay)} ngày</span><span class="dong-nho">${esc(tenNhom(c.nhom))}</span><span class="dong-so">${so6.map(([a, b]) => `<span>${a}<b>${b}</b></span>`).join("")}</span></button></li>`;
}
function veDsCQ() {
  const k = boDau(S.cqTim.trim());
  const ds = S.cq.cw.filter((c) => (S.cqLoc === "tat" || (S.cqLoc === "moi" ? c.moi : c.nhom === S.cqLoc)) && (!k || boDau(`${c.ma} ${c.cs} ${c.tcph}`).includes(k)));
  $("#ds-cq").innerHTML = ds.slice(0, S.cqHien).map(dongCQ).join("");
  $("#cq-dem").textContent = `${so(ds.length)} chứng quyền`;
  $("#cq-trong").hidden = ds.length > 0;
  const them = $("#cq-them"), con = ds.length - S.cqHien; them.hidden = con <= 0;
  if (con > 0) them.textContent = `Hiện thêm ${so(Math.min(SO_DONG, con))} trong ${so(con)} dòng còn lại`;
}
function veCQ() {
  const q = S.cq, pane = $("#pane-chung-quyen");
  if (!q.co) { pane.innerHTML = `<div class="pane-trong"><div class="pane-dau le"><h1>Chứng quyền</h1></div><p class="trong le">Chưa có lần quét chứng quyền nào.</p></div>`; return; }
  const n = Object.fromEntries(q.nhom.map((x) => [x.ma, x.so])), g = q.nguong, gt = q.giai_thich;
  const loc = [...q.nhom.map((x) => [x.ma, x.ten, x.so]), ["moi", "Mới phát hành", q.so_moi], ["tat", "Tất cả", q.tong]];
  pane.innerHTML = `<div class="pane-trong"><div class="pane-dau le"><h1>Chứng quyền</h1><p>Lần quét ${esc(q.lan_quet)}. ${so(q.tong)} chứng quyền, định giá bằng Black-Scholes.</p></div>
    ${q.cu ? `<div class="le"><div class="bao">${hinh("canh")}<p>Số liệu cũ ${so(q.cu.so_ngay)} ngày: lần quét tự động ngày ${ngay(q.cu.du_kien)} có thể chưa chạy, hoặc hôm đó nghỉ lễ. Số ngày tới đáo hạn và các chỉ số tính tại ngày quét; phần phân tích theo giá lúc này của từng mã thì tính lại khi mở.</p></div></div>` : ""}
    <div class="tom le"><div class="tom-chinh"><b class="re">${so(n["NÊN XEM XÉT"])}</b><span>chứng quyền đạt cả 4 tiêu chí</span></div>
      <div class="tom-3"><div><b>${so(n["THEO DÕI"])}</b><span>trượt 1 tiêu chí</span></div><div><b>${so(n["BỎ QUA"])}</b><span>trượt từ 2 tiêu chí</span></div><div><b>${so(q.so_moi)}</b><span>mới so với lần quét trước</span></div></div></div>
    <div class="ghi le"><p>Bốn tiêu chí, tính theo giá mua (giá chào bán thấp nhất): còn từ ${so(g.ngay)} ngày, IV − HV không quá ${so(g.iv_hv)} điểm, cổ phiếu cơ sở tăng không quá ${so(g.hoa_von)}% là hòa vốn (chưa gồm phí, thuế), khớp từ ${so(g.kl)} chứng quyền mỗi phiên.</p></div>
    <div class="phu-de le">Danh sách<small id="cq-dem"></small><small>trong mỗi nhóm xếp theo IV − HV, thấp nhất trước ${ct(gt["IV − HV"])}</small></div>
    <div class="o-loc le"><label class="an-doc" for="cq-tim">Tìm chứng quyền</label><input id="cq-tim" type="search" placeholder="Tìm mã hoặc tổ chức phát hành" autocomplete="off" spellcheck="false" value="${esc(S.cqTim)}"></div>
    <div class="loc le" role="group" aria-label="Lọc theo nhóm">${loc.map(([k, ten, sl]) => `<button type="button" data-cq-loc="${esc(k)}" aria-pressed="${S.cqLoc === k}">${esc(ten)}<b>${so(sl)}</b></button>`).join("")}</div>
    <ul class="ds" id="ds-cq"></ul><p class="trong le" id="cq-trong" hidden>Không có chứng quyền nào khớp.</p>
    <div class="le"><button class="nut-them" type="button" id="cq-them" hidden></button></div>
    <p class="chan le">Thước: chấm là giá mua, vạch vàng là giá hợp lý theo Black-Scholes. Sàng lọc theo mô hình, không phải khuyến nghị đầu tư. Luôn kiểm tra điều khoản trên trang của tổ chức phát hành hoặc HOSE trước khi mua.</p></div>`;
  veDsCQ();
}
const khoiTrangCu = (phu) => `<section class="khoi sau"><h3 class="le">Phân tích theo giá lúc này<small>${phu}</small></h3><div id="cho-cu" class="dang-ve le">Đang tải giá trực tiếp và biểu đồ…</div></section>`;
function veCW(d) {
  demMr = 0;
  const c = d.cw, gt = (S.cq && S.cq.giai_thich) || {}, coCP = S.ds.some((r) => r.ma === c.cs && r.co_dong_tien), khac = d.cung_cs.filter((x) => x.ma !== c.ma);
  const o = (ten, giaTri, khoa) => `<div><span>${ten}${ct(gt[khoa])}</span><b>${giaTri}</b></div>`;
  return dauTo(c.ma, `Chứng quyền mua ${c.cs} · ${c.tcph}`, `<span class="muc ${LOP_NHOM[c.nhom] || "bq"}">${esc(tenNhom(c.nhom))}</span>`) + `<div class="to-than">
    <div class="kl le"><h2>${esc(tenNhom(c.nhom))}${thieu(c.dat_re) ? "" : `: ${esc(c.chu_dat_re.toLowerCase())} so với giá hợp lý`}</h2>
      <div class="kl-thuoc">${thieu(c.dat_re) ? "" : thuoc(c.dat_re, BIEN_THUOC.cw)}<div class="kl-hai"><div>Giá mua${ct(gt["Giá mua"])}<b>${so(c.gia_mua)} đ</b></div><div>Giá hợp lý (Black-Scholes)<b>${so(c.hop_ly)} đ</b></div></div></div>
      <p class="kl-gio">Số lúc quét ${esc(d.lan_quet)}. Còn ${so(c.con_ngay)} ngày tới đáo hạn ${ngay(d.ngay_dao_han)}${c.gd_cuoi ? `, bán được đến hết ngày ${ngay(c.gd_cuoi)}` : ""}.</p>
      ${c.canh_bao ? `<div class="bao">${hinh("canh")}<p>${esc(c.canh_bao)}.</p></div>` : ""}</div>
    <section class="khoi"><h3 class="le">Bốn tiêu chí lúc quét</h3><ul class="phieu le">${d.tieu_chi.map((t) => `<li>${t.dat ? `<i class="pg re">✓</i>` : `<i class="pg dat">✗</i>`}<div><b>${esc(t.noi_dung)}</b><span>${esc(t.yeu_cau)}</span></div></li>`).join("")}</ul>
      <div class="ghi le"><p>Kết luận của lần quét: ${esc(c.ly_do)}.</p></div></section>
    <section class="khoi"><h3 class="le">Số chính lúc quét</h3>
      <div class="so-3 le">${o("Hòa vốn khi cổ phiếu tăng", pt(c.hoa_von), "CS cần tăng để hòa vốn")}${o("Đòn bẩy", `${so(c.don_bay, 1)}x`, "Đòn bẩy")}${o("Delta", so(c.delta, 2), "Delta")}</div>
      <div class="so-3 le">${o("IV", thieu(c.iv) ? "—" : `${so(c.iv, 1)}%`, "IV")}${o("Biến động 1 năm (HV)", `${so(c.hv, 1)}%`, "")}${o("IV − HV", thieu(c.iv_hv) ? "—" : dau(c.iv_hv, 1), "IV − HV")}</div>
      <div class="so-3 le">${o(`Giá ${esc(c.cs)}`, so(c.gia_cs), "")}${o("Giá thực hiện", so(c.gia_th), "")}${o("Tỷ lệ chuyển đổi", `${so(c.ty_le, 4).replace(/,?0+$/, "")} : 1`, "")}</div>
      <div class="so-3 le">${o("KL khớp", so(c.kl), "")}${o("Đang chào bán", so(c.kl_chao_ban), "")}${o("Lệch 20 phiên", c.moc_lech === d.ngay ? "chưa đủ lịch sử" : pt(c.lech_20), "Lệch 20 phiên")}</div>
      ${c.ghi_chu_iv ? `<div class="ghi le"><p>Không giải được IV: ${esc(c.ghi_chu_iv)}.</p></div>` : ""}</section>
    ${khoiTrangCu(`định giá lại, nến 1 giờ, 4 giờ, ngày, IV theo thời gian, mức theo kịp ${esc(c.cs)}`)}
    <section class="khoi sau"><h3 class="le">Liên quan</h3>${coCP ? `<div class="the-ma le"><button type="button" class="o-ma" data-ma="${esc(c.cs)}">Xem cổ phiếu ${esc(c.cs)}</button></div>` : ""}
      <div class="ghi le"><p>${so(khac.length)} chứng quyền khác của ${esc(c.cs)} nằm trong bảng cuối phần phân tích ở trên; bấm một dòng để mở.</p></div></section>
    <p class="chan le">Sàng lọc theo mô hình Black-Scholes, không phải khuyến nghị đầu tư. Bốn tiêu chí chưa tính phí giao dịch và thuế.</p></div>`;
}
async function moCW(ma, tu) {
  S.ma = ma; S.loai = "cw"; S.trangCu = null; ghiDiaChi();
  moTo(`${dauTo(ma, "Chứng quyền", "")}<div class="to-than"><div class="dang-ve">Đang nạp ${esc(ma)}…</div></div>`, tu);
  try {
    const d = await api(`/api/chung-quyen/${encodeURIComponent(ma)}`);
    if (S.ma !== ma) return;
    $(".to-trong", to).innerHTML = veCW(d); to.scrollTop = 0; napTrangCu();
  } catch (e) { if (S.ma === ma) $(".to-than", to).innerHTML = `<p class="loi le">Không nạp được ${esc(ma)}. ${esc(e.message)}</p>`; }
}

/* ETF */
const giaTriCot = (c, v) => (c.so_le === null ? (v === true ? "Đạt" : v === false ? "" : esc(v ?? "")) : thieu(v) ? "—" : `${c.co_dau ? dau(v, c.so_le) : so(v, c.so_le)}${esc(c.hau_to)}`);
// tô màu theo dấu như bảng của trang cũ: cột có dấu thì dương xanh, âm đỏ
const lopCot = (c, v) => (c.so_le !== null && c.co_dau && !thieu(v) ? (v > 0 ? "re" : v < 0 ? "dat" : "") : "");
const gtCot = (c) => c.giai_thich.replace("🟢:", "Đạt:");
// cột tự nói đủ nghĩa: không gắn dấu "!" ở tờ chi tiết (lời giải thích đầy đủ vẫn có trong mục "Giải thích các cột")
const COT_DE_HIEU = new Set(["Chỉ số", "Giá", "Giá chào bán", "KL chào bán", "1T %", "3T %", "6T %", "1N %", "Phí quản lý %", "GTGD TB20 (tỷ)", "Khối ngoại ròng (tỷ)", "CCQ lưu hành", "Phiên chưa khớp"]);
function bangCot(b, laQuy) {
  return `<div class="cuon"><table><thead><tr><th class="trai">${laQuy ? "Quỹ" : "Chỉ số"}</th>${b.cot.map((c) => `<th${c.so_le === null ? ' class="trai"' : ""}>${esc(c.tieu_de)}</th>`).join("")}</tr></thead><tbody>${b.dong.map((h) => `<tr><td class="trai">${laQuy ? `<button type="button" class="o-ma" data-etf="${esc(h["Mã"])}">${esc(h["Mã"])}</button>` : esc(h["Mã"])}${dauCanh(h["Cảnh báo"])}</td>${b.cot.map((c) => `<td class="${c.so_le === null ? "trai" : lopCot(c, h[c.khoa])}">${giaTriCot(c, h[c.khoa])}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
}
const giaiThichCot = (b) => `<dl class="gt">${b.cot.map((c) => `<dt>${esc(c.tieu_de)}</dt><dd>${esc(gtCot(c))}</dd>`).join("")}</dl>`;
const dlCot = (b, h) => `<dl class="dl">${b.cot.map((c) => `<dt>${esc(c.tieu_de)}${COT_DE_HIEU.has(c.khoa) ? "" : ct(gtCot(c))}</dt><dd class="${lopCot(c, h[c.khoa])}">${giaTriCot(c, h[c.khoa]) || "chưa"}</dd>`).join("")}</dl>`;
const chuNAV = (ck) => (thieu(ck) ? "Chưa có iNAV" : ck < 0 ? `Dưới NAV ${so(-ck, 2)}%` : ck > 0 ? `Trên NAV ${so(ck, 2)}%` : "Bằng NAV");
const lopNAV = (ck) => (thieu(ck) || ck === 0 ? "tt" : ck < 0 ? "re" : "dat");
function dongETF(h) {
  const ck = h["Chiết khấu mua được %"];
  const so4 = [["Thường lệch", pt(h["CL NAV trung vị 1N %"], 2)], ["Sâu nhất 1 năm", pt(h["CL NAV thấp nhất 1N %"])], ["GTGD TB20", thieu(h["GTGD TB20 (tỷ)"]) ? "—" : `${so(h["GTGD TB20 (tỷ)"], 2)} tỷ`], ["Mua–bán", thieu(h["Chênh mua–bán %"]) ? "—" : `${so(h["Chênh mua–bán %"], 2)}%`]];
  return `<li><button class="dong rong le" type="button" data-etf="${esc(h["Mã"])}"><span class="dong-ma">${esc(h["Mã"])}${h["Đạt"] ? `<span class="nho-the dat-nguong">Đạt ngưỡng</span>` : ""}${dauCanh(h["Cảnh báo"])}</span>${thieu(ck) ? "<span></span>" : thuoc(ck, BIEN_THUOC.etf)}<span class="dong-kl ${lopNAV(ck)}">${chuNAV(ck)}</span><span class="dong-phu">${esc(h["Chỉ số"])} · chào bán ${so(h["Giá chào bán"])} · iNAV ${so(h["iNAV"])}</span><span class="dong-nho">Lãi ròng ${pt(h["Lãi ròng nếu về NAV %"], 2)}</span><span class="dong-so">${so4.map(([a, b]) => `<span>${a}<b>${b}</b></span>`).join("")}</span></button></li>`;
}
function veETF() {
  const q = S.etf, pane = $("#pane-etf");
  if (!q.co) { pane.innerHTML = `<div class="pane-trong"><div class="pane-dau le"><h1>ETF</h1></div><p class="trong le">Chưa có kết quả ETF nào.</p></div>`; return; }
  const ck = q.chiet_khau.dong, g = q.nguong, tv = q.trung_vi_cu, dem = (f) => ck.filter((h) => !thieu(h["Chiết khấu mua được %"]) && f(h["Chiết khấu mua được %"])).length;
  const xem = [["ck", "Chiết khấu so với NAV"], ["quy", `Tất cả ${so(q.so_quy)} quỹ`], ["cs", `Chỉ số (${so(q.chi_so.dong.length)})`]];
  const than = S.etfXem === "quy" ? `<div class="le">${bangCot(q.quy, true)}</div><div class="khoi">${mr("Giải thích các cột", giaiThichCot(q.quy), false)}</div>`
    : S.etfXem === "cs" ? `<div class="le">${bangCot(q.chi_so, false)}</div><div class="khoi">${mr("Giải thích các cột", giaiThichCot(q.chi_so), false)}</div>`
    : `<div class="phu-de le">Xếp theo lãi ròng nếu về NAV<small>cao nhất trước ${ct(gtCot(q.chiet_khau.cot.find((c) => c.khoa === "Lãi ròng nếu về NAV %")))}</small></div><ul class="ds">${ck.map(dongETF).join("")}</ul>
      ${tv.quy.length ? `<div class="le"><div class="bao">${hinh("canh")}<p>Mức thường lệch 1 năm có thể đã cũ (lệch trung vị ${so(tv.so_phien)} phiên quá ${so(tv.nguong, 1)} điểm): ${tv.quy.map((x) => `${esc(x.ma)} ${esc(x.chu)}`).join("; ")}. Rẻ hay đắt hơn mức thường của các quỹ này có thể không còn đúng.</p></div></div>` : ""}
      <div class="khoi">${mr("Bảng đủ các cột chiết khấu", bangCot(q.chiet_khau, true), false)}${mr("Giải thích các cột", giaiThichCot(q.chiet_khau), false)}</div>`;
  pane.innerHTML = `<div class="pane-trong"><div class="pane-dau le"><h1>ETF</h1><p>Số liệu ${esc(q.luc)}. ${so(q.so_quy)} quỹ; trang từng quỹ lấy giá trực tiếp.</p></div>
    <div class="tom le"><div class="tom-chinh"><b class="${ck.some((h) => h["Đạt"]) ? "re" : ""}">${so(ck.filter((h) => h["Đạt"]).length)}</b><span>quỹ đang mua được dưới NAV đủ ngưỡng</span></div>
      <div class="tom-3"><div><b>${so(dem((v) => v < 0))}</b><span>quỹ chào bán dưới NAV</span></div><div><b>${so(dem((v) => v > 0))}</b><span>quỹ chào bán trên NAV</span></div><div><b>${so(ck.filter((h) => thieu(h["Chiết khấu mua được %"])).length)}</b><span>quỹ chưa có iNAV hoặc giá chào bán</span></div></div></div>
    <div class="ghi le"><p>Ngưỡng: lãi ròng nếu mua ở giá chào bán rồi bán đúng NAV từ ${so(g.lai_rong)}% và mua được từ ${so(g.mua_duoc / 1e6)} triệu đồng. Chỉ có lời khi giá quay về sát NAV; quỹ ít giao dịch có thể chiết khấu rất lâu, xem mức thường lệch của từng quỹ.</p>${q.loi ? `<p class="dat">${esc(q.loi)}</p>` : ""}</div>
    <div class="dk le"><div class="chon-2" role="group" aria-label="Chọn bảng ETF">${xem.map(([k, ten]) => `<button type="button" data-etf-xem="${k}" aria-pressed="${S.etfXem === k}">${ten}</button>`).join("")}</div></div>
    ${than}
    ${q.canh_bao.length ? `<div class="khoi">${mr(`Cảnh báo dữ liệu (${so(q.canh_bao.length)})`, lietKe(q.canh_bao.map((x) => `${x.ma}: ${x.chu}`)), false)}</div>` : ""}
    <p class="chan le">Thước: chấm là giá chào bán, vạch vàng là iNAV. Sàng lọc theo số liệu, không phải khuyến nghị đầu tư.</p></div>`;
}
function veQuy(ma) {
  demMr = 0;
  const q = S.etf, h = q.chiet_khau.dong.find((x) => x["Mã"] === ma), g = q.quy.dong.find((x) => x["Mã"] === ma) || h, ck = h["Chiết khấu mua được %"];
  return dauTo(ma, `Quỹ ETF mô phỏng ${h["Chỉ số"]}`, h["Đạt"] ? `<span class="muc xx">Đạt ngưỡng</span>` : "") + `<div class="to-than">
    <div class="kl le"><h2>${thieu(ck) ? "Chưa có iNAV hoặc giá chào bán" : `Đang chào bán ${chuNAV(ck).toLowerCase().replace("nav", "NAV")}`}</h2>
      <div class="kl-thuoc">${thieu(ck) ? "" : thuoc(ck, BIEN_THUOC.etf)}<div class="kl-hai"><div>Giá chào bán<b>${so(h["Giá chào bán"])} đ</b></div><div>iNAV<b>${so(h["iNAV"])} đ</b></div></div></div>
      <p class="kl-gio">Số liệu ${esc(q.luc)}. Lãi ròng nếu mua ở giá chào bán rồi bán đúng NAV: <b>${pt(h["Lãi ròng nếu về NAV %"], 2)}</b>, ngưỡng từ ${so(q.nguong.lai_rong)}%.</p>
      ${h["Cảnh báo"] ? `<div class="bao">${hinh("canh")}<p>${esc(h["Cảnh báo"])}.</p></div>` : ""}</div>
    <section class="khoi"><h3 class="le">Số lúc lập báo cáo</h3>${mr("Chiết khấu so với NAV", dlCot(q.chiet_khau, h), true)}${mr("Giá, xu hướng và thanh khoản", dlCot(q.quy, g), false)}</section>
    ${khoiTrangCu("giá và iNAV trực tiếp, nến, giá so với iNAV trong phiên, mức theo kịp chỉ số")}
    <p class="chan le">Sàng lọc theo số liệu, không phải khuyến nghị đầu tư.</p></div>`;
}
function moETF(ma, tu) {
  if (!S.etf || !S.etf.co || !S.etf.chiet_khau.dong.some((x) => x["Mã"] === ma)) return;
  S.ma = ma; S.loai = "etf"; S.trangCu = null; ghiDiaChi(); moTo(veQuy(ma), tu); to.scrollTop = 0; napTrangCu();
}

/* Phái sinh */
const timHD = (ma) => { for (const n of (S.ps && S.ps.nhom) || []) { const h = n.hop_dong.find((x) => x.ma === ma && !x.thieu_dao_han); if (h) return [h, n]; } return null; };
function dongPS(h) {
  if (h.thieu_dao_han) return `<li><div class="dong rong le"><span class="dong-ma">${esc(h.ma)}</span><span></span><span class="dong-kl tt">Thiếu ngày đáo hạn</span><span class="dong-phu">Bảng giá Vietcap lỗi nên chưa tính được basis.</span></div></li>`;
  const so4 = [["Giá", so(h.gia, 1)], ["Basis", pt(h.basis_pt, 2)], ["KL phiên", so(h.kl)], ["Ký quỹ 1 hợp đồng", `${so(h.ky_quy / 1e6, 1)} triệu`]];
  return `<li><button class="dong rong le" type="button" data-ps="${esc(h.ma)}"><span class="dong-ma">${esc(h.ma)}</span>${thuocTT(h.basis_pt, BIEN_THUOC.ps)}<span class="dong-kl ${h.basis > 0 ? "re" : h.basis < 0 ? "dat" : "tt"}">Basis ${dau(h.basis, 2)}</span><span class="dong-phu">${esc(h.thang)} · giao dịch cuối ${ngay(h.gd_cuoi)} · còn ${so(h.con_ngay)} ngày</span><span class="dong-nho">Năm hóa ${pt(h.nam_hoa, 2)}</span><span class="dong-so">${so4.map(([a, b]) => `<span>${a}<b>${b}</b></span>`).join("")}</span></button></li>`;
}
function vePS() {
  const q = S.ps;
  $("#pane-phai-sinh").innerHTML = `<div class="pane-trong"><div class="pane-dau le"><h1>Phái sinh</h1><p>Hợp đồng tương lai chỉ số. Giá là nến ngày Vietcap lấy lúc ${gioPhut(q.luc)}, nhớ tối đa ${so(q.nho_phut)} phút; trong phiên là giá khớp gần nhất.</p></div>
    ${q.canh_bao.length ? `<div class="le"><div class="bao">${hinh("canh")}<p>${esc(q.canh_bao.join("; "))}.</p></div></div>` : ""}
    ${q.nhom.map((n) => `<div class="phu-de le">Hợp đồng tương lai ${esc(n.chi_so)}<small>${esc(n.chi_so)} ${so(n.diem, 2)} điểm, giá ngày ${ngay(n.ngay)} · ký quỹ ban đầu ${so(n.ty_le_ky_quy)}% (${esc(q.nguon_ky_quy)})</small></div><ul class="ds">${n.hop_dong.map(dongPS).join("") || `<li class="trong le">Biểu đồ Vietcap chưa có giá hợp đồng ${esc(n.chi_so)}.</li>`}</ul>`).join("")}
    <div class="ghi le"><p>Basis = giá hợp đồng − chỉ số cơ sở. Basis năm hóa đặt cạnh lãi suất phi rủi ro r = ${so(q.r, 1)}% mỗi năm (giả định, dùng chung với định giá chứng quyền) để bạn tự so. Chưa có tiêu chí "nên xem xét" cho hợp đồng tương lai nên tab này không xếp nhóm.</p></div>
    <div class="khoi">${mr("Basis là gì", `<p>${esc(q.giai_thich)}</p>`, false)}</div>
    <p class="chan le">Thước: chấm là giá hợp đồng, vạch vàng là chỉ số cơ sở. Không phải khuyến nghị đầu tư.</p></div>`;
}
function veHD(h, n) {
  demMr = 0;
  const o = (ten, giaTri) => `<div><span>${ten}</span><b>${giaTri}</b></div>`;
  return dauTo(h.ma, `Hợp đồng tương lai ${n.chi_so} · ${h.thang}`, "") + `<div class="to-than">
    <div class="kl le"><h2>Basis ${dau(h.basis, 2)} điểm, ${pt(h.basis_pt, 2)} so với ${esc(n.chi_so)}</h2>
      <div class="kl-thuoc">${thuocTT(h.basis_pt, BIEN_THUOC.ps)}<div class="kl-hai"><div>Giá hợp đồng<b>${so(h.gia, 1)}</b></div><div>${esc(n.chi_so)} cùng ngày<b>${so(h.S, 2)}</b></div></div></div>
      <p class="kl-gio">Giá ngày ${ngay(h.ngay_gia)}, lấy lúc ${gioPhut(S.ps.luc)}. Ngày giao dịch cuối ${ngay(h.gd_cuoi)}, còn ${so(h.con_ngay)} ngày (${so(h.so_phien)} phiên).</p></div>
    <section class="khoi"><h3 class="le">Số chính</h3>
      <div class="so-3 le">${o("Basis năm hóa", pt(h.nam_hoa, 2))}${o("Lãi suất phi rủi ro (giả định)", `${so(S.ps.r, 1)}%`)}${o("KL phiên", so(h.kl))}</div>
      <div class="so-3 le">${o("Ký quỹ 1 hợp đồng", `${so(h.ky_quy / 1e6, 1)} triệu`)}${o("Tỷ lệ ký quỹ ban đầu", `${so(n.ty_le_ky_quy)}%`)}${o("1 điểm", `${so(S.ps.he_so_nhan)} đ`)}</div>
      <div class="ghi le"><p>Còn ít ngày thì basis năm hóa bị phóng đại: khi đó xem basis theo điểm. Ký quỹ theo ${esc(S.ps.nguon_ky_quy)}.</p></div></section>
    ${khoiTrangCu("nến, sổ lệnh, basis theo ngày, lãi lỗ nếu giữ đến đáo hạn sau phí và thuế")}
    <p class="chan le">Chưa có tiêu chí "nên xem xét" cho hợp đồng tương lai. Không phải khuyến nghị đầu tư.</p></div>`;
}
function moPS(ma, tu) {
  const kq = timHD(ma); if (!kq) return;
  S.ma = ma; S.loai = "ps"; S.trangCu = null; ghiDiaChi(); moTo(veHD(kq[0], kq[1]), tu); to.scrollTop = 0; napTrangCu();
}

/* Trang phân tích cũ của từng mã, đặt trong khung: số và biểu đồ do trang cũ tự tính theo giá lúc mở */
// biến màu của trang cũ → màu của web này (đọc lúc vẽ nên theo đúng chế độ sáng / tối đang bật)
const BIEN_CU = [["--nen", "--mat"], ["--be-mat", "--mat"], ["--chu", "--muc"], ["--chu-phu", "--muc-2"], ["--chu-mo", "--muc-3"], ["--luoi", "--ke"], ["--truc", "--ke"], ["--vien", "--ke"], ["--xanh", "--s1"], ["--cam", "--s2"], ["--lien-ket", "--nhan"], ["--tot", "--tang-dam"], ["--canh-bao", "--vang"], ["--chu-duong", "--tang"], ["--chu-am", "--giam"], ["--nut", "--navy"]];
function khungCu(html) {
  const cs = getComputedStyle(document.documentElement), lay = (ten) => cs.getPropertyValue(ten).trim();
  const kieu = `<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700&display=swap"><style>:root:root:root{color-scheme:${dangToi() ? "dark" : "light"};${BIEN_CU.map(([cu, moi]) => `${cu}:${lay(moi)}`).join(";")}}html,body{background:transparent;overflow:hidden}body{font-family:${lay("--chu")}}main{max-width:none;margin:0;padding:0 0 8px}.dau-trang h1,footer{display:none}.the,.o-so{border-radius:6px}</style>`;
  return html.replace("</head>", `${kieu}</head>`);
}
function veTrangCu() {
  const cho = $("#cho-cu", to); if (!cho || !S.trangCu) return;
  cho.className = "le"; cho.innerHTML = `<iframe class="khung-bd" id="khung-cu" title="Phân tích ${esc(S.ma)} theo giá lúc này" sandbox="allow-scripts"></iframe>`;
  const khung = cho.firstElementChild; khung.style.height = "900px"; khung.srcdoc = khungCu(S.trangCu);
}
async function napTrangCu() {
  const cho = $("#cho-cu", to), ma = S.ma, loai = S.loai; if (!cho || !ma) return;
  const dd = { cw: `/api/chung-quyen/${ma}/trang-cu`, etf: `/api/etf/${ma}/trang-cu`, ps: `/api/phai-sinh/${ma}/trang-cu` }[loai]; if (!dd) return;
  try { const d = await api(dd); if (S.ma !== ma || S.loai !== loai || !cho.isConnected) return; S.trangCu = d.html; veTrangCu(); }
  catch (e) { if (S.ma === ma && cho.isConnected) { cho.className = "loi le"; cho.textContent = `Không tải được phần phân tích theo giá lúc này. ${e.message}`; } }
}
function moDuongCu(dd) {
  let m;
  if ((m = /^\/cw\/([A-Z0-9]{4,12})$/.exec(dd))) moCW(m[1], null);
  else if ((m = /^\/etf\/([A-Z0-9]{3,12})$/.exec(dd))) moETF(m[1], null);
  else if ((m = /^\/phai-sinh\/(VN(?:30|100)F[12][MQ])$/.exec(dd))) moPS(m[1], null);
  else if (/^\/huong-dan(#[\w-]*)?$/.test(dd)) window.open(CW_CU + dd, "_blank", "noopener");
  else if (/^https:\/\//.test(dd)) window.open(dd, "_blank", "noopener");
  else { const i = { "/": 2, "/etf": 3, "/phai-sinh": 4 }[dd]; if (i) { dongTo(false); datDangXem(i, true); } }
}
// khung báo chiều cao nội dung và cú bấm vào liên kết; chỉ nghe đúng khung đang mở
addEventListener("message", (e) => {
  const khung = $("#khung-cu", to), d = e.data; if (!khung || e.source !== khung.contentWindow || !d || d.nguon !== "cw_scanner") return;
  if (d.loai === "cao" && Number.isFinite(d.cao)) khung.style.height = `${Math.min(Math.max(Math.ceil(d.cao), 200), 30000)}px`;
  else if (d.loai === "mo" && typeof d.duong_dan === "string") moDuongCu(d.duong_dan);
});

/* Nạp dữ liệu ba tab và mục "Chứng quyền và ETF" của tab Hôm nay */
function veHnKhac() {
  const cho = $("#hn-khac"); if (!cho) return; const o = [];
  if (S.cq && S.cq.co) { const xx = S.cq.cw.filter((c) => c.nhom === "NÊN XEM XÉT"); o.push(`<div><b>Chứng quyền đạt cả 4 tiêu chí: ${so(xx.length)}</b>${xx.length ? `<div class="the-ma">${xx.slice(0, SO_THE).map((c) => `<button type="button" class="o-ma" data-cw="${esc(c.ma)}">${esc(c.ma)}<small>${esc(c.chu_dat_re)}</small></button>`).join("")}</div>` : ""}<p>Lần quét ${esc(S.cq.lan_quet)}; IV − HV thấp nhất trước.</p></div>`); }
  if (S.etf && S.etf.co) { const dat = S.etf.chiet_khau.dong.filter((h) => h["Đạt"]); o.push(`<div><b>Quỹ ETF mua được dưới NAV đủ ngưỡng: ${so(dat.length)}</b>${dat.length ? `<div class="the-ma">${dat.slice(0, SO_THE).map((h) => `<button type="button" class="o-ma" data-etf="${esc(h["Mã"])}">${esc(h["Mã"])}<small>Lãi ròng ${pt(h["Lãi ròng nếu về NAV %"], 2)}</small></button>`).join("")}</div>` : ""}<p>Số liệu ${esc(S.etf.luc)}.</p></div>`); }
  cho.hidden = !o.length; cho.innerHTML = o.length ? `<h3 class="le">Chứng quyền và ETF</h3><div class="nb le">${o.join("")}</div>` : "";
}
async function napCQ() { try { S.cq = await api("/api/chung-quyen"); S.cqHien = SO_DONG; veCQ(); veHnKhac(); } catch (e) { loiPane("chung-quyen", "Chứng quyền", e); } }
async function napETF() { try { S.etf = await api("/api/etf"); veETF(); veHnKhac(); } catch (e) { loiPane("etf", "ETF", e); } }
// hợp đồng tương lai lấy giá trực tiếp từ Vietcap nên chỉ nạp khi mở tab (hoặc khi địa chỉ trỏ thẳng vào một hợp đồng)
let choPS = null;
function napPS() { if (!choPS) choPS = api("/api/phai-sinh").then((d) => { S.ps = d; vePS(); }).catch((e) => { choPS = null; loiPane("phai-sinh", "Phái sinh", e); }); return choPS; }

/* Dấu "!" giải thích: máy tính rê chuột vào thì hiện, rê ra thì mất; điện thoại bấm để hiện, bấm chỗ khác để tắt */
const noi = document.createElement("div"); noi.id = "noi"; noi.setAttribute("role", "tooltip"); app.appendChild(noi);
let nutNoi = null;
function dongNoi() { if (!nutNoi) return; nutNoi.setAttribute("aria-expanded", "false"); nutNoi.removeAttribute("aria-describedby"); nutNoi = null; noi.classList.remove("mo", "thuc-don"); }
function moNoi(n) {
  if (nutNoi === n) return; dongNoi(); nutNoi = n; noi.textContent = n.dataset.ct; n.setAttribute("aria-expanded", "true"); n.setAttribute("aria-describedby", "noi");
  const a = app.getBoundingClientRect(), r = n.getBoundingClientRect(), w = noi.offsetWidth, h = noi.offsetHeight, tren = r.top - a.top - h - 8;
  noi.style.left = `${Math.min(Math.max(r.left - a.left + r.width / 2 - w / 2, 12), Math.max(a.width - w - 12, 12))}px`;
  noi.style.top = `${tren >= 8 ? tren : r.bottom - a.top + 8}px`; noi.classList.add("mo");
}
app.addEventListener("mouseover", (e) => { if (!chuotThat.matches) return; const n = e.target.closest(".ct"); if (n) moNoi(n); });
app.addEventListener("mouseout", (e) => { if (chuotThat.matches && e.target.closest(".ct")) dongNoi(); });
app.addEventListener("focusin", (e) => { const n = e.target.closest(".ct"); if (n && n.matches(":focus-visible")) moNoi(n); });
app.addEventListener("focusout", (e) => { if (e.target.closest(".ct")) dongNoi(); });
app.addEventListener("scroll", dongNoi, { capture: true, passive: true });
app.addEventListener("input", (e) => {
  if (e.target.id !== "cq-tim") return;
  S.cqTim = e.target.value; S.cqHien = SO_DONG;
  // đang lọc theo nhóm mà gõ tìm: tìm trên cả danh sách, như ô tìm của bảng "Tất cả" ở trang cũ
  if (S.cqTim.trim() && S.cqLoc !== "tat") { S.cqLoc = "tat"; $$("[data-cq-loc]").forEach((x) => x.setAttribute("aria-pressed", x.dataset.cqLoc === "tat")); }
  veDsCQ();
});

/* ---------- Tài khoản được duyệt và hai vai (lát 5a) ---------- */
// Máy chủ quyết định ai vào được (hỏi dịch vụ coin, tra bảng tài khoản đã duyệt); ở đây chỉ hiện đúng trạng thái đó.
let TK = null, daBatDau = false;
const tenTat = (d) => { const tu = (d.ten || d.email || "?").trim().split(/\s+/); return ((tu[0] || "?")[0] + (tu.length > 1 ? tu[tu.length - 1][0] : (tu[0] || "")[1] || "")).toUpperCase(); };
const dinhDanh = (d) => d.email || d.username || d.ten;
// giờ máy chủ lưu là UTC; hiện theo giờ của máy đang xem, kiểu "08:39 ngày 25/11"
const hai = (n) => String(n).padStart(2, "0");
const lucVN = (iso) => { if (!iso) return "chưa có"; const d = new Date(iso); return `${hai(d.getHours())}:${hai(d.getMinutes())} ngày ${hai(d.getDate())}/${hai(d.getMonth() + 1)}`; };
// Màn hình chắn: chờ duyệt, bị khóa hoặc chưa hỏi được máy chủ. Che toàn bộ web, không có số liệu nào phía sau được nạp.
function veCong(tieuDe, doan, coThuLai) {
  let c = $("#dang-nhap"); if (!c) { c = document.createElement("section"); c.id = "dang-nhap"; c.setAttribute("aria-label", "Trạng thái tài khoản"); app.appendChild(c); }
  c.innerHTML = `<div class="luoi" aria-hidden="true"></div><div class="dn le"><div class="dn-logo"><div class="dn-bt" aria-hidden="true"><b>B</b><i>T</i></div><div class="dn-invest">INVEST</div></div>
    <div class="dn-form"><h1 class="dn-tieu">${esc(tieuDe)}</h1>${doan.map((d) => `<p class="dn-ghi">${esc(d)}</p>`).join("")}
      ${coThuLai ? `<button class="nut-chinh" type="button" id="cong-thu">Kiểm tra lại</button>` : ""}${TK ? `<a class="dn-ra" href="${esc(TK.dang_xuat)}">Đăng xuất</a>` : ""}</div></div>`;
  c.classList.remove("roi");
}
function goCong() { const c = $("#dang-nhap"); if (!c) return; c.classList.add("roi"); setTimeout(() => c.remove(), itChuyenDong ? 0 : 480); }
function veNutTK() { const n = $("#nut-tk"); n.hidden = false; $("#nut-dm").hidden = false; veChuong(); $("#tk-chu").textContent = tenTat(TK); n.setAttribute("aria-label", `Tài khoản ${TK.ten}`); }
async function vaoCong() {
  let d;
  try { d = await api("/api/toi"); }
  catch (e) { if (!e.daChuyen) veCong("Chưa vào được", [e.message, "Máy chủ không xác nhận được bạn là ai nên chưa mở số liệu."], true); return; }
  TK = d;
  if (d.trang_thai === "cho_duyet") { veCong("Tài khoản đang chờ duyệt", [`Bạn đã đăng nhập bằng ${dinhDanh(d)}.`, "Quản trị cần duyệt tài khoản này trước khi bạn xem được số liệu."], true); return; }
  if (d.trang_thai !== "da_duyet") { veCong("Tài khoản đã bị khóa", [`Tài khoản ${dinhDanh(d)} không còn được xem số liệu.`, "Liên hệ Quản trị nếu bạn cho rằng đây là nhầm lẫn."], false); return; }
  goCong(); veNutTK();
  if (!daBatDau) { daBatDau = true; batDau(); }
}
/* Thực đơn tài khoản (góc trên) và tờ Tài khoản của Quản trị */
function moThucDonTK(n) {
  if (nutNoi === n) { dongNoi(); return; }
  dongNoi(); nutNoi = n; n.setAttribute("aria-expanded", "true"); noi.classList.add("thuc-don");
  noi.innerHTML = `<div class="tk-ai"><b>${esc(TK.ten)}</b><span>${esc([TK.email || TK.username, TK.ten_vai, TK.che_do === "dev" ? "chế độ thử tại máy" : ""].filter(Boolean).join(" · "))}</span></div>${TK.vai === "quan_tri" ? `<button type="button" data-tk="ds">Tài khoản của đội</button>` : ""}<button type="button" data-tk="ra">Đăng xuất</button>`;
  const a = app.getBoundingClientRect(), r = n.getBoundingClientRect();
  noi.style.left = `${Math.max(Math.min(r.right - a.left - noi.offsetWidth, a.width - noi.offsetWidth - 12), 12)}px`; noi.style.top = `${r.bottom - a.top + 8}px`; noi.classList.add("mo");
}
function dongTK(u, toi) {
  const laToi = u.id === toi, n = (viec, chu, vai) => `<button type="button" class="nut-nho" data-tk-viec="${viec}" data-id="${u.id}"${vai ? ` data-vai="${vai}"` : ""}>${chu}</button>`;
  const nut = u.trang_thai === "cho_duyet" ? n("duyet", "Duyệt") + n("khoa", "Từ chối")
    : u.trang_thai === "khoa" ? n("duyet", "Mở khóa")
    : (u.vai === "quan_tri" ? n("vai", "Đổi thành Nhân viên", "nhan_vien") : n("vai", "Đổi thành Quản trị", "quan_tri")) + n("khoa", "Khóa");
  return `<li class="tk-dong le"><div><b>${esc(u.ten)}${laToi ? " (bạn)" : ""}</b><span>${esc([u.email || u.username, u.ten_vai].filter(Boolean).join(" · "))}</span><span>Mở web lần cuối ${lucVN(u.thay_luc)}${u.duyet_luc ? ` · duyệt ${lucVN(u.duyet_luc)}` : ""}</span></div><div class="tk-nut">${nut}</div></li>`;
}
function veTaiKhoan(d, loi) {
  const nhom = [["cho_duyet", "Chờ duyệt"], ["da_duyet", "Đã duyệt"], ["khoa", "Đã khóa"]].map(([k, ten]) => { const ds = d.tai_khoan.filter((u) => u.trang_thai === k); return ds.length || k === "cho_duyet" ? `<section class="khoi"><h3 class="le">${ten} (${so(ds.length)})</h3>${ds.length ? `<ul class="ds-tk">${ds.map((u) => dongTK(u, d.toi)).join("")}</ul>` : `<p class="trong le">Không có ai đang chờ.</p>`}</section>` : ""; }).join("");
  return dauTo("Tài khoản", "Duyệt người vào web và đặt vai", "") + `<div class="to-than">${loi ? `<p class="loi le" role="alert">${esc(loi)}</p>` : ""}${nhom}
    <p class="chan le">Ai đăng nhập bằng tài khoản coin lần đầu sẽ hiện ở mục Chờ duyệt. Nhân viên xem được mọi số liệu; chỉ Quản trị duyệt, khóa và đổi vai. Mỗi lần duyệt, khóa, đổi vai đều được ghi nhật ký.</p></div>`;
}
async function moTaiKhoan(loi) {
  S.ma = null; S.loai = "tk";
  if (to.hidden) moTo(`${dauTo("Tài khoản", "Duyệt người vào web và đặt vai", "")}<div class="to-than"><div class="dang-ve">Đang nạp danh sách…</div></div>`, null);
  try { const d = await api("/api/tai-khoan"); if (S.loai === "tk") $(".to-trong", to).innerHTML = veTaiKhoan(d, loi); }
  catch (e) { if (S.loai === "tk") $(".to-than", to).innerHTML = `<p class="loi le">Không nạp được danh sách tài khoản. ${esc(e.message)}</p>`; }
}
async function lamViecTK(n) {
  const { tkViec: viec, id, vai } = n.dataset; let loi = "";
  $$("[data-tk-viec]", to).forEach((x) => { x.disabled = true; });
  try { await api(`/api/tai-khoan/${encodeURIComponent(id)}/${viec}`, viec === "vai" ? { vai } : {}); }
  catch (e) { loi = e.message; }
  await moTaiKhoan(loi);
}

/* ---------- Danh mục 4 loại của từng người (lát 5b) ---------- */
// Web này chỉ lưu lệnh; vị thế, giá vốn bình quân và lãi lỗ do dịch vụ chứng quyền tính (công thức người dùng duyệt 25/11/2026).
const TEN_LOAI = { cp: "Cổ phiếu", cw: "Chứng quyền", etf: "ETF", hd: "Hợp đồng tương lai" };
const DON_VI = { cp: "cổ phiếu", cw: "chứng quyền", etf: "chứng chỉ quỹ", hd: "hợp đồng" };
const MUC_BAN = { 1: ["Cân nhắc bán", "tt"], 2: ["Nên bán", "dat"] };
const tien = (v) => (thieu(v) ? "—" : `${dau(v, 0)} đ`);
const lopLai = (v) => (thieu(v) || v === 0 ? "tt" : v > 0 ? "re" : "dat");
const maYeuCau = () => (window.crypto && crypto.randomUUID ? crypto.randomUUID() : `yc-${Date.now()}-${Math.random().toString(36).slice(2, 14)}`);
const homNayISO = () => { const d = new Date(); return `${d.getFullYear()}-${hai(d.getMonth() + 1)}-${hai(d.getDate())}`; };
const duoiNguoi = () => (S.dm && S.dm.nguoi ? `?nguoi=${S.dm.nguoi}` : "");
// thước của một vị thế: lấy số đã có sẵn của từng loại (upside đợt định giá, đắt rẻ lúc quét, chiết khấu so với iNAV, basis)
function thuocDM(loai, r) {
  const trong = "<span></span>";
  if (loai === "cp") return thieu(r.upside) || r.upside <= -1 ? trong : thuoc((1 / (1 + r.upside) - 1) * 100, BIEN_THUOC.cw);
  if (loai === "cw") { const c = S.cq && S.cq.co && S.cq.cw.find((x) => x.ma === r.ma); return c && !thieu(c.dat_re) ? thuoc(c.dat_re, BIEN_THUOC.cw) : trong; }
  if (loai === "etf") { const h = S.etf && S.etf.co && S.etf.chiet_khau.dong.find((x) => x["Mã"] === r.ma), ck = h ? h["Chiết khấu mua được %"] : null; return thieu(ck) ? trong : thuoc(ck, BIEN_THUOC.etf); }
  return r.co_gia && r.chi_so_diem ? thuocTT((r.gia / r.chi_so_diem - 1) * 100, BIEN_THUOC.ps) : trong;
}
const so4DM = (cap) => `<span class="dong-so">${cap.map(([a, b]) => `<span>${a}<b>${b}</b></span>`).join("")}</span>`;
function dongDM(loai, r) {
  if (loai === "hd") {
    const ten = r.ma_nay || r.ma, n = Math.abs(r.so_hd), phu = `${r.so_hd > 0 ? "Long" : "Short"} ${so(n)} hợp đồng ${esc(r.chi_so)} · giao dịch cuối ${ngay(r.gd_cuoi)}`;
    if (!r.co_gia) return `<li><div class="dong rong le"><span class="dong-ma">${esc(ten)}</span><span></span><span class="dong-kl tt">${r.het_han ? "Đã qua ngày giao dịch cuối" : "Chưa có giá"}</span><span class="dong-phu">${phu}</span>${so4DM([["Giá mở", so(r.gia_mo, 1)], ...(r.het_han ? [["Việc cần làm", "ghi lệnh đóng ở giá thanh toán cuối cùng"]] : [])])}</div></li>`;
    return `<li><button class="dong rong le" type="button" data-ps="${esc(ten)}"><span class="dong-ma">${esc(ten)}</span>${thuocDM(loai, r)}<span class="dong-kl ${lopLai(r.lai)}">${tien(r.lai)}</span><span class="dong-phu">${phu} · còn ${so(r.con_ngay)} ngày</span><span class="dong-nho">sau phí và thuế</span>${so4DM([["Giá mở", so(r.gia_mo, 1)], ["Giá hiện tại", so(r.gia, 1)], ["Lãi lỗ gộp", tien(r.lai_gop)], ["Ký quỹ ước tính", `${so(r.ky_quy / 1e6, 1)} triệu`]])}</button></li>`;
  }
  const mo = { cp: "data-ma", cw: "data-cw", etf: "data-etf" }[loai], dv = DON_VI[loai];
  if (!r.co_gia) return `<li><div class="dong rong le"><span class="dong-ma">${esc(r.ma)}</span><span></span><span class="dong-kl tt">Chưa có giá</span><span class="dong-phu">${so(r.so_luong)} ${dv}</span>${so4DM([["Giá vốn", so(r.gia_von, 1)]])}</div></li>`;
  const tt = loai === "cw" && r.trang_thai && MUC_BAN[r.trang_thai.muc];
  const cap = [["Giá vốn", so(r.gia_von, 1)], [r.co_nguoi_mua ? "Giá chờ mua" : "Giá khớp (không ai chờ mua)", so(r.gia_ban)], ["Giá trị theo giá bán", `${so(r.gia_ban * r.so_luong / 1e6, 1)} triệu`]];
  if (loai === "cw") cap.push(["Còn", thieu(r.con_ngay) ? "—" : `${so(r.con_ngay)} ngày để bán`], ["Đòn bẩy", thieu(r.don_bay) ? "—" : `${so(r.don_bay, 1)}x`]);
  return `<li><button class="dong rong le" type="button" ${mo}="${esc(r.ma)}"><span class="dong-ma">${esc(r.ma)}</span>${thuocDM(loai, r)}<span class="dong-kl ${lopLai(r.lai)}">${tien(r.lai)}</span><span class="dong-phu">${so(r.so_luong)} ${dv}${loai === "cw" ? ` · ${esc(r.cs)}` : ""}${tt ? ` · <b class="${tt[1]}">${tt[0]}</b>` : ""}</span><span class="dong-nho">${pt(r.lai_pct * 100, 2)}</span>${so4DM(cap)}${tt && r.trang_thai.ly_do.length ? `<span class="dong-so"><span>${esc(r.trang_thai.ly_do.map((x) => x[1] || x[0]).filter(Boolean).join("; "))}</span></span>` : ""}</button></li>`;
}
function formDM() {
  const f = S.dm.form, hd = f.loai === "hd", ds = { cp: S.ds.map((r) => r.ma), cw: S.cq && S.cq.co ? S.cq.cw.map((c) => c.ma) : [], etf: S.etf && S.etf.co ? S.etf.quy.dong.map((h) => h["Mã"]) : [] }[f.loai] || [];
  const hopDong = hd && S.ps ? S.ps.nhom.flatMap((n) => n.hop_dong.filter((h) => !h.thieu_dao_han).map((h) => `<option value="${esc(h.ma)}">${esc(h.ma)} · ${esc(h.thang)} · giao dịch cuối ${ngay(h.gd_cuoi)}</option>`)).join("") : "";
  const oMa = hd ? `<select id="dm-ma">${hopDong || `<option value="">Chưa nạp được danh sách hợp đồng</option>`}</select>` : `<input id="dm-ma" type="text" list="dm-goi" autocomplete="off" autocapitalize="characters" spellcheck="false" placeholder="${{ cp: "VRE", cw: "CVRE2609", etf: "E1VFVN30" }[f.loai]}"><datalist id="dm-goi">${ds.slice(0, 600).map((m) => `<option value="${esc(m)}">`).join("")}</datalist>`;
  return `<section class="khoi sau"><h3 class="le">Ghi lệnh</h3><div class="dm-form le">
    <div class="loc" role="group" aria-label="Loại tài sản">${Object.entries(TEN_LOAI).map(([k, ten]) => `<button type="button" data-dm-loai="${k}" aria-pressed="${f.loai === k}">${ten}</button>`).join("")}</div>
    <div class="chon-2" role="group" aria-label="Chiều lệnh"><button type="button" data-dm-chieu="MUA" aria-pressed="${f.chieu === "MUA"}">${hd ? "Mua (Long)" : "Mua"}</button><button type="button" data-dm-chieu="BAN" aria-pressed="${f.chieu === "BAN"}">${hd ? "Bán (Short)" : "Bán"}</button></div>
    <label class="truong">Mã${oMa}</label>
    <div class="truong-2"><label class="truong">Số lượng (${DON_VI[f.loai]})<input id="dm-sl" type="number" inputmode="numeric" min="1" step="${f.loai === "cw" ? 100 : 1}"></label>
      <label class="truong">Giá (${hd ? "điểm" : "đồng"})<input id="dm-gia" type="number" inputmode="decimal" min="0" step="any" placeholder="${hd ? "1790,5" : "23000"}"></label></div>
    <label class="truong">Ngày giao dịch<input id="dm-ngay" type="date" max="${homNayISO()}" value="${homNayISO()}"></label>
    ${hd ? "" : `<div class="truong-2"><label class="truong">Báo khi lãi từ (%), không bắt buộc<input id="dm-chot" type="number" inputmode="decimal" min="1" max="1000" step="any"></label><label class="truong">Báo khi lỗ từ (%), không bắt buộc<input id="dm-cat" type="number" inputmode="decimal" min="1" max="1000" step="any"></label></div>`}
    <label class="truong">Ghi chú, không bắt buộc<input id="dm-ghi-chu" type="text" maxlength="255"></label>
    <p class="loi" id="dm-loi" role="alert" hidden></p>
    <button class="nut-ghi" type="button" id="dm-ghi">Ghi lệnh</button></div></section>`;
}
function soLenhDM(lenh, cuaToi) {
  if (!lenh.length) return `<p>Chưa có lệnh nào.</p>`;
  return `<div class="cuon"><table><thead><tr><th class="trai">Ngày</th><th class="trai">Mã</th><th class="trai">Lệnh</th><th>Số lượng</th><th>Giá</th><th class="trai">Ghi chú</th>${cuaToi ? `<th></th>` : ""}</tr></thead><tbody>${lenh.map((l) => `<tr><td class="trai">${ngay(l.ngay)}</td><td class="trai"><b>${esc(l.ma)}</b> <small>${esc(l.ten_loai)}${l.gd_cuoi ? `, giao dịch cuối ${ngay(l.gd_cuoi)}` : ""}</small></td><td class="trai ${l.chieu === "MUA" ? "re" : "dat"}">${l.chieu === "MUA" ? "Mua" : "Bán"}</td><td>${so(l.so_luong)}</td><td>${so(l.gia, l.loai === "hd" ? 1 : 0)}</td><td class="trai">${esc(l.ghi_chu || "")}</td>${cuaToi ? `<td><button type="button" class="nut-nho" data-dm-xoa="${l.id}">Xóa</button></td>` : ""}</tr>`).join("")}</tbody></table></div>`;
}
function veDanhMuc() {
  demMr = 0;
  const m = S.dm, d = m.d, cuaToi = !m.nguoi, quanTri = TK.vai === "quan_tri";
  const chon = quanTri && m.ds ? `<div class="le"><label class="truong">Xem danh mục của<select id="dm-nguoi"><option value="">Tôi (${esc(TK.ten)})</option>${m.ds.filter((u) => u.id !== TK.id).map((u) => `<option value="${u.id}"${m.nguoi === u.id ? " selected" : ""}>${esc(u.ten)}${u.email ? ` · ${esc(u.email)}` : ""} · ${so(u.so_lenh)} lệnh</option>`).join("")}</select></label></div>` : "";
  let than;
  if (!d) than = `<div class="dang-ve le">Đang tải giá và tính danh mục…</div>`;
  else if (d.loi) than = `<p class="loi le" role="alert">Chưa tính được danh mục. ${esc(d.loi)}</p>`;
  else if (d.trong) than = `<p class="trong le">${cuaToi ? "Danh mục của bạn chưa có lệnh nào. Ghi lệnh mua đầu tiên ở bên dưới." : "Tài khoản này chưa ghi lệnh nào."}</p>`;
  else {
    const tat = ["cp", "cw", "etf", "hd"].flatMap((k) => d[k].map((r) => [k, r])), coGia = tat.filter(([, r]) => r.co_gia), tong = coGia.reduce((s, [, r]) => s + r.lai, 0), chot = d.da_dong.reduce((s, r) => s + r.lai_da_chot, 0);
    const nhom = ["cp", "cw", "etf", "hd"].filter((k) => d[k].length).map((k) => `<div class="phu-de le">${TEN_LOAI[k]}<small>${so(d[k].length)} vị thế</small></div><ul class="ds">${d[k].map((r) => dongDM(k, r)).join("")}</ul>`).join("");
    than = `<div class="kl le"><h2 class="${lopLai(tong)}">${coGia.length ? tien(tong) : "Chưa có giá"}</h2>
        <p class="kl-gio">Lãi lỗ nếu bán hết ${so(coGia.length)} vị thế có giá ngay lúc này, đã trừ phí và thuế.${tat.length > coGia.length ? ` ${so(tat.length - coGia.length)} vị thế chưa có giá nên chưa tính.` : ""} Lãi lỗ đã chốt từ các lệnh bán: <b>${tien(chot)}</b>. Giá lấy lúc ${gioPhut(d.luc)} ngày ${ngay(String(d.luc).slice(0, 10))}.</p>
        ${d.loi_gia.map((x) => `<div class="bao">${hinh("canh")}<p>${esc(x)}.</p></div>`).join("")}</div>
      ${d.canh_bao.length ? `<section class="khoi"><h3 class="le">Tín hiệu của các vị thế đang nắm</h3><ul class="huy le">${d.canh_bao.map((c) => `<li><b>${esc(c.ma)}</b>: ${esc(c.noi_dung)}</li>`).join("")}</ul></section>` : ""}
      ${nhom || `<p class="trong le">Không còn vị thế nào đang mở.</p>`}`;
  }
  const p = d && d.phi;
  $(".to-trong", to).innerHTML = dauTo("Danh mục", cuaToi ? "Của bạn" : `Của ${((m.ds || []).find((u) => u.id === m.nguoi) || {}).ten || "người khác"}, chỉ xem`, `<button type="button" class="nut-nho" id="dm-tai">Tải lại giá</button>`) + `<div class="to-than">${chon}
    ${cuaToi && !quanTri ? `<div class="ghi le"><p>Quản trị xem được danh mục này, nhưng không sửa được.</p></div>` : ""}
    ${than}
    ${cuaToi ? formDM() : ""}
    <section class="khoi sau"><h3 class="le">Sổ lệnh</h3>${mr(`${so(m.lenh ? m.lenh.length : 0)} lệnh đang có hiệu lực`, m.lenh ? soLenhDM(m.lenh, cuaToi) : "<p>Đang nạp…</p>", true)}</section>
    <p class="chan le">Cổ phiếu, chứng quyền, ETF: lãi lỗ nếu bán ngay ở giá chờ mua cao nhất${p ? `, đã trừ phí ${so(p.giao_dich_pct, 2)}% mỗi chiều và thuế bán ${so(p.thue_ban_pct, 1)}%` : ""}; giá vốn bình quân đã gồm phí mua. Hợp đồng tương lai: theo giá khớp gần nhất${p ? `, trừ phí ${so(p.hd_phi_moi_lan)} đ mỗi hợp đồng mỗi lần và thuế ${so(p.hd_thue_pct, 1)}% × giá × ${so(p.hd_he_so_nhan)} × tỷ lệ ký quỹ ÷ 2` : ""}. Mức phí và cách tính thuế là giả định chung, khác nhau theo công ty chứng khoán; cách tính thuế hợp đồng tương lai chưa đối chiếu văn bản. Cổ tức bằng cổ phiếu và chia tách không tự điều chỉnh: hãy ghi lệnh điều chỉnh. Thước cạnh mỗi vị thế lấy từ đợt định giá hoặc lần quét gần nhất (cổ phiếu: giá trị hợp lý của đợt định giá; chứng quyền: giá hợp lý lúc quét; ETF: iNAV lúc lập báo cáo), không phải giá lúc này. Không phải khuyến nghị đầu tư.</p></div>`;
}
async function napDanhMuc() {
  const m = S.dm, duoi = duoiNguoi(); m.d = null; veDanhMuc();
  const [d, l, ds] = await Promise.all([
    api(`/api/danh-muc${duoi}`).catch((e) => ({ loi: e.message })),
    api(`/api/danh-muc/lenh${duoi}`).catch(() => ({ lenh: [] })),
    TK.vai === "quan_tri" && !m.ds ? api("/api/danh-muc/nguoi").then((x) => x.nguoi).catch(() => []) : Promise.resolve(m.ds),
  ]);
  if (S.dm !== m || S.loai !== "dm") return;
  m.d = d; m.lenh = l.lenh; m.ds = ds; veDanhMuc();
}
function moDanhMuc() {
  S.ma = null; S.loai = "dm"; S.dm = { nguoi: null, d: null, lenh: null, ds: null, form: { loai: "cp", chieu: "MUA", yc: maYeuCau() } };
  if (to.hidden) moTo(`<div class="to-than"></div>`, null);
  to.scrollTop = 0;
  napPS(); // danh sách hợp đồng cho ô chọn mã; lỗi thì ô đó báo chưa nạp được
  napDanhMuc();
}
async function ghiLenh() {
  const f = S.dm.form, o = $("#dm-loi", to), lay = (id) => { const x = $(id, to); return x ? x.value.trim() : ""; }, soHoac = (id, chia) => (lay(id) === "" ? null : Number(lay(id)) / chia);
  const than = { loai: f.loai, ma: lay("#dm-ma").toUpperCase(), chieu: f.chieu, so_luong: Number(lay("#dm-sl")), gia: Number(lay("#dm-gia")), ngay: lay("#dm-ngay"), chot_loi: soHoac("#dm-chot", 100), cat_lo: soHoac("#dm-cat", 100), ghi_chu: lay("#dm-ghi-chu") || null, ma_yeu_cau: f.yc };
  const bao = (t) => { o.textContent = t; o.hidden = false; };
  if (!than.ma) { bao("Chưa nhập mã."); return; }
  if (!Number.isInteger(than.so_luong) || than.so_luong <= 0) { bao("Số lượng phải là số nguyên dương."); return; }
  if (!(than.gia > 0)) { bao("Chưa nhập giá."); return; }
  const nut = $("#dm-ghi", to); nut.disabled = true; o.hidden = true;
  try { await api("/api/danh-muc/lenh", than); f.yc = maYeuCau(); S.dm.ds = null; await napDanhMuc(); }
  catch (e) { bao(`Chưa ghi được lệnh. ${e.message}`); nut.disabled = false; }
}
async function xoaLenh(id) {
  try { await api(`/api/danh-muc/lenh/${encodeURIComponent(id)}/xoa`, {}); S.dm.ds = null; await napDanhMuc(); }
  catch (e) { const o = $("#dm-loi", to); if (o) { o.textContent = e.message; o.hidden = false; o.scrollIntoView({ block: "center" }); } }
}
app.addEventListener("change", (e) => { if (e.target.id === "dm-nguoi" && S.dm) { S.dm.nguoi = e.target.value ? Number(e.target.value) : null; napDanhMuc(); } });

/* ---------- Cảnh báo trong web (lát 5c) ---------- */
// Web này chỉ lưu mức giá của từng người. Bất thường đang mua được, giá bây giờ của các mức và tín hiệu danh mục do dịch vụ
// chứng quyền tính. Trình duyệt hỏi tin mới mỗi phút khi còn mở; "đã báo", "chưa xem" và bật tắt âm thanh nhớ trong trình
// duyệt theo từng tài khoản (như web chứng quyền). Đóng web thì không báo: không có Discord, không có lịch chạy nền.
const SO_THONG_BAO = 5; // số thông báo của trình duyệt mỗi lượt, như SO_THONG_BAO_TOI_DA của web chứng quyền
const SO_CHUA_XEM = 30; // số tin chưa xem giữ lại
const GIAY_XET_LUOT = 10; // cứ 10 giây xét xem đã tới lượt hỏi chưa (nhiều thẻ cùng mở: chỉ một thẻ hỏi)
const TEN_CHIEU = { duoi: "xuống tới", tren: "lên tới" };
const MAU_HD = /^VN(30|100)F[12][MQ]$/;
const khoaKho = (k) => `bt.bao.${TK ? TK.id : 0}.${k}`;
const docKho = (k) => { try { return localStorage.getItem(khoaKho(k)); } catch (e) { return null; } };
const ghiKho = (k, v) => { try { localStorage.setItem(khoaKho(k), v); } catch (e) { /* trình duyệt chặn lưu: chỉ mất phần nhớ */ } };
const dsKho = (k) => { try { const d = JSON.parse(docKho(k) || "[]"); return Array.isArray(d) ? d : []; } catch (e) { return []; } };
const batAm = () => docKho("am") !== "tat";
const coTB = () => "Notification" in window;
const giaDV = (v, dv) => (thieu(v) ? "—" : `${so(v, dv === "điểm" ? 1 : 0)} ${dv}`);
const trieu = (v) => (thieu(v) ? "—" : `${so(v / 1e6, 1)} triệu`);
const chuDR = (v) => (thieu(v) ? "—" : v > 10 ? "Đắt hơn 1.000%" : v < 0 ? `Rẻ ${so(-v * 100, 1)}%` : `Đắt ${so(v * 100, 1)}%`);
let am = null;
// trình duyệt chỉ cho phát tiếng sau khi người dùng bấm vào trang ít nhất một lần
function moAm() { try { am = am || new (window.AudioContext || window.webkitAudioContext)(); if (am.state === "suspended") am.resume(); } catch (e) { /* trình duyệt không có âm thanh */ } }
function keu() { // hai tiếng "ting-tong" do trình duyệt tạo, không cần tệp âm thanh
  moAm(); if (!am) return;
  [[880, 0], [660, .3], [880, .75], [660, 1.05]].forEach(([tanSo, t]) => {
    const o = am.createOscillator(), g = am.createGain(), t0 = am.currentTime + t;
    o.frequency.value = tanSo; o.connect(g); g.connect(am.destination);
    g.gain.setValueAtTime(.0001, t0); g.gain.exponentialRampToValueAtTime(.3, t0 + .02); g.gain.exponentialRampToValueAtTime(.0001, t0 + .28);
    o.start(t0); o.stop(t0 + .3);
  });
}
// lỗi của lượt hỏi gần nhất: không hỏi được, hoặc hỏi được nhưng một phần không tính được
const loiTin = () => [...(S.tinLoi ? [`Chưa hỏi được tin mới: ${S.tinLoi}`] : []), ...(S.tin ? S.tin.loi.map((x) => `Chưa tính được ${x}`) : [])];
function veChuong() {
  const n = dsKho("chua_xem").length, hong = !n && loiTin().length > 0, nut = $("#nut-cb"), o = $("#cb-so");
  nut.hidden = false; nut.setAttribute("aria-label", n ? `Cảnh báo, ${n} tin chưa xem` : hong ? "Cảnh báo, lượt hỏi gần nhất có lỗi" : "Cảnh báo");
  o.textContent = n > 9 ? "9+" : n ? String(n) : "!"; o.hidden = !n && !hong; o.classList.toggle("hong", hong);
  document.title = n ? `(${n}) BT Invest` : "BT Invest";
}
// tin có id "ngày|loại|mã": loại quyết định tên gọi và bấm vào thì mở gì
const TEN_TIN = { cw: "Chứng quyền rẻ bất thường", giam: "Chứng quyền giảm mạnh", etf: "ETF dưới iNAV", "hd-dat": "Hợp đồng tương lai đắt", "hd-re": "Hợp đồng tương lai rẻ" };
const tenTin = (t) => { const [, loai = "", ma = ""] = String(t.id).split("|"); return TEN_TIN[loai] ? `${TEN_TIN[loai]}: ${ma}` : t.tieu_de; };
function moTin(id) {
  const [, loai = "", ma = ""] = String(id).split("|");
  if (loai === "cw" || loai === "giam") moCW(ma, null);
  else if (loai === "etf") moETF(ma, null);
  else if (loai.startsWith("hd-") && MAU_HD.test(ma)) napPS().then(() => moPS(ma, null));
  else if (loai.startsWith("dm-")) moDanhMuc();
  else moCanhBao();
}
function baoMoi(moi) {
  ghiKho("chua_xem", JSON.stringify(dsKho("chua_xem").concat(moi).slice(-SO_CHUA_XEM)));
  if (!batAm()) return;
  keu();
  if (coTB() && Notification.permission === "granted") moi.slice(0, SO_THONG_BAO).forEach((t) => {
    try { const n = new Notification(tenTin(t), { body: t.noi_dung, tag: t.id }); n.onclick = () => { window.focus(); moTin(t.id); n.close(); }; } catch (e) { /* điện thoại không cho trang tự tạo thông báo: vẫn có tiếng và số trên chuông */ }
  });
}
async function hoiTin() {
  if (!TK || TK.trang_thai !== "da_duyet") return;
  const giay = TK.hoi_canh_bao_giay || 60;
  if (Date.now() - (+docKho("lan_hoi") || 0) < (giay - GIAY_XET_LUOT / 2) * 1000) return; // chưa tới lượt, hoặc thẻ khác vừa hỏi
  ghiKho("lan_hoi", String(Date.now()));
  try {
    const d = await api("/api/canh-bao/tin");
    S.tin = d; S.tinLoi = null;
    const da = dsKho("da_bao"), moi = d.tin.filter((t) => !da.includes(t.id));
    if (moi.length) {
      const homNay = moi[0].id.split("|")[0]; // mỗi tin báo một lần mỗi ngày: bỏ id của ngày cũ
      ghiKho("da_bao", JSON.stringify(da.filter((id) => id.startsWith(homNay)).concat(moi.map((t) => t.id))));
      baoMoi(moi);
    }
  } catch (e) { S.tinLoi = e.message; } // mất mạng hoặc máy chủ lỗi: ghi lại để chuông báo, lượt sau hỏi lại
  veChuong(); veTinCB();
}
function dongMuc(m) {
  const dv = m.don_vi || (MAU_HD.test(m.ma) ? "điểm" : "đ");
  const tt = thieu(m.cham) ? ["chưa lấy được giá", "tt"] : m.cham ? ["đang chạm", "cham"] : thieu(m.gia) ? ["chưa có giá", "tt"] : ["chưa chạm", "tt"];
  return `<li class="tk-dong muc-dong le"><div><b>${esc(m.ma)}</b><span>Báo khi giá ${TEN_CHIEU[m.chieu]} ${giaDV(m.muc, dv)}${m.ghi_chu ? ` · ${esc(m.ghi_chu)}` : ""}</span><span>Giá lúc này ${giaDV(m.gia, dv)}${thieu(m.cach) ? "" : `, cách mức ${pt(m.cach * 100)}`} · <b class="trong-dong ${tt[1]}">${tt[0]}</b></span></div><div class="tk-nut"><button type="button" class="nut-nho" data-cb-xoa="${m.id}">Xóa</button></div></li>`;
}
function formMuc() {
  const f = S.cb.form, hd = S.ps ? S.ps.nhom.flatMap((n) => n.hop_dong.map((h) => h.ma)) : [];
  const ds = [...S.ds.map((r) => r.ma), ...(S.cq && S.cq.co ? S.cq.cw.map((c) => c.ma) : []), ...(S.etf && S.etf.co ? S.etf.quy.dong.map((h) => h["Mã"]) : []), ...hd];
  return `<div class="dm-form">
    <div class="chon-2" role="group" aria-label="Báo khi"><button type="button" data-cb-chieu="duoi" aria-pressed="${f.chieu === "duoi"}">Giá xuống tới</button><button type="button" data-cb-chieu="tren" aria-pressed="${f.chieu === "tren"}">Giá lên tới</button></div>
    <div class="truong-2"><label class="truong">Mã<input id="cb-ma" type="text" list="cb-goi" autocomplete="off" autocapitalize="characters" spellcheck="false" placeholder="VPB, CVPB2615, E1VFVN30, VN30F1M"><datalist id="cb-goi">${ds.slice(0, 800).map((x) => `<option value="${esc(x)}">`).join("")}</datalist></label>
      <label class="truong">Mức giá (đồng; hợp đồng tương lai: điểm)<input id="cb-muc" type="number" inputmode="decimal" min="0" step="any" placeholder="24500"></label></div>
    <label class="truong">Ghi chú, không bắt buộc<input id="cb-ghi-chu" type="text" maxlength="100"></label>
    <p class="loi" id="cb-loi" role="alert" hidden></p>
    <button class="nut-ghi" type="button" id="cb-dat">Đặt mức</button></div>`;
}
const dongKhong = (chu) => `<p class="trong le">${chu}</p>`;
const khoiCB = (ten, n, gt, than) => `<section class="khoi"><h3 class="le">${ten}<small>${so(n)}</small>${ct(gt)}</h3>${than}</section>`;
function dongCBcw(x) {
  return `<li><button class="dong rong le" type="button" data-cw="${esc(x.ma)}"><span class="dong-ma">${esc(x.ma)}</span>${thuoc(x.lech * 100, BIEN_THUOC.cw)}<span class="dong-kl re">${pt(x.lech * 100)}</span><span class="dong-phu">${esc(x.cs)} · chào bán ${so(x.gia)} đ, lẽ ra ${so(x.le_ra)} đ</span><span class="dong-nho">mua được ${trieu(x.mua_duoc)}</span>${so4DM([["Còn", `${so(x.con_ngay)} ngày để bán`], ["So với giá hợp lý", chuDR(x.dat_re)], ["Mức dao động (IV)", thieu(x.iv) ? "—" : `${so(x.iv)}%`], ["Lệch 20 phiên", thieu(x.lech_20) ? "—" : pt(x.lech_20 * 100)], ["Chờ mua", thieu(x.cho_mua) ? "—" : `${so(x.cho_mua)} đ`]])}</button></li>`;
}
function dongCBetf(x, ng) {
  const ph = !x.hd ? "không có hợp đồng tương lai cùng chỉ số" : thieu(x.so_hd) ? `${x.hd} chưa có giá chờ mua` : `bán ${so(x.so_hd, 2)} hợp đồng ${x.hd} cho lệnh ${so(ng.etf_lenh / 1e6)} triệu`;
  return `<li><button class="dong rong le" type="button" data-etf="${esc(x.ma)}"><span class="dong-ma">${esc(x.ma)}</span>${thuoc(x.ck, BIEN_THUOC.etf)}<span class="dong-kl re">${pt(x.lai_rong, 2)}</span><span class="dong-phu">${x.chi_so ? `${esc(x.chi_so)} · ` : ""}chào bán ${so(x.gia)} đ, iNAV ${so(x.inav)} đ</span><span class="dong-nho">lãi ròng nếu về iNAV</span>${so4DM([["Mua được", trieu(x.mua_duoc)], ["Thường lệch", thieu(x.thuong) ? "—" : pt(x.thuong, 2)], ["Phòng hộ", esc(ph)]])}</button></li>`;
}
function dongCBhd(x) {
  const ten = x.bi_danh || x.ma, dat = x.tin_hieu === "dat", mo = MAU_HD.test(ten);
  const trong = `<span class="dong-ma">${esc(ten)}</span>${thieu(x.lech) || !x.hop_ly ? "<span></span>" : thuocTT(x.lech / x.hop_ly * 100, BIEN_THUOC.ps)}<span class="dong-kl ${dat ? "dat" : "re"}">${dat ? "Đắt" : "Rẻ"}</span><span class="dong-phu">${dat ? `Bán hợp đồng, mua ETF ${esc(x.etf)}` : `Chỉ có lợi khi đang giữ ETF ${esc(x.etf)}`}</span><span class="dong-nho">${thieu(x.lai_khoa) ? "" : `lãi khóa ${dau(x.lai_khoa, 1)} điểm`}</span>${so4DM([["Khớp", so(x.gia, 1)], ["Cận trên", so(x.hop_ly, 1)], ["Lệch", `${dau(x.lech, 1)} điểm`], ["Còn", `${so(x.so_phien)} phiên`]])}`;
  return mo ? `<li><button class="dong rong le" type="button" data-ps="${esc(ten)}">${trong}</button></li>` : `<li><div class="dong rong le">${trong}</div></li>`;
}
const bangCBhd = (hd) => `<div class="cuon"><table><thead><tr><th class="trai">Hợp đồng</th><th>Khớp</th><th>Chỉ số</th><th>Cận trên</th><th>Lệch</th><th>Lãi khóa</th><th class="trai">Kết quả</th></tr></thead><tbody>${hd.map((x) => `<tr><td class="trai"><b>${esc(x.bi_danh || x.ma)}</b></td><td>${so(x.gia, 1)}</td><td>${so(x.S, 1)}</td><td>${so(x.hop_ly, 1)}</td><td>${dau(x.lech, 1)}</td><td>${dau(x.lai_khoa, 1)}</td><td class="trai">${x.tin_hieu ? (x.tin_hieu === "dat" ? "Đắt" : "Rẻ") : esc(x.ly_do)}</td></tr>`).join("")}</tbody></table></div>`;
function dongCBgiam(g) {
  return `<li><button class="dong rong le" type="button" data-cw="${esc(g.ma)}"><span class="dong-ma">${esc(g.ma)}</span><span></span><span class="dong-kl dat">${pt(g.giam * 100)}</span><span class="dong-phu">${g.cs ? `${esc(g.cs)} · ` : ""}${so(g.gia)} đ so với tham chiếu ${so(g.ref)} đ</span><span class="dong-nho">${g.luc ? `báo lúc ${esc(g.luc)}` : ""}</span>${so4DM([["Giá mua lúc này", thieu(g.gia_nay) ? "—" : `${so(g.gia_nay)} đ`], ["So với giá hợp lý lúc này", chuDR(g.dat_re_nay)], ["Lệch so với cổ phiếu cơ sở", thieu(g.lech) ? "—" : pt(g.lech * 100)]])}</button></li>`;
}
// bốn nhóm bất thường đang mua được: chung cho mọi người, cùng số với trang Cảnh báo của web chứng quyền
function khoiChung(c) {
  const ng = c.nguong, coHD = c.hd.filter((x) => x.tin_hieu);
  const cw = !c.da_quet ? dongKhong("Chưa có kết quả quét chứng quyền.") : c.cw.length ? `<ul class="ds">${c.cw.map(dongCBcw).join("")}</ul>` : dongKhong(`Không có chứng quyền nào đang chào bán thấp hơn mức lẽ ra từ ${so(ng.cw_lech_pct)}% trở lên.`);
  const etf = c.etf.length ? `<ul class="ds">${c.etf.map((x) => dongCBetf(x, ng)).join("")}</ul>` : dongKhong(`Không có quỹ nào đang chào bán ở giá đủ lãi ròng từ ${so(ng.etf_lai_rong_pct)}% nếu giá về iNAV.`);
  const hd = !c.hd.length ? dongKhong("Chưa lấy được giá hợp đồng tương lai.") : (coHD.length ? `<ul class="ds">${coHD.map(dongCBhd).join("")}</ul>` : dongKhong("Không có hợp đồng nào đắt hoặc rẻ quá chi phí.")) + mr("Từng hợp đồng và lý do không báo", bangCBhd(c.hd), false);
  const giam = c.giam_manh.length ? `<ul class="ds">${c.giam_manh.map(dongCBgiam).join("")}</ul>` : dongKhong("Hôm nay chưa ghi nhận chứng quyền nào giảm mạnh.");
  return khoiCB("Chứng quyền rẻ bất thường", c.cw.length, `Giá chào bán thấp hơn giá lẽ ra theo cổ phiếu cơ sở từ ${so(ng.cw_lech_pct)}% trở lên, và có từ ${so(ng.cw_mua_duoc / 1e6)} triệu đang bán ở các mức rẻ đó. Giá lẽ ra tính bằng Black-Scholes với mức dao động của chính giá chào bán lúc quét gần nhất và giá cổ phiếu lúc này. Chỉ báo chứng quyền thuộc ${so(ng.cw_top)} dòng đầu danh sách, hoặc không đắt hơn giá hợp lý quá ${so(ng.cw_dat_toi_da_pct)}%. Bỏ chứng quyền còn dưới ${so(ng.cw_ngay_gd_cuoi)} ngày để bán. Không phòng hộ được; mua hôm nay sớm nhất chiều T+2 mới bán.`, cw)
    + khoiCB("ETF mua được dưới iNAV", c.etf.length, `Có từ ${so(ng.etf_mua_duoc / 1e6)} triệu đang chào bán ở giá đủ lãi ròng từ ${so(ng.etf_lai_rong_pct)}% nếu giá về iNAV, sau phí và thuế. Bỏ các quỹ thường xuyên rẻ hơn NAV từ ${so(ng.etf_thuong_re_pct)}%. Phòng hộ: bán hợp đồng tương lai cùng chỉ số; số hợp đồng tính cho lệnh ${so(ng.etf_lenh / 1e6)} triệu.`, etf)
    + khoiCB("Hợp đồng tương lai đắt hoặc rẻ", coHD.length, `Cận trên = chỉ số × e^(r × T) với r = ${so(ng.r_pct, 1)}% mỗi năm, chưa trừ cổ tức: là mức cao nhất hợp đồng đáng có, không phải giá hợp lý. Đắt: giá chờ mua của hợp đồng cao hơn cận trên cộng chi phí cả hai chân (bán hợp đồng, mua ETF cùng chỉ số, giữ đến đáo hạn). Rẻ: chỉ có lợi khi đang giữ ETF đó. Chỉ báo trong giờ khớp lệnh và khi hợp đồng còn từ ${so(ng.hd_phien_khoa)} phiên.`, hd)
    + khoiCB("Chứng quyền giảm mạnh hôm nay", c.giam_manh.length, `Chứng quyền thuộc nhóm Nên xem xét hoặc Theo dõi giảm quá ${so(ng.giam_manh_pct)}% so với giá tham chiếu mà không phải do cổ phiếu cơ sở giảm. Danh sách do lịch chạy 5 phút của web chứng quyền ghi trong ngày, kể cả mã đã hồi.`, giam);
}
// khối đầu tờ: tin chưa xem, trạng thái giờ khớp lệnh, bật tắt âm thanh, lỗi. Vẽ riêng để lượt hỏi mỗi phút không xóa chữ đang gõ ở form
function veTinCB() {
  const hop = $("#cb-tin", to); if (!hop || !S.cb || !S.cb.d) return;
  const chua = dsKho("chua_xem"), c = S.cb.d.chung, quyen = coTB() ? Notification.permission : "khong";
  const gio = !c ? "" : c.ngoai_gio ? `Ngoài giờ khớp lệnh: số bên dưới là sổ lệnh còn lại của phiên ${c.phien ? ngay(c.phien) : "trước"}, chỉ để xem, không phải cơ hội. ` : `Đang trong giờ khớp lệnh, số liệu lúc ${gioPhut(c.luc)}. `;
  const chuQuyen = { granted: "Thông báo của trình duyệt: đã cho phép.", denied: "Thông báo của trình duyệt đang bị chặn trong cài đặt; web vẫn kêu và hiện số trên chuông.", khong: "Trình duyệt này không có thông báo; web vẫn kêu và hiện số trên chuông.", default: "" }[quyen];
  const loi = [...(c ? c.loi.map((x) => `Không tải được ${x}`) : []), ...loiTin()];
  hop.innerHTML = `<div class="kl le"><h2>${chua.length ? `${so(chua.length)} tin chưa xem` : "Không có tin mới"}</h2>
    <p class="kl-gio">${gio}Web hỏi tin mới mỗi phút trong giờ khớp lệnh khi còn mở ở một thẻ; đóng web thì không báo.</p>
    ${chua.length ? `<ul class="cb-tin">${chua.slice().reverse().map((x) => `<li><button class="tin-dong" type="button" data-cb-tin="${esc(x.id)}"><b>${esc(tenTin(x))}</b><span>${esc(x.noi_dung)}</span></button></li>`).join("")}</ul><div><button type="button" class="nut-nho" id="cb-da-xem">Đã xem hết</button></div>` : ""}
    <div class="cb-am"><button type="button" class="nut-nho" id="cb-am" aria-pressed="${batAm()}">${batAm() ? "Âm thanh: đang bật" : "Âm thanh: đang tắt"}</button>${quyen === "default" && batAm() ? `<button type="button" class="nut-nho" id="cb-quyen">Cho phép thông báo</button>` : ""}<span>${chuQuyen}</span></div>
    ${loi.map((x) => `<div class="bao">${hinh("canh")}<p>${esc(x)}.</p></div>`).join("")}</div>`;
}
function veCanhBao() {
  demMr = 0;
  const m = S.cb, d = m.d, o = (id) => $(id, to);
  if (o("#cb-ma")) m.form = { ...m.form, ma: o("#cb-ma").value, muc: o("#cb-muc").value, ghiChu: o("#cb-ghi-chu").value }; // giữ chữ đang gõ qua lần vẽ lại
  let than;
  if (!d) than = `<div class="dang-ve le">Đang tải giá và tính cảnh báo…</div>`;
  else if (d.loi) than = `<p class="loi le" role="alert">Chưa tải được trang cảnh báo. ${esc(d.loi)}</p>`;
  else {
    const mg = d.muc_gia;
    than = `<div id="cb-tin"></div>
      <section class="khoi"><h3 class="le">Mức giá tôi đặt<small>${so(mg.muc.length)} trên ${so(mg.toi_da)}</small>${ct("Giá để xét là giá khớp gần nhất. Nếu lệnh khớp cuối nhỏ hơn 5 triệu đồng thì dùng giá mua được ngay (mức xuống tới) hoặc bán được ngay (mức lên tới) đủ 5 triệu. Chỉ riêng bạn thấy các mức này.")}</h3>
        ${mg.loi_gia ? `<div class="le"><div class="bao">${hinh("canh")}<p>Chưa lấy được giá cho các mức đã đặt. ${esc(mg.loi_gia)}</p></div></div>` : ""}
        ${mg.muc.length ? `<ul class="ds-tk">${mg.muc.map(dongMuc).join("")}</ul>` : dongKhong("Chưa đặt mức nào. Đặt một mức để web báo khi giá chạm tới.")}
        <div class="le">${formMuc()}</div></section>
      ${d.chung ? khoiChung(d.chung) : `<div class="le"><p class="loi" role="alert">Chưa tải được phần bất thường đang mua được. ${esc(d.loi_chung)}</p></div>`}`;
  }
  $(".to-trong", to).innerHTML = dauTo("Cảnh báo", "Tin mới và mức giá tôi đặt", `<button type="button" class="nut-nho" id="cb-tai">Tải lại</button>`) + `<div class="to-than">${than}
    <p class="chan le">Chứng quyền, cổ phiếu, ETF nhập mức bằng đồng; hợp đồng tương lai nhập điểm. Tên hợp đồng như VN30F1M tự chuyển sang hợp đồng mới khi đáo hạn. Web chỉ báo khi đang mở: một mức chạm lúc không ai mở web thì không được ghi lại. Phần bất thường là sàng lọc theo giá đang mua được trong sổ lệnh, chưa tín hiệu nào được kiểm chứng là có lãi sau phí. Không phải khuyến nghị đầu tư.</p></div>`;
  if (o("#cb-ma")) { o("#cb-ma").value = m.form.ma; o("#cb-muc").value = m.form.muc; o("#cb-ghi-chu").value = m.form.ghiChu; }
  veTinCB();
}
async function napCanhBao() {
  const m = S.cb; m.d = null; veCanhBao();
  const d = await api("/api/canh-bao").catch((e) => ({ loi: e.message }));
  if (S.cb !== m || S.loai !== "cb") return;
  m.d = d; veCanhBao();
}
async function napMucGia() {
  const m = S.cb, mg = await api("/api/muc-gia");
  if (S.cb !== m || S.loai !== "cb" || !m.d || m.d.loi) return;
  m.d.muc_gia = mg; veCanhBao();
}
function moCanhBao() {
  S.ma = null; S.loai = "cb"; S.cb = { d: null, form: { chieu: "duoi", ma: "", muc: "", ghiChu: "" } };
  if (to.hidden) moTo(`<div class="to-than"></div>`, null);
  to.scrollTop = 0;
  napPS(); // tên các hợp đồng cho ô gợi ý mã; lỗi thì chỉ thiếu gợi ý
  napCanhBao();
}
async function datMuc() {
  const f = S.cb.form, o = $("#cb-loi", to), lay = (id) => $(id, to).value.trim(), bao = (t) => { o.textContent = t; o.hidden = false; };
  const than = { ma: lay("#cb-ma").toUpperCase(), chieu: f.chieu, muc: Number(lay("#cb-muc")), ghi_chu: lay("#cb-ghi-chu") || null };
  if (!than.ma) { bao("Chưa nhập mã."); return; }
  if (!(than.muc > 0)) { bao("Chưa nhập mức giá."); return; }
  const nut = $("#cb-dat", to); nut.disabled = true; o.hidden = true;
  try {
    await api("/api/muc-gia", than);
    ["#cb-ma", "#cb-muc", "#cb-ghi-chu"].forEach((id) => { $(id, to).value = ""; });
    await napMucGia();
  } catch (e) { const oLoi = $("#cb-loi", to), n = $("#cb-dat", to); if (oLoi) { oLoi.textContent = `Chưa đặt được mức. ${e.message}`; oLoi.hidden = false; } if (n) n.disabled = false; }
}
async function xoaMuc(id) {
  try { await api(`/api/muc-gia/${encodeURIComponent(id)}/xoa`, {}); await napMucGia(); }
  catch (e) { const o = $("#cb-loi", to); if (o) { o.textContent = e.message; o.hidden = false; o.scrollIntoView({ block: "center" }); } }
}
// thẻ khác vừa nhận tin hoặc bấm "Đã xem hết": cập nhật chuông ở thẻ này
window.addEventListener("storage", (e) => { if (TK && e.key === khoaKho("chua_xem")) { veChuong(); veTinCB(); } });
// cú bấm đầu tiên vào trang mở sẵn đường tiếng (chỉ khi đang bật âm thanh), để tin đến sau kêu được
["pointerdown", "keydown"].forEach((sk) => document.addEventListener(sk, () => { if (batAm()) moAm(); }, { once: true }));
// Safari cũ nhận hàm gọi lại, trình duyệt mới trả Promise
function xinQuyen() { try { const p = Notification.requestPermission(veTinCB); if (p && p.then) p.then(veTinCB, veTinCB); } catch (e) { veTinCB(); } }

/* ---------- Tờ chi tiết: nở ra từ dòng được bấm, vuốt xuống để đóng ---------- */
let dongGoc = null;
function khungDong(el) { const a = app.getBoundingClientRect(), r = el.getBoundingClientRect(); return `inset(${Math.max(r.top - a.top, 0)}px ${Math.max(a.right - r.right, 0)}px ${Math.max(a.bottom - r.bottom, 0)}px ${Math.max(r.left - a.left, 0)}px round 8px)`; }
function moTo(html, tu) {
  const dangMo = !to.hidden && to.classList.contains("mo");
  to.innerHTML = `<div class="to-trong">${html}</div>`; to.scrollTop = 0;
  if (dangMo) return;
  dongGoc = tu || null; to.hidden = false; man.hidden = false; to.style.transform = "";
  if (!rong.matches && !itChuyenDong && tu) { to.style.transition = "none"; to.style.clipPath = khungDong(tu); void to.offsetHeight; to.style.transition = ""; }
  void to.offsetHeight; requestAnimationFrame(() => { to.classList.add("mo"); man.classList.add("mo"); to.style.clipPath = "inset(0 0 0 0 round 0px)"; });
}
function dongTo(truot) {
  S.ma = null; S.loai = null; S.trangCu = null; S.dm = null; S.cb = null; ghiDiaChi(); to.classList.remove("mo"); man.classList.remove("mo");
  if (!rong.matches && !itChuyenDong) { if (!truot && dongGoc && dongGoc.isConnected && dongGoc.getClientRects().length) to.style.clipPath = khungDong(dongGoc); else to.style.transform = "translateY(100%)"; }
  setTimeout(() => { if (S.ma) return; to.hidden = true; man.hidden = true; to.style.clipPath = ""; to.style.transform = ""; to.innerHTML = ""; if (dongGoc && dongGoc.isConnected) dongGoc.focus({ preventScroll: true }); }, itChuyenDong ? 0 : 450);
}
man.addEventListener("click", () => dongTo(false));
let keo = null;
to.addEventListener("pointerdown", (e) => { if (rong.matches || e.pointerType === "mouse" || !e.target.closest(".to-dau") || e.target.closest("button")) return; keo = { y: e.clientY, d: 0 }; to.style.transition = "none"; });
to.addEventListener("pointermove", (e) => { if (!keo) return; keo.d = Math.max(e.clientY - keo.y, 0); to.style.transform = `translateY(${keo.d}px)`; });
const thaKeo = () => { if (!keo) return; const d = keo.d; keo = null; to.style.transition = ""; if (d > 110) dongTo(true); else to.style.transform = ""; };
to.addEventListener("pointerup", thaKeo); to.addEventListener("pointercancel", thaKeo);

/* ---------- Bấm ---------- */
app.addEventListener("click", (e) => {
  const nTK = e.target.closest("#nut-tk"); if (nTK) { moThucDonTK(nTK); return; }
  const mTK = e.target.closest("[data-tk]"); if (mTK) { dongNoi(); if (mTK.dataset.tk === "ds") moTaiKhoan(""); else location.href = TK.dang_xuat; return; }
  const vTK = e.target.closest("[data-tk-viec]"); if (vTK) { lamViecTK(vTK); return; }
  if (e.target.closest("#cong-thu")) { vaoCong(); return; }
  if (e.target.closest("#nut-dm")) { dongNoi(); moDanhMuc(); return; }
  if (e.target.closest("#nut-cb")) { dongNoi(); moCanhBao(); return; }
  if (e.target.closest("#cb-tai")) { napCanhBao(); return; }
  const cbT = e.target.closest("[data-cb-tin]"); if (cbT) { moTin(cbT.dataset.cbTin); return; }
  if (e.target.closest("#cb-da-xem")) { ghiKho("chua_xem", "[]"); veChuong(); veTinCB(); return; }
  // bật âm thanh: kêu thử (cú bấm này cũng là lần bấm để trình duyệt cho phát tiếng) và xin quyền thông báo
  if (e.target.closest("#cb-am")) { ghiKho("am", batAm() ? "tat" : "bat"); if (batAm()) { keu(); if (coTB() && Notification.permission === "default") xinQuyen(); } veTinCB(); return; }
  if (e.target.closest("#cb-quyen")) { xinQuyen(); return; }
  const cbC = e.target.closest("[data-cb-chieu]"); if (cbC) { S.cb.form.chieu = cbC.dataset.cbChieu; $$("[data-cb-chieu]", to).forEach((x) => x.setAttribute("aria-pressed", x === cbC)); return; }
  if (e.target.closest("#cb-dat")) { datMuc(); return; }
  const cbX = e.target.closest("[data-cb-xoa]"); if (cbX) { if (cbX.dataset.chac) xoaMuc(cbX.dataset.cbXoa); else { cbX.dataset.chac = "1"; cbX.textContent = "Bấm lần nữa để xóa"; setTimeout(() => { if (cbX.isConnected) { delete cbX.dataset.chac; cbX.textContent = "Xóa"; } }, 4000); } return; }
  if (e.target.closest("#dm-tai")) { napDanhMuc(); return; }
  const dmL = e.target.closest("[data-dm-loai]"); if (dmL) { S.dm.form.loai = dmL.dataset.dmLoai; veDanhMuc(); const o = $("#dm-ma", to); if (o) o.focus(); return; }
  const dmC = e.target.closest("[data-dm-chieu]"); if (dmC) { S.dm.form.chieu = dmC.dataset.dmChieu; $$("[data-dm-chieu]", to).forEach((x) => x.setAttribute("aria-pressed", x === dmC)); return; }
  if (e.target.closest("#dm-ghi")) { ghiLenh(); return; }
  // xóa lệnh: bấm hai lần trong 4 giây, để một cú chạm nhầm không xóa mất lệnh
  const dmX = e.target.closest("[data-dm-xoa]"); if (dmX) { if (dmX.dataset.chac) xoaLenh(dmX.dataset.dmXoa); else { dmX.dataset.chac = "1"; dmX.textContent = "Bấm lần nữa để xóa"; setTimeout(() => { if (dmX.isConnected) { delete dmX.dataset.chac; dmX.textContent = "Xóa"; } }, 4000); } return; }
  const nCt = e.target.closest(".ct"); if (nCt) { if (chuotThat.matches || nutNoi !== nCt) moNoi(nCt); else dongNoi(); return; }
  dongNoi();
  const lui = e.target.closest("#to-lui"); if (lui) { dongTo(false); return; }
  const cw = e.target.closest("[data-cw]"); if (cw) { moCW(cw.dataset.cw, cw.classList.contains("dong") ? cw : null); return; }
  const quy = e.target.closest("[data-etf]"); if (quy) { moETF(quy.dataset.etf, quy.classList.contains("dong") ? quy : null); return; }
  const hd = e.target.closest("[data-ps]"); if (hd) { moPS(hd.dataset.ps, hd); return; }
  const cqLoc = e.target.closest("[data-cq-loc]"); if (cqLoc) { S.cqLoc = cqLoc.dataset.cqLoc; S.cqHien = SO_DONG; $$("[data-cq-loc]").forEach((x) => x.setAttribute("aria-pressed", x === cqLoc)); veDsCQ(); return; }
  if (e.target.closest("#cq-them")) { S.cqHien += SO_DONG; veDsCQ(); return; }
  const ex = e.target.closest("[data-etf-xem]"); if (ex) { if (ex.dataset.etfXem !== S.etfXem) { S.etfXem = ex.dataset.etfXem; veETF(); } return; }
  const d = e.target.closest("button.dong[data-ma]"); if (d) { moMa(d.dataset.ma, d); return; }
  const om = e.target.closest(".o-ma[data-ma]"); if (om) { moMa(om.dataset.ma, null); return; }
  const xem = e.target.closest("[data-xem]"); if (xem) { if (xem.dataset.xem !== S.xem && (S.tq || xem.dataset.xem === "xh")) { S.xem = xem.dataset.xem; veCoPhieu(); } return; }
  const cd = e.target.closest("[data-chedo]"); if (cd) { if (cd.dataset.chedo !== S.cheDo) { S.cheDo = cd.dataset.chedo; napTongQuan(); } return; }
  const ng = e.target.closest("[data-nganh]"); if (ng) { const dang = ng.getAttribute("aria-pressed") === "true"; $$("[data-nganh]").forEach((x) => x.setAttribute("aria-pressed", "false")); S.loc.nganh = dang ? null : ng.dataset.nganh; if (!dang) ng.setAttribute("aria-pressed", "true"); veDs(); return; }
  const loc = e.target.closest("[data-loc]"); if (loc) { $$("[data-loc]").forEach((x) => x.setAttribute("aria-pressed", x === loc)); S.loc.nhan = loc.dataset.loc; veDs(); return; }
  const m = e.target.closest(".mr-nut"); if (m) { const hop = m.parentElement, mo = hop.classList.toggle("mo"); m.setAttribute("aria-expanded", mo); if (mo && hop.dataset.nap && !hop.dataset.xong) { hop.dataset.xong = "1"; napMuc(hop, hop.dataset.nap); } return; }
  const kh = e.target.closest("[data-khung]"); if (kh) { S.bd.khung = kh.dataset.khung; $$("[data-khung]", to).forEach((x) => x.setAttribute("aria-pressed", x === kh)); veBieuDo(); return; }
  const tg = e.target.closest("[data-tang]"); if (tg) { const i = +tg.dataset.tang; if (S.bd.tang.has(i)) S.bd.tang.delete(i); else S.bd.tang.add(i); tg.setAttribute("aria-pressed", S.bd.tang.has(i)); veBieuDo(); return; }
  const hs = e.target.closest("[data-hoso]"); if (hs) { S.bd.hoSo = !S.bd.hoSo; hs.setAttribute("aria-pressed", S.bd.hoSo); veBieuDo(); }
});
document.addEventListener("keydown", (e) => { if (e.key === "Escape") { if (!goiY.hidden) dongGoiY(); else if (!to.hidden) dongTo(false); } });
$("#nut-nen").addEventListener("click", (e) => { const toi = !dangToi(); document.documentElement.dataset.theme = toi ? "dark" : "light"; e.currentTarget.setAttribute("aria-pressed", toi); if (S.ma) { if (S.loai === "cp") veBieuDo(); else veTrangCu(); } });

/* ---------- Ô tìm mã ---------- */
const oTim = $("#o-tim"), goiY = $("#goi-y");
function dongGoiY() { goiY.hidden = true; oTim.setAttribute("aria-expanded", "false"); }
function veGoiY() {
  const k = boDau(oTim.value.trim()); if (!k) { dongGoiY(); return; }
  const a = [], b = [], khac = []; for (const r of S.ds) { if (boDau(r.ma).startsWith(k)) a.push(r); else if (boDau(r.ten).includes(k)) b.push(r); }
  if (S.etf && S.etf.co) for (const h of S.etf.quy.dong) if (boDau(h["Mã"]).includes(k)) khac.push(["etf", h["Mã"], `Quỹ ETF · ${h["Chỉ số"]}`]);
  if (S.ps) for (const n of S.ps.nhom) for (const h of n.hop_dong) if (!h.thieu_dao_han && boDau(h.ma).includes(k)) khac.push(["ps", h.ma, `Hợp đồng tương lai ${n.chi_so} · ${h.thang}`]);
  if (S.cq && S.cq.co) for (const c of S.cq.cw) if (boDau(c.ma).includes(k) || boDau(c.cs) === k) khac.push(["cw", c.ma, `Chứng quyền ${c.cs} · ${c.tcph} · ${tenNhom(c.nhom)}`]);
  const dong = [...[...a, ...b].map((r) => `<li><button type="button" data-goi="${esc(r.ma)}" data-loai="cp"${r.co_dong_tien ? "" : " disabled"}><b>${esc(r.ma)}</b><span>${esc([r.ten, r.nganh, r.co_dong_tien ? "" : "chưa có dữ liệu dòng tiền"].filter(Boolean).join(" · "))}</span></button></li>`),
    ...khac.map(([loai, ma, chu]) => `<li><button type="button" data-goi="${esc(ma)}" data-loai="${loai}"><b>${esc(ma)}</b><span>${esc(chu)}</span></button></li>`)].slice(0, S.tq ? S.tq.tim_toi_da : GOI_Y_DU_PHONG);
  goiY.innerHTML = dong.length ? dong.join("") : `<li class="goi-trong">Không thấy mã nào khớp "${esc(oTim.value.trim())}".</li>`;
  goiY.hidden = false; oTim.setAttribute("aria-expanded", "true");
}
const MO_THEO_LOAI = { cp: [1, moMa], cw: [2, moCW], etf: [3, moETF], ps: [4, moPS] };
function chonGoiY(ma, loai) { oTim.value = ""; dongGoiY(); oTim.blur(); const [viTri, mo] = MO_THEO_LOAI[loai] || MO_THEO_LOAI.cp; if (dangXem !== viTri) datDangXem(viTri, true); mo(ma, null); }
oTim.addEventListener("input", veGoiY); oTim.addEventListener("focus", veGoiY);
oTim.addEventListener("keydown", (e) => { if (e.key === "Enter") { const b = $("button:not(:disabled)", goiY); if (!goiY.hidden && b) { e.preventDefault(); chonGoiY(b.dataset.goi, b.dataset.loai); } } });
goiY.addEventListener("click", (e) => { const b = e.target.closest("[data-goi]"); if (b) chonGoiY(b.dataset.goi, b.dataset.loai); });
document.addEventListener("click", (e) => { if (!e.target.closest(".tim")) dongGoiY(); });

/* ---------- Dòng dưới chuột lớn lên nhẹ (máy tính) ---------- */
app.addEventListener("mousemove", (e) => {
  if (!chuotThat.matches || itChuyenDong) return; const ds = e.target.closest(".ds"); $$(".ds .dong[style]").forEach((d) => { if (!ds || !ds.contains(d)) d.style.transform = ""; });
  if (!ds) return; $$("button.dong", ds).forEach((d) => { const r = d.getBoundingClientRect(), k = Math.max(0, 1 - Math.abs(e.clientY - (r.top + r.height / 2)) / 110); d.style.transform = k > 0 ? `scale(${(1 + 0.03 * k * k).toFixed(4)})` : ""; });
});
app.addEventListener("mouseleave", () => $$(".ds .dong[style]").forEach((d) => (d.style.transform = "")));

/* ---------- Khởi động ---------- */
// đọc mã trên địa chỉ TRƯỚC khi datDangXem ghi lại địa chỉ, nếu không tham số ?ma= bị mất
const maMoDau = (new URLSearchParams(location.search).get("ma") || "").toUpperCase();
const viTriHash = TAB.findIndex((t) => `#${t[0]}` === location.hash);
function batDau() {
  datDangXem(viTriHash >= 0 ? viTriHash : 0, false);
  hoiTin(); setInterval(hoiTin, GIAY_XET_LUOT * 1000); // tin cảnh báo: máy chủ chỉ tính trong giờ khớp lệnh
  napHomNay();
  if (!rong.matches) trang.scrollLeft = dangXem * trang.clientWidth;
  datVach(dangXem);
  Promise.all([napTongQuan(), api("/api/ma").then((ds) => { S.ds = ds; }).catch(() => { S.ds = []; })]).then(() => {
    if (S.tq && /^[A-Z0-9]{3,4}$/.test(maMoDau) && S.tq.ma.some((r) => r.ma === maMoDau)) moMa(maMoDau, null);
  });
  // chứng quyền và ETF đọc file kết quả (nhanh) nên nạp ngay; địa chỉ có ?ma= trỏ vào loại nào thì mở tờ của loại đó
  const choCQ = napCQ(), choETF = napETF();
  if (/^VN(30|100)F[12][MQ]$/.test(maMoDau)) napPS().then(() => moPS(maMoDau, null));
  else if (/^[A-Z0-9]{5,12}$/.test(maMoDau)) Promise.all([choCQ, choETF]).then(() => { if (S.cq && S.cq.co && S.cq.cw.some((c) => c.ma === maMoDau)) moCW(maMoDau, null); else moETF(maMoDau, null); });
}
vaoCong();
})();
