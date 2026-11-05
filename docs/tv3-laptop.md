# TV3 · Phần đã chuẩn bị trên laptop

Ngày 05/11/2026, phần laptop phát triển từ source nền `a15dfdb` trên branch `tv3/istio-network`. Phạm vi: công cụ local, kiểm tra offline, ma trận test và hồ sơ nhận việc. Sau khi chuẩn bị công cụ, người dùng đã đăng nhập và kiểm tra quyền Google Cloud bằng API chỉ đọc; chưa SSH, import CA, sửa hosts hoặc apply cấu hình lên cụm. Slide được để lại giai đoạn sau theo yêu cầu.

## 1. Kiểm tra lại toàn bộ phần local

Trong PowerShell tại repo:

```powershell
uv run --offline --no-project python scripts/check-tv3-local.py
```

Lệnh dùng đúng Python đang chạy qua uv, chạy bộ unit test, kiểm tra cú pháp Bash/PowerShell và đọc `gcloud --version` qua wrapper local. Các bài HTTP chỉ dùng loopback và các bài Kubernetes dùng mock. Không thực hiện `auth login`, không liên hệ API của project, không chạy script cài node. Output/log và `report.json` nằm trong thư mục `.generated/laptop-check-*` mới, được Git bỏ qua. Exit 0 khi tất cả kiểm tra local đạt; kết quả không thay nghiệm thu cloud.

Nếu muốn chỉ chạy test:

```powershell
uv run --offline --no-project python -m unittest discover -s tests -v
```

Lệnh `python` trên máy hiện tại trỏ tới alias Microsoft Store; dùng uv như trên, không cần đổi PATH hoặc cài thêm Python. Máy nhận khác cần có Python >=3.10 hoặc runtime uv đã cache để dùng `--offline`.

## 2. Google Cloud CLI portable

SDK được chuẩn bị tại `.cache/gcloud-592.0.0/google-cloud-sdk`, có Python đi kèm. Installer chỉ tải archive Windows x64 đúng phiên bản, so SHA256 rồi giải nén vào cache; không mở browser hoặc thay PATH. Pin/checksum được đối chiếu ngày 05/11/2026 từ [archive chính thức Google](https://docs.cloud.google.com/sdk/docs/downloads-versioned-archives).

Kiểm tra phiên bản trên máy hiện tại:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\gcloud-local.ps1 --version
```

Nếu cần chuẩn bị lại trên máy Windows khác:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install-gcloud-local.ps1
```

`-ExecutionPolicy Bypass` chỉ áp dụng cho tiến trình PowerShell đó, không đổi policy toàn máy. Installer không xóa cache có sẵn. Sau khi bị ngắt giữa chừng, kiểm tra không còn tiến trình installer chạy và hash archive đúng; có thể tiếp tục giải nén bằng `-ResumePartial`. Nếu checksum sai, installer dừng trước giải nén; kiểm tra đúng file tải về trước khi thử lại. Marker `tv3-install-complete.json` chỉ được ghi sau khi giải nén xong.

Wrapper `gcloud-local.ps1` giữ config riêng ở `.cache/tv3-gcloud-config`, tắt kiểm tra cập nhật/usage reporting cho phiên và khôi phục biến môi trường process sau khi chạy. Không ảnh hưởng cấu hình gcloud có sẵn của người dùng. Người dùng hiện đã đăng nhập bằng wrapper; dữ liệu đăng nhập nằm trong cache này, ngoài Git/gói bàn giao và không được gửi cho người khác. Nếu dùng gcloud cài toàn máy ở terminal khác, đó là config khác; dùng nhất quán một cách gọi khi làm lab. Thành viên nhận source tự đăng nhập bằng tài khoản riêng, không nhận cache của máy này.

Hiện không cần cài kubectl/Helm/Terraform lên laptop để hoàn thành các việc offline. Theo quy trình TV1, kubectl/Helm chạy trong phiên `cp-01`; Terraform và vòng đời VM do TV1 phụ trách.

## 3. Hồ sơ đã sẵn sàng để nhóm điền

| File | Nội dung đã chuẩn bị | Phần chờ đầu vào thật |
|---|---|---|
| [tv3-test-matrix.md](tv3-test-matrix.md) | C0–C4, C1b client ngoài mesh; nguồn/đích/port/method/path, kỳ vọng, phục hồi, evidence và người chạy lại | Tên app/Pod/SA/port/path, kết quả thật và ký nhận |
| [tv3-access-checklist.md](tv3-access-checklist.md) | Tách Google IAM, Rancher và Kubernetes; đã ghi kiểm tra IAM chỉ đọc, còn CA/context/lịch phiên và đầu vào TV2 | TV1 bố trí phiên Kubernetes/Rancher, TV2 giao baseline/ứng dụng |
| [application-handover.md](application-handover.md) | Schema thông tin ứng dụng và thứ tự giao nhận | TV2 điền source/image, Service, labels, ServiceAccount và API |
| [tests/security/README.md](../tests/security/README.md) | Lệnh thử từng lớp và hoàn tác riêng | Chỉ chạy sau khi có quyền/baseline và lịch tích hợp |
| [mẫu evidence](evidence/templates/test-result.md) | Các trường source/thời gian/nguồn-đích/kỳ vọng/thực tế/rollback/peer | Chỉ điền Đạt sau khi có kết quả cloud và người thứ hai chạy lại |

Theo cập nhật TV1, cụm/Calico/Rancher đã hoạt động. Khi làm cloud sau này, tiếp nhận trạng thái hiện có, không chạy lại prepare/join/reset/cài CNI. Theo quy trình mới: TV1 xác nhận Ready/quyền → TV2 baseline app → review → TV3 mesh/quan sát → injection/route và kiểm tra lại → policy từng lớp → phục hồi/evidence.

## 4. Kiểm tra truy cập đã thực hiện và phần còn chờ

Ngày 05/11/2026 đã xác nhận tài khoản đang ACTIVE, đọc được project `nt132-kubernetes-513805` và ba VM. API `testIamPermissions` trả có quyền OS Login, OS Admin Login và IAP trên `cp-01`/`wk-02`; không có quyền start/stop trên cả ba VM. Tại lần kiểm tra, cả ba VM đang TERMINATED (dừng, không phải xóa). Đây là ảnh chụp trạng thái tại thời điểm kiểm tra, không phải trạng thái VM được giám sát liên tục.

Chưa kiểm tra kết nối SSH thực tế hoặc quyền Kubernetes/Rancher; chưa import chứng chỉ hay sửa hosts; chưa cài mesh/quan sát hoặc thử policy trên cloud. Khi cần chuyển giai đoạn, dùng [checklist đầu vào](tv3-access-checklist.md), nhờ TV1 bật cụm/bố trí phiên thao tác và nhận dữ liệu app từ TV2. Kiểm tra IAM không thay thế kiểm tra SSH/firewall hoặc baseline ứng dụng.

## 5. Bàn giao phần local

Sau khi cập nhật source, có thể tạo gói overlay theo [phiếu bàn giao](tv3-handover.md):

```powershell
uv run --offline --no-project python scripts/tv3.py package
```

Gói chỉ gồm allowlist source, ma trận/hướng dẫn và script; không có SDK, cache cấu hình gcloud, credentials, kết quả cloud giả hoặc slide. Người nhận chạy lại checker local sau khi chuẩn bị SDK/runtime của chính họ. Việc tạo gói không tự commit, push hoặc gửi cho thành viên nào.
