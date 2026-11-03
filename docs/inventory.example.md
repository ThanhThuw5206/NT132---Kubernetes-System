# Inventory mẫu

Điền sau khi tạo tài nguyên thực. Thông số dưới đây là đề xuất từ kế hoạch.

| Tài nguyên | Tên | IP / vị trí | Người phụ trách | Trạng thái |
|---|---|---|---|---|
| Project | <PROJECT_ID> | Google Cloud | TV1 | Chưa điền |
| VPC | nt132-vpc | custom | TV1 | Chưa xác minh |
| Control plane | cp-01 | 10.20.0.10 | TV1 | Chưa xác minh |
| Worker | wk-01 | 10.20.0.11 | TV2 | Chưa xác minh |
| Worker | wk-02 | 10.20.0.12 | TV3 | Chưa xác minh |
| Public LB | nt132-web-forward | <PUBLIC_IP>:30080 | TV1 | Chưa xác minh |

Ghi version thực của OS, containerd, Kubernetes, Calico, Istio, Rancher và Helm trong phiên bản inventory nhóm dùng. Ghi ngày kiểm tra, region/zone, commit manifest và kết quả nghiệm thu. Giữ credential ngoài tài liệu này.
