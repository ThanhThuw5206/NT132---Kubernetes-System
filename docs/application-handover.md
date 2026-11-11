# Thông tin ứng dụng do TV2 bàn giao

TV2 tự chọn mã nguồn hoặc ứng dụng phù hợp, kiểm tra giấy phép, ghim phiên bản và triển khai manifest trong apps/. TV1 dùng thông tin bàn giao để kiểm tra gateway và load balancer. TV3 dùng cùng thông tin để thiết lập quan sát và policy.

**Thiết kế đã nhận và tích hợp local ngày 06/11/2026:** Bookinfo từ Istio `1.30.7`, namespace `bookinfo`, entry `productpage:9080`, caller `reviews-v2` / SA `bookinfo-reviews`, target `ratings:9080` / Deployment `ratings-v1`, Pod TCP 9080; website `/productpage`, API GET `/ratings/0`. Source/hash/giấy phép và cấu hình nằm trong [apps/bookinfo](../apps/bookinfo/README.md). Đây là thông số thiết kế; bảng nghiệm thu bên dưới vẫn chờ dữ liệu cloud thật.

| Trường | Giá trị thực (Bookinfo) |
|---|---|
| Nguồn và phiên bản | github.com/istio/istio `samples/bookinfo`, tag **1.30.7**, Apache-2.0; image `registry.istio.io/release/examples-bookinfo-*-v*:1.20.3`; hash/provenance tại [source-lock.json](../apps/bookinfo/source-lock.json) |
| APP_NAMESPACE | `bookinfo` |
| ENTRY_SERVICE | `productpage` (nhận request từ gateway) |
| CALLER_SERVICE | `reviews` (phiên bản chạy: **reviews-v2**) |
| TARGET_SERVICE | `ratings` (thử DNS/selector/EndpointSlice) |
| CALLER_DEPLOYMENT / TARGET_DEPLOYMENT | `reviews-v2` (1 replica) / `ratings-v1` (1 replica gốc); `reviews-v1`,`reviews-v3` = 0 |
| CALLER_SERVICE_ACCOUNT | `bookinfo-reviews` |
| APP_PATH | `/productpage` |
| TEST_PATH | `/ratings/0` (sách ID 0 — đúng ID website dùng) |
| ENTRY_SERVICE_PORT / TARGET_SERVICE_PORT / TARGET_PORT | `9080` / `9080` / `9080` (giống nhau) |
| TARGET_LABEL / CALLER_LABEL | `app=ratings` / `app=reviews` (key `app`) |
| Luồng hợp lệ | `reviews-v2` (SA `bookinfo-reviews`) → `GET http://ratings.bookinfo.svc.cluster.local:9080/ratings/0` → HTTP **200**, body JSON có `ratings` |
| Nguồn thử bị chặn | `productpage-v1` (SA `bookinfo-productpage`, nhãn `app=productpage`) gọi **thẳng** `ratings:9080/ratings/0`; exec trong container app `productpage` hoặc debug cùng Pod (không exec `istio-proxy`) |
| Lệnh tạo traffic | Qua gateway: `curl http://127.0.0.1:8080/productpage` (sinh productpage→reviews-v2→ratings). Trực tiếp đích: `exec` curl từ Pod reviews-v2/productpage tới `ratings:9080/ratings/0` |
| Nhu cầu tài nguyên | Image công khai, **không DB/PVC**, không outbound đặc biệt; requests/limits nhẹ do `prepare-bookinfo.py` gắn; theo dõi RAM worker vì có Rancher/fleet |

Các tên viết hoa trong plan và hướng dẫn TV1 là ô điền theo bảng này, chưa phải tên resource có thể apply. Thay toàn bộ token bằng giá trị thật trước khi chạy lệnh hoặc áp YAML. Kiểm tra protocol để lựa chọn phép thử đúng: ca HTTP 403 áp dụng cho đích HTTP, ca lọc mạng kiểm tra kết nối ở cổng đích. Với thử thay Pod/scale, đọc tên Deployment từ bảng thay vì suy ra từ tên Service.

Để phục vụ trọng tâm đồ án, ứng dụng cần tạo được ít nhất một luồng từ workload nguồn đến một Kubernetes Service đích, quan sát được endpoint khi Pod thay đổi và có nguồn thử thứ hai để kiểm tra quyền. Nhóm cùng xác nhận các điều kiện này sau khi TV2 chọn ứng dụng.

## Điều kiện TV3 cần xác nhận trước khi nhận việc

| Điều kiện | TV2 bàn giao / TV3 kiểm tra | Trạng thái |
|---|---|---|
| Hai nguồn baseline | `reviews-v2` và `productpage-v1` cùng gọi `ratings:9080/ratings/0` thành công trước luật hạn chế | ✅ baseline 06/11 (web có sao); TV3 đã kiểm C1 sau mesh |
| Container chạy phép thử | app container của reviews-v2/productpage, hoặc debug cùng Pod; không exec `istio-proxy` | ✅ đã thống nhất; TV3 đã dùng debug netshoot cùng Pod |
| Tách hai lớp quyền | hợp lệ = `app=reviews`/SA `bookinfo-reviews`; đối chứng = `app=productpage`/SA `bookinfo-productpage` | ✅ đã bàn giao |
| Luồng ingress và nội bộ | `gateway → productpage → reviews-v2 → ratings`; productpage cũng gọi details | ✅ đã bàn giao |
| Giao thức/API | HTTP `GET /ratings/0` → 200, JSON có `ratings` | ✅ đã bàn giao |
| Selector/endpoint | `ratings` selector `app=ratings`, port/targetPort 9080, Deployment `ratings-v1`; endpoint/targetRef đã đối chiếu | ✅ SVC01 06/11 (ClusterIP 10.105.126.134) |
| Thay Pod/scale | Deployment `ratings-v1`, replica gốc **1**; rollback về 1 | ✅ SVC02/SVC03 06/11 (đã trả về 1 replica) |
| Policy nền | PeerAuthentication STRICT chọn `app=ratings`; AuthorizationPolicy cho principal reviews GET /ratings/0; phục hồi về baseline | ✅ render từ `application.bookinfo.json`; TV3 đã chạy C1–C4 và phục hồi |
| Cấu hình tích hợp | `config/application.json` copy từ `apps/bookinfo/application.bookinfo.json`, render OK | ✅ đã bàn giao (file vận hành ngoài Git) |

Ghi người bàn giao/người nhận, source/commit hoặc hash gói local, thời gian, kết quả baseline và lỗi còn mở khi cập nhật các dòng này. TV2 tiếp tục sở hữu manifest/workload/Service/route và xác nhận luật Istio; TV3 nhận dữ liệu để kiểm tra mạng/quan sát/NetworkPolicy. Nếu một điều kiện chưa có, ghi rõ TV3 còn làm được phần nào độc lập và phần nào đang chờ, không đánh dấu app hoặc ca bảo mật đã đạt.

## Giao nhận theo thứ tự

1. **TV1/TV3 → TV2:** cụm/Calico hiện có, phiên đúng quyền và NET01. TV2 dùng workload baseline không injection, chứng minh Service/DNS và request nghiệp vụ rồi TV1 review; chưa cần chờ Istio.
2. **TV3 → TV2:** cài Istio/gateway và quan sát sau baseline; giao namespace/Service gateway/cổng thật khi Ready. TV2 bật injection/rollout app, áp route rồi xác minh Pod/app/proxy Ready và baseline lần nữa.
3. **TV2 → TV3:** điền bảng trên bằng dữ liệu runtime, nguồn thật và request; TV3 chạy OBS01 và chuẩn bị SEC03/SVC04.
4. **TV2 → TV3 → TV1:** TV2 lưu SEC01/SEC02 và phục hồi baseline; TV3 chạy riêng SEC03 và phục hồi; TV1 tái hiện rồi chủ trì tích hợp SEC04.
5. **TV3 → TV1/TV2:** tình huống selector sai để TV1 tự sửa, TV2 gọi lại; sau đó đóng gói evidence để cả nhóm chạy lại OPS01.

Xem [phiếu bàn giao TV3](tv3-handover.md) cho cách lấy branch, chuyển thêm sửa đổi chưa commit nếu có, danh sách người nhận và tiêu chí nghiệm thu.
