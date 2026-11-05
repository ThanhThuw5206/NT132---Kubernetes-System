# Trạng thái công việc TV2 · 05/11/2026

Phạm vi phiên này: **chọn ứng dụng mẫu, chuẩn bị manifest và runbook trên laptop**. Source nền `tv3/istio-network` (`89f106d`); branch làm việc `tv2/kubernetes-service`. Ghi commit thực tế bằng `git rev-parse HEAD` khi lấy mã. Chưa deploy app, chưa áp policy trên cụm cloud trong phiên này.

**Cập nhật nhận từ nhóm:** ngày 05/11/2026 ba node v1.35.10 Ready, Pod IP/ClusterIP/DNS trả 200, Rancher thấy ba node Active; Istio/Kiali/app/policy **chưa** triển khai. Đây là trạng thái bàn giao trong repo, không phải nghiệm thu cloud mới của TV2.

## Đã chuẩn bị

| Sản phẩm | File |
|---|---|
| Ứng dụng đã chọn + nguồn/giấy phép | [apps/bookinfo/README.md](../../apps/bookinfo/README.md) — Bookinfo, release Istio 1.30.7, Apache-2.0 |
| Config tích hợp tham chiếu | [apps/bookinfo/application.bookinfo.json](../../apps/bookinfo/application.bookinfo.json) — copy sang `config/application.json` khi deploy |
| Bảng kê Service (điền khi deploy) | [apps/bookinfo/service-inventory.md](../../apps/bookinfo/service-inventory.md) |
| Runbook thao tác từng bước | [docs/tv2-runbook.md](../tv2-runbook.md) |

## Chưa nghiệm thu cloud

| Test / công việc | Trạng thái | Đầu vào để chạy tiếp |
|---|---|---|
| wk-01 join | TV1 đã bootstrap theo bàn giao; TV2 chưa SSH kiểm tra trực tiếp | Context/phiên SSH thật; không prepare/join lại |
| Deploy Bookinfo | Chưa chạy | TV3 báo Istiod/gateway Ready; thư mục release 1.30.7 trên cp-01 |
| APP01 (/productpage có sao) | Chưa chạy | App có sidecar 2/2, route đã apply |
| SVC01 | Chưa chạy | Service ratings có endpoint Ready |
| SVC02 / SVC03 | Chưa chạy | App đã deploy; TV3 chụp chéo snapshot |
| SEC01 / SEC02 | Chưa chạy | Hai nguồn thật, ServiceAccount/API, baseline STRICT |
| NodePort → TV1 | Chưa chạy | Gateway route đạt; thử 30080 hai worker trước khi TV1 nối LB |
| Phiếu bàn giao TV3 | Chưa điền | Giá trị thật sau deploy |

Ứng dụng và project cloud không tự chọn thay TV1/TV3. Khi nhận đầu vào, chạy theo [runbook TV2](../tv2-runbook.md), lưu log thật và nhờ thành viên khác tái hiện trước khi đổi trạng thái sang Đạt. Không đưa Secret/token/kubeconfig vào bằng chứng.
