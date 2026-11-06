# TV2 · Nhật ký phiên deploy baseline Bookinfo — 06/11/2026

Người thực hiện: TV2. Branch `tv2/kubernetes-service` @ `2782c61`. Thao tác trên cụm cloud `nt132-kubernetes-513805`, zone `asia-southeast1-a`.

**Phạm vi đã làm:** kết nối cụm, deploy Bookinfo **baseline (chưa có Istio/sidecar)**, kiểm chứng Service SVC01/SVC02/SVC03, rồi tắt VM. **Chưa làm** (cần TV3 cài Istio): injection/route qua gateway (APP01 đầy đủ), SEC01 (mTLS), SEC02 (AuthorizationPolicy), NodePort→LB.

**Lưu ý trung thực:** các kết quả dưới đây do **TV2 tự chạy một mình**; theo quy ước nhóm cần **kiểm tra chéo** (SVC01: TV1; SVC02/SVC03: TV3) trước khi coi là nghiệm thu chính thức. Không có Secret/token/kubeconfig trong file này.

## 1. Chuẩn bị môi trường (laptop Windows)

- Cài **Google Cloud CLI portable** 592.0.0 qua `scripts/install-gcloud-local.ps1` (gọi bằng `.\scripts\gcloud-local.ps1`).
- `gcloud auth login` (`1ottie1846@gmail.com`), project `nt132-kubernetes-513805`.
- OS Login profile hoạt động: user Linux `usr_1ottie1846_gmail_com`, khóa `~/.ssh/google_compute_engine` đã nạp.
- **Vấn đề gặp và cách xử lý:**
  - `gcloud compute ssh` qua PuTTY báo *Remote side unexpectedly closed* → thực chất do cp-01 lúc đó đang tắt (IAP `4003 failed to connect to backend port 22`). Sau khi TV1 bật cụm thì hết.
  - OpenSSH báo *bad permissions* trên khóa → siết ACL: `icacls ... /inheritance:r /grant:r "USER:R"` → chỉ còn `MSI\USER:(R)`.
- **Cách kết nối dùng được (2 terminal):**
  1. Tunnel: `.\scripts\gcloud-local.ps1 compute start-iap-tunnel cp-01 22 --local-host-port=localhost:2222 --project=nt132-kubernetes-513805 --zone=asia-southeast1-a` → `Listening on port [2222].`
  2. SSH: `ssh -i $env:USERPROFILE\.ssh\google_compute_engine -o StrictHostKeyChecking=accept-new -p 2222 usr_1ottie1846_gmail_com@localhost`
- TV2 không có kubeconfig riêng → dùng `sudo kubectl --kubeconfig=/etc/kubernetes/admin.conf ...` trên cp-01.

## 2. Trạng thái cụm khi vào

- 3 node `v1.35.10`: `cp-01` Ready; `wk-01`, `wk-02` NotReady lúc vừa bật (~5 phút), **Calico tự hội tụ** rồi cả 3 Ready. Không reset/cài lại gì.
- Đã có sẵn: `calico-system`, `tigera-operator`, `cattle-system`/`rancher-ingress` (Rancher).
- **Chưa có** `istio-system` (TV3 chưa cài Istio) và chưa có `bookinfo`.

## 3. Deploy baseline

```bash
git clone https://github.com/ThanhThuw5206/NT132---Kubernetes-System.git   # repo public
git switch tv2/kubernetes-service          # HEAD 2782c61
BOOKINFO_GEN="$(python3 scripts/prepare-bookinfo.py)"   # xác minh 14 resource, sinh manifest
sudo kubectl --kubeconfig=/etc/kubernetes/admin.conf apply -f "$BOOKINFO_GEN/namespace-baseline.json"
sudo kubectl --kubeconfig=/etc/kubernetes/admin.conf apply -f "$BOOKINFO_GEN/workloads.json"
```

Kết quả: namespace `bookinfo` (injection **disabled**), 4 Service + ServiceAccount + Deployment tạo thành công. Rollout: `details-v1`, `ratings-v1`, `reviews-v2`, `productpage-v1` đều **1/1 Running** (baseline không sidecar); `reviews-v1`/`reviews-v3` = 0/0.

**Service (ClusterIP, port 9080):**

| Service | ClusterIP |
|---|---|
| productpage | 10.99.71.168 |
| details | 10.107.157.78 |
| reviews | 10.101.205.59 |
| ratings | 10.105.126.134 |

**Pod baseline (ban đầu, đều ở wk-01):**

| Pod | IP | Image |
|---|---|---|
| details-v1-5985fd9c47-4xkqw | 10.244.95.13 | examples-bookinfo-details-v1:1.20.3 |
| productpage-v1-7746cc5c98-4zffv | 10.244.95.16 | examples-bookinfo-productpage-v1:1.20.3 |
| ratings-v1-744c948b6c-rqpcj | 10.244.95.14 | examples-bookinfo-ratings-v1:1.20.3 |
| reviews-v2-7448df9b9c-zd7t9 | 10.244.95.15 | examples-bookinfo-reviews-v2:1.20.3 |

## 4. APP01 baseline — website có sao

Port-forward `svc/productpage 9080:9080` trên cp-01, rồi `curl http://127.0.0.1:9080/productpage`:

- `HTTP 200`.
- Nội dung có `Book Reviews`, `Reviewer1`, **9× `glyphicon-star`**, **không** có `Ratings service is currently unavailable`.
- → Chuỗi `productpage → reviews-v2 → ratings` thông, hiển thị sao. **Đạt (baseline).**

## 5. SVC01 — Service trỏ đúng Pod

| Thành phần | Giá trị quan sát |
|---|---|
| Service `ratings` | ClusterIP `10.105.126.134`, port/targetPort `9080`, selector `app=ratings` |
| Pod `ratings-v1-744c948b6c-rqpcj` | UID `13fff955-6215-457b-89ef-785a4aaac999`, IP `10.244.95.14`, labels `app=ratings,version=v1` |
| EndpointSlice `ratings-f887l` | endpoint `10.244.95.14:9080` |

Selector `app=ratings` khớp label Pod; endpoint IP = Pod IP. **Đạt** (chờ TV1 chạy lại).

## 6. SVC02 — thay Pod, tên Service giữ nguyên

`rollout restart deployment/ratings-v1`.

| | Trước | Sau |
|---|---|---|
| Pod | ratings-v1-744c948b6c-rqpcj | ratings-v1-6678fcbdc5-g5mmc |
| UID | 13fff955-6215-457b-89ef-785a4aaac999 | 6004ecf3-fff2-4dea-97fb-78d0758b12c4 |
| Pod IP | 10.244.95.14 | 10.244.95.17 |
| Service ClusterIP | 10.105.126.134 | 10.105.126.134 (không đổi) |
| Sao trên web | — | 9 (ratings vẫn gọi được qua tên) |

Pod mới (UID/IP khác), Service tên + ClusterIP không đổi, web vẫn có sao. **Đạt** (chờ TV3 chạy lại). Phân biệt Pod bằng **UID** (IP có thể tái dùng).

## 7. SVC03 — một tên, nhiều backend

Replica gốc = 1. Scale lên 2 rồi về 1.

| Trạng thái | Pod ratings | EndpointSlice |
|---|---|---|
| 2 replica | g5mmc (10.244.95.17, wk-01) + wq26x (UID 2566c157-68f7-41be-93c0-e35b5cd7be62, 10.244.26.96, **wk-02**) | 2 endpoint: 10.244.95.17, 10.244.26.96 |
| về 1 replica | còn 1 Pod | 1 endpoint |

2 replica = 2 endpoint (trải 2 worker), tên + ClusterIP không đổi. **Đạt** (chờ TV3 chạy lại). Không kết luận chia tải đều chỉ từ response giống nhau.

## 8. Tắt cụm

`gcloud compute instances stop wk-01 wk-02` rồi `stop cp-01` → cả 3 **TERMINATED**. App nằm trong etcd (disk) nên bật lại vẫn còn, **không phải deploy lại**.

## 9. Việc còn lại (buổi sau)

1. **TV3 cài Istio** (`istio-system`, gateway NodePort 30080).
2. TV2: bật injection namespace `bookinfo` + rollout → **APP01 qua gateway**; áp Gateway/VirtualService (route `/productpage`).
3. TV2: **SEC01** mTLS STRICT (hai nguồn 200), **SEC02** AuthorizationPolicy (reviews 200 / productpage 403) rồi phục hồi baseline.
4. Thử **NodePort 30080** hai worker → bàn giao TV1 nối LB.
5. Điền [phiếu app](../application-handover.md) → TV3 làm OBS01/SEC03/SVC04.
6. Kiểm tra chéo: TV1/TV3 chạy lại SVC01–03 để chốt nghiệm thu.
