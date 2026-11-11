# Triển khai NT132 trên ba VM Google Cloud

Đây là hướng dẫn chạy bộ config trong repository. Dùng tài liệu này khi thực hành; `tv1-setup.md` và `plan.md` cung cấp phần giải thích và kế hoạch. Không chạy xen kẽ các lệnh tạo hạ tầng thủ công trong tài liệu cũ với Terraform dưới đây.

## 1. Kết quả và phạm vi

Bạn tự cài containerd, kubeadm, kubelet, Kubernetes và các thành phần mạng trên Compute Engine. Không sử dụng GKE. Terraform chỉ tạo hạ tầng Google Cloud, không thay bạn cài Kubernetes.

| Thành phần | Cấu hình và chức năng |
|---|---|
| cp-01 | 10.20.0.10, e2-standard-2, 2 vCPU/8 GiB RAM, boot disk 30 GB. API server, scheduler, controller manager, etcd. |
| wk-01 | 10.20.0.11, e2-standard-2, 2 vCPU/8 GiB RAM, boot disk 40 GB. Chạy workload. |
| wk-02 | 10.20.0.12, cùng cấu hình wk-01. Chạy workload và kiểm chứng giao tiếp khác node. |
| VPC/subnet | nt132-vpc, subnet 10.20.0.0/24. Pod CIDR 10.244.0.0/16; Service CIDR 10.96.0.0/12. |
| Calico | VXLAN giữa node, cấp mạng Pod và thực thi NetworkPolicy. Không bật BGP. |
| Kubernetes Service | ClusterIP/DNS/EndpointSlice, NodePort 30080 tại gateway; Service ứng dụng do TV2 bổ sung. |
| Rancher | Một replica, quản lý cluster qua giao diện; Traefik riêng có Service ClusterIP, HTTPS với CA của lab. |
| Istio | Istiod, gateway, sidecar cho namespace ứng dụng, routing/mTLS/AuthorizationPolicy. |
| Dashboard | Rancher xem tài nguyên; Kiali xem mesh; Prometheus lấy metrics. |
| Cloud LB | Tùy chọn, mặc định tắt; external passthrough TCP port 30080 đến hai worker. |

Tổng boot disk là **110 GB trên cloud**. Laptop chỉ cần Git, Google Cloud CLI, trình duyệt và bản source; không cần VM local. Đây là cụm lab một control plane, không HA. Rancher đặt cùng cụm kubeadm là lựa chọn thực nghiệm, không tuyên bố đây là cấu hình hosting được SUSE chứng nhận. Prometheus/Kiali lấy từ addon lab của Istio; chưa có lưu metrics lâu dài, backup tự động hoặc StorageClass cho dữ liệu ứng dụng.

VM có external IP phục vụ tải package/image, nhưng không có luật mở SSH trực tiếp từ Internet. SSH dùng IAP. Firewall giới hạn API server và kubelet trong cụm. Không mở Rancher/Kiali công khai. Cấu hình mặc định dùng 8 GiB mỗi VM để có dư địa cho dashboard và mesh; theo dõi RAM sau khi TV2 đưa ứng dụng vào. Google Cloud tính phí VM, disk, external IP, traffic và LB nếu bật. Tạo budget alert trong Billing trước khi triển khai; alert không tự dừng chi phí.

## 2. Chuẩn bị tài khoản và môi trường

Các khối `bash` ở phần tạo cloud chạy tại **Google Cloud Shell**. Các khối cài cluster chạy trong **SSH vào đúng VM**, thư mục `~/NT132---Kubernetes-System`. Các khối `powershell` chạy trên **laptop Windows**. Không chạy script Linux trong PowerShell.

Tạo/chọn project, liên kết Billing, mở Cloud Shell. Tài khoản triển khai cần quyền tạo Compute/VPC/firewall/LB, bật API (Service Usage Admin). Tài khoản SSH cần `roles/compute.viewer`, `roles/compute.osAdminLogin`, `roles/iap.tunnelResourceAccessor`. Nhờ người quản trị cấp các quyền này nếu bạn không quản lý IAM. Nếu điền `ssh_members` để Terraform tự cấp quyền, tài khoản chạy Terraform còn cần quyền sửa IAM project. Tổ chức có policy chặn external IP hoặc OS Login cần quản trị viên xử lý phù hợp trước.

```bash
export PROJECT_ID='THAY_PROJECT_ID_THAT'
export ZONE='asia-southeast1-a'
gcloud config set project "$PROJECT_ID"
gcloud auth list
gcloud projects describe "$PROJECT_ID" --format='value(projectId)'
terraform version
git clone --branch main https://github.com/ThanhThuw5206/NT132---Kubernetes-System.git
cd NT132---Kubernetes-System
git rev-parse HEAD
```

Terraform cần >=1.9 và <2. Nếu Cloud Shell chưa có phiên bản phù hợp, cài từ hướng dẫn HashiCorp chính thức trước khi tiếp tục. Nếu repository private, đăng nhập GitHub bằng `gh auth login` và `gh auth setup-git`; không chèn token vào URL clone hoặc file config. Ghi commit đang triển khai vào inventory để ba thành viên cùng dùng một phiên bản.

## 3. Tạo ba VM bằng Terraform — TV1

```bash
cd infra/gcp
cp terraform.tfvars.example terraform.tfvars
nano terraform.tfvars
```

Thay `project_id` bằng ID thật. Giữ region/zone mặc định nếu không có lý do thay đổi; zone phải thuộc region. Giữ `enable_public_lb = false` trong giai đoạn đầu. `ssh_members = []` nghĩa là IAM do bạn/quản trị viên cấp ngoài Terraform. Có thể điền `["user:email-cua-ban@example.com"]` khi bạn có quyền sửa IAM. File `.tfvars` được Git bỏ qua.

```bash
terraform init
terraform fmt -check
terraform validate
terraform test
terraform plan -out=nt132.tfplan
terraform show nt132.tfplan
terraform apply nt132.tfplan
terraform output
```

Đọc plan trước apply: phải có đúng cp-01/wk-01/wk-02, subnet mới, không xóa tài nguyên có sẵn. `terraform test` dùng mock provider, không tạo VM. `terraform apply` mới tạo tài nguyên tính phí. Nếu credential lỗi, thực hiện `gcloud auth application-default login` theo luồng của Cloud Shell rồi chạy lại plan.

State hiện lưu local trong `infra/gcp/terraform.tfstate`; giữ nguyên thư mục Cloud Shell này để quản lý vòng đời. Sao lưu state ở nơi riêng có kiểm soát truy cập, không commit Git. Chỉ TV1 apply và không chạy đồng thời từ máy khác. Không xóa state để chữa lỗi; nếu resource trùng tên, xác định nguồn sở hữu trước khi import hoặc đổi cấu hình. Chưa cài remote backend/locking cho nhóm.

```bash
gcloud compute instances list --filter='name=(cp-01 wk-01 wk-02)'
gcloud compute ssh cp-01 --zone="$ZONE" --tunnel-through-iap
```

Nếu IAP báo 403, kiểm tra ba IAM role và API IAP. Nếu timeout, kiểm tra VM đã chạy và firewall TCP22 từ 35.235.240.0/20. Không mở port22 cho 0.0.0.0/0 để xử lý lỗi này.

## 4. Chuyển source và chuẩn bị từng node

Để tránh đăng nhập GitHub trên cả ba VM, tại Cloud Shell, từ thư mục gốc repository, đóng gói **commit đã lưu** và gửi qua IAP:

```bash
cd ~/NT132---Kubernetes-System
git archive --format=tar.gz --output=/tmp/nt132-source.tar.gz HEAD
for node in cp-01 wk-01 wk-02; do
  gcloud compute scp /tmp/nt132-source.tar.gz "$node:~/nt132-source.tar.gz" \
    --zone="$ZONE" --tunnel-through-iap
  gcloud compute ssh "$node" --zone="$ZONE" --tunnel-through-iap \
    --command='mkdir -p ~/NT132---Kubernetes-System && tar -xzf ~/nt132-source.tar.gz -C ~/NT132---Kubernetes-System'
done
```

Archive không có `.git`, không chứa file chưa commit. Mỗi lần cập nhật phải tạo archive từ commit mới và chuyển lại; không ghi đè các file vận hành riêng mà không kiểm tra. Các bí mật nằm ngoài thư mục source.

**Khi nhận phần TV3:** lấy branch `tv3/istio-network` theo [hướng dẫn bàn giao](tv3-handover.md) trước khi tạo archive, ghi lại `git rev-parse HEAD`. Archive của commit TV3 chứa các file đã commit; archive từ branch TV1 hoặc commit nền `17aaed9` chưa chứa phần bổ sung TV3. Nếu có sửa đổi local mới chưa commit, chuyển thêm overlay theo hướng dẫn và kiểm tra manifest/checksum; `git archive HEAD` luôn bỏ thay đổi chưa commit.

Mở SSH lần lượt vào **cả ba node**, thực hiện trên mỗi node:

```bash
cd ~/NT132---Kubernetes-System
hostname
sudo bash scripts/01-prepare-node.sh
sudo systemctl is-active containerd
kubelet --version
```

Script kiểm tra Ubuntu24.04/amd64 và hostname, tắt swap, nạp overlay/br_netfilter, bật IP forwarding, cấu hình containerd với systemd cgroup, cài đúng phiên bản Kubernetes trong `config/versions.env`, giữ package bằng apt hold. Kubelet có thể chưa hoạt động ổn định trước init/join vì chưa có kubeconfig; không reset node vì lý do này. Script dừng nếu máy không đúng môi trường, và không tự nâng cấp package trên node đã join.

## 5. Init control plane, join hai worker

Trên **cp-01**, dùng tài khoản OS Login thường, không mở toàn bộ shell bằng root:

```bash
cd ~/NT132---Kubernetes-System
bash scripts/02-init-control-plane.sh
kubectl get nodes -o wide
sudo kubeadm token create --print-join-command --ttl 2h
```

Lệnh cuối trả về `kubeadm join 10.20.0.10:6443 --token ... --discovery-token-ca-cert-hash sha256:...`. Đây là thông tin nhạy cảm: sao chép trực tiếp sang terminal worker, không chụp vào báo cáo hoặc lưu Git. Trên **wk-01 và wk-02**, chạy lệnh được cấp với `sudo` ở đầu. Không tự viết token/hash minh họa. Token hết hạn thì tạo token mới ở cp-01.

Trở lại **cp-01**:

```bash
kubectl get nodes -o wide
bash scripts/03-install-calico.sh
kubectl get nodes -o wide
kubectl -n kube-system get pods
kubectl get tigerastatus
```

Phải thấy đủ ba node Ready, CoreDNS Running, Calico Available. Node NotReady trước khi cài CNI là trạng thái dự kiến. Giữ taint control plane, không đưa ứng dụng lên cp-01 để chữa thiếu tài nguyên. Nếu join thất bại, kiểm tra `sudo journalctl -u kubelet -n 80 --no-pager` trên worker và kết nối API nội bộ; không chạy `kubeadm reset` tùy tiện.

Tên Kubernetes Node của worker trên GCE có thể là tên đầy đủ `wk-01.<zone>.c.<project>.internal`. Đây không phải lỗi join. Script nhận diện ba node theo InternalIP 10.20.0.10–12; không cần reset hoặc đổi hostname. Bài test Service gán label `nt132.lab/worker` cho hai worker trước khi đặt Pod lên đúng máy.

## 6. Kiểm chứng mạng và Kubernetes Service trước dashboard

Trên **cp-01**:

```bash
bash scripts/test-cross-node.sh
kubectl -n network-check get pods -o wide
kubectl -n network-check get svc,endpointslice
```

Bài kiểm tra tạm thời đặt server ở wk-01 và client ở wk-02, truy cập qua ClusterIP và DNS của Service. Cả hai phải HTTP200. Đây là probe hạ tầng để xác nhận CNI/Service, không phải website đồ án và không thay lựa chọn của TV2. Chụp kết quả khác node cùng EndpointSlice; sau đó dọn:

```bash
kubectl delete -f tests/service/network-check.yaml
```

Nếu timeout, kiểm tra Calico, UDP4789 giữa node và endpoint của Service. Nếu IP chạy mà DNS lỗi, kiểm tra CoreDNS. Không tiếp tục Istio để che lấp lỗi mạng nền.

## 7. Cài Rancher và chuẩn bị truy cập — TV1

Trên **cp-01**:

```bash
bash scripts/04-install-helm.sh
helm version
bash scripts/06-install-rancher.sh
kubectl -n rancher-ingress get svc
kubectl -n cattle-system get pods,ingress
```

Traefik của Rancher phải là ClusterIP. Script tạo CA/certificate trong `~/.nt132-private/tls`, tạo Secret TLS, thêm CoreDNS rewrite cho `rancher.nt132.test` đến Service Traefik nội bộ, cài Rancher một replica. CA và certificate có hạn 90 ngày. Giữ bản sao bảo mật của thư mục private; script không tự xoay CA khi phát hiện file thiếu hoặc không khớp.

Có hai đường độc lập: agent trong cluster dùng `https://rancher.nt132.test` port443 qua CoreDNS; trình duyệt laptop dùng cùng hostname port8443 qua tunnel. **Rancher server-url phải là `https://rancher.nt132.test`, không thêm :8443**, vì agent không đi qua laptop. Khi đăng nhập lần đầu, kiểm tra/sửa ô server URL đúng giá trị này trước khi lưu.

Kiểm tra DNS từ Pod và kiểm tra TLS/backend từ cp-01 trước khi mở trình duyệt:

```bash
kubectl run nt132-dns-check --image=busybox:1.37.0 --restart=Never --rm -i \
  --pod-running-timeout=120s -- nslookup rancher.nt132.test
TRAEFIK_IP="$(kubectl -n rancher-ingress get svc rancher-ingress -o jsonpath='{.spec.clusterIP}')"
curl --fail --cacert "$HOME/.nt132-private/tls/ca.crt" \
  --resolve "rancher.nt132.test:443:$TRAEFIK_IP" https://rancher.nt132.test/ping
```

DNS phải trả IP Service Traefik, `/ping` trả `pong`, curl không báo lỗi chứng chỉ. CoreDNS reload có thể cần khoảng một phút sau patch; nếu chưa phân giải được, xem `kubectl -n kube-system logs deployment/coredns --tail=80` rồi thử lại. Không dùng `curl -k` để coi như đã kiểm chứng CA.

Trên **laptop**, cài Google Cloud CLI, chạy PowerShell:

```powershell
gcloud auth login
$ProjectId = 'THAY_PROJECT_ID_THAT'
gcloud config set project $ProjectId
gcloud compute scp 'cp-01:~/.nt132-private/tls/ca.crt' '.\nt132-lab-ca.crt' --zone=asia-southeast1-a --tunnel-through-iap
Import-Certificate -FilePath '.\nt132-lab-ca.crt' -CertStoreLocation Cert:\CurrentUser\Root
```

Chỉ import CA công khai bạn vừa tạo trong project của mình; không chuyển `ca.key`, `tls.key` về repo. Mở Notepad bằng quyền Administrator, mở `C:\Windows\System32\drivers\etc\hosts`, thêm một dòng nếu chưa tồn tại:

```text
127.0.0.1 rancher.nt132.test
```

Trên **cp-01**, mở terminal riêng và giữ chạy:

```bash
cd ~/NT132---Kubernetes-System
bash scripts/09-port-forward.sh rancher
```

Trên **laptop**, tại thư mục repo, mở terminal riêng và giữ chạy:

```powershell
.\scripts\windows-tunnel.ps1 -ProjectId $ProjectId
```

Nếu Windows chặn script, có thể chạy trực tiếp lệnh tương đương, không cần thay execution policy toàn máy:

```powershell
gcloud compute ssh cp-01 --project=$ProjectId --zone=asia-southeast1-a --tunnel-through-iap -- -N -L 8443:127.0.0.1:8443 -L 8080:127.0.0.1:8080 -L 20001:127.0.0.1:20001
```

Mở `https://rancher.nt132.test:8443`. Lấy bootstrap password tại terminal cp-01:

```bash
kubectl -n cattle-system get secret bootstrap-secret -o jsonpath='{.data.bootstrapPassword}' | base64 -d
echo
```

Đặt mật khẩu riêng, lưu server-url như trên. Không đưa mật khẩu/token vào ảnh. Dashboard cần thấy cluster local, ba node, namespaces và workloads. Port-forward có thể ngắt khi Pod bị thay; chạy lại terminal forwarding nếu trình duyệt mất kết nối.

## 8. Cài Istio, Prometheus, Kiali — TV3 phối hợp TV1

**Điều kiện trước bước này (cập nhật local 06/11):** TV2 đã triển khai Bookinfo baseline không injection, kiểm chứng Service/DNS/HTTP và TV1 review. Làm phần baseline tại [runbook TV2](tv2-runbook.md) trước; chưa cần Istio để chạy baseline. Source Bookinfo/hash/license được chuẩn bị sẵn trong repo bằng `scripts/prepare-bookinfo.py`, không giả định đã có `~/istio-1.30.7/samples`. Các bước dưới là hướng dẫn cho phiên cloud, chưa được chạy trong đợt laptop.

Trên **cp-01**:

```bash
bash scripts/05-install-istio.sh || exit 1
bash scripts/07-install-observability.sh || exit 1
bash scripts/08-verify-cluster.sh || exit 1
kubectl -n istio-system get pods,svc
```

Istiod phân phối cấu hình mesh, gateway nhận traffic, Prometheus thu metrics, Kiali hiển thị graph. Gateway Service là NodePort30080, không dựa vào cloud-controller để cấp external IP. Các phiên bản cụ thể được ghim trong `config/versions.env`; không tự đổi một thành phần sang `latest`.

Mở thêm hai terminal **cp-01**, mỗi terminal một lệnh giữ chạy:

```bash
bash scripts/09-port-forward.sh kiali
```

```bash
bash scripts/09-port-forward.sh app
```

Giữ tunnel Windows ở phần trước. Mở `http://localhost:20001` để xem Kiali, `http://localhost:8080` để truy cập gateway. Trước khi TV2 có route/app, gateway trả404 và graph trống là bình thường. Kiali addon dùng chế độ lab, vì vậy chỉ truy cập qua tunnel. Không công khai port20001.

## 9. Nhận ứng dụng TV2 và tạo config tích hợp

TV2 đã chọn Bookinfo. Bàn giao runtime vẫn gồm namespace, Service đầu vào/đích, ports, labels, ServiceAccount, đường HTTP, imageID và kết quả baseline thật. Xem [phiếu app](application-handover.md) và [runbook TV2](tv2-runbook.md). Workload được sinh offline từ source upstream có hash/license bằng `scripts/prepare-bookinfo.py`; không tải lại manifest không kiểm tra nguồn. Bookinfo hiện không dùng PVC; nếu đổi ứng dụng cần storage, nhóm thống nhất riêng. Boot disk của VM không tự trở thành PersistentVolume.

Các lệnh copy sau chỉ dùng lần đầu. Nếu `config/application.json` đã có, so sánh với bản tham chiếu và giữ thay đổi vận hành cần thiết trước khi thay; không ghi đè config của phiên đang dùng.

Trên **cp-01**:

```bash
cp apps/bookinfo/application.bookinfo.json config/application.json || exit 1
GEN=$(python3 scripts/tv3.py render config/application.json) || exit 1
export GEN
echo "$GEN"
```

Đối chiếu config tham chiếu với baseline thật trước khi apply. `entry_service_port` và `target_service_port` là cổng Service; `target_port` là cổng Pod thực nhận traffic, dùng cho NetworkPolicy. Caller và target cùng namespace; SA/labels phải đúng workload. Bookinfo dùng GET `/ratings/0`, trùng product ID của `/productpage`. Tùy chọn `public_http_matches` chọn rõ các URI productpage/static/login/logout/API; config cũ không có trường này vẫn dùng một match `public_path_prefix`.

Renderer in đúng thư mục mới `.generated/tv3-*` vào `$GEN`; không dùng glob chọn nhầm lần cũ. Sau khi Istio/gateway ở mục 8 Ready, TV2 bật injection cho namespace baseline đã có:

```bash
kubectl apply -f "$GEN/namespace.json" || exit 1
```

TV2 rollout bốn Deployment baseline theo runbook TV2 để Pod mới nhận proxy; không cần tạo lại Namespace hoặc dựng lại baseline. Không bật injection cho kube-system, cattle-system hoặc toàn cluster. Kiểm tra app/proxy Ready bằng helper hỗ trợ native sidecar:

```bash
kubectl -n bookinfo rollout restart deploy/details-v1 deploy/productpage-v1 deploy/reviews-v2 deploy/ratings-v1 || exit 1
for deploy in details-v1 productpage-v1 reviews-v2 ratings-v1; do
  kubectl -n bookinfo rollout status "deployment/$deploy" --timeout=300s || exit 1
done
kubectl -n bookinfo get pods -o json | python3 scripts/check-bookinfo-pods.py || exit 1
kubectl apply -f "$GEN/gateway.json" || exit 1
kubectl apply -f "$GEN/route.json" || exit 1
kubectl -n bookinfo get pods,svc,endpointslice
curl -i http://127.0.0.1:8080/productpage
```

Lệnh curl chạy trên cp-01 khi port-forward app đang mở. Thay namespace/path bằng giá trị TV2. Thực hiện các bước triển khai trong terminal SSH lab riêng: `|| exit 1` dừng terminal đó nếu lệnh lỗi, không tiếp tục apply sau lỗi renderer/rollout/checker. Giữ forwarding ở terminal khác. Nếu config/application.json đã có, đối chiếu trước khi copy bản tham chiếu. Không chạy `kubectl apply -f "$GEN"`: thư mục có `inputs.json` không phải Kubernetes resource, và các policy cần triển khai từng bước để có đối chứng.

## 10. Kiểm thử bảo mật theo từng lớp — TV3

Trước mỗi lớp, ghi request nguồn, đích, danh tính, HTTP status và kỳ vọng. TV2 cung cấp cách gọi API thật từ caller; không áp dụng policy trước khi kiểm tra labels/ServiceAccount/sidecar.

1. **C0 sau mesh:** hai nguồn trong mesh gọi GET `/ratings/0` đều 200 trước luật hạn chế; Service selector khớp Pod và EndpointSlice Ready. Baseline không proxy trước mesh là bước riêng.
2. **C1 / mTLS:** chỉ áp `mtls.json`, hai nguồn trong mesh vẫn 200, có bằng chứng mTLS. C1b dùng client không proxy đã được cấp quyền, có lượt thành công trước STRICT; không mặc định lỗi TLS là HTTP 403.
3. **C2 / danh tính và API:** giữ STRICT, chỉ thêm `authorization.json`. Reviews đúng SA/method/path được 200; productpage gọi thẳng target bị 403/RBAC. Lưu evidence, **gỡ riêng AuthorizationPolicy vừa tạo**, lặp hai nguồn đều 200 trước C3.
4. **C3 / mạng:** giữ STRICT, xác nhận AuthorizationPolicy thử đã gỡ rồi chỉ thêm `network-policy.json`. Reviews qua TCP 9080 được, nguồn khác thất bại kết nối/upstream, DNS và endpoint còn đúng. Lưu evidence, **gỡ riêng NetworkPolicy vừa tạo**, lặp hai nguồn đều 200. Cho riêng metrics bằng selector namespace+Pod kết hợp, không mở toàn namespace vào cổng app.
5. **C4 / kết hợp:** chỉ sau C2/C3 riêng và phục hồi đã đạt mới bật cả hai luật, thử hai nguồn và website có sao. Gỡ riêng luật thử, trở lại C1, đối chiếu nguồn/đích/path/trạng thái và người chạy lại. Không suy nguyên nhân lớp mạng chỉ từ một timeout/503.

Thực hiện lệnh từng ca và rollback theo [runbook TV2](tv2-runbook.md), [security README](../tests/security/README.md) và [ma trận](tv3-test-matrix.md). Không ghi đè hoặc xóa policy nền của người khác để tạo baseline.

Đường từ ingress gateway trực tiếp vào target sẽ bị policy này chặn nếu gateway không thuộc nhóm caller được cho phép. Chọn target là dịch vụ nội bộ sau entry service; nếu app có luồng khác, TV3 phải điều chỉnh ma trận nguồn/đích trước. NetworkPolicy này chỉ giới hạn ingress target, chưa có default-deny egress toàn namespace.

Hoàn tác riêng một lớp khi cần chẩn đoán, ví dụ:

```bash
kubectl delete -f "$GEN/network-policy.json" --ignore-not-found
```

Ghi lại việc hoàn tác và apply lại sau khi sửa. Không xóa cả namespace để chữa policy. Tạo traffic bằng endpoint thật, chọn đúng namespace và khoảng thời gian gần nhất trong Kiali; graph chỉ xuất hiện khi có traffic và metrics.

## 11. Bật public load balancer khi cần báo cáo từ bên ngoài

Không cần bật LB để show Rancher/Kiali qua tunnel. Khi ứng dụng đã chạy qua gateway và muốn người khác truy cập, tại **Cloud Shell**, thư mục `infra/gcp`, sửa `terraform.tfvars`: đặt `enable_public_lb = true`. Đặt `web_source_ranges` theo public IP/CIDR người xem, ví dụ một IP thực kèm `/32`. `0.0.0.0/0` mở HTTP lab cho toàn Internet, chỉ chọn nếu thực sự cần; không dùng dữ liệu hoặc mật khẩu thật.

```bash
terraform plan -out=nt132-public.tfplan
terraform show nt132-public.tfplan
terraform apply nt132-public.tfplan
terraform output -raw web_ip
gcloud compute backend-services list --regions=asia-southeast1
```

Đọc tên backend được liệt kê rồi kiểm tra:

```bash
gcloud compute backend-services get-health TEN_BACKEND_THAT --region=asia-southeast1
curl -i http://DIA_CHI_LB_THAT:30080/DUONG_DAN_THAT
```

Chạy curl từ máy thuộc CIDR được cho phép. Hai worker phải healthy. Health check TCP30080 chỉ xác nhận cổng gateway nhận kết nối, không chứng minh business endpoint hoạt động. Luồng: client → regional LB:30080 → NodePort worker → Istio gateway → VirtualService → Service ứng dụng → Pod. `externalTrafficPolicy: Cluster` cho phép worker chuyển đến gateway Pod nằm ở worker khác; không dùng bài kiểm tra này để khẳng định giữ nguyên source IP. LB này không cấp HTTPS cho app.

## 12. Lịch năm ngày và trách nhiệm

Sau khi TV1 mở được Rancher, dùng [hướng dẫn thêm thành viên](them-thanh-vien.md) để mời TV2/TV3 vào GitHub, Google Cloud và Rancher bằng tài khoản riêng, rồi bàn giao branch và nhiệm vụ.

| Ngày | TV1 | TV2 | TV3 | Điều kiện chốt ngày |
|---|---|---|---|---|
| 1 | Project/IAM/budget, Terraform tạo3VM, chuẩn bị cp-01 và init. | Chọn app, ghi nguồn/license/version, chuẩn bị wk-01 và join. | Chuẩn bị wk-02 và join; cài Calico cùng TV1. | Ba node Ready, inventory không có secret. |
| 2 | Cài Rancher, CA/DNS/tunnel; đăng nhập dashboard. | Test ClusterIP/DNS/EndpointSlice khác node; hoàn tất phiếu app. | Kiểm tra VXLAN, cài Istio, đối chiếu Service gateway. | Show được Rancher và cấu trúc cụm dù app chưa xong. |
| 3 | Kiểm tra RAM/events, hỗ trợ nguồn lực, lưu evidence. | Deploy app vào namespace injection, probes/Service/port đúng. | Cài Prometheus/Kiali, tích hợp gateway/route. | Truy cập app qua tunnel, graph có traffic. |
| 4 | Nếu cần, bật LB và kiểm tra health/firewall. | Chạy ca scale/restart/selector, giải thích endpoint thay đổi. | Từng lớp mTLS/AuthorizationPolicy/NetworkPolicy có ca cho phép và chặn. | Có bảng kết quả và bằng chứng cho từng lớp. |
| 5 | Tập demo kiến trúc/IAP/Rancher, tổng hợp inventory và chi phí. | Demo Service/DNS/EndpointSlice/failover Pod. | Demo Kiali/mesh/policy, ghi giới hạn. | Một buổi chạy thử đủ luồng, có phương án tunnel dự phòng. |

TV1 chịu trách nhiệm hạ tầng và dashboard quản trị; TV2 chịu trách nhiệm workload/Service và bài kiểm chứng; TV3 chịu trách nhiệm mạng Pod/mesh/quan sát/bảo mật. Mỗi người tự cấu hình và giải thích worker hoặc control plane mình phụ trách, đọc chéo phần người khác. Không giao toàn bộ thao tác kỹ thuật cho TV1.

## 13. Checklist trước báo cáo và xử lý lỗi

Trên cp-01:

```bash
bash scripts/08-verify-cluster.sh
kubectl get nodes -o wide
kubectl get pods -A -o wide
kubectl get events -A --sort-by=.lastTimestamp
kubectl -n cattle-system logs deployment/rancher --tail=80
kubectl -n istio-system logs deployment/istiod --tail=80
```

Lưu ảnh ba node Ready, Rancher workloads, sơ đồ IP/CIDR, Service+EndpointSlice, Kiali có traffic, request thành công/thất bại, LB health nếu bật. Che project identity cần bảo mật, token/password và nội dung Secret. `kubectl top` chưa dùng được nếu chưa cài metrics-server; không xem đó là lỗi Prometheus. Dùng thông tin scheduling/requests, events, `free -h` trên node và metrics từ Prometheus để đánh giá tài nguyên hiện có.

| Triệu chứng | Kiểm tra trước |
|---|---|
| Pod Pending | `kubectl describe pod ...`: thiếu CPU/RAM, taint hoặc PVC chưa bind. Không gỡ taint cp-01 tùy tiện. |
| ImagePullBackOff | Tên/tag image, quyền registry và kết nối ra Internet của worker. |
| Rancher502/không mở được | Ba mắt xích: Pod Rancher Ready, port-forward cp-01 còn chạy, SSH tunnel laptop còn chạy. |
| Rancher agent TLS lỗi | server-url không có8443, CoreDNS rewrite, CA Secret và certificate cùng CA. |
| Service không có endpoint | selector Service so với labels Pod, readinessProbe và targetPort. |
| Istio404 | Namespace/Gateway/VirtualService và path; chưa có route thì404 là bình thường. |
| Kiali trống | App đã có sidecar chưa, traffic thực, namespace/time range, Prometheus Running. |
| Worker NotReady | kubelet/containerd, Calico và firewall VXLAN; xem journal trước khi thay config. |

## 14. Dừng lab và dọn tài nguyên

Dừng terminal tunnel không dừng tính phí cloud. Stop VM vẫn còn phí disk/IP và LB. Nếu giữ cụm cho buổi sau, đảm bảo có thể chịu chi phí và tắt/mở theo quy trình nhóm; đây không phải HA cluster.

Khi kết thúc đồ án, sao lưu dữ liệu ứng dụng cần giữ, evidence và tài liệu, xác nhận đúng project/state tại Cloud Shell rồi chạy:

```bash
cd ~/NT132---Kubernetes-System/infra/gcp
terraform plan -destroy -out=nt132-destroy.tfplan
terraform show nt132-destroy.tfplan
# Chỉ chạy sau khi đã xem danh sách và chấp nhận mất VM/disk/dữ liệu:
terraform apply nt132-destroy.tfplan
gcloud compute instances list
gcloud compute addresses list
gcloud compute forwarding-rules list
```

Terraform chỉ dọn tài nguyên nó quản lý, không xóa cả project. Các API vẫn bật sau destroy. Gỡ dòng hosts và CA `NT132 Lab CA` khỏi laptop khi không dùng nữa (chọn đúng certificate theo thumbprint, không xóa CA khác).

## 15. Phạm vi đã kiểm tra của bộ config

Đã có kiểm tra local: Terraform format/validate và mock test topology, render Helm chart đúng version, parse YAML, syntax Bash và unit test renderer ứng dụng. Ngày 05/11/2026, nhóm đã apply hạ tầng, đưa ba node v1.35.10 về Ready, kiểm chứng Pod IP/ClusterIP/DNS khác node trả HTTP 200 và mở Rancher v2.15.3 với đủ ba node Active. Istio, Kiali, ứng dụng TV2 và các policy theo ứng dụng chưa được triển khai. Repo không chứa credentials, token join, private key, mật khẩu Rancher hoặc ứng dụng được chọn thay TV2.

Tham khảo chính thức: [kubeadm](https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/install-kubeadm/), [Istio supported releases](https://istio.io/latest/docs/releases/supported-releases/), [Rancher installation](https://ranchermanager.docs.rancher.com/getting-started/installation-and-upgrade/install-upgrade-on-a-kubernetes-cluster/), [Calico requirements](https://docs.tigera.io/calico/latest/getting-started/kubernetes/requirements), [IAP TCP forwarding](https://cloud.google.com/iap/docs/using-tcp-forwarding), [Google Cloud passthrough LB](https://cloud.google.com/load-balancing/docs/network/setting-up-network-backend-service).
