# Trạng thái phần ứng dụng TV2 · cập nhật local 06/11/2026

TV2 chọn Bookinfo và giao tài liệu/config tại `4377766` (từ TV3 `89f106d`). Đợt tích hợp sau đó trên laptop TV3 sửa config/hướng dẫn, thêm workload có nguồn/hash và công cụ offline cho cả nhóm. Các bổ sung này không có nghĩa TV2 đã triển khai app/nghiệm thu cloud; ghi commit/hash gói thật khi nhận source.

Theo ghi nhận TV1 05/11, ba node v1.35.10 Ready, Pod IP/ClusterIP/DNS 200, Rancher ba node Active.

**Phiên cloud 06/11/2026 (chiều):** TV2 đã SSH vào cp-01 (IAP tunnel + OpenSSH, dùng `sudo kubectl --kubeconfig=/etc/kubernetes/admin.conf`), **deploy Bookinfo baseline** và chạy **APP01(baseline)/SVC01/SVC02/SVC03 — tất cả đạt**, rồi tắt VM. Nhật ký và số liệu đầy đủ: [TV2-baseline-20261106.md](TV2-baseline-20261106.md). Các kết quả này do **TV2 chạy một mình, chờ TV1/TV3 kiểm tra chéo** mới chốt nghiệm thu. Phần cần Istio (injection/route/SEC) vẫn chờ TV3.

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

## Tiến độ cloud

| Test / công việc | Trạng thái | Ghi chú / đầu vào tiếp theo |
|---|---|---|
| Tiếp nhận cụm | ✅ 06/11 | SSH cp-01 OK; 3 node Ready (Calico hội tụ sau boot); không prepare/join lại |
| Deploy baseline | ✅ 06/11 | namespace `bookinfo` injection disabled, 4 app 1/1 Running; image :1.20.3 |
| APP01 baseline (website có sao) | ✅ 06/11 | port-forward productpage → HTTP 200, 9 sao, không "unavailable" |
| SVC01 | ✅ TV2 (chờ TV1 chạy lại) | selector/port/EndpointSlice khớp Pod ratings |
| SVC02 | ✅ TV2 (chờ TV3 chạy lại) | thay Pod: UID 13fff955→6004ecf3, ClusterIP giữ, web vẫn sao |
| SVC03 | ✅ TV2 (chờ TV3 chạy lại) | scale 1→2→1: 2 replica = 2 endpoint (2 worker) |
| Injection/route/APP01 qua gateway | ⏳ Chưa chạy | **Chờ TV3 cài Istio**; rồi bật injection/rollout/route |
| SEC01/SEC02 | ⏳ Chưa chạy | Cần Istio; hai nguồn/SA thật, evidence mTLS/RBAC/rollback |
| NodePort → TV1 | ⏳ Chưa chạy | Cần gateway; thử 30080 hai worker trước LB |
| Phiếu app → TV3 | ⏳ Chưa điền | Điền [application-handover](../application-handover.md) cho OBS01/SEC03/SVC04 |

TV2 tiếp tục sở hữu workload/Service/route/luật Istio; TV3 nhận dữ liệu làm OBS01/NetworkPolicy/selector lab. Ca chưa chạy giữ Chưa chạy; thiếu quyền/đầu vào ghi Bị chặn và người xử lý, không tự điền số liệu để đóng bàn giao.
