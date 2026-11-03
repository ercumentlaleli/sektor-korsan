# Sektör veri atlası

İmalat sanayii için TÜİK ve TCMB verilerini gösteren bir Streamlit panosu. sektorel.streamlit.app örnek alınarak yapıldı.

## Sekmeler
- **Atlas**: Üretimdeki yıllık değişim, altı göstergelik özet şerit (üretim, ciro, kapasite, ihracat, ücretli çalışan, Yİ-ÜFE) ve sektör haritası
- **Üretim ve fiyat**: Sektör seçimi, üretim endeksi, sektör sıralaması, sektörel ÜFE, son 24 ayın ısı haritası, üretici fiyatları, sektöre göre dış ticaret
- **İstihdam ve ciro**: Ücretli çalışan, nominal ve reel ciro, yurt içi ve yurt dışı ciro, sektör karşılaştırması
- **TCMB**: Kapasite kullanım oranı, reel efektif kur, USD/TRY
- **Haber**: Sektöre göre son 30 günün haberleri (Google Haberler RSS)
- **Ürünler**: PRODTR ürünlerinde satış değeri, hacim ve birim fiyat ayrıştırması; yurt içi pazar ve ithalat bağımlılığı; ürün tablosu
- **NACE 4'lü**: 3'lü ve 4'lü NACE düzeyinde sanayi üretim endeksleri
- **Firmalar**: İSO 500 ve İkinci 500 listeleri; pazar yapısı, il dağılımı, büyüme, firma listesi
- **Kod analizi**: PRODTR ya da GTİP koduyla arama; ürünün TL, dolar ve reel büyümesi, NACE sınıfı, sektör içindeki yeri ve eşleşen GTİP kodları
- **Veri**: Tablolar, CSV ve Excel indirme

## Çalıştırma
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Veri
Uygulama yalnızca `data/` klasöründeki CSV'leri okur; bu yüzden anında açılır, anahtar olmadan da çalışır. CSV'leri yenilemek için:
```bash
python scripts/guncelle.py          # EVDS + TÜİK + ürünler (İSO 500 hariç)
python scripts/guncelle.py --evds   # yalnızca EVDS
python scripts/guncelle.py --tuik   # yalnızca TÜİK
python scripts/guncelle.py --iso    # yalnızca İSO 500 (yılda bir, yeni liste çıkınca)
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
| `tuik_nace34.csv`, `nace_adlari.csv` | TÜİK SDMX | NACE 3'lü ve 4'lü sanayi üretim endeksleri ve adları |
| `dt_ihracat.csv`, `dt_ithalat.csv` | TÜİK, EVDS üzerinden | ISIC Rev.4'e göre aylık ihracat ve ithalat (bin $) |
| `iso500.csv` | iso500.org.tr | İSO 500 ve İkinci 500 (2024, 2025) |
| `urun_*.csv`, `prodtr_*.csv` | TÜİK Sanayi Ürün İstatistikleri (`data/ham/`) | 2005–2025 PRODTR satış değeri, miktar |
| `gtip_prodtr.csv`, `pazar_grup.csv` | TÜİK GTİP–PRODTR eşlemesi (`data/ham/`) | Eşleme ve pazar grupları |
| `comtrade_hs6.csv` | UN Comtrade (anahtarsız) | Türkiye'nin HS6 düzeyinde yıllık ithalat ve ihracatı |

## TÜİK SDMX
- İstemci `tuik.py` içinde. Anahtar `giris.tuik.gov.tr` üzerinden Bearer token'a çevrilir; veri `https://nsiws.tuik.gov.tr/rest/` adresinden SDMX-CSV olarak çekilir.
- Anahtar şu sırayla aranır: `TUIK_API_KEY` ortam değişkeni, `TUIK_SDMX_API_KEY` ortam değişkeni, `.streamlit/secrets.toml` içindeki `TUIK_API_KEY`.
- Göstergelerin hangi veri akışından geleceği `tuik_seriler.toml` dosyasında tanımlıdır. TÜİK servisi joker karakterli anahtarları kabul etmediği için veri akışları `all` ile çekilip süzülür. Yeni veri akışı eklemek için:
```bash
python scripts/tuik_kesfet.py --test        # anahtar ve bağlantı testi
python scripts/tuik_kesfet.py ciro sanayi   # adında bu kelimeler geçen veri akışları
python scripts/tuik_kesfet.py --boyut DF_X  # bir veri akışının boyutları ve örnek veri
```

## Ürün verileri hakkında
- `data/ham/` klasöründeki iki TÜİK dosyası `python scripts/urunler.py` ile işlenir; yeni yıl yayımlandığında dosyaları değiştirip betiği tekrar çalıştırmak yeterli.
- Gizli (c) PRODTR değerleri, açıklanan PRODCOM toplamından kalan fark olarak "(gizli alt kalemler)" satırına yazılır. Böylece imalat toplamı TÜİK'in açıkladığı toplamla tutarlıdır (2025: 16,7 trilyon ₺).
- İç pazar = yurt içi satış ($) − ihracat + ithalat. GTİP üzerinden birbirine bağlı PRODTR kodları tek pazar grubu olarak toplanır. Eşleme 2018 GTİP'e, Comtrade verisi HS 2022'ye dayandığı için bazı kodlarda sapma olabilir.

## Yayınlama

### 1. GitHub
Bu klasörü bir GitHub deposuna gönderin (`main` dalı).

### 2. Streamlit Community Cloud
1. share.streamlit.io adresinde GitHub hesabınızla giriş yapın → **Create app** → deponuzu, `main` dalını ve `app.py` dosyasını seçin.
2. **Advanced settings** bölümünde Python sürümünü **3.12** seçin.
3. **Secrets** alanına şunu yapıştırın (`.streamlit/secrets.toml.example` ile aynı):
   ```
   EVDS_API_KEY = "..."
   TUIK_API_KEY = "..."
   ```
4. **Deploy**. Depoya her yeni commit geldiğinde uygulama kendini yeniden yükler.

### 3. Günlük otomatik güncelleme (GitHub Actions)
`.github/workflows/veri-guncelle.yml` hafta içi her gün 10:47 ve 15:47'de (TSİ) EVDS, TÜİK ve ürün verilerini çeker (İSO 500 yılda bir yayımlandığı için dahil değildir; elle çalıştırırken kapsam alanına `--iso` yazın); değişiklik varsa `data/` klasörünü commit'ler. Streamlit Cloud bu commit'le uygulamayı günceller.

Depoda **Settings → Secrets and variables → Actions → New repository secret** ile iki secret ekleyin:
- `EVDS_API_KEY`
- `TUIK_API_KEY`

Elle çalıştırmak için: **Actions → Verileri güncelle → Run workflow**.
