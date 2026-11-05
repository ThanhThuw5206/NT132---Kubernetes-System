# apps/bookinfo · Ứng dụng mẫu do TV2 chọn

Ứng dụng kiểm chứng Kubernetes Service của nhóm là **Bookinfo**, lấy từ samples của release Istio đã ghim trong [`config/versions.env`](../../config/versions.env) (`ISTIO_VERSION=1.30.7`). Bookinfo là nhiều microservice gọi nhau qua tên Service nội bộ, phù hợp để chứng minh DNS → selector → EndpointSlice → Pod và tách lỗi quyền truy cập.

## Nguồn và giấy phép

| Trường | Giá trị |
|---|---|
| Nguồn | https://github.com/istio/istio — thư mục `samples/bookinfo` |
| Release/tag | `1.30.7` (đồng bộ với `ISTIO_VERSION`); manifest lấy từ gói release `istio-1.30.7` |
| Giấy phép | Apache License 2.0 |
| Image | Dùng image `docker.io/istio/examples-bookinfo-*` đã ghim trong manifest của **đúng release 1.30.7**, không dùng tag `latest` |

**Không hard-code tag image trong repo.** Tag image Bookinfo gắn với từng release Istio; để đúng digest, TV2 áp manifest trực tiếp từ thư mục `samples/bookinfo/platform/kube/bookinfo.yaml` của gói `istio-1.30.7` đã tải, rồi **ghi lại tag/digest thực tế** quan sát được vào [`service-inventory.md`](service-inventory.md). Đây là cách "ghim theo release" mà README gốc yêu cầu.

## Ánh xạ Bookinfo vào renderer tích hợp

[`scripts/render-application.py`](../../scripts/render-application.py) sinh Gateway/VirtualService/PeerAuthentication/AuthorizationPolicy/NetworkPolicy từ `config/application.json`. File [`application.bookinfo.json`](application.bookinfo.json) trong thư mục này là **bản tham chiếu** đã điền sẵn cho Bookinfo — copy sang `config/application.json` (file đó bị `.gitignore`, không commit):

| Ô renderer | Giá trị Bookinfo | Ý nghĩa |
|---|---|---|
| namespace | `bookinfo` | Namespace ứng dụng, bật `istio-injection=enabled` |
| entry_service / port | `productpage` / `9080` | Service nhận request từ ingress gateway |
| public_path_prefix | `/productpage` | Đường vào website qua gateway |
| target_service / port / target_port | `ratings` / `9080` / `9080` | Service đích để thử DNS/selector/EndpointSlice |
| target_labels | `app=ratings` | Selector Pod đích |
| allowed_caller_labels | `app=reviews` | Nguồn hợp lệ (reviews-v2 gọi ratings) |
| allowed_service_account | `bookinfo-reviews` | Danh tính workload được phép gọi ratings |
| allowed_http_methods / paths | `GET` / `/ratings/1` | API thử; ca dùng đúng sách ID 1 |

Luồng nội bộ: `gateway → productpage → reviews(v2) → ratings`. `productpage` cũng gọi `details`. Nguồn đối chứng bị chặn là `productpage` (ServiceAccount `bookinfo-productpage`, gọi thẳng `ratings` không được phép).

## Thứ tự triển khai (chi tiết trong [docs/tv2-runbook.md](../../docs/tv2-runbook.md))

1. TV3 xác nhận Istiod + ingress gateway Ready.
2. `kubectl apply -f "$GEN/namespace.json"` (namespace đã bật injection) — `$GEN` là thư mục renderer vừa in.
3. Áp manifest Bookinfo từ samples release 1.30.7 vào namespace `bookinfo`.
4. Giữ `reviews-v2` (scale `reviews-v1`, `reviews-v3` về 0) để cạnh reviews → ratings ổn định.
5. `kubectl apply -f "$GEN/gateway.json"` và `"$GEN/route.json"`.
6. Port-forward gateway, mở `/productpage`, xác nhận có điểm sao.
7. Điền [`service-inventory.md`](service-inventory.md) bằng dữ liệu thật và bàn giao [`docs/application-handover.md`](../../docs/application-handover.md) cho TV3.
