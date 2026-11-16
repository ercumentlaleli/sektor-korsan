"""Sektör veri atlası — TÜİK/TCMB verileriyle imalat sanayii panosu."""
from __future__ import annotations

import io
import re

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from data import (SEKTORLER, ay, ay_kisa, guncelleme_bilgisi, load, load_geojson, load_iso500, load_kredi, load_urunler, pazar_tablosu, load_nace34, load_tuik, num, pct, son_gecerli,
                  veri_surumu, yoy)

st.set_page_config(page_title="Sektör veri atlası", page_icon="📊", layout="wide",
                   initial_sidebar_state="collapsed")

# ---------------------------------------------------------------- tema
# Palet ve yazı tipi: 'İmalat Sanayii Görünüm Raporu' sunumunun teması (Calibri; lacivert/mavi, beyaz zemin)
INK, NAVY, RED, TEAL, OCHRE = "#262626", "#203764", "#C0504D", "#305496", "#8EA9DB"
MUTED, LINE, BG, CARD = "#595959", "#D9D9D9", "#FFFFFF", "#F2F2F2"
BLUE, DARK, PALE, CARD2, NOTR = "#305496", "#222A35", "#D9E1F2", "#E7E6E6", "#F2F2F2"
FONT = "Calibri, Carlito, 'Segoe UI', Arial, sans-serif"

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Carlito:ital,wght@0,400;0,700;1,400&display=swap');
/* Tipografi ve renkler: Kalkınma Yatırım Bankası 'İmalat Sanayii Görünüm Raporu' sunum stiline göre
   (Calibri; başlık 20pt, metin 12pt, not 8pt, kaynak 7pt; lacivert/mavi palet, beyaz zemin, gri paneller) */
html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {{ background:{BG}; }}
[data-testid="stAppViewContainer"] *:not([data-testid="stIconMaterial"]):not([class*="material"]) {{ font-family: {FONT}; }}
[data-testid="stAppViewContainer"] {{ color:{INK}; font-size:16px; }}
.block-container {{ max-width: 1180px; padding-top: 3.2rem; }}
h1,h2,h3,.serif {{ color:{INK}; font-weight:700; }}
.brand {{ font-size: 1.5rem; font-weight:700; color:{NAVY}; margin:0 0 .5rem 0; padding-bottom:.35rem;
          border-bottom:2px solid {NAVY}; }}
.eyebrow {{ color:{BLUE}; letter-spacing:.08em; font-size:.75rem; text-transform:uppercase; font-weight:700; }}
.hero {{ color:{INK}; font-size:clamp(1.6rem,2.6vw,1.75rem); line-height:1.15; margin:.35rem 0 .25rem 0; font-weight:700; }}
.sub {{ color:{MUTED}; font-size:.86rem; }}
.big {{ font-size:clamp(2.6rem,5vw,3.4rem); line-height:1; font-weight:700; }}
.big .p {{ font-size:.55em; vertical-align:.3em; margin-right:.05em; }}
.neg {{ color:{RED}; }} .pos {{ color:{TEAL}; }} .neu {{ color:{NAVY}; }}
.lead {{ font-size:1rem; line-height:1.55; color:{INK}; }}
.kpi {{ background:{CARD}; border-radius:8px; border-top:3px solid transparent; padding:.7rem .7rem .55rem .7rem; height:100%; }}
.kpi.sel {{ background:{PALE}; border-top:3px solid {NAVY}; }}
.kpi .l {{ font-size:.8rem; color:{MUTED}; font-weight:700; }}
.kpi .v {{ font-size:1.55rem; font-weight:700; margin:.2rem 0 .1rem 0; }}
.kpi .v .p {{ font-size:.65em; }}
.kpi .n {{ font-size:.72rem; color:{MUTED}; }}
.secno, .sbas {{ display:flex; align-items:center; gap:.6rem; background:{DARK}; color:#fff; font-weight:700; font-size:1rem;
          border-radius:7px; padding:.42rem .9rem .42rem .5rem; margin-top:2.2rem; margin-bottom:.6rem;
          box-shadow:0 1px 3px rgba(0,0,0,.18); }}
.secno .no, .sbas .no {{ display:inline-flex; align-items:center; justify-content:center; min-width:1.55rem; height:1.55rem;
              border-radius:50%; border:1.5px solid #fff; font-size:.78rem; }}
.secd {{ color:{INK}; font-size:1rem; line-height:1.55; margin-bottom:.9rem; max-width:900px; }}
.stat .l {{ font-size:.8rem; color:{MUTED}; font-weight:700; }}
.stat .v {{ font-size:1.45rem; font-weight:700; color:{NAVY}; }}
.stat .n {{ font-size:.72rem; color:{MUTED}; }}
.src {{ font-size:.66rem; color:{MUTED}; font-style:italic; margin-top:.2rem; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(200px,1fr)); gap:6px; }}
.tile {{ border-radius:7px; padding:.65rem .8rem; min-height:98px; }}
.tile .c {{ font-size:.72rem; opacity:.8; font-weight:700; }}
.tile .t {{ font-size:.92rem; margin:.3rem 0 .25rem 0; }}
.tile .v {{ font-size:1.35rem; font-weight:700; }}
.tile.tot {{ outline:2px solid {NAVY}; outline-offset:-2px; }}
.legend {{ display:flex; align-items:center; gap:8px; font-size:.74rem; color:{MUTED}; justify-content:flex-end; white-space:nowrap; }}
.legend .bar {{ width:160px; height:6px; border-radius:3px; background:linear-gradient(90deg,{RED},{NOTR},{TEAL}); }}
.stTabs [data-baseweb="tab-list"] {{ gap:0; border:1px solid {LINE}; border-radius:6px; width:fit-content; overflow:hidden; }}
.stTabs [data-baseweb="tab"] {{ padding:.4rem 1rem; border-right:1px solid {LINE}; height:auto; font-weight:700; }}
.stTabs [aria-selected="true"] {{ background:{NAVY}; }}
.stTabs [aria-selected="true"] p {{ color:#fff !important; }}
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] {{ display:none; }}
[data-testid="stToolbar"] {{ display:none; }}
[data-testid="stDataFrame"] {{ border-radius:6px; }}
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
[class*="st-key-kpi_"]:hover .kpi {{ background:{CARD2}; }}
.kpi {{ transition:background .15s; }}
div[data-testid="stSegmentedControl"] button {{ font-size:.82rem; }}
[class*="st-key-slayt_"] .sbas {{ margin-top:0; }}
.sno {{ display:inline-flex; align-items:center; justify-content:center; min-width:1.35rem; height:1.35rem;
        border-radius:50%; background:{DARK}; color:#fff; font-size:.72rem; letter-spacing:0; margin-right:.5rem; }}
hr.slayt-ayrac {{ border:none; border-top:1.5px solid {LINE}; margin:2.4rem 0 1.6rem 0; }}
.slayt-no {{ font-size:.7rem; color:{MUTED}; text-align:right; letter-spacing:.06em; }}
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
    return mix(NOTR, RED, -t * .55) if t < 0 else mix(NOTR, TEAL, t * .55)


# ---- sunum: her sekmenin üstünde, ekrandaki sekmeyi slaytlara çeviren PPTX düğmesi (bkz. sunum_js.py)
def senkron(key: str, secenekler: list, cevir=lambda c: c) -> None:
    """Atlas'ta seçilen sektör değişince, sekmenin sektör seçimini (key) ona eşitler.

    Kullanıcı sekmede sonradan elle seçim yaparsa, Atlas'ta yeni bir seçim yapılana kadar korunur.
    """
    hedef = st.session_state.get("atlas_sektor", "C")
    if st.session_state.get(f"_senk_{key}") == hedef:
        return
    st.session_state[f"_senk_{key}"] = hedef
    deger = cevir(hedef)
    if deger in secenekler:
        st.session_state[key] = deger
    elif hedef == "C" and secenekler and key in st.session_state:
        st.session_state[key] = secenekler[0]


def sunum_basla(anahtar: str):
    """Sekmenin başında çağrılır; indirme düğmesi için üstte bir alan döndürür."""
    return st.container()


def sunum_dugme(alan, anahtar: str, sekme_adi: str, sektor_adi: str | None = None, hepsi: bool = False) -> None:
    """Sekmenin sonunda çağrılır; üst alana, ekrandaki sekmeyi slaytlara çeviren PPTX düğmesini koyar."""
    from sunum_js import sunum_dugmesi
    baslik = sekme_adi + (f" · {sektor_adi}" if sektor_adi else "")
    dosya = re.sub(r"[^A-Za-z0-9]+", "_", trk(baslik).translate(str.maketrans("çğıöşü", "cgiosu"))).strip("_")
    with alan:
        if hepsi:  # Atlas: bu sekme + seçili sektörün tüm sekmeleri tek sunumda
            from sunum_js import tum_sekmeler_dugmesi
            _, orta_, sag_ = st.columns([3, 1.1, 1.1])
            with orta_:
                sunum_dugmesi(f"{dosya}.pptx")
            with sag_:
                ad_ = sektor_adi or "İmalat sanayii"
                d2 = re.sub(r"[^A-Za-z0-9]+", "_", trk("Sektor atlasi " + ad_).translate(
                    str.maketrans("çğıöşü", "cgiosu"))).strip("_")
                tum_sekmeler_dugmesi(f"{d2}.pptx", ad_)
        else:
            _, sag_ = st.columns([4, 1])
            with sag_:
                sunum_dugmesi(f"{dosya}.pptx")


def grafik(fig, **kw) -> None:
    st.plotly_chart(fig, **kw)


def section(no: str, title: str, desc: str = "") -> None:
    rozet = f'<span class="no">{int(no)}</span>' if str(no).strip().isdigit() else ""
    st.markdown(f'<div class="secno">{rozet}<span>{title}</span></div>'
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
                    plot_bgcolor="rgba(0,0,0,0)", font=dict(family=FONT, size=11, color=MUTED),
                    showlegend=False, hovermode="x unified",
                    hoverlabel=dict(bgcolor="#FFFFFF", bordercolor=LINE, font_color=INK))
    f.update_xaxes(showgrid=False, linecolor=LINE, ticks="", dtick="M12", tickformat="%Y")
    f.update_yaxes(gridcolor="#E7E6E6", zeroline=True, zerolinecolor="#A6A6A6", side="right",
                   ticksuffix="", tickformat=",.0f")
    return f


def ts(s: pd.Series) -> pd.Series:
    s = s.dropna()
    return pd.Series(s.values, index=s.index.to_timestamp())


IMALAT_RENK = "#7F7F7F"  # karşılaştırma çizgisi (imalat sanayii toplamı)


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
                      fillcolor="rgba(32,55,100,.08)",
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


def trk(t: str) -> str:
    """Türkçe küçük harf: İ -> i, I -> ı (str.lower 'İ' harfini bozuk 'i̇' yapar)."""
    return str(t).replace("İ", "i").replace("I", "ı").lower()


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
                     font=dict(family=FONT, size=11, color=INK), bargap=.38,
                     hoverlabel=dict(bgcolor="#FFFFFF"))
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
(tab_atlas, tab_uretim, tab_ist, tab_tcmb, tab_haber, tab_urun, tab_nace, tab_firma, tab_kod, tab_sunum,
 tab_veri) = st.tabs(["Atlas", "Üretim ve fiyat", "İstihdam ve ciro", "TCMB", "Haber", "Ürünler", "NACE 4'lü",
                      "Firmalar", "Kod analizi", "Sunum", "Veri"])

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
                            seviye=False, lim=8, merkez=None, tutar=TS["ucretli_calisan"],
                            tutar_fmt=lambda x: f"{num(x, 0)} kişi", tutar_etiket="Çalışan sayısı",
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


def tutar_txt(k: str, x: float) -> str:
    """Kartlardaki tutar satırı: dış ticarette mn $, ücretli çalışanda kişi sayısı."""
    return ATLAS[k].get("tutar_fmt", mn_usd)(x)


def kpi_kart(k: str, ser: pd.Series, kod: str, sec: bool) -> str:
    """Atlas KPI kartının HTML'i (Atlas şeridi ve Sunum slaytı ortak kullanır)."""
    g = ATLAS[k]
    p_k, last = son_gecerli(ser)
    color = TEAL if (g["seviye"] or last >= 0) else RED
    vcls = "neg" if color == RED else "pos"
    k_tut = atlas_tutar(k, kod, p_k)
    not_ = f"<b>{tutar_txt(k, k_tut)}</b><br>{ay(p_k)}" if k_tut is not None and not np.isnan(k_tut) else ay(p_k)
    return (f'<div class="kpi{" sel" if sec else ""}"><div class="l">{g["kart"]}</div>'
            f'<div class="v {vcls}">{kpi_val(last)}</div>{sparkline(ser, color)}'
            f'<div class="n">{not_}</div></div>')


with tab_atlas:
    _ust = sunum_basla("atlas")
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
        boy = "" if len(s_ad) < 22 else ' style="font-size:1.5rem"'
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
            onceki = (f" · bir yıl önce {tutar_txt(secili, a_tut0)}"
                      if a_tut0 is not None and not np.isnan(a_tut0) else "")
            st.markdown(f'<div style="margin-top:.5rem;font-size:.95rem">{A.get("tutar_etiket", "Son 12 ay toplamı")} '
                        f'<b style="font-weight:700;font-size:1.25rem;color:{NAVY}">{tutar_txt(secili, a_tut)}</b>'
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
        with c.container(key=f"kpi_{k}"):
            st.markdown(kpi_kart(k, ser, sek_kod, k == secili), unsafe_allow_html=True)
            st.button(ATLAS[k]["kart"], key=f"kpib_{k}", on_click=_atlas_sec, args=(k,))

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
                t_ek = (f'<div class="n" style="font-size:.74rem;opacity:.75">{tutar_txt(secili, t_tut)}</div>'
                        if t_tut is not None and not np.isnan(t_tut) else "")
                with c.container(key=f"tile_{code}"):
                    st.markdown(f'<div class="tile{secik}" style="background:{div_color(val - merkez, A["lim"])}">'
                                f'<div class="c">{etiket}</div><div class="t">{ad_}</div>'
                                f'<div class="v">{fmt(val)}</div>{t_ek}</div>', unsafe_allow_html=True)
                    st.button(ad_, key=f"tileb_{code}", on_click=_atlas_sektor, args=(code,))
        src(A["kaynak"])
    sunum_dugme(_ust, "atlas", "Atlas", s_ad if sek_kod != "C" else "İmalat sanayii", hepsi=True)

# ================================================================ ÜRETİM VE FİYAT
with tab_uretim:
    _ust = sunum_basla("uretim")
    secenek = ["C · İmalat sanayii (toplam)"] + [f"{k} · {v[0]}" for k, v in SEKTORLER.items()]
    c1, c2 = st.columns([3, 1])
    senkron("uretim_sektor", secenek, lambda c: next((o for o in secenek if o.startswith(c + " ·")), None))
    secim = c1.selectbox("Sektör", secenek, index=0, key="uretim_sektor")
    kod = secim.split(" · ")[0]
    ad = "İmalat sanayii" if kod == "C" else SEKTORLER[kod][0]
    endeks = sue if kod == "C" else S[kod]
    ey = yoy(endeks)
    pe, ve = son_gecerli(ey)

    hl, hr = st.columns([1, 1.6], gap="large")
    with hl:
        _bas = ad if len(ad) < 28 else SEKTORLER[kod][1]
        _boy = "" if len(_bas) < 16 else ' style="font-size:1.5rem"'
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
            f"{ay(pe)} itibarıyla imalat sanayiinde üretim geçen yılın aynı ayına göre "
            f"{pct(abs(ve))} {yonfiil}." if kod == "C" else
            f"{ay(pe)} itibarıyla {trk(ad)} sektöründe üretim geçen yılın aynı ayına göre {pct(abs(ve))} {yonfiil}.")
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
        f = line_chart([("Yıllık %", ey, NAVY), ("12 ay ortalama", ort12, OCHRE)]
                       + ([("İmalat sanayii, yıllık %", sue_y, IMALAT_RENK)] if karsi else []))
    grafik(f, width="stretch", config=CFG)
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
            grafik(hbar(son_sek, TEAL, RED, kod), width="stretch", config=CFG)
        with br:
            if "yiufe" in TS:
                uf = TS["yiufe"].drop(columns="C", errors="ignore").apply(yoy)
                uf_p = uf.dropna(how="all").index[-1]
                st.markdown(f'<div class="eyebrow" style="margin:.4rem 0">Üretici fiyatları, yıllık · {ay(uf_p)}</div>',
                            unsafe_allow_html=True)
                grafik(hbar(uf.loc[uf_p], OCHRE, TEAL, kod, "Yİ-ÜFE yıllık"), width="stretch", config=CFG)
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
            customdata=z, colorscale=[[0, RED], [.5, NOTR], [1, TEAL]], zmid=0, zmin=-30, zmax=30,
            xgap=2, ygap=2, hovertemplate="%{y} · %{x}<br>%{customdata:.1f}%<extra></extra>",
            colorbar=dict(thickness=8, len=.8, ticksuffix="%", outlinewidth=0)))
        fh.update_layout(height=640, margin=dict(l=4, r=4, t=6, b=6), paper_bgcolor="rgba(0,0,0,0)",
                         plot_bgcolor="rgba(0,0,0,0)", font=dict(family=FONT, size=10.5, color=INK))
        fh.update_yaxes(autorange="reversed", ticks="")
        fh.update_xaxes(ticks="", tickangle=0, nticks=8)
        grafik(fh, width="stretch", config=CFG)
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
                                  font=dict(family=FONT, size=12, color=INK), bargap=.55,
                                  hoverlabel=dict(bgcolor="#FFFFFF"))
                fb_.update_xaxes(visible=False, range=[lo_ - (pad_ * 1.6 if lo_ < 0 else pad_ * .15), hi_ + pad_])
                fb_.update_yaxes(showgrid=False, ticks="")
                return fb_

            bl, br = st.columns(2, gap="large")
            with bl:
                st.markdown(f'<div class="eyebrow" style="margin:.4rem 0">Üretim, yıllık değişim · {ay(a_p)}</div>',
                            unsafe_allow_html=True)
                alt_s = {c: (f"satışların %{num(pay.get(c), 0)} · " if c in pay.index else "")
                         + f"12 ay ort. {pct(a_12.get(c, np.nan), sign=True)}" for c in a_son.index}
                grafik(alt_bar(a_son, alt_s, TEAL, RED, True), width="stretch", config=CFG)
            with br:
                if len(uf_son):
                    st.markdown(f'<div class="eyebrow" style="margin:.4rem 0">Üretici fiyatları, yıllık · '
                                f'{ay(uf_p4)}</div>', unsafe_allow_html=True)
                    alt_f = {c: f"yurt dışı satış fiyatı {pct(yd_son[c])}" for c in uf_son.index if c in yd_son.index}
                    grafik(alt_bar(uf_son, alt_f, OCHRE, TEAL, False), width="stretch", config=CFG)
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
                customdata=z4, colorscale=[[0, RED], [.5, NOTR], [1, TEAL]], zmid=0, zmin=-20, zmax=20,
                xgap=2, ygap=2, hovertemplate="%{y} · %{x}<br>%{customdata:.1f}%<extra></extra>",
                colorbar=dict(thickness=8, len=.8, ticksuffix="%", outlinewidth=0)))
            fh4.update_layout(height=max(240, 60 * len(order4) + 60), margin=dict(l=4, r=4, t=6, b=6),
                              paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                              font=dict(family=FONT, size=11, color=INK))
            fh4.update_yaxes(autorange="reversed", ticks="")
            fh4.update_xaxes(ticks="", tickangle=0, nticks=8)
            grafik(fh4, width="stretch", config=CFG)
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
    yer = "imalat sanayiinde" if kod == "C" else f"{trk(ad)} sektöründe"
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
                        ("YD-ÜFE", ydufe_y, "#7F7F7F")]
                       + ([("İmalat sanayii Yİ-ÜFE", yoy(M["yiufe_imalat"]), IMALAT_RENK)] if karsi else []))
    grafik(f, width="stretch", config=CFG)
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
        grafik(f, width="stretch", config=CFG)
        exa = TS["ihracat"].drop(columns="C", errors="ignore")
        exa12 = exa.rolling(12).sum()
        g12 = yoy(exa12).iloc[-1]
        pay = (exa12.iloc[-1] / TS["ihracat"]["C"].rolling(12).sum().iloc[-1] * 100)
        c_l, c_r = st.columns(2, gap="large")
        with c_l:
            st.markdown(f'<div class="eyebrow" style="margin:.4rem 0">İhracat, son 12 ay, yıllık · {ay(pdt)}</div>',
                        unsafe_allow_html=True)
            grafik(hbar(g12, TEAL, RED, kod, "12 ay yıllık"), width="stretch", config=CFG)
        with c_r:
            st.markdown(f'<div class="eyebrow" style="margin:.4rem 0">İmalat ihracatındaki pay · son 12 ay</div>',
                        unsafe_allow_html=True)
            fp = hbar(pay, NAVY, NAVY, kod, "Pay")
            fp.update_traces(text=[pct(v) for v in pay.dropna().sort_values().values])
            grafik(fp, width="stretch", config=CFG)
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
                             font=dict(family=FONT, size=12, color=INK), bargap=.5)
            fy.update_xaxes(visible=False, range=[lo_ - (pad_ if lo_ < 0 else 0), hi_ + pad_])
            fy.update_yaxes(showgrid=False, ticks="", autorange="reversed")  # en eski yıl üstte
            return fy

        st.markdown('<p style="font-weight:600;margin-top:1.4rem">Yıllık değişim: yıl, yılbaşından bu yana, son ay</p>',
                    unsafe_allow_html=True)
        y_l, y_r = st.columns(2, gap="large")
        with y_l:
            st.markdown('<div class="eyebrow" style="margin:.4rem 0">İhracat ($)</div>', unsafe_allow_html=True)
            grafik(degisim_bar(yillik_degisim(ex), TEAL), width="stretch", config=CFG)
        with y_r:
            st.markdown('<div class="eyebrow" style="margin:.4rem 0">İthalat ($)</div>', unsafe_allow_html=True)
            grafik(degisim_bar(yillik_degisim(im), OCHRE), width="stretch", config=CFG)
        src("TÜİK, ekonomik faaliyetlere göre dış ticaret (ISIC Rev.4), TCMB EVDS üzerinden · yıllık toplamlar, "
            "geçen yılın aynı dönemine göre")
    sunum_dugme(_ust, "uretim", "Üretim ve fiyat", ad)

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
        f = line_chart([("Yıllık %", sy["2015":], NAVY), ("12 ay ortalama", o12["2015":], OCHRE)])
    grafik(f, width="stretch", config=CFG)
    src(kaynak)


with tab_ist:
    _ust = sunum_basla("ist")
    gerekli = {"ucretli_calisan", "ciro"}
    if not gerekli <= set(TS):
        st.info("Bu sekme TÜİK SDMX verisi gerektiriyor. `TUIK_API_KEY` tanımlayıp "
                "`python scripts/guncelle.py --tuik` çalıştırın.", icon="ℹ️")
    else:
        ortak = [c for c in TS["ciro"].columns if c in TS["ucretli_calisan"].columns]
        senkron("ist_sektor", ortak)
        sec = st.selectbox("Sektör", ortak, format_func=lambda c: "C · İmalat sanayii (toplam)" if c == "C"
                           else f"{c} · {ADLAR.get(c, (c,))[0]}", key="ist_sektor")
        ad_i = "İmalat sanayii" if sec == "C" else ADLAR.get(sec, (sec, sec))[0]
        yer = "imalat sanayiinde" if sec == "C" else f"{trk(ad_i)} sektöründe"
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
            grafik(f, width="stretch", config=CFG)
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
            grafik(hbar(uc_all.loc[pu], TEAL, RED, sec), width="stretch", config=CFG)
        with c_r:
            pc = ci_all.dropna(how="all").index[-1]
            st.markdown(f'<div class="eyebrow" style="margin:.4rem 0">Ciro (nominal), yıllık · {ay(pc)}</div>',
                        unsafe_allow_html=True)
            grafik(hbar(ci_all.loc[pc], NAVY, RED, sec, "Ciro yıllık"), width="stretch", config=CFG)
    sunum_dugme(_ust, "ist", "İstihdam ve ciro", globals().get("ad_i"))

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
                     font=dict(family=FONT, size=11, color=MUTED),
                     legend=dict(orientation="h", y=1.02, yanchor="bottom", x=0, font=dict(color=INK, size=11)),
                     showlegend=len(seriler) > 1)
    fg.update_xaxes(type="category", showgrid=False, linecolor=LINE)
    fg.update_yaxes(gridcolor="#E7E6E6", tickprefix="%", zeroline=True, zerolinecolor="#A6A6A6")
    return fg


with tab_tcmb:
    _ust = sunum_basla("tcmb")
    kko_s = TS.get("kko", pd.DataFrame())
    t_ops = ["C"] + [k for k in ADLAR if k in kko_s.columns or k in set(KR["sektor"])]
    t1, t2 = st.columns([4, 1])
    senkron("t_sektor", t_ops)
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
    _boy = "" if len(t_kisa) < 16 else ' style="font-size:1.5rem"'
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
                f"{ay(p_kt)} itibarıyla {'imalat sanayii' if t_kod == 'C' else trk(t_ad) + ' sektörü'}nde kapasite "
                f"kullanım oranı {pct(v_kt)}." + (f" İmalat sanayii ortalaması {pct(kko.get(p_kt, v_kko))}." if karsi_t else ""))
        stats([("Bir yıl önce", pct(kko_t.get(p_kt - 12, np.nan)), ay(p_kt - 12)),
               ("Son 12 ay ortalaması", pct(k12.dropna().iloc[-1]), ""),
               ("Son 3 ay, önceki 3 aya göre",
                f"{num(kko_t.dropna().iloc[-3:].mean() - kko_t.dropna().iloc[-6:-3].mean(), 1)} puan", "ortalamalar")]
              + ([("İmalat sanayii", pct(kko.get(p_kt, v_kko)), ay(p_kt))] if karsi_t else []))
        f = line_chart([("Aylık", kko_t[donem], NAVY), ("12 aylık ortalama", k12[donem], OCHRE)]
                       + ([("İmalat sanayii", kko[donem], IMALAT_RENK)] if karsi_t else []))
        f.update_yaxes(tickformat=".0f")
        grafik(f, width="stretch", config=CFG)
        src("TCMB EVDS, imalat sanayi kapasite kullanım oranı" + (" · kesikli çizgi: imalat sanayii" if karsi_t else ""))

    section("02", "Reel efektif döviz kuru",
            f"{ay(p_rk)} itibarıyla Yİ-ÜFE bazlı reel efektif kur endeksi {num(v_rk)}; bir yıl öncesine göre "
            f"{pct(abs(rk_y.dropna().iloc[-1]))} {'yükseldi' if rk_y.dropna().iloc[-1] > 0 else 'düştü'}.")
    f = line_chart([("Reel efektif kur", rek[donem], NAVY)], pctaxis=False)
    f.add_hline(y=100, line=dict(color=LINE, dash="dot"))
    grafik(f, width="stretch", config=CFG)
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
    grafik(f, width="stretch", config=CFG)
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
            ac = (f"{kr_son} yıl sonunda imalat sanayii kredilerinin %{num(n_s / n_c * 100)}'si {trk(t_ad)} "
                  f"sektörüne gitti. Sektörün nakdi kredisi {kr_son} yılında {pct(b_s)} "
                  f"{'arttı' if b_s > 0 else 'azaldı'} ve {tut} oldu. İmalat sanayii kredisi aynı dönemde "
                  f"{pct(b_c)} {'arttı' if b_c > 0 else 'azaldı'}. Aralık TÜFE artışı {pct(tufe_dec)} iken reel "
                  f"değişim {pct(reel_k, sign=True)}. {ort_y[0]}-{ort_y[-1]} ortalamasında tahsili gecikmiş alacak "
                  f"oranı {trk(t_ad)} sektöründe {pct(o_s_ort)}, imalat sanayiinde {pct(o_c_ort)}. "
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
                sr.append(("İmalat sanayii", [kredi_buyume("C", y) for y in yb], OCHRE))
            grafik(grup_bar(yb, sr), width="stretch", config=CFG)
        with k_r:
            st.markdown('<p style="font-weight:600;margin:.8rem 0 0 0">Tahsili gecikmiş alacak oranı, %</p>',
                        unsafe_allow_html=True)
            sr = [(t_ad if karsi_t else "İmalat sanayii", [kredi_oran(t_kod, y) for y in yillar_k], NAVY)]
            if karsi_t:
                sr.append(("İmalat sanayii", [kredi_oran("C", y) for y in yillar_k], OCHRE))
            grafik(grup_bar(yillar_k, sr), width="stretch", config=CFG)
        if not karsi_t:
            ks = pd.Series({k: kredi_deger(k, kr_son) for k in ADLAR}).dropna()
            ko = pd.Series({k: kredi_oran(k, kr_son) for k in ADLAR}).dropna()
            s_l, s_r = st.columns(2, gap="large")
            with s_l:
                st.markdown(f'<div class="eyebrow" style="margin:.6rem 0">İmalat kredileri içindeki pay · {kr_son}</div>',
                            unsafe_allow_html=True)
                fp = hbar(ks / n_c * 100, NAVY, NAVY, None, "Pay")
                fp.update_traces(text=[pct(v) for v in (ks / n_c * 100).sort_values().values])
                grafik(fp, width="stretch", config=CFG)
            with s_r:
                st.markdown(f'<div class="eyebrow" style="margin:.6rem 0">Tahsili gecikmiş alacak oranı · {kr_son}</div>',
                            unsafe_allow_html=True)
                fo = hbar(ko, RED, RED, None, "Oran")
                fo.update_traces(text=[pct(v) for v in ko.sort_values().values])
                grafik(fo, width="stretch", config=CFG)
        src("TCMB, sektör bilançoları (yıl sonu nakdi kredi: TL + YP; tahsili gecikmiş: tasfiye olunacak krediler) · "
            "2023 seri değişikliği nedeniyle 2023 büyümesi gösterilmiyor · grafikler seçili dönemin son 6 yılı"
            + (f" · $ dönüşümü Aralık {kr_son} ortalama kuruyla" if para == "$" else ""))
    sunum_dugme(_ust, "tcmb", "TCMB göstergeleri", t_ad)

# ================================================================ HABER
def haber_kartlari(liste: list[dict], numarali: bool = False, basla: int = 1) -> str:
    import html as _h
    kart = []
    for i, h in enumerate(liste, start=basla):
        t = h["tarih"].tz_convert("Europe/Istanbul") if hasattr(h["tarih"], "tz_convert") else h["tarih"]
        tstr = f"{t.day} {AYLAR_KISA_[t.month - 1]} {t.year}" if t else ""
        no = (f'<span style="font-weight:700;color:{RED};font-size:.8rem;'
              f'min-width:1.8rem;display:inline-block">{i:02d}</span>' if numarali else "")
        kart.append(f'<div style="border-top:1px solid {LINE};padding:.7rem 0;display:flex;gap:.4rem">{no}<div>'
                    f'<div class="sub" style="font-size:.74rem">{_h.escape(h["kaynak"])} · {tstr}</div>'
                    f'<a href="{_h.escape(h["link"] or "#")}" target="_blank" '
                    f'style="font-weight:700;font-size:1.08rem;color:{INK};text-decoration:none">'
                    f'{_h.escape(h["baslik"])}</a></div></div>')
    return "".join(kart)


with tab_haber:
    _ust = sunum_basla("haber")
    import html as _html
    from data import HABER_EN, HABER_SORGU, haberler, ilk_terim
    st.markdown('<div class="eyebrow">Haber</div><div class="hero">Sektör gündemi</div>'
                '<div class="sub">Google Haberler · son 3 ay · saatlik yenilenir</div>', unsafe_allow_html=True)
    h1, h2 = st.columns([3, 1])
    senkron("h_sektor", list(HABER_SORGU))
    h_sec = h1.selectbox("Sektör", list(HABER_SORGU), key="h_sektor",
                         format_func=lambda c: "C · İmalat sanayii (toplam)" if c == "C" else f"{c} · {ADLAR[c][0]}")
    ek = h2.text_input("Ek arama terimi", key="h_ek", placeholder="ör. ihracat")
    ek_ = f" {ek.strip()}" if ek.strip() else ""
    sorgu = HABER_SORGU[h_sec] + ek_

    # 01 öne çıkan 20 haber (son 90 gün)
    liste = haberler(sorgu, gun=90, adet=20)
    section("01", "Son 3 ayın öne çıkan 20 haberi",
            "Haber sitelerinin okunma sayıları açık değil; sıralama Google Haberler'in son 90 gündeki öne çıkarma "
            "sırasıdır (ilgi ve yaygınlık). Aynı haberin farklı sitelerdeki kopyaları tek sayılır.")
    if not liste:
        st.info("Haber bulunamadı ya da haber kaynağına şu an erişilemedi. Birkaç dakika sonra tekrar deneyin.", icon="ℹ️")
    else:
        kaynaklar = pd.Series([h["kaynak"] for h in liste]).value_counts()
        st.markdown(f'<div class="sub" style="margin-bottom:.4rem">En sık kaynaklar: '
                    + ", ".join(f"{_html.escape(k)} ({v})" for k, v in kaynaklar.head(4).items()) + "</div>",
                    unsafe_allow_html=True)
        sol, sag = st.columns(2, gap="large")
        sol.markdown(haber_kartlari(liste[:10], numarali=True), unsafe_allow_html=True)
        sag.markdown(haber_kartlari(liste[10:20], numarali=True, basla=11), unsafe_allow_html=True)
    src(f"Google Haberler RSS · arama: {_html.escape(sorgu)}")

    # 02 raporlar
    section("02", "Sektör raporları",
            "Son 3 ayda sektörle ilgili yayımlanan raporlar ve araştırmalar: yurt içinde Türkçe, yurt dışında İngilizce "
            "haber kaynaklarında başlığında rapor, araştırma, anket, endeks gibi ifadeler geçen içerikler, en yeni üstte.")
    RAPOR_TR = ("rapor", "araştırma", "anket", "endeks", "analiz", "görünüm", "değerlendirme", "çalışma")
    RAPOR_EN = ("report", "study", "outlook", "survey", "index", "analysis", "forecast", "market size", "review")

    def rapor_sec(liste_: list[dict], kelimeler: tuple) -> list[dict]:
        return [h for h in liste_ if any(k in trk(h["baslik"]) for k in kelimeler)]

    ilk_ = ilk_terim(HABER_SORGU[h_sec])
    r_tr = rapor_sec(haberler(f"{ilk_} rapor{ek_}", gun=90, adet=60)
                     + haberler(f"{ilk_} araştırması{ek_}", gun=90, adet=40), RAPOR_TR)
    r_tr = sorted({h["baslik"]: h for h in r_tr}.values(),
                  key=lambda x: x["tarih"] or pd.Timestamp(0, tz="UTC"), reverse=True)[:10]
    r_en = rapor_sec(haberler(f'"{HABER_EN[h_sec]}" report{ek_}', gun=90, adet=60, dil="en"), RAPOR_EN)
    r_en = sorted(r_en, key=lambda x: x["tarih"] or pd.Timestamp(0, tz="UTC"), reverse=True)[:10]
    rl, rr = st.columns(2, gap="large")
    with rl:
        st.markdown('<div class="eyebrow" style="margin:.4rem 0">Yurt içi</div>', unsafe_allow_html=True)
        st.markdown(haber_kartlari(r_tr) if r_tr else '<div class="sub">Rapor bulunamadı.</div>', unsafe_allow_html=True)
    with rr:
        st.markdown('<div class="eyebrow" style="margin:.4rem 0">Yurt dışı</div>', unsafe_allow_html=True)
        st.markdown(haber_kartlari(r_en) if r_en else '<div class="sub">Rapor bulunamadı.</div>', unsafe_allow_html=True)
    src(f"Google Haberler RSS · yurt içi: {_html.escape(ilk_terim(HABER_SORGU[h_sec]))} rapor · "
        f"yurt dışı: \"{_html.escape(HABER_EN[h_sec])}\" report")
    sunum_dugme(_ust, "haber", "Haber", "İmalat sanayii" if h_sec == "C" else ADLAR[h_sec][0])

# ================================================================ NACE 4'LÜ
with tab_nace:
    _ust = sunum_basla("nace")
    N4, NADI = load_nace34(_SURUM)
    if N4.empty:
        st.info("NACE 3'lü/4'lü verisi yok. `python scripts/guncelle.py --tuik` çalıştırın.", icon="ℹ️")
    else:
        st.markdown("<div class=\"eyebrow\">NACE 4'lü</div><div class=\"hero\">Alt sektörler</div>"
                    "<div class=\"sub\">Sanayi üretim endeksi, sınıf (4'lü) ve grup (3'lü) düzeyi · TÜİK SDMX</div>",
                    unsafe_allow_html=True)
        bolumler = sorted({c[:3] for c in N4.columns})
        senkron("n4_bolum", bolumler)
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
        seri_bolumu("02", NADI.get(k_sec, k_sec), N4[k_sec], f"{trk(NADI.get(k_sec, k_sec))} faaliyetinde",
                    "üretim", "TÜİK SDMX, sanayi üretim endeksi alt endeksleri · 2021=100", "n4_g")
    sunum_dugme(_ust, "nace", "NACE 4'lü", globals().get("b_sec"))

# ================================================================ FİRMALAR (İSO 500)
def tl_buyuk(x: float) -> str:
    if abs(x) >= 1e12:
        return f"{num(x / 1e12, 1)} trilyon ₺"
    if abs(x) >= 1e9:
        return f"{num(x / 1e9, 1)} mlr ₺"
    return f"{num(x / 1e6, 1)} mn ₺"


with tab_firma:
    _ust = sunum_basla("firma")
    F = load_iso500(_SURUM)
    if F.empty:
        st.info("İSO 500 verisi yok. `python scripts/guncelle.py --iso` çalıştırın.", icon="ℹ️")
    else:
        f1, f2, f3 = st.columns([1, 1.2, 2.4])
        yillar = sorted(F["yil"].unique(), reverse=True)
        yil = f1.selectbox("Yıl", yillar, key="f_yil")
        liste = f2.segmented_control("Liste", ["Tümü", "İSO 500", "İkinci 500"], default="Tümü", key="f_liste")
        sek_ops = ["C"] + sorted(c for c in F["nace"].dropna().unique() if 10 <= int(c[1:]) <= 33)
        senkron("f_sektor", sek_ops)
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
                        f'<div class="big neu" style="font-size:clamp(2.2rem,4vw,2.8rem)">{tl_buyuk(top)}</div>',
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
                                f'<div style="font-weight:700;font-size:1.2rem;color:{NAVY}">'
                                f'{pct(r["uretimden_satislar"] / top * 100)}</div></div>')
                st.markdown("".join(rows), unsafe_allow_html=True)
            with m_r:
                kum = pay["uretimden_satislar"].cumsum().values / top * 100
                fc = base_fig(380)
                fc.add_scatter(x=np.arange(1, len(kum) + 1), y=kum, mode="lines", line=dict(color=NAVY, width=2),
                               fill="tozeroy", fillcolor="rgba(32,55,100,.08)",
                               hovertemplate="İlk %{x} firma: %{y:.1f}%<extra></extra>")
                for n_ in (10, 50, 100):
                    if n_ <= len(kum):
                        fc.add_annotation(x=n_, y=kum[n_ - 1], text=f"İlk {n_} · {pct(kum[n_ - 1])}", showarrow=True,
                                          arrowhead=0, ax=40, ay=20, font=dict(size=10, color=INK))
                fc.update_xaxes(dtick=None, tickformat=",d")
                fc.update_yaxes(tickprefix="%", range=[0, 102])
                st.markdown('<div class="sub">İlk n firmanın satışlardaki toplam payı</div>', unsafe_allow_html=True)
                grafik(fc, width="stretch", config=CFG)

            # 02 iller: harita + ilk 8 il
            fv_il = cur.dropna(subset=["favok", "net_satislar"])
            fv_il = fv_il[fv_il["net_satislar"] > 0]
            il_g = cur.groupby("il").agg(satis=("uretimden_satislar", "sum"), firma=("unvan", "count"),
                                         calisan=("calisan", "sum"), ihracat=("ihracat_bin_usd", "sum"))
            il_g["favok"] = (fv_il.groupby("il")["favok"].sum() / fv_il.groupby("il")["net_satislar"].sum() * 100)
            if len(ortak):
                og = ortak.groupby("il")[["uretimden_satislar", "uretimden_satislar_once"]].sum()
                il_g["degisim"] = (og["uretimden_satislar"] / og["uretimden_satislar_once"] - 1) * 100
            else:
                il_g["degisim"] = np.nan
            il_g = il_g.drop(index="Belirtilmemiş", errors="ignore").sort_values("satis", ascending=False)
            il_pay = il_g["satis"] / top * 100
            en_fv = il_g["favok"].dropna()
            section("02", "İllere göre dağılım",
                    f"Firmalar {len(il_g)} ilde toplanıyor; en büyük il {il_g.index[0]} (satışların {pct(il_pay.iloc[0])}). "
                    f"İlk üç ilin toplam payı {pct(il_pay.head(3).sum())}."
                    + (f" FAVÖK marjı en yüksek il {en_fv.idxmax()} ({pct(en_fv.max())})." if len(en_fv) else ""))
            GOST = {"Üretimden satışlar": ("satis", lambda v: tl_buyuk(v)),
                    "Firma sayısı": ("firma", lambda v: num(v, 0)),
                    "Çalışan sayısı": ("calisan", lambda v: num(v, 0)),
                    "İhracat": ("ihracat", lambda v: f"{num(v / 1e6, 2 if v < 1e6 else 1)} mlr $"),
                    "FAVÖK marjı": ("favok", lambda v: pct(v)),
                    "Satış değişimi (önceki yıl)": ("degisim", lambda v: pct(v, sign=True))}
            olcu = st.segmented_control("Gösterge", list(GOST), default="Üretimden satışlar", key="f_il_olcu",
                                        label_visibility="collapsed") or "Üretimden satışlar"
            kol, fmt_il = GOST[olcu]
            iv = il_g[kol].replace(0, np.nan).dropna() if kol in ("calisan", "ihracat") else il_g[kol].dropna()
            m_l, m_r = st.columns([1.8, 1], gap="large")
            with m_r:
                il_sec = st.selectbox("İl", ["Tümü"] + list(il_g.index), key="f_il_sec")
            with m_l:
                geo = load_geojson()
                if geo and len(iv):
                    ad_map = {"Afyonkarahisar": "Afyon"}
                    tum = [f_["properties"]["name"] for f_ in geo["features"]]
                    fm = go.Figure(go.Choropleth(geojson=geo, locations=tum, z=[0] * len(tum),
                                                 featureidkey="properties.name", showscale=False,
                                                 colorscale=[[0, "#E7E6E6"], [1, "#E7E6E6"]],
                                                 marker_line_color="#FFFFFF", marker_line_width=.6, hoverinfo="skip"))
                    loc = [ad_map.get(k, k) for k in iv.index]
                    diverj = kol == "degisim"
                    renk = ([[0, RED], [.5, NOTR], [1, TEAL]] if diverj else [[0, PALE], [1, NAVY]])
                    fm.add_trace(go.Choropleth(
                        geojson=geo, locations=loc, z=iv.values, featureidkey="properties.name",
                        colorscale=renk, zmid=0 if diverj else None,
                        marker_line_color="#FFFFFF", marker_line_width=.6,
                        customdata=[[k, fmt_il(v), int(il_g.loc[k, "firma"])] for k, v in iv.items()],
                        hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]}<br>%{customdata[2]} firma<extra></extra>",
                        colorbar=dict(orientation="h", thickness=8, len=.6, y=-.02, x=.5, xanchor="center",
                                      outlinewidth=0, tickvals=[iv.min(), iv.max()],
                                      ticktext=[fmt_il(iv.min()), fmt_il(iv.max())])))
                    # ilk 10 ilin adı haritada
                    mrk = {}
                    for f_ in geo["features"]:
                        g_ = f_["geometry"]
                        pts = []
                        polys = g_["coordinates"] if g_["type"] == "MultiPolygon" else [g_["coordinates"]]
                        en_buyuk = max(polys, key=lambda pl: len(pl[0]))
                        pts = en_buyuk[0]
                        mrk[f_["properties"]["name"]] = (np.mean([p_[0] for p_ in pts]), np.mean([p_[1] for p_ in pts]))
                    ilk = [ad_map.get(k, k) for k in iv.sort_values(ascending=False).index[:10]]
                    fm.add_scattergeo(lon=[mrk[k][0] for k in ilk if k in mrk], lat=[mrk[k][1] for k in ilk if k in mrk],
                                      text=[k for k in ilk if k in mrk], mode="text", hoverinfo="skip",
                                      textfont=dict(size=10.5, color=INK, family=FONT))
                    fm.update_geos(fitbounds="geojson", visible=False, bgcolor="rgba(0,0,0,0)")
                    fm.update_layout(height=420, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)",
                                     showlegend=False)
                    grafik(fm, width="stretch", config=CFG)
                stats([("İlk 3 ilin payı", pct(il_pay.head(3).sum()), "üretimden satışlar"),
                       ("İlk 10 ilin payı", pct(il_pay.head(10).sum()), "üretimden satışlar"),
                       ("Firması olan il", num(len(il_g), 0), "81 ilin içinde")])
            with m_r:
                if il_sec == "Tümü":
                    st.markdown(f'<p style="font-weight:600;font-weight:700;font-size:1.25rem;margin:.6rem 0">'
                                f'{olcu} · ilk 8 il</p>', unsafe_allow_html=True)
                    top8 = iv.sort_values(ascending=False).head(8)
                    mx = top8.abs().max() or 1
                    h_ = ""
                    for k, v in top8.items():
                        w_ = max(abs(v) / mx * 100, 2)
                        renk_b = (RED if v < 0 else NAVY)
                        h_ += (f'<div style="margin:.55rem 0"><div style="font-size:.95rem">{k}</div>'
                               f'<div class="sub" style="font-size:.76rem">{int(il_g.loc[k, "firma"])} firma</div>'
                               f'<div style="display:flex;align-items:center;gap:.8rem">'
                               f'<div style="flex:1"><div style="height:9px;border-radius:3px;background:{renk_b};width:{w_}%"></div></div>'
                               f'<div style="font-weight:600;font-size:.88rem;white-space:nowrap">{fmt_il(v)}</div></div></div>')
                    st.markdown(h_, unsafe_allow_html=True)
                else:
                    fi = cur[cur["il"] == il_sec].sort_values("uretimden_satislar", ascending=False)
                    r_il = il_g.loc[il_sec]
                    st.markdown(f'<p style="font-weight:600;font-weight:700;font-size:1.25rem;margin:.6rem 0">'
                                f'{il_sec} · {int(r_il["firma"])} firma</p>'
                                f'<div class="sub">Satışlar {tl_buyuk(r_il["satis"])} · payı {pct(il_pay[il_sec])}'
                                + (f' · FAVÖK marjı {pct(r_il["favok"])}' if pd.notna(r_il["favok"]) else "") + '</div>',
                                unsafe_allow_html=True)
                    h_ = ""
                    for r in fi.head(12).itertuples():
                        h_ += (f'<div style="border-top:1px solid {LINE};padding:.45rem 0;display:flex;justify-content:space-between;gap:.8rem">'
                               f'<div style="font-size:.86rem">{r.unvan}<div class="sub" style="font-size:.72rem">'
                               f'{"İSO 500" if r.liste == 1 else "İkinci 500"} · sıra {int(r.sira)} · {r.nace}</div></div>'
                               f'<div style="font-weight:600;font-size:.84rem;white-space:nowrap">{tl_buyuk(r.uretimden_satislar)}</div></div>')
                    st.markdown(h_, unsafe_allow_html=True)
            src("İstanbul Sanayi Odası, İSO 500 ve İkinci 500 · il: firmanın bağlı olduğu sanayi/ticaret odasının ili "
                "(genel merkez ili değil) · il sınırları: Turkey-Maps-GeoJSON (Apache-2.0) · bej: listede firma yok ya da "
                "gösterge için yeterli veri yok")

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
    sunum_dugme(_ust, "firma", "Firmalar", globals().get("ad_f"))

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
              f'<div style="font-weight:700;font-size:1.15rem;color:{NAVY};white-space:nowrap">{deger_}</div></div>')
    return h


def mlr_usd(x: float) -> str:
    return f"{num(x / 1e9, 2 if abs(x) < 1e9 else 1)} mlr $"


with tab_urun:
    _ust = sunum_basla("urun")
    if U is None:
        st.info("Ürün verisi yok. `data/ham/` klasörüne TÜİK dosyalarını koyup `python scripts/urunler.py` çalıştırın.",
                icon="ℹ️")
    else:
        yillar_u = [c for c in U.deger.columns if U.deger[c].notna().any()]
        u1, u2 = st.columns([1, 3])
        yil_u = u1.selectbox("Yıl", yillar_u[::-1], key="u_yil")
        nace_ops = ["C"] + sorted(U.bilgi["nace"].unique())
        senkron("u_sektor", nace_ops)
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

        usd_k = USD_YIL.get(yil_u, np.nan)
        dolar_txt = (f'<div class="sub" style="margin-top:.3rem">≈ <b style="font-weight:700;font-size:1.5rem;'
                     f'color:{NAVY}">{num(top_u / usd_k / 1e9, 1)} mlr $</b> · {yil_u} ortalama kuru {num(usd_k, 2)} ₺</div>'
                     if pd.notna(usd_k) else "")
        st.markdown(f'<div class="eyebrow">Ürünler · sanayi ürün istatistikleri · {yil_u}</div>'
                    f'<div class="hero">{ad_u if len(ad_u) < 30 else ADLAR[u_sek][1]}</div>'
                    f'<p style="margin:1rem 0 .2rem 0;font-weight:600;font-size:.88rem">Satış değeri, toplam (₺)</p>'
                    f'<div class="big neu" style="font-size:clamp(2.2rem,4vw,2.8rem)">{tl_buyuk(top_u)}</div>' + dolar_txt,
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

        # 01 yurt içi pazar: sektör toplamı (yıllar) + ürün bazında listeler
        def sektor_pazar(kod: str) -> pd.DataFrame:
            """Yıllık: yurt içi satış ($), ihracat, ithalat, yerli üretimden iç piyasa, pazar, ithalat payı (milyar $)."""
            if "ihracat" not in TS or "ithalat" not in TS or kod not in TS["ihracat"]:
                return pd.DataFrame()
            idx = U.bilgi.index if kod == "C" else U.bilgi.index[U.bilgi["nace"] == kod]
            sat = U.deger.loc[idx].sum(min_count=1)

            def yil_top(s_):
                s_ = s_.dropna()
                g_ = s_.groupby(s_.index.year)
                return g_.sum()[g_.size() == 12].rename(lambda y_: str(y_)) / 1e6  # bin $ -> milyar $
            ex_y, im_y = yil_top(TS["ihracat"][kod]), yil_top(TS["ithalat"][kod])
            yl = [y_ for y_ in sat.index if y_ in ex_y.index and y_ in im_y.index and y_ in USD_YIL.index
                  and pd.notna(sat[y_]) and int(y_) <= int(yil_u)]
            d_ = pd.DataFrame(index=yl)
            d_["satis"] = [sat[y_] / USD_YIL[y_] / 1e9 for y_ in yl]
            d_["ihracat"], d_["ithalat"] = ex_y.reindex(yl), im_y.reindex(yl)
            d_["yerli"] = (d_["satis"] - d_["ihracat"]).clip(lower=0)
            d_["pazar"] = d_["yerli"] + d_["ithalat"]
            d_["pazar_tl"] = d_["pazar"] * USD_YIL.reindex(yl).values
            d_["ith_pay"] = d_["ithalat"] / d_["pazar"] * 100
            d_["ihr_pay"] = d_["ihracat"] / d_["satis"] * 100
            return d_

        SP = sektor_pazar(u_sek)
        tic_yillari = set(U.ticaret["yil"].unique())
        if not SP.empty and yil_u in SP.index:
            r_ = SP.loc[yil_u]
            onceki_y = str(int(yil_u) - 1)
            uf_s = ufe_yillik(u_sek)
            reel_p = ((SP.loc[yil_u, "pazar_tl"] / SP.loc[onceki_y, "pazar_tl"])
                      / (uf_s.get(yil_u, np.nan) / uf_s.get(onceki_y, np.nan)) - 1) * 100 if onceki_y in SP.index else np.nan
            bas_y = str(max(int(SP.index[0]), int(yil_u) - 5))
            n_y = int(yil_u) - int(bas_y)
            cagr = lambda col: ((SP.loc[yil_u, col] / SP.loc[bas_y, col]) ** (1 / n_y) - 1) * 100 if n_y > 0 else np.nan
            c_p, c_y, c_i = cagr("pazar"), cagr("yerli"), cagr("ithalat")
            fark_pay = r_["ith_pay"] - SP.loc[bas_y, "ith_pay"]
            pay_yon = (f"%{num(r_['ith_pay'], 0)} civarında yatay seyretti" if abs(fark_pay) < 2 else
                       f"{num(SP.loc[bas_y, 'ith_pay'], 0)}'den %{num(r_['ith_pay'], 0)}'e "
                       f"{'yükseldi' if fark_pay > 0 else 'geriledi'}")
            net = (f"Sektör net ihracatçı; ihracatı ithalatının {num(r_['ihracat'] / r_['ithalat'], 1)} katı, "
                   if r_["ihracat"] > r_["ithalat"] else
                   f"Sektör net ithalatçı; ithalatı ihracatının {num(r_['ithalat'] / max(r_['ihracat'], 1e-9), 1)} katı, ")
            ad_k = trk(ad_u) if u_sek != "C" else "imalat sanayii"
            section("01", "Yurt içi pazar",
                    f"{yil_u} yılında {ad_k} iç pazarı en az {num(r_['pazar'], 1)} mlr $ ({num(r_['pazar_tl'], 1)} mlr ₺); "
                    f"bir önceki yıla göre reel olarak %{num(abs(reel_p), 1)} {'büyüdü' if reel_p > 0 else 'daraldı'}. "
                    f"{bas_y}–{yil_u} arasında pazar dolar bazında yılda ortalama %{num(abs(c_p), 1)} "
                    f"{'büyüdü' if c_p > 0 else 'daraldı'}. İthalatın pazardaki payı {pay_yon}. "
                    f"{net}üretimin %{num(r_['ihr_pay'], 0)} kadarı yurt dışına satılıyor.")
            stats([("Pazar büyüklüğü", f'≥ {num(r_["pazar_tl"], 1)}<span class="p" style="font-size:.5em"> mlr ₺</span>',
                    f"{yil_u} · {num(r_['pazar'], 1)} mlr $"),
                   ("Reel değişim", f'<span class="{cls(reel_p)}">{pct(reel_p, sign=True)}</span>', "bir önceki yıla göre"),
                   ("Yıllık ortalama büyüme ($)", f'<span class="{cls(c_p)}">{pct(c_p, sign=True)}</span>', f"{bas_y}–{yil_u}"),
                   ("İthalatın pazardaki payı", f"≤ {pct(r_['ith_pay'])}", f"{bas_y}: {pct(SP.loc[bas_y, 'ith_pay'])}"),
                   ("İhracatın üretimdeki payı", pct(r_["ihr_pay"]), "")])
            fpz = go.Figure()
            fpz.add_bar(x=SP.index, y=SP["yerli"], name="Yerli üretimden iç piyasaya", marker_color=NAVY,
                        hovertemplate="%{x}: %{y:.1f} mlr $<extra>Yerli üretimden iç piyasaya</extra>")
            fpz.add_bar(x=SP.index, y=SP["ithalat"], name="İthalat", marker_color=OCHRE,
                        hovertemplate="%{x}: %{y:.1f} mlr $<extra>İthalat</extra>")
            fpz.add_scatter(x=SP.index, y=SP["ith_pay"], name="İthalat nüfuzu (%, sağ eksen)", yaxis="y2",
                            mode="lines+markers", line=dict(color=RED, width=2), marker=dict(size=6),
                            hovertemplate="%{x}: %{y:.1f}%<extra>İthalat nüfuzu</extra>")
            fpz.update_layout(height=420, barmode="stack", bargap=.35, margin=dict(l=4, r=8, t=40, b=24),
                              paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                              font=dict(family=FONT, size=11, color=MUTED),
                              legend=dict(orientation="h", y=1.02, yanchor="bottom", x=0, font=dict(color=INK, size=11)),
                              yaxis=dict(title="milyar $", gridcolor="#E7E6E6", rangemode="tozero"),
                              yaxis2=dict(overlaying="y", side="right", ticksuffix="%", showgrid=False, tickformat=".0f",
                                          range=[0, max(SP["ith_pay"].max() * 1.25, 10)]))
            fpz.update_xaxes(type="category", showgrid=False, linecolor=LINE)
            grafik(fpz, width="stretch", config=CFG)
            src("TÜİK sanayi ürün istatistikleri (yurt içi satış), TÜİK ISIC Rev.4 dış ticaret (TCMB EVDS), TCMB kur · "
                "milyar dolar · gizli (c) ürünler nedeniyle pazar alt sınır (≥), ithalat payı üst sınırdır (≤)")
            st.markdown(f'<div class="secd" style="margin-top:.6rem">{bas_y}–{yil_u} arasında yerli üreticilerin iç piyasa '
                        f'satışları dolar bazında yılda ortalama {pct(c_y, sign=True)}, ithalat {pct(c_i, sign=True)} '
                        f'değişti.</div>', unsafe_allow_html=True)
        if int(yil_u) in tic_yillari and yil_u in USD_YIL:
            if SP.empty or yil_u not in SP.index:
                section("01", "Yurt içi pazar")
            st.markdown('<p style="font-weight:600;margin-top:1.2rem">Ürün bazında iç pazar</p>'
                        f'<div class="secd">İç pazar = yurt içi satış − ihracat + ithalat. Birbirine GTİP üzerinden bağlı '
                        f'PRODTR kodları tek pazar olarak toplanır; (+n) birlikte sayılan ek ürün sayısıdır.</div>',
                        unsafe_allow_html=True)
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
            bb_ = buyuk.dropna(subset=["buyume"])
            c1_, c2_ = st.columns(2, gap="large")
            c1_.markdown(liste_html("Pazarı en büyük ürünler", [
                (r.ad, f"ithalatın payı %{num(r.ithalat_payi, 0)} · yıllık {pct(r.buyume, sign=True)}", mlr_usd(r.pazar))
                for r in Px.nlargest(8, "pazar").itertuples()]), unsafe_allow_html=True)
            c2_.markdown(liste_html("İthalata en bağımlı ürünler", [
                (r.ad, f"pazar {mlr_usd(r.pazar)}", f"%{num(min(r.ithalat_payi, 100), 0)}")
                for r in buyuk.nlargest(8, "ithalat_payi").itertuples()]), unsafe_allow_html=True)
            c3_, c4_ = st.columns(2, gap="large")
            c3_.markdown(liste_html("Pazarı en hızlı büyüyenler ($)", [
                (r.ad, f"pazar {mlr_usd(r.pazar)} · ithalatın payı %{num(r.ithalat_payi, 0)}", pct(r.buyume, sign=True))
                for r in bb_[bb_["buyume"] > 0].nlargest(8, "buyume").itertuples()]), unsafe_allow_html=True)
            c4_.markdown(liste_html("Pazarı en hızlı daralanlar ($)", [
                (r.ad, f"pazar {mlr_usd(r.pazar)} · ithalatın payı %{num(r.ithalat_payi, 0)}", pct(r.buyume, sign=True))
                for r in bb_[bb_["buyume"] < 0].nsmallest(8, "buyume").itertuples()]), unsafe_allow_html=True)
            src(f"TÜİK sanayi ürün istatistikleri (PRODTR) ve GTİP–PRODTR eşlemesi · dış ticaret: UN Comtrade (HS6) · "
                f"TL→$ dönüşümü {yil_u} ortalama kuru ({num(USD_YIL[yil_u], 2)}) · listeler en büyük 100 pazar içinden · ihracatı satıştan büyük görünen gruplar hariç")
        else:
            st.caption("Bu yıl için ürün bazında dış ticaret verisi yok; ürün listeleri hesaplanmadı.")

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
                         plot_bgcolor="rgba(0,0,0,0)", font=dict(family=FONT, size=11, color=INK), bargap=.35)
        fu.update_xaxes(visible=False)
        grafik(fu, width="stretch", config=CFG)

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
    sunum_dugme(_ust, "urun", "Ürünler", globals().get("ad_u"))

# ================================================================ KOD ANALİZİ
with tab_kod:
    _ust = sunum_basla("kod")
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
                grafik(fk, width="stretch", config=CFG)
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
    sunum_dugme(_ust, "kod", "Kod analizi", globals().get("q_") or None)

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



# Yurt içi pazar ($): PRODTR satış değerinin NACE 2'li toplamı (yıllık ortalama kurla $) − ihracat + ithalat.
# Ürünler sekmesindeki 'Yurt içi pazar' hesabıyla aynı (yerli üretimden iç piyasa negatifse 0 alınır).
PAZAR_YILI = (str(max(int(c) for c in U.deger.columns if U.deger[c].notna().any())) if U is not None else "")


def yurtici_pazar(kod: str, yil: str) -> float:
    if U is None or "ihracat" not in TS or "ithalat" not in TS \
            or yil not in U.deger.columns or yil not in USD_YIL.index:
        return np.nan
    idx = U.bilgi.index if kod == "C" else U.bilgi.index[U.bilgi["nace"] == kod]
    if not len(idx):
        return np.nan
    sat = U.deger.loc[idx, yil].sum(min_count=1)

    def yil_top(s_):
        s_ = s_.dropna()
        s_ = s_[s_.index.year == int(yil)]
        return s_.sum() * 1000 if len(s_) == 12 else np.nan  # bin $ -> $
    if kod in TS["ihracat"] and kod in TS["ithalat"]:
        ex, im = yil_top(TS["ihracat"][kod]), yil_top(TS["ithalat"][kod])
    else:  # dış ticareti olmayan hizmet sektörü (C33 kurulum ve onarım): pazar = satış
        ex = im = 0.0
    if np.isnan(sat) or np.isnan(ex) or np.isnan(im):
        return np.nan
    return max(sat / USD_YIL[yil] - ex, 0) + im


def mlr_usd_kisa(x: float) -> str:
    return f"{num(x / 1e9, 1)} mlr $"


@st.cache_data(show_spinner=False)
def tim_ulke(surum: float = 0) -> pd.DataFrame:
    """TİM ülkelere göre ihracat: son 12 ay ve önceki 12 ay (1000 $); scripts/tim.py üretir."""
    from pathlib import Path
    f = Path(__file__).parent / "data" / "tim_ulke_ihracat.csv"
    return pd.read_csv(f, index_col=0) if f.exists() else pd.DataFrame()


def ihracat_haritasi(tim: pd.DataFrame, h: int = 480) -> go.Figure:
    """Ülkelere göre son 12 ay ihracatın dünya haritası (renk: tutar, logaritmik); Türkiye koyu."""
    from ulkeler import ISO3
    d = tim[~tim["serbest_bolge"]].copy()
    d["iso"] = [ISO3.get(u) for u in d.index]
    d = d[d["iso"].notna() & (d["son12"] > 0)]
    d["deg"] = (d["son12"] / d["onceki12"].where(d["onceki12"] > 0) - 1) * 100
    d["ad"] = [ulke_adi(u) for u in d.index]
    d["metin"] = [f"{num(v / 1e6, 2)} mlr $" + (f" · {pct(g, sign=True)}" if pd.notna(g) else "")
                  for v, g in zip(d["son12"], d["deg"])]
    log = np.log10(d["son12"] * 1000)  # $ cinsinden
    ticks = [7, 8, 9, 10]  # 10 mn $, 100 mn $, 1 mlr $, 10 mlr $
    f = go.Figure(go.Choropleth(
        locations=d["iso"], z=log, locationmode="ISO-3", customdata=np.c_[d["ad"], d["metin"]],
        colorscale=[[0, "#EEF2F9"], [.35, "#B4C6E7"], [.7, BLUE], [1, NAVY]], zmin=6.5, zmax=log.max(),
        marker_line_color="#FFFFFF", marker_line_width=.4,
        hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]}<extra></extra>",
        colorbar=dict(title=dict(text="", side="right"), tickvals=ticks,
                      ticktext=["10 mn $", "100 mn $", "1 mlr $", "10 mlr $"], thickness=8, len=.55,
                      x=.0, xanchor="left", y=.08, yanchor="bottom", orientation="h",
                      tickfont=dict(size=9, color=MUTED), outlinewidth=0)))
    f.add_trace(go.Choropleth(locations=["TUR"], z=[1], locationmode="ISO-3", showscale=False,
                              colorscale=[[0, DARK], [1, DARK]], marker_line_color="#FFFFFF",
                              hovertemplate="Türkiye<extra></extra>"))
    f.update_geos(projection_type="natural earth", showframe=False, showcoastlines=False,
                  showland=True, landcolor="#F2F2F2", showcountries=False, showocean=False,
                  lataxis_range=[-58, 84], bgcolor="rgba(0,0,0,0)")
    f.update_layout(height=h, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(family=FONT, size=11, color=INK), hoverlabel=dict(bgcolor="#FFFFFF"))
    return f


def ulke_adi(u: str) -> str:
    """TİM'in büyük harfli ülke adı -> 'Birleşik Krallık' (kısaltmalar olduğu gibi: ABD, BAE)."""
    if u in ("ABD", "BAE", "KKTC"):
        return u
    ust = {"i": "İ", "ı": "I"}
    kel = [w[:1].replace(w[:1], ust.get(w[:1], w[:1].upper())) + w[1:] for w in trk(u).split()]
    return " ".join(kel).replace("Federasyonu", "Fed.")


# ================================================================ SUNUM
# Her slayt yatay çizgiyle (hr.slayt-ayrac) ayrılır; PPTX düğmesi bu çizgilerden keserek her birini bir slayt yapar.
def yillik_buyume(seviye: pd.Series) -> tuple[pd.Series, bool, int]:
    """Aylık endeksin yıllık ortalamasının bir önceki yıla göre değişimi (%).

    Son yıl eksikse (yılbaşından bugüne), o yılın mevcut ayları önceki yılın aynı aylarıyla karşılaştırılır.
    Döner: (yıl -> değişim), son yıl eksik mi, son yılın son ayı.
    """
    s_ = seviye.dropna()
    yillar = sorted(set(s_.index.year))
    son_yil, son_ay = yillar[-1], int(s_.index[-1].month)
    out = {}
    for y in yillar[1:]:
        cur, prev = s_[s_.index.year == y], s_[s_.index.year == y - 1]
        if len(prev) < 12:
            continue
        if y == son_yil and len(cur) < 12:
            aylar = set(cur.index.month)
            prev = prev[prev.index.month.isin(aylar)]
        elif len(cur) < 12:
            continue
        out[y] = (cur.mean() / prev.mean() - 1) * 100
    return pd.Series(out, dtype=float), son_ay < 12, son_ay


def yillik_bar(b: pd.Series, ytd: bool, son_ay: int, h: int = 330) -> go.Figure:
    etiket = [str(y) for y in b.index]
    if ytd:
        etiket[-1] = f"{b.index[-1]}<br><span style='font-size:10px'>Oca–{AYLAR_KISA_[son_ay - 1]}</span>"
    renk = [TEAL if v >= 0 else RED for v in b.values]
    if ytd:  # yılbaşından bugüne: açık ton
        renk[-1] = OCHRE if b.iloc[-1] >= 0 else "#E6B9B8"
    f = go.Figure(go.Bar(
        x=etiket, y=b.values, marker=dict(color=renk),
        text=[pct(v) for v in b.values], textposition="outside", cliponaxis=False,
        textfont=dict(size=12, color=INK, family=FONT),
        hovertemplate="%{x}: %{y:.1f}<extra></extra>"))
    lo, hi = min(b.min(), 0), max(b.max(), 0)
    pad = (hi - lo) * .14
    f.update_layout(height=h, margin=dict(l=4, r=8, t=18, b=8), paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)", font=dict(family=FONT, size=11, color=MUTED), bargap=.32,
                    showlegend=False, hoverlabel=dict(bgcolor="#FFFFFF", bordercolor=LINE, font_color=INK))
    f.update_xaxes(showgrid=False, linecolor=LINE, ticks="", type="category", tickfont=dict(color=INK, size=11))
    f.update_yaxes(visible=False, range=[lo - (pad if lo < 0 else 0), hi + pad], zeroline=True,
                   zerolinecolor="#A6A6A6")
    return f


def slayt_ayrac() -> None:
    st.markdown('<hr class="slayt-ayrac">', unsafe_allow_html=True)


def slayt_baslik(no: int, metin: str) -> None:
    """Numaralı slayt başlık şeridi."""
    st.markdown(f'<div class="sbas"><span class="no">{no}</span><span>{metin}</span></div>', unsafe_allow_html=True)


def uretim_slayti(no: int, kod: str, ad: str, bant: bool = False) -> None:
    """Sanayi üretimi slaytı: son ay yıllık değişim, yıllık ortalama büyüme (bar) ve gösterge kartları.

    kod = "C" imalat toplamı ya da NACE 2'li sektör (C13 …); ekranda kod ve NACE adı gösterilmez, yalnızca `ad`.
    """
    seviye = sue if kod == "C" else S[kod]
    with st.container(key=f"slayt_{no}"):
        s_y = yoy(seviye)
        u_p, u_v = son_gecerli(s_y)
        u_once = s_y.get(u_p - 12, np.nan)
        u_fark = u_v - u_once
        b_y, b_ytd, b_ay = yillik_buyume(seviye)
        b_y = b_y[b_y.index >= 2022]

        if bant:  # koyu başlık şeridi (diğer slaytlar gibi)
            slayt_baslik(no, ad)
        l, r = st.columns([1, 1.15], gap="large")
        with l:
            boy = "" if len(ad) < 22 else ' style="font-size:1.5rem"'
            ust_ = "" if bant else (f'<div class="eyebrow"><span class="sno">{no}</span>Aylık sanayi göstergeleri</div>'
                                    f'<div class="hero"{boy}>{ad}</div>')
            st.markdown(ust_ + f'<p style="margin:{".4rem" if bant else "1.4rem"} 0 .2rem 0;font-weight:600;font-size:.92rem">'
                        f'Sanayi üretim endeksi, yıllık değişim</p>'
                        + big_pct(u_v, "neg" if u_v < 0 else "pos"), unsafe_allow_html=True)
            once_txt = pct(u_once) if not np.isnan(u_once) else "—"
            fark_txt = "" if np.isnan(u_fark) else \
                f' · <b class="{cls(u_fark)}">{num(u_fark, 1) if u_fark < 0 else "+" + num(u_fark)} puan</b>'
            st.markdown(f'<div class="sub" style="margin-top:.8rem">{ay(u_p)} · bir yıl önce '
                        f'<b style="color:{INK}">{once_txt}</b>{fark_txt}</div>', unsafe_allow_html=True)
            if b_ytd and len(b_y):
                st.markdown(f'<div style="margin-top:1rem;font-size:.95rem">Ocak–{AYLAR_[b_ay - 1]} {b_y.index[-1]} '
                            f'ortalaması, geçen yılın aynı dönemine göre '
                            f'<b style="font-weight:700;font-size:1.25rem;color:{TEAL if b_y.iloc[-1] >= 0 else RED}">'
                            f'{pct(b_y.iloc[-1], sign=True)}</b></div>', unsafe_allow_html=True)
        with r:
            ek = f" · {b_y.index[-1]}: Ocak–{AYLAR_[b_ay - 1]}, geçen yılın aynı dönemine göre" if b_ytd else ""
            st.markdown(f'<div class="sub" style="text-align:right">● Yıllık ortalama, önceki yıla göre{ek}</div>',
                        unsafe_allow_html=True)
            st.plotly_chart(yillik_bar(b_y, b_ytd, b_ay), width="stretch", config=CFG,
                            key=f"sunum_s{no}_bar_{kod}")

        mev = {k: atlas_seri(k, kod) for k in ATLAS}
        mev = {k: v for k, v in mev.items() if v is not None}
        cols = st.columns(len(mev), gap="small")
        for c, (k, ser) in zip(cols, mev.items()):
            c.markdown(kpi_kart(k, ser, kod, k == "uretim"), unsafe_allow_html=True)
        src("TÜİK, sanayi üretim endeksi (takvim etkisinden arındırılmış, 2021=100), ciro, ücretli çalışan, "
            "dış ticaret, Yİ-ÜFE · TCMB EVDS, kapasite kullanım oranı · yıllık değişim: yıllık ortalama endekse göre")


with tab_sunum:
    _ust_s = sunum_basla("sunum")
    s_kod = st.session_state.get("atlas_sektor", "C")
    if s_kod != "C" and (s_kod not in S or S[s_kod].dropna().empty):
        s_kod = "C"
    ss_ad = "İmalat sanayii" if s_kod == "C" else ADLAR[s_kod][1]

    # Sektör seçimi: 6. ve sonraki slaytlar bu sektörün verisini gösterir. Seçim kutusu sunuma girmez
    # (PPTX ilk slaytın '.eyebrow' satırından başlar; bkz. sunum_js.py).
    sek_ops = sorted([k for k in S.columns if k in ADLAR and S[k].notna().any()], key=lambda k: int(k[1:]))
    sc_, _ = st.columns([1.3, 3])
    sn_kod = sc_.selectbox("Sektör (6. ve sonraki slaytlar)", sek_ops,
                           index=sek_ops.index("C13") if "C13" in sek_ops else 0, key="sunum_sektor",
                           format_func=lambda k: f"{k} · {ADLAR[k][1]}")
    sn_ad = ADLAR[sn_kod][1]

    # ---------------------------------------------------------- slayt 1: sanayi üretimi, yıllık (imalat)
    uretim_slayti(1, s_kod, ss_ad)
    slayt_ayrac()

    # ---------------------------------------------------------- slayt 2: sektör haritası, yılbaşından bugüne
    with st.container(key="slayt_2"):
        ytd_yil, ytd_ay = int(sue.dropna().index[-1].year), int(sue.dropna().index[-1].month)
        ytd_ad = f"Ocak–{AYLAR_[ytd_ay - 1]} {ytd_yil}" if ytd_ay > 1 else f"Ocak {ytd_yil}"

        def ytd_degisim(seviye: pd.Series) -> float:
            """Yılbaşından imalatın son ayına kadar ortalama, geçen yılın aynı aylarına göre (%)."""
            s_ = seviye.dropna()
            cur = s_[(s_.index.year == ytd_yil) & (s_.index.month <= ytd_ay)]
            prev = s_[(s_.index.year == ytd_yil - 1) & (s_.index.month <= ytd_ay)]
            if len(cur) < ytd_ay or len(prev) < ytd_ay:
                return np.nan
            return (cur.mean() / prev.mean() - 1) * 100

        pz_yil = PAZAR_YILI
        slayt_baslik(2, "Sektör haritası")
        aa, bb = st.columns([3, 1])
        aa.markdown(f'<div class="secd">Sanayi üretim endeksi, {ytd_ad} ortalaması, geçen yılın aynı dönemine göre '
                    f'değişim · sağda: {pz_yil} yurt içi pazar</div>', unsafe_allow_html=True)
        bb.markdown('<div class="legend">düşüş <div class="bar"></div> artış</div>', unsafe_allow_html=True)
        sek_kodlar = sorted([k for k in S.columns if k in ADLAR], key=lambda k: int(k[1:]))
        karolar2 = [("C", "C · toplam", "İmalat sanayii", ytd_degisim(sue))] + [
            (k, k, ADLAR[k][1], ytd_degisim(S[k])) for k in sek_kodlar]
        karolar2 = [x for x in karolar2 if not np.isnan(x[3])]
        for i_ in range(0, len(karolar2), 4):
            satir = st.columns(4, gap="small")
            for c, (code, etiket, ad_, val) in zip(satir, karolar2[i_:i_ + 4]):
                pz = yurtici_pazar(code, pz_yil)
                pz_txt = (mlr_usd_kisa(pz) if not np.isnan(pz) else
                          '<span style="font-size:.78rem;font-weight:400">veri gizliliği nedeniyle yok</span>')
                c.markdown(f'<div class="tile{" tot" if code == "C" else ""}" style="background:{div_color(val, 15)}">'
                           f'<div style="text-align:right"><span class="c">Yurt içi pazar {pz_yil}</span></div>'
                           f'<div class="t" style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{ad_}</div>'
                           f'<div style="display:flex;justify-content:space-between;align-items:baseline">'
                           f'<span class="v">{pct(val, sign=True)}</span>'
                           f'<span style="font-size:1.1rem;font-weight:700">{pz_txt}</span></div></div>',
                           unsafe_allow_html=True)
        src(f"TÜİK, sanayi üretim endeksi (takvim etkisinden arındırılmış, 2021=100) · TCMB EVDS üzerinden · "
            f"yurt içi pazar = PRODTR satış değeri ({pz_yil} ortalama kurla $) − ihracat + ithalat "
            f"(TÜİK, ISIC Rev.4 dış ticaret) · kurulum ve onarımda dış ticaret olmadığından pazar = satış")
    slayt_ayrac()

    # ---------------------------------------------------------- slayt 3: dış ticaret, sektörlere göre (ihracat ve ithalat)
    if "ihracat" in TS and "ithalat" in TS:
        with st.container(key="slayt_3"):
            def dt12(df: pd.DataFrame) -> tuple:
                """Son 12 ay: sektörlerin yıllık değişimi, imalat içindeki payı, imalat toplamı, dönem,
                sektör tutarları (bin $)."""
                t12 = df.rolling(12).sum().dropna(how="all")
                sek12 = t12.drop(columns="C", errors="ignore")
                sek12 = sek12[[c for c in sek12.columns if c in ADLAR]]
                return (yoy(sek12).iloc[-1], sek12.iloc[-1] / t12["C"].iloc[-1] * 100, t12["C"], t12.index[-1],
                        sek12.iloc[-1])

            ex_g, ex_pay, ex_top, ex_p, ex_t = dt12(TS["ihracat"])
            im_g, im_pay, im_top, im_p, im_t = dt12(TS["ithalat"])
            ex_yg, im_yg = yoy(ex_top).iloc[-1], yoy(im_top).iloc[-1]

            def kucuk_bar(v: pd.Series, renk_pos: str, renk_neg: str, pay: bool = False,
                          tutar: pd.Series | None = None) -> go.Figure:
                fb = hbar(v, renk_pos, renk_neg, None, "Pay" if pay else "12 ay yıllık")
                srt_ = v.dropna().sort_values()
                if pay:
                    fb.update_traces(text=[pct(x) for x in srt_.values])
                elif tutar is not None:  # değişim + son 12 ay tutarı (milyar $)
                    fb.update_traces(text=[f"{pct(x, sign=True)} · {num(tutar.get(k, np.nan) / 1e6, 1)} mlr $"
                                           for k, x in srt_.items()])
                fb.update_traces(textfont=dict(size=10, color=INK),
                                 y=[ADLAR.get(k, (k, k))[1].replace("Metalik olmayan mineral", "Mineral ürünler")
                                    for k in v.dropna().sort_values().index])
                lo, hi = min(v.min(), 0), max(v.max(), 0)
                k_ = 2.0 if tutar is not None else 1.0  # uzun etiket için daha fazla boşluk
                pad = (hi - lo) * .3 * k_
                fb.update_xaxes(range=[lo - ((hi - lo) * .7 * k_ if lo < 0 else 0), hi + pad])
                fb.update_yaxes(automargin=True)
                fb.update_layout(height=22 * len(v.dropna()) + 16, bargap=.3, margin=dict(l=2, r=40, t=4, b=4),
                                 font=dict(size=10.5))
                return fb

            slayt_baslik(3, "Dış ticaret")
            st.markdown(f'<div class="secd">Son 12 ayda ({ay(ex_p)} itibarıyla) imalat sanayii ihracatı '
                        f'<b>{num(ex_top.iloc[-1] / 1e6, 1)} mlr $</b> ({pct(ex_yg, sign=True)}), ithalatı '
                        f'<b>{num(im_top.iloc[-1] / 1e6, 1)} mlr $</b> ({pct(im_yg, sign=True)}); '
                        f'karşılama oranı {pct(ex_top.iloc[-1] / im_top.iloc[-1] * 100, 0)}.</div>',
                        unsafe_allow_html=True)
            k_ex, k_im = st.columns(2, gap="large")
            for kol, ad_dt, g_, pay_, p_, renk, t_ in ((k_ex, "İhracat", ex_g, ex_pay, ex_p, NAVY, ex_t),
                                                       (k_im, "İthalat", im_g, im_pay, im_p, BLUE, im_t)):
                with kol:
                    st.markdown(f'<div style="font-weight:700;color:{NAVY};font-size:1.05rem;'
                                f'border-bottom:2px solid {NAVY};padding-bottom:.2rem;margin-bottom:.4rem">'
                                f'{ad_dt} ($), son 12 ay · {ay(p_)}</div>', unsafe_allow_html=True)
                    a_, b_ = st.columns([1.6, 1], gap="small")
                    a_.markdown(f'<div class="eyebrow" style="margin:.2rem 0">Yıllık değişim · tutar</div>',
                                unsafe_allow_html=True)
                    a_.plotly_chart(kucuk_bar(g_, TEAL, RED, tutar=t_), width="stretch", config=CFG,
                                    key=f"sunum_s3_{ad_dt}_g")
                    b_.markdown(f'<div class="eyebrow" style="margin:.2rem 0">İmalat {trk(ad_dt)}ındaki pay</div>',
                                unsafe_allow_html=True)
                    b_.plotly_chart(kucuk_bar(pay_, renk, renk, pay=True), width="stretch", config=CFG,
                                    key=f"sunum_s3_{ad_dt}_p")
            src("TÜİK, genel ticaret sistemine göre dış ticaret, ISIC Rev.4 · TCMB EVDS üzerinden · "
                "son 12 ay toplamı, bir önceki 12 aya göre")
        slayt_ayrac()

    # ---------------------------------------------------------- slayt 4: ülkelere göre ihracat (TİM)
    TIM = tim_ulke(_SURUM)
    if not TIM.empty:
        with st.container(key="slayt_4"):
            t_p = pd.Period(TIM["donem"].iloc[0], "M")
            ulk = TIM[~TIM["serbest_bolge"]].nlargest(20, "son12").copy()
            ulk["deg"] = (ulk["son12"] / ulk["onceki12"] - 1) * 100
            ulk["ad"] = [ulke_adi(u) for u in ulk.index]
            top_s = TIM["son12"].sum()
            pay20 = ulk["son12"].sum() / top_s * 100

            def ulke_bar(x: pd.Series, etiket: list[str], renk: list[str], h: int) -> go.Figure:
                fb = go.Figure(go.Bar(x=x.values, y=ulk["ad"], orientation="h", marker_color=renk,
                                      text=etiket, textposition="outside", cliponaxis=False,
                                      textfont=dict(size=10.5, color=INK),
                                      hovertemplate="%{y}: %{text}<extra></extra>"))
                lo, hi = min(x.min(), 0), max(x.max(), 0)
                pad = (hi - lo) * .75  # tutar + değişim etiketi için yer
                fb.update_layout(height=h, margin=dict(l=2, r=10, t=4, b=4), bargap=.3,
                                 paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                                 font=dict(family=FONT, size=11, color=INK), hoverlabel=dict(bgcolor="#FFFFFF"))
                fb.update_xaxes(visible=False, range=[lo - (pad if lo < 0 else 0), hi + pad])
                fb.update_yaxes(autorange="reversed", showgrid=False, ticks="", automargin=True)
                return fb

            slayt_baslik(4, "Ülkelere göre ihracat")
            st.markdown(f'<div class="secd">Son 12 ayda ({ay(t_p)} itibarıyla) en çok ihracat yapılan 20 ülke, '
                        f'ihracatın %{num(pay20, 0)}\'ini oluşturuyor.</div>',
                        unsafe_allow_html=True)
            h4 = 24 * len(ulk) + 16
            k1, k2 = st.columns([1.75, 1], gap="medium")
            k1.markdown(f'<div class="eyebrow" style="margin:.2rem 0">İhracat, son 12 ay · {ay(t_p)}</div>',
                        unsafe_allow_html=True)
            k1.markdown('<div style="height:1.6rem"></div>', unsafe_allow_html=True)
            k1.plotly_chart(ihracat_haritasi(TIM, 410), width="stretch", config=CFG, key="sunum_s4_harita")
            k2.markdown('<div class="eyebrow" style="margin:.2rem 0">İlk 20 ülke · tutar ve yıllık değişim</div>',
                        unsafe_allow_html=True)
            k2.plotly_chart(ulke_bar(ulk["son12"] / 1e6,
                                     [f"{num(v / 1e6, 1)} mlr $ · {pct(d, sign=True)}"
                                      for v, d in zip(ulk["son12"], ulk["deg"])],
                                     [NAVY] * len(ulk), h4), width="stretch", config=CFG, key="sunum_s4_tutar")
            src("TİM, ülkelere göre konsolide ihracat (ihracatçı birliklerine kayıtlı ihracat; TÜİK genel ihracat "
                "toplamından düşüktür) · serbest bölgeler hariç · son 12 ay toplamı, bir önceki 12 aya göre")
        slayt_ayrac()

    # ---------------------------------------------------------- slayt 5: ücretli çalışan, ciro ve KKO, sektörlere göre
    if "ucretli_calisan" in TS and "ciro" in TS:
        with st.container(key="slayt_5"):
            def sek_son(df: pd.DataFrame) -> pd.DataFrame:
                d = df.drop(columns="C", errors="ignore")
                return d[[c for c in d.columns if c in ADLAR]]

            # ücretli çalışan: son ay düzeyi ve geçen yılın aynı ayına göre değişim
            uc = sek_son(TS["ucretli_calisan"]).dropna(how="all")
            p_uc = uc.index[-1]
            uc_v, uc_g = uc.loc[p_uc], (uc.loc[p_uc] / uc.loc[p_uc - 12] - 1) * 100
            uc_c = TS["ucretli_calisan"]["C"].dropna()
            # ciro: son 12 ay toplamı, önceki 12 aya göre
            ci = sek_son(TS["ciro"]).dropna(how="all")
            p_ci = ci.index[-1]
            ci12 = ci.rolling(12).sum()
            ci_g = (ci12.loc[p_ci] / ci12.loc[p_ci - 12] - 1) * 100
            ci_c12 = TS["ciro"]["C"].dropna().rolling(12).sum()
            # KKO: son ay ve son 12 ay ortalaması
            kk = sek_son(TS["kko"]).dropna(how="all") if "kko" in TS else pd.DataFrame()

            def sunum_hbar(v: pd.Series, metin: dict, renk_pos: str, renk_neg: str,
                           eksen0: float | None = 0.0) -> go.Figure:
                v = v.dropna().sort_values()
                fb = go.Figure(go.Bar(
                    x=v.values, y=[ADLAR.get(k, (k, k))[1].replace("Metalik olmayan mineral", "Mineral ürünler")
                                   for k in v.index],
                    orientation="h", marker_color=[renk_pos if x >= (eksen0 or 0) else renk_neg for x in v.values],
                    text=[metin[k] for k in v.index], textposition="outside", cliponaxis=False,
                    textfont=dict(size=10, color=INK), hovertemplate="%{y}: %{text}<extra></extra>"))
                lo, hi = (min(v.min(), 0), max(v.max(), 0)) if eksen0 is not None else (v.min() - 5, v.max())
                pad = (hi - lo) * (.8 if lo < 0 else .6)
                fb.update_layout(height=22 * len(v) + 16, margin=dict(l=2, r=4, t=4, b=4), bargap=.3,
                                 paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                                 font=dict(family=FONT, size=10.5, color=INK), hoverlabel=dict(bgcolor="#FFFFFF"))
                fb.update_xaxes(visible=False, range=[lo - ((hi - lo) * 1.1 if lo < 0 and eksen0 is not None else 0),
                                                      hi + pad])
                fb.update_yaxes(showgrid=False, ticks="", automargin=True)
                return fb

            ust_ = (f'İmalat sanayiinde {ay(p_uc)} itibarıyla <b>{num(uc_c.iloc[-1] / 1e6, 2)} milyon</b> ücretli çalışan '
                    f'var ({pct((uc_c.iloc[-1] / uc_c.get(p_uc - 12, np.nan) - 1) * 100, sign=True)}); nominal ciro son '
                    f'12 ayda {pct((ci_c12.iloc[-1] / ci_c12.get(ci_c12.index[-1] - 12, np.nan) - 1) * 100, sign=True)} '
                    f'arttı')
            if not kk.empty:
                ust_ += f'; kapasite kullanımı {ay(kko.dropna().index[-1])} itibarıyla %{num(kko.dropna().iloc[-1])}'
            slayt_baslik(5, "İstihdam, ciro ve kapasite kullanımı")
            st.markdown(f'<div class="secd">{ust_}.</div>', unsafe_allow_html=True)
            g1, g2, g3 = st.columns(3, gap="medium")
            with g1:
                st.markdown(f'<div class="eyebrow" style="margin:.2rem 0">Ücretli çalışan · {ay(p_uc)}</div>'
                            f'<div class="sub" style="font-size:.72rem">kişi sayısı · geçen yılın aynı ayına göre</div>',
                            unsafe_allow_html=True)
                st.plotly_chart(sunum_hbar(uc_g, {k: f"{num(uc_v[k] / 1e3, 0)} bin · {pct(uc_g[k], sign=True)}"
                                                  for k in uc_g.index}, BLUE, RED),
                                width="stretch", config=CFG, key="sunum_s5_uc")
            with g2:
                st.markdown(f'<div class="eyebrow" style="margin:.2rem 0">Ciro (nominal) · {ay(p_ci)}</div>'
                            f'<div class="sub" style="font-size:.72rem">son 12 ay, önceki 12 aya göre</div>',
                            unsafe_allow_html=True)
                st.plotly_chart(sunum_hbar(ci_g, {k: pct(ci_g[k], sign=True) for k in ci_g.index}, NAVY, RED),
                                width="stretch", config=CFG, key="sunum_s5_ciro")
            with g3:
                if not kk.empty:
                    p_kk = kk.index[-1]
                    kk_son, kk_ort = kk.loc[p_kk], kk.iloc[-12:].mean()
                    st.markdown(f'<div class="eyebrow" style="margin:.2rem 0">Kapasite kullanım oranı · {ay(p_kk)}</div>'
                                f'<div class="sub" style="font-size:.72rem">son ay · son 12 ay ortalaması</div>',
                                unsafe_allow_html=True)
                    st.plotly_chart(sunum_hbar(kk_son, {k: f"%{num(kk_son[k])} · ort. %{num(kk_ort[k])}"
                                                        for k in kk_son.index}, TEAL, TEAL, eksen0=None),
                                    width="stretch", config=CFG, key="sunum_s5_kko")
            src("TÜİK SDMX, ücretli çalışan (takvim etkisinden arındırılmış) ve ciro endeksi (2021=100) · "
                "TCMB EVDS, sektörlere göre kapasite kullanım oranı")
        slayt_ayrac()

    # ---------------------------------------------------------- slayt 6: seçili sektör (slayt 1'in sektör sürümü)
    uretim_slayti(6, sn_kod, sn_ad, bant=True)
    slayt_ayrac()

    sunum_dugme(_ust_s, "sunum", "Sunum", ss_ad if s_kod != "C" else "İmalat sanayii")
