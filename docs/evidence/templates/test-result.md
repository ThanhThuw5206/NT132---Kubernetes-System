# Mẫu kết quả kiểm thử TV3

Đây là mẫu, chưa phải bằng chứng của một lần chạy. Sao chép sang thư mục mốc tương ứng trước khi điền.

| Trường | Giá trị |
|---|---|
| Test / mốc | NET01 / OBS01 / SEC03 / SVC04 / PUB01 |
| Trạng thái | Chưa chạy |
| Người chạy / người kiểm tra chéo | Chưa điền / Chưa điền |
| Commit source / thay đổi local | Chưa điền |
| Thời gian bắt đầu/kết thúc + múi giờ | Chưa điền, dùng UTC+07:00 hoặc ghi rõ UTC |
| Context / namespace | Chưa điền |
| Node/Pod/UID nguồn và đích | Chưa điền |
| ServiceAccount / labels nguồn | Chưa điền |
| Service DNS / ClusterIP / port / targetPort | Chưa điền |
| EndpointSlice/targetRef trước và sau | Chưa điền |
| Policy namespace/root đang bật | Chưa điền |
| Phiên bản thực tế | Chưa điền |
| Lệnh và điều kiện đầu | Chưa điền |
| Kết quả mong đợi | Chưa điền |
| Kết quả thực tế / stdout / stderr / exit code | Chưa chạy |
| Log/JSON/ảnh/metric và cùng khoảng thời gian | Chưa có |
| Hoàn tác và kết quả phục hồi | Chưa chạy |
| Người khác chạy lại / khác biệt quan sát | Chưa chạy |
| Việc bị chặn / người bàn giao đầu vào | Chưa điền |

Chỉ đổi sang **Đạt** khi có kết quả thực và người thứ hai chạy lại. Khi ghi **Bị chặn**, chỉ ra thiếu đầu vào nào; khi ghi **Chưa đạt**, giữ log lỗi và cách khôi phục. Không đưa Secret/token/kubeconfig vào bằng chứng.
