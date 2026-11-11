# Trạng thái phần ứng dụng TV2 · đối chiếu 07/11/2026

TV2 chọn Bookinfo và giao tài liệu/config tại `4377766` (từ TV3 `89f106d`). TV3 bổ sung workload có nguồn/hash và công cụ offline tại `2782c61`; TV2 dùng source này cho phiên baseline rồi ghi nhật ký/kết quả lên GitHub tại `8260fc9`. Ghi commit/hash gói thật khi nhận source; công cụ offline và kết quả cloud là hai loại bằng chứng riêng.

Theo ghi nhận TV1 05/11, ba node v1.35.10 Ready, Pod IP/ClusterIP/DNS 200, Rancher ba node Active.

**Phiên cloud 06/11/2026 (chiều):** TV2 đã SSH vào cp-01 (IAP tunnel + OpenSSH, dùng `sudo kubectl --kubeconfig=/etc/kubernetes/admin.conf`), **deploy Bookinfo baseline** và ghi kết quả kỹ thuật đạt cho **APP01(baseline)/SVC01/SVC02/SVC03**, rồi tắt VM. Nhật ký và số liệu: [TV2-baseline-20261106.md](TV2-baseline-20261106.md). Đây là phiên **TV2 tự chạy**, chưa phải biên bản kiểm tra chéo có người khác ký nhận.

**Sau phiên TV3 tối 06/11–đầu 07/11:** Istio/gateway và Prometheus/Kiali đã được cài, Bookinfo đã có proxy/route; TV3 có kết quả kỹ thuật NodePort hai worker, C0–C4/C1b, SVC01–04 và phục hồi tại [TV3-status](TV3-status.md). SVC02/SVC03 của TV3 là một lượt kỹ thuật sau đó, với Pod/UID khác; không ghi thay thành TV2 đã chạy mesh hoặc đã có nghiệm thu chéo chính thức. Cả ba VM được xác nhận TERMINATED lúc 00:06:38 ngày 07/11. Khi mở lab, giữ trạng thái đã tích hợp, không apply lại namespace baseline injection disabled.

**Phiên mesh TV2 09–10/11/2026:** TV2 tự bật cụm (có quyền start/stop), vào cụm đã tích hợp (pod 2/2, gateway/route sẵn, không policy), và tự chạy **APP01 qua gateway + C1 + SEC01 (STRICT) + SEC02 (200/403, có log RBAC) + phục hồi**, rồi gỡ luật về baseline và tắt VM. Nhật ký/số liệu: [TV2-mesh-20261110.md](TV2-mesh-20261110.md). Đây là lượt mesh mang tên TV2; vẫn chờ TV1/TV3 kiểm tra chéo để ký nhận.

## Đã chuẩn bị local

| Sản phẩm | Tình trạng / nơi nhận |
|---|---|
| App/nguồn/giấy phép | [Bookinfo README](../../apps/bookinfo/README.md), Istio 1.30.7, Apache-2.0 |
| Workload có provenance/hash | [source-lock](../../apps/bookinfo/source-lock.json), [upstream](../../apps/bookinfo/upstream/); không cần thư mục full release trên VM |
| Chuẩn bị workload | scripts/prepare-bookinfo.py xác minh source, sinh baseline injection disabled/workload/metadata; TV2 đã deploy baseline trong phiên 06/11 |
| Config mesh/route/policy | [application.bookinfo.json](../../apps/bookinfo/application.bookinfo.json): /ratings/0 cùng luồng website, route tường minh |
| Baseline/mesh | [Runbook TV2](../tv2-runbook.md): baseline trước mesh theo TV1, sau đó injection/rollout/route/test riêng từng lớp |
| Công cụ/readiness | curl + getent, debug cùng Pod/SA có quyền, app/proxy Ready kiểu thường và native |
| Inventory/bàn giao | [Bảng Service](../../apps/bookinfo/service-inventory.md) giữ baseline TV2 và số đo sau mesh/cuối phiên TV3; dùng đúng thời điểm, không coi Pod UID lịch sử là hiện hành |

Kết quả checker gần nhất do TV3 ghi tại [TV3-status](TV3-status.md). Unit test/mock/hash/render local không thay nghiệm thu app/cloud.

## Tiến độ cloud

| Test / công việc | Trạng thái | Ghi chú / đầu vào tiếp theo |
|---|---|---|
| Tiếp nhận cụm | ✅ 06/11 | SSH cp-01 OK; 3 node Ready (Calico hội tụ sau boot); không prepare/join lại |
| Deploy baseline | ✅ TV2 06/11 | Lúc baseline: namespace `bookinfo` injection disabled, 4 app 1/1 Running; image :1.20.3. Sau đó TV3 đã bật injection |
| APP01 baseline (website có sao) | ✅ 06/11 | port-forward productpage → HTTP 200, 9 sao, không "unavailable" |
| SVC01 | ✅ TV2 (chờ TV1 chạy lại) | selector/port/EndpointSlice khớp Pod ratings |
| SVC02 | Kỹ thuật TV2 và lượt TV3 sau đó đã có kết quả | TV2: UID 13fff955→6004ecf3, ClusterIP giữ, web vẫn sao; lượt TV3 và rollback ghi riêng. Chờ ký nhận kiểm tra chéo |
| SVC03 | Kỹ thuật TV2 và lượt TV3 sau đó đã có kết quả | TV2: scale 1→2→1, 2 endpoint ở 2 worker; TV3 đã đối chiếu đủ tập UID endpoint/Pod trong lượt riêng. Chờ ký nhận kiểm tra chéo |
| Injection/route/APP01 qua gateway | ✅ TV2 10/11 | port-forward istio-ingressgateway → HTTP 200, 9 sao; nhật ký [TV2-mesh-20261110](TV2-mesh-20261110.md) |
| SEC01/SEC02 | ✅ TV2 10/11 (chờ kiểm tra chéo) | C1 2 nguồn 200; SEC01 STRICT 200/200; SEC02 reviews 200 / productpage 403 + log RBAC; gỡ luật phục hồi baseline |
| NodePort → TV1 | TV3 đã thử hai worker | Cả hai URL nội bộ port 30080 trả HTTP 200; PUB01 vẫn chờ TV1 bàn giao LB/health/firewall |
| Phiếu app → TV3 | Dữ liệu thực đã có, còn xác nhận bàn giao | Đối chiếu [inventory](../../apps/bookinfo/service-inventory.md) và [application-handover](../application-handover.md); OBS01/SEC03/SVC04 đã có lượt TV3 |

TV2 tiếp tục sở hữu workload/Service/route/luật Istio; TV3 nhận dữ liệu làm OBS01/NetworkPolicy/selector lab. Ca chưa chạy giữ Chưa chạy; thiếu quyền/đầu vào ghi Bị chặn và người xử lý, không tự điền số liệu để đóng bàn giao.
