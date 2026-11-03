"""TÜİK SDMX REST istemcisi.

Akış (TÜİK SDMX Web Servisi belgelerine göre):
  1. API anahtarı -> giris.tuik.gov.tr (OpenID Connect) üzerinden Bearer token
  2. Token ile https://nsiws.tuik.gov.tr/rest/ altındaki SDMX 2.1 uç noktaları

Anahtar şu sırayla aranır: TUIK_API_KEY, TUIK_SDMX_API_KEY ortam değişkenleri,
ardından st.secrets["TUIK_API_KEY"].
"""
from __future__ import annotations

import io
import os
import time
import tomllib
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import requests

BASE_URL = "https://nsiws.tuik.gov.tr/rest/"
TOKEN_URL = "https://giris.tuik.gov.tr/realms/web/protocol/openid-connect/token"
CLIENT_ID = "nsi-ws-consumer"
AGENCY = "TR"
CSV_ACCEPT = "application/vnd.sdmx.data+csv;version=2.0"
CONFIG = Path(__file__).parent / "tuik_seriler.toml"

NS = {
    "m": "http://www.sdmx.org/resources/sdmxml/schemas/v2_1/message",
    "s": "http://www.sdmx.org/resources/sdmxml/schemas/v2_1/structure",
    "c": "http://www.sdmx.org/resources/sdmxml/schemas/v2_1/common",
}


def api_key() -> str | None:
    for name in ("TUIK_API_KEY", "TUIK_SDMX_API_KEY"):
        if os.environ.get(name, "").strip():
            return os.environ[name].strip()
    try:
        import streamlit as st
        k = st.secrets.get("TUIK_API_KEY")
        return str(k).strip() if k else None
    except Exception:
        return None


class TuikError(RuntimeError):
    pass


class TuikClient:
    def __init__(self, key: str, timeout: int = 60):
        self.key = key
        self.timeout = timeout
        self._token: str | None = None
        self._exp = 0.0

    # ---------------- kimlik doğrulama
    def token(self) -> str:
        if self._token and time.time() < self._exp - 30:
            return self._token
        r = requests.post(TOKEN_URL, data={"grant_type": "password", "client_id": CLIENT_ID,
                                           "api_key": self.key}, timeout=30)
        if r.status_code != 200:
            # yanıt gövdesi kimlik bilgisi içerebilir; yazdırmıyoruz
            raise TuikError(f"Token alınamadı (HTTP {r.status_code}). API anahtarını kontrol edin.")
        body = r.json()
        self._token = body["access_token"]
        self._exp = time.time() + float(body.get("expires_in", 300))
        return self._token

    def _get(self, path: str, params: dict | None = None, accept: str | None = None) -> requests.Response:
        headers = {"Authorization": f"Bearer {self.token()}"}
        if accept:
            headers["Accept"] = accept
        r = requests.get(BASE_URL + path, params=params, headers=headers, timeout=self.timeout)
        if r.status_code == 401:  # token süresi dolmuş olabilir: bir kez yenile
            self._token = None
            headers["Authorization"] = f"Bearer {self.token()}"
            r = requests.get(BASE_URL + path, params=params, headers=headers, timeout=self.timeout)
        if r.status_code == 404:
            raise TuikError(f"Bulunamadı: {path}")
        if r.status_code >= 400:
            raise TuikError(f"HTTP {r.status_code}: {path}")
        return r

    # ---------------- yapı (metadata)
    def dataflows(self) -> pd.DataFrame:
        """Tüm veri akışları: id, version, ad (TR/EN)."""
        xml = ET.fromstring(self._get(f"dataflow/{AGENCY}/all/latest").content)
        rows = []
        for df in xml.iter(f"{{{NS['s']}}}Dataflow"):
            names = {n.get("{http://www.w3.org/XML/1998/namespace}lang"): n.text
                     for n in df.findall("c:Name", NS)}
            rows.append({"id": df.get("id"), "version": df.get("version"),
                         "ad": names.get("tr") or next(iter(names.values()), ""),
                         "name_en": names.get("en", "")})
        return pd.DataFrame(rows)

    def dimensions(self, dataflow_id: str) -> list[str]:
        """Veri akışının boyutları (anahtar sırası)."""
        xml = ET.fromstring(self._get(f"dataflow/{AGENCY}/{dataflow_id}/latest",
                                      params={"references": "datastructure"}).content)
        dims = sorted(((int(d.get("position", 0)), d.get("id"))
                       for d in xml.iter(f"{{{NS['s']}}}Dimension")))
        return [d for _, d in dims]

    def codelist(self, dataflow_id: str, dimension: str) -> dict[str, str]:
        """Bir boyutun kod -> Türkçe ad sözlüğü."""
        xml = ET.fromstring(self._get(f"dataflow/{AGENCY}/{dataflow_id}/latest",
                                      params={"references": "all"}).content)
        cl_id = None
        for d in xml.iter(f"{{{NS['s']}}}Dimension"):
            if d.get("id") == dimension:
                ref = d.find(".//s:Enumeration/Ref", NS)
                cl_id = ref.get("id") if ref is not None else None
        lang = "{http://www.w3.org/XML/1998/namespace}lang"
        for cl in xml.iter(f"{{{NS['s']}}}Codelist"):
            if cl_id is None or cl.get("id") == cl_id:
                out = {}
                for code in cl.findall("s:Code", NS):
                    names = {n.get(lang): n.text for n in code.findall("c:Name", NS)}
                    out[code.get("id")] = names.get("tr") or next(iter(names.values()), "")
                if cl_id is not None:
                    return out
        return {}

    # ---------------- veri
    def data(self, dataflow_id: str, key: str = "all", start: str | None = None,
             end: str | None = None) -> pd.DataFrame:
        """SDMX-CSV 2.0 olarak veri çeker. Sütunlar: boyutlar + TIME_PERIOD + OBS_VALUE."""
        params = {}
        if start:
            params["startPeriod"] = start
        if end:
            params["endPeriod"] = end
        r = self._get(f"data/{dataflow_id}/{key}", params=params, accept=CSV_ACCEPT)
        if not r.content.strip():
            return pd.DataFrame()
        df = pd.read_csv(io.BytesIO(r.content), dtype=str)
        df["OBS_VALUE"] = pd.to_numeric(df["OBS_VALUE"].str.replace(",", "."), errors="coerce")
        return df


# ---------------- yapılandırmadan seri üretme

@dataclass
class SeriTanimi:
    ad: str
    dataflow: str
    key: str
    filtre: dict[str, str]
    sektor_boyutu: str | None
    aciklama: str


def tanimlar() -> dict[str, SeriTanimi]:
    """tuik_seriler.toml içindeki, dataflow alanı doldurulmuş tanımlar."""
    if not CONFIG.exists():
        return {}
    cfg = tomllib.loads(CONFIG.read_text(encoding="utf-8"))
    out = {}
    for ad, t in cfg.items():
        if not isinstance(t, dict) or not t.get("dataflow"):
            continue
        out[ad] = SeriTanimi(ad, t["dataflow"], t.get("key", "all"), t.get("filtre", {}),
                             t.get("sektor_boyutu"), t.get("aciklama", ad))
    return out


def _period(s: pd.Series) -> pd.PeriodIndex:
    s = s.str.replace("M", "-", regex=False)  # 2026M08 -> 2026-08
    return pd.PeriodIndex(pd.to_datetime(s, format="mixed"), freq="M")


def seri_cek(client: TuikClient, t: SeriTanimi, start: str = "2014-01",
             ham: pd.DataFrame | None = None) -> pd.DataFrame:
    """Tanıma göre veriyi çeker; satır=ay, sütun=NACE kodu (C ve C10..C33).

    `ham` verilirse istek atılmaz (aynı veri akışından birden çok seri üretmek için).
    """
    df = client.data(t.dataflow, t.key, start=start) if ham is None else ham
    if df.empty:
        return df
    for k, v in t.filtre.items():
        if k in df:
            df = df[df[k] == v]
    if "YAYIM_DONEMI" in df:  # birden çok yayım dönemi varsa en yenisi
        df = df[df["YAYIM_DONEMI"] == df["YAYIM_DONEMI"].max()]
    df = df.assign(tarih=_period(df["TIME_PERIOD"]))
    if t.sektor_boyutu and t.sektor_boyutu in df:
        df = df[df[t.sektor_boyutu].str.fullmatch(r"C(\d\d)?", na=False)]
        out = df.pivot_table(index="tarih", columns=t.sektor_boyutu, values="OBS_VALUE", aggfunc="first")
    else:
        out = df.groupby("tarih")["OBS_VALUE"].first().to_frame("C")
    return out.sort_index()
