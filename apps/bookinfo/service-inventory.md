# Inventory Bookinfo · thiết kế đã chốt, runtime còn chờ

Cập nhật local 06/11/2026. Bảng điền trước **thiết kế** từ source ghim, không phải dữ liệu quan sát trên cụm. UID/IP/endpoint/imageID/giờ và kết quả chờ TV2 deploy; không suy đoán hoặc ghi Đạt từ unit test. Không đưa Secret/token/kubeconfig vào đây.

## Source và cấu hình chuẩn bị

| Trường | Giá trị thiết kế / nơi đối chiếu |
|---|---|
| Upstream | Istio tag 1.30.7, samples/bookinfo/platform/kube/bookinfo.yaml |
| Giấy phép/hash | [source-lock.json](source-lock.json), [upstream](upstream/) |
| Namespace | bookinfo |
| Baseline | prepare-bookinfo.py sinh injection disabled; sau review mới bật mesh/rollout |
| Website | GET /productpage; product ID 0 |
| Target API | GET http://ratings.bookinfo.svc.cluster.local:9080/ratings/0 |
| Source / thời điểm | Chưa ghi commit/hash gói và thời gian chạy thực |
| Context / người thao tác / chạy lại | Chưa bàn giao/xác nhận |

## Service và backend

| Service | Nguồn gọi | Kiểu dự kiến | port | targetPort dự kiến | selector dự kiến | UID / ClusterIP thực | Endpoint Ready (Pod/UID/IP/node) thực |
|---|---|---|---|---|---|---|---|
| productpage | gateway/baseline port-forward | ClusterIP | 9080 | 9080 | app=productpage | Chưa đo | Chưa đo |
| details | productpage | ClusterIP | 9080 | 9080 | app=details | Chưa đo | Chưa đo |
| reviews | productpage | ClusterIP | 9080 | 9080 | app=reviews | Chưa đo | Chưa đo |
| ratings | reviews-v2 | ClusterIP | 9080 | 9080 | app=ratings | Chưa đo | Chưa đo |
| istio-ingressgateway (istio-system) | client/LB | NodePort | 80 | 80 | istio=ingressgateway | Chưa đo | Chưa đo; nodePort dự kiến 30080 |

Lấy số liệu bằng `kubectl --context "$CTX" -n bookinfo get svc,endpointslice,pods -o wide` và `kubectl --context "$CTX" -n bookinfo get service ratings -o yaml`. Endpoint Ready phải khớp selector/Pod UID, không chỉ tên Pod. Với gateway, đối chiếu Service/targetPort/selector thật TV3 giao; giá trị dự kiến không thay số đo.

## Deployment, ServiceAccount và nguồn thử

| Deployment | Replica thiết kế | Replica thực/gốc trước thử | SA dự kiến | Labels dự kiến | Pod UID/container thử/imageID thực |
|---|---|---|---|---|---|
| productpage-v1 | 1 | Chưa đo | bookinfo-productpage | app=productpage, version=v1 | Chưa đo |
| details-v1 | 1 | Chưa đo | bookinfo-details | app=details, version=v1 | Chưa đo |
| reviews-v2 | 1 | Chưa đo | bookinfo-reviews | app=reviews, version=v2 | Chưa đo |
| ratings-v1 | 1 | Chưa đo | bookinfo-ratings | app=ratings, version=v1 | Chưa đo |
| reviews-v1 / reviews-v3 | 0 / 0 | Chưa đo | bookinfo-reviews | app=reviews, version=v1/v3 | Chưa đo |

- Hợp lệ: reviews-v2, SA bookinfo-reviews, GET /ratings/0 → 200/body JSON có ratings.
- Đối chứng: productpage-v1, SA bookinfo-productpage, gọi **thẳng** cùng API → 200 ở baseline/C1, 403 ở C2; tách với gọi website qua gateway.
- Container thử: app nếu đủ curl/getent, hoặc debug **cùng Pod** đã có quyền, UID khác 1337, ghi imageID. Theo [runbook §4](../../docs/tv2-runbook.md); sau rollout chọn lại Pod/UID.
- Proxy: trước mesh chủ động không proxy; sau mesh cần Pod/app Ready và proxy Ready ở container thường hoặc restartable init. Chưa xác nhận runtime.

## Tag nguồn và digest runtime

| Workload | Image/tag nguồn ghim | Image/tag quan sát | imageID/digest quan sát |
|---|---|---|---|
| productpage | registry.istio.io/release/examples-bookinfo-productpage-v1:1.20.3 | Chưa đo | Chưa đo |
| details | registry.istio.io/release/examples-bookinfo-details-v1:1.20.3 | Chưa đo | Chưa đo |
| reviews-v2 | registry.istio.io/release/examples-bookinfo-reviews-v2:1.20.3 | Chưa đo | Chưa đo |
| ratings | registry.istio.io/release/examples-bookinfo-ratings-v1:1.20.3 | Chưa đo | Chưa đo |
| Debug (nếu cần) | nicolaka/netshoot:v0.14 | Chưa chạy | Chưa đo |

prepare-bookinfo.py thêm probes/resources cho lab; giữ preparation.json cùng inventory để truy ra cấu hình. Theo dõi readiness/OOM/events/tài nguyên thực rồi phối hợp TV1/TV2 điều chỉnh. Baseline, route, SVC01–03, C1–C4, rollback và người chạy lại ghi riêng theo [mẫu evidence](../../docs/evidence/templates/test-result.md).
