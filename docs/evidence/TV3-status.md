# TV3 · Trạng thái và kết quả

Cập nhật **06/11/2026 (Asia/Saigon)**. Đây là nơi ghi việc đã làm và bằng chứng. Cách thực hiện nằm ở [runbook](../tv3-runbook.md), đầu vào/người nhận ở [bàn giao](../tv3-handover.md), tiêu chí ở [ma trận kiểm thử](../tv3-test-matrix.md).

## 1. Source và phạm vi

Nhánh bàn giao `tv3/istio-network` đã nhận TV1 `612e3b0` và merge fast-forward TV2 `4377766` từ `89f106d`; source nền là `17aaed9`. TV2 chọn Bookinfo, sau đó TV3 bổ sung phần tích hợp trên laptop và gộp tài liệu còn bốn file. Ghi HEAD và hash gói thực tế khi nhận mã; kết quả ở đây không thay nghiệm thu cloud.

Đợt chuẩn bị này chưa bật/tắt VM, SSH, import CA/sửa hosts, cài mesh/app hoặc apply policy trên cloud. Chỉ có các phép đọc project/VM và thử quyền IAM đã ghi dưới đây; không có nghiệm thu Kubernetes/Rancher trực tiếp bằng tài khoản TV3. Slide tạm bỏ qua theo yêu cầu.

## 2. Phần local đã hoàn thành

| Sản phẩm | Kết quả / nơi nhận |
|---|---|
| Nền mạng | NET01 sáu request hai chiều, nhận diện worker FQDN bằng InternalIP, retry và log từng lượt; script Calico có chờ trạng thái Available/Progressing/Degraded |
| Công cụ TV3 | Snapshot nền; traffic; probe nguồn/SA/DNS/policy/endpoint; Service snapshot trước-sau thay Pod/scale; Service thử selector riêng; package/verify-package |
| Bookinfo có nguồn | [Source lock](../../apps/bookinfo/source-lock.json), YAML upstream Istio 1.30.7, JSON tương đương và Apache LICENSE; SHA256 được kiểm tra trước khi sinh workload |
| Baseline offline | `prepare-bookinfo.py` sinh namespace injection disabled và 14 resource; chỉ reviews-v2 hoạt động cùng ba app còn lại; có probes và requests/limits ban đầu |
| Tích hợp route/policy | GET `/ratings/0` đúng luồng website; route tường minh productpage/static/login/logout/API; giữ principal reviews và cổng ratings 9080, tương thích config cũ |
| Readiness | Helper đọc Pod JSON, hỗ trợ proxy thường/native, phân biệt baseline không proxy với mesh; không dùng cứng cột 2/2 |
| Hướng dẫn nhóm | Baseline → TV1 review → mesh/quan sát → injection/rollout/route → policy từng lớp và phục hồi; debug cùng Pod có curl/getent và quyền phù hợp |

Workload/probes/resources là thiết kế local, chưa đo startup/RAM/OOM trên cụm. Tag image upstream `registry.istio.io/release/*:1.20.3` chưa thay được imageID/digest runtime. Chi tiết thiết kế và nguồn ở [Bookinfo README](../../apps/bookinfo/README.md); dữ liệu thật còn chờ trong [inventory](../../apps/bookinfo/service-inventory.md).

## 3. Kiểm tra đã chạy

- Python SDK **3.14.9**, Git Bash **5.3.15**: **50/50 test đạt**. Sáu kiểm tra tổng hợp đạt: unit test, source/hash/sinh baseline Bookinfo, render tích hợp, cú pháp Bash, cú pháp PowerShell và `gcloud --version`. Log/report/manifests lần kiểm tra trước khi commit: `.generated/laptop-check-chzr5nyc/`.
- Đã đối chiếu YAML/JSON upstream bằng parser có sẵn: cùng 14 resource. Runtime công cụ chỉ dùng thư viện chuẩn; `.gitattributes` giữ nguyên bytes upstream qua Windows/Linux.
- Gói source của đợt tích hợp đã được kiểm tra checksum, giải nén sang thư mục riêng và chạy lại đủ 50 test đạt. Lượt gọn tài liệu cập nhật liên kết/allowlist và kiểm tra lại gói; số file của từng gói nằm trong manifest, không dùng ZIP cũ để nhận phần tài liệu mới.
- Python **3.15.2 qua uv** bị Windows Application Control chặn DLL `_overlapped` ở lượt 06/11, cả trong và ngoài sandbox. Không đổi chính sách Windows; dùng runtime SDK theo runbook. Kết quả 37 test trước đây được thay bằng kết quả 50 test mới ở trên.

Test dùng mock/HTTP loopback và không gọi API project. Kết quả offline không chứng minh VM Ready, traffic Kiali hoặc policy cloud đã đạt.

## 4. Truy cập đã kiểm tra

| Lần kiểm tra | Kết quả có bằng chứng | Giới hạn |
|---|---|---|
| API chỉ đọc ngày 05/11 | Tài khoản ACTIVE, đọc được project `nt132-kubernetes-513805` và ba VM ở `asia-southeast1-a` | Không ghi email/token vào repo |
| IAM đã thử | OS Login/Admin và IAP có hiệu lực trên cp-01/wk-02 | Chưa thử kết nối SSH, firewall, sudo hoặc Kubernetes thực tế |
| Sau khi TV1 phân lại quyền | `testIamPermissions` trả có start và stop trên cả cp-01/wk-01/wk-02 | Chỉ thử quyền, không bật/tắt VM; không gọi lại IAM trong đợt sửa/gọn tài liệu |
| Snapshot Compute ngày 05/11 | Ba VM TERMINATED, IP nội bộ 10.20.0.10/.11/.12 | Là dữ liệu lịch sử; trạng thái chạy/dừng hiện tại chưa kiểm tra lại |

## 5. Cloud và kiểm tra chéo còn chờ

TV1 `612e3b0` ghi nhận ngày 05/11: ba node v1.35.10 Ready, Pod IP/ClusterIP/DNS trả 200, Rancher đủ ba node Active; Istio/Kiali/app/policy chưa triển khai. Đây là ghi nhận bàn giao của TV1, chưa được TV3 kiểm tra lại trong đợt local.

| Việc | Trạng thái TV3 / đầu vào cần tiếp |
|---|---|
| Tiếp nhận wk-02, Calico và NET01 | Chưa SSH/chạy lại trên cụm; cần phiên/quyền và lịch lab. Không prepare/join/reset/cài lại CNI hiện có |
| App baseline trước mesh | TV2 chưa deploy/nghiệm thu; cần hai nguồn HTTP/DNS, endpoint Ready và TV1 review |
| Istio, gateway, Prometheus/Kiali | Chưa cài/nghiệm thu; cần baseline, Helm/quyền cấp cluster và lịch tích hợp |
| OBS01, SEC01–04, SVC04 | Chưa chạy trên ứng dụng; cần proxy/route, dữ liệu app và nguồn thử thật, policy nền/rollback |
| IAM01, SVC02/SVC03, PUB01, OPS01 | Chưa kiểm tra chéo; cần viewer riêng, lịch thử app/LB và thành viên chạy lại |

TV3 chủ trì NET01/OBS01/SEC03/SVC04; TV2 sở hữu workload/Service/route và luật Istio; TV1 sở hữu hạ tầng/Rancher/LB. Điều kiện giao nhận chi tiết chỉ cập nhật tại [phiếu bàn giao](../tv3-handover.md). Chỉ ghi Đạt khi có kết quả thực, phục hồi và người thứ hai chạy lại.

## 6. Nguồn phân công và điều chỉnh so với kế hoạch

Đã đối chiếu [kế hoạch repo](../plan.md) và file người dùng cung cấp `E:\Down\KE_HOACH_TONG_THE_KUBERNETES_3_VM_GOOGLE_CLOUD.md`, SHA256 `591D4A3BD7EAC2ACAF78C0BE148D8E3EF23D47D49683412CA5B660F3FBA0CCB2`. Kế hoạch/lịch không phải bằng chứng thao tác đã chạy.

| Kế hoạch gốc | Quyết định trong source hiện tại |
|---|---|
| Bookinfo / reviews → ratings | TV2 đã tự chốt Bookinfo tại 4377766; dùng thiết kế đã bàn giao, runtime còn chờ |
| Control plane 4 GiB/20 GB, worker disk 30 GB | Terraform hiện đặt ba VM 8 GiB, tổng boot disk 30+40+40=110 GB; không dựng trùng hạ tầng |
| Headlamp trước, Rancher tuần 2 | TV1 đã đưa Rancher vào sớm; TV3 tập trung Prometheus/Kiali và mạng/policy |
| NodePort tuần 2 | Gateway đã cấu hình NodePort 30080; public LB tùy chọn, tunnel không thay PUB01 |
| Thử cộng dồn policy | C2/C3 phải chạy riêng và phục hồi trước C4 kết hợp, theo ma trận |

Mốc dự kiến của kế hoạch: M1 06/11, M2 13/11, M3 20/11, M4 27/11; không suy ra mốc đã hoàn thành từ ngày trên lịch. Chốt source/phiên demo theo kết quả thật của nhóm.
