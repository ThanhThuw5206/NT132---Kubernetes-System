# TV2 · Giải thích công việc để ôn và bảo vệ

Tài liệu tự học cho TV2: khái niệm → cấu hình của TV2 → từng việc đã làm và vì sao → lệnh dùng để làm gì → slide demo → câu hỏi bảo vệ. Dùng kèm nhật ký [baseline 06/11](evidence/TV2-baseline-20261106.md) và [mesh 10/11](evidence/TV2-mesh-20261110.md).

## 1. Bạn đang chứng minh điều gì?

Đề tài: khảo sát **Kubernetes Service**. Vấn đề cốt lõi: **Pod sinh ra/chết liên tục, mỗi lần đổi IP** → làm sao app gọi app khác mà không cần biết IP? Trả lời: **Service** — tên + IP ảo cố định đứng trước nhóm Pod.

Dùng website mẫu **Bookinfo**:

```
Trình duyệt → gateway → productpage → reviews(v2) → ratings
                                     → details
```

TV2 tập trung cặp **reviews-v2 → ratings** để trả lời 2 câu:
1. Gọi tên `ratings` có tới đúng Pod không? → Service/selector/EndpointSlice (bài **SVC**).
2. Ai được phép gọi `ratings`? → mTLS + AuthorizationPolicy (bài **SEC**).

## 2. Khái niệm cốt lõi

| Khái niệm | Giải thích |
|---|---|
| Pod | "gói" chứa container đang chạy; có IP riêng nhưng **tạm thời**. |
| Service (ClusterIP) | "tổng đài" có **tên + ClusterIP cố định**; gọi tên → chuyển tới Pod thật. |
| selector | Service dùng **nhãn** để chọn Pod, ví dụ `app=ratings`. |
| EndpointSlice | **danh sách IP Pod khỏe** đứng sau Service; tự cập nhật khi Pod đổi. |
| DNS (CoreDNS) | dịch tên `ratings` → ClusterIP. |
| port / targetPort | cổng Service / cổng trong Pod (ở đây đều 9080). |
| sidecar (istio-proxy) | container phụ Istio chèn vào mỗi Pod; mọi traffic đi qua nó → Pod mesh là **2/2**. |
| mTLS STRICT | bắt buộc kết nối mã hóa + xác thực 2 chiều; client không sidecar bị từ chối. |
| AuthorizationPolicy | luật "ai được gọi gì" theo **danh tính + method/path**. |
| ServiceAccount (SA) | danh tính Pod; reviews = `bookinfo-reviews`, productpage = `bookinfo-productpage`. |
| NodePort / gateway | `istio-ingressgateway` mở cổng **30080** làm cửa vào. |

## 3. Cấu hình của TV2 là gì?

Toàn bộ cấu hình gói trong **1 file**: `apps/bookinfo/application.bookinfo.json`. Nó khai báo app:

```json
{
  "namespace": "bookinfo",
  "entry_service": "productpage",
  "target_service": "ratings",
  "target_labels": {"app": "ratings"},
  "allowed_caller_labels": {"app": "reviews"},
  "allowed_service_account": "bookinfo-reviews",
  "allowed_http_methods": ["GET"],
  "allowed_http_paths": ["/ratings/0"]
}
```

Script `scripts/render-application.py` đọc file này → **tự sinh 6 manifest**:

| File | Là gì | Bước |
|---|---|---|
| namespace.json | namespace bật injection | mesh |
| gateway.json | Istio Gateway (cửa vào) | route |
| route.json | VirtualService (`/productpage`→productpage) | route |
| mtls.json | PeerAuthentication STRICT | SEC01 |
| authorization.json | AuthorizationPolicy | SEC02 |
| network-policy.json | NetworkPolicy (lớp mạng, TV3) | SEC03 |

Ý nghĩa: **1 nguồn sự thật (JSON) → máy sinh tất cả**, tránh viết tay YAML dễ sai. Cộng thêm **workload Bookinfo** (Deployment/Service/SA) do `prepare-bookinfo.py` sinh từ source upstream đã ghim hash.

## 4. Từng việc đã làm + vì sao

### 4.1 Kết nối cụm

| Lệnh | Làm gì | Vì sao |
|---|---|---|
| `gcloud auth login` | đăng nhập Google | thao tác bằng tài khoản bạn |
| `gcloud compute start-iap-tunnel cp-01 22 ...` | mở đường ống laptop→cổng 22 cp-01 qua IAP | VM không mở SSH ra Internet; IAP là cửa an toàn |
| `ssh -i ...google_compute_engine -p 2222 ...@localhost` | SSH qua đường ống | vào shell Linux cp-01 |
| `sudo kubectl --kubeconfig=/etc/kubernetes/admin.conf` | kubectl quyền admin cụm | TV2 không có kubeconfig riêng; mượn admin trong phiên |

Lỗi "Remote side closed / 4003" = VM đang tắt. Lỗi "bad permissions" = file khóa mở quyền quá rộng, siết bằng `icacls`.

### 4.2 Deploy baseline (chưa Istio)

| Lệnh | Làm gì |
|---|---|
| `python3 scripts/prepare-bookinfo.py` | xác minh hash source rồi sinh manifest baseline |
| `kubectl apply -f namespace-baseline.json` | tạo namespace bookinfo |
| `kubectl apply -f workloads.json` | tạo Service+SA+Deployment |
| `kubectl rollout status deployment/...` | chờ Pod chạy xong |

Làm baseline trước để chứng minh **Service của Kubernetes hoạt động độc lập**, trước khi thêm Istio (tách lớp để dễ tìm lỗi).

### 4.3 Ba bài Service (trọng tâm)

- **SVC01** — `get svc/pods/endpointslice`: chứng minh *tên → ClusterIP → selector chọn Pod → EndpointSlice ghi IP Pod*. Endpoint IP = Pod IP.
- **SVC02** — `rollout restart deployment/ratings-v1`: Pod mới UID `13fff955…`→`6004ecf3…`, IP `.14`→`.17`, **ClusterIP giữ** `10.105.126.134`, web vẫn sao. Phân biệt Pod bằng **UID** (IP có thể tái dùng).
- **SVC03** — `scale --replicas=2`: EndpointSlice 1 IP → 2 IP (2 worker) → 1. Service theo dõi tập Pod thay đổi.

### 4.4 Phần mesh

- **APP01 qua gateway**: port-forward `istio-ingressgateway` → `/productpage` 200 + sao; request đi `gateway → VirtualService → productpage → reviews-v2 → ratings`.
- **2 nguồn test (netshoot)**: app Bookinfo không có `curl` → `kubectl debug <pod> -c probe --image=nicolaka/netshoot ...` gắn container có curl **vào chính Pod** → giữ đúng danh tính SA của Pod. Không exec vào `istio-proxy`.
- **SEC01** `apply mtls.json`: STRICT; 2 nguồn có sidecar vẫn 200.
- **SEC02** `apply authorization.json`: chỉ cho principal `bookinfo-reviews` GET /ratings/0 → **reviews 200 / productpage 403**, log Envoy `rbac_access_denied`. Rồi `delete` cả 2 để phục hồi baseline.

## 5. Từ điển lệnh

| Lệnh | Nghĩa |
|---|---|
| `kubectl get <loại>` | liệt kê (pods, svc, nodes, endpointslice) |
| `-n bookinfo` / `-l app=ratings` | theo namespace / theo nhãn |
| `-o wide / jsonpath / yaml` | định dạng output |
| `kubectl apply/delete -f file` | tạo-cập nhật / xóa |
| `kubectl exec <pod> -c <container> -- lệnh` | chạy lệnh trong container |
| `kubectl rollout restart/status` | thay Pod / chờ xong |
| `kubectl scale --replicas=N` | đổi số bản sao |
| `kubectl port-forward svc/x 8080:80` | nối cổng để test |
| `curl -s -o /dev/null -w '%{http_code}'` | gọi HTTP, in mã trạng thái |
| `--noproxy '*'` | gọi thẳng, bỏ proxy môi trường |

## 6. Ba slide demo

1. **Service tìm đúng Pod (SVC01/02)**: tên cố định, Pod tạm thời; thay Pod UID/IP đổi, ClusterIP giữ, web vẫn sao.
2. **Một Service nhiều backend (SVC03)**: scale 1→2 Pod, EndpointSlice 2 IP ở 2 worker.
3. **Ai được phép gọi? (SEC01/02)**: reviews(bookinfo-reviews) 200 vs productpage(bookinfo-productpage) 403 + log RBAC; phân quyền theo danh tính + mTLS, không theo IP.

## 7. Câu hỏi bảo vệ

1. **Pod đổi IP client sao biết?** → gọi tên Service → DNS → ClusterIP → EndpointSlice tới Pod Ready (SVC02).
2. **IP tái dùng phân biệt sao?** → dùng UID.
3. **Sao productpage 403 còn reviews 200 dù cùng gọi ratings?** → AuthorizationPolicy chỉ cho principal `bookinfo-reviews`; productpage SA khác → Envoy chặn (`rbac_access_denied`). Phân quyền theo danh tính, không theo mạng.
4. **mTLS STRICT để làm gì?** → ép kết nối mã hóa/xác thực; client ngoài mesh bị từ chối.
5. **Sao Pod 2/2?** → app + sidecar istio-proxy.
