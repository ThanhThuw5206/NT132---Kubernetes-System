# TV2 · Bookinfo, Kubernetes Service và bàn giao TV3

Cập nhật **06/11/2026** sau khi nhận Bookinfo tại `4377766` và sửa tích hợp trên laptop. Phần local đã có source ghim phiên bản, công cụ sinh workload/config và hướng dẫn kiểm tra. Các lệnh Kubernetes, Helm, SSH và test cloud bên dưới **chưa chạy trong đợt chuẩn bị này**.

TV2 sở hữu workload, Service/route, SVC01–03 và luật Istio SEC01/SEC02. TV3 sở hữu mạng/mesh nền, Prometheus/Kiali, NetworkPolicy và selector lab. TV1 điều phối hạ tầng, quyền, Rancher và frontend public. Theo bàn giao 05/11, ba node/Calico/Rancher đã hoạt động; tiếp nhận cụm hiện có, không prepare/init/join/reset lại.

## 1. Thứ tự chung và nơi chạy

Theo [TV1 §9](them-thanh-vien.md): **cụm Ready/NET01 → Bookinfo baseline không proxy → TV1 review → TV3 cài Istio/quan sát → TV2 bật injection/rollout/route → kiểm tra lại → từng lớp policy và phục hồi**. TV2 chứng minh Service trước Istio; không chờ gateway để deploy baseline.

| Việc | Nơi làm | Điều kiện hoàn tất |
|---|---|---|
| Kiểm tra source/hash, sinh manifest, đọc policy | Laptop, không cần bật VM | Checker local đạt, output mới và danh sách file rõ ràng |
| App baseline, Service/EndpointSlice | Phiên quản trị trên cp-01 | HTTP nội bộ đúng, TV1 review; chưa injection/policy |
| Istio/gateway/Prometheus/Kiali | cp-01, TV3 chủ trì | Nền Ready, bàn giao gateway Service/cổng/quyền/context |
| Injection, route, SVC/SEC, evidence | cp-01, TV2/TV3 phối hợp | Pod/app/proxy Ready, kiểm thử/phục hồi có log thật |
| NodePort/LB | Trong VPC rồi laptop ngoài VPC | TV2 thử NodePort; TV1 giao LB; tunnel không thay PUB01 |

Khối `powershell` chạy trên laptop tại repo; `bash` chạy **trong SSH đã có quyền Kubernetes trên cp-01**, không phải Cloud Shell. SSH/IAP và lịch bật/tắt theo [runbook hằng ngày](bat-tat-lab.md); tài khoản SSH mới không tự có kubeconfig quản trị. Không chép admin.conf, token hoặc cache gcloud giữa các máy. Dùng một terminal SSH riêng cho triển khai/test; các lệnh có `|| exit 1` sẽ đóng terminal đó khi lỗi để dừng chuỗi phụ thuộc. Giữ port-forward trong terminal khác; sau lỗi đọc kết quả và trạng thái lab trước khi mở lại phiên tiếp tục.

## 2. Chuẩn bị trên laptop

Lấy cùng source tích hợp TV3 mà nhóm bàn giao, ghi `git rev-parse HEAD` và đọc diff local. Config thiết kế tại [apps/bookinfo](../apps/bookinfo/README.md); không cần `~/istio-1.30.7` để lấy workload nữa.

Laptop hiện tại có Python SDK portable chạy được checker; uv/Python 3.15.2 gặp Windows Application Control chặn DLL. Dùng:

```powershell
$Python = '.\.cache\gcloud-592.0.0\google-cloud-sdk\platform\bundledpython\python.exe'
& $Python scripts/check-tv3-local.py
& $Python scripts/prepare-bookinfo.py --check
& $Python scripts/prepare-bookinfo.py
& $Python scripts/tv3.py render apps/bookinfo/application.bookinfo.json
```

Máy khác dùng Python >=3.10 hoạt động bình thường; không nhận SDK/cache đăng nhập của máy này. `prepare-bookinfo.py` chỉ đọc source/hash và sinh thư mục mới `.generated/bookinfo-*`:

- `namespace-baseline.json`: namespace Bookinfo, injection **disabled** cho baseline.
- `workloads.json`: Kubernetes List của Service/ServiceAccount/Deployment, giữ reviews-v2 chạy, reviews-v1/v3 bằng 0; có probes/tài nguyên lab.
- `preparation.json`: nguồn/hash, image/cấu hình chuẩn bị; **không phải resource để apply**.

Renderer tích hợp sinh namespace bật injection, Gateway/VirtualService và từng policy riêng. Không apply nguyên thư mục output vì có metadata và các policy cần thử độc lập. Công cụ local không gọi cloud hoặc deploy.

## 3. Phiên cloud sau này: tiếp nhận cụm và app baseline

Đặt context thật TV1 bàn giao; `TEN_CONTEXT_LAB` là ô điền:

```bash
set -o pipefail
cd ~/NT132---Kubernetes-System || exit 1
kubectl config get-contexts || exit 1
export CTX=TEN_CONTEXT_LAB
kubectl --context "$CTX" get --raw=/readyz || exit 1
kubectl --context "$CTX" get nodes -o wide || exit 1
kubectl --context "$CTX" -n kube-system get pods || exit 1
```

TV1 xác nhận ba node Ready/quyền thực hiện. TV3/TV2 chạy NET01 khi thống nhất phạm vi: script có tạo fixture/gán label node, không chỉ đọc. Các script cài đặt dùng current-context; trước khi chạy đối chiếu `kubectl config current-context` đúng `$CTX`, không đổi context của phiên đang phục vụ người khác.

Nếu namespace bookinfo đã có workload/policy của lượt khác, lưu inventory/thống nhất baseline trước; không tắt injection hoặc ghi đè trạng thái đang dùng. Với lần triển khai đầu được bố trí:

```bash
BOOKINFO_GEN="$(python3 scripts/prepare-bookinfo.py)" || exit 1
export BOOKINFO_GEN
printf '%s\n' "$BOOKINFO_GEN"
kubectl --context "$CTX" apply -f "$BOOKINFO_GEN/namespace-baseline.json" || exit 1
kubectl --context "$CTX" apply -f "$BOOKINFO_GEN/workloads.json" || exit 1
for deployment in details-v1 ratings-v1 reviews-v2 productpage-v1; do
  kubectl --context "$CTX" -n bookinfo rollout status "deployment/$deployment" --timeout=300s || exit 1
done
kubectl --context "$CTX" -n bookinfo get pods -o json | python3 scripts/check-bookinfo-pods.py --baseline || exit 1
kubectl --context "$CTX" -n bookinfo get deploy,pods,svc,endpointslice -o wide
```

Mỗi rollout phải thành công; checker baseline cần đủ bốn app Ready, không proxy. Đối chiếu Service selector/ports và EndpointSlice. Có thể xem website bằng port-forward **Service productpage** trong terminal riêng trên cp-01:

```bash
kubectl --context "$CTX" -n bookinfo port-forward svc/productpage 9080:9080 --address=127.0.0.1
```

Tại terminal khác: `curl -fsS http://127.0.0.1:9080/productpage`, kiểm tra sách/review/sao, không chỉ HTTP 200. Baseline còn cần hai nguồn gọi trực tiếp ratings theo mục 4; port-forward một mình chưa chứng minh DNS Service. TV1 review baseline/[inventory](../apps/bookinfo/service-inventory.md) trước mesh.

## 4. Hai nguồn HTTP/DNS đúng danh tính

Lấy Pod thật sau mỗi rollout; tên/UID có thể đổi:

```bash
REVIEWS=$(kubectl --context "$CTX" -n bookinfo get pod -l app=reviews,version=v2 -o jsonpath='{.items[0].metadata.name}') || exit 1
PP=$(kubectl --context "$CTX" -n bookinfo get pod -l app=productpage -o jsonpath='{.items[0].metadata.name}') || exit 1
REVIEWS_CONTAINER=reviews
PP_CONTAINER=productpage
kubectl --context "$CTX" -n bookinfo get pod "$REVIEWS" "$PP" -o custom-columns=NAME:.metadata.name,UID:.metadata.uid,SA:.spec.serviceAccountName,IP:.status.podIP,NODE:.spec.nodeName
```

Thử app container trước; cần cả curl và getent. Ví dụ reviews:

```bash
SRC="$REVIEWS"
SRC_CONTAINER="$REVIEWS_CONTAINER"
kubectl --context "$CTX" -n bookinfo exec "$SRC" -c "$SRC_CONTAINER" -- sh -c 'command -v curl && command -v getent && test "$(id -u)" != 1337'
```

Nếu thiếu lệnh/shell, dùng debug container trong **chính Pod đó**, theo quyền TV1 cấp. Kiểm tra quyền, không tự đổi RBAC:

```bash
kubectl --context "$CTX" auth can-i update pods/ephemeralcontainers -n bookinfo
kubectl --context "$CTX" auth can-i patch pods/ephemeralcontainers -n bookinfo
kubectl --context "$CTX" auth can-i create pods/exec -n bookinfo
```

Chỉ tạo khi đủ quyền và có lịch thử. Image dùng phiên bản `nicolaka/netshoot:v0.14`, không latest; vẫn phải xác minh công cụ/UID và ghi imageID thực. [Dockerfile nguồn](https://raw.githubusercontent.com/nicolaka/netshoot/v0.14/Dockerfile) không thay kiểm tra runtime:

```bash
PROBE_CONTAINER="tv3-debug-$(date +%s%N)"
kubectl --context "$CTX" -n bookinfo debug "$SRC" --attach=false --container="$PROBE_CONTAINER" --image=nicolaka/netshoot:v0.14 --profile=general -- sleep 3600 || exit 1
DEBUG_RUNNING=''
for ((attempt=0; attempt<60; attempt++)); do
  DEBUG_RUNNING=$(kubectl --request-timeout=5s --context "$CTX" -n bookinfo get pod "$SRC" -o "jsonpath={.status.ephemeralContainerStatuses[?(@.name==\"$PROBE_CONTAINER\")].state.running.startedAt}") || exit 1
  [ -n "$DEBUG_RUNNING" ] && break
  sleep 2
done
if [ -z "$DEBUG_RUNNING" ]; then
  printf '%s\n' 'Debug container did not become Running after 60 checks; inspect image pull and Pod events before retrying.' >&2
  exit 1
fi
kubectl --context "$CTX" -n bookinfo exec "$SRC" -c "$PROBE_CONTAINER" -- sh -c 'command -v curl && command -v getent && test "$(id -u)" != 1337' || exit 1
SRC_CONTAINER="$PROBE_CONTAINER"
if [ "$SRC" = "$REVIEWS" ]; then
  REVIEWS_CONTAINER="$SRC_CONTAINER"
elif [ "$SRC" = "$PP" ]; then
  PP_CONTAINER="$SRC_CONTAINER"
fi
```

Lặp với `SRC="$PP"`, `SRC_CONTAINER=productpage`; nếu cần debug mới thì dùng tên mới và lưu `PP_CONTAINER="$SRC_CONTAINER"`. Nếu app container đã đủ lệnh thì giữ tên app gốc. Không exec trong istio-proxy, không dùng `--copy-to` hoặc Pod mới với SA mặc định thay nguồn. Debug cùng Pod giữ network/labels/SA, không cần chia sẻ process namespace. Không dùng UID 1337 (UID proxy có thể được bỏ qua interception) hoặc profile privileged.

Ephemeral container tự kết thúc sau một giờ; entry còn trong Pod tới khi Pod được thay, không thể xóa riêng entry. TV2 thay Pod trong lượt rollout có kế hoạch sau khi lưu evidence. Sau rollout thêm proxy phải chọn lại Pod/UID và chuẩn bị lại công cụ; debug cũ không chuyển sang Pod mới.

Baseline trước mesh và các lượt phục hồi dùng cùng DNS/path:

```bash
kubectl --context "$CTX" -n bookinfo exec "$REVIEWS" -c "$REVIEWS_CONTAINER" -- getent hosts ratings.bookinfo.svc.cluster.local
kubectl --context "$CTX" -n bookinfo exec "$REVIEWS" -c "$REVIEWS_CONTAINER" -- curl --noproxy '*' -sS --max-time 10 -o /dev/null -w '%{http_code}\n' http://ratings.bookinfo.svc.cluster.local:9080/ratings/0
kubectl --context "$CTX" -n bookinfo exec "$PP" -c "$PP_CONTAINER" -- getent hosts ratings.bookinfo.svc.cluster.local
kubectl --context "$CTX" -n bookinfo exec "$PP" -c "$PP_CONTAINER" -- curl --noproxy '*' -sS --max-time 10 -o /dev/null -w '%{http_code}\n' http://ratings.bookinfo.svc.cluster.local:9080/ratings/0
```

Hai nguồn phải 200 khi chưa hạn chế. Lưu cả body JSON có ratings, DNS/exit code, UID/SA và endpoint Ready; bỏ `-o /dev/null` để lấy body khi cần. **Không dùng tv3.py probe trước mesh**: probe yêu cầu proxy Ready cho C1–C4. C1b không proxy cũng dùng lệnh riêng và đối chứng trước STRICT.

## 5. Sau baseline: mesh, injection và route

TV3 cài Istio/gateway/Prometheus/Kiali theo [runbook TV3](tv3-runbook.md), bàn giao istio-system, Service istio-ingressgateway, HTTP 80/NodePort 30080, Istiod/gateway Ready và quyền đọc policy app/root mesh. Workload vendored đủ để deploy app; istioctl chỉ là công cụ chẩn đoán nếu được chuẩn bị riêng đúng phiên bản, không phải dependency renderer/Helm.

Nếu config/application.json đã có, so sánh trước khi thay. Với lần đầu:

```bash
cp apps/bookinfo/application.bookinfo.json config/application.json || exit 1
GEN="$(python3 scripts/tv3.py render config/application.json)" || exit 1
export GEN
kubectl --context "$CTX" apply -f "$GEN/namespace.json" || exit 1
for deployment in details-v1 ratings-v1 reviews-v2 productpage-v1; do
  kubectl --context "$CTX" -n bookinfo rollout restart "deployment/$deployment" || exit 1
  kubectl --context "$CTX" -n bookinfo rollout status "deployment/$deployment" --timeout=300s || exit 1
done
kubectl --context "$CTX" -n bookinfo get pods -o json | python3 scripts/check-bookinfo-pods.py || exit 1
kubectl --context "$CTX" apply -f "$GEN/gateway.json" || exit 1
kubectl --context "$CTX" apply -f "$GEN/route.json" || exit 1
```

Checker đọc JSON stdin, không gọi API: kiểm tra đủ bốn app/Pod Ready và proxy Ready. Không lấy cột `READY 2/2` làm điều kiện cố định: proxy thường ở spec.containers/status.containerStatuses; native sidecar ở spec.initContainers có restartPolicy Always và status.initContainerStatuses. Dừng lượt triển khai nếu rollout/checker trả lỗi, chưa áp route hoặc policy kế tiếp. Có thể lưu JSON Pod để làm evidence và chạy lại checker offline. Chọn lại nguồn/công cụ theo mục 4, lặp DNS/HTTP hai nguồn đều 200.

Mở gateway ở terminal riêng:

```bash
kubectl --context "$CTX" -n istio-system port-forward svc/istio-ingressgateway 8080:80 --address=127.0.0.1
```

Terminal cp-01 khác kiểm tra `/productpage` có sách/review/sao; assets, login/logout và API đã route theo config. Route gateway không tự cho principal productpage gọi thẳng ratings sau SEC02; cạnh hợp lệ là reviews-v2 → ratings. Không chỉ nhìn HTTP 200 của HTML rồi kết luận website đạt.

## 6. Service và policy: từng lớp có đối chứng/rollback

TV2 điền [bảng Service](../apps/bookinfo/service-inventory.md) từ dữ liệu thực. SVC01 cần selector/port/targetPort khớp Pod Ready và EndpointSlice targetRef. SVC02/SVC03 chạy khi baseline đạt, chưa bật luật hạn chế nếu chưa thống nhất:

```bash
python3 scripts/tv3.py service-snapshot config/application.json --context "$CTX" || exit 1
# SVC02: lưu UID/ClusterIP/endpoint rồi thay ratings, chờ Ready và gọi lại cùng DNS.
kubectl --context "$CTX" -n bookinfo rollout restart deployment/ratings-v1 || exit 1
kubectl --context "$CTX" -n bookinfo rollout status deployment/ratings-v1 --timeout=300s || exit 1
python3 scripts/tv3.py service-snapshot config/application.json --context "$CTX" || exit 1
# SVC03: đọc/lưu replica gốc, không mặc định số thực tế là 1.
kubectl --context "$CTX" -n bookinfo get deployment ratings-v1 -o jsonpath='{.spec.replicas}{"\n"}'
```

SVC02: UID Pod đổi, UID/ClusterIP Service giữ nguyên, HTTP phục hồi; ghi gián đoạn nếu có. SVC03: lưu replica gốc, scale ratings lên 2/chờ rollout/snapshot/gọi lại, trả đúng replica gốc rồi snapshot/gọi lần ba. Đối chiếu toàn bộ endpoint Ready với Pod UID; không suy ra chia tải đều từ vài body giống nhau. Theo [hướng dẫn Service](../tests/service/README.md), TV2 chịu trách nhiệm các thay đổi/rollback workload.

Trước SEC01, ghi SA thật, endpoint, policy namespace app/root mesh. Theo [ma trận C0–C4](tv3-test-matrix.md):

```bash
# C1 / SEC01: chỉ STRICT; hai nguồn trong mesh vẫn phải 200.
kubectl --context "$CTX" apply -f "$GEN/mtls.json" || exit 1
python3 scripts/tv3.py probe config/application.json --context "$CTX" --pod "$REVIEWS" --container "$REVIEWS_CONTAINER" --path /ratings/0 --expect 200 --phase C1-reviews || exit 1
python3 scripts/tv3.py probe config/application.json --context "$CTX" --pod "$PP" --container "$PP_CONTAINER" --path /ratings/0 --expect 200 --phase C1-productpage || exit 1
# C2 / SEC02: chỉ thêm luật danh tính/API.
kubectl --context "$CTX" apply -f "$GEN/authorization.json" || exit 1
python3 scripts/tv3.py probe config/application.json --context "$CTX" --pod "$REVIEWS" --container "$REVIEWS_CONTAINER" --path /ratings/0 --expect 200 --phase C2-reviews || exit 1
python3 scripts/tv3.py probe config/application.json --context "$CTX" --pod "$PP" --container "$PP_CONTAINER" --path /ratings/0 --expect 403 --phase C2-productpage || exit 1
```

Lưu bằng chứng mTLS đúng cặp nguồn/đích, không chỉ YAML STRICT. Lưu log RBAC của proxy ratings khi nguồn đối chứng 403; có thể cần cấu hình access log phù hợp, không suy luận từ việc mặc định chưa có dòng log. C1b cần client không proxy đã được cấp quyền và baseline trước STRICT; không mặc định từ chối là HTTP 403.

Sau C2 gỡ **riêng luật của lượt thử**, giữ STRICT, hai nguồn phải trở lại 200:

```bash
kubectl --context "$CTX" delete -f "$GEN/authorization.json" || exit 1
python3 scripts/tv3.py probe config/application.json --context "$CTX" --pod "$REVIEWS" --container "$REVIEWS_CONTAINER" --path /ratings/0 --expect 200 --phase C2-recovered-reviews || exit 1
python3 scripts/tv3.py probe config/application.json --context "$CTX" --pod "$PP" --container "$PP_CONTAINER" --path /ratings/0 --expect 200 --phase C2-recovered-productpage || exit 1
```

Không ghi đè/xóa policy có sẵn của người khác để tạo baseline. TV3 tiếp tục C3 NetworkPolicy riêng/phục hồi; C4 kết hợp sau khi ca riêng đạt. Website còn sao dưới C2/C4 vì reviews GET /ratings/0 được phép. SVC04 dùng Service riêng do TV3 tạo, TV1 sửa/TV2 gọi lại; không sửa selector ratings thật để mô phỏng lỗi.

## 7. Bàn giao và nghiệm thu

TV2 thử NodePort từ cp-01/client trong VPC trên **hai worker** rồi giao TV1:

```bash
curl --noproxy '*' -fsS --max-time 15 http://10.20.0.11:30080/productpage
curl --noproxy '*' -fsS --max-time 15 http://10.20.0.12:30080/productpage
```

Ghi HTTP/nội dung có sao/giờ/IP thật; TV1 xử lý LB/frontend. Port-forward không thay bằng chứng ngoài VPC. TV2 điền [phiếu app](application-handover.md); TV3 chạy OBS01/kiểm tra chéo.

| Ca | Đạt khi | Chủ trì / chạy lại |
|---|---|---|
| Baseline trước mesh | Hai nguồn DNS/HTTP 200, website có sao, endpoint Ready; chưa proxy/policy | TV2 / TV1 |
| APP01 | Website qua gateway có sách/review/sao, app/proxy Ready, route demo hoạt động | TV2 / TV1 |
| SVC01 | Selector/ports/EndpointSlice targetRef khớp Pod Ready | TV2 / TV1 |
| SVC02 | Pod UID đổi, cùng DNS phục hồi, Service UID/ClusterIP không đổi | TV2 / TV3 |
| SVC03 | Endpoint phản ánh đủ Pod Ready sau scale/rollback, gọi cùng DNS được | TV2 / TV3 |
| SEC01 | Hai nguồn trong mesh 200 với STRICT và bằng chứng mTLS; C1b ghi riêng | TV2 / TV3 |
| SEC02 | Reviews 200, productpage gọi thẳng bị 403/RBAC; website vẫn sao; phục hồi hai nguồn 200 | TV2 / TV1 |

Chỉ ghi Đạt khi có lệnh/log thật, phục hồi và người khác chạy lại. Pod UID/IP/endpoint/imageID/context/giờ còn chờ nếu chưa chạy. [Mẫu evidence](evidence/templates/test-result.md) tách ảnh demo khỏi kết quả thật.

Nhóm nhận phần tích hợp từ nhánh TV3, ghi đúng commit/gói theo [phiếu bàn giao](tv3-handover.md). Không switch/commit/push chỉ vì ví dụ trong tài liệu. TV2 tiếp tục quản lý nhánh ứng dụng sau khi nhận tích hợp; giữ config vận hành/kubeconfig/token/private key/cache ngoài Git.
