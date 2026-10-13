"""
generator.py: 스마트 로또 번호 추천 및 조합 생성 엔진
"""

import random
from collections import Counter
from analyzer import calculate_ac, get_ball_color


class LottoGenerator:
    def __init__(self, draws):
        self.draws = sorted(draws, key=lambda x: x["drw_no"])
        self.total_draws = len(self.draws)
        self._calculate_weights()

    def _calculate_weights(self):
        """번호별 출현 빈도 및 최근 미출현 상태에 따른 가중치 산출"""
        main_counts = Counter()
        latest_drw = self.draws[-1]["drw_no"] if self.draws else 1
        last_seen = {}

        for d in self.draws:
            drw = d["drw_no"]
            nums = [d["num1"], d["num2"], d["num3"], d["num4"], d["num5"], d["num6"]]
            for n in nums:
                main_counts[n] += 1
                last_seen[n] = drw

        # 빈도수 기반 가중치 (기본 10 + 출현 횟수)
        self.freq_weights = {}
        for n in range(1, 46):
            self.freq_weights[n] = 10 + main_counts[n]

        # 미출현 기간 기반 가중치 (오래 안 나올수록 가중치 증가)
        self.cold_weights = {}
        for n in range(1, 46):
            gap = latest_drw - last_seen.get(n, 0)
            self.cold_weights[n] = 5 + (gap * 2)

        # 최근 10회차 출현 번호 목록
        recent_10_draws = self.draws[-10:] if len(self.draws) >= 10 else self.draws
        self.recent_numbers = set()
        for d in recent_10_draws:
            for k in ["num1", "num2", "num3", "num4", "num5", "num6"]:
                self.recent_numbers.add(d[k])

    def evaluate_combination(self, numbers):
        """조합의 밸런스 및 통계 적합도 점수(0~100) 평가"""
        nums = sorted(numbers)
        total_sum = sum(nums)
        odds = sum(1 for n in nums if n % 2 != 0)
        evens = 6 - odds
        ac = calculate_ac(nums)

        # 연번 계산
        consecutive_pairs = 0
        has_triple = False
        for i in range(len(nums) - 1):
            if nums[i + 1] - nums[i] == 1:
                consecutive_pairs += 1
                if i + 2 < len(nums) and nums[i + 2] - nums[i + 1] == 1:
                    has_triple = True

        # 구간대 편중 계산 (한 구간에 최대 몇 개 몰렸는지)
        sections = Counter()
        for n in nums:
            sections[(n - 1) // 10] += 1
        max_in_section = max(sections.values()) if sections else 0

        # 끝수 중복
        ending_digits = Counter(n % 10 for n in nums)
        max_ending_dup = max(ending_digits.values()) if ending_digits else 0

        # 적합도 점수 계산
        score = 100

        # 총합 패널티 (이상적: 100~175)
        if total_sum < 90 or total_sum > 185:
            score -= 25
        elif total_sum < 100 or total_sum > 175:
            score -= 10

        # 홀짝 패널티 (이상적: 3:3, 2:4, 4:2)
        if odds in (0, 6):
            score -= 30
        elif odds in (1, 5):
            score -= 15

        # AC값 패널티 (이상적: 7~10)
        if ac < 6:
            score -= 20
        elif ac < 7:
            score -= 10

        # 연번 패널티 (연번 2쌍 초과 또는 3연번 이상)
        if has_triple:
            score -= 15
        if consecutive_pairs > 2:
            score -= 15

        # 구간 편중 패널티
        if max_in_section >= 4:
            score -= 20

        # 끝수 몰림 패널티
        if max_ending_dup >= 4:
            score -= 15

        score = max(0, min(100, score))

        return {
            "numbers": nums,
            "ball_details": [{"number": n, "color": get_ball_color(n)} for n in nums],
            "sum": total_sum,
            "odd_even": f"{odds}:{evens}",
            "ac": ac,
            "consecutive_pairs": consecutive_pairs,
            "has_triple": has_triple,
            "max_in_section": max_in_section,
            "score": score
        }

    def _passes_golden_filter(self, numbers):
        """황금 통계 밸런스 엄격 필터 통과 여부"""
        nums = sorted(numbers)
        s = sum(nums)
        if not (100 <= s <= 175):
            return False

        odds = sum(1 for n in nums if n % 2 != 0)
        if odds not in (2, 3, 4):
            return False

        ac = calculate_ac(nums)
        if ac < 7:
            return False

        # 3연속 번호 제외 및 연번 2쌍 초과 제외
        consecutive_pairs = 0
        for i in range(len(nums) - 1):
            if nums[i + 1] - nums[i] == 1:
                consecutive_pairs += 1
                if i + 2 < len(nums) and nums[i + 2] - nums[i + 1] == 1:
                    return False
        if consecutive_pairs > 2:
            return False

        # 구간대 몰림 방지 (한 구간 3개 초과 제외)
        sections = Counter((n - 1) // 10 for n in nums)
        if max(sections.values()) > 3:
            return False

        # 끝수 중복 방지 (동일 끝수 3개 초과 제외)
        endings = Counter(n % 10 for n in nums)
        if max(endings.values()) > 2:
            return False

        return True

    def generate_single(self, strategy="golden", include_numbers=None, exclude_numbers=None):
        """
        단일 게임 번호 생성 (6개)
        strategy: 'golden', 'hot', 'cold', 'trend', 'random'
        """
        include = set(include_numbers or [])
        exclude = set(exclude_numbers or [])

        # 유효성 검사
        if len(include) > 5:
            include = set(list(include)[:5])

        available_pool = [n for n in range(1, 46) if n not in exclude and n not in include]
        need_count = 6 - len(include)

        if len(available_pool) < need_count:
            raise ValueError("제외수가 너무 많아 6개 번호를 선택할 수 없습니다.")

        max_attempts = 3000
        best_combo = None
        best_score = -1

        for _ in range(max_attempts):
            chosen = list(include)

            if strategy == "random":
                chosen += random.sample(available_pool, need_count)
            elif strategy == "hot":
                # 빈도수 가중치 샘플링
                weights = [self.freq_weights[n] for n in available_pool]
                picks = []
                temp_pool = list(available_pool)
                temp_weights = list(weights)
                for _ in range(need_count):
                    pick = random.choices(temp_pool, weights=temp_weights, k=1)[0]
                    picks.append(pick)
                    idx = temp_pool.index(pick)
                    del temp_pool[idx]
                    del temp_weights[idx]
                chosen += picks
            elif strategy == "cold":
                # 미출현 가중치 샘플링
                weights = [self.cold_weights[n] for n in available_pool]
                picks = []
                temp_pool = list(available_pool)
                temp_weights = list(weights)
                for _ in range(need_count):
                    pick = random.choices(temp_pool, weights=temp_weights, k=1)[0]
                    picks.append(pick)
                    idx = temp_pool.index(pick)
                    del temp_pool[idx]
                    del temp_weights[idx]
                chosen += picks
            elif strategy == "trend":
                # 최근 10회차 번호에서 2~3개, 미출현/나머지에서 3~4개 균형 배분
                recent_available = [n for n in available_pool if n in self.recent_numbers]
                other_available = [n for n in available_pool if n not in self.recent_numbers]

                r_take = min(len(recent_available), random.choice([1, 2, 3]))
                o_take = need_count - r_take

                if len(other_available) < o_take:
                    r_take = need_count - len(other_available)
                    o_take = need_count - r_take

                picks = random.sample(recent_available, r_take) + random.sample(other_available, o_take)
                chosen += picks
            else:  # 'golden' 기본
                # 무작위 추출 후 골든 밸런스 필터 검사
                chosen += random.sample(available_pool, need_count)

            eval_res = self.evaluate_combination(chosen)
            score = eval_res["score"]

            if strategy == "golden":
                if self._passes_golden_filter(chosen):
                    return eval_res
            else:
                if score > best_score:
                    best_score = score
                    best_combo = eval_res
                    if score >= 85:
                        return eval_res

            if score > best_score:
                best_score = score
                best_combo = eval_res

        # 조건에 완벽히 맞는 조합이 없더라도 가장 점수가 높은 조합 반환
        return best_combo if best_combo else self.evaluate_combination(random.sample(range(1, 46), 6))

    def generate_games(self, count=5, strategy="golden", include_numbers=None, exclude_numbers=None):
        """지정된 게임 수(기본 5게임, 1세트)만큼 번호 생성"""
        games = []
        for i in range(count):
            combo = self.generate_single(
                strategy=strategy,
                include_numbers=include_numbers,
                exclude_numbers=exclude_numbers
            )
            combo["game_index"] = chr(65 + i)  # A, B, C, D, E...
            games.append(combo)
        return games
