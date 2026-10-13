"""
data_manager.py: 로또 역대 당첨 데이터 수집, 저장(SQLite), 증분 업데이트 모듈
(Dual-Source: 고속 GitHub CDN + 공식 동행복권 API Fallback)
"""

import sqlite3
import json
import urllib.request
import urllib.error
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
from datetime import date

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lotto.db")

DHLOTTERY_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://www.dhlottery.co.kr/",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest"
}


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS draws (
            drw_no INTEGER PRIMARY KEY,
            date TEXT NOT NULL,
            num1 INTEGER NOT NULL,
            num2 INTEGER NOT NULL,
            num3 INTEGER NOT NULL,
            num4 INTEGER NOT NULL,
            num5 INTEGER NOT NULL,
            num6 INTEGER NOT NULL,
            bonus INTEGER NOT NULL,
            winner_count INTEGER DEFAULT 0,
            prize_amount INTEGER DEFAULT 0,
            total_prize INTEGER DEFAULT 0,
            auto_count INTEGER DEFAULT 0,
            manual_count INTEGER DEFAULT 0,
            semi_auto_count INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()


def fetch_draw_github(drw_no, timeout=4):
    """GitHub 오픈 데이터셋에서 단일 회차 조회 (고속 CDN)"""
    url = f"https://raw.githubusercontent.com/smok95/lotto/main/results/{drw_no}.json"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            numbers = data.get("numbers", [])
            if len(numbers) != 6:
                return None

            divisions = data.get("divisions", [])
            div1 = divisions[0] if divisions else {}
            comb = data.get("winners_combination", {}) or {}

            raw_date = data.get("date", "")
            f_date = raw_date[:10] if len(raw_date) >= 10 else raw_date

            return {
                "drw_no": int(data["draw_no"]),
                "date": f_date,
                "num1": int(numbers[0]),
                "num2": int(numbers[1]),
                "num3": int(numbers[2]),
                "num4": int(numbers[3]),
                "num5": int(numbers[4]),
                "num6": int(numbers[5]),
                "bonus": int(data.get("bonus_no", 0)),
                "winner_count": int(div1.get("winners", 0) or 0),
                "prize_amount": int(div1.get("prize", 0) or 0),
                "total_prize": int(div1.get("prize", 0) * div1.get("winners", 0) if div1 else 0),
                "auto_count": int(comb.get("auto", 0) or 0),
                "manual_count": int(comb.get("manual", 0) or 0),
                "semi_auto_count": int(comb.get("semi_auto", 0) or 0),
            }
    except Exception:
        return None


def fetch_draw_dhlottery(drw_no, timeout=4):
    """동행복권 공식 엔드포인트에서 단일 회차 조회"""
    url = f"https://www.dhlottery.co.kr/lt645/selectPstLt645Info.do?srchLtEpsd={drw_no}"
    req = urllib.request.Request(url, headers=DHLOTTERY_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            lst = data.get("data", {}).get("list", [])
            if lst and lst[0].get("tm1WnNo") is not None:
                row = lst[0]
                ymd = str(row.get("ltRflYmd", ""))
                f_date = f"{ymd[:4]}-{ymd[4:6]}-{ymd[6:]}" if len(ymd) == 8 else ymd
                return {
                    "drw_no": int(row["ltEpsd"]),
                    "date": f_date,
                    "num1": int(row["tm1WnNo"]),
                    "num2": int(row["tm2WnNo"]),
                    "num3": int(row["tm3WnNo"]),
                    "num4": int(row["tm4WnNo"]),
                    "num5": int(row["tm5WnNo"]),
                    "num6": int(row["tm6WnNo"]),
                    "bonus": int(row["bnsWnNo"]),
                    "winner_count": int(row.get("rnk1WnNope", 0) or 0),
                    "prize_amount": int(row.get("rnk1WnAmt", 0) or 0),
                    "total_prize": int(row.get("rnk1SumWnAmt", 0) or 0),
                    "auto_count": int(row.get("winType1", 0) or 0),
                    "manual_count": int(row.get("winType2", 0) or 0),
                    "semi_auto_count": int(row.get("winType3", 0) or 0),
                }
    except Exception:
        return None


def fetch_draw(drw_no):
    """듀얼 소스: GitHub CDN 우선 -> 실패 시 동행복권 API"""
    res = fetch_draw_github(drw_no)
    if res:
        return res
    return fetch_draw_dhlottery(drw_no)


def find_latest_draw_remote():
    """
    로또 1회차(2002-12-07) 기준으로 경과 주수를 계산하여 최신 회차를 특정.
    """
    start_date = date(2002, 12, 7)
    today = date.today()
    diff_days = (today - start_date).days
    estimated_drw = (diff_days // 7) + 1

    for d in [estimated_drw + 1, estimated_drw, estimated_drw - 1]:
        if fetch_draw(d):
            return d
    return max(1100, estimated_drw)


def get_latest_draw_local():
    """로컬 DB의 최신 회차 반환"""
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM draws ORDER BY drw_no DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_draws(order_asc=True):
    """로컬 DB의 전체 회차 목록 반환"""
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    order = "ASC" if order_asc else "DESC"
    cursor.execute(f"SELECT * FROM draws ORDER BY drw_no {order}")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_draw_by_no(drw_no):
    """특정 회차 반환"""
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM draws WHERE drw_no = ?", (drw_no,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def save_draws_batch(draws_list):
    """회차 리스트를 일괄 DB 저장"""
    if not draws_list:
        return
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.executemany("""
        INSERT OR REPLACE INTO draws (
            drw_no, date, num1, num2, num3, num4, num5, num6, bonus,
            winner_count, prize_amount, total_prize,
            auto_count, manual_count, semi_auto_count
        ) VALUES (
            :drw_no, :date, :num1, :num2, :num3, :num4, :num5, :num6, :bonus,
            :winner_count, :prize_amount, :total_prize,
            :auto_count, :manual_count, :semi_auto_count
        )
    """, draws_list)
    conn.commit()
    conn.close()


def sync_data(progress_callback=None, max_workers=20):
    """
    로컬 DB와 최신 회차를 고속 병렬 동기화
    """
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT drw_no FROM draws")
    existing_set = {row["drw_no"] for row in cursor.fetchall()}
    conn.close()

    latest_remote = find_latest_draw_remote()
    missing_draws = [d for d in range(1, latest_remote + 1) if d not in existing_set]

    total_missing = len(missing_draws)
    if total_missing == 0:
        if progress_callback:
            progress_callback(latest_remote, latest_remote, "최신 데이터가 이미 동기화되어 있습니다.")
        return {"updated_count": 0, "latest_draw": latest_remote}

    downloaded = []
    chunk_buffer = []
    completed_count = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {executor.submit(fetch_draw, d): d for d in missing_draws}
        for future in as_completed(future_map):
            d_no = future_map[future]
            try:
                res = future.result()
                if res:
                    downloaded.append(res)
                    chunk_buffer.append(res)
            except Exception as e:
                print(f"[ERROR] Draw {d_no}: {e}", flush=True)

            completed_count += 1

            if len(chunk_buffer) >= 50:
                save_draws_batch(chunk_buffer)
                chunk_buffer = []

            if progress_callback and (completed_count % 50 == 0 or completed_count == total_missing):
                progress_callback(completed_count, total_missing, f"{completed_count}/{total_missing} 회차 수집 중... (성공: {len(downloaded)})")

    if chunk_buffer:
        save_draws_batch(chunk_buffer)

    if progress_callback:
        progress_callback(total_missing, total_missing, f"총 {len(downloaded)}개 회차 동기화 완료!")

    return {
        "updated_count": len(downloaded),
        "latest_draw": latest_remote
    }


if __name__ == "__main__":
    print("로또 역대 데이터 고속 동기화 시작...", flush=True)
    t0 = time.time()
    def on_prog(cur, tot, msg):
        print(f"[{cur}/{tot}] {msg}", flush=True)
    res = sync_data(progress_callback=on_prog)
    t1 = time.time()
    print(f"동기화 완료: {res} (소요 시간: {t1 - t0:.2f}초)", flush=True)
    latest = get_latest_draw_local()
    print("최신 저장 회차:", latest, flush=True)
