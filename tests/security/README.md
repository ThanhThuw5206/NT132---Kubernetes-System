# C1–C4 · Tách lỗi Istio và NetworkPolicy

Chạy trên namespace lab do nhóm quản lý, sau NET01 và app qua gateway đã đạt. TV2 xác nhận API GET, danh tính và labels; TV3 chủ trì C3, TV1 chạy lại. Source chuẩn bị chưa phải kết quả nghiệm thu cloud.

## Chuẩn bị

1. Điền `config/application.json` bằng dữ liệu thật. Cần hai Pod nguồn có sidecar Ready: nguồn hợp lệ khớp `allowed_caller_labels`/`allowed_service_account`, nguồn đối chứng có nhãn khác **và** ServiceAccount khác. Cả hai phải gọi target được trước khi hạn chế.
2. Container ứng dụng hoặc debug của mỗi Pod cần `curl` và `getent`. Nếu thiếu, nhờ TV2 chuẩn bị debug container theo quyền được cấp; không thay sang một Pod khác vì sẽ đổi danh tính/nhãn. Công cụ không exec vào `istio-proxy` để giả làm ứng dụng.

   Công cụ hỗ trợ cả proxy thông thường và native sidecar (`initContainers` với `restartPolicy: Always`, trạng thái tại `initContainerStatuses`). Không kết luận thiếu proxy chỉ từ danh sách `spec.containers`; Istio mặc định dùng native sidecar cho Pod đủ điều kiện từ 1.27. [Thay đổi chính thức của Istio](https://istio.io/latest/news/releases/1.27.x/announcing-1.27/change-notes/).
3. Kiểm tra policy đang có ở namespace ứng dụng và root namespace mesh (`istio-system` trong bộ cài này). Nếu có luật hạn chế/cho phép khác tác động tới hai nguồn/đích, thống nhất baseline trước. Không xóa policy không thuộc bài thử.
4. Render và ghi đường dẫn in ra. Mỗi lượt render là thư mục mới; dùng đúng thư mục đó xuyên suốt C1–C4.

Trên Bash Linux, tại repo (thay các giá trị `TEN_...` bằng thực tế):

```bash
export LAB_CONTEXT='TEN_CONTEXT_LAB'
export ALLOWED_POD='TEN_POD_HOP_LE'
export BLOCKED_POD='TEN_POD_DOI_CHUNG'
export ALLOWED_CONTAINER='TEN_CONTAINER_CO_CURL_GETENT'
export BLOCKED_CONTAINER='TEN_CONTAINER_CO_CURL_GETENT'
export TEST_PATH='/DUONG_API_GET_THAT'
export APP_NAMESPACE="$(python3 -c 'import json; print(json.load(open("config/application.json"))["namespace"])')"
export GEN="$(python3 scripts/tv3.py render config/application.json)"
export TV3_EVIDENCE_ROOT=".generated/security-$(date -u +%Y%m%dT%H%M%SZ)"
K=(kubectl --context "$LAB_CONTEXT" --request-timeout=20s -n "$APP_NAMESPACE")
"${K[@]}" get pods -o wide
"${K[@]}" get networkpolicies,authorizationpolicies,peerauthentications
kubectl --context "$LAB_CONTEXT" -n istio-system get authorizationpolicies,peerauthentications
```

`TEST_PATH` phải là một path cụ thể trong `allowed_http_paths`, không có wildcard. Probe chỉ gửi GET. Trước khi apply, kiểm tra các tên dành cho bài thử chưa tồn tại; nếu trùng, dừng để đối chiếu chủ sở hữu/cấu hình gốc, không ghi đè rồi xóa:

```bash
for resource in networkpolicy/target-ingress authorizationpolicy/target-from-caller peerauthentication/target-strict; do
  existing="$("${K[@]}" get "$resource" --ignore-not-found -o name)" || exit 1
  [[ -z "$existing" ]] || { echo "Da ton tai $resource; dung de kiem tra"; exit 1; }
done
```

Hàm ghi cặp kết quả; nếu một lệnh trả khác 0, dừng ca và kiểm tra log trước khi thay lớp tiếp:

```bash
probe_pair() {
  local phase="$1" expected_blocked="$2"
  python3 scripts/tv3.py probe config/application.json --context "$LAB_CONTEXT" \
    --pod "$ALLOWED_POD" --container "$ALLOWED_CONTAINER" --path "$TEST_PATH" --expect 200 --phase "$phase" \
    --output "$TV3_EVIDENCE_ROOT/$phase-allowed" || return
  python3 scripts/tv3.py probe config/application.json --context "$LAB_CONTEXT" \
    --pod "$BLOCKED_POD" --container "$BLOCKED_CONTAINER" --path "$TEST_PATH" --expect "$expected_blocked" --phase "$phase" \
    --output "$TV3_EVIDENCE_ROOT/$phase-control"
}
```

Mỗi `probe.json` có phase, context, namespace, Pod UID/IP/node/labels/ServiceAccount, DNS, response/exit code, policy ứng dụng/root namespace mesh và EndpointSlice target cùng thời điểm; kèm commit nền và hash script local. Root namespace mặc định là `istio-system`, đổi bằng `--mesh-root-namespace` nếu nhóm đổi thiết kế. Nếu không đọc được policy cần thiết, report ghi `evidence_errors` và không báo khớp kỳ vọng. Không thu Secret/env/kubeconfig. Các policy toàn cụm của CNI hoặc egress khác ngoài hai namespace vẫn cần đối chiếu với người quản trị khi có. `matched_expectation` chỉ là kết quả khớp phép thử, chưa tự đánh dấu SEC03 đạt.

## Kiểm soát kết nối cũ trước C0–C4

Proxy có thể tái sử dụng kết nối TCP đã được cho phép trước lúc thêm NetworkPolicy. Kubernetes để việc áp thay đổi lên kết nối đang tồn tại tùy implementation; một request mới không nhất thiết tạo kết nối upstream mới. Không kết luận CNI hỏng chỉ từ HTTP 200 trên kết nối cũ. [Quy định về kết nối đang tồn tại](https://kubernetes.io/docs/concepts/services-networking/network-policies/#networkpolicy-and-existing-connections).

Lượt Bookinfo ngày 06/11 đã gặp hiện tượng C3 vẫn 200; lượt giữ điều kiện kết nối mới cố định từ trước C0 tới sau C4 cho kết quả khác. Để chạy lại cùng điều kiện, đọc DestinationRule hiện có trước, chỉ dùng fixture sau với `bookinfo`/`ratings` đúng thiết kế. Đây là cấu hình **thử tạm**, không phải luật nghiệp vụ cần giữ trên cluster:

```bash
test "$APP_NAMESPACE" = bookinfo || exit 1
"${K[@]}" get destinationrules
export FRESH_RULE=tv3-test-fresh-ratings-connections
# create từ chối tên đã tồn tại; không dùng apply ghi đè luật của người khác.
export FRESH_UID="$("${K[@]}" create -f tests/security/fresh-connections.bookinfo.yaml -o jsonpath='{.metadata.uid}')"
test -n "$FRESH_UID" || exit 1
# Đợi proxy nhận cấu hình, rồi lấy baseline trước STRICT:
sleep 5
probe_pair C0 200
```

Fixture giới hạn mỗi kết nối một request và thời gian một giây; ghi manifest/UID vào evidence và chỉ tiếp tục khi C0 hai nguồn cùng 200. Giữ nguyên fixture xuyên suốt các ca và phục hồi; vẫn cần lưu DNS/endpoint/log, không đổi matcher thành HTTP 503 để tự nhận đạt. Xóa fixture ở cuối quy trình bên dưới, sau các ca C1–C4.

## C1 · Đối chứng STRICT

```bash
"${K[@]}" apply -f "$GEN/mtls.json"
probe_pair C1 200
```

Hai nguồn nhận 200, DNS phân giải và target có endpoint Ready. Lưu bằng chứng mTLS từ proxy/metric cùng cặp nguồn-đích, xem [OBS01](../../observability/README.md). Nếu policy vừa apply chưa được proxy nhận, kiểm tra config/log và thử lại với thư mục evidence mới; không bỏ qua lượt lỗi. Chỉ tiếp tục sau khi baseline đạt.

## C2 · Chỉ AuthorizationPolicy hạn chế

```bash
"${K[@]}" apply -f "$GEN/authorization.json"
probe_pair C2 403
```

Nguồn hợp lệ 200, nguồn đối chứng 403. TV2 kiểm tra principal/method/path đúng; lưu log `istio-proxy` ở Pod target, có dấu vết RBAC từ chối tương ứng request. HTTP status riêng lẻ chưa đủ quy kết.

Gỡ đúng luật vừa tạo và xác nhận phục hồi trước C3:

```bash
"${K[@]}" delete -f "$GEN/authorization.json"
probe_pair C2-recovered 200
```

## C3 / SEC03 · Chỉ NetworkPolicy hạn chế

```bash
"${K[@]}" apply -f "$GEN/network-policy.json"
probe_pair C3 network-block
```

Nguồn hợp lệ 200; nguồn sai vẫn phân giải DNS nhưng không kết nối được, target vẫn có endpoint Ready. Probe chỉ nhận curl exit 7/28 với HTTP `000` là triệu chứng kết nối bị chặn; exit 6 (DNS), 124 (hết hạn kubectl), 126/127 (thiếu công cụ) không được chấp nhận. Nếu proxy nguồn trả 503 thay vì lỗi TCP trực tiếp, công cụ để kết quả chưa khớp; cần đối chiếu upstream failure/log tại proxy và trạng thái CNI, không đổi kỳ vọng thành 503 rồi kết luận policy đạt.

**Nhánh upstream error qua proxy:** kế hoạch cho phép ghi lỗi upstream từ proxy nguồn ở C3. Khi thấy 503/504, report đặt `upstream_error_observed=true`, giữ `matched_expectation=false` và exit 1 để yêu cầu xem xét. Dừng apply lớp mới; lưu log `istio-proxy` của đúng Pod nguồn trong cùng khoảng thời gian, URL và đích; đối chiếu cờ lỗi upstream (ví dụ `UF`), endpoint vẫn Ready, nguồn hợp lệ vẫn 200, DNS thành công, không có AuthorizationPolicy hạn chế, rồi thực hiện lượt gỡ NetworkPolicy/phục hồi bên dưới. `UF` cũng có thể liên quan lỗi mTLS, nên một log/cờ riêng lẻ chưa chứng minh nguyên nhân. [Chẩn đoán traffic của Istio](https://istio.io/latest/docs/ops/common-problems/network-issues/). Nếu baseline → lỗi khi chỉ bật luật mạng → phục hồi đều được TV1 tái hiện và bằng chứng đầy đủ, ghi kết luận SEC03 qua kiểm tra thủ công vào mẫu evidence; không sửa JSON nguồn để giả thành matcher đã tự đạt.

Gỡ đúng NetworkPolicy và lặp đối chứng:

```bash
"${K[@]}" delete -f "$GEN/network-policy.json"
probe_pair C3-recovered 200
```

TV1 phải chạy lại được trước khi đánh dấu SEC03 đạt. Dùng kết quả baseline, luật duy nhất thay đổi và phục hồi để phân biệt chặn mạng với sự cố routing khác.

## C4 / SEC04 · Cả hai lớp

```bash
"${K[@]}" apply -f "$GEN/authorization.json"
"${K[@]}" apply -f "$GEN/network-policy.json"
probe_pair C4 network-block
```

Website qua entry vẫn phải phục vụ đúng; nguồn hợp lệ vào target, nguồn sai bị chặn. Lưu cả policy đang bật, metric và request website. Chỉ test URL public khi TV1 đã bàn giao LB; port-forward chỉ nghiệm thu đường qua tunnel.

Trả lại baseline STRICT sau buổi thử:

```bash
"${K[@]}" delete -f "$GEN/network-policy.json" --ignore-not-found
"${K[@]}" delete -f "$GEN/authorization.json" --ignore-not-found
probe_pair final-recovered 200
```

Giữ STRICT nếu đó là trạng thái nhóm đã thống nhất. Nếu STRICT cũng chỉ được tạo cho buổi thử và cần trả về trạng thái trước C1, gỡ riêng `mtls.json` sau khi lưu evidence/phục hồi. Không xóa namespace, không xóa toàn bộ policy bằng `--all`. Nếu một ca dừng giữa chừng, kiểm tra luật đang tồn tại rồi dùng đúng lệnh hoàn tác ở trên.

Nếu đã tạo fixture kết nối mới từ đầu, sau khi các policy thử đã gỡ và cả hai nguồn phục hồi, đối chiếu UID rồi xóa riêng fixture:

```bash
test -n "${FRESH_UID:-}" || exit 1
test "$("${K[@]}" get destinationrule "$FRESH_RULE" -o jsonpath='{.metadata.uid}')" = "$FRESH_UID" || exit 1
"${K[@]}" delete destinationrule "$FRESH_RULE"
probe_pair final-without-connection-fixture 200
```
