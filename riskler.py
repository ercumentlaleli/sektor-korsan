"""Sunum, slayt 14: sektöre ilişkin riskler (NACE 2'li koda göre).

Her madde: (başlık, etiket, metin). Etiket "Fırsat" ise kart yeşil tonla gösterilir.
Metinler sektör geneli için yazılmıştır; yeni sektör eklemek için aynı yapıda bir liste eklemek yeterlidir.
"""

RISKLER: dict[str, list[tuple[str, str, str]]] = {
    "C13": [
        ("Hammadde fiyatları", "Maliyet",
         "Küresel pamuk, polyester ve iplik fiyatlarındaki dalgalanmalar üretim maliyetlerini etkileyerek sektörün iç ve "
         "dış pazardaki rekabet gücü üzerinde baskı oluşturabilir. İklim değişikliğinin yurt içi pamuk üretimini olumsuz "
         "etkilemesi hammadde arzına ilişkin riski artırmaktadır."),
        ("Jeopolitik ve makroekonomik belirsizlik", "Maliyet",
         "Makroekonomik belirsizlikler ile ABD-İsrail ve İran savaşı gibi jeopolitik gelişmeler, enerji ve hammadde "
         "maliyetlerini yükselterek sektörün kârlılığı ve satış gelirleri üzerinde aşağı yönlü baskı oluşturabilir."),
        ("Rusya ve ABD pazarları", "Dış pazar",
         "Rusya Federasyonu'na yönelik yaptırımlar ve ödeme-bankacılık kanallarındaki güçlükler tahsilat sürelerini ve "
         "tahsilat riskini artırabilir. ABD'de uygulanan ilave gümrük vergileri ve ticaret politikalarındaki belirsizlikler "
         "ise bu pazardaki fiyat rekabetini ve satış hacmini olumsuz etkileyebilir."),
        ("Avrupa'da zayıf talep", "Dış talep",
         "Ev tekstili ve döşemelik kumaş talebi konut ve mobilya sektörlerine bağlıdır. Başta Avrupa olmak üzere ana "
         "ihracat pazarlarındaki yüksek faiz ortamı, zayıf tüketici harcamaları ve konut sektöründeki durgunluk sipariş "
         "hacimleri üzerinde aşağı yönlü baskı oluşturabilir."),
        ("Kur ve maliyet dengesi", "Kârlılık",
         "Yurt içinde maliyet artışlarının kur artışının üzerinde seyretmesi, ihracat ağırlıklı satış yapısına sahip "
         "sektörde kârlılığı sınırlamaktadır."),
        ("Düşük maliyetli üretici ülkeler", "Rekabet",
         "Ucuz işgücü, enerji maliyetleri ve ticaret anlaşmaları nedeniyle üretim yatırımlarının Mısır gibi ülkelere kayması "
         "ve Bangladeş, Vietnam ve Hindistan'ın küresel pazar payını artırması, orta ve uzun vadede fiyat rekabeti "
         "üzerinde baskı oluşturabilir."),
        ("PEM menşe kümülasyonu ve AB-Hindistan STA", "Rekabet",
         "PEM anlaşması kapsamındaki çapraz menşe kümülasyonunun Mısır gibi düşük maliyetli ülkelerce etkin kullanılması "
         "ve AB'nin Hindistan ile müzakerelerini tamamladığı serbest ticaret anlaşması, AB pazarında fiyat rekabetini "
         "artırarak Türkiye'nin tercihli konumunu ve pazar payını zayıflatabilir."),
        ("AB sürdürülebilirlik düzenlemeleri", "Düzenleme",
         "Tekstil ürünleri ESPR 2025-2030 çalışma planındaki öncelikli ürün grupları arasındadır. Karbon ve çevresel ayak "
         "izi ile hammaddenin izlenebilirliği zamanla AB pazarına giriş kriterine dönüşebilir. Uyum ilave maliyet "
         "yaratırken uyum sağlayamayan üreticilerin ihracat gelirleri gerileyebilir; talep düşük maliyetli ve çevresel "
         "uyumu yüksek tedarikçilere yönelebilir."),
        ("Geri dönüştürülmüş elyaf talebi", "Düzenleme",
         "Avrupa pazarında geri dönüştürülmüş elyaf içerikli ürünlere yönelik talebin artması, hammadde tedarikinin ve "
         "ürün yapısının dönüştürülmesini gerektirmektedir. Bu dönüşüme uyum sağlayamayan üreticilerin AB pazarındaki "
         "rekabet gücü zayıflayabilir."),
        ("İthal boya ve kimyasallar", "Maliyet",
         "Boyama ve terbiyede kullanılan boya ve yardımcı kimyasalların önemli bölümü ithal edildiğinden döviz kuru, "
         "küresel kimyasal fiyatları ve lojistik maliyetlerindeki değişimler üretim maliyetlerini etkileyebilir. "
         "Kimyasal kullanımına yönelik çevresel düzenlemelerin sıkılaşması ilave uyum maliyeti doğurabilir."),
        ("Finansal kırılganlık", "Finansal",
         "Konkordato ilan eden ve faaliyetini sonlandıran işletme sayısındaki artış, sektörde finansal kırılganlığın "
         "yükseldiğine işaret etmektedir. 2025 yılında tekstil sektöründe 177 dosya için geçici mühlet kararı verilmiş; "
         "giyim, ayakkabı, halı, çanta, iplik imalatı ve deri işleme ile birlikte bu sayı 234'e ulaşmıştır."),
        ("Yatırım iştahı ve teknolojik yenilenme", "Yatırım",
         "Belirsizlikler ve düşük kârlılık nedeniyle firmalar kapasite artırımı yerine mevcut faaliyetlerini korumaya "
         "odaklanmaktadır. Jakarlı dokuma, dijital baskı ve otomasyon teknolojilerindeki yenilenmenin gecikmesi orta "
         "vadede verimlilik ve rekabet gücü kaybına yol açabilir."),
        ("Karbon fiyatlaması", "Düzenleme",
         "Tekstil ürünleri hâlihazırda AB Sınırda Karbon Düzenleme Mekanizması kapsamında değildir; Türkiye Emisyon "
         "Ticaret Sistemi de ilk aşamada yüksek emisyonlu büyük tesisleri kapsamaktadır. Doğrudan etki sınırlı olmakla "
         "birlikte sistemin enerji fiyatlarına yansıması dolaylı maliyet artışı yaratabilir."),
        ("Yakın coğrafyaya tedarik (nearshoring)", "Fırsat",
         "AB'nin \"Made in Europe\" yaklaşımı ağırlıklı olarak çelik, otomotiv ve temiz teknolojiyi hedeflediğinden "
         "sektöre doğrudan etkisi sınırlıdır. AB'nin tedarik zincirlerini Asya'dan yakın coğrafyalara kaydırma eğilimi ise "
         "Gümrük Birliği kapsamındaki Türk üreticilere teslim süresi ve lojistik avantajı sağlayabilir."),
    ],
}
