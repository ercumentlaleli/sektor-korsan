"""Ekrandaki sekmeyi tarayıcıda görüntüye çevirip PPTX olarak indiren düğmeler.

Sunum sunucuda değil, kullanıcının tarayıcısında üretilir: sekme paneli modern-screenshot ile
görüntüye çevrilir, bölüm numaralarından (01, 02 …) slaytlara bölünür ve PptxGenJS ile her slayta
bir görüntü olarak konur. Böylece slaytlar ekranda görünenle birebir aynıdır. Slayta sığmayacak
kadar uzun bölümler, satır sınırlarından (grafiklerin ortasından değil) birden çok slayta bölünür.

- sunum_dugmesi: yalnızca o anki sekme
- tum_sekmeler_dugmesi: sekmeleri sırayla açar (Veri hariç) ve hepsini tek sunumda birleştirir
"""
from __future__ import annotations

import json

import streamlit.components.v1 as components

_CEKIRDEK = r"""
<style>
  body{margin:0;font-family:Calibri,Carlito,'Segoe UI',Arial,sans-serif;background:transparent}
  button{width:100%;height:38px;border:1px solid #D9D9D9;border-radius:6px;background:#FFFFFF;color:#262626;font-weight:700;
         font-size:13.5px;cursor:pointer;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  button.ana{background:#203764;color:#fff;border-color:#203764}
  button:hover{filter:brightness(.96)} button:disabled{opacity:.7;cursor:wait}
</style>
<button id="b" class="__SINIF__">__ETIKET__</button>
<script>
const AYAR = __AYAR__;
const P = window.parent, D = P.document;
const bekle = ms => new Promise(r => setTimeout(r, ms));
function yukle(src, ad){
  return new Promise((ok, hata)=>{
    if (P[ad]) return ok();
    const s = D.createElement('script'); s.src = src; s.onload = ()=>ok(); s.onerror = hata; D.head.appendChild(s);
  });
}
function aktifPanel(){
  const ps = [...D.querySelectorAll('[data-testid="stTabPanel"]')];
  return ps.find(p => p.offsetParent !== null && p.getBoundingClientRect().height > 0) || ps[0];
}
// paneli görüntüye çevirip bölüm bölüm slayta ekler
async function paneliEkle(panel, pptx){
  // yakalama sırasında sayfa geniş düzene alınır: tüm slaytlar aynı genişlikte ve 16:9'a daha yakın olur
  D.body.classList.add('sunum-cekim'); P.dispatchEvent(new Event('resize')); await bekle(1500);
  try { return await paneliEkle_(panel, pptx); }
  finally { D.body.classList.remove('sunum-cekim'); P.dispatchEvent(new Event('resize')); }
}
async function paneliEkle_(panel, pptx){
  const kok = panel.getBoundingClientRect();
  const Y = el => el.getBoundingClientRect().top - kok.top;
  let bas = 0;
  const dugme = [...panel.querySelectorAll('iframe')].find(f => (f.srcdoc || '').includes('id="b"'));
  if (dugme){ const k = dugme.closest('[data-testid="stElementContainer"]') || dugme;
              bas = k.getBoundingClientRect().bottom - kok.top + 4; }
  const ilk = panel.querySelector('.eyebrow, .sbas');
  if (ilk) bas = Math.max(bas, Y(ilk) - 8);
  const son = kok.height;
  const kes = [...[...panel.querySelectorAll('.secno')].map(e => Y(e) - 6),
               ...[...panel.querySelectorAll('hr.slayt-ayrac')].map(e => Y(e) + e.getBoundingClientRect().height / 2)]
    .sort((a, b) => a - b).filter(y => y > bas + 40 && y < son);
  const blok = panel.querySelector('[data-testid="stVerticalBlock"]');
  const satir = blok ? [...blok.children].map(c => Y(c)).filter(y => y > bas) : [];
  const olcek = 1.6;
  const tuval = await P.modernScreenshot.domToCanvas(panel, {
    scale: olcek, backgroundColor: '#FFFFFF', filter: n => n.tagName !== 'IFRAME'
  });
  const W = kok.width, maxH = W * 0.8, esik = W * 1.05;
  const dilimler = [], sinir = [bas, ...kes, son];
  for (let i = 0; i < sinir.length - 1; i++){
    let a = sinir[i], z = sinir[i + 1];
    while (z - a > esik){                 // çok uzun bölümü satır sınırlarından böl
      const aday = satir.filter(y => y > a + maxH * 0.45 && y <= a + maxH);
      if (!aday.length) break;            // güvenli satır aralığı yoksa bölme, tek slayta sığdır
      const c = aday[aday.length - 1];
      dilimler.push([a, c]); a = c;
    }
    if (z - a > 30) dilimler.push([a, z]);
  }
  // her slayt kendi başlık şeridinden aynı boşlukla başlar; bitişte ayraç çizgisi dışarıda kalır
  const basliklar = [...panel.querySelectorAll('.sbas, .secno')].map(e => Y(e));
  const ayraclar = [...panel.querySelectorAll('hr.slayt-ayrac')].map(e => Y(e));
  for (const d of dilimler){
    const bs = basliklar.find(y => y >= d[0] - 2 && y < d[1]);
    if (bs !== undefined && bs - d[0] < 120) d[0] = bs - 6;
    const hr = ayraclar.find(y => y > d[0] && y <= d[1] + 2);
    if (hr !== undefined) d[1] = hr - 4;
  }
  // tüm slaytlarda ortak ölçek: başlık şeridi her slaytta aynı kalınlık ve genişlikte, üstten hizalı
  const kutuW = 12.73, kutuH = 6.95, ust = .28;
  const tamGen = kutuW / W;
  const sigdir = dilimler.map(([a, z]) => Math.min(tamGen, kutuH / (z - a)));
  const ortak = Math.max(Math.min(...sigdir), tamGen * 0.8);
  for (let i = 0; i < dilimler.length; i++){
    const [a, z] = dilimler[i];
    const c = D.createElement('canvas');
    c.width = Math.round(W * olcek); c.height = Math.round((z - a) * olcek);
    const x = c.getContext('2d'); x.fillStyle = '#FFFFFF'; x.fillRect(0, 0, c.width, c.height);
    x.drawImage(tuval, 0, Math.round(a * olcek), c.width, c.height, 0, 0, c.width, c.height);
    const sl = pptx.addSlide(); sl.background = { color: 'FFFFFF' };
    const k = Math.min(ortak, sigdir[i]);          // ortak ölçeğe sığmayan istisnai uzun dilim küçültülür
    const w = W * k, h = (z - a) * k;
    sl.addImage({ data: c.toDataURL('image/png'), x: (13.333 - w) / 2, y: ust, w, h });
  }
  return dilimler.length;
}
function kapak(pptx, baslik, alt){
  const sl = pptx.addSlide(); sl.background = { color: 'FFFFFF' };
  sl.addText('SEKTÖR VERİ ATLASI', { x: .8, y: 2.3, w: 11.5, h: .4, fontSize: 13, bold: true, color: '203764', fontFace: 'Calibri' });
  sl.addText(baslik, { x: .8, y: 2.8, w: 11.5, h: 1.3, fontSize: 44, color: '203764', fontFace: 'Calibri', bold: true });
  sl.addText(alt, { x: .8, y: 4.2, w: 11.5, h: .5, fontSize: 16, color: '595959', fontFace: 'Calibri' });
}
document.getElementById('b').onclick = async ()=>{
  const b = document.getElementById('b'); const etiket = b.textContent; b.disabled = true;
  try{
    b.textContent = 'Hazırlanıyor…';
    await yukle('https://cdn.jsdelivr.net/npm/modern-screenshot@4.6.0/dist/index.js', 'modernScreenshot');
    await yukle('https://cdn.jsdelivr.net/npm/pptxgenjs@3.12.0/dist/pptxgen.bundle.js', 'PptxGenJS');
    const pptx = new P.PptxGenJS(); pptx.layout = 'LAYOUT_WIDE';   // 13.33 x 7.5 in
    if (!AYAR.hepsi){
      await paneliEkle(aktifPanel(), pptx);
    } else {
      const sekmeler = [...D.querySelectorAll('[data-baseweb="tab"], [role="tab"]')]
        .filter((t, i, a) => a.indexOf(t) === i && !AYAR.haric.includes(t.textContent.trim()));
      const ilkSekme = sekmeler.find(t => t.getAttribute('aria-selected') === 'true') || sekmeler[0];
      const tarih = new Date().toLocaleDateString('tr-TR');
      kapak(pptx, AYAR.sektor, `Atlas, üretim ve fiyat, istihdam, TCMB, haber, ürünler, NACE 4'lü, firmalar · ${tarih}`);
      let n = 0;
      for (const t of sekmeler){
        n++; b.textContent = `${n}/${sekmeler.length} · ${t.textContent.trim()}`;
        t.click(); await bekle(1800);          // sekme ve grafiklerin yerleşmesi için
        P.dispatchEvent(new Event('resize')); await bekle(600);
        await paneliEkle(aktifPanel(), pptx);
      }
      ilkSekme.click();
    }
    b.textContent = 'İndiriliyor…';
    await pptx.writeFile({ fileName: AYAR.dosya });
    b.textContent = '✓ İndirildi';
  }catch(e){ console.error(e); b.textContent = 'Hata: ' + (e && e.message ? e.message : e); }
  setTimeout(()=>{ b.disabled = false; b.textContent = etiket; }, 3000);
};
</script>
"""


def _bilesen(etiket: str, ayar: dict, sinif: str = "") -> None:
    html = (_CEKIRDEK.replace("__AYAR__", json.dumps(ayar, ensure_ascii=False))
            .replace("__ETIKET__", etiket).replace("__SINIF__", sinif))
    components.html(html, height=42)


def sunum_dugmesi(dosya_adi: str) -> None:
    """Ekrandaki sekmeyi slaytlara çeviren indirme düğmesi (tarayıcıda çalışır)."""
    _bilesen("⬇ Sunumu indir (PPTX)", {"dosya": dosya_adi, "hepsi": False})


def tum_sekmeler_dugmesi(dosya_adi: str, sektor_adi: str) -> None:
    """Tüm sekmeleri (Veri hariç) sırayla yakalayıp tek sunumda birleştiren düğme."""
    _bilesen("⬇ Tüm sekmeler (PPTX)", {"dosya": dosya_adi, "hepsi": True, "sektor": sektor_adi,
                                       "haric": ["Veri", "Sunum"]}, sinif="ana")
