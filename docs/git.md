# Git - Các lệnh thường dùng

## Thiết lập ban đầu
```bash
git config --global user.name "Tên của bạn"
git config --global user.email "email@example.com"
git config --list                        # Xem cấu hình hiện tại
```

---

## Khởi tạo & Clone
```bash
git init                                 # Khởi tạo repo mới trong thư mục hiện tại
git clone <url>                          # Clone repo từ GitHub về máy
git clone <url> tên-thư-mục             # Clone và đặt tên thư mục
```

---

## Kiểm tra trạng thái
```bash
git status                               # Xem file nào thay đổi, staged, untracked
git log --oneline                        # Xem lịch sử commit ngắn gọn
git log --oneline --graph --all          # Xem lịch sử dạng cây nhánh
git diff                                 # Xem thay đổi chưa staged
git diff --staged                        # Xem thay đổi đã staged
```

---

## Thêm & Commit
```bash
git add .                                # Stage tất cả thay đổi
git add <file>                           # Stage file cụ thể
git commit -m "nội dung commit"          # Commit với message
git commit -am "nội dung"               # Add + commit cùng lúc (file đã track)
git commit --amend -m "sửa message"     # Sửa commit cuối (chưa push)
```

---

## Nhánh (Branch)
```bash
git branch                               # Xem danh sách nhánh local
git branch -a                            # Xem cả nhánh remote
git branch tên-nhánh                     # Tạo nhánh mới
git checkout tên-nhánh                   # Chuyển sang nhánh
git checkout -b tên-nhánh               # Tạo và chuyển sang nhánh mới
git switch tên-nhánh                     # Chuyển nhánh (Git mới hơn)
git switch -c tên-nhánh                  # Tạo và chuyển nhánh (Git mới hơn)
git branch -d tên-nhánh                  # Xóa nhánh đã merge
git branch -D tên-nhánh                  # Xóa nhánh bất kể trạng thái
```

---

## Merge & Rebase
```bash
git merge tên-nhánh                      # Merge nhánh vào nhánh hiện tại
git merge --no-ff tên-nhánh             # Merge giữ lại merge commit
git rebase main                          # Rebase nhánh hiện tại lên main
git merge --abort                        # Hủy merge đang conflict
git rebase --abort                       # Hủy rebase đang conflict
```

---

## Remote (GitHub)
```bash
git remote -v                            # Xem danh sách remote
git remote add origin <url>              # Thêm remote origin
git remote set-url origin <url>          # Đổi URL remote
git fetch origin                         # Lấy thay đổi từ remote (chưa merge)
git pull                                 # fetch + merge nhánh hiện tại
git pull origin main                     # Pull từ nhánh main của origin
git push                                 # Push nhánh hiện tại lên remote
git push origin tên-nhánh               # Push nhánh cụ thể lên remote
git push -u origin tên-nhánh            # Push và set upstream (lần đầu)
git push origin --delete tên-nhánh      # Xóa nhánh trên remote
```

---

## Hoàn tác (Undo)
```bash
git restore <file>                       # Hủy thay đổi chưa staged của file
git restore --staged <file>              # Unstage file (bỏ khỏi staging area)
git reset HEAD~1                         # Hoàn tác commit cuối, giữ thay đổi
git reset --hard HEAD~1                  # Hoàn tác commit cuối, XÓA thay đổi ⚠️
git revert <commit-hash>                 # Tạo commit mới đảo ngược commit cũ (an toàn)
```

---

## Stash (Lưu tạm)
```bash
git stash                                # Lưu tạm thay đổi chưa commit
git stash push -m "tên mô tả"           # Stash với tên
git stash list                           # Xem danh sách stash
git stash pop                            # Lấy stash mới nhất ra và xóa khỏi stash
git stash apply stash@{0}               # Áp dụng stash nhưng không xóa
git stash drop stash@{0}                # Xóa một stash cụ thể
git stash clear                          # Xóa toàn bộ stash
```

---

## Tag
```bash
git tag                                  # Xem danh sách tag
git tag v1.0.0                           # Tạo tag nhẹ
git tag -a v1.0.0 -m "Release 1.0.0"   # Tạo tag có chú thích
git push origin v1.0.0                  # Push tag lên remote
git push origin --tags                  # Push tất cả tags
```

---

## Tình huống thực tế hay gặp

### Bắt đầu làm tính năng mới
```bash
git checkout main
git pull
git checkout -b feature/tên-tính-năng
# ... code ...
git add .
git commit -m "feat: thêm tính năng X"
git push -u origin feature/tên-tính-năng
```

### Lỡ commit nhầm branch
```bash
git log --oneline -1                     # Lấy hash commit vừa làm
git reset HEAD~1                         # Bỏ commit, giữ code
git checkout đúng-nhánh
git add .
git commit -m "message"
```

### Xử lý conflict khi pull
```bash
git pull                                 # Báo conflict
# Mở file conflict, sửa tay phần <<<< ==== >>>>
git add <file-đã-sửa>
git commit -m "resolve conflict"
```

### Xem ai sửa dòng nào
```bash
git blame <file>                         # Xem từng dòng do ai commit
```

### Tìm commit gây ra bug
```bash
git bisect start
git bisect bad                           # Commit hiện tại có bug
git bisect good <hash-commit-tốt>        # Commit cũ không có bug
# Git tự checkout giữa chừng, test rồi nhập:
git bisect good / git bisect bad
git bisect reset                         # Kết thúc bisect
```
