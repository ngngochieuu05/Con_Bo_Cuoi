# Security Policy

<a href="#english">🇬🇧 English</a> · <a href="#vietnamese">🇻🇳 Tiếng Việt</a>

---

<a id="english"></a>

## 🇬🇧 English

### Supported Versions

| Version | Supported |
|---------|-----------|
| `main` branch | ✅ Active |
| `dev*` branches | ⚠️ Development only |
| Older releases | ❌ Not supported |

### Reporting a Vulnerability

**Do NOT open a public GitHub issue for security vulnerabilities.**

Please report security issues privately:

1. **Email:** [trantandatt.26@gmail.com](mailto:trantandatt.26@gmail.com)
2. **Subject:** `[SECURITY] Con Bò Cười — <brief description>`
3. **Include:**
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (optional)

We will acknowledge your report within **72 hours** and aim to release a fix within **14 days** for critical issues.

### Security Practices

| Area | Practice |
|------|----------|
| **Passwords** | SHA-256 hashed — no plaintext storage |
| **Sessions** | Cleared on logout via `page.data` purge |
| **Secrets** | `.env` and credential files are gitignored |
| **Seed accounts** | Weak default passwords — change before any production deployment |
| **Dependencies** | No auto-pinned versions; review before upgrading |

### Known Limitations

- **SHA-256 without salt** — passwords are vulnerable to rainbow table attacks. A future phase will migrate to bcrypt/argon2.
- **JSON file store** — not suitable for multi-user production; meant for local/LAN use only.
- **No HTTPS enforcement** — web mode over LAN should be fronted by a reverse proxy with TLS for production deployments.

### Scope

The following are **in scope** for vulnerability reports:

- Authentication bypass or privilege escalation
- Injection vulnerabilities (command, path traversal)
- Sensitive data exposure (credentials, session tokens)
- Insecure deserialization from JSON store

The following are **out of scope:**

- Denial-of-service against a local desktop instance
- Social engineering
- Issues in dependencies not exploitable via this application

---

<a id="vietnamese"></a>

## 🇻🇳 Tiếng Việt

### Phiên bản được hỗ trợ

| Phiên bản | Hỗ trợ |
|-----------|--------|
| Nhánh `main` | ✅ Đang hoạt động |
| Nhánh `dev*` | ⚠️ Chỉ dùng phát triển |
| Bản phát hành cũ | ❌ Không hỗ trợ |

### Báo cáo lỗ hổng bảo mật

**Không mở public issue trên GitHub cho các lỗ hổng bảo mật.**

Vui lòng báo cáo bằng cách:

1. **Email:** [trantandatt.26@gmail.com](mailto:trantandatt.26@gmail.com)
2. **Tiêu đề:** `[SECURITY] Con Bò Cười — <mô tả ngắn>`
3. **Nội dung bao gồm:**
   - Mô tả lỗ hổng
   - Các bước tái hiện
   - Mức độ ảnh hưởng
   - Đề xuất cách sửa (nếu có)

Chúng tôi sẽ xác nhận báo cáo trong vòng **72 giờ** và cố gắng phát hành bản vá trong **14 ngày** với các vấn đề nghiêm trọng.

### Thực hành bảo mật

| Khu vực | Thực hành |
|---------|-----------|
| **Mật khẩu** | Hash SHA-256 — không lưu plaintext |
| **Phiên làm việc** | Xóa hoàn toàn khi đăng xuất qua `page.data` |
| **Secrets** | File `.env` và credential được gitignore |
| **Tài khoản seed** | Mật khẩu mặc định yếu — **đổi trước khi deploy production** |
| **Dependencies** | Không tự động pin phiên bản; kiểm tra trước khi nâng cấp |

### Giới hạn đã biết

- **SHA-256 không có salt** — dễ bị tấn công rainbow table. Phase tương lai sẽ chuyển sang bcrypt/argon2.
- **Lưu trữ file JSON** — không phù hợp cho production đa người dùng; chỉ dùng cho local/LAN.
- **Không bắt buộc HTTPS** — web mode qua LAN cần reverse proxy với TLS cho môi trường production.

### Phạm vi

**Trong phạm vi** báo cáo:

- Bypass xác thực hoặc leo thang đặc quyền
- Lỗ hổng injection (command injection, path traversal)
- Lộ thông tin nhạy cảm (credentials, session token)
- Deserialization không an toàn từ JSON store

**Ngoài phạm vi:**

- Tấn công DoS vào desktop instance cục bộ
- Social engineering
- Lỗi trong dependency không khai thác được qua ứng dụng này
