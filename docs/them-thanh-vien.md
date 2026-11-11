# Thêm TV2 và TV3 vào đồ án

Tài liệu này dùng sau khi TV1 đã dựng cụm Kubernetes ba node và mở được Rancher. Mỗi thành viên dùng tài khoản riêng; không chia sẻ mật khẩu Rancher admin, SSH private key, kubeconfig admin, join token hoặc tài khoản Google của TV1.

## 1. Trạng thái bàn giao hiện tại

Đã kiểm chứng ngày 05/11/2026 trên Google Cloud:

| Thành phần | Trạng thái |
|---|---|
| cp-01 / 10.20.0.10 | Kubernetes control plane v1.35.10, Ready |
| wk-01 / 10.20.0.11 | Worker, Ready |
| wk-02 / 10.20.0.12 | Worker, Ready |
| Calico | CNI hoạt động; Pod khác node giao tiếp được |
| Kubernetes Service | Pod IP, ClusterIP và DNS đều trả HTTP 200 |
| Rancher | v2.15.3, cluster `local` có đủ ba node Active |
| Istio, Prometheus, Kiali | Chưa triển khai |
| Ứng dụng TV2 | Chưa lựa chọn/triển khai |

TV1 đã hoàn thành mốc hạ tầng và dashboard cho báo cáo tiến độ. TV1 vẫn giữ trách nhiệm vận hành cloud, Terraform state, quyền truy cập, review thay đổi và hỗ trợ tích hợp cuối.

## 2. Thông tin cần nhận từ hai thành viên

TV1 cần thu thập riêng:

| Người | Thông tin |
|---|---|
| TV2 | Email Google dùng Google Cloud, GitHub username, tên Rancher mong muốn |
| TV3 | Email Google dùng Google Cloud, GitHub username, tên Rancher mong muốn |

Không ghi email, mật khẩu hoặc token vào repository. GitHub username có thể ghi vào phân công nếu nhóm muốn.

## 3. Mời vào GitHub

TV1 thao tác tại repository `ThanhThuw5206/NT132---Kubernetes-System`:

1. Mở **Settings** của repository.
2. Trong **Access**, chọn **Collaborators** hoặc **Collaborators & teams**.
3. Chọn **Add people**.
4. Tìm GitHub username của TV2, chọn đúng tài khoản và gửi lời mời.
5. Lặp lại với TV3.
6. Hai thành viên mở email/thông báo GitHub và chấp nhận lời mời.

Với repository thuộc tài khoản cá nhân, collaborator có quyền ghi code. Không đưa mật khẩu hay token GitHub cho nhau. TV1 giữ quyền quản trị repository.

Sau khi chấp nhận, mỗi người clone và tạo branch riêng từ bản cloud hiện tại.

### TV2

```bash
git clone https://github.com/ThanhThuw5206/NT132---Kubernetes-System.git
cd NT132---Kubernetes-System
git fetch origin
git switch --create tv2/application-service origin/main
```

### TV3

```bash
git clone https://github.com/ThanhThuw5206/NT132---Kubernetes-System.git
cd NT132---Kubernetes-System
git fetch origin
git switch --create tv3/istio-network origin/main
```

Mỗi người chỉ push branch của mình và tạo pull request về `main`. Không push trực tiếp lên `main`, không commit Secret, kubeconfig, private key, Terraform state hoặc file `config/application.json`.

## 4. Cấp Google Cloud IAM để SSH bằng IAP

Chỉ cần cấp khi TV2/TV3 phải đăng nhập VM. Việc xem Rancher và làm code không bắt buộc có quyền Google Cloud.

TV1 mở Google Cloud Console, chọn project `nt132-kubernetes-513805`, rồi:

1. Vào **IAM & Admin → IAM**.
2. Bấm **Grant Access**.
3. Trong **New principals**, nhập email Google của thành viên.
4. Thêm ba role:
   - **Compute Viewer** (`roles/compute.viewer`)
   - **Compute OS Admin Login** (`roles/compute.osAdminLogin`)
   - **IAP-secured Tunnel User** (`roles/iap.tunnelResourceAccessor`)
5. Bấm **Save**.
6. Lặp lại cho thành viên còn lại.

Không cấp Owner, Editor, Billing Account Admin, Project IAM Admin hoặc quyền sửa Terraform cho TV2/TV3. `OS Admin Login` cho phép sudo trên VM, vì vậy chỉ cấp cho đúng thành viên và thu hồi khi đồ án kết thúc.

TV1 cũng có thể cấp bằng Cloud Shell, thay email mẫu bằng email thật:

```bash
gcloud projects add-iam-policy-binding nt132-kubernetes-513805 \
  --member='user:TV2_EMAIL' --role='roles/compute.viewer'
gcloud projects add-iam-policy-binding nt132-kubernetes-513805 \
  --member='user:TV2_EMAIL' --role='roles/compute.osAdminLogin'
gcloud projects add-iam-policy-binding nt132-kubernetes-513805 \
  --member='user:TV2_EMAIL' --role='roles/iap.tunnelResourceAccessor'
```

Lặp lại ba lệnh với `TV3_EMAIL`. Không chạy lệnh khi vẫn còn chuỗi `TV2_EMAIL`/`TV3_EMAIL`.

Mỗi thành viên cài Google Cloud CLI, sau đó tự đăng nhập:

```powershell
gcloud auth login
gcloud config set project nt132-kubernetes-513805
gcloud auth list
```

TV2 kiểm tra SSH tới worker mình phụ trách:

```powershell
gcloud compute ssh wk-01 --project=nt132-kubernetes-513805 --zone=asia-southeast1-a --tunnel-through-iap
```

TV3 kiểm tra SSH tới worker mình phụ trách:

```powershell
gcloud compute ssh wk-02 --project=nt132-kubernetes-513805 --zone=asia-southeast1-a --tunnel-through-iap
```

Không chạy `kubeadm init`, `kubeadm join`, `kubeadm reset` hoặc sửa containerd trên các node đã hoạt động. TV1 giữ quyền bật/tắt VM để tránh hai người thao tác vòng đời máy cùng lúc.

## 5. Tạo tài khoản Rancher riêng

TV1 đăng nhập Rancher bằng admin:

1. Bấm **☰ → Users & Authentication**.
2. Chọn **Users → Create**.
3. Tạo user TV2, đặt username riêng, display name rõ ràng và mật khẩu tạm thời.
4. Chọn global permission **Standard User**.
5. Lặp lại cho TV3.
6. Gửi username/mật khẩu tạm bằng kênh riêng; yêu cầu đổi mật khẩu sau lần đăng nhập đầu.

Không cấp Administrator hoặc Restricted Administrator chỉ để xem cluster.

### Quyền TV2 trong Rancher

1. Vào cluster `local` → **Cluster → Projects/Namespaces**.
2. Tạo project `nt132-application` nếu chưa có.
3. Mở menu của project → **Edit Config → Members → Add**.
4. Chọn user TV2 và role **Project Member**.
5. Tạo namespace ứng dụng bên trong project sau khi TV2 chốt tên.

TV2 có thể quản lý Deployment, Pod, Service, ConfigMap và workload trong project ứng dụng mà không có quyền quản trị toàn Rancher.

### Quyền TV3 trong Rancher

1. Vào **Cluster Management → local → Edit Config/Manage Members**.
2. Thêm user TV3 với **Cluster Member** để xem tài nguyên cấp cluster.
3. Khi đã có namespace/project phục vụ mesh, thêm TV3 làm Project Member/Owner đúng phạm vi cần thao tác.

Cài Istio tạo CRD và tài nguyên cấp cluster, nên `Cluster Member` có thể không đủ để chạy Helm. Phương án thực hành của nhóm:

- TV3 chuẩn bị, giải thích và chạy script trong phiên SSH riêng đã được cấp OS Admin Login.
- TV1 quan sát, lưu bằng chứng và review thay đổi Git.
- Không cấp Rancher Cluster Owner lâu dài chỉ để cài Istio.

## 6. Công việc TV1 còn lại

Sau khi cấp quyền, cả nhóm dùng [runbook vận hành hằng ngày](bat-tat-lab.md) để bật/tắt VM, kiểm tra cluster, mở Rancher và tiếp tục đúng phần việc.

TV1 không cần viết lại cụm. Các việc còn lại:

1. Bật/tắt ba VM và theo dõi credit.
2. Quản lý Terraform state; chỉ TV1 chạy `terraform apply/destroy`.
3. Quản lý IAM, Rancher users, CA/tunnel và branch tích hợp.
4. Review PR của TV2/TV3, kiểm tra không có secret.
5. Hỗ trợ tạo namespace và tích hợp route khi TV2 bàn giao ứng dụng.
6. Bật public load balancer ở giai đoạn cuối nếu thực sự cần demo ngoài tunnel.
7. Thu thập ảnh dashboard, node Ready, Service/DNS và chi phí.

## 7. Công việc TV2 — ứng dụng và Kubernetes Service

TV2 không dùng Bookinfo hoặc ứng dụng mẫu do TV1 chọn thay. TV2 tự chọn workload có ít nhất hai thành phần giao tiếp qua HTTP để chứng minh Service.

### Phần code/config phải làm

1. Ghi nguồn repository, license, release/tag/commit và image version.
2. Đặt source cần thiết trong `src/` và manifest trong `apps/<ten-ung-dung>/`.
3. Viết Deployment cho entry/caller và target; có labels rõ ràng, readiness/liveness probe, requests/limits và ServiceAccount.
4. Viết Service ClusterIP cho từng thành phần; đối chiếu `port`, `targetPort` và container port.
5. Không commit password thật. Secret chỉ có template/placeholder hoặc được tạo ngoài Git.
6. Điền đầy đủ `docs/application-handover.md`: namespace, Service, labels, port, path và luồng gọi.
7. Tạo local `config/application.json` từ file example để renderer kiểm tra thông số; file này đã được `.gitignore`.
8. Viết README trong thư mục app với thứ tự apply, test, rollback và cleanup.

### Bài kiểm chứng phải nộp

- DNS Service phân giải được.
- EndpointSlice có endpoint Ready đúng labels.
- Caller gọi target qua tên Service thành công.
- Scale target từ một lên hai replica; Service/ClusterIP giữ nguyên và EndpointSlice thay đổi.
- Xóa một Pod; Deployment tạo Pod mới và Service hoạt động lại sau khi Pod Ready.
- Selector sai tạo tình huống Service không có endpoint, sau đó sửa và kiểm chứng phục hồi.

### Sản phẩm PR TV2

- `src/` hoặc liên kết nguồn được ghim commit.
- `apps/<ten-ung-dung>/`.
- Phiếu bàn giao đã điền.
- Test log đã loại thông tin nhạy cảm.
- 2–3 slide giải thích caller → Service → EndpointSlice → target Pod.

## 8. Công việc TV3 — Istio, quan sát và policy

TV3 tiếp nhận Calico đang hoạt động; không cài lại CNI. Trọng tâm là mesh, quan sát và kiểm soát traffic.

### Phần code/config phải làm

1. Review `cluster/calico/installation.yaml`, firewall VXLAN và trạng thái Calico hiện tại.
2. Chạy/kiểm chứng `scripts/05-install-istio.sh` với phiên bản đã ghim.
3. Chạy/kiểm chứng `scripts/07-install-observability.sh` để có Prometheus và Kiali.
4. Phối hợp TV2 dùng renderer tạo Gateway, VirtualService, PeerAuthentication, AuthorizationPolicy và NetworkPolicy theo Service thật.
5. Ghi ma trận nguồn → đích → port → method/path → kết quả mong đợi.
6. Không bật sidecar injection cho `kube-system`, `cattle-system` hoặc toàn cluster.
7. Viết README/test log cho từng policy và lệnh rollback riêng.

### Bài kiểm chứng phải nộp

- Namespace ứng dụng có sidecar; Pod app Ready đầy đủ container.
- Gateway/VirtualService đưa request đến entry Service.
- Kiali có cạnh traffic sau khi tạo request thật.
- STRICT mTLS vẫn cho luồng trong mesh hoạt động và từ chối client ngoài mesh theo ca test.
- AuthorizationPolicy cho đúng ServiceAccount/method/path, chặn danh tính hoặc path sai.
- NetworkPolicy cho nguồn đúng label, chặn nguồn khác; gỡ policy thì kết nối phục hồi.

### Sản phẩm PR TV3

- Giá trị Istio/manifest tích hợp đã sửa theo app thật.
- Policy trong `mesh/istio/` và `network/policies/`.
- Ma trận test cho phép/chặn, timestamp và HTTP status.
- 2–3 slide giải thích Calico, Istio, Kiali và hai lớp policy.

## 9. Quy trình phối hợp

1. TV1 bật ba VM và xác nhận node Ready.
2. TV2 deploy workload cơ bản, chưa áp policy; chốt Service/labels/ports.
3. TV1 review kết quả baseline và phiếu bàn giao.
4. TV3 cài Istio/observability, tích hợp route rồi áp từng policy một.
5. TV2 chạy request nghiệp vụ; TV3 quan sát và ghi kết quả; TV1 kiểm tra Rancher/tài nguyên.
6. Mỗi thành viên tạo PR; một thành viên khác đọc và tái hiện ít nhất một ca test.
7. Chỉ TV1 tích hợp vào branch chung sau khi test đạt.

Không áp tất cả policy cùng lúc ở lần đầu vì sẽ khó xác định lớp nào gây lỗi. Không dừng/xóa VM, namespace chung hoặc tài nguyên Rancher khi chưa báo nhóm.

## 10. Thu hồi quyền khi kết thúc

- Xóa Rancher local user hoặc membership không còn dùng.
- Vào Google Cloud IAM, thu hồi ba role đã cấp cho từng thành viên.
- Xóa access token cá nhân đã tạo; không cần chia sẻ hoặc thu hồi SSH key của người khác thủ công khi OS Login/IAM đã bị gỡ.
- Xóa collaborator GitHub nếu repository không còn cần truy cập.
- TV1 thực hiện backup cần thiết rồi dùng Terraform plan/destroy theo runbook kết thúc lab.

Tham khảo: [GitHub repository access](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/managing-teams-and-people-with-access-to-your-repository), [Google IAP TCP forwarding IAM](https://docs.cloud.google.com/iap/docs/using-tcp-forwarding), [Rancher local users](https://ranchermanager.docs.rancher.com/v2.14/how-to-guides/new-user-guides/authentication-permissions-and-global-configuration/authentication-config/create-local-users), [Rancher project membership](https://ranchermanager.docs.rancher.com/how-to-guides/new-user-guides/add-users-to-projects).
