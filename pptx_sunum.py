"""Sunum sekmesini düzenlenebilir PPTX'e çevirir (python-pptx; tarayıcıda görüntü yakalama yok).

Sunum sekmesindeki her slayt, ekrana çizilirken aynı içeriği bir `Sunum` kaydına da yazar (metin, kart, Plotly
grafiği, tablo, harita değerleri). İndirme düğmesine basılınca kayıt PowerPoint nesnelerine çevrilir:
- metinler metin kutusu, kartlar ve şeritler şekil,
- Plotly çubuk/çizgi/alan grafikleri PowerPoint'in kendi (düzenlenebilir, veri sayfalı) grafikleri,
- tablolar PowerPoint tablosu, haritalar il/ülke sınırlarından çizilen düzenlenebilir şekiller.

Slayt boyutu 16:9 (13,333 × 7,5 inç). Her slayt dikey akışla yerleşir: sabit yükseklikli bloklar (başlık şeridi,
paragraf, kartlar, not, kaynak) önce yerleşir, kalan yükseklik grafik/tablo satırlarına paylaştırılır.
"""
from __future__ import annotations

import html as _html
import io
import json
import math
import re
from pathlib import Path

import numpy as np

from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import (XL_CHART_TYPE, XL_LABEL_POSITION, XL_LEGEND_POSITION, XL_MARKER_STYLE,
                            XL_TICK_LABEL_POSITION, XL_TICK_MARK)
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

DATA = Path(__file__).parent / "data"
SW, SH = 13.333, 7.5            # slayt (inç)
ML, MR, MT, MB = .4, .4, .28, .22
W = SW - ML - MR
FONT = "Calibri"
PX_PT = .9                      # Plotly piksel yazı boyutu -> punto

R = dict(INK="#262626", NAVY="#203764", RED="#C0504D", TEAL="#305496", OCHRE="#8EA9DB", MUTED="#595959",
         LINE="#D9D9D9", CARD="#F2F2F2", BLUE="#305496", DARK="#222A35", PALE="#D9E1F2", WHITE="#FFFFFF")


# ---------------------------------------------------------------------------------------------- yardımcılar
def rgb(c: str | None, yedek: str = "#262626") -> RGBColor:
    c = (c or yedek).strip()
    if c.startswith("rgba") or c.startswith("rgb"):
        n = [float(x) for x in re.findall(r"[\d.]+", c)[:3]]
        return RGBColor(*[int(v) for v in n])
    c = c.lstrip("#")
    if len(c) == 3:
        c = "".join(ch * 2 for ch in c)
    try:
        return RGBColor.from_string(c.upper()[:6])
    except Exception:
        return RGBColor.from_string(yedek.lstrip("#"))


def karis(c1: str, c2: str, t: float) -> str:
    a = [int(c1.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]
    b = [int(c2.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]
    t = min(max(t, 0), 1)
    return "#" + "".join(f"{round(x + (y - x) * t):02X}" for x, y in zip(a, b))


def duz(s) -> str:
    """HTML etiketlerini atar, <br> -> satır sonu."""
    s = str(s or "")
    s = re.sub(r"<br\s*/?>", "\n", s)
    s = re.sub(r"<[^>]+>", "", s)
    return _html.unescape(s).replace("\xa0", " ")


def html_parcalar(s: str, renk: str, kalin: bool = False) -> list[tuple[str, dict]]:
    """Basit HTML -> [(metin, {kalin, renk, oran, alt, ust})]. b/strong, span (class pos/neg/p, style color/font-size),
    sub/sup ve br desteklenir; diğer etiketler atılır."""
    out, yigin = [], [dict(kalin=kalin, renk=renk, oran=1.0, alt=False, ust=False)]
    for parca in re.split(r"(<[^>]+>)", str(s or "")):
        if not parca:
            continue
        if parca.startswith("<"):
            t = parca.lower()
            if re.match(r"<br", t):
                out.append(("\n", dict(yigin[-1])))
                continue
            if t.startswith("</"):
                if len(yigin) > 1 and re.match(r"</(b|strong|span|sub|sup)\b", t):
                    yigin.pop()
                continue
            m = re.match(r"<(b|strong|span|sub|sup)\b(.*)", parca, re.S | re.I)
            if not m:
                continue
            st_ = dict(yigin[-1])
            ad, ozn = m.group(1).lower(), m.group(2)
            if ad in ("b", "strong"):
                st_["kalin"] = True
            if ad == "sub":
                st_["alt"] = True
            if ad == "sup":
                st_["ust"] = True
            k = re.search(r'class="([^"]*)"', ozn)
            if k:
                ks = k.group(1).split()
                if "pos" in ks:
                    st_["renk"] = R["TEAL"]
                if "neg" in ks:
                    st_["renk"] = R["RED"]
                if "p" in ks:
                    st_["oran"] *= .6
            stl = re.search(r'style="([^"]*)"', ozn)
            if stl:
                cc = re.search(r"(?<![-\w])color:\s*(#[0-9A-Fa-f]{3,6})", stl.group(1))
                if cc:
                    st_["renk"] = cc.group(1)
                fs = re.search(r"font-size:\s*([\d.]+)em", stl.group(1))
                if fs:
                    st_["oran"] *= float(fs.group(1))
                fsr = re.search(r"font-size:\s*([\d.]+)rem", stl.group(1))
                if fsr:
                    st_["oran"] *= float(fsr.group(1)) / 1.0
                if re.search(r"font-weight:\s*(6|7|8|9)00", stl.group(1)):
                    st_["kalin"] = True
            yigin.append(st_)
        else:
            out.append((_html.unescape(parca).replace("\xa0", " "), dict(yigin[-1])))
    return out


def metin_kutusu(sl, x, y, w, h, s, boy=11.0, renk=None, kalin=False, hiza="l", dikey="t", satir=1.15,
                 italik=False, html=True):
    tb = sl.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = {"t": MSO_ANCHOR.TOP, "m": MSO_ANCHOR.MIDDLE, "b": MSO_ANCHOR.BOTTOM}[dikey]
    paragrafa_yaz(tf.paragraphs[0], tf, s, boy, renk or R["INK"], kalin, hiza, satir, italik, html)
    return tb


def paragrafa_yaz(p, tf, s, boy, renk, kalin=False, hiza="l", satir=1.15, italik=False, html=True, link=None):
    parcalar = html_parcalar(s, renk, kalin) if html else [(str(s), dict(kalin=kalin, renk=renk, oran=1.0,
                                                                          alt=False, ust=False))]
    p.alignment = {"l": PP_ALIGN.LEFT, "c": PP_ALIGN.CENTER, "r": PP_ALIGN.RIGHT}[hiza]
    p.line_spacing = satir
    for metin, st_ in parcalar:
        satirlar = metin.split("\n")
        for i, sat in enumerate(satirlar):
            if i > 0:
                p = tf.add_paragraph()
                p.alignment = {"l": PP_ALIGN.LEFT, "c": PP_ALIGN.CENTER, "r": PP_ALIGN.RIGHT}[hiza]
                p.line_spacing = satir
            if not sat:
                continue
            r_ = p.add_run()
            r_.text = sat
            f = r_.font
            f.name, f.size, f.bold, f.italic = FONT, Pt(boy * st_["oran"]), st_["kalin"], italik
            f.color.rgb = rgb(st_["renk"])
            if st_.get("alt") or st_.get("ust"):
                r_._r.get_or_add_rPr().set("baseline", "-25000" if st_.get("alt") else "30000")
            if link:
                r_.hyperlink.address = link
    return p


def kutu(sl, x, y, w, h, dolgu, cizgi=None, yuvarlak=.06, sekil=MSO_SHAPE.ROUNDED_RECTANGLE):
    s = sl.shapes.add_shape(sekil, Inches(x), Inches(y), Inches(w), Inches(h))
    if sekil == MSO_SHAPE.ROUNDED_RECTANGLE:
        s.adjustments[0] = yuvarlak
    if dolgu:
        s.fill.solid()
        s.fill.fore_color.rgb = rgb(dolgu)
    else:
        s.fill.background()
    if cizgi:
        s.line.color.rgb = rgb(cizgi)
        s.line.width = Pt(.75)
    else:
        s.line.fill.background()
    s.shadow.inherit = False
    s.text_frame.text = ""
    return s


def cizgi(sl, x1, y1, x2, y2, renk, kalinlik=.75):
    c = sl.shapes.add_connector(1, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    c.line.color.rgb = rgb(renk)
    c.line.width = Pt(kalinlik)
    return c


def yukseklik_tahmini(s: str, genislik: float, boy: float, satir=1.18) -> float:
    """Metnin kutu yüksekliği tahmini (inç): Calibri ortalama karakter genişliği ~0,5 em."""
    metin = duz(s)
    kar_gen = boy / 72 * .5
    n_kar = max(int(genislik / kar_gen), 10)
    n_satir = sum(max(1, math.ceil(len(p) / n_kar)) for p in metin.split("\n"))
    return n_satir * boy / 72 * satir + .02


# ---------------------------------------------------------------------------------------------- kayıt
class Sunum:
    """Sunum sekmesinin kaydı: slaytlar ve blokları. olustur() PPTX baytlarını döndürür."""

    def __init__(self):
        self.slaytlar: list[dict] = []

    # --- kayıt arayüzü
    def slayt(self, no: int, baslik: str):
        self.slaytlar.append(dict(no=no, baslik=baslik, bloklar=[]))
        return self

    def _ekle(self, **b):
        if self.slaytlar:
            self.slaytlar[-1]["bloklar"].append(b)
        return self

    def paragraf(self, html: str, boy: float = 11.0):
        return self._ekle(tur="paragraf", html=html, boy=boy)

    def altbaslik(self, metin: str):
        return self._ekle(tur="altbaslik", metin=metin)

    def kartlar(self, ogeler: list[tuple], stil: str = "stat"):
        """stat: (etiket, değer_html, not_html). kpi: (etiket, değer_html, not_html, seri_listesi, renk, seçili)."""
        return self._ekle(tur="kartlar", ogeler=ogeler, stil=stil)

    def satir(self, kolonlar: list[list[tuple]], oran: list[float] | None = None, agirlik: float = 1.0,
              h: float | None = None, genislik_cm: list[float] | None = None, yapis: bool = False):
        """Esnek satır: kolon öğeleri ("eyebrow", t) ("sub", t) ("baslik2", t) ("metin", html, boy) ("buyuk", etiket,
        değer_html, alt_html) ("fig", plotly_fig) ("tablo", başlıklar, satırlar, hizalar, genişlik_oranları)
        ("harita", tür, değerler, biçim, etiket_n) ("haberler", liste) ("bosluk", inç)."""
        return self._ekle(tur="satir", kolonlar=kolonlar, oran=oran or [1] * len(kolonlar), agirlik=agirlik, h=h,
                          genislik_cm=genislik_cm, yapis=yapis)

    def karolar(self, ogeler: list[dict], sutun: int = 4):
        return self._ekle(tur="karolar", ogeler=ogeler, sutun=sutun)

    def riskler(self, ogeler: list[tuple], sutun: int = 4):
        return self._ekle(tur="riskler", ogeler=ogeler, sutun=sutun)

    def not_(self, html: str):
        return self._ekle(tur="not", html=html)

    def kaynak(self, metin: str):
        return self._ekle(tur="kaynak", metin=metin)

    # --- üretim
    def olustur(self) -> bytes:
        prs = Presentation()
        prs.slide_width, prs.slide_height = Inches(SW), Inches(SH)
        bos = prs.slide_layouts[6]
        for s in self.slaytlar:
            sl = prs.slides.add_slide(bos)
            Slayt(sl, s).ciz()
        b = io.BytesIO()
        prs.save(b)
        return b.getvalue()


SABIT = {"altbaslik": .34, "kaynak": None, "not": None}


class Slayt:
    def __init__(self, sl, kayit: dict):
        self.sl, self.k = sl, kayit
        self.y = MT

    # yükseklik tahminleri
    def _sabit_h(self, b) -> float | None:
        t = b["tur"]
        if t == "paragraf":
            return yukseklik_tahmini(b["html"], W, b["boy"], 1.2) + .04
        if t == "altbaslik":
            return .34
        if t == "kartlar":
            return 1.28 if b["stil"] == "kpi" else .72
        if t == "not":
            return yukseklik_tahmini(b["html"], W, 8.5) + .02
        if t == "kaynak":
            return yukseklik_tahmini(b["metin"], W, 7.5) + .02
        if t == "satir" and b.get("h"):
            return b["h"]
        return None

    def ciz(self):
        sl = self.sl
        # başlık şeridi: her slaytta aynı yer ve kalınlık
        kutu(sl, ML, MT, W, .46, R["DARK"], yuvarlak=.18)
        daire = sl.shapes.add_shape(MSO_SHAPE.OVAL, Inches(ML + .1), Inches(MT + .07), Inches(.32), Inches(.32))
        daire.fill.background()
        daire.line.color.rgb = rgb("#FFFFFF")
        daire.line.width = Pt(1.25)
        daire.shadow.inherit = False
        tf = daire.text_frame
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        paragrafa_yaz(tf.paragraphs[0], tf, str(self.k["no"]), 10, "#FFFFFF", True, "c")
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        metin_kutusu(sl, ML + .55, MT, W - .7, .46, self.k["baslik"], 15, "#FFFFFF", True, dikey="m", html=False)
        self.y = MT + .46 + .14

        bloklar = self.k["bloklar"]
        kaynaklar = [b for b in bloklar if b["tur"] == "kaynak"]
        akis = [b for b in bloklar if b["tur"] != "kaynak"]
        kaynak_h = sum(self._sabit_h(b) for b in kaynaklar)
        alt = SH - MB - kaynak_h - (.06 if kaynaklar else 0)
        bosluk = .1
        sabit = sum(self._sabit_h(b) or 0 for b in akis) + bosluk * max(len(akis) - 1, 0)
        esnek = [b for b in akis if self._sabit_h(b) is None]
        kalan = max(alt - self.y - sabit, .6 * len(esnek))
        top_ag = sum(b.get("agirlik", 1.0) for b in esnek) or 1
        for b in akis:
            h = self._sabit_h(b)
            if h is None:
                h = kalan * b.get("agirlik", 1.0) / top_ag
            if b.get("yapis"):           # bir önceki alt başlığın çizgisinden başla
                self.y -= bosluk + .04
            getattr(self, "_" + b["tur"])(b, self.y, h)
            self.y += h + bosluk
        ky = SH - MB - kaynak_h
        for b in kaynaklar:
            hh = self._sabit_h(b)
            metin_kutusu(sl, ML, ky, W, hh, "Kaynak: " + b["metin"], 7.5, R["MUTED"], italik=True, html=False)
            ky += hh

    # --- bloklar
    def _paragraf(self, b, y, h):
        metin_kutusu(self.sl, ML, y, W * .97, h, b["html"], b["boy"], satir=1.12)

    def _altbaslik(self, b, y, h):
        metin_kutusu(self.sl, ML, y + .02, W, .26, b["metin"], 11.5, R["INK"], True, html=False)
        cizgi(self.sl, ML, y + .3, ML + W, y + .3, R["LINE"], 1)

    def _not(self, b, y, h):
        metin_kutusu(self.sl, ML, y, W, h, b["html"], 8.5, R["MUTED"])

    def _kartlar(self, b, y, h):
        og = b["ogeler"]
        n = len(og)
        ara = .12 if b["stil"] == "kpi" else .2
        kw = (W - ara * (n - 1)) / n
        for i, o in enumerate(og):
            x = ML + i * (kw + ara)
            if b["stil"] == "kpi":
                etiket, deger, not_, seri, renk, secili = o
                kutu(self.sl, x, y, kw, h, R["PALE"] if secili else R["CARD"], yuvarlak=.08)
                if secili:
                    kutu(self.sl, x, y, kw, .04, R["NAVY"], sekil=MSO_SHAPE.RECTANGLE)
                sp_w, sp_h = 2.8 / 2.54, 2.3 / 2.54          # kıvılcım grafiği: 2,8 × 2,3 cm
                tw = kw - sp_w - .12                          # soldaki metin sütunu
                metin_kutusu(self.sl, x + .08, y + .07, tw, .3, etiket, 7.5, R["MUTED"], True, satir=1.0)
                metin_kutusu(self.sl, x + .08, y + .38, tw, .3, deger, 14, renk, True)
                metin_kutusu(self.sl, x + .08, y + .7, tw, h - .74, not_, 6.5, R["MUTED"], satir=1.0)
                if seri is not None and len(seri) > 1:
                    lo_, hi_ = float(min(seri)), float(max(seri))
                    pay_ = (hi_ - lo_) * .08 or 1
                    cizgi_grafigi(self.sl, x + kw - sp_w, y + (h - sp_h) / 2, sp_w, sp_h, seri, renk,
                                  rng=[lo_ - pay_, hi_ + pay_])
            else:
                etiket, deger, not_ = o[:3]
                metin_kutusu(self.sl, x, y, kw, .22, etiket, 9, R["MUTED"], True)
                metin_kutusu(self.sl, x, y + .22, kw, .34, deger, 18, R["NAVY"], True)
                metin_kutusu(self.sl, x, y + .56, kw, h - .56, not_, 8, R["MUTED"])

    def _karolar(self, b, y, h):
        og, n = b["ogeler"], b["sutun"]
        satir_n = math.ceil(len(og) / n)
        ara = .08
        kw, kh = (W - ara * (n - 1)) / n, (h - ara * (satir_n - 1)) / satir_n
        for i, o in enumerate(og):
            x = ML + (i % n) * (kw + ara)
            yy = y + (i // n) * (kh + ara)
            s = kutu(self.sl, x, yy, kw, kh, o["dolgu"], cizgi=o.get("cerceve"), yuvarlak=.08)
            if o.get("cerceve"):
                s.line.width = Pt(1.5)
            metin_kutusu(self.sl, x + .1, yy + .05, kw - .2, .16, o["ust"], 6.5, R["INK"], True, hiza="r")
            metin_kutusu(self.sl, x + .1, yy + kh * .3, kw - .2, .22, o["ad"], 10, R["INK"])
            metin_kutusu(self.sl, x + .1, yy + kh - .4, kw * .5, .34, o["deger"], 15, R["INK"], True, dikey="b")
            metin_kutusu(self.sl, x + kw * .4, yy + kh - .4, kw * .6 - .1, .34, o["sag"], 11, R["INK"], True,
                         hiza="r", dikey="b")

    def _riskler(self, b, y, h):
        og, n = b["ogeler"], b["sutun"]
        satir_n = math.ceil(len(og) / n)
        ara = .1
        kw, kh = (W - ara * (n - 1)) / n, (h - ara * (satir_n - 1)) / satir_n
        for i, (bas, etk, mtn) in enumerate(og):
            x = ML + (i % n) * (kw + ara)
            yy = y + (i // n) * (kh + ara)
            firsat = etk == "Fırsat"
            kutu(self.sl, x, yy, kw, kh, "#F3F8F5" if firsat else R["CARD"], yuvarlak=.05)
            renk = "#2E6B4F" if firsat else R["NAVY"]
            et = kutu(self.sl, x + kw - .95, yy + .08, .85, .17, "#E3EFE9" if firsat else R["PALE"], yuvarlak=.2)
            tf = et.text_frame
            tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
            tf.vertical_anchor = MSO_ANCHOR.MIDDLE
            paragrafa_yaz(tf.paragraphs[0], tf, etk.upper(), 6, renk, True, "c", html=False)
            metin_kutusu(self.sl, x + .1, yy + .07, kw - 1.1, .36,
                         f'<span style="color:{"#2E6B4F" if firsat else R["RED"]}">{i + 1:02d}</span> {bas}', 9,
                         R["INK"], True)
            metin_kutusu(self.sl, x + .1, yy + .45, kw - .2, kh - .5, mtn, 7.6, R["INK"], satir=1.1, html=False)

    def _satir(self, b, y, h):
        if b.get("genislik_cm"):        # sabit genişlikler: ilk kolon sola, son kolon sağa dayalı
            gen = [g / 2.54 for g in b["genislik_cm"]]
            ara = (W - sum(gen)) / max(len(gen) - 1, 1)
            x = ML
            for kol, g in zip(b["kolonlar"], gen):
                self._kolon(kol, x, y, g, h)
                x += g + ara
            return
        oran = b["oran"]
        ara = .25
        top = sum(oran)
        gen = [(W - ara * (len(oran) - 1)) * o / top for o in oran]
        x = ML
        for kol, g in zip(b["kolonlar"], gen):
            self._kolon(kol, x, y, g, h)
            x += g + ara

    def _kolon(self, kol, x, y, w, h):
        sabit_h = {"eyebrow": .24, "sub": .2, "baslik2": .34, "bosluk": None}

        def oh(o):
            t = o[0]
            if t in ("eyebrow", "sub", "baslik2"):
                return sabit_h[t] if t != "sub" else yukseklik_tahmini(o[1], w, 8) + .02
            if t == "bosluk":
                return o[1]
            if t == "metin":
                if len(o) > 3 and o[3]:          # sabit yükseklik (inç)
                    return o[3]
                return yukseklik_tahmini(o[1], w, o[2] if len(o) > 2 else 10.5, 1.2) + .04
            if t == "buyuk":
                return .78 + (yukseklik_tahmini(o[3], w, 10.5, 1.2) if len(o) > 3 and o[3] else 0)
            return None
        sabit = sum(oh(o) or 0 for o in kol)
        esnek = [o for o in kol if oh(o) is None]
        eh = max(h - sabit, .5) / max(len(esnek), 1)
        yy = y
        for o in kol:
            hh = oh(o) or eh
            t = o[0]
            if t == "eyebrow":
                metin_kutusu(self.sl, x, yy, w, hh, o[1].upper(), 8, R["BLUE"], True, html=False)
            elif t == "sub":
                metin_kutusu(self.sl, x, yy, w, hh, o[1], 8, R["MUTED"])
            elif t == "baslik2":
                metin_kutusu(self.sl, x, yy, w, .26, o[1], 11, R["NAVY"], True, html=False)
                cizgi(self.sl, x, yy + .29, x + w, yy + .29, R["NAVY"], 1.5)
            elif t == "metin":   # ("metin", html, boy[, sabit_yükseklik_inç[, dikey_kaydırma_inç]])
                dy = o[4] if len(o) > 4 and o[4] else 0
                metin_kutusu(self.sl, x, yy + dy, w, hh, o[1], o[2] if len(o) > 2 else 10.5, satir=1.12)
            elif t == "buyuk":
                metin_kutusu(self.sl, x, yy, w, .24, o[1], 10, R["INK"], True)
                metin_kutusu(self.sl, x, yy + .22, w, .52, o[2], 30, R["NAVY"], True)
                if len(o) > 3 and o[3]:
                    metin_kutusu(self.sl, x, yy + .78, w, hh - .78, o[3], 10.5, satir=1.15)
            elif t == "fig":
                grafik_ekle(self.sl, o[1], x, yy, w, hh)
            elif t == "tablo":
                tablo_ekle(self.sl, x, yy, w, hh, *o[1:])
            elif t == "harita":
                harita_ekle(self.sl, x, yy, w, hh, *o[1:])
            elif t == "haberler":
                haber_listesi(self.sl, x, yy, w, hh, o[1])
            elif t == "haber_tablosu":
                haber_tablosu(self.sl, x, yy, w, hh, o[1])
            elif t == "ic":   # iç satır: ("ic", [kolon, kolon…], oranlar[, genişlikler_cm (None: kalan)])
                ara = .15
                top = sum(o[2])
                xx = x
                sabit_gen = o[3] if len(o) > 3 and o[3] else None
                if sabit_gen:
                    kalan_w = w - ara * (len(o[1]) - 1) - sum(g / 2.54 for g in sabit_gen if g)
                    n_bos = sum(1 for g in sabit_gen if not g) or 1
                for k_i, (ik, io) in enumerate(zip(o[1], o[2])):
                    if sabit_gen:
                        ig = sabit_gen[k_i] / 2.54 if sabit_gen[k_i] else kalan_w / n_bos
                    else:
                        ig = (w - ara * (len(o[1]) - 1)) * io / top
                    self._kolon(ik, xx, yy, ig, hh)
                    xx += ig + ara
            yy += hh


# ---------------------------------------------------------------------------------------------- grafikler
def _renkler(marker_color, n) -> list:
    if marker_color is None:
        return [None] * n
    if isinstance(marker_color, str):
        return [marker_color] * n
    mc = list(marker_color)
    return (mc + [mc[-1]] * n)[:n] if mc else [None] * n


def _yazi_boyu(tr, yedek=10.5):
    try:
        return float(tr.textfont.size or yedek) * PX_PT
    except Exception:
        return yedek * PX_PT


def _ortak_eksen(ch, yazi=8.5, gizli_deger=True, ters=False, alt_etiket=True):
    ch.has_title = False
    ch.font.name = FONT
    ch.font.size = Pt(yazi)
    ch.font.color.rgb = rgb(R["INK"])
    try:
        va = ch.value_axis
        va.has_major_gridlines = False
        va.visible = not gizli_deger
        va.major_tick_mark = XL_TICK_MARK.NONE
        va.format.line.fill.background()
    except Exception:
        pass
    try:
        ca = ch.category_axis
        ca.major_tick_mark = XL_TICK_MARK.NONE
        ca.has_major_gridlines = False
        ca.format.line.color.rgb = rgb(R["LINE"])
        ca.tick_labels.font.size = Pt(yazi)
        ca.tick_labels.font.color.rgb = rgb(R["INK"])
        if alt_etiket:
            ca.tick_label_position = XL_TICK_LABEL_POSITION.LOW
        if ters:
            ca.reverse_order = True
    except Exception:
        pass


def _aralik(ch, rng):
    try:
        if rng and rng[0] is not None and rng[1] is not None:
            ch.value_axis.minimum_scale = float(rng[0])
            ch.value_axis.maximum_scale = float(rng[1])
    except Exception:
        pass


def _ters_cevirme(ser_el, i):
    """Serideki i. noktanın (c:dPt) negatif değerde rengini tersine çevirmesini kapatır."""
    for dpt in ser_el.findall(qn("c:dPt")):
        idx = dpt.find(qn("c:idx"))
        if idx is not None and idx.get("val") == str(i):
            if dpt.find(qn("c:invertIfNegative")) is None:
                el = dpt.makeelement(qn("c:invertIfNegative"), {"val": "0"})
                idx.addnext(el)
            return


def cubuk_grafigi(sl, x, y, w, h, kategoriler, seriler, yatay=False, yigin=False, bosluk=.3, ters=False,
                  rng=None, lejant=False, yazi=8.5):
    """seriler: [dict(ad, degerler, renkler, etiketler, etiket_boy)]."""
    cd = CategoryChartData()
    cd.categories = kategoriler
    for s in seriler:
        cd.add_series(s["ad"] or " ", [None if v is None or (isinstance(v, float) and math.isnan(v)) else float(v)
                                       for v in s["degerler"]])
    if yatay:
        tur = XL_CHART_TYPE.BAR_STACKED if yigin else XL_CHART_TYPE.BAR_CLUSTERED
    else:
        tur = XL_CHART_TYPE.COLUMN_STACKED if yigin else XL_CHART_TYPE.COLUMN_CLUSTERED
    gf = sl.shapes.add_chart(tur, Inches(x), Inches(y), Inches(w), Inches(h), cd)
    ch = gf.chart
    ch.has_legend = lejant
    if lejant:
        ch.legend.position = XL_LEGEND_POSITION.TOP
        ch.legend.include_in_layout = False
        ch.legend.font.size = Pt(yazi)
    pl = ch.plots[0]
    pl.gap_width = int(max(min(bosluk / max(1 - bosluk, .05) * 100, 400), 10))
    pl.overlap = 100 if yigin else (-5 if len(seriler) > 1 else 0)
    pl.vary_by_categories = False
    _ortak_eksen(ch, yazi, True, ters)
    tum = [float(v) for s in seriler for v in s["degerler"] if v is not None and not
           (isinstance(v, float) and math.isnan(v))]
    if yigin and seriler:
        n_ = len(seriler[0]["degerler"])
        tum = [sum(float(s["degerler"][i] or 0) for s in seriler) for i in range(n_)] + [0.0]
    if tum and not yigin:
        lo, hi = min(min(tum), 0.0), max(max(tum), 0.0)
        aralik = (hi - lo) or 1.0
        en_uzun = max((len(e) for s in seriler for e in (s.get("etiketler") or []) if e), default=0)
        if yatay:
            # çizim alanı ~ grafiğin %62'si (kategori adları solda); etiket genişliği oranı kadar pay bırak
            et_w = en_uzun * yazi / 72 * .6
            f = min(et_w / max(w * .62, .5), .55)
        else:
            f = .16 if en_uzun else .05
        pay = aralik * f / max(1 - f, .3)
        alt_ = lo - (pay if lo < 0 else 0)
        ust_ = hi + (pay if hi > 0 else 0)
        rng = [alt_, ust_]
    _aralik(ch, rng)
    for s, ser in zip(seriler, pl.series):
        ser.invert_if_negative = False
        rk = s.get("renkler") or [None] * len(s["degerler"])
        tek = len(set(rk)) == 1 and rk[0]
        if tek:
            ser.format.fill.solid()
            ser.format.fill.fore_color.rgb = rgb(rk[0])
        for i, v in enumerate(s["degerler"]):
            pt = ser.points[i]
            if not tek and rk[i]:
                pt.format.fill.solid()
                pt.format.fill.fore_color.rgb = rgb(rk[i])
                _ters_cevirme(ser._element, i)
            et = (s.get("etiketler") or [None] * len(s["degerler"]))[i]
            if et:
                et = et.replace(" ", "\u00a0")
                dl = pt.data_label
                tf = dl.text_frame
                tf.text = et
                tf._txBody.find(qn("a:bodyPr")).set("wrap", "none")
                for p in tf.paragraphs:
                    for r_ in p.runs:
                        r_.font.size = Pt(s.get("etiket_boy", yazi))
                        r_.font.color.rgb = rgb(s.get("etiket_renk", R["INK"]))
                        r_.font.name = FONT
                dl.position = XL_LABEL_POSITION.CENTER if yigin else XL_LABEL_POSITION.OUTSIDE_END
    return ch


def cizgi_grafigi(sl, x, y, w, h, degerler, renk, kategoriler=None, etiketler=None, alan=False, rng=None,
                  eksen=False, yazi=8, isaret=False):
    v = [None if d is None or (isinstance(d, float) and math.isnan(d)) else float(d) for d in degerler]
    cd = CategoryChartData()
    cd.categories = kategoriler or [str(i) for i in range(len(v))]
    cd.add_series(" ", v)
    tur = XL_CHART_TYPE.AREA if alan else (XL_CHART_TYPE.LINE_MARKERS if isaret else XL_CHART_TYPE.LINE)
    gf = sl.shapes.add_chart(tur, Inches(x), Inches(y), Inches(w), Inches(h), cd)
    ch = gf.chart
    ch.has_legend = False
    _ortak_eksen(ch, yazi, not eksen, alt_etiket=False)
    if not eksen:
        try:
            ch.category_axis.visible = False
        except Exception:
            pass
    _aralik(ch, rng)
    ser = ch.plots[0].series[0]
    if alan:
        ser.format.fill.solid()
        ser.format.fill.fore_color.rgb = rgb("#E9EDF5")
        ser.format.line.color.rgb = rgb(renk)
        ser.format.line.width = Pt(1.75)
    else:
        ser.format.line.color.rgb = rgb(renk)
        ser.format.line.width = Pt(1.25 if not isaret else 1.75)
        ser.smooth = False
        if isaret:
            ser.marker.style = XL_MARKER_STYLE.CIRCLE
            ser.marker.size = 5
            ser.marker.format.fill.solid()
            ser.marker.format.fill.fore_color.rgb = rgb(renk)
            ser.marker.format.line.color.rgb = rgb(renk)
        else:
            ser.marker.style = XL_MARKER_STYLE.NONE
    if etiketler:
        for i, et in enumerate(etiketler):
            if et:
                dl = ser.points[i].data_label
                dl.text_frame.text = et
                dl.text_frame._txBody.find(qn("a:bodyPr")).set("wrap", "none")
                for p in dl.text_frame.paragraphs:
                    for r_ in p.runs:
                        r_.font.size = Pt(yazi)
                        r_.font.color.rgb = rgb(renk)
                dl.position = XL_LABEL_POSITION.ABOVE
    return ch


def karma_grafik(sl, x, y, w, h, kategoriler, seriler, cizgi_s, yazi=8.5):
    """Yığılmış sütun + çizgi (ikincil eksen) tek bir PowerPoint grafiği. Tüm seriler aynı veri sayfasındadır;
    çizgi serisi çubuk grafiğinden alınıp ikincil eksenli bir çizgi grafiğine taşınır."""
    tum = seriler + [dict(ad=cizgi_s["ad"], degerler=cizgi_s["degerler"])]
    cd = CategoryChartData()
    cd.categories = kategoriler
    for s in tum:
        cd.add_series(s["ad"] or " ", [None if v is None else float(v) for v in s["degerler"]])
    gf = sl.shapes.add_chart(XL_CHART_TYPE.COLUMN_STACKED, Inches(x), Inches(y), Inches(w), Inches(h), cd)
    ch = gf.chart
    ch.has_legend = True
    ch.legend.position = XL_LEGEND_POSITION.TOP
    ch.legend.include_in_layout = False
    ch.legend.font.size = Pt(yazi)
    pl = ch.plots[0]
    pl.gap_width, pl.overlap = 55, 100
    _ortak_eksen(ch, yazi, True)
    yigin_top = [sum(float(s["degerler"][i] or 0) for s in seriler) for i in range(len(kategoriler))]
    ch.value_axis.minimum_scale, ch.value_axis.maximum_scale = 0, max(yigin_top) * 1.9
    for s, ser in zip(seriler, pl.series):
        ser.invert_if_negative = False
        rk = (s.get("renkler") or [R["NAVY"]])[0] or R["NAVY"]
        ser.format.fill.solid()
        ser.format.fill.fore_color.rgb = rgb(rk)
        for i, et in enumerate(s.get("etiketler") or []):
            if et:
                dl = ser.points[i].data_label
                dl.text_frame.text = et
                dl.text_frame._txBody.find(qn("a:bodyPr")).set("wrap", "none")
                for p in dl.text_frame.paragraphs:
                    for r_ in p.runs:
                        r_.font.size = Pt(s.get("etiket_boy", yazi))
                        r_.font.color.rgb = rgb(s.get("etiket_renk", R["INK"]))
                dl.position = XL_LABEL_POSITION.CENTER
    # --- çizgi serisini ikincil eksenli lineChart'a taşı
    plotArea = ch._chartSpace.chart.plotArea
    bar = plotArea.find(qn("c:barChart"))
    ser_el = bar.findall(qn("c:ser"))[-1]
    bar.remove(ser_el)
    for tag in ("c:invertIfNegative", "c:shape", "c:dLbls"):
        for el in ser_el.findall(qn(tag)):
            ser_el.remove(el)
    E = lambda tag, **a: plotArea.makeelement(qn(tag), {k: str(v) for k, v in a.items()})
    # çizgi biçimi
    renk = cizgi_s["renk"].lstrip("#").upper()
    spPr = ser_el.find(qn("c:spPr"))
    if spPr is not None:
        ser_el.remove(spPr)
    spPr = E("c:spPr")
    ln = spPr.makeelement(qn("a:ln"), {"w": "22225"})
    sf = ln.makeelement(qn("a:solidFill"), {})
    sf.append(sf.makeelement(qn("a:srgbClr"), {"val": renk}))
    ln.append(sf)
    spPr.append(ln)
    marker = E("c:marker")
    marker.append(E("c:symbol", val="circle"))
    marker.append(E("c:size", val=5))
    mSp = E("c:spPr")
    mf = mSp.makeelement(qn("a:solidFill"), {})
    mf.append(mf.makeelement(qn("a:srgbClr"), {"val": renk}))
    mSp.append(mf)
    mln = mSp.makeelement(qn("a:ln"), {})
    mlf = mln.makeelement(qn("a:solidFill"), {})
    mlf.append(mlf.makeelement(qn("a:srgbClr"), {"val": renk}))
    mln.append(mlf)
    mSp.append(mln)
    marker.append(mSp)
    tx = ser_el.find(qn("c:tx"))
    (tx if tx is not None else ser_el.find(qn("c:order"))).addnext(spPr)
    spPr.addnext(marker)
    # veri etiketleri (değerler üstte)
    if cizgi_s.get("etiketler"):
        dLbls = E("c:dLbls")
        for i, et in enumerate(cizgi_s["etiketler"]):
            if not et:
                continue
            d = E("c:dLbl")
            d.append(E("c:idx", val=i))
            txx = E("c:tx")
            rich = E("c:rich")
            rich.append(rich.makeelement(qn("a:bodyPr"), {"wrap": "none"}))
            rich.append(rich.makeelement(qn("a:lstStyle"), {}))
            ap = rich.makeelement(qn("a:p"), {})
            ar = ap.makeelement(qn("a:r"), {})
            rpr = ar.makeelement(qn("a:rPr"), {"lang": "tr-TR", "sz": str(int(yazi * 100)), "b": "0"})
            rf = rpr.makeelement(qn("a:solidFill"), {})
            rf.append(rf.makeelement(qn("a:srgbClr"), {"val": renk}))
            rpr.append(rf)
            ar.append(rpr)
            at = ar.makeelement(qn("a:t"), {})
            at.text = et
            ar.append(at)
            ap.append(ar)
            rich.append(ap)
            txx.append(rich)
            d.append(txx)
            d.append(E("c:dLblPos", val="t"))
            for tag in ("c:showLegendKey", "c:showVal", "c:showCatName", "c:showSerName", "c:showPercent",
                        "c:showBubbleSize"):
                d.append(E(tag, val=1 if tag == "c:showVal" else 0))
            dLbls.append(d)
        for tag in ("c:showLegendKey", "c:showVal", "c:showCatName", "c:showSerName", "c:showPercent",
                    "c:showBubbleSize"):
            dLbls.append(E(tag, val=0))
        marker.addnext(dLbls)
    ser_el.append(E("c:smooth", val=0))
    line = E("c:lineChart")
    line.append(E("c:grouping", val="standard"))
    line.append(E("c:varyColors", val=0))
    line.append(ser_el)
    line.append(E("c:marker", val=1))
    line.append(E("c:axId", val=50010))
    line.append(E("c:axId", val=50020))
    bar.addnext(line)
    # ikincil eksenler: görünmez kategori ekseni + sağda değer ekseni (yüzde)
    vals = cizgi_s["degerler"]
    aralik = (max(vals) - min(vals)) or 2
    alt_, ust_ = 0, max(vals) * 1.15     # sağ eksen sıfırdan; çizgi çubukların üstündeki bantta kalır
    son_eksen = plotArea.findall(qn("c:valAx"))[-1]
    cat2 = E("c:catAx")
    for el in (E("c:axId", val=50010), ):
        cat2.append(el)
    sc = E("c:scaling")
    sc.append(E("c:orientation", val="minMax"))
    cat2.append(sc)
    cat2.append(E("c:delete", val=1))
    cat2.append(E("c:axPos", val="b"))
    cat2.append(E("c:majorTickMark", val="none"))
    cat2.append(E("c:minorTickMark", val="none"))
    cat2.append(E("c:tickLblPos", val="nextTo"))
    cat2.append(E("c:crossAx", val=50020))
    cat2.append(E("c:crosses", val="autoZero"))
    cat2.append(E("c:auto", val=1))
    cat2.append(E("c:lblAlgn", val="ctr"))
    cat2.append(E("c:lblOffset", val=100))
    cat2.append(E("c:noMultiLvlLbl", val=0))
    val2 = E("c:valAx")
    val2.append(E("c:axId", val=50020))
    sc2 = E("c:scaling")
    sc2.append(E("c:orientation", val="minMax"))
    sc2.append(E("c:max", val=round(ust_, 2)))
    sc2.append(E("c:min", val=round(alt_, 2)))
    val2.append(sc2)
    val2.append(E("c:delete", val=0))
    val2.append(E("c:axPos", val="r"))
    val2.append(E("c:numFmt", formatCode='"%"0', sourceLinked=0))
    val2.append(E("c:majorTickMark", val="none"))
    val2.append(E("c:minorTickMark", val="none"))
    val2.append(E("c:tickLblPos", val="nextTo"))
    vsp = E("c:spPr")
    vln = vsp.makeelement(qn("a:ln"), {})
    vln.append(vln.makeelement(qn("a:noFill"), {}))
    vsp.append(vln)
    val2.append(vsp)
    vtx = E("c:txPr")
    vtx.append(vtx.makeelement(qn("a:bodyPr"), {}))
    vtx.append(vtx.makeelement(qn("a:lstStyle"), {}))
    vp = vtx.makeelement(qn("a:p"), {})
    vpp = vp.makeelement(qn("a:pPr"), {})
    vdr = vpp.makeelement(qn("a:defRPr"), {"sz": "800"})
    vdf = vdr.makeelement(qn("a:solidFill"), {})
    vdf.append(vdf.makeelement(qn("a:srgbClr"), {"val": renk}))
    vdr.append(vdf)
    vpp.append(vdr)
    vp.append(vpp)
    vp.append(vp.makeelement(qn("a:endParaRPr"), {"lang": "tr-TR"}))
    vtx.append(vp)
    val2.append(vtx)
    val2.append(E("c:crossAx", val=50010))
    val2.append(E("c:crosses", val="max"))
    val2.append(E("c:crossBetween", val="between"))
    son_eksen.addnext(cat2)
    cat2.addnext(val2)
    return ch


def grafik_ekle(sl, fig, x, y, w, h):
    """Plotly figürünü PowerPoint grafiğine çevirir (çubuk, yığılmış çubuk, çizgi, alan, çubuk + çizgi)."""
    izler = list(fig.data)
    lay = fig.layout
    cubuk = [t for t in izler if t.type == "bar"]
    cizgiler = [t for t in izler if t.type == "scatter" and "lines" in (t.mode or "lines")]
    yazilar = [t for t in izler if t.type == "scatter" and (t.mode or "") == "text"]
    if cubuk:
        yatay = (cubuk[0].orientation or "v") == "h"
        kat_kaynak = cubuk[0].y if yatay else cubuk[0].x
        kategoriler = [duz(k) for k in kat_kaynak]
        # açıklama (annotation) olarak yazılmış etiketler (ör. negatif değerlerin sıfırın sağındaki etiketi)
        ek_et = {}
        for a in (lay.annotations or []):
            key = a.y if yatay else a.x
            ek_et[duz(key)] = duz(a.text)
        # toplam etiketleri (yalnızca metin izi) kategori adına eklenir
        if yazilar:
            top = {duz(k): duz(t) for k, t in zip(yazilar[0].x, yazilar[0].text)}
            kategoriler = [f"{k}\n{top.get(k, '')}".strip() for k in kategoriler]
        seriler = []
        for t in cubuk:
            deg = list(t.x if yatay else t.y)
            n = len(deg)
            etk = [duz(e) if e is not None else "" for e in (list(t.text) if t.text is not None and not
                                                            isinstance(t.text, str) else [t.text] * n)]
            kk = [duz(k) for k in (t.y if yatay else t.x)]
            etk = [e if e else ek_et.get(k, "") for e, k in zip(etk, kk)]
            renk_et = R["INK"]
            try:
                if t.textfont and t.textfont.color and isinstance(t.textfont.color, str):
                    renk_et = t.textfont.color
            except Exception:
                pass
            seriler.append(dict(ad=duz(t.name or ""), degerler=deg, renkler=_renkler(t.marker.color, n),
                                etiketler=etk, etiket_boy=_yazi_boyu(t), etiket_renk=renk_et))
        yigin = (lay.barmode or "") == "stack"
        eks = lay.xaxis if yatay else lay.yaxis
        rng = list(eks.range) if eks.range is not None else None
        ters = bool(lay.yaxis.autorange == "reversed") if yatay else False
        lejant = len(cubuk) > 1 and lay.showlegend is not False and any(s["ad"] for s in seriler)
        if cizgiler and yigin:   # yığılmış çubuk + çizgi: tek grafik, çizgi sağ (ikincil) eksende
            t = cizgiler[0]
            etk = list(t.text) if t.text is not None and not isinstance(t.text, str) else None
            karma_grafik(sl, x, y, w, h, kategoriler, seriler, dict(
                ad=duz(t.name or ""), degerler=[float(v) for v in t.y], renk=t.line.color or R["RED"],
                etiketler=[duz(e) for e in etk] if etk else None), yazi=8.5)
            return
        cy, chh = y, h
        if cizgiler:  # çubuk + çizgi: çizgi üst bantta ayrı (düzenlenebilir) bir çizgi grafiği olarak
            t = cizgiler[0]
            lj = "   ".join([f'<span style="color:{t.line.color or R["RED"]}">●</span> {duz(t.name or "")}'] +
                           [f'<span style="color:{(s["renkler"] or ["#000"])[0]}">■</span> {s["ad"]}' for s in seriler])
            metin_kutusu(sl, x, y, w, .2, lj, 8, R["INK"])
            band = h * .22
            etk = list(t.text) if t.text is not None and not isinstance(t.text, str) else None
            yv = [float(v) for v in t.y]
            pay_ = (max(yv) - min(yv)) * .5 or 1
            cizgi_grafigi(sl, x, y + .2, w, band, yv, t.line.color or R["RED"],
                          kategoriler=[duz(k) for k in t.x], etiketler=[duz(e) for e in etk] if etk else None,
                          isaret=True, yazi=8, rng=[min(yv) - pay_, max(yv) + pay_])
            cy, chh = y + .2 + band, h - band - .2
            lejant = False
            rng = None
        n_kat = len(kategoriler)
        yazi = 8.5 if n_kat <= 12 else (7.5 if n_kat <= 20 else 7)
        cubuk_grafigi(sl, x, cy, w, chh, kategoriler, seriler, yatay, yigin, float(lay.bargap or .3), ters, rng,
                      lejant, yazi)
        return
    if cizgiler:
        t = cizgiler[0]
        alan = (t.fill or "") in ("tozeroy", "tonexty")
        kat = [str(int(v)) if isinstance(v, (int, float, np.integer, np.floating)) and float(v).is_integer()
               else duz(v) for v in t.x]
        ch = cizgi_grafigi(sl, x, y, w, h, list(t.y), t.line.color or R["NAVY"], kategoriler=kat, alan=alan,
                           rng=list(lay.yaxis.range) if lay.yaxis.range is not None else None, eksen=True)
        try:
            ch.value_axis.visible = True
            ch.value_axis.tick_labels.font.size = Pt(8)
            ch.value_axis.has_major_gridlines = True
            ch.value_axis.major_gridlines.format.line.color.rgb = rgb("#E7E6E6")
            ch.category_axis.tick_labels.font.size = Pt(8)
            ch.category_axis.tick_label_position = XL_TICK_LABEL_POSITION.LOW
            if len(kat) > 20:
                ch.category_axis.tick_lbl_skip = max(len(kat) // 8, 1)
                ca = ch.category_axis._element
                for tag in ("c:tickLblSkip", "c:tickMarkSkip"):
                    el = ca.find(qn(tag))
                    if el is None:
                        el = ca.makeelement(qn(tag), {})
                        ca.append(el)
                    el.set("val", str(max(len(kat) // 8, 1)))
        except Exception:
            pass
        # açıklamalar (ör. "İlk 10 · %33,1") grafiğin sağ altına not olarak
        notlar = [duz(a.text) for a in (lay.annotations or [])]
        if notlar:
            metin_kutusu(sl, x + w * .45, y + h * .62, w * .5, .5, "\n".join(notlar), 8, R["INK"], hiza="r")


# ---------------------------------------------------------------------------------------------- tablo
def _hucre_kenar(hucre, alt_renk="D9D9D9", alt_k=9525):
    tcPr = hucre._tc.get_or_add_tcPr()
    for ad in ("a:lnL", "a:lnR", "a:lnT", "a:lnB"):
        for el in tcPr.findall(qn(ad)):
            tcPr.remove(el)
    for ad, renk, k in (("a:lnL", None, 0), ("a:lnR", None, 0), ("a:lnT", None, 0), ("a:lnB", alt_renk, alt_k)):
        ln = tcPr.makeelement(qn(ad), {"w": str(k)})
        if renk:
            sf = ln.makeelement(qn("a:solidFill"), {})
            c = sf.makeelement(qn("a:srgbClr"), {"val": renk})
            sf.append(c)
            ln.append(sf)
        else:
            ln.append(ln.makeelement(qn("a:noFill"), {}))
        tcPr.append(ln)


def tablo_ekle(sl, x, y, w, h, basliklar, satirlar, hizalar=None, oranlar=None, boy=9):
    n_s, n_k = len(satirlar) + 1, len(basliklar)
    gf = sl.shapes.add_table(n_s, n_k, Inches(x), Inches(y), Inches(w), Inches(min(h, .3 + .27 * len(satirlar))))
    tbl = gf.table
    tblPr = tbl._tbl.tblPr
    tblPr.set("firstRow", "1")
    tblPr.set("bandRow", "0")
    sid = tblPr.find(qn("a:tableStyleId"))
    if sid is None:
        sid = tblPr.makeelement(qn("a:tableStyleId"), {})
        tblPr.append(sid)
    sid.text = "{2D5ABB26-0587-4C30-8999-92F81FD0307C}"   # No Style, No Grid
    oranlar = oranlar or [1] * n_k
    top = sum(oranlar)
    for j, o in enumerate(oranlar):
        tbl.columns[j].width = Inches(w * o / top)
    hizalar = hizalar or ["l"] + ["r"] * (n_k - 1)
    sat_h = min((h - .32) / max(len(satirlar), 1), .32)
    tbl.rows[0].height = Inches(.32)
    for i in range(1, n_s):
        tbl.rows[i].height = Inches(sat_h)
    for i in range(n_s):
        for j in range(n_k):
            c = tbl.cell(i, j)
            c.fill.background()
            c.margin_left = c.margin_right = Inches(.04)
            c.margin_top = c.margin_bottom = Inches(.01)
            c.vertical_anchor = MSO_ANCHOR.BOTTOM if i == 0 else MSO_ANCHOR.MIDDLE
            tf = c.text_frame
            tf.word_wrap = True
            deger = basliklar[j] if i == 0 else satirlar[i - 1][j]
            paragrafa_yaz(tf.paragraphs[0], tf, deger, (boy - 1.5) if i == 0 else boy,
                          R["MUTED"] if i == 0 else R["INK"], i == 0, hizalar[j], 1.0)
            _hucre_kenar(c, "D9D9D9" if i else "BFBFBF", 9525 if i else 15875)
    return tbl


# ---------------------------------------------------------------------------------------------- haberler
def haber_tablosu(sl, x, y, w, h, kolonlar):
    """Haberler tek tabloda: her sütun bir haber kolonu, her satır bir haber; satır ve sütunlar hizalı.
    kolonlar: [[(no, grup_basligi_veya_None, kaynak_tarih, rapor_mu, baslik, link), …], …]"""
    n_k = len(kolonlar)
    n_s = max(len(k) for k in kolonlar)
    gf = sl.shapes.add_table(n_s + 1, n_k, Inches(x), Inches(y), Inches(w), Inches(h))
    tbl = gf.table
    tblPr = tbl._tbl.tblPr
    tblPr.set("firstRow", "1")
    tblPr.set("bandRow", "0")
    sid = tblPr.find(qn("a:tableStyleId"))
    if sid is None:
        sid = tblPr.makeelement(qn("a:tableStyleId"), {})
        tblPr.append(sid)
    sid.text = "{2D5ABB26-0587-4C30-8999-92F81FD0307C}"
    ara_w = w / n_k
    for j in range(n_k):
        tbl.columns[j].width = Inches(ara_w)
    tbl.rows[0].height = Inches(.24)
    for i in range(1, n_s + 1):
        tbl.rows[i].height = Inches((h - .24) / n_s)
    for j, kol in enumerate(kolonlar):
        # başlık satırı: sütunun ilk haberinin grubu (Türkiye / uluslararası)
        grup = next((g for _, g, *_ in kol if g), "") if kol else ""
        bas = kol[0][1] if kol and kol[0][1] else grup
        c = tbl.cell(0, j)
        c.fill.background()
        c.margin_left = c.margin_right = Inches(.05)
        c.margin_top = c.margin_bottom = Inches(.01)
        c.vertical_anchor = MSO_ANCHOR.BOTTOM
        paragrafa_yaz(c.text_frame.paragraphs[0], c.text_frame, (bas or "").upper(), 7, R["BLUE"], True, html=False)
        _hucre_kenar(c, "BFBFBF", 15875)
        for i in range(n_s):
            c = tbl.cell(i + 1, j)
            c.fill.background()
            c.margin_left = c.margin_right = Inches(.05)
            c.margin_top = c.margin_bottom = Inches(.02)
            c.vertical_anchor = MSO_ANCHOR.TOP
            tf = c.text_frame
            tf.word_wrap = True
            if i < len(kol):
                no, grp, meta, rapor, baslik, link = kol[i]
                ust = (f'<span style="color:{R["RED"]}"><b>{no:02d}</b></span>  {meta}'
                       + ("  <b>RAPOR</b>" if rapor else ""))
                if grp and i > 0:   # sütun ortasında grup değişiyorsa
                    ust = f'<b><span style="color:{R["BLUE"]}">{grp.upper()}</span></b>  ' + ust
                paragrafa_yaz(tf.paragraphs[0], tf, ust, 6.5, R["MUTED"], satir=1.0)
                p2 = tf.add_paragraph()
                paragrafa_yaz(p2, tf, baslik, 7.5, R["INK"], True, html=False, link=link, satir=1.0)
            _hucre_kenar(c, "D9D9D9", 9525)
    return tbl


def haber_listesi(sl, x, y, w, h, liste):
    """liste: [(no, grup_basligi_veya_None, kaynak_tarih, rapor_mu, baslik, link)]"""
    tb = sl.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    ilk = True
    for no, grup, meta, rapor, baslik, link in liste:
        if grup:
            p = tf.paragraphs[0] if ilk else tf.add_paragraph()
            ilk = False
            paragrafa_yaz(p, tf, grup.upper(), 7, R["BLUE"], True, html=False)
            p.space_after = Pt(2)
        p = tf.paragraphs[0] if ilk else tf.add_paragraph()
        ilk = False
        paragrafa_yaz(p, tf, f'<span style="color:{R["RED"]}"><b>{no:02d}</b></span>  {meta}'
                      + ("  <b>RAPOR</b>" if rapor else ""), 6.5, R["MUTED"])
        p.space_before = Pt(3)
        p2 = tf.add_paragraph()
        paragrafa_yaz(p2, tf, baslik, 8, R["INK"], True, html=False, link=link, satir=1.0)
        p2.space_after = Pt(1)


# ---------------------------------------------------------------------------------------------- haritalar
_GEO: dict = {}


def _geo(tur: str):
    if tur not in _GEO:
        f = DATA / ("tr_iller.geojson" if tur == "tr" else "dunya_ulkeler.geojson")
        g = json.loads(f.read_text(encoding="utf-8"))
        ozellik = "name" if tur == "tr" else "iso3"
        poligonlar = {}
        for ft in g["features"]:
            geo = ft["geometry"]
            pls = geo["coordinates"] if geo["type"] == "MultiPolygon" else [geo["coordinates"]]
            halkalar = []
            for pl in pls:
                halka = pl[0]
                adim = max(1, len(halka) // (90 if tur == "tr" else 120))
                halka = halka[::adim]
                if len(halka) >= 3:
                    halkalar.append(halka)
            poligonlar[ft["properties"][ozellik]] = halkalar
        _GEO[tur] = poligonlar
    return _GEO[tur]


def harita_ekle(sl, x, y, w, h, tur, degerler: dict, bicim, etiket_n=8, log=False, ozel: dict | None = None):
    """tur: 'tr' (il adları) ya da 'dunya' (ISO3). Boş bölgeler gri; renk ölçeği açık maviden laciverte.
    ozel: {bölge: renk} sabit renkler (ör. Türkiye)."""
    pol = _geo(tur)
    ad_es = {"Afyonkarahisar": "Afyon"} if tur == "tr" else {"XKX": "KOS"}
    deg = {ad_es.get(k, k): float(v) for k, v in degerler.items()
           if v is not None and not (isinstance(v, float) and math.isnan(v))}
    # izdüşüm: eşdikdörtgen (enlem kosinüsüyle düzeltilmiş)
    tum = [p for hs in pol.values() for hl in hs for p in hl]
    lon0, lon1 = min(p[0] for p in tum), max(p[0] for p in tum)
    lat0, lat1 = min(p[1] for p in tum), max(p[1] for p in tum)
    if tur == "dunya":
        lat0, lat1 = -56, 84
    kx = math.cos(math.radians((lat0 + lat1) / 2)) if tur == "tr" else 1.0
    gen_d, yuk_d = (lon1 - lon0) * kx, (lat1 - lat0)
    renk_h = .32
    olcek = min(w / gen_d, (h - renk_h) / yuk_d)
    ox = x + (w - gen_d * olcek) / 2
    oy = y + ((h - renk_h) - yuk_d * olcek) / 2
    if deg:
        vs = np.array(list(deg.values()), dtype=float)
        if log:
            vs_t = np.log10(np.clip(vs, 1e-9, None))
            lo, hi = 4.0, 7.0    # 10 mn $ – 10 mlr $ (bin $ cinsinden)
        else:
            vs_t = vs
            lo, hi = float(vs.min()), float(vs.max())
    a_renk, k_renk = ("#EEF2F9", R["NAVY"]) if log else (R["PALE"], R["NAVY"])

    def renk_bul(v):
        t = (math.log10(max(v, 1e-9)) if log else v)
        return karis(a_renk, k_renk, (t - lo) / (hi - lo) if hi > lo else 1)

    def emu(lon, lat):
        return (Inches(ox + (lon - lon0) * kx * olcek), Inches(oy + (lat1 - min(max(lat, lat0), lat1)) * olcek))

    for ad, halkalar in pol.items():
        if not halkalar:
            continue
        if ozel and ad in ozel:
            renk = ozel[ad]
        elif ad in deg:
            renk = renk_bul(deg[ad])
        else:
            renk = "#E7E6E6"
        x0, y0 = emu(*halkalar[0][0])
        fb = sl.shapes.build_freeform(x0, y0, scale=1.0)
        for i, hl in enumerate(halkalar):
            pts = [emu(*p) for p in hl]
            if i > 0:
                fb.move_to(*pts[0])
            fb.add_line_segments(pts[1:], close=True)
        try:
            s = fb.convert_to_shape()
        except Exception:
            continue
        s.fill.solid()
        s.fill.fore_color.rgb = rgb(renk)
        s.line.color.rgb = rgb("#FFFFFF")
        s.line.width = Pt(.4)
        s.shadow.inherit = False
        s.name = str(ad)
    # en büyük n bölgenin adı
    if etiket_n and deg and tur == "tr":
        for ad in sorted(deg, key=lambda k: -deg[k])[:etiket_n]:
            hs = pol.get(ad)
            if not hs:
                continue
            en = max(hs, key=len)
            cx, cy = np.mean([p[0] for p in en]), np.mean([p[1] for p in en])
            ex, ey = emu(cx, cy)
            metin_kutusu(sl, Emu(ex).inches - .5, Emu(ey).inches - .08, 1.0, .16, ad, 6.5, R["INK"], hiza="c",
                         html=False)
    # renk ölçeği
    if deg:
        by = y + h - renk_h + .06
        g = kutu(sl, x + w * .2, by, w * .6, .07, None, sekil=MSO_SHAPE.RECTANGLE)
        g.fill.gradient()
        g.fill.gradient_angle = 0
        st_ = g.fill.gradient_stops
        st_[0].color.rgb, st_[1].color.rgb = rgb(a_renk), rgb(k_renk)
        st_[0].position, st_[1].position = 0, 1.0
        if log:
            for i, (t, ad_) in enumerate(((4, "10 mn $"), (5, "100 mn $"), (6, "1 mlr $"), (7, "10 mlr $"))):
                xx = x + w * .2 + w * .6 * (t - 4) / 3
                metin_kutusu(sl, xx - .4, by + .09, .8, .16, ad_, 6.5, R["MUTED"], hiza="c", html=False)
        else:
            metin_kutusu(sl, x + w * .2 - .5, by + .09, 1.0, .16, bicim(min(deg.values())), 6.5, R["MUTED"],
                         hiza="c", html=False)
            metin_kutusu(sl, x + w * .8 - .5, by + .09, 1.0, .16, bicim(max(deg.values())), 6.5, R["MUTED"],
                         hiza="c", html=False)
