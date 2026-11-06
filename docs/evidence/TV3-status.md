# TV3 · Trạng thái và kết quả

Cập nhật **07/11/2026 (Asia/Saigon)**, sau phiên cloud tối 06/11. Đây là nơi ghi việc đã làm và bằng chứng. Cách thực hiện nằm ở [runbook](../tv3-runbook.md), đầu vào/người nhận ở [bàn giao](../tv3-handover.md), tiêu chí ở [ma trận kiểm thử](../tv3-test-matrix.md).

## 1. Source và phạm vi

Nhánh bàn giao `tv3/istio-network` đã nhận TV1 `612e3b0` và merge fast-forward TV2 `4377766` từ `89f106d`; source nền là `17aaed9`. TV2 chọn Bookinfo, sau đó TV3 bổ sung phần tích hợp trên laptop và gộp tài liệu còn bốn file. Ghi HEAD và hash gói thực tế khi nhận mã; kết quả ở đây không thay nghiệm thu cloud.

Phần chuẩn bị laptop đã hoàn tất. Ngày 06/11 TV3 chạy NET01 trên cụm thật (mục 7), sau đó theo yêu cầu tiếp tục xử lý Calico, cài mesh/quan sát và tích hợp Bookinfo (mục 8). **Kết quả kỹ thuật và kiểm tra chéo là hai trạng thái riêng**; chưa có thành viên khác ký nhận. Không import CA/sửa hosts hoặc nghiệm thu Rancher UI. Slide tạm bỏ qua. Bản bàn giao ngày 07/11 trên `tv3/istio-network` gồm source sau cloud, cập nhật TV2 và tài liệu này; evidence raw vẫn giữ tại laptop.

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

Chi tiết thiết kế và nguồn ở [Bookinfo README](../../apps/bookinfo/README.md); số liệu quan sát trên cụm ở [inventory](../../apps/bookinfo/service-inventory.md). Readiness đã được kiểm tra sau injection; chưa có phép đo tải dài hạn/RAM/OOM. Không lấy image tag nguồn thay imageID/digest runtime.

## 3. Kiểm tra đã chạy

- Python SDK **3.14.9**, Git Bash **5.3.15**: **50/50 test đạt**. Sáu kiểm tra tổng hợp đạt: unit test, source/hash/sinh baseline Bookinfo, render tích hợp, cú pháp Bash, cú pháp PowerShell và `gcloud --version`. Log/report/manifests lần kiểm tra trước khi commit: `.generated/laptop-check-chzr5nyc/`.
- Đã đối chiếu YAML/JSON upstream bằng parser có sẵn: cùng 14 resource. Runtime công cụ chỉ dùng thư viện chuẩn; `.gitattributes` giữ nguyên bytes upstream qua Windows/Linux.
- Gói source của đợt tích hợp đã được kiểm tra checksum, giải nén sang thư mục riêng và chạy lại đủ 50 test đạt. Lượt gọn tài liệu cập nhật liên kết/allowlist và kiểm tra lại gói; số file của từng gói nằm trong manifest, không dùng ZIP cũ để nhận phần tài liệu mới.
- Python **3.15.2 qua uv** bị Windows Application Control chặn DLL `_overlapped` ở lượt 06/11, cả trong và ngoài sandbox. Không đổi chính sách Windows; dùng runtime SDK theo runbook. Kết quả 37 test trước đây được thay bằng kết quả 50 test mới ở trên.
- Sau sửa lỗi EndpointSlice rỗng, checker lúc **00:04 ngày 07/11** đạt **51/51 test**, source/hash Bookinfo, render, cú pháp Bash/PowerShell và gcloud version. Log/report: `.generated/tv3-cloud-setup-534ca265/final-laptop-check/`. Phần snapshot và probe đều xử lý endpoint null, vẫn ghi chưa đạt khi đích không có endpoint Ready.

Test dùng mock/HTTP loopback và không gọi API project. Kết quả offline không chứng minh VM Ready, traffic Kiali hoặc policy cloud đã đạt.

## 4. Truy cập đã kiểm tra

| Lần kiểm tra | Kết quả có bằng chứng | Giới hạn |
|---|---|---|
| API chỉ đọc ngày 05/11 | Tài khoản ACTIVE, đọc được project `nt132-kubernetes-513805` và ba VM ở `asia-southeast1-a` | Không ghi email/token vào repo |
| SSH/IAP thực ngày 06/11 | SSH được cp-01/wk-02; sudo không tương tác thành công, containerd/kubelet active | Kết nối bị gián đoạn khi cụm dừng lúc 22:00; sau bật lại đã xác minh thành công |
| Phiên Kubernetes/Helm | API trả ok, dùng `sudo` với `/etc/kubernetes/admin.conf` trên cp-01, Helm v3.19.0 đọc được release; quyền cần cho NET01 và tạo CRD trả yes | Context cá nhân mặc định chưa cấu hình; không sao chép admin.conf ra laptop. Đây chưa phải quyền Rancher/viewer hoặc RBAC Kubernetes riêng |
| Quyền vòng đời VM | Đã thử quyền và thực hiện start/stop thành công trên cả ba VM | Không sửa IAM/firewall, không chạy Terraform hoặc xóa VM/disk |
| Cuối nhiệm vụ 1 ngày 06/11 | cp-01/wk-01/wk-02 đều **TERMINATED**, IP nội bộ vẫn .10/.11/.12 | Dừng hai worker trước rồi control plane; không có VM nào còn RUNNING ở lần xác nhận cuối |
| Cuối phiên tích hợp ngày 07/11 lúc 00:06:38 UTC+07 | API xác nhận lại **cp-01/wk-01/wk-02 đều TERMINATED** | Bằng chứng đã về laptop; dừng hai worker hoàn tất rồi mới dừng control plane |

## 5. Cloud và kiểm tra chéo còn chờ

TV1 `612e3b0` ghi nhận cụm/Service/Rancher hoạt động ngày 05/11. TV3 đã trực tiếp kiểm tra hạ tầng, HTTP Bookinfo trước/sau mesh và NodePort. Review của TV1/TV2 và nghiệm thu Rancher UI vẫn còn chờ; kết quả tự động không thay chữ ký hoặc thao tác độc lập của thành viên khác.

| Việc | Trạng thái TV3 / đầu vào cần tiếp |
|---|---|
| Tiếp nhận wk-02, Calico và NET01 | Worker cấu hình đúng; NET01 đạt 6/6, fixture đã dọn. Đã bổ sung APIServer để xử lý tiers, giữ nguyên Installation/IP pool; chờ TV2 chạy lại NET01 |
| App baseline trước mesh | Đã kiểm tra website/reviews/ratings HTTP 200, nội dung reviewer/rating đúng; bốn app Ready, reviews-v1/v3 giữ 0. Chờ TV1/TV2 review độc lập |
| Istio, gateway, Prometheus/Kiali | Đã cài và rollout thành công; Bookinfo có proxy/route, NodePort cả hai worker đạt HTTP 200 và 9 sao |
| OBS01, C0–C4/C1b, SVC01–04 | Đã có kết quả kỹ thuật và phục hồi qua các lượt ở mục 8; còn chờ TV1/TV2 chạy lại, ảnh Kiali/UI và ký nhận |
| IAM01, PUB01, OPS01 | Còn chờ viewer riêng, frontend LB và thành viên chạy lại. API forwarding-rules trả danh sách rỗng; không tạo LB hoặc tự thay RBAC |

TV3 chủ trì NET01/OBS01/SEC03/SVC04; TV2 sở hữu workload/Service/route và luật Istio; TV1 sở hữu hạ tầng/Rancher/LB. Điều kiện giao nhận chi tiết chỉ cập nhật tại [phiếu bàn giao](../tv3-handover.md). Chỉ ghi Đạt khi có kết quả thực, phục hồi và người thứ hai chạy lại.

## 6. Nguồn phân công và điều chỉnh so với kế hoạch

Đã đối chiếu [kế hoạch repo](../plan.md) và file người dùng cung cấp `E:\Down\KE_HOACH_TONG_THE_KUBERNETES_3_VM_GOOGLE_CLOUD.md`, SHA256 `591D4A3BD7EAC2ACAF78C0BE148D8E3EF23D47D49683412CA5B660F3FBA0CCB2`. Kế hoạch/lịch không phải bằng chứng thao tác đã chạy.

| Kế hoạch gốc | Quyết định trong source hiện tại |
|---|---|
| Bookinfo / reviews → ratings | TV2 đã tự chốt Bookinfo tại 4377766; đã đối chiếu runtime ở mục 8 và inventory, còn chờ review độc lập |
| Control plane 4 GiB/20 GB, worker disk 30 GB | Terraform hiện đặt ba VM 8 GiB, tổng boot disk 30+40+40=110 GB; không dựng trùng hạ tầng |
| Headlamp trước, Rancher tuần 2 | TV1 đã đưa Rancher vào sớm; TV3 tập trung Prometheus/Kiali và mạng/policy |
| NodePort tuần 2 | Gateway đã cấu hình NodePort 30080; public LB tùy chọn, tunnel không thay PUB01 |
| Thử cộng dồn policy | C2/C3 phải chạy riêng và phục hồi trước C4 kết hợp, theo ma trận |

Mốc dự kiến của kế hoạch: M1 06/11, M2 13/11, M3 20/11, M4 27/11; không suy ra mốc đã hoàn thành từ ngày trên lịch. Chốt source/phiên demo theo kết quả thật của nhóm.

## 7. Kết quả nhiệm vụ 1 / NET01 thực · 06/11/2026

**Thời gian NET01: 22:16:39–22:16:55 UTC+07:00.** Source `2782c613950f64a0753724383612e0dc0d783044`, chạy từ thư mục `/tmp` riêng trên cp-01; không ghi đè source đang có trên VM. Context `kubernetes-admin@nt132`, namespace thử `network-check`, TCP 80; thực thi qua sudo/admin.conf tại server, không xuất credential ra laptop.

Ba node Ready đúng IP 10.20.0.10/.11/.12, Kubernetes **v1.35.10**, containerd **2.2.1**; Helm **v3.19.0**. CoreDNS Ready **2/2**. Tigera `calico` và `ippools`: Available=True, Progressing=False, Degraded=False. **Riêng `tiers` Degraded=True**, thông báo chờ Tigera API server; ghi nhận để TV1/TV3 xem tiếp, chưa thay cấu hình CNI trong lượt này.

Các giá trị sau thuộc lượt chạy đã lưu, fixture hiện đã dọn:

| Hướng | Pod IP đích | Service ClusterIP | Service DNS | Kết quả |
|---|---|---|---|---|
| wk-02 → wk-01 | 10.244.95.24 | 10.109.250.119 | server.network-check.svc.cluster.local | Cả ba HTTP 200, curl exit 0 ngay lần đầu |
| wk-01 → wk-02 | 10.244.26.105 | 10.106.188.214 | server-reverse.network-check.svc.cluster.local | Cả ba HTTP 200, curl exit 0 ngay lần đầu |

Đã đối chiếu bốn Pod Ready ở đúng worker, Service selector/port và EndpointSlice Ready/targetRef khớp Pod UID/IP, script exit 0. Hai nhãn worker giữ nguyên. **Người chạy: phiên TV3; người chạy lại: chưa có** — chưa đóng nghiệm thu NET01 có kiểm tra chéo.

Bằng chứng local: `.generated/tv3-task1-live-b1c36d8b/`, gồm `verified-task1.json`, `net01-evidence.tar.gz`, log và JSON Pod/Service/EndpointSlice. SHA256 archive: `5a9a1fdf535702d074d46836005d6fc39df8c1e0b163ab4da83fb0989fe4b47c`. Đã kiểm tra checksum sau tải về; raw SSH log/cache đăng nhập không đưa vào Git.

**Hoàn tác:** kiểm tra UID/nhãn sở hữu rồi xóa đúng bốn Pod, hai Service; kiểm kê các loại tài nguyên namespaced trước khi xóa namespace thử. Bookinfo vẫn có bốn Deployment Ready trước khi tắt, reviews-v1/v3 giữ 0. Sau khi lưu bằng chứng, dừng wk-01/wk-02 rồi cp-01; `vm-final-state.json` xác nhận cả ba TERMINATED. Kết quả/hướng dẫn đã đưa vào bản bàn giao; log và archive gốc ở đường dẫn local phía trên.

## 8. Tích hợp và kiểm thử cloud · tối 06/11–00:00 ngày 07/11/2026

Theo yêu cầu làm tiếp các phần TV3 có thể thực hiện, chạy từ thư mục `/tmp/nt132-tv3-setup.dLH15twV` riêng trên cp-01, context `kubernetes-admin@nt132`; không ghi đè repo đang có trên VM. Source nền `2782c613950f64a0753724383612e0dc0d783044` cùng sửa đổi local được ghi SHA256 từng file trong `.generated/tv3-cloud-setup-534ca265/source-manifest.json`. Gói cài SHA256 `e8e996ee6542ba1f12bacb731b6cecb39466426afce6813c6065af5d04ae105b`; test driver của lượt chạy lại SHA256 `4389e72fd9018de5c5e3603aea7d0753719663e3c2d6fb2f0d0dc4e0ba4958fe`.

**Nền tảng đã hoàn tất lúc 23:30:47 UTC+07:** wk-02 có kubelet/containerd active, swap tắt, sysctl/cgroup/package hold đúng; không chạy setup/join lại. Thêm duy nhất `APIServer/default` tối thiểu: apiserver và tiers Available, Installation/IP pool giữ nguyên. Cài Istio **1.30.7** gồm base/istiod/gateway, Prometheus/Kiali theo addon cùng tag; giới hạn Prometheus cho lab. Bật injection riêng `bookinfo`, rollout bốn app, reviews-v1/v3 giữ 0, áp Gateway/VirtualService. Tất cả app/proxy Ready; website trước/sau mesh có reviewer và rating.

**NodePort/SVC01:** lúc 23:38:42 UTC+07, cp-01 gọi `http://10.20.0.11:30080/productpage` và `.12:30080/productpage`: cả hai HTTP 200, hai reviewer và **9 sao SVG**. Snapshot cụm và Service exit 0. Đây là đường nội bộ VPC, chưa phải PUB01. Gateway ClusterIP `10.105.30.70`; Prometheus `10.96.7.235:9090`; Kiali `10.98.231.20:20001/kiali`, đều dùng đường quản trị riêng.

Lượt đầu đã có metric/graph reviews-v2 → ratings nhưng bị ngắt có chủ đích để sửa checker HTML (sao SVG nằm ở `id`, không ở `class`) và việc ghi PID debug qua kubelet. Giữ nguyên log lỗi/C0 bị ngắt; đã xác minh dừng debug cũ. Lượt thứ hai C3 còn trả 200 trên nguồn đối chứng. Lượt kiểm soát kết nối mới giữ DestinationRule thử tạm từ trước C0 đến sau C4 đã ghi nhận chặn đúng; không cần đổi CNI/IP pool. Việc xử lý kết nối đang tồn tại phụ thuộc implementation theo [tài liệu Kubernetes](https://kubernetes.io/docs/concepts/services-networking/network-policies/#networkpolicy-and-existing-connections); không suy riêng một HTTP 200 thành lỗi CNI.

| Ca / lượt bằng chứng | Kết quả kỹ thuật quan sát |
|---|---|
| OBS01 · `run-20261106T163943Z-7a3e9d` | Traffic gateway 180 giây, toàn HTTP 200; Prometheus reviews-v2 → ratings rate dương khoảng 0,60 req/s, Kiali API graph có cạnh đúng principal/workload, rate khoảng 0,55; chưa có ảnh UI hoặc TV1 phát lại traffic |
| C0/C1 · `run-20261106T165356Z-2892d8` | Hai nguồn reviews/productpage cùng HTTP 200 trước/sau STRICT; counter đích `mutual_tls` đúng reviews → ratings tăng **369 → 376** |
| C1b · cùng lượt | Client riêng không proxy, UID 1000: HTTP 200 trước STRICT → curl exit 56/HTTP 000 (connection reset) khi STRICT → HTTP 200 sau gỡ STRICT; client đã xóa |
| C2 · cùng lượt | reviews HTTP 200, productpage gọi thẳng ratings HTTP 403; API đối chứng `/ratings/1` từ reviews: 200 trước luật → 403 khi luật bật. Lưu proxy log/RBAC; gỡ AuthorizationPolicy thì hai nguồn phục hồi 200 |
| C3 · cùng lượt | Chỉ NetworkPolicy hạn chế trên baseline STRICT: reviews 200; productpage DNS thành công, endpoint Ready nhưng curl exit **28/HTTP 000**, matcher khớp. Gỡ NetworkPolicy: hai nguồn lại 200 |
| C4 · cùng lượt | Cả hai luật bật: reviews 200, đối chứng exit 28/000; website qua gateway HTTP 200, hai reviewer và **9 sao**. Gỡ riêng luật, hai nguồn phục hồi 200 |
| SVC02/SVC03 · cùng lượt | ratings scale **1 → 2 → 1**; đối chiếu đủ tập UID Pod Ready với EndpointSlice. Chỉ xóa Pod cũ sau khi có backend thứ hai Ready; thấy Pod UID mới, DNS/HTTP phục hồi, Service UID/ClusterIP giữ nguyên. Template và replica gốc đã phục hồi; không suy ra chia tải đều |
| SVC04 · `run-20261106T170006Z-1a0642` | Kết thúc **00:00:36 ngày 07/11**: selector sai vẫn có DNS nhưng không có endpoint Ready/HTTP thành công; sửa đúng thì endpoint khớp Pod và HTTP 200. Service thử giữ UID `641817db-8e58-4d71-8b56-8c0fbf1d4658`, ClusterIP `10.109.48.167`; đã xóa, ratings thật không đổi |

Lượt policy/Service dừng tại SVC04 do helper chưa xử lý `EndpointSlice.endpoints: null`; đã sửa helper, thêm regression test và chạy lại **riêng SVC04** đạt, không chạy lại restart/scale thừa. Vì vậy không ghi toàn bộ mọi lượt đều thành công: giữ các summary lỗi gốc và kết quả chạy lại theo từng ca. Fixture tái hiện kết nối mới ở [security README](../../tests/security/README.md), được tạo/xóa riêng bằng UID trong lượt thực. Driver policy SHA256 `c97b6c44bd60441555e6491bed40f499d74bcf515b86da5bdf481bedff82a6e1`; driver SVC04 SHA256 `8b96f03a0470595be94454c9a44731071b9c9d01e6561fa805ec31a129b4bdd1`.

**Đã phục hồi trước tắt máy:** không còn policy/Service/client/DestinationRule thử; ratings Service giữ UID/spec gốc, replicas bốn app = 1, reviews-v1/v3 = 0; mọi debug TV3 terminated, app/proxy Ready. Giữ lại Istio/Prometheus/Kiali, namespace injection và Gateway/VirtualService để bàn giao; không áp lại baseline tắt injection.

Bằng chứng đầy đủ local: `.generated/tv3-cloud-setup-534ca265/final-evidence/.cloud-evidence/`, gồm các thư mục `test-suite/run-*`, `nodeport`, `final`, log cài và JSON gốc. Archive `final-cloud-evidence.tar.gz` SHA256 **`dce4f21d06379aeaee132f7c8fb055cf53c8f021420c3dc10783092171d67fb1`**, đã so sau tải và giải nén. `final/verification.json` chốt cleanup lúc **00:01:20 ngày 07/11 UTC+07**. Git nhận source và bản tóm tắt trong tài liệu/inventory; evidence raw, SSH key/cache đăng nhập và kubeconfig vẫn ở ngoài Git.

**Còn lại:** TV1/TV2 chạy lại độc lập NET01/OBS01/SEC01–04/SVC01–04 và OPS01; chụp Kiali UI; IAM01 bằng danh tính viewer riêng; PUB01 sau khi TV1 bàn giao LB/health/firewall. Kiali anonymous/admin.conf hiện tại không thay bằng chứng viewer. Slide tiếp tục bỏ qua theo yêu cầu.

**VM đã tắt:** API lúc **00:06:38 ngày 07/11 UTC+07** xác nhận `cp-01`, `wk-01`, `wk-02` đều **TERMINATED**; dữ liệu ở `.generated/tv3-cloud-setup-534ca265/vm-final-state.json`. Dừng hai worker thành công trước control plane. `verified-cloud-results.json` đối chiếu lại các kết quả theo từng lượt và trạng thái VM; `runtime-sources/SHA256.json` giữ hash đúng driver/helper của lượt policy và SVC04. Mọi công việc còn lại của phiên này làm trên laptop, không bật VM lại.

Gói source chốt trước khi nhận update TV2 ở `.generated/tv3-cloud-setup-534ca265/handover-package/`: overlay 62 file, manifest và checksum, đã verify tại thời điểm đóng gói. Gói này chưa có nhật ký mới `8260fc9`; dùng gói sau merge ở mục 9 hoặc lấy bản bàn giao Git ngày 07/11. Gói source không chứa config vận hành, credential hoặc evidence raw; hướng dẫn nhận gói tại [bàn giao](../tv3-handover.md).

## 9. Nhận cập nhật TV2 và kiểm tra tương thích · 07/11/2026

Đã fetch GitHub và merge fast-forward `2782c61 → 8260fc95574166d8edd9b7dbc3f555004032af38` vào **nhánh local `tv3/istio-network`**. Commit TV2 mới chỉ đổi README, inventory, TV2-status và thêm [nhật ký baseline TV2](TV2-baseline-20261106.md); không đổi script, manifest, image, port, selector, ServiceAccount hoặc config ứng dụng. Source của các lượt cloud mục 7–8 vẫn giữ đúng commit/hash lịch sử, không thay bằng HEAD sau merge.

Khi khôi phục phần TV3 chưa commit có **một xung đột nội dung ở inventory**: TV2 điền baseline trước mesh, TV3 điền sau injection/cuối phiên. Đã giữ nguyên toàn bộ số đo TV3, thêm lịch sử/nguồn TV2; bốn ClusterIP trùng khớp. Pod UID/IP được ghi riêng theo từng mốc. Đã hòa giải trạng thái cũ “chờ TV3 cài Istio” trong README/TV2-status, đánh dấu nhật ký baseline là lịch sử để tránh apply namespace injection disabled lên cụm hiện có. Nhật ký mới đã được thêm vào allowlist đóng gói; không tự ký nhận kiểm tra chéo cho thành viên khác.

Backup trước merge đủ **22 file local**, diff và manifest/checksum ở `.generated/tv3-tv2-merge-20261106T171443Z/working-tree-backup.zip`; còn stash riêng inventory `TV3 inventory before TV2 8260fc9 merge 20261107`. Sau merge đã kiểm tra lại **51/51 test** và toàn bộ checker offline đạt (source/hash Bookinfo, render, Bash/PowerShell, gcloud version); log ở thư mục `local-check/` cùng đợt backup. Các sửa đổi script/cấu hình TV3 được giữ nguyên; không còn file unmerged hoặc marker xung đột.

Gói source sau merge ở `.generated/tv3-tv2-merge-20261106T171443Z/handover-package/`, gồm cả nhật ký TV2 mới; manifest/checksum đã verify tại thời điểm đóng gói. Sau đó source cloud và phần hòa giải tài liệu được chốt trong bản commit bàn giao ngày 07/11 trên `tv3/istio-network`, kế thừa TV2 `8260fc9`. Thành viên nhận qua Git làm theo [hướng dẫn clone](../tv3-handover.md), ghi `git rev-parse HEAD` thực tế; không dùng commit bàn giao thay hash source đã chạy trên cloud. Đợt nhận source và phát hành này chỉ thao tác laptop: **không bật VM, không apply cloud**, trạng thái VM được xác nhận lần cuối ở mục 8.
