# TV3 · Phạm vi NetworkPolicy cho Service đích

Manifest thật được tạo bởi `python3 scripts/tv3.py render config/application.json` vào `.generated/tv3-*/network-policy.json`. Dùng thông số TV2 đã bàn giao; repo không chứa policy có tên ứng dụng đoán trước.

| Nguồn | Đích | Cổng | Ý định của luật |
|---|---|---|---|
| Pod khớp `allowed_caller_labels`, cùng namespace | Pod khớp `target_labels` | TCP `target_port` của Pod | Cho phép luồng nghiệp vụ |
| Pod khác nhãn hoặc namespace khác | Cùng target | Cổng ứng dụng | Không được luật này cho phép |
| Pod `app=prometheus` **và** namespace `istio-system` | Cùng target | TCP 15020, 15090 | Cho scrape khi `permit_prometheus_scrape=true` |
| Gateway trực tiếp tới target | Cùng target | Cổng ứng dụng | Không được mở riêng; target phải là dịch vụ nội bộ sau entry theo thiết kế hiện tại |

Luật chỉ giới hạn ingress tại target, không phải default-deny toàn namespace hoặc egress policy. DNS của nguồn không bị luật ingress này chủ động giới hạn. Cổng Pod (`target_port`) có thể khác cổng Service (`target_service_port`); không hoán đổi hai giá trị.

NetworkPolicy được cộng gộp: một policy khác có thể cho phép thêm traffic; cần kiểm tra cả ingress đích và egress nguồn trước khi quy kết kết quả. [Quy tắc NetworkPolicy của Kubernetes](https://kubernetes.io/docs/concepts/services-networking/network-policies/).

Policy mạng dựa vào nhãn Pod; AuthorizationPolicy dựa vào danh tính ServiceAccount và HTTP method/path. Muốn tạo nguồn đối chứng cho cả hai lớp, TV2 phải giao Pod có nhãn **và** ServiceAccount phù hợp với từng ca; đổi riêng ServiceAccount chưa tạo ra khác biệt cho NetworkPolicy.

Các bước apply riêng, đối chứng, gỡ riêng và phục hồi nằm tại [suite C1–C4](../../tests/security/README.md). Dùng trên namespace lab đã xác minh; nếu có luồng hợp lệ khác vào target, mở rộng ma trận trước khi áp luật.
