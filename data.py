"""Veri katmanı.

EVDS_API_KEY tanımlıysa (ortam değişkeni ya da st.secrets) seriler TCMB EVDS'den
canlı çekilir ve 6 saat önbelleğe alınır. Anahtar yoksa ya da istek başarısız olursa
`data/` klasöründeki anlık görüntü (snapshot) CSV'leri kullanılır.
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


@st.cache_data(ttl=6 * 3600, show_spinner="Veriler yükleniyor…")
def load() -> Veri:
    key = _api_key()
    if key:
        try:
            m = evds_fetch(list(MAKRO_SERILER.values()), "01-01-2014", key)
            m.columns = list(MAKRO_SERILER.keys())
            codes = [f"TP.TSANAYTKVM2021.{k}" for k in SEKTORLER]
            parts = [evds_fetch(codes[i:i + 8], "01-01-2014", key) for i in range(0, len(codes), 8)]
            s = pd.concat(parts, axis=1)
            s.columns = list(SEKTORLER.keys())
            u = evds_fetch(["TP.DK.USD.S.YTL"], "01-01-2014", key,
                           "&frequency=5&aggregationTypes=avg")
            return Veri(m.dropna(how="all"), s.dropna(how="all"),
                        u.iloc[:, 0].dropna(), "EVDS (canlı)")
        except Exception as e:  # ağ/anahtar sorunu -> anlık görüntüye düş
            st.session_state["evds_hata"] = str(e)
    return Veri(_read_csv("makro.csv"), _read_csv("sektor_sue.csv"),
                _read_csv("usdtry.csv")["usdtry"], "Anlık görüntü")


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
