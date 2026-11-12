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
M_VARS = config.get("mediator_vars", {})
Y_VARS = config.get("dependent_var", {})

# Ánh xạ điểm số sang chữ hiển thị trên Form (Tự động nhận diện thang 5, 6 hoặc 7 điểm)
LIKERT_LABELS = config.get("likert_labels", {
    "1": "1",
    "2": "2",
    "3": "3",
    "4": "4",
    "5": "5"
})

NUMERIC_KEYS = [int(k) for k in LIKERT_LABELS.keys() if str(k).isdigit()]
MIN_SCALE = min(NUMERIC_KEYS) if NUMERIC_KEYS else 1
MAX_SCALE = max(NUMERIC_KEYS) if NUMERIC_KEYS else 5
SCALE_SPAN = max(1, MAX_SCALE - MIN_SCALE)

MODEL_TYPE = "CẤU TRÚC SEM (2 TẦNG TRUNG GIAN)" if M_VARS else "HỒI QUY ĐA BIẾN (1 TẦNG)"

print("=" * 65)
print(f"HỆ THỐNG ENGINE SINH SỐ LIỆU KHẢO SÁT TỰ ĐỘNG")
print(f"Khách hàng       : {CLIENT_NAME}")
print(f"Loại mô hình     : {MODEL_TYPE} | Thang đo: {MIN_SCALE}-{MAX_SCALE} điểm")
print(f"Số mẫu đợt này   : {BATCH_SAMPLES} mẫu | Giãn cách: {MIN_DELAY}s - {MAX_DELAY}s")
print(f"Biến nhân khẩu   : {len(DEMOGRAPHICS)} câu")
print(f"Cấu trúc biến    : X={len(X_VARS)} | M(Trung gian)={len(M_VARS)} | Y={len(Y_VARS)}")
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
# 3. ĐỘNG CƠ TOÁN HỌC LIKERT ĐA TẦNG (TỰ ĐỘNG CO GIÃN THANG 5/6/7 ĐIỂM)
# =====================================================================
SCALE_RATIO = SCALE_SPAN / 4.0  # = 1.0 với thang 1-5, = 1.25 với thang 1-6, = 1.5 với thang 1-7

def scale_mean(base_mean_5):
    return MIN_SCALE + (base_mean_5 - 1.0) * SCALE_RATIO

AUTO_PROFILES = [
    {"mean": scale_mean(3.95), "beta_m": 0.32, "beta_y": 0.26, "sd": round(0.48 * np.sqrt(SCALE_RATIO), 3)},
    {"mean": scale_mean(3.72), "beta_m": 0.30, "beta_y": 0.24, "sd": round(0.50 * np.sqrt(SCALE_RATIO), 3)},
    {"mean": scale_mean(3.55), "beta_m": 0.27, "beta_y": 0.21, "sd": round(0.52 * np.sqrt(SCALE_RATIO), 3)},
    {"mean": scale_mean(3.82), "beta_m": 0.25, "beta_y": 0.22, "sd": round(0.50 * np.sqrt(SCALE_RATIO), 3)},
    {"mean": scale_mean(3.40), "beta_m": 0.22, "beta_y": 0.19, "sd": round(0.54 * np.sqrt(SCALE_RATIO), 3)},
    {"mean": scale_mean(3.65), "beta_m": 0.26, "beta_y": 0.23, "sd": round(0.50 * np.sqrt(SCALE_RATIO), 3)},
    {"mean": scale_mean(3.90), "beta_m": 0.31, "beta_y": 0.25, "sd": round(0.48 * np.sqrt(SCALE_RATIO), 3)}
]

def extract_var_info(var_data, idx=0, role="x"):
    """
    Hỗ trợ cả kiểu mảng ['entry.1', ...] lẫn kiểu object:
    - Biến độc lập X : {'entries': [...], 'mean': 4.65, 'beta_m': 0.34, 'beta_y': 0.0, 'sd': 0.56}
    - Biến trung gian M: {'entries': [...], 'mean': 4.55, 'beta_y': 0.38, 'sd': 0.54}
    - Biến phụ thuộc Y : {'entries': [...], 'mean': 4.40, 'sd': 0.54}
    """
    if role == "y":
        default_prof = {"mean": scale_mean(3.80), "beta_m": 0.0, "beta_y": 1.0, "sd": round(0.46 * np.sqrt(SCALE_RATIO), 3)}
    elif role == "m":
        default_prof = {"mean": scale_mean(3.65), "beta_m": 0.0, "beta_y": 0.35, "sd": round(0.46 * np.sqrt(SCALE_RATIO), 3)}
    else:
        default_prof = AUTO_PROFILES[idx % len(AUTO_PROFILES)]

    if isinstance(var_data, list):
        return var_data, default_prof["mean"], default_prof["beta_m"], default_prof["beta_y"], default_prof["sd"]
    elif isinstance(var_data, dict):
        entries = var_data.get("entries", [])
        mean = float(var_data.get("mean", default_prof["mean"]))
        beta_fallback = float(var_data.get("beta", default_prof["beta_y"]))
        beta_m = float(var_data.get("beta_m", default_prof["beta_m"]))
        beta_y = float(var_data.get("beta_y", beta_fallback))
        sd = float(var_data.get("sd", default_prof["sd"]))
        return entries, mean, beta_m, beta_y, sd
    return [], scale_mean(3.70), 0.25, 0.22, 0.48

# Độ lệch cố định cho từng câu hỏi nhỏ (item) để các biến quan sát trong cùng nhân tố tự nhiên khác nhau
ITEM_OFFSETS = {}
for role_key, group in [("x", X_VARS), ("m", M_VARS), ("y", Y_VARS)]:
    for g_idx, (_, g_val) in enumerate(group.items()):
        entries, _, _, _, _ = extract_var_info(g_val, g_idx, role=role_key)
        for e_idx, entry_id in enumerate(entries):
            ITEM_OFFSETS[entry_id] = ((e_idx % 3) - 1) * 0.13 * np.sqrt(SCALE_RATIO)

def generate_likert_payload():
    likert_payload = {}
    roll = random.random()

    def map_label(score_int):
        return LIKERT_LABELS.get(str(score_int), str(score_int))

    all_entries = []
    for role_key, group in [("x", X_VARS), ("m", M_VARS), ("y", Y_VARS)]:
        for i, val in enumerate(group.values()):
            ents, _, _, _, _ = extract_var_info(val, i, role=role_key)
            all_entries.extend(ents)

    # --- TRƯỜNG HỢP 1: DỮ LIỆU RÁC - NGƯỜI ĐIỀN BỪA (1.5%) ---
    if roll < 0.015:
        for entry_id in all_entries:
            likert_payload[entry_id] = map_label(random.randint(MIN_SCALE, MAX_SCALE))
        return likert_payload, "RÁC (Điền ngẫu nhiên)"

    # --- TRƯỜNG HỢP 2: DỮ LIỆU RÁC - NGƯỜI KHÓ TÍNH / TIÊU CỰC (1.5%) ---
    elif roll < 0.030:
        low_center = MIN_SCALE + 0.28 * SCALE_SPAN
        low_cap = max(MIN_SCALE + 1, int(np.ceil((MIN_SCALE + MAX_SCALE) / 2.0)))
        for entry_id in all_entries:
            low_score = int(np.clip(np.round(np.random.normal(low_center, 0.65)), MIN_SCALE, low_cap))
            likert_payload[entry_id] = map_label(low_score)
        return likert_payload, "RÁC (Điểm thấp/Khó tính)"

    # --- TRƯỜNG HỢP 3: DỮ LIỆU CHUẨN MÔ HÌNH ĐA BIẾN / CẤU TRÚC SEM (97%) ---
    shared_base = np.random.normal(0, 0.25)

    latent_x = {}
    effect_on_m = 0.0
    effect_on_y = 0.0
    num_x = max(1, len(X_VARS))
    scale_factor = 1.0 / np.sqrt(num_x / 3.0)
    loading_boost = np.sqrt(SCALE_RATIO)

    # 3.1. Sinh nhân tố tiềm ẩn và điểm cho các biến độc lập X
    for idx, (x_code, x_val) in enumerate(X_VARS.items()):
        entries, target_mean, beta_m, beta_y, noise_sd = extract_var_info(x_val, idx, role="x")
        latent_x[x_code] = 0.35 * shared_base + np.random.normal(0, 0.85)
        effect_on_m += beta_m * scale_factor * latent_x[x_code]
        effect_on_y += beta_y * scale_factor * latent_x[x_code]

        for entry_id in entries:
            item_offset = ITEM_OFFSETS.get(entry_id, 0.0)
            loading = random.uniform(0.68, 0.78) * loading_boost
            noise = np.random.normal(0, noise_sd)

            raw_score = (target_mean + item_offset) + loading * latent_x[x_code] + noise
            final_score = int(np.clip(np.round(raw_score), MIN_SCALE, MAX_SCALE))
            likert_payload[entry_id] = map_label(final_score)

    # 3.2. Sinh điểm cho biến trung gian M (Tự động kích hoạt khi JSON có mediator_vars)
    num_m = max(1, len(M_VARS))
    m_scale = 1.0 / np.sqrt(num_m)
    for idx, (m_code, m_val) in enumerate(M_VARS.items()):
        entries, target_mean, _, beta_m_to_y, noise_sd = extract_var_info(m_val, idx, role="m")
        latent_m = effect_on_m + np.random.normal(0, 0.56)
        effect_on_y += beta_m_to_y * m_scale * latent_m

        for entry_id in entries:
            item_offset = ITEM_OFFSETS.get(entry_id, 0.0)
            loading = random.uniform(0.68, 0.78) * loading_boost
            noise = np.random.normal(0, noise_sd)

            raw_score = (target_mean + item_offset) + loading * latent_m + noise
            final_score = int(np.clip(np.round(raw_score), MIN_SCALE, MAX_SCALE))
            likert_payload[entry_id] = map_label(final_score)

    # 3.3. Sinh điểm chi tiết cho biến phụ thuộc Y
    latent_y = effect_on_y + np.random.normal(0, 0.48)
    for idx, (y_code, y_val) in enumerate(Y_VARS.items()):
        entries, target_mean, _, _, noise_sd = extract_var_info(y_val, idx, role="y")
        for entry_id in entries:
            item_offset = ITEM_OFFSETS.get(entry_id, 0.0)
            loading = random.uniform(0.68, 0.78) * loading_boost
            noise = np.random.normal(0, noise_sd)

            raw_score = (target_mean + item_offset) + loading * latent_y + noise
            final_score = int(np.clip(np.round(raw_score), MIN_SCALE, MAX_SCALE))
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
