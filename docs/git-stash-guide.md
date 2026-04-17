# Git Stash Guide

Lưu tạm thời các thay đổi chưa commit để chuyển sang task khác mà không mất work.

---

## Khái niệm

`git stash` hoạt động như một **stack** (LIFO — Last In First Out):
- Mỗi lần stash → đẩy vào đỉnh stack
- `stash@{0}` luôn là stash mới nhất
- `stash@{1}` là stash trước đó, v.v.

Stash lưu: staged files, unstaged files.  
Stash **không** lưu: untracked files (mặc định), ignored files.

---

## Lệnh cơ bản

### Tạo stash

```bash
# Stash tất cả staged + unstaged (không gồm untracked)
git stash

# Stash với tên mô tả (khuyến nghị)
git stash push -m "wip: expert dashboard refactor"

# Stash cả untracked files
git stash push -u -m "wip: new feature with new files"

# Stash cả untracked + ignored files
git stash push -a -m "wip: full state backup"

# Stash chỉ 1 file cụ thể
git stash push -m "wip: only auth.py" webapp_system/src/bll/services/auth_service.py
```

### Xem danh sách

```bash
git stash list
# Output:
# stash@{0}: On devD: wip: expert dashboard refactor
# stash@{1}: On main: wip: new feature with new files
```

### Xem nội dung stash

```bash
# Xem danh sách files trong stash
git stash show stash@{0}

# Xem diff chi tiết
git stash show -p stash@{0}

# Xem files của stash mới nhất
git stash show
```

---

## Apply stash

### Pop — apply + xóa khỏi list

```bash
# Apply stash mới nhất (stash@{0}) rồi xóa
git stash pop

# Apply stash cụ thể rồi xóa
git stash pop stash@{1}
```

### Apply — apply nhưng giữ lại trong list

```bash
# Apply stash mới nhất, giữ trong list
git stash apply

# Apply stash cụ thể, giữ trong list
git stash apply stash@{1}
```

> **Khi nào dùng apply thay pop?**  
> Khi muốn apply cùng 1 stash vào nhiều branch khác nhau.

---

## Xóa stash

```bash
# Xóa stash cụ thể
git stash drop stash@{0}

# Xóa tất cả stash
git stash clear
```

---

## Tạo branch từ stash

Hữu ích khi stash bị conflict với code hiện tại:

```bash
# Tạo branch mới từ stash@{0}, apply vào đó, rồi xóa stash
git stash branch feature/expert-ui stash@{0}
```

---

## Workflow thực tế

### Tình huống 1 — Chuyển nhánh gấp

```bash
# Đang làm dở feature, cần fix bug gấp ở main
git stash push -m "wip: expert dashboard half-done"
git checkout main
# ... fix bug ...
git checkout devD
git stash pop
```

### Tình huống 2 — Lấy 1 file từ stash mà không apply toàn bộ

```bash
# Chỉ lấy file auth_service.py từ stash@{0}
git checkout stash@{0} -- webapp_system/src/bll/services/auth_service.py
```

### Tình huống 3 — Xem stash có chứa file nào không

```bash
git stash list --name-only
# hoặc
git stash show stash@{0} --name-only
```

---

## Conflict khi apply

Nếu apply bị conflict, Git báo lỗi nhưng **không** xóa stash khỏi list (dù dùng `pop`):

```bash
git stash pop
# CONFLICT (content): Merge conflict in file.py

# Giải quyết conflict như bình thường
# Sau khi fix xong, xóa stash thủ công
git stash drop stash@{0}
```

---

## Tips

| Việc cần làm | Lệnh |
|---|---|
| Luôn đặt tên stash | `git stash push -m "mô tả rõ"` |
| Kiểm tra stash định kỳ | `git stash list` |
| Dọn stash cũ không cần | `git stash drop stash@{N}` |
| Không stash quá lâu | Apply hoặc tạo branch từ stash sớm |

---

## Phân biệt stash vs commit

| | Stash | Commit |
|---|---|---|
| Lưu ở đâu | Local only | Local + remote (sau push) |
| Có trong `git log` | Không | Có |
| Dễ bị quên | Có | Không |
| Dùng khi | Work in progress tạm thời | Milestone hoàn chỉnh |
