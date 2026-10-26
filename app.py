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
# ⚙️ PAGINA CONFIGURATIE & SCHONE CSS (Geen Scrollbalken)
# ==============================================================================
st.set_page_config(
    page_title="BIST 30 & Turkse Economie Master Scanner",
    page_icon="🇹🇷",
    layout="wide"
)

st.markdown("""
<style>
    /* Blokkeer Streamlit's neiging om metrics af te korten */
    [data-testid="stMetricValue"] { font-size: 1.6rem !important; white-space: nowrap !important; }
    
    /* Schone HTML Kaarten - Tekst breekt netjes af, NOOIT een horizontale scrollbalk */
    .clean-card {
        background-color: #ffffff;
        padding: 18px;
        border-radius: 8px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        margin-bottom: 16px;
        word-wrap: break-word;
        white-space: normal;
        border-left: 5px solid #cbd5e1;
    }
    .clean-card.scandal-card { border-left-color: #ef4444; } /* Rood */
    .clean-card.positive-card { border-left-color: #10b981; } /* Groen */
    .clean-card.news-card { border-left-color: #3b82f6; } /* Blauw */
    
    .card-title { margin-top: 0; color: #0f172a; font-size: 18px; font-weight: 700; margin-bottom: 4px; line-height: 1.3; }
    .card-subtitle { font-size: 13px; color: #64748b; margin-bottom: 12px; }
    .card-text { font-size: 15px; color: #334155; line-height: 1.5; margin-bottom: 8px; }
    .card-text strong { color: #1e293b; }
    
    .badge-pill { padding: 3px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; margin-right: 6px; }
    .badge-neg { background-color: #fee2e2; color: #991b1b; }
    .badge-pos { background-color: #dcfce7; color: #166534; }
    .badge-warn { background-color: #fef9c3; color: #854d0e; }
    .badge-info { background-color: #e0f2fe; color: #075985; }
    
    .stock-chip { 
        display: inline-block; background-color: #f1f5f9; padding: 4px 8px; 
        border-radius: 4px; font-size: 13px; margin: 2px 4px 2px 0; border: 1px solid #e2e8f0;
    }
    hr { margin: 12px 0; border: 0; border-top: 1px solid #e2e8f0; }
</style>
""", unsafe_allow_html=True)

st.markdown('<p style="font-size: 28px; font-weight: bold; color: #1E3A8A; margin-bottom: 0;">🇹🇷 BIST 30 & Turkse Economie Master Scanner</p>', unsafe_allow_html=True)
st.markdown("Gecombineerde **Master News Hub** met **Turkse nieuwsfeeds + Google News**, **voorzichtige ontdubbeling**, **live sentiment barometer**, **vrije zoekfunctie** en de **30-dagen Macro-Agenda**.")

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
    "gübre fabrikaları": "GUBRF", "koza altın": "KOZAL", "koza anadolu": "KOZAA",
    "coca-cola içecek": "CCOLA"
}

DIRECT_TURKISH_RSS_FEEDS = [
    ("📰 Bloomberg HT (Direct)", "https://www.bloomberght.com/rss"),
    ("📰 Habertürk Ekonomi (Direct)", "https://www.haberturk.com/rss/ekonomi.xml"),
    ("📰 NTV Ekonomi (Direct)", "https://www.ntv.com.tr/ekonomi.rss"),
    ("📰 CNN Türk Ekonomi (Direct)", "https://www.cnnturk.com/feed/rss/ekonomi/news"),
    ("📰 Dünya Gazetesi (Direct)", "https://www.dunya.com/rss"),
    ("📰 Cumhuriyet Ekonomi (Direct)", "https://www.cumhuriyet.com.tr/rss/ekonomi.xml"),
    ("📰 T24 Gündem & Politika (Direct)", "https://t24.com.tr/rss")
]

# ==============================================================================
# 🎛️ ZIJBALK: INSTELLINGEN
# ==============================================================================
st.sidebar.header("⚙️ Systeem & Inhouds-Filter")

custom_search_query = st.sidebar.text_input("🔎 Vrije Live Zoekopdracht (Optioneel):", value="", placeholder="Bijv. İmamoğlu, Trump...")
st.sidebar.markdown("---")

select_all_bist = st.sidebar.checkbox("Selecteer ALLE BIST 30 aandelen tegelijk", value=False)
if select_all_bist:
    default_selection = ALL_SIDEBAR_OPTIONS
else:
    default_selection = [BIST_INDEX_OPTION, "THYAO (Turkish Airlines)", "ASELS (Aselsan)", "KCHOL (Koç Holding)", "AKBNK (Akbank)", "GARAN (Garanti BBVA)", "TUPRS (Tüpraş)"]

selected_tickers = st.sidebar.multiselect("🎯 Kies BIST 30 Index en/of aandelen:", options=ALL_SIDEBAR_OPTIONS, default=default_selection)
max_days_slider = st.sidebar.slider("Nieuws ouderdom (dagen):", min_value=1, max_value=5, value=3)
include_direct_newspaper_rss = st.sidebar.checkbox("⚡ Inclusief rechtstreekse Turkse kranten-feeds", value=True)

dedup_strictness = st.sidebar.radio("🧠 Inhoudelijke Ontdubbeling:", ["Slim (1 kaart per uniek verhaal)", "Maximaal (Groepeer per thema)"], index=0)

# ==============================================================================
# 🧠 NLP & SEMANTISCHE FILTERS
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

def translate_to_nl(text):
    if not text or len(text.strip()) < 3: return text
    try:
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=nl&dt=t&q={urllib.parse.quote(text[:480])}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            translated = "".join([part[0] for part in data[0] if part and part[0]])
            return translated if translated else text
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
        except: data[name] = {"price": None, "change": 0.0, "as_of": "N/B"}
        
    usd_try = data.get("USD/TRY", {}).get("price")
    gold_usd = data.get("Goud Ons ($)", {}).get("price")
    if usd_try and gold_usd:
        data["Gram Goud (₺)"] = {"price": (gold_usd * usd_try) / 31.1035, "change": data["Goud Ons ($)"]["change"] + data["USD/TRY"]["change"]}
    else: data["Gram Goud (₺)"] = {"price": None, "change": 0.0}
    return data

@st.cache_data(ttl=600, show_spinner=False)
def get_bist_technical_snapshots(tickers_tuple):
    snapshots = {}
    for code in tickers_tuple:
        try:
            hist = yf.Ticker(f"{code}.IS").history(period="3mo")
            if len(hist) >= 15:
                curr = float(hist["Close"].iloc[-1])
                prev = float(hist["Close"].iloc[-2])
                chg_1d = ((curr - prev) / prev) * 100.0
                
                delta = hist["Close"].diff()
                gain = delta.clip(lower=0).ewm(alpha=1/14, min_periods=14, adjust=False).mean().iloc[-1]
                loss = (-delta.clip(upper=0)).ewm(alpha=1/14, min_periods=14, adjust=False).mean().iloc[-1]
                rsi = 100.0 - (100.0 / (1.0 + (gain / loss))) if loss > 0 else 50.0
                
                w_h, w_l = float(hist["High"].tail(20).max()), float(hist["Low"].tail(20).min())
                pivot = (w_h + w_l + curr) / 3.0
                rng = max(w_h - w_l, curr * 0.02)
                
                snapshots[code] = {
                    "price": round(curr, 2), "change": round(chg_1d, 2), "rsi": round(float(rsi), 1),
                    "s1": round(pivot - (0.382 * rng), 2), "r1": round(pivot + (0.382 * rng), 2),
                    "trend": "📈" if curr >= float(hist["Close"].rolling(20).mean().iloc[-1]) else "📉"
                }
        except: pass
    return snapshots

# ==============================================================================
# 🧠 INTELLIGENCE: JIP-EN-JANNEKE & CATEGORISATIE
# ==============================================================================
def detect_sector_and_badge(combined_text, mentioned_stocks):
    sectors = []
    if any(w in combined_text for w in ["banka", "faiz", "tcmb", "akbnk", "garan", "ykbnk", "isctr"]): sectors.append("🏦 Banken")
    if any(w in combined_text for w in ["savunma", "asels", "oorlog", "navo"]): sectors.append("🛡️ Defensie")
    if any(w in combined_text for w in ["petrol", "enerji", "tuprs", "astor", "olie"]): sectors.append("⚡ Energie")
    if mentioned_stocks: sectors.insert(0, f"🎯 Aandelen: {', '.join(sorted(mentioned_stocks))}")
    if not sectors: sectors.append("📈 Brede BIST 30 Markt & Macro")
    
    if any(w in combined_text for w in ["tutuklama", "gözaltı", "soruşturma", "ceza", "işlem yasağı", "kayyum"]):
        return '<span class="badge-pill badge-neg">🔴 HOOG RISICO / SCHANDAAL</span>', " · ".join(sectors[:3]), "neg"
    elif any(w in combined_text for w in ["temettü", "bedelsiz", "rekor", "not artışı", "yabancı"]):
        return '<span class="badge-pill badge-pos">🟢 POSITIEF / GROEI</span>', " · ".join(sectors[:3]), "pos"
    elif any(w in combined_text for w in ["resmi gazete", "vergi", "faiz", "enflasyon", "trump", "fed"]):
        return '<span class="badge-pill badge-warn">⚠️ BELEID & MACRO</span>', " · ".join(sectors[:3]), "warn"
    return '<span class="badge-pill badge-info">⚖️ MARKT DUIDING</span>', " · ".join(sectors[:3]), "info"

def build_jip_en_janneke_analysis(title_orig, title_nl, desc_nl, matched_tickers):
    combined = f"{title_orig} {title_nl} {desc_nl}".lower()
    badge_html, sector_str, sentiment_type = detect_sector_and_badge(combined, matched_tickers)

    if any(w in combined for w in ["brüt takas", "işlem yasağı", "tedbir", "bedelsiz"]):
        card_class, jip = "scandal-card" if "yasağı" in combined else "positive-card", "SPK of Borsa İstanbul heeft een direct besluit genomen over specifieke aandelen."
        impact = "Beïnvloedt direct de liquiditeit en handel van het aandeel. Brüt takas droogt speculatie op, een 'bedelsiz' (splitsing) trekt vaak particulieren aan."
    elif any(w in combined for w in ["fon", "spk", "tutuklama", "gözaltı", "kayyum", "soruşturma"]):
        card_class, jip = "scandal-card", "Justitie of SPK grijpt in. Er lopen onderzoeken, arrestaties of inbeslagnames (kayyum)."
        impact = "Zorgt voor acute koersdruk en paniek bij de direct betrokken bedrijven. Institutioneel geld vlucht weg."
    elif any(w in combined for w in ["resmi gazete", "vergi", "atama"]):
        card_class, jip = "news-card", "Nieuw overheidsbesluit in het Staatsblad (Resmi Gazete) over belastingen of benoemingen."
        impact = "Nieuwe belastingen (zoals ÖTV) drukken de koersen van de geraakte sector. Steunmaatregelen stuwen ze."
    elif any(w in combined for w in ["faiz", "tcmb", "enflasyon", "fed", "powell"]):
        card_class, jip = "news-card", "Cruciale updates over inflatie en het rentebeleid van centrale banken."
        impact = "Hoge of stijgende rentes maken lenen duurder, wat BIST 30 aandelen drukt. Verwachting van lagere rente is dé brandstof voor Goud en Zilver."
    elif any(w in combined for w in ["trump", "abd", "savaş", "israil", "rusya", "oorlog", "sanctie"]):
        card_class, jip = "news-card", "Geopolitieke spanningen, oorlog of internationale sancties."
        impact = "Zorgt voor paniek op de BIST 30. Kapitaal vlucht direct naar 'veilige havens', waardoor Goud en Zilver scherp in prijs stijgen."
    else:
        card_class, jip = "news-card", "Actueel economisch of bedrijfsnieuws (KAP meldingen of macro-data)."
        impact = "Geeft richting aan de dagelijkse handel. Positieve cijfers ondersteunen het vertrouwen in de zwaargewichten."

    return jip, impact, card_class, badge_html, sector_str, sentiment_type

# ==============================================================================
# 📡 RSS HARVESTING & SAMENVOEGEN
# ==============================================================================
SOURCE_STATUS = {}
def record_source(name, status, count=0): SOURCE_STATUS[name] = {"status": status, "count": count}

def fetch_google_rss_feed(args):
    cat_label, query, lang, max_items, max_days, extra_tickers, custom_kw = args
    q_enc = urllib.parse.quote(f"{query} when:{max_days}d" if max_days else query)
    url = f"https://news.google.com/rss/search?q={q_enc}&hl={lang}&gl={lang.upper()}&ceid={lang.upper()}:{lang}"
    
    items, now_utc = [], datetime.now(timezone.utc)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            root = ET.fromstring(resp.read())
        for item in root.findall(".//item"):
            title, link = item.findtext("title") or "", item.findtext("link") or ""
            desc = clean_html_text(item.findtext("description") or "")
            src = item.find("source").text if item.find("source") is not None else "Nieuws"
            if not title or not link: continue
            
            title = title.rsplit(" - ", 1)[0].strip() if " - " in title else title.strip()
            if not is_economically_relevant(title, desc, extra_tickers, custom_kw): continue
            
            dt = now_utc
            pub_str = item.findtext("pubDate")
            if pub_str:
                try: 
                    p_dt = parsedate_to_datetime(pub_str)
                    if p_dt: dt = p_dt if p_dt.tzinfo else p_dt.replace(tzinfo=timezone.utc)
                except: pass
            
            items.append({"category": cat_label, "title_orig": title, "desc_orig": desc, "source": src, "link": link, "datetime": dt, "lang": lang})
            if len(items) >= max_items: break
        record_source(cat_label, "OK", len(items))
    except: record_source(cat_label, "FOUT", 0)
    return items

def fetch_direct_newspaper_rss(args):
    source_label, url, max_days, extra_tickers, custom_kw = args
    items, now_utc = [], datetime.now(timezone.utc)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            root = ET.fromstring(resp.read())
        for item in root.findall(".//item")[:15]:
            title, link = clean_html_text(item.findtext("title") or ""), (item.findtext("link") or "").strip()
            desc = clean_html_text(item.findtext("description") or "")
            if not title or not link or not is_economically_relevant(title, desc, extra_tickers, custom_kw): continue
            
            dt, pub_str = now_utc, item.findtext("pubDate")
            if pub_str:
                try: 
                    p_dt = parsedate_to_datetime(pub_str)
                    if p_dt: dt = p_dt if p_dt.tzinfo else p_dt.replace(tzinfo=timezone.utc)
                except: pass
                
            items.append({"category": source_label, "title_orig": title, "desc_orig": desc[:300], "source": source_label.split(" ")[1], "link": link, "datetime": dt, "lang": "tr"})
    except: pass
    return items

def deduplicate_by_semantic_content(items, max_mode=False):
    items.sort(key=lambda x: -x["datetime"].timestamp())
    unique_items, seen_links = [], set()
    for item in items:
        norm_link = item["link"].split("?")[0].rstrip("/").lower()
        if norm_link in seen_links: continue
        
        c_title = normalize_tr(item.get("title_nl", item["title_orig"]))
        dup_of = None
        for ex in unique_items:
            similarity = difflib.SequenceMatcher(None, c_title, normalize_tr(ex.get("title_nl", ex["title_orig"]))).ratio()
            if similarity >= (0.82 if max_mode else 0.88):
                dup_of = ex
                break
                
        if dup_of:
            links = dup_of.setdefault("extra_source_links", [])
            if norm_link not in [l["link"].lower() for l in links]:
                links.append({"name": item["source"], "link": item["link"]})
        else:
            seen_links.add(norm_link)
            unique_items.append(item)
    return unique_items

# ==============================================================================
# 📅 AGENT 5: 30-DAGEN AGENDA
# ==============================================================================
def get_upcoming_30_day_agenda():
    return [
        {"date": datetime(2026, 10, 28).date(), "title": "🇺🇸 Fed Rentebesluit & Powell", "jip": "De Amerikaanse centrale bank maakt haar rentebesluit bekend.", "impact": "Hint op lagere rente is direct positief voor Goud en Zilver.", "link": "https://www.federalreserve.gov/"},
        {"date": datetime(2026, 10, 29).date(), "title": "🇹🇷 Cumhuriyet Bayramı", "jip": "Nationale feestdag. Borsa İstanbul is gesloten.", "impact": "Handelaren verkopen vooraf vaak aandelen om kredietrente te besparen.", "link": "https://www.borsaistanbul.com/"},
        {"date": datetime(2026, 11, 3).date(), "title": "🇹🇷 TÜİK Inflatiecijfers", "jip": "Publicatie van de officiële Turkse consumentenprijzen.", "impact": "Lage inflatie stuwt bankaandelen omhoog.", "link": "https://www.tuik.gov.tr/"},
        {"date": datetime(2026, 11, 19).date(), "title": "🇹🇷 TCMB Rentebesluit", "jip": "De Turkse Centrale Bank bepaalt de nieuwe rente.", "impact": "Cruciaal voor de Lira, Gram Goud en de hele BIST 30 Index.", "link": "https://www.tcmb.gov.tr/"}
    ]

# ==============================================================================
# 🖥️ HOOFDPROGRAMMA & INTERFACE
# ==============================================================================
market_data = get_live_market_snapshot()
cols = st.columns(min(len(market_data), 6))
for i, (name, info) in enumerate(list(market_data.items())[:6]):
    if info["price"] is not None: cols[i].metric(name, f"{info['price']:,.2f}", f"{info['change']:+.2f}%")
st.markdown("---")

if "master_enriched" not in st.session_state: st.session_state.master_enriched = None

if st.button("🚀 Start Volledige Master Analyse (BIST 30 Focus)", type="primary"):
    tickers_clean = [t.split(" ")[0] for t in selected_tickers if t != BIST_INDEX_OPTION]
    
    with st.spinner("📡 Ophalen van Google News, Turkse feeds, ontdubbelen en koersdata koppelen... dit duurt enkele seconden."):
        rss_tasks = [
            ("🚨 Fondsschandaal & Justitie", '("fon" OR "SPK" OR "manipülasyon" OR "gözaltı" OR "kayyum")', "tr", 12, max_days_slider, tickers_clean, custom_search_query),
            ("📜 Resmi Gazete & Beleid", '("Resmi Gazete" OR "ÖTV" OR "vergi")', "tr", 10, max_days_slider, tickers_clean, custom_search_query),
            ("🧠 Top-Economen", '("Mahfi Eğilmez" OR "Özgür Demirtaş" OR "Hakan Kara" OR "İslam Memiş")', "tr", 10, max_days_slider, tickers_clean, custom_search_query),
            ("📈 BIST 30 & Macro", '("Borsa İstanbul" OR "BIST 30" OR "TCMB" OR "faiz")', "tr", 12, max_days_slider, tickers_clean, custom_search_query),
            ("🌍 Oorlog & Geopolitiek (NL)", '(oorlog OR sancties OR "Midden-Oosten")', "nl", 10, max_days_slider, [], custom_search_query),
            ("🥇 Goud & Zilver (NL)", '(goudprijs OR zilverprijs OR "Fed rente" OR edelmetalen)', "nl", 10, max_days_slider, [], custom_search_query),
            ("🏛️ OFFICIEEL KAP", 'site:kap.org.tr "bildirim"', "tr", 8, max_days_slider, tickers_clean, custom_search_query)
        ]
        
        with ThreadPoolExecutor(max_workers=10) as ex:
            google_res = list(ex.map(fetch_google_rss_feed, rss_tasks))
            direct_res = []
            if include_direct_newspaper_rss:
                direct_tasks = [(label, url, max_days_slider, tickers_clean, custom_search_query) for label, url in DIRECT_TURKISH_RSS_FEEDS]
                direct_res = list(ex.map(fetch_direct_newspaper_rss, direct_tasks))
                
        raw_items = [item for sublist in google_res + direct_res for item in sublist]
        
        # Verrijken en Vertalen
        for item in raw_items:
            item["title_nl"] = translate_to_nl(item["title_orig"]) if item["lang"] == "tr" else item["title_orig"]
            item["desc_nl"] = translate_to_nl(item["desc_orig"]) if item["lang"] == "tr" else item["desc_orig"]
            
            matched = [tk for tk in [t.split(" ")[0] for t in BIST_30_STOCKS] if tk in item["title_orig"].upper() or tk in item["title_nl"].upper()]
            item["_matched_tickers"] = matched
            
            jip, impact, c_class, badge, sec_str, s_type = build_jip_en_janneke_analysis(item["title_orig"], item["title_nl"], item["desc_nl"], matched)
            item.update({"jip": jip, "impact": impact, "card_class": c_class, "badge_html": badge, "sector_str": sec_str, "sentiment_type": s_type})
            
        unique_items = deduplicate_by_semantic_content(raw_items, max_mode=dedup_strictness.startswith("Maximaal"))
        
        all_tickers = set(tickers_clean[:12])
        for it in unique_items: all_tickers.update(it["_matched_tickers"])
        
        st.session_state.master_enriched = unique_items
        st.session_state.raw_count = len(raw_items)
        st.session_state.stock_tech_map = get_bist_technical_snapshots(tuple(sorted(all_tickers)[:50]))
        st.session_state.agenda = get_upcoming_30_day_agenda()

if st.session_state.master_enriched is not None:
    data = st.session_state.master_enriched
    tech = st.session_state.stock_tech_map
    
    st.success(f"✅ Master Analyse voltooid! Van de {st.session_state.raw_count} berichten zijn er **{len(data)} unieke dossiers** gebouwd.")
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🌐 Agent 1: Master Hub", "🕵️‍♂️ Agent 2: Koers-Matrix", "💡 Agent 3: Advies", "⚖️ Agent 4: Risk", "📅 Agent 5: Agenda"])
    
    with tab1:
        st.markdown("### 🌐 Agent 1: Master News Hub")
        
        # 🌡️ LIVE MARKT BAROMETER 🌡️
        neg_c = sum(1 for x in data if x["sentiment_type"] == "neg")
        pos_c = sum(1 for x in data if x["sentiment_type"] == "pos")
        
        if neg_c > pos_c + 2:
            st.error(f"🚨 **Markt Barometer (BIST 30):** Hoog risico. Er circuleren {neg_c} zware waarschuwingen of justitiële schandalen.")
        elif pos_c > neg_c:
            st.success(f"🟢 **Markt Barometer (BIST 30):** Positieve flow. Bedrijfs- en macro-nieuws is overwegend constructief.")
        else:
            st.info(f"⚖️ **Markt Barometer (BIST 30):** Neutraal beeld. Markten zoeken richting.")
            
        st.markdown("<br>", unsafe_allow_html=True)
            
        for item in data:
            chips = ""
            for tk in item["_matched_tickers"]:
                s = tech.get(tk)
                if s and s.get("price"):
                    chips += f"<span class='stock-chip'>📊 <strong>{tk}</strong>: ₺{s['price']:,.2f} ({s['change']:+.2f}%) | RSI: {s['rsi']} | S1: ₺{s['s1']} | {s['trend']}</span>"
            
            also = ""
            if item.get("extra_source_links"):
                links = " · ".join([f"<a href='{l['link']}' target='_blank'>{l['name']}</a>" for l in item["extra_source_links"][:3]])
                also = f"<div class='card-subtitle'>🧠 <em>Ook gemeld door: {links} (automatisch samengevoegd)</em></div>"
            
            st.markdown(f"""
            <div class="clean-card {item['card_class']}">
                <div style="margin-bottom: 6px;">{item['badge_html']} <span style="font-size: 13px; color: #475569; font-weight: bold;">| 🕒 {item['datetime'].strftime('%d-%m %H:%M')} | Bron: {item['source']}</span></div>
                <h4 class="card-title">{item['title_nl']}</h4>
                <div class="card-subtitle">Originele kop: {item['title_orig']}</div>
                {also}
                <div style="font-size: 13px; color: #1e3a8a; font-weight: 600; margin-bottom: 4px;">🎯 Sectoren: {item['sector_str']}</div>
                <div style="margin-bottom: 8px;">{chips}</div>
                <hr>
                <div class="card-text"><strong>🗣️ Wat betekent dit:</strong> {item['jip']}</div>
                <div class="card-text"><strong>📊 Economische impact:</strong> {item['impact']}</div>
                <div style="margin-top: 10px;"><a href="{item['link']}" target="_blank" style="font-weight: bold; color: #1d4ed8; text-decoration: none;">🔗 Lees originele artikel</a></div>
            </div>
            """, unsafe_allow_html=True)
            
    with tab2:
        st.markdown("### 🕵️‍♂️ Agent 2: Live Technische Koers-Matrix (BIST 30)")
        if tech:
            df = pd.DataFrame([{"Ticker": k, "Koers": v.get("price"), "Mutatie %": v.get("change"), "RSI": v.get("rsi"), "Steun S1": v.get("s1"), "Weerstand R1": v.get("r1"), "Trend": v.get("trend")} for k, v in tech.items()])
            st.dataframe(df, use_container_width=True, hide_index=True)
            
    with tab5:
        st.markdown("### 📅 Agent 5: Komende 30-Dagen Macro Agenda")
        for ev in st.session_state.agenda:
            st.markdown(f"""
            <div class="clean-card news-card">
                <h4 class="card-title">📅 {ev['date'].strftime('%d-%m-%Y')} - {ev['title']}</h4>
                <hr>
                <div class="card-text"><strong>🗣️ Wat gaat er gebeuren:</strong> {ev['jip']}</div>
                <div class="card-text"><strong>📊 Impact:</strong> {ev['impact']}</div>
                <a href="{ev['link']}" target="_blank" style="font-size: 13px; color: #2563eb; font-weight: bold; text-decoration: none;">🔗 Officiële kalender</a>
            </div>
            """, unsafe_allow_html=True)
