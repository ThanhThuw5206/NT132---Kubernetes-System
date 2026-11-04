# TV3 · Hướng dẫn thực hiện và bàn giao

Source nền `17aaed9`; cập nhật **05/11/2026**. Mục tiêu là kiểm chứng đường **DNS Service → selector → EndpointSlice → Pod** và phân biệt không có backend với lỗi quyền truy cập. Calico/Istio/Kiali phục vụ mục tiêu này. Source chuẩn bị, kiểm tra offline và nghiệm thu cloud là ba trạng thái khác nhau.

## 1. Chạy được trên laptop Windows hiện tại

Máy hiện tại đã có Python qua **uv**; lệnh `python` đang có thể trỏ tới shortcut Microsoft Store. Tại thư mục repo, dùng:

```powershell
uv run --offline --no-project python -m unittest discover -s tests -v
uv run --offline --no-project python scripts/tv3.py --help
```

Không chạy script cài node Linux từ PowerShell. Trên máy khác, `--offline` chỉ dùng khi runtime uv đã được cache; nếu đã có Python >=3.10, có thể chạy `python -m unittest discover -s tests -v`. Trên VM Ubuntu dùng `python3`. Các công cụ TV3 chỉ dùng thư viện chuẩn Python.

Test HTTP local mở server loopback; test NET01 offline dùng kubectl giả trong thư mục tạm. Chúng không gọi cloud. Kiểm tra cú pháp Bash trong Git Bash: `for file in scripts/*.sh; do bash -n "$file" || exit; done`.

Để nhận code đã commit, lấy branch `tv3/istio-network` theo [phiếu bàn giao](tv3-handover.md) và ghi commit đang dùng. Gói overlay local là phương án bổ sung khi có sửa đổi mới chưa commit; riêng `git archive HEAD` không chứa các sửa đổi đó.

## 2. Phân công, đầu vào và mốc nghiệm thu

| Mốc | TV3 chủ trì | TV3 kiểm tra chéo / phối hợp | Người nhận và bằng chứng |
|---|---|---|---|
| M1 · 06/11 | `wk-02`, Calico, NET01; Istio nền; Prometheus/Kiali và OBS01 | TV1 giao VM/join/API; TV2 giao app/route/request. TV3 chạy lại IAM01, SVC02 và hỗ trợ Service/EndpointSlice | TV2 nhận mạng/mesh Ready trước deploy; TV1 tự mở graph và tạo request mới; log/ảnh/metric đúng thời điểm |
| M2 · 13/11 | Kiểm tra độc lập URL frontend từ ngoài VPC, đối chiếu Kiali; hỗ trợ chẩn đoán Pod → Service → NodePort → LB | TV2 sở hữu NodePort/route; TV1 sở hữu LB/Rancher. TV3 là người kiểm tra PUB01 | TV1 nhận URL/status/nội dung trang/graph; TV2 đối chiếu Service; không dùng port-forward làm bằng chứng public |
| M3 · 20/11 | SEC03: NetworkPolicy riêng, DNS/endpoint, nguồn đúng/sai và phục hồi | TV2 chủ trì SEC01/SEC02; TV3 kiểm tra mTLS và thử lại; TV1 chủ trì tích hợp SEC04 | TV1 chạy lại SEC03; ghi rõ policy đang bật mỗi lượt C1–C4 |
| M4 · 27/11 | SVC04 và hồ sơ chẩn đoán; chạy lại suite/đóng gói evidence | TV2 chủ trì thay Pod/scale SVC02/SVC03; TV3 theo dõi EndpointSlice/UID và gọi cùng DNS. Cả nhóm OPS01 | TV1 sửa selector; TV2 gọi lại thành công; người khác chạy lại từ hướng dẫn và ghi sai khác |

TV1 vẫn sở hữu cloud/Rancher/LB; TV2 sở hữu ứng dụng/Service/route và xác nhận luật Istio. TV3 không cần chờ ứng dụng hoàn chỉnh để chuẩn bị mạng/mesh/hồ sơ, nhưng graph/policy nghiệm thu phải dùng luồng thật do TV2 bàn giao. Lịch là kế hoạch, không tự chứng minh mốc đã đạt.

## 3. Chuẩn bị `wk-02`, mạng nền và mesh

Nhận project/zone, quyền IAM/IAP, VM và join command riêng từ TV1; dùng cùng phiên bản source. Đọc [bảng Calico/CIDR](../cluster/calico/README.md) và [deploy-cloud.md](deploy-cloud.md), phần 4–6. Không tạo thêm `wk-02` nếu Terraform đã tạo. Trên **wk-02**, tại thư mục source:

```bash
hostname  # phải là wk-02
sudo bash scripts/01-prepare-node.sh
sudo systemctl is-active containerd
kubelet --version
# Chạy sudo kubeadm join với token/hash thật do TV1 cấp qua kênh riêng.
```

Sau khi cả hai worker đã join, TV1/TV3 thống nhất một người chạy Calico trên **cp-01**:

```bash
kubectl config current-context
kubectl get nodes -o wide
bash scripts/03-install-calico.sh
bash scripts/test-cross-node.sh
```

NET01 đặt client/server ở hai hướng `wk-02 → wk-01` và ngược lại, thử Pod IP/ClusterIP/DNS: tổng cộng sáu HTTP 200. Script lưu log/exit code trong `.generated/net01-*`; kiểm tra label sở hữu `nt132-net01` trước apply và không tự dọn. Nếu fixture cũ/trùng tên chưa có label đúng, xem lại trước khi chạy bản mới. Không lấy việc có Pod Running làm thay HTTP thực.

Lưu bằng chứng, để TV2 chạy lại; trước khi dọn, kiểm tra namespace thử không có tài nguyên ngoài bài:

```bash
kubectl -n network-check get all
kubectl delete -f tests/service/network-check.yaml
```

File gồm namespace `network-check`; không xóa nếu còn tài nguyên khác cần giữ trong đó. Client ngủ một giờ; nếu chạy lại sau khi Pod Completed, dọn đúng fixture rồi tạo lại. Giữ taint control plane.

Khi mạng nền đạt và đã có Helm, tiếp tục trên **cp-01**:

```bash
helm version
bash scripts/05-install-istio.sh
kubectl -n istio-system get deployments,svc,pods -o wide
bash scripts/07-install-observability.sh
```

Nếu chưa có Helm, phối hợp TV1 chạy `bash scripts/04-install-helm.sh`. Giao TV2 ngay namespace `istio-system`, tên Service gateway, port/targetPort/NodePort thật và trạng thái Istiod/gateway Ready. TV2 triển khai workload/route sau khi bật injection; không chờ hoàn tất mọi dashboard mới bàn giao. Thống nhất trước khi hai người sửa cùng gateway Service.

## 4. Snapshot và nhận ứng dụng

Trên máy quản trị có Python/kubectl, đọc context rồi truyền tên lab đã xác nhận:

```bash
kubectl config get-contexts
python3 scripts/tv3.py snapshot --context TEN_CONTEXT_LAB
```

Snapshot đọc trạng thái/phiên bản mạng/mesh và node; không phụ thuộc Rancher, không thay NET01/OBS01. Context và IP kiểm tra chống nhầm thao tác thông thường, không định danh duy nhất một cụm. Xem kết quả kiểm tra, không chỉ exit code.

Để hỗ trợ TV2 ở SVC02/SVC03, dùng `python3 scripts/tv3.py service-snapshot config/application.json --context TEN_CONTEXT_LAB` trước/sau TV2 thay Pod hoặc scale. Công cụ ghi UID/ClusterIP/selector/ports, Pod Ready và targetRef từng endpoint, không tự sửa workload. Xem [hướng dẫn Service](../tests/service/README.md) để chụp đủ lượt phục hồi và gọi lại cùng DNS.

TV2 điền [phiếu app](application-handover.md), chuẩn bị `config/application.json` từ example bằng giá trị thật. Config vận hành nằm trong `.gitignore`; chia sẻ qua kênh nhóm đã thống nhất và không kèm credential. Trên máy quản trị:

```bash
python3 scripts/tv3.py render config/application.json
```

Lệnh chỉ sinh file và in thư mục mới `.generated/tv3-*`; chưa apply. Dùng đúng thư mục vừa in. Không apply cả thư mục vì có `inputs.json` và hai trạng thái khác nhau của cùng Service thử. TV2 apply namespace injection, workload và route theo runbook cloud. Không mặc định Bookinfo trừ khi TV2 chọn ứng dụng đó.

TV3 tiếp tục theo [OBS01](../observability/README.md), [ma trận NetworkPolicy](../network/policies/README.md), [C1–C4/SEC03](../tests/security/README.md) và [SVC04](../tests/service/README.md). Khi so sánh lỗi, giữ nguyên nguồn/đích/path và ghi lớp duy nhất vừa thay đổi, baseline trước/sau và thao tác phục hồi.

## 5. Việc kiểm tra chéo phải để lại kết quả

| ID | TV3 thực hiện với người chủ trì | Cần ghi |
|---|---|---|
| IAM01 | Dùng đúng tài khoản viewer do TV1 cấp, mở dashboard/read workload; kiểm tra quyền sửa bằng `kubectl auth can-i`, không sửa workload thật | Đọc được dữ liệu demo; quyền patch Deployment là `no`; danh tính/namespace/quyền được cấp |
| SVC02 | TV2 thực hiện thay Pod; TV3 gọi trước/sau từ cùng nguồn và theo dõi EndpointSlice | DNS/ClusterIP giữ nguyên, UID/targetRef trước-sau, thời gian gián đoạn nếu có, Ready và HTTP sau phục hồi |
| SEC01 | TV2 bật STRICT theo phạm vi đã thống nhất; TV3 thử hai nguồn trong mesh | Hai HTTP 200 và bằng chứng request dùng mTLS từ metric/proxy đúng cặp nguồn-đích |
| SVC03 | TV2 lưu replica gốc, scale và rollback; TV3 quan sát endpoint, gọi cùng DNS | Ba trạng thái trước/sau scale/sau phục hồi; endpoint Ready ↔ Pod UID; không dùng response giống nhau để kết luận chia tải đều |
| PUB01 | Từ laptop ngoài VPC, gọi frontend IP/cổng/path do TV1 giao | HTTP status/nội dung đúng, timestamp, IP frontend, graph cùng khung giờ; TV1 đối chiếu backend healthy |
| OPS01 | Thành viên khác dùng gói source/hướng dẫn để chạy lại dashboard và demo | Phiên bản source/checksum, bước đã lặp, lỗi/sai khác, người kiểm tra; cả nhóm ký nhận kết quả |

Các bài này chưa được coi đã chạy chỉ vì có hướng dẫn. TV3 hỗ trợ SEC02/SEC04 nhưng không đổi người chủ trì hoặc gộp policy đến mức mất đối chứng từng lớp.

## 6. Evidence, demo và bàn giao

Đầu ra mặc định ở `.generated/`, được Git bỏ qua; `--output` chọn thư mục mới và không ghi đè. Sau khi đọc/kiểm tra dữ liệu, chuyển bằng chứng cần chia sẻ vào `docs/evidence/M1`, `M2`, `M3` hoặc `M4`; điền [mẫu kết quả](evidence/templates/test-result.md). Mỗi lượt cần source/commit hoặc hash gói local, thời gian/múi giờ, nguồn/đích/namespace, lệnh, kết quả mong đợi/thực tế, policy và hoàn tác, người chạy lại.

Phần TV3 trình bày M1 khoảng 2 phút: mở request thật → chọn namespace/cửa sổ vừa chạy trên Kiali → chỉ cạnh caller → target và metric → đối chiếu Service/endpoint thật với phần TV2. Phần bảo vệ sau đó dùng cặp bằng chứng **DNS có tên nhưng endpoint trống** và **endpoint còn Ready nhưng nguồn bị chặn** để giải thích lỗi theo lớp. Nếu dùng ảnh/video dự phòng, ghi rõ thời điểm và tách khỏi demo trực tiếp.

[Phiếu bàn giao TV3](tv3-handover.md) ghi thứ tự TV1/TV2 nhận việc, cách lấy branch hoặc chuyển sửa đổi local và các mục cần ký nhận. [Trạng thái hiện tại](evidence/TV3-status.md) ghi kết quả đã chạy; chưa có cloud/app không phải test đạt.
