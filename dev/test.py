"""Kiểm thử trang phiếu trong Chrome không giao diện: lỗi script, hành vi, gửi phiếu, ảnh chụp.

Chạy: python3 test.py  (cần playwright cho Python và Google Chrome)
"""
import functools
import http.server
import json
import pathlib
import sys
import threading

from playwright.sync_api import sync_playwright

dev = pathlib.Path(__file__).resolve().parent
root = dev.parent
shots = dev / "shots"
shots.mkdir(exist_ok=True)
errors = []
received = []
STORE = "tt-khao-sat-ai-v1"


def check(cond, label):
    print(("ok   " if cond else "FAIL ") + label)
    if not cond:
        errors.append(label)


class Site(http.server.SimpleHTTPRequestHandler):
    """Phục vụ thư mục gốc của repo; /config.js có thể được thay bằng cấu hình thử."""

    submit_url = ""

    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path.split("?")[0] == "/config.js" and Site.submit_url:
            body = ("window.SURVEY_CONFIG = { submitUrl: %s };" % json.dumps(Site.submit_url)).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/javascript")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()


class Api(http.server.BaseHTTPRequestHandler):
    """Máy chủ nhận phiếu giả lập, có CORS như máy chủ thật cần có."""

    fail = False

    def log_message(self, *a):
        pass

    def cors(self):
        self.send_header("Access-Control-Allow-Origin", self.headers.get("Origin", "*"))
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(204)
        self.cors()
        self.end_headers()

    def do_POST(self):
        raw = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        if Api.fail:
            self.send_response(500)
            self.cors()
            self.end_headers()
            return
        received.append(json.loads(raw.decode("utf-8")))
        self.send_response(201)
        self.cors()
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"ok":true}')


def serve(handler):
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, "http://127.0.0.1:%d" % srv.server_address[1]


site_srv, url = serve(functools.partial(Site, directory=str(root)))
api_srv, api = serve(Api)

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
    ctx = browser.new_context(viewport={"width": 1280, "height": 900}, accept_downloads=True)
    page = ctx.new_page()
    page.on("pageerror", lambda e: errors.append("pageerror: " + str(e)))
    page.on("console", lambda m: errors.append("console: " + m.text) if m.type == "error" else None)

    # --- Chế độ không có máy chủ nhận phiếu ---
    page.goto(url + "/")
    check(page.locator("h1").inner_text() == "Phiếu khảo sát nhu cầu ứng dụng trợ lý AI", "tiêu đề trang mở đầu")
    check(page.locator(".steps a").count() == 8, "tám bước trong mục lục")
    check(page.evaluate("document.fonts.check('600 16px \"Be Vietnam Pro\"')"), "phông đã nạp")
    page.screenshot(path=str(shots / "01-mo-dau.png"))

    page.goto(url + "/#chung")
    page.click("button[data-rank='1.1'][data-v='Thủy sản']")
    page.click("button[data-rank='1.1'][data-v='Hóa chất công nghiệp']")
    page.wait_for_timeout(400)
    check(page.evaluate("JSON.parse(localStorage.getItem('%s'))['1.1']" % STORE) == ["Thủy sản", "Hóa chất công nghiệp"], "lưu thứ tự xếp hạng")
    page.check("input[data-k='1.4'][value='Thêm đơn hàng']", force=True)
    page.check("input[data-k='1.4'][value='Bớt sai sót']", force=True)
    check(page.locator("input[data-k='1.4'][value='Báo cáo nhanh hơn']").is_disabled(), "khóa lựa chọn thứ ba khi chọn tối đa hai")
    page.check("input[data-k='1.5'][value='Làm trọn bộ phận Sales']", force=True)
    check(page.locator("button[data-clear='1.5']").count() == 1, "có nút Bỏ chọn")
    page.fill("input[data-k='1.6']", "Tháng 1 năm 2027")
    page.wait_for_timeout(400)
    check(page.locator(".steps a[href='#chung'] .st-prog").inner_text() == "4/7", "tiến độ Phần 1 là 4/7")
    page.screenshot(path=str(shots / "02-phan-1.png"), full_page=True)

    page.goto(url + "/#sales")
    for code in ["S1", "S2", "S3", "S4", "S5"]:
        page.check(f"input[data-k='need.{code}.level'][value='Cần ngay']", force=True)
    check(page.locator("input[data-k='need.S6.level'][value='Cần ngay']").is_disabled(), "khóa việc Cần ngay thứ sáu")
    check("5/5" in page.locator("[data-limit]").first.inner_text(), "ghi chú giới hạn hiện 5/5")
    page.fill("input[data-k='need.S1.tool']", "Zalo, khoảng 100 lần mỗi tuần")
    page.goto(url + "/#kho")
    check(page.locator("input[data-k='need.K1.level'][value='Cần ngay']").is_disabled(), "giới hạn áp dụng cho cả ba bộ phận")
    page.goto(url + "/#uu-tien")
    check(page.locator("[data-nowlist] li").count() == 5, "Phần 6 liệt kê năm việc đã chọn")
    page.select_option("select[data-k='top.1']", "S1")

    page.goto(url + "/#gui")
    page.wait_for_timeout(400)
    check(page.locator("button[data-act='submit']").count() == 0, "không có nút Gửi phiếu khi chưa cấu hình máy chủ")
    with page.expect_download() as dl:
        page.click("button[data-act='download']")
    exported = pathlib.Path(dl.value.path()).read_text(encoding="utf-8")
    data = json.loads(exported)
    check(data["form"] == "thanh-thinh-khao-sat-tro-ly-ai" and data["answers"]["need.S1.level"] == "Cần ngay", "file kết quả đúng định dạng")
    check("1. Thủy sản" in [r for r in data["readable"] if r["code"] == "1.1"][0]["answer"], "bản đọc được có thứ tự xếp hạng")
    page.screenshot(path=str(shots / "03-gui-phieu.png"), full_page=True)
    page.reload()
    page.goto(url + "/#chung")
    check(page.input_value("input[data-k='1.6']") == "Tháng 1 năm 2027", "giữ câu trả lời sau khi tải lại trang")

    # --- Điện thoại: gộp file, từ chối file lạ ---
    ctx2 = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2)
    m = ctx2.new_page()
    m.on("pageerror", lambda e: errors.append("pageerror(mobile): " + str(e)))
    m.goto(url + "/#kho")
    m.check("input[data-k='3.3'][value='Có']", force=True)
    m.goto(url + "/#gui")
    (shots / "import.json").write_text(exported, encoding="utf-8")
    m.set_input_files("#imp", str(shots / "import.json"))
    m.wait_for_timeout(600)
    merged = m.evaluate("JSON.parse(localStorage.getItem('%s'))" % STORE)
    check(merged.get("3.3") == "Có" and merged.get("1.6") == "Tháng 1 năm 2027", "gộp file giữ câu đã có và thêm câu mới")
    (shots / "bad.json").write_text('{"form":"khac","answers":{}}', encoding="utf-8")
    m.set_input_files("#imp", str(shots / "bad.json"))
    m.wait_for_timeout(500)
    check("bị bỏ qua" in m.locator("#msg-in").inner_text(), "bỏ qua file không phải của phiếu")
    m.goto(url + "/#sales")
    m.screenshot(path=str(shots / "04-dien-thoai.png"))
    check(not m.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth + 1"), "không tràn ngang trên điện thoại")

    # --- Chế độ gửi về máy chủ riêng ---
    Site.submit_url = api + "/khao-sat"
    ctx3 = browser.new_context(viewport={"width": 1280, "height": 900})
    s = ctx3.new_page()
    s.on("pageerror", lambda e: errors.append("pageerror(submit): " + str(e)))
    s.goto(url + "/#kho")
    s.check("input[data-k='3.3'][value='Không']", force=True)
    s.goto(url + "/#gui")
    s.wait_for_timeout(400)
    check(s.locator("button[data-act='submit']").inner_text() == "Gửi phiếu", "có nút Gửi phiếu khi đã cấu hình máy chủ")
    s.click("button[data-act='submit']")
    s.wait_for_timeout(800)
    check(len(received) == 1 and received[0]["answers"].get("3.3") == "Không" and received[0]["clientId"], "máy chủ nhận đúng nội dung phiếu")
    check(s.locator("#msg-out").inner_text().startswith("Đã gửi phiếu lúc"), "báo đã gửi")
    check("Lần gửi gần nhất" in s.locator("#saved").inner_text(), "mục lục ghi lần gửi gần nhất")
    s.screenshot(path=str(shots / "05-da-gui.png"), full_page=True)
    Api.fail = True
    s.click("button[data-act='submit']")
    s.wait_for_timeout(800)
    check(s.locator("#msg-out").inner_text().startswith("Chưa gửi được phiếu"), "báo lỗi khi máy chủ từ chối")
    check(not s.locator("button[data-act='submit']").is_disabled(), "nút Gửi phiếu bật lại sau lỗi")

    browser.close()

site_srv.shutdown()
api_srv.shutdown()
print("\n".join(["", "LỖI:"] + errors) if errors else "\nmọi kiểm tra đều đạt")
sys.exit(1 if errors else 0)
