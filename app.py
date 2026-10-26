import os
import re
import html
import time
import difflib
import streamlit as st
import yfinance as yf
import pandas as pd
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor
from email.utils import parsedate_to_datetime

# ==============================================================================
# ⚙️ CONFIGURATIE & SCHONE CSS OPMAAK
# ==============================================================================
st.set_page_config(
    page_title="BIST & Gold Intelligence Scanner",
    page_icon="📰",
    layout="wide"
)

st.markdown("""
<style>
    /* Blokkeer Streamlit's neiging om K/M te gebruiken */
    [data-testid="stMetricValue"] { font-size: 1.6rem !important; white-space: nowrap !important; }
    
    /* Schone Nieuwskaarten - Breekt tekst netjes af, NOOIT een scrollbalk */
    .news-card {
        background-color: #ffffff;
        padding: 18px;
        border-radius: 8px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        margin-bottom: 15px;
        border-left: 5px solid #cbd5e1;
        word-wrap: break-word;
        white-space: normal;
    }
    .news-card.pos { border-left-color: #10b981; }
    .news-card.neg { border-left-color: #ef4444; }
    .news-card.warn { border-left-color: #f59e0b; }
    .news-card.info { border-left-color: #3b82f6; }
    
    .news-title { margin-top: 0; color: #0f172a; font-size: 18px; font-weight: 700; margin-bottom: 8px; line-height: 1.3; }
    .news-meta { font-size: 12px; color: #64748b; margin-bottom: 12px; font-weight: 600; }
    .news-section { font-size: 15px; color: #334155; line-height: 1.5; margin-bottom: 8px; }
    .news-section strong { color: #1e293b; }
    
    .badge-bar { margin-bottom: 10px; }
    .badge { padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; margin-right: 6px; }
    .badge-bist { background-color: #e0e7ff; color: #3730a3; }
    .badge-macro { background-color: #fef9c3; color: #854d0e; }
    .badge-justice { background-color: #fee2e2; color: #991b1b; }
    
    hr { margin: 10px 0; border: 0; border-top: 1px solid #e2e8f0; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 🗂 WOORDENLIJSTEN & INTELLIGENCE DATA
# ==============================================================================
BIST_TICKERS = [
    "AKBNK", "ALARK", "ASELS", "ASTOR", "BIMAS", "BRSAN", "CCOLA", "CIMSA", "CWENE", "DOAS", 
    "EGEEN", "EKGYO", "ENJSA", "ENKAI", "EREGL", "FROTO", "GARAN", "GESAN", "GUBRF", "HALKB", 
    "HEKTS", "ISCTR", "KCHOL", "KONTR", "KOZAA", "KOZAL", "KRDMD", "MIATK", "ODAS", "OYAKC", 
    "PETKM", "PGSUS", "SAHOL", "SASA", "SISE", "SMRTG", "SOKM", "TAVHL", "TCELL", "THYAO", 
    "TOASO", "TTKOM", "TUPRS", "VAKBN", "VESTL", "YKBNK"
]

TOP_ANALYSTS = [
    "Mahfi Eğilmez", "Özgür Demirtaş", "Emre Alkin", "İslam Memiş", "Tunç Şatıroğlu", 
    "Hakan Kara", "Kerim Rota", "Işık Ökte", "Tuncay Turşucu", "Atilla Yeşilada", "Luke Gromen", "Peter Schiff"
]

DIRECT_FEEDS = {
    "TR_ECONOMY": [
        ("Bloomberg HT", "https://www.bloomberght.com/rss"),
        ("NTV Ekonomi", "https://www.ntv.com.tr/ekonomi.rss"),
        ("Dünya", "https://www.dunya.com/rss"),
        ("T24 Gündem", "https://t24.com.tr/rss")
    ],
    "GLOBAL_MACRO": [
        ("Kitco Gold", "https://www.kitco.com/rss/news_precious_metals.xml"),
        ("Investing NL", "https://nl.investing.com/rss/news.rss")
    ]
}

# ==============================================================================
# 📊 LIVE MACRO TICKER (YFINANCE)
# ==============================================================================
@st.cache_data(ttl=300, show_spinner=False)
def get_live_market_data():
    symbols = {
        "BIST 100": "XU100.IS", 
        "USD/TRY": "USDTRY=X", 
        "EUR/TRY": "EURTRY=X",
        "Goud Ons ($)": "GC=F", 
        "Zilver Ons ($)": "SI=F", 
        "Brent Olie ($)": "BZ=F", 
        "VIX (Angst)": "^VIX"
    }
    data = {}
    for name, sym in symbols.items():
        try:
            hist = yf.Ticker(sym).history(period="5d")
            if len(hist) >= 2:
                curr = float(hist["Close"].iloc[-1])
                prev = float(hist["Close"].iloc[-2])
                chg = ((curr - prev) / prev) * 100.0
                data[name] = {"price": curr, "change": chg}
            else:
                data[name] = {"price": 0.0, "change": 0.0}
        except:
            data[name] = {"price": 0.0, "change": 0.0}

    usd_try = data["USD/TRY"]["price"]
    gold_usd = data["Goud Ons ($)"]["price"]
    silver_usd = data["Zilver Ons ($)"]["price"]

    if gold_usd > 0 and usd_try > 0:
        data["Gram Goud (₺)"] = {
            "price": (gold_usd * usd_try) / 31.1035,
            "change": data["Goud Ons ($)"]["change"] + data["USD/TRY"]["change"]
        }
    else:
        data["Gram Goud (₺)"] = {"price": 0.0, "change": 0.0}
        
    if silver_usd > 0 and usd_try > 0:
        data["Gram Zilver (₺)"] = {
            "price": (silver_usd * usd_try) / 31.1035,
            "change": data["Zilver Ons ($)"]["change"] + data["USD/TRY"]["change"]
        }
    else:
        data["Gram Zilver (₺)"] = {"price": 0.0, "change": 0.0}
        
    return data

# ==============================================================================
# 🧠 TEKSTANALYSE & JIP-EN-JANNEKE ENGINE
# ==============================================================================
def clean_html(raw_html):
    if not raw_html: return ""
    clean = re.sub(r'<[^>]+>', ' ', raw_html)
    clean = html.unescape(clean)
    return re.sub(r'\s+', ' ', clean).strip()

def analyze_article(title, desc, source):
    """Categoriseert het nieuws en bouwt de Jip-en-Janneketaal zinnen."""
    full_text = f"{title} {desc}".lower()
    
    sentiment = "info"
    jip_summary = "Dit is een algemeen economisch bericht."
    econ_impact = "De impact op de bredere markt is afhankelijk van verdere details."
    tags = []
    
    # 1. Justitie & Schandalen
    if any(w in full_text for w in ["tutuklama", "gözaltı", "operasyon", "spk", "ceza", "kayyum", "manipülasyon", "soruşturma"]):
        sentiment = "neg"
        tags.append("🚨 Justitie & SPK")
        jip_summary = "Er is ingegrepen door justitie of de beurswaakhond (SPK). Het gaat hier om onderzoeken, arrestaties, huiszoekingen of zware boetes."
        econ_impact = "Dit nieuws veroorzaakt doorgaans een onmiddellijke schokgolf. Aandelen van betrokken bedrijven kunnen scherp dalen door paniekverkopen. Grote partijen blijven voorlopig aan de zijlijn."
        
    # 2. Rente, TCMB & Fed
    elif any(w in full_text for w in ["faiz", "tcmb", "merkez bankası", "enflasyon", "fed", "powell", "şimşek"]):
        sentiment = "warn"
        tags.append("🏦 Macro & Rente")
        jip_summary = "Dit bericht draait om het rente- of inflatiebeleid van centrale banken zoals de TCMB of de Fed."
        econ_impact = "Beslissingen over rente sturen de hele markt. Een hogere rente is nadelig voor aandelen omdat lenen duurder wordt. Voor Goud en Zilver is een signaal dat de rente omlaag gaat juist de perfecte brandstof voor een prijsstijging."
        
    # 3. Oorlog & Geopolitiek
    elif any(w in full_text for w in ["savaş", "israil", "rusya", "iran", "yaptırım", "oorlog", "sanctie", "füze", "pentagon"]):
        sentiment = "neg"
        tags.append("🌍 Geopolitiek & Oorlog")
        jip_summary = "Er is sprake van toenemende geopolitieke spanningen, oorlogsdreiging of internationale sancties."
        econ_impact = "Bij internationale onrust vlucht kapitaal razendsnel uit risicovolle aandelen (BIST 100 daalt) richting 'veilige havens'. Dit is de primaire reden waarom prijzen van Goud en Zilver bij dit soort nieuws vaak omhoog schieten. Defensie-aandelen (zoals ASELSAN) kunnen wel profiteren."
        
    # 4. Economische Groei & Positief Nieuws
    elif any(w in full_text for w in ["büyüme", "rekor", "not artışı", "fitch", "moody", "yabancı yatırımcı", "temettü", "bedelsiz"]):
        sentiment = "pos"
        tags.append("📈 Groei & Instroom")
        jip_summary = "Positief economisch nieuws: denk aan sterke kwartaalcijfers, een upgrade van de kredietstatus van Turkije, of vers buitenlands kapitaal dat de markt instroomt."
        econ_impact = "Dit is uitstekend nieuws voor de beurs. Banken en de zwaargewichten uit de BIST 100 Index reageren hier direct positief op omdat het vertrouwen toeneemt."
        
    # Zoek naar specifieke BIST tickers
    matched_tickers = [tk for tk in BIST_TICKERS if tk in title.upper() or tk in desc.upper()]
    if matched_tickers:
        tags.append(f"🏢 BIST: {', '.join(matched_tickers)}")
        
    # Zoek naar bekende analisten
    matched_analysts = [an for an in TOP_ANALYSTS if an.lower() in full_text]
    if matched_analysts:
        tags.append(f"🧠 Analist: {', '.join(matched_analysts)}")

    return sentiment, tags, jip_summary, econ_impact

# ==============================================================================
# 📡 RSS OOGSTMACHINE (Layers A & B)
# ==============================================================================
def fetch_rss_feed(url, source_name, max_items=10):
    items = []
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 BISTScanner/2.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            root = ET.fromstring(resp.read())
            
        for item in root.findall(".//item")[:max_items]:
            title = clean_html(item.findtext("title") or "")
            desc = clean_html(item.findtext("description") or "")
            link = item.findtext("link") or ""
            pub_date = item.findtext("pubDate") or ""
            
            if not title or not link: continue
            
            dt = datetime.now(timezone.utc)
            if pub_date:
                try:
                    parsed_dt = parsedate_to_datetime(pub_date)
                    if parsed_dt: dt = parsed_dt if parsed_dt.tzinfo else parsed_dt.replace(tzinfo=timezone.utc)
                except: pass
                
            sentiment, tags, jip, impact = analyze_article(title, desc, source_name)
            
            items.append({
                "title": title, "desc": desc, "link": link, "source": source_name, 
                "datetime": dt, "sentiment": sentiment, "tags": tags, "jip": jip, "impact": impact
            })
    except:
        pass
    return items

def fetch_google_news(query, lang="tr", max_items=15):
    q_enc = urllib.parse.quote(f"{query} when:3d")
    url = f"https://news.google.com/rss/search?q={q_enc}&hl={lang}&gl={lang.upper()}&ceid={lang.upper()}:{lang}"
    return fetch_rss_feed(url, "Google News (Aggregator)", max_items)

def run_harvesting_engine():
    tasks = []
    
    # Layer A & B: Directe Turkse Feeds
    for name, url in DIRECT_FEEDS["TR_ECONOMY"]:
        tasks.append((url, name, 8))
        
    # Layer A & B: Directe Globale Feeds
    for name, url in DIRECT_FEEDS["GLOBAL_MACRO"]:
        tasks.append((url, name, 8))
        
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(lambda p: fetch_rss_feed(*p), tasks))
        
    # Specifieke Google News Queries
    gn_results = []
    queries = [
        ('("SPK" OR "tutuklama" OR "kayyum" OR "manipülasyon" OR "operasyon")', 'tr'),
        ('("TCMB" OR "faiz" OR "enflasyon" OR "Mehmet Şimşek")', 'tr'),
        ('(goudprijs OR zilverprijs OR "Fed rente" OR "Midden-Oosten" OR oorlog)', 'nl')
    ]
    with ThreadPoolExecutor(max_workers=3) as executor:
        gn_results = list(executor.map(lambda q: fetch_google_news(q[0], q[1], 12), queries))
        
    all_items = []
    for r in results + gn_results: all_items.extend(r)
    return all_items

# ==============================================================================
# 🧹 SEMANTISCHE ONTDUBBELING
# ==============================================================================
def deduplicate_news(items):
    items.sort(key=lambda x: x["datetime"].timestamp(), reverse=True)
    unique_items = []
    seen_links = set()
    
    for item in items:
        link = item["link"].split("?")[0].strip("/")
        if link in seen_links: continue
        
        is_dup = False
        title_lower = item["title"].lower()
        
        for ex in unique_items:
            # Als titels voor 75% overeenkomen, is het hetzelfde nieuwsfeit
            if difflib.SequenceMatcher(None, title_lower, ex["title"].lower()).ratio() > 0.75:
                is_dup = True
                break
                
        if not is_dup:
            seen_links.add(link)
            unique_items.append(item)
            
    return unique_items

# ==============================================================================
# 🖥️ COMMAND CENTER UI BOUWEN
# ==============================================================================
st.markdown('<h1 style="color: #1e3a8a; margin-bottom: 0;">📰 BIST Gold & Macro Intelligence</h1>', unsafe_allow_html=True)
st.markdown("Dual-Agent architectuur: Lokale schandalen & beleid vs. Globale macro & edelmetalen.")

# -- LIVE TICKER --
m_data = get_live_market_data()
cols = st.columns(len(m_data))
for i, (name, d) in enumerate(m_data.items()):
    cols[i].metric(name, f"{d['price']:,.2f}", f"{d['change']:+.2f}%")
st.markdown("---")

# -- OPHALEN DATA --
if "news_cache" not in st.session_state:
    with st.spinner("De 4 Intelligence Layers scannen, vertalen en ontdubbelen..."):
        raw_news = run_harvesting_engine()
        clean_news = deduplicate_news(raw_news)
        
        # Splitsen per agent
        agent1_news = [n for n in clean_news if "nl" not in n["source"].lower() and "google" not in n["source"].lower() or any(tag.startswith("🚨") or tag.startswith("🏢") for tag in n["tags"])]
        agent2_news = [n for n in clean_news if "goud" in n["title"].lower() or "fed" in n["title"].lower() or any(tag.startswith("🌍") for tag in n["tags"])]
        
        # Fallback toewijzing
        for n in clean_news:
            if n not in agent1_news and n not in agent2_news:
                agent1_news.append(n)
                
        st.session_state.news_cache = {"a1": agent1_news, "a2": agent2_news, "raw_count": len(raw_news), "clean_count": len(clean_news)}

c_data = st.session_state.news_cache
st.success(f"✅ Oogst voltooid: {c_data['raw_count']} ruwe artikelen gescand, {c_data['raw_count'] - c_data['clean_count']} duplicaten verwijderd.")

tab1, tab2 = st.tabs([f"🇹🇷 Agent 1: BIST, Beleid & Justitie ({len(c_data['a1'])})", f"🌍 Agent 2: Macro, Goud & Oorlog ({len(c_data['a2'])})"])

def render_html_card(news):
    """Rendert een strakke HTML kaart zonder streamit markdown-bugs (geen scrollbalken)."""
    tags_html = "".join([f"<span class='badge badge-bist'>{t}</span>" for t in news['tags']])
    
    st.markdown(f"""
    <div class="news-card {news['sentiment']}">
        <div class="badge-bar">{tags_html}</div>
        <h4 class="news-title">{news['title']}</h4>
        <div class="news-meta">🕒 {news['datetime'].strftime('%d-%m %H:%M')} | 📰 Bron: {news['source']}</div>
        <hr>
        <div class="news-section"><strong>Wat betekent dit:</strong> {news['jip']}</div>
        <div class="news-section"><strong>Markt & Economische Impact:</strong> {news['impact']}</div>
        <div style="margin-top: 10px;">
            <a href="{news['link']}" target="_blank" style="font-size: 13px; color: #2563eb; text-decoration: none; font-weight: bold;">🔗 Lees originele bron</a>
        </div>
    </div>
    """, unsafe_allow_html=True)

with tab1:
    st.markdown("### Lokale Radar: Justitie, SPK, Aandelen & TCMB")
    
    neg_a1 = sum(1 for n in c_data['a1'] if n['sentiment'] == 'neg')
    if neg_a1 >= 3:
        st.error(f"🚨 **Lokale Markt Barometer:** Hoge stress. Er zijn {neg_a1} negatieve of justitiële berichten actief. Kans op volatiliteit in specifieke aandelen.")
    elif neg_a1 == 0:
        st.success("🟢 **Lokale Markt Barometer:** Rustige nieuwsflow, geen grote SPK of justitiële schandalen gedetecteerd.")
        
    for news in c_data['a1']:
        render_html_card(news)

with tab2:
    st.markdown("### Globale Radar: Fed, Oorlog, Goud & Zilver")
    
    neg_a2 = sum(1 for n in c_data['a2'] if n['sentiment'] == 'neg')
    warn_a2 = sum(1 for n in c_data['a2'] if n['sentiment'] == 'warn')
    
    if neg_a2 >= 2 or warn_a2 >= 3:
        st.warning(f"🔥 **Goud/Zilver Barometer:** Verhoogde geopolitieke of monetaire activiteit. Edelmetalen staan onder hoogspanning en kunnen grote bewegingen maken.")
    else:
        st.info("📊 **Goud/Zilver Barometer:** Edelmetalen reageren momenteel puur op reguliere rente- en dollardata.")
        
    for news in c_data['a2']:
        render_html_card(news)
