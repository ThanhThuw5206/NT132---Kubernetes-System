# NT132 · Kubernetes System

**Thông số ứng dụng do TV2 quyết định — đã chốt ứng dụng Bookinfo.** Xem [apps/bookinfo](apps/bookinfo/README.md), [runbook TV2](docs/tv2-runbook.md) và [phiếu bàn giao](docs/application-handover.md). APP_NAMESPACE, ENTRY_SERVICE, CALLER_SERVICE, TARGET_SERVICE, SERVICE_PORT và các token viết hoa trong ví dụ cần thay bằng giá trị thực trước khi chạy; bản điền sẵn cho Bookinfo nằm tại `apps/bookinfo/application.bookinfo.json`. Với đường dẫn, /APP_PATH và /TEST_PATH là ký hiệu cả path, thay bằng đường dẫn thật có một dấu / đầu. Các dòng mô tả chức năng của ứng dụng là tiêu chí kiểm thử cần đối chiếu với lựa chọn của TV2.

Đồ án quản trị mạng với cụm Kubernetes tự dựng trên ba VM Compute Engine. Nhóm dùng ứng dụng do TV2 tự chọn — **Bookinfo từ release Istio đã ghim (1.30.7)** — để kiểm chứng Kubernetes Service, kết hợp Rancher, Istio và Calico.

## Cấu trúc thư mục

| Thư mục | Nội dung và người phụ trách |
|---|---|
| infra/gcp/ | VPC, VM, firewall, IP và cloud load balancer. TV1. |
| cluster/bootstrap/ | Cấu hình runtime, kubeadm và hướng dẫn join. TV1 cùng hai worker owner. |
| cluster/calico/ | CNI và cấu hình mạng Pod. TV3. |
| apps/ | Manifest và tài liệu ứng dụng mẫu theo release đã ghim; `apps/bookinfo/` là ứng dụng đã chốt. TV2. |
| src/ | Source mẫu được nhóm lựa chọn, kèm nguồn và giấy phép. TV2. |
| mesh/istio/ | Cài Istio, gateway, route, mTLS và phân quyền. TV2/TV3. |
| network/policies/ | Kubernetes NetworkPolicy và ma trận nguồn/đích. TV3. |
| management/rancher/ | Helm values, ingress riêng và DNS nội bộ của Rancher. TV1. |
| observability/ | Prometheus, Kiali và hướng dẫn tạo traffic. TV3. |
| tests/service/ | Kiểm thử DNS, selector, EndpointSlice và NodePort. Cả nhóm. |
| tests/security/ | Các ca đối chứng, Istio và NetworkPolicy. Cả nhóm. |
| scripts/ | Script thao tác có phạm vi rõ ràng và hướng dẫn chạy. |
| docs/ | Kế hoạch, hướng dẫn, inventory và bằng chứng đã loại thông tin nhạy cảm. |

Repository đã có Terraform tạo ba VM, script bootstrap kubeadm/Calico, Helm values cho Rancher/Istio và script dashboard. Theo cập nhật của TV1 ngày 05/11/2026, cụm ba node đã được kiểm chứng Ready, Kubernetes Service/DNS hoạt động và Rancher hiển thị đủ ba node Active. Xác nhận inventory hiện có với TV1 trước khi tạo tài nguyên. Ứng dụng do TV2 lựa chọn: **Bookinfo**, với manifest/config trong `apps/bookinfo/`, [inventory](apps/bookinfo/service-inventory.md) và [runbook TV2](docs/tv2-runbook.md).

**Tiến độ đối chiếu ngày 07/11/2026:** TV2 đã deploy baseline và ghi kết quả kỹ thuật APP01/SVC01–03 trong [nhật ký 06/11](docs/evidence/TV2-baseline-20261106.md), đưa lên GitHub tại `8260fc9`. Sau đó TV3 đã cài Istio/Prometheus/Kiali, bật injection/route, thử NodePort hai worker, policy và Service cùng các lượt phục hồi; xem [TV3-status](docs/evidence/TV3-status.md). Còn chờ kiểm tra chéo độc lập của các thành viên, viewer và frontend LB. Nhật ký baseline là lịch sử trước mesh; không apply lại namespace injection disabled hoặc dựng lại cụm đang có. Cả ba VM đã được xác nhận TERMINATED lúc 00:06:38 ngày 07/11 trong bằng chứng TV3.

**Phiên mesh TV2 10/11/2026:** trên cụm đã tích hợp, TV2 tự chạy APP01 qua gateway (HTTP 200, 9 sao) và luật phân quyền — SEC01 mTLS STRICT (hai nguồn 200) rồi SEC02 AuthorizationPolicy (reviews 200 / productpage 403, có log RBAC `rbac_access_denied`), sau đó gỡ luật phục hồi baseline và tắt VM. Nhật ký: [TV2-mesh-20261110](docs/evidence/TV2-mesh-20261110.md). Lượt mang tên TV2, vẫn chờ TV1/TV3 kiểm tra chéo. **TV2 đã bàn giao thông số NodePort 30080 cho TV1 làm cloud LB (PUB01)** tại [infra/public-access.md](infra/public-access.md) — gateway `istio-ingressgateway` NodePort 80→30080, hai worker wk-01/wk-02, health check TCP 30080; PUB01 chờ TV1 dựng LB và test từ ngoài VPC.

**Bắt đầu tại [hướng dẫn triển khai cloud](docs/deploy-cloud.md)**: có từng lệnh chạy tại Cloud Shell, VM và Windows, kiểm tra sau mỗi giai đoạn, lịch năm ngày và cách dọn tài nguyên. Đây là nguồn hướng dẫn thao tác cho bộ config hiện tại; không chạy xen kẽ lệnh tạo hạ tầng trong tài liệu cũ.

Phiên bản được ghim tại `config/versions.env`. Điền project trong `infra/gcp/terraform.tfvars` (không commit), dùng Terraform plan trước apply. Cấu hình mặc định là ba VM 2 vCPU/8 GiB, tổng boot disk 110 GB, truy cập dashboard qua IAP/SSH; public LB tùy chọn. Laptop không cần máy ảo.

Thông số ứng dụng nhập qua `config/application.json` theo file example. `scripts/render-application.py` kiểm tra thông số rồi tạo route và policy riêng cho lần chạy. Không apply cả thư mục kết quả; làm theo thứ tự trong hướng dẫn để kiểm chứng từng lớp.

Phần Bookinfo chuẩn bị trên laptop ngày 06/11 có source upstream kèm hash/giấy phép và `scripts/prepare-bookinfo.py` để sinh workload baseline không injection, probes/tài nguyên và reviews-v2. Quy trình dựng mới đi từ baseline được review tới Istio/injection/route rồi thử policy từng lớp. Xem [kết quả local/cloud và việc còn chờ](docs/evidence/TV3-status.md); kết quả offline được ghi riêng với các lượt cloud. Renderer hỗ trợ tùy chọn `public_http_matches` cho các path website cụ thể, giữ `public_path_prefix` cho config cũ.

## Tài liệu bắt đầu

- [Triển khai cloud từng bước](docs/deploy-cloud.md)
- [Runbook hằng ngày: IAM, bật/tắt VM, Rancher và làm tiếp](docs/bat-tat-lab.md)
- [Thêm TV2/TV3, phân quyền và bàn giao công việc](docs/them-thanh-vien.md)
- [Kế hoạch tổng thể](docs/plan.md)
- [TV2: runbook triển khai Kubernetes Service (Bookinfo)](docs/tv2-runbook.md)
- [TV2: ứng dụng Bookinfo — nguồn, giấy phép và bảng kê Service](apps/bookinfo/README.md)
- [TV2: trạng thái công việc và bằng chứng](docs/evidence/TV2-status.md)
- [TV2: nhật ký phiên deploy baseline 06/11](docs/evidence/TV2-baseline-20261106.md)
- [TV2: nhật ký phiên mesh APP01/SEC01/SEC02 10/11](docs/evidence/TV2-mesh-20261110.md)
- [TV2 → TV1: bàn giao NodePort → Cloud LB (PUB01)](infra/public-access.md)
- [TV2: giải thích công việc để ôn và bảo vệ](docs/tv2-giai-thich.md)
- [TV3: hướng dẫn laptop, công cụ và thực hiện trên cloud](docs/tv3-runbook.md)
- [TV3: quyền truy cập, đầu vào và bàn giao cho nhóm](docs/tv3-handover.md)
- [TV3: ma trận kiểm thử và bằng chứng](docs/tv3-test-matrix.md)
- [TV3: trạng thái, kết quả đã kiểm tra và việc còn chờ](docs/evidence/TV3-status.md)
- [Hướng dẫn TV1](docs/tv1-setup.md)
- [Inventory mẫu](docs/inventory.example.md)

## Làm việc với Git

Branch tích hợp và branch mặc định của nhóm là `main`. Mỗi thành viên cập nhật `main`, tạo branch riêng cho phần việc của mình, ví dụ `tv2/kubernetes-service` hoặc `tv3/istio-network`, rồi mở pull request về `main`. Không push trực tiếp lên `main`.

Phần mạng/quan sát/kiểm thử TV3 được bàn giao tại branch `tv3/istio-network`, phát triển từ `17aaed9`. Phần ứng dụng/Service TV2 phát triển tại branch `tv2/kubernetes-service`, tách từ `tv3/istio-network` nên đã gồm đủ hạ tầng TV1 và nền mesh/mạng TV3. Các thành viên lấy đúng branch và ghi `git rev-parse HEAD` vào inventory/evidence; xem phiếu bàn giao để nhận việc và chạy lại các kiểm tra.

Trước khi commit, xem `git diff --cached` để kiểm tra đúng file. Giữ kubeconfig, token, private key và dữ liệu Secret ngoài Git. Chỉ đưa manifest mẫu có placeholder và chứng chỉ công khai đã kiểm tra vào repo.

Khi thêm ứng dụng do TV2 lựa chọn, ghi URL nguồn, release/tag hoặc commit và giấy phép. Dùng image có sẵn đã ghim version. Trọng tâm nghiệm thu là Kubernetes Service và các đường truy cập.
