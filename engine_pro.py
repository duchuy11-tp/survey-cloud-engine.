import os
import sys
import json
import time
import random
import requests

# =====================================================================
# 1. ĐỌC THAM SỐ TỪ GITHUB ACTIONS & QUÉT FILE CẤU HÌNH
# =====================================================================
INPUT_CONFIG = os.getenv("CLIENT_CONFIG", "VIMC_Logistics_NhuY_220.json").strip()
START_INDEX = int(os.getenv("START_INDEX", "0"))
END_INDEX = int(os.getenv("END_INDEX", "31"))
MIN_DELAY = int(os.getenv("MIN_DELAY", "220"))
MAX_DELAY = int(os.getenv("MAX_DELAY", "1040"))

if os.path.exists(os.path.join("clients", INPUT_CONFIG)):
    CONFIG_FILE = os.path.join("clients", INPUT_CONFIG)
elif os.path.exists(INPUT_CONFIG):
    CONFIG_FILE = INPUT_CONFIG
else:
    print(f"[LỖI] Không tìm thấy file: {INPUT_CONFIG} trong 'clients/' hoặc thư mục gốc", flush=True)
    sys.exit(1)

with open(CONFIG_FILE, "r", encoding="utf-8") as f:
    config = json.load(f)

RAW_URL = config.get("form_url", "").strip()
if "viewform" in RAW_URL:
    FORM_URL = RAW_URL.split("viewform")[0] + "formResponse"
elif not RAW_URL.endswith("formResponse"):
    FORM_URL = RAW_URL.rstrip("/") + "/formResponse"
else:
    FORM_URL = RAW_URL

CLIENT_NAME = config.get("client_name", "Khach_Hang")
PAGE_HISTORY = config.get("page_history", None)
FIXED_RESPONSES = config.get("fixed_responses", [])

if not FIXED_RESPONSES:
    print("[LỖI] File JSON không chứa mảng 'fixed_responses'.", flush=True)
    sys.exit(1)

if START_INDEX < 0 or END_INDEX >= len(FIXED_RESPONSES) or START_INDEX > END_INDEX:
    print(f"[LỖI] Dải Index {START_INDEX} -> {END_INDEX} không hợp lệ (tổng mảng: {len(FIXED_RESPONSES)}).", flush=True)
    sys.exit(1)

batch_to_run = FIXED_RESPONSES[START_INDEX : END_INDEX + 1]
total_in_batch = len(batch_to_run)

print("=" * 65, flush=True)
print("HỆ THỐNG ENGINE PRO - NẠP DỮ LIỆU CỐ ĐỊNH (FIXED REPLAY)", flush=True)
print(f"Khách hàng   : {CLIENT_NAME}", flush=True)
print(f"Dải Index    : {START_INDEX} -> {END_INDEX} (Số mẫu đợt này: {total_in_batch})", flush=True)
print(f"Giãn cách    : {MIN_DELAY}s - {MAX_DELAY}s", flush=True)
print("=" * 65, flush=True)

# =====================================================================
# 2. VÒNG LẶP ĐẨY TỪNG PHIẾU CỐ ĐỊNH LÊN GOOGLE FORMS
# =====================================================================
USER_AGENTS = [
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.6312.99 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
]

session = requests.Session()
success_count = 0
fail_count = 0

for i, item in enumerate(batch_to_run):
    batch_idx = item.get("batch_index", START_INDEX + i)
    csv_row_id = item.get("csv_row", "N/A")

    data_pairs = [("fvv", "1")]
    if PAGE_HISTORY is not None:
        data_pairs.append(("pageHistory", str(PAGE_HISTORY)))

    for entry_id, val in item.get("payload", {}).items():
        if isinstance(val, list):
            for v in val:
                data_pairs.append((entry_id, str(v)))
        else:
            data_pairs.append((entry_id, str(val)))

    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Content-Type": "application/x-www-form-urlencoded"
    }

    now_str = time.strftime("%H:%M:%S")
    try:
        res = session.post(FORM_URL, data=data_pairs, headers=headers, timeout=20)
        if res.status_code == 200:
            success_count += 1
            print(f"[{i+1}/{total_in_batch}] {now_str} | Thành công | Index #{batch_idx} (CSV dòng #{csv_row_id})", flush=True)
        else:
            fail_count += 1
            print(f"[{i+1}/{total_in_batch}] {now_str} | Lỗi HTTP {res.status_code} | Index #{batch_idx}", flush=True)
    except requests.RequestException as e:
        fail_count += 1
        print(f"[{i+1}/{total_in_batch}] {now_str} | Lỗi mạng: {e}", flush=True)

    if i < total_in_batch - 1:
        sleep_sec = random.uniform(MIN_DELAY, MAX_DELAY)
        time.sleep(sleep_sec)

print("=" * 65, flush=True)
print(f"HOÀN TẤT ĐỢT CHẠY PRO: Thành công {success_count}/{total_in_batch} | Lỗi: {fail_count}", flush=True)
print("=" * 65, flush=True)
