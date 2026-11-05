# TV3 · Ma trận kiểm thử và bằng chứng

Soạn trên laptop ngày **05/11/2026** theo [phân công TV1](them-thanh-vien.md) và [kế hoạch](plan.md). **Các dòng dưới là kế hoạch, chưa phải kết quả cloud.** Điền giá trị thật từ [phiếu ứng dụng](application-handover.md) trước khi chạy. Dùng [mẫu kết quả](evidence/templates/test-result.md) cho từng lượt; giữ log lỗi và lượt phục hồi.

## 1. Tên dùng trong ma trận

| Token | TV2/TV1 xác nhận trước khi thử |
|---|---|
| `APP_NAMESPACE` | Namespace ứng dụng riêng; không dùng namespace hệ thống |
| `ENTRY_SERVICE:ENTRY_SERVICE_PORT` | Service nhận request từ gateway và cổng Service |
| `TARGET_SERVICE:TARGET_SERVICE_PORT` | Service nội bộ để thử; DNS đầy đủ `TARGET_SERVICE.APP_NAMESPACE.svc.cluster.local` |
| `TARGET_PORT` | Cổng Pod thực nhận traffic; có thể khác cổng Service |
| `APP_PATH` / `TEST_PATH` | Path ngoài gateway tạo luồng nội bộ / API GET cụ thể trên target |
| `ALLOWED_POD` | Pod nguồn trong mesh, đúng `allowed_caller_labels` và `allowed_service_account` |
| `CONTROL_POD` | Pod nguồn trong cùng namespace, cũng có proxy Ready nhưng khác cả caller labels và ServiceAccount |
| `NON_MESH_CLIENT` | Client riêng không có proxy, chỉ tạo khi TV1/TV2 thống nhất quyền và phạm vi thử |
| `TARGET_POD` | Pod Ready được selector Service chọn; ghi tên, UID, IP, node thật |
| `PUBLIC_IP:30080` | Frontend LB do TV1 bàn giao sau khi app qua gateway đã đạt |

Nguồn thử chạy bằng app/debug container có `curl` và công cụ DNS phù hợp. Không exec trong `istio-proxy` để thay nguồn ứng dụng. Không tự chọn Bookinfo hoặc tự đoán Service/Deployment từ tên placeholder. `config/application.json` thật giữ ngoài Git theo `.gitignore`; bảng này chỉ chứa quy ước và kỳ vọng.

## 2. Cổng kiểm tra trước khi đổi policy

1. TV1 xác nhận cụm hiện có Ready, cung cấp phiên kubectl/Helm đúng quyền và trạng thái VM; TV3 tiếp nhận Calico đang chạy, không bootstrap lại.
2. Theo quy trình TV1, TV2 bàn giao baseline ứng dụng gọi nhau được trước khi TV3 tích hợp mesh. Sau injection/route, kiểm tra lại app/Service/EndpointSlice trước các ca quyền.
3. Đọc policy ứng dụng, root namespace mesh và các luật mạng có thể liên quan. Baseline C0 phải được xác minh, không xóa luật không thuộc bài thử để tạo baseline giả.
4. Ghi thời gian, source/commit hoặc hash gói, context, namespace, nguồn/đích, danh tính/nhãn, DNS, Service UID/ClusterIP và endpoint Ready. Chỉ đổi một lớp ở C2/C3.

## 3. C0–C4: cùng một request, đổi riêng lớp đang thử

Các ca HTTP dưới dùng GET `TEST_PATH` tới `TARGET_SERVICE:TARGET_SERVICE_PORT`, trừ khi dòng ghi rõ URL khác. Trạng thái mặc định của toàn bộ ma trận: **Chưa chạy trên cloud**.

| Ca / chủ trì → người chạy lại | Nguồn → đích / port / method-path | Điều kiện đầu và lớp thay đổi | Kỳ vọng và bằng chứng phải lưu | Hoàn tác / kiểm tra phục hồi |
|---|---|---|---|---|
| C0 · TV2/TV3 → TV1 | `ALLOWED_POD` và `CONTROL_POD` → target Service / Service port / GET `TEST_PATH` | App đã có proxy Ready, endpoint Ready; chưa có luật hạn chế hai nguồn theo baseline đã thống nhất | Cả hai HTTP 200/nội dung đúng. Lưu DNS, Pod UID/labels/SA, targetRef và policy đang có. Đây là đối chứng trước STRICT | Giữ cấu hình app; nếu chưa đạt thì chẩn đoán trước khi áp luật |
| C1 / SEC01 · TV2 → TV3 | Cùng hai nguồn trong mesh → cùng target/port/GET | C0 đạt; chỉ bật PeerAuthentication STRICT theo target | Cả hai vẫn 200; lưu bằng chứng mTLS đúng cặp nguồn/đích từ metric/proxy cùng thời gian. YAML STRICT một mình chưa chứng minh request đã dùng mTLS | Giữ STRICT làm baseline C1 cho C2–C4; nếu cần trở về C0, gỡ đúng luật mới tạo theo thỏa thuận |
| C1b · TV2/TV3 → TV1 | `NON_MESH_CLIENT` → cùng target/port/GET | Cần được cấp quyền tạo client riêng; client này gọi thành công khi chưa STRICT; chưa có AuthorizationPolicy/NetworkPolicy hạn chế; chỉ bật STRICT như C1 | Request không mTLS không được phục vụ thành công. Ghi lỗi TLS/kết nối và cấu hình nguồn không proxy; không mặc định đây là HTTP 403. So với lượt 200 trước STRICT để tách lỗi mạng | Khôi phục STRICT về trạng thái đã thống nhất, xóa riêng client thử sau khi lưu log. Không tắt injection của namespace đang dùng để tạo client |
| C2 / SEC02 · TV2 → TV3/TV1 | `ALLOWED_POD` → target / Service port / GET `TEST_PATH` | C1 đạt; chỉ thêm AuthorizationPolicy cho principal/method/path đúng | 200/nội dung đúng, target endpoint vẫn Ready; nguồn/SA/path đúng như manifest | Gỡ riêng AuthorizationPolicy thử; lặp cả hai nguồn C1 đều 200 |
| C2 đối chứng danh tính · TV2 → TV1 | `CONTROL_POD` → cùng target/port/GET | Cùng lượt C2; nguồn khác ServiceAccount, NetworkPolicy hạn chế chưa bật | 403 tại proxy đích, có log RBAC từ chối đúng request/time. DNS và endpoint vẫn tồn tại | Cùng lượt phục hồi C2: gỡ đúng luật, source đối chứng trở lại 200 |
| C2 đối chứng API · TV2 → TV3 | `ALLOWED_POD` → cùng target/port nhưng path hoặc method đã thống nhất là không được cho phép | C2 đã có lượt hợp lệ; chọn API thử không gây thay đổi dữ liệu | 403/RBAC đối với method/path sai, không nhầm 404 của ứng dụng với policy từ chối. Probe hiện chỉ gửi GET/path hợp lệ; ca này cần lệnh riêng TV2 xác nhận | Gỡ đúng AuthorizationPolicy rồi gọi lại API hợp lệ, không lấy response của API vốn không tồn tại làm bằng chứng phục hồi |
| C3 / SEC03 · TV3 → TV1 | `ALLOWED_POD` và `CONTROL_POD` → target / TCP `TARGET_PORT` qua Service / GET `TEST_PATH` | Đã gỡ AuthorizationPolicy thử và chạy lại C1 đều 200; chỉ thêm NetworkPolicy ingress chọn target, cho caller labels trong cùng namespace | Nguồn hợp lệ 200; nguồn sai thất bại kết nối/upstream, nhưng DNS vẫn phân giải và target còn Ready. Lưu stdout/stderr/exit code, policy, endpoint và log proxy nếu có | Gỡ riêng NetworkPolicy; cả hai nguồn phải trở lại 200 khi giữ baseline STRICT |
| C4 / SEC04 · TV1 → TV2/TV3 | Hai nguồn trực tiếp → target; thêm browser → gateway → entry → caller → target / các port thực / GET API và `APP_PATH` | C2/C3 riêng và các lượt phục hồi đã đạt; bật cả hai luật | Nguồn hợp lệ qua, nguồn sai bị chặn; website vẫn có nội dung đúng. Ghi chính xác cả hai luật đang bật; không suy từ một timeout ra lớp gây lỗi | Gỡ riêng hai luật thử theo thứ tự, xác nhận C1 phục hồi. Giữ/gỡ STRICT theo trạng thái nhóm đã thống nhất; không xóa namespace |

C1 kiểm tra **hai nguồn cùng trong mesh** vẫn hoạt động dưới STRICT; C1b kiểm tra **nguồn ngoài mesh** bị từ chối. Không thay hai ca này cho nhau. C1b cần đầu vào/quyền riêng; nếu chưa có thì ghi **Bị chặn – chưa có client đối chứng được cấp quyền**, không ghi Đạt.

Lỗi 503/504 từ proxy nguồn ở C3/C4 cần đối chiếu endpoint, DNS, log upstream và baseline → bật luật → gỡ luật → phục hồi. `scripts/tv3.py probe` chỉ tự khớp lỗi mạng trực tiếp curl exit 7/28 với HTTP `000`; nó giữ upstream error để xem xét thủ công, không tự kết luận SEC03 đạt. Xem [quy trình C1–C4](../tests/security/README.md) và [phạm vi NetworkPolicy](../network/policies/README.md).

## 4. Các ca mạng, Service, quan sát và vận hành

| ID / chủ trì → người chạy lại | Nguồn → đích / port / thao tác | Điều kiện và kỳ vọng | Bằng chứng / hoàn tác |
|---|---|---|---|
| NET01 · TV3 → TV2 | Client `wk-02` → server `wk-01` và chiều ngược / TCP 80 / GET `/` qua Pod IP, ClusterIP, DNS | Cụm/CNI đã được TV1 bàn giao; fixture riêng được xác minh; sáu HTTP 200, đúng hai worker khác nhau theo InternalIP/FQDN | Log từng attempt và HTTP/exit, Pod IP/node, Service/EndpointSlice, source hash; dọn riêng fixture sau khi kiểm tra namespace không có tài nguyên khác |
| SVC01 · TV2 → TV1/TV3 | Client hợp lệ → target Service / cổng thật / GET API | Selector chọn Pod Ready; port/targetPort và targetRef đúng | Service UID/ClusterIP/selector/ports, Pod UID/IP/labels, endpoint; thao tác đọc không cần rollback |
| SVC02 · TV2 → TV3 | Cùng nguồn → cùng DNS/Service port/GET trước và sau TV2 thay Pod | Pod mới Ready có UID mới; Service UID/ClusterIP giữ nguyên, lời gọi phục hồi; ghi gián đoạn thật | Hai `service-snapshot.json`, HTTP/DNS/time, targetRef UID; TV2 giữ đúng replica/manifest gốc |
| SVC03 · TV2 → TV3 | Cùng nguồn → cùng target/port/GET trước/sau scale và sau rollback | Tập endpoint phản ánh đủ Pod Ready; không dùng vài response giống nhau để khẳng định chia tải đều | Snapshot ba trạng thái, replica gốc/đã scale, lời gọi; TV2 trả replica gốc và TV3 thử lại |
| SVC04 · TV3 → TV1 sửa / TV2 gọi lại | Nguồn được phép → Service thử riêng / cổng giống target / GET API thật | DNS phân giải khi selector sai nhưng không có endpoint Ready; sau TV1 sửa selector có endpoint và HTTP 200; policy giữ nguyên | Service thử cùng UID/ClusterIP trước-sau, endpoint/targetRef, DNS/HTTP; xóa riêng Service thử, gọi lại Service gốc |
| OBS01 · TV3 → TV1 | Laptop hoặc cp-01 phát GET `APP_PATH` → gateway:80 (port-forward laptop:8080) → entry/caller → target | App có sidecar, route và Prometheus/Kiali; request thực sự tạo luồng nội bộ | Timestamp traffic, metric và graph cùng cửa sổ 5 phút, cạnh caller → target; TV1 tạo request mới và tìm lại cạnh. Dừng traffic/forwarding sau buổi |
| IAM01 · TV1 → TV3 | Danh tính viewer → API/dashboard / quyền đọc node/workload và `can-i patch deployments.apps` ở namespace app | Dùng đúng viewer do TV1 cấp; đọc được dữ liệu demo, quyền patch là `no` | Kết quả `can-i`/UI với danh tính và phạm vi; không thực hiện patch thật để thử, không tự đổi RBAC |
| PUB01 · TV1 → TV3/TV2 | Laptop ngoài VPC → `PUBLIC_IP:30080` / GET `APP_PATH` | Chỉ sau TV1 bàn giao LB/health/firewall và app qua gateway đạt | IP frontend/URL/status/nội dung/timestamp, backend health của TV1, graph cùng thời điểm; không thay bằng port-forward, TV1 quản lý vòng đời LB |
| OPS01 · Cả nhóm → người chưa chạy ca đó | Người nhận source/commit/gói → chạy lại dashboard và ít nhất một ca thực | Có đủ đầu vào, lệnh và evidence thật; mọi sai khác được ghi nhận | Source commit/hash, người giao/nhận, bước đã chạy lại, lỗi mở và trạng thái policy; trả trạng thái lab theo biên bản |

## 5. Đóng hồ sơ một lượt chạy

Mỗi lượt ghi **Chưa chạy / Bị chặn / Chưa đạt / Đạt**, người chạy/người kiểm tra chéo, source/commit hoặc hash gói, thời gian và múi giờ, context/namespace, Pod nguồn-đích, nhãn/ServiceAccount, DNS/Service/endpoint, policy đang bật, lệnh, kết quả mong đợi/thực tế, log/ảnh/metric và kết quả rollback. Xem [mẫu evidence](evidence/templates/test-result.md).

Hiện tại đã hoàn tất phần **soạn ma trận trên laptop**. Cột kết quả thực tế và ký nhận chỉ điền sau khi chạy trên cụm được cấp quyền; không biến kết quả unit test/mock local thành nghiệm thu NET01/OBS01/SEC01–04.
