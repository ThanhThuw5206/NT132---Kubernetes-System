# NT132 · Kubernetes System

**Thông số ứng dụng do TV2 quyết định.** Xem [phiếu bàn giao](docs/application-handover.md). APP_NAMESPACE, ENTRY_SERVICE, CALLER_SERVICE, TARGET_SERVICE, SERVICE_PORT và các token viết hoa trong ví dụ cần thay bằng giá trị thực trước khi chạy. Với đường dẫn, /APP_PATH và /TEST_PATH là ký hiệu cả path, thay bằng đường dẫn thật có một dấu / đầu. Các dòng mô tả chức năng của ứng dụng là tiêu chí kiểm thử cần đối chiếu với lựa chọn của TV2.

Đồ án quản trị mạng với cụm Kubernetes tự dựng trên ba VM Compute Engine. Nhóm dùng ứng dụng do TV2 tự chọn để kiểm chứng Kubernetes Service, kết hợp Rancher, Istio và Calico.

## Cấu trúc thư mục

| Thư mục | Nội dung và người phụ trách |
|---|---|
| infra/gcp/ | VPC, VM, firewall, IP và cloud load balancer. TV1. |
| cluster/bootstrap/ | Cấu hình runtime, kubeadm và hướng dẫn join. TV1 cùng hai worker owner. |
| cluster/calico/ | CNI và cấu hình mạng Pod. TV3. |
| apps/ | Manifest của ứng dụng mẫu theo release đã ghim. TV2. |
| src/ | Source mẫu được nhóm lựa chọn, kèm nguồn và giấy phép. TV2. |
| mesh/istio/ | Cài Istio, gateway, route, mTLS và phân quyền. TV2/TV3. |
| network/policies/ | Kubernetes NetworkPolicy và ma trận nguồn/đích. TV3. |
| management/rancher/ | Helm values, ingress riêng và DNS nội bộ của Rancher. TV1. |
| observability/ | Prometheus, Kiali và hướng dẫn tạo traffic. TV3. |
| tests/service/ | Kiểm thử DNS, selector, EndpointSlice và NodePort. Cả nhóm. |
| tests/security/ | Các ca đối chứng, Istio và NetworkPolicy. Cả nhóm. |
| scripts/ | Script thao tác có phạm vi rõ ràng và hướng dẫn chạy. |
| docs/ | Kế hoạch, hướng dẫn, inventory và bằng chứng đã loại thông tin nhạy cảm. |

Repository đã có Terraform tạo ba VM, script bootstrap kubeadm/Calico, Helm values cho Rancher/Istio và script dashboard. Repo chưa lưu bằng chứng apply/nghiệm thu trên project thật; xác nhận inventory hiện có với TV1 trước khi tạo tài nguyên. Ứng dụng do TV2 lựa chọn và bổ sung.

**Bắt đầu tại [hướng dẫn triển khai cloud](docs/deploy-cloud.md)**: có từng lệnh chạy tại Cloud Shell, VM và Windows, kiểm tra sau mỗi giai đoạn, lịch năm ngày và cách dọn tài nguyên. Đây là nguồn hướng dẫn thao tác cho bộ config hiện tại; không chạy xen kẽ lệnh tạo hạ tầng trong tài liệu cũ.

Phiên bản được ghim tại `config/versions.env`. Điền project trong `infra/gcp/terraform.tfvars` (không commit), dùng Terraform plan trước apply. Cấu hình mặc định là ba VM 2 vCPU/8 GiB, tổng boot disk 110 GB, truy cập dashboard qua IAP/SSH; public LB tùy chọn. Laptop không cần máy ảo.

Thông số ứng dụng nhập qua `config/application.json` theo file example. `scripts/render-application.py` kiểm tra thông số rồi tạo route và policy riêng cho lần chạy. Không apply cả thư mục kết quả; làm theo thứ tự trong hướng dẫn để kiểm chứng từng lớp.

## Tài liệu bắt đầu

- [Triển khai cloud từng bước](docs/deploy-cloud.md)
- [Kế hoạch tổng thể](docs/plan.md)
- [TV3: việc có thể làm và điều kiện bàn giao hiện tại](docs/tv3-current-work.md)
- [TV3: bộ công cụ, kiểm thử và hướng dẫn thực hiện](docs/tv3-runbook.md)
- [Bàn giao TV3 cho TV1/TV2 qua branch hoặc gói source local](docs/tv3-handover.md)
- [Hướng dẫn TV1](docs/tv1-setup.md)
- [Inventory mẫu](docs/inventory.example.md)

## Làm việc với Git

Branch khởi tạo là `tv1/project-setup`. Mỗi thành viên tạo branch riêng từ commit nhóm thống nhất, ví dụ `tv2/kubernetes-service` hoặc `tv3/istio-network`.

Phần mạng/quan sát/kiểm thử TV3 được bàn giao tại branch `tv3/istio-network`, phát triển từ `17aaed9`. Các thành viên lấy đúng branch và ghi `git rev-parse HEAD` vào inventory/evidence; xem phiếu bàn giao để nhận việc và chạy lại các kiểm tra.

Trước khi commit, xem `git diff --cached` để kiểm tra đúng file. Giữ kubeconfig, token, private key và dữ liệu Secret ngoài Git. Chỉ đưa manifest mẫu có placeholder và chứng chỉ công khai đã kiểm tra vào repo.

Khi thêm ứng dụng do TV2 lựa chọn, ghi URL nguồn, release/tag hoặc commit và giấy phép. Dùng image có sẵn đã ghim version. Trọng tâm nghiệm thu là Kubernetes Service và các đường truy cập.
