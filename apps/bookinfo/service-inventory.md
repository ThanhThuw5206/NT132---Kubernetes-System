# Inventory Bookinfo · thiết kế và số đo runtime

Cập nhật **06/11/2026** từ checkpoint cloud của phiên TV3. Đây là số đo tại một thời điểm sau injection, **trước các bài thay Pod/scale SVC02/SVC03**; tên/UID ratings phía dưới không đại diện cho Pod cuối buổi. Kết quả và trạng thái mới nhất chỉ ghi ở [TV3-status](../../docs/evidence/TV3-status.md). Chưa có thành viên khác chạy lại hoặc ký nhận.

## Baseline TV2 trước mesh · đã nhận commit `8260fc9`

TV2 ghi nhận phiên 06/11 trên source `2782c61`: namespace injection disabled, website HTTP 200/có 9 sao; SVC01–03 tự chạy, còn chờ kiểm tra chéo. Giữ đầy đủ nhật ký/số đo gốc tại [TV2-baseline-20261106](../../docs/evidence/TV2-baseline-20261106.md); đây là lịch sử trước các phép thử TV3 phía dưới, không phải trạng thái hiện tại để deploy lại.

| Mốc TV2 | Số đo lịch sử |
|---|---|
| Bốn Service ClusterIP | productpage `10.99.71.168`; details `10.107.157.78`; reviews `10.101.205.59`; ratings `10.105.126.134` — đều khớp bản chụp cuối TV3 |
| ratings trước SVC02 | `ratings-v1-744c948b6c-rqpcj`, UID `13fff955-6215-457b-89ef-785a4aaac999`, IP `10.244.95.14` |
| ratings sau SVC02 | `ratings-v1-6678fcbdc5-g5mmc`, UID `6004ecf3-fff2-4dea-97fb-78d0758b12c4`, IP `10.244.95.17`; ClusterIP giữ nguyên |
| SVC03 TV2 | Replica `1 → 2 → 1`; backend thứ hai UID `2566c157-68f7-41be-93c0-e35b5cd7be62`, IP `10.244.26.96` tại wk-02 |

Tên/UID/IP Pod thay đổi qua các lần restart/rollout và bài thay Pod; đọc theo mốc từng phiên. TV3 sau đó kiểm tra kỹ thuật độc lập Service/thay Pod/scale và mesh theo [TV3-status](../../docs/evidence/TV3-status.md), không ghi thay chữ ký người chạy lại hoặc suy Service UID gốc TV2 khi nhật ký chưa đo.

## Source, thời điểm và phạm vi

| Trường | Giá trị / bằng chứng |
|---|---|
| Upstream / giấy phép | Istio tag `1.30.7`, `samples/bookinfo/platform/kube/bookinfo.yaml`; [source lock](source-lock.json), [Apache LICENSE](upstream/LICENSE) |
| Source chạy | HEAD nền `2782c613950f64a0753724383612e0dc0d783044` cộng sửa đổi local theo `source-manifest.json`; SHA256 gói `e8e996ee6542ba1f12bacb731b6cecb39466426afce6813c6065af5d04ae105b` |
| Phiên / namespace | `kubernetes-admin@nt132` / `bookinfo`; sudo với admin.conf tại cp-01, không xuất kubeconfig ra laptop |
| Baseline trước mesh | HTTP website, reviews và ratings đều 200; người kiểm tra là tự động hóa TV3, TV1/TV2 review còn chờ |
| Sau injection | `pods-after-injection.json` được lưu trước khi cài đặt kết thúc lúc **2026-11-06 16:30:47 UTC**; Pod cũ đang xóa bị loại khỏi bảng dưới |
| Checkpoint Service / NodePort | **2026-11-06 16:38:42–16:38:45 UTC** (23:38:42–23:38:45 UTC+07:00) |
| Bằng chứng local | `.generated/tv3-cloud-setup-534ca265/checkpoint/.cloud-evidence/`: `setup-state.json`, `pods-after-injection.json`, `istio-services.json`, `istio-foundation.json`, `nodeport/service/service-snapshot.json`, `nodeport/summary.json` |
| Website / target API | GET `/productpage`; GET `http://ratings.bookinfo.svc.cluster.local:9080/ratings/0` |

Các trường chưa có trong checkpoint ghi **Chưa đo**, dù source đã có giá trị thiết kế. Không suy EndpointSlice từ riêng Pod Ready hoặc suy nghiệm thu public từ request nội bộ.

## Service và backend

| Service / namespace | Nguồn gọi theo thiết kế | Kiểu; port → targetPort | Selector | UID / ClusterIP quan sát | EndpointSlice Ready đã đối chiếu |
|---|---|---|---|---|---|
| productpage / bookinfo | gateway | Thiết kế: ClusterIP; 9080 → 9080 | Thiết kế: `app=productpage` | Chưa đo trong checkpoint | Chưa đo trong checkpoint |
| details / bookinfo | productpage | Thiết kế: ClusterIP; 9080 → 9080 | Thiết kế: `app=details` | Chưa đo trong checkpoint | Chưa đo trong checkpoint |
| reviews / bookinfo | productpage | Thiết kế: ClusterIP; 9080 → 9080 | Thiết kế: `app=reviews` | Chưa đo trong checkpoint | Chưa đo trong checkpoint |
| ratings / bookinfo | reviews-v2 | Quan sát: ClusterIP; TCP 9080 → 9080 | `app=ratings` | `d8da52cf-30dc-412b-895e-99892072e967` / `10.105.126.134` | Slice `ratings-f887l`: `10.244.95.34`, targetRef Pod/UID khớp dòng ratings bên dưới; Ready/serving=true, terminating=false |
| istio-ingressgateway / istio-system | client; frontend LB còn chờ | Quan sát: NodePort; TCP 80 → 80, nodePort **30080**; status TCP 15021 → 15021, nodePort 32192 | `app=istio-ingressgateway`, `istio=ingressgateway` | `768a06dc-0e4f-476b-9fa5-a6a0a69158d1` / `10.105.30.70` | Chưa đo EndpointSlice gateway trong checkpoint |

Gateway có `externalTrafficPolicy=Cluster`. Từ cp-01, hai URL `http://10.20.0.11:30080/productpage` và `http://10.20.0.12:30080/productpage` đều trả 200, có Reviewer1/Reviewer2 và 9 phần tử sao trong HTML tại thời điểm trên. Đây là kiểm tra NodePort nội bộ, chưa phải PUB01 từ ngoài VPC.

Lấy lại dữ liệu hiện tại bằng `kubectl --context "$CTX" -n bookinfo get svc,endpointslice,pods -o wide`; dùng `scripts/tv3.py service-snapshot config/application.json --context "$CTX"` cho ratings. Đối chiếu selector, port và targetRef UID/IP; sau thay Pod phải chụp lại.

## Pod, ServiceAccount và replica

Tên Node rút gọn trong bảng: `wk-01` và `wk-02` lần lượt là `wk-01.asia-southeast1-a.c.nt132-kubernetes-513805.internal` và `wk-02.asia-southeast1-a.c.nt132-kubernetes-513805.internal`.

| Workload / replica gốc trước thử | Pod sau injection | Pod UID | Pod IP / Node | ServiceAccount / labels ứng dụng |
|---|---|---|---|---|
| details-v1 / 1 | `details-v1-5f99cc7756-l6fh9` | `ddb8473c-985f-4d39-98c3-db5e1a5b368d` | `10.244.26.116` / wk-02 | `bookinfo-details`; `app=details,version=v1` |
| productpage-v1 / 1 | `productpage-v1-86bbb558b8-j4xnw` | `5c178d62-877f-4680-a303-fa57899a5a3e` | `10.244.95.35` / wk-01 | `bookinfo-productpage`; `app=productpage,version=v1` |
| ratings-v1 / 1 | `ratings-v1-745569b87c-s2zs2` | `8b082360-5ec8-4f94-ab48-29039b8ad241` | `10.244.95.34` / wk-01 | `bookinfo-ratings`; `app=ratings,version=v1` |
| reviews-v2 / 1 | `reviews-v2-688cf6d5d5-62htc` | `03224cc7-68e0-4d65-b061-a47620a8b7d0` | `10.244.26.117` / wk-02 | `bookinfo-reviews`; `app=reviews,version=v2` |
| reviews-v1 / reviews-v3 | Thiết kế replica 0 / 0; checkpoint này không chứa Deployment JSON để ghi số đo riêng | — | — | Thiết kế: `bookinfo-reviews` |

Cả bốn Pod được liệt kê có app Ready và `istio-proxy` Ready dạng restartable init container; restart count app/proxy đều 0 tại checkpoint. Replica gốc lấy từ `setup-state.json`; bảng không thay bản chụp Deployment sau mỗi lần scale. Pod productpage cũ có `deletionTimestamp` không được tính là backend hiện hành.

Nguồn hợp lệ theo thiết kế là reviews-v2/SA `bookinfo-reviews`; nguồn đối chứng là productpage-v1/SA `bookinfo-productpage`, gọi thẳng cùng `/ratings/0`. Container thử phải có curl/getent, ở đúng Pod và UID khác 1337; app/debug container thực tế dùng cho từng bài test được ghi trong evidence của bài đó. Checkpoint này chưa có digest debug container.

## Image và digest quan sát

Image/tag quan sát của cả bốn app trùng nguồn ghim `registry.istio.io/release/*:1.20.3`. Các digest dưới đây lấy từ `status.containerStatuses[].imageID`, không suy từ tag:

| Container | Image/tag quan sát | SHA256 trong imageID |
|---|---|---|
| details | `registry.istio.io/release/examples-bookinfo-details-v1:1.20.3` | `a49731e1fc05d7c24a4103709f41d64180bed989b251625f4c31ba63022e303b` |
| productpage | `registry.istio.io/release/examples-bookinfo-productpage-v1:1.20.3` | `1e339866b782d22b063539d19c87b4682291c889e67c3d4abdea947bef917958` |
| ratings | `registry.istio.io/release/examples-bookinfo-ratings-v1:1.20.3` | `aad8f7bb46664704eecd92d9ebe8563e3e41571e2301f593cc521301b14ae51d` |
| reviews | `registry.istio.io/release/examples-bookinfo-reviews-v2:1.20.3` | `09b92ca16738b5bded2ae66ba0a4b21d32e86d8b6ddb34331abfe1179d8c6298` |
| istio-proxy, cả bốn Pod | `registry.istio.io/release/proxyv2:1.30.7` | `f8f963340f92550b7b67228b0319fba7963a98137bdaace3f593da186427e717` |
| Debug | Thiết kế `nicolaka/netshoot:v0.14`; chưa có số đo trong checkpoint này | Chưa đo |

ImageID đầy đủ dùng cùng repository như cột image, thay `:tag` bằng `@sha256:DIGEST`. Giữ JSON gốc để kiểm tra lại. Bảng này không đánh giá RAM thực/OOM, không thay bằng chứng policy/phục hồi hoặc kiểm tra chéo theo [ma trận TV3](../../docs/tv3-test-matrix.md).

## Số đo cuối sau thay Pod/scale · 07/11/2026

Bản chụp trước shutdown lúc **00:01:20 UTC+07** trong `final-evidence/.cloud-evidence/final/bookinfo.json`; bảng checkpoint phía trên được giữ để so sánh. Sau đó API xác nhận cả ba VM TERMINATED lúc **00:06:38**. Số liệu là lịch sử của phiên này, cần đọc lại sau khi bật lab.

| Service | UID / ClusterIP | port → targetPort; selector | Endpoint Ready / Pod UID / IP / node |
|---|---|---|---|
| details | `4315873f-b563-45c3-926d-e9f5587ba0fc` / `10.107.157.78` | 9080 → 9080; `app=details` | `details-v1-5f99cc7756-l6fh9` / `ddb8473c-985f-4d39-98c3-db5e1a5b368d` / `10.244.26.116` / wk-02 |
| productpage | `b3f0c3f5-2e09-4341-bc92-962f2b7f63d3` / `10.99.71.168` | 9080 → 9080; `app=productpage` | `productpage-v1-86bbb558b8-j4xnw` / `5c178d62-877f-4680-a303-fa57899a5a3e` / `10.244.95.35` / wk-01 |
| ratings | `d8da52cf-30dc-412b-895e-99892072e967` / `10.105.126.134` | 9080 → 9080; `app=ratings` | `ratings-v1-745569b87c-zjgv9` / `c4cb18d8-4f84-4579-a990-30731286937d` / `10.244.26.118` / wk-02 |
| reviews | `8fbc7b81-6f3f-4005-95b0-1f1d59dfaabd` / `10.101.205.59` | 9080 → 9080; `app=reviews` | `reviews-v2-688cf6d5d5-62htc` / `03224cc7-68e0-4d65-b061-a47620a8b7d0` / `10.244.26.117` / wk-02 |

Đã đối chiếu đầy đủ tập UID endpoint với Pod Ready cho cả bốn Service. Replica cuối: details/productpage/ratings/reviews-v2 = 1; reviews-v1/v3 = 0. Service thử, policy/client/DestinationRule thử đã xóa; mọi ephemeral debug TV3 terminated. Giữ mesh, injection và route đã cài.
