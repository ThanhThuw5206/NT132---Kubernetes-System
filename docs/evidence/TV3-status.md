# Trạng thái công việc TV3 · 05/11/2026

Phạm vi đã thực hiện: **source, công cụ và kiểm tra local** trên laptop Windows. Source nền `17aaed9`; nhánh bàn giao `tv3/istio-network`. Ghi commit thực tế bằng `git rev-parse HEAD` khi lấy mã. Không tạo VM/LB, không cài hoặc đổi policy trên cụm cloud trong phiên này.

**Cập nhật nhận từ TV1:** branch `tv1/cloud-config` tại `612e3b0` ghi nhận ba node Ready, Pod IP/ClusterIP/DNS trả 200 và Rancher thấy ba node Active ngày 05/11/2026; Istio/Kiali/app/policy chưa triển khai. Đây là trạng thái TV1 bàn giao trong repo, không phải một lần nghiệm thu cloud mới của TV3. Các bảng Chưa chạy dưới đây nói về các ca TV3 trong phiên chuẩn bị này; nhận quyền/inventory trước khi thử lại, không dựng trùng hoặc reset cụm đang có.

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
| Chuẩn bị laptop | [Hướng dẫn laptop](../tv3-laptop.md), checker offline có log, Google Cloud CLI portable 592.0.0 với archive đã so SHA256 chính thức; `--version` chạy thành công |
| Ma trận/đầu vào | [Ma trận C0–C4/C1b và các ca Service](../tv3-test-matrix.md), [checklist TV1/TV2](../tv3-access-checklist.md), đã điền thông số có trong repo và trạng thái công cụ của máy hiện tại |

Theo yêu cầu hiện tại, bỏ qua slide; không đưa slide vào gói bàn giao đợt laptop. Người dùng đã đăng nhập bằng tài khoản riêng. Phép kiểm tra chỉ đọc ngày 05/11 xác nhận project/VM truy cập được, OS Login/Admin và IAP trên cp-01/wk-02 có hiệu lực, quyền start/stop ba VM không có. Lúc kiểm tra ba VM đang TERMINATED. Chưa import CA, sửa hosts, SSH, thay IAM hoặc khởi động/cài đặt lên cụm; chưa kiểm tra Kubernetes/Rancher trực tiếp bằng tài khoản TV3.

## Kiểm tra local đã chạy

Môi trường: Python **3.15.2** từ runtime uv đã có trên máy; Git Bash **5.3.15**. Không cài thêm package Python, không cần WSL.

```text
uv run --offline --no-project python -m unittest discover -s tests -v
Ran 37 tests
OK

uv run --offline --no-project python scripts/tv3.py --help
Exit 0

Bash syntax: scripts/*.sh
Passed

git diff --check
Passed
```

37 test gồm: 5 test renderer; 3 test nhận diện node theo InternalIP; 8 test NET01/Calico với kubectl/curl giả; 11 test công cụ TV3; 4 test package/native sidecar/ánh xạ Service–Pod; 6 test HTTP body/timeout/report (có server loopback thật). NET01 và snapshot đã được kết hợp với hỗ trợ FQDN của TV1; các test kiểm tra cả retry tạm thời và ghi lại lỗi từng lần. Các ca lỗi khác bao gồm DNS/thiếu lệnh, Pod cùng node, resource thuộc người khác, Calico Degraded, config placeholder, ghi đè output, endpoint sai Pod UID, rollout cũ, package thiếu/chứa file không được phép hoặc bị đổi sau đóng gói, body bị cắt/chunk sai/quá lớn và Ctrl+C. Các test này không chứng minh CNI/mesh/policy đang hoạt động trên Google Cloud.

Đã rà lại phân công với kế hoạch đồ án: TV3 chủ trì NET01/OBS01/SEC03/SVC04, kiểm tra chéo IAM01/SVC02/SEC01/SVC03/PUB01 và phối hợp OPS01. Các thành viên xem phiếu bàn giao để nhận đúng source/đầu việc; phần ứng dụng, Service/route và luật Istio vẫn do TV2 xác nhận, hạ tầng/Rancher/LB do TV1 phụ trách.

Giới hạn công cụ được ghi rõ: timeout HTTP là thời gian socket không nhận dữ liệu, không phải hạn tổng thời gian; Ctrl+C giữ report chưa hoàn tất. 503/504 qua proxy chỉ là dấu hiệu upstream cần đối chiếu log/baseline/phục hồi, không tự nghiệm thu SEC03. Source chưa commit được chuyển bằng overlay, không dựa vào `git archive HEAD` riêng lẻ.

## Chưa nghiệm thu cloud

| Test / công việc | Trạng thái thực tế trong phiên | Đầu vào để chạy tiếp |
|---|---|---|
| Tiếp nhận wk-02 | TV1 đã bootstrap theo bàn giao; TV3 chưa SSH kiểm tra trực tiếp | TV1 bật cụm theo lịch; xác nhận phiên SSH/context, không prepare/join lại |
| Calico / NET01 | TV1 đã ghi nhận CNI/Service hoạt động; TV3 chưa chạy lại fixture hai chiều trên cụm | Node Ready, context đúng và phạm vi thử được thống nhất; không cài lại Calico |
| Istio / Prometheus / Kiali | Chưa cài trong phiên | Mạng nền đạt, Helm và quyền quản trị phù hợp |
| OBS01 | Chưa chạy trên ứng dụng | TV2 giao app/sidecar/route và request tạo luồng nội bộ |
| SEC01–SEC04 | Chưa chạy trên ứng dụng | Hai nguồn thật, labels/ServiceAccount/API, baseline và chính sách đã thống nhất |
| SVC04 | Chưa chạy trên ứng dụng | Service thật, nguồn hợp lệ; TV1 sửa thử và TV2 gọi lại |
| PUB01 | Chưa chạy | TV1 giao frontend LB/firewall, app qua gateway đã đạt |
| Kiểm tra chéo | Chưa chạy | TV1/TV2 chạy lại và ghi nhận bằng chứng |

Ứng dụng và project cloud không được tự chọn thay TV1/TV2. Khi nhận đầu vào, chạy theo [runbook TV3](../tv3-runbook.md), lưu log thật và nhờ thành viên khác tái hiện trước khi đổi trạng thái sang Đạt. File này không khẳng định cloud ngoài phiên hiện đang chạy hay đã dừng.
