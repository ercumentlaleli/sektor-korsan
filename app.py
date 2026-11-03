"""Sektör veri atlası — TÜİK/TCMB verileriyle imalat sanayii panosu."""
from __future__ import annotations

import io

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from data import (SEKTORLER, ay, ay_kisa, guncelleme_bilgisi, load, load_tuik, num, pct, son_gecerli,
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
.tile.tot {{ outline:2px solid {INK}; }}
.legend {{ display:flex; align-items:center; gap:8px; font-size:.74rem; color:{MUTED}; justify-content:flex-end; }}
.legend .bar {{ width:200px; height:6px; border-radius:3px; background:linear-gradient(90deg,{RED},#efe9df,{TEAL}); }}
.stTabs [data-baseweb="tab-list"] {{ gap:0; border:1px solid {LINE}; border-radius:4px; width:fit-content; }}
.stTabs [data-baseweb="tab"] {{ padding:.35rem 1rem; border-right:1px solid {LINE}; height:auto; }}
.stTabs [aria-selected="true"] {{ background:#dfe3e7; }}
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] {{ display:none; }}
[data-testid="stToolbar"] {{ display:none; }}
.brand,.hero,.big,.big *,.lead,.sech,.kpi .v,.kpi .v *,.stat .v,.stat .v *,.tile .v {{ font-family: Fraunces, Georgia, serif !important; }}
.secno,.tile .c {{ font-family: "JetBrains Mono", monospace !important; }}
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


def line_chart(series: list[tuple[str, pd.Series, str]], h: int = 340, pctaxis: bool = True,
               clip: bool = True, fill: bool = False) -> go.Figure:
    f = base_fig(h)
    allv = []
    for i, (name, s, color) in enumerate(series):
        s = ts(s)
        allv.extend(s.values)
        f.add_scatter(x=s.index, y=s.values, name=name, mode="lines",
                      line=dict(color=color, width=2 if i == 0 else 1.4,
                                dash="dot" if "ortalama" in name.lower() else None),
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
        f.update_layout(showlegend=True, legend=dict(orientation="h", y=1.12, x=0,
                                                     font=dict(color=INK, size=11)))
    return f


CFG = {"displayModeBar": False}
ADLAR = {**SEKTORLER, "C18": ("Kayıtlı medyanın basılması ve çoğaltılması", "Basım")}


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
tab_atlas, tab_uretim, tab_ist, tab_tcmb, tab_veri = st.tabs(
    ["Atlas", "Üretim ve fiyat", "İstihdam ve ciro", "TCMB", "Veri"])

# ================================================================ ATLAS
with tab_atlas:
    l, r = st.columns([1, 1.15], gap="large")
    with l:
        st.markdown(f'<div class="eyebrow">Aylık sanayi göstergeleri</div>'
                    f'<div class="hero">İmalat sanayii</div>'
                    f'<div class="sub">Bölüm C · imalat, toplam</div>'
                    f'<p style="margin:1.4rem 0 .2rem 0;font-weight:600;font-size:.92rem">'
                    f'Sanayi üretim endeksi, yıllık değişim</p>' + big_pct(v_sue, "neg" if v_sue < 0 else "pos"),
                    unsafe_allow_html=True)
        once = sue_y.get(p_sue - 12, np.nan)
        fark = v_sue - once
        st.markdown(f'<div class="sub" style="margin-top:.8rem">{ay(p_sue)} · bir yıl önce '
                    f'<b style="color:{INK}">{pct(once)}</b> · '
                    f'<b class="{cls(fark)}">{num(fark, 1) if fark < 0 else "+" + num(fark)} puan</b></div>',
                    unsafe_allow_html=True)
    with r:
        st.markdown(f'<div class="sub" style="text-align:right">● Veri {ay(p_sue)} · TÜİK, TCMB</div>',
                    unsafe_allow_html=True)
        f = line_chart([("Üretim, yıllık %", sue_y["2021-07":], NAVY)], h=320, fill=True)
        st.plotly_chart(f, width="stretch", config=CFG)

    # KPI şeridi
    p_kko, v_kko = son_gecerli(kko)
    p_uf, v_uf = son_gecerli(yiufe_y)
    p_yd, v_yd = son_gecerli(ydufe_y)
    p_rk, v_rk = son_gecerli(rek)
    p_us, v_us = son_gecerli(USD)
    kpis = [
        ("Üretim endeksi, yıllık", kpi_val(v_sue), sue_y, ay(p_sue), True),
        ("Kapasite kullanımı", kpi_val(v_kko), kko, ay(p_kko), False),
        ("Yİ-ÜFE imalat, yıllık", kpi_val(v_uf), yiufe_y, ay(p_uf), False),
        ("YD-ÜFE imalat, yıllık", kpi_val(v_yd), ydufe_y, ay(p_yd), False),
        ("Reel efektif kur", kpi_val(v_rk, ""), rek, f"{ay(p_rk)} · 2025=100", False),
        ("USD/TRY, aylık ort.", kpi_val(v_us, ""), USD, ay(p_us), False),
    ]
    cols = st.columns(6, gap="small")
    for c, (lab, val, ser, note, sel) in zip(cols, kpis):
        last = ser.dropna().iloc[-1]
        color = RED if (lab.startswith("Üretim") and last < 0) else TEAL
        vcls = "neg" if color == RED else "pos"
        c.markdown(f'<div class="kpi{" sel" if sel else ""}"><div class="l">{lab}</div>'
                   f'<div class="v {vcls}">{val}</div>{sparkline(ser, color)}'
                   f'<div class="n">{note}</div></div>', unsafe_allow_html=True)

    # Sektör haritası
    section("01", "Sektör haritası")
    a, b = st.columns([2, 1])
    a.markdown(f'<div class="secd">Sanayi üretim endeksi, yıllık değişim · {ay(son_sek_p)}</div>',
               unsafe_allow_html=True)
    b.markdown('<div class="legend">düşüş <div class="bar"></div> artış</div>', unsafe_allow_html=True)
    tiles = [f'<div class="tile tot" style="background:{div_color(v_sue)}"><div class="c">C · toplam</div>'
             f'<div class="t">İmalat sanayii</div><div class="v">{pct(v_sue)}</div></div>']
    for code, val in son_sek.sort_index(key=lambda i: i.str[1:].astype(int)).items():
        tiles.append(f'<div class="tile" style="background:{div_color(val)}"><div class="c">{code}</div>'
                     f'<div class="t">{SEKTORLER[code][1]}</div><div class="v">{pct(val, sign=True)}</div></div>')
    st.markdown(f'<div class="grid">{"".join(tiles)}</div>', unsafe_allow_html=True)
    src("TÜİK, sanayi üretim endeksi (takvim etkisinden arındırılmış, 2021=100) · TCMB EVDS üzerinden")

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
        st.markdown(f'<div class="eyebrow">Üretim ve fiyat</div><div class="hero">{ad if len(ad) < 28 else SEKTORLER[kod][1]}</div>'
                    f'<p style="margin:1rem 0 .2rem 0;font-weight:600;font-size:.88rem">Sanayi üretimi, yıllık değişim · {ay(pe)}</p>'
                    + big_pct(ve, "neg" if ve < 0 else "pos"), unsafe_allow_html=True)
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
    stats([("Bir yıl önce", pct(ey.get(pe - 12, np.nan)), ay(pe - 12)),
           ("Son 12 ay ortalaması", pct(ort12.dropna().iloc[-1]) if ort12.notna().any() else "—", ""),
           ("Son 3 ay, önceki 3 aya göre", f'<span class="{cls(son3)}">{num(son3) if son3 < 0 else "+" + num(son3)} puan</span>', "ortalamalar")])
    if gor == "Endeks":
        f = line_chart([("Endeks (2021=100)", endeks, NAVY)], pctaxis=False, clip=False)
    elif gor == "12 ay ortalama, yıllık %":
        f = line_chart([("12 ay ortalama, yıllık %", ort12, NAVY)], clip=False)
    else:
        f = line_chart([("Yıllık %", ey, NAVY), ("12 ay ortalama", ort12, "#8a95a5")])
    st.plotly_chart(f, width="stretch", config=CFG)
    src("TÜİK, sanayi üretim endeksi · takvim etkisinden arındırılmış · uç aylar ölçeğe dahil "
        "edilmedi, değerleri grafiğin kenarında")
    with st.expander("Veri tablosu"):
        st.dataframe(pd.DataFrame({"Endeks": endeks, "Yıllık %": ey.round(1), "12 ay ort. %": ort12.round(1)})
                     .dropna(how="all").iloc[::-1].rename(index=str), width="stretch")

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
            f"TÜFE (genel) {pct(son_gecerli(tufe_y)[1])}")])
    if gor3 == "Endeks":
        f = line_chart([("Yİ-ÜFE (2003=100)", yi_s, NAVY),
                        ("TÜFE genel (2003=100)", M["tufe"], OCHRE)], pctaxis=False, clip=False)
    else:
        f = line_chart([("Yİ-ÜFE", yiufe_y, NAVY), ("TÜFE genel", tufe_y, OCHRE),
                        ("YD-ÜFE", ydufe_y, "#7f8c8d")], clip=False)
    st.plotly_chart(f, width="stretch", config=CFG)
    src("TÜİK, Yİ-ÜFE (2003=100), YD-ÜFE (2010=100), TÜFE (2003=100)")

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
with tab_tcmb:
    st.markdown(f'<div class="eyebrow">TCMB göstergeleri</div><div class="hero">İmalat sanayii</div>'
                f'<p style="margin:1rem 0 .2rem 0;font-weight:600;font-size:.88rem">Kapasite kullanım oranı · {ay(p_kko)}</p>'
                f'<div class="big neu"><span class="p">%</span>{num(v_kko)}</div>', unsafe_allow_html=True)
    rk_y = yoy(rek)
    st.markdown(f'<p class="lead" style="margin:1rem 0">Reel efektif kur bir yıl öncesinin '
                f'{"üzerinde" if rk_y.dropna().iloc[-1] > 0 else "altında"}: Türk lirasının reel olarak '
                f'{"değer kazanması ihracatçının fiyat rekabetini zorlaştırır." if rk_y.dropna().iloc[-1] > 0 else "değer kaybetmesi ihracatçının fiyat rekabetini destekler."}</p>',
                unsafe_allow_html=True)
    stats([("Reel efektif kur", num(v_rk), f"{ay(p_rk)} · 2025=100"),
           ("USD/TRY", num(v_us, 2), f"yıllık {pct(usd_y.dropna().iloc[-1], sign=True)}"),
           ("Kapasite kullanımı, 12 ay ort.", pct(kko.rolling(12).mean().dropna().iloc[-1]), "")])

    k12 = kko.rolling(12).mean()
    section("01", "Kapasite kullanım oranı",
            f"{ay(p_kko)} itibarıyla imalat sanayiinde kapasite kullanım oranı {pct(v_kko)}.")
    stats([("Bir yıl önce", pct(kko.get(p_kko - 12, np.nan)), ay(p_kko - 12)),
           ("Son 12 ay ortalaması", pct(k12.dropna().iloc[-1]), ""),
           ("Son 3 ay, önceki 3 aya göre", f"{num(kko.dropna().iloc[-3:].mean() - kko.dropna().iloc[-6:-3].mean(), 1)} puan", "ortalamalar")])
    f = line_chart([("Aylık", kko["2015":], NAVY), ("12 aylık ortalama", k12["2015":], "#8a95a5")])
    f.update_yaxes(tickformat=".0f")
    st.plotly_chart(f, width="stretch", config=CFG)
    src("TCMB EVDS, imalat sanayi kapasite kullanım oranı")

    section("02", "Reel efektif döviz kuru",
            f"{ay(p_rk)} itibarıyla Yİ-ÜFE bazlı reel efektif kur endeksi {num(v_rk)}; bir yıl öncesine göre "
            f"{pct(abs(rk_y.dropna().iloc[-1]))} {'yükseldi' if rk_y.dropna().iloc[-1] > 0 else 'düştü'}.")
    f = line_chart([("Reel efektif kur", rek["2015":], NAVY)], pctaxis=False, clip=False)
    f.add_hline(y=100, line=dict(color=LINE, dash="dot"))
    st.plotly_chart(f, width="stretch", config=CFG)
    src("TCMB EVDS, Yİ-ÜFE bazlı reel efektif kur · 2025=100; yükseliş TL'nin reel değer kazandığını gösterir")

    section("03", "Dolar kuru",
            f"{ay(p_us)} itibarıyla aylık ortalama dolar kuru {num(v_us)}; bir yıl öncesine göre "
            f"{pct(usd_y.dropna().iloc[-1])} yükseldi.")
    g = st.segmented_control("Görünüm", ["Düzey", "Yıllık %"], default="Düzey",
                             label_visibility="collapsed", key="g_usd")
    if g == "Yıllık %":
        f = line_chart([("USD/TRY, yıllık %", usd_y["2015":], NAVY)], clip=False)
    else:
        f = line_chart([("USD/TRY", USD["2015":], NAVY)], pctaxis=False, clip=False)
    st.plotly_chart(f, width="stretch", config=CFG)
    src("TCMB EVDS, USD/TRY döviz satış kuru · aylık ortalama")

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
