"""
simulator.py: 과거 당첨 번호 기반 백테스팅 및 수익률 시뮬레이터
"""

from analyzer import get_ball_color


class LottoSimulator:
    def __init__(self, draws):
        self.draws = sorted(draws, key=lambda x: x["drw_no"])
        self.total_draws = len(self.draws)

    def simulate(self, my_numbers):
        """
        my_numbers: 6개 정수 리스트
        역대 전 회차에 동일 번호로 응모했을 때의 가상 결과 시뮬레이션
        """
        my_set = set(my_numbers)
        if len(my_set) != 6 or any(n < 1 or n > 45 for n in my_set):
            raise ValueError("1~45 사이의 서로 다른 6개 번호를 입력해야 합니다.")

        my_sorted = sorted(my_numbers)

        rank_counts = {
            1: 0,
            2: 0,
            3: 0,
            4: 0,
            5: 0,
            "miss": 0
        }

        total_prize_earned = 0
        winning_history = []

        # 게임당 가격: 1,000원 (과거 2,000원 시절도 있었으나 현행 1,000원 기준 계산)
        ticket_price = 1000
        total_spent = self.total_draws * ticket_price

        for d in self.draws:
            drw_nums = {d["num1"], d["num2"], d["num3"], d["num4"], d["num5"], d["num6"]}
            bonus = d["bonus"]

            matched = my_set & drw_nums
            match_count = len(matched)
            matched_bonus = bonus in my_set

            rank = None
            prize = 0

            if match_count == 6:
                rank = 1
                prize = d.get("prize_amount", 2000000000)
            elif match_count == 5 and matched_bonus:
                rank = 2
                # 2등 상금이 없을 경우 대략 5,000만원 추정
                prize = 50000000
            elif match_count == 5:
                rank = 3
                # 3등 상금 약 150만원
                prize = 1500000
            elif match_count == 4:
                rank = 4
                prize = 50000
            elif match_count == 3:
                rank = 5
                prize = 5000
            else:
                rank = "miss"

            rank_counts[rank] += 1
            total_prize_earned += prize

            if rank != "miss":
                winning_history.append({
                    "drw_no": d["drw_no"],
                    "date": d.get("date", ""),
                    "rank": rank,
                    "match_count": match_count,
                    "matched_numbers": sorted(list(matched)),
                    "bonus_matched": matched_bonus,
                    "prize": prize,
                    "draw_numbers": [d["num1"], d["num2"], d["num3"], d["num4"], d["num5"], d["num6"]],
                    "bonus": bonus
                })

        # 최신 당첨순으로 정렬
        winning_history.sort(key=lambda x: x["drw_no"], reverse=True)

        net_profit = total_prize_earned - total_spent
        roi = round((net_profit / total_spent) * 100, 2) if total_spent > 0 else 0

        # 최고 등수
        highest_rank = None
        for r in [1, 2, 3, 4, 5]:
            if rank_counts[r] > 0:
                highest_rank = r
                break

        return {
            "my_numbers": my_sorted,
            "ball_details": [{"number": n, "color": get_ball_color(n)} for n in my_sorted],
            "total_draws_tested": self.total_draws,
            "total_spent": total_spent,
            "total_prize_earned": total_prize_earned,
            "net_profit": net_profit,
            "roi_percentage": roi,
            "highest_rank": highest_rank,
            "rank_counts": rank_counts,
            "win_rate_percentage": round((len(winning_history) / self.total_draws) * 100, 2) if self.total_draws > 0 else 0,
            "winning_history": winning_history[:50],  # 상위 50건 반환
            "total_winning_events": len(winning_history)
        }

    def simulate_multiple(self, combinations):
        """
        combinations: list of list of 6 integers (최대 50개 조합)
        50개 번호조합을 일괄 시뮬레이션하여 통합 수익률 및 조합별 성적 랭킹 반환
        """
        if not combinations:
            raise ValueError("하나 이상의 번호 조합을 입력해야 합니다.")

        if len(combinations) > 50:
            combinations = combinations[:50]

        valid_combos = []
        for idx, nums in enumerate(combinations):
            s = set(nums)
            if len(s) != 6 or any(n < 1 or n > 45 for n in s):
                continue
            valid_combos.append({
                "combo_id": idx + 1,
                "numbers": sorted(list(s)),
                "set": s
            })

        if not valid_combos:
            raise ValueError("유효한 6개 번호 조합(1~45 중복 없음)이 없습니다.")

        ticket_price = 1000
        num_combos = len(valid_combos)
        total_spent = num_combos * self.total_draws * ticket_price

        # 전체 통합 등수 카운트
        aggregate_ranks = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        total_prize_all = 0

        combo_results = []
        for c in valid_combos:
            combo_results.append({
                "combo_id": c["combo_id"],
                "numbers": c["numbers"],
                "ball_details": [{"number": n, "color": get_ball_color(n)} for n in c["numbers"]],
                "rank_counts": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, "miss": 0},
                "total_prize": 0,
                "highest_rank": None,
                "winning_events": 0
            })

        all_high_wins = []  # 1등~3등 당첨 하이라이트

        for d in self.draws:
            drw_nums = {d["num1"], d["num2"], d["num3"], d["num4"], d["num5"], d["num6"]}
            bonus = d["bonus"]
            drw_no = d["drw_no"]
            date_str = d.get("date", "")
            first_prize = d.get("prize_amount", 2000000000)

            for i, c in enumerate(valid_combos):
                matched = c["set"] & drw_nums
                match_count = len(matched)
                matched_bonus = bonus in c["set"]

                rank = None
                prize = 0

                if match_count == 6:
                    rank = 1
                    prize = first_prize
                elif match_count == 5 and matched_bonus:
                    rank = 2
                    prize = 50000000
                elif match_count == 5:
                    rank = 3
                    prize = 1500000
                elif match_count == 4:
                    rank = 4
                    prize = 50000
                elif match_count == 3:
                    rank = 5
                    prize = 5000
                else:
                    rank = "miss"

                res = combo_results[i]
                res["rank_counts"][rank] += 1
                res["total_prize"] += prize

                if rank != "miss":
                    aggregate_ranks[rank] += 1
                    total_prize_all += prize
                    res["winning_events"] += 1

                    if rank in [1, 2, 3]:
                        all_high_wins.append({
                            "combo_id": c["combo_id"],
                            "combo_numbers": c["numbers"],
                            "drw_no": drw_no,
                            "date": date_str,
                            "rank": rank,
                            "prize": prize,
                            "matched_numbers": sorted(list(matched))
                        })

        # 개별 조합별 메트릭 계산
        spent_per_combo = self.total_draws * ticket_price
        for res in combo_results:
            for r in [1, 2, 3, 4, 5]:
                if res["rank_counts"][r] > 0:
                    res["highest_rank"] = r
                    break
            res["net_profit"] = res["total_prize"] - spent_per_combo
            res["roi"] = round((res["net_profit"] / spent_per_combo) * 100, 2)
            res["win_rate"] = round((res["winning_events"] / self.total_draws) * 100, 2)

        # 상금 순위로 정렬
        ranked_combos = sorted(combo_results, key=lambda x: x["total_prize"], reverse=True)
        for rank_idx, item in enumerate(ranked_combos, start=1):
            item["standing"] = rank_idx

        # 전체 종합 메트릭
        total_net_profit = total_prize_all - total_spent
        total_roi = round((total_net_profit / total_spent) * 100, 2) if total_spent > 0 else 0

        # 전체 최고 등수
        highest_rank_overall = None
        for r in [1, 2, 3, 4, 5]:
            if aggregate_ranks[r] > 0:
                highest_rank_overall = r
                break

        # 고액 당첨 최신순 정렬
        all_high_wins.sort(key=lambda x: (x["rank"], -x["drw_no"]))

        return {
            "total_combos_tested": num_combos,
            "total_draws_tested": self.total_draws,
            "total_games_played": num_combos * self.total_draws,
            "total_spent": total_spent,
            "total_prize_earned": total_prize_all,
            "net_profit": total_net_profit,
            "roi_percentage": total_roi,
            "highest_rank": highest_rank_overall,
            "rank_counts": aggregate_ranks,
            "combos": ranked_combos,
            "best_combo": ranked_combos[0] if ranked_combos else None,
            "high_wins": all_high_wins[:30]
        }

