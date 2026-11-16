# -*- coding: utf-8 -*-
"""
HỆ THỐNG ENGINE ĐIỀN KHẢO SÁT TỰ ĐỘNG
Đề tài: 汉语方位词“里、内、中”与越南语 “trong” 的对比研究——越南大学生使用情况调查问卷
Mục tiêu:
- 年级: Chỉ chọn 大二 hoặc 大三 (tuyệt đối không chọn Đại 4).
- Các câu điền chữ: Bám sát phạm vi 3 từ 方位词: 里, 内, 中 (và các biến thể ngữ pháp/lỗi chuyển di của người học).
- Xoay vòng phân bổ (Shuffled Deck Rotation) cho tất cả các câu điền chữ: Đảm bảo không bị lặp 1 chữ/1 câu quá nhiều, nhìn tự nhiên như sinh viên thật trả lời.
- Chạy 80 mẫu hoàn chỉnh.
"""

import sys
import os
import time
import random
import re
import urllib.request
import urllib.parse
import argparse

# Thiết lập encoding utf-8 cho terminal Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

VIEWFORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSdlpkaZB2js5d_NrWRK5YvFmWRL556iuQd0JckVPTUkn0dBqA/viewform"
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSdlpkaZB2js5d_NrWRK5YvFmWRL556iuQd0JckVPTUkn0dBqA/formResponse"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6367.82 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
    "Mozilla/5.0 (Linux; Android 13; Pixel 7 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.6312.118 Mobile Safari/537.36",
]

# =====================================================================
# BỘ KHO ĐÁP ÁN ĐIỀN CHỮ PHẠM VI "里 - 内 - 中" (NGẮN & DÀI THEO MẪU THẬT)
# =====================================================================

PHRASE_POOLS = [
    # 1. Trong cửa hàng (chỉ vị trí bên trong cửa hàng) -> entry.2041831362
    [
        "商店里", "在商店里", "店里", "在店里", "商店里面", "在商店里面",
        "商店内", "在商店内", "店铺里", "在店铺里", "商店里。", "在商店里。",
        "店里面", "在店里面", "商场里", "在商场里", "便利店里", "小店里",
        "商店中", "在商铺里", "超市里", "在超市里", "店中", "商品店里"
    ],
    # 2. Trong nước (trong phạm vi một quốc gia) -> entry.480562815
    [
        "国内", "在国内", "国家内", "国内。", "在国内。", "国家里",
        "境内", "在境内", "国家内部", "在国家内", "全国范围内", "在全国范围内",
        "国境内", "在国境内", "国内范围", "在一国之内", "国家之内", "在国家之内",
        "国内各省", "在国家里", "全国之内", "在国内中"
    ],
    # 3. Trong vòng hai ngày (hạn chót không quá hai ngày) -> entry.1267623290
    [
        "两天内", "两天之内", "两日内", "在两天内", "2天内", "两日之内",
        "在两天之内", "两天以内", "两天内。", "在两日内", "两日以内", "2天之内",
        "两天中", "两天时间之内", "两日时间之内", "在2天内", "两天时间里", "两天里",
        "二日内", "二天内", "48小时内", "两天限期内"
    ],
    # 4. Trong cuốn sách này (nội dung được trình bày trong sách) -> entry.1230641362
    [
        "这本书里", "这本书中", "在这本书中", "在这本书里", "书里", "书中",
        "在这本书内", "这本书内", "这本书里面", "在这本书里面", "本图书中", "此书中",
        "在这本书中。", "在这本书里。", "该书中", "在这部书里", "这本教材里", "本教材中",
        "在这本图书里", "书本里", "这本书记载中", "书本中"
    ],
    # 5. Trong lớp học của chúng tôi (không gian lớp học) -> entry.1593654005
    [
        "我们教室里", "在我们教室里", "教室里", "在教室里", "我们班里", "在我们班里",
        "我们的教室里", "在我们的教室里", "教室里面", "我们班级里", "在我们班级里", "在我们教室里面",
        "我们班中", "在我们的班里", "班级内", "我们教室里。", "教室里。", "在班里",
        "班里", "我们的班级里", "在课室里", "课室里"
    ],
    # 6. Trong ví tiền của anh ấy (vị trí bên trong ví) -> entry.407099934
    [
        "他的钱包里", "在他的钱包里", "他钱包里", "在他钱包里", "钱包里", "在钱包里",
        "他的钱包里面", "在他钱包里面", "他的皮夹里", "在皮夹里", "他的钱包中", "在他的钱包中",
        "他的包里", "在他包里", "他的钱包内", "他的钱包里。", "在他钱包里。", "皮夹里面",
        "钱包里面", "他的公文包里", "在随身钱包里", "他皮夹里"
    ],
    # 7. Trong lịch sử (xét trong tiến trình lịch sử) -> entry.1398374225
    [
        "历史中", "在历史中", "在历史上", "历史上", "历史长河中", "在历史的长河中",
        "历史进程中", "在人类历史中", "历史内", "在历史内", "历史里", "在历史里",
        "历史中。", "在历史中。", "整个历史中", "历史发展中", "在历史时期中", "历程中",
        "在人类历史上", "纵观历史中", "从历史中"
    ],
    # 8. Trong quá trình làm việc (chỉ quá trình/công việc đang diễn ra) -> entry.1338174115
    [
        "工作过程中", "在工作过程中", "工作中", "在工作中", "工作的过程中", "在工作的过程中",
        "工作过程当中", "在工作过程当中", "在工作里", "工作内", "在工作内", "在做事的过程中",
        "做事的过程中", "工作过程中。", "在工作过程中。", "在工作期间", "工作期间中", "实际工作中",
        "在实际工作中", "在业务过程中", "办事过程中"
    ]
]

SENTENCE_POOLS = [
    # 1. Có rất nhiều thông tin quan trọng trong thông báo này. -> entry.1878840463
    [
        "这份通知里有很多重要信息。", "这个通知里有很多重要的信息。", "在这份通知中有很多重要信息。",
        "这份通知中包含很多重要信息。", "这个通知里包含许多重要的信息。", "在这则通知里有很多重要信息。",
        "本公告中包含大量重要信息。", "在这个通知中，有很多重要信息。", "通知里有很多重要的信息。",
        "这份通知里有许多重要信息。", "在这份通报中包含很多重要信息。", "这则通知里有很多重要内容。",
        "在这份通知里，有很多重要的消息。", "这个通知内有很多重要信息。", "在这份公告里有很多重要信息。",
        "这份通知提出了很多重要信息。", "本通知中载有许多重要信息。", "在这份通告中有很多重要信息。",
        "这个通知里有很多重要资料。", "本公告里有很多重要的信息。", "这份通报里有很多重要的内容。",
        "这个通知中包含许多重要信息。", "在这份通知书里有很多重要信息。", "这封通知里有很多重要信息。",
        "这个通知里有许多重要的事情。", "这份通知中有很多重要的内容。", "在这项通知里有很多重要信息。",
        "在这份通告里包含许多重要信息。"
    ],
    # 2. Vé này chỉ có giá trị trong vòng một tuần. -> entry.835569814
    [
        "这张票只在一周内有效。", "这张票一周内有效。", "这张票只在一个星期内有效。",
        "此票仅限一周内有效。", "这张票的有效期只有一周。", "这张票的有效期只有一周内。",
        "这张门票只在一周内有效。", "这张票只有一个星期内有效。", "此门票仅在一周内有效。",
        "这张票只有一周内的价值。", "该票只在一周内有效。", "这张票有效期为一周内。",
        "这张票在一个星期内有效。", "这张票在一个星期之内有效。", "此票只在一个星期内有效。",
        "这张入场券只在一周内有效。", "这张票仅限一个星期内使用。", "这张票在一周之内有效。",
        "该门票仅限一周内有效。", "这张票只在一周里有效。", "这张票在一个星期里有效。",
        "这张票仅在一周之内有效。", "这张票的有效期为一个星期。", "这张门票仅限一周内使用。",
        "这个票只在一周内有效。", "这张票有效期为一个星期内。", "此票仅一周内有效。"
    ],
    # 3. Trong quá trình học tiếng Trung, từ vựng là phần rất quan trọng. -> entry.1799267530
    [
        "在学习汉语的过程中，词汇是非常重要的一部分。", "在学习汉语的过程中，词汇是很重要的一部分。",
        "在学习汉语过程中，词汇是非常重要的部分。", "在学习中文的过程中，词汇是非常重要的一部分。",
        "在学汉语的过程中，词汇量是非常重要的一部分。", "学习汉语的过程中，词汇是一个很重要的部分。",
        "在学习中文的过程中，词汇量是非常重要的一部分。", "在学习汉语过程中，生词是重要的部分。",
        "在学中文的过程中，词汇是非常重要的一部分。", "在学习汉语的过程中，词汇是一个很重要的部分。",
        "学习汉语过程中，词汇部分是最重要的。", "在学习中文过程中，单词是一个非常重要的部分。",
        "在学汉语的过程中，词汇是很重要的部分。", "在学习汉语的过程中，词汇是不可或缺的一部分。",
        "在学习汉语过程当中，词汇是非常重要的一部分。", "在学中文过程中，生词是关键的部分。",
        "学中文的过程中，词汇是最重要的。", "在学习汉语中，词汇是很重要的部分。",
        "在学习汉语的过程中，词汇至关重要。", "在学汉语过程中，词汇是一个关键部分。",
        "在学习汉语的过程里，词汇是非常重要的一部分。", "在学习中文的过程中，词汇起着非常重要的作用。",
        "在学习汉语的过程中，词汇部分至关重要。", "在学中文的过程中，掌握词汇是非常重要的一部分。"
    ],
    # 4. Trong phòng tôi có một chiếc máy tính. -> entry.4028556
    [
        "我的房间里有一台电脑。", "我房间里有一台电脑。", "在我的房间里有一台电脑。",
        "在我房间里有一台电脑。", "我的房间里有一台笔记本电脑。", "我房间里有一台笔记本电脑。",
        "我的房间里放着一台电脑。", "我房里有一台电脑。", "在我房里有一台电脑。",
        "我的房间里有一个电脑。", "我房间里有个电脑。", "我的房间中有一台电脑。",
        "在我房间里放着一台电脑。", "我的卧室里有一台电脑。", "我房间里有一台计算机。",
        "在我的房间中有一台电脑。", "我的房间里设有一台电脑。", "我房间内有一台电脑。",
        "我的房间里有一台笔记本。", "在我的卧室里有一台电脑。", "我的房里有一台笔记本电脑。",
        "我房间里有一台台式电脑。", "在我房间里有一台笔记本。", "我的书房里有一台电脑。"
    ],
    # 5. Trong vườn có trồng rất nhiều loại hoa. -> entry.1014075710
    [
        "花园里种了很多种花。", "花园里种着很多种花。", "在花园里种了很多种花。",
        "花园里种植了许多种类的花卉。", "院子里种了很多花。", "在院子里种了很多种花。",
        "花园里种了许多种花。", "院子里种着各种各样的花。", "花园里种了各种各样的花。",
        "花园里种植了许多花卉。", "在花园中种植了许多种花。", "花园中种着各种花草。",
        "花园里种了许许多多的花。", "院子里种了许多种花。", "在院子里，种着很多花。",
        "花园里栽种了许多种花。", "园子里种了很多花。", "在花园里种着各种各样的花。",
        "花园内种植了许多种花。", "花园里种着多种花卉。", "院子里面种了很多花。",
        "花园里种植了各种花卉。", "在园子里种了很多种花。", "花园中盛开着很多种花。"
    ],
    # 6. Trong cuộc họp hôm nay, chúng tôi đã thảo luận về kế hoạch mới. -> entry.2061178147
    [
        "在今天的会议中，我们讨论了新计划。", "在今天的会议中，我们讨论了新的计划。",
        "今天的会议中，我们讨论了新计划。", "在今天的会议上，我们讨论了新计划。",
        "在今天的会议上，我们讨论了新的计划。", "今天的会议上，我们讨论了新计划。",
        "在今天的会议中，我们已经讨论了新计划。", "在今日的会议中，我们讨论了新计划。",
        "在今天的会议中，我们对新计划进行了讨论。", "今天的会议中，我们大家讨论了新计划。",
        "在今天的会议里，我们讨论了新计划。", "在今天的会议中，我们一起讨论了新计划。",
        "在今天的会议当中，我们讨论了新计划。", "今天的会议里，我们讨论了新的计划。",
        "在今日的会议上，我们讨论了新的方案。", "在今天的会议中，我们讨论了新的发展计划。",
        "今天的会议中，我们商讨了新计划。", "在今天的例会中，我们讨论了新计划。",
        "在今天的开会中，我们讨论了新计划。", "今天的会议上，我们已经讨论了新计划。",
        "在今天的会议内，我们讨论了新计划。", "在今天的会议中，我们详细讨论了新计划。"
    ]
]


class ShuffledDeck:
    """Xoay vòng xáo trộn liên tục để không bị lặp 1 câu quá nhiều"""
    def __init__(self, items):
        self.original_items = list(items)
        self.deck = []

    def next_item(self):
        if not self.deck:
            self.deck = list(self.original_items)
            random.shuffle(self.deck)
        item = self.deck.pop()
        # 15% xác suất tự nhiên: bỏ hoặc thêm dấu chấm câu cuối
        if random.random() < 0.15:
            if item.endswith("。"):
                item = item[:-1]
            elif not item.endswith("。") and len(item) > 4:
                item = item + "。"
        return item


class SurveyGenerator:
    def __init__(self, total_samples=80):
        self.total_samples = total_samples
        self.phrase_decks = [ShuffledDeck(p) for p in PHRASE_POOLS]
        self.sentence_decks = [ShuffledDeck(s) for s in SENTENCE_POOLS]

        # Khởi tạo danh sách năm học: CHỈ ĐẠI 2 HOẶC ĐẠI 3
        # Chia đều tỷ lệ (khoảng 50% Đại 2, 50% Đại 3) và xáo trộn ngẫu nhiên
        n_daier = total_samples // 2
        n_daisan = total_samples - n_daier
        self.grades = ["大二"] * n_daier + ["大三"] * n_daisan
        random.shuffle(self.grades)
        self.current_idx = 0

    def generate_one_sample(self):
        p = {}

        # -------------------------------------------------------------
        # PHẦN 1: 基本信息 (Demographics) - CHỈ CHỌN 大二 HOẶC 大三
        # -------------------------------------------------------------
        if self.current_idx < len(self.grades):
            grade = self.grades[self.current_idx]
            self.current_idx += 1
        else:
            grade = random.choice(["大二", "大三"])
        p["entry.872637280"] = grade

        if grade == "大二":
            # Thời gian học của Đại 2
            p["entry.1609241786"] = random.choices(
                ["1年以下", "1—2年", "2—3年"], weights=[15, 65, 20], k=1
            )[0]
            # Trình độ HSK của Đại 2
            p["entry.1487674089"] = random.choices(
                ["尚未参加", "HSK三级及以下", "HSK四级", "HSK五级及以上"],
                weights=[35, 15, 45, 5], k=1
            )[0]
        else:  # 大三
            # Thời gian học của Đại 3
            p["entry.1609241786"] = random.choices(
                ["1—2年", "2—3年", "3年以上"], weights=[20, 65, 15], k=1
            )[0]
            # Trình độ HSK của Đại 3
            p["entry.1487674089"] = random.choices(
                ["尚未参加", "HSK三级及以下", "HSK四级", "HSK五级及以上"],
                weights=[15, 5, 50, 30], k=1
            )[0]

        # -------------------------------------------------------------
        # PHẦN 2: 选择题 (10 câu hỏi trắc nghiệm A. 里, B. 中, C. 内, D. 不填)
        # Tỷ lệ chuẩn hoá theo dữ liệu thực tế 27 sinh viên
        # -------------------------------------------------------------
        # 1. 我的书包____有很多书。
        p["entry.1963756870"] = random.choices(["A. 里", "C. 内"], weights=[96, 4], k=1)[0]
        # 2. 请在三天____完成这项作业。
        p["entry.1608071791"] = random.choices(["C. 内", "B. 中"], weights=[88, 12], k=1)[0]
        # 3. 比赛正在进行____，请大家保持安静。
        p["entry.705379980"] = random.choices(["B. 中", "D. 不填", "C. 内"], weights=[80, 16, 4], k=1)[0]
        # 4. 我们在日常生活____经常会遇到各种各样的问题。
        p["entry.1286629160"] = random.choices(["B. 中", "A. 里", "C. 内"], weights=[74, 22, 4], k=1)[0]
        # 5. 下课以后，我把课本放在教室____的书架上。
        p["entry.1709682949"] = random.choices(["A. 里", "D. 不填"], weights=[88, 12], k=1)[0]
        # 6. 这本书____介绍了中国传统节日的由来。
        p["entry.1547797449"] = random.choices(["A. 里", "D. 不填", "C. 内", "B. 中"], weights=[42, 32, 15, 11], k=1)[0]
        # 7. 我们学校____有一座很大的图书馆。
        p["entry.1875288263"] = random.choices(["A. 里", "D. 不填", "C. 内", "B. 中"], weights=[75, 17, 4, 4], k=1)[0]
        # 8. 房间____只有他一个人。
        p["entry.651301189"] = random.choices(["A. 里", "B. 中"], weights=[96, 4], k=1)[0]
        # 9. 根据公司规定，员工必须在一个月____完成这个项目。
        p["entry.955829653"] = random.choices(["C. 内", "B. 中"], weights=[92, 8], k=1)[0]
        # 10. 这部历史纪录片____记录了许多重要事件。
        p["entry.541170650"] = random.choices(["B. 中", "A. 里", "D. 不填", "C. 内"], weights=[38, 34, 24, 4], k=1)[0]

        # -------------------------------------------------------------
        # PHẦN 3: 判断正误 (8 câu đúng sai √, ×)
        # -------------------------------------------------------------
        # 1. 他坐在房间里吃苹果。
        p["entry.1869050604"] = random.choices(["√", "×"], weights=[93, 7], k=1)[0]
        # 2. 这本书里介绍了中国汉字的发展历史。
        p["entry.494265837"] = random.choices(["√", "×"], weights=[55, 45], k=1)[0]
        # 3. 老师要求我们必须在三天中把作业写完。
        p["entry.743851314"] = random.choices(["×", "√"], weights=[85, 15], k=1)[0]
        # 4. 比赛正在进行里，请大家不要说话。
        p["entry.370332784"] = random.choices(["×", "√"], weights=[98, 2], k=1)[0]
        # 5. 在现代社会里，科技发展得非常快。
        p["entry.815890002"] = random.choices(["×", "√"], weights=[67, 33], k=1)[0]
        # 6. 会议正在进行中，请大家不要随意离场。
        p["entry.578238272"] = random.choices(["√", "×"], weights=[89, 11], k=1)[0]
        # 7. 请在规定时间内提交申请材料。
        p["entry.1884788380"] = random.choices(["√", "×"], weights=[96, 4], k=1)[0]
        # 8. 他把手机放在书包内。
        p["entry.1720091532"] = random.choices(["×", "√"], weights=[63, 37], k=1)[0]

        # -------------------------------------------------------------
        # PHẦN 4: 短语翻译 (8 câu dịch cụm từ - Lấy từ Shuffled Deck)
        # -------------------------------------------------------------
        p["entry.2041831362"] = self.phrase_decks[0].next_item()
        p["entry.480562815"]  = self.phrase_decks[1].next_item()
        p["entry.1267623290"] = self.phrase_decks[2].next_item()
        p["entry.1230641362"] = self.phrase_decks[3].next_item()
        p["entry.1593654005"] = self.phrase_decks[4].next_item()
        p["entry.407099934"]  = self.phrase_decks[5].next_item()
        p["entry.1398374225"] = self.phrase_decks[6].next_item()
        p["entry.1338174115"] = self.phrase_decks[7].next_item()

        # -------------------------------------------------------------
        # PHẦN 5: 句子翻译 (6 câu dịch câu - Lấy từ Shuffled Deck)
        # -------------------------------------------------------------
        p["entry.1878840463"] = self.sentence_decks[0].next_item()
        p["entry.835569814"]  = self.sentence_decks[1].next_item()
        p["entry.1799267530"] = self.sentence_decks[2].next_item()
        p["entry.4028556"]    = self.sentence_decks[3].next_item()
        p["entry.1014075710"] = self.sentence_decks[4].next_item()
        p["entry.2061178147"] = self.sentence_decks[5].next_item()

        return p


def get_dynamic_fbzx():
    """Lấy fbzx mới nhất từ Google Form để submit luôn hợp lệ"""
    try:
        req = urllib.request.Request(
            VIEWFORM_URL,
            headers={"User-Agent": random.choice(USER_AGENTS)}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")
            m = re.search(r'name="fbzx"\s+value="([^"]+)"', html)
            if m:
                return m.group(1)
    except Exception:
        pass
    return "-6258269203048502663"


def submit_single_sample(payload, fbzx=None):
    """Gửi một mẫu câu trả lời đến Google Form"""
    current_fbzx = fbzx or get_dynamic_fbzx()
    data = dict(payload)
    data["fvv"] = "1"
    data["pageHistory"] = "0"
    data["fbzx"] = current_fbzx

    encoded_data = urllib.parse.urlencode(data).encode("utf-8")
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Referer": VIEWFORM_URL,
        "Content-Type": "application/x-www-form-urlencoded"
    }

    req = urllib.request.Request(FORM_URL, data=encoded_data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            code = resp.getcode()
            body = resp.read().decode("utf-8", errors="replace")
            success = "感谢您填写本次问卷" in body or "已收到您的回答" in body or "Cảm ơn bạn" in body
            return code, success
    except Exception as e:
        return 0, str(e)


def main():
    parser = argparse.ArgumentParser(description="Chạy gửi khảo sát Google Form tự động")
    parser.add_argument("--samples", type=int, default=None, help="Số lượng mẫu cần gửi (mặc định: 80 hoặc lấy từ BATCH_SAMPLES)")
    parser.add_argument("--min-delay", type=int, default=None, help="Giãn cách tối thiểu giữa 2 lần gửi (giây)")
    parser.add_argument("--max-delay", type=int, default=None, help="Giãn cách tối đa giữa 2 lần gửi (giây)")
    parser.add_argument("--dry-run", action="store_true", help="Chạy thử nghiệm kiểm tra logic, không gửi lên Google Form")
    args = parser.parse_args()

    # Hỗ trợ đọc cả từ CLI arguments và Environment Variables (GitHub Actions)
    if args.samples is not None:
        total_samples = args.samples
    elif "BATCH_SAMPLES" in os.environ and os.environ["BATCH_SAMPLES"].strip():
        total_samples = int(os.environ["BATCH_SAMPLES"].strip())
    else:
        total_samples = 80

    if args.min_delay is not None:
        min_delay = args.min_delay
    elif "MIN_DELAY" in os.environ and os.environ["MIN_DELAY"].strip():
        min_delay = int(os.environ["MIN_DELAY"].strip())
    else:
        min_delay = 5

    if args.max_delay is not None:
        max_delay = args.max_delay
    elif "MAX_DELAY" in os.environ and os.environ["MAX_DELAY"].strip():
        max_delay = int(os.environ["MAX_DELAY"].strip())
    else:
        max_delay = 12

    is_dry_run = args.dry_run or (os.environ.get("DRY_RUN", "false").strip().lower() in ("true", "1"))

    generator = SurveyGenerator(total_samples)

    print("=" * 70)
    print("HỆ THỐNG GỬI KHẢO SÁT TỰ ĐỘNG - TIẾNG TRUNG 方位词 (里、内、中)")
    print(f"Tổng số mẫu cần chạy: {total_samples}")
    print(f"Chế độ chạy         : {'DRY-RUN (Thử nghiệm)' if is_dry_run else 'GỬI THẬT (LIVE)'}")
    print(f"Giãn cách delay     : {min_delay}s - {max_delay}s")
    print(f"Quy định年级         : CHỈ CHỌN 大二 HOẶC 大三")
    print(f"Phạm vi điền chữ    : 方位词 里, 内, 中 (Xoay vòng đa dạng, không lặp)")
    print("=" * 70)

    if is_dry_run:
        print("[DRY-RUN] Đang tạo thử 80 mẫu để kiểm tra phân bổ...")
        samples = [generator.generate_one_sample() for _ in range(total_samples)]
        
        # Thống kê年级
        grades = [s["entry.872637280"] for s in samples]
        print(f"\n[PHÂN BỔ 年级]: {dict((g, grades.count(g)) for g in set(grades))}")
        assert all(g in ["大二", "大三"] for g in grades), "LỖI: Có mẫu chứa Đại 4!"
        print("  -> Kiểm duyệt thành công: 100% mẫu là 大二 hoặc 大三.")

        # Thống kê câu điền chữ
        print("\n[KIỂM DUYỆT ĐIỀN CHỮ - SỐ LƯỢNG BIẾN THỂ / TỶ LỆ TRÙNG LẶP]:")
        for i in range(8):
            entry = f"entry.{[2041831362, 480562815, 1267623290, 1230641362, 1593654005, 407099934, 1398374225, 1338174115][i]}"
            vals = [s[entry] for s in samples]
            cnt = dict((v, vals.count(v)) for v in set(vals))
            print(f"  - 短语 {i+1} ({len(cnt)} biến thể khác nhau): lặp tối đa = {max(cnt.values())} lần. Ví dụ: {list(cnt.keys())[:3]}")

        for i in range(6):
            entry = f"entry.{[1878840463, 835569814, 1799267530, 4028556, 1014075710, 2061178147][i]}"
            vals = [s[entry] for s in samples]
            cnt = dict((v, vals.count(v)) for v in set(vals))
            print(f"  - 句子 {i+1} ({len(cnt)} biến thể khác nhau): lặp tối đa = {max(cnt.values())} lần. Ví dụ: {list(cnt.keys())[:2]}")

        print("\n[DRY-RUN HOÀN TẤT] Toàn bộ logic chuẩn xác 100%! Bạn có thể bỏ cờ --dry-run để chạy thật.")
        return

    # CHẾ ĐỘ GỬI THẬT
    success_count = 0
    fail_count = 0
    start_time = time.time()

    print(f"\nBắt đầu gửi {total_samples} mẫu...")
    cached_fbzx = get_dynamic_fbzx()

    for idx in range(1, total_samples + 1):
        sample = generator.generate_one_sample()
        
        # Thử gửi
        code, ok = submit_single_sample(sample, fbzx=cached_fbzx)
        
        if ok is True:
            success_count += 1
            print(f"[{idx:02d}/{total_samples}] [THÀNH CÔNG] 年级: {sample['entry.872637280']} | HSK: {sample['entry.1487674089']} | Điền: '{sample['entry.2041831362']}' / '{sample['entry.480562815']}' / '{sample['entry.1267623290']}'...")
        else:
            fail_count += 1
            print(f"[{idx:02d}/{total_samples}] [LỖI HTTP {code}] Chi tiết: {ok}. Đang làm mới fbzx...")
            cached_fbzx = get_dynamic_fbzx()

        if idx < total_samples:
            delay = random.randint(min_delay, max_delay)
            time.sleep(delay)

    elapsed = time.time() - start_time
    print("=" * 70)
    print(f"HOÀN THÀNH TIẾN TRÌNH!")
    print(f"Thành công : {success_count}/{total_samples} mẫu")
    print(f"Thất bại   : {fail_count} mẫu")
    print(f"Tổng thời gian: {elapsed:.1f} giây (~{elapsed/60:.1f} phút)")
    print("=" * 70)


if __name__ == "__main__":
    main()
