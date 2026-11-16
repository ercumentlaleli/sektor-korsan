"""BDDK aylık bülten, sektörel kredi dağılımı (tablo 5, bankacılık sektörü) -> data/bddk_sektor_kredi.csv

`bddkdata` kütüphanesiyle (https://pypi.org/project/bddkdata) geçen yılın Aralık ayından yayımlanmış son aya kadar
imalat sanayii alt kalemlerinin nakdi ve takipteki kredileri çekilir (bin TL). Uygulama bunu, TCMB sektör
bilançolarından gelen yıl sonu serisine son yılın yılbaşından bugüne değişimini eklemek için kullanır.

BDDK sınıflaması NACE Rev.2 2'liden kabadır; hangi BDDK kaleminin hangi NACE bölümlerini kapsadığı `GRUP` sözlüğündedir.

Kullanım: python scripts/bddk.py   (scripts/guncelle.py --bddk de çağırır)
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

# BDDK kalemi (başı) -> (kısa ad, kapsadığı NACE 2'li bölümler)
GRUP = {
    "İmalat Sanayi": ("İmalat sanayii", ["C"]),
    "Gıda, Meşrubat ve Tütün": ("Gıda, içecek ve tütün", ["C10", "C11", "C12"]),
    "Tekstil ve Tekstil Ürünleri": ("Tekstil ve giyim", ["C13", "C14"]),
    "Deri ve Deri Ürünleri": ("Deri", ["C15"]),
    "Ağaç ve Ağaç Ürünleri": ("Ağaç ürünleri", ["C16"]),
    "Kağıt Hammaddesi": ("Kâğıt ve basım", ["C17", "C18"]),
    "Nükleer Yakıt, Petrol": ("Kok ve petrol", ["C19"]),
    "Kimya Ürünleri": ("Kimya ve ilaç", ["C20", "C21"]),
    "Kauçuk ve Plastik": ("Kauçuk ve plastik", ["C22"]),
    "Diğer Metal Dışı Madenler": ("Mineral ürünler", ["C23"]),
    "Metal Ana San.": ("Ana metal ve metal ürünleri", ["C24", "C25"]),
    "Makina ve Techizat": ("Makine ve ekipman", ["C28"]),
    "Elektrikli ve Optik": ("Elektrikli ve optik", ["C26", "C27"]),
    "Ulaşım Araçları": ("Ulaşım araçları", ["C29", "C30"]),
    "Başka Yerlerde Sınıflandırılmamış İmalat": ("Diğer imalat", ["C31", "C32", "C33"]),
}


def ay_tablosu(y: int, m: int) -> pd.DataFrame | None:
    from bddkdata import fetch_data
    d = fetch_data(y, m, y, m, 5, "TL", 10001)
    if d is None or d.empty:
        return None
    satir = []
    for _, r in d.iterrows():
        kalem = str(r["Kalem"]).strip()
        for bas, (ad, kodlar) in GRUP.items():
            if kalem.startswith(bas):
                satir.append({"donem": f"{y}-{m:02d}", "grup": ad, "nace": " ".join(kodlar),
                              "nakdi": float(r["Nakdi Krediler"]), "takipteki": float(r["Takipteki Krediler"])})
                break
    return pd.DataFrame(satir) if satir else None


def main() -> pd.DataFrame:
    print("BDDK sektörel kredi dağılımı…")
    b = date.today()
    aylar = [(b.year - 1, 12)] + [(b.year, m) for m in range(1, b.month + 1)]
    if b.month == 1:  # Ocak'ta yeni yılın verisi henüz yok: geçen yılı tamamla
        aylar = [(b.year - 2, 12)] + [(b.year - 1, m) for m in range(1, 13)]
    parca = []
    for y, m in aylar:
        try:
            t = ay_tablosu(y, m)
        except Exception as e:  # yayımlanmamış ay
            print(f"  {y}-{m:02d}: {e}")
            t = None
        if t is not None:
            parca.append(t)
    if not parca:
        raise RuntimeError("BDDK verisi alınamadı")
    out = pd.concat(parca, ignore_index=True)
    out.to_csv(DATA / "bddk_sektor_kredi.csv", index=False)
    print(f"  bddk_sektor_kredi.csv: {out['donem'].nunique()} ay, son dönem {out['donem'].max()}")
    return out


if __name__ == "__main__":
    main()
    sys.exit(0)
