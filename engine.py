import os
import sys
import json
import time
import random
import requests
import numpy as np

# =====================================================================
# 1. ĐỌC THAM SỐ TỪ GITHUB ACTIONS & TỰ ĐỘNG QUÉT THƯ MỤC CLIENTS/
# =====================================================================
INPUT_CONFIG = os.getenv("CLIENT_CONFIG", "client_sample.json").strip()
BATCH_SAMPLES = int(os.getenv("BATCH_SAMPLES", "30"))
MIN_DELAY = int(os.getenv("MIN_DELAY", "20"))
MAX_DELAY = int(os.getenv("MAX_DELAY", "60"))

# Tự động tìm trong folder clients/ trước, nếu không có mới tìm ở thư mục gốc
if os.path.exists(os.path.join("clients", INPUT_CONFIG)):
    CONFIG_FILE = os.path.join("clients", INPUT_CONFIG)
elif os.path.exists(INPUT_CONFIG):
    CONFIG_FILE = INPUT_CONFIG
else:
    print(f"[LỖI] Không tìm thấy file: {INPUT_CONFIG} (đã quét cả thư mục 'clients/' và thư mục gốc)")
    sys.exit(1)

with open(CONFIG_FILE, "r", encoding="utf-8") as f:
    config = json.load(f)

PAGE_HISTORY = config.get("page_history", None)

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
# 3. ĐỘNG CƠ TOÁN HỌC LIKERT ĐA TẦNG (ALPHA ~ 0.78-0.86 | SIG < 0.05)
# =====================================================================
# Hồ sơ phân tầng tự động cho từng biến X để biểu đồ các biến KHÔNG BAO GIỜ giống nhau
AUTO_PROFILES = [
    {"mean": 4.05, "beta": 0.36, "sd": 0.52},  # Nhóm biến dẫn dắt (Điểm cao, tác động mạnh nhất)
    {"mean": 3.75, "beta": 0.28, "sd": 0.58},  # Nhóm biến khá (Điểm khá, tác động mạnh nhì)
    {"mean": 3.45, "beta": 0.22, "sd": 0.62},  # Nhóm biến trung bình khá (Điểm vừa phải, nhiều mức 3-4)
    {"mean": 3.88, "beta": 0.25, "sd": 0.55},  # Nhóm biến tích cực vừa
    {"mean": 3.25, "beta": 0.19, "sd": 0.65},  # Nhóm biến khắt khe/thận trọng (Nhiều mức 2-3-4)
    {"mean": 3.60, "beta": 0.24, "sd": 0.58},
    {"mean": 3.95, "beta": 0.30, "sd": 0.54}
]

def extract_var_info(var_data, idx=0, is_y=False):
    """Hỗ trợ cả 2 kiểu JSON: kiểu mảng ['entry.1',...] và kiểu object {'entries': [...], 'mean': 3.8, 'beta': 0.3}"""
    default_prof = {"mean": 3.80, "beta": 1.0, "sd": 0.50} if is_y else AUTO_PROFILES[idx % len(AUTO_PROFILES)]
    if isinstance(var_data, list):
        return var_data, default_prof["mean"], default_prof["beta"], default_prof["sd"]
    elif isinstance(var_data, dict):
        entries = var_data.get("entries", [])
        mean = float(var_data.get("mean", default_prof["mean"]))
        beta = float(var_data.get("beta", default_prof["beta"]))
        sd = float(var_data.get("sd", default_prof["sd"]))
        return entries, mean, beta, sd
    return [], 3.7, 0.25, 0.55

# Tạo độ lệch chuẩn cố định cho từng câu hỏi nhỏ (item) để các câu trong cùng 1 nhóm biến cũng tự nhiên khác nhau
ITEM_OFFSETS = {}
for x_idx, (x_code, x_val) in enumerate(X_VARS.items()):
    entries, _, _, _ = extract_var_info(x_val, x_idx)
    for e_idx, entry_id in enumerate(entries):
        ITEM_OFFSETS[entry_id] = ((e_idx % 3) - 1) * 0.15

for y_idx, (y_code, y_val) in enumerate(Y_VARS.items()):
    entries, _, _, _ = extract_var_info(y_val, y_idx, is_y=True)
    for e_idx, entry_id in enumerate(entries):
        ITEM_OFFSETS[entry_id] = ((e_idx % 3) - 1) * 0.12

def generate_likert_payload():
    likert_payload = {}
    roll = random.random()

    def map_label(score_int):
        return LIKERT_LABELS.get(str(score_int), str(score_int))

    all_entries = []
    for i, val in enumerate(X_VARS.values()):
        ents, _, _, _ = extract_var_info(val, i)
        all_entries.extend(ents)
    for i, val in enumerate(Y_VARS.values()):
        ents, _, _, _ = extract_var_info(val, i, is_y=True)
        all_entries.extend(ents)

    # --- TRƯỜNG HỢP 1: DỮ LIỆU RÁC - NGƯỜI ĐIỀN BỪA (1.5%) ---
    if roll < 0.015:
        for entry_id in all_entries:
            likert_payload[entry_id] = map_label(random.randint(1, 5))
        return likert_payload, "RÁC (Điền ngẫu nhiên)"

    # --- TRƯỜNG HỢP 2: DỮ LIỆU RÁC - NGƯỜI KHÓ TÍNH / TIÊU CỰC (1.5%) ---
    elif roll < 0.030:
        for entry_id in all_entries:
            low_score = int(np.clip(np.round(np.random.normal(2.1, 0.65)), 1, 3))
            likert_payload[entry_id] = map_label(low_score)
        return likert_payload, "RÁC (Điểm thấp/Khó tính)"

    # --- TRƯỜNG HỢP 3: DỮ LIỆU CHUẨN MÔ HÌNH HỒI QUY (97%) ---
    shared_base = np.random.normal(0, 0.35)

    latent_x = {}
    effect_on_y = 0.0
    num_x = max(1, len(X_VARS))
    scale_factor = 1.0 / np.sqrt(num_x / 3.0)

    # 3.1. Sinh nhân tố tiềm ẩn và điểm cho từng nhóm biến độc lập X
    for idx, (x_code, x_val) in enumerate(X_VARS.items()):
        entries, target_mean, beta_weight, noise_sd = extract_var_info(x_val, idx, is_y=False)
        latent_x[x_code] = 0.45 * shared_base + np.random.normal(0, 0.80)
        effect_on_y += beta_weight * scale_factor * latent_x[x_code]

        base_factor = latent_x[x_code]
        for entry_id in entries:
            item_offset = ITEM_OFFSETS.get(entry_id, 0.0)
            loading = random.uniform(0.65, 0.76)
            noise = np.random.normal(0, noise_sd)

            raw_score = (target_mean + item_offset) + loading * base_factor + noise
            final_score = int(np.clip(np.round(raw_score), 1, 5))
            likert_payload[entry_id] = map_label(final_score)

    # 3.2. Sinh điểm chi tiết cho biến phụ thuộc Y
    latent_y = effect_on_y + np.random.normal(0, 0.48)
    for idx, (y_code, y_val) in enumerate(Y_VARS.items()):
        entries, target_mean, _, noise_sd = extract_var_info(y_val, idx, is_y=True)
        for entry_id in entries:
            item_offset = ITEM_OFFSETS.get(entry_id, 0.0)
            loading = random.uniform(0.68, 0.78)
            noise = np.random.normal(0, noise_sd)

            raw_score = (target_mean + item_offset) + loading * latent_y + noise
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

    # Bắt buộc kèm fvv="1" và pageHistory để Google Forms ghi nhận đầy đủ các trang
    full_payload["fvv"] = "1"
    if PAGE_HISTORY is not None:
        full_payload["pageHistory"] = str(PAGE_HISTORY)

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
