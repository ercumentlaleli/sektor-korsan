"""Sekme içeriğinden PowerPoint (pptx) sunumu üretir.

Uygulama her sekmeyi çizerken bölüm başlıklarını, açıklamaları, gösterge kutularını ve
Plotly grafiklerini bir listeye kaydeder (bkz. app.py: section, stats, grafik). Bu modül o
listeyi slaytlara çevirir. Grafikler resim değil, PowerPoint'in yerel (düzenlenebilir)
grafikleri olarak eklenir; böylece sunucuda tarayıcı ya da resim motoru gerekmez.
"""
from __future__ import annotations

import io
import math
import re
from datetime import date

import pandas as pd
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION, XL_MARKER_STYLE, XL_TICK_LABEL_POSITION
from pptx.enum.text import PP_ALIGN
from pptx.util import Emu, Inches, Pt

BG = RGBColor(0xF4, 0xEF, 0xE6)
INK = RGBColor(0x1D, 0x1D, 0x1B)
NAVY = RGBColor(0x1F, 0x3A, 0x5F)
MUTED = RGBColor(0x6F, 0x6A, 0x60)
RED = RGBColor(0xB5, 0x47, 0x2A)
SERIF, SANS = "Georgia", "Calibri"
W, H = Inches(13.333), Inches(7.5)
MAX_NOKTA = 160


def temiz(t) -> str:
    """HTML etiketlerini ve fazla boşlukları temizler."""
    t = re.sub(r"<br\s*/?>", " · ", str(t))
    t = re.sub(r"<[^>]+>", "", t)
    t = t.replace("&nbsp;", " ").replace("&amp;", "&")
    return re.sub(r"\s+", " ", t).strip()


def _renk(c) -> RGBColor | None:
    if isinstance(c, (list, tuple)) and c:
        c = c[0]
    if not isinstance(c, str):
        return None
    c = c.strip()
    if c.startswith("#") and len(c) >= 7:
        return RGBColor.from_string(c[1:7].upper())
    m = re.match(r"rgba?\((\d+),\s*(\d+),\s*(\d+)", c)
    if m:
        return RGBColor(*(int(x) for x in m.groups()))
    return None


def _arkaplan(slide) -> None:
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = BG


def _metin(slide, x, y, w, h, metin, boyut=14, renk=INK, kalin=False, yazi=SANS, hizala=None):
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = metin
    p.font.size, p.font.bold, p.font.name = Pt(boyut), kalin, yazi
    p.font.color.rgb = renk
    if hizala:
        p.alignment = hizala
    return tb


def tr_upper(t: str) -> str:
    return str(t).replace("i", "İ").replace("ı", "I").upper()


def _baslik(slide, ust: str, baslik: str) -> None:
    _metin(slide, Inches(.6), Inches(.35), Inches(12), Inches(.4), tr_upper(ust), 11, NAVY, True)
    _metin(slide, Inches(.6), Inches(.7), Inches(12), Inches(.8), baslik, 28, INK, yazi=SERIF)


def _kategori(x) -> str:
    if isinstance(x, (pd.Timestamp,)) or hasattr(x, "strftime"):
        return x.strftime("%Y-%m")
    s = str(x)
    if re.match(r"^\d{4}-\d{2}-\d{2}", s):
        return s[:7]
    return temiz(s)


def _deger(v):
    try:
        v = float(v)
        return None if math.isnan(v) or math.isinf(v) else v
    except (TypeError, ValueError):
        return None


def _grafik_ekle(slide, fig, x, y, w, h) -> bool:
    """Plotly figürünü yerel PowerPoint grafiğine çevirir. Desteklenmeyen tür (harita, ısı haritası) -> False."""
    izler = [t for t in fig.data if t.type in ("scatter", "bar")]
    # son değer etiketleri gibi tek noktalık yardımcı izleri at
    izler = [t for t in izler if t.x is not None and len(t.x) > 1 or (t.type == "bar")]
    if not izler:
        return False
    barlar = [t for t in izler if t.type == "bar"]
    if barlar:
        izler = barlar
        yatay = getattr(barlar[0], "orientation", None) == "h"
        yigin = getattr(fig.layout, "barmode", None) == "stack"
        if yatay:
            tur = XL_CHART_TYPE.BAR_STACKED if yigin else XL_CHART_TYPE.BAR_CLUSTERED
        else:
            tur = XL_CHART_TYPE.COLUMN_STACKED if yigin else XL_CHART_TYPE.COLUMN_CLUSTERED
    else:
        yatay, tur = False, XL_CHART_TYPE.LINE

    def eksenler(t):
        kat, val = (t.y, t.x) if yatay else (t.x, t.y)
        return list(kat if kat is not None else []), list(val if val is not None else [])

    kat0, _ = eksenler(izler[0])
    kategoriler = [_kategori(k) for k in kat0]
    adim = max(1, math.ceil(len(kategoriler) / MAX_NOKTA))
    secili = list(range(0, len(kategoriler), adim))
    if secili and secili[-1] != len(kategoriler) - 1:
        secili.append(len(kategoriler) - 1)
    cd = CategoryChartData()
    etiketler = [kategoriler[i] for i in secili]
    cd.categories = etiketler
    renkler, nokta_renk = [], []
    for i_, t in enumerate(izler):
        kat, val = eksenler(t)
        harita = {_kategori(k): _deger(v) for k, v in zip(kat, val)}
        ad = temiz(t.name) if t.name else (" " * (i_ + 1))  # adsız seri: "Seri 1" yazısı çıkmasın
        cd.add_series(ad, [harita.get(c) for c in etiketler])
        r = _renk(getattr(t.marker, "color", None)) if t.type == "bar" else _renk(getattr(t.line, "color", None))
        renkler.append(r)
        mc = getattr(t.marker, "color", None) if t.type == "bar" else None
        if mc is not None and not isinstance(mc, str) and len(mc) == len(kat):
            pr = {_kategori(k): _renk(c) for k, c in zip(kat, mc)}
            nokta_renk.append([pr.get(c) for c in etiketler])
        else:
            nokta_renk.append(None)
    gf = slide.shapes.add_chart(tur, x, y, w, h, cd)
    ch = gf.chart
    ch.font.size, ch.font.name = Pt(10), SANS
    ch.has_legend = len(izler) > 1
    if ch.has_legend:
        ch.legend.position = XL_LEGEND_POSITION.TOP
        ch.legend.include_in_layout = False
    for s_, r, pr in zip(ch.series, renkler, nokta_renk):
        if r is None:
            continue
        if tur == XL_CHART_TYPE.LINE:
            s_.format.line.color.rgb = r
            s_.format.line.width = Pt(2)
            s_.smooth = False
        else:
            s_.format.fill.solid()
            s_.format.fill.fore_color.rgb = r
            s_.invert_if_negative = False
            if pr:  # çubuk başına renk (ör. artış yeşil, düşüş kırmızı)
                for j, c in enumerate(pr):
                    if c is not None:
                        pt = s_.points[j]
                        pt.format.fill.solid()
                        pt.format.fill.fore_color.rgb = c
    if barlar:
        ch.category_axis.tick_label_position = XL_TICK_LABEL_POSITION.LOW
    if tur == XL_CHART_TYPE.LINE:
        for s_ in ch.series:
            s_.marker.style = XL_MARKER_STYLE.NONE
    if barlar and len(etiketler) <= 30:
        pl = ch.plots[0]
        pl.has_data_labels = True
        pl.data_labels.font.size = Pt(9)
        pl.data_labels.number_format = '#,##0.0'
        pl.data_labels.number_format_is_linked = False
    return True


def _gostergeler(slide, ogeler, y) -> None:
    n = max(len(ogeler), 1)
    gen = (W - Inches(1.2)) / n
    for i, (etiket, deger, notu) in enumerate(ogeler):
        x = Inches(.6) + int(gen * i)
        _metin(slide, x, y, int(gen) - Inches(.1), Inches(.3), temiz(etiket), 11, MUTED)
        _metin(slide, x, y + Inches(.3), int(gen) - Inches(.1), Inches(.6), temiz(deger), 24, NAVY, yazi=SERIF)
        if notu:
            _metin(slide, x, y + Inches(.9), int(gen) - Inches(.1), Inches(.3), temiz(notu), 10, MUTED)


def sunum_olustur(kayitlar: list[tuple], baslik: str, alt_baslik: str = "") -> bytes:
    """Kayıtları (bolum / gosterge / grafik / liste) slaytlara dönüştürür, pptx baytlarını döndürür."""
    prs = Presentation()
    prs.slide_width, prs.slide_height = W, H
    bos = prs.slide_layouts[6]

    s = prs.slides.add_slide(bos)
    _arkaplan(s)
    _metin(s, Inches(.8), Inches(2.3), Inches(11.5), Inches(.4), "SEKTÖR VERİ ATLASI", 13, NAVY, True)
    _metin(s, Inches(.8), Inches(2.8), Inches(11.5), Inches(1.4), baslik, 44, NAVY, yazi=SERIF)
    _metin(s, Inches(.8), Inches(4.3), Inches(11.5), Inches(.5), alt_baslik, 16, MUTED)
    _metin(s, Inches(.8), Inches(6.6), Inches(11.5), Inches(.4),
           f"Kaynak: TÜİK, TCMB, İSO, UN Comtrade · {date.today():%d.%m.%Y}", 10, MUTED)

    bolum_ad, bolum_aciklama, slayt, y_imlec = baslik, "", None, None

    def yeni_slayt(alt: str = ""):
        sl = prs.slides.add_slide(bos)
        _arkaplan(sl)
        _baslik(sl, baslik, bolum_ad + (f" · {alt}" if alt else ""))
        return sl

    for k in kayitlar:
        tur = k[0]
        if tur == "bolum":
            bolum_ad, bolum_aciklama = temiz(k[1]) or baslik, temiz(k[2])
            slayt = yeni_slayt()
            y_imlec = Inches(1.6)
            if bolum_aciklama:
                _metin(slayt, Inches(.6), y_imlec, Inches(12), Inches(1.6), bolum_aciklama, 15, INK)
                y_imlec += Inches(1.8)
        elif tur == "gosterge":
            if slayt is None or y_imlec is None or y_imlec > Inches(5.6):
                slayt, y_imlec = yeni_slayt(), Inches(1.6)
            _gostergeler(slayt, k[1], y_imlec)
            y_imlec += Inches(1.4)
        elif tur == "grafik":
            fig = k[1]
            # grafik bölüm slaytına sığıyorsa oraya, değilse yeni slayta
            if slayt is not None and y_imlec is not None and y_imlec <= Inches(3.6):
                x, y, w, h = Inches(.6), y_imlec, Inches(12.1), H - y_imlec - Inches(.4)
                hedef = slayt
            else:
                hedef = yeni_slayt()
                x, y, w, h = Inches(.6), Inches(1.6), Inches(12.1), Inches(5.5)
            if _grafik_ekle(hedef, fig, x, y, w, h):
                slayt, y_imlec = None, None  # sonraki öğe yeni slayta
            elif hedef is not slayt:
                _metin(hedef, Inches(.6), Inches(3.2), Inches(12), Inches(.6),
                       "Bu görsel (harita / ısı haritası) uygulamada etkileşimli olarak görüntülenebilir.", 14, MUTED)
        elif tur == "liste":
            sl = yeni_slayt(temiz(k[1]))
            tb = sl.shapes.add_textbox(Inches(.6), Inches(1.6), Inches(12.1), Inches(5.6))
            tf = tb.text_frame
            tf.word_wrap = True
            for i, (ust, metin) in enumerate(k[2][:12]):
                p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
                p.text = f"{metin}"
                p.font.size, p.font.name = Pt(14), SERIF
                p.font.color.rgb = INK
                if ust:
                    q = tf.add_paragraph()
                    q.text = ust
                    q.font.size, q.font.color.rgb = Pt(10), MUTED
            slayt, y_imlec = None, None

    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()
