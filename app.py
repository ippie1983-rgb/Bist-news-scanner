# ==============================================================================
# 🧩 SCANNER ENGINE (scanner_engine.py) - Achtergrondlogica & AI-Auditor
# ==============================================================================

import os
import re
import html
import json
import difflib
import yfinance as yf
import pandas as pd
import numpy as np
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from concurrent.futures import ThreadPoolExecutor

# ==============================================================================
# 🗂 BIST 30 CONFIGURATIE & META-DATA
# ==============================================================================
BIST_INDEX_OPTION = "📈 BIST 30 Index (Algemeen & Brede Markt)"

BIST_30_STOCKS = [
    "AKBNK (Akbank)", "ALARK (Alarko Holding)", "ASELS (Aselsan)", "ASTOR (Astor Enerji)", "BIMAS (Bim Mağazalar)",
    "BRSAN (Borusan Boru)", "CCOLA (Coca-Cola İçecek)", "DOAS (Doğuş Otomotiv)", "EKGYO (Emlak Konut GYO)", "ENKAI (Enka İnşaat)",
    "EREGL (Erdemir)", "FROTO (Ford Otosan)", "GARAN (Garanti BBVA)", "GUBRF (Gübre Fabrikaları)", "HEKTS (Hektaş)",
    "ISCTR (İş Bankası C)", "KCHOL (Koç Holding)", "KONTR (Kontrolmatik)", "KOZAL (Koza Altın)", "KRDMD (Kardemir D)",
    "MGROS (Migros)", "OYAKC (Oyak Çimento)", "PETKM (Petkim)", "PGSUS (Pegasus)", "SAHOL (Sabancı Holding)",
    "SASA (Sasa Polyester)", "SISE (Şişecam)", "TCELL (Turkcell)", "THYAO (Turkish Airlines)", "TUPRS (Tüpraş)"
]

BIST_30_META = {
    "AKBNK": {"name": "Akbank", "sector": "Banken", "consolidated": True},
    "ALARK": {"name": "Alarko Holding", "sector": "Holding & Energie", "consolidated": True},
    "ASELS": {"name": "Aselsan", "sector": "Defensie & Tech", "consolidated": True},
    "ASTOR": {"name": "Astor Enerji", "sector": "Energie & Transformatoren", "consolidated": False},
    "BIMAS": {"name": "Bim Mağazalar", "sector": "Supermarkten & Retail", "consolidated": True},
    "BRSAN": {"name": "Borusan Boru", "sector": "Staal & Industrie", "consolidated": True},
    "CCOLA": {"name": "Coca-Cola İçecek", "sector": "Voeding & Dranken", "consolidated": True},
    "DOAS": {"name": "Doğuş Otomotiv", "sector": "Automotive", "consolidated": True},
    "EKGYO": {"name": "Emlak Konut GYO", "sector": "Vastgoed (GYO)", "consolidated": False},
    "ENKAI": {"name": "Enka İnşaat", "sector": "Bouw & Energie", "consolidated": True},
    "EREGL": {"name": "Erdemir", "sector": "Staal & Mijnbouw", "consolidated": True},
    "FROTO": {"name": "Ford Otosan", "sector": "Automotive & Export", "consolidated": False},
    "GARAN": {"name": "Garanti BBVA", "sector": "Banken", "consolidated": True},
    "GUBRF": {"name": "Gübre Fabrikaları", "sector": "Agri & Mijnbouw", "consolidated": True},
    "HEKTS": {"name": "Hektaş", "sector": "Agri & Chemie", "consolidated": True},
    "ISCTR": {"name": "İş Bankası C", "sector": "Banken", "consolidated": True},
    "KCHOL": {"name": "Koç Holding", "sector": "Holding", "consolidated": True},
    "KONTR": {"name": "Kontrolmatik", "sector": "Tech & Energieopslag", "consolidated": True},
    "KOZAL": {"name": "Koza Altın", "sector": "Goudmijnen", "consolidated": False},
    "KRDMD": {"name": "Kardemir D", "sector": "Staal & Spoor", "consolidated": True},
    "MGROS": {"name": "Migros", "sector": "Supermarkten & Retail", "consolidated": True},
    "OYAKC": {"name": "Oyak Çimento", "sector": "Cement & Bouw", "consolidated": False},
    "PETKM": {"name": "Petkim", "sector": "Petrochemie", "consolidated": True},
    "PGSUS": {"name": "Pegasus", "sector": "Luchtvaart", "consolidated": True},
    "SAHOL": {"name": "Sabancı Holding", "sector": "Holding", "consolidated": True},
    "SASA": {"name": "Sasa Polyester", "sector": "Chemie & Industrie", "consolidated": False},
    "SISE": {"name": "Şişecam", "sector": "Glas & Industrie", "consolidated": True},
    "TCELL": {"name": "Turkcell", "sector": "Telecom & Tech", "consolidated": True},
    "THYAO": {"name": "Turkish Airlines", "sector": "Luchtvaart", "consolidated": True},
    "TUPRS": {"name": "Tüpraş", "sector": "Raffinage & Energie", "consolidated": True}
}

COMPANY_TO_TICKER_MAP = {
    "türk hava yolları": "THYAO", "turkish airlines": "THYAO", "aselsan": "ASELS", "koç holding": "KCHOL",
    "koc holding": "KCHOL", "akbank": "AKBNK", "garanti bbva": "GARAN", "garanti bankası": "GARAN",
    "tüpraş": "TUPRS", "tupras": "TUPRS", "bim mağazalar": "BIMAS", "erdemir": "EREGL", "ereğli demir": "EREGL",
    "şişecam": "SISE", "sisecam": "SISE", "sasa polyester": "SASA", "emlak konut": "EKGYO",
    "iş bankası": "ISCTR", "petkim": "PETKM", "pegasus": "PGSUS", "doğuş otomotiv": "DOAS",
    "enka inşaat": "ENKAI", "kardemir": "KRDMD", "turkcell": "TCELL", "ford otosan": "FROTO",
    "migros": "MGROS", "astor enerji": "ASTOR", "sabancı holding": "SAHOL", "oyak çimento": "OYAKC",
    "hektaş": "HEKTS", "kontrolmatik": "KONTR", "alarko": "ALARK", "borusan": "BRSAN",
    "gübre fabrikaları": "GUBRF", "koza altın": "KOZAL", "coca-cola içecek": "CCOLA"
}

DIRECT_TURKISH_RSS_FEEDS = [
    ("📰 Bloomberg HT (Direct)", "https://www.bloomberght.com/rss"),
    ("📰 Habertürk Ekonomi (Direct)", "https://www.haberturk.com/rss/ekonomi.xml"),
    ("📰 NTV Ekonomi (Direct)", "https://www.ntv.com.tr/ekonomi.rss"),
    ("📰 CNN Türk Ekonomi (Direct)", "https://www.cnnturk.com/feed/rss/ekonomi/news"),
    ("📰 Dünya Gazetesi (Direct)", "https://www.dunya.com/rss"),
    ("📰 Cumhuriyet Ekonomi (Direct)", "https://www.cumhuriyet.com.tr/rss/ekonomi.xml"),
    ("📰 T24 Gündem (Direct)", "https://t24.com.tr/rss")
]

HARD_EXCLUDE_WORDS = [
    "futbol", "maç", "gol", "süper lig", "galatasaray", "fenerbahçe", "beşiktaş", "trabzonspor", "derbi", "hakem", "transfer",
    "basketbol", "magazin", "dizi", "şarkıcı", "burç", "astroloji", "survivor", "uyuşturucu", "cinayet", "trafik kazası",
    "boşanma", "aldatma", "hava durumu", "yemek tarifi", "bulmaca"
]

ECONOMIC_POLITICAL_WHITELIST = [
    "ekonomi", "borsa", "bist", "hisse", "spk", "sermaye", "fon", "manipülasyon", "soruşturma", "operasyon", "gözaltı",
    "tutuklama", "ev hapsi", "kayyum", "tmsf", "ceza", "görevden", "resmi gazete", "tcmb", "merkez bankası", "faiz",
    "enflasyon", "tüik", "şimşek", "erdoğan", "karahan", "dolar", "altın", "gümüş", "petrol", "cds", "fitch", "moody",
    "temettü", "kap", "bilanço", "ihale", "goud", "zilver", "rente", "inflatie", "oorlog", "olie", "geopolitiek", "fed"
]

STOPWORDS_ALL = {
    "de", "het", "een", "en", "van", "in", "op", "voor", "met", "aan", "tot", "bij", "naar", "over", "door", "uit", "als", "dat",
    "die", "dit", "zijn", "was", "wordt", "werden", "heeft", "hebben", "niet", "ook", "nog", "wel", "maar", "dan", "wat", "wie",
    "bir", "ve", "ile", "için", "bu", "şu", "da", "den", "mi", "mı", "mu", "mü", "ama", "fakat", "ancak", "gibi", "kadar", "sonra",
    "önce", "üzere", "göre", "karşı", "rağmen", "son", "dakika", "haber", "flaş", "şok", "yeni", "gelişme", "açıklama", "karar",
    "oldu", "geldi", "verildi", "yapıldı", "dedi", "söyledi", "hakkında", "olarak", "devam", "ediyor", "etti", "çıktı", "büyük"
}

COMMON_CAPITALIZED_IGNORE = {
    "son", "dakika", "flaş", "şok", "türkiye", "istanbul", "ankara", "borsa", "bist", "spk", "tcmb", "merkez", "bankası",
    "resmi", "gazete", "hisse", "kap", "tüik", "fed", "abd", "avrupa", "altın", "gümüş", "dolar", "euro", "petrol"
}

SEMANTIC_CONCEPT_DICT = {
    "CONCEPT_HUISARREST": ["ev hapsi", "konutu terk etmeme", "elektronik kelepçe", "huisarrest", "enkelband", "thuisdetentie"],
    "CONCEPT_ARRESTATIE_JUSTITIE": ["tutuklandı", "tutuklama", "gözaltı", "operasyonu", "savcılık", "gearresteerd", "aangehouden", "celstraf"],
    "CONCEPT_FONDS_MANIPULATIE": ["fon soruşturması", "fon skandalı", "fon vurgunu", "fon tasfiye", "manipülasyon", "fondsschandaal", "beursmanipulatie"],
    "CONCEPT_SPK_MAATREGEL": ["işlem yasağı", "brüt takas", "tedbir kararı", "vbts", "spk bülteni", "handelsverbod", "spk boete"],
    "CONCEPT_KAYYUM_BESLAG": ["kayyum", "tmsf", "mal varlığına el konuldu", "el koyma", "curator", "beslag gelegd"],
    "CONCEPT_ONTSLAG_BENOEMING": ["görevden alındı", "atama kararı", "istifa etti", "ontslagen", "afgetreden"],
    "CONCEPT_BURG_GEMEENTE": ["belediye başkanı", "belediyesine", "burgemeester", "gemeente"],
    "CONCEPT_RESMI_GAZETE_BELASTING": ["resmi gazete", "cumhurbaşkanı kararı", "ötv", "vergi", "staatsblad", "belasting"],
    "CONCEPT_TCMB_RENTE": ["faiz kararı", "ppk toplantısı", "politika faizi", "merkez bankası faiz", "fatih karahan", "rentebesluit"],
    "CONCEPT_INFLATIE_TUIK": ["enflasyon rakamları", "tüfe", "tüik", "inflatiecijfers", "consumentenprijzen"],
    "CONCEPT_CDS_KREDIETNOOT": ["cds primi", "kredi notu", "fitch", "moody's", "s&p", "yabancı yatırımcı", "kredietwaardigheid"],
    "CONCEPT_GOUD_ZILVER": ["altın fiyatları", "gram altın", "ons altın", "gümüş fiyatları", "goudprijs", "zilverprijs", "edelmetalen"],
    "CONCEPT_FED_VS_TRUMP": ["jerome powell", "fed faiz", "fomc", "donald trump", "yaptırım", "gümrük", "amerikaanse rente", "handelsoorlog"],
    "CONCEPT_OORLOG_OLIE": ["orta doğu", "israil", "iran", "ukrayna", "rusya", "brent petrol", "midden-oosten", "olieprijs", "geopolitiek"],
    "CONCEPT_KAP_DIVIDEND_BILANCO": ["bilanço", "net kar", "temettü", "bedelsiz", "bedelli", "kwartaalcijfers", "nettowinst", "dividend", "aandelensplitsing"]
}

FAMOUS_PERSONS = [
    "mahfi eğilmez", "özgür demirtaş", "emre alkin", "hakan kara", "islam memiş", "ışık ökte",
    "tunç şatıroğlu", "mehmet şimşek", "fatih karahan", "recep tayyip erdoğan", "cevdet yılmaz",
    "ekrem imamoğlu", "donald trump", "jerome powell"
]

def normalize_tr(text):
    if not text: return ""
    return text.translate(str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")).lower()

def is_economically_relevant(title, description="", extra_tickers=None, custom_kw=""):
    text = normalize_tr(f"{title or ''} {description or ''}")
    custom = normalize_tr(custom_kw or "").strip()
    if custom and custom in text: return True
    if extra_tickers:
        for ticker in extra_tickers:
            if re.search(r"(?<![a-z0-9])" + re.escape(str(ticker).lower()) + r"(?![a-z0-9])", text): return True
    if any(normalize_tr(word) in text for word in ECONOMIC_POLITICAL_WHITELIST): return True
    if any(re.search(r"(?<!\w)" + re.escape(normalize_tr(bad)) + r"(?!\w)", text) for bad in HARD_EXCLUDE_WORDS): return False
    return False

def extract_proper_entities_and_numbers(title_orig, title_nl):
    entities = set()
    for txt in [title_orig, title_nl]:
        for tok in re.findall(r'\b[A-ZÇĞİÖŞÜ][a-zçğıöşü]{2,}\b', txt):
            nt = normalize_tr(tok)
            if nt not in COMMON_CAPITALIZED_IGNORE and nt not in STOPWORDS_ALL:
                entities.add(nt[:5] if len(nt) >= 5 else nt)
    numbers = set(re.findall(r'\b\d+\b', f"{title_orig} {title_nl}"))
    return entities, numbers

def analyze_article_semantics(item, all_bist_tickers):
    text_raw = f"{item.get('title_orig', '')} {item.get('desc_orig', '')} {item.get('title_nl', '')} {item.get('desc_nl', '')}".lower()
    text_norm = normalize_tr(text_raw)
    
    m_tickers = set()
    for comp, tck in COMPANY_TO_TICKER_MAP.items():
        if comp in text_raw or normalize_tr(comp) in text_norm: m_tickers.add(tck.upper())
    for tck in all_bist_tickers:
        if re.search(r'\b' + re.escape(tck.lower()) + r'\b', text_raw): m_tickers.add(tck.upper())
        
    m_persons = {normalize_tr(p) for p in FAMOUS_PERSONS if p in text_raw or normalize_tr(p) in text_norm}
    entities, numbers = extract_proper_entities_and_numbers(item.get("title_orig", ""), item.get("title_nl", ""))
    
    m_concepts = []
    for c_key, phrases in SEMANTIC_CONCEPT_DICT.items():
        if any(p in text_raw or normalize_tr(p) in text_norm for p in phrases): m_concepts.append(c_key)
        
    core_stems = {w[:5] for w in re.findall(r'[a-z0-9]{4,}', text_norm) if w not in STOPWORDS_ALL and w[:5] not in STOPWORDS_ALL}
    
    cluster, topic = None, "📰 Algemeen Economisch Bericht"
    if "CONCEPT_HUISARREST" in m_concepts: cluster, topic = "CLUSTER_HUISARREST_ZAAK", "⚖️ Dossier: Huisarrest & Maatregel"
    elif "CONCEPT_FONDS_MANIPULATIE" in m_concepts: cluster, topic = "CLUSTER_FONDS_SCHANDAAL", "🚨 Dossier: Fondsschandaal"
    elif "CONCEPT_KAYYUM_BESLAG" in m_concepts: cluster, topic = "CLUSTER_KAYYUM_TMSF", "🏛️ Dossier: Kayyum / TMSF"
    elif "CONCEPT_SPK_MAATREGEL" in m_concepts: cluster, topic = f"CLUSTER_SPK_{'_'.join(sorted(m_tickers))}", "⚠️ Dossier: SPK Maatregel"
    elif "CONCEPT_ARRESTATIE_JUSTITIE" in m_concepts: cluster, topic = "CLUSTER_ARRESTATIE", "🚓 Dossier: Justitie"
    elif "CONCEPT_RESMI_GAZETE_BELASTING" in m_concepts: cluster, topic = "CLUSTER_RESMI_GAZETE", "📜 Dossier: Resmi Gazete"
    elif m_persons and any(p in m_persons for p in ["mahfi egilmez", "ozgur demirtas", "emre alkin", "hakan kara", "islam memis"]):
        cluster, topic = f"CLUSTER_ECON_{sorted(list(m_persons))[0]}", f"🧠 Analyse: {sorted(list(m_persons))[0].title()}"
    elif m_tickers: cluster, topic = f"CLUSTER_AANDEEL_{'_'.join(sorted(m_tickers))}", f"🏢 Aandeel: {', '.join(sorted(m_tickers))}"
    elif "CONCEPT_TCMB_RENTE" in m_concepts: cluster, topic = "CLUSTER_TCMB", "🏦 Dossier: TCMB Rente"
    elif "CONCEPT_INFLATIE_TUIK" in m_concepts: cluster, topic = "CLUSTER_TUIK", "📊 Dossier: Inflatie (TÜİK)"
    
    item.update({
        "_matched_tickers": m_tickers, "_matched_persons": m_persons, "_proper_entities": entities,
        "_numbers": numbers, "_matched_concepts": set(m_concepts), "_core_stems": core_stems,
        "_story_cluster": cluster, "topic_readable": topic
    })
    return item

def translate_to_nl(text):
    if not text or len(text.strip()) < 3: return text
    try:
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=nl&dt=t&q={urllib.parse.quote(text[:480])}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return "".join([part[0] for part in data[0] if part and part[0]]) or text
    except: return text

def clean_html_text(raw_html):
    if not raw_html: return ""
    clean = html.unescape(re.sub(r'<[^>]+>', ' ', raw_html))
    clean = clean.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ').replace('`', "'").replace('*', '')
    return re.sub(r'\s+', ' ', clean).strip()

def _hidden_double_check_auditor(code, rev_growth, net_growth, net_val, prev_net_val, profit_margin, curr_price, sma20, rsi):
    if net_val is None:
        return (
            "⏳ Afwachtend (Geen vers kwartaalrapport in feed)",
            "De primaire cijfers zijn nog niet verwerkt in de datastroom; wacht op het officiële KAP-bilanço rapport.",
            "⚠️ Dubbel-Check: Nog niet geverifieerd wegens ontbrekende balansregel."
        )

    initial_positive = False
    if net_val > 0 and (net_growth is not None and net_growth > 5.0):
        initial_positive = True
    elif net_val < 0:
        initial_positive = False

    warnings = []
    if rev_growth is not None and rev_growth < -2.0 and (net_growth is not None and net_growth > 0):
        warnings.append("Winst steeg, maar omzet kromp (mogelijk eenmalige boekhoudkundige meevaller).")
    if profit_margin is not None and profit_margin < 3.0 and net_val > 0:
        warnings.append(f"Winstmarge is flinterdun ({profit_margin:.1f}%).")
    if curr_price < sma20 and initial_positive:
        warnings.append("Cijfers ogen goed, maar de koers handelt nog onder SMA20 (markt prijst nog risico in).")
    if rsi > 72 and initial_positive:
        warnings.append(f"Goede cijfers zijn mogelijk al ingeprijsd (RSI staat hoog op {rsi:.1f}).")

    if net_val < 0:
        verdict = "🔴 Negatief (Verliesgevend Kwartaal)"
        reason = f"Het bedrijf boekte een nettoverlies van ₺{net_val:,.0f}. Hoge financieringskosten drukken het resultaat.".replace(",", ".")
        check_status = "✅ Gecontroleerd & Bevestigd (Hard verlies)"
    elif initial_positive and not warnings:
        verdict = "🟢 Positief (Gezonde Winst- & Omzetgroei)"
        reason = (
            f"Nettowinst groeide met {net_growth:+.1f}% (Omzetontwikkeling: {rev_growth:+.1f}% | Marge: {profit_margin:.1f}%). "
            f"Zowel fundamenteel als technisch ({'boven' if curr_price >= sma20 else 'rond'} SMA20) ondersteund."
        )
        check_status = "✅ Dubbel-Check Akkoord (Zuivere kwaliteit)"
    elif initial_positive and warnings:
        verdict = "🟡 Voorzichtig Positief (Met Kanttekening)"
        reason = f"Winst groeide met {net_growth:+.1f}%, maar let op: {' '.join(warnings)}"
        check_status = "🔎 Gecorrigeerd door Controle-Agent"
    elif net_growth is not None and net_growth < -5.0:
        verdict = "🔴 Negatief (Winstkrimp)"
        reason = f"De nettowinst daalde met {net_growth:+.1f}% t.o.v. het vorige kwartaal. Margedruk zichtbaar."
        check_status = "✅ Gecontroleerd & Bevestigd (Winstdaling)"
    else:
        verdict = "⚖️ Neutraal (Stabiel Kwartaal)"
        reason = "Resultaten liggen in lijn met het voorgaande kwartaal zonder extreme uitschieters."
        check_status = "✅ Gecontroleerd"

    return verdict, reason, check_status

@st.cache_data(ttl=300, show_spinner=False)
def get_live_market_snapshot():
    symbols = {
        "BIST 30": "XU030.IS", "BIST 100": "XU100.IS", "USD/TRY": "USDTRY=X",
        "EUR/TRY": "EURTRY=X", "Goud Ons ($)": "GC=F", "Zilver Ons ($)": "SI=F",
        "Brent Olie ($)": "BZ=F", "VIX (Angst)": "^VIX"
    }
    data = {}
    for name, sym in symbols.items():
        try:
            hist = yf.Ticker(sym).history(period="5d")
            if hist is not None and len(hist) >= 2:
                curr, prev = float(hist["Close"].iloc[-1]), float(hist["Close"].iloc[-2])
                data[name] = {"price": curr, "change": ((curr - prev) / prev) * 100.0, "as_of": str(hist.index[-1].date())}
            else:
                data[name] = {"price": None, "change": 0.0, "as_of": "N/B"}
        except:
            data[name] = {"price": None, "change": 0.0, "as_of": "N/B"}
        
    usd_try = data.get("USD/TRY", {}).get("price")
    gold_usd = data.get("Goud Ons ($)", {}).get("price")
    silv_usd = data.get("Zilver Ons ($)", {}).get("price")
    if usd_try and gold_usd:
        data["Gram Goud (₺)"] = {"price": (gold_usd * usd_try) / 31.1035, "change": data["Goud Ons ($)"]["change"] + data["USD/TRY"]["change"]}
    if usd_try and silv_usd:
        data["Gram Zilver (₺)"] = {"price": (silv_usd * usd_try) / 31.1035, "change": data["Zilver Ons ($)"]["change"] + data["USD/TRY"]["change"]}
    return data

@st.cache_data(ttl=600, show_spinner=False)
def get_bist_technical_snapshots(tickers_tuple):
    snapshots = {}
    yf_symbols = [f"{c}.IS" for c in tickers_tuple]
    bulk_data = {}
    try:
        raw_bulk = yf.download(yf_symbols, period="3mo", group_by="ticker", progress=False, threads=True)
        for c in tickers_tuple:
            sym = f"{c}.IS"
            if sym in raw_bulk and not raw_bulk[sym].dropna(how="all").empty:
                bulk_data[c] = raw_bulk[sym].dropna(subset=["Close"])
    except:
        pass

    for code in tickers_tuple:
        meta = BIST_30_META.get(code, {"name": code, "sector": "BIST 30", "consolidated": True})
        expected_q_date = "Uiterlijk 20-11-2026 (Q3 Geconsolideerd)" if meta["consolidated"] else "Uiterlijk 09-11-2026 (Q3 Niet-Gecons.)"
        
        try:
            t_obj = yf.Ticker(f"{code}.IS")
            hist = bulk_data.get(code)
            if hist is None or len(hist) < 5:
                hist = t_obj.history(period="3mo")
            if hist is None or len(hist) < 5:
                hist = t_obj.history(period="1mo")
                
            if hist is not None and not hist.empty:
                close_s = hist["Close"].dropna().astype(float)
                high_s = hist["High"].dropna().astype(float) if "High" in hist else close_s
                low_s = hist["Low"].dropna().astype(float) if "Low" in hist else close_s
                vol_s = hist["Volume"].dropna().astype(float) if "Volume" in hist else pd.Series([1.0]*len(close_s))

                curr = float(close_s.iloc[-1])
                prev = float(close_s.iloc[-2]) if len(close_s) >= 2 else curr
                chg_1d = ((curr - prev) / prev) * 100.0 if prev > 0 else 0.0
                
                sma20 = float(close_s.rolling(min(20, len(close_s))).mean().iloc[-1])
                sma50 = float(close_s.rolling(50).mean().iloc[-1]) if len(close_s) >= 50 else sma20
                
                vol_curr = float(vol_s.iloc[-1]) if len(vol_s) > 0 else 0.0
                vol_sma20 = float(vol_s.rolling(min(20, len(vol_s))).mean().iloc[-1]) if len(vol_s) > 0 else 1.0
                vol_ratio = (vol_curr / vol_sma20) * 100.0 if vol_sma20 > 0 else 100.0
                
                delta = close_s.diff()
                gain = delta.clip(lower=0).ewm(alpha=1/14, min_periods=min(10, len(close_s)), adjust=False).mean().iloc[-1]
                loss = (-delta.clip(upper=0)).ewm(alpha=1/14, min_periods=min(10, len(close_s)), adjust=False).mean().iloc[-1]
                rsi = 100.0 - (100.0 / (1.0 + (gain / loss))) if loss and loss > 0 else 50.0
                
                w_h = float(high_s.tail(20).max())
                w_l = float(low_s.tail(20).min())
                pivot = (w_h + w_l + curr) / 3.0
                rng = max(w_h - w_l, curr * 0.02)
                
                s1, s2, s3 = pivot - (0.382 * rng), pivot - (0.618 * rng), pivot - rng
                r1, r2, r3 = pivot + (0.382 * rng), pivot + (0.618 * rng), pivot + rng
                dist_s1 = ((curr - s1) / curr) * 100.0 if curr > 0 else 0.0
                history_prices = [round(float(x), 2) for x in close_s.tail(30).tolist()]
                
                q_known_period = "Wacht op KAP-sync"
                q_rev_str, q_net_str = "Zie KAP", "Zie KAP"
                rev_growth, net_growth, profit_margin = None, None, None
                net_val, prev_net_val = None, None
                
                try:
                    q_fin = t_obj.quarterly_income_stmt
                    if q_fin is None or q_fin.empty:
                        q_fin = t_obj.quarterly_financials
                    if q_fin is not None and not q_fin.empty:
                        cols_q = q_fin.columns[:2]
                        latest_col = cols_q[0]
                        prev_col = cols_q[1] if len(cols_q) > 1 else None
                        
                        q_date_str = str(latest_col.date()) if hasattr(latest_col, "date") else str(latest_col)[:10]
                        q_known_period = f"Bekend t/m {q_date_str}"
                        
                        rev_rows = [r for r in q_fin.index if any(k in str(r).lower() for k in ["total revenue", "operating revenue", "revenue", "interest income"])]
                        net_rows = [r for r in q_fin.index if any(k in str(r).lower() for k in ["net income", "net profit"])]
                        
                        rev_val = float(q_fin.loc[rev_rows[0], latest_col]) if rev_rows and pd.notna(q_fin.loc[rev_rows[0], latest_col]) else None
                        prev_rev_val = float(q_fin.loc[rev_rows[0], prev_col]) if rev_rows and prev_col is not None and pd.notna(q_fin.loc[rev_rows[0], prev_col]) else None
                        
                        net_val = float(q_fin.loc[net_rows[0], latest_col]) if net_rows and pd.notna(q_fin.loc[net_rows[0], latest_col]) else None
                        prev_net_val = float(q_fin.loc[net_rows[0], prev_col]) if net_rows and prev_col is not None and pd.notna(q_fin.loc[net_rows[0], prev_col]) else None
                        
                        if rev_val is not None: q_rev_str = f"₺{rev_val:,.0f}".replace(",", ".")
                        if net_val is not None: q_net_str = f"₺{net_val:,.0f}".replace(",", ".")
                        
                        if rev_val and prev_rev_val and prev_rev_val != 0:
                            rev_growth = ((rev_val - prev_rev_val) / abs(prev_rev_val)) * 100.0
                        if net_val is not None and prev_net_val is not None and prev_net_val != 0:
                            net_growth = ((net_val - prev_net_val) / abs(prev_net_val)) * 100.0
                        if rev_val and net_val is not None and rev_val > 0:
                            profit_margin = (net_val / rev_val) * 100.0
                except:
                    pass

                verdict, reason, hidden_audit_status = _hidden_double_check_auditor(
                    code, rev_growth, net_growth, net_val, prev_net_val, profit_margin, curr, sma20, float(rsi)
                )

                snapshots[code] = {
                    "name": meta["name"], "sector": meta["sector"],
                    "price": round(curr, 2), "change": round(chg_1d, 2), "rsi": round(float(rsi), 1),
                    "sma20": round(sma20, 2), "sma50": round(sma50, 2),
                    "s1": round(s1, 2), "s2": round(s2, 2), "s3": round(s3, 2),
                    "r1": round(r1, 2), "r2": round(r2, 2), "r3": round(r3, 2),
                    "dist_s1": round(dist_s1, 2), "vol_ratio": round(vol_ratio, 1),
                    "history": history_prices,
                    "q_known": q_known_period, "q_expected": expected_q_date,
                    "q_rev": q_rev_str, "q_net": q_net_str,
                    "audit_verdict": verdict, "audit_reason": f"{reason} [{hidden_audit_status}]",
                    "trend": "📈 Boven SMA20" if curr >= sma20 else "📉 Onder SMA20"
                }
            else:
                snapshots[code] = {
                    "name": meta["name"], "sector": meta["sector"],
                    "price": 0.0, "change": 0.0, "rsi": 50.0, "sma20": 0.0, "sma50": 0.0,
                    "s1": 0.0, "s2": 0.0, "s3": 0.0, "r1": 0.0, "r2": 0.0, "r3": 0.0,
                    "dist_s1": 0.0, "vol_ratio": 100.0, "history": [0.0, 0.0],
                    "q_known": "Nog niet geladen", "q_expected": expected_q_date,
                    "q_rev": "N/B", "q_net": "N/B",
                    "audit_verdict": "⏳ Data ophalen", "audit_reason": "Herlaad of controleer KAP.",
                    "trend": "⚖️ Data vertraagd"
                }
        except:
            snapshots[code] = {
                "name": meta["name"], "sector": meta["sector"],
                "price": 0.0, "change": 0.0, "rsi": 50.0, "sma20": 0.0, "sma50": 0.0,
                "s1": 0.0, "s2": 0.0, "s3": 0.0, "r1": 0.0, "r2": 0.0, "r3": 0.0,
                "dist_s1": 0.0, "vol_ratio": 100.0, "history": [0.0, 0.0],
                "q_known": "Nog niet geladen", "q_expected": expected_q_date,
                "q_rev": "N/B", "q_net": "N/B",
                "audit_verdict": "⏳ Data ophalen", "audit_reason": "Herlaad of controleer KAP.",
                "trend": "⚖️ Data vertraagd"
            }
    return snapshots

def detect_sector_and_badge(combined_text, mentioned_stocks):
    sectors = []
    if any(w in combined_text for w in ["banka", "faiz", "tcmb", "akbnk", "garan", "ykbnk", "isctr"]):
        sectors.append("🏦 Banken (AKBNK, GARAN, ISCTR)")
    if any(w in combined_text for w in ["savunma", "asels", "oorlog", "navo"]):
        sectors.append("🛡️ Defensie (ASELS)")
    if any(w in combined_text for w in ["havayolu", "thyao", "pgsus", "luchtvaart", "turizm"]):
        sectors.append("✈️ Luchtvaart (THYAO, PGSUS)")
    if any(w in combined_text for w in ["petrol", "enerji", "tuprs", "astor", "olie", "raffinage"]):
        sectors.append("⚡ Energie & Raffinage (TUPRS, ASTOR)")
    if any(w in combined_text for w in ["market", "gıda", "enflasyon", "bimas", "mgros", "ccola"]):
        sectors.append("🛒 Retail & Voeding (BIMAS, MGROS, CCOLA)")
    if mentioned_stocks:
        sectors.insert(0, f"🎯 Specifiek aandeel: {', '.join(sorted(mentioned_stocks))}")
    if not sectors:
        sectors.append("📈 Brede BIST 30 Markt & USD/TRY")
    
    if any(w in combined_text for w in ["tutuklama", "gözaltı", "soruşturma", "ceza", "işlem yasağı", "kayyum", "ev hapsi"]):
        return '<span class="badge-neg">🔴 HOOG RISICO / KOERSDRUK</span>', " · ".join(sectors[:3]), "neg"
    elif any(w in combined_text for w in ["temettü", "bedelsiz", "rekor", "not artışı", "yabancı"]):
        return '<span class="badge-pos">🟢 POSITIEVE KATALYSATOR</span>', " · ".join(sectors[:3]), "pos"
    elif any(w in combined_text for w in ["resmi gazete", "vergi", "faiz", "enflasyon", "trump", "fed"]):
        return '<span class="badge-warn">⚠️ BELEID & MACRO</span>', " · ".join(sectors[:3]), "warn"
    return '<span class="badge-info">⚖️ MARKT DUIDING</span>', " · ".join(sectors[:3]), "info"

def build_jip_en_janneke_analysis(title_orig, title_nl, desc_nl, matched_tickers, cat):
    combined = f"{title_orig} {title_nl} {desc_nl}".lower()
    badge_html, sector_str, sentiment_type = detect_sector_and_badge(combined, matched_tickers)

    actual_content = desc_nl if desc_nl and len(desc_nl) > 25 else title_nl
    if actual_content.lower().startswith(title_nl.lower()):
        actual_content = actual_content[len(title_nl):].strip(" -|:")
    if not actual_content or len(actual_content) < 15:
        actual_content = f"{title_nl}. {desc_nl}".strip()

    if any(w in combined for w in ["brüt takas", "işlem yasağı", "tedbir", "bedelsiz"]):
        card_class = "scandal-card" if "yasağı" in combined or "brüt" in combined else "positive-card"
        impact = (
            "Waarom dit telt: Een SPK-handelsmaatregel ('brüt takas' of kredietverbod) haalt direct de snelheid en hefboom uit een aandeel, "
            "waardoor kortetermijnspeculanten gedwongen verkopen. Een goedgekeurde 'bedelsiz' (gratis aandelensplitsing) maakt het aandeel optisch goedkoper en trekt juist extra particuliere kopers aan."
        )
    elif any(w in combined for w in ["fon", "spk", "tutuklama", "gözaltı", "kayyum", "soruşturma", "ev hapsi"]):
        card_class = "scandal-card"
        impact = (
            "Waarom dit telt: Grote (buitenlandse) fondsen hanteren strenge compliance-regels. Zodra een bedrijf, fonds of bestuurder wordt geraakt door huisarrest, "
            "beslaglegging (TMSF/kayyum) of manipulatie-onderzoek, verkopen instellingen direct om reputatie- en bevriezingsrisico te vermijden. "
            "Wie lijdt hieronder: Speculatieve fondsen en direct genoemde bedrijven; grote liquide BIST 30-banken vangen soms het vluchtkapitaal op."
        )
    elif any(w in combined for w in ["resmi gazete", "vergi", "ötv", "atama"]):
        card_class = "news-card"
        impact = (
            "Waarom dit telt: Besluiten in the Resmi Gazete zijn direct wet bij beursopening. Hogere belastingen (zoals ÖTV) maken auto's en consumentengoederen duurder, "
            "wat de omzet van autofabrikanten (FROTO, DOAS) en industrie kan afremmen. Subsidies of infrastructuurbesluiten helpen juist bouw en energie (ENKAI, ASTOR, EKGYO)."
        )
    elif any(w in combined for w in ["faiz", "tcmb", "enflasyon", "fed", "powell", "tüik"]):
        card_class = "news-card"
        impact = (
            "Waarom dit telt: Rente en inflatie bepalen de waardering van de hele BIST 30. Zolang de rente extreem hoog blijft, lijden bedrijven met veel schulden of grote investeringsplannen "
            "(zoals SASA, HEKTS, KRDMD) onder zware rentelasten, terwijl supermarkten (BIMAS, MGROS) prijsstijgingen makkelijker doorberekenen aan de klant. "
            "Lagere inflatie opent de deur naar renteverlagingen, wat vooral banken (AKBNK, GARAN, ISCTR) en vastgoed (EKGYO) omhoog stuwt."
        )
    elif any(w in combined for w in ["trump", "abd", "savaş", "israil", "rusya", "oorlog", "sanctie", "iran", "petrol"]):
        card_class = "news-card"
        impact = (
            "Waarom dit telt: Geopolitieke spanning en oorlogsdreiging jagen de olieprijs op en zorgen voor vluchtgedrag naar veilige havens (Goud en Zilver stijgen). "
            "Wie lijdt hieronder: Luchtvaartmaatschappijen (THYAO, PGSUS) krijgen te maken met duurdere kerosine en mogelijke vluchtannuleringen. "
            "Wie profiteert: Defensiegigant ASELSAN en raffinaderij Tüpraş (TUPRS) presteren vaak sterker tijdens regionale spanningen."
        )
    else:
        card_class = "news-card"
        impact = (
            "Waarom dit telt: Bedrijfsspecifieke KAP-meldingen (nieuwe orders, dividend, kwartaalwinst) en kapitaalstromen bepalen welke BIST 30-aandelen beter presteren dan het marktgemiddelde. "
            "Exporteurs met inkomsten in dollars of euro's (FROTO, THYAO, SISE, ENKAI) zijn daarbij beter beschermd tegen een zwakkere Lira."
        )

    if matched_tickers:
        impact += f" Direct gekoppelde BIST 30-aandelen in dit dossier: {', '.join(sorted(matched_tickers))}."

    return actual_content, impact, card_class, badge_html, sector_str, sentiment_type

def calculate_article_priority_and_sort_key(item):
    cat, text = item.get("category", ""), f"{item.get('title_orig', '')} {item.get('title_nl', '')} {item.get('desc_orig', '')}".lower()
    
    if "🔎 Vrije Zoekopdracht" in cat: prio, lbl = 1, "🔎 Prio 1: Eigen Zoekopdracht"
    elif any(k in cat for k in ["Fondsschandaal", "SPK Bulletin", "Politiek", "Resmi Gazete"]) or any(w in text for w in ["fon", "spk", "manipülasyon", "tutuklama", "gözaltı", "kayyum", "resmi gazete", "ev hapsi"]):
        prio, lbl = 1, "🔥 Prio 1: Schandaal & Justitie"
    elif any(k in cat for k in ["BIST", "Top-Economen", "CDS-Premie"]) or any(w in text for w in ["tcmb", "merkez bankası", "faiz", "enflasyon", "mehmet şimşek", "cds"]):
        prio, lbl = 2, "📈 Prio 2: Macro & BIST 30"
    elif "Bedrijfsnieuws" in cat or item.get("_matched_tickers"): prio, lbl = 3, "🏢 Prio 3: Bedrijfsnieuws (KAP)"
    else: prio, lbl = 4, "🌍 Prio 4: Globaal & Edelmetalen"

    item.update({"priority_level": prio, "priority_label": lbl})
    return prio

def fetch_google_rss_feed(args):
    cat_label, query, lang, max_items, max_days, extra_tickers, custom_kw = args
    q_enc = urllib.parse.quote(f"{query} when:{max_days}d" if max_days else query)
    url = f"https://news.google.com/rss/search?q={q_enc}&hl={lang}&gl={lang.upper()}&ceid={lang.upper()}:{lang}"
    
    items, now_utc = [], datetime.now(timezone.utc)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            root = ET.fromstring(resp.read())
        for item in root.findall(".//item"):
            title, link = item.findtext("title") or "", item.findtext("link") or ""
            desc = clean_html_text(item.findtext("description") or "")
            src = item.find("source").text if item.find("source") is not None else "Nieuws"
            if not title or not link: continue
            
            title = clean_html_text(title.rsplit(" - ", 1)[0].strip() if " - " in title else title.strip())
            if src in desc: desc = desc.replace(src, "").strip(" -·")
            if not is_economically_relevant(title, desc, extra_tickers, custom_kw): continue
            
            dt = now_utc
            pub_str = item.findtext("pubDate")
            if pub_str:
                try:
                    p_dt = parsedate_to_datetime(pub_str)
                    if p_dt: dt = p_dt if p_dt.tzinfo else p_dt.replace(tzinfo=timezone.utc)
                except: pass
            
            items.append({"category": cat_label, "title_orig": title, "desc_orig": desc, "source": src, "link": link, "datetime": dt, "date_str": dt.strftime("%d-%m-%Y %H:%M"), "lang": lang})
            if len(items) >= max_items: break
        record_source(cat_label, "OK" if items else "Geen resultaten", len(items))
    except Exception as e: record_source(cat_label, "FOUT", 0, str(e))
    return items

def fetch_direct_newspaper_rss(args):
    source_label, url, max_days, extra_tickers, custom_kw = args
    items, now_utc = [], datetime.now(timezone.utc)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            root = ET.fromstring(resp.read())
        for item in root.findall(".//item")[:18]:
            title, link = clean_html_text(item.findtext("title") or ""), (item.findtext("link") or "").strip()
            desc = clean_html_text(item.findtext("description") or "")
            if not title or not link or not is_economically_relevant(title, desc, extra_tickers, custom_kw): continue
            
            dt, pub_str = now_utc, item.findtext("pubDate")
            if pub_str:
                try:
                    p_dt = parsedate_to_datetime(pub_str)
                    if p_dt: dt = p_dt if p_dt.tzinfo else p_dt.replace(tzinfo=timezone.utc)
                except: pass
                
            items.append({"category": source_label, "title_orig": title, "desc_orig": desc[:350], "source": source_label.split(" ")[1], "link": link, "datetime": dt, "date_str": dt.strftime("%d-%m-%Y %H:%M"), "lang": "tr"})
        record_source(source_label, "OK" if items else "Geen resultaten", len(items))
    except Exception as e: record_source(source_label, "FOUT", 0, str(e))
    return items

def enrich_articles_with_dutch_summaries(items, all_bist_codes):
    def process_one(item):
        item["title_nl"] = clean_html_text(translate_to_nl(item["title_orig"])) if item["lang"] == "tr" else clean_html_text(item["title_orig"])
        item["desc_nl"] = clean_html_text(translate_to_nl(item["desc_orig"])) if item["lang"] == "tr" else clean_html_text(item["desc_orig"])
        
        analyze_article_semantics(item, all_bist_codes)
        jip, imp, c_cls, bdg, sec, s_type = build_jip_en_janneke_analysis(item["title_orig"], item["title_nl"], item["desc_nl"], item.get("_matched_tickers", set()), item["category"])
        item.update({"jip": jip, "impact": imp, "card_class": c_cls, "badge_html": bdg, "sector_str": sec, "sentiment_type": s_type})
        calculate_article_priority_and_sort_key(item)
        return item

    with ThreadPoolExecutor(max_workers=10) as ex: return list(ex.map(process_one, items))

def deduplicate_by_semantic_content(enriched_list, max_mode=False):
    unique_items, seen_links = [], set()
    sorted_candidates = sorted(enriched_list, key=lambda x: (x.get("priority_level", 4), -x.get("datetime", datetime.now(timezone.utc)).timestamp()))
    
    for item in sorted_candidates:
        norm_link = item["link"].split("?")[0].rstrip("/").lower()
        if norm_link in seen_links: continue
        
        c_cluster, c_concepts, c_tickers, c_persons = item.get("_story_cluster"), item.get("_matched_concepts", set()), item.get("_matched_tickers", set()), item.get("_matched_persons", set())
        c_entities, c_numbers = item.get("_proper_entities", set()), item.get("_numbers", set())
        c_title = normalize_tr(item.get("title_orig", item.get("title_nl", "")))
        
        dup_of = None
        for ex in unique_items:
            ex_tickers = ex.get("_matched_tickers", set())
            if c_tickers and ex_tickers and not (c_tickers & ex_tickers): continue
            
            ex_title = normalize_tr(ex.get("title_orig", ex.get("title_nl", "")))
            sim = difflib.SequenceMatcher(None, c_title, ex_title).ratio() if c_title and ex_title else 0.0
            
            ex_concepts, ex_persons = ex.get("_matched_concepts", set()), ex.get("_matched_persons", set())
            sh_entities, sh_numbers = bool(c_entities & ex.get("_proper_entities", set())), bool(c_numbers & ex.get("_numbers", set()))
            
            same_person = bool(c_persons & ex_persons and c_concepts & ex_concepts and (sh_entities or sh_numbers or sim >= 0.72))
            same_ticker = bool(c_tickers & ex_tickers and c_concepts & ex_concepts and (sh_entities or sh_numbers or sim >= 0.78))
            same_cluster = bool(c_cluster and ex.get("_story_cluster") == c_cluster and (sh_entities or sh_numbers or sim >= 0.80))
            
            if sim >= (0.82 if max_mode else 0.88) or same_person or same_ticker or same_cluster:
                dup_of = ex
                break
                
        if dup_of:
            links = dup_of.setdefault("extra_source_links", [])
            if norm_link not in [l["link"].lower() for l in links]: links.append({"name": item["source"], "link": item["link"]})
            dup_of["merged_count"] = dup_of.get("merged_count", 1) + item.get("merged_count", 1)
        else:
            seen_links.add(norm_link)
            item["extra_source_links"] = list(item.get("extra_source_links", []))
            item["merged_count"] = 1
            unique_items.append(item)
    return unique_items

def get_upcoming_30_day_agenda():
    return [
        {"date": datetime(2026, 10, 28).date(), "time_str": "28-10-2026 (21:00 TR)", "title": "🇺🇸 Fed Rentebesluit & Powell", "jip": "De Amerikaanse centrale bank maakt haar rentebesluit bekend.", "impact": "Hint op lagere rente is positief voor Goud, Zilver en opkomende beurzen zoals BIST 30.", "link": "https://www.federalreserve.gov/"},
        {"date": datetime(2026, 10, 29).date(), "time_str": "29-10-2026 (Hele dag)", "title": "🇹🇷 Cumhuriyet Bayramı — Beurs Gesloten", "jip": "Nationale feestdag in Turkije. Borsa İstanbul is de hele dag gesloten.", "impact": "Handelaren bouwen vaak kort voor de feestdag hefboomposities af om geen kredietrente te betalen.", "link": "https://www.borsaistanbul.com/"},
        {"date": datetime(2026, 11, 3).date(), "time_str": "03-11-2026 (10:00 TR)", "title": "🇹🇷 TÜİK Inflatiecijfers (Oktober)", "jip": "Publicatie van de officiële Turkse consumentenprijzen (CPI).", "impact": "Lager dan verwachte inflatie geeft de TCMB ruimte voor renteverlaging en stuwt AKBNK, GARAN en ISCTR.", "link": "https://www.tuik.gov.tr/"},
        {"date": datetime(2026, 11, 6).date(), "time_str": "06-11-2026 (10:30 TR)", "title": "🇹🇷 TCMB 4e Inflatieverslag", "jip": "Gouverneur Fatih Karahan presenteert de nieuwe inflatieverwachtingen.", "impact": "Cruciaal voor de verwachte rente- en Lira-koers richting het jaareinde.", "link": "https://www.tcmb.gov.tr/"},
        {"date": datetime(2026, 11, 9).date(), "time_str": "09-11-2026 (18:00 TR)", "title": "🇹🇷 KAP Deadline Q3 Cijfers (Niet-Geconsolideerd)", "jip": "Uiterste publicatiedatum Q3-kwartaalcijfers voor niet-geconsolideerde BIST 30-bedrijven (o.a. ASTOR, EKGYO, FROTO, KOZAL, OYAKC, SASA).", "impact": "Zorgt voor directe koersreacties op basis van winstmarges.", "link": "https://www.kap.org.tr/"},
        {"date": datetime(2026, 11, 11).date(), "time_str": "11-11-2026 (16:30 TR)", "title": "🇺🇸 Amerikaanse Inflatiecijfers (US CPI)", "jip": "Publicatie van de Amerikaanse inflatiecijfers.", "impact": "Directe richtingaanwijzer voor de dollar, Goud en Zilver.", "link": "https://www.bls.gov/cpi/"},
        {"date": datetime(2026, 11, 19).date(), "time_str": "19-11-2026 (14:00 TR)", "title": "🇹🇷 TCMB Rentebesluit (PPK)", "jip": "De Turkse Centrale Bank maakt het nieuwe rentebesluit bekend.", "impact": "Hét belangrijkste binnenlandse macro-moment voor USD/TRY, Gram Goud en de BIST 30.", "link": "https://www.tcmb.gov.tr/"},
        {"date": datetime(2026, 11, 20).date(), "time_str": "20-11-2026 (18:00 TR)", "title": "🇹🇷 KAP Deadline Q3 Cijfers (Geconsolideerd & Banken)", "jip": "Uiterste datum voor grote holdings en banken (o.a. KCHOL, SAHOL, THYAO, AKBNK, GARAN, TUPRS) om hun Q3-cijfers te rapporteren.", "impact": "Bepaalt welke BIST 30-zwaargewichten de eindejaarsrally leiden.", "link": "https://www.kap.org.tr/"}
    ]
# ==============================================================================
# 🖥️ HOOFDBESTAND (app.py) - Streamlit User Interface & Command Center
# ==============================================================================

import streamlit as st
import pandas as pd
from datetime import datetime, timezone

# Importeer alle logica uit onze motor
from scanner_engine import (
    BIST_INDEX_OPTION, BIST_30_STOCKS, ALL_SIDEBAR_OPTIONS, 
    get_live_market_snapshot, get_bist_technical_snapshots, 
    get_upcoming_30_day_agenda, fetch_google_rss_feed, 
    fetch_direct_newspaper_rss, DIRECT_TURKISH_RSS_FEEDS,
    enrich_articles_with_dutch_summaries, deduplicate_by_semantic_content
)

# ==============================================================================
# ⚙️ PAGINA CONFIGURATIE & SCHONE CSS
# ==============================================================================
st.set_page_config(
    page_title="BIST 30 & Turkse Economie Master Scanner",
    page_icon="🇹🇷",
    layout="wide"
)

st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 1.55rem !important; white-space: nowrap !important; }
    
    /* Schone HTML Kaarten - Tekst breekt altijd netjes af */
    .clean-card {
        background-color: #ffffff; padding: 18px; border-radius: 8px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05); margin-bottom: 16px;
        word-wrap: break-word; overflow-wrap: break-word; white-space: normal;
        border-left: 5px solid #cbd5e1;
    }
    .clean-card.scandal-card { border-left-color: #ef4444; background-color: #fffafa; }
    .clean-card.positive-card { border-left-color: #10b981; background-color: #f7fee7; }
    .clean-card.news-card { border-left-color: #3b82f6; background-color: #ffffff; }
    
    .card-title { margin-top: 0; color: #0f172a; font-size: 18px; font-weight: 700; margin-bottom: 4px; line-height: 1.35; }
    .card-subtitle { font-size: 12px; color: #64748b; margin-bottom: 8px; }
    .card-text { font-size: 15px; color: #334155; line-height: 1.55; margin-bottom: 8px; }
    .card-text strong { color: #0f172a; }
    
    .prio-pill { background-color: #1e293b; color: white; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; }
    .topic-pill { background-color: #e2e8f0; color: #334155; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; }
    
    .badge-neg { background-color: #fee2e2; color: #991b1b; padding: 3px 6px; border-radius: 4px; font-size: 11px; font-weight: bold; }
    .badge-pos { background-color: #dcfce7; color: #166534; padding: 3px 6px; border-radius: 4px; font-size: 11px; font-weight: bold; }
    .badge-warn { background-color: #fef9c3; color: #854d0e; padding: 3px 6px; border-radius: 4px; font-size: 11px; font-weight: bold; }
    .badge-info { background-color: #e0f2fe; color: #075985; padding: 3px 6px; border-radius: 4px; font-size: 11px; font-weight: bold; }
    
    .stock-chip { display: inline-block; background-color: #f8fafc; padding: 4px 8px; border-radius: 4px; font-size: 13px; margin: 2px 4px 2px 0; border: 1px solid #cbd5e1; }
    hr { margin: 12px 0; border: 0; border-top: 1px solid #e2e8f0; }
</style>
""", unsafe_allow_html=True)

st.markdown('<p style="font-size: 28px; font-weight: bold; color: #1E3A8A; margin-bottom: 0;">🇹🇷 BIST 30 & Turkse Economie Ultimate Master Scanner</p>', unsafe_allow_html=True)
st.markdown(
    "Gecombineerde **Master News Hub** met **Turkse nieuwsfeeds + Google News**, **diepe semantische ontdubbeling**, "
    "**volledige 30/30 BIST 30 Koers- & Fibonacci-Matrix met ?-uitleg**, **Kwartaalcijfers met verborgen Dubbel-Check Auditor** en **30-dagen Macro-Agenda**."
)

# ==============================================================================
# 🎛️ ZIJBALK: INSTELLINGEN
# ==============================================================================
st.sidebar.header("⚙️ Systeem & Inhouds-Filter")
st.sidebar.info("Gegarandeerde dekking van alle **30 BIST 30 hoofdfondsen** inclusief onzichtbare Dubbel-Check Auditor.")

custom_search_query = st.sidebar.text_input("🔎 Vrije Live Zoekopdracht:", value="", placeholder="Bijv. Tera, İmamoğlu, Trump...")
st.sidebar.markdown("---")

select_all_bist = st.sidebar.checkbox("Selecteer ALLE 30 BIST 30 aandelen tegelijk", value=True)
default_selection = ALL_SIDEBAR_OPTIONS if select_all_bist else [
    BIST_INDEX_OPTION, "THYAO (Turkish Airlines)", "ASELS (Aselsan)", "KCHOL (Koç Holding)",
    "AKBNK (Akbank)", "GARAN (Garanti BBVA)", "TUPRS (Tüpraş)"
]

selected_tickers = st.sidebar.multiselect("🎯 Kies BIST 30 Index en/of aandelen:", options=ALL_SIDEBAR_OPTIONS, default=default_selection)
max_days_slider = st.sidebar.slider("Nieuws ouderdom (dagen):", min_value=1, max_value=5, value=3)
include_direct_newspaper_rss = st.sidebar.checkbox("⚡ Inclusief rechtstreekse Turkse kranten-feeds", value=True)

dedup_strictness = st.sidebar.radio("🧠 Inhoudelijke Ontdubbeling:", ["Slim (1 kaart per uniek verhaal)", "Maximaal (Groepeer per thema)"], index=0)
sort_mode = st.sidebar.radio("Sorteervolgorde in Master Hub:", ["Op Prioriteit (Nieuwste eerst)", "Puur op Datum"], index=0)

# ==============================================================================
# 🖥️ HOOFDPROGRAMMA & INTERFACE
# ==============================================================================
st.markdown("### 📊 Marktoverzicht (BIST 30, Valuta & Edelmetalen)")
market_data = get_live_market_snapshot()
m_items = [(k, v) for k, v in market_data.items() if v.get("price") is not None]
for row_slice in [m_items[:5], m_items[5:10]]:
    if row_slice:
        cols = st.columns(len(row_slice))
        for i, (name, info) in enumerate(row_slice):
            cols[i].metric(name, f"{info['price']:,.2f}", f"{info['change']:+.2f}%")
st.markdown("---")

if "master_enriched" not in st.session_state: st.session_state.master_enriched = None
if "source_status_snapshot" not in st.session_state: st.session_state.source_status_snapshot = {}

if st.button("🚀 Start Volledige Master Analyse (Alle 30 BIST 30 Aandelen + Kwartaal-Audit)", type="primary"):
    tickers_clean = [t.split(" ")[0] for t in selected_tickers if t != BIST_INDEX_OPTION]
    all_bist_codes = [t.split(" ")[0] for t in BIST_30_STOCKS]
    
    with st.spinner("📡 Ophalen Google News, Turkse kranten, 30/30 BIST 30 koersmatrix en verborgen Kwartaal-Audit..."):
        rss_tasks = [
            ("🚨 Fondsschandaal, SPK & Operaties", '("fon soruşturması" OR "SPK" OR "manipülasyon" OR "borsa operasyon" OR "ev hapsi")', "tr", 12, max_days_slider, tickers_clean, custom_search_query),
            ("⚠️ SPK Bulletin, Brüt Takas", '("SPK bülteni" OR "işlem yasağı" OR "brüt takas" OR "tedbir")', "tr", 10, max_days_slider, tickers_clean, custom_search_query),
            ("📜 Resmi Gazete & Belastingen", '("Resmi Gazete" OR "Cumhurbaşkanı Kararı" OR "ÖTV" OR "vergi")', "tr", 10, max_days_slider, tickers_clean, custom_search_query),
            ("🏛️ Politiek & Justitie", '("görevden alındı" OR "kayyum" OR "gözaltı" OR "tutuklama" OR "ev hapsi")', "tr", 10, max_days_slider, tickers_clean, custom_search_query),
            ("🧠 Turkse Top-Economen", '("Mahfi Eğilmez" OR "Özgür Demirtaş" OR "Hakan Kara" OR "İslam Memiş")', "tr", 10, max_days_slider, tickers_clean, custom_search_query),
            ("🌐 CDS & Krediet", '("CDS primi" OR "yabancı yatırımcı" OR "Fitch" OR "Moody\'s")', "tr", 10, max_days_slider, tickers_clean, custom_search_query),
            ("🌍 Geopolitiek & Trump", '("Trump" OR "ABD" OR "yaptırım" OR "İsrail" OR "İran")', "tr", 10, max_days_slider, tickers_clean, custom_search_query),
            ("📈 BIST 30 & Macro", '("Borsa İstanbul" OR "BIST 30" OR "TCMB" OR "Mehmet Şimşek" OR "enflasyon")', "tr", 12, max_days_slider, tickers_clean, custom_search_query),
            ("🌍 Wereldnieuws & Energie (NL)", '(oorlog OR sancties OR "Midden-Oosten" OR olieprijs)', "nl", 10, max_days_slider, [], custom_search_query),
            ("🥇 Goud & Zilver (NL)", '(goudprijs OR zilverprijs OR "Fed rente" OR edelmetalen)', "nl", 10, max_days_slider, [], custom_search_query),
            ("🏛️ OFFICIEEL KAP", 'site:kap.org.tr "bildirim"', "tr", 12, max_days_slider, tickers_clean, custom_search_query),
            ("🏦 OFFICIEEL TCMB", 'site:tcmb.gov.tr (PPK OR faiz OR enflasyon)', "tr", 10, max_days_slider, tickers_clean, custom_search_query)
        ]
        if custom_search_query:
            rss_tasks.insert(0, (f"🔎 Vrije Zoekopdracht: '{custom_search_query}'", f'"{custom_search_query}"', "tr", 12, max_days_slider, tickers_clean, custom_search_query))
        if tickers_clean:
            for i in range(0, len(tickers_clean), 5):
                batch = tickers_clean[i:i+5]
                rss_tasks.append((f"🏢 Bedrijfsnieuws ({', '.join(batch)})", f"({' OR '.join(batch)}) AND (hisse OR KAP OR bilanço OR temettü)", "tr", 6, max_days_slider, batch, custom_search_query))
                
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=12) as ex:
            google_res = list(ex.map(fetch_google_rss_feed, rss_tasks))
            direct_res = []
            if include_direct_newspaper_rss:
                direct_tasks = [(label, url, max_days_slider, tickers_clean, custom_search_query) for label, url in DIRECT_TURKISH_RSS_FEEDS]
                direct_res = list(ex.map(fetch_direct_newspaper_rss, direct_tasks))
                
        raw_items = [item for sublist in google_res + direct_res for item in sublist]
        enriched = enrich_articles_with_dutch_summaries(raw_items, all_bist_codes)
        unique_items = deduplicate_by_semantic_content(enriched, max_mode=dedup_strictness.startswith("Maximaal"))
        
        if sort_mode == "Puur op Datum": unique_items.sort(key=lambda x: -x["datetime"].timestamp())
        else: unique_items.sort(key=lambda x: (x["priority_level"], -x["datetime"].timestamp()))
        
        st.session_state.master_enriched = unique_items
        st.session_state.raw_count = len(raw_items)
        st.session_state.stock_tech_map = get_bist_technical_snapshots(tuple(all_bist_codes))
        st.session_state.agenda = get_upcoming_30_day_agenda()
        from scanner_engine import SOURCE_STATUS
        st.session_state.source_status_snapshot = dict(SOURCE_STATUS)

if st.session_state.master_enriched is not None:
    data = st.session_state.master_enriched
    tech = st.session_state.stock_tech_map
    
    st.success(f"✅ Master Analyse voltooid! **{len(data)} unieke nieuwsdossiers** gebouwd en **{len(tech)} van de 30 BIST 30-aandelen** geladen.")
    
    with st.expander("🔎 Broncontrole: welke feeds werkten?", expanded=False):
        if st.session_state.source_status_snapshot:
            import pandas as pd
            st.dataframe(pd.DataFrame([{"Bron": k, "Status": v["status"], "Berichten": v["count"], "Fout": v.get("error","")} for k,v in st.session_state.source_status_snapshot.items()]), use_container_width=True, hide_index=True)
            
    tab1, tab2, tab6, tab3, tab4, tab5 = st.tabs([
        f"🌐 Agent 1: Master Hub ({len(data)})", 
        f"🕵️‍♂️ Agent 2: BIST 30 Matrix ({len(tech)}/30)", 
        "📊 Agent 6: Kwartaalcijfers & AI-Audit", 
        "💡 Agent 3: Advies", 
        "⚖️ Agent 4: Risk", 
        f"📅 Agent 5: Agenda ({len(st.session_state.agenda)})"
    ])
    
    with tab1:
        st.markdown("### 🌐 Agent 1: Master News Hub")
        
        neg_c = sum(1 for x in data if x["sentiment_type"] == "neg")
        pos_c = sum(1 for x in data if x["sentiment_type"] == "pos")
        warn_c = sum(1 for x in data if x["sentiment_type"] == "warn")
        
        if neg_c > pos_c + 2:
            st.error(f"🚨 **Live Markt Barometer (BIST 30):** Verhoogd risico ({neg_c} negatieve/justitiële dossiers tegenover {pos_c} positieve). Wees alert op koersdruk.")
        elif pos_c > neg_c:
            st.success(f"🟢 **Live Markt Barometer (BIST 30):** Constructief klimaat ({pos_c} positieve katalysatoren tegenover {neg_c} negatieve).")
        else:
            st.info(f"⚖️ **Live Markt Barometer (BIST 30):** Gemengd beeld ({pos_c} positief, {neg_c} negatief, {warn_c} macro/beleid).")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🟢 Positieve Katalysatoren", pos_c)
        c2.metric("🔴 Hoog Risico / Schandaal", neg_c)
        c3.metric("⚠️ Beleid & Macro-Impact", warn_c)
        c4.metric("🧹 Samengevoegde Duplicaten", st.session_state.raw_count - len(data))
        
        f1, f2 = st.columns([2, 2])
        prio_filter = f1.selectbox("🔍 Filter op prioriteit:", ["Alle Unieke Dossiers", "🔥 Prio 1: Schandaal & Justitie", "📈 Prio 2: Macro & BIST 30", "🏢 Prio 3: Bedrijfsnieuws (KAP)", "🌍 Prio 4: Globaal & Edelmetalen"])
        inline_filter = f2.text_input("⚡ Snel filteren:", placeholder="Typ een woord, aandeel of naam...")
        
        filtered_data = [x for x in data if prio_filter.startswith("Alle") or f"Prio {x.get('priority_level')}" in prio_filter]
        if inline_filter.strip():
            q_f = inline_filter.lower().strip()
            filtered_data = [x for x in filtered_data if q_f in x["title_nl"].lower() or q_f in x["jip"].lower() or q_f in x["impact"].lower()]
            
        export_lines = [f"# BIST 30 Master Rapport ({datetime.now().strftime('%d-%m-%Y %H:%M')})\n"]
        for idx, item in enumerate(filtered_data, 1):
            chips = ""
            for tk in sorted(item.get("_matched_tickers", set())):
                s = tech.get(tk)
                if s and s.get("price", 0) > 0:
                    chips += f"<span class='stock-chip'>📊 <strong>{tk}</strong>: ₺{s['price']:,.2f} ({s['change']:+.2f}%) | RSI: {s['rsi']} | S1: ₺{s['s1']} | R1: ₺{s['r1']} | {s['trend']}</span>"
            
            also = ""
            if item.get("extra_source_links"):
                links = " · ".join([f"<a href='{l['link']}' target='_blank'>{l['name']}</a>" for l in item["extra_source_links"][:5]])
                also = f"<div class='card-subtitle'>🧠 <em>Zelfde verhaal ook gemeld door: {links} (automatisch samengevoegd).</em></div>"
            
            html_card = (
                f"<div class='clean-card {item['card_class']}'>"
                f"<div style='margin-bottom: 8px;'>"
                f"<span class='prio-pill'>{item['priority_label']}</span> <span class='topic-pill'>{item['topic_readable']}</span> {item['badge_html']} "
                f"<span style='font-size: 13px; color: #475569; font-weight: bold; margin-left: 8px;'>#{idx} | 🕒 {item['date_str']} | Bron: {item['source']}</span>"
                f"</div>"
                f"<div class='card-title'>{item['title_nl']}</div>"
                f"<div class='card-subtitle'>Originele kop: {item['title_orig']}</div>"
                f"{also}"
                f"<div style='font-size: 13px; color: #1e3a8a; font-weight: 600; margin-bottom: 4px;'>🎯 Geraakte Sectoren: {item['sector_str']}</div>"
                f"<div style='margin-bottom: 8px;'>{chips}</div>"
                f"<hr>"
                f"<div class='card-text'><strong>📰 Inhoud / Samenvatting van het bericht:</strong> {item['jip']}</div>"
                f"<div class='card-text'><strong>📊 Economische impact, Waarom & Welke Bedrijven:</strong> {item['impact']}</div>"
                f"<div style='margin-top: 10px;'><a href='{item['link']}' target='_blank' style='font-weight: bold; color: #1d4ed8; text-decoration: none;'>🔗 Lees originele bron ({item['source']})</a></div>"
                f"</div>"
            )
            st.markdown(html_card, unsafe_allow_html=True)
            export_lines.append(f"## #{idx} [{item['priority_label']}] {item['title_nl']} ({item['date_str']})\n- Samenvatting: {item['jip']}\n- Impact: {item['impact']}\n- Bron: {item['link']}\n\n")

        if filtered_data:
            st.download_button("📥 Download Volledig Rapport (.md)", "\n".join(export_lines), file_name=f"BIST30_Dossier_{datetime.now().strftime('%Y%m%d_%H%M')}.md", mime="text/markdown")
            
    with tab2:
        st.markdown("### 🕵️‍♂️ Agent 2: Geavanceerde Technische Koers-Matrix (Alle 30 BIST 30 Aandelen)")
        st.caption("Beweeg met je muis over het **?**-icoontje naast elke kolomnaam in de tabel voor een directe uitleg, of klik hieronder op de uitlegbalk.")
        
        with st.expander("❓ Klik hier voor Jip-en-Janneke uitleg van elk technisch onderwerp in deze tabel", expanded=False):
            st.markdown(
                "- **❓ Koers (₺) & Mutatie %:** De laatst bekende beurskoers in Turkse Lira en hoeveel procent het aandeel op de laatste handelsdag is gestegen of gedaald.\n"
                "- **❓ RSI (Relative Strength Index 14):** Meet of een aandeel te hard is afgestraft of te hard is gestegen (schaal 0 tot 100). **Onder 35 = Oversold (mogelijk koopmoment / overdreven afgestraft)**. **Boven 70 = Overbought (oververhit, kans op winstnemingen)**.\n"
                "- **❓ Vol. Spurt % (Volume Spike):** Vergelijkt het handelsvolume van vandaag met het gemiddelde van de afgelopen 20 dagen. **Boven 150%** betekent dat grote partijen plotseling massaal handelen.\n"
                "- **❓ Afstand S1 %:** Laat zien hoeveel procent de huidige koers boven Steun S1 ligt. Ligt dit tussen **-2% en +2%**, dan bevindt het aandeel zich vlak bij een belangrijke vangnet-steun.\n"
                "- **❓ Steun S1 / S2 / S3 (Fibonacci Support):** Prijsniveaus waar vaak kopers klaarstaan om het aandeel op te vangen als het daalt. **S1** is de eerste steun, **S2** de stevigere steun, **S3** de uiterste bodemsteun.\n"
                "- **❓ Weerstand R1 / R2 / R3 (Fibonacci Resistance):** Prijsniveaus waar beleggers vaak winst nemen als de koers stijgt. Breekt een aandeel met hoog volume door **R1**, dan ligt de weg open naar **R2** en **R3**.\n"
                "- **❓ Trend (SMA20):** Geeft aan of de koers boven of onder de 20-daagse gemiddelde lijn ligt. Boven SMA20 = positieve kortetermijntrend."
            )

        if tech:
            import pandas as pd
            df_tech = pd.DataFrame([
                {
                    "Ticker": k,
                    "Bedrijf": v.get("name"),
                    "Koers (₺)": v.get("price"),
                    "Mutatie %": v.get("change"), 
                    "RSI": v.get("rsi"),
                    "Vol. Spurt %": v.get("vol_ratio"),
                    "Afstand S1 %": v.get("dist_s1"),
                    "Steun S1": v.get("s1"),
                    "Steun S2": v.get("s2"),
                    "Steun S3": v.get("s3"),
                    "Weerstand R1": v.get("r1"),
                    "Weerstand R2": v.get("r2"),
                    "Weerstand R3": v.get("r3"),
                    "Trend": v.get("trend"),
                    "30d Grafiek": v.get("history")
                } for k, v in tech.items()
            ])
            
            a2_filter = st.selectbox(
                "🎯 Filter Technische Setups:",
                [
                    f"Alle {len(df_tech)} BIST 30 Aandelen (Volledig Overzicht)", 
                    "💎 Koopzone nabij S1 (Afstand tot S1 tussen -3% en +2%)", 
                    "📉 Oversold Kansen (RSI < 35)", 
                    "🚀 Volume Spike (> 150% van 20d gemiddelde)",
                    "📈 Sterke Trend (Boven SMA20)"
                ]
            )
            
            df_filtered = df_tech.copy()
            if "Koopzone" in a2_filter:
                df_filtered = df_filtered[(df_filtered["Afstand S1 %"] >= -3.0) & (df_filtered["Afstand S1 %"] <= 2.0)]
            elif "Oversold" in a2_filter:
                df_filtered = df_filtered[df_filtered["RSI"] < 35]
            elif "Volume Spike" in a2_filter:
                df_filtered = df_filtered[df_filtered["Vol. Spurt %"] > 150]
            elif "Sterke Trend" in a2_filter:
                df_filtered = df_filtered[df_filtered["Trend"].str.contains("Boven")]
                
            st.dataframe(
                df_filtered,
                column_config={
                    "Ticker": st.column_config.TextColumn("Ticker ❓", help="Beurscode van het aandeel op Borsa İstanbul (BIST 30)."),
                    "Bedrijf": st.column_config.TextColumn("Bedrijf ❓", help="Officiële naam van het BIST 30 hoofdfonds."),
                    "Koers (₺)": st.column_config.NumberColumn("Koers (₺) ❓", format="₺%.2f", help="Laatste bekende koers in Turkse Lira."),
                    "Mutatie %": st.column_config.NumberColumn("Mutatie % ❓", format="%+.2f%%", help="Procentuele verandering op de laatste handelsdag."),
                    "RSI": st.column_config.NumberColumn("RSI (14) ❓", format="%.1f", help="Relative Strength Index: <35 is goedkoop/oversold, >70 is duur/overbought."),
                    "Vol. Spurt %": st.column_config.NumberColumn("Vol. Spurt % ❓", format="%.0f%%", help="Handelsvolume vergeleken met het 20-daags gemiddelde (100% = normaal, >150% = opvallende activiteit)."),
                    "Afstand S1 %": st.column_config.NumberColumn("Afstand S1 % ❓", format="%+.2f%%", help="Hoeveel procent de koers verwijderd is van eerste steunlijn S1."),
                    "Steun S1": st.column_config.NumberColumn("Steun S1 ❓", format="₺%.2f", help="Eerste Fibonacci-steun (0.382): eerste vangnet bij een dip."),
                    "Steun S2": st.column_config.NumberColumn("Steun S2 ❓", format="₺%.2f", help="Tweede Fibonacci-steun (0.618): sterke koopzone bij correcties."),
                    "Steun S3": st.column_config.NumberColumn("Steun S3 ❓", format="₺%.2f", help="Derde Fibonacci-steun (1.000): uiterste bodem van de afgelopen 20 dagen."),
                    "Weerstand R1": st.column_config.NumberColumn("Weerstand R1 ❓", format="₺%.2f", help="Eerste Fibonacci-weerstand (0.382): eerste koersdoel voor winstneming."),
                    "Weerstand R2": st.column_config.NumberColumn("Weerstand R2 ❓", format="₺%.2f", help="Tweede Fibonacci-weerstand (0.618): belangrijk uitbraakdoel."),
                    "Weerstand R3": st.column_config.NumberColumn("Weerstand R3 ❓", format="₺%.2f", help="Derde Fibonacci-weerstand (1.000): bovenkant van het 20-daags kanaal."),
                    "Trend": st.column_config.TextColumn("Trend ❓", help="Geeft aan of het aandeel boven of onder het 20-daags gemiddelde (SMA20) noteert."),
                    "30d Grafiek": st.column_config.LineChartColumn("30d Grafiek ❓", width="medium", help="Visuele koersontwikkeling van de afgelopen 30 handelsdagen.")
                },
                use_container_width=True,
                hide_index=True
            )

    with tab6:
        st.markdown("### 📊 Agent 6: Kwartaalcijfers, Verwachte Datums & Onzichtbare Dubbel-Check Auditor")
        st.markdown(
            "Dit overzicht toont per BIST 30-aandeel **welke kwartaalcijfers al bekend zijn**, **wanneer de eerstvolgende kwartaalcijfers op KAP worden verwacht**, "
            "en het **gecontroleerde eindoordeel** (waarbij een onzichtbare achtergrond-agent de cijfers heeft gecontroleerd op winstkwaliteit, marges en trend)."
        )
        if tech:
            import pandas as pd
            df_q = pd.DataFrame([
                {
                    "Ticker": k,
                    "Bedrijf": v.get("name"),
                    "Sector": v.get("sector"),
                    "Bekend Kwartaal": v.get("q_known"),
                    "Verwacht Kwartaal (KAP)": v.get("q_expected"),
                    "Laatste Omzet": v.get("q_rev"),
                    "Laatste Nettowinst": v.get("q_net"),
                    "Oordeel (Na Dubbel-Check)": v.get("audit_verdict"),
                    "Grondige Onderbouwing": v.get("audit_reason")
                } for k, v in tech.items()
            ])
            st.dataframe(
                df_q,
                column_config={
                    "Bekend Kwartaal": st.column_config.TextColumn("Bekend Kwartaal ❓", help="Het laatst gepubliceerde kwartaalrapport dat in de financiële database staat."),
                    "Verwacht Kwartaal (KAP)": st.column_config.TextColumn("Verwacht Kwartaal (KAP) ❓", help="Officiële uiterste KAP-deadline voor de aankomende kwartaalcijfers (09-11 voor niet-geconsolideerd, 20-11 voor geconsolideerd)."),
                    "Laatste Omzet": st.column_config.TextColumn("Laatste Omzet ❓", help="Totale kwartaalomzet uit het laatst bekende kwartaalbericht."),
                    "Laatste Nettowinst": st.column_config.TextColumn("Laatste Nettowinst ❓", help="Nettowinst (or verlies) onderaan de streep in het laatst bekende kwartaal."),
                    "Oordeel (Na Dubbel-Check)": st.column_config.TextColumn("Oordeel ❓", width="medium", help="Eindoordeel nadat de onzichtbare controle-agent winstgroei, omzetkrimp en SMA20-trend tegen elkaar heeft afgewogen."),
                    "Grondige Onderbouwing": st.column_config.TextColumn("Grondige Onderbouwing ❓ (Dubbelklik of schuif 👉)", width="large", help="Dubbelklik op een vakje of gebruik het schuifvenster hieronder om de volledige zin te lezen.")
                },
                use_container_width=True,
                hide_index=True
            )

            st.markdown("#### ↔️ Volledige Onderbouwing per Aandeel (Schuif opzij om de hele zin te lezen)")
            scroll_rows = ""
            for k, v in tech.items():
                scroll_rows += (
                    f"<div style='background:#f8fafc; border:1px solid #cbd5e1; border-left:4px solid #1e3a8a; "
                    f"border-radius:6px; padding:10px 12px; margin-bottom:8px; overflow-x:auto; white-space:nowrap; font-size:14px; color:#0f172a;'>"
                    f"<strong>{k} ({v.get('name')})</strong> — {v.get('audit_verdict')} &nbsp;|&nbsp; "
                    f"<span>{v.get('audit_reason')}</span>"
                    f"</div>"
                )
            st.markdown(scroll_rows, unsafe_allow_html=True)

    with tab3:
        st.markdown(
            "### 💡 Agent 3: Concreet Beleggingsadvies\n"
            "- **Stap 1 (Nieuws-Check in Agent 1):** Controleer of er geen Prio-1 justitie- of SPK-schandalen spelen rond je aandeel.\n"
            "- **Stap 2 (Technisch Instapmoment in Agent 2):** Zoek aandelen met een **RSI tussen 35 en 55** die dicht bij **Steun S1** noteren.\n"
            "- **Stap 3 (Fundamentele Kwaliteit in Agent 6):** Kies bij voorkeur aandelen met het label **🟢 Positief (Gezonde Winst- & Omzetgroei)** die door de dubbel-check zijn gekomen."
        )
    with tab4:
        st.markdown(
            f"### ⚖️ Agent 4: Risico-Audit\n"
            f"- **Actieve Prio-1 Risicodossiers:** `{sum(1 for x in data if x['priority_level'] == 1)}` dossiers gevonden.\n"
            f"- **Kwartaalcijfers-risico:** Houd rekening met extra volatiliteit rond **9 november 2026** (niet-geconsolideerde KAP-deadline) en **20 november 2026** (geconsolideerde holdings & banken)."
        )
    
    with tab5:
        st.markdown("### 📅 Agent 5: Komende 30-Dagen Macro & Kwartaalcijfers Agenda")
        for ev in st.session_state.agenda:
            dl = (ev["date"] - datetime.now(timezone.utc).date()).days
            html_agenda = (
                f"<div class='clean-card news-card'>"
                f"<div style='margin-bottom: 6px;'><span class='topic-pill'>{'Vandaag!' if dl==0 else f'Over {dl} dagen'}</span></div>"
                f"<div class='card-title'>📅 {ev['time_str']} — {ev['title']}</div>"
                f"<hr>"
                f"<div class='card-text'><strong>🗣️ Wat gaat er gebeuren:</strong> {ev['jip']}</div>"
                f"<div class='card-text'><strong>📊 Markt & BIST 30 Impact:</strong> {ev['impact']}</div>"
                f"<a href='{ev['link']}' target='_blank' style='font-size: 13px; color: #2563eb; font-weight: bold; text-decoration: none;'>🔗 Officiële kalender</a>"
                f"</div>"
            )
            st.markdown(html_agenda, unsafe_allow_html=True)
# ==============================================================================
# 🖥️ HOOFDBESTAND (app.py) - Streamlit User Interface & Command Center
# ==============================================================================

import streamlit as st
import pandas as pd
from datetime import datetime, timezone

# Importeer alle logica uit onze motor
from scanner_engine import (
    BIST_INDEX_OPTION, BIST_30_STOCKS, ALL_SIDEBAR_OPTIONS, 
    get_live_market_snapshot, get_bist_technical_snapshots, 
    get_upcoming_30_day_agenda, fetch_google_rss_feed, 
    fetch_direct_newspaper_rss, DIRECT_TURKISH_RSS_FEEDS,
    enrich_articles_with_dutch_summaries, deduplicate_by_semantic_content
)

# ==============================================================================
# ⚙️ PAGINA CONFIGURATIE & SCHONE CSS
# ==============================================================================
st.set_page_config(
    page_title="BIST 30 & Turkse Economie Master Scanner",
    page_icon="🇹🇷",
    layout="wide"
)

st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 1.55rem !important; white-space: nowrap !important; }
    
    /* Schone HTML Kaarten - Tekst breekt altijd netjes af */
    .clean-card {
        background-color: #ffffff; padding: 18px; border-radius: 8px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05); margin-bottom: 16px;
        word-wrap: break-word; overflow-wrap: break-word; white-space: normal;
        border-left: 5px solid #cbd5e1;
    }
    .clean-card.scandal-card { border-left-color: #ef4444; background-color: #fffafa; }
    .clean-card.positive-card { border-left-color: #10b981; background-color: #f7fee7; }
    .clean-card.news-card { border-left-color: #3b82f6; background-color: #ffffff; }
    
    .card-title { margin-top: 0; color: #0f172a; font-size: 18px; font-weight: 700; margin-bottom: 4px; line-height: 1.35; }
    .card-subtitle { font-size: 12px; color: #64748b; margin-bottom: 8px; }
    .card-text { font-size: 15px; color: #334155; line-height: 1.55; margin-bottom: 8px; }
    .card-text strong { color: #0f172a; }
    
    .prio-pill { background-color: #1e293b; color: white; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; }
    .topic-pill { background-color: #e2e8f0; color: #334155; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; }
    
    .badge-neg { background-color: #fee2e2; color: #991b1b; padding: 3px 6px; border-radius: 4px; font-size: 11px; font-weight: bold; }
    .badge-pos { background-color: #dcfce7; color: #166534; padding: 3px 6px; border-radius: 4px; font-size: 11px; font-weight: bold; }
    .badge-warn { background-color: #fef9c3; color: #854d0e; padding: 3px 6px; border-radius: 4px; font-size: 11px; font-weight: bold; }
    .badge-info { background-color: #e0f2fe; color: #075985; padding: 3px 6px; border-radius: 4px; font-size: 11px; font-weight: bold; }
    
    .stock-chip { display: inline-block; background-color: #f8fafc; padding: 4px 8px; border-radius: 4px; font-size: 13px; margin: 2px 4px 2px 0; border: 1px solid #cbd5e1; }
    hr { margin: 12px 0; border: 0; border-top: 1px solid #e2e8f0; }
</style>
""", unsafe_allow_html=True)

st.markdown('<p style="font-size: 28px; font-weight: bold; color: #1E3A8A; margin-bottom: 0;">🇹🇷 BIST 30 & Turkse Economie Ultimate Master Scanner</p>', unsafe_allow_html=True)
st.markdown(
    "Gecombineerde **Master News Hub** met **Turkse nieuwsfeeds + Google News**, **diepe semantische ontdubbeling**, "
    "**volledige 30/30 BIST 30 Koers- & Fibonacci-Matrix met ?-uitleg**, **Kwartaalcijfers met verborgen Dubbel-Check Auditor** en **30-dagen Macro-Agenda**."
)

# ==============================================================================
# 🎛️ ZIJBALK: INSTELLINGEN
# ==============================================================================
st.sidebar.header("⚙️ Systeem & Inhouds-Filter")
st.sidebar.info("Gegarandeerde dekking van alle **30 BIST 30 hoofdfondsen** inclusief onzichtbare Dubbel-Check Auditor.")

custom_search_query = st.sidebar.text_input("🔎 Vrije Live Zoekopdracht:", value="", placeholder="Bijv. Tera, İmamoğlu, Trump...")
st.sidebar.markdown("---")

select_all_bist = st.sidebar.checkbox("Selecteer ALLE 30 BIST 30 aandelen tegelijk", value=True)
default_selection = ALL_SIDEBAR_OPTIONS if select_all_bist else [
    BIST_INDEX_OPTION, "THYAO (Turkish Airlines)", "ASELS (Aselsan)", "KCHOL (Koç Holding)",
    "AKBNK (Akbank)", "GARAN (Garanti BBVA)", "TUPRS (Tüpraş)"
]

selected_tickers = st.sidebar.multiselect("🎯 Kies BIST 30 Index en/of aandelen:", options=ALL_SIDEBAR_OPTIONS, default=default_selection)
max_days_slider = st.sidebar.slider("Nieuws ouderdom (dagen):", min_value=1, max_value=5, value=3)
include_direct_newspaper_rss = st.sidebar.checkbox("⚡ Inclusief rechtstreekse Turkse kranten-feeds", value=True)

dedup_strictness = st.sidebar.radio("🧠 Inhoudelijke Ontdubbeling:", ["Slim (1 kaart per uniek verhaal)", "Maximaal (Groepeer per thema)"], index=0)
sort_mode = st.sidebar.radio("Sorteervolgorde in Master Hub:", ["Op Prioriteit (Nieuwste eerst)", "Puur op Datum"], index=0)

# ==============================================================================
# 🖥️ HOOFDPROGRAMMA & INTERFACE
# ==============================================================================
st.markdown("### 📊 Marktoverzicht (BIST 30, Valuta & Edelmetalen)")
market_data = get_live_market_snapshot()
m_items = [(k, v) for k, v in market_data.items() if v.get("price") is not None]
for row_slice in [m_items[:5], m_items[5:10]]:
    if row_slice:
        cols = st.columns(len(row_slice))
        for i, (name, info) in enumerate(row_slice):
            cols[i].metric(name, f"{info['price']:,.2f}", f"{info['change']:+.2f}%")
st.markdown("---")

if "master_enriched" not in st.session_state: st.session_state.master_enriched = None
if "source_status_snapshot" not in st.session_state: st.session_state.source_status_snapshot = {}

if st.button("🚀 Start Volledige Master Analyse (Alle 30 BIST 30 Aandelen + Kwartaal-Audit)", type="primary"):
    tickers_clean = [t.split(" ")[0] for t in selected_tickers if t != BIST_INDEX_OPTION]
    all_bist_codes = [t.split(" ")[0] for t in BIST_30_STOCKS]
    
    with st.spinner("📡 Ophalen Google News, Turkse kranten, 30/30 BIST 30 koersmatrix en verborgen Kwartaal-Audit..."):
        rss_tasks = [
            ("🚨 Fondsschandaal, SPK & Operaties", '("fon soruşturması" OR "SPK" OR "manipülasyon" OR "borsa operasyon" OR "ev hapsi")', "tr", 12, max_days_slider, tickers_clean, custom_search_query),
            ("⚠️ SPK Bulletin, Brüt Takas", '("SPK bülteni" OR "işlem yasağı" OR "brüt takas" OR "tedbir")', "tr", 10, max_days_slider, tickers_clean, custom_search_query),
            ("📜 Resmi Gazete & Belastingen", '("Resmi Gazete" OR "Cumhurbaşkanı Kararı" OR "ÖTV" OR "vergi")', "tr", 10, max_days_slider, tickers_clean, custom_search_query),
            ("🏛️ Politiek & Justitie", '("görevden alındı" OR "kayyum" OR "gözaltı" OR "tutuklama" OR "ev hapsi")', "tr", 10, max_days_slider, tickers_clean, custom_search_query),
            ("🧠 Turkse Top-Economen", '("Mahfi Eğilmez" OR "Özgür Demirtaş" OR "Hakan Kara" OR "İslam Memiş")', "tr", 10, max_days_slider, tickers_clean, custom_search_query),
            ("🌐 CDS & Krediet", '("CDS primi" OR "yabancı yatırımcı" OR "Fitch" OR "Moody\'s")', "tr", 10, max_days_slider, tickers_clean, custom_search_query),
            ("🌍 Geopolitiek & Trump", '("Trump" OR "ABD" OR "yaptırım" OR "İsrail" OR "İran")', "tr", 10, max_days_slider, tickers_clean, custom_search_query),
            ("📈 BIST 30 & Macro", '("Borsa İstanbul" OR "BIST 30" OR "TCMB" OR "Mehmet Şimşek" OR "enflasyon")', "tr", 12, max_days_slider, tickers_clean, custom_search_query),
            ("🌍 Wereldnieuws & Energie (NL)", '(oorlog OR sancties OR "Midden-Oosten" OR olieprijs)', "nl", 10, max_days_slider, [], custom_search_query),
            ("🥇 Goud & Zilver (NL)", '(goudprijs OR zilverprijs OR "Fed rente" OR edelmetalen)', "nl", 10, max_days_slider, [], custom_search_query),
            ("🏛️ OFFICIEEL KAP", 'site:kap.org.tr "bildirim"', "tr", 12, max_days_slider, tickers_clean, custom_search_query),
            ("🏦 OFFICIEEL TCMB", 'site:tcmb.gov.tr (PPK OR faiz OR enflasyon)', "tr", 10, max_days_slider, tickers_clean, custom_search_query)
        ]
        if custom_search_query:
            rss_tasks.insert(0, (f"🔎 Vrije Zoekopdracht: '{custom_search_query}'", f'"{custom_search_query}"', "tr", 12, max_days_slider, tickers_clean, custom_search_query))
        if tickers_clean:
            for i in range(0, len(tickers_clean), 5):
                batch = tickers_clean[i:i+5]
                rss_tasks.append((f"🏢 Bedrijfsnieuws ({', '.join(batch)})", f"({' OR '.join(batch)}) AND (hisse OR KAP OR bilanço OR temettü)", "tr", 6, max_days_slider, batch, custom_search_query))
                
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=12) as ex:
            google_res = list(ex.map(fetch_google_rss_feed, rss_tasks))
            direct_res = []
            if include_direct_newspaper_rss:
                direct_tasks = [(label, url, max_days_slider, tickers_clean, custom_search_query) for label, url in DIRECT_TURKISH_RSS_FEEDS]
                direct_res = list(ex.map(fetch_direct_newspaper_rss, direct_tasks))
                
        raw_items = [item for sublist in google_res + direct_res for item in sublist]
        enriched = enrich_articles_with_dutch_summaries(raw_items, all_bist_codes)
        unique_items = deduplicate_by_semantic_content(enriched, max_mode=dedup_strictness.startswith("Maximaal"))
        
        if sort_mode == "Puur op Datum": unique_items.sort(key=lambda x: -x["datetime"].timestamp())
        else: unique_items.sort(key=lambda x: (x["priority_level"], -x["datetime"].timestamp()))
        
        st.session_state.master_enriched = unique_items
        st.session_state.raw_count = len(raw_items)
        st.session_state.stock_tech_map = get_bist_technical_snapshots(tuple(all_bist_codes))
        st.session_state.agenda = get_upcoming_30_day_agenda()
        from scanner_engine import SOURCE_STATUS
        st.session_state.source_status_snapshot = dict(SOURCE_STATUS)

if st.session_state.master_enriched is not None:
    data = st.session_state.master_enriched
    tech = st.session_state.stock_tech_map
    
    st.success(f"✅ Master Analyse voltooid! **{len(data)} unieke nieuwsdossiers** gebouwd en **{len(tech)} van de 30 BIST 30-aandelen** geladen.")
    
    with st.expander("🔎 Broncontrole: welke feeds werkten?", expanded=False):
        if st.session_state.source_status_snapshot:
            import pandas as pd
            st.dataframe(pd.DataFrame([{"Bron": k, "Status": v["status"], "Berichten": v["count"], "Fout": v.get("error","")} for k,v in st.session_state.source_status_snapshot.items()]), use_container_width=True, hide_index=True)
            
    tab1, tab2, tab6, tab3, tab4, tab5 = st.tabs([
        f"🌐 Agent 1: Master Hub ({len(data)})", 
        f"🕵️‍♂️ Agent 2: BIST 30 Matrix ({len(tech)}/30)", 
        "📊 Agent 6: Kwartaalcijfers & AI-Audit", 
        "💡 Agent 3: Advies", 
        "⚖️ Agent 4: Risk", 
        f"📅 Agent 5: Agenda ({len(st.session_state.agenda)})"
    ])
    
    with tab1:
        st.markdown("### 🌐 Agent 1: Master News Hub")
        
        neg_c = sum(1 for x in data if x["sentiment_type"] == "neg")
        pos_c = sum(1 for x in data if x["sentiment_type"] == "pos")
        warn_c = sum(1 for x in data if x["sentiment_type"] == "warn")
        
        if neg_c > pos_c + 2:
            st.error(f"🚨 **Live Markt Barometer (BIST 30):** Verhoogd risico ({neg_c} negatieve/justitiële dossiers tegenover {pos_c} positieve). Wees alert op koersdruk.")
        elif pos_c > neg_c:
            st.success(f"🟢 **Live Markt Barometer (BIST 30):** Constructief klimaat ({pos_c} positieve katalysatoren tegenover {neg_c} negatieve).")
        else:
            st.info(f"⚖️ **Live Markt Barometer (BIST 30):** Gemengd beeld ({pos_c} positief, {neg_c} negatief, {warn_c} macro/beleid).")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🟢 Positieve Katalysatoren", pos_c)
        c2.metric("🔴 Hoog Risico / Schandaal", neg_c)
        c3.metric("⚠️ Beleid & Macro-Impact", warn_c)
        c4.metric("🧹 Samengevoegde Duplicaten", st.session_state.raw_count - len(data))
        
        f1, f2 = st.columns([2, 2])
        prio_filter = f1.selectbox("🔍 Filter op prioriteit:", ["Alle Unieke Dossiers", "🔥 Prio 1: Schandaal & Justitie", "📈 Prio 2: Macro & BIST 30", "🏢 Prio 3: Bedrijfsnieuws (KAP)", "🌍 Prio 4: Globaal & Edelmetalen"])
        inline_filter = f2.text_input("⚡ Snel filteren:", placeholder="Typ een woord, aandeel of naam...")
        
        filtered_data = [x for x in data if prio_filter.startswith("Alle") or f"Prio {x.get('priority_level')}" in prio_filter]
        if inline_filter.strip():
            q_f = inline_filter.lower().strip()
            filtered_data = [x for x in filtered_data if q_f in x["title_nl"].lower() or q_f in x["jip"].lower() or q_f in x["impact"].lower()]
            
        export_lines = [f"# BIST 30 Master Rapport ({datetime.now().strftime('%d-%m-%Y %H:%M')})\n"]
        for idx, item in enumerate(filtered_data, 1):
            chips = ""
            for tk in sorted(item.get("_matched_tickers", set())):
                s = tech.get(tk)
                if s and s.get("price", 0) > 0:
                    chips += f"<span class='stock-chip'>📊 <strong>{tk}</strong>: ₺{s['price']:,.2f} ({s['change']:+.2f}%) | RSI: {s['rsi']} | S1: ₺{s['s1']} | R1: ₺{s['r1']} | {s['trend']}</span>"
            
            also = ""
            if item.get("extra_source_links"):
                links = " · ".join([f"<a href='{l['link']}' target='_blank'>{l['name']}</a>" for l in item["extra_source_links"][:5]])
                also = f"<div class='card-subtitle'>🧠 <em>Zelfde verhaal ook gemeld door: {links} (automatisch samengevoegd).</em></div>"
            
            html_card = (
                f"<div class='clean-card {item['card_class']}'>"
                f"<div style='margin-bottom: 8px;'>"
                f"<span class='prio-pill'>{item['priority_label']}</span> <span class='topic-pill'>{item['topic_readable']}</span> {item['badge_html']} "
                f"<span style='font-size: 13px; color: #475569; font-weight: bold; margin-left: 8px;'>#{idx} | 🕒 {item['date_str']} | Bron: {item['source']}</span>"
                f"</div>"
                f"<div class='card-title'>{item['title_nl']}</div>"
                f"<div class='card-subtitle'>Originele kop: {item['title_orig']}</div>"
                f"{also}"
                f"<div style='font-size: 13px; color: #1e3a8a; font-weight: 600; margin-bottom: 4px;'>🎯 Geraakte Sectoren: {item['sector_str']}</div>"
                f"<div style='margin-bottom: 8px;'>{chips}</div>"
                f"<hr>"
                f"<div class='card-text'><strong>📰 Inhoud / Samenvatting van het bericht:</strong> {item['jip']}</div>"
                f"<div class='card-text'><strong>📊 Economische impact, Waarom & Welke Bedrijven:</strong> {item['impact']}</div>"
                f"<div style='margin-top: 10px;'><a href='{item['link']}' target='_blank' style='font-weight: bold; color: #1d4ed8; text-decoration: none;'>🔗 Lees originele bron ({item['source']})</a></div>"
                f"</div>"
            )
            st.markdown(html_card, unsafe_allow_html=True)
            export_lines.append(f"## #{idx} [{item['priority_label']}] {item['title_nl']} ({item['date_str']})\n- Samenvatting: {item['jip']}\n- Impact: {item['impact']}\n- Bron: {item['link']}\n\n")

        if filtered_data:
            st.download_button("📥 Download Volledig Rapport (.md)", "\n".join(export_lines), file_name=f"BIST30_Dossier_{datetime.now().strftime('%Y%m%d_%H%M')}.md", mime="text/markdown")
            
    with tab2:
        st.markdown("### 🕵️‍♂️ Agent 2: Geavanceerde Technische Koers-Matrix (Alle 30 BIST 30 Aandelen)")
        st.caption("Beweeg met je muis over het **?**-icoontje naast elke kolomnaam in de tabel voor een directe uitleg, of klik hieronder op de uitlegbalk.")
        
        with st.expander("❓ Klik hier voor Jip-en-Janneke uitleg van elk technisch onderwerp in deze tabel", expanded=False):
            st.markdown(
                "- **❓ Koers (₺) & Mutatie %:** De laatst bekende beurskoers in Turkse Lira en hoeveel procent het aandeel op de laatste handelsdag is gestegen of gedaald.\n"
                "- **❓ RSI (Relative Strength Index 14):** Meet of een aandeel te hard is afgestraft of te hard is gestegen (schaal 0 tot 100). **Onder 35 = Oversold (mogelijk koopmoment / overdreven afgestraft)**. **Boven 70 = Overbought (oververhit, kans op winstnemingen)**.\n"
                "- **❓ Vol. Spurt % (Volume Spike):** Vergelijkt het handelsvolume van vandaag met het gemiddelde van de afgelopen 20 dagen. **Boven 150%** betekent dat grote partijen plotseling massaal handelen.\n"
                "- **❓ Afstand S1 %:** Laat zien hoeveel procent de huidige koers boven Steun S1 ligt. Ligt dit tussen **-2% en +2%**, dan bevindt het aandeel zich vlak bij een belangrijke vangnet-steun.\n"
                "- **❓ Steun S1 / S2 / S3 (Fibonacci Support):** Prijsniveaus waar vaak kopers klaarstaan om het aandeel op te vangen als het daalt. **S1** is de eerste steun, **S2** de stevigere steun, **S3** de uiterste bodemsteun.\n"
                "- **❓ Weerstand R1 / R2 / R3 (Fibonacci Resistance):** Prijsniveaus waar beleggers vaak winst nemen als de koers stijgt. Breekt een aandeel met hoog volume door **R1**, dan ligt de weg open naar **R2** en **R3**.\n"
                "- **❓ Trend (SMA20):** Geeft aan of de koers boven of onder de 20-daagse gemiddelde lijn ligt. Boven SMA20 = positieve kortetermijntrend."
            )

        if tech:
            import pandas as pd
            df_tech = pd.DataFrame([
                {
                    "Ticker": k,
                    "Bedrijf": v.get("name"),
                    "Koers (₺)": v.get("price"),
                    "Mutatie %": v.get("change"), 
                    "RSI": v.get("rsi"),
                    "Vol. Spurt %": v.get("vol_ratio"),
                    "Afstand S1 %": v.get("dist_s1"),
                    "Steun S1": v.get("s1"),
                    "Steun S2": v.get("s2"),
                    "Steun S3": v.get("s3"),
                    "Weerstand R1": v.get("r1"),
                    "Weerstand R2": v.get("r2"),
                    "Weerstand R3": v.get("r3"),
                    "Trend": v.get("trend"),
                    "30d Grafiek": v.get("history")
                } for k, v in tech.items()
            ])
            
            a2_filter = st.selectbox(
                "🎯 Filter Technische Setups:",
                [
                    f"Alle {len(df_tech)} BIST 30 Aandelen (Volledig Overzicht)", 
                    "💎 Koopzone nabij S1 (Afstand tot S1 tussen -3% en +2%)", 
                    "📉 Oversold Kansen (RSI < 35)", 
                    "🚀 Volume Spike (> 150% van 20d gemiddelde)",
                    "📈 Sterke Trend (Boven SMA20)"
                ]
            )
            
            df_filtered = df_tech.copy()
            if "Koopzone" in a2_filter:
                df_filtered = df_filtered[(df_filtered["Afstand S1 %"] >= -3.0) & (df_filtered["Afstand S1 %"] <= 2.0)]
            elif "Oversold" in a2_filter:
                df_filtered = df_filtered[df_filtered["RSI"] < 35]
            elif "Volume Spike" in a2_filter:
                df_filtered = df_filtered[df_filtered["Vol. Spurt %"] > 150]
            elif "Sterke Trend" in a2_filter:
                df_filtered = df_filtered[df_filtered["Trend"].str.contains("Boven")]
                
            st.dataframe(
                df_filtered,
                column_config={
                    "Ticker": st.column_config.TextColumn("Ticker ❓", help="Beurscode van het aandeel op Borsa İstanbul (BIST 30)."),
                    "Bedrijf": st.column_config.TextColumn("Bedrijf ❓", help="Officiële naam van het BIST 30 hoofdfonds."),
                    "Koers (₺)": st.column_config.NumberColumn("Koers (₺) ❓", format="₺%.2f", help="Laatste bekende koers in Turkse Lira."),
                    "Mutatie %": st.column_config.NumberColumn("Mutatie % ❓", format="%+.2f%%", help="Procentuele verandering op de laatste handelsdag."),
                    "RSI": st.column_config.NumberColumn("RSI (14) ❓", format="%.1f", help="Relative Strength Index: <35 is goedkoop/oversold, >70 is duur/overbought."),
                    "Vol. Spurt %": st.column_config.NumberColumn("Vol. Spurt % ❓", format="%.0f%%", help="Handelsvolume vergeleken met het 20-daags gemiddelde (100% = normaal, >150% = opvallende activiteit)."),
                    "Afstand S1 %": st.column_config.NumberColumn("Afstand S1 % ❓", format="%+.2f%%", help="Hoeveel procent de koers verwijderd is van eerste steunlijn S1."),
                    "Steun S1": st.column_config.NumberColumn("Steun S1 ❓", format="₺%.2f", help="Eerste Fibonacci-steun (0.382): eerste vangnet bij een dip."),
                    "Steun S2": st.column_config.NumberColumn("Steun S2 ❓", format="₺%.2f", help="Tweede Fibonacci-steun (0.618): sterke koopzone bij correcties."),
                    "Steun S3": st.column_config.NumberColumn("Steun S3 ❓", format="₺%.2f", help="Derde Fibonacci-steun (1.000): uiterste bodem van de afgelopen 20 dagen."),
                    "Weerstand R1": st.column_config.NumberColumn("Weerstand R1 ❓", format="₺%.2f", help="Eerste Fibonacci-weerstand (0.382): eerste koersdoel voor winstneming."),
                    "Weerstand R2": st.column_config.NumberColumn("Weerstand R2 ❓", format="₺%.2f", help="Tweede Fibonacci-weerstand (0.618): belangrijk uitbraakdoel."),
                    "Weerstand R3": st.column_config.NumberColumn("Weerstand R3 ❓", format="₺%.2f", help="Derde Fibonacci-weerstand (1.000): bovenkant van het 20-daags kanaal."),
                    "Trend": st.column_config.TextColumn("Trend ❓", help="Geeft aan of het aandeel boven of onder het 20-daags gemiddelde (SMA20) noteert."),
                    "30d Grafiek": st.column_config.LineChartColumn("30d Grafiek ❓", width="medium", help="Visuele koersontwikkeling van de afgelopen 30 handelsdagen.")
                },
                use_container_width=True,
                hide_index=True
            )

    with tab6:
        st.markdown("### 📊 Agent 6: Kwartaalcijfers, Verwachte Datums & Onzichtbare Dubbel-Check Auditor")
        st.markdown(
            "Dit overzicht toont per BIST 30-aandeel **welke kwartaalcijfers al bekend zijn**, **wanneer de eerstvolgende kwartaalcijfers op KAP worden verwacht**, "
            "en het **gecontroleerde eindoordeel** (waarbij een onzichtbare achtergrond-agent de cijfers heeft gecontroleerd op winstkwaliteit, marges en trend)."
        )
        if tech:
            import pandas as pd
            df_q = pd.DataFrame([
                {
                    "Ticker": k,
                    "Bedrijf": v.get("name"),
                    "Sector": v.get("sector"),
                    "Bekend Kwartaal": v.get("q_known"),
                    "Verwacht Kwartaal (KAP)": v.get("q_expected"),
                    "Laatste Omzet": v.get("q_rev"),
                    "Laatste Nettowinst": v.get("q_net"),
                    "Oordeel (Na Dubbel-Check)": v.get("audit_verdict"),
                    "Grondige Onderbouwing": v.get("audit_reason")
                } for k, v in tech.items()
            ])
            st.dataframe(
                df_q,
                column_config={
                    "Bekend Kwartaal": st.column_config.TextColumn("Bekend Kwartaal ❓", help="Het laatst gepubliceerde kwartaalrapport dat in de financiële database staat."),
                    "Verwacht Kwartaal (KAP)": st.column_config.TextColumn("Verwacht Kwartaal (KAP) ❓", help="Officiële uiterste KAP-deadline voor de aankomende kwartaalcijfers (09-11 voor niet-geconsolideerd, 20-11 voor geconsolideerd)."),
                    "Laatste Omzet": st.column_config.TextColumn("Laatste Omzet ❓", help="Totale kwartaalomzet uit het laatst bekende kwartaalbericht."),
                    "Laatste Nettowinst": st.column_config.TextColumn("Laatste Nettowinst ❓", help="Nettowinst (of verlies) onderaan de streep in het laatst bekende kwartaal."),
                    "Oordeel (Na Dubbel-Check)": st.column_config.TextColumn("Oordeel ❓", width="medium", help="Eindoordeel nadat de onzichtbare controle-agent winstgroei, omzetkrimp en SMA20-trend tegen elkaar heeft afgewogen."),
                    "Grondige Onderbouwing": st.column_config.TextColumn("Grondige Onderbouwing ❓ (Dubbelklik of schuif 👉)", width="large", help="Dubbelklik op een vakje of gebruik het schuifvenster hieronder om de volledige zin te lezen.")
                },
                use_container_width=True,
                hide_index=True
            )

            st.markdown("#### ↔️ Volledige Onderbouwing per Aandeel (Schuif opzij om de hele zin te lezen)")
            scroll_rows = ""
            for k, v in tech.items():
                scroll_rows += (
                    f"<div style='background:#f8fafc; border:1px solid #cbd5e1; border-left:4px solid #1e3a8a; "
                    f"border-radius:6px; padding:10px 12px; margin-bottom:8px; overflow-x:auto; white-space:nowrap; font-size:14px; color:#0f172a;'>"
                    f"<strong>{k} ({v.get('name')})</strong> — {v.get('audit_verdict')} &nbsp;|&nbsp; "
                    f"<span>{v.get('audit_reason')}</span>"
                    f"</div>"
                )
            st.markdown(scroll_rows, unsafe_allow_html=True)

    with tab3:
        st.markdown(
            "### 💡 Agent 3: Concreet Beleggingsadvies\n"
            "- **Stap 1 (Nieuws-Check in Agent 1):** Controleer of er geen Prio-1 justitie- of SPK-schandalen spelen rond je aandeel.\n"
            "- **Stap 2 (Technisch Instapmoment in Agent 2):** Zoek aandelen met een **RSI tussen 35 en 55** die dicht bij **Steun S1** noteren.\n"
            "- **Stap 3 (Fundamentele Kwaliteit in Agent 6):** Kies bij voorkeur aandelen met het label **🟢 Positief (Gezonde Winst- & Omzetgroei)** die door de dubbel-check zijn gekomen."
        )
    with tab4:
        st.markdown(
            f"### ⚖️ Agent 4: Risico-Audit\n"
            f"- **Actieve Prio-1 Risicodossiers:** `{sum(1 for x in data if x['priority_level'] == 1)}` dossiers gevonden.\n"
            f"- **Kwartaalcijfers-risico:** Houd rekening met extra volatiliteit rond **9 november 2026** (niet-geconsolideerde KAP-deadline) en **20 november 2026** (geconsolideerde holdings & banken)."
        )
    
    with tab5:
        st.markdown("### 📅 Agent 5: Komende 30-Dagen Macro & Kwartaalcijfers Agenda")
        for ev in st.session_state.agenda:
            dl = (ev["date"] - datetime.now(timezone.utc).date()).days
            html_agenda = (
                f"<div class='clean-card news-card'>"
                f"<div style='margin-bottom: 6px;'><span class='topic-pill'>{'Vandaag!' if dl==0 else f'Over {dl} dagen'}</span></div>"
                f"<div class='card-title'>📅 {ev['time_str']} — {ev['title']}</div>"
                f"<hr>"
                f"<div class='card-text'><strong>🗣️ Wat gaat er gebeuren:</strong> {ev['jip']}</div>"
                f"<div class='card-text'><strong>📊 Markt & BIST 30 Impact:</strong> {ev['impact']}</div>"
                f"<a href='{ev['link']}' target='_blank' style='font-size: 13px; color: #2563eb; font-weight: bold; text-decoration: none;'>🔗 Officiële kalender</a>"
                f"</div>"
            )
            st.markdown(html_agenda, unsafe_allow_html=True)
