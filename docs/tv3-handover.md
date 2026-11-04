# TV3 · Phiếu bàn giao cho cả nhóm

Ngày lập **05/11/2026**. Source nền `17aaed9`; nhánh bàn giao là `tv3/istio-network`. Tài liệu này hướng dẫn lấy mã và nhận việc, không phải biên bản thành viên đã ký nhận hoặc nghiệm thu cloud. Xem [trạng thái thực tế](evidence/TV3-status.md).

## 1. Nhóm đang nhận những gì?

| Sản phẩm local | Dùng để làm gì? | Người nhận |
|---|---|---|
| Fixture/script NET01 hai chiều | Chứng minh Pod IP/ClusterIP/DNS xuyên worker; thu log/exit code | TV2 chạy lại, TV1 đối chiếu firewall nếu lỗi |
| Calico values và bảng phiên bản/CIDR | Cài một CNI thống nhất, so source với runtime thật | TV1/TV3 trước cài cụm |
| Script cài Istio/quan sát và snapshot | Chuẩn bị nền mesh/Prometheus/Kiali, đọc readiness/phiên bản | TV2 nhận gateway Ready để deploy app; TV1 mở lại dashboard |
| Công cụ traffic/probe | Tạo request và ghi thời điểm/status; ghi nguồn/danh tính/DNS/policy/endpoint | TV1/TV2 chạy lại OBS01/ca quyền |
| Renderer và Service thử selector | Tạo manifest theo thông số app, chẩn đoán SVC04 bằng Service riêng | TV1 sửa lỗi, TV2 gọi lại và kiểm tra Service gốc |
| Snapshot Service–Pod–EndpointSlice | Ghi UID/ClusterIP/selector/ports và ánh xạ endpoint sang Pod Ready trước/sau restart/scale | TV2 chủ trì SVC02/SVC03, TV3 kiểm tra chéo |
| Quy trình/mẫu evidence | C1–C4 riêng từng lớp, hoàn tác, kiểm tra chéo và đóng gói kết quả | Cả nhóm OPS01 |

Danh sách đóng gói tường minh nằm tại `docs/tv3-package-files.txt`; đó là source overlay và các dependency cần thiết, không phải bộ ứng dụng đã chọn hoặc bằng chứng cloud. Khi công cụ thay đổi, xem `scripts/tv3.py --help` và runbook đi cùng đúng gói.

## 2. Nhận mã từ branch TV3 trên GitHub

Đây là cách nhận code đã commit của TV3. Lần đầu, clone sang thư mục riêng để giữ nguyên công việc hiện có của người nhận:

```powershell
git clone --branch tv3/istio-network --single-branch https://github.com/ThanhThuw5206/NT132---Kubernetes-System.git NT132-TV3-review
Set-Location NT132-TV3-review
git branch --show-current
git rev-parse HEAD
uv run --offline --no-project python -m unittest discover -s tests -v
uv run --offline --no-project python scripts/tv3.py --help
```

Trên máy có Python thật dùng `python`, trên Ubuntu dùng `python3`; uv offline cần runtime đã cache. Ghi commit nhận được vào inventory/evidence. Sau khi nhóm thống nhất tích hợp, TV1/TV2 có thể merge branch này vào branch làm việc của mình; không cần giải nén ZIP lên code đã nhận đúng commit. Các ca cloud vẫn cần đầu vào và kiểm tra chéo ở mục 6.

## 3. Tùy chọn: chuyển thay đổi local chưa commit bằng ZIP

Phần này dành cho các sửa đổi mới còn chưa commit hoặc khi cần chuyển source local qua kênh riêng. **`git archive HEAD` chỉ chứa commit**, sẽ bỏ file mới/sửa chưa commit. Từ laptop có code cần chuyển, chạy:

```powershell
uv run --offline --no-project python scripts/tv3.py package
```

Lệnh không cần `config/application.json`, không commit/push và không tự gửi file. Nó tạo thư mục `.generated/tv3-*` mới, chứa:

- `tv3-overlay.zip`: các file source được cho phép và `tv3-overlay-manifest.json` bên trong.
- `manifest.json`: source nền và hash từng file trong gói để người nhận đối chiếu nội dung local.
- `SHA256SUMS`: checksum của các artifact được công cụ liệt kê.

Đọc danh sách file/manifest trước khi chuyển. Config vận hành thật, `.git`, kubeconfig/token/SSH key/Terraform state không thuộc gói. Giữ cấu hình app và thông tin truy cập riêng theo cách nhóm thống nhất. Việc tạo gói chỉ hoàn thành chuẩn bị bàn giao; người dùng chọn kênh và người nhận.

## 4. Thành viên nhận gói ZIP trên máy khác

Nhận đúng ZIP, manifest và SHA256SUMS của cùng một lần tạo gói. Trong PowerShell, đặt đường dẫn đến thư mục nhận thật:

```powershell
$PackageDir = (Resolve-Path 'DUONG_DAN_THU_MUC_NHAN_GOI').Path
Get-Content -LiteralPath (Join-Path $PackageDir 'SHA256SUMS')
Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $PackageDir 'tv3-overlay.zip')
Get-Content -LiteralPath (Join-Path $PackageDir 'manifest.json')
```

So hash ZIP với SHA256SUMS, kiểm tra source nền `17aaed9` và danh sách file đúng phần được bàn giao. Checksum giúp đối chiếu gói đã nhận; không tự chứng minh tác giả hay kết quả test cloud. Xem tên file bên trong bằng trình giải nén trước khi áp overlay.

Chuẩn bị **repo sạch riêng** ở source nền; không ghi đè thư mục làm việc còn thay đổi của thành viên khác. Ví dụ lần nhận đầu:

```powershell
git clone --branch tv1/cloud-config https://github.com/ThanhThuw5206/NT132---Kubernetes-System.git NT132-TV3-review
Set-Location NT132-TV3-review
git switch -c tv3/review-local 17aaed9
git status --short
Expand-Archive -LiteralPath (Join-Path $PackageDir 'tv3-overlay.zip') -DestinationPath (Get-Location).Path -Force
git status --short
git diff --stat
```

Chỉ giải nén sau khi đã xác nhận repo sạch/đúng base và danh sách ZIP. `-Force` áp có chủ đích source overlay lên source nền. Đọc `tv3-overlay-manifest.json` sau giải nén, đối chiếu hash/nội dung với manifest đi kèm và kiểm tra diff; không coi thông tin commit nền là commit chứa các thay đổi chưa lưu.

Chạy lại test bằng uv đã có runtime hoặc Python >=3.10 trên máy nhận:

```powershell
uv run --offline --no-project python -m unittest discover -s tests -v
uv run --offline --no-project python scripts/tv3.py --help
uv run --offline --no-project python scripts/tv3.py verify-package tv3-overlay-manifest.json
```

Nếu máy nhận chưa có uv/runtime, dùng Python thật hoặc chuẩn bị runtime trước; `--offline` không tự cài thứ chưa có. Không dùng lỗi Microsoft Store alias để kết luận bộ test hỏng.

## 5. Đưa source cho VM sau khi nhóm sẵn sàng

TV1 lấy đúng commit từ branch `tv3/istio-network`, rồi đưa source đã commit lên VM bằng archive theo [deploy-cloud.md](deploy-cloud.md). Ghi cùng commit trên cả ba VM; không dùng riêng archive cũ của TV1 để chạy các công cụ TV3 mới.

Nếu dùng thêm sửa đổi local chưa commit, chuyển **cùng gói overlay đã kiểm tra** qua IAP/SSH hoặc cách nhóm đã chọn và giải nén vào thư mục source nền sạch, đúng phiên bản. Các lệnh ZIP dưới đây chỉ dành cho phương án overlay này:

Trên VM có Python3, có thể xem và giải nén ZIP bằng thư viện chuẩn, không cần cài `unzip`:

```bash
python3 -m zipfile -l ~/tv3-overlay.zip
# Sau khi kiểm tra danh sách và đúng thư mục source nền:
python3 -m zipfile -e ~/tv3-overlay.zip ~/NT132---Kubernetes-System
cd ~/NT132---Kubernetes-System
python3 scripts/tv3.py verify-package tv3-overlay-manifest.json
python3 -m unittest discover -s tests -v
python3 scripts/tv3.py --help
```

Giữ manifest/hash gói cùng inventory và evidence để truy ra source đã chạy, kể cả khi bản source VM không có `.git`. Nếu trên VM còn thay đổi/cấu hình riêng, so sánh trước khi giải nén; không chép config vận hành vào gói source để tiện gửi.

## 6. Ai cần làm tiếp và ký nhận điều gì?

| Bàn giao | TV3 cung cấp | Thành viên tiếp tục | Điều kiện nhận / mốc |
|---|---|---|---|
| TV1 → TV3 | Ghi rõ đầu vào còn chờ | TV1 giao VM, project/zone, quyền IAP/API, join riêng và CIDR/firewall | Xác minh `wk-02` và context thật trước bootstrap; M1 |
| TV3 → TV2 | NET01 thực, namespace/Service gateway, cổng thật, Istiod/gateway Ready | TV2 bật injection, deploy app và route | TV2 chạy lại NET01, không chỉ đọc source; M1 |
| TV2 → TV3 | [Phiếu app](application-handover.md) và baseline hai nguồn | TV2 cung cấp labels/ServiceAccount/API/ports/request; TV3 kiểm tra OBS01 | App có sidecar, request tạo luồng nội bộ thật; M1 |
| TV3 → TV1 | Graph/metric cùng thời gian và cách mở lại | TV1 phát request mới và tự tìm cạnh | OBS01; không nghiệm thu từ ảnh cũ; M1 |
| TV1/TV2 → TV3 | Frontend URL và app/gateway đã đạt | TV3 kiểm tra từ ngoài VPC, gửi status/nội dung/graph về TV1/TV2 | PUB01; tách bằng chứng public với port-forward; M2 |
| TV2 → TV3 → TV1 | SEC01/SEC02 + phục hồi; SEC03 riêng + phục hồi | TV1 chạy lại luật mạng, chủ trì C4 tích hợp | Lưu policy từng lượt C1–C4 và rollback; M3 |
| TV3 → TV1 → TV2 | Service thử selector sai, triệu chứng/bằng chứng | TV1 tự sửa; TV2 gọi lại cùng URL và kiểm tra Service gốc | SVC04; dọn riêng Service thử; M4 |
| TV2 → TV3 | Kịch bản thay Pod/scale và replica gốc | TV3 đối chiếu UID/targetRef/EndpointSlice trước-sau, gọi cùng DNS | SVC02/SVC03, có phục hồi và ghi gián đoạn nếu có |
| TV1 → TV3 | Danh tính viewer/quyền cần demo | TV3 đọc dashboard và kiểm tra `can-i`, không sửa workload thật | IAM01, quyền sửa phải bị từ chối |
| Cả nhóm | Gói source/hash, hướng dẫn và evidence thật | Người khác chạy lại, ghi lỗi/sai khác và ký nhận | OPS01; khóa đúng source demo khi cả nhóm thống nhất |

## 7. Mẫu ghi nhận bàn giao thực

Sao chép cho từng lần giao, không tự điền là đã gửi/đã nhận:

```text
Người giao / người nhận:
Thời điểm và múi giờ:
Source nền / hash ZIP / hash manifest:
Đã kiểm tra danh sách file và diff:
Đầu vào cloud/app đã nhận:
Lệnh đã chạy và kết quả thực:
Test cloud đã nghiệm thu / người chạy lại:
Policy/trạng thái cluster hiện tại và rollback:
Việc còn mở / người xử lý / người đang chờ:
Link evidence / log / ảnh:
Xác nhận người nhận:
```

Phần source/hướng dẫn TV3 được bàn giao qua branch; việc thành viên nhận và chạy lại cần được ghi riêng. Chưa có ký nhận hoặc nghiệm thu cloud trong phiên này. Dùng [mẫu test](evidence/templates/test-result.md) cho từng NET01/OBS01/SEC03/SVC04/PUB01 và các ca kiểm tra chéo.
