# TV3 · NET01 và bài selector sai SVC04

NET01 có fixture `network-check.yaml` và script `scripts/test-cross-node.sh` chạy hai chiều; xem [runbook TV3](../../docs/tv3-runbook.md). Các kiểm tra mock local không phải NET01 trên cloud.

## TV3 kiểm tra chéo SVC02 / SVC03 cùng TV2

TV2 sở hữu thao tác tạo lại Pod và scale Deployment; tên Deployment lấy từ phiếu bàn giao, không suy ra từ Service. TV3 ghi bằng chứng trước/sau và gọi lại cùng DNS bằng nguồn hợp lệ:

```bash
python3 scripts/tv3.py service-snapshot config/application.json --context TEN_CONTEXT_LAB --output .generated/svc-before
# TV2 thực hiện đúng một ca restart hoặc scale, đợi workload Ready.
python3 scripts/tv3.py service-snapshot config/application.json --context TEN_CONTEXT_LAB --output .generated/svc-after
```

Chọn thư mục output mới cho mỗi lượt. Hai `service-snapshot.json` ghi UID/ClusterIP/selector/ports của Service, UID/IP/node/labels của các Pod được selector chọn và targetRef của EndpointSlice. Mỗi endpoint Ready phải khớp UID, tên, IP của Pod được chọn đang Ready; endpoint cũ trỏ sai UID bị báo chưa đạt. Snapshot không thu Pod environment hoặc Secret.

- **SVC02:** DNS/UID Service/ClusterIP giữ nguyên; Pod mới có UID mới, EndpointSlice trỏ Pod hiện tại và lời gọi qua cùng tên thành công. Không chỉ dựa vào việc Pod IP đổi vì IP có thể được tái sử dụng.
- **SVC03:** endpoint Ready phản ánh đủ tập Pod sau scale; TV2 trả replica về số ban đầu, TV3 chụp thêm lượt phục hồi và gọi lại cùng DNS. Không kết luận tải chia đều chỉ từ vài response giống nhau.

Exit 0 chỉ cho biết các quan hệ Service–Pod–EndpointSlice tại thời điểm chụp hợp lệ; vẫn cần DNS/HTTP và kiểm tra chéo. Exit 1 vẫn lưu snapshot trạng thái chưa đạt để chẩn đoán. Kết quả được ghi vào hồ sơ của TV2/nhóm, TV3 không tự nhận hoàn thành phần triển khai của TV2.

## SVC04: DNS có tên nhưng selector không chọn Pod

Cần app thật và nguồn gọi được phép do TV2 bàn giao. Trước bài thử, gọi Service gốc thành công bằng cùng nguồn/path để loại lỗi app/policy. Giữ policy không đổi xuyên suốt ca. Không đổi selector của Service gốc.

Render bằng `python3 scripts/tv3.py render config/application.json`, gán `GEN` đúng thư mục vừa in. Hai file `selector-broken.json` và `selector-fixed.json` mô tả **cùng một Service thử riêng**, tên có hash từ namespace/target. `port` lấy từ Service, `targetPort` lấy từ cổng Pod; không sao chép ClusterIP/UID của Service gốc.

Trên Bash Linux, đặt context và namespace thật, Pod/container nguồn đã có `curl`/`getent`, path API thật:

```bash
export LAB_CONTEXT='TEN_CONTEXT_LAB'
export GEN='DUONG_DAN_VUA_RENDER'
export SOURCE_POD='TEN_POD_NGUON_HOP_LE'
export SOURCE_CONTAINER='TEN_CONTAINER_CO_CURL_GETENT'
export TEST_PATH='/DUONG_API_GET_THAT'
export APP_NAMESPACE="$(python3 -c 'import json; print(json.load(open("config/application.json"))["namespace"])')"
export TARGET_SERVICE="$(python3 -c 'import json; print(json.load(open("config/application.json"))["target_service"])')"
export TEST_SERVICE="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["metadata"]["name"])' "$GEN/selector-broken.json")"
export LAB_SERVICE_PORT="$(python3 -c 'import json; print(json.load(open("config/application.json"))["target_service_port"])')"
K=(kubectl --context "$LAB_CONTEXT" --request-timeout=20s -n "$APP_NAMESPACE")
"${K[@]}" get svc "$TARGET_SERVICE" -o yaml
"${K[@]}" get svc "$TEST_SERVICE" --ignore-not-found -o yaml
"${K[@]}" get pods -l nt132.test/no-backend=tv3-selector-test
```

Service thử phải chưa tồn tại (hoặc được xác minh đúng bài của mình); selector sai phải chưa khớp Pod nào. Nếu có tài nguyên trùng, dừng để kiểm tra, không apply đè. Lưu UID/ClusterIP/selector Service gốc làm đối chiếu.

Tạo trạng thái lỗi, lưu YAML và EndpointSlice sau khi controller cập nhật:

```bash
"${K[@]}" apply -f "$GEN/selector-broken.json"
"${K[@]}" get svc "$TEST_SERVICE" -o yaml
"${K[@]}" get endpointslice -l "kubernetes.io/service-name=$TEST_SERVICE" -o yaml
"${K[@]}" exec "$SOURCE_POD" -c "$SOURCE_CONTAINER" -- getent hosts "$TEST_SERVICE.$APP_NAMESPACE.svc.cluster.local"
"${K[@]}" exec "$SOURCE_POD" -c "$SOURCE_CONTAINER" -- curl -sS --max-time 10 -o /dev/null -w '%{http_code}' \
  "http://$TEST_SERVICE.$APP_NAMESPACE.svc.cluster.local:$LAB_SERVICE_PORT$TEST_PATH"
```

Kỳ vọng DNS trả ClusterIP, chưa có endpoint Ready và HTTP chưa thành công. Curl ở lượt lỗi có thể trả exit khác 0; ghi stdout/stderr/exit code, không xem đó là suite đã đạt. Một EndpointSlice trống khác với việc không có object EndpointSlice; cả hai đều chưa có backend Ready.

Có thể thu thêm cấu trúc bằng `python3 scripts/tv3.py service-snapshot config/application.json --context "$LAB_CONTEXT" --service "$TEST_SERVICE"`. Trạng thái selector sai sẽ trả exit 1 và vẫn lưu JSON, vì chưa có endpoint Ready; đó là dữ liệu của ca lỗi có chủ đích. Sau khi TV1 sửa, chụp lại vào thư mục mới và đối chiếu UID/ClusterIP của **cùng Service thử**.

**Giao TV1 sửa:** gửi tên Service và triệu chứng; TV1 đối chiếu selector với Pod labels, sửa manifest Service thử. File `selector-fixed.json` là đáp án để kiểm tra sau bước chẩn đoán:

```bash
"${K[@]}" apply -f "$GEN/selector-fixed.json"
for attempt in {1..30}; do
  ready="$("${K[@]}" get endpointslice -l "kubernetes.io/service-name=$TEST_SERVICE" \
    -o 'jsonpath={range .items[*].endpoints[*]}{.conditions.ready}{"\n"}{end}')" || exit 1
  [[ "$ready" == *true* ]] && break
  sleep 2
done
[[ "$ready" == *true* ]] || { echo 'Chua co endpoint Ready'; exit 1; }
"${K[@]}" get svc "$TEST_SERVICE" -o yaml
"${K[@]}" get endpointslice -l "kubernetes.io/service-name=$TEST_SERVICE" -o yaml
"${K[@]}" exec "$SOURCE_POD" -c "$SOURCE_CONTAINER" -- getent hosts "$TEST_SERVICE.$APP_NAMESPACE.svc.cluster.local"
"${K[@]}" exec "$SOURCE_POD" -c "$SOURCE_CONTAINER" -- curl -sS --max-time 10 -o /dev/null -w '%{http_code}' \
  "http://$TEST_SERVICE.$APP_NAMESPACE.svc.cluster.local:$LAB_SERVICE_PORT$TEST_PATH"
```

TV2 gọi lại cùng URL bằng nguồn hợp lệ, cần HTTP 200. Nếu có Istio host-based route/policy hoặc app ràng buộc Host header, đối chiếu cùng TV2 trước khi kết luận selector đã được kiểm chứng; không đổi policy để che lỗi bài thử. Lưu Service UID/ClusterIP trước/sau (phải là cùng Service), endpoint/targetRef và hai kết quả gọi.

Sau khi lưu bằng chứng, xóa đúng Service thử bằng một file (hai file cùng tên resource):

```bash
"${K[@]}" delete -f "$GEN/selector-broken.json"
"${K[@]}" get svc "$TARGET_SERVICE" -o yaml
```

Gọi lại Service gốc, đối chiếu UID/ClusterIP/selector với lúc bắt đầu. SVC04 chỉ đạt khi TV1 sửa được và TV2 xác nhận lại; ghi vào [mẫu evidence](../../docs/evidence/templates/test-result.md).
