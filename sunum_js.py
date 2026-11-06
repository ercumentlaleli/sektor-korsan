"""Ekrandaki sekmeyi tarayıcıda görüntüye çevirip PPTX olarak indiren düğme.

Sunum sunucuda değil, kullanıcının tarayıcısında üretilir: sekme paneli modern-screenshot ile
görüntüye çevrilir, bölüm numaralarından (01, 02 …) slaytlara bölünür ve PptxGenJS ile her slayta
bir görüntü olarak konur. Böylece slaytlar ekranda görünenle birebir aynıdır. Slayta sığmayacak
kadar uzun bölümler, satır sınırlarından (grafiklerin ortasından değil) birden çok slayta bölünür.
"""
from __future__ import annotations

import json

import streamlit.components.v1 as components

_JS = r"""
<style>
  body{margin:0;font-family:Inter,system-ui,sans-serif;background:transparent}
  button{width:100%;height:38px;border:1px solid #d9d1c3;border-radius:6px;background:#fffdf8;color:#1d1d1b;
         font-size:14px;cursor:pointer}
  button:hover{background:#efe9df} button:disabled{opacity:.6;cursor:wait}
</style>
<button id="b">⬇ Sunumu indir (PPTX)</button>
<script>
const AYAR = __AYAR__;
const P = window.parent, D = P.document;
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
document.getElementById('b').onclick = async ()=>{
  const b = document.getElementById('b'); b.disabled = true; b.textContent = 'Hazırlanıyor…';
  try{
    await yukle('https://cdn.jsdelivr.net/npm/modern-screenshot@4.6.0/dist/index.js', 'modernScreenshot');
    await yukle('https://cdn.jsdelivr.net/npm/pptxgenjs@3.12.0/dist/pptxgen.bundle.js', 'PptxGenJS');
    const panel = aktifPanel();
    const kok = panel.getBoundingClientRect();
    const Y = el => el.getBoundingClientRect().top - kok.top;
    // başlangıç: düğmenin bulunduğu satırın altı (seçim kutuları dahil, düğme hariç)
    const benim = window.frameElement.closest('[data-testid="stElementContainer"]') || window.frameElement;
    let bas = benim.getBoundingClientRect().bottom - kok.top + 4;
    const ilk = panel.querySelector('.eyebrow');
    if (AYAR.basliktan && ilk) bas = Math.max(bas, Y(ilk) - 8);
    const son = kok.height;
    // bölüm sınırları
    const kes = [...panel.querySelectorAll('.secno')].map(e => Y(e) - 6).filter(y => y > bas + 40 && y < son);
    // güvenli bölme noktaları: ana dikey bloktaki satırların üst kenarları
    const blok = panel.querySelector('[data-testid="stVerticalBlock"]');
    const satir = blok ? [...blok.children].map(c => Y(c)).filter(y => y > bas) : [];
    const olcek = 1.6;
    const tuval = await P.modernScreenshot.domToCanvas(panel, {
      scale: olcek, backgroundColor: '#F4EFE6',
      filter: n => !(n.tagName === 'IFRAME' && n === window.frameElement)
    });
    const W = kok.width, maxH = W * 0.8, esik = W * 1.05;
    let dilimler = [], sinir = [bas, ...kes, son];
    for (let i = 0; i < sinir.length - 1; i++){
      let a = sinir[i], z = sinir[i + 1];
      while (z - a > esik){                // çok uzun bölümü satır sınırlarından böl
        const aday = satir.filter(y => y > a + maxH * 0.45 && y <= a + maxH);
        if (!aday.length) break;            // güvenli satır aralığı yoksa bölme, tek slayta sığdır
        const c = aday[aday.length - 1];
        dilimler.push([a, c]); a = c;
      }
      if (z - a > 30) dilimler.push([a, z]);
    }
    const pptx = new P.PptxGenJS(); pptx.layout = 'LAYOUT_WIDE';   // 13.33 x 7.5 in
    for (const [a, z] of dilimler){
      const c = D.createElement('canvas');
      c.width = Math.round(W * olcek); c.height = Math.round((z - a) * olcek);
      const x = c.getContext('2d'); x.fillStyle = '#F4EFE6'; x.fillRect(0, 0, c.width, c.height);
      x.drawImage(tuval, 0, Math.round(a * olcek), c.width, c.height, 0, 0, c.width, c.height);
      const sl = pptx.addSlide(); sl.background = { color: 'F4EFE6' };
      const kutuW = 12.73, kutuH = 6.9, oran = c.height / c.width;
      let w = kutuW, h = kutuW * oran; if (h > kutuH){ h = kutuH; w = h / oran; }
      sl.addImage({ data: c.toDataURL('image/png'), x: (13.333 - w) / 2, y: (7.5 - h) / 2, w, h });
    }
    await pptx.writeFile({ fileName: AYAR.dosya });
    b.textContent = '✓ İndirildi';
  }catch(e){ console.error(e); b.textContent = 'Hata: ' + (e && e.message ? e.message : e); }
  setTimeout(()=>{ b.disabled = false; b.textContent = '⬇ Sunumu indir (PPTX)'; }, 3000);
};
</script>
"""


def sunum_dugmesi(dosya_adi: str, basliktan: bool = True) -> None:
    """Ekrandaki sekmeyi slaytlara çeviren indirme düğmesi (tarayıcıda çalışır)."""
    ayar = json.dumps({"dosya": dosya_adi, "basliktan": basliktan})
    components.html(_JS.replace("__AYAR__", ayar), height=42)
