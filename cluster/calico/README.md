# Calico · Bảng thiết kế và phiên bản của TV3

Ngày đối chiếu tài liệu chính thức: **05/11/2026**. Giữ nguyên pins của repo, chưa nâng cấp thành phần.

| Thành phần | Source hiện tại | Đối chiếu / việc còn phải đo |
|---|---|---|
| OS | Ubuntu 24.04 amd64 | Script chuẩn bị node kiểm tra OS/kiến trúc. Ghi image ID và kernel thật sau khi có VM. |
| Kubernetes | kubeadm/kubelet/kubectl `v1.35.10` | Cùng pin tại `config/versions.env` và cấu hình kubeadm. Chưa thử tải package trên cloud. |
| Calico | `v3.33.0`, operator | Tài liệu Calico 3.33 liệt kê Kubernetes 1.35 trong các bản được kiểm thử; yêu cầu kernel Linux >=5.10. [Nguồn Tigera](https://docs.tigera.io/calico/latest/getting-started/kubernetes/requirements). |
| Istio | `1.30.7`, sidecar mode | Nhánh Istio 1.30 hỗ trợ Kubernetes 1.32–1.36 tại thời điểm đối chiếu. Kubernetes 1.35 nằm trong dải này. [Nguồn Istio](https://istio.io/latest/docs/releases/supported-releases/). |
| containerd | Package Ubuntu, chưa ghim version | Ghi `containerd --version`, CRI và cgroup thực trên cả ba node; chưa kết luận tương thích runtime chỉ từ source. |
| Helm | `v3.19.0` | Script tải archive/checksum đúng pin. Chưa chạy cài Helm trên VM trong lần này. |
| Prometheus/Kiali | Addon tại tag Istio `1.30.7` | Giữ cùng bộ addon; ghi image/digest thực sau deploy. Không giả định có lưu trữ metric lâu dài. |

Đây là kiểm tra dải phiên bản được công bố, chưa chứng minh cài đặt end-to-end. Rancher do TV1 kiểm tra riêng. Calico operator/CRD và các yêu cầu API phải được kiểm tra trên Kubernetes thực trước nghiệm thu.

| Mạng | Giá trị source | Chỗ đối chiếu |
|---|---|---|
| Node subnet | `10.20.0.0/24` | `infra/gcp/main.tf` |
| cp-01 / wk-01 / wk-02 | `10.20.0.10 / .11 / .12` | Terraform output, `kubectl get nodes -o wide` |
| Pod CIDR | `10.244.0.0/16` | `cluster/bootstrap/kubeadm.yaml`, `installation.yaml` |
| Service CIDR | `10.96.0.0/12` | kubeadm config |
| Encapsulation | VXLAN, BGP Disabled | `installation.yaml`, UDP 4789 hai chiều giữa node |
| Node autodetection | CIDR `10.20.0.0/24` | InternalIP thật phải thuộc subnet này |
| IP forwarding | GCE `can_ip_forward=true`, Linux forwarding=1 | Terraform và script chuẩn bị node |

Các dải phải không chồng lấn VPC/VPN thực của nhóm. Cấu hình hiện có hạ tầng và script gắn với các IP trên; không chỉ đổi một CIDR trong Calico rồi chạy tiếp.

Kiểm tra trên từng node, ghi kết quả vào inventory, không chạy lại bootstrap trên máy đã join để chữa lỗi:

```bash
hostname
cat /etc/os-release
uname -r
containerd --version
kubelet --version
sysctl net.ipv4.ip_forward net.bridge.bridge-nf-call-iptables
sudo systemctl is-active containerd kubelet
```

Kiểm tra trên cp-01:

Script `03-install-calico.sh` hiện chờ `tigerastatus/calico` có `Available=True`, `Progressing=False`, `Degraded=False`, với timeout cho từng điều kiện; không chỉ in trạng thái rồi báo thành công. Các component khác trong `tigerastatus` vẫn phải được đối chiếu trước bàn giao và trong snapshot TV3.

```bash
kubectl get nodes -o wide
kubectl get installation default -o yaml
kubectl get tigerastatus
kubectl -n calico-system get pods -o wide
kubectl -n kube-system get pods -l k8s-app=kube-dns -o wide
```

Nếu mạng Pod thất bại: kiểm tra node Ready, Calico/route/MTU và UDP 4789 giữa node cùng TV1. Nếu Pod IP đạt nhưng DNS lỗi: kiểm tra CoreDNS/Service/EndpointSlice. Không đổi sang CNI khác hoặc gỡ taint control plane để che lỗi mạng.
