"""Sektör veri atlası — TÜİK/TCMB verileriyle imalat sanayii panosu."""
from __future__ import annotations

import io
import re

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from data import (SEKTORLER, ay, ay_kisa, guncelleme_bilgisi, load, load_iso500, load_kredi, load_urunler, pazar_tablosu, load_nace34, load_tuik, num, pct, son_gecerli,
                  veri_surumu, yoy)

st.set_page_config(page_title="Sektör veri atlası", page_icon="📊", layout="wide",
                   initial_sidebar_state="collapsed")

# ---------------------------------------------------------------- tema
INK, NAVY, RED, TEAL, OCHRE = "#1d1d1b", "#1F3A5F", "#B5472A", "#2F6B73", "#B8822E"
MUTED, LINE, BG, CARD = "#6f6a60", "#d9d1c3", "#F4EFE6", "#EAE3D6"

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400&display=swap');
html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {{ background:{BG}; }}
[data-testid="stAppViewContainer"] *:not([data-testid="stIconMaterial"]):not([class*="material"]) {{ font-family: Inter, system-ui, sans-serif; }}
.block-container {{ max-width: 1120px; padding-top: 2.2rem; }}
h1,h2,h3,.serif {{ font-family: Fraunces, Georgia, serif !important; color:{INK}; font-weight:500; }}
.brand {{ font-family: Fraunces, serif; font-size: 1.45rem; color:{INK}; margin:0 0 .4rem 0; }}
.eyebrow {{ color:{NAVY}; letter-spacing:.18em; font-size:.74rem; text-transform:uppercase; font-weight:500; }}
.eyebrow:before {{ content:""; display:inline-block; width:22px; height:1.5px; background:{NAVY}; vertical-align:middle; margin-right:10px; }}
.hero {{ font-family:Fraunces, serif; color:{NAVY}; font-size:clamp(2.4rem,5vw,3.9rem); line-height:1; margin:.6rem 0 .3rem 0; font-weight:500; }}
.sub {{ color:{MUTED}; font-size:.86rem; }}
.big {{ font-family:Fraunces, serif; font-size:clamp(4rem,10vw,7.5rem); line-height:1; letter-spacing:-.02em; }}
.big .p {{ font-size:.38em; vertical-align:.95em; opacity:.6; margin-right:.05em; }}
.neg {{ color:{RED}; }} .pos {{ color:{TEAL}; }} .neu {{ color:{NAVY}; }}
.lead {{ font-family:Fraunces, serif; font-size:1.18rem; line-height:1.5; color:{INK}; }}
.kpi {{ border-top:1px solid {LINE}; padding:.85rem .2rem .6rem .2rem; height:100%; }}
.kpi.sel {{ background:#e6e9ec; border-top:3px solid {NAVY}; padding-left:.7rem; }}
.kpi .l {{ font-size:.78rem; color:{MUTED}; }}
.kpi .v {{ font-family:Fraunces, serif; font-size:1.9rem; margin:.25rem 0 .1rem 0; }}
.kpi .v .p {{ font-size:.55em; opacity:.6; }}
.kpi .n {{ font-size:.72rem; color:{MUTED}; }}
.secno {{ font-family:'JetBrains Mono', monospace; color:{RED}; font-size:.78rem; border-top:1px solid {INK}; padding-top:1rem; margin-top:2.5rem; }}
.sech {{ font-family:Fraunces, serif; font-size:2rem; color:{INK}; margin:.2rem 0 .3rem 0; }}
.secd {{ color:{MUTED}; font-size:.9rem; margin-bottom:1rem; max-width:760px; }}
.stat .l {{ font-size:.76rem; color:{MUTED}; }}
.stat .v {{ font-family:Fraunces, serif; font-size:1.7rem; }}
.stat .n {{ font-size:.72rem; color:{MUTED}; }}
.src {{ font-size:.74rem; color:#9a9387; margin-top:.2rem; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(200px,1fr)); gap:6px; }}
.tile {{ border-radius:3px; padding:.75rem .8rem; min-height:108px; }}
.tile .c {{ font-family:'JetBrains Mono',monospace; font-size:.72rem; opacity:.75; }}
.tile .t {{ font-size:.9rem; margin:.35rem 0 .3rem 0; }}
.tile .v {{ font-family:Fraunces, serif; font-size:1.6rem; }}
.tile.tot {{ outline:2px solid {INK}; outline-offset:-2px; }}
.legend {{ display:flex; align-items:center; gap:8px; font-size:.74rem; color:{MUTED}; justify-content:flex-end; white-space:nowrap; }}
.legend .bar {{ width:160px; height:6px; border-radius:3px; background:linear-gradient(90deg,{RED},#efe9df,{TEAL}); }}
.stTabs [data-baseweb="tab-list"] {{ gap:0; border:1px solid {LINE}; border-radius:4px; width:fit-content; }}
.stTabs [data-baseweb="tab"] {{ padding:.35rem 1rem; border-right:1px solid {LINE}; height:auto; }}
.stTabs [aria-selected="true"] {{ background:#dfe3e7; }}
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] {{ display:none; }}
[data-testid="stToolbar"] {{ display:none; }}
.brand,.hero,.big,.big *,.lead,.sech,.kpi .v,.kpi .v *,.stat .v,.stat .v *,.tile .v {{ font-family: Fraunces, Georgia, serif !important; }}
.secno,.tile .c {{ font-family: "JetBrains Mono", monospace !important; }}
[class*="st-key-kpi_"], [class*="st-key-tile_"] {{ position:relative; gap:0; }}
[class*="st-key-tileb_"], [class*="st-key-kpib_"] {{ position:absolute; inset:0; z-index:3; margin:0;
  width:100% !important; height:100% !important; }}
[class*="st-key-tileb_"] *, [class*="st-key-kpib_"] * {{ width:100% !important; height:100% !important; }}
[class*="st-key-tileb_"] > div, [class*="st-key-tileb_"] .stButton,
[class*="st-key-tileb_"] div[data-testid="stTooltipHoverTarget"] {{ width:100% !important; height:100% !important; }}
[class*="st-key-tileb_"] button {{ width:100% !important; height:100% !important; opacity:0; cursor:pointer; }}
[class*="st-key-tile_"]:hover .tile {{ filter:brightness(.96); }}
[class*="st-key-kpib_"] {{ position:absolute; inset:0; z-index:3; margin:0; }}
[class*="st-key-kpib_"] > div, [class*="st-key-kpib_"] .stButton, [class*="st-key-kpib_"] .stTooltipIcon,
[class*="st-key-kpib_"] div[data-testid="stTooltipHoverTarget"] {{ width:100% !important; height:100% !important; }}
[class*="st-key-kpib_"] button {{ width:100% !important; height:100% !important; opacity:0; cursor:pointer; }}
[class*="st-key-kpi_"]:hover .kpi {{ background:#ebe5d9; }}
.kpi {{ transition:background .15s; }}
div[data-testid="stSegmentedControl"] button {{ font-size:.8rem; }}
</style>
""", unsafe_allow_html=True)

_SURUM = veri_surumu()
V = load(_SURUM)
T = load_tuik(_SURUM)
TS = T.seriler
M, S, USD = V.makro, V.sektor, V.usd

# ---------------------------------------------------------------- yardımcılar

def cls(x: float) -> str:
    return "neg" if x < 0 else "pos"


def big_pct(x: float, color: str | None = None) -> str:
    c = color or ("neg" if x < 0 else "neu")
    sign = "−" if x < 0 else ""
    return f'<div class="big {c}">{sign}<span class="p">%</span>{num(abs(x))}</div>'


def kpi_val(x: float, unit: str = "%", sign: bool = False) -> str:
    s = "−" if x < 0 else ("+" if sign and x > 0 else "")
    return f'{s}<span class="p">{unit}</span>{num(abs(x))}' if unit else f"{s}{num(abs(x))}"


def sparkline(s: pd.Series, color: str, w: int = 150, h: int = 34) -> str:
    v = s.dropna().values[-48:]
    if len(v) < 2:
        return ""
    lo, hi = np.percentile(v, 2), np.percentile(v, 98)
    v = np.clip(v, lo, hi)
    xs = np.linspace(0, w, len(v))
    ys = h - (v - lo) / (hi - lo + 1e-9) * (h - 4) - 2
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))
    return (f'<svg width="100%" viewBox="0 0 {w} {h}" preserveAspectRatio="none" style="height:{h}px">'
            f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="1.4"/></svg>')


def mix(c1: str, c2: str, t: float) -> str:
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(a, b))


def div_color(x: float, lim: float = 15) -> str:
    t = max(-1.0, min(1.0, x / lim))
    return mix("#efe9df", RED, -t * .55) if t < 0 else mix("#efe9df", TEAL, t * .55)


def section(no: str, title: str, desc: str = "") -> None:
    st.markdown(f'<div class="secno">{no}</div><div class="sech">{title}</div>'
                + (f'<div class="secd">{desc}</div>' if desc else ""), unsafe_allow_html=True)


def stats(items: list[tuple[str, str, str]]) -> None:
    cols = st.columns(len(items))
    for c, (l, v, n) in zip(cols, items):
        c.markdown(f'<div class="stat"><div class="l">{l}</div><div class="v">{v}</div>'
                   f'<div class="n">{n}</div></div>', unsafe_allow_html=True)


def src(t: str) -> None:
    st.markdown(f'<div class="src">Kaynak: {t}</div>', unsafe_allow_html=True)


def base_fig(h: int = 340) -> go.Figure:
    f = go.Figure()
    f.update_layout(height=h, margin=dict(l=4, r=64, t=10, b=24), paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)", font=dict(family="Inter", size=11, color=MUTED),
                    showlegend=False, hovermode="x unified",
                    hoverlabel=dict(bgcolor="#fffdf8", bordercolor=LINE, font_color=INK))
    f.update_xaxes(showgrid=False, linecolor=LINE, ticks="", dtick="M12", tickformat="%Y")
    f.update_yaxes(gridcolor="#e4dccd", zeroline=True, zerolinecolor="#b9b0a0", side="right",
                   ticksuffix="", tickformat=",.0f")
    return f


def ts(s: pd.Series) -> pd.Series:
    s = s.dropna()
    return pd.Series(s.values, index=s.index.to_timestamp())


IMALAT_RENK = "#a0896b"  # karşılaştırma çizgisi (imalat sanayii toplamı)


def line_chart(series: list[tuple[str, pd.Series, str]], h: int = 340, pctaxis: bool = True,
               clip: bool = False, fill: bool = False) -> go.Figure:
    f = base_fig(h)
    allv = []
    for i, (name, s, color) in enumerate(series):
        s = ts(s)
        allv.extend(s.values)
        f.add_scatter(x=s.index, y=s.values, name=name, mode="lines",
                      line=dict(color=color, width=2 if i == 0 else 1.4,
                                dash="dot" if "ortalama" in name.lower()
                                else ("dash" if name.startswith("İmalat sanayii") else None)),
                      fill="tozeroy" if (fill and i == 0) else None,
                      fillcolor="rgba(31,58,95,.07)",
                      hovertemplate="%{y:.1f}<extra>" + name + "</extra>")
        if i == 0 and len(s):
            f.add_scatter(x=[s.index[-1]], y=[s.values[-1]], mode="markers+text",
                          marker=dict(size=7, color=color, line=dict(color=BG, width=2)),
                          text=[(pct(s.values[-1]) if pctaxis else num(s.values[-1]))],
                          textposition="middle right", textfont=dict(color=color, size=11),
                          hoverinfo="skip", showlegend=False)
    if clip and len(allv) > 24:
        lo, hi = np.nanpercentile(allv, 1.5), np.nanpercentile(allv, 98.5)
        pad = (hi - lo) * .12
        f.update_yaxes(range=[lo - pad, hi + pad])
        s0 = ts(series[0][1])
        mx, mn = s0.idxmax(), s0.idxmin()
        if s0[mx] > hi + pad:
            f.add_annotation(x=mx, y=hi + pad, text=f"▲ {pct(s0[mx])} · {ay(pd.Period(mx, 'M'))}",
                             showarrow=False, yanchor="bottom", font=dict(size=10, color=MUTED))
        if s0[mn] < lo - pad:
            f.add_annotation(x=mn, y=lo - pad, text=f"▼ {pct(s0[mn])} · {ay(pd.Period(mn, 'M'))}",
                             showarrow=False, yanchor="top", font=dict(size=10, color=MUTED))
    if pctaxis:
        f.update_yaxes(tickprefix="%")
    if len(series) > 1:
        f.update_layout(showlegend=True, margin=dict(t=34),
                        legend=dict(orientation="h", y=1.0, yanchor="bottom", x=0,
                                    font=dict(color=INK, size=11)))
    return f


CFG = {"displayModeBar": False}

KISA_NACE4 = {
    "C1310": "İplik", "C1320": "Dokuma kumaş", "C1330": "Tekstil terbiyesi", "C1391": "Örme kumaş",
    "C1392": "Ev tekstili", "C1393": "Halı ve kilim", "C1394": "Halat ve ip", "C1395": "Dokusuz kumaşlar",
    "C1396": "Teknik tekstiller", "C1399": "Diğer tekstiller",
    "C1411": "Deri giyim", "C1412": "İş kıyafeti", "C1413": "Dış giyim", "C1414": "İç giyim",
    "C1419": "Diğer giyim", "C1431": "Çorap", "C1439": "Örme giyim",
    "C1011": "Kırmızı et", "C1012": "Kümes hayvanı eti", "C1013": "Et ürünleri", "C1020": "Su ürünleri",
    "C1031": "Patates işleme", "C1032": "Meyve ve sebze suyu", "C1039": "Meyve ve sebze işleme",
    "C1041": "Sıvı ve katı yağlar", "C1051": "Süt ürünleri", "C1052": "Dondurma", "C1061": "Değirmencilik",
    "C1062": "Nişasta", "C1071": "Ekmek ve taze pastane", "C1072": "Bisküvi ve kuru pastane",
    "C1073": "Makarna", "C1081": "Şeker", "C1082": "Çikolata ve şekerleme", "C1083": "Çay ve kahve",
    "C1084": "Baharat ve sos", "C1085": "Hazır yemek", "C1086": "Bebek ve diyet gıdaları",
    "C1089": "Diğer gıda", "C1091": "Çiftlik hayvanı yemi", "C1092": "Evcil hayvan yemi",
    "C1101": "Damıtılmış alkollü içkiler", "C1102": "Şarap", "C1105": "Bira", "C1107": "Alkolsüz içecekler",
    "C1511": "Deri tabaklama", "C1512": "Bavul ve çanta", "C1520": "Ayakkabı",
    "C2211": "Lastik", "C2219": "Diğer kauçuk ürünleri", "C2221": "Plastik levha ve boru",
    "C2222": "Plastik ambalaj", "C2223": "Plastik inşaat malzemesi", "C2229": "Diğer plastik ürünler",
    "C2311": "Düz cam", "C2313": "Cam ambalaj ve ev eşyası", "C2331": "Seramik karo", "C2342": "Seramik sağlık gereçleri",
    "C2351": "Çimento", "C2361": "Beton ürünleri", "C2363": "Hazır beton", "C2370": "Mermer ve taş",
    "C2410": "Demir çelik", "C2420": "Çelik boru", "C2442": "Alüminyum", "C2444": "Bakır",
    "C2451": "Demir döküm", "C2453": "Hafif metal döküm",
    "C2511": "Metal yapı", "C2512": "Metal kapı ve pencere", "C2521": "Kalorifer radyatörü ve kazanı",
    "C2550": "Metal dövme ve presleme", "C2562": "Metal işleme", "C2572": "Kilit ve menteşe",
    "C2573": "El aletleri", "C2592": "Hafif metal ambalaj", "C2599": "Diğer metal ürünler",
    "C2711": "Motor, jeneratör, trafo", "C2712": "Elektrik dağıtım ve kontrol cihazı", "C2720": "Akü ve pil",
    "C2732": "Elektrik kablosu", "C2740": "Aydınlatma", "C2751": "Beyaz eşya", "C2752": "Elektriksiz ev aletleri",
    "C2790": "Diğer elektrikli teçhizat", "C2811": "Motor ve türbin", "C2813": "Pompa ve kompresör",
    "C2814": "Musluk ve vana", "C2815": "Rulman ve dişli", "C2822": "Kaldırma ve taşıma ekipmanı",
    "C2825": "Soğutma ve havalandırma", "C2829": "Diğer genel amaçlı makine", "C2830": "Tarım makineleri",
    "C2841": "Metal işleme makineleri", "C2892": "Madencilik ve inşaat makineleri", "C2893": "Gıda makineleri",
    "C2894": "Tekstil makineleri", "C2910": "Motorlu kara taşıtları", "C2920": "Karoser ve treyler",
    "C2932": "Taşıt yan sanayi", "C2931": "Taşıt elektrik ekipmanı", "C3011": "Gemi inşası",
    "C3020": "Raylı taşıtlar", "C3030": "Hava ve uzay araçları", "C3040": "Askeri savaş araçları",
    "C3091": "Motosiklet", "C3092": "Bisiklet", "C3101": "Büro mobilyası", "C3102": "Mutfak mobilyası",
    "C3103": "Yatak", "C3109": "Diğer mobilya",
}
from data import AYLAR_KISA as AYLAR_KISA_
from data import AYLAR as AYLAR_
ADLAR = {**SEKTORLER, "C18": ("Kayıtlı medyanın basılması ve çoğaltılması", "Basım")}


def kisalt(t: str, n: int = 110) -> str:
    t = str(t)
    return t if len(t) <= n else t[:n - 1] + "…"




def hbar(vals: pd.Series, renk_pos: str, renk_neg: str, secili: str | None = None,
         hover: str = "Yıllık") -> go.Figure:
    srt = vals.dropna().sort_values()
    renk = [(renk_pos if v > 0 else renk_neg) for v in srt.values]
    if secili and secili != "C":
        renk = [c if k == secili else c + "66" for k, c in zip(srt.index, renk)]
    fb = go.Figure(go.Bar(
        x=srt.values, y=[ADLAR.get(k, (k, k))[1] for k in srt.index], orientation="h", marker_color=renk,
        text=[pct(v, sign=True) for v in srt.values], textposition="outside",
        textfont=dict(size=10, color=INK), cliponaxis=False,
        customdata=[ADLAR.get(k, (k, k))[0] for k in srt.index],
        hovertemplate="<b>%{customdata}</b><br>" + hover + ": %{x:.1f}<extra></extra>"))
    fb.update_layout(height=max(380, 26 * len(srt)), margin=dict(l=4, r=56, t=6, b=6),
                     paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                     font=dict(family="Inter", size=11, color=INK), bargap=.38,
                     hoverlabel=dict(bgcolor="#fffdf8"))
    lo, hi = min(srt.min(), 0), max(srt.max(), 0)
    pad = (hi - lo) * .22
    fb.update_xaxes(visible=False, range=[lo - (pad if lo < 0 else 0), hi + pad])
    fb.update_yaxes(showgrid=False, ticks="")
    return fb

# ---------------------------------------------------------------- türetilmiş seriler
sue = M["sue_imalat"]
sue_y = yoy(sue)
p_sue, v_sue = son_gecerli(sue_y)
yiufe_y, tufe_y, ydufe_y = yoy(M["yiufe_imalat"]), yoy(M["tufe"]), yoy(M["ydufe_imalat"])
kko = M["kko"]
rek = M["rek"]
usd_y = yoy(USD)
sek_y = S.apply(yoy)
son_sek = sek_y.dropna(how="all").iloc[-1].dropna()
son_sek_p = sek_y.dropna(how="all").index[-1]

# ---------------------------------------------------------------- kenar çubuğu
with st.sidebar:
    import os, subprocess, sys
    import tuik as _tuik
    st.markdown("#### Veri")
    gb = guncelleme_bilgisi()
    st.caption(f"En güncel üretim verisi: **{ay(p_sue)}**")
    st.caption(f"EVDS son güncelleme: **{gb.get('evds', '—').replace('T', ' ')}**")
    st.caption(f"TÜİK son güncelleme: **{gb.get('tuik', '—').replace('T', ' ')}**")
    evds_var, tuik_var = bool(os.environ.get("EVDS_API_KEY")), bool(_tuik.api_key())
    st.caption(f"EVDS anahtarı: {'✓' if evds_var else '✗'} · TÜİK anahtarı: {'✓' if tuik_var else '✗'}")
    if evds_var or tuik_var:
        if st.button("Verileri şimdi güncelle", help="EVDS ve TÜİK'ten çeker (3–5 dk sürebilir)"):
            with st.spinner("EVDS ve TÜİK'ten veriler çekiliyor…"):
                r = subprocess.run([sys.executable, "scripts/guncelle.py"], capture_output=True, text=True,
                                   cwd=os.path.dirname(os.path.abspath(__file__)), timeout=900)
            if r.returncode == 0:
                st.cache_data.clear()
                st.rerun()
            else:
                st.error("Güncelleme başarısız.")
                st.code(r.stdout[-1500:] + r.stderr[-1500:])
    else:
        st.info("Verileri yenilemek için `EVDS_API_KEY` ve `TUIK_API_KEY` tanımlayın.", icon="ℹ️")
    for k, v in gb.get("tuik_hatalar", {}).items():
        st.caption(f"TÜİK {k}: {v[:140]}")

# ---------------------------------------------------------------- başlık
st.markdown('<div class="brand">Sektör veri atlası</div>', unsafe_allow_html=True)
tab_atlas, tab_uretim, tab_ist, tab_tcmb, tab_haber, tab_urun, tab_nace, tab_firma, tab_kod, tab_veri = st.tabs(
    ["Atlas", "Üretim ve fiyat", "İstihdam ve ciro", "TCMB", "Haber", "Ürünler", "NACE 4'lü", "Firmalar", "Kod analizi", "Veri"])

# ================================================================ ATLAS
p_kko, v_kko = son_gecerli(kko)
p_uf, v_uf = son_gecerli(yiufe_y)
p_yd, v_yd = son_gecerli(ydufe_y)
p_rk, v_rk = son_gecerli(rek)
p_us, v_us = son_gecerli(USD)


def _sektor(df: pd.DataFrame | None, fn) -> pd.DataFrame:
    if df is None:
        return pd.DataFrame()
    d = df.drop(columns="C", errors="ignore")
    d = d[[c for c in d.columns if c in ADLAR]]
    return d.apply(fn)


def _yoy12(s: pd.Series) -> pd.Series:
    return yoy(s.rolling(12).sum())


# Atlas göstergeleri: kart, büyük grafik ve sektör haritası aynı tanımdan beslenir.
# merkez=None -> renk ölçeği 0 etrafında (artış/düşüş); "imalat" -> imalat toplamına göre (üstünde/altında)
ATLAS = {
    "uretim": dict(kart="Üretim, yıllık", baslik="Sanayi üretim endeksi, yıllık değişim",
                   seri=sue_y, sektor=_sektor(S, yoy), seviye=False, lim=15, merkez=None,
                   kaynak="TÜİK, sanayi üretim endeksi (takvim etkisinden arındırılmış, 2021=100) · TCMB EVDS üzerinden"),
}
if "ciro" in TS:
    ATLAS["ciro"] = dict(kart="Ciro, yıllık", baslik="Ciro endeksi, yıllık değişim (nominal)",
                         seri=yoy(TS["ciro"]["C"]), sektor=_sektor(TS["ciro"], yoy), seviye=False, lim=20,
                         merkez="imalat",
                         kaynak="TÜİK SDMX, ciro endeksi · takvim etkisinden arındırılmış, 2021=100 · "
                                "renk: imalat toplamına göre")
ATLAS["kapasite"] = dict(kart="Kapasite kullanımı", baslik="Kapasite kullanım oranı",
                         seri=kko, sektor=TS["kko"].copy() if "kko" in TS else pd.DataFrame(), seviye=True,
                         lim=10, merkez="imalat",
                         kaynak="TCMB EVDS, imalat sanayi kapasite kullanım oranı · renk: imalat ortalamasına göre")
if "ihracat" in TS:
    ATLAS["ihracat"] = dict(kart="İhracat ($), 12 ay", baslik="İhracat ($), son 12 ay, bir önceki 12 aya göre",
                            seri=_yoy12(TS["ihracat"]["C"]), sektor=_sektor(TS["ihracat"], _yoy12), seviye=False,
                            lim=15, merkez=None, tutar=TS["ihracat"].rolling(12).sum(),
                            kaynak="TÜİK, ISIC Rev.4'e göre dış ticaret · TCMB EVDS üzerinden · 12 aylık toplam")
if "ithalat" in TS:
    ATLAS["ithalat"] = dict(kart="İthalat ($), 12 ay", baslik="İthalat ($), son 12 ay, bir önceki 12 aya göre",
                            seri=_yoy12(TS["ithalat"]["C"]), sektor=_sektor(TS["ithalat"], _yoy12), seviye=False,
                            lim=15, merkez=None, tutar=TS["ithalat"].rolling(12).sum(),
                            kaynak="TÜİK, ISIC Rev.4'e göre dış ticaret · TCMB EVDS üzerinden · 12 aylık toplam")
if "ucretli_calisan" in TS:
    ATLAS["calisan"] = dict(kart="Ücretli çalışan", baslik="Ücretli çalışan sayısı, yıllık değişim",
                            seri=yoy(TS["ucretli_calisan"]["C"]), sektor=_sektor(TS["ucretli_calisan"], yoy),
                            seviye=False, lim=8, merkez=None,
                            kaynak="TÜİK SDMX, ücretli çalışan istatistikleri · takvim etkisinden arındırılmış")
ATLAS["ufe"] = dict(kart="Yİ-ÜFE, yıllık", baslik="Yurt içi üretici fiyatları, yıllık değişim",
                    seri=yiufe_y, sektor=_sektor(TS.get("yiufe"), yoy), seviye=False, lim=15, merkez="imalat",
                    kaynak="TÜİK, Yİ-ÜFE (2003=100) · renk: imalat toplamına göre")


def _atlas_sec(k: str) -> None:
    st.session_state["atlas_sec"] = k


def _atlas_sektor(kod: str) -> None:
    st.session_state["atlas_sektor"] = kod


def atlas_seri(k: str, kod: str) -> pd.Series | None:
    """Gösterge k'nın seçili sektördeki (kod) serisi; C = imalat toplamı."""
    g = ATLAS[k]
    if kod == "C":
        return g["seri"]
    s_ = g["sektor"].get(kod) if not g["sektor"].empty else None
    return s_ if s_ is not None and s_.notna().any() else None


def atlas_tutar(k: str, kod: str, donem=None) -> float | None:
    """Dış ticaret kartları için son 12 ay toplamı (bin $); yoksa None."""
    t = ATLAS[k].get("tutar")
    if t is None or kod not in t:
        return None
    s_ = t[kod].dropna()
    if s_.empty:
        return None
    return float(s_.get(donem, np.nan)) if donem is not None else float(s_.iloc[-1])


def mn_usd(bin_usd: float) -> str:
    return f"{num(bin_usd / 1000, 0)} mn $"


with tab_atlas:
    sek_kod = st.session_state.get("atlas_sektor", "C")
    mevcut = {k: atlas_seri(k, sek_kod) for k in ATLAS}
    mevcut = {k: v for k, v in mevcut.items() if v is not None}
    if not mevcut:  # bu sektörde hiç veri yoksa toplama dön
        sek_kod, mevcut = "C", {k: ATLAS[k]["seri"] for k in ATLAS}
    secili = st.session_state.get("atlas_sec", "uretim")
    if secili not in mevcut:
        secili = next(iter(mevcut))
    A = ATLAS[secili]
    A_seri = mevcut[secili]
    a_p, a_v = son_gecerli(A_seri)
    a_once = A_seri.get(a_p - 12, np.nan)
    a_fark = a_v - a_once
    if sek_kod == "C":
        s_ad, s_alt = "İmalat sanayii", "Bölüm C · imalat, toplam"
    else:
        s_ad = ADLAR[sek_kod][0]
        s_alt = f"NACE {sek_kod} · {ADLAR[sek_kod][1]}"

    l, r = st.columns([1, 1.15], gap="large")
    with l:
        if A["seviye"]:
            buyuk = f'<div class="big neu"><span class="p">%</span>{num(a_v)}</div>'
        else:
            buyuk = big_pct(a_v, "neg" if a_v < 0 else "pos")
        boy = "" if len(s_ad) < 22 else ' style="font-size:clamp(1.8rem,3.4vw,2.6rem)"'
        st.markdown(f'<div class="eyebrow">Aylık sanayi göstergeleri</div>'
                    f'<div class="hero"{boy}>{s_ad}</div>'
                    f'<div class="sub">{s_alt}</div>'
                    f'<p style="margin:1.4rem 0 .2rem 0;font-weight:600;font-size:.92rem">{A["baslik"]}</p>' + buyuk,
                    unsafe_allow_html=True)
        once_txt = pct(a_once) if not np.isnan(a_once) else "—"
        fark_txt = "" if np.isnan(a_fark) else \
            f' · <b class="{cls(a_fark)}">{num(a_fark, 1) if a_fark < 0 else "+" + num(a_fark)} puan</b>'
        st.markdown(f'<div class="sub" style="margin-top:.8rem">{ay(a_p)} · bir yıl önce '
                    f'<b style="color:{INK}">{once_txt}</b>{fark_txt}</div>', unsafe_allow_html=True)
        a_tut = atlas_tutar(secili, sek_kod, a_p)
        if a_tut is not None and not np.isnan(a_tut):
            a_tut0 = atlas_tutar(secili, sek_kod, a_p - 12)
            onceki = f" · bir yıl önce {mn_usd(a_tut0)}" if a_tut0 is not None and not np.isnan(a_tut0) else ""
            st.markdown(f'<div style="margin-top:.5rem;font-size:.95rem">Son 12 ay toplamı '
                        f'<b style="font-family:Fraunces,serif;font-size:1.25rem;color:{NAVY}">{mn_usd(a_tut)}</b>'
                        f'<span class="sub" style="white-space:nowrap">{onceki}</span></div>', unsafe_allow_html=True)
        if sek_kod != "C":
            st.button("← İmalat sanayii (toplam)", key="atlas_geri", on_click=_atlas_sektor, args=("C",))
    with r:
        st.markdown(f'<div class="sub" style="text-align:right">● Veri {ay(a_p)} · TÜİK, TCMB</div>',
                    unsafe_allow_html=True)
        f = line_chart([(A["kart"], A_seri["2021-07":], NAVY)], h=320, fill=not A["seviye"])
        if A["seviye"]:
            f.update_yaxes(tickformat=".0f")
        st.plotly_chart(f, width="stretch", config=CFG, key=f"atlas_grafik_{secili}_{sek_kod}")

    # KPI şeridi: her kart tıklanabilir; seçili sektörün serileri
    cols = st.columns(len(mevcut), gap="small")
    for c, (k, ser) in zip(cols, mevcut.items()):
        g = ATLAS[k]
        p_k, last = son_gecerli(ser)
        color = TEAL if (g["seviye"] or last >= 0) else RED
        vcls = "neg" if color == RED else "pos"
        k_tut = atlas_tutar(k, sek_kod, p_k)
        not_ = f"<b>{mn_usd(k_tut)}</b><br>{ay(p_k)}" if k_tut is not None and not np.isnan(k_tut) else ay(p_k)
        with c.container(key=f"kpi_{k}"):
            st.markdown(f'<div class="kpi{" sel" if k == secili else ""}"><div class="l">{g["kart"]}</div>'
                        f'<div class="v {vcls}">{kpi_val(last)}</div>{sparkline(ser, color)}'
                        f'<div class="n">{not_}</div></div>', unsafe_allow_html=True)
            st.button(g["kart"], key=f"kpib_{k}", on_click=_atlas_sec, args=(k,))

    # Sektör haritası: seçili göstergeye göre; karoya tıklanınca Atlas o sektöre geçer
    section("01", "Sektör haritası")
    sek = A["sektor"].dropna(how="all")
    if sek.empty:
        st.caption("Bu gösterge için sektör kırılımı yok.")
    else:
        sp = sek.index[-1]
        son = sek.loc[sp].dropna()
        toplam = A["seri"].get(sp, ATLAS[secili]["seri"].dropna().iloc[-1])
        merkez = toplam if A["merkez"] == "imalat" else 0.0
        aa, bb = st.columns([2, 1])
        aa.markdown(f'<div class="secd">{A["baslik"]} · {ay(sp)} · ayrıntı için bir sektöre tıklayın</div>',
                    unsafe_allow_html=True)
        if A["merkez"] == "imalat":
            bb.markdown('<div class="legend">imalatın altında <div class="bar"></div> üstünde</div>',
                        unsafe_allow_html=True)
        else:
            bb.markdown('<div class="legend">düşüş <div class="bar"></div> artış</div>', unsafe_allow_html=True)
        fmt = (lambda v: pct(v)) if A["seviye"] else (lambda v: pct(v, sign=True))
        karolar = [("C", "C · toplam", "İmalat sanayii", toplam)] + [
            (code, code, ADLAR[code][1], val)
            for code, val in son.sort_index(key=lambda i: i.str[1:].astype(int)).items()]
        for i in range(0, len(karolar), 4):
            satir = st.columns(4, gap="small")
            for c, (code, etiket, ad_, val) in zip(satir, karolar[i:i + 4]):
                secik = " tot" if code == sek_kod else ""
                t_tut = atlas_tutar(secili, code, sp)
                t_ek = (f'<div class="n" style="font-size:.74rem;opacity:.75">{mn_usd(t_tut)}</div>'
                        if t_tut is not None and not np.isnan(t_tut) else "")
                with c.container(key=f"tile_{code}"):
                    st.markdown(f'<div class="tile{secik}" style="background:{div_color(val - merkez, A["lim"])}">'
                                f'<div class="c">{etiket}</div><div class="t">{ad_}</div>'
                                f'<div class="v">{fmt(val)}</div>{t_ek}</div>', unsafe_allow_html=True)
                    st.button(ad_, key=f"tileb_{code}", on_click=_atlas_sektor, args=(code,))
        src(A["kaynak"])

# ================================================================ ÜRETİM VE FİYAT
with tab_uretim:
    secenek = ["C · İmalat sanayii (toplam)"] + [f"{k} · {v[0]}" for k, v in SEKTORLER.items()]
    c1, c2 = st.columns([3, 1])
    secim = c1.selectbox("Sektör", secenek, index=0)
    kod = secim.split(" · ")[0]
    ad = "İmalat sanayii" if kod == "C" else SEKTORLER[kod][0]
    endeks = sue if kod == "C" else S[kod]
    ey = yoy(endeks)
    pe, ve = son_gecerli(ey)

    hl, hr = st.columns([1, 1.6], gap="large")
    with hl:
        _bas = ad if len(ad) < 28 else SEKTORLER[kod][1]
        _boy = "" if len(_bas) < 16 else ' style="font-size:clamp(2rem,3.6vw,2.8rem)"'
        st.markdown(f'<div class="eyebrow">Üretim ve fiyat</div><div class="hero"{_boy}>{_bas}</div>'
                    f'<p style="margin:1rem 0 .2rem 0;font-weight:600;font-size:.88rem">Sanayi üretimi, yıllık değişim · {ay(pe)}</p>'
                    + big_pct(ve, "neg" if ve < 0 else "pos"), unsafe_allow_html=True)
        if kod != "C":
            v_im = sue_y.get(pe, np.nan)
            st.markdown(f'<div class="sub" style="margin-top:.6rem">Karşılaştırma: imalat sanayii '
                        f'<b class="{cls(v_im)}">{pct(v_im, sign=True)}</b> · fark '
                        f'<b class="{cls(ve - v_im)}" style="white-space:nowrap">{num(ve - v_im) if ve - v_im < 0 else "+" + num(ve - v_im)} puan</b></div>',
                        unsafe_allow_html=True)
    with hr:
        yon = "geriliyor" if ve < 0 else "artıyor"
        fiy = ("altında" if v_uf < son_gecerli(tufe_y)[1] else "üzerinde")
        ihr = "hızlı" if v_yd > v_uf else "yavaş"
        st.markdown(f'<p class="lead" style="margin-top:2.6rem">Üretim bir yıl önceye göre {yon}. '
                    f'İmalat üretici fiyatları tüketici enflasyonunun (TÜFE {pct(son_gecerli(tufe_y)[1])}) '
                    f'{fiy} artıyor; yurt dışı satış fiyatları yurt içinden {ihr} yükseliyor.</p>',
                    unsafe_allow_html=True)
    stats([("Yİ-ÜFE imalat, yıllık", pct(v_uf), f"{ay(p_uf)} · yurt içi üretici fiyatı"),
           ("YD-ÜFE imalat, yıllık", pct(v_yd), f"{ay(p_yd)} · yurt dışı satış fiyatı (TL)"),
           ("TÜFE, yıllık", pct(son_gecerli(tufe_y)[1]), ay(son_gecerli(tufe_y)[0])),
           ("Kapasite kullanımı", pct(v_kko), ay(p_kko))])

    # 01 üretim
    yonfiil = "azaldı" if ve < 0 else "arttı"
    section("01", "Sanayi üretim endeksi",
            f"{ay(pe)} itibarıyla {ad.lower() if kod == 'C' else ad}nda üretim geçen yılın aynı ayına göre "
            f"{pct(abs(ve))} {yonfiil}." if kod == "C" else
            f"{ay(pe)} itibarıyla {ad.lower()} sektöründe üretim geçen yılın aynı ayına göre {pct(abs(ve))} {yonfiil}.")
    gor = st.segmented_control("Görünüm", ["Yıllık %", "12 ay ortalama, yıllık %", "Endeks"],
                               default="Yıllık %", label_visibility="collapsed", key="g1")
    ort12 = ey.rolling(12).mean()
    son3 = ey.dropna().iloc[-3:].mean() - ey.dropna().iloc[-6:-3].mean()
    st_items = [("Bir yıl önce", pct(ey.get(pe - 12, np.nan)), ay(pe - 12)),
                ("Son 12 ay ortalaması", pct(ort12.dropna().iloc[-1]) if ort12.notna().any() else "—", ""),
                ("Son 3 ay, önceki 3 aya göre", f'<span class="{cls(son3)}">{num(son3) if son3 < 0 else "+" + num(son3)} puan</span>', "ortalamalar")]
    karsi = kod != "C"
    if karsi:
        st_items.append(("İmalat sanayii", pct(sue_y.get(pe, np.nan), sign=True),
                         f"{ay(pe)} · 12 ay ort. {pct(sue_y.rolling(12).mean().get(pe, np.nan))}"))
    stats(st_items)
    if gor == "Endeks":
        f = line_chart([(f"{SEKTORLER[kod][1] if karsi else 'Endeks'} (2021=100)", endeks, NAVY)]
                       + ([("İmalat sanayii (2021=100)", sue, IMALAT_RENK)] if karsi else []), pctaxis=False)
    elif gor == "12 ay ortalama, yıllık %":
        f = line_chart([("12 ay ortalama, yıllık %", ort12, NAVY)]
                       + ([("İmalat sanayii, 12 ay ort.", sue_y.rolling(12).mean(), IMALAT_RENK)] if karsi else []))
    else:
        f = line_chart([("Yıllık %", ey, NAVY), ("12 ay ortalama", ort12, "#8a95a5")]
                       + ([("İmalat sanayii, yıllık %", sue_y, IMALAT_RENK)] if karsi else []))
    st.plotly_chart(f, width="stretch", config=CFG)
    src("TÜİK, sanayi üretim endeksi · takvim etkisinden arındırılmış"
        + (" · kesikli çizgi: imalat sanayii toplamı" if karsi else ""))
    with st.expander("Veri tablosu"):
        st.dataframe(pd.DataFrame({"Endeks": endeks, "Yıllık %": ey.round(1), "12 ay ort. %": ort12.round(1)})
                     .dropna(how="all").iloc[::-1].rename(index=str), width="stretch")

    if kod == "C":
        # 02 sektörler
        n_art = int((son_sek > 0).sum())
        en_y, en_d = son_sek.idxmax(), son_sek.idxmin()
        section("02", "Sektörler",
                f"{ay(son_sek_p)} itibarıyla {len(son_sek)} sektörden {n_art} tanesinde üretim bir yıl öncesine göre arttı. "
                f"En güçlü artış {SEKTORLER[en_y][0]} ({pct(son_sek[en_y], sign=True)}), en sert düşüş "
                f"{SEKTORLER[en_d][0]} ({pct(son_sek[en_d])}) sektöründe.")
        bl, br = st.columns(2, gap="large")
        with bl:
            st.markdown(f'<div class="eyebrow" style="margin:.4rem 0">Üretim, yıllık değişim · {ay(son_sek_p)}</div>',
                        unsafe_allow_html=True)
            st.plotly_chart(hbar(son_sek, TEAL, RED, kod), width="stretch", config=CFG)
        with br:
            if "yiufe" in TS:
                uf = TS["yiufe"].drop(columns="C", errors="ignore").apply(yoy)
                uf_p = uf.dropna(how="all").index[-1]
                st.markdown(f'<div class="eyebrow" style="margin:.4rem 0">Üretici fiyatları, yıllık · {ay(uf_p)}</div>',
                            unsafe_allow_html=True)
                st.plotly_chart(hbar(uf.loc[uf_p], OCHRE, TEAL, kod, "Yİ-ÜFE yıllık"), width="stretch", config=CFG)
            else:
                st.caption("Sektörel üretici fiyatları için TÜİK verisi yok (`scripts/guncelle.py --tuik`).")

        # ısı haritası
        st.markdown('<p style="font-weight:600;margin-top:1rem">Üretimin yıllık değişimi, son 24 ay</p>',
                    unsafe_allow_html=True)
        hm = sek_y.dropna(how="all").iloc[-24:]
        order = son_sek.sort_values(ascending=False).index
        z = hm[order].T.values
        fh = go.Figure(go.Heatmap(
            z=np.clip(z, -30, 30), x=[ay_kisa(p) for p in hm.index], y=[SEKTORLER[k][1] for k in order],
            customdata=z, colorscale=[[0, RED], [.5, "#efe9df"], [1, TEAL]], zmid=0, zmin=-30, zmax=30,
            xgap=2, ygap=2, hovertemplate="%{y} · %{x}<br>%{customdata:.1f}%<extra></extra>",
            colorbar=dict(thickness=8, len=.8, ticksuffix="%", outlinewidth=0)))
        fh.update_layout(height=640, margin=dict(l=4, r=4, t=6, b=6), paper_bgcolor="rgba(0,0,0,0)",
                         plot_bgcolor="rgba(0,0,0,0)", font=dict(family="Inter", size=10.5, color=INK))
        fh.update_yaxes(autorange="reversed", ticks="")
        fh.update_xaxes(ticks="", tickangle=0, nticks=8)
        st.plotly_chart(fh, width="stretch", config=CFG)
        src("TÜİK, sanayi üretim endeksi · renk ölçeği ±%30'da kesildi")
    else:
        # 02 alt sektörler (NACE 4'lü): üretim, üretici fiyatları, son 24 ay
        N4_, NADI4 = load_nace34(_SURUM)
        alt = [c for c in N4_.columns if len(c) == 5 and c.startswith(kod)] if not N4_.empty else []
        if not alt:
            section("02", "Alt sektörler", "Bu sektör için alt sektör (NACE 4'lü) üretim verisi yok.")
        else:
            def kisa_ad(c: str) -> str:
                if c in KISA_NACE4:
                    return KISA_NACE4[c]
                a_ = NADI4.get(c, c)
                a_ = re.split(r" \(|, |; | ile | hariç", a_)[0]
                a_ = a_.replace("Başka yerde sınıflandırılmamış ", "Diğer ").replace("diğer diğer", "diğer")
                for ek in (" imalatı", " üretimi", "nin", "nın", "lerin", "ların"):
                    if a_.endswith(ek):
                        a_ = a_[: -len(ek)]
                a_ = a_.strip()
                return kisalt(a_[0].upper() + a_[1:], 40)

            a_y = N4_[alt].apply(yoy)
            a_p = a_y.dropna(how="all").index[-1]
            a_son = a_y.loc[a_p].dropna()
            a_12 = a_y.rolling(12).mean().loc[a_p]
            # satış payları: sanayi ürün istatistikleri, son yıl
            U_ = load_urunler(_SURUM)
            pay = pd.Series(dtype=float)
            if U_ is not None:
                sy_ = [c for c in U_.deger.columns if U_.deger[c].notna().any()][-1]
                bi_ = U_.bilgi[U_.bilgi["nace"] == kod]
                sat = U_.deger.loc[bi_.index, sy_].groupby(bi_["nace4"]).sum()
                pay = sat / sat.sum() * 100 if sat.sum() > 0 else pay
            # üretici fiyatları (4'lü)
            uf34 = TS.get("yiufe34")
            yd34 = TS.get("ydufe34")
            uf_son = pd.Series(dtype=float)
            if uf34 is not None:
                uf_k = uf34[[c for c in uf34.columns if c in alt]].apply(yoy)
                if not uf_k.dropna(how="all").empty:
                    uf_p4 = uf_k.dropna(how="all").index[-1]
                    uf_son = uf_k.loc[uf_p4].dropna()
            yd_son = pd.Series(dtype=float)
            if yd34 is not None:
                yd_k = yd34[[c for c in yd34.columns if c in alt]].apply(yoy)
                if not yd_k.dropna(how="all").empty:
                    yd_son = yd_k.loc[yd_k.dropna(how="all").index[-1]].dropna()

            n_art = int((a_son > 0).sum())
            ac = (f"{ay(a_p)} itibarıyla {len(a_son)} alt sektörden {n_art} tanesinde üretim bir yıl öncesine göre arttı. "
                  f"En güçlü artış {kisa_ad(a_son.idxmax())} ({pct(a_son.max(), sign=True)}), en sert düşüş "
                  f"{kisa_ad(a_son.idxmin())} ({pct(a_son.min(), sign=True)}) alt sektöründe.")
            pay_v = pay.reindex(a_son.index).dropna()
            if len(pay_v):
                eb = pay_v.idxmax()
                ac += (f" Satışların %{num(pay_v.max(), 0)} kadarını oluşturan en büyük alt sektör {kisa_ad(eb)}; "
                       f"burada üretim {pct(a_son[eb], sign=True)}, son on iki ayın ortalaması "
                       f"{pct(a_12.get(eb, np.nan), sign=True)}.")
            if len(uf_son):
                ac += (f" Üretici fiyatlarında en hızlı artış {kisa_ad(uf_son.idxmax())} ({pct(uf_son.max())}), "
                       f"en yavaş {kisa_ad(uf_son.idxmin())} ({pct(uf_son.min())}).")
            section("02", "Alt sektörler", ac)

            def alt_bar(vals: pd.Series, alt_satir: dict, renk_pos: str, renk_neg: str, imza: bool) -> go.Figure:
                srt = vals.sort_values()
                etiket = [f"{kisa_ad(c)}<br><span style='font-size:10px;color:{MUTED}'>{alt_satir.get(c, '')}</span>"
                          for c in srt.index]
                fb_ = go.Figure(go.Bar(
                    x=srt.values, y=etiket, orientation="h",
                    marker_color=[renk_pos if v >= 0 else renk_neg for v in srt.values],
                    text=[pct(v, sign=imza) for v in srt.values], textposition="outside",
                    textfont=dict(size=11, color=INK), cliponaxis=False,
                    customdata=[NADI4.get(c, c) for c in srt.index],
                    hovertemplate="<b>%{customdata}</b><br>%{x:.1f}%<extra></extra>"))
                lo_, hi_ = min(srt.min(), 0), max(srt.max(), 0)
                pad_ = (hi_ - lo_) * .3 or 1
                fb_.update_layout(height=max(260, 62 * len(srt)), margin=dict(l=4, r=56, t=6, b=6),
                                  paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                                  font=dict(family="Inter", size=12, color=INK), bargap=.55,
                                  hoverlabel=dict(bgcolor="#fffdf8"))
                fb_.update_xaxes(visible=False, range=[lo_ - (pad_ * 1.6 if lo_ < 0 else pad_ * .15), hi_ + pad_])
                fb_.update_yaxes(showgrid=False, ticks="")
                return fb_

            bl, br = st.columns(2, gap="large")
            with bl:
                st.markdown(f'<div class="eyebrow" style="margin:.4rem 0">Üretim, yıllık değişim · {ay(a_p)}</div>',
                            unsafe_allow_html=True)
                alt_s = {c: (f"satışların %{num(pay.get(c), 0)} · " if c in pay.index else "")
                         + f"12 ay ort. {pct(a_12.get(c, np.nan), sign=True)}" for c in a_son.index}
                st.plotly_chart(alt_bar(a_son, alt_s, TEAL, RED, True), width="stretch", config=CFG)
            with br:
                if len(uf_son):
                    st.markdown(f'<div class="eyebrow" style="margin:.4rem 0">Üretici fiyatları, yıllık · '
                                f'{ay(uf_p4)}</div>', unsafe_allow_html=True)
                    alt_f = {c: f"yurt dışı satış fiyatı {pct(yd_son[c])}" for c in uf_son.index if c in yd_son.index}
                    st.plotly_chart(alt_bar(uf_son, alt_f, OCHRE, TEAL, False), width="stretch", config=CFG)
                else:
                    st.caption("Bu alt sektörler için üretici fiyat endeksi yayımlanmıyor.")

            # alt sektörlerin son 24 ayı
            st.markdown('<p style="font-weight:600;margin-top:1rem">Üretimin yıllık değişimi, son 24 ay</p>',
                        unsafe_allow_html=True)
            hm4 = a_y.dropna(how="all").iloc[-24:]
            order4 = a_son.sort_values(ascending=False).index
            z4 = hm4[order4].T.values
            fh4 = go.Figure(go.Heatmap(
                z=np.clip(z4, -20, 20), x=[ay(p) for p in hm4.index], y=[kisa_ad(c) for c in order4],
                customdata=z4, colorscale=[[0, RED], [.5, "#efe9df"], [1, TEAL]], zmid=0, zmin=-20, zmax=20,
                xgap=2, ygap=2, hovertemplate="%{y} · %{x}<br>%{customdata:.1f}%<extra></extra>",
                colorbar=dict(thickness=8, len=.8, ticksuffix="%", outlinewidth=0)))
            fh4.update_layout(height=max(240, 60 * len(order4) + 60), margin=dict(l=4, r=4, t=6, b=6),
                              paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                              font=dict(family="Inter", size=11, color=INK))
            fh4.update_yaxes(autorange="reversed", ticks="")
            fh4.update_xaxes(ticks="", tickangle=0, nticks=8)
            st.plotly_chart(fh4, width="stretch", config=CFG)
            src("TÜİK, sanayi üretim endeksi (NACE 4'lü) ve üretici fiyat endeksi; satış payları: sanayi ürün "
                "istatistikleri · renk ölçeği ±%20'de kesildi")

    # 03 fiyatlar
    yi_s, yd_s = M["yiufe_imalat"], M["ydufe_imalat"]
    if kod != "C" and "yiufe" in TS and kod in TS["yiufe"]:
        yi_s = TS["yiufe"][kod]
        yd_s = TS["ydufe"][kod] if "ydufe" in TS and kod in TS["ydufe"] else yd_s
    yiufe_y, ydufe_y = yoy(yi_s), yoy(yd_s)
    p_uf, v_uf = son_gecerli(yiufe_y)
    gap = v_uf - son_gecerli(tufe_y)[1]
    yer = "imalat sanayiinde" if kod == "C" else f"{ad.lower()} sektöründe"
    section("03", "Üretici fiyatları",
            f"{ay(p_uf)} itibarıyla {yer} yurt içi üretici fiyatları geçen yılın aynı ayına göre {pct(v_uf)} arttı.")
    gor3 = st.segmented_control("Görünüm", ["Yıllık %", "Endeks"], default="Yıllık %",
                                label_visibility="collapsed", key="g3")
    stats([("Bir yıl önce", pct(yiufe_y.get(p_uf - 12, np.nan)), ay(p_uf - 12)),
           ("Son 12 ay ortalaması", pct(yiufe_y.rolling(12).mean().dropna().iloc[-1]), ""),
           ("TÜFE ile fark", f'<span class="{cls(-gap)}">{num(gap) if gap < 0 else "+" + num(gap)} puan</span>',
            f"TÜFE (genel) {pct(son_gecerli(tufe_y)[1])}")]
          + ([("İmalat sanayii Yİ-ÜFE", pct(yoy(M["yiufe_imalat"]).get(p_uf, np.nan)), ay(p_uf))] if karsi else []))
    if gor3 == "Endeks":
        f = line_chart([("Yİ-ÜFE (2003=100)", yi_s, NAVY),
                        ("TÜFE genel (2003=100)", M["tufe"], OCHRE)]
                       + ([("İmalat sanayii Yİ-ÜFE (2003=100)", M["yiufe_imalat"], IMALAT_RENK)] if karsi else []),
                       pctaxis=False)
    else:
        f = line_chart([("Yİ-ÜFE", yiufe_y, NAVY), ("TÜFE genel", tufe_y, OCHRE),
                        ("YD-ÜFE", ydufe_y, "#7f8c8d")]
                       + ([("İmalat sanayii Yİ-ÜFE", yoy(M["yiufe_imalat"]), IMALAT_RENK)] if karsi else []))
    st.plotly_chart(f, width="stretch", config=CFG)
    src("TÜİK, Yİ-ÜFE (2003=100), YD-ÜFE (2010=100), TÜFE (2003=100)")

    # 04 dış ticaret
    if "ihracat" in TS and "ithalat" in TS and kod in TS["ihracat"]:
        ex, im = TS["ihracat"][kod].dropna(), TS["ithalat"][kod].dropna()
        ex12, im12 = ex.rolling(12).sum(), im.rolling(12).sum()
        ex12y, im12y = yoy(ex12), yoy(im12)
        pdt = ex.index[-1]
        kap = ex12.iloc[-1] / im12.iloc[-1] * 100
        section("04", "Dış ticaret",
                f"Son 12 ayda ({ay(pdt)} itibarıyla) {yer} ihracat {num(ex12.iloc[-1] / 1e6, 1)} milyar $, "
                f"ithalat {num(im12.iloc[-1] / 1e6, 1)} milyar $. İhracat bir önceki 12 aya göre "
                f"{pct(ex12y.iloc[-1], sign=True)} değişti; ihracatın ithalatı karşılama oranı {pct(kap, 0)}.")
        stats([("İhracat, son 12 ay", f"{num(ex12.iloc[-1] / 1e6, 1)} mlr $", pct(ex12y.iloc[-1], sign=True) + " yıllık"),
               ("İthalat, son 12 ay", f"{num(im12.iloc[-1] / 1e6, 1)} mlr $", pct(im12y.iloc[-1], sign=True) + " yıllık"),
               ("Dış ticaret dengesi", f"{num((ex12.iloc[-1] - im12.iloc[-1]) / 1e6, 1)} mlr $", "son 12 ay"),
               ("Karşılama oranı", pct(kap, 0), "ihracat / ithalat")])
        g4 = st.segmented_control("Görünüm", ["12 aylık toplam, yıllık %", "12 aylık toplam (mlr $)", "Aylık (mlr $)"],
                                  default="12 aylık toplam, yıllık %", label_visibility="collapsed", key="g4")
        if g4 == "12 aylık toplam (mlr $)":
            f = line_chart([("İhracat", ex12["2015":] / 1e6, TEAL), ("İthalat", im12["2015":] / 1e6, RED)],
                           pctaxis=False, clip=False)
        elif g4 == "Aylık (mlr $)":
            f = line_chart([("İhracat", ex["2015":] / 1e6, TEAL), ("İthalat", im["2015":] / 1e6, RED)],
                           pctaxis=False, clip=False)
        else:
            ex_im = yoy(TS["ihracat"]["C"].rolling(12).sum())
            f = line_chart([("İhracat", ex12y["2015":], TEAL), ("İthalat", im12y["2015":], RED)]
                           + ([("İmalat sanayii ihracatı", ex_im["2015":], IMALAT_RENK)] if karsi else []))
        st.plotly_chart(f, width="stretch", config=CFG)
        exa = TS["ihracat"].drop(columns="C", errors="ignore")
        exa12 = exa.rolling(12).sum()
        g12 = yoy(exa12).iloc[-1]
        pay = (exa12.iloc[-1] / TS["ihracat"]["C"].rolling(12).sum().iloc[-1] * 100)
        c_l, c_r = st.columns(2, gap="large")
        with c_l:
            st.markdown(f'<div class="eyebrow" style="margin:.4rem 0">İhracat, son 12 ay, yıllık · {ay(pdt)}</div>',
                        unsafe_allow_html=True)
            st.plotly_chart(hbar(g12, TEAL, RED, kod, "12 ay yıllık"), width="stretch", config=CFG)
        with c_r:
            st.markdown(f'<div class="eyebrow" style="margin:.4rem 0">İmalat ihracatındaki pay · son 12 ay</div>',
                        unsafe_allow_html=True)
            fp = hbar(pay, NAVY, NAVY, kod, "Pay")
            fp.update_traces(text=[pct(v) for v in pay.dropna().sort_values().values])
            st.plotly_chart(fp, width="stretch", config=CFG)
        src("TÜİK, genel ticaret sistemine göre dış ticaret, ISIC Rev.4 · TCMB EVDS üzerinden · bin ABD doları")

        # yıllık değişim: tam yıllar, yılbaşından bu yana, son ay
        def yillik_degisim(m: pd.Series, ilk_yil: int = 2019) -> pd.Series:
            m = m.dropna()
            son_p = m.index[-1]
            yil = m.groupby(m.index.year).agg(["sum", "size"])
            tam = yil[yil["size"] == 12]["sum"]
            out = {}
            for y in tam.index:
                if y >= ilk_yil and (y - 1) in tam.index:
                    out[str(y)] = (tam[y] / tam[y - 1] - 1) * 100
            if son_p.month < 12:
                bu = m[(m.index.year == son_p.year)].sum()
                once = m[(m.index.year == son_p.year - 1) & (m.index.month <= son_p.month)].sum()
                if once > 0:
                    out[f"{son_p.year} Ocak – {AYLAR_[son_p.month - 1]}"] = (bu / once - 1) * 100
            onceki = m.get(son_p - 12, np.nan)
            out[f"{son_p.year} {AYLAR_[son_p.month - 1]}"] = (m[son_p] / onceki - 1) * 100
            return pd.Series(out)

        def degisim_bar(v: pd.Series, renk_pos: str) -> go.Figure:
            fy = go.Figure(go.Bar(x=v.values, y=list(v.index), orientation="h",
                                  marker_color=[renk_pos if x_ >= 0 else RED for x_ in v.values],
                                  text=[pct(x_, sign=True) for x_ in v.values], textposition="outside",
                                  textfont=dict(size=11, color=INK), cliponaxis=False,
                                  hovertemplate="%{y}: %{x:.1f}%<extra></extra>"))
            lo_, hi_ = min(v.min(), 0), max(v.max(), 0)
            pad_ = (hi_ - lo_) * .25 or 1
            fy.update_layout(height=40 * len(v) + 40, margin=dict(l=4, r=56, t=6, b=6),
                             paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                             font=dict(family="Inter", size=12, color=INK), bargap=.5)
            fy.update_xaxes(visible=False, range=[lo_ - (pad_ if lo_ < 0 else 0), hi_ + pad_])
            fy.update_yaxes(showgrid=False, ticks="", autorange="reversed")  # en eski yıl üstte
            return fy

        st.markdown('<p style="font-weight:600;margin-top:1.4rem">Yıllık değişim: yıl, yılbaşından bu yana, son ay</p>',
                    unsafe_allow_html=True)
        y_l, y_r = st.columns(2, gap="large")
        with y_l:
            st.markdown('<div class="eyebrow" style="margin:.4rem 0">İhracat ($)</div>', unsafe_allow_html=True)
            st.plotly_chart(degisim_bar(yillik_degisim(ex), TEAL), width="stretch", config=CFG)
        with y_r:
            st.markdown('<div class="eyebrow" style="margin:.4rem 0">İthalat ($)</div>', unsafe_allow_html=True)
            st.plotly_chart(degisim_bar(yillik_degisim(im), OCHRE), width="stretch", config=CFG)
        src("TÜİK, ekonomik faaliyetlere göre dış ticaret (ISIC Rev.4), TCMB EVDS üzerinden · yıllık toplamlar, "
            "geçen yılın aynı dönemine göre")

# ================================================================ İSTİHDAM VE CİRO (TÜİK SDMX)
def seri_bolumu(no: str, baslik: str, s_: pd.Series, yer: str, fiil: str, kaynak: str, key: str,
                endeks_adi: str = "Endeks", endeks_var: bool = True) -> None:
    sy = yoy(s_)
    p_, v_ = son_gecerli(sy)
    section(no, baslik, f"{ay(p_)} itibarıyla {yer} {fiil} geçen yılın aynı ayına göre "
                        f"{pct(abs(v_))} {'azaldı' if v_ < 0 else 'arttı'}.")
    secenek = ["Yıllık %", "12 ay ortalama, yıllık %"] + ([endeks_adi] if endeks_var else [])
    g = st.segmented_control("Görünüm", secenek, default="Yıllık %", label_visibility="collapsed", key=key)
    o12 = sy.rolling(12).mean()
    d3 = sy.dropna().iloc[-3:].mean() - sy.dropna().iloc[-6:-3].mean()
    stats([("Bir yıl önce", pct(sy.get(p_ - 12, np.nan)), ay(p_ - 12)),
           ("Son 12 ay ortalaması", pct(o12.dropna().iloc[-1]), ""),
           ("Son 3 ay, önceki 3 aya göre",
            f'<span class="{cls(d3)}">{num(d3) if d3 < 0 else "+" + num(d3)} puan</span>', "ortalamalar")])
    if g == endeks_adi:
        f = line_chart([(endeks_adi, s_["2015":], NAVY)], pctaxis=False, clip=False)
    elif g == "12 ay ortalama, yıllık %":
        f = line_chart([("12 ay ortalama, yıllık %", o12["2015":], NAVY)], clip=False)
    else:
        f = line_chart([("Yıllık %", sy["2015":], NAVY), ("12 ay ortalama", o12["2015":], "#8a95a5")])
    st.plotly_chart(f, width="stretch", config=CFG)
    src(kaynak)


with tab_ist:
    gerekli = {"ucretli_calisan", "ciro"}
    if not gerekli <= set(TS):
        st.info("Bu sekme TÜİK SDMX verisi gerektiriyor. `TUIK_API_KEY` tanımlayıp "
                "`python scripts/guncelle.py --tuik` çalıştırın.", icon="ℹ️")
    else:
        ortak = [c for c in TS["ciro"].columns if c in TS["ucretli_calisan"].columns]
        sec = st.selectbox("Sektör", ortak, format_func=lambda c: "C · İmalat sanayii (toplam)" if c == "C"
                           else f"{c} · {ADLAR.get(c, (c,))[0]}", key="ist_sektor")
        ad_i = "İmalat sanayii" if sec == "C" else ADLAR.get(sec, (sec, sec))[0]
        yer = "imalat sanayiinde" if sec == "C" else f"{ad_i.lower()} sektöründe"
        uc = TS["ucretli_calisan"][sec]
        ci = TS["ciro"][sec]
        uf_kaynak = TS["yiufe"][sec] if "yiufe" in TS and sec in TS["yiufe"] else M["yiufe_imalat"]
        reel = (ci / uf_kaynak.reindex(ci.index)).dropna()
        reel = reel / reel["2021"].mean() * 100
        uc_y, ci_y, re_y = yoy(uc), yoy(ci), yoy(reel)
        p_uc, v_uc = son_gecerli(uc_y)
        p_ci, v_ci = son_gecerli(ci_y)
        v_re = son_gecerli(re_y)[1]
        sue_s = sue if sec == "C" else (S[sec] if sec in S else None)

        hl, hr = st.columns([1, 1.6], gap="large")
        with hl:
            st.markdown(f'<div class="eyebrow">İstihdam ve ciro</div>'
                        f'<div class="hero">{ad_i if len(ad_i) < 28 else ADLAR[sec][1]}</div>'
                        f'<p style="margin:1rem 0 .2rem 0;font-weight:600;font-size:.88rem">'
                        f'Ücretli çalışan, yıllık değişim · {ay(p_uc)}</p>' + big_pct(v_uc, "neg" if v_uc < 0 else "pos"),
                        unsafe_allow_html=True)
        with hr:
            verim = "yükseliyor; bu, emek verimliliğinde artışa işaret eder" if v_re > v_uc else \
                    "geriliyor; bu, emek verimliliğinde zayıflamaya işaret eder"
            st.markdown(f'<p class="lead" style="margin-top:2.6rem">Ücretli çalışan sayısı bir yıl önceye göre '
                        f'{"azalıyor" if v_uc < 0 else "artıyor"}. Reel ciro istihdamdan '
                        f'{"hızlı" if v_re > v_uc else "yavaş"} seyrettiği için çalışan başına reel ciro {verim}.</p>',
                        unsafe_allow_html=True)
        items = [("Ciro, yıllık (nominal)", pct(v_ci, sign=True), ay(p_ci)),
                 ("Ciro, yıllık (reel)", pct(v_re, sign=True), "Yİ-ÜFE ile arındırılmış"),
                 ("Ücretli çalışan", num(uc.dropna().iloc[-1] / 1000, 0) + " bin", ay(uc.dropna().index[-1]))]
        if sue_s is not None and yoy(sue_s).notna().any():
            items.append(("Üretim, yıllık", pct(son_gecerli(yoy(sue_s))[1], sign=True), "karşılaştırma için"))
        stats(items)

        seri_bolumu("01", "Ücretli çalışan", uc, yer, "ücretli çalışan sayısı",
                    "TÜİK SDMX, ücretli çalışan istatistikleri · takvim etkisinden arındırılmış",
                    "ist_uc", "Çalışan sayısı")
        seri_bolumu("02", "Ciro endeksi (nominal)", ci, yer, "ciro",
                    "TÜİK SDMX, ciro endeksi · takvim etkisinden arındırılmış, 2021=100", "ist_ci")
        seri_bolumu("03", "Reel ciro", reel, yer, "reel ciro",
                    "TÜİK SDMX, ciro endeksi ve Yİ-ÜFE (hesaplama) · 2021=100", "ist_re")

        if "ciro_yurtici" in TS and "ciro_yurtdisi" in TS and sec in TS["ciro_yurtdisi"]:
            yi_, yd_ = yoy(TS["ciro_yurtici"][sec]), yoy(TS["ciro_yurtdisi"][sec])
            p4 = yd_.dropna().index[-1]
            section("04", "Yurt içi ve yurt dışı ciro",
                    f"{ay(p4)} itibarıyla yurt içi satışlardan elde edilen ciro {pct(yi_.dropna().iloc[-1], sign=True)}, "
                    f"yurt dışı satışlardan elde edilen ciro {pct(yd_.dropna().iloc[-1], sign=True)} değişti (yıllık, nominal TL).")
            f = line_chart([("Yurt dışı ciro, yıllık %", yd_["2015":], TEAL),
                            ("Yurt içi ciro, yıllık %", yi_["2015":], OCHRE)], clip=False)
            st.plotly_chart(f, width="stretch", config=CFG)
            src("TÜİK SDMX, ciro endeksi · yurt içi / yurt dışı kırılımı")

        # sektör karşılaştırması
        section("05", "Sektörler", "Son açıklanan ayda ücretli çalışan ve nominal ciro, yıllık değişim.")
        c_l, c_r = st.columns(2, gap="large")
        uc_all = TS["ucretli_calisan"].drop(columns="C", errors="ignore").apply(yoy)
        ci_all = TS["ciro"].drop(columns="C", errors="ignore").apply(yoy)
        with c_l:
            pu = uc_all.dropna(how="all").index[-1]
            st.markdown(f'<div class="eyebrow" style="margin:.4rem 0">Ücretli çalışan, yıllık · {ay(pu)}</div>',
                        unsafe_allow_html=True)
            st.plotly_chart(hbar(uc_all.loc[pu], TEAL, RED, sec), width="stretch", config=CFG)
        with c_r:
            pc = ci_all.dropna(how="all").index[-1]
            st.markdown(f'<div class="eyebrow" style="margin:.4rem 0">Ciro (nominal), yıllık · {ay(pc)}</div>',
                        unsafe_allow_html=True)
            st.plotly_chart(hbar(ci_all.loc[pc], NAVY, RED, sec, "Ciro yıllık"), width="stretch", config=CFG)

# ================================================================ TCMB
KR = load_kredi(_SURUM)


def kredi_deger(sek: str, yil: int, alan: str = "nakdi") -> float:
    """Yıl sonu kredi (bin TL); seri değişikliği nedeniyle varsa yeni seri tercih edilir."""
    d = KR[(KR["sektor"] == sek) & (KR["yil"] == yil)]
    if d.empty:
        return np.nan
    d = d.sort_values("seri", key=lambda s_: s_.map({"yeni": 0, "eski": 1}))
    return float(d.iloc[0][alan])


def kredi_buyume(sek: str, yil: int) -> float:
    """Aynı seri içinde yıllık büyüme; 2023 seri değişikliği nedeniyle hesaplanmaz."""
    if yil == 2023:
        return np.nan
    seri = "yeni" if yil >= 2024 else "eski"
    d = KR[(KR["sektor"] == sek) & (KR["seri"] == seri)].set_index("yil")["nakdi"]
    if yil in d.index and (yil - 1) in d.index and d[yil - 1] > 0:
        return (d[yil] / d[yil - 1] - 1) * 100
    return np.nan


def kredi_oran(sek: str, yil: int) -> float:
    """Tahsili gecikmiş alacak oranı: sorunlu / (nakdi + sorunlu)."""
    n, s_ = kredi_deger(sek, yil), kredi_deger(sek, yil, "sorunlu")
    return s_ / (n + s_) * 100 if pd.notna(n) and pd.notna(s_) and n + s_ > 0 else np.nan


def grup_bar(yillar: list[int], seriler: list[tuple[str, list[float], str]], h: int = 380) -> go.Figure:
    fg = go.Figure()
    for ad_, vals, renk in seriler:
        fg.add_bar(x=[str(y) for y in yillar], y=vals, name=ad_, marker_color=renk,
                   text=[pct(v) if pd.notna(v) else "" for v in vals], textposition="outside",
                   textfont=dict(size=11, color=INK), cliponaxis=False, constraintext="none", textangle=0,
                   hovertemplate="%{x}: %{y:.1f}%<extra>" + ad_ + "</extra>")
    fg.update_layout(height=h, barmode="group", bargap=.3, bargroupgap=.06, margin=dict(l=4, r=8, t=40, b=24),
                     paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                     font=dict(family="Inter", size=11, color=MUTED),
                     legend=dict(orientation="h", y=1.02, yanchor="bottom", x=0, font=dict(color=INK, size=11)),
                     showlegend=len(seriler) > 1)
    fg.update_xaxes(type="category", showgrid=False, linecolor=LINE)
    fg.update_yaxes(gridcolor="#e4dccd", tickprefix="%", zeroline=True, zerolinecolor="#b9b0a0")
    return fg


with tab_tcmb:
    kko_s = TS.get("kko", pd.DataFrame())
    t_ops = ["C"] + [k for k in ADLAR if k in kko_s.columns or k in set(KR["sektor"])]
    t1, t2 = st.columns([4, 1])
    t_kod = t1.selectbox("Sektör", t_ops, key="t_sektor",
                         format_func=lambda c: "C · İmalat sanayii (toplam)" if c == "C" else f"{c} · {ADLAR[c][0]}")
    son_yil = int(USD.index[-1].year)
    with t2.popover(f"⚙ {st.session_state.get('t_yil', (2015, son_yil))[0]}–"
                    f"{st.session_state.get('t_yil', (2015, son_yil))[1]} · "
                    f"{'₺' if st.session_state.get('t_para', '₺') == '₺' else '$'}", width="stretch"):
        st.slider("Dönem", 2010, son_yil, (2015, son_yil), key="t_yil")
        st.radio("Kredi tutarı", ["₺", "$"], horizontal=True, key="t_para")
    y0, y1 = st.session_state.get("t_yil", (2015, son_yil))
    para = st.session_state.get("t_para", "₺")
    donem = slice(str(y0), str(y1))
    t_ad = "İmalat sanayii" if t_kod == "C" else ADLAR[t_kod][0]
    t_kisa = "İmalat sanayii" if t_kod == "C" else ADLAR[t_kod][1]
    kko_t = kko if t_kod == "C" else (kko_s[t_kod] if t_kod in kko_s else None)
    karsi_t = t_kod != "C"

    if kko_t is not None and kko_t.notna().any():
        p_kt, v_kt = son_gecerli(kko_t)
        big_t = f'<div class="big neu"><span class="p">%</span>{num(v_kt)}</div>'
        bas_t = f"Kapasite kullanım oranı · {ay(p_kt)}"
    else:
        big_t, bas_t = "", "Bu sektör için kapasite kullanım oranı yayımlanmıyor"
    _boy = "" if len(t_kisa) < 16 else ' style="font-size:clamp(2rem,3.6vw,2.8rem)"'
    st.markdown(f'<div class="eyebrow">TCMB göstergeleri</div><div class="hero"{_boy}>{t_kisa}</div>'
                f'<p style="margin:1rem 0 .2rem 0;font-weight:600;font-size:.88rem">{bas_t}</p>{big_t}',
                unsafe_allow_html=True)
    if karsi_t and big_t:
        st.markdown(f'<div class="sub">Karşılaştırma: imalat sanayii {pct(kko.get(p_kt, v_kko))}</div>',
                    unsafe_allow_html=True)
    rk_y = yoy(rek)
    st.markdown(f'<p class="lead" style="margin:1rem 0">Reel efektif kur bir yıl öncesinin '
                f'{"üzerinde" if rk_y.dropna().iloc[-1] > 0 else "altında"}: Türk lirasının reel olarak '
                f'{"değer kazanması ihracatçının fiyat rekabetini zorlaştırır." if rk_y.dropna().iloc[-1] > 0 else "değer kaybetmesi ihracatçının fiyat rekabetini destekler."}</p>',
                unsafe_allow_html=True)
    kr_son = int(KR["yil"].max()) if not KR.empty else None
    ust = [("Reel efektif kur", num(v_rk), f"{ay(p_rk)} · 2025=100"),
           ("USD/TRY", num(v_us, 2), f"yıllık {pct(usd_y.dropna().iloc[-1], sign=True)}")]
    if kko_t is not None and kko_t.notna().any():
        ust.append(("Kapasite kullanımı, 12 ay ort.", pct(kko_t.rolling(12).mean().dropna().iloc[-1]), t_kisa))
    if kr_son and pd.notna(kredi_deger(t_kod, kr_son)):
        ust.append(("Nakdi kredi", f"{num(kredi_deger(t_kod, kr_son) / 1e6, 1)} mlr ₺", f"{kr_son} yıl sonu"))
    stats(ust)

    # 01 kapasite kullanımı
    if kko_t is not None and kko_t.notna().any():
        k12 = kko_t.rolling(12).mean()
        section("01", "Kapasite kullanım oranı",
                f"{ay(p_kt)} itibarıyla {t_ad.lower() if t_kod == 'C' else t_ad.lower() + ' sektörü'}nde kapasite "
                f"kullanım oranı {pct(v_kt)}." + (f" İmalat sanayii ortalaması {pct(kko.get(p_kt, v_kko))}." if karsi_t else ""))
        stats([("Bir yıl önce", pct(kko_t.get(p_kt - 12, np.nan)), ay(p_kt - 12)),
               ("Son 12 ay ortalaması", pct(k12.dropna().iloc[-1]), ""),
               ("Son 3 ay, önceki 3 aya göre",
                f"{num(kko_t.dropna().iloc[-3:].mean() - kko_t.dropna().iloc[-6:-3].mean(), 1)} puan", "ortalamalar")]
              + ([("İmalat sanayii", pct(kko.get(p_kt, v_kko)), ay(p_kt))] if karsi_t else []))
        f = line_chart([("Aylık", kko_t[donem], NAVY), ("12 aylık ortalama", k12[donem], "#8a95a5")]
                       + ([("İmalat sanayii", kko[donem], IMALAT_RENK)] if karsi_t else []))
        f.update_yaxes(tickformat=".0f")
        st.plotly_chart(f, width="stretch", config=CFG)
        src("TCMB EVDS, imalat sanayi kapasite kullanım oranı" + (" · kesikli çizgi: imalat sanayii" if karsi_t else ""))

    section("02", "Reel efektif döviz kuru",
            f"{ay(p_rk)} itibarıyla Yİ-ÜFE bazlı reel efektif kur endeksi {num(v_rk)}; bir yıl öncesine göre "
            f"{pct(abs(rk_y.dropna().iloc[-1]))} {'yükseldi' if rk_y.dropna().iloc[-1] > 0 else 'düştü'}.")
    f = line_chart([("Reel efektif kur", rek[donem], NAVY)], pctaxis=False)
    f.add_hline(y=100, line=dict(color=LINE, dash="dot"))
    st.plotly_chart(f, width="stretch", config=CFG)
    src("TCMB EVDS, Yİ-ÜFE bazlı reel efektif kur · 2025=100; yükseliş TL'nin reel değer kazandığını gösterir")

    section("03", "Dolar kuru",
            f"{ay(p_us)} itibarıyla aylık ortalama dolar kuru {num(v_us)}; bir yıl öncesine göre "
            f"{pct(usd_y.dropna().iloc[-1])} yükseldi.")
    g = st.segmented_control("Görünüm", ["Düzey", "Yıllık %"], default="Düzey",
                             label_visibility="collapsed", key="g_usd")
    if g == "Yıllık %":
        f = line_chart([("USD/TRY, yıllık %", usd_y[donem], NAVY)])
    else:
        f = line_chart([("USD/TRY", USD[donem], NAVY)], pctaxis=False)
    st.plotly_chart(f, width="stretch", config=CFG)
    src("TCMB EVDS, USD/TRY döviz satış kuru · aylık ortalama")

    # 04 kredi
    if kr_son and pd.notna(kredi_deger(t_kod, kr_son)):
        n_s = kredi_deger(t_kod, kr_son)
        n_c = kredi_deger("C", kr_son)
        b_s, b_c = kredi_buyume(t_kod, kr_son), kredi_buyume("C", kr_son)
        tufe_a = M["tufe"].dropna()
        tufe_dec = (tufe_a[pd.Period(f"{kr_son}-12", "M")] / tufe_a[pd.Period(f"{kr_son - 1}-12", "M")] - 1) * 100
        reel_k = ((1 + b_s / 100) / (1 + tufe_dec / 100) - 1) * 100
        o_s, o_c = kredi_oran(t_kod, kr_son), kredi_oran("C", kr_son)
        ort_y = [y for y in range(kr_son - 2, kr_son + 1)]
        o_s_ort = np.nanmean([kredi_oran(t_kod, y) for y in ort_y])
        o_c_ort = np.nanmean([kredi_oran("C", y) for y in ort_y])
        usd_ara = float(USD.get(pd.Period(f"{kr_son}-12", "M"), USD.dropna().iloc[-1]))
        tut = (f"{num(n_s / 1e6, 1)} milyar TL" if para == "₺" else f"{num(n_s * 1000 / usd_ara / 1e9, 1)} milyar $")
        if karsi_t:
            ac = (f"{kr_son} yıl sonunda imalat sanayii kredilerinin %{num(n_s / n_c * 100)}'si {t_ad.lower()} "
                  f"sektörüne gitti. Sektörün nakdi kredisi {kr_son} yılında {pct(b_s)} "
                  f"{'arttı' if b_s > 0 else 'azaldı'} ve {tut} oldu. İmalat sanayii kredisi aynı dönemde "
                  f"{pct(b_c)} {'arttı' if b_c > 0 else 'azaldı'}. Aralık TÜFE artışı {pct(tufe_dec)} iken reel "
                  f"değişim {pct(reel_k, sign=True)}. {ort_y[0]}-{ort_y[-1]} ortalamasında tahsili gecikmiş alacak "
                  f"oranı {t_ad.lower()} sektöründe {pct(o_s_ort)}, imalat sanayiinde {pct(o_c_ort)}. "
                  f"{kr_son} yıl sonunda sektörde oran {pct(o_s)}.")
        else:
            ac = (f"İmalat sanayiinin nakdi kredisi {kr_son} yılında {pct(b_s)} {'arttı' if b_s > 0 else 'azaldı'} "
                  f"ve {tut} oldu. Aralık TÜFE artışı {pct(tufe_dec)} iken reel değişim {pct(reel_k, sign=True)}. "
                  f"{kr_son} yıl sonunda tahsili gecikmiş alacak oranı {pct(o_s)}.")
        section("04", "Kredi", ac)
        tut_k = (f'{num(n_s / 1e6, 1)}<span class="p" style="font-size:.5em"> mlr ₺</span>' if para == "₺"
                 else f'{num(n_s * 1000 / usd_ara / 1e9, 1)}<span class="p" style="font-size:.5em"> mlr $</span>')
        stats([(f"Nakdi kredi, {kr_son}", tut_k, "yıl sonu"),
               ("Yıllık büyüme (nominal)", f'<span class="pos">{pct(b_s, sign=True)}</span>',
                f"reel {pct(reel_k, sign=True)} · Aralık TÜFE {pct(tufe_dec)}")]
              + ([("İmalat kredileri içindeki pay", pct(n_s / n_c * 100), "")] if karsi_t else [])
              + [("Tahsili gecikmiş alacak oranı", pct(o_s), "sorunlu / toplam")])
        yillar_k = [y for y in sorted(KR["yil"].unique()) if max(y0, 2010) <= y <= y1][-6:]  # okunabilirlik için son 6 yıl
        yb = [y for y in yillar_k if y != 2023 and pd.notna(kredi_buyume("C", y))]
        k_l, k_r = st.columns(2, gap="large")
        with k_l:
            st.markdown('<p style="font-weight:600;margin:.8rem 0 0 0">Kredi büyümesi, yıllık %</p>', unsafe_allow_html=True)
            sr = [(t_ad if karsi_t else "İmalat sanayii", [kredi_buyume(t_kod, y) for y in yb], NAVY)]
            if karsi_t:
                sr.append(("İmalat sanayii", [kredi_buyume("C", y) for y in yb], "#8a5a12"))
            st.plotly_chart(grup_bar(yb, sr), width="stretch", config=CFG)
        with k_r:
            st.markdown('<p style="font-weight:600;margin:.8rem 0 0 0">Tahsili gecikmiş alacak oranı, %</p>',
                        unsafe_allow_html=True)
            sr = [(t_ad if karsi_t else "İmalat sanayii", [kredi_oran(t_kod, y) for y in yillar_k], NAVY)]
            if karsi_t:
                sr.append(("İmalat sanayii", [kredi_oran("C", y) for y in yillar_k], "#8a5a12"))
            st.plotly_chart(grup_bar(yillar_k, sr), width="stretch", config=CFG)
        if not karsi_t:
            ks = pd.Series({k: kredi_deger(k, kr_son) for k in ADLAR}).dropna()
            ko = pd.Series({k: kredi_oran(k, kr_son) for k in ADLAR}).dropna()
            s_l, s_r = st.columns(2, gap="large")
            with s_l:
                st.markdown(f'<div class="eyebrow" style="margin:.6rem 0">İmalat kredileri içindeki pay · {kr_son}</div>',
                            unsafe_allow_html=True)
                fp = hbar(ks / n_c * 100, NAVY, NAVY, None, "Pay")
                fp.update_traces(text=[pct(v) for v in (ks / n_c * 100).sort_values().values])
                st.plotly_chart(fp, width="stretch", config=CFG)
            with s_r:
                st.markdown(f'<div class="eyebrow" style="margin:.6rem 0">Tahsili gecikmiş alacak oranı · {kr_son}</div>',
                            unsafe_allow_html=True)
                fo = hbar(ko, RED, RED, None, "Oran")
                fo.update_traces(text=[pct(v) for v in ko.sort_values().values])
                st.plotly_chart(fo, width="stretch", config=CFG)
        src("TCMB, sektör bilançoları (yıl sonu nakdi kredi: TL + YP; tahsili gecikmiş: tasfiye olunacak krediler) · "
            "2023 seri değişikliği nedeniyle 2023 büyümesi gösterilmiyor · grafikler seçili dönemin son 6 yılı"
            + (f" · $ dönüşümü Aralık {kr_son} ortalama kuruyla" if para == "$" else ""))

# ================================================================ HABER
with tab_haber:
    import html as _html
    from data import HABER_SORGU, haberler
    st.markdown('<div class="eyebrow">Haber</div><div class="hero">Sektör gündemi</div>'
                '<div class="sub">Google Haberler · son 30 gün · saatlik yenilenir</div>', unsafe_allow_html=True)
    h1, h2 = st.columns([3, 1])
    h_sec = h1.selectbox("Sektör", list(HABER_SORGU), key="h_sektor",
                         format_func=lambda c: "C · İmalat sanayii (toplam)" if c == "C" else f"{c} · {ADLAR[c][0]}")
    ek = h2.text_input("Ek arama terimi", key="h_ek", placeholder="ör. ihracat")
    sorgu = HABER_SORGU[h_sec] + (f" {ek}" if ek.strip() else "")
    liste = haberler(sorgu)
    if not liste:
        st.info("Haber bulunamadı ya da haber kaynağına erişilemedi.", icon="ℹ️")
    else:
        kaynaklar = pd.Series([h["kaynak"] for h in liste]).value_counts()
        st.markdown(f'<div class="secd">{len(liste)} haber · en çok: '
                    + ", ".join(f"{_html.escape(k)} ({v})" for k, v in kaynaklar.head(4).items()) + "</div>",
                    unsafe_allow_html=True)
        kart = []
        for h in liste:
            t = h["tarih"].tz_convert("Europe/Istanbul") if hasattr(h["tarih"], "tz_convert") else h["tarih"]
            tstr = f"{t.day} {AYLAR_KISA_[t.month - 1]} · {t:%H:%M}" if t else ""
            kart.append(f'<div style="border-top:1px solid {LINE};padding:.75rem 0">'
                        f'<div class="sub" style="font-size:.74rem">{_html.escape(h["kaynak"])} · {tstr}</div>'
                        f'<a href="{_html.escape(h["link"] or "#")}" target="_blank" '
                        f'style="font-family:Fraunces,serif;font-size:1.12rem;color:{INK};text-decoration:none">'
                        f'{_html.escape(h["baslik"])}</a></div>')
        st.markdown("".join(kart), unsafe_allow_html=True)
    src(f"Google Haberler RSS · arama: {_html.escape(sorgu)}")

# ================================================================ NACE 4'LÜ
with tab_nace:
    N4, NADI = load_nace34(_SURUM)
    if N4.empty:
        st.info("NACE 3'lü/4'lü verisi yok. `python scripts/guncelle.py --tuik` çalıştırın.", icon="ℹ️")
    else:
        st.markdown("<div class=\"eyebrow\">NACE 4'lü</div><div class=\"hero\">Alt sektörler</div>"
                    "<div class=\"sub\">Sanayi üretim endeksi, sınıf (4'lü) ve grup (3'lü) düzeyi · TÜİK SDMX</div>",
                    unsafe_allow_html=True)
        bolumler = sorted({c[:3] for c in N4.columns})
        b_sec = st.selectbox("Bölüm (NACE 2'li)", bolumler, key="n4_bolum",
                             format_func=lambda b: f"{b} · {ADLAR.get(b, (NADI.get(b, b),))[0]}")
        alt = [c for c in N4.columns if c.startswith(b_sec)]
        n4y = N4[alt].apply(yoy)
        son_p = n4y.dropna(how="all").index[-1]
        tablo = pd.DataFrame({
            "Kod": alt,
            "Ad": [NADI.get(c, c) for c in alt],
            "Düzey": ["4'lü" if len(c) == 5 else "3'lü" for c in alt],
            "Yıllık %": [n4y[c].get(son_p, np.nan) for c in alt],
            "12 ay ort. %": [n4y[c].rolling(12).mean().get(son_p, np.nan) for c in alt],
            "Son 36 ay": [N4[c].dropna().iloc[-36:].tolist() for c in alt],
        })
        g_ = tablo[tablo["Düzey"] == "4'lü"].dropna(subset=["Yıllık %"])
        if len(g_):
            n_art = int((g_["Yıllık %"] > 0).sum())
            en_y, en_d = g_.loc[g_["Yıllık %"].idxmax()], g_.loc[g_["Yıllık %"].idxmin()]
            section("01", f"{b_sec} altındaki sınıflar",
                    f"{ay(son_p)} itibarıyla {len(g_)} sınıftan {n_art} tanesinde üretim bir yıl öncesine göre arttı. "
                    f"En güçlü artış {en_y['Ad']} ({pct(en_y['Yıllık %'], sign=True)}), en sert düşüş "
                    f"{en_d['Ad']} ({pct(en_d['Yıllık %'])}).")
        st.dataframe(
            tablo, hide_index=True, width="stretch", height=min(38 * (len(tablo) + 1), 640),
            column_config={
                "Yıllık %": st.column_config.NumberColumn(format="%.1f"),
                "12 ay ort. %": st.column_config.NumberColumn(format="%.1f"),
                "Son 36 ay": st.column_config.LineChartColumn("Endeks, son 36 ay", width="medium"),
            })
        src(f"TÜİK SDMX, sanayi üretim endeksi alt endeksleri · takvim etkisinden arındırılmış · son dönem {ay(son_p)}")

        k_sec = st.selectbox("Sınıf", alt, key="n4_sinif", format_func=lambda c: f"{c} · {NADI.get(c, c)}")
        seri_bolumu("02", NADI.get(k_sec, k_sec), N4[k_sec], f"{NADI.get(k_sec, k_sec).lower()} faaliyetinde",
                    "üretim", "TÜİK SDMX, sanayi üretim endeksi alt endeksleri · 2021=100", "n4_g")

# ================================================================ FİRMALAR (İSO 500)
def tl_buyuk(x: float) -> str:
    if abs(x) >= 1e12:
        return f"{num(x / 1e12, 1)} trilyon ₺"
    if abs(x) >= 1e9:
        return f"{num(x / 1e9, 1)} mlr ₺"
    return f"{num(x / 1e6, 1)} mn ₺"


with tab_firma:
    F = load_iso500(_SURUM)
    if F.empty:
        st.info("İSO 500 verisi yok. `python scripts/guncelle.py --iso` çalıştırın.", icon="ℹ️")
    else:
        f1, f2, f3 = st.columns([1, 1.2, 2.4])
        yillar = sorted(F["yil"].unique(), reverse=True)
        yil = f1.selectbox("Yıl", yillar, key="f_yil")
        liste = f2.segmented_control("Liste", ["Tümü", "İSO 500", "İkinci 500"], default="Tümü", key="f_liste")
        sek_ops = ["C"] + sorted(c for c in F["nace"].dropna().unique() if 10 <= int(c[1:]) <= 33)
        f_sek = f3.selectbox("Sektör", sek_ops, key="f_sektor",
                             format_func=lambda c: "İmalat sanayii (toplam)" if c == "C"
                             else f"{c} · {ADLAR.get(c, (c,))[0]}")
        Fx = F[F["nace"].str[1:].astype(int).between(10, 33)].copy()  # yalnızca imalat (NACE 10–33)
        if liste == "İSO 500":
            Fx = Fx[Fx["liste"] == 1]
        elif liste == "İkinci 500":
            Fx = Fx[Fx["liste"] == 2]
        if f_sek != "C":
            Fx = Fx[Fx["nace"] == f_sek]
        cur, prev = Fx[Fx["yil"] == yil], Fx[Fx["yil"] == yil - 1]
        ad_f = "İmalat sanayii (toplam)" if f_sek == "C" else ADLAR.get(f_sek, (f_sek,))[0]
        if cur.empty:
            st.info("Bu seçimde firma yok.")
        else:
            top = cur["uretimden_satislar"].sum()
            # aynı firmaların satış büyümesi (iki yıl da listede olanlar)
            ortak = cur.merge(prev[["firma_id", "uretimden_satislar"]], on="firma_id", suffixes=("", "_once"))
            buy = ortak["uretimden_satislar"].sum() / ortak["uretimden_satislar_once"].sum() * 100 - 100 \
                if len(ortak) else np.nan
            uf_yil = M["yiufe_imalat"]
            fiyat = uf_yil[str(yil)].mean() / uf_yil[str(yil - 1)].mean() * 100 - 100
            reel = ((1 + buy / 100) / (1 + fiyat / 100) - 1) * 100 if not np.isnan(buy) else np.nan
            st.markdown(f'<div class="eyebrow">Firmalar · İSO 500 / İkinci 500 · {yil}</div>'
                        f'<div class="hero">{ad_f if len(ad_f) < 30 else ADLAR[f_sek][1]}</div>'
                        f'<p style="margin:1rem 0 .2rem 0;font-weight:600;font-size:.88rem">Üretimden satışlar, toplam (₺)</p>'
                        f'<div class="big neu" style="font-size:clamp(3rem,7vw,5.5rem)">{tl_buyuk(top)}</div>',
                        unsafe_allow_html=True)
            if not np.isnan(buy):
                st.markdown(f'<p class="lead" style="margin:1rem 0">Bir önceki yıl da listede olan {len(ortak)} firmanın '
                            f'satışları {pct(buy)} {"arttı" if buy > 0 else "azaldı"}; imalat Yİ-ÜFE yıllık ortalama artışı '
                            f'({pct(fiyat)}) düşüldüğünde reel değişim {pct(reel, sign=True)}.</p>', unsafe_allow_html=True)
            pay = cur.sort_values("uretimden_satislar", ascending=False)
            p5 = pay["uretimden_satislar"].head(5).sum() / top * 100
            hhi = ((pay["uretimden_satislar"] / top * 100) ** 2).sum()
            fv = cur.dropna(subset=["favok", "net_satislar"])
            fv = fv[fv["net_satislar"] > 0]
            ih = cur.dropna(subset=["ihracat_bin_usd", "net_satislar"])
            usd_yil = USD[str(yil)].mean()
            ih_oran = (ih["ihracat_bin_usd"].sum() * 1000 * usd_yil) / ih["net_satislar"].sum() * 100 if len(ih) else np.nan
            cal = cur["calisan"].dropna()
            stats([("Firma sayısı", num(len(cur), 0), f"{liste} · {yil}"),
                   ("İlk 5 firmanın payı", pct(p5), f"HHI {num(hhi, 0)}"),
                   ("FAVÖK marjı", pct(fv["favok"].sum() / fv["net_satislar"].sum() * 100) if len(fv) else "—",
                    f"{len(fv)} firmanın verisi"),
                   ("İhracat / net satış", pct(ih_oran) if len(ih) else "—", f"{len(ih)} firmanın verisi"),
                   ("Çalışan", num(cal.sum(), 0), f"{len(cal)} firmanın verisi")])

            # 01 pazar yapısı
            p10 = pay["uretimden_satislar"].head(10).sum() / top * 100
            ilk = pay.iloc[0]
            section("01", "Pazar yapısı",
                    f"Listedeki en büyük firma {ilk['unvan']}; satışlar içindeki payı {pct(ilk['uretimden_satislar'] / top * 100)}. "
                    f"İlk on firmanın toplam payı {pct(p10)}.")
                    
            m_l, m_r = st.columns([1.1, 1], gap="large")
            with m_l:
                rows = []
                for _, r in pay.head(12).iterrows():
                    rows.append(f'<div style="border-top:1px solid {LINE};padding:.5rem 0;display:flex;justify-content:space-between;gap:1rem">'
                                f'<div><div style="font-size:.92rem">{r["unvan"]}</div>'
                                f'<div class="sub" style="font-size:.74rem">{"İSO 500" if r["liste"] == 1 else "İkinci 500"} · '
                                f'sıra {int(r["sira"])} · {r["il"]}</div></div>'
                                f'<div style="font-family:Fraunces,serif;font-size:1.2rem;color:{NAVY}">'
                                f'{pct(r["uretimden_satislar"] / top * 100)}</div></div>')
                st.markdown("".join(rows), unsafe_allow_html=True)
            with m_r:
                kum = pay["uretimden_satislar"].cumsum().values / top * 100
                fc = base_fig(380)
                fc.add_scatter(x=np.arange(1, len(kum) + 1), y=kum, mode="lines", line=dict(color=NAVY, width=2),
                               fill="tozeroy", fillcolor="rgba(31,58,95,.07)",
                               hovertemplate="İlk %{x} firma: %{y:.1f}%<extra></extra>")
                for n_ in (10, 50, 100):
                    if n_ <= len(kum):
                        fc.add_annotation(x=n_, y=kum[n_ - 1], text=f"İlk {n_} · {pct(kum[n_ - 1])}", showarrow=True,
                                          arrowhead=0, ax=40, ay=20, font=dict(size=10, color=INK))
                fc.update_xaxes(dtick=None, tickformat=",d")
                fc.update_yaxes(tickprefix="%", range=[0, 102])
                st.markdown('<div class="sub">İlk n firmanın satışlardaki toplam payı</div>', unsafe_allow_html=True)
                st.plotly_chart(fc, width="stretch", config=CFG)

            # 02 iller
            il_g = cur.groupby("il").agg(satis=("uretimden_satislar", "sum"), firma=("unvan", "count"),
                                         calisan=("calisan", "sum"), ihracat=("ihracat_bin_usd", "sum"))
            il_g = il_g.drop(index="Belirtilmemiş", errors="ignore").sort_values("satis", ascending=False)
            il_pay = il_g["satis"] / top * 100
            section("02", "İllere göre dağılım",
                    f"Firmalar {len(il_g)} ilde toplanıyor; en büyük il {il_g.index[0]} (satışların {pct(il_pay.iloc[0])}). "
                    f"İlk üç ilin toplam payı {pct(il_pay.head(3).sum())}.")
            olcu = st.segmented_control("Gösterge", ["Üretimden satışlar", "Firma sayısı", "Çalışan sayısı", "İhracat"],
                                        default="Üretimden satışlar", key="f_il_olcu", label_visibility="collapsed")
            kol = {"Üretimden satışlar": "satis", "Firma sayısı": "firma", "Çalışan sayısı": "calisan",
                   "İhracat": "ihracat"}[olcu]
            ilv = il_g[kol].sort_values().tail(15)
            fil = go.Figure(go.Bar(x=ilv.values, y=ilv.index, orientation="h", marker_color=NAVY,
                                   text=[tl_buyuk(v) if kol == "satis" else
                                         (f"{num(v / 1e6, 1)} mlr $" if kol == "ihracat" else num(v, 0)) for v in ilv.values],
                                   textposition="outside", textfont=dict(size=10, color=INK), cliponaxis=False))
            fil.update_layout(height=460, margin=dict(l=4, r=80, t=6, b=6), paper_bgcolor="rgba(0,0,0,0)",
                              plot_bgcolor="rgba(0,0,0,0)", font=dict(family="Inter", size=11, color=INK), bargap=.35)
            fil.update_xaxes(visible=False)
            st.plotly_chart(fil, width="stretch", config=CFG)
            stats([("İlk 3 ilin payı", pct(il_pay.head(3).sum()), "üretimden satışlar"),
                   ("İlk 10 ilin payı", pct(il_pay.head(10).sum()), "üretimden satışlar"),
                   ("Firması olan il", num(len(il_g), 0), "81 ilin içinde")])
            src("İstanbul Sanayi Odası, İSO 500 ve İkinci 500 · il: firmanın bağlı olduğu sanayi/ticaret odasının ili "
                "(genel merkez ili değil)")

            # 03 büyüme
            if len(ortak):
                ortak = ortak.assign(buyume=(ortak["uretimden_satislar"] / ortak["uretimden_satislar_once"] - 1) * 100)
                ortak = ortak[ortak["uretimden_satislar_once"] > 0]
                section("03", "Büyüme",
                        f"İki yıl da listede olan {len(ortak)} firma içinde satışlarını en çok artıran "
                        f"{ortak.loc[ortak['buyume'].idxmax(), 'unvan']} ({pct(ortak['buyume'].max(), 0, sign=True)}).")
                b_l, b_r = st.columns(2, gap="large")
                cols_ = ["unvan", "il", "buyume", "uretimden_satislar"]
                cfg_ = {"unvan": "Firma", "il": "İl", "buyume": st.column_config.NumberColumn("Satış değişimi %", format="%.1f"),
                        "uretimden_satislar": st.column_config.NumberColumn("Üretimden satışlar (₺)", format="%,.0f")}
                b_l.markdown("**En hızlı büyüyenler**")
                b_l.dataframe(ortak.nlargest(10, "buyume")[cols_], hide_index=True, width="stretch", column_config=cfg_)
                b_r.markdown("**En çok gerileyenler**")
                b_r.dataframe(ortak.nsmallest(10, "buyume")[cols_], hide_index=True, width="stretch", column_config=cfg_)

            # 04 tüm firmalar
            section("04", "Firma listesi")
            goster = cur.sort_values("uretimden_satislar", ascending=False)[
                ["sira", "unvan", "nace", "il", "uretimden_satislar", "favok", "ihracat_bin_usd", "calisan"]]
            st.dataframe(goster, hide_index=True, width="stretch", height=420, column_config={
                "sira": "Sıra", "unvan": "Firma", "nace": "NACE", "il": "İl",
                "uretimden_satislar": st.column_config.NumberColumn("Üretimden satışlar (₺)", format="%,.0f"),
                "favok": st.column_config.NumberColumn("FAVÖK (₺)", format="%,.0f"),
                "ihracat_bin_usd": st.column_config.NumberColumn("İhracat (bin $)", format="%,.0f"),
                "calisan": st.column_config.NumberColumn("Çalışan", format="%,d")})
            src("İstanbul Sanayi Odası, İSO 500 ve İkinci 500 (iso500.org.tr)")

# ================================================================ ÜRÜNLER (PRODTR)
def yillik_ort(s: pd.Series) -> pd.Series:
    s = s.dropna()
    g = s.groupby(s.index.year)
    return g.mean()[g.size() == 12].rename(lambda y: str(y))


def ufe_yillik(nace: str) -> pd.Series:
    if nace != "C" and "yiufe" in TS and nace in TS["yiufe"]:
        return yillik_ort(TS["yiufe"][nace])
    return yillik_ort(M["yiufe_imalat"])


USD_YIL = yillik_ort(USD)
U = load_urunler(_SURUM)
_, NADI_ = load_nace34(_SURUM)


def liste_html(baslik: str, satirlar: list[tuple[str, str, str]]) -> str:
    h = f'<div class="eyebrow" style="margin:.6rem 0 .3rem 0">{baslik}</div>'
    for ad_, alt_, deger_ in satirlar:
        h += (f'<div style="border-top:1px solid {LINE};padding:.5rem 0;display:flex;justify-content:space-between;gap:1rem">'
              f'<div><div style="font-size:.88rem">{ad_}</div><div class="sub" style="font-size:.74rem">{alt_}</div></div>'
              f'<div style="font-family:Fraunces,serif;font-size:1.15rem;color:{NAVY};white-space:nowrap">{deger_}</div></div>')
    return h


def mlr_usd(x: float) -> str:
    return f"{num(x / 1e9, 2 if abs(x) < 1e9 else 1)} mlr $"


with tab_urun:
    if U is None:
        st.info("Ürün verisi yok. `data/ham/` klasörüne TÜİK dosyalarını koyup `python scripts/urunler.py` çalıştırın.",
                icon="ℹ️")
    else:
        yillar_u = [c for c in U.deger.columns if U.deger[c].notna().any()]
        u1, u2 = st.columns([1, 3])
        yil_u = u1.selectbox("Yıl", yillar_u[::-1], key="u_yil")
        nace_ops = ["C"] + sorted(U.bilgi["nace"].unique())
        u_sek = u2.selectbox("Sektör", nace_ops, key="u_sektor",
                             format_func=lambda c: "C · İmalat sanayii (toplam)" if c == "C"
                             else f"{c} · {ADLAR.get(c, (c,))[0]}")
        y0 = str(int(yil_u) - 1)
        B = U.bilgi if u_sek == "C" else U.bilgi[U.bilgi["nace"] == u_sek]
        V1 = U.deger.loc[B.index, yil_u]
        V0 = U.deger.loc[B.index, y0] if y0 in U.deger else pd.Series(np.nan, index=B.index)
        top_u = V1.sum()
        nom = (top_u / V0.sum() - 1) * 100 if V0.sum() > 0 else np.nan
        # hacim: iki yılda da değeri ve miktarı olan PRODTR kalemleri (önceki yıl fiyatlarıyla)
        kodlar_ = [k for k in B.index if not B.loc[k, "gizli"]]
        q1 = U.miktar.reindex(kodlar_)[yil_u] if yil_u in U.miktar else pd.Series(dtype=float)
        q0 = U.miktar.reindex(kodlar_)[y0] if y0 in U.miktar else pd.Series(dtype=float)
        ok = (q1 > 0) & (q0 > 0) & (V0.reindex(kodlar_) > 0) & (V1.reindex(kodlar_) > 0)
        hacim = ((V0.reindex(kodlar_)[ok] * (q1[ok] / q0[ok])).sum() / V0.reindex(kodlar_)[ok].sum() - 1) * 100 \
            if ok.any() else np.nan
        kapsam = V1.reindex(kodlar_)[ok].sum() / top_u * 100 if ok.any() else np.nan
        fiyat_u = ((1 + nom / 100) / (1 + hacim / 100) - 1) * 100 if not np.isnan(hacim) else np.nan
        uf_ = ufe_yillik(u_sek)
        ufe_art = (uf_.get(yil_u, np.nan) / uf_.get(y0, np.nan) - 1) * 100
        ad_u = "İmalat sanayii" if u_sek == "C" else ADLAR.get(u_sek, (u_sek, u_sek))[0]

        st.markdown(f'<div class="eyebrow">Ürünler · sanayi ürün istatistikleri · {yil_u}</div>'
                    f'<div class="hero">{ad_u if len(ad_u) < 30 else ADLAR[u_sek][1]}</div>'
                    f'<p style="margin:1rem 0 .2rem 0;font-weight:600;font-size:.88rem">Satış değeri, toplam (₺)</p>'
                    f'<div class="big neu" style="font-size:clamp(3rem,7vw,5.5rem)">{tl_buyuk(top_u)}</div>',
                    unsafe_allow_html=True)
        if not np.isnan(nom):
            reel_ = "reel olarak büyüdü" if nom > ufe_art else "reel olarak geriledi"
            ust = "üzerinde" if nom > ufe_art else "altında"
            cumle = (f"Satış değeri bir önceki yıla göre {'arttı' if nom > 0 else 'azaldı'}; üretici fiyatlarındaki "
                     f"artışın ({pct(ufe_art)}) {ust} kaldığı için {reel_}.")
            if not np.isnan(hacim):
                cumle += (" Miktarı izlenebilen ürünlerde artışın neredeyse tamamı fiyattan geldi."
                          if abs(hacim) < 2 else
                          f" Miktarı izlenebilen ürünlerde hacim {pct(hacim, sign=True)} değişti.")
            st.markdown(f'<p class="lead" style="margin:1rem 0">{cumle}</p>', unsafe_allow_html=True)
        n_urun = int((V1 > 0).sum())
        stats([("Satış verisi olan ürün", num(n_urun, 0), yil_u),
               ("İlk 10 ürünün payı", pct(V1.nlargest(10).sum() / top_u * 100), ""),
               ("Satış değeri, yıllık", pct(nom, sign=True), "nominal ₺"),
               ("Miktar (hacim)", pct(hacim, sign=True) if not np.isnan(hacim) else "—",
                f"satış değerinin %{num(kapsam, 0)} kadarı" if not np.isnan(kapsam) else ""),
               ("Birim fiyat", pct(fiyat_u, sign=True) if not np.isnan(fiyat_u) else "—",
                f"Yİ-ÜFE yıllık ort. {pct(ufe_art)}")])

        # 01 yurt içi pazar
        tic_yillari = set(U.ticaret["yil"].unique())
        if int(yil_u) in tic_yillari and yil_u in USD_YIL:
            section("01", "Yurt içi pazar",
                    f"{ad_u} ürünlerinde iç pazar büyüklüğü: yurt içi satış − ihracat + ithalat. "
                    "Birbirine GTİP üzerinden bağlı PRODTR kodları tek pazar olarak toplanır; (+n) birlikte sayılan ek ürün sayısıdır.")
            P1 = pazar_tablosu(U, int(yil_u), USD_YIL[yil_u])
            if int(y0) in tic_yillari and y0 in USD_YIL:
                P0 = pazar_tablosu(U, int(y0), USD_YIL[y0])
                P1["buyume"] = (P1["pazar"] / P0["pazar"].reindex(P1.index) - 1) * 100
            else:
                P1["buyume"] = np.nan
            P1["nace"] = "C" + P1["kod"].str[:2]
            Px = P1 if u_sek == "C" else P1[P1["nace"] == u_sek]
            Px = Px[Px["ticaret_var"]].dropna(subset=["pazar"])
            # ihracatı yurt içi satıştan büyük görünen gruplar eşleme tutarsızlığına işaret eder
            Px = Px[Px["X"] <= Px["satis_usd"] * 1.05]
            Px = Px.assign(ad=[kisalt(U.bilgi["ad"].get(k, k)) + (f" (+{n - 1})" if n > 1 else "")
                               for k, n in zip(Px["kod"], Px["n"])])
            buyuk = Px.nlargest(min(100, len(Px)), "pazar")
            c1_, c2_, c3_ = st.columns(3, gap="large")
            c1_.markdown(liste_html("Pazarı en büyük ürünler", [
                (r.ad, f"ithalatın payı %{num(r.ithalat_payi, 0)} · yıllık {pct(r.buyume, sign=True)}", mlr_usd(r.pazar))
                for r in Px.nlargest(8, "pazar").itertuples()]), unsafe_allow_html=True)
            c2_.markdown(liste_html("İthalata en bağımlı ürünler", [
                (r.ad, f"pazar {mlr_usd(r.pazar)}", f"%{num(min(r.ithalat_payi, 100), 0)}")
                for r in buyuk.nlargest(8, "ithalat_payi").itertuples()]), unsafe_allow_html=True)
            c3_.markdown(liste_html("Pazarı en hızlı büyüyenler ($)", [
                (r.ad, f"pazar {mlr_usd(r.pazar)} · ithalatın payı %{num(r.ithalat_payi, 0)}", pct(r.buyume, sign=True))
                for r in buyuk.dropna(subset=["buyume"]).nlargest(8, "buyume").itertuples()]), unsafe_allow_html=True)
            src(f"TÜİK sanayi ürün istatistikleri (PRODTR) ve GTİP–PRODTR eşlemesi · dış ticaret: UN Comtrade (HS6) · "
                f"TL→$ dönüşümü {yil_u} ortalama kuru ({num(USD_YIL[yil_u], 2)}) · listeler en büyük 100 pazar içinden · ihracatı satıştan büyük görünen gruplar hariç")
        else:
            st.caption("Bu yıl için dış ticaret verisi yok; iç pazar hesaplanmadı.")

        # 02 en büyük ürünler
        section("02", "En büyük ürünler", f"{yil_u} satış değerine göre ilk 15 ürün ve yıllık değişimleri.")
        ilk15 = V1.nlargest(15)
        deg_ = ((ilk15 / V0.reindex(ilk15.index) - 1) * 100)
        fu = go.Figure(go.Bar(
            x=ilk15.values[::-1] / 1e9, y=[kisalt(U.bilgi.loc[k, "ad"], 60) for k in ilk15.index[::-1]],
            orientation="h", marker_color=NAVY,
            text=[f"{num(v / 1e9, 0)} mlr ₺ · {pct(d, sign=True)}" for v, d in zip(ilk15.values[::-1], deg_.values[::-1])],
            textposition="outside", textfont=dict(size=10, color=INK), cliponaxis=False,
            customdata=[U.bilgi.loc[k, "ad"] for k in ilk15.index[::-1]],
            hovertemplate="%{customdata}<br>%{x:,.1f} mlr ₺<extra></extra>"))
        fu.update_layout(height=560, margin=dict(l=4, r=140, t=6, b=6), paper_bgcolor="rgba(0,0,0,0)",
                         plot_bgcolor="rgba(0,0,0,0)", font=dict(family="Inter", size=11, color=INK), bargap=.35)
        fu.update_xaxes(visible=False)
        st.plotly_chart(fu, width="stretch", config=CFG)

        # 03 ürün tablosu
        section("03", "Ürün tablosu")
        son10 = [c for c in U.deger.columns if c.isdigit() and int(c) > int(yil_u) - 10 and int(c) <= int(yil_u)]
        tab_ = pd.DataFrame({
            "Kod": B.index, "Ürün": B["ad"].values,
            "Satış değeri (mn ₺)": (V1 / 1e6).round(1).values,
            "Yıllık %": ((V1 / V0 - 1) * 100).round(1).values,
            "Miktar yıllık %": [((q1.get(k) / q0.get(k) - 1) * 100) if k in q1.index and q0.get(k, 0) > 0 else np.nan
                                for k in B.index],
            "Son 10 yıl": [U.deger.loc[k, son10].fillna(0).tolist() for k in B.index],
        }).dropna(subset=["Satış değeri (mn ₺)"]).sort_values("Satış değeri (mn ₺)", ascending=False)
        st.dataframe(tab_, hide_index=True, width="stretch", height=480, column_config={
            "Yıllık %": st.column_config.NumberColumn(format="%.1f"),
            "Miktar yıllık %": st.column_config.NumberColumn(format="%.1f"),
            "Satış değeri (mn ₺)": st.column_config.NumberColumn(format="%,.1f"),
            "Son 10 yıl": st.column_config.LineChartColumn("Satış değeri, son 10 yıl")})
        src("TÜİK, Sanayi Ürün İstatistikleri Veri Tabanı 2005–2025 · gizli (c) PRODTR değerleri, açıklanan PRODCOM "
            "toplamından kalan fark olarak '(gizli alt kalemler)' satırında gösterilir")

# ================================================================ KOD ANALİZİ
with tab_kod:
    if U is None:
        st.info("Ürün verisi yok. `python scripts/urunler.py` çalıştırın.", icon="ℹ️")
    else:
        st.markdown('<div class="eyebrow">Kod analizi</div><div class="hero">PRODTR ↔ GTİP</div>'
                    '<div class="sub">Eşleşen ürünün TL, dolar ve reel büyümesi; NACE sınıfı ve sektör içindeki yeri.</div>',
                    unsafe_allow_html=True)
        ornek = st.segmented_control("Örnekler", ["Transformatör", "Taşıt parçaları", "Çelik boru", "Çikolata"],
                                     key="k_ornek", label_visibility="collapsed")
        ara = st.text_input("PRODTR ya da GTİP kodu veya ürün adı", value=ornek or "",
                            key=f"k_ara_{ornek}", placeholder="ör. 27.11.41, 850421, transformatör")
        q_ = ara.strip()
        if q_:
            qd = q_.replace(".", "").replace(" ", "")
            kod_ad = U.bilgi[~U.bilgi["gizli"]][["kod", "ad"]].drop_duplicates("kod")
            m1 = kod_ad[kod_ad["kod"].str.replace(".", "", regex=False).str.startswith(qd) |
                        kod_ad["ad"].str.contains(q_, case=False, na=False, regex=False)]["kod"].tolist()
            e_ = U.eslesme
            m2 = e_[e_["gtip"].str.startswith(qd) | e_["gtip_ad"].str.contains(q_, case=False, na=False, regex=False)][
                "prodtr"].tolist()
            adaylar = list(dict.fromkeys([k for k in m1 + m2 if k in U.deger.index]))
            if not adaylar:
                st.warning("Eşleşen PRODTR kodu bulunamadı.")
            else:
                son_y = [c for c in U.deger.columns if U.deger[c].notna().any()][-1]
                adaylar.sort(key=lambda k: -(U.deger.loc[k, son_y] if pd.notna(U.deger.loc[k, son_y]) else -1))
                k_sec = st.selectbox(f"{len(adaylar)} eşleşen ürün", adaylar[:80], key="k_sec",
                                     format_func=lambda k: f"{k} · {kisalt(U.bilgi.loc[k, 'ad'], 120)}")
                bi = U.bilgi.loc[k_sec]
                seri = U.deger.loc[k_sec].dropna()
                seri.index = seri.index.astype(str)
                uf_k = ufe_yillik(bi["nace"])
                usd_s = seri / USD_YIL.reindex(seri.index)
                reel_s = seri / uf_k.reindex(seri.index) * uf_k.get(seri.index[-1], np.nan)
                gy = lambda s: (s.iloc[-1] / s.iloc[-2] - 1) * 100 if len(s.dropna()) > 1 else np.nan
                sek_v = U.deger.loc[U.bilgi.index[U.bilgi["nace"] == bi["nace"]], son_y]
                sira = int((sek_v > seri.get(son_y, 0)).sum()) + 1 if son_y in seri else None
                st.markdown(f'<p class="lead" style="margin:1rem 0"><b>{k_sec}</b> · {bi["ad"]}</p>',
                            unsafe_allow_html=True)
                stats([("Satış değeri", tl_buyuk(seri.iloc[-1]) if len(seri) else "—", seri.index[-1] if len(seri) else ""),
                       ("TL büyümesi", pct(gy(seri), sign=True), "yıllık, nominal"),
                       ("Dolar büyümesi", pct(gy(usd_s.dropna()), sign=True), "yıllık ortalama kurla"),
                       ("Reel büyüme", pct(gy(reel_s.dropna()), sign=True), "sektör Yİ-ÜFE ile arındırılmış")])
                n4 = bi["nace4"]
                stats([("NACE sınıfı", n4, kisalt(NADI_.get(n4, ""), 70)),
                       ("Sektör", bi["nace"], ADLAR.get(bi["nace"], ("",))[0]),
                       ("Sektör içindeki sırası", f"{sira}." if sira else "—", f"{int(sek_v.notna().sum())} ürün içinde"),
                       ("Sektördeki payı", pct(seri.get(son_y, np.nan) / sek_v.sum() * 100, 2), f"satış değeri, {son_y}")])
                gk = st.segmented_control("Görünüm", ["TL", "Dolar", "Reel TL"], default="TL",
                                          key="k_gor", label_visibility="collapsed")
                s_ = {"TL": seri / 1e6, "Dolar": usd_s / 1e6, "Reel TL": reel_s / 1e6}[gk]
                fk = base_fig(320)
                fk.add_bar(x=s_.index, y=s_.values, marker_color=NAVY,
                           hovertemplate="%{x}: %{y:,.1f} mn<extra></extra>")
                fk.update_xaxes(dtick=1, tickformat=None, type="category")
                fk.update_yaxes(tickformat=",.0f", ticksuffix=" mn")
                st.plotly_chart(fk, width="stretch", config=CFG)
                mq = U.miktar.loc[k_sec].dropna() if k_sec in U.miktar.index else pd.Series(dtype=float)
                if len(mq) > 1:
                    mq.index = mq.index.astype(str)
                    bf = (U.deger_prodtr.loc[k_sec].reindex(mq.index) / mq).dropna()
                    st.caption(f"Satış miktarı ({U.birim.get(k_sec, '')}): son yıl {num(mq.iloc[-1], 0)}, yıllık "
                               f"{pct(gy(mq), sign=True)} · birim fiyat yıllık {pct(gy(bf), sign=True)}")
                src("TÜİK, Sanayi Ürün İstatistikleri Veri Tabanı · reel: sektör Yİ-ÜFE yıllık ortalaması · "
                    "dolar: yıllık ortalama USD/TRY")

                # bağlı GTİP kodları
                gt = U.eslesme[U.eslesme["prodtr"] == k_sec][["gtip", "gtip_ad", "hs6"]]
                if len(gt):
                    section("", "Eşleşen GTİP kodları",
                            f"{len(gt)} GTİP kodu bu PRODTR koduna eşleniyor. Dış ticaret HS6 düzeyindedir; aynı HS6 "
                            "başka ürünlerle paylaşılıyorsa tutar o ürünleri de kapsar.")
                    tic_ = U.ticaret.pivot_table(index="hs6", columns=["akis", "yil"], values="deger_usd", aggfunc="sum")
                    for yy in sorted(U.ticaret["yil"].unique())[-1:]:
                        gt[f"İthalat {yy} (mn $)"] = (gt["hs6"].map(tic_.get(("M", yy), pd.Series(dtype=float))) / 1e6).round(1)
                        gt[f"İhracat {yy} (mn $)"] = (gt["hs6"].map(tic_.get(("X", yy), pd.Series(dtype=float))) / 1e6).round(1)
                    st.dataframe(gt.rename(columns={"gtip": "GTİP", "gtip_ad": "Tanım", "hs6": "HS6"}),
                                 hide_index=True, width="stretch")
                    src("TÜİK GTİP 2018–PRODTR 2018 eşleme tablosu · UN Comtrade (HS6)")

# ================================================================ VERİ
with tab_veri:
    section("", "Veri ve indirme", "Panodaki tüm seriler. Tablolar en yeni dönem üstte olacak şekilde sıralıdır.")
    makro = M.copy()
    makro["usdtry"] = USD
    makro.index = makro.index.astype(str)
    st.markdown("**Makro göstergeler (düzey)**")
    st.dataframe(makro.iloc[::-1], width="stretch", height=320)
    sek = S.rename(columns={k: f"{k} {v[1]}" for k, v in SEKTORLER.items()})
    sek.index = sek.index.astype(str)
    st.markdown("**Sektör üretim endeksleri (2021=100)**")
    st.dataframe(sek.iloc[::-1], width="stretch", height=320)

    for ad_, df_ in TS.items():
        d_ = df_.copy(); d_.index = d_.index.astype(str)
        st.markdown(f"**TÜİK · {T.aciklama[ad_]}**")
        st.dataframe(d_.iloc[::-1], width="stretch", height=240)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf) as xw:
        makro.to_excel(xw, sheet_name="makro")
        sek.to_excel(xw, sheet_name="sektor_uretim")
        for ad_, df_ in TS.items():
            d_ = df_.copy(); d_.index = d_.index.astype(str)
            d_.to_excel(xw, sheet_name=f"tuik_{ad_}"[:31])
    c1, c2, c3 = st.columns(3)
    c1.download_button("Makro (CSV)", makro.to_csv().encode("utf-8-sig"), "makro.csv", "text/csv")
    c2.download_button("Sektörler (CSV)", sek.to_csv().encode("utf-8-sig"), "sektor_uretim.csv", "text/csv")
    c3.download_button("Tümü (Excel)", buf.getvalue(), "sektor_atlasi.xlsx",
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    src("TÜİK ve TCMB, EVDS üzerinden · seri kodları `data.py` içinde")
