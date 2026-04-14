# Investment Command Center v2.0

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from ta.momentum import RSIIndicator
from dataclasses import dataclass
from typing import Optional
from enum import Enum
from datetime import datetime

# ──────────────────────────────────────────────

# Domain Models

# ──────────────────────────────────────────────

class Signal(Enum):
STRONG_BUY = “STRONG_BUY”
VALUE_ONLY = “VALUE_ONLY”
TECH_ONLY = “TECH_ONLY”
WAIT = “WAIT”

SIGNAL_DISPLAY = {
Signal.STRONG_BUY: {“icon”: “🔴”, “label”: “강력 매수”, “color”: “#ef4444”, “bg”: “#7f1d1d”},
Signal.VALUE_ONLY: {“icon”: “📊”, “label”: “가치 충족”, “color”: “#3b82f6”, “bg”: “#1e3a5f”},
Signal.TECH_ONLY: {“icon”: “📈”, “label”: “기술 충족”, “color”: “#10b981”, “bg”: “#064e3b”},
Signal.WAIT: {“icon”: “⏳”, “label”: “대기”, “color”: “#64748b”, “bg”: “#1e293b”},
}

@dataclass
class SectorConfig:
name: str
default_per: float

@dataclass
class StockMetrics:
ticker: str
name: str
sector: str
current_price: Optional[float]
per: Optional[float]
pbr: Optional[float]
roe: Optional[float]
ma120: Optional[float]
ma120_gap: Optional[float]
rsi: Optional[float]
sector_per_limit: float
volatility: Optional[float]
entry_price: Optional[float]
signal: Signal
value_pass: bool
tech_pass: bool

@dataclass
class PortfolioEntry:
ticker: str
buy_price: float
quantity: int
buy_date: str

# ──────────────────────────────────────────────

# Sector PER Configuration

# ──────────────────────────────────────────────

DEFAULT_SECTOR_PER = {
“Technology”: SectorConfig(“Technology/IT”, 25),
“Financial Services”: SectorConfig(“Financial/금융”, 12),
“Energy”: SectorConfig(“Energy/에너지”, 14),
“Consumer Cyclical”: SectorConfig(“Consumer Discretionary/소비재”, 18),
“Healthcare”: SectorConfig(“Healthcare/헬스케어”, 22),
“Industrials”: SectorConfig(“Industrials/산업재”, 17),
“ETF”: SectorConfig(“ETF”, 22),
“Unknown”: SectorConfig(“기타/Unknown”, 15),
}

SECTOR_KR_MAP = {
“Technology”: “IT”,
“Financial Services”: “금융”,
“Energy”: “에너지”,
“Consumer Cyclical”: “소비재”,
“Healthcare”: “헬스케어”,
“Industrials”: “산업재”,
“Communication Services”: “통신”,
“Consumer Defensive”: “필수소비재”,
“Real Estate”: “부동산”,
“Utilities”: “유틸리티”,
“Basic Materials”: “소재”,
“ETF”: “ETF”,
“Unknown”: “기타”,
}

# ──────────────────────────────────────────────

# Data Repository

# ──────────────────────────────────────────────

class StockRepository:
“”“yfinance 데이터 접근 계층”””

```
@staticmethod
@st.cache_data(ttl=600, show_spinner=False)
def fetch_info(ticker: str) -> dict:
    try:
        return yf.Ticker(ticker).info or {}
    except Exception:
        return {}

@staticmethod
@st.cache_data(ttl=600, show_spinner=False)
def fetch_history(ticker: str, period: str = "1y") -> pd.DataFrame:
    try:
        return yf.Ticker(ticker).history(period=period)
    except Exception:
        return pd.DataFrame()
```

# ──────────────────────────────────────────────

# Analysis Service

# ──────────────────────────────────────────────

class AnalysisService:
“”“종목 분석 비즈니스 로직”””

```
ETF_TICKERS = {"SPY", "QQQ", "IVV", "VOO", "TQQQ", "SOXL", "IWM", "DIA", "VTI", "SCHD"}

def __init__(self, sector_per_config: dict[str, float]):
    self.sector_per = sector_per_config

def _resolve_sector(self, info: dict, ticker: str) -> str:
    if ticker.upper() in self.ETF_TICKERS:
        return "ETF"
    sector = info.get("sector", "")
    return sector if sector else "Unknown"

def _get_sector_per_limit(self, sector: str) -> float:
    return self.sector_per.get(sector, self.sector_per.get("Unknown", 15))

def _calc_technical(self, hist: pd.DataFrame) -> tuple:
    if hist.empty or len(hist) < 14:
        return None, None, None, None

    close = hist["Close"]
    ma120 = close.rolling(window=120).mean().iloc[-1] if len(close) >= 120 else None
    current = close.iloc[-1]
    ma120_gap = ((current - ma120) / ma120) * 100 if ma120 and ma120 > 0 else None

    rsi_series = RSIIndicator(close, window=14).rsi()
    rsi = rsi_series.iloc[-1] if not rsi_series.empty else None

    returns = close.pct_change().dropna()
    vol = returns.tail(20).std() * np.sqrt(252) * 100 if len(returns) >= 20 else None

    return ma120, ma120_gap, rsi, vol

def analyze(self, ticker: str) -> StockMetrics:
    info = StockRepository.fetch_info(ticker)
    hist = StockRepository.fetch_history(ticker, period="1y")

    name = info.get("shortName", info.get("longName", ticker))
    sector = self._resolve_sector(info, ticker)
    sector_kr = SECTOR_KR_MAP.get(sector, sector)
    sector_per_limit = self._get_sector_per_limit(sector)

    current_price = info.get("currentPrice") or info.get("regularMarketPrice")
    if current_price is None and not hist.empty:
        current_price = float(hist["Close"].iloc[-1])

    per = info.get("trailingPE") or info.get("forwardPE")
    pbr = info.get("priceToBook")
    roe_raw = info.get("returnOnEquity")
    roe = roe_raw * 100 if roe_raw and abs(roe_raw) < 10 else roe_raw

    ma120, ma120_gap, rsi, vol = self._calc_technical(hist)

    # ── 가치 판정 ──
    value_pass = False
    if per is not None and pbr is not None and roe is not None:
        per_ok = per > 0 and per < 15 and per < sector_per_limit
        pbr_ok = pbr < 1.5
        roe_ok = roe > 10
        value_pass = per_ok and pbr_ok and roe_ok

    # ── 기술 판정 ──
    tech_pass = False
    if ma120_gap is not None and abs(ma120_gap) <= 5:
        tech_pass = True
    if rsi is not None and rsi <= 35:
        tech_pass = True

    # ── 시그널 ──
    if value_pass and tech_pass:
        signal = Signal.STRONG_BUY
    elif value_pass:
        signal = Signal.VALUE_ONLY
    elif tech_pass:
        signal = Signal.TECH_ONLY
    else:
        signal = Signal.WAIT

    # ── 타점 계산 ──
    entry_price = None
    if current_price:
        base_entry = current_price
        if ma120 and current_price > ma120:
            base_entry = ma120
        if vol and vol > 30:
            discount = 0.03 + min((vol - 30) / 100, 0.02)
            base_entry = base_entry * (1 - discount)
        entry_price = round(base_entry, 2)

    return StockMetrics(
        ticker=ticker,
        name=name,
        sector=sector_kr,
        current_price=round(current_price, 2) if current_price else None,
        per=round(per, 2) if per else None,
        pbr=round(pbr, 2) if pbr else None,
        roe=round(roe, 2) if roe else None,
        ma120=round(ma120, 2) if ma120 else None,
        ma120_gap=round(ma120_gap, 2) if ma120_gap is not None else None,
        rsi=round(rsi, 2) if rsi else None,
        sector_per_limit=sector_per_limit,
        volatility=round(vol, 2) if vol else None,
        entry_price=entry_price,
        signal=signal,
        value_pass=value_pass,
        tech_pass=tech_pass,
    )
```

# ──────────────────────────────────────────────

# Chart Builder (모바일 최적화)

# ──────────────────────────────────────────────

class ChartBuilder:

```
@staticmethod
def build_candle_chart(ticker: str, name: str) -> go.Figure:
    hist = StockRepository.fetch_history(ticker, period="1y")
    if hist.empty:
        fig = go.Figure()
        fig.add_annotation(text="데이터 없음", x=0.5, y=0.5,
                           xref="paper", yref="paper", showarrow=False,
                           font=dict(color="#94a3b8", size=16))
        fig.update_layout(height=300, paper_bgcolor="#0f172a", plot_bgcolor="#1e293b")
        return fig

    close = hist["Close"]
    ma120 = close.rolling(120).mean()
    rsi_series = RSIIndicator(close, window=14).rsi()

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        vertical_spacing=0.1,
        row_heights=[0.7, 0.3],
        subplot_titles=[f"{name}", "RSI (14)"],
    )

    # 캔들차트
    fig.add_trace(go.Candlestick(
        x=hist.index, open=hist["Open"], high=hist["High"],
        low=hist["Low"], close=hist["Close"],
        name="캔들",
        increasing_line_color="#ef4444", increasing_fillcolor="#ef4444",
        decreasing_line_color="#3b82f6", decreasing_fillcolor="#3b82f6",
    ), row=1, col=1)

    # 120일선
    fig.add_trace(go.Scatter(
        x=hist.index, y=ma120, name="120일선",
        line=dict(color="#f59e0b", width=2, dash="dot"),
    ), row=1, col=1)

    # RSI
    fig.add_trace(go.Scatter(
        x=hist.index, y=rsi_series, name="RSI",
        line=dict(color="#a78bfa", width=1.5),
        fill="tozeroy", fillcolor="rgba(139,92,246,0.08)",
    ), row=2, col=1)

    fig.add_hline(y=35, line_dash="dash", line_color="#ef4444",
                  annotation_text="35", row=2, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="#6b7280",
                  annotation_text="70", row=2, col=1)

    # 모바일 최적화 레이아웃
    fig.update_layout(
        height=420,
        xaxis_rangeslider_visible=False,
        template="plotly_dark",
        paper_bgcolor="#0f172a",
        plot_bgcolor="#1e293b",
        font=dict(color="#94a3b8", size=11),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.06,
            font=dict(size=10),
        ),
        margin=dict(l=45, r=10, t=50, b=20),
        dragmode="pan",  # 모바일에서 핀치 줌 대신 팬
    )
    fig.update_xaxes(gridcolor="#1e293b", showgrid=True)
    fig.update_yaxes(gridcolor="#1e293b", showgrid=True)

    return fig
```

# ──────────────────────────────────────────────

# Streamlit UI Helpers

# ──────────────────────────────────────────────

def fmt(value, suffix=””, fallback=“N/A”):
“”“안전한 포맷팅”””
if value is None:
return fallback
if isinstance(value, float):
if abs(value) >= 1000:
return f”{value:,.0f}{suffix}”
return f”{value:.2f}{suffix}”
return f”{value}{suffix}”

def signal_html(signal: Signal) -> str:
d = SIGNAL_DISPLAY[signal]
return (
f’<span style=“display:inline-block;padding:3px 10px;border-radius:6px;’
f’font-size:12px;font-weight:700;’
f’background:{d[“bg”]};color:{d[“color”]};’
f’border:1px solid {d[“color”]}30;”>’
f’{d[“icon”]} {d[“label”]}</span>’
)

def metric_color(value, good_fn=None, warn_fn=None):
“”“조건부 색상”””
if value is None:
return “#475569”
if good_fn and good_fn(value):
return “#4ade80”
if warn_fn and warn_fn(value):
return “#f87171”
return “#e2e8f0”

# ──────────────────────────────────────────────

# Mobile Card Component

# ──────────────────────────────────────────────

def render_stock_card(m: StockMetrics):
“”“모바일 최적화 종목 카드”””
d = SIGNAL_DISPLAY[m.signal]
is_strong = m.signal == Signal.STRONG_BUY

```
border_color = d["color"] if is_strong else "#1e293b"
bg = "linear-gradient(135deg, #2a1215 0%, #1a0a0c 100%)" if is_strong else "linear-gradient(135deg, #111827 0%, #0f172a 100%)"

# PER 색상
per_color = "#475569"
if m.per is not None:
    per_color = "#4ade80" if (m.per > 0 and m.per < 15 and m.per < m.sector_per_limit) else "#f87171"

# RSI 색상
rsi_color = "#475569"
if m.rsi is not None:
    rsi_color = "#4ade80" if m.rsi <= 35 else ("#f87171" if m.rsi > 70 else "#e2e8f0")

# 이격도 색상
gap_color = "#475569"
if m.ma120_gap is not None:
    gap_color = "#4ade80" if abs(m.ma120_gap) <= 5 else "#e2e8f0"

card_html = f"""
<div style="
    background:{bg};
    border:1px solid {border_color};
    border-radius:14px;
    padding:16px;
    margin-bottom:12px;
    {'box-shadow:0 0 20px rgba(239,68,68,0.15);' if is_strong else ''}
">
    <!-- 헤더: 종목명 + 시그널 -->
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
        <div>
            <div style="font-size:16px;font-weight:700;color:#f1f5f9;">{m.name}</div>
            <div style="font-size:12px;color:#475569;margin-top:2px;">{m.ticker} · {m.sector}</div>
        </div>
        {signal_html(m.signal)}
    </div>

    <!-- 현재가 & 타점 -->
    <div style="display:flex;gap:12px;margin-bottom:14px;">
        <div style="flex:1;background:#0c1222;border-radius:10px;padding:10px 12px;border:1px solid #1e293b;">
            <div style="font-size:10px;color:#64748b;margin-bottom:2px;">현재가</div>
            <div style="font-size:18px;font-weight:700;color:#f1f5f9;">{fmt(m.current_price)}</div>
        </div>
        <div style="flex:1;background:#0c1222;border-radius:10px;padding:10px 12px;border:1px solid #f59e0b30;">
            <div style="font-size:10px;color:#f59e0b;margin-bottom:2px;">🎯 타점 (진입가)</div>
            <div style="font-size:18px;font-weight:700;color:#f59e0b;">{fmt(m.entry_price)}</div>
        </div>
    </div>

    <!-- 지표 그리드 -->
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;">
        <div style="text-align:center;padding:6px;background:#0a0f1a;border-radius:8px;">
            <div style="font-size:10px;color:#64748b;">PER</div>
            <div style="font-size:14px;font-weight:600;color:{per_color};">{fmt(m.per)}</div>
            <div style="font-size:9px;color:#475569;">기준 {m.sector_per_limit:.0f}</div>
        </div>
        <div style="text-align:center;padding:6px;background:#0a0f1a;border-radius:8px;">
            <div style="font-size:10px;color:#64748b;">PBR</div>
            <div style="font-size:14px;font-weight:600;color:{'#4ade80' if m.pbr and m.pbr < 1.5 else '#f87171' if m.pbr else '#475569'};">{fmt(m.pbr)}</div>
        </div>
        <div style="text-align:center;padding:6px;background:#0a0f1a;border-radius:8px;">
            <div style="font-size:10px;color:#64748b;">ROE</div>
            <div style="font-size:14px;font-weight:600;color:{'#4ade80' if m.roe and m.roe > 10 else '#f87171' if m.roe else '#475569'};">{fmt(m.roe, '%')}</div>
        </div>
        <div style="text-align:center;padding:6px;background:#0a0f1a;border-radius:8px;">
            <div style="font-size:10px;color:#64748b;">RSI</div>
            <div style="font-size:14px;font-weight:600;color:{rsi_color};">{fmt(m.rsi)}</div>
        </div>
        <div style="text-align:center;padding:6px;background:#0a0f1a;border-radius:8px;">
            <div style="font-size:10px;color:#64748b;">이격도</div>
            <div style="font-size:14px;font-weight:600;color:{gap_color};">{fmt(m.ma120_gap, '%')}</div>
        </div>
        <div style="text-align:center;padding:6px;background:#0a0f1a;border-radius:8px;">
            <div style="font-size:10px;color:#64748b;">변동성</div>
            <div style="font-size:14px;font-weight:600;color:#e2e8f0;">{fmt(m.volatility, '%')}</div>
        </div>
    </div>

    <!-- 판정 요약 -->
    <div style="display:flex;gap:8px;margin-top:10px;">
        <span style="font-size:11px;padding:3px 8px;border-radius:4px;
            background:{'#064e3b' if m.value_pass else '#1e293b'};
            color:{'#6ee7b7' if m.value_pass else '#475569'};">
            {'✅' if m.value_pass else '❌'} 가치
        </span>
        <span style="font-size:11px;padding:3px 8px;border-radius:4px;
            background:{'#064e3b' if m.tech_pass else '#1e293b'};
            color:{'#6ee7b7' if m.tech_pass else '#475569'};">
            {'✅' if m.tech_pass else '❌'} 기술
        </span>
        {'<span style="font-size:11px;padding:3px 8px;border-radius:4px;background:#7f1d1d;color:#fca5a5;font-weight:700;animation:pulse 1.5s infinite;">🔴 진입 타점 도달!</span>' if is_strong else ''}
    </div>
</div>
"""
st.markdown(card_html, unsafe_allow_html=True)
```

# ──────────────────────────────────────────────

# Portfolio Helpers

# ──────────────────────────────────────────────

def calc_portfolio_value(portfolio: list[PortfolioEntry]) -> tuple[float, list[dict]]:
total_value = 0.0
rows = []
for entry in portfolio:
info = StockRepository.fetch_info(entry.ticker)
hist = StockRepository.fetch_history(entry.ticker, period=“5d”)
current = info.get(“currentPrice”) or info.get(“regularMarketPrice”)
if current is None and not hist.empty:
current = float(hist[“Close”].iloc[-1])

```
    if current:
        market_val = current * entry.quantity
        pnl_pct = ((current - entry.buy_price) / entry.buy_price) * 100
        total_value += market_val
        rows.append({
            "ticker": entry.ticker, "buy_price": entry.buy_price,
            "quantity": entry.quantity, "current": current,
            "market_val": market_val, "pnl_pct": pnl_pct,
            "buy_date": entry.buy_date,
        })
    else:
        rows.append({
            "ticker": entry.ticker, "buy_price": entry.buy_price,
            "quantity": entry.quantity, "current": None,
            "market_val": 0, "pnl_pct": 0,
            "buy_date": entry.buy_date,
        })
return total_value, rows
```

# ──────────────────────────────────────────────

# Session State

# ──────────────────────────────────────────────

def init_session_state():
if “watchlist” not in st.session_state:
st.session_state.watchlist = [
“005930.KS”, “000270.KS”, “000660.KS”, “005380.KS”, “SPY”, “QQQ”
]
if “portfolio” not in st.session_state:
st.session_state.portfolio = []
if “sector_per_overrides” not in st.session_state:
st.session_state.sector_per_overrides = {}

def build_sector_per_config() -> dict[str, float]:
config = {}
for key, sc in DEFAULT_SECTOR_PER.items():
override = st.session_state.sector_per_overrides.get(key)
config[key] = override if override else sc.default_per
return config

# ──────────────────────────────────────────────

# Sidebar

# ──────────────────────────────────────────────

def render_sidebar():
with st.sidebar:
st.markdown(”## ⚙️ 설정”)

```
    # ── 종목 관리 ──
    st.markdown("### 📋 종목 관리")
    new_ticker = st.text_input("티커 입력", placeholder="예: AAPL, 035420.KS")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("➕ 추가", use_container_width=True):
            t = new_ticker.strip().upper()
            if t and t not in st.session_state.watchlist:
                st.session_state.watchlist.append(t)
                st.rerun()
    with c2:
        if st.button("🔄 새로고침", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    if st.session_state.watchlist:
        remove = st.selectbox("종목 삭제", ["선택하세요"] + st.session_state.watchlist)
        if remove != "선택하세요":
            if st.button(f"🗑️ {remove} 삭제"):
                st.session_state.watchlist.remove(remove)
                st.rerun()

    st.markdown("---")

    # ── 섹터 PER ──
    with st.expander("📊 섹터별 기준 PER 조정"):
        for key, sc in DEFAULT_SECTOR_PER.items():
            val = st.slider(
                sc.name, 5.0, 40.0,
                float(st.session_state.sector_per_overrides.get(key, sc.default_per)),
                1.0, key=f"sper_{key}",
            )
            st.session_state.sector_per_overrides[key] = val

    st.markdown("---")

    # ── 매수 이력 ──
    st.markdown("### 💰 매수 이력")
    buy_ticker = st.text_input("매수 종목", placeholder="005930.KS", key="bt")
    buy_price = st.number_input("매수 단가", 0.0, step=100.0, key="bp")
    buy_qty = st.number_input("수량", 1, step=1, key="bq")
    buy_date = st.date_input("매수일", datetime.today(), key="bd")

    if st.button("📝 매수 기록 추가", use_container_width=True):
        t = buy_ticker.strip().upper()
        if t and buy_price > 0:
            st.session_state.portfolio.append(
                PortfolioEntry(t, buy_price, buy_qty, buy_date.strftime("%Y-%m-%d"))
            )
            st.rerun()

    if st.session_state.portfolio:
        st.markdown("**기록된 이력:**")
        for i, p in enumerate(st.session_state.portfolio):
            c1, c2 = st.columns([3, 1])
            c1.caption(f"{p.ticker} · ₩{p.buy_price:,.0f} × {p.quantity}")
            if c2.button("🗑️", key=f"del_p_{i}"):
                st.session_state.portfolio.pop(i)
                st.rerun()
```

# ──────────────────────────────────────────────

# Main Render Functions

# ──────────────────────────────────────────────

def render_goal_progress(total_value: float):
GOAL = 50_000_000
pct = min(total_value / GOAL * 100, 100) if GOAL > 0 else 0

```
if pct > 60:
    bar_color = "linear-gradient(90deg, #10b981, #34d399)"
elif pct > 30:
    bar_color = "linear-gradient(90deg, #3b82f6, #60a5fa)"
else:
    bar_color = "linear-gradient(90deg, #6366f1, #818cf8)"

st.markdown(f"""
<div style="
    background:linear-gradient(135deg,#0c1222,#111a2e);
    border:1px solid #1e3a5f;border-radius:14px;
    padding:18px 20px;margin-bottom:20px;
">
    <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:4px;">
        <span style="color:#94a3b8;font-size:12px;">🏠 창릉 청약 자금</span>
        <span style="color:#64748b;font-size:11px;">₩{max(GOAL-total_value,0):,.0f} 남음</span>
    </div>
    <div style="font-size:24px;font-weight:800;color:#f1f5f9;margin-bottom:10px;">
        ₩{total_value:,.0f}
        <span style="font-size:13px;color:#475569;font-weight:400;"> / ₩{GOAL:,.0f}</span>
    </div>
    <div style="background:#0f172a;border-radius:8px;height:20px;border:1px solid #1e293b;overflow:hidden;">
        <div style="height:100%;border-radius:8px;width:{pct:.1f}%;
            background:{bar_color};
            display:flex;align-items:center;justify-content:center;
            font-size:10px;font-weight:700;color:#fff;">
            {f'{pct:.1f}%' if pct >= 10 else ''}
        </div>
    </div>
</div>
""", unsafe_allow_html=True)
```

def render_scanner(results: list[StockMetrics]):
st.markdown(”## 🔍 자동 스캐너”)

```
# 강력 매수 알림
strong_buys = [m for m in results if m.signal == Signal.STRONG_BUY]
if strong_buys:
    names = ", ".join(f"**{m.name}**" for m in strong_buys)
    st.error(f"🔴 강력 매수 시그널 감지: {names}")

# 섹터별 그루핑 + 카드 렌더링
sector_groups: dict[str, list[StockMetrics]] = {}
for r in results:
    sector_groups.setdefault(r.sector, []).append(r)

for sector, items in sorted(sector_groups.items()):
    st.markdown(f"#### 📁 {sector}")
    for m in items:
        render_stock_card(m)
```

def render_chart_view(results: list[StockMetrics]):
st.markdown(”## 📈 차트 뷰”)

```
options = {f"{m.name} ({m.ticker})": m for m in results}
selected = st.selectbox("종목 선택", list(options.keys()), key="chart_select")

if selected:
    m = options[selected]

    # 요약 메트릭 (2열)
    c1, c2 = st.columns(2)
    c1.metric("현재가", fmt(m.current_price))
    c2.metric("🎯 타점", fmt(m.entry_price))

    c3, c4 = st.columns(2)
    c3.metric("RSI", fmt(m.rsi))
    c4.metric("이격도", fmt(m.ma120_gap, "%"))

    fig = ChartBuilder.build_candle_chart(m.ticker, m.name)
    st.plotly_chart(fig, use_container_width=True, config={
        "displayModeBar": False,  # 모바일에서 버튼 바 숨김
        "scrollZoom": False,
    })
```

def render_portfolio():
st.markdown(”## 💼 포트폴리오”)

```
if not st.session_state.portfolio:
    st.info("👈 사이드바에서 매수 이력을 추가하세요")
    return 0.0

total_value, rows = calc_portfolio_value(st.session_state.portfolio)

for r in rows:
    pnl_color = "#4ade80" if r["pnl_pct"] > 0 else "#f87171" if r["pnl_pct"] < 0 else "#94a3b8"
    pnl_sign = "+" if r["pnl_pct"] > 0 else ""

    st.markdown(f"""
    <div style="
        background:#111827;border:1px solid #1e293b;border-radius:12px;
        padding:14px 16px;margin-bottom:8px;
        display:flex;justify-content:space-between;align-items:center;
    ">
        <div>
            <div style="font-size:14px;font-weight:600;color:#f1f5f9;">{r['ticker']}</div>
            <div style="font-size:11px;color:#475569;">
                ₩{r['buy_price']:,.0f} × {r['quantity']} · {r['buy_date']}
            </div>
        </div>
        <div style="text-align:right;">
            <div style="font-size:14px;font-weight:700;color:{pnl_color};">
                {pnl_sign}{r['pnl_pct']:.2f}%
            </div>
            <div style="font-size:11px;color:#94a3b8;">
                ₩{r['market_val']:,.0f}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown(f"""
<div style="text-align:right;font-size:16px;font-weight:700;color:#f59e0b;margin-top:8px;">
    총 평가: ₩{total_value:,.0f}
</div>
""", unsafe_allow_html=True)

return total_value
```

# ──────────────────────────────────────────────

# Main

# ──────────────────────────────────────────────

def main():
st.set_page_config(
page_title=“투자 사령부”,
page_icon=“🎖️”,
layout=“centered”,  # 모바일 최적화: centered
initial_sidebar_state=“collapsed”,  # 모바일에서 기본 접힘
)

```
# ── 글로벌 스타일 ──
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700;900&display=swap');

.stApp {
    background-color: #080d19;
}
[data-testid="stSidebar"] {
    background-color: #111827;
}
[data-testid="stSidebar"] * {
    color: #e2e8f0;
}
/* metric 카드 다크 테마 */
[data-testid="stMetric"] {
    background: #111827;
    border: 1px solid #1e293b;
    border-radius: 10px;
    padding: 12px;
}
[data-testid="stMetricLabel"] {
    color: #64748b !important;
}
[data-testid="stMetricValue"] {
    color: #f1f5f9 !important;
    font-size: 18px !important;
}
/* 구분선 */
hr { border-color: #1e293b !important; }
/* pulse 애니메이션 */
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}
/* selectbox, input 다크 */
.stSelectbox > div > div,
.stTextInput > div > div > input,
.stNumberInput > div > div > input {
    background-color: #0f172a !important;
    color: #e2e8f0 !important;
    border-color: #1e293b !important;
}
/* expander */
[data-testid="stExpander"] {
    border-color: #1e293b !important;
}
/* footer hide */
footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

init_session_state()
render_sidebar()

# ── 헤더 ──
st.markdown("""
<div style="margin-bottom:4px;">
    <div style="font-size:28px;font-weight:900;
        background:linear-gradient(135deg,#f59e0b,#ef4444);
        -webkit-background-clip:text;-webkit-text-fill-color:transparent;">
        🎖️ 투자 사령부
    </div>
    <div style="color:#475569;font-size:12px;margin-top:2px;">
        사령관 매수 원칙 기반 스캐너 · ⚠️ 데이터 15~20분 지연
    </div>
</div>
""", unsafe_allow_html=True)

# ── 포트폴리오 평가액 ──
total_portfolio = 0.0
if st.session_state.portfolio:
    total_portfolio, _ = calc_portfolio_value(st.session_state.portfolio)

render_goal_progress(total_portfolio)

# ── 스캔 실행 ──
sector_per_config = build_sector_per_config()
service = AnalysisService(sector_per_config)

with st.spinner("🔍 종목 스캔 중..."):
    results = []
    progress_bar = st.progress(0)
    for i, ticker in enumerate(st.session_state.watchlist):
        try:
            m = service.analyze(ticker)
            results.append(m)
        except Exception as e:
            st.warning(f"{ticker} 분석 실패: {e}")
        progress_bar.progress((i + 1) / len(st.session_state.watchlist))
    progress_bar.empty()

if results:
    render_scanner(results)
    st.markdown("---")
    render_chart_view(results)

st.markdown("---")
render_portfolio()

# ── 푸터 ──
st.markdown("""
<div style="text-align:center;color:#334155;font-size:10px;margin-top:40px;padding:16px 0;">
    투자 사령부 v2.0 · 투자 판단의 최종 책임은 본인에게 있습니다<br>
    Powered by yfinance & Streamlit
</div>
""", unsafe_allow_html=True)
```

if **name** == “**main**”:
main()
