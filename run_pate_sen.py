import argparse
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSeWpGDbg6NO5n9pHRX-JfH_qLs4Tm9AGnzbfz7jfTKxjEJOCA/formResponse"
PAGE_HISTORY = "0,1,2,3,4,5,6,7"

USER_AGENTS = [
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.6312.99 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
]


def generate_sample():
    p = {}

    # === PHẦN A (Trang 0) ===
    p["entry.242642823"] = random.choices(["Nam", "Nữ", "Khác"], weights=[47, 51, 2], k=1)[0]
    p["entry.827098147"] = "18–22 tuổi"
    p["entry.785444148"] = "Học sinh/sinh viên"
    p["entry.419326349"] = random.choices(
        ["Dưới 3 triệu đồng", "Từ 3 đến dưới 8 triệu đồng"], weights=[75, 25], k=1
    )[0]

    # === PHẦN B (Trang 1) ===
    p["entry.2100211866"] = random.choices(
        [
            "Chưa bao giờ",
            "Hiếm khi (vài lần/năm)",
            "Thỉnh thoảng (1–2 lần/tháng)",
            "Thường xuyên (1–2 lần/tuần)",
            "Rất thường xuyên (trên 2 lần/tuần)",
        ],
        weights=[5, 20, 45, 25, 5],
        k=1,
    )[0]

    b1_opts = [
        "Hạt sen tươi/khô để nấu ăn",
        "Chè hạt sen",
        "Sữa/đồ uống từ hạt sen",
        "Bánh hoặc món tráng miệng",
        "Hạt sen sấy/snack",
        "Bột hạt sen",
    ]
    p["entry.626507224"] = random.sample(b1_opts, random.randint(1, 2))

    b2_opts = [
        "Siêu thị",
        "Cửa hàng thực phẩm sạch",
        "Cửa hàng tiện lợi",
        "Chợ truyền thống",
        "Sàn thương mại điện tử",
    ]
    p["entry.1718100848"] = random.sample(b2_opts, random.randint(1, 3))

    b3_opts = [
        "Hương vị",
        "Giá bán",
        "Thành phần/nguyên liệu",
        "Giá trị dinh dưỡng",
        "Độ an toàn vệ sinh thực phẩm",
        "Sự tiện lợi",
    ]
    p["entry.1558075595"] = random.sample(b3_opts, random.randint(1, 2))

    p["entry.1806152078"] = random.choices(
        ["Ít quan tâm", "Bình thường", "Khá quan tâm", "Rất quan tâm"],
        weights=[8, 25, 45, 22],
        k=1,
    )[0]

    b5_opts = [
        "Thành phần nguyên liệu tự nhiên",
        "Có giá trị dinh dưỡng",
        "Hạn chế nguyên liệu động vật",
        "Phù hợp với chế độ ăn chay",
        "Ít chất béo",
        "Tiện lợi khi sử dụng",
        "Hương vị mới lạ",
    ]
    p["entry.526300627"] = random.sample(b5_opts, random.randint(2, 4))

    # === PHẦN C (Trang 2) ===
    p["entry.1469967758"] = random.choices(
        ["Ít hấp dẫn", "Bình thường", "Hấp dẫn", "Rất hấp dẫn"], weights=[15, 50, 25, 10], k=1
    )[0]
    p["entry.440650413"] = random.choices(
        ["Bình thường", "Hấp dẫn", "Rất hấp dẫn"], weights=[8, 55, 37], k=1
    )[0]
    p["entry.1502137396"] = random.choices(
        ["Ít hấp dẫn", "Bình thường", "Hấp dẫn", "Rất hấp dẫn"], weights=[15, 45, 30, 10], k=1
    )[0]
    p["entry.177598363"] = random.choices(
        ["Pate chay hạt sen kết hợp nấm", "Bơ hạt sen", "Mì hạt sen", "Cả ba sản phẩm đều có tiềm năng"],
        weights=[82, 8, 5, 5],
        k=1,
    )[0]

    c3_opts = [
        "Sản phẩm mới lạ, chưa phổ biến trên thị trường",
        "Nguyên liệu quen thuộc, dễ tiếp cận",
        "Có hương vị hấp dẫn",
        "Có giá trị dinh dưỡng",
        "Tiện lợi trong quá trình sử dụng",
        "Có tiềm năng thay thế một số sản phẩm hiện có",
    ]
    p["entry.927653105"] = random.sample(c3_opts, random.randint(1, 2))

    # === PHẦN D: MÌ HẠT SEN (Trang 3) ===
    p["entry.1419574487"] = random.choices(
        ["Ít hơn 1 lần/tháng", "1–3 lần/tháng", "1–3 lần/tuần", "Trên 3 lần/tuần"],
        weights=[20, 45, 25, 10],
        k=1,
    )[0]
    d_mi_opts = [
        "Độ dai của sợi mì",
        "Hương vị",
        "Mùi hạt sen",
        "Giá trị dinh dưỡng",
        "Thành phần tự nhiên",
        "Không sử dụng chất bảo quản",
        "Giá bán",
    ]
    p["entry.1010902062"] = random.sample(d_mi_opts, random.randint(2, 3))
    p["entry.1024169457"] = random.choices(
        ["Từ 200 g đến dưới 250 g", "Từ 250 g đến dưới 400 g"], weights=[55, 45], k=1
    )[0]
    p["entry.406266138"] = random.choices(
        ["Dưới 20.000 đồng", "20.000–30.000 đồng", "30.000–40.000 đồng"], weights=[25, 55, 20], k=1
    )[0]

    # === PATE HẠT SEN (Trang 4) ===
    p["entry.923617261"] = random.choices(
        ["Chưa bao giờ", "Hiếm khi", "Thỉnh thoảng", "Thường xuyên"], weights=[15, 30, 35, 20], k=1
    )[0]
    p["entry.1927410635"] = random.sample(
        ["Nấm đông cô", "Nấm bào ngư", "Nấm rơm", "Nấm đùi gà"], random.randint(1, 2)
    )
    pate_dac_tinh = [
        "Kết cấu mịn, đồng nhất",
        "Mềm, dễ phết lên bánh mì",
        "Có độ béo vừa phải",
        "Có mùi thơm đặc trưng của hạt sen",
        "Hương vị đậm đà, dễ ăn",
        "Không bị tách nước/tách dầu",
    ]
    p["entry.2006585611"] = random.sample(pate_dac_tinh, random.randint(2, 4))
    p["entry.955938042"] = random.choices(
        ["Từ 100 g đến dưới 150 g", "Từ 150 g đến dưới 200 g", "Dưới 100 g"], weights=[60, 25, 15], k=1
    )[0]
    p["entry.1453250125"] = random.choices(
        ["45.000–55.000 đồng", "Dưới 45.000 đồng", "55.000–65.000 đồng"], weights=[55, 25, 20], k=1
    )[0]

    # === BƠ HẠT SEN (Trang 5) ===
    p["entry.7458628"] = random.choices(
        ["Chưa bao giờ", "Hiếm khi", "Thỉnh thoảng", "Thường xuyên"], weights=[20, 35, 30, 15], k=1
    )[0]
    bo_opts = [
        "Vị hạt sen rõ",
        "Vị béo, thơm",
        "Kết cấu mịn",
        "Dễ phết lên bánh mì",
        "Ít ngọt",
        "Thành phần tự nhiên",
        "Giá hợp lý",
    ]
    p["entry.625561673"] = random.sample(bo_opts, random.randint(2, 4))
    p["entry.480460579"] = random.choices(
        ["Từ 100 g đến dưới 150 g", "Từ 150 g đến dưới 200 g", "Dưới 100 g"], weights=[55, 30, 15], k=1
    )[0]
    p["entry.732092531"] = random.choices(
        ["30.000–40.000 đồng", "40.000–50.000 đồng", "Dưới 30.000 đồng"], weights=[50, 30, 20], k=1
    )[0]

    # === PHẦN E: CẢM QUAN PATE (Trang 6) ===
    p["entry.1385269180"] = random.choices(
        [
            "Vị hòa quyện cân bằng giữa hạt sen và nấm",
            "Vị thơm và đậm đà đặc trưng của nấm",
            "Vị bùi, béo nhẹ của hạt sen",
        ],
        weights=[55, 25, 20],
        k=1,
    )[0]
    p["entry.646888957"] = random.choices(["Vừa phải", "Đậm"], weights=[55, 45], k=1)[0]
    p["entry.598220533"] = random.choices(["Vừa phải", "Đậm"], weights=[60, 40], k=1)[0]
    p["entry.2010068962"] = random.choices(["Vừa phải", "Đậm"], weights=[70, 30], k=1)[0]
    p["entry.597209355"] = random.choices(["Vừa phải", "Nhẹ"], weights=[75, 25], k=1)[0]
    p["entry.1170571586"] = random.choices(["Vừa phải", "Nhẹ"], weights=[75, 25], k=1)[0]

    p["entry.188298218"] = random.sample(
        [
            "Mùi thơm tự nhiên của hạt sen",
            "Mùi thơm đặc trưng của nấm",
            "Mùi thơm hài hòa giữa các nguyên liệu",
            "Mùi thơm của gia vị và thảo mộc",
        ],
        random.randint(1, 2),
    )
    p["entry.62203359"] = random.choices(
        ["Chấp nhận nếu mùi nấm hài hòa với hạt sen", "Thích mùi nấm đặc trưng rõ rệt", "Không thích mùi nấm quá rõ"],
        weights=[70, 22, 8],
        k=1,
    )[0]
    p["entry.269962237"] = random.sample(
        ["Sánh, mềm và dễ phết", "Mịn nhưng vẫn có một ít phần thịt nấm", "Mịn hoàn toàn, không có hạt lợn cợn"],
        random.randint(1, 2),
    )
    p["entry.1905097545"] = random.choices(
        ["Màu sắc tự nhiên kết hợp giữa hạt sen và nấm", "Nâu nhạt", "Vàng nhạt"],
        weights=[50, 35, 15],
        k=1,
    )[0]

    cq_opts = [
        "Hương vị hài hòa",
        "Mùi thơm hấp dẫn",
        "Kết cấu mềm mịn",
        "Dễ phết và dễ sử dụng",
        "Độ béo vừa phải",
    ]
    p["entry.1567799875"] = random.sample(cq_opts, random.randint(2, 3))

    # === PHẦN F: TÂM LÝ & THƯƠNG MẠI HÓA (Trang 7) ===
    ngan_ngai_opts = [
        "Chưa từng sử dụng sản phẩm tương tự",
        "Lo ngại hương vị không phù hợp",
        "Chưa tin tưởng vào chất lượng sản phẩm mới",
        "Lo ngại sản phẩm không đảm bảo an toàn thực phẩm",
        "Giá bán cao",
    ]
    p["entry.1012420233"] = random.sample(ngan_ngai_opts, random.randint(1, 3))
    p["entry.701147640"] = random.choices(
        ["Rất hứng thú và muốn trải nghiệm", "Khá hứng thú", "Bình thường"], weights=[55, 38, 7], k=1
    )[0]

    tin_tuong_opts = [
        "Có bảng thành phần nguyên liệu rõ ràng",
        "Có chứng nhận an toàn vệ sinh thực phẩm",
        "Có nguồn gốc nguyên liệu rõ ràng",
        "Được dùng thử trước khi mua",
        "Được sản xuất bởi thương hiệu uy tín",
    ]
    p["entry.1236132141"] = random.sample(tin_tuong_opts, random.randint(1, 3))

    p["entry.548135944"] = random.choices(
        ["Chắc chắn có", "Có lẽ có", "Chưa chắc chắn"], weights=[45, 48, 7], k=1
    )[0]
    p["entry.1320349930"] = random.choices(
        ["Hũ thủy tinh", "Hũ nhựa thực phẩm", "Hộp nhựa có nắp đậy"], weights=[62, 24, 14], k=1
    )[0]

    canh_tranh_opts = [
        "Hương vị thơm ngon, khác biệt",
        "Chất lượng và độ an toàn thực phẩm",
        "Giá bán hợp lý",
        "Thành phần nguyên liệu tự nhiên",
        "Giá trị dinh dưỡng",
    ]
    p["entry.439280750"] = random.sample(canh_tranh_opts, random.randint(1, 3))

    p["entry.1324061877"] = random.choices(
        ["Từ 15–30 ngày", "Từ 1–3 tháng", "Từ 7–15 ngày"], weights=[42, 38, 20], k=1
    )[0]
    p["entry.1273510568"] = random.choices(
        ["Sẵn sàng", "Cân nhắc tùy theo mức giá", "Hoàn toàn sẵn sàng"], weights=[55, 25, 20], k=1
    )[0]

    gop_y_list = [
        "Sản phẩm rất mới lạ và tiềm năng, chúc nhóm sớm ra mắt thị trường!",
        "Nên đóng gói hũ thủy tinh nhỏ gọn 120g tiện dùng thử.",
        "Mong muốn vị béo vừa phải, không bị ngấy, thơm mùi nấm tự nhiên.",
        "Nếu có phiên bản cay nhẹ hoặc có tiêu hạt ăn kèm bánh mì sẽ rất ngon.",
        "Cần ghi rõ hạn sử dụng và hướng dẫn bảo quản sau khi mở nắp.",
    ]
    p["entry.2039170889"] = random.choice(gop_y_list)

    p["fvv"] = "1"
    p["pageHistory"] = PAGE_HISTORY
    return p


def submit_sample(payload):
    encoded = urllib.parse.urlencode(payload, doseq=True).encode("utf-8")
    req = urllib.request.Request(
        FORM_URL,
        data=encoded,
        headers={
            "User-Agent": random.choice(USER_AGENTS),
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        body = resp.read().decode("utf-8", errors="ignore")
        ok = ("freebirdFormviewerViewResponseError" not in body) and (resp.status == 200)
        return resp.status, ok


def main():
    parser = argparse.ArgumentParser(description="Chạy khảo sát Pate Hạt Sen (độc lập, đủ 8 trang)")
    parser.add_argument("--samples", type=int, default=20, help="Số lượng mẫu cần gửi (mặc định: 20)")
    parser.add_argument("--min-delay", type=int, default=20, help="Giãn cách tối thiểu (giây)")
    parser.add_argument("--max-delay", type=int, default=60, help="Giãn cách tối đa (giây)")
    parser.add_argument("--dry-run", action="store_true", help="Chạy thử không gửi lên Google Forms")
    args = parser.parse_args()

    print("=" * 65)
    print(f"PATE HẠT SEN STANDALONE | Số mẫu: {args.samples} | pageHistory: {PAGE_HISTORY}")
    print("=" * 65)

    if args.dry_run:
        sample = generate_sample()
        print(f"[DRY-RUN] Tổng số trường: {len(sample)} (48 câu hỏi + fvv + pageHistory)")
        print(f"[DRY-RUN] pageHistory = {sample['pageHistory']}")
        for eid in [
            "entry.1012420233",
            "entry.701147640",
            "entry.1236132141",
            "entry.548135944",
            "entry.1320349930",
            "entry.439280750",
            "entry.1324061877",
            "entry.1273510568",
            "entry.2039170889",
        ]:
            print(f"  {eid}: {sample.get(eid)}")
        return

    ok_count = 0
    fail_count = 0
    for i in range(1, args.samples + 1):
        sample = generate_sample()
        now_str = time.strftime("%H:%M:%S")
        try:
            status, valid = submit_sample(sample)
            if valid:
                ok_count += 1
                print(f"[{i}/{args.samples}] {now_str} | Gửi thành công (HTTP {status})")
            else:
                fail_count += 1
                print(f"[{i}/{args.samples}] {now_str} | Google Forms từ chối (HTTP {status})")
        except Exception as e:
            fail_count += 1
            print(f"[{i}/{args.samples}] {now_str} | Lỗi: {e}")

        if i < args.samples:
            time.sleep(random.uniform(args.min_delay, args.max_delay))

    print("=" * 65)
    print(f"HOÀN TẤT: Thành công {ok_count}/{args.samples} | Lỗi: {fail_count}")
    print("=" * 65)


if __name__ == "__main__":
    main()
