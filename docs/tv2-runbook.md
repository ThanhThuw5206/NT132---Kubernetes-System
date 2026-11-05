# TV2 · Runbook triển khai Kubernetes Service (Bookinfo)

Bạn là **Thành viên 2**: quản lý `wk-01`, chọn ứng dụng mẫu và phụ trách trọng tâm đồ án — Kubernetes Service, DNS, selector, EndpointSlice, route tại gateway và luật phân quyền HTTP của Istio. Ứng dụng đã chốt là **Bookinfo** (xem [apps/bookinfo](../apps/bookinfo/README.md)).

Tài liệu này là phần việc TV2 trong [deploy-cloud.md](deploy-cloud.md) (mục 9) và [kế hoạch tổng thể](plan.md) (mục 3.2), gom theo đúng thứ tự thao tác. Quy ước khối lệnh: `bash` chạy **trong SSH vào VM** (cp-01 hoặc wk-01), thư mục `~/NT132---Kubernetes-System`; `powershell` chạy trên **laptop Windows**; khối `bash (Cloud Shell)` chạy ở **Google Cloud Shell**.

---

## 0. Bối cảnh — TV2 ở đâu trong luồng

Trạng thái ngày 05/11/2026 (theo [TV3-status](evidence/TV3-status.md) và [deploy-cloud §15](deploy-cloud.md)): ba node v1.35.10 Ready, Calico/CoreDNS/DNS hoạt động, Rancher v2.15.3 thấy đủ ba node Active. **Istio, Prometheus/Kiali, ứng dụng và policy chưa được triển khai.** Đó là phần việc tuần này.

Thứ tự phụ thuộc bạn cần nhớ:

1. **TV3 → TV2:** TV3 cài Istiod + ingress gateway và báo "gateway Ready" + tên namespace/Service/cổng gateway. Bạn **chưa** deploy app được khi chưa có sidecar injector.
2. **TV2 (bạn):** bật injection cho namespace `bookinfo`, deploy Bookinfo, cấu hình route, chứng minh Service (SVC01/SVC02/SVC03), xác nhận luật Istio (SEC01/SEC02).
3. **TV2 → TV1:** bàn giao NodePort 30080 đã thử trên cả hai worker để TV1 nối cloud LB.
4. **TV2 → TV3:** điền [phiếu bàn giao app](application-handover.md) để TV3 chạy OBS01/SEC03/SVC04.

Bạn **không** chạy Terraform, firewall, LB hay vòng đời VM (việc của TV1); **không** cài Calico/Istio nền hay NetworkPolicy lớp mạng (việc của TV3). Bạn sở hữu: manifest ứng dụng trong `apps/`, Service/route, và xác nhận AuthorizationPolicy/PeerAuthentication.

---

## 1. Chuẩn bị laptop và nhận quyền (một lần)

### 1.1. Công cụ trên laptop Windows

Cài: **Git**, **Google Cloud CLI (gcloud)**, trình duyệt. Không cần VM local. Kiểm tra:

```powershell
git --version
gcloud --version
```

### 1.2. Nhận quyền Google Cloud từ TV1

TV1 cấp cho email Google của bạn ba role trên project `nt132-kubernetes-513805`: **Compute Viewer**, **Compute OS Admin Login**, **IAP-secured Tunnel User** (xem [bat-tat-lab §0](bat-tat-lab.md)). Sau khi được cấp, đăng nhập và tự kiểm tra SSH được vào worker của mình:

```powershell
gcloud auth login
gcloud config set project nt132-kubernetes-513805
gcloud compute ssh wk-01 --project=nt132-kubernetes-513805 --zone=asia-southeast1-a --tunnel-through-iap
```

Nếu IAP báo 403 → thiếu role; nếu timeout → VM chưa bật (nhờ TV1 bật) hoặc firewall. Không tự mở SSH ra Internet.

### 1.3. Lấy đúng branch làm việc của bạn

Branch của bạn là `tv2/kubernetes-service`, tạo từ branch bàn giao TV3 `tv3/istio-network` (đã gồm hạ tầng TV1 + Istio/mạng TV3 + renderer). Trên laptop:

```powershell
git clone https://github.com/ThanhThuw5206/NT132---Kubernetes-System.git
cd NT132---Kubernetes-System
git fetch origin
git switch tv2/kubernetes-service
git rev-parse HEAD   # ghi commit này vào inventory/evidence
```

Giữ kubeconfig, token, private key **ngoài Git**. Chỉ commit manifest mẫu có placeholder.

---

## 2. Ngày 1 · Dựng wk-01 và join cụm

> Nếu TV1 đã bootstrap đủ ba node (trạng thái 05/11) thì **không** join lại. Mục này dùng khi dựng lab mới hoặc wk-01 chưa join. Khi bật/tắt máy giữa các buổi, theo [runbook hằng ngày](bat-tat-lab.md), **không** init/join lại.

### 2.1. Chuẩn hóa node (trên wk-01)

TV1 đã gửi inventory (subnet, IP `10.20.0.11` cho wk-01, zone). SSH vào wk-01 rồi:

```bash
cd ~/NT132---Kubernetes-System
hostname
sudo bash scripts/01-prepare-node.sh
sudo systemctl is-active containerd
kubelet --version
```

Script tắt swap, nạp module kernel, bật IP forwarding, cài đúng phiên bản trong `config/versions.env` và apt-hold. Kubelet có thể chưa ổn định trước khi join — bình thường, không reset.

### 2.2. Join vào control plane

TV1 cấp lệnh join (token + CA hash) **qua kênh riêng**. Trên wk-01 chạy đúng lệnh đó với `sudo` ở đầu:

```bash
sudo kubeadm join 10.20.0.10:6443 --token <TV1_CAP> --discovery-token-ca-cert-hash sha256:<TV1_CAP>
```

Không tự bịa token. Token hết hạn thì xin TV1 tạo mới. Sau join, nhờ TV1/bạn kiểm tra trên cp-01: `kubectl get nodes -o wide` phải thấy wk-01 (tên node trên GCE có thể là `wk-01.<zone>.c.<project>.internal` — không phải lỗi). Node NotReady trước khi TV3 cài Calico là dự kiến.

### 2.3. Chọn ứng dụng và ghi nguồn gốc

Ứng dụng đã chốt là Bookinfo. Việc cần làm: tải gói release Istio `1.30.7` để có `samples/bookinfo`, và điền nguồn/giấy phép/tag image thực vào [apps/bookinfo/README.md](../apps/bookinfo/README.md) và [service-inventory.md](../apps/bookinfo/service-inventory.md). (Tải gói và cài istioctl do TV3 chủ trì ở bước Istio; bạn dùng chung thư mục release trên cp-01.)

---

## 3. Ngày 2 · Kiểm chứng Service xuyên node (NET01) cùng TV3

TV3 chủ trì NET01 bằng [fixture network-check](../tests/service/network-check.yaml) và [test-cross-node.sh](../scripts/test-cross-node.sh). Phần của bạn: đặt HTTP server/client ở đúng hai worker và đối chiếu kết quả gọi theo **IP Pod** và theo **DNS Service**. Trên cp-01:

```bash
bash scripts/test-cross-node.sh
kubectl -n network-check get pods -o wide
kubectl -n network-check get svc,endpointslice
```

Cả hai cách gọi phải HTTP 200 và hai Pod nằm **khác node**. Nếu IP chạy nhưng DNS lỗi → kiểm tra CoreDNS/EndpointSlice (không sửa firewall cloud vội). Dọn sau khi lưu bằng chứng:

```bash
kubectl delete -f tests/service/network-check.yaml
```

Đây là probe hạ tầng, **không** phải website đồ án. Ghi kết quả vào NET01 (TV3 chủ trì, bạn kiểm tra chéo).

**Nhận bàn giao gateway từ TV3** trước khi sang ngày 3: TV3 báo `istio-system` có Istiod + ingress gateway Ready, Service gateway là NodePort, cổng HTTP 30080. Kiểm tra nhanh trên cp-01:

```bash
kubectl -n istio-system get deploy,svc,pods -o wide
```

---

## 4. Ngày 3 · Deploy Bookinfo và cấu hình route

Toàn bộ mục này chạy trên **cp-01** (nơi có kubeconfig quản trị của TV1 và thư mục release Istio). Làm trong phiên có TV1 giám sát; không sửa namespace hệ thống.

### 4.1. Tạo config tích hợp từ bản tham chiếu Bookinfo

```bash
cd ~/NT132---Kubernetes-System
cp apps/bookinfo/application.bookinfo.json config/application.json
python3 scripts/render-application.py config/application.json
```

`config/application.json` bị `.gitignore` (file vận hành). `render-application.py` kiểm tra đầu vào rồi **in ra một thư mục riêng** `./.generated/application-<mã>`. Gán đúng thư mục vừa in:

```bash
export GEN="$(python3 scripts/render-application.py config/application.json)"
echo "$GEN"
ls "$GEN"   # namespace.json gateway.json route.json mtls.json authorization.json network-policy.json inputs.json
```

> Đừng `kubectl apply -f "$GEN"` cả thư mục: có `inputs.json` không phải resource, và các policy phải áp **từng bước** để có đối chứng. Áp từng file theo đúng thứ tự dưới.

### 4.2. Tạo namespace đã bật injection, rồi deploy Bookinfo

```bash
kubectl apply -f "$GEN/namespace.json"
kubectl get ns bookinfo --show-labels    # phải có istio-injection=enabled
```

Áp manifest Bookinfo từ samples của release `1.30.7` (thư mục istio đã giải nén trên cp-01, ví dụ `~/istio-1.30.7`). Vì injection đã bật trước khi tạo Pod, sidecar được inject ngay:

```bash
ISTIO_DIR=~/istio-1.30.7
kubectl apply -n bookinfo -f "$ISTIO_DIR/samples/bookinfo/platform/kube/bookinfo.yaml"
# Giữ reviews-v2 cho cạnh reviews -> ratings ổn định:
kubectl -n bookinfo scale deploy/reviews-v1 deploy/reviews-v3 --replicas=0
kubectl -n bookinfo get deploy,pods,svc -o wide
```

Chờ từng Pod nghiệp vụ `READY 2/2` (app container + istio-proxy). Ghi tag/digest image thực vào [service-inventory.md](../apps/bookinfo/service-inventory.md):

```bash
kubectl -n bookinfo get pods -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.containers[*].image}{"\n"}{end}'
```

### 4.3. Áp Gateway + VirtualService và kiểm tra website

```bash
kubectl apply -f "$GEN/gateway.json"
kubectl apply -f "$GEN/route.json"
kubectl -n bookinfo get pods,svc,endpointslice
```

TV3/TV1 đang giữ port-forward gateway (`bash scripts/09-port-forward.sh app` → localhost:8080). Trên cp-01, với port-forward đang mở:

```bash
curl -i http://127.0.0.1:8080/productpage | head -40
```

Phải ra HTTP 200 và HTML trang sách. **Kiểm tra cả nội dung**: trang phải hiện điểm sao (reviews-v2 gọi được ratings); HTTP 200 của HTML vẫn có thể kèm lỗi reviews/ratings. Nếu 404 → so Host/path/gateway selector/VirtualService; chưa có route thì 404 là bình thường.

### 4.4. SVC01 — bảng kê Service

Điền [service-inventory.md](../apps/bookinfo/service-inventory.md) bằng dữ liệu thật: port/targetPort, selector, EndpointSlice Ready/targetRef của từng Service, đặc biệt `ratings`:

```bash
kubectl -n bookinfo get svc ratings -o yaml
kubectl -n bookinfo get pods -l app=ratings -o custom-columns=NAME:.metadata.name,UID:.metadata.uid,IP:.status.podIP,NODE:.spec.nodeName
kubectl -n bookinfo get endpointslice -l kubernetes.io/service-name=ratings -o yaml
```

**SVC01 đạt** khi ratings có ít nhất một endpoint Ready, nhãn và targetRef khớp Pod đang Ready.

---

## 5. Ngày 4 · Thí nghiệm Service và luật phân quyền

### 5.1. SVC02 — thay Pod, tên Service giữ nguyên

Mục tiêu: chứng minh client dùng **cùng tên `ratings`** vẫn gọi được sau khi Pod ratings bị thay, nhờ Service + EndpointSlice; phân biệt Pod bằng **UID** (IP có thể tái dùng).

```bash
# 1) Trước: lưu UID/ClusterIP/endpoint và gọi thử từ nguồn hợp lệ (reviews-v2)
kubectl -n bookinfo get svc ratings -o jsonpath='{.spec.clusterIP}{"\n"}'
kubectl -n bookinfo get pods -l app=ratings -o jsonpath='{range .items[*]}{.metadata.name}{" "}{.metadata.uid}{"\n"}{end}'
REVIEWS=$(kubectl -n bookinfo get pod -l app=reviews,version=v2 -o jsonpath='{.items[0].metadata.name}')
kubectl -n bookinfo exec "$REVIEWS" -c reviews -- curl -sS -o /dev/null -w '%{http_code}\n' http://ratings:9080/ratings/1

# 2) Thay đúng Pod ratings do Deployment quản lý, chờ Ready
kubectl -n bookinfo rollout restart deploy/ratings-v1
kubectl -n bookinfo rollout status deploy/ratings-v1

# 3) Sau: UID mới, endpoint trỏ Pod mới, gọi lại cùng tên vẫn 200
kubectl -n bookinfo get pods -l app=ratings -o jsonpath='{range .items[*]}{.metadata.name}{" "}{.metadata.uid}{"\n"}{end}'
kubectl -n bookinfo get endpointslice -l kubernetes.io/service-name=ratings -o yaml
kubectl -n bookinfo exec "$REVIEWS" -c reviews -- curl -sS -o /dev/null -w '%{http_code}\n' http://ratings:9080/ratings/1
```

Ghi DNS/ClusterIP/Service-UID **không đổi**, UID Pod **đổi**, HTTP 200 trước/sau. TV3 chụp chéo bằng `python3 scripts/tv3.py service-snapshot ...` (xem [tests/service](../tests/service/README.md)). Chỉ một replica có thể có khoảng gián đoạn ngắn — ghi lại thay vì bỏ qua.

### 5.2. SVC03 — một tên, nhiều backend (scale)

```bash
kubectl -n bookinfo get deploy ratings-v1 -o jsonpath='{.spec.replicas}{"\n"}'   # lưu số gốc
kubectl -n bookinfo scale deploy/ratings-v1 --replicas=2
kubectl -n bookinfo rollout status deploy/ratings-v1
kubectl -n bookinfo get endpointslice -l kubernetes.io/service-name=ratings -o wide
# ... đối chiếu 2 targetRef với 2 Pod Ready, gọi lại cùng tên ...
kubectl -n bookinfo scale deploy/ratings-v1 --replicas=1     # trả về số gốc
```

EndpointSlice phải phản ánh đủ tập Pod Ready sau scale. **Không** kết luận tải chia đều chỉ từ vài response giống nhau. Bàn giao TV3 ba trạng thái: trước scale / sau scale / sau phục hồi.

### 5.3. SEC01 — baseline mTLS STRICT

Đọc ServiceAccount thật trước:

```bash
kubectl -n bookinfo get deploy reviews-v2 -o jsonpath='{.spec.template.spec.serviceAccountName}{"\n"}'     # bookinfo-reviews
kubectl -n bookinfo get deploy productpage-v1 -o jsonpath='{.spec.template.spec.serviceAccountName}{"\n"}' # bookinfo-productpage
```

Áp PeerAuthentication STRICT cho ratings; **cả hai** nguồn trong mesh vẫn phải 200:

```bash
kubectl apply -f "$GEN/mtls.json"
PP=$(kubectl -n bookinfo get pod -l app=productpage -o jsonpath='{.items[0].metadata.name}')
kubectl -n bookinfo exec "$REVIEWS" -c reviews        -- curl -sS -o /dev/null -w '%{http_code}\n' http://ratings:9080/ratings/1
kubectl -n bookinfo exec "$PP"      -c productpage    -- curl -sS -o /dev/null -w '%{http_code}\n' http://ratings:9080/ratings/1
```

Mỗi nguồn gọi 3 lần, lưu mã 200 và bằng chứng mTLS (`connection_security_policy`). Client **không** sidecar vào ratings STRICT phải bị từ chối.

### 5.4. SEC02 — AuthorizationPolicy theo danh tính

```bash
kubectl apply -f "$GEN/authorization.json"
# reviews (bookinfo-reviews) GET /ratings/1  -> 200
kubectl -n bookinfo exec "$REVIEWS" -c reviews     -- curl -sS -o /dev/null -w '%{http_code}\n' http://ratings:9080/ratings/1
# productpage (bookinfo-productpage) gọi thẳng   -> 403
kubectl -n bookinfo exec "$PP"      -c productpage -- curl -sS -o /dev/null -w '%{http_code}\n' http://ratings:9080/ratings/1
# log RBAC tại proxy đích
kubectl -n bookinfo logs "$(kubectl -n bookinfo get pod -l app=ratings -o jsonpath='{.items[0].metadata.name}')" -c istio-proxy --tail=40
```

Kỳ vọng: reviews **200**, productpage **403** với dấu vết RBAC denied tại Envoy của ratings. Sau khi lưu bằng chứng, **gỡ đúng luật và phục hồi baseline** trước khi TV3 chạy SEC03 (NetworkPolicy):

```bash
kubectl delete -f "$GEN/authorization.json" --ignore-not-found
kubectl -n bookinfo exec "$REVIEWS" -c reviews     -- curl -sS -o /dev/null -w '%{http_code}\n' http://ratings:9080/ratings/1  # 200
kubectl -n bookinfo exec "$PP"      -c productpage -- curl -sS -o /dev/null -w '%{http_code}\n' http://ratings:9080/ratings/1  # 200 trở lại
```

Giữ nguyên PeerAuthentication STRICT xuyên suốt C1–C4. Ghi SEC01/SEC02 bằng [mẫu evidence](evidence/templates/test-result.md). Đừng dùng một Pod curl mới với ServiceAccount mặc định rồi kết luận danh tính reviews bị chặn.

### 5.5. Bàn giao NodePort cho TV1 (giai đoạn B)

Service gateway đã là NodePort 30080 (xem [mesh/istio/gateway-values.yaml](../mesh/istio/gateway-values.yaml)). Nhiệm vụ của bạn: thử `/productpage` qua IP riêng của **từng worker** từ cp-01/client cùng VPC:

```bash
curl -i http://10.20.0.11:30080/productpage | head -5   # wk-01
curl -i http://10.20.0.12:30080/productpage | head -5   # wk-02
```

`externalTrafficPolicy: Cluster` cho phép worker chuyển tới gateway Pod ở worker khác, nên cả hai IP đều phải trả trang có sao. Ghi IP worker, giờ thử, mã HTTP, có/không có sao rồi **giao TV1** để nối cloud LB. Nếu một URL lỗi → gửi TV3 endpoint/route cần kiểm tra trước khi TV1 động vào LB.

### 5.6. Điền phiếu bàn giao cho TV3

Điền [application-handover.md](application-handover.md) (namespace, entry/caller/target service, ports, labels, ServiceAccount, API path, luồng hợp lệ, nguồn đối chứng bị chặn, lệnh tạo traffic). TV3 cần phiếu này để dựng OBS01 và chuẩn bị SEC03/SVC04. SVC04 (selector sai) do TV3 tạo, TV1 sửa, **bạn gọi lại cùng URL để xác nhận HTTP 200** sau khi sửa.

---

## 6. Ngày 5 · Demo (phần nói 2 phút của TV2)

Mở YAML của `ratings`, chỉ `port`, `targetPort`, `selector`; đối chiếu địa chỉ backend trong EndpointSlice với Pod thật. Cho thấy cùng tên `ratings` vẫn gọi được sau khi Pod mới Ready; nếu IP tái dùng thì dùng **UID** để phân biệt. Câu chuyển tiếp cho TV3: "Service `ratings` và backend đang nhận lưu lượng — đây là nơi request đi vào."

Lệnh mở sẵn trước khi trình chiếu (mỗi port-forward một terminal):

```bash
kubectl -n bookinfo get endpointslice -l kubernetes.io/service-name=ratings -o wide
bash scripts/09-port-forward.sh app     # localhost:8080 -> /productpage
```

---

## 7. Checklist nghiệm thu phần TV2

| ID | Đạt khi | Chủ trì / kiểm tra chéo |
|---|---|---|
| SVC01 | ratings có ≥1 endpoint Ready đúng nhãn/targetRef | TV2 / TV1 |
| SVC02 | Thay Pod ratings, cùng tên vẫn 200, UID Pod mới chứng minh | TV2 / TV3 |
| SVC03 | EndpointSlice phản ánh tập Pod sau scale, gọi cùng tên được | TV2 / TV3 |
| APP01 | `/productpage` qua gateway có sách+review+sao, Pod 2/2 Ready | TV2 / TV1 |
| SEC01 | Hai nguồn 200 khi chỉ STRICT, có bằng chứng mTLS | TV2 / TV3 |
| SEC02 | reviews 200, productpage 403 + log RBAC; đã phục hồi baseline | TV2 / TV1 |

Chỉ đánh dấu **Đạt** khi có lệnh đã dùng + kết quả quan sát + một thành viên khác chạy lại được. Ca chưa chạy để **Chưa chạy**, lỗi môi trường ghi **Bị chặn** kèm bước khắc phục. Không dùng ảnh thay cho kết quả âm tính của policy.

---

## 8. Xử lý lỗi nhanh (phần TV2)

| Triệu chứng | Kiểm tra trước |
|---|---|
| Pod Bookinfo chỉ 1/2 Ready (thiếu sidecar) | Namespace có `istio-injection=enabled` **trước** khi tạo Pod? Nếu áp label sau, `kubectl -n bookinfo rollout restart deploy` để inject lại |
| Service không có endpoint Ready | selector vs nhãn Pod, readinessProbe, `targetPort` đúng cổng app (9080) |
| `/productpage` 404 | Gateway selector `istio=ingressgateway`, host/path của VirtualService, route đã apply chưa |
| Trang 200 nhưng không có sao | reviews gọi ratings lỗi: xem reviews-v2 còn chạy, ratings Ready, policy chưa chặn nhầm |
| Luôn 200 dù đã áp AuthorizationPolicy | Đúng namespace/selector đích? Nguồn có proxy SYNCED? principal đúng `bookinfo-reviews`? `istioctl proxy-status` |
| productpage vẫn 200 khi đã muốn chặn | Bạn đang exec đúng container app (không phải istio-proxy) và đúng ServiceAccount? |

Tham khảo chẩn đoán đầy đủ ở [deploy-cloud §13](deploy-cloud.md) và [plan §19](plan.md).

---

## 9. Git — làm việc trên branch TV2

```powershell
git switch tv2/kubernetes-service
git add apps/bookinfo docs/tv2-runbook.md docs/evidence/TV2-status.md apps/bookinfo/service-inventory.md
git diff --cached        # kiểm tra đúng file, KHÔNG có kubeconfig/token/application.json
git commit -m "Add TV2 Bookinfo service lab runbook and manifests"
git push -u origin tv2/kubernetes-service
```

Không commit `config/application.json` (đã trong `.gitignore`), kubeconfig, token, private key hay nội dung Secret. Khi tích hợp, mở Pull Request từ `tv2/kubernetes-service` để TV1 review; TV1 tạo namespace/quyền và lưu bằng chứng.
