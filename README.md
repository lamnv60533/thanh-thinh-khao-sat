# Phiếu khảo sát nhu cầu ứng dụng trợ lý AI — Hóa chất Thành Thịnh

Trang web tĩnh để khách tự điền phiếu khảo sát. Không có máy chủ đi kèm: Vercel chỉ phát file, câu trả lời nằm trên trình duyệt của người điền cho tới khi họ tải file kết quả hoặc bấm Gửi phiếu.

## Cấu trúc

| File | Vai trò |
| --- | --- |
| `index.html` | Trang phiếu, đã gộp sẵn CSS, script và phông chữ. Đây là file được triển khai. |
| `config.js` | Địa chỉ máy chủ nhận phiếu. Để trống thì trang chỉ cho tải file kết quả. |
| `vercel.json` | Header bảo mật và chặn công cụ tìm kiếm lập chỉ mục. |
| `dev/` | Mã nguồn, lệnh build và kiểm thử. Không được triển khai (xem `.vercelignore`). |

Mỗi phần có đường dẫn riêng để gửi cho đúng người: `/#chung`, `/#sales`, `/#kho`, `/#ke-toan`, `/#phan-mem`, `/#uu-tien`, `/#gui`.

## Bật gửi phiếu về máy chủ của bạn

Sửa `config.js`:

```js
window.SURVEY_CONFIG = { submitUrl: "https://api.example.vn/khao-sat" };
```

Khi có địa chỉ này, bước cuối của phiếu hiện nút **Gửi phiếu**. Trình duyệt của người điền gửi thẳng tới máy chủ của bạn; dữ liệu không đi qua Vercel.

Máy chủ cần đáp ứng:

- **HTTPS.** Trang chạy trên HTTPS nên trình duyệt chặn mọi địa chỉ `http://`.
- **`POST` với `Content-Type: application/json`**, trả về mã 2xx khi nhận thành công.
- **CORS.** Trả lời yêu cầu `OPTIONS` và kèm các header sau, với origin là tên miền của trang phiếu:

  ```
  Access-Control-Allow-Origin: https://<ten-mien-trang-phieu>
  Access-Control-Allow-Methods: POST, OPTIONS
  Access-Control-Allow-Headers: Content-Type
  ```

Nội dung gửi lên:

```json
{
  "form": "thanh-thinh-khao-sat-tro-ly-ai",
  "version": 1,
  "clientId": "mã ngẫu nhiên của từng trình duyệt",
  "exportedAt": "2026-11-18T14:38:00.000Z",
  "answers": { "2.3a": ["Zalo cá nhân của nhân viên"], "need.S1.level": "Cần ngay" },
  "readable": [
    { "part": "Phần 2. Kinh doanh / Sales", "code": "2.3", "question": "Khách nhắn vào đâu?", "answer": "…" }
  ]
}
```

Gợi ý cho máy chủ:

- Lưu đè theo `clientId`: một người sửa rồi gửi lại thì bản mới thay bản cũ.
- Mỗi bộ phận gửi từ một máy khác nhau, nên một công ty sẽ có vài bản; gộp theo khóa trong `answers`.
- Kiểm tra `form`, giới hạn kích thước (một phiếu đầy đủ dưới 100 KB) và giới hạn tần suất, vì địa chỉ này công khai trong `config.js`.

Ví dụ NestJS:

```ts
@Controller('khao-sat')
export class SurveyController {
  constructor(private readonly surveys: SurveyService) {}

  @Post()
  @HttpCode(201)
  async receive(@Body() body: { form: string; clientId: string; answers: Record<string, unknown> }) {
    if (body?.form !== 'thanh-thinh-khao-sat-tro-ly-ai' || !body.clientId) throw new BadRequestException();
    await this.surveys.upsertByClientId(body.clientId, body);
    return { ok: true };
  }
}

// main.ts
app.enableCors({ origin: ['https://<ten-mien-trang-phieu>'], methods: ['POST', 'OPTIONS'], allowedHeaders: ['Content-Type'] });
```

## Đọc file kết quả

File `.json` người điền tải về có cùng cấu trúc như trên. Cách đọc nhanh nhất: mở trang phiếu, vào bước **Gửi phiếu**, bấm **Nhập file của bộ phận khác** để gộp các file, rồi bấm **In hoặc lưu PDF**.

## Sửa nội dung phiếu

Câu hỏi nằm trong mảng `PARTS` của `dev/src/index.html`.

```bash
cd dev
npm install
npm run build   # ghi lại ../index.html
npm test        # build rồi chạy kiểm thử (cần Python, playwright và Google Chrome)
```

Đẩy lên nhánh `main` thì Vercel tự triển khai lại.
