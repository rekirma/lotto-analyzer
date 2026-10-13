"""
analyzer.py: 로또 6/45 정밀 통계 및 패턴 분석 모듈
"""

import math
from collections import Counter, defaultdict


def calculate_ac(numbers):
    """
    AC값(산술적 복잡도, Arithmetic Complexity) 계산:
    6개 번호에서 두 수의 차이(절대값)들의 고유 개수 - (6 - 1)
    범위는 보통 0 ~ 10, 로또 당첨번호의 80% 이상이 7~10 사이에 분포함.
    """
    nums = sorted(numbers)
    diffs = set()
    n = len(nums)
    for i in range(n):
        for j in range(i + 1, n):
            diffs.add(nums[j] - nums[i])
    return len(diffs) - (n - 1)


def get_ball_color(num):
    """로또 공 색상 반환"""
    if 1 <= num <= 10:
        return "yellow"   # 1~10: 노랑
    elif 11 <= num <= 20:
        return "blue"     # 11~20: 파랑
    elif 21 <= num <= 30:
        return "red"      # 21~30: 빨강
    elif 31 <= num <= 40:
        return "gray"     # 31~40: 회색
    elif 41 <= num <= 45:
        return "green"    # 41~45: 초록
    return "default"


class LottoAnalyzer:
    def __init__(self, draws):
        """
        draws: list of dict (drw_no, date, num1~6, bonus, winner_count, prize_amount, etc.)
        기본적으로 회차 오름차순(1회 -> 최신회) 정렬되어 있다고 가정
        """
        self.draws = sorted(draws, key=lambda x: x["drw_no"])
        self.total_draws = len(self.draws)

    def get_latest_draw(self):
        if not self.draws:
            return None
        return self.draws[-1]

    def frequency_stats(self, recent_count=None):
        """
        번호별(1~45) 출현 빈도 통계
        recent_count: 최근 N회차만 분석하고 싶을 때 (None이면 전체)
        """
        target_draws = self.draws[-recent_count:] if recent_count else self.draws
        target_len = len(target_draws)

        main_counts = Counter()
        bonus_counts = Counter()

        for d in target_draws:
            nums = [d["num1"], d["num2"], d["num3"], d["num4"], d["num5"], d["num6"]]
            for num in nums:
                main_counts[num] += 1
            bonus_counts[d["bonus"]] += 1

        stats = []
        for n in range(1, 46):
            m_cnt = main_counts[n]
            b_cnt = bonus_counts[n]
            t_cnt = m_cnt + b_cnt
            prob = round((m_cnt / target_len) * 100, 2) if target_len > 0 else 0
            stats.append({
                "number": n,
                "main_count": m_cnt,
                "bonus_count": b_cnt,
                "total_count": t_cnt,
                "percentage": prob,
                "color": get_ball_color(n)
            })

        # 본 번호 출현 횟수 기준 정렬
        sorted_by_main = sorted(stats, key=lambda x: x["main_count"], reverse=True)
        for rank, item in enumerate(sorted_by_main, start=1):
            item["rank"] = rank

        hot_10 = sorted_by_main[:10]
        cold_10 = sorted_by_main[-10:][::-1]

        return {
            "total_analyzed_draws": target_len,
            "all_numbers": sorted(stats, key=lambda x: x["number"]),
            "ranked_numbers": sorted_by_main,
            "hot_10": hot_10,
            "cold_10": cold_10
        }

    def unappeared_stats(self):
        """
        미출현 번호 주기 분석:
        각 번호가 마지막으로 출현한 회차 및 현재 미출현 지속 회차수
        """
        if not self.draws:
            return {}

        latest_drw = self.draws[-1]["drw_no"]
        last_seen = {}  # number -> latest drw_no

        for d in self.draws:
            drw = d["drw_no"]
            nums = [d["num1"], d["num2"], d["num3"], d["num4"], d["num5"], d["num6"]]
            for num in nums:
                last_seen[num] = drw

        unappeared_list = []
        for n in range(1, 46):
            last_drw = last_seen.get(n, 0)
            gap = latest_drw - last_drw
            unappeared_list.append({
                "number": n,
                "last_draw": last_drw,
                "unappeared_count": gap,
                "color": get_ball_color(n)
            })

        # 가장 오랫동안 나오지 않은 순으로 정렬
        unappeared_sorted = sorted(unappeared_list, key=lambda x: x["unappeared_count"], reverse=True)

        # 5회 이상, 10회 이상, 15회 이상 미출현 번호 분류
        unappeared_5 = [item for item in unappeared_sorted if item["unappeared_count"] >= 5]
        unappeared_10 = [item for item in unappeared_sorted if item["unappeared_count"] >= 10]
        unappeared_15 = [item for item in unappeared_sorted if item["unappeared_count"] >= 15]

        return {
            "latest_draw": latest_drw,
            "unappeared_ranking": unappeared_sorted,
            "top_cold": unappeared_sorted[:10],
            "unappeared_over_5": unappeared_5,
            "unappeared_over_10": unappeared_10,
            "unappeared_over_15": unappeared_15
        }

    def odd_even_stats(self):
        """홀짝 비율 통계 (6:0, 5:1, 4:2, 3:3, 2:4, 1:5, 0:6)"""
        counts = Counter()

        for d in self.draws:
            nums = [d["num1"], d["num2"], d["num3"], d["num4"], d["num5"], d["num6"]]
            odd = sum(1 for n in nums if n % 2 != 0)
            even = 6 - odd
            pattern = f"{odd}:{even}"
            counts[pattern] += 1

        patterns = ["3:3", "2:4", "4:2", "1:5", "5:1", "0:6", "6:0"]
        result = []
        for pat in patterns:
            cnt = counts[pat]
            pct = round((cnt / self.total_draws) * 100, 2) if self.total_draws > 0 else 0
            result.append({
                "pattern": pat,
                "count": cnt,
                "percentage": pct
            })

        return {
            "total_draws": self.total_draws,
            "patterns": result
        }

    def section_stats(self):
        """
        구간대(색상)별 분포 분석:
        1~10 (노랑), 11~20 (파랑), 21~30 (빨강), 31~40 (회색), 41~45 (초록)
        """
        sec_counts = {
            "1-10": 0,
            "11-20": 0,
            "21-30": 0,
            "31-40": 0,
            "41-45": 0
        }
        total_balls = self.total_draws * 6

        for d in self.draws:
            nums = [d["num1"], d["num2"], d["num3"], d["num4"], d["num5"], d["num6"]]
            for n in nums:
                if 1 <= n <= 10:
                    sec_counts["1-10"] += 1
                elif 11 <= n <= 20:
                    sec_counts["11-20"] += 1
                elif 21 <= n <= 30:
                    sec_counts["21-30"] += 1
                elif 31 <= n <= 40:
                    sec_counts["31-40"] += 1
                elif 41 <= n <= 45:
                    sec_counts["41-45"] += 1

        sections = [
            {"label": "1~10번대 (노랑)", "key": "1-10", "count": sec_counts["1-10"], "color": "#fbc400", "ball_count": 10},
            {"label": "11~20번대 (파랑)", "key": "11-20", "count": sec_counts["11-20"], "color": "#69c8f2", "ball_count": 10},
            {"label": "21~30번대 (빨강)", "key": "21-30", "count": sec_counts["21-30"], "color": "#ff7272", "ball_count": 10},
            {"label": "31~40번대 (회색)", "key": "31-40", "count": sec_counts["31-40"], "color": "#aaa", "ball_count": 10},
            {"label": "41~45번대 (초록)", "key": "41-45", "count": sec_counts["41-45"], "color": "#b0d840", "ball_count": 5},
        ]

        for s in sections:
            s["percentage"] = round((s["count"] / total_balls) * 100, 2) if total_balls > 0 else 0
            # 공 1개당 평균 출현 횟수
            s["avg_per_ball"] = round(s["count"] / s["ball_count"], 1)

        return sections

    def sum_stats(self):
        """총합(Sum) 통계 분석 (최소, 최대, 평균, 분포 구간)"""
        sums = []
        brackets = {
            "~80": 0,
            "81~100": 0,
            "101~120": 0,
            "121~140": 0,
            "141~160": 0,
            "161~180": 0,
            "181~200": 0,
            "201~": 0
        }

        for d in self.draws:
            nums = [d["num1"], d["num2"], d["num3"], d["num4"], d["num5"], d["num6"]]
            s = sum(nums)
            sums.append(s)

            if s <= 80:
                brackets["~80"] += 1
            elif s <= 100:
                brackets["81~100"] += 1
            elif s <= 120:
                brackets["101~120"] += 1
            elif s <= 140:
                brackets["121~140"] += 1
            elif s <= 160:
                brackets["141~160"] += 1
            elif s <= 180:
                brackets["161~180"] += 1
            elif s <= 200:
                brackets["181~200"] += 1
            else:
                brackets["201~"] += 1

        if not sums:
            return {}

        min_s = min(sums)
        max_s = max(sums)
        avg_s = round(sum(sums) / len(sums), 1)
        sorted_s = sorted(sums)
        median_s = sorted_s[len(sorted_s) // 2]

        bracket_list = []
        for k, cnt in brackets.items():
            pct = round((cnt / self.total_draws) * 100, 2) if self.total_draws > 0 else 0
            bracket_list.append({"range": k, "count": cnt, "percentage": pct})

        # 100~175 범위 집중도 계산
        golden_count = sum(1 for s in sums if 100 <= s <= 175)
        golden_pct = round((golden_count / self.total_draws) * 100, 2)

        return {
            "min_sum": min_s,
            "max_sum": max_s,
            "avg_sum": avg_s,
            "median_sum": median_s,
            "golden_range_count": golden_count,
            "golden_range_percentage": golden_pct,
            "distribution": bracket_list
        }

    def consecutive_stats(self):
        """연속 번호(연번) 출현 빈도 통계"""
        pair_counts = Counter()  # 0쌍, 1쌍, 2쌍, 3쌍 이상
        triple_count = 0        # 3연속 번호

        for d in self.draws:
            nums = sorted([d["num1"], d["num2"], d["num3"], d["num4"], d["num5"], d["num6"]])
            pairs = 0
            has_triple = False
            for i in range(len(nums) - 1):
                if nums[i + 1] - nums[i] == 1:
                    pairs += 1
                    if i + 2 < len(nums) and nums[i + 2] - nums[i + 1] == 1:
                        has_triple = True

            pair_counts[pairs] += 1
            if has_triple:
                triple_count += 1

        result = [
            {"pairs": "연번 없음", "count": pair_counts[0], "percentage": round((pair_counts[0] / self.total_draws) * 100, 2)},
            {"pairs": "1쌍 연번", "count": pair_counts[1], "percentage": round((pair_counts[1] / self.total_draws) * 100, 2)},
            {"pairs": "2쌍 연번", "count": pair_counts[2], "percentage": round((pair_counts[2] / self.total_draws) * 100, 2)},
            {"pairs": "3쌍 이상 연번", "count": sum(pair_counts[k] for k in pair_counts if k >= 3), "percentage": round((sum(pair_counts[k] for k in pair_counts if k >= 3) / self.total_draws) * 100, 2)},
        ]

        return {
            "pair_stats": result,
            "triple_consecutive_count": triple_count,
            "triple_percentage": round((triple_count / self.total_draws) * 100, 2)
        }

    def ac_stats(self):
        """AC값(산술 복잡도) 분포 통계"""
        ac_counts = Counter()
        for d in self.draws:
            nums = [d["num1"], d["num2"], d["num3"], d["num4"], d["num5"], d["num6"]]
            ac = calculate_ac(nums)
            ac_counts[ac] += 1

        ac_list = []
        for ac_val in range(1, 11):
            cnt = ac_counts[ac_val]
            pct = round((cnt / self.total_draws) * 100, 2) if self.total_draws > 0 else 0
            ac_list.append({"ac": ac_val, "count": cnt, "percentage": pct})

        # 7~10 AC값 비율
        high_ac = sum(ac_counts[v] for v in range(7, 11))
        high_ac_pct = round((high_ac / self.total_draws) * 100, 2)

        return {
            "distribution": ac_list,
            "high_ac_percentage": high_ac_pct
        }

    def ending_digit_stats(self):
        """끝수(끝자리 0~9) 출현 통계"""
        end_counts = Counter()
        for d in self.draws:
            nums = [d["num1"], d["num2"], d["num3"], d["num4"], d["num5"], d["num6"]]
            for n in nums:
                end_counts[n % 10] += 1

        total_balls = self.total_draws * 6
        result = []
        for digit in range(10):
            cnt = end_counts[digit]
            pct = round((cnt / total_balls) * 100, 2) if total_balls > 0 else 0
            result.append({"digit": digit, "count": cnt, "percentage": pct})

        return sorted(result, key=lambda x: x["count"], reverse=True)

    def prize_stats(self):
        """역대 당첨금 및 당첨자수 하이라이트 통계"""
        if not self.draws:
            return {}

        max_prize_draw = max(self.draws, key=lambda x: x.get("prize_amount", 0))
        max_winners_draw = max(self.draws, key=lambda x: x.get("winner_count", 0))

        valid_prizes = [d["prize_amount"] for d in self.draws if d.get("prize_amount", 0) > 0]
        avg_prize = round(sum(valid_prizes) / len(valid_prizes)) if valid_prizes else 0

        valid_winners = [d["winner_count"] for d in self.draws if d.get("winner_count", 0) > 0]
        avg_winners = round(sum(valid_winners) / len(valid_winners), 1) if valid_winners else 0

        total_auto = sum(d.get("auto_count", 0) for d in self.draws)
        total_manual = sum(d.get("manual_count", 0) for d in self.draws)
        total_semi = sum(d.get("semi_auto_count", 0) for d in self.draws)
        total_methods = total_auto + total_manual + total_semi

        return {
            "max_prize": {
                "amount": max_prize_draw.get("prize_amount", 0),
                "draw_no": max_prize_draw.get("drw_no", 0),
                "date": max_prize_draw.get("date", "")
            },
            "max_winners": {
                "count": max_winners_draw.get("winner_count", 0),
                "draw_no": max_winners_draw.get("drw_no", 0),
                "date": max_winners_draw.get("date", ""),
                "amount": max_winners_draw.get("prize_amount", 0)
            },
            "avg_prize": avg_prize,
            "avg_winners": avg_winners,
            "method_ratio": {
                "auto": total_auto,
                "manual": total_manual,
                "semi_auto": total_semi,
                "auto_pct": round((total_auto / total_methods) * 100, 1) if total_methods > 0 else 0,
                "manual_pct": round((total_manual / total_methods) * 100, 1) if total_methods > 0 else 0,
            }
        }

    def get_matching_draws(self, target_draw_no):
        """
        특정 기준 회차(target_draw_no)의 당첨번호 6개와
        다른 모든 회차들의 일치 개수(5개, 4개, 3개, 2개)를 정밀 분석하여 반환.
        """
        target = None
        for d in self.draws:
            if d["drw_no"] == target_draw_no:
                target = d
                break

        if not target:
            target = self.get_latest_draw()

        if not target:
            return {}

        target_nums = {target["num1"], target["num2"], target["num3"], target["num4"], target["num5"], target["num6"]}
        target_list = sorted(list(target_nums))

        matches = {5: [], 4: [], 3: [], 2: []}

        for d in self.draws:
            if d["drw_no"] == target["drw_no"]:
                continue

            d_nums = [d["num1"], d["num2"], d["num3"], d["num4"], d["num5"], d["num6"]]
            d_set = set(d_nums)
            intersect = target_nums & d_set
            k = len(intersect)

            if k in matches:
                matches[k].append({
                    "drw_no": d["drw_no"],
                    "date": d.get("date", ""),
                    "matched_count": k,
                    "matched_numbers": sorted(list(intersect)),
                    "numbers": [
                        {
                            "number": n,
                            "color": get_ball_color(n),
                            "is_matched": n in target_nums
                        } for n in d_nums
                    ],
                    "bonus": {
                        "number": d["bonus"],
                        "color": get_ball_color(d["bonus"]),
                        "is_matched": d["bonus"] in target_nums
                    },
                    "prize_amount": d.get("prize_amount", 0),
                    "winner_count": d.get("winner_count", 0)
                })

        # 최신 회차순으로 정렬
        for k in matches:
            matches[k].sort(key=lambda x: x["drw_no"], reverse=True)

        return {
            "target_draw": {
                "drw_no": target["drw_no"],
                "date": target.get("date", ""),
                "numbers": [
                    {"number": n, "color": get_ball_color(n)}
                    for n in target_list
                ],
                "bonus": {"number": target["bonus"], "color": get_ball_color(target["bonus"])},
                "prize_amount": target.get("prize_amount", 0),
                "winner_count": target.get("winner_count", 0)
            },
            "summary": {
                "match_5": len(matches[5]),
                "match_4": len(matches[4]),
                "match_3": len(matches[3]),
                "match_2": len(matches[2]),
            },
            "matches": matches
        }

    def get_all_pair_high_matches(self, min_match=4):
        """
        역대 1회부터 최신 회차까지 모든 회차 쌍 중 당첨번호가 5개 또는 4개 일치했던
        역대급 데칼코마니 회차 쌍을 전수 탐색하여 반환.
        """
        num_sets = [
            (
                d["drw_no"],
                d.get("date", ""),
                {d["num1"], d["num2"], d["num3"], d["num4"], d["num5"], d["num6"]},
                [d["num1"], d["num2"], d["num3"], d["num4"], d["num5"], d["num6"]]
            )
            for d in self.draws
        ]

        pair_5 = []
        pair_4 = []
        n = len(num_sets)

        for i in range(n):
            d1_no, d1_dt, s1, l1 = num_sets[i]
            for j in range(i + 1, n):
                d2_no, d2_dt, s2, l2 = num_sets[j]
                intersect = s1 & s2
                k = len(intersect)

                if k == 5:
                    pair_5.append({
                        "draw1": {"drw_no": d1_no, "date": d1_dt, "numbers": [{"number": x, "color": get_ball_color(x), "is_matched": x in intersect} for x in l1]},
                        "draw2": {"drw_no": d2_no, "date": d2_dt, "numbers": [{"number": x, "color": get_ball_color(x), "is_matched": x in intersect} for x in l2]},
                        "matched_count": 5,
                        "matched_numbers": sorted(list(intersect))
                    })
                elif k == 4 and min_match <= 4:
                    pair_4.append({
                        "draw1": {"drw_no": d1_no, "date": d1_dt, "numbers": [{"number": x, "color": get_ball_color(x), "is_matched": x in intersect} for x in l1]},
                        "draw2": {"drw_no": d2_no, "date": d2_dt, "numbers": [{"number": x, "color": get_ball_color(x), "is_matched": x in intersect} for x in l2]},
                        "matched_count": 4,
                        "matched_numbers": sorted(list(intersect))
                    })

        # 최신 회차 관련 순으로 정렬
        pair_5.sort(key=lambda x: max(x["draw1"]["drw_no"], x["draw2"]["drw_no"]), reverse=True)
        pair_4.sort(key=lambda x: max(x["draw1"]["drw_no"], x["draw2"]["drw_no"]), reverse=True)

        return {
            "total_pairs_5": len(pair_5),
            "total_pairs_4": len(pair_4),
            "pairs_5": pair_5,
            "pairs_4": pair_4[:50]  # 4개 일치 쌍은 상위 50개만 반환
        }

    def full_summary(self):
        """대시보드 전체 요약 데이터 반환"""
        latest = self.get_latest_draw()
        return {
            "total_draws": self.total_draws,
            "latest_draw": latest,
            "frequency": self.frequency_stats(),
            "unappeared": self.unappeared_stats(),
            "odd_even": self.odd_even_stats(),
            "section": self.section_stats(),
            "sum": self.sum_stats(),
            "consecutive": self.consecutive_stats(),
            "ac": self.ac_stats(),
            "ending_digit": self.ending_digit_stats(),
            "prize": self.prize_stats()
        }

