# TV3 · Phạm vi và việc có thể làm hiện tại

Rà soát ngày **05/11/2026 (Asia/Saigon)** theo source nền `17aaed9`, [kế hoạch của repo](plan.md) và file người dùng cung cấp `E:\Down\KE_HOACH_TONG_THE_KUBERNETES_3_VM_GOOGLE_CLOUD.md` (SHA256 `591D4A3BD7EAC2ACAF78C0BE148D8E3EF23D47D49683412CA5B660F3FBA0CCB2`). Kế hoạch là yêu cầu và lịch dự kiến; các lệnh trong đó chưa phải thao tác đã chạy.

**Mục tiêu của TV3:** chứng minh một request tới tên Service có đi được giữa các Pod, có backend Ready và có được phép truy cập hay không. Calico/Istio/Kiali là công cụ phục vụ bài kiểm chứng Kubernetes Service. Chỉ cài dashboard hoặc có script chưa hoàn thành mục tiêu này.

Bắt đầu tại [runbook TV3](tv3-runbook.md). Các thành viên nhận việc đọc [phiếu bàn giao TV3](tv3-handover.md); trạng thái có bằng chứng nằm tại [TV3-status.md](evidence/TV3-status.md).

## 1. Phạm vi theo phân công đồ án

| Việc | TV3 làm đến đâu? | Người phối hợp / bằng chứng |
|---|---|---|
| `wk-02` và mạng Pod | Chuẩn bị/join worker, chốt phiên bản/CIDR, cài Calico một lần cho cụm; chẩn đoán Pod IP/DNS | TV1 giao VM/join và xử lý VPC/firewall; TV2 chạy lại NET01 |
| Istio nền | Cài Istiod và ingress gateway, giao namespace/Service/ports/trạng thái Ready | TV2 sở hữu ứng dụng, injection của workload và route; phối hợp trước khi đổi gateway Service |
| Quan sát | Cài Prometheus/Kiali, phát request thật và chứng minh caller → target | TV2 giao request/ứng dụng; TV1 tự lặp lại graph/metric OBS01 |
| NetworkPolicy | Chủ trì ca chỉ có luật mạng: DNS còn phân giải, backend còn Ready, nguồn đúng qua được, nguồn sai thất bại; gỡ luật và kiểm tra phục hồi | TV2 bàn giao baseline sau ca Istio; TV1 tái hiện SEC03 |
| Lỗi selector | Tạo Service thử riêng không có backend, để TV1 tìm/sửa selector; TV2 gọi lại cùng URL | TV3 lưu trước/sau và dọn riêng Service thử; SVC04 |
| Kiểm tra chéo | IAM01, SVC02, SEC01, SVC03, PUB01 và chạy lại OPS01 | Chủ trì chính vẫn theo bảng kiểm thử của plan; TV3 ghi kết quả độc lập |
| Hồ sơ/demo | Ma trận nguồn-đích, phiên bản thực, log/metric/ảnh, hướng dẫn apply/rollback và phần trình bày 2 phút | Có người thứ hai chạy lại; không lấy kết quả test local thay nghiệm thu cloud |

TV1 vẫn chủ trì cloud/Rancher/LB; TV2 chủ trì workload/Service, mTLS/AuthorizationPolicy và thay Pod/scale. TV3 hỗ trợ kiểm chứng các phần này, không tự chọn ứng dụng hoặc tạo thêm hạ tầng thay các bạn. Chia tải nhiều version chỉ làm nếu rubric yêu cầu, sau khi luồng cơ bản và rollback đã đạt.

## 2. Những phần đã chuẩn bị trên máy

Đã có fixture/script NET01 hai chiều; công cụ `scripts/tv3.py` để thu snapshot, tạo traffic, ghi phép thử DNS/HTTP và sinh bài selector riêng; hướng dẫn OBS01, C1–C4, SVC04; ma trận NetworkPolicy và mẫu evidence. Xem [trạng thái kiểm tra local](evidence/TV3-status.md) để biết lệnh và kết quả gần nhất.

Nhánh bàn giao là `tv3/istio-network`, phát triển từ source nền `17aaed9`. Các thành viên lấy đúng branch/commit theo [phiếu bàn giao](tv3-handover.md); branch TV1 hoặc commit nền chưa chứa phần bổ sung TV3. **`git archive HEAD` không lấy file chưa commit**: nếu có sửa đổi local mới, dùng thêm gói overlay/checksum.

## 3. Những việc có thể làm tiếp ngay

1. Chạy kiểm tra offline bằng uv như runbook; rà các manifest sinh ra bằng cấu hình thật sau khi TV2 bàn giao.
2. Điền bảng đầu vào/giao nhận trong phiếu bàn giao: người sở hữu, giá trị đã xác minh, lỗi còn mở, thành viên nào đang chờ. Chưa có giá trị thật thì để **Chưa bàn giao**.
3. Lấy branch TV3 để nhóm xem/chạy lại; chỉ đóng gói overlay nếu cần chia sẻ sửa đổi local chưa commit. Đọc danh sách file/checksum trước khi chuyển; tạo gói không tự gửi cho ai.
4. Khi TV1 giao cụm: thực hiện `wk-02 → Calico → NET01 → Istio nền`; báo TV2 ngay khi gateway/mesh Ready, không chờ hoàn tất toàn bộ dashboard mới bàn giao.
5. Khi TV2 giao app: OBS01 trước; kiểm tra chéo các bài Service; sau đó cô lập ca SEC03 và SVC04 theo lịch/điều kiện thực tế.

## 4. Các khác biệt với file kế hoạch gửi kèm

| Nội dung | Quyết định thể hiện trong source hiện tại |
|---|---|
| Bookinfo / `reviews → ratings` | Branch mới để TV2 chọn ứng dụng. Chỉ dùng tên Bookinfo nếu TV2 xác nhận; [phiếu app](application-handover.md) quy định dữ liệu thật cần bàn giao. |
| Control plane 4 GiB/20 GB, worker disk 30 GB | Terraform hiện đặt cả ba VM 8 GiB, disk 30 + 40 + 40 GB. Đối chiếu output thật; không dựng trùng VM bằng lệnh thủ công. |
| Headlamp tuần đầu, Rancher tuần 2 | Source triển khai Rancher sớm; TV1 sở hữu dashboard quản trị. TV3 tập trung Prometheus/Kiali và kiểm tra quyền viewer khi được giao. |
| NodePort tuần 2 | Helm values tạo NodePort HTTP `30080` ngay; cloud LB vẫn tùy chọn. NodePort/port-forward không thay bằng chứng truy cập frontend từ ngoài VPC. |
| Runbook cloud thử cộng dồn policy | Nghiệm thu cần có C1, C2 riêng, phục hồi, C3 riêng, phục hồi rồi C4 cả hai. TV2 xác nhận luật Istio; TV3 chủ trì luật mạng. |

Lệnh hạ tầng theo [deploy-cloud.md](deploy-cloud.md), trách nhiệm/tiêu chí theo plan với tên ứng dụng do TV2 giao. Những thay đổi về kiến trúc/ports cần được ghi nhận chung trước khi áp lên cụm.

## 5. Mốc và giới hạn kết luận

Theo lịch dự kiến: **M1 06/11** là mạng/ứng dụng/graph; **M2 13/11** là đường public và Rancher; **M3 20/11** là C1–C4; **M4 27/11** là bài Service, tái hiện và bàn giao. Ngày 05/11 ưu tiên NET01/OBS01 nếu cụm và app đã có; chưa có đầu vào thì ghi phụ thuộc đang thiếu, không suy ra các ngày trước đã xong.

Hiện chưa có nghiệm thu cloud trong phiên làm việc này. Repo và test offline không chứng minh VM đã Ready, Kiali có traffic hay policy đã chặn đúng. Chỉ đổi sang **Đạt** khi có kết quả thực, thao tác phục hồi và người khác chạy lại được.
