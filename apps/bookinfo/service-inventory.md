# Inventory Bookinfo · thiết kế + runtime baseline 06/11/2026

Cập nhật 06/11/2026: đã deploy **baseline (chưa Istio)** và điền số liệu quan sát của phiên này. Các cột runtime cho giai đoạn mesh (gateway, proxy) vẫn chờ TV3 cài Istio. Kết quả do TV2 chạy một mình, **chờ kiểm tra chéo** TV1/TV3. Chi tiết phiên: [TV2-baseline-20261106.md](../../docs/evidence/TV2-baseline-20261106.md). Không đưa Secret/token/kubeconfig vào đây.

## Source và cấu hình chuẩn bị

| Trường | Giá trị thiết kế / nơi đối chiếu |
|---|---|
| Upstream | Istio tag 1.30.7, samples/bookinfo/platform/kube/bookinfo.yaml |
| Giấy phép/hash | [source-lock.json](source-lock.json), [upstream](upstream/) |
| Namespace | bookinfo |
| Baseline | prepare-bookinfo.py sinh injection disabled; sau review mới bật mesh/rollout |
| Website | GET /productpage; product ID 0 |
| Target API | GET http://ratings.bookinfo.svc.cluster.local:9080/ratings/0 |
| Source / thời điểm | branch tv2/kubernetes-service `2782c61`; deploy baseline 06/11/2026 (~14:4x UTC) |
| Context / người thao tác / chạy lại | admin.conf qua `sudo kubectl` trên cp-01; TV2 chạy; chờ TV1/TV3 chạy lại |

## Service và backend

| Service | Nguồn gọi | Kiểu dự kiến | port | targetPort dự kiến | selector dự kiến | UID / ClusterIP thực | Endpoint Ready (Pod/UID/IP/node) thực |
|---|---|---|---|---|---|---|---|
| productpage | gateway/baseline port-forward | ClusterIP | 9080 | 9080 | app=productpage | ClusterIP 10.99.71.168 | Pod 10.244.95.16 @ wk-01 |
| details | productpage | ClusterIP | 9080 | 9080 | app=details | ClusterIP 10.107.157.78 | Pod 10.244.95.13 @ wk-01 |
| reviews | productpage | ClusterIP | 9080 | 9080 | app=reviews | ClusterIP 10.101.205.59 | Pod reviews-v2 10.244.95.15 @ wk-01 |
| ratings | reviews-v2 | ClusterIP | 9080 | 9080 | app=ratings | ClusterIP 10.105.126.134 | EndpointSlice ratings-f887l → 10.244.95.14 (Pod UID 13fff955…) |
| istio-ingressgateway (istio-system) | client/LB | NodePort | 80 | 80 | istio=ingressgateway | Chưa đo (chờ Istio) | Chưa đo; nodePort dự kiến 30080 |

Lấy số liệu bằng `kubectl --context "$CTX" -n bookinfo get svc,endpointslice,pods -o wide` và `kubectl --context "$CTX" -n bookinfo get service ratings -o yaml`. Endpoint Ready phải khớp selector/Pod UID, không chỉ tên Pod. Với gateway, đối chiếu Service/targetPort/selector thật TV3 giao; giá trị dự kiến không thay số đo.

## Deployment, ServiceAccount và nguồn thử

| Deployment | Replica thiết kế | Replica thực/gốc trước thử | SA dự kiến | Labels dự kiến | Pod UID/container thử/imageID thực |
|---|---|---|---|---|---|
| productpage-v1 | 1 | 1 (Ready) | bookinfo-productpage | app=productpage, version=v1 | Pod ...7746cc5c98-4zffv |
| details-v1 | 1 | 1 (Ready) | bookinfo-details | app=details, version=v1 | Pod ...5985fd9c47-4xkqw |
| reviews-v2 | 1 | 1 (Ready) | bookinfo-reviews | app=reviews, version=v2 | Pod ...7448df9b9c-zd7t9 |
| ratings-v1 | 1 | 1 (Ready) | bookinfo-ratings | app=ratings, version=v1 | Pod ...744c948b6c-rqpcj, UID 13fff955… (SVC02 → 6004ecf3…) |
| reviews-v1 / reviews-v3 | 0 / 0 | 0 / 0 (đúng thiết kế) | bookinfo-reviews | app=reviews, version=v1/v3 | không có Pod |

- Hợp lệ: reviews-v2, SA bookinfo-reviews, GET /ratings/0 → 200/body JSON có ratings.
- Đối chứng: productpage-v1, SA bookinfo-productpage, gọi **thẳng** cùng API → 200 ở baseline/C1, 403 ở C2; tách với gọi website qua gateway.
- Container thử: app nếu đủ curl/getent, hoặc debug **cùng Pod** đã có quyền, UID khác 1337, ghi imageID. Theo [runbook §4](../../docs/tv2-runbook.md); sau rollout chọn lại Pod/UID.
- Proxy: trước mesh chủ động không proxy; sau mesh cần Pod/app Ready và proxy Ready ở container thường hoặc restartable init. Chưa xác nhận runtime.

## Tag nguồn và digest runtime

| Workload | Image/tag nguồn ghim | Image/tag quan sát | imageID/digest quan sát |
|---|---|---|---|
| productpage | registry.istio.io/release/examples-bookinfo-productpage-v1:1.20.3 | khớp tag nguồn (06/11) | digest chưa ghi |
| details | registry.istio.io/release/examples-bookinfo-details-v1:1.20.3 | khớp tag nguồn (06/11) | digest chưa ghi |
| reviews-v2 | registry.istio.io/release/examples-bookinfo-reviews-v2:1.20.3 | khớp tag nguồn (06/11) | digest chưa ghi |
| ratings | registry.istio.io/release/examples-bookinfo-ratings-v1:1.20.3 | khớp tag nguồn (06/11) | digest chưa ghi |
| Debug (nếu cần) | nicolaka/netshoot:v0.14 | Chưa chạy | Chưa đo |

prepare-bookinfo.py thêm probes/resources cho lab; giữ preparation.json cùng inventory để truy ra cấu hình. Theo dõi readiness/OOM/events/tài nguyên thực rồi phối hợp TV1/TV2 điều chỉnh. Baseline, route, SVC01–03, C1–C4, rollback và người chạy lại ghi riêng theo [mẫu evidence](../../docs/evidence/templates/test-result.md).
