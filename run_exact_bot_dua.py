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

    row_sizes = [min_per_row] * n_rows
    rem = total_picks - sum(row_sizes)
    while rem > 0:
        idx = rng.randrange(n_rows)
        if row_sizes[idx] < max_per_row:
            row_sizes[idx] += 1
            rem -= 1

    rows = [[] for _ in range(n_rows)]
    sorted_opts = sorted(option_counts.items(), key=lambda x: -x[1])

    for opt, count in sorted_opts:
        candidates = [i for i in range(n_rows) if len(rows[i]) < row_sizes[i] and opt not in rows[i]]
        rng.shuffle(candidates)
        candidates.sort(key=lambda i: -(row_sizes[i] - len(rows[i])))
        if len(candidates) < count:
            raise ValueError(f"Không thể phân bổ đủ {count} cho {opt}")
        for i in candidates[:count]:
            rows[i].append(opt)

    rng.shuffle(rows)
    return rows


def generate_varied_likert_block(n_rows, item_counts_list, seed=42):
    """
    Sinh ma trận n_rows x n_items cho thang đo Likert 1-4 (Cột 1..Cột 4)
    với mỗi hàng (item) có số lượng [c1, c2, c3, c4] riêng biệt, tự nhiên (không bị đồng đều),
    đồng thời giữ tương quan nội tại (Cronbach's Alpha > 0.75).
    """
    rng = np.random.default_rng(seed)
    latent = rng.uniform(0, 1, size=n_rows)
    n_items = len(item_counts_list)
    matrix = np.zeros((n_rows, n_items), dtype=int)

    for j, (c1_n, c2_n, c3_n, c4_n) in enumerate(item_counts_list):
        assert c1_n + c2_n + c3_n + c4_n == n_rows, f"Item {j} sum != {n_rows}"
        sorted_vals = [1] * c1_n + [2] * c2_n + [3] * c3_n + [4] * c4_n
        item_score = latent + rng.normal(0, 0.16, size=n_rows)
        order = np.argsort(item_score)
        for rank_idx, row_idx in enumerate(order):
            matrix[row_idx, j] = sorted_vals[rank_idx]

    return matrix


def make_varied_item_counts(n_rows, n_items, c4_range, c2_range, c1_range, seed=42):
    """
    Tạo danh sách (c1, c2, c3, c4) khác nhau tự nhiên cho từng câu hỏi trong một nhóm,
    đảm bảo Cột 4 cao nhất > Cột 3 > Cột 2 >= Cột 1 (Cột 1 & 2 ít, có thể bằng 0).
    """
    rng = random.Random(seed)
    items = []
    used_c4 = set()
    for _ in range(n_items):
        # Chọn c4 không trùng lặp trong cùng 1 nhóm để biểu đồ tự nhiên
        for _attempt in range(50):
            c4 = rng.randint(c4_range[0], c4_range[1])
            if c4 not in used_c4:
                used_c4.add(c4)
                break
        c1 = rng.randint(c1_range[0], c1_range[1])
        c2 = rng.randint(c2_range[0], c2_range[1])
        c3 = n_rows - c4 - c2 - c1
        # Đảm bảo c3 > c2 và c4 > c3
        while c3 >= c4 or c3 <= c2:
            if c3 >= c4:
                c4 += 1
                c3 -= 1
            elif c3 <= c2 and c2 > 0:
                c2 -= 1
                c3 += 1
            else:
                break
        items.append((c1, c2, c3, c4))
    return items


def build_100_exact_samples(seed=2026):
    rng = random.Random(seed)
    N = 100

    # 1. A1: Giới tính (Nữ 69%, Nam 31%)
    genders = ["Nữ"] * 69 + ["Nam"] * 31
    rng.shuffle(genders)

    # 2. A2, A4, A5: Khớp logic chéo Tuổi - Nghề nghiệp - Thu nhập
    profiles = []
    hssv_incomes = ["Chưa có thu nhập"] * 15 + ["Dưới 5 triệu"] * 55
    rng.shuffle(hssv_incomes)
    for i in range(70):
        profiles.append(("18 – 24", "Học sinh/sinh viên", hssv_incomes[i]))

    other_jobs = ["Nhân viên văn phòng"] * 12 + ["Công nhân/lao động phổ thông"] * 10 + ["Nội trợ"] * 8
    other_ages = ["18 – 24"] * 5 + ["25 – 30"] * 8 + ["31 – 40"] * 7 + ["Trên 41"] * 10
    other_incomes = (
        ["Dưới 5 triệu"] * 8
        + ["Từ 5 triệu đến 10 triệu đồng"] * 11
        + ["Từ 11 triệu đến 20 triệu đồng"] * 6
        + ["Từ 21 triệu đến 30 triệu đồng"] * 3
        + ["Trên 30 triệu đồng"] * 2
    )
    rng.shuffle(other_jobs)
    rng.shuffle(other_ages)
    rng.shuffle(other_incomes)
    for i in range(30):
        profiles.append((other_ages[i], other_jobs[i], other_incomes[i]))

    rng.shuffle(profiles)

    # 3. A3: Tỉnh/TP sinh sống
    cities = (
        ["TP.HCM"] * 25
        + ["Thành phố Hồ Chí Minh"] * 22
        + ["HCM"] * 19
        + ["Tp HCM"] * 15
        + ["Sài Gòn"] * 10
        + ["Bình Dương"] * 3
        + ["Tây Ninh"] * 3
        + ["Củ Chi"] * 3
    )
    rng.shuffle(cities)

    # 4. B1: Đồ uống từng dùng (Checkbox)
    b1_rows = distribute_checkbox_exact(
        N,
        {
            "Sữa chua uống hoặc đồ uống probiotic": 77,
            "Nước ép trái cây đóng chai (cam, táo, dứa, v.v.)": 70,
            "Nước detox, nước ép rau củ": 41,
            "Nước tăng lực hoặc nước uống bổ sung vitamin": 27,
            "Bột hòa tan (collagen, vitamin C, chất xơ, v.v.)": 14,
        },
        min_per_row=1,
        max_per_row=4,
        seed=seed + 1,
    )

    # 5. B2: Tần suất sử dụng (Khóa Hằng ngày)
    b2_list = ["1-2 lần/tuần"] * 49 + ["1-3 lần/tháng"] * 35 + ["3-5 lần/tuần"] * 13 + ["Chưa từng sử dụng"] * 3
    rng.shuffle(b2_list)

    # 6. B3: Yếu tố quan tâm nhất
    b3_list = (
        ["Thành phần và nguồn gốc nguyên liệu"] * 53
        + ["Giá cả phù hợp"] * 17
        + ["Hàm lượng chất xơ/dinh dưỡng"] * 12
        + ["Mùi vị dễ uống"] * 9
        + ["Thương hiệu và độ uy tín"] * 5
        + ["Dễ tìm mua"] * 2
        + ["Bao bì và quy cách đóng gói"] * 2
    )
    rng.shuffle(b3_list)

    # 7. B4: Mục đích sử dụng (Bắt buộc >= 2 đáp án)
    b4_rows = distribute_checkbox_exact(
        N,
        {
            "Hỗ trợ tiêu hóa, ngăn táo bón": 80,
            "Giúp da khỏe, đẹp": 59,
            "Cải thiện sức khỏe đường ruột": 53,
            "Bổ sung dinh dưỡng cho cơ thể": 47,
            "Kiểm soát cân nặng, giảm cảm giác thèm ăn": 42,
        },
        min_per_row=2,
        max_per_row=4,
        seed=seed + 2,
    )

    # 8. B5: Liên tưởng bột dứa
    b5_list = (
        ["Thức uống bổ sung vitamin và năng lượng"] * 57
        + ["Sản phẩm tốt cho tiêu hóa"] * 25
        + ["Dễ pha, tiện lợi sử dụng hàng ngày"] * 11
        + ["Hỗ trợ làm đẹp, thanh lọc cơ thể"] * 5
        + ["Mùi vị tự nhiên, thơm ngon"] * 2
    )
    rng.shuffle(b5_list)

    # 9. B6: Kênh biết đến (BẮT BUỘC ĐÚNG 2 ĐÁP ÁN MỖI DÒNG)
    b6_rows = distribute_checkbox_exact(
        N,
        {
            "Mạng xã hội (Facebook, TikTok, YouTube,...)": 68,
            "Siêu thị/cửa hàng tiện lợi": 62,
            "Người thân, bạn bè giới thiệu": 40,
            "Sàn thương mại điện tử (Shopee, Lazada,...)": 16,
            "Quảng cáo trên truyền hình/báo chí": 14,
        },
        min_per_row=2,
        max_per_row=2,
        seed=seed + 3,
    )

    # 10. D1, D2, D3
    d1_list = ["Concept 1: Dứa Cam"] * 72 + ["Concept 2: Dứa Chanh Dây"] * 19 + ["Concept 3: Dứa Cần Tây"] * 9
    rng.shuffle(d1_list)

    d2_list = ["40.000 – 60.000 VNĐ"] * 47 + ["65.000 – 80.000 VNĐ"] * 44 + ["Trên 80.000 VNĐ"] * 9
    rng.shuffle(d2_list)

    d3_list = ["Sẵn lòng"] * 48 + ["Rất sẵn lòng"] * 38 + ["Phân vân"] * 14
    rng.shuffle(d3_list)

    # 11. Phần C: Mỗi phần và mỗi câu có số lượng khác nhau tự nhiên (Cột 4 cao nhất > Cột 3 >> Cột 2 >= Cột 1)
    sk_counts = make_varied_item_counts(N, 5, c4_range=(55, 64), c2_range=(6, 12), c1_range=(0, 2), seed=seed + 10)
    tl_counts = make_varied_item_counts(N, 3, c4_range=(65, 73), c2_range=(4, 9),  c1_range=(0, 1), seed=seed + 11)
    cq_counts = make_varied_item_counts(N, 4, c4_range=(59, 68), c2_range=(5, 10), c1_range=(0, 2), seed=seed + 12)
    tp_counts = make_varied_item_counts(N, 3, c4_range=(67, 75), c2_range=(4, 8),  c1_range=(0, 1), seed=seed + 13)
    bb_counts = make_varied_item_counts(N, 5, c4_range=(57, 66), c2_range=(6, 11), c1_range=(0, 2), seed=seed + 14)
    gc_counts = make_varied_item_counts(N, 3, c4_range=(61, 69), c2_range=(5, 10), c1_range=(0, 1), seed=seed + 15)

    sk_mat = generate_varied_likert_block(N, sk_counts, seed=seed + 20)
    tl_mat = generate_varied_likert_block(N, tl_counts, seed=seed + 21)
    cq_mat = generate_varied_likert_block(N, cq_counts, seed=seed + 22)
    tp_mat = generate_varied_likert_block(N, tp_counts, seed=seed + 23)
    bb_mat = generate_varied_likert_block(N, bb_counts, seed=seed + 24)
    gc_mat = generate_varied_likert_block(N, gc_counts, seed=seed + 25)

    # 12. Phần D: Concept 1 cao nhất > Concept 2 cao nhì > Concept 3 thấp nhất, các tiêu chí biến thiên tự nhiên
    c1_counts = make_varied_item_counts(N, 5, c4_range=(58, 66), c2_range=(5, 10),  c1_range=(0, 1), seed=seed + 30)
    c2_counts = make_varied_item_counts(N, 5, c4_range=(47, 54), c2_range=(11, 17), c1_range=(0, 2), seed=seed + 31)
    c3_counts = make_varied_item_counts(N, 5, c4_range=(38, 44), c2_range=(18, 24), c1_range=(1, 3), seed=seed + 32)

    c1_mat = generate_varied_likert_block(N, c1_counts, seed=seed + 40)
    c2_mat = generate_varied_likert_block(N, c2_counts, seed=seed + 41)
    c3_mat = generate_varied_likert_block(N, c3_counts, seed=seed + 42)

    samples = []
    for i in range(N):
        age, job, inc = profiles[i]
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
        for val in b1_rows[i]:
            pairs.append(("entry.1803028686", val))
        for val in b4_rows[i]:
            pairs.append(("entry.1367829508", val))
        for val in b6_rows[i]:
            pairs.append(("entry.428650777", val))

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
    print(f"=== KIỂM TRA CHÍNH XÁC {len(samples)} MẪU (PHIÊN BẢN MỚI BIẾN THIÊN TỰ NHIÊN) ===")

    def get_vals(entry):
        return [v for s in samples for k, v in s if k == entry]

    groups = [
        ("C1. Sức khỏe", ["entry.735391411", "entry.569581271", "entry.1997950294", "entry.1155553088", "entry.213517069"]),
        ("C2. Tiện lợi", ["entry.850387370", "entry.644423906", "entry.1519365744"]),
        ("C3. Cảm quan", ["entry.500388262", "entry.2065162975", "entry.1366585057", "entry.168174214"]),
        ("C4. Thành phần", ["entry.1907819095", "entry.1599106116", "entry.27980518"]),
        ("C5. Bao bì", ["entry.1212414479", "entry.1213021156", "entry.138091049", "entry.2036120319", "entry.1838370143"]),
        ("C6. Giá cả", ["entry.1770830723", "entry.1207326280", "entry.1184972236"]),
        ("D. Concept 1 (Cao nhất)", ["entry.1659912241", "entry.1828241229", "entry.885402233", "entry.1054547256", "entry.1366155745"]),
        ("D. Concept 2 (Cao nhì)", ["entry.869652347", "entry.2137221507", "entry.224696852", "entry.1314766207", "entry.917523594"]),
        ("D. Concept 3 (Thấp nhất)", ["entry.2039952361", "entry.161404900", "entry.764835763", "entry.988682671", "entry.1869753584"]),
    ]

    for g_name, ents in groups:
        print(f"\n[{g_name}]:")
        for idx, ent in enumerate(ents, 1):
            c = Counter(get_vals(ent))
            print(f"   Câu {idx}: Cột 1={c['Cột 1']:2d} | Cột 2={c['Cột 2']:2d} | Cột 3={c['Cột 3']:2d} | Cột 4={c['Cột 4']:2d}")

    b4_lens = Counter(sum(1 for k, v in s if k == "entry.1367829508") for s in samples)
    b6_lens = Counter(sum(1 for k, v in s if k == "entry.428650777") for s in samples)
    print(f"\nKiểm tra Checkbox:")
    print(f"   - B4 (>= 2 đáp án): {dict(b4_lens)}")
    print(f"   - B6 (đúng 2 đáp án): {dict(b6_lens)}")


def send_samples(samples, min_delay, max_delay):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": FORM_URL.replace("/formResponse", "/viewform"),
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
