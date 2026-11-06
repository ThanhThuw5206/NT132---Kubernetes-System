# Trạng thái phần ứng dụng TV2 · cập nhật local 06/11/2026

TV2 chọn Bookinfo và giao tài liệu/config tại `4377766` (từ TV3 `89f106d`). Đợt tích hợp sau đó trên laptop TV3 sửa config/hướng dẫn, thêm workload có nguồn/hash và công cụ offline cho cả nhóm. Các bổ sung này không có nghĩa TV2 đã triển khai app/nghiệm thu cloud; ghi commit/hash gói thật khi nhận source.

Theo ghi nhận TV1 05/11, ba node v1.35.10 Ready, Pod IP/ClusterIP/DNS 200, Rancher ba node Active. Đây là bàn giao cũ trong repo; đợt local này không kiểm tra lại VM/cụm, bật/tắt, SSH hoặc apply policy.

## Đã chuẩn bị local

| Sản phẩm | Tình trạng / nơi nhận |
|---|---|
| App/nguồn/giấy phép | [Bookinfo README](../../apps/bookinfo/README.md), Istio 1.30.7, Apache-2.0 |
| Workload có provenance/hash | [source-lock](../../apps/bookinfo/source-lock.json), [upstream](../../apps/bookinfo/upstream/); không cần thư mục full release trên VM |
| Chuẩn bị workload | scripts/prepare-bookinfo.py xác minh source, sinh baseline injection disabled/workload/metadata; chưa apply |
| Config mesh/route/policy | [application.bookinfo.json](../../apps/bookinfo/application.bookinfo.json): /ratings/0 cùng luồng website, route tường minh |
| Baseline/mesh | [Runbook TV2](../tv2-runbook.md): baseline trước mesh theo TV1, sau đó injection/rollout/route/test riêng từng lớp |
| Công cụ/readiness | curl + getent, debug cùng Pod/SA có quyền, app/proxy Ready kiểu thường và native |
| Inventory/bàn giao | [Bảng Service](../../apps/bookinfo/service-inventory.md) tách thiết kế/tag nguồn khỏi UID/endpoint/imageID/kết quả runtime còn chờ |

Kết quả checker gần nhất do TV3 ghi tại [TV3-status](TV3-status.md). Unit test/mock/hash/render local không thay nghiệm thu app/cloud.

## Chưa nghiệm thu cloud

| Test / công việc | Trạng thái | Đầu vào để tiếp tục |
|---|---|---|
| Tiếp nhận wk-01 | TV1 đã bootstrap theo bàn giao; TV2 chưa SSH kiểm tra trực tiếp đợt này | Context/SSH thật; không prepare/join lại |
| Deploy baseline | Chưa chạy | Cụm/quyền Ready, output chuẩn bị xác minh; chưa cần Istio |
| Review baseline | Chưa chạy | Website có sao, hai nguồn DNS/HTTP 200, endpoint/source/hash; TV1 review |
| Injection/route/APP01 | Chưa chạy | TV3 mesh/gateway Ready sau baseline; app/proxy Ready; route/nội dung đúng |
| SVC01–SVC03 | Chưa chạy | Service/Pod/EndpointSlice thật, replica gốc, lệnh/log phục hồi |
| SEC01/SEC02 | Chưa chạy | Hai nguồn/công cụ/SA thật, baseline/quyền đọc policy; evidence mTLS/RBAC/rollback |
| NodePort → TV1 | Chưa chạy | Gateway/route đạt, thử hai worker trước LB |
| Runtime → TV3 | Chưa điền | UID/IP/SA/endpoint/imageID/context/request/kết quả và người chạy lại |

TV2 tiếp tục sở hữu workload/Service/route/luật Istio; TV3 nhận dữ liệu làm OBS01/NetworkPolicy/selector lab. Ca chưa chạy giữ Chưa chạy; thiếu quyền/đầu vào ghi Bị chặn và người xử lý, không tự điền số liệu để đóng bàn giao.
