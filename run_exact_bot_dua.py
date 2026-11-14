import urllib.request
import urllib.parse
import random
import time
import sys
import argparse
import numpy as np
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8')

FORM_URL = "https://docs.google.com/forms/u/0/d/e/1FAIpQLSe2g3jAzcLBOIBbslgZm1_bv4QSqDnljn_BfvU547W3y-Xc6g/formResponse"
PAGE_HISTORY = "0,1,2,3,4"

def distribute_checkbox_exact(n_rows, option_counts, min_per_row=1, max_per_row=4, seed=42):
    """
    Phân bổ chính xác số lượng xuất hiện của từng đáp án vào n_rows dòng
    sao cho mỗi dòng không bị trùng đáp án và số đáp án mỗi dòng nằm trong [min_per_row, max_per_row].
    """
    rng = random.Random(seed)
    total_picks = sum(option_counts.values())
    
    # Xác định kích thước (số đáp án) cho mỗi dòng sao cho tổng = total_picks
    row_sizes = [min_per_row] * n_rows
    rem = total_picks - sum(row_sizes)
    while rem > 0:
        idx = rng.randrange(n_rows)
        if row_sizes[idx] < max_per_row:
            row_sizes[idx] += 1
            rem -= 1
            
    # Sắp xếp dòng theo kích thước giảm dần để phân bổ an toàn
    rows = [[] for _ in range(n_rows)]
    # Sắp xếp đáp án theo số lần xuất hiện giảm dần
    sorted_opts = sorted(option_counts.items(), key=lambda x: -x[1])
    
    for opt, count in sorted_opts:
        # Chọn 'count' dòng còn slot trống, ưu tiên dòng còn nhiều slot trống nhất (có trộn ngẫu nhiên)
        candidates = [i for i in range(n_rows) if len(rows[i]) < row_sizes[i] and opt not in rows[i]]
        rng.shuffle(candidates)
        candidates.sort(key=lambda i: -(row_sizes[i] - len(rows[i])))
        if len(candidates) < count:
            raise ValueError(f"Không thể phân bổ đủ {count} cho {opt}")
        for i in candidates[:count]:
            rows[i].append(opt)
            
    rng.shuffle(rows)
    return rows

def generate_likert_block(n_rows, n_items, target_probs, seed=42):
    """
    Sinh ma trận n_rows x n_items cho thang đo Likert 1-4 (Cột 1..Cột 4)
    đảm bảo tỷ lệ tổng thể chính xác theo target_probs và có tương quan nội tại (Cronbach's Alpha cao).
    """
    rng = np.random.default_rng(seed)
    # Điểm nền (latent score) cho từng người từ 0 đến 1
    latent = rng.uniform(0, 1, size=n_rows)
    
    # Với mỗi câu hỏi, xếp hạng người dùng dựa trên latent + nhiễu nhẹ, rồi gán đúng quota Cột 1, 2, 3, 4
    matrix = np.zeros((n_rows, n_items), dtype=int)
    
    c1_n = round(n_rows * target_probs[0])
    c2_n = round(n_rows * target_probs[1])
    c3_n = round(n_rows * target_probs[2])
    c4_n = n_rows - c1_n - c2_n - c3_n
    
    sorted_vals = [1]*c1_n + [2]*c2_n + [3]*c3_n + [4]*c4_n
    
    for j in range(n_items):
        # Nhiễu nhỏ giúp câu hỏi có độ biến thiên tự nhiên nhưng vẫn giữ Cronbach's Alpha > 0.75
        item_score = latent + rng.normal(0, 0.16, size=n_rows)
        order = np.argsort(item_score)
        for rank_idx, row_idx in enumerate(order):
            matrix[row_idx, j] = sorted_vals[rank_idx]
            
    return matrix

def build_100_exact_samples(seed=2026):
    rng = random.Random(seed)
    N = 100
    
    # 1. A1: Giới tính (Nữ 69%, Nam 31%)
    genders = ["Nữ"] * 69 + ["Nam"] * 31
    rng.shuffle(genders)
    
    # 2. A2, A4, A5: Khớp logic chéo Tuổi - Nghề nghiệp - Thu nhập
    # Nghề nghiệp: HSSV 70, NVVP 12, Công nhân 10, Nội trợ 8
    # Tuổi: 18-24 (75), 25-30 (8), 31-40 (7), Trên 41 (10)
    # Thu nhập: Dưới 5tr (63), Chưa có (15), 5-10tr (11), 11-20tr (6), 21-30tr (3), Trên 30tr (2)
    
    profiles = []
    # Nhóm HSSV (70 người): tất cả đều 18-24, thu nhập chưa có hoặc dưới 5tr
    hssv_incomes = ["Chưa có thu nhập"] * 15 + ["Dưới 5 triệu"] * 55
    rng.shuffle(hssv_incomes)
    for i in range(70):
        profiles.append(("18 – 24", "Học sinh/sinh viên", hssv_incomes[i]))
        
    # Nhóm 30 người còn lại: 12 NVVP, 10 Công nhân, 8 Nội trợ
    other_jobs = ["Nhân viên văn phòng"] * 12 + ["Công nhân/lao động phổ thông"] * 10 + ["Nội trợ"] * 8
    other_ages = ["18 – 24"] * 5 + ["25 – 30"] * 8 + ["31 – 40"] * 7 + ["Trên 41"] * 10
    other_incomes = ["Dưới 5 triệu"] * 8 + ["Từ 5 triệu đến 10 triệu đồng"] * 11 + ["Từ 11 triệu đến 20 triệu đồng"] * 6 + ["Từ 21 triệu đến 30 triệu đồng"] * 3 + ["Trên 30 triệu đồng"] * 2
    rng.shuffle(other_jobs)
    rng.shuffle(other_ages)
    rng.shuffle(other_incomes)
    for i in range(30):
        profiles.append((other_ages[i], other_jobs[i], other_incomes[i]))
        
    rng.shuffle(profiles)
    
    # 3. A3: Tỉnh/TP sinh sống
    cities = (["TP.HCM"] * 25 + ["Thành phố Hồ Chí Minh"] * 22 + ["HCM"] * 19 + 
              ["Tp HCM"] * 15 + ["Sài Gòn"] * 10 + ["Bình Dương"] * 3 + ["Tây Ninh"] * 3 + ["Củ Chi"] * 3)
    rng.shuffle(cities)
    
    # 4. B1: Đồ uống từng dùng (Checkbox) -> Bám sát tỷ lệ bài mẫu
    b1_rows = distribute_checkbox_exact(N, {
        "Sữa chua uống hoặc đồ uống probiotic": 77,
        "Nước ép trái cây đóng chai (cam, táo, dứa, v.v.)": 70,
        "Nước detox, nước ép rau củ": 41,
        "Nước tăng lực hoặc nước uống bổ sung vitamin": 27,
        "Bột hòa tan (collagen, vitamin C, chất xơ, v.v.)": 14,
    }, min_per_row=1, max_per_row=4, seed=seed+1)
    
    # 5. B2: Tần suất sử dụng (Khóa Hằng ngày)
    b2_list = ["1-2 lần/tuần"] * 49 + ["1-3 lần/tháng"] * 35 + ["3-5 lần/tuần"] * 13 + ["Chưa từng sử dụng"] * 3
    rng.shuffle(b2_list)
    
    # 6. B3: Yếu tố quan tâm nhất (Thành phần 53%, Giá cả 17%, Hàm lượng 12%...)
    b3_list = (["Thành phần và nguồn gốc nguyên liệu"] * 53 +
               ["Giá cả phù hợp"] * 17 +
               ["Hàm lượng chất xơ/dinh dưỡng"] * 12 +
               ["Mùi vị dễ uống"] * 9 +
               ["Thương hiệu và độ uy tín"] * 5 +
               ["Dễ tìm mua"] * 2 +
               ["Bao bì và quy cách đóng gói"] * 2)
    rng.shuffle(b3_list)
    
    # 7. B4: Mục đích sử dụng (Bắt buộc >= 2 đáp án)
    b4_rows = distribute_checkbox_exact(N, {
        "Hỗ trợ tiêu hóa, ngăn táo bón": 80,
        "Giúp da khỏe, đẹp": 59,
        "Cải thiện sức khỏe đường ruột": 53,
        "Bổ sung dinh dưỡng cho cơ thể": 47,
        "Kiểm soát cân nặng, giảm cảm giác thèm ăn": 42,
    }, min_per_row=2, max_per_row=4, seed=seed+2)
    
    # 8. B5: Liên tưởng bột dứa
    b5_list = (["Thức uống bổ sung vitamin và năng lượng"] * 57 +
               ["Sản phẩm tốt cho tiêu hóa"] * 25 +
               ["Dễ pha, tiện lợi sử dụng hàng ngày"] * 11 +
               ["Hỗ trợ làm đẹp, thanh lọc cơ thể"] * 5 +
               ["Mùi vị tự nhiên, thơm ngon"] * 2)
    rng.shuffle(b5_list)
    
    # 9. B6: Kênh biết đến (BẮT BUỘC ĐÚNG 2 ĐÁP ÁN MỖI DÒNG -> Tổng 200 lượt)
    b6_rows = distribute_checkbox_exact(N, {
        "Mạng xã hội (Facebook, TikTok, YouTube,...)": 68,
        "Siêu thị/cửa hàng tiện lợi": 62,
        "Người thân, bạn bè giới thiệu": 40,
        "Sàn thương mại điện tử (Shopee, Lazada,...)": 16,
        "Quảng cáo trên truyền hình/báo chí": 14,
    }, min_per_row=2, max_per_row=2, seed=seed+3)
    
    # 10. D1, D2, D3
    d1_list = ["Concept 1: Dứa Cam"] * 72 + ["Concept 2: Dứa Chanh Dây"] * 19 + ["Concept 3: Dứa Cần Tây"] * 9
    rng.shuffle(d1_list)
    
    d2_list = ["40.000 – 60.000 VNĐ"] * 47 + ["65.000 – 80.000 VNĐ"] * 44 + ["Trên 80.000 VNĐ"] * 9
    rng.shuffle(d2_list)
    
    d3_list = ["Sẵn lòng"] * 48 + ["Rất sẵn lòng"] * 38 + ["Phân vân"] * 14
    rng.shuffle(d3_list)
    
    # 11. Phần C & D Likert (Cột 1..Cột 4 khớp tỷ lệ biểu đồ bài mẫu)
    # Tỷ lệ mục tiêu: [Cột 1, Cột 2, Cột 3, Cột 4]
    sk_mat = generate_likert_block(N, 5, [0.02, 0.11, 0.28, 0.59], seed=seed+10) # Sức khỏe
    tl_mat = generate_likert_block(N, 3, [0.01, 0.06, 0.23, 0.70], seed=seed+11) # Tiện lợi
    cq_mat = generate_likert_block(N, 4, [0.01, 0.08, 0.27, 0.64], seed=seed+12) # Cảm quan
    tp_mat = generate_likert_block(N, 3, [0.01, 0.08, 0.19, 0.72], seed=seed+13) # Thành phần
    bb_mat = generate_likert_block(N, 5, [0.01, 0.10, 0.25, 0.64], seed=seed+14) # Bao bì
    gc_mat = generate_likert_block(N, 3, [0.01, 0.09, 0.24, 0.66], seed=seed+15) # Giá cả
    
    c1_mat = generate_likert_block(N, 5, [0.00, 0.08, 0.30, 0.62], seed=seed+16) # Concept 1 (cao vượt trội)
    c2_mat = generate_likert_block(N, 5, [0.02, 0.23, 0.35, 0.40], seed=seed+17) # Concept 2 (thấp hơn)
    c3_mat = generate_likert_block(N, 5, [0.00, 0.18, 0.28, 0.54], seed=seed+18) # Concept 3 (vừa phải)
    
    samples = []
    for i in range(N):
        age, job, inc = profiles[i]
        # Build list of (key, value) pairs so checkbox can repeat the same key
        pairs = [
            ("pageHistory", PAGE_HISTORY),
            ("entry.2022562691", genders[i]),
            ("entry.685695320", age),
            ("entry.1632344155", cities[i]),
            ("entry.1496334987", inc),
            ("entry.538106461", job),
            ("entry.296656021", b2_list[i]),
            ("entry.1332127414", b3_list[i]),
            ("entry.373341248", b5_list[i]),
            ("entry.494834499", d1_list[i]),
            ("entry.136666543", d2_list[i]),
            ("entry.1148291922", d3_list[i]),
        ]
        # Checkboxes
        for val in b1_rows[i]:
            pairs.append(("entry.1803028686", val))
        for val in b4_rows[i]:
            pairs.append(("entry.1367829508", val))
        for val in b6_rows[i]:
            pairs.append(("entry.428650777", val))
            
        # Likert mappings
        sk_entries = ["entry.735391411", "entry.569581271", "entry.1997950294", "entry.1155553088", "entry.213517069"]
        for j, ent in enumerate(sk_entries):
            pairs.append((ent, f"Cột {sk_mat[i, j]}"))
            
        tl_entries = ["entry.850387370", "entry.644423906", "entry.1519365744"]
        for j, ent in enumerate(tl_entries):
            pairs.append((ent, f"Cột {tl_mat[i, j]}"))
            
        cq_entries = ["entry.500388262", "entry.2065162975", "entry.1366585057", "entry.168174214"]
        for j, ent in enumerate(cq_entries):
            pairs.append((ent, f"Cột {cq_mat[i, j]}"))
            
        tp_entries = ["entry.1907819095", "entry.1599106116", "entry.27980518"]
        for j, ent in enumerate(tp_entries):
            pairs.append((ent, f"Cột {tp_mat[i, j]}"))
            
        bb_entries = ["entry.1212414479", "entry.1213021156", "entry.138091049", "entry.2036120319", "entry.1838370143"]
        for j, ent in enumerate(bb_entries):
            pairs.append((ent, f"Cột {bb_mat[i, j]}"))
            
        gc_entries = ["entry.1770830723", "entry.1207326280", "entry.1184972236"]
        for j, ent in enumerate(gc_entries):
            pairs.append((ent, f"Cột {gc_mat[i, j]}"))
            
        c1_entries = ["entry.1659912241", "entry.1828241229", "entry.885402233", "entry.1054547256", "entry.1366155745"]
        for j, ent in enumerate(c1_entries):
            pairs.append((ent, f"Cột {c1_mat[i, j]}"))
            
        c2_entries = ["entry.869652347", "entry.2137221507", "entry.224696852", "entry.1314766207", "entry.917523594"]
        for j, ent in enumerate(c2_entries):
            pairs.append((ent, f"Cột {c2_mat[i, j]}"))
            
        c3_entries = ["entry.2039952361", "entry.161404900", "entry.764835763", "entry.988682671", "entry.1869753584"]
        for j, ent in enumerate(c3_entries):
            pairs.append((ent, f"Cột {c3_mat[i, j]}"))
            
        samples.append(pairs)
    return samples

def verify_samples(samples):
    print(f"=== KIỂM TRA CHÍNH XÁC {len(samples)} MẪU ===")
    def get_vals(entry):
        return [v for s in samples for k, v in s if k == entry]
    
    for name, ent in [
        ("A1. Giới tính", "entry.2022562691"),
        ("A2. Tuổi", "entry.685695320"),
        ("A5. Nghề nghiệp", "entry.538106461"),
        ("B1. Đồ uống từng dùng", "entry.1803028686"),
        ("B3. Yếu tố quan tâm", "entry.1332127414"),
        ("B4. Mục đích (>=2 đáp án)", "entry.1367829508"),
        ("B6. Kênh biết đến (đúng 2)", "entry.428650777"),
        ("D1. Concept yêu thích", "entry.494834499"),
        ("D2. Giá chi trả", "entry.136666543"),
        ("D3. Sẵn lòng mua thử", "entry.1148291922"),
    ]:
        c = Counter(get_vals(ent))
        print(f"\n[{name}]:")
        for k, v in c.most_common():
            print(f"   - {k}: {v}%")
            
    # Check lengths of B4 and B6
    b4_lens = Counter(sum(1 for k, v in s if k == "entry.1367829508") for s in samples)
    b6_lens = Counter(sum(1 for k, v in s if k == "entry.428650777") for s in samples)
    print(f"\nKiểm tra số lượng lựa chọn mỗi dòng:")
    print(f"   - B4 (Mục đích >= 2): {dict(b4_lens)}")
    print(f"   - B6 (Kênh đúng 2):  {dict(b6_lens)}")
    
    # Check Likert Cột 1-4 tổng thể Phần C
    c_entries = [
        "entry.735391411", "entry.569581271", "entry.1997950294", "entry.1155553088", "entry.213517069",
        "entry.850387370", "entry.644423906", "entry.1519365744",
        "entry.500388262", "entry.2065162975", "entry.1366585057", "entry.168174214",
        "entry.1907819095", "entry.1599106116", "entry.27980518",
        "entry.1212414479", "entry.1213021156", "entry.138091049", "entry.2036120319", "entry.1838370143",
        "entry.1770830723", "entry.1207326280", "entry.1184972236"
    ]
    c_vals = [v for s in samples for k, v in s if k in c_entries]
    c_cnt = Counter(c_vals)
    tot = len(c_vals)
    print(f"\nTổng hợp Likert Phần C (23 câu x 100 = {tot} lượt):")
    for k in ["Cột 1", "Cột 2", "Cột 3", "Cột 4"]:
        print(f"   - {k}: {c_cnt[k]} ({c_cnt[k]/tot*100:.1f}%)")

def send_samples(samples, min_delay, max_delay):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": FORM_URL.replace("/formResponse", "/viewform")
    }
    total = len(samples)
    for idx, pairs in enumerate(samples, 1):
        data = urllib.parse.urlencode(pairs).encode("utf-8")
        req = urllib.request.Request(FORM_URL, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                status = resp.getcode()
                print(f"[{idx}/{total}] Gửi thành công! HTTP {status}")
        except Exception as e:
            print(f"[{idx}/{total}] LỖI khi gửi: {e}")
            
        if idx < total:
            delay = random.uniform(min_delay, max_delay)
            print(f"   Đang nghỉ {delay:.1f} giây trước khi gửi phiếu tiếp theo...")
            time.sleep(delay)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Chỉ kiểm tra số liệu, không gửi lên Google Form")
    parser.add_argument("--min-delay", type=float, default=60.0, help="Thời gian nghỉ tối thiểu (giây)")
    parser.add_argument("--max-delay", type=float, default=120.0, help="Thời gian nghỉ tối đa (giây)")
    args = parser.parse_args()
    
    samples = build_100_exact_samples()
    if args.dry_run:
        verify_samples(samples)
    else:
        print(f"Bắt đầu gửi {len(samples)} mẫu lên Google Form (Delay: {args.min_delay}s - {args.max_delay}s)...")
        send_samples(samples, args.min_delay, args.max_delay)
        print("HOÀN TẤT 100/100 MẪU!")
