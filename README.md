# Sektör veri atlası

İmalat sanayii için TÜİK ve TCMB verilerini gösteren bir Streamlit panosu. sektorel.streamlit.app örnek alınarak yapıldı.

## Sekmeler
- **Atlas**: Üretim endeksindeki yıllık değişim, 6 göstergelik özet şerit (küçük grafiklerle) ve 23 sektörün renkli haritası
- **Üretim ve fiyat**: Sektör seçimi, üretim grafiği (yıllık % / 12 ay ortalama / endeks), sektör sıralaması, son 24 ayın ısı haritası, üretici fiyatlarının TÜFE ile karşılaştırması
- **İstihdam ve ciro** (TÜİK SDMX): ücretli çalışan, nominal ve reel ciro, yurt içi ve yurt dışı ciro, sektör karşılaştırması
- **TCMB**: Kapasite kullanım oranı, reel efektif kur, USD/TRY
- **Veri**: Tablolar, CSV ve Excel indirme

## Çalıştırma
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Veri
Uygulama yalnızca `data/` klasöründeki CSV'leri okur; bu yüzden anında açılır, anahtar olmadan da çalışır. CSV'leri yenilemek için:
```bash
python scripts/guncelle.py          # EVDS + TÜİK (yaklaşık 4–5 dk)
python scripts/guncelle.py --evds   # yalnızca EVDS
python scripts/guncelle.py --tuik   # yalnızca TÜİK
```
Kenar çubuğundaki **Verileri şimdi güncelle** düğmesi de aynı betiği çalıştırır. Gerekli ortam değişkenleri `EVDS_API_KEY` ve `TUIK_API_KEY`. Betik günlük olarak cron ya da GitHub Actions ile çalıştırılabilir.

| Dosya | Kaynak | İçerik |
|---|---|---|
| `makro.csv` | EVDS | İmalat SÜE, Yİ-ÜFE, TÜFE, YD-ÜFE, kapasite kullanım oranı, reel efektif kur |
| `sektor_sue.csv` | EVDS | 23 sektörün sanayi üretim endeksi |
| `usdtry.csv` | EVDS | Aylık ortalama USD/TRY |
| `tuik_ucretli_calisan.csv` | TÜİK SDMX | Ücretli çalışan sayısı, sektörlere göre |
| `tuik_ciro*.csv` | TÜİK SDMX | Ciro endeksi (toplam, yurt içi, yurt dışı), sektörlere göre |
| `tuik_yiufe.csv`, `tuik_ydufe.csv` | TÜİK SDMX | Sektörel Yİ-ÜFE ve YD-ÜFE |

## TÜİK SDMX
- İstemci `tuik.py` içinde. Anahtar `giris.tuik.gov.tr` üzerinden Bearer token'a çevrilir; veri `https://nsiws.tuik.gov.tr/rest/` adresinden SDMX-CSV olarak çekilir.
- Anahtar şu sırayla aranır: `TUIK_API_KEY` ortam değişkeni, `TUIK_SDMX_API_KEY` ortam değişkeni, `.streamlit/secrets.toml` içindeki `TUIK_API_KEY`.
- Göstergelerin hangi veri akışından geleceği `tuik_seriler.toml` dosyasında tanımlıdır. TÜİK servisi joker karakterli anahtarları kabul etmediği için veri akışları `all` ile çekilip süzülür. Yeni veri akışı eklemek için:
```bash
python scripts/tuik_kesfet.py --test        # anahtar ve bağlantı testi
python scripts/tuik_kesfet.py ciro sanayi   # adında bu kelimeler geçen veri akışları
python scripts/tuik_kesfet.py --boyut DF_X  # bir veri akışının boyutları ve örnek veri
```
