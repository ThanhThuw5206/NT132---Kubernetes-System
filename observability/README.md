# TV3 · Prometheus, Kiali và OBS01

Cần mạng nền đạt, Istiod/gateway Ready, workload có sidecar và route do TV2 bàn giao. Cài addon bằng `bash scripts/07-install-observability.sh` trên cp-01. TV1 hoặc TV3 mở port-forward và tunnel theo [runbook TV3](../docs/tv3-runbook.md).

## Tạo traffic có timestamp

Chạy trên laptop có Python hoặc cp-01 đang có port-forward gateway:

```bash
python3 scripts/tv3.py traffic http://127.0.0.1:8080/DUONG_DAN_THAT --duration 180 --interval 1 --timeout 10
```

Thay đường dẫn bằng request TV2 xác nhận tạo được luồng caller → target. Công cụ ngừng bắt đầu request mới sau thời lượng đã chọn, ghi từng HTTP status/lỗi và thời điểm theo UTC+07:00 vào `.generated/tv3-*/traffic.json`. `--timeout` là thời gian chờ khi socket không nhận dữ liệu; response gửi chậm liên tục có thể kéo dài hơn thời lượng + timeout. Có thể Ctrl+C để dừng, log vẫn được lưu và đánh dấu chưa hoàn tất. Không tự follow redirect hoặc lưu response body; đọc tối đa 1 MiB để kiểm tra body, đánh dấu lỗi nếu bị cắt, framing sai hoặc lớn hơn giới hạn. Từ chối URL có credential/query/fragment. Chọn API GET không có tác dụng sửa dữ liệu. Exit 0 chỉ khi vòng chạy hoàn tất, có request và tất cả trả 200/body hợp lệ; vẫn phải xem nội dung trang thật và metric để nghiệm thu OBS01.

Trong Kiali (`http://localhost:20001`): chọn namespace thật, cửa sổ 5 phút, graph workload/service. Ghi tên nguồn/đích, request rate, giờ bắt đầu/kết thúc và ảnh cạnh caller → target. Nhờ TV1 phát request mới rồi tự tìm lại cạnh. Không mặc định tên `reviews`/`ratings` nếu TV2 chọn app khác.

## Đối chiếu Prometheus

Trên cp-01, mở terminal riêng:

```bash
kubectl -n istio-system port-forward svc/prometheus 9090:9090 --address=127.0.0.1
```

Trong terminal cp-01 khác, đặt namespace thật; lưu JSON cùng khung giờ traffic:

```bash
export APP_NAMESPACE='TEN_NAMESPACE_THAT'
query="sum by (source_workload, destination_service_name) (rate(istio_requests_total{reporter=\"destination\",destination_service_namespace=\"$APP_NAMESPACE\"}[5m]))"
curl -fsS --get http://127.0.0.1:9090/api/v1/query --data-urlencode "query=$query"
```

Để đối chiếu mTLS, thêm `connection_security_policy="mutual_tls"` vào bộ lọc metric và kiểm tra source/destination đúng cặp thử; lưu thêm policy/proxy evidence khi nghiệm thu SEC01. Không dùng chỉ nhãn STRICT trong YAML để kết luận request đã dùng mTLS. Cần traffic trước khi truy vấn; graph trống chưa đủ kết luận mạng hỏng. [Hướng dẫn metric chính thức của Istio](https://istio.io/latest/docs/tasks/observability/metrics/querying-metrics/).

| Triệu chứng | Kiểm tra tiếp |
|---|---|
| Gateway 404 | Route/Gateway/path đã được TV2 apply chưa? |
| Trang 200 nhưng không có cạnh nội bộ | Request có gọi caller → target thật không, hay chỉ phục vụ trang tĩnh/cache? |
| Không có series | Sidecar Ready, Prometheus targets, labels và namespace thật |
| Có series nhưng graph trống | Kiali namespace/time window/refresh và khoảng thời gian traffic |
| Sau policy mất metrics | Ngoại lệ scrape có khớp Pod Prometheus thật và cổng metrics không? |

Dashboard chỉ truy cập qua port-forward/IAP trong thiết kế này. TV3 không cần mở firewall public cho Kiali hoặc Prometheus.
