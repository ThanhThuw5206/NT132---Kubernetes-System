# TV3 · Nhận source, đầu vào và bàn giao

Cập nhật **07/11/2026**. Nhánh bàn giao `tv3/istio-network`, source nền `17aaed9`, gồm phần tích hợp Bookinfo và bộ tài liệu TV3 đã gộp. Người nhận ghi commit thực tế sau khi lấy mã. Xem [trạng thái đã kiểm tra](evidence/TV3-status.md); file này là checklist nhận việc, chưa phải ký nhận hay nghiệm thu cloud.

Thao tác laptop/cloud ở [runbook TV3](tv3-runbook.md); kỳ vọng, rollback và người chạy lại ở [ma trận test](tv3-test-matrix.md). TV1 giữ hạ tầng/Rancher/LB; TV2 giữ workload/Service/route và luật Istio; TV3 phụ trách mạng, mesh nền, quan sát, NetworkPolicy và bài selector.

**Bản bàn giao ngày 07/11 sau cloud và merge TV2 `8260fc9`:** source gồm Calico APIServer tối thiểu, Istio/giám sát, sửa helper EndpointSlice rỗng, fixture kết nối mới và kết quả kỹ thuật NET01/OBS01/C0–C4/C1b/SVC01–04 cùng phục hồi tại [TV3-status](evidence/TV3-status.md). Chưa có người khác kiểm tra chéo/ký nhận. Lấy commit mới trên nhánh `tv3/istio-network` theo mục 1; bản clone cũ cần cập nhật trước khi đối chiếu. Evidence raw chỉ giữ tại laptop TV3, không nằm trong repo.

Khi mở lại lab, giữ Istio/Prometheus/Kiali và Bookinfo injection/route đã cài; kiểm tra Ready rồi làm tiếp, không bootstrap worker/CNI hoặc apply namespace baseline tắt injection. Policy, Service/client và DestinationRule thử đã dọn, replicas gốc đã phục hồi. Xem [inventory thực](../apps/bookinfo/service-inventory.md), hướng dẫn kết nối mới trong [suite policy](../tests/security/README.md) và trạng thái VM cuối phiên tại TV3-status.

**Cả ba VM đã TERMINATED lúc 00:06:38 ngày 07/11.** Việc nhận tiếp: TV1 kiểm tra viewer/IAM01, review graph và bàn giao frontend PUB01 khi LB sẵn sàng; TV2 đối chiếu inventory/route, chạy lại Service/mTLS/API và NET01; TV3 phối hợp OBS01/NetworkPolicy/selector và lưu ký nhận OPS01. Người chạy lại dùng Pod/UID hiện tại sau khi mở lab, giữ log thất bại và lượt phục hồi; không chép số đo lịch sử thành kết quả mới. Gói evidence nguyên bản ở laptop TV3 cần được rà thông tin trước khi chia sẻ; bản tóm tắt sạch nằm tại TV3-status/inventory.

## 1. Nhận đúng source

**Code đã push:** clone sang thư mục riêng để giữ công việc hiện có của người nhận, rồi ghi commit vào inventory/evidence:

```powershell
git clone --branch tv3/istio-network --single-branch https://github.com/ThanhThuw5206/NT132---Kubernetes-System.git NT132-TV3-review
Set-Location NT132-TV3-review
git rev-parse HEAD
```

Thành viên chạy checker theo runbook trước khi tích hợp vào branch của mình. Ghi HEAD của bản đã nhận; các sửa đổi local phát sinh về sau chỉ được chia sẻ qua Git sau khi commit/push hoặc qua gói overlay đã kiểm tra.

**Sửa đổi chưa commit:** `git archive HEAD` chỉ lấy commit. Tạo gói source overlay bằng Python đang hoạt động theo runbook:

```text
python scripts/tv3.py package
```

Gói `.generated/tv3-*` có `tv3-overlay.zip`, `manifest.json` và `SHA256SUMS`; ZIP chứa thêm `tv3-overlay-manifest.json`. [Allowlist](tv3-package-files.txt) quy định source/dependency được lấy, bao gồm sửa đổi chưa commit. Lệnh không cần config vận hành, không tự commit, push hoặc gửi cho ai. Không chuyển SDK/cache đăng nhập, kubeconfig/token, SSH key, Terraform state hoặc `config/application.json` trong gói source.

Người nhận ZIP làm theo thứ tự sau, dùng các artifact của **cùng lần đóng gói**:

1. Đọc manifest/danh sách ZIP; so SHA256 ZIP và manifest với `SHA256SUMS`, xác nhận base `17aaed9`. Checksum đối chiếu nội dung, không tự chứng minh tác giả hoặc test cloud.
2. Chuẩn bị repo sạch riêng ở base, không giải nén đè thư mục còn thay đổi. Ví dụ PowerShell:

```powershell
$PackageDir = (Resolve-Path 'DUONG_DAN_THU_MUC_NHAN_GOI').Path
Get-Content -LiteralPath (Join-Path $PackageDir 'SHA256SUMS')
Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $PackageDir 'tv3-overlay.zip')
Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $PackageDir 'manifest.json')
Get-Content -LiteralPath (Join-Path $PackageDir 'manifest.json')
git clone --branch tv1/cloud-config https://github.com/ThanhThuw5206/NT132---Kubernetes-System.git NT132-TV3-review
Set-Location NT132-TV3-review
git switch -c tv3/review-local 17aaed9
git status --short
```

3. Chỉ sau khi hash/danh sách đúng và repo sạch, áp overlay rồi kiểm tra. `python` dưới đây là Python >=3.10 thực; máy hiện tại dùng runtime trong runbook, Ubuntu dùng `python3`.

```powershell
Expand-Archive -LiteralPath (Join-Path $PackageDir 'tv3-overlay.zip') -DestinationPath (Get-Location).Path -Force
git diff --stat
python scripts/tv3.py verify-package tv3-overlay-manifest.json
python -m unittest discover -s tests -v
```

Đối chiếu `tv3-overlay-manifest.json` trong ZIP với manifest đi kèm; giữ manifest/hash và kết quả test cùng biên bản nhận. Commit nền không đại diện cho những file local chưa commit.

Khi đưa source lên VM, TV1 dùng archive đúng commit hoặc chuyển chính gói overlay đã kiểm tra theo [deploy-cloud](deploy-cloud.md). Giữ cấu hình riêng của VM trước khi cập nhật. Với repo nguồn sạch đúng base, Ubuntu có thể xem/giải nén ZIP bằng `python3 -m zipfile -l` / `python3 -m zipfile -e`, rồi chạy `verify-package` và test như trên; không cần `unzip`. Ghi source/hash đang chạy trên các VM.

## 2. Đầu vào TV1 bàn giao

Điền **Đã nhận và kiểm tra / Chưa nhận / Bị chặn**, người giao và thời điểm vào biên bản cuối file. Trạng thái IAM/VM đã kiểm tra trước đây chỉ ghi tại [TV3-status](evidence/TV3-status.md); không suy quyền hoặc trạng thái hiện tại từ việc có hướng dẫn.

| Đầu vào | Điều kiện TV3 cần nhận / phần còn chờ |
|---|---|
| Inventory và lịch phiên | Project `nt132-kubernetes-513805`, zone `asia-southeast1-a`, VM cp-01/wk-01/wk-02, IP nội bộ .10/.11/.12; xác nhận cụm Ready và người đang dùng lab. Tên Node có thể là FQDN. |
| Google IAM và SSH/IAP | Tài khoản riêng, quyền đúng phạm vi; kiểm tra kết nối SSH/firewall/sudo thực tế. Có quyền start/stop vẫn cần phối hợp người đang dùng lab. |
| Kubernetes/Helm | Context đúng và phiên có quyền cài CRD/resource mesh cấp cluster; quyền đọc policy app/root mesh, log, exec, port-forward; quyền debug/client riêng nếu cần. Phiên sudo/admin.conf đã thử ở nhiệm vụ 1, xem trạng thái; quyền Rancher/viewer và RBAC riêng vẫn xác nhận độc lập. |
| Rancher | User riêng, cluster/project/role đúng; mật khẩu tạm qua kênh riêng. Cluster Member có thể chưa đủ cài Istio. |
| CA, hostname, tunnel | Chỉ nhận `ca.crt` công khai, đối chiếu CA/hostname trước import; không nhận private key. Chốt hosts/port và người giữ port-forward để tránh trùng phiên. |
| Thay đổi/rollback | Lịch cài Istio/Prometheus/Kiali, namespace được dùng, policy nền cần giữ, người sở hữu và trạng thái phải phục hồi. |
| Frontend public, giai đoạn sau | URL/IP/cổng, nguồn cho phép, LB health/firewall cho PUB01; không cần để chuẩn bị local. |

Google IAM, Rancher và Kubernetes RBAC là ba lớp quyền khác nhau. OS Admin Login cho phép sudo nhưng tài khoản SSH mới chưa tự có kubeconfig của TV1. TV1 bố trí phiên quản trị phù hợp; không chép `admin.conf` ra laptop/Git để tiện dùng. TV3 tiếp nhận worker/Calico đang hoạt động, không init/join/reset hoặc cài CNI lại.

## 3. Đầu vào TV2 và thứ tự giao nhận

Thiết kế Bookinfo đã có tại [apps/bookinfo](../apps/bookinfo/README.md): namespace `bookinfo`, entry `productpage:9080`, target `ratings:9080`, Pod TCP 9080; caller reviews-v2/SA bookinfo-reviews, đối chứng productpage-v1/SA bookinfo-productpage; website `/productpage`, API GET `/ratings/0`. Các giá trị này còn phải đối chiếu triển khai thật.

| TV2 bàn giao | Điều kiện nhận / dữ liệu runtime còn chờ |
|---|---|
| Baseline và nguồn workload | TV3 đã kiểm tra HTTP/nội dung trước mesh; Pod/Service/endpoint và imageID sau injection đã ghi trong [inventory](../apps/bookinfo/service-inventory.md). Còn chờ TV1 review và TV2 đối chiếu/chạy lại độc lập. |
| Service/Pod/ports | Selector, labels, readiness/resources, Service UID/ClusterIP/port/targetPort, Deployment/replica gốc và EndpointSlice targetRef; ghi tên Pod/UID/IP/node thật. |
| Hai nguồn trong mesh | Cùng namespace, proxy Ready; khác cả labels và ServiceAccount. Container app/debug đúng Pod có `curl` và `getent`; không exec trong istio-proxy thay nguồn. |
| API/traffic và luồng hợp lệ | Request không đổi dữ liệu, response/status/nội dung mong đợi; liệt kê mọi nguồn hợp lệ vào target, ingress và metrics. Config tham chiếu đã render local, config vận hành đối chiếu runtime và giữ ngoài Git. |
| Client ngoài mesh C1b | Quyền tạo client riêng, lượt thành công trước STRICT và cleanup; không tắt injection namespace đang dùng để tạo đối chứng. |
| Policy và phục hồi | Policy app/root mesh/CNI đang có; C0/C1 hai nguồn, kết quả C2 và rollback trước TV3 thử C3; manifest/replica gốc cho restart/scale. |

Điền chi tiết ở [phiếu app](application-handover.md); thực hiện theo [runbook TV2](tv2-runbook.md). Thứ tự chung:

1. TV1 xác nhận cụm/quyền; TV3/TV2 NET01. TV2 deploy baseline không proxy rồi TV1 review.
2. TV3 cài mesh/quan sát, giao gateway Ready/cổng thật; TV2 bật injection, rollout và route, kiểm tra baseline lần nữa.
3. TV2 giao nguồn/Service/endpoint thật; TV3 chạy OBS01, TV1 tạo traffic mới và tìm lại graph/metric.
4. TV2 C1/C2 và phục hồi → TV3 C3 riêng và phục hồi → TV1 chạy lại/C4. TV2 thay Pod/scale, TV3 chụp chéo SVC02/SVC03; SVC04 TV3 tạo Service riêng, TV1 sửa, TV2 gọi lại.
5. TV1 giao frontend để TV3 kiểm tra PUB01; cả nhóm chạy lại OPS01, ghi sai khác và nguồn demo. Xem ma trận cho tiêu chí từng ca, không lấy test local thay kết quả cloud.

## 4. Biên bản một lần nhận/bàn giao

```text
Người giao / người nhận / thời điểm và múi giờ:
Branch/commit hoặc base + hash ZIP/manifest; đã so danh sách/hash/diff:
Đầu vào nhận được và trạng thái Đã kiểm tra / Chưa nhận / Bị chặn:
Context/namespace; người đang dùng lab; phạm vi thay đổi và rollback:
Lệnh/kết quả thực; link evidence; người chạy lại và xác nhận:
Policy/trạng thái sau buổi; lỗi còn mở / người xử lý / người đang chờ:
```

Không ghi token, mật khẩu, private key, kubeconfig hoặc email cá nhân vào biên bản trong repo. Kết quả từng ca dùng [mẫu evidence](evidence/templates/test-result.md); chỉ đánh dấu Đạt khi có kết quả thực, phục hồi và người khác chạy lại.
