# Sektör veri atlası

İmalat sanayii için TÜİK ve TCMB verilerini gösteren bir Streamlit panosu. sektorel.streamlit.app örnek alınarak yapıldı.

## Sekmeler
- **Atlas**: Üretim endeksindeki yıllık değişim, 6 göstergelik özet şerit (küçük grafiklerle) ve 23 sektörün renkli haritası
- **Üretim ve fiyat**: Sektör seçimi, üretim grafiği (yıllık % / 12 ay ortalama / endeks), sektör sıralaması, son 24 ayın ısı haritası, üretici fiyatlarının TÜFE ile karşılaştırması
- **İstihdam ve dış ticaret**: TÜİK SDMX'ten ücretli çalışan, ciro, sektörel dış ticaret, sektörel ÜFE (TÜİK API anahtarı gerekir)
- **TCMB**: Kapasite kullanım oranı, reel efektif kur, USD/TRY
- **Veri**: Tablolar, CSV ve Excel indirme

## Çalıştırma
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Veri
- `EVDS_API_KEY` ortam değişkeni ya da `.streamlit/secrets.toml` içinde `EVDS_API_KEY = "..."` tanımlıysa seriler EVDS'den canlı çekilir ve 6 saat önbellekte tutulur.
- Anahtar yoksa ya da istek başarısız olursa `data/` klasöründeki anlık veriler kullanılır (Kasım 2026'da EVDS'den alındı).
  - `makro.csv`: 2014–2026 arası üretim endeksi, Yİ-ÜFE, TÜFE, YD-ÜFE, kapasite kullanım oranı, reel efektif kur
  - `sektor_sue.csv`: 23 NACE sektörünün üretim endeksi (anlık veride 2023-09'dan itibaren; canlı modda 2014'ten itibaren)
  - `usdtry.csv`: Aylık ortalama dolar kuru

Seri kodları `data.py` içindedir.

## TÜİK SDMX
- İstemci `tuik.py` içinde. Anahtar `giris.tuik.gov.tr` üzerinden Bearer token'a çevrilir; veri `https://nsiws.tuik.gov.tr/rest/` adresinden SDMX-CSV olarak çekilir.
- Anahtar şu sırayla aranır: `TUIK_API_KEY` ortam değişkeni, `TUIK_SDMX_API_KEY` ortam değişkeni, `.streamlit/secrets.toml` içindeki `TUIK_API_KEY`.
- Uygulamadaki göstergelerin hangi veri akışından geleceği `tuik_seriler.toml` dosyasında tanımlanır. Veri akışı kimliklerini bulmak için:
```bash
python scripts/tuik_kesfet.py --test        # anahtar ve bağlantı testi
python scripts/tuik_kesfet.py ciro sanayi   # adında bu kelimeler geçen veri akışları
python scripts/tuik_kesfet.py --boyut DF_X  # bir veri akışının boyutları ve örnek veri
```
