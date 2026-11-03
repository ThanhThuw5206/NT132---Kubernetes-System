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
| management/rancher/ | Helm values, ingress và cấu hình DNS công khai của lab. TV1. |
| observability/ | Prometheus, Kiali và hướng dẫn tạo traffic. TV3. |
| tests/service/ | Kiểm thử DNS, selector, EndpointSlice và NodePort. Cả nhóm. |
| tests/security/ | Các ca đối chứng, Istio và NetworkPolicy. Cả nhóm. |
| scripts/ | Script thao tác có phạm vi rõ ràng và hướng dẫn chạy. |
| docs/ | Kế hoạch, hướng dẫn, inventory và bằng chứng đã loại thông tin nhạy cảm. |

Đây là cấu trúc khởi tạo. Các thư mục cấu hình và source sẽ được điền bằng tài nguyên đã kiểm tra của nhóm. Hạ tầng hiện chưa được triển khai bởi repository này.

## Tài liệu bắt đầu

- [Kế hoạch tổng thể](docs/plan.md)
- [Hướng dẫn TV1](docs/tv1-setup.md)
- [Inventory mẫu](docs/inventory.example.md)

## Làm việc với Git

Branch khởi tạo là `tv1/project-setup`. Mỗi thành viên tạo branch riêng từ commit nhóm thống nhất, ví dụ `tv2/kubernetes-service` hoặc `tv3/istio-network`.

Trước khi commit, xem `git diff --cached` để kiểm tra đúng file. Giữ kubeconfig, token, private key và dữ liệu Secret ngoài Git. Chỉ đưa manifest mẫu có placeholder và chứng chỉ công khai đã kiểm tra vào repo.

Khi thêm ứng dụng do TV2 lựa chọn, ghi URL nguồn, release/tag hoặc commit và giấy phép. Dùng image có sẵn đã ghim version. Trọng tâm nghiệm thu là Kubernetes Service và các đường truy cập.
