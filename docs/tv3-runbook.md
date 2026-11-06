# TV3 · Hướng dẫn thực hiện

Cập nhật **07/11/2026**. Mục tiêu là kiểm chứng **DNS Service → selector → EndpointSlice → Pod** và phân biệt thiếu backend với lỗi quyền truy cập. TV3 phụ trách NET01, Istio nền, Prometheus/Kiali, NetworkPolicy SEC03 và bài selector SVC04; phối hợp kiểm tra Service, mTLS, quyền viewer và frontend public. TV1 giữ hạ tầng/Rancher/LB; TV2 giữ ứng dụng/Service/route và luật Istio.

Đọc [bàn giao và checklist đầu vào](tv3-handover.md) để nhận việc, [ma trận test](tv3-test-matrix.md) để chạy từng ca và [trạng thái TV3](evidence/TV3-status.md) để biết kết quả đã xác minh. Lịch M1–M4 theo [kế hoạch](plan.md); có script hoặc test offline chưa đồng nghĩa nghiệm thu cloud. Chưa cần slide trong đợt này.

## 1. Chuẩn bị và kiểm tra trên laptop

Các lệnh PowerShell dưới chạy tại root repo. Phần offline không cần bật VM hoặc cài kubectl/Helm/Terraform trên laptop; theo quy trình hiện tại, các công cụ quản trị cụm chạy trong phiên `cp-01`.

### Google Cloud CLI portable

Máy hiện tại đã có SDK 592.0.0 tại `.cache/gcloud-592.0.0/google-cloud-sdk`. Kiểm tra phiên bản; nếu chuẩn bị máy Windows x64 khác thì chạy installer trước:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\gcloud-local.ps1 --version
# Chỉ khi máy chưa có SDK portable:
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install-gcloud-local.ps1
```

Installer kiểm tra SHA256 archive đúng phiên bản rồi giải nén vào cache; không đổi PATH hoặc đăng nhập. `-ExecutionPolicy Bypass` chỉ áp dụng cho tiến trình đó. Nếu giải nén bị ngắt, xác nhận installer cũ đã dừng và hash archive đúng rồi mới chạy lại với `-ResumePartial`; marker `tv3-install-complete.json` chỉ có sau khi cài hoàn tất. Pin/checksum tham chiếu [archive chính thức Google](https://docs.cloud.google.com/sdk/docs/downloads-versioned-archives).

Wrapper `gcloud-local.ps1` dùng config riêng `.cache/tv3-gcloud-config`, tắt update check/usage reporting và khôi phục biến môi trường process sau lệnh. Config này khác config gcloud cài toàn máy; dùng nhất quán wrapper khi làm lab. Mỗi thành viên tự đăng nhập bằng tài khoản riêng, không gửi SDK/cache đăng nhập trong gói source. Quyền và lịch phiên thực hiện được ghi ở phiếu bàn giao.

### Python, manifest và checker offline

Trên máy hiện tại, `python` có thể trỏ Microsoft Store; Python 3.15.2 qua uv bị Windows Application Control chặn DLL `_overlapped`. Dùng Python 3.14.9 đã có trong SDK portable:

```powershell
$Python = '.\.cache\gcloud-592.0.0\google-cloud-sdk\platform\bundledpython\python.exe'
& $Python scripts/check-tv3-local.py
& $Python scripts/prepare-bookinfo.py --check
& $Python scripts/prepare-bookinfo.py
& $Python scripts/tv3.py render apps/bookinfo/application.bookinfo.json
```

Checker chạy unit test, kiểm tra hash/sinh baseline Bookinfo, render tích hợp, cú pháp Bash/PowerShell và `gcloud --version`. Test Kubernetes dùng mock, HTTP chỉ dùng loopback; không gọi API project. Báo cáo và manifest nằm trong `.generated/laptop-check-*`. Chỉ chạy test riêng bằng `& $Python -m unittest discover -s tests -v`. Máy khác dùng Python >=3.10 hoạt động được; uv offline chỉ dùng khi runtime của máy đó đã cache và chạy bình thường. Trên Ubuntu dùng `python3`; các công cụ mới chỉ cần thư viện chuẩn.

`prepare-bookinfo.py` sinh `namespace-baseline.json` tắt injection và `workloads.json` từ source/hash/license đã ghim; `preparation.json` là metadata. Renderer sinh namespace **bật injection**, gateway/route, từng policy và hai trạng thái Service thử selector. Mỗi lần tạo thư mục mới, không ghi đè. **Không apply nguyên thư mục output** hoặc dùng namespace bật injection cho baseline trước mesh. Xem [Bookinfo README](../apps/bookinfo/README.md) và [runbook TV2](tv2-runbook.md).

Nhận/chuyển source và đóng gói overlay theo [phiếu bàn giao](tv3-handover.md). `git archive HEAD` chỉ lấy file đã commit; gói source không kèm `.cache`, config vận hành, credentials, evidence runtime hoặc slide.

## 2. Tiếp nhận cụm và kiểm tra mạng

Các khối Bash dưới dành cho **phiên cloud sau khi đã nhận đủ đầu vào**, không phải lệnh đã chạy trong đợt laptop. TV1 đã bàn giao cụm/Calico/Rancher hoạt động ngày 05/11; xác minh trạng thái hiện tại, **không prepare/init/join/reset hoặc cài lại Calico**. Script bootstrap chỉ dùng khi nhóm chủ động dựng lab mới theo [deploy-cloud](deploy-cloud.md). Worker GCE có thể mang tên Node FQDN; script nhận diện bằng InternalIP/nhãn `nt132.lab/worker`, không đổi tên bằng cách reset node.

Trong SSH vào `wk-02`, kiểm tra `hostname -s`, `sudo systemctl is-active containerd`, `kubelet --version`. Trong phiên quản trị trên **cp-01**, nhận đúng context từ TV1 và kiểm tra:

```bash
kubectl config get-contexts
export CTX=TEN_CONTEXT_LAB
kubectl --context "$CTX" get nodes -o wide
kubectl --context "$CTX" get tigerastatus
kubectl --context "$CTX" -n kube-system get pods
```

`TEN_CONTEXT_LAB` là ô điền, chưa phải context có thể chạy. Đối chiếu [phiên bản/CIDR Calico](../cluster/calico/README.md). Các script cài đặt/NET01 dùng current-context; trước khi chạy phải đối chiếu `kubectl config current-context` đúng `$CTX`. Dùng terminal SSH lab riêng; `|| exit 1` dừng terminal đó nếu lệnh lỗi, giữ forwarding ở terminal khác.

Lượt TV3 ngày 06/11 dùng phiên `sudo` trên cp-01 với `KUBECONFIG=/etc/kubernetes/admin.conf`, context `kubernetes-admin@nt132`. Nếu dùng lại phương thức đã được TV1 cấp, mở shell `sudo -i`, vào thư mục source đã kiểm tra rồi `export KUBECONFIG=/etc/kubernetes/admin.conf`; đối chiếu project/node/context trước thao tác. Không sao chép kubeconfig này về laptop. Phiên này có quyền quản trị, chưa chứng minh quyền viewer/Rancher riêng.

Nếu chỉ `tiers` chờ Tigera API server, xem hướng dẫn bổ sung **riêng APIServer** trong Calico README; không chạy lại bootstrap `03-install-calico.sh` trên cụm đang dùng. Lượt cloud đã kiểm tra Installation và IP pool không đổi sau bổ sung; khả năng dựng cụm mới từ đầu vẫn là phép thử khác.

Khi có phạm vi chạy NET01, trên cp-01:

```bash
test "$(kubectl config current-context)" = "$CTX" || exit 1
bash scripts/test-cross-node.sh || exit 1
```

Script **tạo fixture/gán label node**, thử sáu request Pod IP/ClusterIP/DNS theo cả hai hướng giữa worker và lưu từng attempt/HTTP/exit code ở `.generated/net01-*`. Kiểm tra label sở hữu trước apply; resource trùng tên của người khác phải được xử lý riêng. TV2 chạy lại sau khi TV3 lưu bằng chứng.

NET01 không tự dọn. Trước khi `kubectl --context "$CTX" delete -f tests/service/network-check.yaml`, kiểm tra namespace `network-check` không còn tài nguyên ngoài bài cần giữ vì fixture chứa cả Namespace. Client ngủ một giờ; nếu Pod đã Completed, dọn đúng fixture rồi tạo lại khi cần. Giữ taint control plane.

## 3. Baseline Bookinfo rồi tích hợp mesh

Thứ tự chung: **Ready/NET01 → TV2 baseline không proxy → TV1 review → TV3 mesh/quan sát → TV2 injection/rollout/route → kiểm tra lại → policy từng lớp**. TV2 thực hiện baseline theo [runbook TV2](tv2-runbook.md); TV3 tiếp nhận Service/labels/SA/ports và kết quả thực trước khi cài mesh.

Sau baseline, trong phiên cp-01 đúng context/quyền:

```bash
test "$(kubectl config current-context)" = "$CTX" || exit 1
helm version || exit 1
bash scripts/05-install-istio.sh || exit 1
kubectl --context "$CTX" -n istio-system get deployments,svc,pods -o wide
bash scripts/07-install-observability.sh || exit 1
```

Đây là bước cài/tích hợp, không cần chạy lại mỗi lần bật VM. Đọc [trạng thái hiện tại](evidence/TV3-status.md) rồi kiểm tra `helm -n istio-system list`, deployment/pods và route trước. Values Istiod 1.30.7 dùng `resources` ở cấp gốc; gateway giữ `targetPort: 80`, NodePort 30080, một replica và tắt autoscaling cho lab. Prometheus được giới hạn requests/limits và retention bằng patch đi kèm; Kiali/Prometheus dùng ClusterIP, truy cập qua tunnel/port-forward. Xem [hướng dẫn quan sát](../observability/README.md).

Nếu thiếu Helm, chuẩn bị trong phiên cloud cùng TV1. Giao TV2 namespace `istio-system`, Service gateway, port/targetPort/NodePort thật và trạng thái Istiod/gateway Ready. TV2 bật injection ở riêng `bookinfo`, rollout workload baseline và áp route theo runbook; không bật injection namespace hệ thống hoặc toàn cluster. Helper `check-bookinfo-pods.py` đọc PodList JSON, kiểm tra bốn app/Pod Ready và proxy thường hoặc native sidecar; thêm `--baseline` khi kiểm tra trước mesh. Không lấy cố định `READY 2/2` làm tiêu chí.

Thiết kế Bookinfo dùng `productpage:9080 → reviews-v2 → ratings:9080`, caller SA `bookinfo-reviews`, API GET `/ratings/0`. Config `public_http_matches` chọn rõ trang/static/login/logout/API; vẫn cần kiểm tra website có sao, không chỉ HTTP 200. TV2 điền [phiếu app](application-handover.md) và inventory từ runtime, không lấy config thiết kế thay Pod UID/IP/endpoint thật.

## 4. Quan sát, policy và kiểm tra chéo

Trên máy quản trị có Python/kubectl, dùng context đã xác nhận:

```bash
python3 scripts/tv3.py snapshot --context "$CTX"
python3 scripts/tv3.py service-snapshot config/application.json --context "$CTX"
```

Snapshot đọc node/runtime/readiness/pins, không phụ thuộc Rancher; context/IP chỉ chống nhầm thông thường, không định danh duy nhất cụm. `service-snapshot` ghi Service UID/ClusterIP/selector/ports và EndpointSlice ↔ Pod Ready, không tự restart/scale; chụp trước/sau thay Pod và ba lượt scale/phục hồi do TV2 thực hiện. Công cụ ánh xạ endpoint hiện có, chưa tự chứng minh mọi Pod Ready đều có endpoint; đối chiếu đầy đủ theo bài Service.

Thực hiện theo [ma trận TV3](tv3-test-matrix.md), không chép lại kết quả từ hướng dẫn:

- **OBS01:** [observability README](../observability/README.md) hướng dẫn traffic, Prometheus/Kiali và graph caller → target cùng cửa sổ thời gian; TV1 phát request mới rồi tìm lại cạnh.
- **C1–C4:** [security README](../tests/security/README.md) và [NetworkPolicy README](../network/policies/README.md). C2 AuthorizationPolicy riêng rồi phục hồi; C3 NetworkPolicy riêng rồi phục hồi; C4 kết hợp sau ca riêng đạt. Giữ nguyên nguồn/đích/path khi so sánh.
- **SVC02/SVC03/SVC04:** [Service README](../tests/service/README.md). SVC04 dùng Service thử riêng, TV1 sửa selector và TV2 gọi lại; không sửa Service ratings thật để tạo lỗi.
- **IAM01/PUB01/OPS01:** kiểm tra chéo theo ma trận và phiếu bàn giao. Quyền viewer đọc được nhưng patch bị từ chối; frontend public cần bằng chứng ngoài VPC, port-forward không thay PUB01.

Nguồn `probe` phải là app/debug container có `curl` và `getent`, proxy Ready, đúng Pod/SA; chuẩn bị debug cùng Pod theo runbook TV2. Probe không dùng cho baseline trước mesh hoặc client không proxy C1b. Timeout hay 503/504 không tự chứng minh NetworkPolicy chặn đúng: đối chiếu DNS, endpoint, policy, log và lượt phục hồi. Timeout HTTP của công cụ là thời gian socket không nhận dữ liệu, không phải hạn tổng thời gian; Ctrl+C giữ report chưa hoàn tất.

## 5. Lưu evidence và chuyển giao

Output mặc định trong `.generated/` được Git bỏ qua; đọc/loại thông tin nhạy cảm trước khi chuyển kết quả cần chia sẻ vào `docs/evidence/M1`–`M4`. Dùng [mẫu kết quả](evidence/templates/test-result.md): source/commit hoặc hash gói, thời gian/múi giờ, context, nguồn/đích/SA, lệnh, kỳ vọng/thực tế, policy, rollback và người chạy lại. Chỉ đánh dấu Đạt sau phép thử thực và phục hồi; kết quả offline nằm riêng ở [TV3-status](evidence/TV3-status.md).

Phần trình bày dùng request thật → graph/metric cùng thời gian → Service/endpoint để phân biệt “DNS có tên nhưng không có backend” với “backend Ready nhưng nguồn bị chặn”. Ảnh/video dự phòng phải ghi thời điểm. Thực hiện nhận việc, chuyển source và ký nhận theo [phiếu bàn giao TV3](tv3-handover.md).

## 6. Kết thúc phiên cloud

Lưu evidence về laptop, đối chiếu checksum; kiểm tra policy/replica phục hồi, xóa đúng Service/client thử có UID đã ghi và dừng traffic/debug/forwarding. Giữ mesh, giám sát và route đã bàn giao. Entry ephemeral container đã terminated có thể còn trong Pod cho tới khi Pod được thay tự nhiên.

Dừng worker trước, đợi lệnh hoàn tất rồi mới dừng control plane theo [hướng dẫn bật/tắt lab](bat-tat-lab.md). Trên laptop:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\gcloud-local.ps1 compute instances stop wk-01 wk-02 --project=nt132-kubernetes-513805 --zone=asia-southeast1-a --quiet
# Chỉ tiếp tục sau khi hai worker dừng thành công:
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\gcloud-local.ps1 compute instances stop cp-01 --project=nt132-kubernetes-513805 --zone=asia-southeast1-a --quiet
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\gcloud-local.ps1 compute instances list --project=nt132-kubernetes-513805 --filter='name=(cp-01 wk-01 wk-02)' --format='table(name,status)'
```

Chỉ kết thúc khi API xác nhận đủ ba VM `TERMINATED`; stop VM giữ lại disk và cấu hình cụm.
