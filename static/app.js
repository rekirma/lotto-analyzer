/**
 * app.js: 로또 6/45 스마트 정밀 분석기 클라이언트 스크립트
 * (동일 회차 매칭 2~5개 분석 및 50개 번호조합 일괄 백테스팅 시뮬레이터 포함)
 */

// 전역 상태
let currentTab = 'dashboard';
let currentPeriod = 'all';
let currentStatsData = null;
let currentStrategy = 'golden';
let currentGameCount = 5;
let ballSelectMode = 'include'; // 'include' or 'exclude'
let includedBalls = new Set();
let excludedBalls = new Set();
let generatedGamesCache = [];

// 동일 회차 매칭 상태
let matchCurrentTargetDrwNo = null;
let matchCurrentData = null;
let matchCurrentFilter = 'all';
let allPairsLoaded = false;
let allPairsVisible = true;

// 50개 조합 백테스팅 상태
let simCombinations = [];

// 차트 인스턴스 보관
let freqChart = null;
let oddEvenChart = null;
let sumChart = null;
let acChart = null;

// 역대 회차 페이지네이션 상태
let historyCurrentPage = 1;
let historyTotalPages = 1;
let historySearchQuery = '';

// ==========================================
// 1. 초기화 및 이벤트 리스너
// ==========================================
document.addEventListener('DOMContentLoaded', () => {
  initApp();
  renderInteractiveBallGrid();
  setupManualInputs();
  // 기본 5개 랜덤 조합 세팅
  addRandomCombos(5);
});

async function initApp() {
  await loadDashboardData();
  await loadHistory(1);
}

// 탭 전환
function switchTab(tabId) {
  currentTab = tabId;
  const tabs = ['dashboard', 'matches', 'generator', 'simulator', 'history'];

  tabs.forEach(t => {
    const view = document.getElementById(`view-${t}`);
    const btn = document.getElementById(`tab-${t}`);
    if (view && btn) {
      if (t === tabId) {
        view.classList.remove('hidden');
        btn.classList.add('active-tab');
        btn.classList.remove('text-slate-400');
      } else {
        view.classList.add('hidden');
        btn.classList.remove('active-tab');
        btn.classList.add('text-slate-400');
      }
    }
  });

  // 차트 리사이즈 대응
  if (tabId === 'dashboard') {
    setTimeout(() => {
      if (freqChart) freqChart.resize();
      if (oddEvenChart) oddEvenChart.resize();
      if (sumChart) sumChart.resize();
      if (acChart) acChart.resize();
    }, 100);
  }

  // 매칭 탭 열릴 때 초기 데이터 로드
  if (tabId === 'matches') {
    if (!matchCurrentData) {
      loadMatchesForTarget(null);
    }
  }
}

// 토스트 메시지
function showToast(message, type = 'info') {
  const container = document.getElementById('toastContainer');
  const toast = document.createElement('div');
  const bg = type === 'success' ? 'bg-emerald-600 text-white' : type === 'error' ? 'bg-rose-600 text-white' : 'bg-slate-800 text-slate-100 border border-slate-700';

  toast.className = `px-4 py-3 rounded-xl shadow-2xl flex items-center gap-3 text-xs font-semibold ${bg} transition-all duration-300 transform translate-y-2 opacity-0 pointer-events-auto`;
  toast.innerHTML = `
    <i class="fa-solid ${type === 'success' ? 'fa-check' : type === 'error' ? 'fa-circle-exclamation' : 'fa-circle-info'}"></i>
    <span>${message}</span>
  `;

  container.appendChild(toast);
  setTimeout(() => {
    toast.classList.remove('translate-y-2', 'opacity-0');
  }, 10);

  setTimeout(() => {
    toast.classList.add('translate-y-2', 'opacity-0');
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

// 공 색상 클래스 매핑
function getBallColorClass(num) {
  if (num <= 10) return 'lotto-yellow';
  if (num <= 20) return 'lotto-blue';
  if (num <= 30) return 'lotto-red';
  if (num <= 40) return 'lotto-gray';
  return 'lotto-green';
}

function createBallHtml(num, size = 'default', isMatched = null) {
  const colorClass = getBallColorClass(num);
  const sizeClass = size === 'sm' ? 'lotto-ball-sm' : size === 'mini' ? 'lotto-ball-mini' : 'lotto-ball';
  const matchClass = isMatched === true ? 'ball-matched' : isMatched === false ? 'ball-unmatched' : '';
  return `<div class="${sizeClass} ${colorClass} ${matchClass}">${num}</div>`;
}

// ==========================================
// 2. 대시보드 통계 로드 및 렌더링
// ==========================================
async function loadDashboardData(period = 'all') {
  try {
    const res = await fetch(`/api/stats?period=${period}`);
    const json = await res.json();
    if (json.status !== 'success') {
      showToast(json.message || '데이터 로드 실패', 'error');
      return;
    }

    currentStatsData = json.data;
    renderDashboard(currentStatsData);
  } catch (err) {
    console.error(err);
    showToast('통계 데이터를 불러오는 중 오류가 발생했습니다.', 'error');
  }
}

function reloadStats(period) {
  currentPeriod = period;
  ['all', '100', '50'].forEach(p => {
    const b = document.getElementById(`filter-${p}`);
    if (p === period) {
      b.className = 'filter-btn active-filter px-2.5 py-1 rounded';
    } else {
      b.className = 'filter-btn px-2.5 py-1 rounded text-slate-400 hover:text-white';
    }
  });
  loadDashboardData(period);
}

function renderDashboard(data) {
  const latest = data.latest_draw;
  if (!latest) return;

  // 헤더 요약 뱃지
  document.getElementById('latestDrawBadge').classList.remove('hidden');
  document.getElementById('headerDrawNo').textContent = `${latest.drw_no}회`;
  const headerBalls = [latest.num1, latest.num2, latest.num3, latest.num4, latest.num5, latest.num6];
  document.getElementById('headerDrawBalls').innerHTML = headerBalls.map(n => createBallHtml(n, 'mini')).join('');

  // 최신 회차 하이라이트 배너
  document.getElementById('latestDate').textContent = `${latest.date} 추첨`;
  document.getElementById('latestDrawNum').textContent = latest.drw_no;
  document.getElementById('latestPrize').textContent = Number(latest.prize_amount).toLocaleString();
  document.getElementById('latestWinners').textContent = latest.winner_count;
  document.getElementById('latestAuto').textContent = latest.auto_count || 0;
  document.getElementById('latestManual').textContent = latest.manual_count || 0;

  document.getElementById('latestBalls').innerHTML = headerBalls.map(n => createBallHtml(n, 'default')).join('');
  document.getElementById('latestBonusBall').innerHTML = createBallHtml(latest.bonus, 'default');

  // 지표 카드 갱신
  document.getElementById('statTotalDraws').textContent = `${data.total_draws}회`;
  
  const hot1 = data.frequency.hot_10[0];
  if (hot1) {
    const ballEl = document.getElementById('statHotBall');
    ballEl.textContent = hot1.number;
    ballEl.className = `lotto-ball-sm ${getBallColorClass(hot1.number)} font-bold`;
    document.getElementById('statHotInfo').textContent = `${hot1.number}번 (${hot1.main_count}회)`;
    document.getElementById('statHotSub').textContent = `역대 출현율 ${hot1.percentage}%`;
  }

  const cold1 = data.unappeared.top_cold[0];
  if (cold1) {
    const ballEl = document.getElementById('statColdBall');
    ballEl.textContent = cold1.number;
    ballEl.className = `lotto-ball-sm ${getBallColorClass(cold1.number)} font-bold`;
    document.getElementById('statColdInfo').textContent = `${cold1.number}번`;
    document.getElementById('statColdSub').textContent = `최근 ${cold1.unappeared_count}회 연속 미출현 (마지막 ${cold1.last_draw}회)`;
  }

  document.getElementById('statGoldenSumPct').textContent = `${data.sum.golden_range_percentage}%`;

  // 차트 렌더링
  renderFreqChart(data.frequency);
  renderOddEvenChart(data.odd_even);
  renderSectionBars(data.section);
  renderUnappearedList(data.unappeared.top_cold);
  renderSumChart(data.sum);
  renderConsecutiveStats(data.consecutive);
  renderAcChart(data.ac);
}

function renderFreqChart(freqData) {
  const ctx = document.getElementById('freqChart').getContext('2d');
  const labels = freqData.all_numbers.map(item => `${item.number}`);
  const counts = freqData.all_numbers.map(item => item.main_count);
  const bgColors = freqData.all_numbers.map(item => {
    const n = item.number;
    if (n <= 10) return '#fbc400';
    if (n <= 20) return '#69c8f2';
    if (n <= 30) return '#ff7272';
    if (n <= 40) return '#aaaaaa';
    return '#b0d840';
  });

  if (freqChart) freqChart.destroy();

  freqChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label: '출현 횟수',
        data: counts,
        backgroundColor: bgColors,
        borderRadius: 4,
        borderWidth: 0,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#0f172a',
          titleColor: '#e2e8f0',
          bodyColor: '#cbd5e1',
          borderColor: '#334155',
          borderWidth: 1,
          callbacks: {
            title: items => `${items[0].label}번 공`,
            label: item => `당첨 횟수: ${item.raw}회`
          }
        }
      },
      scales: {
        x: { grid: { display: false }, ticks: { color: '#94a3b8', font: { size: 10 } } },
        y: { grid: { color: '#1e293b' }, ticks: { color: '#94a3b8', font: { size: 10 } } }
      }
    }
  });
}

function renderOddEvenChart(oddEvenData) {
  const ctx = document.getElementById('oddEvenChart').getContext('2d');
  const labels = oddEvenData.patterns.map(p => `홀:${p.pattern.split(':')[0]} 짝:${p.pattern.split(':')[1]}`);
  const counts = oddEvenData.patterns.map(p => p.count);

  if (oddEvenChart) oddEvenChart.destroy();

  oddEvenChart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: labels,
      datasets: [{
        data: counts,
        backgroundColor: [
          '#10b981', '#3b82f6', '#06b6d4',
          '#6366f1', '#f59e0b', '#ec4899', '#ef4444'
        ],
        borderWidth: 2,
        borderColor: '#0f172a'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '68%',
      plugins: {
        legend: {
          position: 'right',
          labels: { color: '#cbd5e1', font: { size: 10 }, boxWidth: 10 }
        }
      }
    }
  });
}

function renderSectionBars(sections) {
  const container = document.getElementById('sectionProgressBars');
  container.innerHTML = sections.map(sec => `
    <div class="space-y-1">
      <div class="flex items-center justify-between text-xs">
        <span class="text-slate-300 font-medium">${sec.label}</span>
        <span class="text-slate-400">${sec.count}개 (${sec.percentage}%)</span>
      </div>
      <div class="w-full bg-slate-900 rounded-full h-2.5 overflow-hidden">
        <div class="h-2.5 rounded-full" style="width: ${sec.percentage}%; background-color: ${sec.color};"></div>
      </div>
    </div>
  `).join('');
}

function renderUnappearedList(topCold) {
  const container = document.getElementById('unappearedList');
  container.innerHTML = topCold.map((item, idx) => `
    <div class="flex items-center justify-between p-2 rounded-xl bg-slate-900/60 border border-slate-700/50">
      <div class="flex items-center gap-2.5">
        <span class="text-xs font-bold text-slate-500 w-4">${idx + 1}</span>
        ${createBallHtml(item.number, 'sm')}
        <span class="text-xs text-slate-300 font-semibold">${item.number}번</span>
      </div>
      <div class="text-right">
        <span class="text-xs font-bold text-cyan-400">${item.unappeared_count}회 연속</span>
        <span class="text-[11px] text-slate-500 block">마지막 ${item.last_draw}회</span>
      </div>
    </div>
  `).join('');
}

function renderSumChart(sumData) {
  const ctx = document.getElementById('sumChart').getContext('2d');
  document.getElementById('avgSumLabel').textContent = `평균 합계: ${sumData.avg_sum} (최소 ${sumData.min_sum} ~ 최대 ${sumData.max_sum})`;

  const labels = sumData.distribution.map(d => d.range);
  const counts = sumData.distribution.map(d => d.count);

  if (sumChart) sumChart.destroy();

  sumChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label: '회차 수',
        data: counts,
        backgroundColor: '#10b981',
        borderRadius: 4
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: '#94a3b8', font: { size: 10 } }, grid: { display: false } },
        y: { ticks: { color: '#94a3b8', font: { size: 10 } }, grid: { color: '#1e293b' } }
      }
    }
  });
}

function renderConsecutiveStats(consecData) {
  const container = document.getElementById('consecutiveList');
  container.innerHTML = consecData.pair_stats.map(item => `
    <div class="flex items-center justify-between text-xs py-1.5 border-b border-slate-800">
      <span class="text-slate-300">${item.pairs}</span>
      <div class="flex items-center gap-2">
        <span class="text-slate-400">${item.count}회</span>
        <span class="text-emerald-400 font-semibold w-12 text-right">${item.percentage}%</span>
      </div>
    </div>
  `).join('') + `
    <div class="flex items-center justify-between text-xs py-1.5 text-purple-300 font-medium">
      <span>3연속 번호 출현</span>
      <span>${consecData.triple_consecutive_count}회 (${consecData.triple_percentage}%)</span>
    </div>
  `;
}

function renderAcChart(acData) {
  const ctx = document.getElementById('acChart').getContext('2d');
  document.getElementById('highAcPct').textContent = `${acData.high_ac_percentage}%`;

  const labels = acData.distribution.map(d => `AC ${d.ac}`);
  const counts = acData.distribution.map(d => d.count);

  if (acChart) acChart.destroy();

  acChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [{
        data: counts,
        borderColor: '#f59e0b',
        backgroundColor: 'rgba(245, 158, 11, 0.1)',
        fill: true,
        tension: 0.3,
        pointRadius: 2
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: '#94a3b8', font: { size: 9 } }, grid: { display: false } },
        y: { display: false }
      }
    }
  });
}

// ==========================================
// 3. 동일 회차 매칭 분석 (2, 3, 4, 5개 일치)
// ==========================================
async function loadMatchesForTarget(drwNo = null) {
  try {
    const url = drwNo ? `/api/draw-matches?drw_no=${drwNo}` : `/api/draw-matches`;
    const res = await fetch(url);
    const json = await res.json();

    if (json.status !== 'success') {
      showToast(json.message || '매칭 데이터 조회 실패', 'error');
      return;
    }

    matchCurrentData = json.data;
    matchCurrentTargetDrwNo = matchCurrentData.target_draw.drw_no;
    document.getElementById('matchDrawInput').value = matchCurrentTargetDrwNo;

    renderMatchHeader(matchCurrentData.target_draw);
    renderMatchSummary(matchCurrentData.summary);
    filterMatches(matchCurrentFilter);

    if (!allPairsLoaded) {
      loadAllPairMatches();
    }
  } catch (err) {
    console.error(err);
    showToast('매칭 데이터 조회 중 오류가 발생했습니다.', 'error');
  }
}

function renderMatchHeader(target) {
  document.getElementById('matchTargetDrawNo').textContent = target.drw_no;
  document.getElementById('matchTargetDate').textContent = target.date;
  document.getElementById('matchTargetPrize').textContent = Number(target.prize_amount).toLocaleString();

  const ballsContainer = document.getElementById('matchTargetBalls');
  ballsContainer.innerHTML = target.numbers.map(n => createBallHtml(n.number, 'default')).join('');

  document.getElementById('matchTargetBonusBall').innerHTML = createBallHtml(target.bonus.number, 'default');
}

function renderMatchSummary(summary) {
  document.getElementById('matchSummary5').textContent = `${summary.match_5}건`;
  document.getElementById('matchSummary4').textContent = `${summary.match_4}건`;
  document.getElementById('matchSummary3').textContent = `${summary.match_3}건`;
  document.getElementById('matchSummary2').textContent = `${summary.match_2}건`;

  document.getElementById('mfBtn-5').textContent = `5개 일치 (${summary.match_5})`;
  document.getElementById('mfBtn-4').textContent = `4개 일치 (${summary.match_4})`;
  document.getElementById('mfBtn-3').textContent = `3개 일치 (${summary.match_3})`;
  document.getElementById('mfBtn-2').textContent = `2개 일치 (${summary.match_2})`;
}

function filterMatches(filterVal) {
  matchCurrentFilter = filterVal;

  ['all', 5, 4, 3, 2].forEach(k => {
    const btn = document.getElementById(`mfBtn-${k}`);
    if (btn) {
      if (k === filterVal) {
        btn.className = 'px-2.5 py-1 rounded-lg bg-rose-600 text-white font-bold';
      } else {
        btn.className = 'px-2.5 py-1 rounded-lg bg-slate-800 text-slate-300 hover:text-white border border-slate-700';
      }
    }
  });

  [5, 4, 3, 2].forEach(k => {
    const card = document.getElementById(`btnFilter${k}`);
    if (card) {
      if (k === filterVal) {
        card.classList.add('active-filter-card');
      } else {
        card.classList.remove('active-filter-card');
      }
    }
  });

  const badge = document.getElementById('currentMatchFilterBadge');
  if (filterVal === 'all') {
    badge.textContent = '전체 보기';
    badge.className = 'px-2 py-0.5 rounded text-xs font-bold bg-rose-500/20 text-rose-300 border border-rose-500/30';
  } else {
    badge.textContent = `${filterVal}개 번호 동일 회차`;
    const col = filterVal === 5 ? 'text-amber-400 bg-amber-500/20 border-amber-500/30' : filterVal === 4 ? 'text-emerald-400 bg-emerald-500/20 border-emerald-500/30' : filterVal === 3 ? 'text-blue-400 bg-blue-500/20 border-blue-500/30' : 'text-slate-300 bg-slate-700/40 border-slate-600';
    badge.className = `px-2 py-0.5 rounded text-xs font-bold border ${col}`;
  }

  if (matchCurrentData) {
    renderMatchedCards(matchCurrentData.matches, filterVal);
  }
}

function renderMatchedCards(matches, filterVal) {
  const container = document.getElementById('matchedDrawsContainer');
  let list = [];

  if (filterVal === 'all') {
    list = [...matches[5], ...matches[4], ...matches[3], ...matches[2]];
  } else {
    list = matches[filterVal] || [];
  }

  if (!list.length) {
    container.innerHTML = `
      <div class="col-span-full py-12 text-center text-slate-500 bg-slate-900/40 rounded-2xl border border-slate-800">
        <i class="fa-solid fa-circle-info text-2xl mb-2 text-slate-600 block"></i>
        <span>해당 조건(번호 ${filterVal}개 동일)에 일치하는 과거 회차가 없습니다.</span>
      </div>
    `;
    return;
  }

  container.innerHTML = list.map(item => {
    const k = item.matched_count;
    const badgeColor = k === 5
      ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
      : k === 4
      ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
      : k === 3
      ? 'bg-blue-500/20 text-blue-300 border-blue-500/40'
      : 'bg-slate-700 text-slate-300 border-slate-600';

    const ballsHtml = item.numbers.map(b => createBallHtml(b.number, 'sm', b.is_matched)).join(' ');
    const bonusHtml = createBallHtml(item.bonus.number, 'sm', item.bonus.is_matched);

    const matchedNumsStr = item.matched_numbers.join(', ');

    return `
      <div class="p-4 rounded-xl bg-slate-800/80 border border-slate-700/80 shadow-md hover:border-slate-600 transition space-y-3">
        <div class="flex items-center justify-between pb-2 border-b border-slate-700/50">
          <div>
            <span class="font-extrabold text-white text-base">제 ${item.drw_no}회</span>
            <span class="text-xs text-slate-400 ml-1.5">${item.date}</span>
          </div>
          <span class="px-2.5 py-0.5 rounded-full text-xs font-black border ${badgeColor}">
            ${k}개 일치!
          </span>
        </div>

        <div class="flex items-center gap-1.5 flex-wrap py-1">
          ${ballsHtml}
          <span class="text-slate-500 font-bold px-0.5">+</span>
          ${bonusHtml}
        </div>

        <div class="flex items-center justify-between pt-2 border-t border-slate-700/40 text-xs">
          <div class="text-slate-400">
            동일 번호: <span class="font-bold text-amber-300">[${matchedNumsStr}]</span>
          </div>
          <span class="font-semibold text-emerald-400">${Number(item.prize_amount).toLocaleString()}원</span>
        </div>
      </div>
    `;
  }).join('');
}

function changeMatchDrawStep(delta) {
  if (!matchCurrentTargetDrwNo) return;
  const nextNo = matchCurrentTargetDrwNo + delta;
  if (nextNo < 1) return;
  loadMatchesForTarget(nextNo);
}

function loadMatchesForInput() {
  const input = document.getElementById('matchDrawInput');
  const val = parseInt(input.value);
  if (isNaN(val) || val < 1) {
    showToast('유효한 회차 번호를 입력하세요.', 'error');
    return;
  }
  loadMatchesForTarget(val);
}

function loadMatchesForLatest() {
  loadMatchesForTarget(null);
}

async function loadAllPairMatches() {
  try {
    const res = await fetch(`/api/pair-matches?min_match=5`);
    const json = await res.json();
    if (json.status !== 'success') return;

    allPairsLoaded = true;
    renderAllPairs(json.data.pairs_5);
  } catch (err) {
    console.error(err);
  }
}

function renderAllPairs(pairs) {
  const container = document.getElementById('allPairsContainer');
  if (!pairs || !pairs.length) {
    container.innerHTML = '<span class="text-xs text-slate-500 col-span-full">5개 번호 동일 회차 쌍이 없습니다.</span>';
    return;
  }

  container.innerHTML = pairs.map((pair, idx) => {
    const d1Balls = pair.draw1.numbers.map(b => createBallHtml(b.number, 'mini', b.is_matched)).join(' ');
    const d2Balls = pair.draw2.numbers.map(b => createBallHtml(b.number, 'mini', b.is_matched)).join(' ');
    const matchedStr = pair.matched_numbers.join(', ');

    return `
      <div class="p-3.5 rounded-xl bg-slate-900/80 border border-slate-700/60 text-xs space-y-2">
        <div class="flex items-center justify-between">
          <span class="font-bold text-amber-400">#${idx + 1} 데칼코마니 (5개 일치)</span>
          <span class="px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 font-bold text-[10px] border border-amber-500/30">
            [${matchedStr}] 동일
          </span>
        </div>
        <div class="flex items-center justify-between bg-slate-950/60 p-2 rounded-lg">
          <span class="font-extrabold text-white w-14">제 ${pair.draw1.drw_no}회</span>
          <div class="flex items-center gap-1">${d1Balls}</div>
          <span class="text-[11px] text-slate-500">${pair.draw1.date}</span>
        </div>
        <div class="flex items-center justify-between bg-slate-950/60 p-2 rounded-lg">
          <span class="font-extrabold text-white w-14">제 ${pair.draw2.drw_no}회</span>
          <div class="flex items-center gap-1">${d2Balls}</div>
          <span class="text-[11px] text-slate-500">${pair.draw2.date}</span>
        </div>
      </div>
    `;
  }).join('');
}

function toggleAllPairsSection() {
  const container = document.getElementById('allPairsContainer');
  const btn = document.getElementById('btnTogglePairs');
  allPairsVisible = !allPairsVisible;

  if (allPairsVisible) {
    container.classList.remove('hidden');
    btn.textContent = '접기';
  } else {
    container.classList.add('hidden');
    btn.textContent = '펼치기';
  }
}

// ==========================================
// 4. 스마트 번호 추천기
// ==========================================
document.querySelectorAll('input[name="strategy"]').forEach(radio => {
  radio.addEventListener('change', (e) => {
    currentStrategy = e.target.value;
    document.querySelectorAll('.strategy-option').forEach(el => el.classList.remove('active', 'border-emerald-500'));
    e.target.closest('.strategy-option').classList.add('active', 'border-emerald-500');
  });
});

function setGameCount(cnt) {
  currentGameCount = cnt;
  [1, 5, 10].forEach(n => {
    const btn = document.getElementById(`cntBtn-${n}`);
    if (n === cnt) {
      btn.className = 'count-btn active px-3 py-1 rounded-lg text-xs font-bold border border-emerald-500 bg-emerald-600/30 text-emerald-300';
    } else {
      btn.className = 'count-btn px-3 py-1 rounded-lg text-xs font-bold border border-slate-700 bg-slate-900 text-slate-300';
    }
  });
}

function setSelectMode(mode) {
  ballSelectMode = mode;
  const btnInc = document.getElementById('modeBtnInclude');
  const btnExc = document.getElementById('modeBtnExclude');

  if (mode === 'include') {
    btnInc.className = 'px-2.5 py-1 rounded-lg font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40';
    btnExc.className = 'px-2.5 py-1 rounded-lg font-bold bg-slate-800 text-slate-400 border border-slate-700';
  } else {
    btnExc.className = 'px-2.5 py-1 rounded-lg font-bold bg-rose-500/20 text-rose-300 border border-rose-500/40';
    btnInc.className = 'px-2.5 py-1 rounded-lg font-bold bg-slate-800 text-slate-400 border border-slate-700';
  }
}

function renderInteractiveBallGrid() {
  const grid = document.getElementById('interactiveBallGrid');
  grid.innerHTML = '';

  for (let n = 1; n <= 45; n++) {
    const ball = document.createElement('div');
    ball.id = `grid-ball-${n}`;
    ball.className = `lotto-ball-grid ${getBallColorClass(n)}`;
    ball.textContent = n;
    ball.onclick = () => onGridBallClick(n);
    grid.appendChild(ball);
  }
  updateBallGridUi();
}

function onGridBallClick(n) {
  if (ballSelectMode === 'include') {
    if (includedBalls.has(n)) {
      includedBalls.delete(n);
    } else {
      if (includedBalls.size >= 5) {
        showToast('고정수는 최대 5개까지만 선택할 수 있습니다.', 'error');
        return;
      }
      excludedBalls.delete(n);
      includedBalls.add(n);
    }
  } else {
    if (excludedBalls.has(n)) {
      excludedBalls.delete(n);
    } else {
      if (excludedBalls.size >= 39) {
        showToast('최소 6개의 번호는 남아있어야 합니다.', 'error');
        return;
      }
      includedBalls.delete(n);
      excludedBalls.add(n);
    }
  }
  updateBallGridUi();
}

function clearBallSelections() {
  includedBalls.clear();
  excludedBalls.clear();
  updateBallGridUi();
}

function updateBallGridUi() {
  for (let n = 1; n <= 45; n++) {
    const el = document.getElementById(`grid-ball-${n}`);
    if (!el) continue;
    el.classList.remove('ball-included', 'ball-excluded');

    if (includedBalls.has(n)) {
      el.classList.add('ball-included');
    } else if (excludedBalls.has(n)) {
      el.classList.add('ball-excluded');
    }
  }

  document.getElementById('includeCount').textContent = includedBalls.size;
  document.getElementById('excludeCount').textContent = excludedBalls.size;
}

async function generateNumbers() {
  const btn = document.getElementById('btnGenerate');
  btn.disabled = true;
  btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> <span>분석 및 최적 조합 생성 중...</span>';

  try {
    const payload = {
      strategy: currentStrategy,
      count: currentGameCount,
      include_numbers: Array.from(includedBalls),
      exclude_numbers: Array.from(excludedBalls)
    };

    const res = await fetch('/api/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const json = await res.json();

    if (json.status !== 'success') {
      showToast(json.message || '생성 실패', 'error');
      return;
    }

    generatedGamesCache = json.games;
    renderGeneratedTickets(generatedGamesCache);
    showToast(`총 ${json.games.length}게임의 스마트 추천 번호가 생성되었습니다!`, 'success');
  } catch (err) {
    console.error(err);
    showToast('번호 생성 중 통신 오류가 발생했습니다.', 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i> <span>스마트 번호 추천 생성하기</span>';
  }
}

function renderGeneratedTickets(games) {
  const area = document.getElementById('generatedResultsArea');
  const container = document.getElementById('ticketCardsContainer');
  area.classList.remove('hidden');
  container.innerHTML = '';

  const chunks = [];
  for (let i = 0; i < games.length; i += 5) {
    chunks.push(games.slice(i, i + 5));
  }

  chunks.forEach((chunk, chunkIdx) => {
    const ticketCard = document.createElement('div');
    ticketCard.className = 'ticket-card p-5';

    let rowsHtml = chunk.map(g => {
      const ballsHtml = g.numbers.map(n => createBallHtml(n, 'sm')).join('');
      const scoreBadge = g.score >= 90
        ? `<span class="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 font-bold text-[10px] border border-emerald-500/30">적합도 ${g.score}점</span>`
        : `<span class="px-2 py-0.5 rounded bg-amber-500/20 text-amber-400 font-bold text-[10px] border border-amber-500/30">적합도 ${g.score}점</span>`;

      return `
        <div class="ticket-game-row">
          <div class="flex items-center gap-3">
            <span class="w-5 text-center font-extrabold text-amber-400 text-sm">${g.game_index}</span>
            <div class="flex items-center gap-1.5 sm:gap-2">${ballsHtml}</div>
          </div>
          <div class="text-right hidden sm:block">
            <div class="flex items-center gap-1 justify-end">
              ${scoreBadge}
            </div>
            <span class="text-[10px] text-slate-400 block mt-0.5">합:${g.sum} | 홀짝:${g.odd_even} | AC:${g.ac}</span>
          </div>
        </div>
      `;
    }).join('');

    ticketCard.innerHTML = `
      <div class="flex items-center justify-between pb-3 mb-3 border-b border-slate-700/60">
        <div class="flex items-center gap-2">
          <span class="w-2.5 h-2.5 rounded-full bg-emerald-400"></span>
          <span class="font-extrabold text-white text-sm">로또 6/45 맞춤 슬립 #${chunkIdx + 1}</span>
        </div>
        <span class="text-xs text-slate-400">${getStrategyName(currentStrategy)}</span>
      </div>
      <div class="space-y-1.5">${rowsHtml}</div>
    `;

    container.appendChild(ticketCard);
  });
}

function getStrategyName(strat) {
  switch (strat) {
    case 'golden': return '🏆 황금 밸런스';
    case 'hot': return '🔥 최다 빈도';
    case 'cold': return '❄️ 미출현 반등';
    case 'trend': return '📈 최근 트렌드';
    default: return '🎲 자동 무작위';
  }
}

function copyGeneratedNumbers() {
  if (!generatedGamesCache.length) return;
  const text = generatedGamesCache.map(g => `[게임 ${g.game_index}] ${g.numbers.join(', ')} (총합: ${g.sum}, 홀짝: ${g.odd_even})`).join('\n');
  navigator.clipboard.writeText(text).then(() => {
    showToast('생성된 번호가 클립보드에 복사되었습니다!', 'success');
  }).catch(() => {
    showToast('복사에 실패했습니다.', 'error');
  });
}

function sendGeneratedToSimulator() {
  if (!generatedGamesCache.length) {
    showToast('먼저 추천 번호를 생성해주세요.', 'error');
    return;
  }

  let added = 0;
  generatedGamesCache.forEach(g => {
    if (simCombinations.length < 50) {
      simCombinations.push(g.numbers);
      added++;
    }
  });

  updateComboChipsUi();
  switchTab('simulator');
  showToast(`${added}개의 추천 조합이 50개 시뮬레이터에 등록되었습니다!`, 'success');
}

// ==========================================
// 5. 50개 번호조합 백테스팅 시뮬레이터
// ==========================================
function setupManualInputs() {
  for (let i = 1; i <= 6; i++) {
    const input = document.getElementById(`manualNum${i}`);
    if (input) {
      input.addEventListener('input', (e) => {
        const val = parseInt(e.target.value);
        if (val > 45) e.target.value = 45;
        if (val < 1 && e.target.value !== '') e.target.value = 1;
        if (e.target.value.length >= 2 && i < 6) {
          const next = document.getElementById(`manualNum${i + 1}`);
          if (next) next.focus();
        }
      });
    }
  }
}

function addManualCombo() {
  if (simCombinations.length >= 50) {
    showToast('최대 50개 조합까지만 등록할 수 있습니다.', 'error');
    return;
  }

  const numbers = [];
  for (let i = 1; i <= 6; i++) {
    const val = parseInt(document.getElementById(`manualNum${i}`).value);
    if (isNaN(val) || val < 1 || val > 45) {
      showToast(`${i}번째 번호를 올바르게 입력해주세요 (1~45).`, 'error');
      return;
    }
    numbers.push(val);
  }

  const unique = new Set(numbers);
  if (unique.size !== 6) {
    showToast('중복되지 않는 6개 번호를 입력해야 합니다.', 'error');
    return;
  }

  simCombinations.push(sortedNumbers(numbers));
  updateComboChipsUi();
  showToast('조합이 추가되었습니다.', 'success');

  // 인풋 초기화
  for (let i = 1; i <= 6; i++) {
    document.getElementById(`manualNum${i}`).value = '';
  }
}

function parseAndAddCombos() {
  const text = document.getElementById('simPasteArea').value.trim();
  if (!text) {
    showToast('붙여넣을 번호 텍스트를 입력해주세요.', 'error');
    return;
  }

  const lines = text.split('\n');
  let addedCount = 0;

  for (const line of lines) {
    if (simCombinations.length >= 50) break;
    const matches = line.match(/\b([1-9]|[1-3][0-9]|4[0-5])\b/g);
    if (matches && matches.length >= 6) {
      const nums = matches.slice(0, 6).map(Number);
      const unique = new Set(nums);
      if (unique.size === 6) {
        simCombinations.push(sortedNumbers(nums));
        addedCount++;
      }
    }
  }

  updateComboChipsUi();
  document.getElementById('simPasteArea').value = '';

  if (addedCount > 0) {
    showToast(`총 ${addedCount}개의 번호 조합이 등록되었습니다!`, 'success');
  } else {
    showToast('유효한 6자리 번호 조합을 찾을 수 없습니다.', 'error');
  }
}

function sortedNumbers(arr) {
  return [...arr].sort((a, b) => a - b);
}

function generateRandom6() {
  const nums = [];
  while (nums.length < 6) {
    const r = Math.floor(Math.random() * 45) + 1;
    if (!nums.includes(r)) nums.push(r);
  }
  return sortedNumbers(nums);
}

function addRandomCombos(count) {
  let added = 0;
  for (let i = 0; i < count; i++) {
    if (simCombinations.length >= 50) break;
    simCombinations.push(generateRandom6());
    added++;
  }
  updateComboChipsUi();
  if (added > 0) {
    showToast(`랜덤 ${added}개 조합이 추가되었습니다.`, 'success');
  }
}

function fillRandom50Combos() {
  simCombinations = [];
  for (let i = 0; i < 50; i++) {
    simCombinations.push(generateRandom6());
  }
  updateComboChipsUi();
  showToast('랜덤 50개 조합이 가득 채워졌습니다!', 'success');
}

function loadGeneratedCombosToSim() {
  if (!generatedGamesCache.length) {
    showToast('스마트 번호 추천 탭에서 먼저 번호를 생성해주세요.', 'error');
    return;
  }
  let added = 0;
  generatedGamesCache.forEach(g => {
    if (simCombinations.length < 50) {
      simCombinations.push(g.numbers);
      added++;
    }
  });
  updateComboChipsUi();
  showToast(`추천 번호 ${added}개가 추가되었습니다.`, 'success');
}

function clearAllCombos() {
  simCombinations = [];
  updateComboChipsUi();
  document.getElementById('multiSimResultArea').classList.add('hidden');
  showToast('모든 조합이 비워졌습니다.', 'info');
}

function removeCombo(idx) {
  simCombinations.splice(idx, 1);
  updateComboChipsUi();
}

function updateComboChipsUi() {
  const count = simCombinations.length;
  document.getElementById('comboCountBadge').textContent = count;
  document.getElementById('comboChipsCount').textContent = count;
  document.getElementById('simBtnLabel').textContent = `등록된 ${count}개 조합 백테스팅 실행하기`;

  const grid = document.getElementById('comboChipsGrid');
  if (!count) {
    grid.innerHTML = '<span class="text-xs text-slate-500 py-3 block w-full text-center">등록된 번호 조합이 없습니다. 위의 버튼을 눌러 번호를 등록해주세요.</span>';
    return;
  }

  grid.innerHTML = simCombinations.map((combo, idx) => {
    const ballsHtml = combo.map(n => createBallHtml(n, 'mini')).join('');
    return `
      <div class="combo-chip">
        <span class="font-extrabold text-blue-400">#${idx + 1}</span>
        <div class="flex items-center gap-0.5">${ballsHtml}</div>
        <span onclick="removeCombo(${idx})" class="combo-chip-remove" title="삭제">✕</span>
      </div>
    `;
  }).join('');
}

async function runMultiSimulation() {
  if (!simCombinations.length) {
    showToast('최소 1개 이상의 번호 조합을 등록해주세요.', 'error');
    return;
  }

  const btn = document.getElementById('btnRunMultiSim');
  btn.disabled = true;
  btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> <span>${simCombinations.length}개 조합 전 회차 백테스팅 계산 중...</span>`;

  try {
    const res = await fetch('/api/simulate-multi', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ combinations: simCombinations })
    });
    const json = await res.json();

    if (json.status !== 'success') {
      showToast(json.message || '시뮬레이션 실패', 'error');
      return;
    }

    renderMultiSimResult(json.result);
    showToast(`총 ${json.result.total_combos_tested}개 조합의 백테스팅이 완료되었습니다!`, 'success');
  } catch (err) {
    console.error(err);
    showToast('시뮬레이션 통신 중 오류가 발생했습니다.', 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<i class="fa-solid fa-play"></i> <span>등록된 ${simCombinations.length}개 조합 백테스팅 실행하기</span>`;
  }
}

function renderMultiSimResult(result) {
  const area = document.getElementById('multiSimResultArea');
  area.classList.remove('hidden');

  // 종합 요약
  document.getElementById('msTotalSpent').textContent = `${result.total_spent.toLocaleString()}원`;
  document.getElementById('msGamesCountLabel').textContent = `총 ${result.total_combos_tested}개 조합 × ${result.total_draws_tested}회 = ${result.total_games_played.toLocaleString()}게임`;

  document.getElementById('msTotalPrize').textContent = `${result.total_prize_earned.toLocaleString()}원`;
  const totalWins = Object.values(result.rank_counts).reduce((a, b) => a + b, 0);
  document.getElementById('msWinCountLabel').textContent = `총 ${totalWins.toLocaleString()}회 당첨`;

  const profitEl = document.getElementById('msNetProfit');
  const profitSub = document.getElementById('msNetProfitSub');
  if (result.net_profit >= 0) {
    profitEl.textContent = `+${result.net_profit.toLocaleString()}원`;
    profitEl.className = 'text-2xl font-bold mt-1 text-emerald-400';
    profitSub.textContent = '🎉 전체 흑자 기록!';
  } else {
    profitEl.textContent = `${result.net_profit.toLocaleString()}원`;
    profitEl.className = 'text-2xl font-bold mt-1 text-rose-400';
    profitSub.textContent = '손실 기록';
  }

  const roiEl = document.getElementById('msRoi');
  if (result.roi_percentage >= 0) {
    roiEl.textContent = `+${result.roi_percentage.toLocaleString()}%`;
    roiEl.className = 'text-2xl font-bold mt-1 text-emerald-400';
  } else {
    roiEl.textContent = `${result.roi_percentage.toLocaleString()}%`;
    roiEl.className = 'text-2xl font-bold mt-1 text-rose-400';
  }

  document.getElementById('msHighestRank').textContent = result.highest_rank
    ? `최고 성적: ${result.highest_rank}등 달성!`
    : '당첨 없음';

  // 등수별 종합 그리드
  const ranks = [
    { rank: '1등', count: result.rank_counts[1], color: 'text-amber-400', desc: '6개 일치' },
    { rank: '2등', count: result.rank_counts[2], color: 'text-blue-400', desc: '5개+보너스' },
    { rank: '3등', count: result.rank_counts[3], color: 'text-cyan-400', desc: '5개 일치' },
    { rank: '4등', count: result.rank_counts[4], color: 'text-emerald-400', desc: '4개 일치 (5만원)' },
    { rank: '5등', count: result.rank_counts[5], color: 'text-slate-300', desc: '3개 일치 (5천원)' },
  ];
  document.getElementById('msRankGrid').innerHTML = ranks.map(r => `
    <div class="bg-slate-900/80 p-3 rounded-xl border border-slate-700/60">
      <div class="text-xs font-bold ${r.color}">${r.rank}</div>
      <div class="text-xl font-extrabold text-white mt-1">${r.count.toLocaleString()}회</div>
      <div class="text-[10px] text-slate-500 mt-0.5">${r.desc}</div>
    </div>
  `).join('');

  // 조합별 성적 랭킹 테이블 (1위 ~ 50위)
  document.getElementById('msComboTableCount').textContent = result.combos.length;
  const tbody = document.getElementById('msCombosTableBody');
  tbody.innerHTML = result.combos.map(item => {
    const ballsHtml = item.numbers.map(n => createBallHtml(n, 'mini')).join(' ');
    const rankBadge = item.highest_rank
      ? `<span class="px-2 py-0.5 rounded font-black text-[11px] ${item.highest_rank === 1 ? 'bg-amber-400/20 text-amber-300 border border-amber-400/40' : item.highest_rank === 2 ? 'bg-blue-400/20 text-blue-300 border border-blue-400/40' : item.highest_rank === 3 ? 'bg-cyan-400/20 text-cyan-300' : 'bg-slate-700 text-slate-300'}">${item.highest_rank}등</span>`
      : '<span class="text-slate-600">-</span>';

    const profitColor = item.net_profit >= 0 ? 'text-emerald-400' : 'text-slate-400';
    const standingBadge = item.standing <= 3
      ? `<span class="w-5 h-5 rounded-full bg-amber-500/20 text-amber-400 font-extrabold flex items-center justify-center text-xs">${item.standing}</span>`
      : `<span class="text-slate-500 font-bold ml-1">${item.standing}</span>`;

    return `
      <tr class="hover:bg-slate-800/50 transition">
        <td class="py-2.5 px-3">${standingBadge}</td>
        <td class="py-2.5 px-3 font-extrabold text-blue-400">#${item.combo_id}</td>
        <td class="py-2.5 px-3"><div class="flex items-center gap-1">${ballsHtml}</div></td>
        <td class="py-2.5 px-3 text-center">${rankBadge}</td>
        <td class="py-2.5 px-3 text-center text-slate-300 font-medium">
          ${item.rank_counts[1]} / ${item.rank_counts[2]} / ${item.rank_counts[3]}
        </td>
        <td class="py-2.5 px-3 text-center text-slate-400">
          ${item.rank_counts[4]} / ${item.rank_counts[5]}
        </td>
        <td class="py-2.5 px-3 text-right font-bold text-emerald-400">${item.total_prize.toLocaleString()}원</td>
        <td class="py-2.5 px-3 text-right font-semibold ${profitColor}">${item.roi > 0 ? '+' : ''}${item.roi}%</td>
      </tr>
    `;
  }).join('');

  // 고액 당첨 이력 테이블
  const highWinsBody = document.getElementById('msHighWinsTableBody');
  if (!result.high_wins || !result.high_wins.length) {
    highWinsBody.innerHTML = '<tr><td colspan="6" class="py-6 text-center text-slate-500">1등~3등 당첨 이력이 없습니다.</td></tr>';
  } else {
    highWinsBody.innerHTML = result.high_wins.map(w => {
      const matchedHtml = w.matched_numbers.map(n => createBallHtml(n, 'mini')).join(' ');
      const rankBadge = w.rank === 1
        ? '<span class="px-2 py-0.5 rounded bg-amber-400/20 text-amber-300 font-black border border-amber-400/40">1등</span>'
        : w.rank === 2
        ? '<span class="px-2 py-0.5 rounded bg-blue-400/20 text-blue-300 font-black border border-blue-400/40">2등</span>'
        : '<span class="px-2 py-0.5 rounded bg-cyan-400/20 text-cyan-300 font-bold">3등</span>';

      return `
        <tr class="hover:bg-slate-800/40 transition">
          <td class="py-2.5 px-3 font-bold text-white">${w.drw_no}회</td>
          <td class="py-2.5 px-3 text-slate-400">${w.date}</td>
          <td class="py-2.5 px-3 font-bold text-blue-400">#${w.combo_id}번 조합</td>
          <td class="py-2.5 px-3">${rankBadge}</td>
          <td class="py-2.5 px-3"><div class="flex items-center gap-1">${matchedHtml}</div></td>
          <td class="py-2.5 px-3 text-right font-bold text-emerald-400">${w.prize.toLocaleString()}원</td>
        </tr>
      `;
    }).join('');
  }
}

// ==========================================
// 6. 역대 회차 조회
// ==========================================
async function loadHistory(page = 1) {
  try {
    const query = encodeURIComponent(historySearchQuery);
    const res = await fetch(`/api/history?page=${page}&limit=15&search=${query}`);
    const json = await res.json();
    if (json.status !== 'success') return;

    historyCurrentPage = json.page;
    historyTotalPages = json.total_pages;

    document.getElementById('historyPageInfo').textContent = `${historyCurrentPage} / ${historyTotalPages || 1} 페이지 (총 ${json.total}건)`;
    document.getElementById('btnPrevPage').disabled = historyCurrentPage <= 1;
    document.getElementById('btnNextPage').disabled = historyCurrentPage >= historyTotalPages;

    const tbody = document.getElementById('historyTableBody');
    if (!json.data.length) {
      tbody.innerHTML = `<tr><td colspan="5" class="py-8 text-center text-slate-500">검색 결과가 없습니다.</td></tr>`;
      return;
    }

    tbody.innerHTML = json.data.map(d => {
      const balls = [d.num1, d.num2, d.num3, d.num4, d.num5, d.num6].map(n => createBallHtml(n, 'sm')).join(' ');
      const bonusBall = createBallHtml(d.bonus, 'sm');

      return `
        <tr class="hover:bg-slate-800/50 transition">
          <td class="py-3 px-3 font-extrabold text-amber-400 text-sm">${d.drw_no}회</td>
          <td class="py-3 px-3 text-slate-400">${d.date}</td>
          <td class="py-3 px-3">
            <div class="flex items-center gap-1.5 flex-wrap">
              ${balls}
              <span class="text-slate-500 font-bold px-1">+</span>
              ${bonusBall}
            </div>
          </td>
          <td class="py-3 px-3 text-white font-medium">${d.winner_count}명</td>
          <td class="py-3 px-3 text-right font-bold text-emerald-400">${Number(d.prize_amount).toLocaleString()}원</td>
        </tr>
      `;
    }).join('');
  } catch (err) {
    console.error(err);
  }
}

function searchHistory() {
  historySearchQuery = document.getElementById('historySearchInput').value.trim();
  loadHistory(1);
}

document.getElementById('historySearchInput').addEventListener('keydown', (e) => {
  if (e.key === 'Enter') searchHistory();
});

function prevHistoryPage() {
  if (historyCurrentPage > 1) loadHistory(historyCurrentPage - 1);
}

function nextHistoryPage() {
  if (historyCurrentPage < historyTotalPages) loadHistory(historyCurrentPage + 1);
}

// ==========================================
// 7. 데이터 최신화 동기화
// ==========================================
async function syncData() {
  const btn = document.getElementById('btnSync');
  const icon = document.getElementById('syncIcon');
  btn.disabled = true;
  icon.classList.add('fa-spin');

  showToast('동행복권 서버에서 최신 회차 데이터를 동기화하는 중입니다...', 'info');

  try {
    const res = await fetch('/api/sync', { method: 'POST' });
    const json = await res.json();

    if (json.status === 'success') {
      showToast(`동기화 완료! (최신 회차: ${json.result.latest_draw}회)`, 'success');
      await loadDashboardData(currentPeriod);
      await loadHistory(1);
      if (currentTab === 'matches') loadMatchesForTarget(matchCurrentTargetDrwNo);
    } else {
      showToast(json.message || '동기화 실패', 'error');
    }
  } catch (err) {
    console.error(err);
    showToast('동기화 요청 중 오류가 발생했습니다.', 'error');
  } finally {
    btn.disabled = false;
    icon.classList.remove('fa-spin');
  }
}
