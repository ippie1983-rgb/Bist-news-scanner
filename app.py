import os
import re
import html
import json
import difflib
import streamlit as st
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
# ⚙️ PAGINA CONFIGURATIE & SCHONE CSS
# ==============================================================================
st.set_page_config(page_title="BIST 30 & Turkse Economie Master Scanner", page_icon="🇹🇷", layout="wide")

st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 1.6rem !important; white-space: nowrap !important; }
    
    /* Schone HTML Kaarten - NOOIT een horizontale scrollbalk */
    .clean-card {
        background-color: #ffffff; padding: 18px; border-radius: 8px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05); margin-bottom: 16px;
        word-wrap: break-word; white-space: normal; border-left: 5px solid #cbd5e1;
    }
    .clean-card.scandal-card { border-left-color: #ef4444; } /* Rood */
    .clean-card.positive-card { border-left-color: #10b981; } /* Groen */
    .clean-card.news-card { border-left-color: #3b82f6; } /* Blauw */
    
    .card-title { margin-top: 0; color: #0f172a; font-size: 18px; font-weight: 700; margin-bottom: 4px; line-height: 1.3; }
    .card-subtitle { font-size: 12px; color: #64748b; margin-bottom: 8px; }
    
    .prio-pill { background-color: #1e293b; color: white; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; }
    .topic-pill { background-color: #e2e8f0; color: #334155; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; }
    
    .badge-neg { background-color: #fee2e2; color: #991b1b; padding: 3px 6px; border-radius: 4px; font-size: 11px; font-weight: bold; }
    .badge-pos { background-color: #dcfce7; color: #166534; padding: 3px 6px; border-radius: 4px; font-size: 11px; font-weight: bold; }
    .badge-warn { background-color: #fef9c3; color: #854d0e; padding: 3px 6px; border-radius: 4px; font-size: 11px; font-weight: bold; }
    .badge-info { background-color: #e0f2fe; color: #075985; padding: 3px 6px; border-radius: 4px; font-size: 11px; font-weight: bold; }
    
    .stock-chip { display: inline-block; background-color: #f8fafc; padding: 4px 8px; border-radius: 4px; font-size: 13px; margin: 2px 4px 2px 0; border: 1px solid #e2e8f0; }
    hr { margin: 12px 0; border: 0; border-top: 1px solid #e2e8f0; }
</style>
""", unsafe_allow_html=True)

st.markdown('<p style="font-size: 28px; font-weight: bold; color: #1E3A8A; margin-bottom: 0;">🇹🇷 BIST 30 & Turkse Economie Master Scanner</p>', unsafe_allow_html=True)
st.markdown("Gecombineerde **Master News Hub** met **Turkse nieuwsfeeds + Google News**, **diepe semantische ontdubbeling**, **live sentiment barometer** en de **30-dagen Macro-Agenda**.")

# ==============================================================================
# 🗂 BIST 30 LIJST & CONFIGURATIE
# ==============================================================================
BIST_INDEX_OPTION = "📈 BIST 30 Index (Brede Markt)"

BIST_30_STOCKS = [
    "AKBNK (Akbank)", "ALARK (Alarko Holding)", "ASELS (Aselsan)", "ASTOR (Astor Enerji)", 
    "BIMAS (Bim Mağazalar)", "BRSAN (Borusan Boru)", "CCOLA (Coca-Cola İçecek)", "ENKAI (Enka İnşaat)", 
    "EREGL (Erdemir)", "FROTO (Ford Otosan)", "GARAN (Garanti BBVA)", "GUBRF (Gübre Fabrikaları)", 
    "HEKTS (Hektaş)", "ISCTR (İş Bankası C)", "KCHOL (Koç Holding)", "KONTR (Kontrolmatik)", 
    "KOZAA (Koza Anadolu Metal)", "KOZAL (Koza Altın)", "KRDMD (Kardemir D)", "ODAS (Odaş Elektrik)", 
    "OYAKC (Oyak Çimento)", "PETKM (Petkim)", "PGSUS (Pegasus)", "SAHOL (Sabancı Holding)", 
    "SASA (Sasa Polyester)", "SISE (Şişecam)", "TCELL (Turkcell)", "THYAO (Turkish Airlines)", 
    "TOASO (Tofaş Oto)", "TUPRS (Tüpraş)", "YKBNK (Yapı Kredi)"
]

ALL_SIDEBAR_OPTIONS = [BIST_INDEX_OPTION] + BIST_30_STOCKS

COMPANY_TO_TICKER_MAP = {
    "türk hava yolları": "THYAO", "turkish airlines": "THYAO", "aselsan": "ASELS", "koç holding": "KCHOL", 
    "koc holding": "KCHOL", "akbank": "AKBNK", "garanti bbva": "GARAN", "garanti bankası": "GARAN",
    "tüpraş": "TUPRS", "tupras": "TUPRS", "bim mağazalar": "BIMAS", "erdemir": "EREGL", "ereğli demir": "EREGL", 
    "şişecam": "SISE", "sisecam": "SISE", "sasa polyester": "SASA", "yapı kredi": "YKBNK", 
    "iş bankası": "ISCTR", "petkim": "PETKM", "pegasus": "PGSUS", "tofaş": "TOASO",
    "enka inşaat": "ENKAI", "kardemir": "KRDMD", "turkcell": "TCELL", "ford otosan": "FROTO", 
    "astor enerji": "ASTOR", "sabancı holding": "SAHOL", "oyak çimento": "OYAKC", "hektaş": "HEKTS", 
    "odaş": "ODAS", "kontrolmatik": "KONTR", "alarko": "ALARK", "borusan": "BRSAN", 
    "gübre fabrikaları": "GUBRF", "koza altın": "KOZAL", "koza anadolu": "KOZAA", "coca-cola içecek": "CCOLA"
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

# ==============================================================================
# 🎛️ ZIJBALK: INSTELLINGEN
# ==============================================================================
st.sidebar.header("⚙️ Systeem & Inhouds-Filter")

custom_search_query = st.sidebar.text_input("🔎 Vrije Live Zoekopdracht:", value="", placeholder="Bijv. İmamoğlu, Trump...")
st.sidebar.markdown("---")

select_all_bist = st.sidebar.checkbox("Selecteer ALLE BIST 30 aandelen tegelijk", value=False)
default_selection = ALL_SIDEBAR_OPTIONS if select_all_bist else [BIST_INDEX_OPTION, "THYAO (Turkish Airlines)", "ASELS (Aselsan)", "KCHOL (Koç Holding)", "AKBNK (Akbank)", "GARAN (Garanti BBVA)", "TUPRS (Tüpraş)"]

selected_tickers = st.sidebar.multiselect("🎯 Kies BIST 30 Index en/of aandelen:", options=ALL_SIDEBAR_OPTIONS, default=default_selection)
max_days_slider = st.sidebar.slider("Nieuws ouderdom (dagen):", min_value=1, max_value=5, value=3)
include_direct_newspaper_rss = st.sidebar.checkbox("⚡ Inclusief rechtstreekse Turkse kranten-feeds", value=True)

dedup_strictness = st.sidebar.radio("🧠 Inhoudelijke Ontdubbeling:", ["Slim (1 kaart per uniek verhaal)", "Maximaal (Groepeer per thema)"], index=0)
sort_mode = st.sidebar.radio("Sorteervolgorde in Master Hub:", ["Op Prioriteit (Nieuwste eerst)", "Puur op Datum"], index=0)

# ==============================================================================
# 🧠 NLP & SEMANTISCHE FILTERS (ORIGINELE ZWARE MOTOR)
# ==============================================================================
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

COMMON_CAPITALIZED_IGNORE = {"son", "dakika", "flaş", "şok", "türkiye", "istanbul", "ankara", "borsa", "bist", "spk", "tcmb", "merkez", "bankası", "resmi", "gazete", "hisse", "kap", "tüik", "fed", "abd", "avrupa", "altın", "gümüş", "dolar", "euro", "petrol"}

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

FAMOUS_PERSONS = ["mahfi eğilmez", "özgür demirtaş", "emre alkin", "hakan kara", "islam memiş", "ışık ökte", "tunç şatıroğlu", "mehmet şimşek", "fatih karahan", "recep tayyip erdoğan", "cevdet yılmaz", "ekrem imamoğlu", "donald trump", "jerome powell"]

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
            if nt not in COMMON_CAPITALIZED_IGNORE and nt not in STOPWORDS_ALL: entities.add(nt[:5] if len(nt)>=5 else nt)
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
    
    # Bepaal Story Cluster
    cluster, topic = None, "📰 Algemeen Economisch Bericht"
    if "CONCEPT_HUISARREST" in m_concepts: cluster, topic = "CLUSTER_HUISARREST_ZAAK", "⚖️ Dossier: Huisarrest & Maatregel"
    elif "CONCEPT_FONDS_MANIPULATIE" in m_concepts: cluster, topic = "CLUSTER_FONDS_SCHANDAAL", "🚨 Dossier: Fondsschandaal"
    elif "CONCEPT_KAYYUM_BESLAG" in m_concepts: cluster, topic = "CLUSTER_KAYYUM_TMSF", "🏛️ Dossier: Kayyum / TMSF"
    elif "CONCEPT_SPK_MAATREGEL" in m_concepts: cluster, topic = f"CLUSTER_SPK_{'_'.join(sorted(m_tickers))}", "⚠️ Dossier: SPK Maatregel"
    elif "CONCEPT_ARRESTATIE_JUSTITIE" in m_concepts: cluster, topic = "CLUSTER_ARRESTATIE", "🚓 Dossier: Justitie"
    elif "CONCEPT_RESMI_GAZETE_BELASTING" in m_concepts: cluster, topic = "CLUSTER_RESMI_GAZETE", "📜 Dossier: Resmi Gazete"
    elif m_persons and any(p in m_persons for p in ["mahfi egilmez", "ozgur demirtas"]): cluster, topic = f"CLUSTER_ECON_{sorted(list(m_persons))[0]}", f"🧠 Analyse: {sorted(list(m_persons))[0].title()}"
    elif m_tickers: cluster, topic = f"CLUSTER_AANDEEL_{'_'.join(sorted(m_tickers))}", f"🏢 Aandeel: {', '.join(sorted(m_tickers))}"
    elif "CONCEPT_TCMB_RENTE" in m_concepts: cluster, topic = "CLUSTER_TCMB", "🏦 Dossier: TCMB Rente"
    elif "CONCEPT_INFLATIE_TUIK" in m_concepts: cluster, topic = "CLUSTER_TUIK", "📊 Dossier: Inflatie (TÜİK)"
    
    item.update({"_matched_tickers": m_tickers, "_matched_persons": m_persons, "_proper_entities": entities, "_numbers": numbers, "_matched_concepts": set(m_concepts), "_core_stems": core_stems, "_story_cluster": cluster, "topic_readable": topic})
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
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', raw_html))).strip()

# ==============================================================================
# 📊 LIVE MARKTDATA & TECHNISCHE INDICATOREN (YFINANCE)
# ==============================================================================
@st.cache_data(ttl=300, show_spinner=False)
def get_live_market_snapshot():
    symbols = {"BIST 30": "XU030.IS", "BIST 100": "XU100.IS", "USD/TRY": "USDTRY=X", "Goud Ons ($)": "GC=F", "Zilver Ons ($)": "SI=F", "Brent Olie ($)": "BZ=F", "VIX (Angst)": "^VIX"}
    data = {}
    for name, sym in symbols.items():
        try:
            hist = yf.Ticker(sym).history(period="3d")
            if len(hist) >= 2:
                curr, prev = float(hist["Close"].iloc[-1]), float(hist["Close"].iloc[-2])
                data[name] = {"price": curr, "change": ((curr - prev) / prev) * 100.0, "as_of": str(hist.index[-1].date())}
            else:
                data[name] = {"price": None, "change": 0.0, "as_of": "N/B"}
        except Exception as e: data[name] = {"price": None, "change": 0.0, "as_of": "N/B", "error": str(e)}
        
    usd_try, gold_usd = data.get("USD/TRY", {}).get("price"), data.get("Goud Ons ($)", {}).get("price")
    if usd_try and gold_usd: data["Gram Goud (₺)"] = {"price": (gold_usd * usd_try) / 31.1035, "change": data["Goud Ons ($)"]["change"] + data["USD/TRY"]["change"]}
    else: data["Gram Goud (₺)"] = {"price": None, "change": 0.0}
    return data

@st.cache_data(ttl=600, show_spinner=False)
def get_bist_technical_snapshots(tickers_tuple):
    snapshots = {}
    for code in tickers_tuple:
        try:
            hist = yf.Ticker(f"{code}.IS").history(period="3mo")
            if len(hist) >= 15:
                curr, prev = float(hist["Close"].iloc[-1]), float(hist["Close"].iloc[-2])
                chg_1d = ((curr - prev) / prev) * 100.0
                sma20 = float(hist["Close"].rolling(20).mean().iloc[-1])
                sma50 = float(hist["Close"].rolling(50).mean().iloc[-1]) if len(hist)>=50 else None
                
                delta = hist["Close"].diff()
                gain = delta.clip(lower=0).ewm(alpha=1/14, min_periods=14, adjust=False).mean().iloc[-1]
                loss = (-delta.clip(upper=0)).ewm(alpha=1/14, min_periods=14, adjust=False).mean().iloc[-1]
                rsi = 100.0 - (100.0 / (1.0 + (gain / loss))) if loss > 0 else 50.0
                
                w_h, w_l = float(hist["High"].tail(20).max()), float(hist["Low"].tail(20).min())
                pivot, rng = (w_h + w_l + curr) / 3.0, max(w_h - w_l, curr * 0.02)
                
                snapshots[code] = {
                    "price": round(curr, 2), "change": round(chg_1d, 2), "rsi": round(float(rsi), 1),
                    "sma20": round(sma20, 2), "sma50": round(sma50, 2) if sma50 else None,
                    "s1": round(pivot - (0.382 * rng), 2), "r1": round(pivot + (0.382 * rng), 2),
                    "trend": "📈 Boven SMA20" if curr >= sma20 else "📉 Onder SMA20"
                }
        except: pass
    return snapshots

# ==============================================================================
# 🧠 INTELLIGENCE & PRIORITEIT
# ==============================================================================
def detect_sector_and_badge(combined_text, mentioned_stocks):
    sectors = []
    if any(w in combined_text for w in ["banka", "faiz", "tcmb", "akbnk", "garan", "ykbnk", "isctr"]): sectors.append("🏦 Banken")
    if any(w in combined_text for w in ["savunma", "asels", "oorlog", "navo"]): sectors.append("🛡️ Defensie")
    if any(w in combined_text for w in ["havayolu", "thyao", "pgsus", "tavhl", "luchtvaart"]): sectors.append("✈️ Luchtvaart")
    if any(w in combined_text for w in ["petrol", "enerji", "tuprs", "astor", "olie"]): sectors.append("⚡ Energie")
    if mentioned_stocks: sectors.insert(0, f"🎯 Aandeel: {', '.join(sorted(mentioned_stocks))}")
    if not sectors: sectors.append("📈 Brede BIST 30 Markt & Macro")
    
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

    if any(w in combined for w in ["brüt takas", "işlem yasağı", "tedbir", "bedelsiz"]):
        card_class, jip = "scandal-card" if "yasağı" in combined else "positive-card", f"De SPK of Borsa İstanbul heeft een officieel besluit genomen: {title_nl}."
        impact = "Beïnvloedt direct de handel van het aandeel. Brüt takas droogt speculatie op, een 'bedelsiz' (splitsing) trekt vaak particulieren aan."
    elif any(w in combined for w in ["fon", "spk", "tutuklama", "gözaltı", "kayyum", "soruşturma", "ev hapsi"]):
        card_class, jip = "scandal-card", f"Justitie of SPK grijpt in. Er is sprake van onderzoeken, arrestaties, of huisarrest: {title_nl}."
        impact = "Zorgt voor acute koersdruk en paniek bij de direct betrokken bedrijven. Institutioneel geld vlucht weg."
    elif any(w in combined for w in ["resmi gazete", "vergi", "atama"]):
        card_class, jip = "news-card", f"Nieuw overheidsbesluit in het Staatsblad (Resmi Gazete): {title_nl}."
        impact = "Nieuwe belastingen (zoals ÖTV) drukken direct de koersen van de geraakte sector."
    elif any(w in combined for w in ["faiz", "tcmb", "enflasyon", "fed", "powell"]):
        card_class, jip = "news-card", f"Cruciale update over rente of inflatie: {title_nl}."
        impact = "Stijgende rentes maken lenen duurder, wat BIST 30 aandelen drukt. Verwachting van lagere rente stuwt Goud en Zilver."
    elif any(w in combined for w in ["trump", "abd", "savaş", "israil", "rusya", "oorlog", "sanctie"]):
        card_class, jip = "news-card", f"Geopolitieke spanningen of sancties: {title_nl}."
        impact = "Zorgt voor onrust op de beurs. Kapitaal vlucht naar 'veilige havens', waardoor Goud en Zilver scherp in prijs stijgen."
    else:
        card_class, jip = "news-card", f"Actueel economisch of bedrijfsnieuws: {title_nl}."
        impact = "Geeft richting aan de dagelijkse handel. Positieve cijfers ondersteunen het vertrouwen."

    return jip, impact, card_class, badge_html, sector_str, sentiment_type

def calculate_article_priority_and_sort_key(item):
    cat, text = item.get("category", ""), f"{item.get('title_orig', '')} {item.get('title_nl', '')} {item.get('desc_orig', '')}".lower()
    
    if "🔎 Vrije Zoekopdracht" in cat: prio, lbl = 1, "🔎 Prio 1: Eigen Zoekopdracht"
    elif any(k in cat for k in ["Fondsschandaal", "SPK Bulletin", "Politiek", "Resmi Gazete"]) or any(w in text for w in ["fon", "spk", "manipülasyon", "tutuklama", "gözaltı", "kayyum", "resmi gazete", "ev hapsi"]):
        prio, lbl = 1, "🔥 Prio 1: Schandaal & Justitie"
    elif any(k in cat for k in ["BIST", "Top-Economen", "CDS-Premie"]) or any(w in text for w in ["tcmb", "merkez bankası", "faiz", "enflasyon", "mehmet şimşek", "cds"]):
        prio, lbl = 2, "📈 Prio 2: Macro & BIST 30"
    elif "Aandelennieuws" in cat or item.get("_matched_tickers"): prio, lbl = 3, "🏢 Prio 3: Bedrijfsnieuws (KAP)"
    else: prio, lbl = 4, "🌍 Prio 4: Globaal & Edelmetalen"

    item.update({"priority_level": prio, "priority_label": lbl})
    return prio

# ==============================================================================
# 📡 RSS HARVESTING & ORIGINELE SEMANTISCHE ONTDUBBELING
# ==============================================================================
SOURCE_STATUS = {}
def record_source(name, status, count=0, error=""): SOURCE_STATUS[name] = {"status": status, "count": int(count), "error": str(error)[:240]}

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
            
            title = title.rsplit(" - ", 1)[0].strip() if " - " in title else title.strip()
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
        item["title_nl"] = translate_to_nl(item["title_orig"]) if item["lang"] == "tr" else item["title_orig"]
        item["desc_nl"] = translate_to_nl(item["desc_orig"]) if item["lang"] == "tr" else item["desc_orig"]
        
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
        c_entities, c_numbers, c_stems = item.get("_proper_entities", set()), item.get("_numbers", set()), item.get("_core_stems", set())
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

# ==============================================================================
# 📅 AGENT 5: ORIGINELE 30-DAGEN AGENDA (8 Events)
# ==============================================================================
def get_upcoming_30_day_agenda():
    return [
        {"date": datetime(2026, 10, 28).date(), "time_str": "28-10-2026 (21:00 TR)", "title": "🇺🇸 Fed Rentebesluit & Powell", "jip": "De Amerikaanse centrale bank maakt haar rentebesluit bekend.", "impact": "Hint op lagere rente is positief voor Goud en Zilver.", "link": "https://www.federalreserve.gov/"},
        {"date": datetime(2026, 10, 29).date(), "time_str": "29-10-2026 (Hele dag)", "title": "🇹🇷 Cumhuriyet Bayramı", "jip": "Nationale feestdag. Borsa İstanbul is gesloten.", "impact": "Handelaren verkopen vaak voor sluiting om kredietrente te besparen.", "link": "https://www.borsaistanbul.com/"},
        {"date": datetime(2026, 11, 3).date(), "time_str": "03-11-2026 (10:00 TR)", "title": "🇹🇷 TÜİK Inflatiecijfers (Oktober)", "jip": "Publicatie van de officiële consumentenprijzen.", "impact": "Lage inflatie stuwt bankaandelen omhoog.", "link": "https://www.tuik.gov.tr/"},
        {"date": datetime(2026, 11, 6).date(), "time_str": "06-11-2026 (10:30 TR)", "title": "🇹🇷 TCMB 4e Inflatieverslag", "jip": "Fatih Karahan presenteert de nieuwe voorspellingen.", "impact": "Beleggers letten op signalen over het rentepad.", "link": "https://www.tcmb.gov.tr/"},
        {"date": datetime(2026, 11, 9).date(), "time_str": "09-11-2026 (18:00 TR)", "title": "🇹🇷 KAP Deadline Q3 Cijfers (Niet-Gecons.)", "jip": "Laatste dag voor publicatie Q3 cijfers.", "impact": "Zorgt voor flinke koersbewegingen op bedrijfsniveau.", "link": "https://www.kap.org.tr/"},
        {"date": datetime(2026, 11, 11).date(), "time_str": "11-11-2026 (16:30 TR)", "title": "🇺🇸 Amerikaanse Inflatiecijfers", "jip": "Publicatie van de Amerikaanse CPI.", "impact": "Lagere Amerikaanse inflatie stuwt Goud en Zilver.", "link": "https://www.bls.gov/cpi/"},
        {"date": datetime(2026, 11, 19).date(), "time_str": "19-11-2026 (14:00 TR)", "title": "🇹🇷 TCMB Rentebesluit", "jip": "De Turkse Centrale Bank bepaalt de nieuwe rente.", "impact": "Cruciaal voor de Lira, Gram Goud en de hele BIST 30.", "link": "https://www.tcmb.gov.tr/"},
        {"date": datetime(2026, 11, 20).date(), "time_str": "20-11-2026 (18:00 TR)", "title": "🇹🇷 KAP Deadline Q3 (Holdings & Banken)", "jip": "Grote holdings maken kwartaalcijfers bekend.", "impact": "Sluit het cijferseizoen af en bepaalt leiders in de BIST 30.", "link": "https://www.kap.org.tr/"}
    ]

# ==============================================================================
# 🖥️ HOOFDPROGRAMMA & INTERFACE
# ==============================================================================
st.markdown("### 📊 Marktoverzicht (Yahoo Finance; mogelijk vertraagd)")
market_data = get_live_market_snapshot()
cols = st.columns(min(len(market_data), 6))
for i, (name, info) in enumerate(list(market_data.items())[:6]):
    if info["price"] is not None: cols[i].metric(name, f"{info['price']:,.2f}", f"{info['change']:+.2f}%")
st.markdown("---")

if "master_enriched" not in st.session_state: st.session_state.master_enriched = None
if "source_status_snapshot" not in st.session_state: st.session_state.source_status_snapshot = {}

if st.button("🚀 Start Volledige Master Analyse (BIST 30 & Ontdubbeling)", type="primary"):
    tickers_clean = [t.split(" ")[0] for t in selected_tickers if t != BIST_INDEX_OPTION]
    all_bist_codes = [t.split(" ")[0] for t in BIST_30_STOCKS]
    SOURCE_STATUS.clear()
    
    with st.spinner("📡 Ophalen Google News, Turkse feeds, ontdubbelen en koersdata koppelen..."):
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
        if custom_search_query: rss_tasks.insert(0, (f"🔎 Vrije Zoekopdracht: '{custom_search_query}'", f'"{custom_search_query}"', "tr", 12, max_days_slider, tickers_clean, custom_search_query))
        if tickers_clean:
            for i in range(0, len(tickers_clean), 5):
                batch = tickers_clean[i:i+5]
                rss_tasks.append((f"🏢 Bedrijfsnieuws ({', '.join(batch)})", f"({' OR '.join(batch)}) AND (hisse OR KAP OR bilanço OR temettü)", "tr", 6, max_days_slider, batch, custom_search_query))
                
        with ThreadPoolExecutor(max_workers=12) as ex:
            google_res = list(ex.map(fetch_google_rss_feed, rss_tasks))
            direct_res = []
            if include_direct_newspaper_rss:
                direct_tasks = [(label, url, max_days_slider, tickers_clean, custom_search_query) for label, url in DIRECT_TURKISH_RSS_FEEDS]
                direct_res = list(ex.map(fetch_direct_newspaper_rss, direct_tasks))
                
        raw_items = [item for sublist in google_res + direct_res for item in sublist]
        enriched = enrich_articles_with_dutch_summaries(raw_items, all_bist_codes)
        unique_items = deduplicate_by_semantic_content(enriched, max_mode=dedup_strictness.startswith("Maximaal"))
        
        all_tickers = set(tickers_clean[:12])
        for it in unique_items: all_tickers.update(it.get("_matched_tickers", set()))
        
        if sort_mode == "Puur op Datum": unique_items.sort(key=lambda x: -x["datetime"].timestamp())
        else: unique_items.sort(key=lambda x: (x["priority_level"], -x["datetime"].timestamp()))
        
        st.session_state.master_enriched = unique_items
        st.session_state.raw_count = len(raw_items)
        st.session_state.stock_tech_map = get_bist_technical_snapshots(tuple(sorted(all_tickers)[:50]))
        st.session_state.agenda = get_upcoming_30_day_agenda()
        st.session_state.source_status_snapshot = dict(SOURCE_STATUS)

if st.session_state.master_enriched is not None:
    data = st.session_state.master_enriched
    tech = st.session_state.stock_tech_map
    
    st.success(f"✅ Master Analyse voltooid! Van de {st.session_state.raw_count} berichten zijn er **{len(data)} unieke dossiers** gebouwd (dankzij de semantische ontdubbeling).")
    
    with st.expander("🔎 Broncontrole: welke feeds werkten?", expanded=False):
        if st.session_state.source_status_snapshot:
            st.dataframe(pd.DataFrame([{"Bron": k, "Status": v["status"], "Berichten": v["count"], "Fout": v.get("error","")} for k,v in st.session_state.source_status_snapshot.items()]), use_container_width=True, hide_index=True)
            
    tab1, tab2, tab3, tab4, tab5 = st.tabs([f"🌐 Agent 1: Master Hub ({len(data)})", "🕵️‍♂️ Agent 2: Koers-Matrix", "💡 Agent 3: Advies", "⚖️ Agent 4: Risk", f"📅 Agent 5: Agenda ({len(st.session_state.agenda)})"])
    
    with tab1:
        st.markdown("### 🌐 Agent 1: Master News Hub")
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🟢 Positieve Katalysatoren", sum(1 for x in data if x["sentiment_type"] == "pos"))
        c2.metric("🔴 Hoog Risico / Schandaal", sum(1 for x in data if x["sentiment_type"] == "neg"))
        c3.metric("⚠️ Beleid & Macro-Impact", sum(1 for x in data if x["sentiment_type"] == "warn"))
        c4.metric("🧹 Samengevoegde Duplicaten", st.session_state.raw_count - len(data))
        
        f1, f2 = st.columns([2, 2])
        prio_filter = f1.selectbox("🔍 Filter op prioriteit:", ["Alle Unieke Dossiers", "🔥 Prio 1: Schandaal & Justitie", "📈 Prio 2: Macro & BIST 30", "🏢 Prio 3: Bedrijfsnieuws (KAP)", "🌍 Prio 4: Globaal & Edelmetalen"])
        inline_filter = f2.text_input("⚡ Snel filteren:", placeholder="Typ een woord...")
        
        filtered_data = [x for x in data if prio_filter.startswith("Alle") or str(x.get("priority_level")) in prio_filter]
        if inline_filter.strip(): filtered_data = [x for x in filtered_data if inline_filter.lower() in x["title_nl"].lower() or inline_filter.lower() in x["jip"].lower()]
            
        export_lines = [f"# BIST 30 Master Rapport ({datetime.now().strftime('%d-%m-%Y %H:%M')})\n"]
        for idx, item in enumerate(filtered_data, 1):
            chips = ""
            for tk in item.get("_matched_tickers", set()):
                s = tech.get(tk)
                if s and s.get("price"):
                    chips += f"<span class='stock-chip'>📊 <strong>{tk}</strong>: ₺{s['price']:,.2f} ({s['change']:+.2f}%) | RSI: {s['rsi']} | S1: ₺{s['s1']} | {s['trend']}</span>"
            
            also = ""
            if item.get("extra_source_links"):
                links = " · ".join([f"<a href='{l['link']}' target='_blank'>{l['name']}</a>" for l in item["extra_source_links"][:5]])
                also = f"<div class='card-subtitle'>🧠 <em>Zelfde inhoud ook gemeld door: {links} (automatisch samengevoegd).</em></div>"
            
            st.markdown(f"""
            <div class="clean-card {item['card_class']}">
                <div style="margin-bottom: 8px;">
                    <span class="prio-pill">{item['priority_label']}</span> <span class="topic-pill">{item['topic_readable']}</span> {item['badge_html']} 
                    <span style="font-size: 13px; color: #475569; font-weight: bold; margin-left: 8px;">#{idx} | 🕒 {item['date_str']} | Bron: {item['source']}</span>
                </div>
                <h4 class="card-title">{item['title_nl']}</h4>
                <div class="card-subtitle">Originele kop: {item['title_orig']}</div>
                {also}
                <div style="font-size: 13px; color: #1e3a8a; font-weight: 600; margin-bottom: 4px;">🎯 Sectoren: {item['sector_str']}</div>
                <div style="margin-bottom: 8px;">{chips}</div>
                <hr>
                <div class="card-text"><strong>🗣️ Wat betekent dit:</strong> {item['jip']}</div>
                <div class="card-text"><strong>📊 Economische impact:</strong> {item['impact']}</div>
                <div style="margin-top: 10px;"><a href="{item['link']}" target="_blank" style="font-weight: bold; color: #1d4ed8; text-decoration: none;">🔗 Lees originele bron</a></div>
            </div>
            """, unsafe_allow_html=True)
            export_lines.append(f"## #{idx} [{item['priority_label']}] {item['title_nl']} ({item['date_str']})\n- Impact: {item['impact']}\n- Bron: {item['link']}\n\n")

        if filtered_data: st.download_button("📥 Download Rapport (.md)", "\n".join(export_lines), file_name=f"BIST30_Dossier_{datetime.now().strftime('%Y%m%d_%H%M')}.md", mime="text/markdown")
            
    with tab2:
        st.markdown("### 🕵️‍♂️ Agent 2: Live Technische Koers-Matrix")
        if tech: st.dataframe(pd.DataFrame([{"Ticker": k, "Koers": v.get("price"), "Mutatie %": v.get("change"), "RSI": v.get("rsi"), "SMA 20": v.get("sma20"), "Steun S1": v.get("s1"), "Weerstand R1": v.get("r1"), "Trend": v.get("trend")} for k, v in tech.items()]), use_container_width=True, hide_index=True)
            
    with tab3: st.markdown("### 💡 Agent 3: Beleggingsadvies\n- Vermijd Prio-1 Schandaalfondsen.\n- Gebruik de RSI & Steun (S1) data uit de kaarten voor instapmomenten.")
    with tab4: st.markdown(f"### ⚖️ Agent 4: Risico-Audit\nLet op de {sum(1 for x in data if x['priority_level'] == 1)} Prio-1 schandalen en het macro-klimaat.")
    
    with tab5:
        st.markdown("### 📅 Agent 5: Komende 30-Dagen Macro Agenda")
        for ev in st.session_state.agenda:
            dl = (ev["date"] - datetime.now(timezone.utc).date()).days
            st.markdown(f"""
            <div class="clean-card news-card">
                <div style="margin-bottom: 6px;"><span class="topic-pill">{'Vandaag!' if dl==0 else f'Over {dl} dagen'}</span></div>
                <h4 class="card-title">📅 {ev['time_str']} - {ev['title']}</h4>
                <hr>
                <div class="card-text"><strong>🗣️ Wat gaat er gebeuren:</strong> {ev['jip']}</div>
                <div class="card-text"><strong>📊 Impact:</strong> {ev['impact']}</div>
                <a href="{ev['link']}" target="_blank" style="font-size: 13px; color: #2563eb; font-weight: bold; text-decoration: none;">🔗 Officiële kalender</a>
            </div>
            """, unsafe_allow_html=True)
