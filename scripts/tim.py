"""TİM (Türkiye İhracatçılar Meclisi) ülkelere göre ihracat rakamları -> data/tim_ulke_ihracat.csv

TİM her ay "ülkeler konsolide ihracat rakamları" dosyasını yayımlar (1000 $): o ay ve yılbaşından
bu yana, bu yıl ve geçen yıl. Son 12 ay ve önceki 12 ay şu üç dosyadan türetilir (son ay = Y yılı, m. ay):
    son 12 ay     = YB(Y, m)   + [Yıl(Y-1) − YB(Y-1, m)]
    önceki 12 ay  = YB(Y-1, m) + [Yıl(Y-2) − YB(Y-2, m)]
YB = yılbaşından m. aya kadar toplam; Yıl = Ocak–Aralık toplamı.
Dosyalar: (Y, m) [YB(Y,m), YB(Y-1,m)], (Y-1, 12) [Yıl(Y-1), Yıl(Y-2)], (Y-1, m) [YB(Y-2,m)].

Kullanım: python scripts/tim.py   (scripts/guncelle.py --tim de çağırır)
"""
from __future__ import annotations

import io
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
URL = "https://tim.org.tr/files/downloads/rakamlar/{y}/{m}/{y}-{m:02d}-ulkeler-konsolide-ihracat-rakamlari.xlsx"
UA = {"User-Agent": "sektor-veri-atlasi/1.0"}


def dosya(y: int, m: int) -> pd.DataFrame | None:
    """TİM dosyası: ulke, ay_once, ay_bu, yb_once, yb_bu (1000 $). Yoksa None."""
    r = requests.get(URL.format(y=y, m=m), headers=UA, timeout=90)
    if r.status_code != 200 or "spreadsheet" not in r.headers.get("content-type", ""):
        return None
    d = pd.read_excel(io.BytesIO(r.content), header=None)
    # başlık: 4. satırda ULKE; sütunlar: ay (geçen yıl, bu yıl, değişim), önceki ay (bu yıl, değişim), YB (geçen, bu, değişim)
    d = d.iloc[4:, [0, 1, 2, 6, 7]]
    d.columns = ["ulke", "ay_once", "ay_bu", "yb_once", "yb_bu"]
    d["ulke"] = d["ulke"].astype(str).str.strip()
    d = d[d["ulke"].ne("") & d["ulke"].ne("nan") & ~d["ulke"].str.upper().str.contains("TOPLAM")]
    for c in d.columns[1:]:
        d[c] = pd.to_numeric(d[c], errors="coerce").fillna(0.0)
    return d.set_index("ulke")


def son_donem(bugun: date | None = None) -> tuple[int, int, pd.DataFrame]:
    """Yayımlanmış en son ayın dosyası (bugünden geriye doğru dener)."""
    b = bugun or date.today()
    y, m = b.year, b.month
    for _ in range(4):
        d = dosya(y, m)
        if d is not None:
            return y, m, d
        y, m = (y, m - 1) if m > 1 else (y - 1, 12)
    raise RuntimeError("TİM ülke dosyası bulunamadı")


def main() -> pd.DataFrame:
    print("TİM ülkelere göre ihracat…")
    y, m, bu = son_donem()
    if m == 12:
        son12, once12 = bu["yb_bu"], bu["yb_once"]
    else:
        ara, gecen = dosya(y - 1, 12), dosya(y - 1, m)
        if ara is None or gecen is None:
            raise RuntimeError(f"TİM: {y - 1}-12 veya {y - 1}-{m:02d} dosyası yok")
        ulkeler = bu.index.union(ara.index).union(gecen.index)
        bu, ara, gecen = (x.reindex(ulkeler).fillna(0.0) for x in (bu, ara, gecen))
        son12 = bu["yb_bu"] + ara["yb_bu"] - bu["yb_once"]
        once12 = bu["yb_once"] + ara["yb_once"] - gecen["yb_once"]
    out = pd.DataFrame({"son12": son12, "onceki12": once12})
    out["serbest_bolge"] = out.index.str.upper().str.contains(r"SERBEST B|SERB\.\s*BÖL", regex=True)
    out["donem"] = f"{y}-{m:02d}"
    out = out.sort_values("son12", ascending=False)
    out.index.name = "ulke"
    out.to_csv(DATA / "tim_ulke_ihracat.csv")
    print(f"  tim_ulke_ihracat.csv: {len(out)} ülke, dönem {y}-{m:02d}, "
          f"toplam son 12 ay {out['son12'].sum() / 1e6:,.1f} mlr $")
    return out


if __name__ == "__main__":
    main()
    sys.exit(0)
