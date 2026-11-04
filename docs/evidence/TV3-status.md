# Trạng thái công việc TV3 · 05/11/2026

Phạm vi đã thực hiện: **source, công cụ và kiểm tra local** trên laptop Windows. Source nền `17aaed9`; nhánh bàn giao `tv3/istio-network`. Ghi commit thực tế bằng `git rev-parse HEAD` khi lấy mã. Không tạo VM/LB, không cài hoặc đổi policy trên cụm cloud trong phiên này.

## Đã hoàn thành trên máy

| Sản phẩm | File / kết quả |
|---|---|
| Đối chiếu phân công và phụ thuộc | [tv3-current-work.md](../tv3-current-work.md), [runbook](../tv3-runbook.md) |
| Bảng phiên bản và thiết kế mạng | [Calico README](../../cluster/calico/README.md); đã đối chiếu tài liệu chính thức cho dải Kubernetes của Calico/Istio, chưa xác minh runtime thật |
| NET01 hai chiều | Fixture có client/server trên mỗi worker, script gọi Pod IP/ClusterIP/DNS sáu lượt, lưu log/exit code, kiểm tra label sở hữu trước apply |
| Readiness Calico | Script cài đặt chờ Available=True, Progressing=False, Degraded=False với timeout; có test mô phỏng Degraded |
| Snapshot riêng TV3 | `scripts/tv3.py snapshot`: kiểm tra nền không phụ thuộc Rancher, ghi node/runtime/image/Helm và pins |
| Công cụ OBS01 | `scripts/tv3.py traffic`: GET có timeout/thời lượng, timestamp UTC+07:00, ghi status/lỗi, không ẩn redirect |
| Manifest SVC04 | `scripts/tv3.py render`: Service thử riêng có hai trạng thái selector sai/đúng, dùng ports/labels từ config thật |
| Policy và phép thử DNS/HTTP | Tái sử dụng renderer sẵn có; `scripts/tv3.py probe` ghi nguồn/danh tính/policy/EndpointSlice và kết quả gọi |
| Bằng chứng SVC02/SVC03 | `service-snapshot` ghi Service UID/ClusterIP/selector/ports và kiểm tra EndpointSlice targetRef/IP khớp Pod Ready được selector chọn; không tự restart/scale |
| Proxy theo phiên bản hiện tại | Probe nhận cả proxy thường và native sidecar Ready; đọc policy namespace ứng dụng và root mesh, ghi lỗi nếu evidence thiếu |
| Gói bàn giao source local | `package` tạo overlay ZIP/manifest/SHA256SUMS theo allowlist, gồm thay đổi chưa commit; `verify-package` đối chiếu từng file sau giải nén |
| Quy trình nghiệm thu | [C1–C4](../../tests/security/README.md), [SVC04](../../tests/service/README.md), [OBS01](../../observability/README.md), [ma trận luật mạng](../../network/policies/README.md) |
| Hồ sơ kết quả | [Mẫu evidence](templates/test-result.md), giữ trạng thái chưa chạy cho cloud |
| Hướng dẫn cho TV1/TV2 | [Phiếu bàn giao](../tv3-handover.md), cách lấy branch TV3, bảng người nhận/đầu vào/mốc/ký nhận và cách chuyển source lên VM |

## Kiểm tra local đã chạy

Môi trường: Python **3.15.2** từ runtime uv đã có trên máy; Git Bash **5.3.15**. Không cài thêm package Python, không cần WSL.

```text
uv run --offline --no-project python -m unittest discover -s tests -v
Ran 32 tests
OK

uv run --offline --no-project python scripts/tv3.py --help
Exit 0

Bash syntax: scripts/*.sh
Passed

git diff --check
Passed
```

32 test gồm: 5 test renderer có sẵn; 6 test điều phối NET01/Calico với kubectl/curl giả; 11 test công cụ TV3; 4 test package/native sidecar/ánh xạ Service–Pod; 6 test HTTP body/timeout/report (có server loopback thật). Các ca lỗi bao gồm DNS/thiếu lệnh, Pod cùng node, resource thuộc người khác, Calico Degraded, config placeholder, ghi đè output, endpoint sai Pod UID, rollout cũ, package thiếu/chứa file không được phép hoặc bị đổi sau đóng gói, body bị cắt/chunk sai/quá lớn và Ctrl+C. Các test này không chứng minh CNI/mesh/policy đang hoạt động trên Google Cloud.

Đã rà lại phân công với kế hoạch đồ án: TV3 chủ trì NET01/OBS01/SEC03/SVC04, kiểm tra chéo IAM01/SVC02/SEC01/SVC03/PUB01 và phối hợp OPS01. Các thành viên xem phiếu bàn giao để nhận đúng source/đầu việc; phần ứng dụng, Service/route và luật Istio vẫn do TV2 xác nhận, hạ tầng/Rancher/LB do TV1 phụ trách.

Giới hạn công cụ được ghi rõ: timeout HTTP là thời gian socket không nhận dữ liệu, không phải hạn tổng thời gian; Ctrl+C giữ report chưa hoàn tất. 503/504 qua proxy chỉ là dấu hiệu upstream cần đối chiếu log/baseline/phục hồi, không tự nghiệm thu SEC03. Source chưa commit được chuyển bằng overlay, không dựa vào `git archive HEAD` riêng lẻ.

## Chưa nghiệm thu cloud

| Test / công việc | Trạng thái thực tế trong phiên | Đầu vào để chạy tiếp |
|---|---|---|
| wk-02 chuẩn bị/join | Chưa chạy | TV1 giao VM, IAM/IAP, source và join command |
| Calico / NET01 | Chưa chạy trên cụm | Ba node join, context đúng và quyền vận hành |
| Istio / Prometheus / Kiali | Chưa cài trong phiên | Mạng nền đạt, Helm và quyền quản trị phù hợp |
| OBS01 | Chưa chạy trên ứng dụng | TV2 giao app/sidecar/route và request tạo luồng nội bộ |
| SEC01–SEC04 | Chưa chạy trên ứng dụng | Hai nguồn thật, labels/ServiceAccount/API, baseline và chính sách đã thống nhất |
| SVC04 | Chưa chạy trên ứng dụng | Service thật, nguồn hợp lệ; TV1 sửa thử và TV2 gọi lại |
| PUB01 | Chưa chạy | TV1 giao frontend LB/firewall, app qua gateway đã đạt |
| Kiểm tra chéo | Chưa chạy | TV1/TV2 chạy lại và ghi nhận bằng chứng |

Ứng dụng và project cloud không được tự chọn thay TV1/TV2. Khi nhận đầu vào, chạy theo [runbook TV3](../tv3-runbook.md), lưu log thật và nhờ thành viên khác tái hiện trước khi đổi trạng thái sang Đạt. File này không khẳng định cloud ngoài phiên hiện đang chạy hay đã dừng.
