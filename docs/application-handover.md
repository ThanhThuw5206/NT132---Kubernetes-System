# Thông tin ứng dụng do TV2 bàn giao

TV2 tự chọn mã nguồn hoặc ứng dụng phù hợp, kiểm tra giấy phép, ghim phiên bản và triển khai manifest trong apps/. TV1 dùng thông tin bàn giao để kiểm tra gateway và load balancer. TV3 dùng cùng thông tin để thiết lập quan sát và policy.

| Trường | TV2 điền trước khi tích hợp |
|---|---|
| Nguồn và phiên bản | URL repo, tag/commit, giấy phép, image/digest |
| APP_NAMESPACE | Namespace thực của ứng dụng |
| ENTRY_SERVICE | Service tiếp nhận request từ gateway |
| CALLER_SERVICE | Workload được phép gọi Service đích |
| TARGET_SERVICE | Service đích dùng để thử DNS, selector, EndpointSlice |
| CALLER_DEPLOYMENT / TARGET_DEPLOYMENT | Tên Deployment thực, số replica ban đầu |
| CALLER_SERVICE_ACCOUNT | Danh tính workload được phép |
| APP_PATH | Đường dẫn website qua ingress, bắt đầu bằng / |
| TEST_PATH | Đường dẫn HTTP ở Service đích, bắt đầu bằng / |
| ENTRY_SERVICE_PORT / TARGET_SERVICE_PORT / TARGET_PORT | Port Service đầu vào, port Service đích (SERVICE_PORT trong plan) và cổng ứng dụng trong Pod; ghi rõ nếu khác nhau |
| TARGET_LABEL / CALLER_LABEL | Giá trị nhãn app thực dùng trong selector; ghi thêm nếu key khác app |
| Luồng hợp lệ | Nguồn → đích, protocol/port, response và nội dung mong đợi |
| Nguồn thử bị chặn | Pod trong cùng namespace dùng làm đối chứng, có ServiceAccount khác và nhãn không khớp caller; ghi tên container thực thi |
| Lệnh tạo traffic | Request thực sự phát sinh lời gọi giữa các workload |
| Nhu cầu tài nguyên | CPU/RAM, dữ liệu, volume và outbound nếu cần |

Các tên viết hoa trong plan và hướng dẫn TV1 là ô điền theo bảng này, chưa phải tên resource có thể apply. Thay toàn bộ token bằng giá trị thật trước khi chạy lệnh hoặc áp YAML. Kiểm tra protocol để lựa chọn phép thử đúng: ca HTTP 403 áp dụng cho đích HTTP, ca lọc mạng kiểm tra kết nối ở cổng đích. Với thử thay Pod/scale, đọc tên Deployment từ bảng thay vì suy ra từ tên Service.

Để phục vụ trọng tâm đồ án, ứng dụng cần tạo được ít nhất một luồng từ workload nguồn đến một Kubernetes Service đích, quan sát được endpoint khi Pod thay đổi và có nguồn thử thứ hai để kiểm tra quyền. Nhóm cùng xác nhận các điều kiện này sau khi TV2 chọn ứng dụng.

## Điều kiện TV3 cần xác nhận trước khi nhận việc

| Điều kiện | TV2 bàn giao / TV3 kiểm tra | Trạng thái ban đầu |
|---|---|---|
| Hai nguồn baseline | Cùng namespace và cùng gọi thành công một API GET cụ thể ở target trước khi có luật hạn chế; có sidecar Ready | Chưa bàn giao |
| Container chạy phép thử | Tên app/debug container có công cụ HTTP và DNS theo công cụ probe đang dùng; không exec vào `istio-proxy` để giả làm ứng dụng | Chưa bàn giao |
| Tách hai lớp quyền | Nguồn hợp lệ đúng labels/ServiceAccount; nguồn đối chứng khác cả hai. Chỉ đổi ServiceAccount chưa tạo ca NetworkPolicy khác biệt | Chưa bàn giao |
| Luồng ingress và nội bộ | Ghi luồng thật, ví dụ gateway → entry → caller → target (entry có thể cũng là caller); chỉ ra request ngoài nào phát sinh lời gọi nội bộ và các nguồn hợp lệ khác vào target | Chưa bàn giao |
| Giao thức/API | HTTP GET path cụ thể, mã trả lời và nội dung mong đợi; nếu app dùng TCP/gRPC hoặc chỉ có POST thì thống nhất phép thử phù hợp trước | Chưa bàn giao |
| Selector/endpoint | Target Service selector khớp Pod Ready; `port`, `targetPort`, tên Deployment và endpoint/targetRef đã đối chiếu | Chưa bàn giao |
| Thay Pod/scale | Deployment và số replica gốc; TV2 thực hiện thay đổi, TV3 gọi/quan sát; có lệnh rollback và ghi gián đoạn nếu có | Chưa bàn giao |
| Policy nền | Các policy ở namespace app và root namespace mesh có thể ảnh hưởng phép thử; baseline/phạm vi STRICT và trạng thái cần phục hồi | Chưa bàn giao |
| Cấu hình tích hợp | `config/application.json` đã thay placeholder, khớp config/schema hiện có; file vận hành không nằm trong gói source chia sẻ | Chưa bàn giao |

Ghi người bàn giao/người nhận, source/commit hoặc hash gói local, thời gian, kết quả baseline và lỗi còn mở khi cập nhật các dòng này. TV2 tiếp tục sở hữu manifest/workload/Service/route và xác nhận luật Istio; TV3 nhận dữ liệu để kiểm tra mạng/quan sát/NetworkPolicy. Nếu một điều kiện chưa có, ghi rõ TV3 còn làm được phần nào độc lập và phần nào đang chờ, không đánh dấu app hoặc ca bảo mật đã đạt.

## Giao nhận theo thứ tự

1. **TV3 → TV2:** mạng xuyên worker và Istiod/gateway Ready, namespace/Service gateway/cổng thật. TV2 mới triển khai workload có sidecar và route.
2. **TV2 → TV3:** điền bảng trên, gửi đường dẫn manifest và request baseline thật; TV3 dựng OBS01 và chuẩn bị SEC03/SVC04.
3. **TV2 → TV3 → TV1:** TV2 lưu SEC01/SEC02 và phục hồi baseline; TV3 chạy riêng SEC03 và phục hồi; TV1 tái hiện rồi chủ trì tích hợp SEC04.
4. **TV3 → TV1/TV2:** tình huống selector sai để TV1 tự sửa, TV2 gọi lại; sau đó đóng gói evidence để cả nhóm chạy lại OPS01.

Xem [phiếu bàn giao TV3](tv3-handover.md) cho cách nhận code chưa push, danh sách người nhận và tiêu chí nghiệm thu.
