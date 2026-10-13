"""
app.py: 로또 분석기 메인 웹 서버 및 REST API / CLI 실행 진입점
"""

import sys
import os
import json
import urllib.parse
from http.server import HTTPServer, SimpleHTTPRequestHandler
import webbrowser
import argparse

# 윈도우 콘솔 UTF-8 출력 지원
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import data_manager
from analyzer import LottoAnalyzer
from generator import LottoGenerator
from simulator import LottoSimulator

PORT = 8080
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")


class LottoAPIHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == "/":
            self.path = "/index.html"
            return super().do_GET()

        if path.startswith("/api/"):
            self.handle_api_get(path, query)
        else:
            return super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else b"{}"

        try:
            body_json = json.loads(body.decode("utf-8")) if body else {}
        except Exception:
            body_json = {}

        if path.startswith("/api/"):
            self.handle_api_post(path, body_json)
        else:
            self.send_error(404, "Endpoint Not Found")

    def send_json(self, data, status=200):
        resp = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(resp)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(resp)

    def handle_api_get(self, path, query):
        if path == "/api/info":
            latest = data_manager.get_latest_draw_local()
            all_draws = data_manager.get_all_draws()
            self.send_json({
                "status": "success",
                "total_draws": len(all_draws),
                "latest_draw": latest
            })

        elif path == "/api/stats":
            period = query.get("period", ["all"])[0]
            draws = data_manager.get_all_draws()

            if not draws:
                self.send_json({"status": "error", "message": "데이터가 없습니다. 먼저 동기화를 진행해주세요."}, status=400)
                return

            recent_count = None
            if period.isdigit():
                recent_count = int(period)

            analyzer = LottoAnalyzer(draws)
            summary = analyzer.full_summary()
            if recent_count:
                summary["frequency"] = analyzer.frequency_stats(recent_count=recent_count)

            self.send_json({"status": "success", "data": summary})

        elif path == "/api/history":
            page = int(query.get("page", [1])[0])
            limit = int(query.get("limit", [20])[0])
            search = query.get("search", [""])[0].strip()

            draws = data_manager.get_all_draws(order_asc=False)

            if search:
                if search.isdigit():
                    s_no = int(search)
                    draws = [d for d in draws if d["drw_no"] == s_no or s_no in [d["num1"], d["num2"], d["num3"], d["num4"], d["num5"], d["num6"], d["bonus"]]]

            total_items = len(draws)
            start_idx = (page - 1) * limit
            end_idx = start_idx + limit
            page_data = draws[start_idx:end_idx]

            self.send_json({
                "status": "success",
                "page": page,
                "limit": limit,
                "total": total_items,
                "total_pages": (total_items + limit - 1) // limit,
                "data": page_data
            })

        elif path == "/api/draw-matches":
            drw_no_param = query.get("drw_no", [None])[0]
            draws = data_manager.get_all_draws()
            if not draws:
                self.send_json({"status": "error", "message": "데이터가 없습니다."}, status=400)
                return

            analyzer = LottoAnalyzer(draws)
            target_no = int(drw_no_param) if drw_no_param and drw_no_param.isdigit() else draws[-1]["drw_no"]
            match_data = analyzer.get_matching_draws(target_no)
            self.send_json({"status": "success", "data": match_data})

        elif path == "/api/pair-matches":
            min_match_param = query.get("min_match", ["4"])[0]
            min_match = int(min_match_param) if min_match_param.isdigit() else 4
            draws = data_manager.get_all_draws()
            if not draws:
                self.send_json({"status": "error", "message": "데이터가 없습니다."}, status=400)
                return

            analyzer = LottoAnalyzer(draws)
            pair_data = analyzer.get_all_pair_high_matches(min_match=min_match)
            self.send_json({"status": "success", "data": pair_data})

        else:
            self.send_error(404, "API Endpoint Not Found")

    def handle_api_post(self, path, body):
        if path == "/api/sync":
            try:
                res = data_manager.sync_data()
                self.send_json({"status": "success", "result": res})
            except Exception as e:
                self.send_json({"status": "error", "message": str(e)}, status=500)

        elif path == "/api/generate":
            draws = data_manager.get_all_draws()
            if not draws:
                self.send_json({"status": "error", "message": "데이터가 없습니다. 먼저 동기화하세요."}, status=400)
                return

            strategy = body.get("strategy", "golden")
            count = int(body.get("count", 5))
            include_numbers = body.get("include_numbers", [])
            exclude_numbers = body.get("exclude_numbers", [])

            generator = LottoGenerator(draws)
            try:
                games = generator.generate_games(
                    count=count,
                    strategy=strategy,
                    include_numbers=include_numbers,
                    exclude_numbers=exclude_numbers
                )
                self.send_json({"status": "success", "games": games})
            except Exception as e:
                self.send_json({"status": "error", "message": str(e)}, status=400)

        elif path == "/api/simulate":
            draws = data_manager.get_all_draws()
            if not draws:
                self.send_json({"status": "error", "message": "데이터가 없습니다. 먼저 동기화하세요."}, status=400)
                return

            numbers = body.get("numbers", [])
            simulator = LottoSimulator(draws)
            try:
                sim_res = simulator.simulate(numbers)
                self.send_json({"status": "success", "result": sim_res})
            except Exception as e:
                self.send_json({"status": "error", "message": str(e)}, status=400)

        elif path == "/api/simulate-multi":
            draws = data_manager.get_all_draws()
            if not draws:
                self.send_json({"status": "error", "message": "데이터가 없습니다. 먼저 동기화하세요."}, status=400)
                return

            combinations = body.get("combinations", [])
            simulator = LottoSimulator(draws)
            try:
                multi_res = simulator.simulate_multiple(combinations)
                self.send_json({"status": "success", "result": multi_res})
            except Exception as e:
                self.send_json({"status": "error", "message": str(e)}, status=400)

        else:
            self.send_error(404, "API Endpoint Not Found")


def run_cli():
    print("=" * 60)
    print("      🍀 대한민국 로또 6/45 정밀 통계 및 스마트 추천기")
    print("=" * 60)

    latest = data_manager.get_latest_draw_local()
    if not latest:
        print("[!] 로컬에 데이터가 없습니다. 동기화를 진행합니다...")
        data_manager.sync_data(progress_callback=lambda c, t, m: print(f"[{c}/{t}] {m}"))
        latest = data_manager.get_latest_draw_local()

    draws = data_manager.get_all_draws()
    print(f"\n[최신 회차 정보: {latest['drw_no']}회 ({latest['date']})]")
    print(f"당첨번호: {latest['num1']}, {latest['num2']}, {latest['num3']}, {latest['num4']}, {latest['num5']}, {latest['num6']} + 보너스: {latest['bonus']}")
    print(f"1등 당첨금: {latest['prize_amount']:,}원 (당첨자수: {latest['winner_count']}명)")

    analyzer = LottoAnalyzer(draws)
    freq = analyzer.frequency_stats()
    unapp = analyzer.unappeared_stats()

    print("\n[🔥 최다 출현 번호 TOP 5 (Hot Numbers)]")
    for item in freq["hot_10"][:5]:
        print(f"  {item['rank']}위: {item['number']:02d}번 ({item['main_count']}회 출현, {item['percentage']}%)")

    print("\n[❄️ 장기 미출현 번호 TOP 5 (Cold Numbers)]")
    for item in unapp["top_cold"][:5]:
        print(f"  {item['number']:02d}번: 최근 {item['unappeared_count']}회 연속 미출현 (마지막 {item['last_draw']}회)")

    print("\n[✨ 추천 번호 생성 (골든 밸런스 5게임)]")
    gen = LottoGenerator(draws)
    games = gen.generate_games(count=5, strategy="golden")
    for g in games:
        nums_str = " ".join(f"{n:02d}" for n in g["numbers"])
        print(f"  게임 {g['game_index']}: [{nums_str}] (총합: {g['sum']}, 홀짝: {g['odd_even']}, AC: {g['ac']}, 밸런스 점수: {g['score']}점)")
    print("=" * 60)


def start_server(port=PORT, auto_open=True):
    # 서버 기동 전 DB가 비어있으면 초기 동기화
    latest = data_manager.get_latest_draw_local()
    if not latest:
        print("[!] 로컬 DB가 비어 있어 초기 데이터 동기화를 시작합니다...")
        data_manager.sync_data(progress_callback=lambda c, t, m: print(f"[{c}/{t}] {m}", flush=True))

    server_address = ("", port)
    httpd = HTTPServer(server_address, LottoAPIHandler)
    url = f"http://localhost:{port}"
    print("=" * 60)
    print(f"🚀 로또 분석 프로그램 대시보드가 실행되었습니다!")
    print(f"🌐 접속 주소: {url}")
    print("   (종료하려면 Ctrl+C를 누르세요)")
    print("=" * 60)

    if auto_open:
        webbrowser.open(url)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n서버를 종료합니다.")
        httpd.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="로또 6/45 정밀 통계 및 스마트 추천 프로그램")
    parser.add_argument("--cli", action="store_true", help="콘솔 모드로 실행")
    parser.add_argument("--port", type=int, default=PORT, help="웹 서버 포트 (기본: 8080)")
    parser.add_argument("--no-browser", action="store_true", help="브라우저 자동 열기 비활성화")
    args = parser.parse_args()

    if args.cli:
        run_cli()
    else:
        start_server(port=args.port, auto_open=not args.no_browser)
