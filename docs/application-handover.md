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
| SERVICE_PORT / TARGET_PORT | Port của Service và cổng ứng dụng trong Pod |
| TARGET_LABEL / CALLER_LABEL | Giá trị nhãn app thực dùng trong selector; ghi thêm nếu key khác app |
| Luồng hợp lệ | Nguồn → đích, protocol/port, response và nội dung mong đợi |
| Nguồn thử bị chặn | Pod và ServiceAccount khác dùng làm đối chứng |
| Lệnh tạo traffic | Request thực sự phát sinh lời gọi giữa các workload |
| Nhu cầu tài nguyên | CPU/RAM, dữ liệu, volume và outbound nếu cần |

Các tên viết hoa trong plan và hướng dẫn TV1 là ô điền theo bảng này, chưa phải tên resource có thể apply. Thay toàn bộ token bằng giá trị thật trước khi chạy lệnh hoặc áp YAML. Kiểm tra protocol để lựa chọn phép thử đúng: ca HTTP 403 áp dụng cho đích HTTP, ca lọc mạng kiểm tra kết nối ở cổng đích. Với thử thay Pod/scale, đọc tên Deployment từ bảng thay vì suy ra từ tên Service.

Để phục vụ trọng tâm đồ án, ứng dụng cần tạo được ít nhất một luồng từ workload nguồn đến một Kubernetes Service đích, quan sát được endpoint khi Pod thay đổi và có nguồn thử thứ hai để kiểm tra quyền. Nhóm cùng xác nhận các điều kiện này sau khi TV2 chọn ứng dụng.
