# Bookinfo · Ứng dụng TV2 chọn và cấu hình tích hợp local

TV2 chọn **Bookinfo** từ samples Istio `1.30.7`, đồng bộ [versions.env](../../config/versions.env). App kiểm chứng Service → selector → EndpointSlice → Pod qua `productpage → reviews-v2 → ratings`, đồng thời productpage gọi details. Cập nhật 06/11/2026 chuẩn bị trên laptop; chưa deploy/nghiệm thu cloud.

## Source và chuẩn bị workload

Source upstream tại [upstream](upstream/), kèm Apache-2.0 và checksum/provenance [source-lock.json](source-lock.json). Chạy từ root repo:

```bash
python3 scripts/prepare-bookinfo.py
```

Lệnh xác minh source/hash rồi sinh thư mục mới `.generated/bookinfo-*`; không tải package, gọi Kubernetes hoặc apply. Thêm `--check` nếu chỉ muốn xác minh mà chưa sinh output. `namespace-baseline.json` tắt injection; `workloads.json` chứa Service/SA/Deployment, probes/tài nguyên lab; `preparation.json` là metadata. Chỉ hai file đầu là resource. Không cần tải full release Istio để lấy app; TV3 cài Istio nền qua Helm riêng.

Image dự kiến giữ registry/tag upstream: `registry.istio.io/release/examples-bookinfo-*:1.20.3`. Đây là tag nguồn, **chưa phải digest/imageID runtime**. TV2 điền tag/imageID, Pod UID, Service/EndpointSlice và kết quả thật vào [inventory](service-inventory.md) sau deploy. Giữ reviews-v2 một replica cho cạnh ratings, reviews-v1/v3 bằng 0. Probes/resources là cấu hình lab cần theo dõi, không chứng minh runtime đã đủ tài nguyên.

## Config mesh và policy

[application.bookinfo.json](application.bookinfo.json) là config thiết kế cho [renderer](../../scripts/render-application.py), có thể render trực tiếp trên laptop:

```bash
python3 scripts/tv3.py render apps/bookinfo/application.bookinfo.json
```

| Trường | Giá trị / phạm vi |
|---|---|
| Namespace | bookinfo; baseline tắt injection, sau mesh Ready mới bật/rollout |
| Entry / Service port | productpage:9080 |
| Gateway paths | Exact /productpage, /login, /logout, /api/v1/products; prefix /static/, /api/v1/products/; không route toàn bộ / |
| Target Service / Pod port | ratings:9080 / TCP 9080 |
| Target labels | app=ratings |
| Caller / ServiceAccount | app=reviews / bookinfo-reviews |
| API được phép | **GET /ratings/0**, cùng ID 0 của website /productpage |
| Nguồn đối chứng | productpage-v1, SA bookinfo-productpage, gọi thẳng ratings |

Renderer hỗ trợ `public_http_matches` tường minh; `public_path_prefix` là fallback cho config cũ không có trường này. Route website không mở thêm quyền vào ratings: AuthorizationPolicy chỉ cho principal reviews GET đúng path. [Productpage](https://raw.githubusercontent.com/istio/istio/1.30.7/samples/bookinfo/src/productpage/productpage.py) dùng ID 0; [reviews](https://raw.githubusercontent.com/istio/istio/1.30.7/samples/bookinfo/src/reviews/reviews-application/src/main/java/application/rest/LibertyRestEndpoint.java) chuyển ID đó tới ratings.

## Luồng bàn giao

1. TV1 giao cụm Ready/quyền/context; TV3/TV2 kiểm tra NET01 trên Calico hiện có.
2. TV2 deploy baseline không injection từ output chuẩn bị, chứng minh website/DNS/HTTP/endpoint; TV1 review.
3. TV3 cài Istio/gateway/Prometheus/Kiali; TV2 bật injection, rollout app, áp route và kiểm tra app/proxy Ready.
4. TV2 chạy Service/STRICT/AuthorizationPolicy từng lớp/phục hồi; TV3 quan sát/NetworkPolicy/selector lab/kiểm tra chéo.
5. Điền inventory/[phiếu app](../../docs/application-handover.md), lưu evidence thật và người chạy lại.

Lệnh, công cụ app/debug container có curl + getent, native proxy Ready và rollback ở [runbook TV2](../../docs/tv2-runbook.md). Không lấy cố định 2/2 làm tiêu chí proxy; không apply nguyên output renderer hoặc chạy cloud khi chỉ chuẩn bị local.
