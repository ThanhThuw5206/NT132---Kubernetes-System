# Runbook hằng ngày: bật/tắt VM, vào Rancher và tiếp tục công việc

Áp dụng cho project `nt132-kubernetes-513805`, zone `asia-southeast1-a`, ba VM `cp-01`, `wk-01`, `wk-02`. Các lệnh quản lý VM bên dưới chạy trong **Google Cloud Shell**, không chạy trong terminal SSH của VM. Tài liệu này không tự tắt máy; bạn chủ động chạy khi kết thúc buổi thực hành.

Trạng thái ngày 05/11/2026: ba node Kubernetes v1.35.10 Ready, Calico/CoreDNS hoạt động, Service khác node đã trả HTTP 200 và Rancher v2.15.3 hiển thị đủ ba node Active. Không init/join/cài lại các thành phần này mỗi lần bật máy.

## 0. TV1 cấp Google Cloud cho TV2/TV3 một lần

GitHub đã mời riêng. Để mỗi người SSH bằng tài khoản Google của mình, TV1 vào Google Cloud Console, chọn project `nt132-kubernetes-513805`:

1. Mở **IAM & Admin → IAM → Grant Access**.
2. Nhập email Google của TV2.
3. Thêm ba role: **Compute Viewer**, **Compute OS Admin Login**, **IAP-secured Tunnel User**.
4. Bấm **Save** và lặp lại với email TV3.

Không cấp Owner, Editor, Billing Admin hoặc quyền sửa IAM. `OS Admin Login` có quyền sudo trên VM, chỉ cấp cho đúng thành viên và thu hồi khi kết thúc đồ án.

Mỗi thành viên cài Google Cloud CLI trên laptop, rồi tự chạy:

```powershell
gcloud auth login
gcloud config set project nt132-kubernetes-513805
gcloud auth list
gcloud config get-value project
```

TV2 kiểm tra quyền với worker phụ trách:

```powershell
gcloud compute ssh wk-01 --project=nt132-kubernetes-513805 --zone=asia-southeast1-a --tunnel-through-iap
```

TV3 kiểm tra quyền với worker phụ trách:

```powershell
gcloud compute ssh wk-02 --project=nt132-kubernetes-513805 --zone=asia-southeast1-a --tunnel-through-iap
```

TV1 vẫn là người duy nhất chạy Terraform và mặc định là người bật/tắt VM. Nếu giao quyền bật/tắt cho người khác, cả nhóm phải báo trước để tránh một người tắt cụm khi người khác đang test.

## 1. Hai thao tác dùng mỗi ngày

**Khi nghỉ:** chờ công việc cài đặt hoàn tất, lưu file → thoát SSH → dừng worker → dừng control plane → kiểm tra ba máy TERMINATED.

**Khi làm tiếp:** mở Cloud Shell → bật control plane → bật worker → kiểm tra dịch vụ/cluster → mở lại tunnel nếu cần dashboard.

Stop giữ boot disk và dữ liệu đã ghi lên disk. Không phải cài lại Kubernetes sau mỗi lần bật. Đây là cách nghỉ giữa các buổi lab, không phải bảo trì không gián đoạn cho môi trường production.

## 2. Tắt máy cuối buổi — lệnh copy trực tiếp

### 2.1. Trước khi tắt

- Đợi script cài apt, kubeadm init/join, Helm hoặc Terraform chạy xong. Không tắt ngang lúc đang cài đặt.
- Lưu file đang sửa. Đợi thao tác ghi dữ liệu ứng dụng hoàn tất; nếu sau này có database, dùng quy trình dừng/backup của ứng dụng trước.
- Ghi tiến độ: máy nào đã prepare, đã init/join chưa, đã cài Calico/Rancher chưa. Không ghi join token hay mật khẩu vào ghi chú/Git.
- Nếu đang chạy port-forward, nhấn Ctrl+C ở terminal đó. Đóng tunnel không đồng nghĩa đã tắt VM.
- Nếu dấu nhắc đang có `@cp-01`, `@wk-01` hoặc `@wk-02`, chạy `exit` để trở về Cloud Shell. Dấu nhắc cần có `@cloudshell`.

Hiện cụm đã hoàn thành bootstrap. Trước khi tắt, chỉ cần bảo đảm không còn Helm/kubectl apply, rollout hoặc bài test đang chạy.

### 2.2. Dừng hai worker trước

Trong **Cloud Shell**:

```bash
gcloud compute instances stop wk-01 wk-02 \
  --project=nt132-kubernetes-513805 \
  --zone=asia-southeast1-a
```

Đợi lệnh kết thúc thành công. Nếu báo lỗi, xử lý lỗi hoặc kiểm tra trạng thái trước; không coi việc đóng terminal là đã tắt xong.

### 2.3. Dừng control plane

```bash
gcloud compute instances stop cp-01 \
  --project=nt132-kubernetes-513805 \
  --zone=asia-southeast1-a
```

### 2.4. Xác nhận đã tắt hết

```bash
gcloud compute instances list \
  --project=nt132-kubernetes-513805 \
  --filter='name=(cp-01 wk-01 wk-02)' \
  --format='table(name,zone.basename(),status)'
```

Kết quả mong đợi:

```text
NAME   ZONE               STATUS
cp-01  asia-southeast1-a   TERMINATED
wk-01  asia-southeast1-a   TERMINATED
wk-02  asia-southeast1-a   TERMINATED
```

**TERMINATED ở đây nghĩa là VM đã dừng, không phải bị xóa.** Bạn có thể đóng trình duyệt sau khi xác nhận. Nếu còn STOPPING, chờ rồi chạy lại lệnh kiểm tra; nếu còn RUNNING, máy đó chưa dừng.

## 3. Bật lại đầu buổi

### 3.1. Mở đúng tài khoản/project

1. Đăng nhập Google Cloud Console bằng tài khoản đang quản lý project mới.
2. Chọn project `nt132-kubernetes-513805` trên thanh trên cùng.
3. Bấm biểu tượng `>_` để mở Cloud Shell, Authorize nếu được yêu cầu.
4. Các lệnh dưới dùng project/zone trực tiếp nên không phụ thuộc biến export từ phiên hôm trước.

### 3.2. Bật control plane trước

```bash
gcloud compute instances start cp-01 \
  --project=nt132-kubernetes-513805 \
  --zone=asia-southeast1-a
```

Đợi lệnh hoàn tất. Trạng thái RUNNING xác nhận máy đã bật, chưa đồng nghĩa Kubernetes API đã sẵn sàng.

### 3.3. Bật hai worker

```bash
gcloud compute instances start wk-01 wk-02 \
  --project=nt132-kubernetes-513805 \
  --zone=asia-southeast1-a
```

Kiểm tra:

```bash
gcloud compute instances list \
  --project=nt132-kubernetes-513805 \
  --filter='name=(cp-01 wk-01 wk-02)' \
  --format='table(name,zone.basename(),status,networkInterfaces[0].networkIP)'
```

Cần đủ ba máy RUNNING, IP nội bộ vẫn là .10/.11/.12. IP bên ngoài có thể thay đổi khi bật lại; dùng SSH theo tên VM và IAP như dưới, không dùng IP public cũ đã chụp.

### 3.4. SSH vào cp-01

```bash
gcloud compute ssh cp-01 \
  --project=nt132-kubernetes-513805 \
  --zone=asia-southeast1-a \
  --tunnel-through-iap
```

Trên **cp-01**:

```bash
hostname -s
cd ~/NT132---Kubernetes-System
sudo systemctl is-active containerd
```

Nếu SSH chưa kết nối được ngay sau start, chờ hệ điều hành khởi động rồi thử lại. Không tạo lại VM vì một lần SSH thất bại.

## 4. Tiếp tục đúng mốc đang làm

### A. Mới prepare, chưa init cluster — chỉ dùng khi dựng lại lab mới

Trên máy đã prepare, kiểm tra:

```bash
kubeadm version -o short
kubelet --version
```

Không cần chạy lại script prepare chỉ vì vừa bật VM. Chuyển sang worker chưa prepare để tiếp tục hướng dẫn setup. Kubelet có thể chưa hoạt động ổn định trước khi init/join; `kubectl get nodes` chưa dùng được ở giai đoạn này.

### B. Kiểm tra cụm hiện tại sau khi bật lại

Trên cp-01, TV1 dùng tài khoản OS Login đã setup kubeconfig:

```bash
kubectl get --raw=/readyz
kubectl get nodes -o wide
kubectl wait --for=condition=Ready nodes --all --timeout=300s
kubectl -n kube-system rollout status deployment/coredns --timeout=180s
kubectl get pods -A
```

API cần trả `ok`, ba node cần Ready. Nếu API chưa lên ngay, chờ rồi thử lại; không reset/init lại cluster. Nếu mới init/join nhưng CHƯA cài Calico, node NotReady có thể do chưa có CNI — tiếp tục bước cài Calico thay vì chờ Ready vô hạn.

TV2/TV3 đăng nhập cp-01 bằng tài khoản Google riêng sẽ không có file kubeconfig của TV1. Khi cần kiểm tra trong buổi có TV1 giám sát, dùng:

```bash
sudo kubectl --kubeconfig=/etc/kubernetes/admin.conf get nodes -o wide
```

Lệnh này có quyền quản trị cụm; không dùng tùy tiện, không sao chép `/etc/kubernetes/admin.conf` ra laptop/Git và không chia sẻ output Secret.

Khi API lỗi kéo dài, kiểm tra:

```bash
sudo systemctl status containerd kubelet --no-pager
sudo journalctl -u kubelet -n 80 --no-pager
```

Gửi lỗi để chẩn đoán trước khi sửa. Không chạy `kubeadm reset`, không xóa `/var/lib/etcd`, không tạo join mới chỉ vì restart VM. Join token hết hạn không làm node đã tham gia bị rời cluster.

### C. Đã cài Rancher

Sau khi cluster Ready, trên cp-01:

```bash
kubectl -n rancher-ingress rollout status deployment/rancher-ingress --timeout=300s
kubectl -n cattle-system rollout status deployment/rancher --timeout=300s
```

Mở lại port-forward, giữ terminal này chạy:

```bash
cd ~/NT132---Kubernetes-System
bash scripts/09-port-forward.sh rancher
```

Trên **PowerShell laptop**, mở lại SSH tunnel:

```powershell
gcloud compute ssh cp-01 --project=nt132-kubernetes-513805 --zone=asia-southeast1-a --tunnel-through-iap --ssh-flag="-N" --ssh-flag="-L 8443:127.0.0.1:8443"
```

Mở `https://rancher.nt132.test:8443`. Dòng hosts và CA đã import trên laptop vẫn dùng lại; không cần tạo lại CA hoặc cài lại Rancher. Hai terminal forwarding phải còn chạy. Nếu chưa từng thiết lập hosts/CA, làm phần truy cập Windows trong `deploy-cloud.md` trước.

Chưa cài Istio thì không dùng `08-verify-cluster.sh` làm điều kiện nghiệm thu lần mở máy này, vì script đó còn kiểm tra Istio.

### D. Laptop mới kết nối Rancher lần đầu

Mỗi thành viên cần tài khoản Rancher riêng do TV1 tạo với Standard User và quyền project/cluster phù hợp. Không dùng chung tài khoản `admin`.

TV1 chỉ gửi file CA công khai `ca.crt`; tuyệt đối không gửi `ca.key` hoặc `tls.key`. Thành viên lưu file thành:

```text
C:\Users\TEN_WINDOWS\nt132-lab-ca.crt
```

Trong PowerShell:

```powershell
Import-Certificate -FilePath "$env:USERPROFILE\nt132-lab-ca.crt" -CertStoreLocation Cert:\CurrentUser\Root
```

Mở Notepad bằng **Run as administrator**, mở `C:\Windows\System32\drivers\etc\hosts` dưới chế độ All Files và thêm:

```text
127.0.0.1 rancher.nt132.test
```

Trên cp-01 chỉ cần **một** tiến trình port-forward cho cả buổi. TV1 chạy:

```bash
cd ~/NT132---Kubernetes-System
bash scripts/09-port-forward.sh rancher
```

Nếu TV1 không có mặt, thành viên được cấp OS Admin Login có thể mở tương đương trên cp-01:

```bash
sudo kubectl --kubeconfig=/etc/kubernetes/admin.conf \
  -n rancher-ingress port-forward svc/rancher-ingress \
  8443:443 --address=127.0.0.1
```

Nếu báo port 8443 đã được sử dụng, tiến trình port-forward đã chạy; không mở bản thứ hai. Mỗi thành viên vẫn mở tunnel riêng trên laptop:

```powershell
gcloud compute ssh cp-01 --project=nt132-kubernetes-513805 --zone=asia-southeast1-a --tunnel-through-iap --ssh-flag="-N" --ssh-flag="-L 8443:127.0.0.1:8443"
```

Sau đó mở `https://rancher.nt132.test:8443` và đăng nhập bằng Rancher user riêng. PowerShell đứng yên là tunnel đang chạy. Khi xong, nhấn Ctrl+C ở tunnel laptop; người mở port-forward trên cp-01 cũng nhấn Ctrl+C sau khi tất cả thành viên kết thúc.

### E. Làm tiếp theo vai trò

**Chỉ sửa code/tài liệu:** không cần bật VM. Làm trên branch Git riêng, push và tạo PR.

**TV2 làm ứng dụng/Service:** bật đủ cụm, mở Rancher, kiểm tra ba node Active; deploy vào project/namespace ứng dụng được cấp. Chốt Deployment, Service, labels, port/targetPort, probes và ServiceAccount trước khi bàn giao. Dùng Rancher shell hoặc phiên thao tác được TV1 giám sát; không sửa namespace hệ thống.

**TV3 làm Istio/Kiali/policy:** chỉ bắt đầu khi workload baseline của TV2 gọi nhau thành công. Chạy script Istio/observability từ cp-01 trong phiên có TV1 theo dõi, rồi áp Gateway/VirtualService và từng policy riêng. Không bật injection cho `kube-system`, `cattle-system` hoặc toàn cluster.

**TV1 tích hợp:** kiểm tra node/Rancher, review PR, tạo namespace/quyền và lưu bằng chứng. Chỉ TV1 thay Terraform, firewall, load balancer hoặc vòng đời VM.

Thứ tự một buổi tích hợp: TV1 bật cụm → xác nhận Ready → mở Rancher → TV2 deploy/test baseline → TV3 tích hợp mesh/policy → cả nhóm lưu log/ảnh → dừng tunnel → TV1 stop worker rồi stop cp.

## 5. Bật/tắt bằng nút trên Console

**Tắt:** vào Compute Engine → VM instances → chọn hai dòng wk-01 và wk-02 → Stop → xác nhận → đợi dừng. Sau đó chọn cp-01 → Stop → xác nhận. Kiểm tra cả ba máy đã dừng.

**Bật:** chọn cp-01 → Start/Resume (hoặc Start theo giao diện) → đợi RUNNING. Sau đó chọn wk-01 và wk-02 → Start. Tiếp tục kiểm tra cluster bằng lệnh ở phần 4.

Chọn **Stop**, không chọn Delete hoặc Reset. Không cần Suspend cho quy trình lab này. Khi dùng lệnh gcloud, trạng thái dừng được hiển thị là TERMINATED.

## 6. Tắt rồi còn tốn khoản nào?

| Khoản | Sau khi cả ba VM đã STOP/TERMINATED |
|---|---|
| CPU/RAM của ba VM thông thường hiện tại | Ngừng tính phí chạy VM |
| Boot disk Persistent Disk 30 + 40 + 40 GB | Vẫn tính phí lưu trữ vì disk còn tồn tại |
| External IP tạm thời do config hiện tại cấp | Được giải phóng khi stop; IP có thể đổi khi start |
| Static external IP/LB nếu bổ sung sau này | Không tự được dọn chỉ vì stop VM; cần kiểm tra riêng |
| Snapshot hoặc tài nguyên khác nếu tự tạo | Vẫn có thể tính phí theo tài nguyên tồn tại |

Ba địa chỉ cố định 10.20.0.10–12 trong repo là **IP nội bộ**, không phải static external IP. Public LB hiện được cấu hình tắt. Không chuyển public IP của node thành static chỉ để SSH: IAP dùng tên VM nên không cần giữ public IP cũ.

Google ghi rõ VM dừng không tính phí sử dụng VM nhưng các tài nguyên còn giữ như disk/static IP vẫn có thể tính phí; IP public tạm thời được giải phóng khi stop. Nguồn: [Stop/start VM](https://docs.cloud.google.com/compute/docs/instances/stop-start-instance), [vòng đời stop/suspend](https://docs.cloud.google.com/compute/docs/instances/suspend-stop-reset-instances-overview), [network pricing](https://cloud.google.com/vpc/network-pricing).

**Cách tiết kiệm trong lúc còn làm đồ án:** chỉ bật cụm khi cần cài/test/demo, stop cả ba khi nghỉ, giữ LB tắt khi chỉ cần tunnel. Viết tài liệu/chỉnh code local không cần bật VM. Mở đủ ba máy khi kiểm thử cụm hoàn chỉnh; chỉ bật cp-01 sẽ không đảm bảo Rancher hoạt động vì workload nằm ở worker.

Không khẳng định stop làm chi phí về 0. Muốn bỏ cả phí disk cần xóa tài nguyên lưu trữ; việc đó làm mất dữ liệu nếu chưa backup, nên không dùng làm thao tác nghỉ hàng ngày. `terraform destroy` dành cho kết thúc lab có chủ đích, không dùng mỗi tối. Cấu hình boot disk hiện đặt auto-delete khi VM bị xóa.

## 7. Các việc KHÔNG cần chạy mỗi lần bật lại

- Không chạy `terraform apply` để bật VM: dùng `gcloud compute instances start`.
- Không chạy lại kubeadm init hoặc join cho node đã tham gia cluster.
- Không cài lại Calico, Helm hoặc Rancher chỉ vì vừa stop/start.
- Không xóa Terraform state hay file chứng chỉ trong `~/.nt132-private`.
- Không drain/cordon toàn cụm cho mỗi lần nghỉ lab; nếu đã cordon vì lý do khác, kiểm tra và uncordon đúng node trước khi tiếp tục scheduling.

Disk giữ source/cấu hình đã lưu, nhưng bộ nhớ RAM và tiến trình đang chạy không được giữ. Dữ liệu chỉ nằm trong container writable layer, emptyDir hoặc metrics addon lab không nên coi là dữ liệu được backup; muốn lưu bền phải có thiết kế volume/backup phù hợp.

## 8. Checklist mỗi buổi

**Trước khi nghỉ:** script đã xong → lưu file/tiến độ → dừng workers → dừng cp → xác nhận cả ba TERMINATED.

**Khi trở lại:** bật cp → bật workers → xác nhận RUNNING → SSH → kiểm tra theo giai đoạn hiện tại → mở lại tunnel nếu dùng Rancher.

Bạn có thể dừng VM ngay sau một bước đã hoàn thành, không bắt buộc làm xong cả cluster trong một buổi.
