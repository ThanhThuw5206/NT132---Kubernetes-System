# Bảng kê Service Bookinfo — TV2 điền bằng dữ liệu thật

Điền sau khi deploy trên cụm. Lấy số liệu bằng `kubectl -n bookinfo get svc,endpointslice,pods -o wide` và `kubectl -n bookinfo get <svc> -o yaml`. Không suy đoán; ghi đúng giá trị quan sát. Không đưa Secret/token vào file này.

| Service | Nguồn gọi | Kiểu | port | targetPort | selector | Endpoint Ready (Pod/UID) | Ghi chú |
|---|---|---|---|---|---|---|---|
| productpage | ingress gateway | ClusterIP | 9080 | 9080 | app=productpage | | entry_service |
| details | productpage | ClusterIP | 9080 | 9080 | app=details | | |
| reviews | productpage | ClusterIP | 9080 | 9080 | app=reviews | | v1/v3 scale về 0, giữ v2 |
| ratings | reviews-v2 | ClusterIP | 9080 | 9080 | app=ratings | | target_service |
| istio-ingressgateway (istio-system) | client/LB | NodePort | 80 | 80 | istio=ingressgateway | | nodePort 30080 |

## Deployment và ServiceAccount (dùng cho SVC02/SVC03 và ca bảo mật)

| Deployment | Replica gốc | ServiceAccount | Labels (app,version) |
|---|---|---|---|
| productpage-v1 | 1 | bookinfo-productpage | app=productpage, version=v1 |
| details-v1 | 1 | bookinfo-details | app=details, version=v1 |
| reviews-v2 | 1 | bookinfo-reviews | app=reviews, version=v2 |
| ratings-v1 | 1 | bookinfo-ratings | app=ratings, version=v1 |

## Image đã ghim (ghi tag/digest thực tế từ release 1.30.7)

| Workload | Image + tag quan sát | Digest (nếu có) |
|---|---|---|
| productpage | | |
| details | | |
| reviews-v2 | | |
| ratings | | |

## Luồng hợp lệ và nguồn đối chứng bị chặn (bàn giao TV3)

- Luồng hợp lệ: `reviews-v2` (SA `bookinfo-reviews`) → `GET http://ratings:9080/ratings/1` → HTTP 200, body JSON có `ratings`.
- Nguồn đối chứng: `productpage` (SA `bookinfo-productpage`) gọi thẳng `ratings:9080/ratings/1` — dùng để chứng minh AuthorizationPolicy/NetworkPolicy chặn đúng.
- Container chạy phép thử: exec vào container ứng dụng của Pod reviews-v2 / productpage (không exec vào `istio-proxy`). Nếu container không có `curl`, dùng `kubectl debug` ephemeral container cùng Pod để giữ danh tính.
