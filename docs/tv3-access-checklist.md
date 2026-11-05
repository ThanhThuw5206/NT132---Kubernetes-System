# TV3 · Checklist đầu vào và quyền truy cập

Biểu mẫu chuẩn bị trên laptop ngày **05/11/2026** theo [hướng dẫn TV1](them-thanh-vien.md). Chưa có tài khoản/quyền nào được xác nhận chỉ từ việc file này tồn tại. Điền trạng thái **Đã nhận và kiểm tra / Chưa nhận / Bị chặn**, kèm người bàn giao và thời gian; không điền mật khẩu, token, private key, kubeconfig hoặc email cá nhân vào repo.

## 1. Phần laptop có thể chuẩn bị trước

| Hạng mục | Cách xác nhận local | Trạng thái / ghi chú |
|---|---|---|
| Source đúng branch/commit | Ghi `git branch --show-current`, `git rev-parse HEAD`; giữ thay đổi local và source package riêng | Phần laptop trên branch `tv3/istio-network`, phát triển từ `a15dfdb`; người nhận ghi HEAD thực tế khi lấy mã |
| Python thật hoặc uv có runtime cache | Dùng uv theo [runbook](tv3-runbook.md); Microsoft Store alias `python` không phải lỗi bộ test | Laptop hiện tại: Python 3.15.2 qua uv, đã chạy test local |
| Git Bash khi kiểm tra cú pháp script Linux | Chạy syntax check local; không chạy script cài node bằng PowerShell | Laptop hiện tại: có Git Bash 5.3.15 |
| Google Cloud CLI | Xác nhận công cụ local nếu đã cài; đăng nhập là bước cần tài khoản của chính thành viên | Laptop hiện tại: portable 592.0.0, tài khoản đã ACTIVE và kiểm tra API chỉ đọc ngày 05/11 |
| File chuẩn bị | Đọc [ma trận test](tv3-test-matrix.md), [phiếu app](application-handover.md), policy/rollback; chưa cần bật VM | Đã có mẫu; người nhận đọc và ghi điểm còn thiếu |

Người dùng đã đăng nhập bằng tài khoản riêng; các phép đọc project/VM và kiểm tra IAM không bật máy hoặc đổi quyền. Import CA, sửa hosts, SSH/tunnel hoặc mở Rancher còn chờ đúng đầu vào bên dưới.

Các kết quả đã điền ở phần laptop chỉ áp dụng cho máy đang chuẩn bị ngày 05/11/2026. Thành viên nhận source trên máy khác cần chạy lại [checker local](tv3-laptop.md), không coi Python/SDK có sẵn trên máy mình chỉ vì repo có biểu mẫu này.

## 2. TV1 bàn giao quyền và môi trường

| Đầu vào / người giao | TV3 cần xác nhận | Trạng thái ban đầu |
|---|---|---|
| Project/zone/VM · TV1 | Project `nt132-kubernetes-513805`, zone `asia-southeast1-a`, VM `cp-01`, `wk-01`, `wk-02`; cần lịch bật máy và đầu mối vận hành | Đã đọc được project ACTIVE và ba VM ngày 05/11; chưa thống nhất lịch phiên |
| Inventory hiện có · TV1 | IP nội bộ .10/.11/.12, tên Node thực có thể là FQDN; TV1 ghi nhận Ready/Calico/Rancher hoạt động ngày 05/11 | Tại lần đọc Compute API gần nhất: ba VM TERMINATED; chưa kiểm tra trực tiếp Kubernetes |
| Google IAM · TV1 | Tài khoản riêng có quyền theo phạm vi nhóm | Đã kiểm tra quyền đọc project/VM; OS Login/Admin và IAP trên cp-01/wk-02 có hiệu lực. Start/stop cả ba VM: không có |
| SSH/IAP · TV1 | Thành viên SSH bằng tài khoản riêng vào đúng VM; không dùng SSH key/tài khoản của TV1 | IAM IAP đã xác nhận; kết nối SSH/firewall/sudo thực tế chưa thử vì VM đang dừng tại lần kiểm tra |
| Quyền Kubernetes/Helm · TV1 | Có phiên kubectl/Helm với context và quyền cần thiết để review/apply CRD/resource mesh; TV1 theo dõi phiên triển khai | Chưa bố trí phiên |
| Quyền đọc/lấy log/exec/forward · TV1 | Đúng namespace và tác vụ NET01/OBS01/policy; quyền tạo client/debug riêng nếu cần ca C1b | Chưa xác nhận |
| Rancher user · TV1 | Tài khoản riêng, đổi mật khẩu tạm qua kênh riêng; đúng cluster/project và quyền được giao | Chưa nhận; không ghi mật khẩu vào bảng |
| CA công khai · TV1 | Chỉ nhận `ca.crt`, đối chiếu CA/hostname của lab qua đầu mối TV1 trước khi import | Chưa nhận; không nhận `ca.key`/`tls.key` |
| Tunnel/hosts · TV1 | Hostname Rancher và các port đã chốt; ai mở port-forward trên cp-01, ai đang dùng để tránh trùng phiên | Chưa thống nhất |
| Trạng thái policy ban đầu · TV1 | Chính sách ứng dụng/root mesh/CNI liên quan, ai sở hữu, trạng thái cần giữ/khôi phục | Chưa nhận |
| Thay đổi cấp cluster · TV1 | Thống nhất thời điểm cài Istio/Prometheus/Kiali, namespace hệ thống được dùng và cách rollback | Chưa lên lịch |
| Frontend public · TV1, giai đoạn sau | URL/IP/cổng frontend, nguồn được phép và health check; dùng cho PUB01, không cần để soạn code local | Chưa bàn giao |

Google IAM, Rancher role và Kubernetes RBAC là các lớp quyền khác nhau. Theo TV1, Rancher Cluster Member có thể chưa đủ cài Istio vì có CRD/resource cấp cluster. OS Admin Login cho phép sudo trên VM nhưng tài khoản SSH mới chưa có kubeconfig của TV1; TV1 cần bố trí phiên thao tác phù hợp. Không sao chép `admin.conf` ra laptop/Git để tiện dùng.

TV1 giữ Terraform state, IAM, firewall, LB và mặc định quyền bật/tắt VM. TV3 không tự tạo lại node, init/join/reset hoặc cài lại Calico đang hoạt động. Xem [runbook bật/tắt lab](bat-tat-lab.md) để phân biệt lệnh Cloud Shell với lệnh trong SSH VM.

## 3. TV2 bàn giao ứng dụng và nguồn thử

| Đầu vào / người giao | Điều kiện nhận | Trạng thái ban đầu |
|---|---|---|
| Ứng dụng baseline · TV2 | Source/image đã ghim và license; request nghiệp vụ thành công trước tích hợp mesh; TV1 review baseline | Chưa bàn giao |
| Namespace / Deployment / Service · TV2 | Tên thật, selectors/labels, readiness, requests/limits, Deployment caller/target và số replica gốc | Chưa bàn giao |
| Ports · TV2 | Tách `entry_service_port`, `target_service_port`, `target_port`; ghi protocol và tên port nếu dùng | Chưa bàn giao |
| API / traffic · TV2 | GET path cụ thể trên target; path bên ngoài tạo luồng nội bộ; response/status/nội dung mong đợi; API thử không gây thay đổi dữ liệu | Chưa bàn giao |
| Hai nguồn trong mesh · TV2 | Hai Pod thực, app/debug container có curl/DNS, proxy Ready; nguồn hợp lệ và đối chứng khác cả nhãn caller lẫn ServiceAccount | Chưa bàn giao |
| Client ngoài mesh · TV2 + TV1 | Client riêng được cấp quyền cho C1b; baseline không STRICT gọi được; có cleanup, không tắt injection namespace đang có | Chưa bố trí; chỉ cần cho ca C1b |
| Dữ liệu config tích hợp · TV2 | `config/application.json` thay đủ placeholder và được renderer chấp nhận; chia sẻ config thật riêng, không commit | Chưa bàn giao |
| Luồng hợp lệ khác · TV2 | Tất cả nguồn hợp lệ tới target, cổng metrics và ingress; tránh viết policy chặn luồng nghiệp vụ cần giữ | Chưa bàn giao |
| Rollback workload · TV2 | Manifest/replica gốc và lệnh phục hồi khi restart/scale/test selector; TV2 chịu trách nhiệm các thay đổi app | Chưa bàn giao |
| Kết quả đối chứng · TV2 | DNS/HTTP/endpoint trước policy; sau mesh hai nguồn đạt C1; policy nền và các lượt phục hồi rõ ràng | Chưa bàn giao |

Điền chi tiết kỹ thuật vào [application-handover.md](application-handover.md); bảng này ghi việc đã nhận/kiểm tra và đầu mối đang chờ. Chưa có API hoặc nguồn thử phù hợp thì chuẩn bị ma trận/README trước, không apply manifest dùng tên giả.

## 4. Điều kiện chuyển từ laptop sang cloud

Chỉ bắt đầu phiên thao tác cloud khi TV1 xác nhận VM/Ready/quyền/context, TV2 giao workload baseline và cả nhóm thống nhất thời điểm. Thứ tự hiện tại theo TV1: **cụm Ready → TV2 baseline → review → TV3 Istio/observability → injection/route và kiểm tra lại → policy từng lớp → evidence và phục hồi**.

| Mục quyết định | Người xác nhận / thời gian | Kết quả |
|---|---|---|
| Trạng thái cụm và người đang dùng | Chưa điền | Chưa xác nhận |
| Phiên kubectl/Helm đúng quyền | Chưa điền | Chưa xác nhận |
| Baseline app/ports/nguồn thử | Chưa điền | Chưa xác nhận |
| Phạm vi thay đổi và rollback | Chưa điền | Chưa thống nhất |
| Người chạy / người kiểm tra chéo | Chưa điền | Chưa phân công cho lượt chạy |

Biểu mẫu này chỉ phục vụ nhận việc. Giữ kết quả test thật và ký nhận ở [mẫu evidence](evidence/templates/test-result.md) hoặc [phiếu bàn giao TV3](tv3-handover.md); không đánh dấu quyền đã cấp hoặc ca cloud đạt dựa trên unit test local.
