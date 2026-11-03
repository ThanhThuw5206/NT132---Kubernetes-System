# Hướng dẫn thực hành cho TV1 · Kubernetes trên ba VM Google Cloud

**Thông số ứng dụng do TV2 quyết định.** Xem [phiếu bàn giao](./application-handover.md). APP_NAMESPACE, ENTRY_SERVICE, CALLER_SERVICE, TARGET_SERVICE, SERVICE_PORT và các token viết hoa trong ví dụ cần thay bằng giá trị thực trước khi chạy. Với đường dẫn, /APP_PATH và /TEST_PATH là ký hiệu cả path, thay bằng đường dẫn thật có một dấu / đầu. Các dòng mô tả chức năng của ứng dụng là tiêu chí kiểm thử cần đối chiếu với lựa chọn của TV2.

Ngày biên soạn 03/11/2026. Tài liệu dành cho bạn phụ trách hạ tầng, control plane, Rancher và đường public của đồ án NT132. Cụm dùng ứng dụng do TV2 tự chọn để học Kubernetes Service. Các câu lệnh dưới đây là hướng dẫn để nhóm triển khai; chưa được chạy trên project Google Cloud của nhóm.

**Kết quả bạn cần bàn giao.** Ba VM gia nhập cùng một cụm; hai worker chạy được Pod liên lạc với nhau; bạn mở Rancher từ laptop để chỉ node, workload và Service; người ngoài VPC mở được ứng dụng do TV2 lựa chọn qua IP của load balancer; bạn tự phân biệt được lỗi đường mạng, Service không có endpoint và policy từ chối.

**Thứ tự đọc và thực hiện**

1. Mục 1–3 chốt thông số, công cụ và tài khoản.
2. Mục 4–7 tạo cloud network, VM, cài runtime và control plane.
3. Mục 8–10 ghép worker, nghiệm thu mạng và chuẩn bị công cụ quản trị.
4. Mục 11–13 cài Rancher, thử quyền và nhận ứng dụng từ TV2/TV3.
5. Mục 14–16 tạo LB, kiểm chứng Service và chuẩn bị báo cáo.
6. Mục 17–20 vận hành, khắc phục lỗi, bàn giao và dọn lab.

## 1. Quy ước để chạy đúng nơi

Trong tài liệu, **Cloud Shell/Bash** là terminal trên Cloud Console, đã có gcloud. **SSH cp-01/Bash** là terminal Linux trên control plane. **SSH từng VM/Bash** phải thực hiện trên cả ba máy, mỗi bạn làm máy của mình. **Laptop/PowerShell** là máy Windows của bạn. Biến Bash không tự tồn tại trong PowerShell hoặc một phiên SSH khác. Khi mở terminal mới, nạp lại biến ở mục tương ứng.

Một khối lệnh nhiều dòng dùng dấu gạch chéo ngược là Bash. Hãy chạy cả khối và kiểm tra kết quả trước khi qua khối kế tiếp. Giá trị có dấu <...> là chỗ phải điền. Các file YAML trong hướng dẫn được tạo trên cp-01 trừ khi có chỉ dẫn khác. VM, firewall và LB là tài nguyên tính phí khi bạn thực sự tạo chúng.

Bạn điều phối theo ba điểm bàn giao. Sau khi init, gửi thông tin join cho TV2/TV3. Sau khi họ hoàn thành CNI, kiểm tra ba node Ready. Sau khi TV2 giao NodePort chạy trên cả hai worker, mới nối cloud LB. TV3 cài Istio và quan sát; TV2 phụ trách ứng dụng mẫu, Service và route. Các phần nhận bàn giao bên dưới giúp bạn kiểm tra kết quả của hai bạn, tránh cài chồng tài nguyên của họ.

## 2. Thiết kế cụ thể dùng xuyên suốt hướng dẫn

| Mục | Giá trị đề xuất | Ý nghĩa |
|---|---|---|
| Region / zone | asia-southeast1 / asia-southeast1-a | Ba máy cùng zone để giảm biến số lúc làm lab. Đổi đồng bộ nếu quota vùng này thiếu. |
| VPC / subnet | nt132-vpc / nt132-subnet | Mạng riêng do nhóm tự tạo. |
| Node subnet | 10.20.0.0/24 | IP riêng của VM. |
| cp-01 | 10.20.0.10, e2-medium, 20 GB | 2 vCPU chia sẻ, 4 GiB RAM, một control plane. Nếu CPU tranh chấp, đổi loại máy sau khi đo. |
| wk-01 / wk-02 | 10.20.0.11 / .12, e2-standard-2, 30 GB mỗi máy | Mỗi worker 2 vCPU, 8 GiB RAM. Tổng disk khởi động 80 GB. |
| OS | Ubuntu 24.04 LTS amd64 | Ghi image cụ thể sau khi tạo; dùng cùng image cho ba máy. |
| Pod CIDR / Service CIDR | 10.244.0.0/16 / 10.96.0.0/12 | Hai dải khác subnet node và mạng laptop/VPN. |
| CNI | Calico VXLAN, kube-proxy thông thường | TV3 triển khai pool và encapsulation đúng với bảng firewall. |
| Đường SSH | gcloud SSH qua IAP | Nhận diện từng người bằng Google IAM và OS Login. |
| Outbound của VM | External IP động, inbound hạn chế bởi firewall | Dễ tải package/image cho lab. Các IP này có chi phí riêng. |
| API server | IP riêng cp-01, TCP 6443 | Chỉ node và đường quản trị được phép kết nối. |
| App public | Regional external passthrough Network LB, TCP 30080 | Cùng cổng frontend và NodePort, giữ IP client qua LB. |
| Rancher | rancher.nt132.test, TLS do CA riêng cấp | Tên lab phân giải qua CoreDNS và hosts laptop. Dùng Traefik riêng cho quản trị. |

Hướng dẫn chọn Rancher làm dashboard quản trị chính. Rancher và Traefik chạy trong cluster, quản trị qua tunnel. Đây là quyết định triển khai cụ thể để bạn có một đường làm xuyên suốt. Kiểm tra tài nguyên hai worker sau khi có Rancher, Istio, Prometheus và Kiali. Giới hạn một control plane phải được nêu trong báo cáo.

## 3. Chuẩn bị tài khoản và ghi phiên bản

### Thao tác 01 · Mở đúng công cụ và tạo project

1. Trên Windows mở trình duyệt, vào https://console.cloud.google.com và đăng nhập tài khoản Google dùng cho đồ án.
2. Bấm bộ chọn project cạnh logo Google Cloud, chọn **New Project**, nhập tên hiển thị NT132 Kubernetes Lab. Ghi lại **Project ID** vì ID dùng trong lệnh có thể khác tên hiển thị. Bấm Create rồi chọn project vừa tạo.
3. Vào **Billing**, liên kết billing account nhóm được phép dùng. Nếu project đã được cấp, chọn project đó và kiểm tra billing đang bật.
4. Vào **IAM & Admin → Quotas & System Limits**, lọc Compute Engine và region asia-southeast1. Xác nhận quota CPU và địa chỉ IP phù hợp ba VM. Nếu tài khoản không có quyền xem hoặc thay billing/quota, người quản lý tài khoản thực hiện bước tương ứng.
5. Bấm biểu tượng **Activate Cloud Shell** ở thanh trên. Khi terminal mở, chạy lệnh dưới, thay chuỗi giữa dấu nháy bằng Project ID thật.

```bash
export PROJECT_ID='DIEN_PROJECT_ID_THAT'
export REGION='asia-southeast1'
export ZONE='asia-southeast1-a'
gcloud config set project "$PROJECT_ID"
gcloud config get-value project
gcloud auth list
```

**Thành phần được setup:** project để chứa toàn bộ VM và mạng. **Kết quả để đi tiếp:** tên project trong output đúng với project đang chọn trên Console. Nếu mở Cloud Shell phiên mới, chạy lại ba lệnh export để khôi phục biến.

### Thao tác 02 · Cấp quyền cho tài khoản nhóm

Người có quyền quản lý IAM vào **IAM & Admin → IAM → Grant access**, điền email thành viên và chọn quyền cần thiết. TV1 cần Compute Admin để làm các bước hạ tầng và Service Usage Admin để bật API. Các bạn cần Compute Viewer để tra thông tin VM, IAP-secured Tunnel User để mở tunnel, Compute OS Admin Login để SSH và dùng sudo cài package. Quyền trong project lab cấp ở mức project sẽ cho phép thao tác theo phạm vi đó, cần thống nhất trong nhóm.

Nếu bạn là người quản lý IAM, có thể chạy trong Cloud Shell thay thao tác UI. Điền một email thật, chạy cho từng thành viên:

```bash
export MEMBER_EMAIL='DIEN_EMAIL_THANH_VIEN'
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="user:$MEMBER_EMAIL" --role=roles/compute.viewer
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="user:$MEMBER_EMAIL" --role=roles/iap.tunnelResourceAccessor
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="user:$MEMBER_EMAIL" --role=roles/compute.osAdminLogin
```

Người quản lý IAM cấp thêm hai role sau cho email TV1:

```bash
export TV1_EMAIL='DIEN_EMAIL_CUA_BAN'
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="user:$TV1_EMAIL" --role=roles/compute.admin
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="user:$TV1_EMAIL" --role=roles/serviceusage.serviceUsageAdmin
```

**Thành phần được setup:** quyền thao tác Google Cloud và quyền đăng nhập Linux. **Kết quả để đi tiếp:** email đúng và role xuất hiện trong IAM. Khi VM đã tạo, từng người phải tự thử SSH. Quyền Kubernetes trong cluster được kiểm tra riêng sau khi cụm hoạt động.

### Thao tác 03 · Cài công cụ trên laptop Windows

1. Vào trang cài Google Cloud CLI cho Windows, tải installer và hoàn tất wizard. Mở một PowerShell mới sau khi cài để PATH được cập nhật.
2. Trong Windows Settings → Apps → Optional features, kiểm tra **OpenSSH Client** đã có. Nếu chưa, chọn thêm feature này.
3. Chạy khối PowerShell ở mục 3.1, đăng nhập đúng email TV1, chọn Project ID thật.
4. Tạo thư mục lưu bằng chứng của riêng bạn:

```powershell
$LabFolder = Join-Path $env:USERPROFILE 'Documents\NT132-TV1'
New-Item -ItemType Directory -Path $LabFolder -Force
New-Item -ItemType Directory -Path (Join-Path $LabFolder 'evidence') -Force
gcloud version
ssh -V
```

**Thành phần được setup:** máy quản trị của bạn. **Kết quả để đi tiếp:** gcloud và ssh trả version. Các lệnh kubectl/Helm chính trong file sẽ chạy trên cp-01 qua SSH.

### 3.1. Trên Google Cloud Console

Chọn hoặc tạo project riêng cho lab. Gắn billing theo tài khoản nhóm được phép dùng. Kiểm tra quota Compute Engine tại region, ít nhất ba VM và 6 vCPU theo loại máy chọn. Tạo budget alert và người nhận. Nhãn nt132 dùng để kiểm kê tài nguyên sau buổi demo.

TV1 cần quyền tạo/quản lý compute, network, firewall và LB trong project. Người quản trị project cấp Service Usage Admin để bật API nếu cần. Mỗi thành viên được cấp IAP-secured Tunnel User và quyền OS Login/OS Admin Login phù hợp để SSH. Thay đổi IAM do người có quyền thực hiện. Xác minh bằng việc từng bạn SSH vào máy riêng; một người SSH thành công chưa chứng minh quyền của hai người còn lại.

Trên laptop cài Google Cloud CLI và OpenSSH client. Kiểm tra bằng PowerShell:

```powershell
gcloud version
ssh -V
gcloud auth login
gcloud config set project <PROJECT_ID>
gcloud auth list
```

### 3.2. Ghim bộ phiên bản trước khi cài

Bạn và TV3 mở ma trận hỗ trợ Rancher, Kubernetes, Calico và Istio, chọn một Kubernetes minor được tất cả hỗ trợ. Ghi phiên bản chính xác vào versions.md. Tài liệu không giả định bản mới nhất của mọi công cụ tương thích với nhau.

| Thành phần | Cách tìm và chốt |
|---|---|
| Kubernetes | Chọn minor từ giao của ma trận hỗ trợ. Sau khi thêm apt repo, dùng apt-cache madison để lấy package version chính xác. |
| Containerd | Dùng bản Ubuntu cung cấp, ghi containerd --version. Các lệnh cấu hình ở mục 6 kiểm tra định dạng thực trước khi sửa. |
| Rancher / Traefik | Sau khi thêm Helm repo, helm search repo --versions, chọn stable và helm show values --version để xem key cấu hình. |
| Calico / Istio | TV3 ghi release, URL manifest và file cấu hình đã chỉnh. |
| Helm | Tải binary Linux amd64 từ release chính thức, xác minh checksum rồi install. |

Nếu chưa chốt được bộ tương thích thì hoàn thành phần VPC/VM và inventory trước, dừng ở bước thêm repo Kubernetes. Các URL tài liệu ở cuối file dẫn tới nguồn để chốt bản thực.

## 4. Tạo VPC và firewall

### Thao tác 04 · Chạy khối tạo mạng ở đâu?

Mở Cloud Shell từ project đã xác nhận ở thao tác 01. Dán khối export/API/VPC bên dưới, đọc lỗi sau từng lệnh. Sau đó chạy khối firewall. Khi xong vào **VPC network → VPC networks**, mở nt132-vpc và kiểm tra subnet nt132-subnet có range 10.20.0.0/24. Vào **Firewall**, tìm từng rule bắt đầu nt132-. Khi lệnh báo Already exists, dùng trang chi tiết để đối chiếu resource có đúng thông số rồi tiếp tục.

**Bạn vừa tạo:** mạng riêng cho node và các cửa cho SSH, API, kubelet, mạng Pod. **Bạn chưa có VM ở bước này.** Chuyển sang mục 5 khi subnet và firewall đã xuất hiện.

**Nơi chạy: Cloud Shell/Bash.** Điền PROJECT_ID bằng ID thật; region/zone phải thống nhất trong cả file.

```bash
export PROJECT_ID='<PROJECT_ID>'
export REGION='asia-southeast1'
export ZONE='asia-southeast1-a'
gcloud config set project "$PROJECT_ID"
gcloud services enable compute.googleapis.com iap.googleapis.com oslogin.googleapis.com
gcloud compute networks create nt132-vpc --subnet-mode=custom
gcloud compute networks subnets create nt132-subnet \
  --network=nt132-vpc --region="$REGION" --range=10.20.0.0/24
```

Tạo các rule sau. Source tags giới hạn rule vào những VM thuộc cùng VPC có tag nhóm. Tag có thể được người quản trị compute thay đổi, vì vậy phải hạn chế quyền sửa hạ tầng của người chỉ xem.

```bash
gcloud compute firewall-rules create nt132-iap-ssh \
  --network=nt132-vpc --direction=INGRESS --action=ALLOW \
  --rules=tcp:22 --source-ranges=35.235.240.0/20 --target-tags=nt132-node
gcloud compute firewall-rules create nt132-node-api \
  --network=nt132-vpc --direction=INGRESS --action=ALLOW \
  --rules=tcp:6443 --source-tags=nt132-node --target-tags=nt132-cp
gcloud compute firewall-rules create nt132-kubelet \
  --network=nt132-vpc --direction=INGRESS --action=ALLOW \
  --rules=tcp:10250 --source-tags=nt132-cp --target-tags=nt132-node
gcloud compute firewall-rules create nt132-vxlan \
  --network=nt132-vpc --direction=INGRESS --action=ALLOW \
  --rules=udp:4789 --source-tags=nt132-node --target-tags=nt132-node
gcloud compute firewall-rules create nt132-node-test \
  --network=nt132-vpc --direction=INGRESS --action=ALLOW \
  --rules=icmp,tcp:30080 --source-tags=nt132-node --target-tags=nt132-node
gcloud compute firewall-rules list --filter='network:nt132-vpc'
```

Rule kubelet hỗ trợ API lấy log/exec/port-forward tới Pod trên worker. VXLAN đóng gói lưu lượng Pod qua UDP giữa node. API, kubelet và Calico là những chức năng khác nhau nên phải ghi được luồng tương ứng. Với Calico bật Typha hoặc metrics collector cần kubelet, bổ sung rule giữa đúng nguồn/đích theo cấu hình TV3 thực dùng. Với một control plane, etcd chỉ dùng nội bộ máy này. [IAP TCP forwarding](https://cloud.google.com/iap/docs/using-tcp-forwarding) · [Ports and protocols Kubernetes](https://kubernetes.io/docs/reference/networking/ports-and-protocols/)

## 5. Tạo ba VM và bàn giao worker

### Thao tác 05 · Tạo máy, xác nhận rồi SSH

1. Trong cùng Cloud Shell, chạy ba lệnh addresses create rồi ba khối instances create bên dưới. Mỗi khối instances create tạo một VM Linux.
2. Mở **Compute Engine → VM instances**. Kiểm tra cp-01, wk-01, wk-02 đều Running. Bấm từng tên máy, so Machine type, Internal IP, Network tags và boot disk với bảng mục 2.
3. Trên **PowerShell của laptop**, chạy lệnh gcloud compute ssh ở cuối mục. Nếu lần đầu hỏi tạo SSH key, làm theo prompt của gcloud.
4. Khi prompt chuyển thành user@cp-01, chạy `hostname`. Phải nhận cp-01. Đây là terminal Linux trên VM, các bước mục 6–7 chạy tại đây.
5. TV2 đổi tên máy thành wk-01, TV3 đổi thành wk-02 rồi thực hiện cùng bước xác nhận. Gửi bảng IP và mục 6 cho hai bạn.

**Kết quả để đi tiếp:** bạn ở trong cp-01, hai bạn ở đúng worker. Chụp ảnh danh sách ba VM và lưu vào thư mục evidence trên laptop.

**Cloud Shell/Bash.** Dành ba IP riêng trước khi tạo VM; ghi tên reservation vào inventory.

```bash
gcloud compute addresses create nt132-cp-ip --region="$REGION" --subnet=nt132-subnet --addresses=10.20.0.10
gcloud compute addresses create nt132-w1-ip --region="$REGION" --subnet=nt132-subnet --addresses=10.20.0.11
gcloud compute addresses create nt132-w2-ip --region="$REGION" --subnet=nt132-subnet --addresses=10.20.0.12
gcloud compute instances create cp-01 \
  --zone="$ZONE" --machine-type=e2-medium \
  --image-family=ubuntu-2404-lts-amd64 --image-project=ubuntu-os-cloud \
  --subnet=nt132-subnet --private-network-ip=10.20.0.10 \
  --boot-disk-size=20GB --boot-disk-type=pd-balanced \
  --tags=nt132-node,nt132-cp --can-ip-forward \
  --metadata=enable-oslogin=TRUE --no-service-account --no-scopes \
  --labels=project=nt132,role=control-plane
gcloud compute instances create wk-01 \
  --zone="$ZONE" --machine-type=e2-standard-2 \
  --image-family=ubuntu-2404-lts-amd64 --image-project=ubuntu-os-cloud \
  --subnet=nt132-subnet --private-network-ip=10.20.0.11 \
  --boot-disk-size=30GB --boot-disk-type=pd-balanced \
  --tags=nt132-node,nt132-worker --can-ip-forward \
  --metadata=enable-oslogin=TRUE --no-service-account --no-scopes \
  --labels=project=nt132,role=worker
gcloud compute instances create wk-02 \
  --zone="$ZONE" --machine-type=e2-standard-2 \
  --image-family=ubuntu-2404-lts-amd64 --image-project=ubuntu-os-cloud \
  --subnet=nt132-subnet --private-network-ip=10.20.0.12 \
  --boot-disk-size=30GB --boot-disk-type=pd-balanced \
  --tags=nt132-node,nt132-worker --can-ip-forward \
  --metadata=enable-oslogin=TRUE --no-service-account --no-scopes \
  --labels=project=nt132,role=worker
gcloud compute instances list --filter='labels.project=nt132'
```

Các lệnh create dành cho tài nguyên chưa tồn tại. Nếu máy đã có, dùng describe để đối chiếu rồi tiếp tục trên máy đó. Nếu tổ chức cấm external IP, chọn private VM và cấu hình Cloud NAT cho outbound trước khi cài gói; ghi điều chỉnh vào inventory. Lab dùng image public nên VM không cần Google service account để kéo image này.

TV1 có thể tạo cả ba VM cho cùng một cấu hình; TV2/TV3 chịu trách nhiệm cài đặt Linux/Kubernetes trên worker được giao. Gửi mỗi người tên project, zone, VM, IP riêng và bước 6. Mỗi người tự SSH bằng tài khoản của mình:

```powershell
gcloud compute ssh cp-01 --zone=asia-southeast1-a --tunnel-through-iap
```

Đổi cp-01 thành wk-01/wk-02 cho hai bạn. Trên VM chạy hostnamectl, ip -br addr, ip route, df -h, free -h và timedatectl. Kết quả đạt: đúng hostname/IP, có default route, disk/RAM đúng cấp và đồng hồ đồng bộ. Chụp inventory ba VM trước khi qua bước 6.

## 6. Chuẩn hóa Ubuntu trên từng VM

### Thao tác 06 · Chạy cài runtime, rồi cài Kubernetes

Trước khi dán lệnh, chạy `hostname` và xác nhận bạn đang ở cp-01. Dán khối từ apt-get đến sysctl trong mục này. Nếu sudo hỏi password hoặc báo thiếu quyền, quay lại kiểm tra quyền OS Admin Login của tài khoản. Nếu apt báo lock, chờ tiến trình cập nhật Ubuntu đang chạy hoàn tất rồi thử lại.

Đọc output sau khi cài runtime. Tiếp theo điền K8S_MINOR bằng phiên bản nhóm đã chốt, chạy đến apt-cache madison. Chọn **nguyên chuỗi ở cột version**, dán vào K8S_PKG, rồi chạy khối apt install. Gửi chính chuỗi minor/package này cho TV2 và TV3.

**Ví dụ cách điền, không phải phiên bản đã chốt:** nếu nhóm chọn minor v1.XX và apt trả 1.XX.Y-1.1 thì đặt K8S_MINOR=v1.XX, K8S_PKG=1.XX.Y-1.1. Không chạy lệnh với XX/Y. Mục tiêu là ba máy dùng cùng bộ phiên bản tương thích Rancher/Istio.

**SSH từng VM/Bash.** Thực hiện trên máy mới dành cho lab. TV1 làm cp-01; hai bạn làm worker. Cấu hình này còn phải tồn tại sau reboot.

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gpg containerd
sudo swapoff -a
sudo cp /etc/fstab /etc/fstab.nt132-backup
sudo sed -i '/^[^#].*[[:space:]]swap[[:space:]]/ s/^/# nt132 /' /etc/fstab
cat <<'EOF' | sudo tee /etc/modules-load.d/nt132.conf
overlay
br_netfilter
EOF
sudo modprobe overlay
sudo modprobe br_netfilter
cat <<'EOF' | sudo tee /etc/sysctl.d/99-nt132.conf
net.ipv4.ip_forward = 1
net.bridge.bridge-nf-call-iptables = 1
net.bridge.bridge-nf-call-ip6tables = 1
EOF
sudo sysctl --system
sudo mkdir -p /etc/containerd
containerd config default | sudo tee /etc/containerd/config.toml >/dev/null
sudo sed -i 's/SystemdCgroup = false/SystemdCgroup = true/g' /etc/containerd/config.toml
sudo systemctl enable --now containerd
sudo systemctl restart containerd
sudo systemctl status containerd --no-pager
grep -n 'SystemdCgroup\|disabled_plugins' /etc/containerd/config.toml
swapon --show
sysctl net.ipv4.ip_forward
```

Kỳ vọng swap không có dòng active, forwarding=1, runtime active và SystemdCgroup=true. CRI phải bật. Nếu config của bản runtime khác không có key SystemdCgroup, tra cấu hình đúng version và chỉnh đúng plugin CRI trước khi tiếp tục. cgroup driver của kubelet và runtime phải thống nhất. Lệnh tạo config default phù hợp VM mới; nếu máy đã có cấu hình runtime, backup và so sánh thay vì chạy đè.

**Cài Kubernetes.** Điền minor và package version đã chốt ở mục 3.2. Ví dụ định dạng minor là v1.xx; package version lấy từ apt-cache, không nhập chuỗi ví dụ.

```bash
export K8S_MINOR='<minor-da-chon>'
sudo mkdir -p /etc/apt/keyrings
curl -fsSL "https://pkgs.k8s.io/core:/stable:/$K8S_MINOR/deb/Release.key" \
  | sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
echo "deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/$K8S_MINOR/deb/ /" \
  | sudo tee /etc/apt/sources.list.d/kubernetes.list
sudo apt-get update
apt-cache madison kubeadm
export K8S_PKG='<package-version-tu-ket-qua-tren>'
sudo apt-get install -y kubelet="$K8S_PKG" kubeadm="$K8S_PKG" kubectl="$K8S_PKG"
sudo apt-mark hold kubelet kubeadm kubectl
sudo systemctl enable kubelet
kubeadm version -o short
containerd --version
```

Kubelet trước init/join có thể chờ bootstrap và báo chưa có cấu hình. Đến bước join xong mới nghiệm thu node. Gửi TV3 bản version thực, không chỉ tên repo. [Cài kubeadm](https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/install-kubeadm/) · [Container runtimes](https://kubernetes.io/docs/setup/production-environment/container-runtimes/)

## 7. Khởi tạo control plane và cấp lệnh join

### Thao tác 07 · Bạn tạo cụm, hai bạn gia nhập cụm

1. Trong SSH cp-01, chạy từ export K8S_VERSION đến kubeadm init bên dưới. Đợi thông báo khởi tạo control plane thành công.
2. Chạy mkdir/install kubeconfig để kubectl của user hiện tại sử dụng được credential quản trị.
3. Chạy get nodes. Lúc này chỉ thấy cp-01 là bình thường; CNI và worker chưa hoàn tất.
4. Chạy token create, gửi **nguyên lệnh join** cho mỗi bạn qua kênh riêng. Hai bạn thêm sudo ở đầu nếu cần và chạy trên worker tương ứng sau khi hoàn tất mục 6.
5. Trên cp-01 chạy `kubectl get nodes -o wide` lần nữa. Ghi đủ ba node xuất hiện. Chuyển sang mục 8 để làm mạng Pod và chuyển trạng thái về Ready.

Nếu init lỗi, giữ toàn bộ lỗi và xem bảng mục 18 trước khi chạy lại. Chỉ chạy init một lần thành công trên control plane của cụm.

**Chỉ SSH cp-01/Bash.** Pull image trước để tách lỗi Internet khỏi lỗi init. Dùng patch version trùng kubeadm:

```bash
export K8S_VERSION="$(kubeadm version -o short)"
sudo kubeadm config images pull --kubernetes-version="$K8S_VERSION"
sudo kubeadm init \
  --kubernetes-version="$K8S_VERSION" \
  --apiserver-advertise-address=10.20.0.10 \
  --pod-network-cidr=10.244.0.0/16 \
  --service-cidr=10.96.0.0/12 \
  --cri-socket=unix:///run/containerd/containerd.sock
mkdir -p "$HOME/.kube"
sudo install -m 600 -o "$(id -u)" -g "$(id -g)" /etc/kubernetes/admin.conf "$HOME/.kube/config"
kubectl get nodes -o wide
sudo kubeadm token create --ttl 2h --print-join-command
```

Lệnh cuối in token nhạy cảm. Gửi riêng cho hai bạn, họ chạy trên worker đã chuẩn hóa. Lệnh dạng sudo kubeadm join 10.20.0.10:6443 --token ... --discovery-token-ca-cert-hash sha256:... . Khi token hết hạn, tạo lại trên cp-01. Không chạy init trên worker.

Lúc chưa cài CNI, node có thể NotReady. Giữ taint control plane để workload được lập lịch trên worker. Kiểm tra bằng kubectl describe node cp-01. Với một control plane, mất cp-01 sẽ làm gián đoạn quản trị API; ghi rõ giới hạn này khi báo cáo.

**Bàn giao TV3** project/zone, CIDR Pod và Service, ba IP node, chế độ VXLAN và rule UDP 4789. TV3 áp Calico đã ghim version. Bạn hỗ trợ firewall và API, rồi nhận lại output get nodes/get pods. Nếu TV3 chưa sẵn sàng, bước 8 mô tả kết quả cấu hình cần thống nhất để bạn tiếp quản có kiểm soát.

## 8. Nhận hai worker và nghiệm thu Calico

### Thao tác 08 · Áp cấu hình mạng Pod và thử từ hai node

TV3 là người thực hiện bước cài Calico, dùng một phiên kubectl có quyền quản trị. Nếu bạn tiếp quản bước này, xác nhận TV3 chưa cài operator trước khi chạy. Cả hai dùng cùng release đã chốt. Trên cp-01:

```bash
export CALICO_VERSION='<vX.Y.Z-da-chot>'
mkdir -p "$HOME/nt132-config/calico"
cd "$HOME/nt132-config/calico"
curl -fL -o operator-crds.yaml "https://raw.githubusercontent.com/projectcalico/calico/$CALICO_VERSION/manifests/operator-crds.yaml"
curl -fL -o tigera-operator.yaml "https://raw.githubusercontent.com/projectcalico/calico/$CALICO_VERSION/manifests/tigera-operator.yaml"
kubectl apply --server-side -f operator-crds.yaml
kubectl apply -f tigera-operator.yaml
kubectl -n tigera-operator rollout status deployment/tigera-operator --timeout=180s
cat > installation.yaml <<'EOF'
apiVersion: operator.tigera.io/v1
kind: Installation
metadata:
  name: default
spec:
  calicoNetwork:
    bgp: Disabled
    ipPools:
      - blockSize: 26
        cidr: 10.244.0.0/16
        encapsulation: VXLAN
        natOutgoing: Enabled
        nodeSelector: all()
EOF
```

Khối cat đến EOF vừa tạo file installation.yaml trong thư mục hiện tại. Chạy cat installation.yaml để đọc lại CIDR và chế độ VXLAN. Nếu release đã chọn tổ chức manifest khác và curl trả 404, lấy đúng file từ trang hướng dẫn của release đó, kiểm tra file tải về trước khi apply. Áp file và theo dõi:

```bash
kubectl apply -f installation.yaml
kubectl get tigerastatus
kubectl get nodes -o wide
kubectl -n calico-system get pods -o wide
```

**Bạn vừa cài:** CNI để Pod giao tiếp xuyên worker và thực thi NetworkPolicy sau này. Nếu Typha xuất hiện, TV1 thêm rule từ node tới TCP 5473 theo cấu hình thực. Không dùng trạng thái Running của một Pod Calico làm kết luận cho cả mạng.

Sau khi ba node Ready, tạo một HTTP server thử trên wk-01 và một client thử trên wk-02. Đây là test trước khi áp policy ứng dụng do TV2 lựa chọn. Trên cp-01, điền image đã ghim của nhóm:

```bash
export HTTP_IMAGE='<image-nginx-tag-hoac-digest-da-chon>'
export CURL_IMAGE='<image-curl-tag-hoac-digest-da-chon>'
kubectl create namespace network-check
cat > cross-node.yaml <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: server
  namespace: network-check
  labels:
    app: test-server
spec:
  nodeSelector:
    kubernetes.io/hostname: wk-01
  containers:
    - name: http
      image: $HTTP_IMAGE
      ports:
        - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: server
  namespace: network-check
spec:
  selector:
    app: test-server
  ports:
    - port: 80
      targetPort: 80
---
apiVersion: v1
kind: Pod
metadata:
  name: client
  namespace: network-check
spec:
  nodeSelector:
    kubernetes.io/hostname: wk-02
  containers:
    - name: curl
      image: $CURL_IMAGE
      command: ["sh", "-c", "sleep 3600"]
EOF
kubectl apply -f cross-node.yaml
kubectl -n network-check wait --for=condition=Ready pod/server pod/client --timeout=180s
SERVER_IP=$(kubectl -n network-check get pod server -o jsonpath='{.status.podIP}')
kubectl -n network-check exec client -- curl -sS --max-time 10 -o /dev/null -w '%{http_code}\n' "http://$SERVER_IP"
kubectl -n network-check exec client -- curl -sS --max-time 10 -o /dev/null -w '%{http_code}\n' http://server
kubectl -n network-check get pods -o wide
```

Hai lượt HTTP phải trả 200, cột NODE phải chỉ hai worker khác nhau. Lưu output trước khi chạy `kubectl delete namespace network-check` để kết thúc bài thử. Nếu tên node thực khác, lấy từ get nodes và sửa nodeSelector trong file trước khi apply.

TV3 cài operator/CRD theo release Calico đã chọn rồi áp Installation. Đề nghị TV3 gửi file cuối cùng vào repo trước khi apply. Cấu hình cần có CIDR 10.244.0.0/16, encapsulation VXLAN, NAT outgoing bật và BGP tắt nếu chỉ dùng VXLAN. Tên field phải đúng CRD của release đang cài; TV3 đối chiếu bằng kubectl explain. Ví dụ phần Installation của Calico operator:

```yaml
apiVersion: operator.tigera.io/v1
kind: Installation
metadata:
  name: default
spec:
  calicoNetwork:
    bgp: Disabled
    ipPools:
      - blockSize: 26
        cidr: 10.244.0.0/16
        encapsulation: VXLAN
        natOutgoing: Enabled
        nodeSelector: all()
```

Sau khi cả hai worker join và CNI chạy, **cp-01/Bash**:

```bash
kubectl get nodes -o wide
kubectl get pods -A -o wide
kubectl -n kube-system rollout status deployment/coredns --timeout=180s
kubectl get tigerastatus
kubectl get events -A --sort-by=.lastTimestamp
```

Kỳ vọng cp-01, wk-01, wk-02 đều Ready; CoreDNS có replica Available; daemon Calico chạy trên node cần thiết. Nếu Calico dùng Typha, kiểm tra TCP 5473 từ node đến Typha theo deployment thực; TV1 tạo rule bổ sung đúng nguồn/đích khi TV3 xác nhận cần.

**Ca kiểm chứng do TV2/TV3 thực hiện.** Hai bạn đặt server trên wk-01, client trên wk-02. Họ phải đưa bạn bằng chứng cả IP Pod lẫn DNS Service đều gọi được, kèm dòng NODE từ get pods -o wide. Nếu chỉ test hai Pod trên cùng worker thì chưa đủ xác nhận VXLAN xuyên node. TV1 nhìn output, đối chiếu CIDR và timestamp rồi lưu NET01. [Calico operator](https://docs.tigera.io/calico/latest/getting-started/kubernetes/self-managed-onprem/onpremises)

## 9. Quản trị từ laptop và giữ thông tin truy cập riêng

### Thao tác 09 · Sắp xếp các cửa sổ terminal

Trên laptop mở bốn tab PowerShell và đặt tên dễ phân biệt. Tab **TUNNEL** chạy lệnh gcloud có -N -L ở dưới và giữ mở. Tab **RANCHER**, **ỨNG_DỤNG**, **KIALI** lần lượt SSH vào cp-01 bằng lệnh gcloud compute ssh bình thường, sau đó mỗi tab chạy đúng một lệnh port-forward khi dịch vụ tương ứng đã được cài. Dùng một tab **ADMIN** khác để chạy lệnh quản trị; không dùng tab đang giữ port-forward để gõ thêm lệnh.

**Kết quả cần thấy:** lệnh tunnel thường đứng chờ, còn port-forward in “Forwarding from 127.0.0.1…”. Đây là trạng thái đang phục vụ kết nối. Nhấn Ctrl+C chỉ khi muốn dừng đường truy cập đó.

Để tránh phải sao chép admin.conf sang ba laptop trong lượt đầu, bạn có thể thực hiện kubectl và Helm trên cp-01 qua SSH. Khi cần mở web trên Windows, ghép SSH local forwarding với kubectl port-forward đang chạy trên cp-01. API vẫn nằm ở IP riêng.

**Laptop/PowerShell, terminal A.** Truyền các cổng local qua SSH. Cổng 8443 sẽ dùng cho Rancher từ bước 11, 8080 cho ứng dụng do TV2 lựa chọn và 20001 cho Kiali:

```powershell
gcloud compute ssh cp-01 --zone=asia-southeast1-a --tunnel-through-iap -- -N -L 8443:127.0.0.1:8443 -L 8080:127.0.0.1:8080 -L 20001:127.0.0.1:20001
```

Để terminal này mở. Nếu bản gcloud Windows dùng SSH client với cú pháp khác, xem gcloud compute ssh --dry-run để nhận lệnh client thực; dùng OpenSSH đã cài và cùng ý nghĩa ba local forwarding. Khi một cổng đang bị ứng dụng khác chiếm, chọn cổng local khác và đổi URL tương ứng. Với Rancher, giữ URL server nội bộ 443, cổng trình duyệt ngoài 8443 chỉ là lối tunnel của bạn.

**Laptop/PowerShell, terminal B.** Mở SSH bình thường để chạy kubectl. Mỗi port-forward cần một terminal SSH còn sống. Khi laptop ngủ hoặc kết nối IAP đứt, cả tunnel và UI có thể dừng. Mở lại tunnel rồi port-forward; không cài lại chart vì lỗi này.

Nếu muốn dùng kubectl trực tiếp trên Windows, cài kubectl tương thích, tạo credential cá nhân và kubeconfig chứa CA của cụm. Mở local forwarding 16443:10.20.0.10:6443, cấu hình server=https://127.0.0.1:16443 và tls-server-name=10.20.0.10. Cấp RBAC cho danh tính đó trước khi thử. admin.conf có quyền cao, giữ trên máy quản trị trong bước khởi tạo.

## 10. Cài Helm và lưu cấu hình trước khi triển khai dashboard

### Thao tác 10 · Cài Helm trên control plane

Mở tab ADMIN, SSH cp-01. Chọn Helm version theo mục 3.2 rồi dán khối cài bên dưới. Sau khi checksum trả OK, tiếp tục tar/install. Helm version phải trả version đã chọn. Lệnh mkdir cuối tạo hai thư mục: nt132-config chứa cấu hình và nt132-evidence chứa kết quả. Những bước Helm kế tiếp chạy từ `$HOME/nt132-config`; dùng `pwd` để xác nhận trước khi tạo file.

**cp-01/Bash.** Chọn bản Helm phù hợp với chart Rancher đã duyệt. Ví dụ tải archive Linux amd64 từ trang release chính thức. Điền VERSION là số version có tiền tố v; checksum tải từ cùng release và phải khớp:

```bash
export HELM_VERSION='<vX.Y.Z>'
mkdir -p "$HOME/nt132-tools"
cd "$HOME/nt132-tools"
curl -fLO "https://get.helm.sh/helm-$HELM_VERSION-linux-amd64.tar.gz"
curl -fLO "https://get.helm.sh/helm-$HELM_VERSION-linux-amd64.tar.gz.sha256sum"
sha256sum -c "helm-$HELM_VERSION-linux-amd64.tar.gz.sha256sum"
tar -xzf "helm-$HELM_VERSION-linux-amd64.tar.gz"
sudo install -m 0755 linux-amd64/helm /usr/local/bin/helm
helm version
mkdir -p "$HOME/nt132-config/rancher" "$HOME/nt132-evidence"
cd "$HOME/nt132-config"
kubectl get nodes -o wide > "$HOME/nt132-evidence/nodes-before-dashboard.txt"
kubectl describe nodes > "$HOME/nt132-evidence/node-resources-before-dashboard.txt"
```

Nếu checksum báo lỗi, xử lý download trước khi install. Xem Allocatable và Allocated resources ở describe nodes; dự trù Rancher, ingress quản trị, Istio, Prometheus/Kiali và ứng dụng do TV2 lựa chọn trên hai worker. Nếu Pending vì thiếu tài nguyên, kiểm tra requests rồi nâng worker theo ngân sách, từng máy một sau khi drain có kiểm soát và workload có khả năng chạy nơi khác.

## 11. Cài Rancher với hostname và TLS hoạt động trong cluster

Thiết kế ở đây dùng Traefik làm ingress quản trị riêng, Service ClusterIP, TLS bằng CA riêng của lab và hostname rancher.nt132.test. Laptop ánh xạ tên này về localhost để đi tunnel; CoreDNS ánh xạ cùng tên tới Service Traefik để agent truy cập qua mạng cluster. Cùng một hostname có hai đường truy cập phù hợp từng phía.

### 11.1. Thêm repo và kiểm tra chart trước khi install

**Thao tác 11A.** Trên tab ADMIN của cp-01, chạy `cd "$HOME/nt132-config"` rồi khối helm repo/search. Trong danh sách chart, lấy số VERSION đã đối chiếu tương thích, đặt vào TRAEFIK_CHART và RANCHER_CHART. Chạy helm show values để lưu cấu hình mặc định. Tiếp theo dán toàn bộ khối `cat > rancher/traefik-values.yaml` đến dòng EOF; thao tác này tự tạo file YAML, bạn không cần mở editor. Chạy helm template, đọc file rendered rồi chạy helm upgrade --install. Nếu get svc trả tên khác ví dụ trong hướng dẫn, chép tên thật và dùng nhất quán ở DNS và port-forward.

**cp-01/Bash**:

```bash
helm repo add traefik https://traefik.github.io/charts
helm repo add rancher-stable https://releases.rancher.com/server-charts/stable
helm repo update
helm search repo traefik/traefik --versions | head -15
helm search repo rancher-stable/rancher --versions | head -15
export TRAEFIK_CHART='<chart-version-da-chon>'
export RANCHER_CHART='<chart-version-da-chon>'
helm show values traefik/traefik --version "$TRAEFIK_CHART" > rancher/traefik-defaults.yaml
helm show values rancher-stable/rancher --version "$RANCHER_CHART" > rancher/rancher-defaults.yaml
```

Đối chiếu key ingressClass, service.type, ports.websecure.tls và providers.kubernetesIngress với file defaults của chart Traefik thực. Ví dụ values dưới dùng ingress class riêng rancher-traefik. Render trước khi install và kiểm tra Service thực là ClusterIP, có cổng 443 và IngressClass đúng tên.

```bash
cat > rancher/traefik-values.yaml <<'EOF'
service:
  type: ClusterIP
ingressClass:
  enabled: true
  isDefaultClass: false
  name: rancher-traefik
providers:
  kubernetesIngress:
    enabled: true
    ingressClass: rancher-traefik
ports:
  websecure:
    tls:
      enabled: true
EOF
helm template rancher-ingress traefik/traefik \
  --namespace rancher-ingress --version "$TRAEFIK_CHART" \
  -f rancher/traefik-values.yaml > rancher/traefik-rendered.yaml
helm upgrade --install rancher-ingress traefik/traefik \
  --namespace rancher-ingress --create-namespace --version "$TRAEFIK_CHART" \
  -f rancher/traefik-values.yaml --wait --timeout=5m
kubectl -n rancher-ingress get deploy,svc,pods
kubectl get ingressclass
```

Nếu tên Service khác rancher-ingress-traefik, ghi tên thật vào bước DNS bên dưới và lệnh port-forward. Các chart khác version có thể thay default resource name. [Traefik trên Kubernetes](https://doc.traefik.io/traefik/setup/kubernetes/)

### 11.2. Cấp chứng chỉ cho hostname lab

**Thao tác 11B.** Trong tab ADMIN, dán từng khối openssl bên dưới theo thứ tự. Lệnh đầu tạo CA của lab; lệnh tiếp tạo key và CSR cho Rancher; lệnh x509 ký chứng chỉ máy chủ. Chỉ tạo Secret sau khi openssl verify trả OK. Các file ca.key và tls.key nằm trên cp-01 trong thư mục riêng; ca.crt là chứng chỉ công khai bạn sẽ tải về Windows.

**cp-01/Bash.** Lưu private key ngoài thư mục config đưa vào Git. Chứng chỉ lab có thời hạn 90 ngày. Bạn chọn own-certificate mode của Rancher để chart đọc Secret TLS.

```bash
mkdir -p "$HOME/.nt132-private/tls"
chmod 700 "$HOME/.nt132-private" "$HOME/.nt132-private/tls"
cd "$HOME/.nt132-private/tls"
umask 077
openssl req -x509 -newkey rsa:3072 -sha256 -nodes -days 90 \
  -keyout ca.key -out ca.crt -subj "/CN=NT132 Lab CA" \
  -addext "basicConstraints=critical,CA:TRUE" \
  -addext "keyUsage=critical,keyCertSign,cRLSign"
openssl req -newkey rsa:2048 -nodes -keyout tls.key -out rancher.csr \
  -subj "/CN=rancher.nt132.test"
cat > server.ext <<'EOF'
subjectAltName=DNS:rancher.nt132.test
basicConstraints=critical,CA:FALSE
keyUsage=critical,digitalSignature,keyEncipherment
extendedKeyUsage=serverAuth
EOF
openssl x509 -req -in rancher.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
  -out tls.crt -days 90 -sha256 -extfile server.ext
openssl verify -CAfile ca.crt tls.crt
openssl x509 -in tls.crt -noout -dates -ext subjectAltName
kubectl create namespace cattle-system
kubectl -n cattle-system create secret tls tls-rancher-ingress \
  --cert=tls.crt --key=tls.key
kubectl -n cattle-system create secret generic tls-ca --from-file=cacerts.pem=ca.crt
```

Kỳ vọng verify trả OK và SAN chứa đúng hostname. Nếu namespace/Secret đã tồn tại, đọc hiện trạng và cập nhật có chủ đích; không tạo CA mới mỗi lần thử install. Giữ ca.key/tls.key riêng, copy public ca.crt sang laptop theo bước 11.5.

### 11.3. DNS nội bộ cho agent

**Thao tác 11C.** Trong tab ADMIN, đặt `export KUBE_EDITOR=nano` rồi chạy kubectl edit ở dưới. Tìm dòng `kubernetes cluster.local` trong Corefile, chèn khối rewrite ngay trước plugin đó ở cùng mức thụt lề nội dung Corefile. Dùng đúng tên Service Traefik ở bước 11A. Nhấn Ctrl+O, Enter, Ctrl+X. Chờ thông báo ConfigMap edited rồi đọc log CoreDNS. Nếu có parse error, chạy `kubectl apply -f "$HOME/nt132-evidence/coredns-before-rancher.yaml"` và xác nhận DNS phục hồi trước khi thử lại.

**cp-01/Bash.** Sao lưu CoreDNS trước khi chỉnh:

```bash
kubectl -n kube-system get configmap coredns -o yaml > "$HOME/nt132-evidence/coredns-before-rancher.yaml"
kubectl -n kube-system edit configmap coredns
```

Trong khối .:53 của Corefile, trước plugin kubernetes, thêm rewrite với tên Service thực tìm ở bước 11.1:

```text
rewrite stop {
    name exact rancher.nt132.test rancher-ingress-traefik.rancher-ingress.svc.cluster.local
    answer auto
}
```

Không sửa các plugin khác. Cluster domain ở đây theo kubeadm mặc định cluster.local. Sau khi lưu, đợi CoreDNS reload; kiểm tra log không có parse error. Chạy Pod DNS tạm bằng image có nslookup đã ghim, hoặc dùng Pod kiểm thử TV3 đã chuẩn bị:

```bash
kubectl -n kube-system logs deployment/coredns --tail=50
kubectl -n rancher-ingress get svc
```

Từ Pod, nslookup rancher.nt132.test phải ra ClusterIP của ingress quản trị. DNS trên cp-01 hệ điều hành có thể khác DNS trong Pod; phải kiểm tra từ Pod. Nếu mất DNS do sửa Corefile, apply lại file backup, xác nhận CoreDNS phục hồi rồi sửa lại một lần có kiểm tra. Đây là bước quyết định để agent gọi server URL được khi laptop tắt.

### 11.4. Deploy Rancher

**Thao tác 11D.** Quay về `$HOME/nt132-config`, kiểm tra `printf '%s\n' "$RANCHER_CHART"` có đúng số phiên bản. Nếu biến trống do đổi phiên SSH, khai báo lại đúng bản đã chọn. Dán khối tạo rancher-values.yaml, chạy render rồi install. Đợi rollout hoàn tất và kiểm tra Ingress có host/TLS/class đúng trước khi mở trình duyệt.

**cp-01/Bash**:

```bash
cd "$HOME/nt132-config"
cat > rancher/rancher-values.yaml <<'EOF'
hostname: rancher.nt132.test
replicas: 1
privateCA: true
ingress:
  ingressClassName: rancher-traefik
  tls:
    source: secret
  extraAnnotations:
    traefik.ingress.kubernetes.io/router.entrypoints: websecure
    traefik.ingress.kubernetes.io/router.tls: "true"
EOF
helm template rancher rancher-stable/rancher \
  --namespace cattle-system --version "$RANCHER_CHART" \
  -f rancher/rancher-values.yaml > rancher/rancher-rendered.yaml
helm upgrade --install rancher rancher-stable/rancher \
  --namespace cattle-system --version "$RANCHER_CHART" \
  -f rancher/rancher-values.yaml --wait --timeout=10m
kubectl -n cattle-system rollout status deployment/rancher --timeout=300s
kubectl -n cattle-system get ingress,svc,pods
kubectl -n cattle-system get ingress rancher -o yaml
```

Kiểm tra Ingress có ingressClassName rancher-traefik, host rancher.nt132.test, tls.secretName tls-rancher-ingress và backend rancher. Nếu chart dùng key khác, chỉnh values theo defaults đã tải và render lại. Private CA phải được Rancher đọc từ tls-ca để agent có thể xác minh TLS. Own-certificate mode dùng Secret đã tạo. [Cài Rancher với chứng chỉ riêng](https://ranchermanager.docs.rancher.com/getting-started/installation-and-upgrade/install-upgrade-on-a-kubernetes-cluster/) · [Chart options](https://ranchermanager.docs.rancher.com/getting-started/installation-and-upgrade/installation-references/helm-chart-options)

### 11.5. Mở UI trên Windows

**Thao tác 11E · Lấy CA công khai về laptop.**

Trên cp-01 chạy `realpath "$HOME/.nt132-private/tls/ca.crt"`, chép nguyên đường dẫn in ra. Trong PowerShell thường trên laptop:

```powershell
$LabFolder = Join-Path $env:USERPROFILE 'Documents\NT132-TV1'
$RemoteCa = '/home/DIEN_USER_LINUX/.nt132-private/tls/ca.crt'
$CaPath = Join-Path $LabFolder 'ca.crt'
gcloud compute scp "cp-01:$RemoteCa" "$CaPath" --zone=asia-southeast1-a --tunnel-through-iap
Get-FileHash -Algorithm SHA256 -LiteralPath $CaPath
```

Thay $RemoteCa bằng đường dẫn vừa lấy. Trên cp-01 chạy `sha256sum "$HOME/.nt132-private/tls/ca.crt"`, đối chiếu hash hai bên. Sau khi khớp, import:

```powershell
$LabCa = Import-Certificate -FilePath $CaPath -CertStoreLocation Cert:\CurrentUser\Root
$LabCa | Select-Object Subject,Thumbprint,NotAfter
```

Lưu Thumbprint để cuối lab gỡ đúng CA đã thêm. Đóng rồi mở lại browser để nhận trust store mới.

**Thao tác 11F · Thêm hostname trên Windows.**

Mở Start, gõ Notepad, chọn **Run as administrator**. Trong Notepad chọn File → Open, đi đến `C:\Windows\System32\drivers\etc`, đổi bộ lọc sang All Files rồi mở hosts. Thêm dòng `127.0.0.1 rancher.nt132.test` nếu chưa có. Lưu file với đúng tên hosts, không thêm đuôi .txt. Trên PowerShell chạy `ipconfig /flushdns`.

**Thao tác 11G · Mở kết nối và kiểm tra.**

Tab TUNNEL giữ lệnh mục 9. Tab RANCHER SSH cp-01 và chạy lệnh port-forward bên dưới. Trên một PowerShell khác chạy:

```powershell
curl.exe --cacert "$CaPath" https://rancher.nt132.test:8443/ping
```

Kết quả mong đợi là pong và không có lỗi xác minh chứng chỉ. Nếu không kết nối được, kiểm tra cả tunnel lẫn port-forward. Nếu lỗi hostname/cert, kiểm tra hosts, SAN, CA và certificate mà ingress đang phục vụ. Sau đó mở browser để đăng nhập theo phần dưới.

**cp-01/Bash, terminal đang giữ riêng**:

```bash
kubectl -n rancher-ingress port-forward svc/rancher-ingress-traefik 8443:443 --address=127.0.0.1
```

Mở tunnel của mục 9 trên Windows. Copy public CA bằng gcloud compute scp từ đường dẫn thực trên cp-01, ví dụ sau khi dùng pwd để xác nhận home user. Import ca.crt vào Trusted Root Certification Authorities của Current User bằng Certificate Import Wizard; xác nhận đây là CA do chính bạn vừa tạo. Thêm một dòng vào Windows hosts tại C:\Windows\System32\drivers\etc\hosts bằng editor chạy quyền quản trị:

```text
127.0.0.1 rancher.nt132.test
```

Browser mở **https://rancher.nt132.test:8443**. Hostname phải khớp SAN, CA phải được browser tin cậy. Trong initial setup, Server URL dành cho agent là **https://rancher.nt132.test** qua cổng 443 nội bộ. Nếu UI tự đề xuất URL có :8443, sửa về URL 443 nội bộ. Agent dùng CoreDNS đến ingress Service 443, còn browser dùng tunnel 8443.

Lấy bootstrap password bằng lệnh Rancher hiển thị sau install hoặc đọc Secret trên cp-01:

```bash
kubectl -n cattle-system get secret bootstrap-secret -o jsonpath='{.data.bootstrapPassword}' | base64 -d
printf '\n'
```

Đặt mật khẩu admin riêng. Không đưa mật khẩu vào ảnh báo cáo. Kiểm tra local cluster và ba node. Nếu UI có nhưng agent disconnected, kiểm tra DNS trong Pod, server-url, CA checksum và log agent trước khi sửa RBAC.

## 12. Kiểm tra Rancher đủ điều kiện báo cáo

### Thao tác 12 · Kiểm tra từ Pod và từ tài khoản trình chiếu

**Trên cp-01, tab ADMIN**, tạo một client kiểm tra DNS/TLS của Rancher. Chọn image curl có shell và chứng chỉ mount đúng đường. Image phải được ghim tag/digest đã chốt; lệnh chỉ tải image public của nhóm đã chọn.

```bash
export CURL_IMAGE='<image-curl-da-chon>'
kubectl create namespace admin-check
kubectl -n admin-check create configmap lab-ca --from-file=ca.crt="$HOME/.nt132-private/tls/ca.crt"
cat > "$HOME/nt132-config/rancher/rancher-check.yaml" <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: rancher-check
  namespace: admin-check
spec:
  restartPolicy: Never
  containers:
    - name: curl
      image: $CURL_IMAGE
      command: ["sh", "-c", "sleep 3600"]
      volumeMounts:
        - name: lab-ca
          mountPath: /lab-ca
          readOnly: true
  volumes:
    - name: lab-ca
      configMap:
        name: lab-ca
EOF
kubectl apply -f "$HOME/nt132-config/rancher/rancher-check.yaml"
kubectl -n admin-check wait --for=condition=Ready pod/rancher-check --timeout=180s
kubectl -n admin-check exec rancher-check -- curl -v --cacert /lab-ca/ca.crt --max-time 10 https://rancher.nt132.test/ping
```

Lưu output có xác minh TLS thành công và pong. Bài này đi qua DNS/Service nội bộ, độc lập với tunnel của laptop. Sau khi lưu kết quả, chạy `kubectl delete namespace admin-check` để xóa tài nguyên thử.

**Trong Rancher UI**, dùng menu Users & Authentication → Users (tên menu tùy bản), tạo local user dùng để trình chiếu. Vào Cluster Management → local → Members, thêm user bằng role chỉ đọc có sẵn của phiên bản hoặc role tùy chỉnh chỉ cho get/list/watch tài nguyên cần xem. Nếu tài khoản viewer thiếu quyền xem node hoặc namespace, đọc resource bị Forbidden và cấp đúng quyền đọc cần thiết. Đăng xuất admin, đăng nhập viewer bằng cửa sổ browser riêng. Mở Nodes, Workloads và Services để thử. Thử quyền sửa bằng kiểm tra RBAC hoặc thao tác trên workload thử đã chuẩn bị, tránh thay đổi ứng dụng đang báo cáo.

Sau khi login, mở Cluster Management rồi chọn local. Kiểm tra ba node có tên/IP đúng inventory. Trong Cluster Explorer chọn namespace APP_NAMESPACE khi TV2 đã deploy, mở Workloads và Service TARGET_SERVICE. Đọc selector, cổng và Pod đích rồi đối chiếu CLI. Một ảnh UI riêng lẻ cần kèm tên cluster/namespace và giờ để tránh dùng nhầm môi trường.

Tạo user trình chiếu với quyền chỉ xem phạm vi cần thiết, đăng nhập lại bằng cửa sổ riêng. Thử xem node/Deployment/Service rồi kiểm tra user không có quyền sửa workload. Admin dùng cho vận hành; user viewer dùng khi mở trước lớp. Lưu ảnh UI cùng output:

```bash
kubectl get nodes -o wide
kubectl -n APP_NAMESPACE get deploy,pods,svc -o wide
kubectl -n APP_NAMESPACE get endpointslice -l kubernetes.io/service-name=TARGET_SERVICE -o wide
kubectl -n cattle-system get pods
```

Từ Pod thử có curl, gọi https://rancher.nt132.test/ping với CA lab đã mount vào Pod để xác minh DNS, TLS và HTTP từ trong cluster. Có thể dùng image curl đã ghim của nhóm và ConfigMap chứa **public** ca.crt. Kỳ vọng TLS verify thành công và /ping trả pong. Nếu chỉ browser truy cập được nhưng Pod không gọi được, kiểm tra CoreDNS rewrite và đường Service ingress. Đây là lý do phải thử cả browser và client trong cluster.

## 13. Nhận ứng dụng do TV2 lựa chọn và Istio từ TV2/TV3

### Thao tác 13 · Mở ứng dụng mẫu và quan sát

Nhận xác nhận hai bạn đã deploy xong; chạy khối get ở dưới để xem tài nguyên thật. Tab ỨNG_DỤNG SSH cp-01, chạy port-forward gateway. Tab KIALI SSH cp-01, chạy port-forward kiali. Giữ tab TUNNEL mở. Trên browser mở URL localhost ở dưới. Kiali chọn namespace APP_NAMESPACE và time range 5 phút. Trên PowerShell ADMIN của Windows chạy vòng lặp 120 request. Chờ dữ liệu được thu thập rồi chỉ cạnh CALLER_SERVICE → TARGET_SERVICE. Nếu chưa có app, gửi output get deploy cho TV2; nếu Istiod/gateway chưa Ready, gửi TV3. Bước này kiểm tra phần hai bạn đã bàn giao.

Yêu cầu TV3 bàn giao version Istio, trạng thái Istiod/gateway, Prometheus và Kiali. TV2 bàn giao namespace APP_NAMESPACE, deployment CALLER_DEPLOYMENT, Service TARGET_SERVICE, route /APP_PATH và cổng gateway. TV1 tự kiểm tra:

```bash
kubectl -n istio-system get deploy,svc,pods -o wide
kubectl -n APP_NAMESPACE get deploy,pods,svc -o wide
kubectl -n APP_NAMESPACE get gateway,virtualservice
kubectl -n APP_NAMESPACE get svc TARGET_SERVICE -o yaml
kubectl -n APP_NAMESPACE get endpointslice -l kubernetes.io/service-name=TARGET_SERVICE -o yaml
```

Mở **cp-01/Bash, mỗi lệnh một terminal**:

```bash
kubectl -n istio-system port-forward svc/istio-ingressgateway 8080:80 --address=127.0.0.1
kubectl -n istio-system port-forward svc/kiali 20001:20001 --address=127.0.0.1
```

Với tunnel mục 9 còn mở, Windows mở http://127.0.0.1:8080/APP_PATH và http://127.0.0.1:20001/kiali. Trang phải trả nội dung đúng theo bàn giao. TV3 chọn namespace APP_NAMESPACE trên Kiali. Tạo lượt gọi mới trên **PowerShell**:

```powershell
1..120 | ForEach-Object {
    curl.exe -sS --max-time 5 -o NUL -w "%{http_code}\n" http://127.0.0.1:8080/APP_PATH
    Start-Sleep -Seconds 1
}
```

Đến đây bạn đã có dashboard và ứng dụng chạy trên cloud để báo cáo. URL localhost đi qua đường quản trị. Thử ngoài VPC ở mục 14 là ca nghiệm thu riêng.

## 14. Tạo Google Cloud Load Balancer trỏ vào NodePort

### 14.1. Kiểm tra NodePort trước khi tạo backend

**Thao tác 14A.** Trên cp-01, chạy đúng ba lệnh kiểm tra bên dưới. Mở hoặc đọc file HTML trả về, đối chiếu có nội dung ứng dụng. Gửi IP worker bị lỗi và output curl cho TV2/TV3. Khi cả hai worker đã phục vụ request, chuyển Cloud Shell ở bước 14B.

**cp-01/Bash.** TV2 cấu hình Service ingress gateway thành NodePort HTTP 30080 và externalTrafficPolicy=Cluster. Xem file thật trước, giữ targetPort của gateway đúng version.

```bash
kubectl -n istio-system get svc istio-ingressgateway -o yaml
curl -sv --max-time 10 http://10.20.0.11:30080/APP_PATH -o /tmp/nt132-w1.html
curl -sv --max-time 10 http://10.20.0.12:30080/APP_PATH -o /tmp/nt132-w2.html
kubectl -n istio-system get endpointslice -l kubernetes.io/service-name=istio-ingressgateway
```

Hai request phải vào được website. Với externalTrafficPolicy=Cluster, worker có thể chuyển đến gateway Pod trên worker khác. Nếu đổi thành Local, node không chứa gateway có thể không phục vụ được; lúc đó phải đổi chiến lược gateway placement và health check. Giữ Cluster theo thiết kế lab.

### 14.2. Tạo tài nguyên LB

**Thao tác 14B.** Cloud Shell mở trong đúng project, nạp lại REGION/ZONE. Chạy lần lượt firewall → instance group → thêm worker → IP → health check → backend → thêm group → forwarding rule. Sau mỗi lệnh kiểm tra tên resource vừa tạo. Dùng get-health cuối khối; đợi hai backend có healthState HEALTHY. Vào Network services → Load balancing trong Console, tìm backend/forwarding rule theo tên nt132 để đối chiếu. Chép IP frontend trả về từ addresses describe sang PowerShell ở bước 14C.

**Cloud Shell/Bash**, nạp lại PROJECT_ID, REGION, ZONE từ mục 4 nếu terminal mới. Rule dưới mở TCP 30080 cho người dùng Internet và probe để website demo public. Đây là cổng ứng dụng, tách khỏi các rule quản trị đã giới hạn nguồn. Nếu nhóm cần giới hạn IP người xem, thay rule bằng nguồn client đã duyệt cộng dải health checker theo tài liệu GCP đúng loại LB.

```bash
gcloud compute firewall-rules create nt132-public-web \
  --network=nt132-vpc --direction=INGRESS --action=ALLOW \
  --rules=tcp:30080 --source-ranges=0.0.0.0/0 --target-tags=nt132-worker
gcloud compute instance-groups unmanaged create nt132-workers --zone="$ZONE"
gcloud compute instance-groups unmanaged add-instances nt132-workers \
  --zone="$ZONE" --instances=wk-01,wk-02
gcloud compute addresses create nt132-web-ip --region="$REGION"
gcloud compute health-checks create tcp nt132-web-hc \
  --region="$REGION" --port=30080
gcloud compute backend-services create nt132-web-backend \
  --region="$REGION" --load-balancing-scheme=EXTERNAL --protocol=TCP \
  --health-checks=nt132-web-hc --health-checks-region="$REGION"
gcloud compute backend-services add-backend nt132-web-backend \
  --region="$REGION" --instance-group=nt132-workers --instance-group-zone="$ZONE"
gcloud compute forwarding-rules create nt132-web-forward \
  --region="$REGION" --load-balancing-scheme=EXTERNAL \
  --ports=30080 --address=nt132-web-ip --backend-service=nt132-web-backend
gcloud compute backend-services get-health nt132-web-backend --region="$REGION"
gcloud compute addresses describe nt132-web-ip --region="$REGION" --format='value(address)'
```

Chờ backend chuyển healthy rồi thử URL. Với passthrough LB, cổng vẫn là 30080 khi tới VM; VM nhận gói có IP đích frontend. Giữ Google guest agent của image GCE hoạt động để cấu hình route frontend phù hợp. Nếu NodePort bằng IP worker chạy nhưng VIP không chạy, kiểm tra guest agent/local route và kube-proxy xử lý VIP, bên cạnh frontend và firewall. TCP health check qua IP node vẫn có thể healthy trong trường hợp đường VIP có lỗi. [GCP backend-service-based Network Load Balancer](https://cloud.google.com/load-balancing/docs/network/setting-up-network-backend-service)

### 14.3. Kiểm tra từ ngoài cụm

**Thao tác 14C.** Điền $WebIp trên Windows bằng IP frontend vừa tạo. Chạy curl ở dưới rồi mở cùng URL trong browser. Gửi URL cho TV3 để bạn ấy thử từ mạng ngoài VPC. Lưu URL, giờ thử, ảnh trả nội dung đúng và output get-health. Nếu localhost qua tunnel chạy mà URL public không chạy, dùng bảng mục 18 để kiểm tra riêng chặng LB/NodePort.

**Laptop/PowerShell.** Điền IP nhận được từ describe:

```powershell
$WebIp = '<IP-frontend>'
curl.exe -v --max-time 10 "http://$($WebIp):30080/APP_PATH"
```

Mở cùng URL bằng browser. Yêu cầu TV3 thử từ mạng khác; ghi HTTP status, ảnh trang trả nội dung đúng, giờ thử và IP frontend. Trong Kiali chọn cửa sổ tương ứng để thấy request mới. Lưu ba bằng chứng cạnh nhau: forwarding rule chứa IP/cổng, get-health có hai backend, browser ngoài VPC thấy trang.

**Cách giải thích với thầy.** Load balancer đưa kết nối tới worker; Service NodePort chọn gateway endpoint; Envoy gateway xử lý route ứng dụng; ENTRY_SERVICE gọi các Service nội bộ để lấy thông tin. K8s Service của gateway vẫn là NodePort. Tài nguyên LB của cloud được nhóm tự tạo và nối vào cổng này.

## 15. Các bài thực hành Service bạn phải tự chạy được

### 15.1. So tên, selector, endpoint và Pod

**cp-01/Bash**:

```bash
kubectl -n APP_NAMESPACE get svc TARGET_SERVICE -o yaml
kubectl -n APP_NAMESPACE get pods -l app=TARGET_LABEL -o wide
kubectl -n APP_NAMESPACE get endpointslice -l kubernetes.io/service-name=TARGET_SERVICE -o yaml
```

Đọc spec.selector app=TARGET_LABEL, so với metadata.labels của Pod. Đọc port=SERVICE_PORT và targetPort; so endpoint port và địa chỉ Pod. EndpointSlice có targetRef và điều kiện ready. ClusterIP là địa chỉ frontend nội bộ ổn định trong vòng đời Service. Khi Pod đổi, endpoint đổi theo tình trạng backend; tên Service giúp client tiếp tục gọi.

TV2 thay đúng một Pod do Deployment quản lý trong phiên thử. Bạn ghi UID cũ/mới, thời điểm Pod mới Ready và kết quả gọi lại. Một replica có thể gián đoạn lúc thay Pod. Cùng Pod IP không đảm bảo cùng Pod; UID là bằng chứng phân biệt.

### 15.2. Sửa một Service thử có selector sai

TV3 tạo Service service-selector-test trong APP_NAMESPACE với selector không khớp. Bạn nhận tên resource và triệu chứng, chạy get svc/get endpointslice để nhận ra thiếu endpoint. Sửa **file thử** về selector app=TARGET_LABEL, apply đúng file đó, đợi endpoint Ready rồi nhờ TV2 gọi lại từ Pod CALLER_SERVICE có quyền. Ghi trạng thái trước/sau và xóa riêng Service thử sau khi bàn giao.

Nếu có EndpointSlice nhưng GET vẫn lỗi, chuyển sang kiểm tra port, readiness, policy và source identity. DNS phân giải được chỉ xác nhận tên đã có câu trả lời. Kiali không tự chứng minh request có quyền; cần mã HTTP và log của lớp đang thử.

### 15.3. Nhận kết quả Istio và NetworkPolicy

Trước khi thử, hỏi hai bạn đã bật policy nào. Nhận tên Pod nguồn, ServiceAccount, đường dẫn, config mTLS và lệnh curl trong Pod. Thực hiện bốn lượt theo thứ tự:

| Lượt | Cấu hình | CALLER_SERVICE → TARGET_SERVICE | ENTRY_SERVICE → TARGET_SERVICE trực tiếp | Bạn lưu gì |
|---|---|---|---|---|
| 1 | STRICT, chưa hạn chế hai nguồn | 200 | 200 | Endpoint tồn tại, nguồn/đích, timestamp |
| 2 | Chỉ thêm AuthorizationPolicy của TV2 | 200 | 403 | Log Envoy đích ghi từ chối RBAC |
| 3 | Bỏ AuthorizationPolicy, phục hồi lượt 1 rồi chỉ bật NetworkPolicy của TV3 | Thành công | Lỗi kết nối/upstream | DNS vẫn phân giải; kết quả khi gỡ luật phục hồi |
| 4 | Bật cả hai | Thành công | Bị chặn | Trang public vẫn trả nội dung đúng qua CALLER_SERVICE |

Giữ timeout hữu hạn. Nếu nguồn dùng proxy, lỗi upstream do NetworkPolicy có thể thành HTTP 503. Kết luận dựa vào đối chứng và lớp vừa thay đổi, không dựa vào một mã lỗi duy nhất. Viết SEC04 là kết quả bạn trực tiếp kiểm tra.

## 16. Lịch thực hiện cá nhân và kịch bản báo cáo

Dùng Ngày 1–5 tương đối theo ngày bạn bắt đầu. Nếu bắt đầu 03/11, ngày 5 là 07/11; nếu lịch hẹn thầy đã cố định 06/11, hoàn thành phần chuẩn bị và VM ngay ngày đầu, dành phần LB cho tuần sau như plan. Ghi lịch thật trong nhật ký và báo rõ mốc.

| Mốc | Việc của bạn | Việc cần hai bạn bàn giao | Bằng chứng |
|---|---|---|---|
| Ngày 1 | Project, IAM, VPC, firewall, VM, runtime cp-01 | OS/runtime worker và bảng phiên bản | Inventory, ba lần SSH, output version |
| Ngày 2 | Init, cấp join, kiểm tra control plane | Worker join, Calico, thử mạng xuyên worker | Ba node Ready, DNS/HTTP liên node |
| Ngày 3 | Helm, Traefik, CA/TLS, CoreDNS và Rancher | Istiod/gateway Ready, ứng dụng do TV2 lựa chọn trả nội dung đúng | Rancher đăng nhập và Pod nội bộ gọi server URL được |
| Ngày 4 | User viewer, mở lại từ laptop trình chiếu | Kiali có graph, bài thay Pod | Dashboard, endpoint trước/sau, log request |
| Ngày 5 | Diễn tập và báo cáo | Hai bạn thực hiện đúng phần mình | Video/ảnh ghi ngày, commit, danh sách việc còn lại |
| Tuần 2 | LB, public IP, Rancher hoàn thiện | NodePort trên hai worker đạt | PUB01, ADM01 |
| Tuần 3–4 | Chạy ca đối chứng, tích hợp và tiếp quản bài sửa Service | Manifest/ca thử policy và selector | SEC04, SVC04 và runbook có người kiểm tra |

**Phần nói của bạn trong 2 phút đầu.** Mở ba VM, chỉ IP riêng cp-01/wk-01/wk-02. Mở Rancher local cluster và khớp ba node. Chọn một Pod thuộc Service TARGET_SERVICE, đọc trường Node rồi đối chiếu với VM. Chuyển sang Service TARGET_SERVICE và hỏi TV2 trình bày vì sao tên Service vẫn dùng được khi Pod thay đổi. Giữ phần cloud LB cho buổi đã có URL public.

**Trước báo cáo 30 phút.** Kiểm tra project/context, tunnel, CA chưa hết hạn và tài khoản viewer. Mở sẵn Rancher, ứng dụng do TV2 lựa chọn và Kiali. TV3 sinh traffic mới. Xác nhận trang trả nội dung đúng và cửa sổ metrics đúng giờ. Nếu dùng bản quay vì mất mạng phòng học, ghi thời điểm bản quay thay vì mô tả là lượt chạy trực tiếp.

## 17. Vận hành hằng ngày, sao lưu và phục hồi

### 17.1. Khi bắt đầu một buổi làm

Trên cp-01 chạy get nodes, get pods -A, get events và df -h. Kiểm tra Pod CrashLoopBackOff, Pending, OOMKilled và số restart tăng so với buổi trước. Xem describe của resource có vấn đề trước khi thay config. Trên Cloud Console kiểm tra VM đang Running và thông số billing theo project.

```bash
kubectl get nodes -o wide
kubectl get pods -A -o wide
kubectl get events -A --sort-by=.lastTimestamp
df -h
free -h
sudo systemctl is-active containerd kubelet
```

Trước thay firewall, lấy describe của rule cần đổi. Trước sửa CoreDNS, export ConfigMap. Trước sửa chart, lưu helm get values và helm get manifest vào thư mục riêng, vì bản render có thể chứa Secret. Lưu evidence đã loại bỏ thông tin nhạy cảm vào Git; file có credential giữ trong nơi lưu riêng.

### 17.2. Những thứ cần backup

| Loại | Nội dung | Cách kiểm tra backup hữu ích |
|---|---|---|
| Cấu hình chia sẻ | Phiên bản, inventory, manifest ứng dụng, Service/policy, Helm values đã loại credential | Một bạn khác đọc được thứ tự apply và tìm đúng tài nguyên thật |
| Control plane | Snapshot etcd và cấu hình kubeadm/PKI cần thiết | Xác minh snapshot bằng tool đúng version, thử restore trên môi trường riêng theo tài liệu kubeadm/etcd |
| TLS/Rancher | CA private key, server key/cert, thông tin đăng nhập và cấu hình URL | Chứng chỉ còn hạn, CA/hostname khớp, có người được phép mở kho backup |
| Cloud | Mô tả VM, disk, firewall, LB, group, address | Dựng lại được tên/region/port và biết IP nào đang được dành |
| Evidence | Log test, ảnh có thời điểm, video | Mở được từ laptop ngay cả khi VM đã tắt |

**Snapshot etcd.** Trên cp-01, đọc /etc/kubernetes/manifests/etcd.yaml để lấy image version, endpoint, đường chứng chỉ và data-dir thực. Cài etcdctl/etcdutl tương thích từ release chính thức. Ví dụ các đường mặc định của kubeadm:

```bash
sudo mkdir -p /var/backups/nt132
sudo env ETCDCTL_API=3 etcdctl \
  --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/healthcheck-client.crt \
  --key=/etc/kubernetes/pki/etcd/healthcheck-client.key \
  snapshot save /var/backups/nt132/etcd-snapshot.db
sudo etcdutl snapshot status /var/backups/nt132/etcd-snapshot.db --write-out=table
sudo chmod 600 /var/backups/nt132/etcd-snapshot.db
```

Dùng tên theo ngày khi giữ nhiều phiên bản để không ghi đè snapshot tốt. Snapshot chứa trạng thái nhạy cảm của cluster; copy tới kho riêng bên ngoài VM qua đường xác thực. Trước khi phục hồi thật, thực hành restore trong môi trường tách biệt, ghi đường data-dir mới và cách cập nhật static Pod manifest. File snapshot thành công chưa chứng minh toàn bộ quy trình restore đã được thử. Phục hồi cp-01 cần phối hợp cả etcd, PKI và endpoint API theo bản đang dùng. [Backup/restore etcd](https://kubernetes.io/docs/tasks/administer-cluster/configure-upgrade-etcd/)

### 17.3. Tạm dừng lab

Nếu chỉ nghỉ ngắn, chọn dừng VM sau khi lưu bằng chứng và xác định các workload sẽ tắt. Khi bật lại, bật cp-01 trước để API sẵn sàng, bật worker, kiểm tra CNI/CoreDNS, Rancher, Istio và ứng dụng do TV2 lựa chọn rồi mới gọi public URL. External IP động của VM có thể đổi; quản trị qua tên VM/IAP và IP riêng đã dành giảm phụ thuộc vào IP đó. IP frontend LB dành riêng giữ URL demo trong thời gian reservation còn tồn tại. Disk, LB và IP có thể còn phí khi VM dừng.

## 18. Bảng xử lý lỗi dành riêng cho TV1

| Triệu chứng | Bạn kiểm tra gì trước? | Cách khôi phục/điểm bàn giao |
|---|---|---|
| gcloud báo project/permission denied | gcloud config get-value project, tài khoản đang active, IAM role | Chọn lại project/tài khoản. Nếu thiếu quyền, người quản trị project cấp đúng vai trò cho thao tác đang cần. |
| SSH qua IAP lỗi | API IAP, IAM tunnel role, OS Login, rule 22 từ dải IAP và tag trên VM | Thử gcloud compute ssh --troubleshoot; phân biệt lỗi tunnel với lỗi Linux user/sudo. |
| apt/curl timeout trên VM | IP outbound, DNS, route, firewall egress, registry endpoint | Kiểm tra đường ra trước khi chạy lại kubeadm hoặc Helm. |
| kubeadm init dừng ở CRI | systemctl containerd, config CRI, cgroup, journal | Sửa runtime, khởi động lại; đọc tình trạng init đã tạo gì trước khi retry. |
| Worker join timeout | TCP 6443, IP riêng cp-01, token, CA hash và đồng hồ | Tạo token mới nếu hết hạn. Nếu node đã hiện, đọc condition NotReady để kiểm tra CNI. |
| Pod Pending | describe pod/events, resource requests, node taint, volume | Dành tài nguyên đúng worker; giữ control plane theo thiết kế, đo tài nguyên thay vì xóa taint vội. |
| DNS cluster lỗi sau rewrite | logs CoreDNS, syntax Corefile, backup | Apply lại ConfigMap tốt trước đó và thử DNS Service chuẩn, rồi thêm lại rewrite có kiểm tra. |
| Rancher 404 | IngressClass, host header, entrypoint TLS, tên ingress | So rendered YAML với resource thật. Curl bằng hostname có TLS và đúng cổng; IP đơn thuần có thể không khớp host. |
| Browser báo CA/SAN | Windows trust store, SAN, thời hạn cert, secret TLS | Import đúng public CA, truy cập đúng hostname, xác nhận cert tại ingress là cert vừa tạo. |
| UI mở nhưng agent lỗi | DNS từ Pod, server-url cổng 443, Secret tls-ca, CA checksum | Đọc log cattle-cluster-agent nếu có, sửa chuỗi DNS/TLS trước khi thay role. |
| NodePort chạy nhưng LB lỗi | Backend/group/region, rule frontend, firewall client/probe, guest agent route VIP | So lần thử qua node IP với lần thử frontend IP. Không dùng TCP healthy làm bằng chứng ứng dụng hoàn chỉnh. |
| Website 503 | EndpointSlice gateway và app, readiness, mTLS/policy | Nhờ TV2 kiểm tra route và TV3 mạng mesh; giữ request/time để khớp access log. |
| Kiali trống | Request mới, Prometheus targets/series, time window | TV3 xác minh series trước khi thay dashboard config. |
| Bị chặn sau policy | Tên nguồn, ServiceAccount, policy đang áp, cùng một URL | TV2/TV3 phục hồi đối chứng; bạn chạy lại và ghi lớp nào vừa thay đổi. |

Trong sự cố, ghi một dòng “đang hỏng ở chặng nào, thử bằng nguồn nào, kết quả cụ thể”. Gửi đúng người phụ trách cùng log. Một lần chỉ đổi một cấu hình để biết thay đổi nào tạo hiệu quả.

## 19. Bàn giao, báo cáo và cleanup

### 19.1. Bộ file của riêng bạn

Trên laptop tạo thư mục TV1 để gom tài liệu. Đây là danh sách cần bàn giao sau khi thực hiện, không phải bằng chứng đã có sẵn:

```text
TV1/
  inventory.md
  versions.md
  cloud-network-and-firewall.md
  cluster-bootstrap.md
  rancher-values.yaml
  traefik-values.yaml
  rancher-dns-tls-runbook.md
  public-access.md
  recovery.md
  cost-and-cleanup.md
  evidence/
    INF01-nodes.txt
    IAM01-viewer.md
    ADM01-rancher.md
    PUB01-external-client.md
    SEC04-combined-policies.md
    SVC04-selector-repair.md
```

Token join, kubeconfig admin và private key phải được giữ trong kho riêng có kiểm soát. Trong inventory ghi resource name, project, zone/region, IP, port, người tạo, ngày tạo và trạng thái. Với test ghi người chạy lại. Một “task xong” cần có người khác tái hiện được từ file.

### 19.2. Mẫu giải thích trước thầy

“Nhóm tạo ba VM Compute Engine. cp-01 chạy API server và các thành phần điều khiển; hai worker chạy Pod. Rancher đang quản trị cụm local này. Ở đây TARGET_SERVICE có tên Service, selector và endpoint thực tế. Sau khi Pod thay đổi, client tiếp tục gọi cùng tên. Request từ ngoài đi qua IP của LB, cổng NodePort 30080 và Istio gateway. Hai lớp policy kiểm soát nguồn nào được gọi tới Service.”

Khi được hỏi Service có phải một process chạy trong Pod không, chỉ ra Service là tài nguyên mô tả địa chỉ/cổng và nhóm backend. Dùng EndpointSlice và Pod để giải thích data plane thực tế; trong mesh proxy có thể chọn endpoint từ cấu hình do Istiod cung cấp. Bạn cần hiểu mối liên hệ này vì cloud LB chỉ là chặng đầu của request.

### 19.3. Dọn tài nguyên đúng thứ tự

Chỉ thực hiện sau khi nhóm lưu backup/evidence và chốt ngừng URL. Trên **Cloud Shell/Bash** kiểm tra project, inventory và tên resource trước mỗi lệnh. Các lệnh cố tình giữ prompt xác nhận mặc định. Xóa group không xóa VM thành viên, còn xóa VM có thể xóa boot disk theo auto-delete.

```bash
gcloud config get-value project
gcloud compute forwarding-rules describe nt132-web-forward --region="$REGION"
gcloud compute forwarding-rules delete nt132-web-forward --region="$REGION"
gcloud compute backend-services delete nt132-web-backend --region="$REGION"
gcloud compute health-checks delete nt132-web-hc --region="$REGION"
gcloud compute instance-groups unmanaged delete nt132-workers --zone="$ZONE"
gcloud compute addresses delete nt132-web-ip --region="$REGION"
```

Tiếp theo xem danh sách VM/disk. Nếu tài liệu quan trọng vẫn chỉ ở cp-01, copy ra trước. Khi đã sẵn sàng, xóa từng VM của lab, kiểm tra disk còn lại trong Console và quyết định disk nào cần giữ. Xóa ba internal address reservations sau khi VM giải phóng IP; xóa từng firewall rule nt132 theo inventory; cuối cùng subnet rồi VPC nếu không có tài nguyên khác đang dùng. Không xóa hàng loạt tài nguyên theo một từ khóa mơ hồ.

Gỡ dòng hosts rancher.nt132.test và CA lab trong trust store sau khi kết thúc lab, dựa vào đúng subject/thumbprint đã ghi lúc import. Kiểm tra trang Billing sau đó để phát hiện IP/disk/snapshot còn lại; dữ liệu billing có độ trễ.

## 20. Danh sách nghiệm thu cá nhân và nguồn kỹ thuật

| Mục | Hoàn thành khi | Ô đánh dấu |
|---|---|---|
| Quyền và máy | Cả ba người SSH được vào đúng VM, dùng tài khoản riêng | ☐ |
| Cụm | Ba node Ready, InternalIP khớp inventory | ☐ |
| Mạng | Client và server trên hai worker gọi được bằng IP Pod và tên Service | ☐ |
| Rancher | Login bằng hostname tin cậy, thấy đúng local cluster, agent truy cập server URL được | ☐ |
| Viewer | Tài khoản trình chiếu đọc được thông tin cần thiết, không sửa workload | ☐ |
| ứng dụng do TV2 lựa chọn | Truy cập qua gateway trả nội dung đúng theo bàn giao; graph có luồng thật | ☐ |
| Public | Client ngoài VPC mở đúng IP frontend, cả hai backend healthy | ☐ |
| Service | Giải thích selector, endpoint và Pod; tái hiện sửa selector sai | ☐ |
| Policy | Tự chạy đối chứng và lượt kết hợp, lưu nguồn/đích/kết quả | ☐ |
| Bàn giao | Manifest, phiên bản, log, diagram, backup và chi phí được lưu ngoài VM | ☐ |
| Kết thúc | Inventory cuối cho biết tài nguyên đã xóa hoặc giữ có chủ đích | ☐ |

Nguồn để đối chiếu phiên bản và các bước phụ thuộc sản phẩm:

- [Kubernetes kubeadm installation](https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/install-kubeadm/), [tạo cluster](https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/create-cluster-kubeadm/) và [Service](https://kubernetes.io/docs/concepts/services-networking/service/).
- [Rancher support matrix](https://www.suse.com/suse-rancher/support-matrix/all-supported-versions/), [cài bằng Helm](https://ranchermanager.docs.rancher.com/getting-started/installation-and-upgrade/install-upgrade-on-a-kubernetes-cluster/), [TLS Secrets](https://ranchermanager.docs.rancher.com/getting-started/installation-and-upgrade/resources/add-tls-secrets).
- [Traefik Kubernetes](https://doc.traefik.io/traefik/setup/kubernetes/), [Calico requirements](https://docs.tigera.io/calico/latest/getting-started/kubernetes/requirements), [Istio supported releases](https://istio.io/latest/docs/releases/supported-releases/).
- [IAP](https://cloud.google.com/iap/docs/using-tcp-forwarding), [Network Load Balancer](https://cloud.google.com/load-balancing/docs/network/setting-up-network-backend-service) và [health check probes](https://cloud.google.com/load-balancing/docs/health-check-concepts).
- [Kế hoạch tổng thể của nhóm](./plan.md) để đối chiếu việc của TV2/TV3 và các ca kiểm thử chung.
