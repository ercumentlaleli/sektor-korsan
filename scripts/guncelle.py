"""Verileri EVDS ve TÜİK SDMX'ten çekip data/ klasörüne CSV olarak yazar.

Kullanım:
    python scripts/guncelle.py            # EVDS + TÜİK (aylık veriler)
    python scripts/guncelle.py --evds     # yalnızca EVDS
    python scripts/guncelle.py --tuik     # yalnızca TÜİK
    python scripts/guncelle.py --iso      # yalnızca İSO 500 (yılda bir, yeni liste çıkınca)
    python scripts/guncelle.py --urun     # yalnızca ürün verileri (yıllık; yeni PRODTR dosyası gelince)

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
sys.path.insert(0, str(ROOT / "scripts"))
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


def iso500(yillar: tuple[int, ...] = (2024, 2025)) -> dict:
    """İSO 500 ve İkinci 500 listeleri (iso500.org.tr). Anahtar gerekmez."""
    import json as _json
    import requests
    print("İSO 500…")
    alanlar = {"FirmaId": "firma_id", "AciklamaDurumuUnvan": "unvan_acik", "Yil": "yil", "BirinciIkinci500": "liste", "UretimdenSatislarGSNo": "sira", "Unvan": "unvan",
               "NACEKod": "nace", "NACE": "nace_ad", "BagliOlduguOda": "oda",
               "UretimdenSatislar": "uretimden_satislar", "NetSatislar": "net_satislar",
               "BurutKatmaDeger": "brut_katma_deger", "Ozkaynak": "ozkaynak", "AktifToplami": "aktif",
               "VergiOncesiDonemKarZarar": "vergi_oncesi_kar", "FAVAK_EBITDAKarZarar": "favok",
               "IhracatBinDolar": "ihracat_bin_usd", "UcretliCalisanlarOrtalamasiKisi": "calisan",
               "SermayePayiKamu": "pay_kamu", "SermayePayiYabanci": "pay_yabanci",
               "SermayePayiHalkaAcik": "pay_halka_acik", "WebAdresi": "web"}
    ses = requests.Session()
    ses.headers["User-Agent"] = "Mozilla/5.0 (sektor-atlasi)"
    ses.get("https://www.iso500.org.tr/500-buyuk-sanayi-kurulusu", timeout=30)
    satirlar = []
    for yil in yillar:
        for liste in (1, 2):
            f = {"yil": yil, "nace": [], "bagliOlduguSanayiOdasi": "", "calisanAraligiMin": 0,
                 "calisanAraligiMax": 0, "sermayeYapisi": 0, "kurulusAdi": "", "birinciIkinci500": liste,
                 "lisanId": 17}
            r = ses.post("https://www.iso500.org.tr/Default/GetList",
                         data={"draw": 1, "start": 0, "length": -1, "dtJson": _json.dumps(f)}, timeout=120)
            r.raise_for_status()
            veri = r.json().get("data", [])
            print(f"  {yil} {'İSO 500' if liste == 1 else 'İkinci 500'}: {len(veri)} firma")
            satirlar += [{v: d.get(k) for k, v in alanlar.items()} for d in veri]
            time.sleep(1)
    df = pd.DataFrame(satirlar)
    # açıklanmayan değerler servis tarafından 0 olarak geliyor
    for k in ("favok", "ihracat_bin_usd", "calisan", "brut_katma_deger", "ozkaynak", "aktif", "net_satislar"):
        df.loc[df[k] == 0, k] = None
    df["nace"] = df["nace"].astype(str).str.split(".").str[0].str.zfill(2)
    df["il"] = (df["oda"].fillna("").str.replace(r"\s+(Sanayi|Ticaret|Ticaret ve Sanayi|Sanayi ve Ticaret)\s+Odası.*$",
                                                   "", regex=True).str.strip())
    ilce_il = {"Ege Bölgesi": "İzmir", "Afşin": "Kahramanmaraş", "Akhisar": "Manisa", "Akyazı": "Sakarya",
               "Bor": "Niğde", "Bozüyük": "Bilecik", "Bucak": "Burdur", "Bulancak": "Giresun",
               "Dörtyol": "Hatay", "Ereğli (Konya)": "Konya", "Gemlik": "Bursa", "Kadirli": "Osmaniye",
               "Karacabey": "Bursa", "Kdz. Ereğli": "Zonguldak", "Lüleburgaz": "Kırklareli", "Milas": "Muğla",
               "Mustafakemalpaşa": "Bursa", "Orhangazi": "Bursa", "Salihli": "Manisa", "Silifke": "Mersin",
               "Soma": "Manisa", "Suluova": "Amasya", "Sungurlu": "Çorum", "Tarsus": "Mersin",
               "Tavşanlı": "Kütahya", "Vezirköprü": "Samsun", "Yenişehir (Bursa)": "Bursa", "Zile": "Tokat",
               "Çarşamba": "Samsun", "Çaycuma": "Zonguldak", "Çayeli": "Rize", "Çerkezköy": "Tekirdağ",
               "Çorlu": "Tekirdağ", "Ünye": "Ordu", "İMEAK Deniz": "İstanbul", "İnegöl": "Bursa",
               "İskenderun": "Hatay", "Kamu": "Belirtilmemiş", "": "Belirtilmemiş"}
    df["il"] = df["il"].replace(ilce_il)
    df.to_csv(DATA / "iso500.csv", index=False)
    print(f"  iso500.csv: {len(df)} satır")
    return {"iso500": datetime.now().isoformat(timespec="minutes")}


def main(argv: list[str]) -> int:
    meta_p = DATA / "guncelleme.json"
    meta = json.loads(meta_p.read_text()) if meta_p.exists() else {}
    hepsi = not any(a.startswith("--") for a in argv)
    if hepsi or "--evds" in argv:
        meta.update(evds())
    if hepsi or "--tuik" in argv:
        meta.update(tuik_())
    # İSO 500 yılda bir yayımlandığı için günlük çalışmaya dahil değil; yalnızca --iso ile çalışır
    if "--iso" in argv:
        try:
            meta.update(iso500())
        except Exception as e:
            print("İSO 500 HATA:", e)
    # Ürün verileri (PRODTR, GTİP eşlemesi, Comtrade) yıllık; yalnızca --urun ile çalışır
    if "--urun" in argv:
        if (DATA / "ham" / "prodtr_2005_2025.xlsx").exists():
            import urunler
            print("Ürünler (PRODTR + Comtrade)…")
            urunler.main([])
            meta["urunler"] = datetime.now().isoformat(timespec="minutes")
    meta_p.write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
