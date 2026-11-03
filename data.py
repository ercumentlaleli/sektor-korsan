"""Veri katmanı.

Uygulama yalnızca `data/` klasöründeki CSV'leri okur; bu yüzden anında açılır ve
API anahtarı olmadan da çalışır. CSV'ler `scripts/guncelle.py` ile EVDS
(EVDS_API_KEY) ve TÜİK SDMX'ten (TUIK_API_KEY) yenilenir.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

DATA_DIR = Path(__file__).parent / "data"
EVDS_URL = "https://evds3.tcmb.gov.tr/igmevdsms-dis/"

# kısa ad -> EVDS seri kodu
MAKRO_SERILER = {
    "sue_imalat": "TP.TSANAYTKVM2021.C",
    "yiufe_imalat": "TP.TUFE1YI.T15",
    "yiufe_genel": "TP.TUFE1YI.T1",
    "tufe": "TP.GENENDEKS.T1",
    "ydufe_imalat": "TP.UFEYD05",
    "kko": "TP.KKO2.IS.TOP",
    "rek": "TP.RK.U01.Y",
}

SEKTORLER = {
    "C10": ("Gıda ürünleri imalatı", "Gıda"),
    "C11": ("İçeceklerin imalatı", "İçecek"),
    "C12": ("Tütün ürünleri imalatı", "Tütün"),
    "C13": ("Tekstil ürünlerinin imalatı", "Tekstil"),
    "C14": ("Giyim eşyalarının imalatı", "Giyim"),
    "C15": ("Deri ve ilgili ürünlerin imalatı", "Deri"),
    "C16": ("Ağaç ve ağaç ürünleri imalatı", "Ağaç ürünleri"),
    "C17": ("Kâğıt ve kâğıt ürünlerinin imalatı", "Kâğıt"),
    "C19": ("Kok kömürü ve rafine petrol ürünleri imalatı", "Kok ve petrol"),
    "C20": ("Kimyasalların ve kimyasal ürünlerin imalatı", "Kimya"),
    "C21": ("Eczacılık ürünlerinin imalatı", "İlaç"),
    "C22": ("Kauçuk ve plastik ürünlerin imalatı", "Kauçuk ve plastik"),
    "C23": ("Metalik olmayan diğer mineral ürünlerin imalatı", "Metalik olmayan mineral"),
    "C24": ("Ana metal sanayii", "Ana metal"),
    "C25": ("Fabrikasyon metal ürünleri imalatı", "Metal ürünleri"),
    "C26": ("Bilgisayar, elektronik ve optik ürünlerin imalatı", "Elektronik ve optik"),
    "C27": ("Elektrikli teçhizat imalatı", "Elektrikli teçhizat"),
    "C28": ("Başka yerde sınıflandırılmamış makine ve ekipman imalatı", "Makine ve ekipman"),
    "C29": ("Motorlu kara taşıtları, treyler ve yarı treyler imalatı", "Motorlu taşıtlar"),
    "C30": ("Diğer ulaşım araçlarının imalatı", "Diğer ulaşım araçları"),
    "C31": ("Mobilya imalatı", "Mobilya"),
    "C32": ("Diğer imalatlar", "Diğer imalat"),
    "C33": ("Makine ve ekipmanların kurulumu ve onarımı", "Kurulum ve onarım"),
}


@dataclass
class Veri:
    makro: pd.DataFrame        # aylık, PeriodIndex
    sektor: pd.DataFrame       # aylık sektör SÜE endeksleri
    usd: pd.Series             # aylık ortalama USD/TRY
    kaynak: str                # "EVDS (canlı)" veya "Anlık görüntü"


def _api_key() -> str | None:
    key = os.environ.get("EVDS_API_KEY")
    if key:
        return key
    try:
        return st.secrets.get("EVDS_API_KEY")  # type: ignore[no-any-return]
    except Exception:
        return None


def _read_csv(name: str) -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / name)
    df["tarih"] = pd.PeriodIndex(df["tarih"], freq="M")
    return df.set_index("tarih").sort_index()


def evds_fetch(codes: list[str], start: str, key: str, extra: str = "") -> pd.DataFrame:
    """EVDS'den birden çok seriyi aylık olarak çeker; sütun adları seri kodudur."""
    url = (f"{EVDS_URL}series={'-'.join(codes)}&startDate={start}"
           f"&endDate=01-12-2030&type=json{extra}")
    r = requests.get(url, headers={"key": key}, timeout=30)
    r.raise_for_status()
    items = r.json()["items"]
    df = pd.DataFrame(items)
    df["tarih"] = pd.PeriodIndex(pd.to_datetime(df["Tarih"], format="%Y-%m"), freq="M")
    out = pd.DataFrame(index=df["tarih"])
    for c in codes:
        col = c.replace(".", "_")
        out[c] = pd.to_numeric(df[col].values, errors="coerce") if col in df else float("nan")
    return out.sort_index()


@st.cache_data(show_spinner=False)
def load(surum: float = 0) -> Veri:
    return Veri(_read_csv("makro.csv"), _read_csv("sektor_sue.csv"),
                _read_csv("usdtry.csv")["usdtry"], "EVDS")


def guncelleme_bilgisi() -> dict:
    import json
    p = DATA_DIR / "guncelleme.json"
    return json.loads(p.read_text()) if p.exists() else {}


def veri_surumu() -> float:
    """CSV'ler değiştiğinde önbelleği geçersiz kılmak için."""
    return max((f.stat().st_mtime for f in DATA_DIR.glob("*.csv")), default=0)


# ---------- hesap yardımcıları ----------

def yoy(s: pd.Series) -> pd.Series:
    return (s / s.shift(12) - 1) * 100


def son_gecerli(s: pd.Series) -> tuple[pd.Period, float]:
    s = s.dropna()
    return s.index[-1], float(s.iloc[-1])


AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz",
         "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
AYLAR_KISA = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]


def ay(p: pd.Period) -> str:
    return f"{AYLAR[p.month - 1]} {p.year}"


def ay_kisa(p: pd.Period) -> str:
    return f"{AYLAR_KISA[p.month - 1]} {str(p.year)[2:]}"


def num(x: float, d: int = 1) -> str:
    """Türkçe sayı biçimi: 1.234,5"""
    s = f"{abs(x):,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return ("−" if x < 0 else "") + s


def pct(x: float, d: int = 1, sign: bool = False) -> str:
    """%2,5 / −%2,5 / +%2,5"""
    s = f"%{num(abs(x), d)}"
    if x < 0:
        return "−" + s
    return ("+" + s) if sign and x > 0 else s


# ---------- TÜİK SDMX ----------

@dataclass
class TuikVeri:
    seriler: dict[str, pd.DataFrame]   # ad -> (ay x NACE)
    aciklama: dict[str, str]


@st.cache_data(show_spinner=False)
def load_tuik(surum: float = 0) -> TuikVeri:
    import tuik
    seriler, aciklama = {}, {}
    for ad, t in tuik.tanimlar().items():
        f = DATA_DIR / f"tuik_{ad}.csv"
        if f.exists():
            seriler[ad], aciklama[ad] = _read_csv(f.name), t.aciklama
    for ad, ac in (("ihracat", "İhracat (bin $)"), ("ithalat", "İthalat (bin $)")):
        f = DATA_DIR / f"dt_{ad}.csv"
        if f.exists():
            seriler[ad], aciklama[ad] = _read_csv(f.name), ac
    return TuikVeri(seriler, aciklama)


@st.cache_data(show_spinner=False)
def load_nace34(surum: float = 0) -> tuple[pd.DataFrame, dict[str, str]]:
    f = DATA_DIR / "tuik_nace34.csv"
    if not f.exists():
        return pd.DataFrame(), {}
    adlar_f = DATA_DIR / "nace_adlari.csv"
    adlar = pd.read_csv(adlar_f, dtype=str).set_index("kod")["ad"].to_dict() if adlar_f.exists() else {}
    return _read_csv(f.name), adlar


# ---------- haberler (Google News RSS) ----------

HABER_SORGU = {
    "C": '"imalat sanayi" OR "sanayi üretimi" OR "kapasite kullanım"',
    "C10": '"gıda sanayi" OR "gıda üreticileri"', "C11": '"içecek sektörü" OR "meşrubat"',
    "C12": '"tütün sektörü" OR "sigara üretimi"', "C13": '"tekstil sektörü" OR "tekstil ihracatı"',
    "C14": '"hazır giyim" sektör', "C15": '"deri sektörü" OR "ayakkabı sektörü"',
    "C16": '"orman ürünleri" OR "ağaç ürünleri" sanayi', "C17": '"kağıt sektörü" OR "ambalaj sanayi"',
    "C19": 'rafineri OR "akaryakıt üretimi"', "C20": '"kimya sektörü" OR "kimya ihracatı"',
    "C21": '"ilaç sektörü" OR "ilaç sanayi"', "C22": '"plastik sektörü" OR "kauçuk sektörü"',
    "C23": '"çimento sektörü" OR "seramik sektörü" OR "cam sanayi"',
    "C24": '"çelik üretimi" OR "demir çelik" OR "alüminyum sektörü"', "C25": '"metal sektörü" sanayi',
    "C26": '"elektronik sektörü" OR "elektronik üretimi"', "C27": '"beyaz eşya" OR "elektrikli teçhizat"',
    "C28": '"makine sektörü" OR "makine ihracatı"', "C29": '"otomotiv sektörü" OR "otomotiv üretimi"',
    "C30": '"savunma sanayi" OR "gemi inşa" OR "havacılık sanayi"', "C31": '"mobilya sektörü" OR "mobilya ihracatı"',
    "C32": '"mücevher sektörü" OR "oyuncak sektörü"', "C33": '"bakım onarım" sanayi',
}


@st.cache_data(ttl=3600, show_spinner=False)
def haberler(sorgu: str, gun: int = 30, adet: int = 40) -> list[dict]:
    import xml.etree.ElementTree as ET
    from email.utils import parsedate_to_datetime
    from urllib.parse import quote
    url = (f"https://news.google.com/rss/search?q={quote(sorgu + f' when:{gun}d')}"
           "&hl=tr&gl=TR&ceid=TR:tr")
    try:
        r = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0 (sektor-atlasi)"})
        r.raise_for_status()
        root = ET.fromstring(r.content)
    except Exception:
        return []
    out = []
    for it in root.iter("item"):
        kaynak = it.findtext("source") or ""
        baslik = (it.findtext("title") or "").removesuffix(f" - {kaynak}")
        try:
            tarih = parsedate_to_datetime(it.findtext("pubDate"))
        except Exception:
            tarih = None
        out.append({"baslik": baslik, "link": it.findtext("link"), "kaynak": kaynak, "tarih": tarih})
    out.sort(key=lambda x: x["tarih"] or pd.Timestamp(0, tz="UTC"), reverse=True)
    return out[:adet]


@st.cache_data(show_spinner=False)
def load_iso500(surum: float = 0) -> pd.DataFrame:
    f = DATA_DIR / "iso500.csv"
    if not f.exists():
        return pd.DataFrame()
    d = pd.read_csv(f, dtype={"nace": str})
    d["nace"] = "C" + d["nace"].astype(str).str.split(".").str[0].str.zfill(2)
    d.loc[d["unvan"].fillna("-").str.strip().isin(["-", ""]), "unvan"] = "Adını açıklamayan kuruluş"
    return d
