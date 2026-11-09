# Bàn giao đưa dịch vụ ra Internet (NodePort → Cloud LB) · TV2 → TV1

Phiếu này TV2 bàn giao cho TV1 để cấu hình **external passthrough Network Load Balancer** (PUB01), cho máy ngoài VPC truy cập website Bookinfo. Cập nhật theo phiên mesh TV2 10/11/2026; xem [TV2-mesh](../docs/evidence/TV2-mesh-20261110.md).

## 1. Thông số gateway (TV2 cung cấp)

| Trường | Giá trị |
|---|---|
| Service gateway | `istio-ingressgateway` · namespace `istio-system` |
| Kiểu | **NodePort** |
| Cổng | `80 → nodePort 30080/TCP` (HTTP); status-port `15021` |
| ClusterIP (tham khảo) | `10.105.30.70` |
| Backend (2 worker) | `wk-01` = 10.20.0.11 · `wk-02` = 10.20.0.12 |
| Đường ứng dụng | `GET /productpage` (trang có điểm sao) |
| externalTrafficPolicy | `Cluster` (worker chuyển tới gateway Pod ở worker khác) |

## 2. Việc TV1 cần làm (theo plan §14 / deploy-cloud §11)

1. Tạo **unmanaged instance group** cùng zone, thêm 2 worker `wk-01`, `wk-02`.
2. Dành **regional external IP** (frontend).
3. Tạo **regional backend service** (EXTERNAL) + **TCP health check cổng 30080**, gắn instance group.
4. Tạo **forwarding rule TCP 30080** trỏ backend service tới frontend IP.
5. **Firewall:** cho dải health check của Google + IP client demo tới cổng 30080 trên tag worker.
6. Bật bằng Terraform: trong `infra/gcp/terraform.tfvars` đặt `enable_public_lb = true`, `web_source_ranges` = IP người xem (ví dụ `<ip>/32`); `terraform plan` → `apply`.

## 3. Nghiệm thu PUB01

- Cả hai backend **healthy**.
- Từ máy **ngoài VPC**: `curl -i http://<FRONTEND_IP>:30080/productpage` → HTTP 200, trang có điểm sao.
- Lưu IP frontend, cổng, thời điểm, ảnh trạng thái backend.

## 4. Trạng thái hiện tại

- ✅ NodePort 30080 đã xác minh trả **HTTP 200** `/productpage` trên **cả hai worker** (lượt kỹ thuật TV3; xem [TV3-status](../docs/evidence/TV3-status.md)).
- ⏳ **PUB01 chờ TV1** tạo cloud LB + firewall rồi test từ ngoài VPC.
- TV1 ghi tên từng resource (group, backend, health check, forwarding rule, firewall) và IP frontend vào mục 1–3 của file này khi hoàn thành.

Health check TCP 30080 chỉ xác nhận cổng gateway nhận kết nối, **không** chứng minh website hoạt động — phải test `/productpage` có sao riêng.
