# NT132 · Kế hoạch tổng thể xây dựng và quản trị Kubernetes trên ba VM Google Cloud

**Thông số ứng dụng do TV2 quyết định.** Xem [phiếu bàn giao](./application-handover.md). APP_NAMESPACE, ENTRY_SERVICE, CALLER_SERVICE, TARGET_SERVICE, SERVICE_PORT và các token viết hoa trong ví dụ cần thay bằng giá trị thực trước khi chạy. Với đường dẫn, /APP_PATH và /TEST_PATH là ký hiệu cả path, thay bằng đường dẫn thật có một dấu / đầu. Các dòng mô tả chức năng của ứng dụng là tiêu chí kiểm thử cần đối chiếu với lựa chọn của TV2.

**Đề tài:** Khảo sát Kubernetes Service trên cụm tự dựng gồm ba VM Compute Engine. Nhóm dùng ứng dụng do TV2 tự chọn để kiểm chứng DNS, ClusterIP, selector, EndpointSlice, NodePort và đường vào từ cloud load balancer. Rancher phục vụ quản trị cụm; Istio và Calico giúp kiểm tra quyền truy cập tới cùng một Service. **Nhóm:** ba thành viên. **Lịch dự kiến:** 02–27/11/2026.

## 1. Phạm vi và quyết định thiết kế

**Cách dùng tài liệu.** Mục 1–3 xác định kiến trúc và người chịu trách nhiệm. Mục 4–8 là lịch và tiêu chí bàn giao. Từ mục 10 trở đi là hướng dẫn thao tác theo thứ tự. Trong các khối lệnh, sh là shell Linux trên VM hoặc máy quản trị Linux; powershell là laptop Windows. Các giá trị dạng <...> phải được thay bằng kết quả khảo sát của nhóm. Đọc hết một bước trước khi chạy. Mỗi lần thay đổi mạng hoặc policy, lưu cấu hình trước và sau để xác định chính xác nguyên nhân nếu demo hỏng.


| Nội dung trong các bản kế hoạch | Quyết định áp dụng cho đồ án |
|---|---|
| Cụm Kubernetes, quản trị node và mạng Pod | Nhóm thuê ba VM Linux, tự cài containerd, kubeadm, kubelet, CNI và vận hành control plane. Google Cloud cung cấp VM, VPC, firewall, IP và bộ cân bằng tải. Laptop giữ công cụ điều khiển. |
| Ứng dụng mẫu | TV2 tự chọn ứng dụng, ghim nguồn/image và chuẩn bị manifest triển khai. Website tạo traffic cho bài lab. Sản phẩm nhóm tự thiết kế là cấu hình Service, mạng, quyền truy cập và bộ kiểm thử. |
| Dashboard sau năm ngày | Headlamp hiển thị cấu trúc cụm và Kiali hiển thị lưu lượng. Plan gốc xếp Rancher vào P0: giữ nghiệm thu Rancher ở tuần 2. Nếu thầy yêu cầu xem Rancher ngay tuần đầu, chuyển việc cài Rancher lên ngày 3 thay Headlamp và dành ngày 4 để kiểm thử đăng nhập. |
| Chức năng kết thúc học phần | Tìm Service qua DNS, nối selector với Pod, quan sát EndpointSlice khi thay Pod hoặc đổi số replica, truy vết đường public qua NodePort, phân biệt lỗi endpoint với lỗi quyền và bàn giao kết quả tái hiện. |
| Mô hình local và GKE cũ | Giữ cách phân quyền, cách tổ chức manifest, kiểm thử và demo từ các bản cũ. Chỉ triển khai một cụm trên Compute Engine. Mọi bước tạo node pool, bật GKE Dataplane V2 và cấp LB tự động của GKE được thay bằng công việc tự cấu hình bên dưới. |

## 2. Kiến trúc vật lý và cấu trúc tài nguyên

| Thành phần | Cấu hình khởi điểm | Trách nhiệm |
|---|---|---|
| Laptop mỗi thành viên | Khoảng 5 GB cho công cụ và repo | SSH, gcloud, Git, kubectl; máy điều phối có Helm và istioctl. Dùng kubeconfig cá nhân qua đường quản trị riêng. |
| cp-01 | 2 vCPU, 4 GiB RAM, disk 20 GB | API server, etcd, scheduler, controller. Giữ taint control plane. Một control plane phù hợp lab và là điểm lỗi đơn. |
| wk-01, wk-02 | Mỗi VM 2 vCPU, 8 GiB RAM, disk 30 GB | Chạy workload, proxy, gateway, công cụ quản trị và quan sát. Kiểm tra requests, Pod Pending và bộ nhớ thực trước khi thêm Rancher. |
| Mạng Google Cloud | Cùng VPC, subnet, zone; ổ khởi động tổng 80 GB | Node dùng IP riêng ổn định. Chọn dải Pod và Service khác dải VPC. Dùng SSH giới hạn nguồn hoặc qua IAP. Chốt đường ra tải gói/image, firewall liên node và các cổng của chế độ Calico đã chọn. |
| Dữ liệu | Git lưu manifest và kết quả thử, disk VM lưu trạng thái cụm | TV2 bàn giao nhu cầu dữ liệu của ứng dụng đã chọn. Bàn giao cấu hình đã ghim và bản sao trạng thái cụm. |

**Ba đường kết nối cần thể hiện trên sơ đồ bàn giao**

```text
Quản trị: laptop → đường quản trị riêng → Kubernetes API trên cp-01
Ngày 5:  trình duyệt → port-forward của ingress gateway → ứng dụng do TV2 lựa chọn
Tuần 2:  Internet → IP công khai của cloud LB → NodePort 30080 của worker
                  → Pod ingress gateway → ENTRY_SERVICE → luồng nội bộ do TV2 bàn giao
Quan sát: proxy phát metrics → Prometheus thu thập → Kiali hiển thị graph
```

| Namespace | Tài nguyên cần có | Chức năng |
|---|---|---|
| kube-system và namespace do bộ cài CNI tạo | CoreDNS, thành phần mạng cụm, Calico | Phân giải tên Service, kết nối Pod xuyên node, thực thi NetworkPolicy. |
| istio-system | Istiod, ingress gateway, Prometheus, Kiali | Phân phối cấu hình proxy, tiếp nhận request, thu thập và hiển thị dữ liệu. Dashboard dùng đường quản trị riêng. |
| APP_NAMESPACE | Deployment, Pod, ServiceAccount riêng cho từng ứng dụng, Service ClusterIP, Istio Gateway/VirtualService, policy | Selector nối Service với Pod. EndpointSlice ghi địa chỉ backend. Proxy ở workload thực thi luật truy cập. |
| headlamp / cattle-system | Dashboard tuần đầu / Rancher quản trị cụm | Quyền trình chiếu chỉ đọc. Cài Rancher với hostname, TLS, ingress nội bộ và chuỗi tin cậy phù hợp. Kiểm tra Rancher nhìn thấy đúng cụm và workload. |

## 3. Phân chia công việc cho ba thành viên

Nhóm cùng trả lời một câu hỏi: **khi một request gọi tên Service `TARGET_SERVICE`, làm thế nào để biết request có đến đúng Pod và có được phép truy cập hay không?** TV1 dựng đường kết nối để request vào được cụm. TV2 chịu trách nhiệm cấu hình Service và chứng minh Kubernetes chọn đúng Pod. TV3 kiểm tra kết nối giữa các Pod, quan sát lưu lượng và giải thích nguyên nhân khi một request bị chặn. Ứng dụng do TV2 lựa chọn được triển khai để cả ba người dùng chung một tình huống kiểm thử.

### 3.1. Thành viên 1 · Dựng cụm trên Google Cloud và đưa dịch vụ ra ngoài

**Vai trò.** TV1 quản lý VM `cp-01`, nơi chạy control plane. Bạn này chịu trách nhiệm về mạng giữa ba VM, đường quản trị từ laptop, dashboard quản trị cụm và đường truy cập từ Internet. TV2 và TV3 tự cài worker của mình; TV1 cung cấp thông tin để hai worker gia nhập cùng một cụm.

| Thời gian | TV1 làm gì, theo thứ tự nào? | Khi nào xong và bàn giao cho ai? |
|---|---|---|
| Tuần 1 · 02–06/11 | Ngày 1, kiểm tra quota, lập bảng IP, tạo VPC/subnet/firewall và VM `cp-01`. Gửi tên mạng, zone và IP đã dành cho từng worker. Ngày 2, khởi tạo Kubernetes và cấp lệnh join cho từng bạn qua kênh riêng. Ngày 3–4, cài dashboard quản trị theo mục 4, tạo tài khoản trình chiếu chỉ đọc và thử mở từ laptop báo cáo. | TV2 và TV3 SSH được vào máy mình, join được cụm. Sau khi TV3 cài mạng Pod, TV1 đối chiếu đủ ba node Ready. TV2 đăng nhập dashboard bằng tài khoản được cấp và chỉ ra worker đang chứa Pod `TARGET_SERVICE`. |
| Tuần 2 · 09–13/11 | Nhận từ TV2 tên Service của ingress gateway và NodePort đã thử. Tạo nhóm backend gồm hai worker, health check, forwarding rule và firewall cho cloud load balancer. Hoàn thiện Rancher, hostname/TLS và quyền xem nếu tuần đầu nhóm dùng Headlamp. | Bàn giao cho TV3 IP frontend, cổng, URL và danh sách backend. TV3 mở trang trả nội dung đúng theo bàn giao từ mạng ngoài VPC. TV2 đối chiếu URL đó với NodePort trong manifest. |
| Tuần 3 · 16–20/11 | Là người chạy đối chứng độc lập. Trước và sau mỗi lần TV2 hoặc TV3 đổi policy, gọi từ cùng hai Pod tới cùng URL, ghi policy đang bật và kết quả. Cuối tuần bật cả hai lớp, kiểm tra lại website qua IP public. | Có bảng so sánh lời gọi được phép, lời gọi bị chặn và kết quả sau khi gỡ luật. TV1 giải thích được vì sao endpoint còn tồn tại dù một nguồn không được truy cập. |
| Tuần 4 · 23–27/11 | Tự chạy lại ca selector sai do TV3 chuẩn bị. Kiểm tra đường public, sơ đồ IP/cổng, backup cấu hình và chi phí. Sau bảo vệ, đối chiếu inventory rồi thu hồi tài nguyên của lab. | Bàn giao sơ đồ từ Internet đến gateway, ảnh health check, hướng dẫn quản trị và danh sách tài nguyên đã giữ hoặc xóa. |

#### Phiếu thao tác của TV1

**TV1.1 · Ngày 1, tạo môi trường mà hai worker sẽ sử dụng.** Trên Cloud Console, chọn project, region và zone của nhóm. Ghi tên VPC, subnet, CIDR của node, CIDR Pod/Service đã thống nhất với TV3 và ba IP nội bộ được dành cho từng VM. Tạo `cp-01`, gắn đúng subnet, cấu hình đường SSH quản trị và đường ra tải image. Gửi TV2/TV3 tên subnet, zone và IP dành cho từng worker trước khi họ tạo VM. Lưu bảng ba dòng vào `infra/inventory.md` với các cột tên VM, IP riêng, zone, người quản trị, trạng thái SSH. **Đạt khi** hai bạn đăng nhập được vào đúng worker và xác nhận IP khớp bảng.

**TV1.2 · Ngày 2, biến cp-01 thành control plane.** SSH vào cp-01, kiểm tra containerd, kubelet, forwarding và hostname theo mục 11. Chạy kubeadm init với IP advertise của cp-01 và CIDR đã duyệt. Kiểm tra API bằng `kubectl get nodes -o wide`. Gửi lệnh join chứa token và CA hash qua kênh riêng; chỉ lưu cú pháp đã che token vào `cluster/bootstrap.md`. Chờ TV2/TV3 join và TV3 hoàn tất Calico, rồi ghép từng dòng node với từng dòng inventory. **Nếu một worker không xuất hiện**, kiểm tra trước xem worker đến được TCP 6443 trên cp-01; nếu worker đã xuất hiện nhưng NotReady, chuyển trạng thái và events cho TV3 kiểm tra CNI.

**TV1.3 · Ngày 3–5, chuẩn bị dashboard có thể mở ngay tại phòng học.** Trên laptop báo cáo, chọn kube-context của lab và thử kết nối qua tunnel. Cài dashboard đã chốt ở mục 4. Với Headlamp, tạo danh tính chỉ đọc theo mục 21 và chạy hai phép thử quyền đọc node/sửa Deployment. Sau khi TV2 đưa ứng dụng do TV2 lựa chọn lên, mở Pod thuộc Service TARGET_SERVICE, đọc trường Node và đối chiếu với danh sách VM. Ngày 4 nhờ TV2 đăng nhập lại từ laptop khác. Ngày 5 bàn giao ảnh cùng thời điểm và cách mở dashboard trong `docs/evidence/M1/INF01-IAM01.md`. **Đạt khi** người xem đọc được nodes/workload, thao tác sửa không được cấp phép và biết TARGET_SERVICE đang ở worker nào.

**TV1.4 · Tuần 2, nối IP bên ngoài vào đúng Service.** Chỉ bắt đầu cấu hình backend sau khi TV2 giao kết quả gọi port 30080 trên *cả hai* worker. Trong Compute Engine, tạo instance group chứa hai worker hiện có; trong phần load balancing, gắn group vào regional backend service, cấu hình TCP health check 30080 rồi tạo forwarding rule trên IP frontend đã dành. Ghi tên từng resource và rule firewall vào `infra/public-access.md`. TV1 đọc trạng thái từng backend; TV3 dùng mạng ngoài VPC mở URL do TV1 cung cấp. Nếu probe unhealthy nhưng NodePort hoạt động, TV1 kiểm tra nguồn probe, target tag và cổng health check trước. **Đạt khi** có kết quả PUB01 từ máy TV3, không chỉ ảnh trạng thái trên Cloud Console.

**TV1.5 · Tuần 2–3, quản trị và nghiệm thu độc lập.** Hoàn thiện Rancher theo mục 15: thử phân giải hostname từ laptop và từ agent, kiểm tra TLS, đăng nhập bằng tài khoản viewer, mở đúng cụm local và namespace APP_NAMESPACE. Sau đó nhận từ TV2/TV3 hai tên Pod nguồn, endpoint cần gọi và cấu hình policy cho từng lượt. Ghi kết quả khi chỉ bật luật Istio, chỉ bật luật mạng và khi bật cả hai. Nếu lỗi, yêu cầu người sở hữu luật khôi phục đối chứng rồi mới kết luận. **Giao cho nhóm** hồ sơ ADM01 và SEC04 với tên nguồn, đích, timestamp và phản hồi thực tế.

**TV1.6 · Tuần 4, tiếp quản bài sửa lỗi và đóng lab.** Nhận tên Service thử từ TV3. Dùng YAML để tìm selector, đối chiếu nhãn Pod, sửa manifest thử rồi quan sát endpoint xuất hiện; nhờ TV2 gọi lại qua cùng tên. Kiểm kê cloud LB, IP, disk và VM; lưu bằng chứng ngoài VM trước khi dọn tài nguyên sau bảo vệ. Sản phẩm cuối là sơ đồ đường public, inventory có trạng thái giữ/xóa và báo cáo chi phí.

**Phần nói ngày 5 (2 phút).** Mở danh sách VM, đối chiếu IP riêng với InternalIP của ba node trong cụm, rồi mở một Pod trên dashboard và chỉ đúng worker chứa Pod đó. Kết thúc bằng cách chuyển giao cho TV2: “Đây là nơi Pod chạy. Nếu Pod này được thay thế, client sẽ tìm Pod mới bằng cách nào?”

### 3.2. Thành viên 2 · Kubernetes Service và cách tìm đúng Pod

**Vai trò.** TV2 quản lý `wk-01` và phụ trách nội dung trọng tâm của đồ án. Bạn này lấy manifest ứng dụng và release do TV2 chọn, dùng image có sẵn và tập trung vào quan hệ giữa tên DNS, selector, port, EndpointSlice và Pod đang phục vụ. TV2 cũng phụ trách route của ứng dụng tại gateway và luật phân quyền HTTP của Istio.

| Thời gian | TV2 làm gì, theo thứ tự nào? | Khi nào xong và bàn giao cho ai? |
|---|---|---|
| Tuần 1 · 02–06/11 | Dựng `wk-01`, join bằng thông tin TV1 cấp. Phối hợp với TV3 đặt client và HTTP server ở hai worker để thử DNS/kết nối. Khi TV3 báo Istiod và gateway sẵn sàng, bật sidecar injection, áp ứng dụng do TV2 lựa chọn và chọn CALLER_DEPLOYMENT. Ghi tên, loại và cổng của từng Service. Riêng với TARGET_SERVICE, đối chiếu selector với label của Pod và targetRef trong EndpointSlice. | Gửi TV3 namespace, URL tạo traffic và bảng Service. Khi thay Pod thuộc Service TARGET_SERVICE, TV2 ghi UID trước/sau, endpoint Ready và kết quả gọi lại qua cùng tên. TV3 lặp được phép thử từ hướng dẫn của TV2. |
| Tuần 2 · 09–13/11 | Cấu hình NodePort 30080 cho ingress gateway, giữ TARGET_SERVICE là ClusterIP. Thử qua IP riêng của **từng worker** trước khi yêu cầu TV1 nối cloud LB. Kiểm tra path, port, targetPort và route tới ENTRY_SERVICE. | Gửi TV1 manifest gateway, cổng đã thử, thời điểm và kết quả HTTP trên cả hai worker. Nếu gọi NodePort còn lỗi, TV2 và TV3 sửa chặng này trước khi TV1 kiểm tra LB. |
| Tuần 3 · 16–20/11 | Bật mTLS STRICT cho đích TARGET_SERVICE và xác nhận danh tính thực của CALLER_SERVICE. Áp AuthorizationPolicy cho phép CALLER_SERVICE gọi đúng đường dẫn. Thử từ CALLER_SERVICE và ENTRY_SERVICE, ghi HTTP status cùng log proxy đích, rồi gỡ luật để khôi phục đối chứng trước lượt thử của TV3. | CALLER_SERVICE nhận 200, ENTRY_SERVICE nhận 403 trong ca chỉ có luật Istio. TV1 chạy lại từ cùng nguồn, TV3 xác nhận trạng thái đối chứng đã phục hồi trước khi bật NetworkPolicy. |
| Tuần 4 · 23–27/11 | Tăng TARGET_SERVICE từ một lên hai replica, đợi cả hai Ready, đối chiếu từng endpoint với Pod rồi đưa về số replica ban đầu. Hoàn thiện sơ đồ Service và kiểm tra lại ca selector sai của TV3. | Bàn giao bảng Service, YAML đã ghim, lệnh thử và bằng chứng SVC01–SVC03. Một bạn khác giải thích được phần nào giữ nguyên và phần nào thay đổi khi backend được thay hoặc tăng số lượng. |

#### Phiếu thao tác của TV2

**TV2.1 · Ngày 1–2, dựng worker và kiểm tra đường tới ứng dụng.** Tạo wk-01 theo inventory TV1 giao, SSH vào chính máy này, chuẩn hóa containerd/kubelet và chạy lệnh join. Báo lại hostname, InternalIP, trạng thái Ready sau khi CNI hoạt động. Trong namespace thử, TV2 đặt HTTP server trên wk-01 và gửi IP, port, tên Service cho TV3; TV3 gọi từ client trên wk-02. TV2 ghi cả vị trí hai Pod và HTTP status trong NET01. Nếu truy cập IP Pod thành công nhưng tên Service lỗi, kiểm tra CoreDNS, namespace và EndpointSlice thay vì sửa firewall cloud ngay.

**TV2.2 · Ngày 3, đưa ứng dụng do TV2 lựa chọn mẫu vào mesh.** Trên laptop có kubeconfig, chờ TV3 xác nhận Istiod và gateway đã Ready. Tạo namespace APP_NAMESPACE, bật injection trước khi áp manifest ứng dụng do TV2 lựa chọn của release đã ghim. Giữ CALLER_DEPLOYMENT hoạt động, cấu hình Istio Gateway và VirtualService cho trang ứng dụng theo mục 12. Lập bảng `apps/service-inventory.md`: mỗi dòng gồm tên Service, nguồn gọi, namespace, loại, selector, port, targetPort và endpoint thực. **Bàn giao cho TV3** namespace, đường dẫn /APP_PATH và phiên bản CALLER_SERVICE đang chạy. Chỉ giao khi trang hiện nội dung kiểm thử và `kubectl -n APP_NAMESPACE get pods` cho thấy app và proxy Ready.

**TV2.3 · Ngày 4–5, chuẩn bị thí nghiệm chính về Service.** Chạy các lệnh dưới đây từ laptop, ghi kết quả trước và sau khi thay đúng một Pod thuộc Service TARGET_SERVICE do Deployment quản lý. Cột UID và targetRef giúp nhận diện Pod kể cả khi địa chỉ IP được cấp lại.

```sh
kubectl -n APP_NAMESPACE get svc TARGET_SERVICE -o yaml
kubectl -n APP_NAMESPACE get pods -l app=TARGET_LABEL -o custom-columns=NAME:.metadata.name,UID:.metadata.uid,IP:.status.podIP,NODE:.spec.nodeName
kubectl -n APP_NAMESPACE get endpointslice -l kubernetes.io/service-name=TARGET_SERVICE -o yaml
```

Từ Pod CALLER_SERVICE có công cụ HTTP hoặc debug container cùng Pod, gọi `http://TARGET_SERVICE:SERVICE_PORT/TEST_PATH` trước khi thay Pod. Chờ Pod mới Ready, chạy lại đúng request rồi điền `docs/evidence/M1/SVC02.md`: tên DNS, ClusterIP, UID cũ/mới, targetRef cũ/mới, mã HTTP trước/sau. **Đạt khi** TV3 đọc phiếu và tự lặp được phép thử. Nếu có gián đoạn lúc chỉ có một replica, ghi độ dài hoặc thời điểm quan sát thay vì bỏ kết quả khỏi báo cáo.

**TV2.4 · Tuần 2, bàn giao NodePort cho TV1.** Chịu trách nhiệm phần cấu hình HTTP của Service ingress gateway: đọc port/targetPort hiện hành, giữ selector/port khác của gateway, đặt nodePort=30080 theo mục 14. Kiểm tra từ cp-01 hoặc client cùng VPC bằng hai URL `http://<IP-wk-01>:30080/APP_PATH` và `http://<IP-wk-02>:30080/APP_PATH`. Ghi IP worker, giờ thử, mã HTTP, có/không trả nội dung đúng và Service đích. Nếu một URL thất bại, cung cấp endpoint gateway và worker lỗi cho TV3; nếu cả hai đạt, giao bảng kết quả và manifest cho TV1 cấu hình LB.

**TV2.5 · Tuần 3, chứng minh quyền gọi theo danh tính.** Đọc ServiceAccount thực của CALLER_DEPLOYMENT và ENTRY_SERVICE. Bật STRICT ở TARGET_SERVICE, xác lập đối chứng hai nguồn cùng nhận 200. Sau đó áp riêng AuthorizationPolicy, gọi lại cùng GET từ cả hai Pod và lấy log istio-proxy của Pod thuộc Service TARGET_SERVICE cho lần trả 403. Gỡ luật phân quyền vừa thử và xác nhận cả hai nguồn gọi lại được trước khi báo TV3 bắt đầu lượt thử NetworkPolicy. Lưu tên manifest, danh tính thật, thời điểm và kết quả vào SEC01/SEC02.

**TV2.6 · Tuần 4, chứng minh một Service theo dõi nhiều backend.** Đọc số replica hiện tại của Deployment TARGET_SERVICE; lưu giá trị để khôi phục. Tăng lên hai replica, chờ rollout, đối chiếu từng targetRef Ready của EndpointSlice với UID của hai Pod. Gọi vẫn bằng tên TARGET_SERVICE, sau đó trả số replica về ban đầu và kiểm tra lại. **Bàn giao cho TV3** SVC03 với ba trạng thái trước khi scale, sau khi scale và sau khi phục hồi. Số endpoint phải phù hợp với Pod Ready thực tế; hai response giống nhau không đủ để kết luận tải chia đều.

**Phần nói ngày 5 (2 phút).** Mở YAML của TARGET_SERVICE, chỉ `port`, `targetPort` và `selector`, rồi đối chiếu địa chỉ backend trong EndpointSlice với Pod thật. Cho thầy thấy cùng tên `TARGET_SERVICE` vẫn gọi được sau khi Pod mới Ready. Nếu IP được tái sử dụng, dùng UID để phân biệt hai Pod.

### 3.3. Thành viên 3 · Mạng giữa các Pod, quan sát và chẩn đoán lỗi Service

**Vai trò.** TV3 quản lý `wk-02`, cài Calico cho mạng Pod, cài Istio nền và dùng Prometheus/Kiali để quan sát. Ngoài dashboard, bạn này trực tiếp thực hiện hai bài kiểm thử: Service có tên nhưng selector không chọn được Pod, và Service có backend Ready nhưng nguồn gọi bị NetworkPolicy chặn. Hai bài dùng cùng đích để giải thích vì sao một lời gọi thất bại.

| Thời gian | TV3 làm gì, theo thứ tự nào? | Khi nào xong và bàn giao cho ai? |
|---|---|---|
| Tuần 1 · 02–06/11 | Chốt phiên bản tương thích, dựng `wk-02`, join cụm và cài Calico với dải Pod đã thống nhất. Kiểm tra kết nối xuyên worker cùng TV2. Cài Istiod và ingress gateway, báo ngay cho TV2 khi hai thành phần sẵn sàng. Sau đó cài Prometheus, Kiali và phát traffic qua URL TV2 cung cấp. | Bàn giao cho TV1 kết quả thử Pod xuyên worker và cách mở graph. TV1 tự tạo request và tìm được cạnh CALLER_SERVICE → TARGET_SERVICE. Nếu graph trống, TV3 kiểm tra traffic, sidecar và số liệu Prometheus trước khi kết luận có lỗi mạng. |
| Tuần 2 · 09–13/11 | Dùng máy ngoài VPC truy cập IP frontend do TV1 bàn giao. Ghi IP, cổng, thời điểm, HTTP status, nội dung trang và cạnh tương ứng trên Kiali. Nếu lỗi, thử theo thứ tự từ Pod, Service, NodePort rồi tới cloud LB cùng người phụ trách từng chặng. | Có hai bằng chứng riêng: trang mở được từ ngoài VPC và lưu lượng xuất hiện trên graph. Gửi kết quả cho TV1 đối chiếu với backend healthy và TV2 đối chiếu với manifest. |
| Tuần 3 · 16–20/11 | Sau khi TV2 hoàn tất ca chỉ có Istio và phục hồi đối chứng, áp NetworkPolicy vào TARGET_SERVICE. Cho CALLER_SERVICE và ENTRY_SERVICE cùng gọi TCP SERVICE_PORT; kiểm tra DNS riêng, ghi lỗi kết nối và thử lại sau khi gỡ policy. | Bàn giao manifest và kết quả SEC03. TV1 tái hiện được ca thử. TV3 giải thích được sự khác nhau giữa không có endpoint, bị lọc mạng và bị proxy trả HTTP 403. |
| Tuần 4 · 23–27/11 | Tạo Service thử có selector không khớp, ghi DNS và EndpointSlice lúc chưa có backend. Bàn giao tình huống cho TV1 sửa; cùng TV2 xác nhận endpoint xuất hiện và nguồn hợp lệ gọi lại được. Xóa Service thử sau khi lưu bằng chứng. | Bàn giao kết quả SVC04, ảnh Kiali có thời điểm, log và hướng dẫn tái hiện lỗi. Bảng kết quả ghi rõ ca nào đã chạy, ca nào còn bị chặn. |

#### Phiếu thao tác của TV3

**TV3.1 · Ngày 1–2, dựng wk-02 và kiểm tra mạng xuyên worker.** Gửi cả nhóm bảng phiên bản Kubernetes, containerd, Calico và Istio trước khi mọi người cài package. Join wk-02 rồi cài Calico một lần cho toàn cụm bằng kubeconfig có quyền phù hợp. Đối chiếu IP pool và chế độ VXLAN với CIDR/firewall TV1 cấu hình. Đặt client trên wk-02, nhận từ TV2 địa chỉ HTTP server ở wk-01, gọi lần lượt bằng IP Pod rồi tên Service. Lưu kết quả hai lần gọi cùng `kubectl get pods -o wide` vào NET01. **Nếu IP Pod đã lỗi**, TV3 kiểm tra Calico/route, TV1 kiểm tra firewall liên node. Chỉ báo mạng đạt khi client gọi được qua cả hai cách.

**TV3.2 · Ngày 3, cài phần nền của Istio rồi giao việc cho TV2 ngay.** Từ máy quản trị, chạy precheck theo mục 12, triển khai Istiod và ingress gateway theo profile đã chọn, xem Deployment và Service trong istio-system. Báo TV2 tên gateway, namespace, port và trạng thái Ready để TV2 bật injection và cấu hình route. Trong lúc TV2 triển khai ứng dụng, TV3 cài Prometheus rồi Kiali. TV3 sở hữu phần cài gateway của Istio; TV2 sở hữu route ứng dụng do TV2 lựa chọn và thay đổi NodePort ở tuần 2. Hai người thống nhất manifest trước khi đổi cùng một Service.

**TV3.3 · Ngày 4–5, dựng lại biểu đồ từ một lần gọi thật.** Nhận URL /APP_PATH từ TV2. Mở gateway và Kiali qua hai terminal port-forward riêng, phát request theo mục 12.2, ghi giờ bắt đầu/kết thúc. Trong Kiali chọn namespace APP_NAMESPACE, cửa sổ năm phút, chọn cạnh CALLER_SERVICE → TARGET_SERVICE và đọc request rate. Gửi TV1 cách mở lại và ảnh có khoảng thời gian. Nếu graph trống, kiểm tra theo thứ tự: trang trả nội dung đúng → Pod có proxy → Prometheus có series → Kiali đúng namespace/time window. **Đạt OBS01 khi** TV1 tự phát traffic mới và tìm lại được cạnh, thay vì chỉ mở ảnh của TV3.

**TV3.4 · Tuần 2, kiểm tra độc lập IP public.** Từ laptop ngoài VPC dùng IP frontend TV1 giao, gọi đúng cổng 30080 và mở /APP_PATH bằng trình duyệt. Ghi thời điểm, URL, HTTP status và ảnh trang trả nội dung đúng; đối chiếu cùng khoảng thời gian với Kiali. Nếu NodePort đã qua nhưng URL public hỏng, gửi log cho TV1 kiểm tra LB. Nếu cả URL nội bộ và public đều lỗi, gửi TV2 endpoint/route cần kiểm tra. Lưu bằng chứng người dùng bên ngoài trong PUB01, tách riêng khỏi traffic phát qua port-forward.

**TV3.5 · Tuần 3, cô lập lỗi lọc mạng.** Đợi TV2 xác nhận đã gỡ AuthorizationPolicy thử và hai nguồn đều trả 200. Chỉ áp NetworkPolicy ingress cho TARGET_SERVICE, cho nhãn CALLER_SERVICE trong APP_NAMESPACE gọi TCP SERVICE_PORT. Từ CALLER_SERVICE và ENTRY_SERVICE kiểm tra DNS, rồi gọi cùng đường dẫn với timeout hữu hạn. Ghi stdout/stderr, mã thoát và log proxy liên quan. Gỡ đúng NetworkPolicy, gọi lại để xác nhận phục hồi, sau đó giao manifest cho TV1 chạy ca tích hợp. **Đạt SEC03 khi** TV1 tái hiện được sự khác biệt trước/sau khi áp một luật; tên TARGET_SERVICE vẫn phân giải được ở cả hai lượt.

**TV3.6 · Tuần 4, giao cho TV1 một lỗi Service có thể tái hiện.** Tạo Service riêng tên service-selector-test, cùng namespace và port với TARGET_SERVICE, nhưng selector không khớp Pod nào. Từ nguồn được phép, lưu kết quả DNS và EndpointSlice khi chưa có endpoint Ready. Giao tên Service, triệu chứng và lệnh kiểm tra cho TV1; để TV1 tự tìm và sửa selector. Sau khi sửa, TV2 xác nhận gọi cùng URL thành công. TV3 lưu hai trạng thái vào SVC04, xóa riêng Service thử rồi kiểm tra Service TARGET_SERVICE gốc. Sản phẩm cuối là một bài phân biệt **tên phân giải được nhưng không có backend** với **backend tồn tại nhưng từ chối nguồn gọi**.

**Phần nói ngày 5 (2 phút).** Phát request từ trang ứng dụng, chọn namespace APP_NAMESPACE và khoảng thời gian vừa chạy trên Kiali. Chỉ vào cạnh CALLER_SERVICE → TARGET_SERVICE, nêu nguồn, đích và bằng chứng request thực. Nối lại với phần của TV2 bằng cách chỉ ra Service TARGET_SERVICE và backend đang nhận lưu lượng.

### 3.4. Điểm bàn giao để nhóm làm việc đúng thứ tự

| Khi nào? | Ai giao cho ai? | Thông tin phải có trước khi làm bước tiếp |
|---|---|---|
| Ngày 1–2 | TV1 → TV2, TV3 | VPC/subnet, IP từng VM, cách SSH và lệnh join qua kênh riêng. Hai bạn phản hồi bằng tên node thực trong cụm. |
| Ngày 2–3 | TV3 → TV2 | Mạng Pod xuyên worker đã chạy; Istiod và ingress gateway Ready. TV2 mới triển khai workload có sidecar. |
| Ngày 3–4 | TV2 → TV3 → TV1 | TV2 giao namespace, URL và Service đích. TV3 tạo traffic và bàn giao graph. TV1 mở lại cả dashboard cụm và graph từ laptop trình chiếu. |
| Tuần 2 | TV2 → TV1 → TV3 | NodePort qua hai worker đã đạt; TV1 nối LB và giao IP frontend; TV3 kiểm tra từ ngoài VPC. |
| Tuần 3 | TV2 → TV3 → TV1 | TV2 lưu ca Istio và phục hồi đối chứng. TV3 chạy ca NetworkPolicy riêng. TV1 bật cả hai và kiểm tra đầu cuối. |

### 3.5. Khối lượng và cách đánh dấu hoàn thành

Tuần đầu dự trù **15 giờ cho mỗi người**: 10 giờ triển khai, 3 giờ kiểm tra chéo, 2 giờ chuẩn bị bằng chứng và diễn tập. Mỗi người tự dựng một VM, thực hiện ít nhất một phép thử Service, viết kết quả phần mình và trình bày trong hai phút. Cuối ngày, từng người ghi việc đã xong, bằng chứng, lỗi còn mở và người đang chờ đầu ra. Nếu một người còn hơn hai giờ việc so với kế hoạch ngày, chuyển phần thử lại hoặc tích hợp cho người kiểm tra chéo.

Một công việc chỉ được đánh dấu **hoàn thành** khi có cấu hình hoặc lệnh đã dùng, kết quả quan sát được và một thành viên khác tái hiện được từ hướng dẫn. Ví dụ, với nhiệm vụ “đưa website ra ngoài”, TV1 tạo được LB là bước triển khai; kết quả nghiệm thu là TV3 mở đúng IP frontend từ ngoài VPC và TV2 đối chiếu được request đó với Service trong cụm.

## 4. Giai đoạn A · Dựng cụm và báo cáo dashboard trong năm ngày

| Ngày | Từng công việc và người thực hiện | Điều kiện hoàn thành |
|---|---|---|
| **02/11 · Thiết kế và VM** | TV1 chốt rubric, loại dashboard, ngân sách, quota, zone; tạo VPC, firewall và cp-01. TV2 tạo wk-01, repo, chọn ứng dụng và phiên bản. TV3 tạo wk-02, đối chiếu tương thích Linux/containerd/Kubernetes/Calico/Istio. Mỗi người cài runtime trên VM của mình. | Bảng phiên bản và IP đã lưu. Ba VM có hostname riêng, SSH được, tải được image. Mỗi thành viên biết dải VPC, Pod, Service và cách kết nối API. |
| **03/11 · Kubernetes** | TV1 cấu hình kubelet/runtime thống nhất, init bằng IP riêng và CIDR phù hợp với CNI. TV2 và TV3 join worker; TV3 cài Calico. TV2 đặt hai Pod thử ở hai worker khác nhau, thử DNS và HTTP. | Ba node Ready, CoreDNS sẵn sàng, kết nối Pod xuyên worker thành công. Lưu kết quả get nodes -o wide và nguồn/đích của phép thử. |
| **04/11 · Dashboard và ứng dụng** | TV1 cài dashboard cụm, bind quyền đọc cần thiết. TV3 cài Istio sidecar mode có ingress gateway, Prometheus rồi Kiali từ bộ addon cùng release. Sau khi Istiod Ready, TV2 bật injection trước khi deploy ứng dụng do TV2 lựa chọn, giữ CALLER_DEPLOYMENT, cấu hình Gateway và VirtualService cho /APP_PATH. | Từ laptop mở được dashboard cụm và Kiali; Pod ứng dụng do TV2 lựa chọn có app và proxy Ready. Truy cập qua gateway bằng port-forward, trang hiện nội dung kiểm thử. |
| **05/11 · Kiểm chứng** | TV1 mở lại bằng máy trình chiếu. TV2 ghi selector, endpoint hiện tại, tạo lại Pod thuộc Service TARGET_SERVICE và chờ Ready, gọi lại bằng cùng tên Service. TV3 phát traffic qua /APP_PATH trong vài phút, chọn APP_NAMESPACE và cửa sổ 5 phút trong Kiali. | Lưu ảnh ba node, Pod trên worker, Service và EndpointSlice, graph có cạnh CALLER_SERVICE → TARGET_SERVICE cùng thời điểm. Một thành viên khác lặp lại được thao tác. |
| **06/11 · Báo cáo** | TV1 đi từ VM đến node và Pod. TV2 đi từ tên Service đến endpoint thực tế. TV3 đi từ request đến biểu đồ. Mỗi bạn có 2 phút; diễn tập hai lượt và ghi hình một lượt làm dự phòng. | Có demo trực tiếp, log và danh sách việc tiếp theo. Nêu rõ URL ngày 5 dùng port-forward; phép thử Internet thực hiện sau khi có LB. |

**Lệnh dùng để kiểm tra ngay trước lúc trình chiếu.** Từ laptop đã kết nối API, mở từng lệnh port-forward trong terminal riêng; đối chiếu tên và cổng thực với Service đã cài.

```sh
kubectl get nodes -o wide
kubectl -n APP_NAMESPACE get pods -o wide
kubectl -n APP_NAMESPACE get svc TARGET_SERVICE -o yaml
kubectl -n APP_NAMESPACE get endpointslice -l kubernetes.io/service-name=TARGET_SERVICE -o wide
kubectl -n istio-system port-forward svc/istio-ingressgateway 8080:80
kubectl -n istio-system port-forward svc/kiali 20001:20001
kubectl -n headlamp port-forward svc/headlamp 8081:80
```

Mở trang ứng dụng tại `http://127.0.0.1:8080/APP_PATH`, Kiali tại `http://127.0.0.1:20001/kiali`. Nếu graph trống, kiểm tra trang trả nội dung đúng, Pod có sidecar, Prometheus có mẫu `istio_requests_total`, namespace và khoảng thời gian đã chọn. Nếu node NotReady, xử lý CNI, CIDR và firewall trước khi triển khai mesh.

## 5. Giai đoạn B · Công bố dịch vụ và quản trị cụm (09–13/11)

| Thứ tự | Công việc | Nghiệm thu |
|---|---|---|
| B1 · TV2 | Đặt Service ingress gateway thành NodePort TCP 30080, externalTrafficPolicy=Cluster. Kiểm tra route chỉ dẫn tới ENTRY_SERVICE; giữ TARGET_SERVICE là ClusterIP. | Truy cập qua IP worker và NodePort từ nguồn được phép. Kiểm tra response, nội dung kiểm thử và endpoint của gateway. |
| B2 · TV1 | Tạo instance group gồm hai worker, regional external passthrough Network Load Balancer, backend service, TCP health check và forwarding rule TCP 30080. Cho phép nguồn health check và client demo tới đúng cổng. | Backend healthy. TV3 gọi http://<PUBLIC_IP>:30080/APP_PATH từ ngoài VPC, TV2 đối chiếu traffic trên Kiali. |
| B3 · TV1, TV3 | Nếu chưa cài ở tuần đầu, cài Rancher sau khi đo tài nguyên và chọn phiên bản tương thích. Chuẩn bị ingress nội bộ, chứng chỉ, hostname và quyền người xem; giữ địa chỉ quản trị riêng. | Từ laptop đăng nhập Rancher, thấy đúng ba node và workload. Đăng nhập lại bằng tài khoản chỉ đọc và kiểm tra quyền. |
| B4 · TV2, TV3 | Đối chiếu ClusterIP của TARGET_SERVICE, NodePort của gateway, loại LoadBalancer và ExternalName. Giải thích ai chịu trách nhiệm cấp IP ngoài trong thiết kế này. | Sơ đồ ghi đúng cổng, Service, Pod gateway, Istio Gateway và cloud LB. Người kiểm tra chéo truy vết được một lượt gọi. |

## 6. Giai đoạn C · Chính sách mạng và service mesh (16–20/11)

Dùng một yêu cầu cố định: GET `http://TARGET_SERVICE:SERVICE_PORT/TEST_PATH` từ **hai Pod nguồn khác nhau** trong namespace APP_NAMESPACE. Có thể dùng ephemeral debug container trong Pod để giữ đúng danh tính, nhãn và đường qua proxy. Duy trì mTLS STRICT, bật access log cần thiết và ghi lại ServiceAccount thực của CALLER_SERVICE. Mỗi bước chỉ thay lớp đang thử.

| Ca thử | Cấu hình và người phụ trách | Kết quả cần lưu |
|---|---|---|
| C1 · Đối chứng | TV1 xác nhận DNS, hai endpoint nguồn hoạt động. Chưa có luật hạn chế hai Pod. | CALLER_SERVICE và ENTRY_SERVICE cùng nhận 200. Lưu lệnh, nguồn, đích, thời gian, bằng chứng mTLS. |
| C2 · Phân quyền HTTP | TV2 đặt AuthorizationPolicy chọn TARGET_SERVICE, chỉ cho principal của CALLER_SERVICE gọi GET trên đường dẫn thử. | CALLER_SERVICE nhận 200, ENTRY_SERVICE nhận 403. Access log của proxy đích cho thấy RBAC từ chối. Gỡ policy, lặp C1. |
| C3 · Lọc mạng | TV3 áp NetworkPolicy ingress chọn TARGET_SERVICE, cho Pod có nhãn CALLER_SERVICE trong cùng namespace vào TCP SERVICE_PORT. | CALLER_SERVICE nhận 200; ENTRY_SERVICE vẫn tra được DNS nhưng thất bại ở kết nối. Gỡ luật để xác nhận phục hồi. |
| C4 · Tích hợp | TV1 bật lại cả hai lớp và thực hiện bộ test do TV2/TV3 bàn giao. | Trang public vẫn trả nội dung đúng qua CALLER_SERVICE. Gọi trực tiếp từ ENTRY_SERVICE bị chặn. Ghi policy đang bật cùng mỗi kết quả. |

Nếu rubric yêu cầu chia tải, TV2 triển khai thêm CALLER_SECOND_VERSION, khai báo subset theo version, đặt VirtualService nội bộ chia 80/20 rồi gửi một tập request đủ lớn. Ghi số lượt từng phiên bản và trả về 100% phiên bản ban đầu. Giữ quy tắc đường gọi TARGET_SERVICE và ca C4 sau khi hoàn tác.

## 7. Giai đoạn D · Kiểm chứng Service, khôi phục và bàn giao (23–27/11)

| Công việc | Các bước cụ thể | Bằng chứng |
|---|---|---|
| D1 · Thay đổi backend | TV2 tăng replica TARGET_SERVICE, TV3 theo dõi EndpointSlice và gửi request qua cùng tên Service. Sau đó trả replica về số ban đầu. | Đối chiếu UID/địa chỉ từng Pod Ready với endpoint trước và sau; DNS và ClusterIP giữ nguyên. |
| D2 · Chẩn đoán Service | TV3 tạo Service thử có selector sai; TV1 sửa selector và TV2 kiểm tra lại cùng một request. | DNS phân giải ở cả hai trạng thái. Khi sửa selector có endpoint Ready và HTTP thành công. |
| D3 · Vận hành | TV1 ghi thủ tục backup etcd/cấu hình, quyền truy cập, khôi phục trên môi trường thử và kiểm kê tài nguyên. TV2 tái triển khai manifest theo thứ tự. TV3 chạy lại suite và đóng gói bằng chứng. | Có hướng dẫn dựng lại, commit đã demo, kết quả đạt/chưa đạt, lỗi còn mở, chi phí thực. Giữ bản sao ngoài disk của VM trước khi dọn lab. |
| D4 · Bảo vệ | 2 phút cụm và Rancher; 5 phút DNS, selector, EndpointSlice, NodePort và URL public; 3 phút phân quyền; 2 phút Kiali và kết luận. | Mỗi thành viên lần theo được một request từ client đến Pod và giải thích điều gì thay đổi khi Pod được tạo lại. |

## 8. Cấu trúc bàn giao và quản lý tiến độ

```text
infra/          Sơ đồ VPC, VM, firewall, backend, LB và checklist chi phí
cluster/        Phiên bản, init/join, cấu hình runtime, CNI, hướng dẫn khôi phục
apps/  Namespace, ServiceAccount, Deployment, Service và image đã ghim
mesh/           Cấu hình Istio, gateway, routes, mTLS và AuthorizationPolicy
network/        NetworkPolicy, nguồn/đích/port, lệnh apply và hoàn tác
observability/  Dashboard, Prometheus, quyền xem, cách tạo traffic
service-labs/   Manifest Service thử, ca đổi selector/replica và hướng dẫn khôi phục
tests/          Ca thử, kết quả đối chứng, smoke test, regression
docs/           Nhật ký quyết định, sơ đồ thực, demo script và evidence theo ngày
```

Đây là cấu trúc repo **đề xuất**. Chỉ đưa manifest và hướng dẫn có thể chia sẻ vào Git. Kubeconfig, token, khóa SSH và thông tin đăng nhập được giữ ngoài repo. Mỗi công việc có người phụ trách, người chạy lại, commit, ngày chạy, kết quả mong đợi/thực tế và đường dẫn log. Chỉ đánh dấu hoàn thành sau khi người thứ hai kiểm tra được kết quả.

| Mốc nghiệm thu | Tài liệu phải bàn giao | Nếu chưa đạt |
|---|---|---|
| M1 · 06/11 | Sơ đồ ba VM, ảnh node và workload, YAML Service, EndpointSlice, ảnh Kiali có traffic | Ghi rõ màn hình hoặc phép thử nào còn lỗi; dùng bản quay lần chạy gần nhất nếu mất mạng. |
| M2 · 13/11 | Sơ đồ đường public, backend healthy, URL thử ngoài VPC, bằng chứng quản trị Rancher | Khoanh vùng từng chặng LB → NodePort → gateway → ứng dụng. Port-forward chỉ chứng minh đường nội bộ. |
| M3 · 20/11 | Bốn ca C1–C4 với YAML, log và kết quả khôi phục | Lặp lại đối chứng trước khi quy lỗi cho proxy hoặc CNI. |
| M4 · 27/11 | Bộ cấu hình tái lập, kết quả nghiệm thu theo rubric, báo cáo, demo và bảng chi phí | Liệt kê phần chưa hoàn thành cùng nguyên nhân; chỉ công bố kết quả đã chạy. |

## 9. Các tài liệu đã dùng để thống nhất kế hoạch

- Plan gốc Project 8 và plan GKE trước điều chỉnh là nguồn cho chức năng quản trị, cấu trúc workload và nghiệm thu.
- Plan tự dựng VM và Istio, plan dashboard năm ngày và slide cloud sau góp ý là cơ sở chốt kiến trúc và lịch. Bản năm ngày có lệnh chi tiết cho Helm, token trình chiếu, port-forward và phát traffic bằng PowerShell.
- Slide cloud chi tiết cũ là nguồn cho phân tầng IAM/RBAC, release, lưu trữ và chi phí; slide local dùng đối chiếu đường vào và điều kiện demo.
- Tài liệu vận hành: [kubeadm](https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/create-cluster-kubeadm/), [Kubernetes Service](https://kubernetes.io/docs/concepts/services-networking/service/), [ứng dụng do TV2 lựa chọn](https://istio.io/latest/docs/examples/APP_NAMESPACE/), [Kiali](https://istio.io/latest/docs/tasks/observability/kiali/), [Google Cloud passthrough Network Load Balancer](https://cloud.google.com/load-balancing/docs/network/networklb-backend-service).

## 10. Ngày 1 · Phiếu thiết kế và chuẩn bị Google Cloud

### 10.1. Chốt sáu đầu vào trước khi thuê máy

| Đầu vào | Ai điền | Giá trị dự kiến hoặc câu hỏi cần trả lời |
|---|---|---|
| Phạm vi chấm điểm | Cả nhóm | Dashboard ngày 5 cần xem trên máy nhóm hay thầy cần tự truy cập? Rancher có bắt buộc trong tuần đầu? Thầy muốn nhóm trình diễn trực tiếp những loại Service nào? Ghi ngày và kết luận cụ thể. |
| Tài khoản | TV1 | Project ID, billing account, ai tạo mạng/VM/LB, ai chỉ SSH vào máy mình, ai có quyền dọn tài nguyên. Dùng tài khoản riêng để truy vết thay đổi. |
| Khu vực | TV1 | Chọn một region và zone có quota cho 6 vCPU và 3 VM. Chọn cùng kiến trúc CPU, cùng bản Linux LTS, xác nhận image ứng dụng do TV2 lựa chọn có kiến trúc phù hợp. |
| Mạng | TV1 + TV3 | Ví dụ subnet node 10.20.0.0/24, IP riêng .10/.11/.12 lần lượt cho cp-01/wk-01/wk-02; Pod 10.244.0.0/16; Service 10.96.0.0/12. Đối chiếu route hiện hữu, VPN và LAN trước khi chốt. |
| Phiên bản | TV3 | Ghi OS/image ID, kernel, containerd, kubeadm/kubelet/kubectl, Calico, Istio, chart dashboard, Prometheus, Kiali. Chọn giao của các ma trận hỗ trợ. Lưu tên release, digest/tag, nguồn tải và ngày kiểm tra. |
| Sức chứa và tài chính | TV2 + TV1 | TV2 cộng requests ứng dụng, proxy và dashboard, so với allocatable của hai worker. TV1 tính theo giờ máy chạy, disk, IP, LB, traffic và NAT nếu chọn. Đặt budget alert, ghi người nhận. |

### 10.2. Thứ tự tạo tài nguyên bằng Cloud Console

1. **TV1 – Project và API.** Chọn đúng project của nhóm, gắn billing, bật Compute Engine API. Kiểm tra zone, quota CPU/disk/IP. Ghi nhãn project/lab trên VM để tìm tài nguyên khi kết thúc.
2. **TV1 – VPC network.** Tạo VPC custom và một subnet trong region đã chọn. Dành ba IP nội bộ ổn định. Tạo network tag hoặc dùng service account để phân biệt control plane với worker khi viết firewall.
3. **TV1 – Đường ra Internet.** Ưu tiên VM có IP riêng; cấu hình Cloud Router/Cloud NAT nếu cần tải package và image ra Internet. Phương án lab khác là cho VM có external IP phục vụ outbound, kiểm soát inbound bằng firewall. Chọn một cách, ghi chi phí và kiểm tra tải từ registry trên cả ba máy. IP của VM khác IP frontend của load balancer.
4. **Mỗi người – VM instances.** Tạo máy mình phụ trách bằng cùng Linux image. Gắn đúng subnet, IP, tag, disk và service account. Nếu Calico yêu cầu IP forwarding theo thiết kế trên GCE, bật thuộc tính phù hợp ở VM và cấu hình Linux forwarding. Chụp bảng ba VM có tên, zone, IP riêng và cấu hình thực.
5. **Mỗi người – laptop.** Cài Git, gcloud, SSH và kubectl. Kiểm tra project đang chọn, SSH từ tài khoản riêng. Ghi phiên bản thực của công cụ. VM và website chạy trên cloud kể cả khi laptop tắt.
6. **TV1 – quản trị private.** Nếu dùng IAP, cấp quyền tunnel/SSH và firewall nguồn IAP phù hợp. Nếu dùng SSH trực tiếp, giới hạn IP nguồn. Dùng tunnel từ laptop đến API riêng; giữ thông tin CA và tên/IP khớp SAN của chứng chỉ. Thành viên chỉ cần quyền Kubernetes tương ứng với công việc.
7. **Điểm dừng.** Từ cả ba VM kiểm tra hostname, route, đồng bộ thời gian, DNS Internet và khả năng tải image. Nếu image pull lỗi, tách lỗi DNS, route outbound và xác thực registry trước khi thử cài Kubernetes.

### 10.3. Bảng luồng mạng để lập firewall

| Nguồn → đích | Luồng cần cho phép | Kiểm tra |
|---|---|---|
| Laptop/IAP → VM quản trị | TCP 22 qua đường SSH đã chọn | SSH được bằng từng tài khoản, xem đúng hostname. |
| Worker và đường quản trị → cp-01 | TCP 6443 tới API server | Worker join; kubectl truy cập được qua đường quản trị. |
| Control plane → kubelet của node | TCP 10250 | Lấy log, exec và port-forward đến Pod trên cả hai worker. |
| Node ↔ node | Chọn ví dụ Calico VXLAN, UDP 4789 giữa IP các node; nếu bật BGP/IP-in-IP thì bổ sung đúng giao thức của chế độ đó | HTTP tới Pod nằm trên worker khác vẫn hoạt động. Ping node chỉ xác nhận được một phần đường đi. |
| Thành phần local trên cp-01 | etcd và cổng control plane theo cấu hình kubeadm | etcd ở một control plane chỉ cần nguồn nội bộ theo thiết kế. Giữ phạm vi truy cập của etcd hẹp. |
| Health checker GCP → worker; IP người demo → frontend | TCP 30080 tại worker cho health check và traffic của passthrough LB. Lấy dải nguồn health check theo tài liệu đúng loại LB | Cả hai backend healthy; máy ngoài VPC truy cập được bằng IP frontend từ nguồn cho phép. |
| Browser → dashboard | Localhost port-forward qua API | UI đăng nhập bằng danh tính trình chiếu; không cần mở cổng dashboard ra Internet. |

VPC firewall lọc traffic tới VM. NetworkPolicy lọc traffic của Pod. Istio AuthorizationPolicy kiểm tra danh tính và thao tác ở workload. Cùng một lần truy cập có thể đi qua cả ba lớp. [Cổng Kubernetes](https://kubernetes.io/docs/reference/networking/ports-and-protocols/) · [Yêu cầu mạng của Calico](https://docs.tigera.io/calico/latest/getting-started/kubernetes/requirements)

## 11. Ngày 2 · Dựng Kubernetes từ ba máy Linux

### 11.1. Chuẩn hóa từng VM

Trên từng VM, người phụ trách ghi kết quả các lệnh đọc trạng thái sau. Lưu kết quả dưới tên node của mình; TV3 đối chiếu cả ba trước khi cho join.

```sh
hostnamectl
ip -br addr
ip route
free -h
df -h /
swapon --show
sysctl net.ipv4.ip_forward
systemctl is-active containerd
kubeadm version -o short
kubelet --version
```

1. Đặt hostname duy nhất, xác nhận route tới IP riêng của hai máy còn lại và IP advertise của control plane. Tránh lấy external IP làm InternalIP.
2. Với cấu hình lab dùng kubeadm mặc định, tắt swap và điều chỉnh cấu hình khởi động để swap không tự bật lại. Bật IPv4 forwarding, nạp module kernel cần cho runtime/CNI, cấu hình sysctl bền vững qua reboot.
3. Cài containerd có CRI bật; chọn cgroup driver systemd thống nhất với kubelet. Kiểm tra service chạy sau reboot. Cài kubeadm và kubelet cùng minor/patch đã chọn, ghim gói. Ghi endpoint CRI nếu VM có nhiều runtime.
4. Kiểm tra dung lượng image filesystem và đồng hồ hệ thống. Pull trước các image control plane trên cp-01 bằng kubeadm của đúng bản. Nếu pull chậm, xử lý trước khi init để phân biệt lỗi Internet với lỗi bootstrap.
5. Kubelet có thể chờ bootstrap trước init/join. Chỉ kết luận lỗi sau khi đọc journal và biết bước cấu hình đã tới đâu.

### 11.2. Khởi tạo cp-01 và kết nạp worker

**TV1 trên cp-01.** Ví dụ dưới đây dùng đúng các dải ở mục 10.1. Thay số nếu phiếu thiết kế đã duyệt khác. Lưu cấu hình kubeadm có version đã ghim trong repo nếu triển khai lại nhiều lần.

```sh
sudo kubeadm init --apiserver-advertise-address=10.20.0.10 --pod-network-cidr=10.244.0.0/16 --service-cidr=10.96.0.0/12
mkdir -p "$HOME/.kube"
sudo install -m 600 -o "$(id -u)" -g "$(id -g)" /etc/kubernetes/admin.conf "$HOME/.kube/config"
kubectl get nodes -o wide
```

**TV3 và TV1.** Cài Calico từ release đã ghim. Nếu dùng operator, cài CRD/operator trước rồi Installation; sửa IPv4 pool thành dải Pod đã chọn, đặt VXLAN nếu dùng bảng firewall trên. Kiểm tra DaemonSet trên node, trạng thái operator và CoreDNS. Một cluster chỉ dùng một CNI chính. Nếu CoreDNS Pending lúc chưa có worker để lập lịch, tiếp tục bước join rồi kiểm tra lại.

**TV2 và TV3 trên worker của mình.** TV1 cấp lệnh join có token và CA hash qua kênh riêng. Dùng IP nội bộ cp-01; nếu token hết hạn, tạo lệnh mới bằng `kubeadm token create --print-join-command`. Sau join, xác nhận kubelet kết nối API và node có InternalIP chính xác.

```sh
kubectl get nodes -o wide
kubectl get pods -A -o wide
kubectl -n kube-system get deploy coredns
kubectl get events -A --sort-by=.lastTimestamp
```

**Bài nghiệm thu xuyên worker.** TV2 tạo namespace thử, đặt Pod HTTP server trên wk-01 và Pod client có curl trên wk-02 bằng nodeSelector hostname. Gọi theo IP Pod trước, sau đó expose server bằng ClusterIP và gọi theo DNS. Ghi Pod IP, node và HTTP status. Nếu IP thành công nhưng DNS không thành công, xem CoreDNS và EndpointSlice. Nếu cả hai thất bại, xem route Pod, firewall/MTU và Calico. Xóa namespace thử sau khi lưu bằng chứng. Người kiểm tra chéo lặp lại từ hướng ngược lại.

**Xử lý một lần join hỏng.** Xem journal kubelet, thời hạn token, đồng hồ, cert/CA hash, đường TCP 6443 và endpoint CRI. Phân biệt worker chưa gia nhập với worker đã đăng ký nhưng NotReady do CNI. Chỉ tái dựng VM lỗi sau khi ghi nguyên nhân và xác định workload đang chạy trên đó; giữ nguyên cp-01 nếu lỗi chỉ nằm ở worker.

## 12. Ngày 3–5 · Dựng ứng dụng, dashboard và chuẩn bị báo cáo

### 12.1. Thứ tự triển khai và bàn giao giữa ba người

| Thứ tự | Chủ trì | Thao tác | Điều kiện để người tiếp theo bắt đầu |
|---|---|---|---|
| 1 | TV3 | Kiểm tra allocatable trên từng worker. Chọn bộ phát hành Istio có samples và istioctl cùng version. Chạy `istioctl x precheck`. | Đã ghi các cảnh báo và xử lý lỗi chặn cài đặt. |
| 2 | TV3 | Cài Istio sidecar mode có Istiod và ingress gateway. Ví dụ dùng profile demo của release đã chọn, khai báo Service gateway là NodePort bằng cấu hình được lưu lại. | Istiod và gateway Available. Kiểm tra tên/port thật bằng get svc. |
| 3 | TV2 | Tạo namespace APP_NAMESPACE; gắn label injection trước khi tạo Pod. Áp manifest ứng dụng do TV2 lựa chọn từ samples, giữ CALLER_DEPLOYMENT cho lượt demo đầu. | Từng Pod nghiệp vụ có app container và istio-proxy Ready; Service có endpoint Ready. |
| 4 | TV2 | Áp Gateway và VirtualService của mẫu trong namespace APP_NAMESPACE. Kiểm tra selector gateway, host và match của /APP_PATH cùng các đường phụ thuộc của giao diện. | Truy cập qua port-forward gateway, trang trả nội dung đúng theo bàn giao. Ghi được log từ gateway và workload. |
| 5 | TV3 | Cài Prometheus sau khi Istio hoạt động. Khi Prometheus Ready, cài Kiali từ cùng bộ addon; kiểm tra Service, quyền và kết nối từ Kiali tới Prometheus. | Sinh request thực thì truy vấn bộ đếm của Istio có dữ liệu. Mở được graph đúng namespace. |
| 6 | TV1 | Cài Headlamp trong namespace riêng, cấp danh tính chỉ đọc cho buổi demo. Nếu dùng Rancher sớm, theo quy trình mục 15. | Máy trình chiếu xem được nodes, workload, Service, EndpointSlice. Kiểm tra danh tính xem không có quyền sửa Deployment. |

**Triển khai ứng dụng do TV2 lựa chọn.** TV2 ghi nguồn, phiên bản, namespace và các Service vào application-handover.md, chuẩn bị manifest trong apps/ rồi triển khai trên cụm đã có Istio. TV3 xác nhận injection và thu thập metrics. TV1 chỉ bắt đầu thử đường public khi nhận đủ port, URL và response mong đợi. Các tên viết hoa ở những mục sau phải được thay bằng thông tin thực trước khi sử dụng.

### 12.2. Các màn hình và câu hỏi người trình bày phải trả lời

| Màn hình | Người thao tác | Câu hỏi cần trả lời bằng dữ liệu vừa thấy |
|---|---|---|
| Compute Engine → Nodes | TV1 | IP riêng của wk-01 trong Cloud Console có khớp InternalIP của node? Node ở trạng thái nào? |
| Dashboard cụm → Workloads → Pod | TV1 | Pod thuộc Service TARGET_SERVICE đang ở worker nào? Tên ứng dụng và proxy là gì? Điều gì xảy ra nếu một Pod được tạo lại? |
| Service TARGET_SERVICE → EndpointSlice → Pod | TV2 | Selector khớp nhãn nào? port và targetPort là bao nhiêu? Endpoint nào Ready và nó thuộc Pod nào? |
| Trình duyệt → /APP_PATH | TV2 | Request nào của ứng dụng tạo lời gọi từ workload nguồn tới Service đích? |
| Kiali → Traffic Graph | TV3 | Khoảng thời gian nào đang được quan sát? Cạnh CALLER_SERVICE → TARGET_SERVICE có request không? Có lỗi HTTP không? Thử ngừng tải rồi so với cửa sổ tiếp theo. |

**Sinh traffic từ PowerShell.** Mở tunnel, port-forward gateway và Kiali trong các terminal riêng. Chạy vòng lặp trước khi trình bày để Prometheus kịp thu thập mẫu. Ghi timestamp đầu/cuối, giữ trang trả nội dung đúng làm đối chứng.

```powershell
1..180 | ForEach-Object {
    curl.exe -sS --max-time 5 -o NUL -w "%{http_code}\n" http://127.0.0.1:8080/APP_PATH
    Start-Sleep -Seconds 1
}
```

**Kiểm tra Prometheus khi graph trống.** Port-forward Service prometheus tới localhost:9090, truy vấn `sum by (source_workload, destination_workload) (rate(istio_requests_total{destination_workload_namespace="APP_NAMESPACE"}[5m]))`. Nếu chưa có series, kiểm tra scrape targets, traffic và sidecar. Nếu đã có series, kiểm tra namespace, thời gian, quyền xem và URL Prometheus trong Kiali. HTTP 200 của HTML vẫn có thể đi kèm lỗi CALLER_SERVICE hoặc TARGET_SERVICE, vì vậy phải kiểm tra cả nội dung trang. [Quan sát mesh bằng Kiali](https://istio.io/latest/docs/tasks/observability/kiali/)

### 12.3. Danh tính trình chiếu và phương án ngày 5

TV1 tạo ServiceAccount demo-viewer trong namespace dashboard. Cấp quyền get/list/watch bằng ClusterRole cho nodes/namespaces, và RoleBinding trong APP_NAMESPACE cho pods, services, deployments, replicasets, endpointslices nếu chỉ cần xem ứng dụng này. Kiểm tra bằng `kubectl auth can-i` cho cả hành động đọc và hành động sửa. Dùng token ngắn hạn và mở UI qua địa chỉ loopback. Dùng tài khoản vận hành riêng cho port-forward; quyền đọc một resource và quyền tạo pods/portforward là hai quyền khác nhau.

- **Trước báo cáo 30 phút:** TV1 xác nhận tunnel, quyền và node; TV2 kiểm tra sao và endpoint; TV3 tạo traffic, đặt đúng time window. Chụp ảnh thực có giờ, commit và namespace. Tránh hiển thị token trong ảnh.
- **Trước báo cáo 5 phút:** mở sẵn ba cửa sổ và thử một request mới. Nếu mạng trường chặn tunnel, dùng bản ghi lần diễn tập, nói rõ thời điểm ghi; không ghi kết quả đó là lần chạy trực tiếp.
- **Trong 6 phút:** TV1 chỉ từ IP VM đến node và Pod; TV2 đi từ tên TARGET_SERVICE đến endpoint đang phục vụ; TV3 chỉ một cạnh trong graph. Kết thúc bằng việc còn lại của tuần 2: dùng IP public để một máy ngoài VPC vào website.
- **Nếu thầy cần tự truy cập từ máy riêng trong tuần đầu:** chuyển B1–B2 lên ngày 4, TV1 nhận LB, TV2 nhận NodePort, TV3 giữ Kiali. Hoãn thử chia phiên bản. Thầy truy cập URL ứng dụng công khai; dashboard quản trị vẫn dùng danh tính và đường kết nối riêng.

## 13. Chuyên đề trọng tâm · Kubernetes Service trong ứng dụng do TV2 lựa chọn

### 13.1. Bảng kê để điền bằng dữ liệu thật

| Service | Ai gọi và vì sao | Kiểu và cổng dự kiến | Bằng chứng |
|---|---|---|---|
| ENTRY_SERVICE | Istio ingress gateway đưa request từ website vào front-end | ClusterIP, HTTP SERVICE_PORT | Route gateway khớp tên Service, có endpoint Ready. |
| CALLER_SERVICE | ENTRY_SERVICE lấy dữ liệu từ workload nguồn | ClusterIP, HTTP SERVICE_PORT | Selector app=CALLER_LABEL có thể chọn nhiều version; TV2 ghi số replica và phiên bản thực. |
| TARGET_SERVICE | CALLER_DEPLOYMENT lấy nội dung kiểm thử | ClusterIP, HTTP SERVICE_PORT | DNS vẫn trả tên/địa chỉ Service khi Pod backend được thay thế. |
| istio-ingressgateway | Client nội bộ qua port-forward, sau đó LB qua worker | NodePort 30080 cho HTTP; lấy targetPort thật của gateway từ release | Service selector chọn Pod gateway; Istio Gateway cấu hình listener cho proxy. |
| kiali, prometheus, headlamp | Thành viên quản trị | ClusterIP; xem cổng thực bằng kubectl | UI đến được qua localhost, không thêm IP công khai cho từng dashboard. |

**Mẫu Service TARGET_SERVICE rút gọn dùng để giải thích manifest gốc.** So sánh với resource do ứng dụng do TV2 lựa chọn đã tạo trước khi chỉnh sửa.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: TARGET_SERVICE
  namespace: APP_NAMESPACE
spec:
  type: ClusterIP
  selector:
    app: TARGET_LABEL
  ports:
    - name: http
      port: SERVICE_PORT
      targetPort: TARGET_PORT
      protocol: TCP
```

Tên ngắn TARGET_SERVICE dùng được từ Pod trong APP_NAMESPACE; từ namespace khác dùng TARGET_SERVICE.APP_NAMESPACE hoặc FQDN theo cluster domain thực. CoreDNS phân giải tên; control plane cập nhật EndpointSlice theo Pod phù hợp. Trong mesh, proxy có thể chọn endpoint trực tiếp từ cấu hình do Istiod phân phối. Khi vẽ sơ đồ, thể hiện Service là hợp đồng tên/cổng, tránh khẳng định mọi gói tin đều đi qua một tiến trình tên “Service”.

### 13.2. Phép thử có thể lặp lại

1. TV2 lưu UID, Pod IP, worker, ClusterIP, port, selector và EndpointSlice ban đầu. Gửi GET từ Pod CALLER_SERVICE tới TARGET_SERVICE:SERVICE_PORT/TEST_PATH. Lưu HTTP status và nội dung mẫu.
2. Tạo lại đúng Pod thuộc Service TARGET_SERVICE do Deployment quản lý trong lúc lab đã dành cho thử nghiệm. Ghi UID cũ và UID mới; theo dõi readiness thay vì đợi số giây cố định. Một replica có thể có khoảng gián đoạn.
3. Xem EndpointSlice mới, đối chiếu targetRef với Pod mới. Gọi lại đúng URL từ cùng nguồn. IP Pod có thể được tái sử dụng; so UID và targetRef để nhận ra Pod mới. Kết quả đạt là tên/port/ClusterIP giữ nguyên và request thành công sau khi Ready.
4. Ca lỗi riêng: tạo Service thử tên service-selector-test trỏ nhãn không tồn tại. So EndpointSlice có zero endpoint với Service thật; điều chỉnh selector cho khớp, theo dõi endpoint xuất hiện rồi xóa Service thử. Không cần sửa Service đang phục vụ demo.
5. TV3 lặp ca thử sau khi áp chính sách. Ghi riêng DNS, kết nối TCP và kết quả HTTP. Nếu DNS vẫn hoạt động nhưng GET trực tiếp bị từ chối, mô hình phân tách quyền đang cho kết quả đúng ở lớp cần kiểm tra.

### 13.3. Bốn kiểu Service và một biến thể thường bị nhầm

**ClusterIP** cho các client trong cụm gọi tên nội bộ. **NodePort** mở cổng quy ước trên node và chuyển lưu lượng tới backend của Service. **LoadBalancer** mô tả nhu cầu cấp load balancer qua một bộ điều khiển tương thích. Với kubeadm trên VM trống, nhóm chủ động tạo LB của GCP và trỏ vào NodePort. **ExternalName** trả DNS alias cho một hostname khác. **Headless** là Service đặt clusterIP: None để DNS có thể trả endpoint trực tiếp, hữu ích khi ứng dụng cần định danh từng replica. Trong báo cáo, nhóm minh họa hai kiểu đã thực sự triển khai và chỉ ra khi nào ba trường hợp còn lại có ích. [Đặc tả Kubernetes Service](https://kubernetes.io/docs/concepts/services-networking/service/)

## 14. Tuần 2 · Từ NodePort đến một IP công khai

### 14.1. Triển khai theo từng chặng

| Ngày | Người làm | Công việc | Điều kiện đạt cuối ngày |
|---|---|---|---|
| 09/11 | TV2 + TV3 | Chọn đúng port entry HTTP của Service gateway; đặt nodePort=30080, externalTrafficPolicy=Cluster; giữ nguyên các port khác của chart và targetPort thật. Kiểm tra VirtualService, hosts và gateway binding. | Từ cp-01 thử cả wk-01:30080 và wk-02:30080 với /APP_PATH; trang trả nội dung đúng khi gateway Pod chỉ chạy trên một worker. |
| 10/11 | TV1 + TV2 | Tạo unmanaged instance group cùng zone và thêm hai worker hiện có. Dành regional external IP, TCP health check port 30080, regional backend service loại EXTERNAL và gắn group. Áp firewall đúng target/tag của worker. | Ghi tên group, backend, IP, cổng và trạng thái health của từng backend. |
| 11/11 | TV1 + TV3 | Tạo regional forwarding rule TCP 30080 trỏ backend service. Cho phép IP client trình chiếu theo thiết kế. Từ mạng ngoài VPC kiểm tra HTTP, giao diện đầy đủ, nội dung kiểm thử, đồng thời tìm traffic vào gateway trên Kiali. | Có ảnh backend healthy, URL và thời điểm thử ngoài VPC. Có thể giải thích nguồn/đích từng chặng. |
| 12/11 | TV1 + TV3 | Cài hoặc hoàn thiện Rancher và TLS, kiểm tra resource sau khi thêm dashboard. TV2 kiểm tra route public sau thay đổi ingress quản trị. | Tài khoản chỉ đọc nhìn thấy cụm; website vẫn dùng IP công khai đã dành. |
| 13/11 | Cả nhóm | Người không cấu hình LB lặp phép thử. Đóng gói inventory, YAML, diagram và runbook; thử một tình huống lỗi trên route thử. | Chốt M2 và danh sách lỗi Service cần tái hiện trong tuần 3–4. |

### 14.2. Cách đọc kết quả khi mất truy cập

- **Port-forward tới gateway hoạt động, NodePort trên cả hai worker hỏng.** Xem Service type, nodePort, EndpointSlice của gateway, externalTrafficPolicy, firewall nội bộ, kube-proxy và route. Chỉ chuyển sang sửa cloud LB sau khi gọi được qua node.
- **Backend unhealthy.** Kiểm tra health check đúng loại/protocol/port, nguồn probe theo tài liệu của loại LB, tag gắn trên worker và firewall host. Xem group có đúng hai VM. TCP health check chỉ kiểm tra kết nối cổng; website và policy phải được thử riêng.
- **NodePort hoạt động, LB healthy nhưng browser timeout.** Đối chiếu region, frontend IP đã đặt, cổng forwarding rule, IP nguồn thực của client sau NAT và rule cho client. Ghi lỗi và thử cùng URL ngoài VPC; dùng một IP worker trực tiếp sẽ bỏ qua LB.
- **Nhận 404 hoặc 503 từ gateway.** 404: so Host header, path, gateway selector và VirtualService; 503: xem upstream endpoint, readiness, destination port và chính sách mTLS. Lưu proxy access log cạnh lệnh curl đã dùng.
- **Khôi phục sau thay đổi.** Quay lại manifest gateway tốt gần nhất trong Git và deploy lại. Nếu lỗi ở forwarding rule/firewall, khôi phục đúng tài nguyên đang lỗi, kiểm tra lần lượt node rồi frontend. Giữ IP dành riêng trong buổi nghiệm thu để URL không thay đổi. [Thiết lập external passthrough Network Load Balancer](https://cloud.google.com/load-balancing/docs/network/setting-up-network-backend-service)

## 15. Rancher, quyền người dùng và tài nguyên ổ đĩa

### 15.1. Rancher quản trị cụm nào?

Mô hình lab đặt Rancher Server trên chính cụm ba VM; cụm này hiện dưới tên local của Rancher. TV1 ghi rõ tên Kubernetes context, cluster ID và ba node để tránh trình bày nhầm một cụm khác. Kiểm tra ma trận hỗ trợ Rancher/Kubernetes trước khi cài. Một replica là lựa chọn lab; chi phí CPU/RAM và phụ thuộc chứng chỉ phải được tính từ đầu.

1. **Đường vào quản trị.** Chọn hostname mà laptop quản trị và agent trong cụm đều phân giải, ví dụ rancher.lab.example dưới miền nhóm kiểm soát. Cấu hình ingress class nội bộ riêng cho Rancher; không tạo thêm public LB. Kiểm tra route từ cả laptop và một Pod trước khi cài chart.
2. **TLS.** Chọn một cách cấp chứng chỉ tương thích với chart. Nếu dùng CA riêng, cài trust chain cho client và Rancher agent. Nếu dùng cơ chế cần cert-manager, đợi controller và webhook sẵn sàng trước khi tạo release. Lưu public CA và cấu hình; private key để ngoài Git.
3. **Triển khai.** Tạo cattle-system, cài chart đã ghim, truyền hostname, số replica và loại TLS. Kiểm tra deployment rollout, ingress address/class và secret TLS. Theo dõi log agent/controller nếu UI mở nhưng báo cluster disconnected.
4. **Ủy quyền.** Một tài khoản vận hành cài đặt; một tài khoản chỉ xem dùng khi trình chiếu. Chạy thử thao tác đọc và xác nhận tài khoản xem không được sửa workload. Ghi sơ đồ quyền Google IAM → SSH → Kubernetes RBAC → Rancher role.
5. **Nghiệm thu.** Người kiểm tra chéo đăng nhập lại, mở đúng local cluster, ba node, namespace APP_NAMESPACE, một Deployment và Service. Nếu dashboard tuần đầu là Headlamp, ghi rõ ngày chuyển sang Rancher và giữ bằng chứng M1 độc lập.

### 15.2. Dùng Rancher để truy vết Service

TV1 chọn namespace APP_NAMESPACE và mở Service TARGET_SERVICE, TV2 đọc selector và cổng của nó, TV3 đối chiếu với Pod Ready và EndpointSlice từ kubectl. Chụp hai ảnh cùng thời điểm để chứng minh giao diện và API đang mô tả cùng một backend. Thay một Pod, đợi Pod mới Ready rồi lặp lại. Khi báo cáo, mở trang mẫu để tạo request và dành phần trình bày cho dữ liệu quan sát được của Service.

## 16. Tuần 3 · Cấu hình bảo mật và kiểm chứng từng lớp

### 16.1. Xác minh đầu vào của policy

TV2 ghi namespace, label app, ServiceAccount, tên cổng HTTP và trust domain từ cấu hình thực. Kiểm tra target workload có sidecar, proxy đã SYNCED và hai nguồn phát request thực sự là Pod CALLER_DEPLOYMENT và ENTRY_SERVICE. Chạy GET trong container có curl hoặc debug container cùng Pod. Không dùng một Pod curl mới với ServiceAccount mặc định rồi kết luận danh tính CALLER_SERVICE bị chặn.

```sh
kubectl -n APP_NAMESPACE get pods -L app,version
kubectl -n APP_NAMESPACE get deploy CALLER_DEPLOYMENT -o jsonpath='{.spec.template.spec.serviceAccountName}'
kubectl -n APP_NAMESPACE get svc TARGET_SERVICE -o yaml
kubectl get authorizationpolicy,peerauthentication -A
kubectl get networkpolicy -A
istioctl proxy-status
```

Dưới đây là ba manifest **cho ba lần áp dụng có kiểm soát**. Lưu từng resource vào một file riêng. Ví dụ dùng trust domain cluster.local và ServiceAccount CALLER_SERVICE_ACCOUNT theo thông tin TV2 bàn giao; cập nhật nếu đầu ra thực khác. Selector bảo vệ Pod đích TARGET_SERVICE. Giữ cùng cấu hình PeerAuthentication trong cả bốn ca C1–C4.

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: TARGET_SERVICE-strict
  namespace: APP_NAMESPACE
spec:
  selector:
    matchLabels:
      app: TARGET_LABEL
  mtls:
    mode: STRICT
---
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: TARGET_SERVICE-from-CALLER_SERVICE
  namespace: APP_NAMESPACE
spec:
  selector:
    matchLabels:
      app: TARGET_LABEL
  action: ALLOW
  rules:
    - from:
        - source:
            principals: ["cluster.local/ns/APP_NAMESPACE/sa/CALLER_SERVICE_ACCOUNT"]
      to:
        - operation:
            methods: ["GET"]
            paths: ["/TEST_PATH"]
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: TARGET_SERVICE-ingress
  namespace: APP_NAMESPACE
spec:
  podSelector:
    matchLabels:
      app: TARGET_LABEL
  policyTypes: [Ingress]
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: CALLER_LABEL
      ports:
        - protocol: TCP
          port: SERVICE_PORT
```

**Phạm vi đường dẫn được phép.** TEST_PATH là endpoint do TV2 bàn giao. Chọn đúng method/path cần cho nghiệp vụ đã thử và ghi kết quả đối chứng. NetworkPolicy dùng nhãn thực của Pod nguồn/đích. Xác nhận mTLS và principal trước khi thử phân quyền. [Istio HTTP authorization](https://istio.io/latest/docs/tasks/security/authorization/authz-http/)

### 16.2. Lịch thí nghiệm và tiêu chí diễn giải

| Ngày | Ai làm | Thử nghiệm | Phải lưu |
|---|---|---|---|
| 16/11 | TV1 kiểm tra, TV2 cấu hình | Bật STRICT, giữ cả hai nguồn được phép. Gửi mỗi nguồn 3 lần đến cùng URL. | DNS, HTTP 200, payload, timestamp, ServiceAccount và bằng chứng TLS. |
| 17/11 | TV2 làm, TV3 thử lại | Chỉ áp AuthorizationPolicy. Thử CALLER_SERVICE đúng method/path; ENTRY_SERVICE cùng method/path; thêm một path khác từ CALLER_SERVICE. | 200 cho yêu cầu hợp lệ; 403 và log RBAC cho lời gọi sai danh tính hoặc đường dẫn. Gỡ đúng resource rồi chạy đối chứng lại. |
| 18/11 | TV3 làm, TV1 thử lại | Chỉ áp NetworkPolicy. Thử GET qua tên Service với timeout hữu hạn từ cả hai nguồn; thử DNS riêng. | Một nguồn qua được; nguồn bị chặn có lỗi kết nối hoặc lỗi upstream từ proxy nguồn. Đối chiếu khi bỏ policy và khi khôi phục lại. |
| 19/11 | Cả nhóm | Bật cả hai policy và gọi lại website ngoài VPC. Kiểm tra bằng curl trực tiếp và bằng giao diện trả nội dung đúng. | Bảng C1–C4 có đủ trường hợp tốt/xấu. Kiali có luồng CALLER_SERVICE → TARGET_SERVICE sau khi thêm policy. |
| 20/11 | TV1 điều phối | Đổi người thực hiện, lặp một ca từ runbook. Nếu còn thời gian, tạo subset của hai phiên bản được chọn, route 80/20 rồi hoàn tác. | Lưu phân bố thực nghiệm, số request, version, thời gian và cấu hình sau rollback. |

**Cách ghi lỗi đúng lớp.** Dùng `curl -sv --connect-timeout 3 --max-time 8 http://TARGET_SERVICE:SERVICE_PORT/TEST_PATH` từ Pod nguồn, lưu cả stderr và mã thoát. 403 cần đối chiếu log Envoy đích. Với NetworkPolicy, HTTP 503 phát bởi proxy nguồn cũng có thể xuất hiện nếu upstream không kết nối được; không đòi mọi môi trường đều hiện đúng chữ “timeout”. Kết luận dựa trên ca đối chứng và thay đổi duy nhất. Đồ thị thiếu cạnh chỉ gợi ý nơi kiểm tra, không chứng minh quyền truy cập bị từ chối.

### 16.3. Nếu làm traffic splitting

TV2 triển khai CALLER_SECOND_VERSION, khai báo DestinationRule cho host CALLER_SERVICE với hai subset theo version; VirtualService nội bộ CALLER_SERVICE gửi 80% tới phiên bản ban đầu và 20% tới phiên bản thử. Giữ route ingress vào ENTRY_SERVICE. TV3 gửi ví dụ 200 request, đếm request theo destination version từ telemetry và ghi khoảng quan sát. Mục tiêu là hai version nhận traffic với xu hướng phù hợp; mẫu đo không cần đúng tuyệt đối 160/40. Trả route về phiên bản ban đầu trước khi scale phiên bản thử xuống. Lặp GET qua trang public và ca C4 để xác nhận rollback không làm mất luồng được phép.

## 17. Tuần 4 · Phòng thực hành Kubernetes Service và bảo vệ

### 17.1. Ba phép thử trên một workload có sẵn

1. **DNS và phạm vi namespace.** Từ Pod client trong APP_NAMESPACE, gọi TARGET_SERVICE:SERVICE_PORT. Từ Pod client ở namespace thử, gọi TARGET_SERVICE.APP_NAMESPACE:SERVICE_PORT. Để tách discovery khỏi authorization, kiểm tra phân giải tên riêng, sau đó thực hiện HTTP từ nguồn được phép. Ghi kết quả DNS, ClusterIP và hostname sử dụng.
2. **Một tên cho nhiều backend.** TV2 ghi số replica ban đầu của TARGET_SERVICE, scale lên 2, đợi rollout thành công. TV3 quan sát EndpointSlice và targetRef để nhận diện cả hai Pod. Gọi cùng tên Service rồi đưa replica về trạng thái ban đầu. Kết quả cần chứng minh là tập endpoint thay đổi trong khi tên và ClusterIP ổn định; một vài response giống nhau chưa chứng minh phân phối tải đều.
3. **Tên tồn tại, endpoint trống.** TV3 tạo Service thử cùng namespace, dùng selector không khớp, quan sát DNS có kết quả trong khi chưa có backend. Sửa selector về app=TARGET_LABEL, đợi endpoint Ready rồi gọi lại. Dùng nguồn được phép và ghi policy đang bật để tránh nhầm lỗi selector với lỗi phân quyền.

### 17.2. Thử nghiệm người khác có thể chạy lại

- **TV1** đứng ở máy ngoài VPC, ghi IP frontend, cổng và URL. Đối chiếu forwarding rule với NodePort của gateway và endpoint gateway đang Ready.
- **TV2** đứng trong cụm, lưu tên DNS, selector, port/targetPort, UID Pod, EndpointSlice trước/sau mỗi thay đổi. Ghi lại lệnh khôi phục replica và xóa riêng Service thử.
- **TV3** phát traffic và gắn timestamp vào ảnh Kiali. So sánh trường hợp endpoint trống với trường hợp có endpoint nhưng Istio từ chối. Bàn giao một cặp kết quả có thể dùng để hỏi đáp.

### 17.3. Lịch chốt công việc

- **23/11:** TV1 xác nhận đường public và dashboard; TV2 chuẩn bị Service thử; TV3 ghi trạng thái đối chứng.
- **24/11:** chạy ca thay replica và selector sai, đổi người khắc phục, trả cluster về trạng thái ban đầu.
- **25/11:** thử lại đường public và bốn ca phân quyền. Ghi kết quả thực tế, cấu hình áp dụng và giới hạn quan sát.
- **26/11:** một thành viên khác chạy lại từ repo. Sửa sơ đồ theo IP/port thực, khóa commit và tập phần hỏi đáp.
- **27/11:** demo trực tiếp, lưu bằng chứng và thu hồi tài nguyên theo mục 20.

## 18. Sổ kiểm thử dùng chung cho cả nhóm

Đặt mã test vào tên log/ảnh để từ báo cáo lần ngược được về đúng lần chạy. Ví dụ `M3-SEC02_20261117_CALLER_SERVICE-to-TARGET_SERVICE`. Mỗi bản ghi có commit, phiên bản, thời điểm, người chạy, nguồn/đích, điều kiện trước test, lệnh, kết quả mong đợi, kết quả thực, bằng chứng và thao tác hoàn tác. Ban đầu để trạng thái **Chưa chạy**.

| ID | Điều kiện và thao tác | Pass khi | Chủ trì / kiểm tra |
|---|---|---|---|
| INF01 | Mở console và get nodes -o wide | Khớp đủ tên, vai trò, InternalIP của ba VM | TV1 / TV2 |
| NET01 | Client và HTTP server đặt trên hai worker; gọi theo IP và DNS | Cả hai cách gọi thành công, vị trí hai Pod khác node | TV3 / TV2 |
| IAM01 | Dùng tài khoản trình chiếu đọc node và thử quyền sửa Deployment | Đọc được dữ liệu cần demo, phép sửa bị từ chối | TV1 / TV3 |
| SVC01 | Ghi cổng, selector, Pod label, EndpointSlice của TARGET_SERVICE | Chỉ được ít nhất một endpoint Ready có đúng nhãn và targetRef | TV2 / TV1 |
| SVC02 | Tạo lại Pod thuộc Service TARGET_SERVICE và gọi lại khi Ready | Cùng tên Service hoạt động; UID Pod mới được chứng minh | TV2 / TV3 |
| APP01 | Qua gateway vào /APP_PATH | Có nội dung theo tiêu chí TV2 bàn giao, các Pod có proxy Ready | TV2 / TV1 |
| OBS01 | Tạo traffic, xem series và Kiali graph | Có cạnh CALLER_DEPLOYMENT → TARGET_SERVICE và metric cùng khoảng thời gian | TV3 / TV1 |
| PUB01 | Browser ngoài VPC mở frontend LB | Thấy trang và nội dung đúng; backend healthy và IP dùng là IP frontend | TV1 / TV3 |
| ADM01 | Đăng nhập Rancher bằng user chỉ đọc | Thấy đủ node và workload, quyền phù hợp | TV1 / TV2 |
| SEC01 | Hai nguồn gọi cùng TARGET_SERVICE khi chỉ STRICT | Hai lượt 200; ghi bằng chứng mTLS | TV2 / TV3 |
| SEC02 | Chỉ áp luật Istio | CALLER_SERVICE 200, ENTRY_SERVICE 403 và có dấu vết từ chối RBAC | TV2 / TV1 |
| SEC03 | Chỉ áp luật Calico NetworkPolicy | CALLER_SERVICE truy cập được, nguồn sai thất bại; phục hồi sau khi gỡ | TV3 / TV1 |
| SEC04 | Bật cả hai lớp, thử website và truy cập trực tiếp | Trang vẫn trả nội dung đúng và ENTRY_SERVICE không gọi thẳng được TARGET_SERVICE | TV1 / TV2 |
| SVC03 | Scale TARGET_SERVICE, đợi tất cả replica Ready | EndpointSlice phản ánh tập Pod sau thay đổi, client gọi được cùng tên | TV2 / TV3 |
| SVC04 | Service thử có selector sai, sau đó sửa đúng | DNS phân giải trước/sau; endpoint xuất hiện và caller hợp lệ nhận 200 sau khi sửa | TV3 / TV1 |
| OPS01 | Thành viên khác mở dashboard và chạy lại demo từ repo | Tái hiện luồng bằng hướng dẫn, mọi sai khác được ghi nhận | Cả nhóm |

**Tiêu chí báo cáo trung thực.** Không dùng ảnh màn hình thay cho kết quả âm tính của policy. Nếu ca test chưa chạy, để Chưa chạy. Nếu lỗi môi trường, ghi Bị chặn và bước khắc phục cụ thể. Nếu rubric cho phép bỏ một mục, ghi Không áp dụng kèm quyết định và ngày xác nhận.

## 19. Khắc phục sự cố theo lớp

| Triệu chứng | Kiểm tra đầu tiên | Phân biệt nguyên nhân và bước tiếp |
|---|---|---|
| kubectl timeout hoặc lỗi x509 | Kiểm tra context, tunnel, CA, TLS server name và thời gian hệ thống | Timeout thường liên quan reachability; x509 cần đối chiếu SAN/CA và credential, giữ xác minh TLS bật. |
| Worker NotReady | describe node, journal kubelet, Pod Calico | Kiểm tra IP pool và CNI config. Nếu cả image pull cũng lỗi, kiểm tra egress/registry trước. |
| Pod Pending | describe pod, FailedScheduling, taint và allocatable | Thiếu RAM/CPU thì đo requests và dời add-on tùy chọn; PVC chưa Bound thì xử lý StorageClass/volume. |
| Pod Running nhưng Service không có endpoint Ready | Selector, namespace, Pod label, readiness, EndpointSlice | So đúng cổng của ứng dụng; tên Service tồn tại không đảm bảo backend đã Ready. |
| Pod không có istio-proxy | Namespace label, revision và thời điểm Pod được tạo | Kiểm tra injector/webhook, rollout lại đúng Deployment và chờ Ready. |
| Gateway trả 503 | Envoy access log, upstream endpoint, mTLS và DNS | Test cùng Service từ nguồn được phép; đối chiếu policy vừa thay đổi. |
| Kiali không có cạnh | Traffic, Prometheus target/series, nhãn app/version và cửa sổ thời gian | Truy vấn trực tiếp Prometheus; dashboard không tự sinh lưu lượng. |
| Luôn 200 dù đã tạo AuthorizationPolicy | Namespace và selector đích, workload có proxy, principal nguồn, policy khác | Đối chiếu ServiceAccount thật, kiểm tra luật được Istiod phân phối và có tác dụng ở proxy đích. |
| Sau NetworkPolicy mọi request lỗi | Nhãn nguồn, port đích, policy cộng dồn, CNI | Tạm khôi phục từng manifest trên lab, chạy C1; giữ policy đúng và thu log từ cả hai nguồn. |
| Rancher login được nhưng mất kết nối agent | Hostname, DNS nội bộ, TLS/CA và ingress class | Kiểm tra từ Pod agent tới server URL, rồi mới kiểm tra quyền viewer. |
| Worker reboot, workload chưa hồi phục | Trạng thái node, runtime, CNI, controller, volume và readiness | Khôi phục theo thứ tự node → mạng → Pod → Service → mesh. Chỉ ghi phục hồi khi request end-to-end đạt. |

## 20. Chi phí, bàn giao và câu hỏi bảo vệ

### 20.1. Bảng dự toán cần điền

| Khoản | Cách tính cho lab | Thời điểm kiểm tra |
|---|---|---|
| Compute | Giá theo vùng và loại máy × giờ chạy của từng VM | Trước cấp VM, sau khi thêm dashboard, trước tuần demo |
| Disk | GB-tháng cho 20 + 30 + 30 GB, cộng volume và snapshot nếu dùng | Sau khi dừng/xóa VM, kiểm tra disk rời |
| Network | IP ngoài, forwarding rule/LB, traffic, NAT nếu đã chọn | Khi bật đường public và sau khi dọn |
| Tổng thực tế | Ghi project/nhãn, khoảng ngày, số liệu Billing và chênh lệch với dự toán | Mỗi cuối tuần, kiểm tra lại sau khi dọn do billing cập nhật trễ |

Dừng VM có thể giảm phí compute nhưng disk, IP, LB và tài nguyên khác có thể vẫn tính phí. Lưu chứng cứ bên ngoài VM. Khi kết thúc, kiểm kê forwarding rule, backend service, health check, group, address, VM, disk, snapshot, NAT của **riêng lab**; đánh dấu tài nguyên nào được phép xóa hoặc cần giữ. Đối chiếu inventory sau cleanup và lưu ngày hoàn thành.

### 20.2. Hồ sơ phục hồi

- **Mất Pod:** Deployment tạo lại Pod. Xác nhận readiness và EndpointSlice; dùng SVC02 làm bằng chứng.
- **Mất worker:** xác minh worker còn lại có chỗ cho workload. Đợi điều kiện lập lịch và volume attach, thử website. Nếu lab chỉ có một replica hoặc thiếu tài nguyên thì ghi khoảng gián đoạn thực.
- **Mất control plane:** cụm lab chỉ có một control plane. Lập phương án sao lưu snapshot etcd bằng công cụ đúng phiên bản, giữ PKI và cấu hình kubeadm an toàn bên ngoài VM. Ghi checksum, ngày và cách khôi phục trong lab riêng. Ghi riêng mục tiêu thời gian phục hồi với thời gian đã đo.

### 20.3. Bộ câu hỏi để ba người đổi phần diễn tập

1. Từ console, làm thế nào chứng minh ba VM đã gia nhập cùng một cluster? Chỉ bằng chứng ở tầng hạ tầng, API và workload.
2. Khi thay Pod thuộc Service TARGET_SERVICE, client tiếp tục dùng tên cũ bằng cách nào? Nếu IP Pod tái sử dụng, bằng chứng nào cho thấy Pod đã đổi?
3. Nếu NodePort của gateway chạy nhưng URL public hỏng, nhóm sẽ kiểm tra thành phần nào tiếp theo? Vì sao backend healthy vẫn chưa đủ kết luận website chạy đúng?
4. Vì sao ENTRY_SERVICE vẫn tra được tên TARGET_SERVICE nhưng gọi bị chặn? Phân biệt bằng chứng từ RBAC của Envoy và phép thử chỉ có NetworkPolicy.
5. Kiali dựa vào dữ liệu nào, và tại sao vừa mở dashboard có thể chưa thấy cạnh? Chỉ cửa sổ thời gian và traffic thực ngay trong demo.
6. Ai xử lý nếu control plane mất, phần nào được lấy lại từ Git, phần nào cần snapshot etcd và bản sao cấu hình? Giải thích giới hạn của lab một control plane bằng tình huống đã kiểm thử.

**Bộ hồ sơ cuối:** một sơ đồ tài nguyên có IP/port thực; một bảng phiên bản; manifest có thứ tự apply/rollback; inventory cloud; test log theo mã; tài liệu vận hành; chi phí; slide demo có chú thích đã chạy/chưa chạy. Mỗi người ký xác nhận phần tự triển khai và một phần đã tái hiện của thành viên khác.

## 21. Phiếu thao tác cho người trực tiếp mở dashboard

### 21.1. Cài Headlamp và thử quyền xem

Trên máy quản trị có Helm và kubeconfig, TV1 chạy các bước dưới đây. Thay phiên bản chart bằng bản đã chọn ngày 1. Với mục tiêu tuần đầu dùng Headlamp; nếu nhóm chuyển sang Rancher sớm thì bỏ qua nhánh này.

```sh
helm repo add headlamp https://kubernetes-sigs.github.io/headlamp/
helm repo update
helm search repo headlamp/headlamp --versions
helm upgrade --install headlamp headlamp/headlamp -n headlamp --create-namespace --version <chart-version>
kubectl -n headlamp get deployments,svc,pods
kubectl -n headlamp create serviceaccount demo-viewer
```

Ví dụ dưới đây dùng quyền xem node ở toàn cụm và quyền xem workload chỉ trong namespace APP_NAMESPACE. Thực hiện khi namespace APP_NAMESPACE đã tồn tại. Tạo role/binding một lần rồi xuất YAML vào repo để lần dựng lại có thể dùng apply; lệnh create sẽ báo AlreadyExists nếu đối tượng đã có.

```sh
kubectl create clusterrole nt132-view-nodes --verb=get,list,watch --resource=nodes,namespaces
kubectl create clusterrolebinding nt132-view-nodes --clusterrole=nt132-view-nodes --serviceaccount=headlamp:demo-viewer
kubectl -n APP_NAMESPACE create role nt132-view-app --verb=get,list,watch --resource=pods,services,deployments.apps,replicasets.apps,endpointslices.discovery.k8s.io
kubectl -n APP_NAMESPACE create rolebinding nt132-view-app --role=nt132-view-app --serviceaccount=headlamp:demo-viewer
kubectl auth can-i list nodes --as=system:serviceaccount:headlamp:demo-viewer
kubectl auth can-i patch deployments.apps -n APP_NAMESPACE --as=system:serviceaccount:headlamp:demo-viewer
kubectl -n headlamp create token demo-viewer --duration=1h
kubectl -n headlamp port-forward svc/headlamp 8081:80
```

Hai lần kiểm tra quyền phải trả **yes** cho list nodes và **no** cho patch deployment. Token chỉ dùng để đăng nhập vào UI trong buổi làm việc. Nếu UI truy vấn tài nguyên ở phạm vi toàn cụm mà tài khoản chỉ có quyền trong APP_NAMESPACE, chọn namespace APP_NAMESPACE rồi thử lại. Kiểm tra API bị từ chối trước khi bổ sung từng quyền đọc thực sự cần thiết. [Cài Headlamp trong cluster](https://headlamp.dev/docs/latest/installation/in-cluster/)

### 21.2. Checklist mở lớp học hoặc phòng báo cáo mới

| Ai | Kiểm tra ngay tại phòng | Nếu kết quả khác buổi diễn tập |
|---|---|---|
| TV1 | Xác nhận IP nguồn quản trị được phép, SSH/tunnel và kubectl còn hoạt động, token xem còn hạn | Làm mới danh tính hoặc cập nhật đúng IP nguồn của nhóm. Không mở API công khai chỉ để xử lý lỗi mạng phòng học. |
| TV2 | Chạy port-forward gateway, mở /APP_PATH và gọi lại TARGET_SERVICE từ Pod đã được phép | Kiểm tra Pod Ready, Service có endpoint, gateway revision và terminal tunnel chưa đóng. |
| TV3 | Sinh traffic, mở graph 5 phút và xem cạnh có request mới | Mở Prometheus kiểm tra series; nếu graph chưa có mẫu, tiếp tục tạo traffic trong lúc TV1 trình bày. |
| Cả nhóm | Đối chiếu sơ đồ chiếu với node/namespace đang hiện; đặt sẵn log của hai phép thử trái chiều | Nếu dùng ảnh hoặc video dự phòng, ghi thời điểm chạy và tách khỏi trạng thái trực tiếp. |

### 21.3. Mẫu ghi một kết quả để người khác chạy lại

```text
Mã test / mốc:
Người chạy / người kiểm tra:
Commit, version, context, namespace:
Thời điểm và múi giờ:
Trạng thái đầu (node, workload, policy):
Nguồn gọi, ServiceAccount, đích, cổng và đường dẫn:
Lệnh hoặc thao tác:
Kỳ vọng:
Kết quả thực tế / mã HTTP / nội dung lỗi:
Đường dẫn ảnh, log, YAML trước và sau:
Thao tác khôi phục / kết quả kiểm tra sau khôi phục:
Kết luận: Đạt | Chưa đạt | Bị chặn | Chưa chạy
```
