"""Verileri EVDS ve TÜİK SDMX'ten çekip data/ klasörüne CSV olarak yazar.

Kullanım:
    python scripts/guncelle.py            # her iki kaynak
    python scripts/guncelle.py --evds     # yalnızca EVDS
    python scripts/guncelle.py --tuik     # yalnızca TÜİK

Gerekli ortam değişkenleri: EVDS_API_KEY, TUIK_API_KEY
Uygulama yalnızca bu CSV'leri okur; bu betik günlük çalıştırılabilir (cron, GitHub Actions).
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("STREAMLIT_LOG_LEVEL", "error")

import pandas as pd  # noqa: E402

import tuik  # noqa: E402
from data import MAKRO_SERILER, SEKTORLER, evds_fetch  # noqa: E402

DATA = ROOT / "data"
START = "2014-01"


def yaz(df: pd.DataFrame, ad: str) -> None:
    out = df.copy()
    out.index = out.index.astype(str)
    out.index.name = "tarih"
    out.round(4).to_csv(DATA / ad)
    print(f"  {ad}: {len(out)} ay, {out.index.min()} – {out.index.max()}, {out.shape[1]} sütun")


def evds() -> dict:
    key = os.environ.get("EVDS_API_KEY")
    if not key:
        print("EVDS_API_KEY yok, EVDS atlandı.")
        return {}
    print("EVDS…")
    start = "01-01-2014"
    m = evds_fetch(list(MAKRO_SERILER.values()), start, key)
    m.columns = list(MAKRO_SERILER.keys())
    yaz(m.dropna(how="all"), "makro.csv")
    codes = [f"TP.TSANAYTKVM2021.{k}" for k in SEKTORLER]
    s = pd.concat([evds_fetch(codes[i:i + 8], start, key) for i in range(0, len(codes), 8)], axis=1)
    s.columns = list(SEKTORLER.keys())
    yaz(s.dropna(how="all"), "sektor_sue.csv")
    u = evds_fetch(["TP.DK.USD.S.YTL"], start, key, "&frequency=5&aggregationTypes=avg")
    u.columns = ["usdtry"]
    yaz(u.dropna(), "usdtry.csv")
    # dış ticaret, ISIC Rev.4 (TÜİK, EVDS üzerinden), bin ABD doları
    kodlar = ["C"] + [k[1:] for k in SEKTORLER] + ["18"]
    for ad, grup in (("ihracat", "IHRISICREV4"), ("ithalat", "ITHISICREV4")):
        seriler = [f"TP.{grup}.{k}" for k in kodlar]
        d = pd.concat([evds_fetch(seriler[i:i + 8], start, key) for i in range(0, len(seriler), 8)], axis=1)
        d.columns = ["C" if k == "C" else f"C{k}" for k in kodlar]
        yaz(d.dropna(how="all", axis=1).dropna(how="all"), f"dt_{ad}.csv")
    return {"evds": datetime.now().isoformat(timespec="minutes")}


def tuik_() -> dict:
    key = tuik.api_key()
    if not key:
        print("TUIK_API_KEY yok, TÜİK atlandı.")
        return {}
    print("TÜİK SDMX…")
    c = tuik.TuikClient(key, timeout=300)
    ham: dict[str, pd.DataFrame] = {}
    hatalar = {}
    for ad, t in tuik.tanimlar().items():
        try:
            if t.dataflow not in ham:
                t0 = time.time()
                ham[t.dataflow] = c.data(t.dataflow, t.key, start=START)
                print(f"  {t.dataflow}: {len(ham[t.dataflow])} gözlem ({time.time() - t0:.0f} sn)")
            yaz(tuik.seri_cek(c, t, ham=ham[t.dataflow]), f"tuik_{ad}.csv")
        except Exception as e:
            hatalar[ad] = str(e)
            print(f"  {ad}: HATA {e}")
    # NACE 3'lü ve 4'lü sanayi üretim endeksleri (imalat)
    try:
        t0 = time.time()
        df_id = "DF_SANAYI_URETIM_ENDEKS_ALT_C"
        d = c.data(df_id, "all", start=START)
        print(f"  {df_id}: {len(d)} gözlem ({time.time() - t0:.0f} sn)")
        d = d[(d["SEASONAL_ADJUST"] == "W") & (d["DEGISIM_TUR"] == "1")
              & d["ACTIVITY_NACE_REV2"].str.fullmatch(r"C\d{3,4}", na=False)]
        if "YAYIM_DONEMI" in d:
            d = d[d["YAYIM_DONEMI"] == d["YAYIM_DONEMI"].max()]
        d = d.assign(tarih=tuik._period(d["TIME_PERIOD"]))
        yaz(d.pivot_table(index="tarih", columns="ACTIVITY_NACE_REV2", values="OBS_VALUE",
                          aggfunc="first").sort_index(), "tuik_nace34.csv")
        adlar = c.codelist(df_id, "ACTIVITY_NACE_REV2")
        pd.Series({k: v for k, v in adlar.items() if k.startswith("C")}, name="ad") \
            .rename_axis("kod").to_csv(DATA / "nace_adlari.csv")
    except Exception as e:
        hatalar["nace34"] = str(e)
        print(f"  nace34: HATA {e}")
    return {"tuik": datetime.now().isoformat(timespec="minutes"), "tuik_hatalar": hatalar}


def main(argv: list[str]) -> int:
    meta_p = DATA / "guncelleme.json"
    meta = json.loads(meta_p.read_text()) if meta_p.exists() else {}
    if "--tuik" not in argv:
        meta.update(evds())
    if "--evds" not in argv:
        meta.update(tuik_())
    meta_p.write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
