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

Repository đã có Terraform tạo ba VM, script bootstrap kubeadm/Calico, Helm values cho Rancher/Istio và script dashboard. Theo cập nhật của TV1 ngày 05/11/2026, cụm ba node đã được kiểm chứng Ready, Kubernetes Service/DNS hoạt động và Rancher hiển thị đủ ba node Active. Xác nhận inventory hiện có với TV1 trước khi tạo tài nguyên. Ứng dụng do TV2 lựa chọn: **đã chốt Bookinfo**, bổ sung manifest/config tham chiếu trong `apps/bookinfo/`, bảng kê Service `apps/bookinfo/service-inventory.md` và runbook thao tác `docs/tv2-runbook.md`; triển khai lên cụm (deploy, SVC/SEC) là bước kế tiếp.

**Bắt đầu tại [hướng dẫn triển khai cloud](docs/deploy-cloud.md)**: có từng lệnh chạy tại Cloud Shell, VM và Windows, kiểm tra sau mỗi giai đoạn, lịch năm ngày và cách dọn tài nguyên. Đây là nguồn hướng dẫn thao tác cho bộ config hiện tại; không chạy xen kẽ lệnh tạo hạ tầng trong tài liệu cũ.

Phiên bản được ghim tại `config/versions.env`. Điền project trong `infra/gcp/terraform.tfvars` (không commit), dùng Terraform plan trước apply. Cấu hình mặc định là ba VM 2 vCPU/8 GiB, tổng boot disk 110 GB, truy cập dashboard qua IAP/SSH; public LB tùy chọn. Laptop không cần máy ảo.

Thông số ứng dụng nhập qua `config/application.json` theo file example. `scripts/render-application.py` kiểm tra thông số rồi tạo route và policy riêng cho lần chạy. Không apply cả thư mục kết quả; làm theo thứ tự trong hướng dẫn để kiểm chứng từng lớp.

Phần Bookinfo chuẩn bị trên laptop ngày 06/11 có source upstream kèm hash/giấy phép và `scripts/prepare-bookinfo.py` để sinh workload baseline không injection, probes/tài nguyên và reviews-v2. Sau baseline được review mới tích hợp Istio/injection/route rồi thử policy từng lớp. Xem [kết quả local và việc còn chờ](docs/evidence/TV3-status.md); chưa dùng những kết quả offline này để nghiệm thu cloud. Renderer hỗ trợ tùy chọn `public_http_matches` cho các path website cụ thể, giữ `public_path_prefix` cho config cũ.

## Tài liệu bắt đầu

- [Triển khai cloud từng bước](docs/deploy-cloud.md)
- [Runbook hằng ngày: IAM, bật/tắt VM, Rancher và làm tiếp](docs/bat-tat-lab.md)
- [Thêm TV2/TV3, phân quyền và bàn giao công việc](docs/them-thanh-vien.md)
- [Kế hoạch tổng thể](docs/plan.md)
- [TV2: runbook triển khai Kubernetes Service (Bookinfo)](docs/tv2-runbook.md)
- [TV2: ứng dụng Bookinfo — nguồn, giấy phép và bảng kê Service](apps/bookinfo/README.md)
- [TV2: trạng thái công việc và bằng chứng](docs/evidence/TV2-status.md)
- [TV3: hướng dẫn laptop, công cụ và thực hiện trên cloud](docs/tv3-runbook.md)
- [TV3: quyền truy cập, đầu vào và bàn giao cho nhóm](docs/tv3-handover.md)
- [TV3: ma trận kiểm thử và bằng chứng](docs/tv3-test-matrix.md)
- [TV3: trạng thái, kết quả đã kiểm tra và việc còn chờ](docs/evidence/TV3-status.md)
- [Hướng dẫn TV1](docs/tv1-setup.md)
- [Inventory mẫu](docs/inventory.example.md)

## Làm việc với Git

Branch khởi tạo là `tv1/project-setup`. Mỗi thành viên tạo branch riêng từ commit nhóm thống nhất, ví dụ `tv2/kubernetes-service` hoặc `tv3/istio-network`.

Phần mạng/quan sát/kiểm thử TV3 được bàn giao tại branch `tv3/istio-network`, phát triển từ `17aaed9`. Phần ứng dụng/Service TV2 phát triển tại branch `tv2/kubernetes-service`, tách từ `tv3/istio-network` nên đã gồm đủ hạ tầng TV1 và nền mesh/mạng TV3. Các thành viên lấy đúng branch và ghi `git rev-parse HEAD` vào inventory/evidence; xem phiếu bàn giao để nhận việc và chạy lại các kiểm tra.

Trước khi commit, xem `git diff --cached` để kiểm tra đúng file. Giữ kubeconfig, token, private key và dữ liệu Secret ngoài Git. Chỉ đưa manifest mẫu có placeholder và chứng chỉ công khai đã kiểm tra vào repo.

Khi thêm ứng dụng do TV2 lựa chọn, ghi URL nguồn, release/tag hoặc commit và giấy phép. Dùng image có sẵn đã ghim version. Trọng tâm nghiệm thu là Kubernetes Service và các đường truy cập.
