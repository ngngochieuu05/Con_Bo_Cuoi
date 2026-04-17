# Bổ sung tùy chỉnh .claude kit

Ghi lại các thay đổi tùy chỉnh so với bản CE gốc.  
Khi nâng cấp lên version mới, áp dụng lại các mục dưới đây.

---

## [2026-04-17] English-only for files

### `rules/development-rules.md`
Thêm vào đầu section `## General` (trước dòng `**File Naming**`):

```markdown
- **Language**: Always use English when working with files — file names, code, comments, commit messages, docs.
```

---

## [2026-04-17] Plan Status Transitions

### `rules/primary-workflow.md`
Thêm section sau dòng `**IMPORTANT**: Ensure token efficiency...` (dòng 4):

```markdown
## Plan Status Transitions

Update plan/phase `status` field at each checkpoint — never skip transitions:

| Transition | When |
|-----------|------|
| `pending` → `in_progress` | BEFORE starting any code |
| `in_progress` → `in_review` | AFTER impl complete, BEFORE sending for review |
| `in_review` → `done` | AFTER review pass + tests pass |
| `any` → `cancelled` | When task is dropped — add reason in plan comments |

**Rule:** Update both `plan.md` (overall status) and the relevant `phase-XX.md` (phase status) at each transition.
```

### `rules/development-rules.md`
Thêm vào cuối file (sau dòng `See primary-workflow.md → Step 6 for workflow integration`):

```markdown

## Plan Status Rules
- `in_review` chỉ được set khi progress = 100% (tất cả phases done)
- `done` chỉ được set sau khi user xác nhận — KHÔNG tự set done
- `in_progress` là trạng thái mặc định khi còn phase chưa hoàn thành
- Flow: `pending → in_progress → in_review (100%) → done (user confirms)`
- See `primary-workflow.md` → **Plan Status Transitions** for full table and rules
```

---

## [2026-04-17] Hook CWD fix — git rev-parse

### `.claude/settings.json`
Tất cả hook commands và `statusLine.command` phải dùng pattern sau để tránh CWD pollution khi Bash tool thay đổi working directory:

```json
"command": "bash -c 'cd \"$(git rev-parse --show-toplevel)\" && node .claude/hooks/X.cjs'"
```

**Lý do:** Claude Code có thể chạy từ subdirectory (e.g. `webapp_system/src`). Nếu hook dùng đường dẫn tương đối `node .claude/hooks/...`, nó sẽ tìm sai chỗ. `git rev-parse --show-toplevel` luôn trả về git root — nơi `.claude/` thực sự nằm.

**Áp dụng cho:** tất cả entries trong `hooks.*[].hooks[].command` và `statusLine.command`.

---

## [2026-04-17] Kanban status normalization fix — `in_review` underscore

### `skills/plans-kanban/scripts/lib/plan-metadata-extractor.cjs`

Thêm `in_review` (underscore) vào function `normalizeStatus` để kanban nhận đúng column:

```js
// Dòng 28 — thêm || s === 'in_review'
if (s === 'in-review' || s === 'in_review' || s === 'review') return 'in-review';
```

**Lý do:** Plan files dùng `in_review` (underscore theo Python convention), nhưng kanban chỉ match `in-review` (hyphen). Kết quả: mọi plan có `status: in_review` bị fallback về cột Pending thay vì In Review.

---

## [2026-04-17] Plan Status Workflow — progress gate

### `rules/primary-workflow.md` — bảng Plan Status Transitions

Cập nhật bảng để thêm cột **Progress gate** và enforce 2 rules cứng:

```markdown
| Transition | When | Progress gate |
|-----------|------|---------------|
| `pending` → `in_progress` | BEFORE starting any code | progress = 0% |
| `in_progress` → `in_review` | AFTER ALL phases done (100%) | progress = 100% only |
| `in_review` → `done` | AFTER user explicitly confirms | user approval required |
| `any` → `cancelled` | When task is dropped | — |

**Rules:**
- NEVER set `in_review` unless progress = 100%
- NEVER set `done` without explicit user confirmation
```

**Lý do:** Cần phân biệt rõ "impl xong" (100% → in_review) vs "user duyệt" (→ done). Cook skill trước đây tự set done mà không qua in_review + user confirm.

---

## [2026-04-17] MCP Docker — lưu vào user-level settings

### `~/.claude/.mcp.json` (tạo mới)
Chuyển MCP_DOCKER từ project `.mcp.json` sang user-level để dùng được ở tất cả projects:

```json
{
  "mcpServers": {
    "MCP_DOCKER": {
      "command": "docker",
      "args": ["mcp", "gateway", "run"],
      "env": {
        "LOCALAPPDATA": "C:\\Users\\Tran Dat\\AppData\\Local",
        "ProgramData": "C:\\ProgramData",
        "ProgramFiles": "C:\\Program Files"
      },
      "type": "stdio"
    }
  }
}
```

---

## [2026-04-17] Allow Claude edit own config files

### `~/.claude/settings.json` — permissions.allow
Thêm 2 rules sau để bypass permissions có thể edit files config của Claude mà không bị hỏi:

```json
"Write(~/.claude/**)",
"Edit(~/.claude/**)"
```

**Lý do:** Claude Code có protection đặc biệt cho `~/.claude/*` — ngay cả khi `defaultMode: bypassPermissions`, edit các file này vẫn bị hỏi xác nhận. Thêm explicit allow rules sẽ bỏ qua prompt đó.
