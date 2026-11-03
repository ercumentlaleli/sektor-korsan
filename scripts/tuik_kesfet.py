"""TÜİK SDMX veri akışlarını keşfetme aracı.

Kullanım:
    python scripts/tuik_kesfet.py                 # tüm veri akışları
    python scripts/tuik_kesfet.py ciro sanayi     # adında kelime geçenler
    python scripts/tuik_kesfet.py --boyut DF_X    # boyutlar + örnek veri
    python scripts/tuik_kesfet.py --test          # anahtar ve bağlantı testi
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pandas as pd  # noqa: E402

from tuik import TuikClient, TuikError, api_key  # noqa: E402

pd.set_option("display.width", 200, "display.max_colwidth", 90, "display.max_rows", 500)


def main(argv: list[str]) -> int:
    key = api_key()
    if not key:
        print("TUIK_API_KEY tanımlı değil.")
        return 1
    c = TuikClient(key)
    try:
        if argv[:1] == ["--test"]:
            c.token()
            n = len(c.dataflows())
            print(f"Bağlantı tamam: {n} veri akışı erişilebilir.")
        elif argv[:1] == ["--boyut"]:
            df_id = argv[1]
            print("Boyutlar:", " . ".join(c.dimensions(df_id)))
            d = c.data(df_id, "all", start="2026-01")
            print(f"{len(d)} gözlem. Örnek:")
            print(d.head(15).to_string())
            for col in d.columns:
                if col not in ("TIME_PERIOD", "OBS_VALUE") and d[col].nunique() < 60:
                    print(f"  {col}: {sorted(d[col].dropna().unique())[:40]}")
        else:
            flows = c.dataflows()
            if argv:
                m = pd.Series(False, index=flows.index)
                for w in argv:
                    m |= flows["ad"].str.contains(w, case=False, na=False) | \
                         flows["name_en"].str.contains(w, case=False, na=False)
                flows = flows[m]
            print(flows.to_string(index=False))
    except TuikError as e:
        print("Hata:", e)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
