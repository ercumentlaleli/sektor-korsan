"""Ürün düzeyi verileri hazırlar (Ürünler ve Kod analizi sekmeleri için).

Girdiler (data/ham/):
  prodtr_2005_2025.xlsx   TÜİK Sanayi Ürün İstatistikleri Veri Tabanı (PRODTR), 2005–2025
  gtip_prodtr_2018.xls    TÜİK GTİP 2018 – PRODTR 2018 eşleme tablosu

Dış kaynak:
  UN Comtrade public preview API (anahtarsız): Türkiye'nin HS6 düzeyinde yıllık ithalat/ihracatı

Çıktılar (data/):
  prodtr_urunler.csv      kod, ad, birim, nace
  prodtr_deger.csv        satış değeri (TL), satır=kod, sütun=yıl
  prodtr_satis_miktar.csv satış miktarı
  prodtr_uretim_miktar.csv üretim miktarı
  gtip_prodtr.csv         GTİP 12'li – PRODTR eşlemesi
  comtrade_hs6.csv        yıl, akış (M/X), hs6, değer ($)

Kullanım:
    python scripts/urunler.py                 # Excel'leri işle + Comtrade (son 2 yıl)
    python scripts/urunler.py --comtrade-yok  # yalnızca Excel'leri işle
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
HAM = ROOT / "data" / "ham"
DATA = ROOT / "data"
COMTRADE = "https://comtradeapi.un.org/public/v1/preview/C/A/HS"


def _sayfa(x: pd.ExcelFile, ad: str) -> pd.DataFrame:
    d = x.parse(ad, dtype=str)
    d = d.rename(columns={d.columns[0]: "kod"})
    yillar = [c for c in d.columns if str(c).strip().isdigit()]
    d = d[d["kod"].str.fullmatch(r"\d\d\.\d\d\.\d\d\.\d\d\.\d\d", na=False)]  # PRODTR düzeyi
    out = d.set_index("kod")[yillar]
    out.columns = [str(c).strip() for c in out.columns]
    # "c" = gizli, "." / "-" = yok
    return out.apply(lambda s: pd.to_numeric(s.str.replace(",", ".", regex=False), errors="coerce"))


def prodtr() -> pd.DataFrame:
    print("PRODTR Excel okunuyor…")
    x = pd.ExcelFile(HAM / "prodtr_2005_2025.xlsx", engine="calamine")
    kl = x.parse("Kod Listesi", dtype=str)
    kl.columns = ["kod", "duzey", "ad", "ad_en", "birim", "birim_en"][:len(kl.columns)]
    kl = kl[kl["duzey"].str.strip() == "PRODTR"].drop_duplicates("kod")
    kl["nace"] = "C" + kl["kod"].str[:2]
    kl["nace4"] = "C" + kl["kod"].str[:2] + kl["kod"].str[3:5]
    kl[["kod", "ad", "birim", "nace", "nace4"]].to_csv(DATA / "prodtr_urunler.csv", index=False)
    for sayfa, dosya in (("Satış Değeri", "prodtr_deger.csv"), ("Satış Miktarı", "prodtr_satis_miktar.csv"),
                         ("Üretim Miktarı", "prodtr_uretim_miktar.csv")):
        d = _sayfa(x, sayfa)
        d.to_csv(DATA / dosya)
        print(f"  {dosya}: {len(d)} ürün, {d.columns[0]}–{d.columns[-1]}")
    return kl


def eslesme() -> pd.DataFrame:
    print("GTİP–PRODTR eşlemesi okunuyor…")
    x = pd.ExcelFile(HAM / "gtip_prodtr_2018.xls", engine="calamine")
    parcalar = []
    for sh in x.sheet_names:
        d = x.parse(sh, header=None, dtype=str).iloc[:, :4]
        d.columns = ["gtip", "gtip_ad", "prodtr", "prodtr_ad"]
        parcalar.append(d)
    d = pd.concat(parcalar)
    d["gtip"] = d["gtip"].str.strip()
    d = d[d["gtip"].str.fullmatch(r"\d{12}", na=False) & d["prodtr"].notna()].drop_duplicates(["gtip", "prodtr"])
    d["hs6"] = d["gtip"].str[:6]
    d.to_csv(DATA / "gtip_prodtr.csv", index=False)
    print(f"  gtip_prodtr.csv: {len(d)} satır, {d['prodtr'].nunique()} PRODTR, {d['hs6'].nunique()} HS6")
    return d


def comtrade(hs6: list[str], yillar: list[int]) -> pd.DataFrame:
    print("UN Comtrade (Türkiye, HS6)…")
    rows = []
    ses = requests.Session()
    for yil in yillar:
        for i in range(0, len(hs6), 240):
            parca = hs6[i:i + 240]
            for deneme in range(4):
                r = ses.get(COMTRADE, params={"reporterCode": "792", "period": str(yil), "flowCode": "M,X",
                                              "cmdCode": ",".join(parca), "partnerCode": "0"}, timeout=180)
                if r.status_code == 200:
                    break
                time.sleep(5 * (deneme + 1))
            r.raise_for_status()
            for d in r.json().get("data", []):
                if d.get("customsCode") == "C00" and d.get("motCode") == 0 and d.get("partner2Code") == 0:
                    rows.append({"yil": yil, "akis": d["flowCode"], "hs6": d["cmdCode"],
                                 "deger_usd": d.get("primaryValue")})
            time.sleep(1.2)
        print(f"  {yil}: {sum(1 for r_ in rows if r_['yil'] == yil)} kayıt")
    out = pd.DataFrame(rows).drop_duplicates(["yil", "akis", "hs6"])
    out.to_csv(DATA / "comtrade_hs6.csv", index=False)
    return out


def kalemler() -> None:
    """Satış değerini, gizli PRODTR değerlerini PRODCOM düzeyinden tamamlayarak kalemlere ayırır.

    PRODCOM değeri açıklanmış ama altındaki bazı PRODTR'ler gizliyse (c), fark
    "<PRODCOM kodu>*" adlı bir kalem olarak eklenir. Böylece toplam, açıklanan
    PRODCOM toplamlarıyla tutarlı olur.
    """
    x = pd.ExcelFile(HAM / "prodtr_2005_2025.xlsx", engine="calamine")
    d = x.parse("Satış Değeri", dtype=str)
    d = d.rename(columns={d.columns[0]: "kod"})
    d.columns = [str(c).strip() for c in d.columns]
    d = d[d["kod"].str.match(r"^\d\d\.", na=False)].drop_duplicates("kod").set_index("kod")
    yillar = [c for c in d.columns if c.isdigit()]
    v = d[yillar].apply(lambda s_: pd.to_numeric(s_, errors="coerce"))
    kl = x.parse("Kod Listesi", dtype=str).iloc[:, [0, 2]]
    kl.columns = ["kod", "ad"]
    adlar = kl.drop_duplicates("kod").set_index("kod")["ad"]
    L = v.index.str.len()
    pc = [k for k in v.index[L == 11] if 10 <= int(k[:2]) <= 33]
    pt = v.index[L == 14]
    satirlar = {}
    for p in pc:
        tr = [t for t in pt if t.startswith(p + ".")]
        alt = v.loc[tr]
        for t in tr:
            satirlar[t] = alt.loc[t]
        fark = v.loc[p] - alt.sum(min_count=1).fillna(0)
        gizli = alt.isna().any()
        fark = fark.where((fark > 1) & gizli)
        if fark.notna().any():
            satirlar[p + "*"] = fark
    out = pd.DataFrame(satirlar).T
    out.index.name = "kalem"
    out.to_csv(DATA / "urun_deger.csv")
    bilgi = pd.DataFrame({"kalem": out.index})
    bilgi["kod"] = bilgi["kalem"].str.rstrip("*")
    bilgi["gizli"] = bilgi["kalem"].str.endswith("*")
    bilgi["ad"] = bilgi["kod"].map(adlar)
    bilgi.loc[bilgi["gizli"], "ad"] = bilgi.loc[bilgi["gizli"], "ad"] + " (gizli alt kalemler)"
    bilgi["nace"] = "C" + bilgi["kod"].str[:2]
    bilgi["nace4"] = "C" + bilgi["kod"].str[:2] + bilgi["kod"].str[3:5]
    bilgi.to_csv(DATA / "urun_bilgi.csv", index=False)
    son = yillar[-1]
    print(f"  urun_deger.csv: {len(out)} kalem; imalat {son} toplamı {out[son].sum() / 1e12:.2f} trilyon TL")


def pazar_gruplari() -> None:
    """PRODTR–HS6 ilişkisinden bağlı bileşenler (pazar grupları) üretir."""
    e = pd.read_csv(DATA / "gtip_prodtr.csv", dtype=str)
    e = e[e["prodtr"].str[:2].astype(int).between(10, 33)]
    ebeveyn: dict[str, str] = {}

    def bul(a: str) -> str:
        while ebeveyn.setdefault(a, a) != a:
            ebeveyn[a] = ebeveyn[ebeveyn[a]]
            a = ebeveyn[a]
        return a

    for p, h in zip(e["prodtr"], e["hs6"]):
        ebeveyn[bul("P" + p)] = bul("H" + h)
    e = e.assign(grup=[bul("P" + p) for p in e["prodtr"]])
    g = e[["prodtr", "hs6", "grup"]].drop_duplicates()
    g.to_csv(DATA / "pazar_grup.csv", index=False)
    print(f"  pazar_grup.csv: {g['grup'].nunique()} grup")


def main(argv: list[str]) -> int:
    prodtr()
    kalemler()
    e = eslesme()
    pazar_gruplari()
    if "--comtrade-yok" not in argv:
        deger = pd.read_csv(DATA / "prodtr_deger.csv", index_col=0)
        son = int(deger.columns[-1])
        comtrade(sorted(e["hs6"].unique()), [son - 1, son])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
