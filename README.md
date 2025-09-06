Trong 6 tuần đầu tiên, cần xây dựng hệ thống với 4 workload cơ bản bao gồm :

- os: centos và ubuntu 24:04
- big data : elatishsearch
- database : oracle
- app : ứng dụng có cả frontend và backend

design ui https://app.diagrams.net/#G1qMtekx-roHUi23HPZPT9qTDaoYVbXET_#%7B%22pageId%22%3A%22R9SdJvhcUGw88E1eOVfx%22%7D
backend : this repo
frontend : https://github.com/Maybetuandat/hardening_vtnet_fe
Công việc hoàn thành hết ngày 14/08/2025:

- xây dựng xong giao diện và mô hình hóa Workload, server
  Công việc còn lại:
- thực hiện thêm server bằng file , cho sẵn template , khi thêm server thì nhớ có nút test connection
- bắt sự kiện cho nút scan, nút export report
- thêm giao diện cho chi tiết hardening. sẽ bao gồm danh sách các lần hardening, và chi tiết lần hardening đó
- upload Security Standard bằng file, cho sẵn template
- update search ở backend, hiện tại search đang ở frontend
  | A: STT | B: Name | C: Description | D: Severity | E: Category | F: Parameters_JSON | G: Is_Active |
  |--------|---------|----------------|-------------|-------------|-------------------|-------------|
  | 1 | file-max | Giới hạn tối đa... | medium | System | {"default_value": "9223372036854775807", "recommended_value": "5000000", "note": "Check lại con số này", "docs": "file-max-docs"} | true |
  | 2 | net.ipv4.tcp_rmem | Tham số quy định... | high | Network | {"min": 4096, "default": 87380, "max": 87380, "unit": "byte", "range": "4096-6291456", "recommended": "4096 87380 56623104"} | true |

- con mot loai tham so nua la tra ve ucredit=-1, dcredit=-1, ...
- Lý thuyết về cách hoạt động của crontab service:
  thư viện sư dụng: Apscheduler là một thư viện cho phép đặt lịch thực thi hàm tác vụ theo thời gian định trước
  có 3 thành phần chính:
- Scheduler: Blocking Scheduler: khi khởi chạy sẽ chặn main thread
  BackgroundScheduler: chạy ở nền
  AsyncIOScheduler: asynce
- trigger có 3 điều kiện chạy:
  DateTrigger: chạy vào một thời điểm cụ thể
  IntervalTrigger: chạy lặp lại theo khoảng thời gian
  CrontabTrigger: chạy giống crontab
- Khi thêm job, có thể gán:

id: định danh duy nhất.

misfire_grace_time: thời gian cho phép bù nếu lỡ giờ.

max_instances: số lần chạy song song tối đa.

coalesce: gộp nhiều lần chạy bị bỏ lỡ thành một lần.

- nhớ trong kiến trúc code. các hàm thao tác ở dao như crud chỉ thực hiện việc crud thôi, không thêm logic
- các logic code sẽ nằm hết ở service đê dễ dàng trong việc bảo trì và thiết kế
