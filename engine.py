import os
import sys
import json
import time
import random
import requests
import numpy as np

# =====================================================================
# 1. ĐỌC THAM SỐ TỪ GITHUB ACTIONS & FILE CẤU HÌNH JSON
# =====================================================================
CONFIG_FILE = os.getenv("CLIENT_CONFIG", "client_sample.json")
BATCH_SAMPLES = int(os.getenv("BATCH_SAMPLES", "30"))
MIN_DELAY = int(os.getenv("MIN_DELAY", "20"))
MAX_DELAY = int(os.getenv("MAX_DELAY", "60"))

if not os.path.exists(CONFIG_FILE):
    print(f"[LỖI] Không tìm thấy file cấu hình: {CONFIG_FILE}")
    sys.exit(1)

with open(CONFIG_FILE, "r", encoding="utf-8") as f:
    config = json.load(f)

# Chuẩn hóa link Google Form sang đuôi /formResponse
RAW_URL = config.get("form_url", "").strip()
if "viewform" in RAW_URL:
    FORM_URL = RAW_URL.split("viewform")[0] + "formResponse"
elif not RAW_URL.endswith("formResponse"):
    FORM_URL = RAW_URL.rstrip("/") + "/formResponse"
else:
    FORM_URL = RAW_URL

CLIENT_NAME = config.get("client_name", "Khach_Hang")
DEMOGRAPHICS = config.get("demographics", {})
X_VARS = config.get("independent_vars", {})
Y_VARS = config.get("dependent_var", {})

# Ánh xạ điểm 1-5 sang chữ hiển thị trên Form (Mặc định là "1", "2", "3", "4", "5")
LIKERT_LABELS = config.get("likert_labels", {
    "1": "1",
    "2": "2",
    "3": "3",
    "4": "4",
    "5": "5"
})

print("=" * 65)
print(f"HỆ THỐNG ENGINE SINH SỐ LIỆU KHẢO SÁT TỰ ĐỘNG")
print(f"Khách hàng       : {CLIENT_NAME}")
print(f"Số mẫu đợt này   : {BATCH_SAMPLES} mẫu | Giãn cách: {MIN_DELAY}s - {MAX_DELAY}s")
print(f"Biến nhân khẩu   : {len(DEMOGRAPHICS)} câu")
print(f"Biến độc lập (X) : {len(X_VARS)} nhóm | Biến phụ thuộc (Y): {len(Y_VARS)} nhóm")
print("=" * 65)

# =====================================================================
# 2. HÀM SINH NHÂN KHẨU HỌC THEO TỶ LỆ THỰC TẾ (WEIGHTED DEMOGRAPHICS)
# =====================================================================
def generate_demographics_payload():
    demo_payload = {}
    for entry_id, rules in DEMOGRAPHICS.items():
        options = rules.get("options", [])
        weights = rules.get("weights", [])
        is_checkbox = rules.get("is_checkbox", False)

        if not options:
            continue

        # Nếu là câu hỏi chọn nhiều đáp án (Checkbox)
        if is_checkbox:
            k = random.randint(1, min(3, len(options)))
            if weights and len(weights) == len(options):
                p = np.array(weights, dtype=float) / np.sum(weights)
                chosen = list(np.random.choice(options, size=k, replace=False, p=p))
            else:
                chosen = random.sample(options, k)
            demo_payload[entry_id] = chosen
        # Nếu là câu hỏi chọn 1 đáp án (Radio / Dropdown)
        else:
            if weights and len(weights) == len(options):
                chosen = random.choices(options, weights=weights, k=1)[0]
            else:
                chosen = random.choice(options)
            demo_payload[entry_id] = chosen

    return demo_payload

# =====================================================================
# 3. ĐỘNG CƠ TOÁN HỌC LIKERT (ALPHA ~ 0.78 - 0.84 | SIG < 0.05 | 3% RÁC)
# =====================================================================
def generate_likert_payload():
    likert_payload = {}
    roll = random.random()

    def map_label(score_int):
        return LIKERT_LABELS.get(str(score_int), str(score_int))

    # --- TRƯỜNG HỢP 1: DỮ LIỆU RÁC - NGƯỜI ĐIỀN BỪA (1.5%) ---
    if roll < 0.015:
        for entries in list(X_VARS.values()) + list(Y_VARS.values()):
            for entry_id in entries:
                likert_payload[entry_id] = map_label(random.randint(1, 5))
        return likert_payload, "RÁC (Điền ngẫu nhiên)"

    # --- TRƯỜNG HỢP 2: DỮ LIỆU RÁC - NGƯỜI KHÓ TÍNH / TIÊU CỰC (1.5%) ---
    elif roll < 0.030:
        for entries in list(X_VARS.values()) + list(Y_VARS.values()):
            for entry_id in entries:
                low_score = int(np.clip(np.round(np.random.normal(2.0, 0.6)), 1, 3))
                likert_payload[entry_id] = map_label(low_score)
        return likert_payload, "RÁC (Điểm thấp/Khó tính)"

    # --- TRƯỜNG HỢP 3: DỮ LIỆU CHUẨN MÔ HÌNH HỒI QUY (97%) ---
    # 3.1. Sinh nền chung nhẹ để giữ VIF < 1.5 (Không đa cộng tuyến)
    shared_base = np.random.normal(0, 0.40)

    latent_x = {}
    for x_code in X_VARS.keys():
        latent_x[x_code] = 0.50 * shared_base + np.random.normal(0, 0.75)

    # 3.2. Tính nhân tố phụ thuộc Y từ tổng tác động dương của các biến X
    # Chia trung bình theo căn bậc hai số lượng biến X để phương sai Y luôn ổn định dù có 3 hay 7 biến X
    num_x = max(1, len(X_VARS))
    scale_factor = 1.0 / np.sqrt(num_x / 3.0)
    effect_on_y = sum(random.uniform(0.26, 0.36) * scale_factor * latent_x[x] for x in X_VARS.keys())
    latent_y = effect_on_y + np.random.normal(0, 0.50)

    # 3.3. Sinh điểm chi tiết cho các biến độc lập X (Cronbach's Alpha ~ 0.78 - 0.83)
    for x_code, entries in X_VARS.items():
        base_factor = latent_x[x_code]
        for entry_id in entries:
            target_mean = random.uniform(3.60, 4.05)
            loading = random.uniform(0.62, 0.73)
            noise = np.random.normal(0, 0.50)

            raw_score = target_mean + loading * base_factor + noise
            final_score = int(np.clip(np.round(raw_score), 1, 5))
            likert_payload[entry_id] = map_label(final_score)

    # 3.4. Sinh điểm chi tiết cho biến phụ thuộc Y (Cronbach's Alpha ~ 0.80 - 0.84)
    for y_code, entries in Y_VARS.items():
        for entry_id in entries:
            target_mean = random.uniform(3.70, 4.15)
            loading = random.uniform(0.64, 0.75)
            noise = np.random.normal(0, 0.48)

            raw_score = target_mean + loading * latent_y + noise
            final_score = int(np.clip(np.round(raw_score), 1, 5))
            likert_payload[entry_id] = map_label(final_score)

    return likert_payload, "CHUẨN"

# =====================================================================
# 4. VÒNG LẶP GỬI FORM & GHI LOG TRỰC TIẾP
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

for i in range(1, BATCH_SAMPLES + 1):
    # Gộp phần Nhân khẩu học + Phần câu hỏi Likert
    full_payload = {}
    full_payload.update(generate_demographics_payload())
    likert_data, sample_type = generate_likert_payload()
    full_payload.update(likert_data)

    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Content-Type": "application/x-www-form-urlencoded"
    }

    now_str = time.strftime("%H:%M:%S")
    try:
        res = session.post(FORM_URL, data=full_payload, headers=headers, timeout=15)
        if res.status_code == 200:
            success_count += 1
            print(f"[{i}/{BATCH_SAMPLES}] {now_str} | Gửi thành công | Loại mẫu: {sample_type}")
        else:
            fail_count += 1
            print(f"[{i}/{BATCH_SAMPLES}] {now_str} | Lỗi HTTP {res.status_code} (Kiểm tra lại mã entry hoặc câu bắt buộc)")
    except requests.RequestException as e:
        fail_count += 1
        print(f"[{i}/{BATCH_SAMPLES}] {now_str} | Lỗi mạng: {e}")

    if i < BATCH_SAMPLES:
        sleep_sec = random.uniform(MIN_DELAY, MAX_DELAY)
        time.sleep(sleep_sec)

print("=" * 65)
print(f"HOÀN TẤT ĐỢT CHẠY: Thành công {success_count}/{BATCH_SAMPLES} | Lỗi: {fail_count}")
print("=" * 65)
