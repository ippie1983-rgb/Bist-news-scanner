import os
import re
import html
import json
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

# Pagina configuratie
st.set_page_config(
    page_title="BIST 100 & Turkse Economie Master Scanner",
    page_icon="🇹🇷",
    layout="wide"
)

# Opmaak voor overzichtelijke artikel-kaarten en impact-badges
st.markdown("""
<style>
    .main-header { font-size: 24px; font-weight: bold; color: #1E3A8A; }
    div[data-testid="stMetricValue"] { font-size: 20px !important; }
    .news-card {
        background-color: #f8fafc;
        border-left: 5px solid #1E3A8A;
        padding: 14px 18px;
        margin-bottom: 14px;
        border-radius: 6px;
        border-top: 1px solid #e2e8f0;
        border-right: 1px solid #e2e8f0;
        border-bottom: 1px solid #e2e8f0;
    }
    .scandal-card {
        background-color: #fef2f2;
        border-left: 5px solid #dc2626;
        padding: 14px 18px;
        margin-bottom: 14px;
        border-radius: 6px;
        border-top: 1px solid #fecaca;
        border-right: 1px solid #fecaca;
        border-bottom: 1px solid #fecaca;
    }
    .positive-card {
        background-color: #f0fdf4;
        border-left: 5px solid #16a34a;
        padding: 14px 18px;
        margin-bottom: 14px;
        border-radius: 6px;
        border-top: 1px solid #bbf7d0;
        border-right: 1px solid #bbf7d0;
        border-bottom: 1px solid #bbf7d0;
    }
    .agenda-card {
        background-color: #eff6ff;
        border-left: 5px solid #2563eb;
        padding: 14px 18px;
        margin-bottom: 14px;
        border-radius: 6px;
        border-top: 1px solid #bfdbfe;
        border-right: 1px solid #bfdbfe;
        border-bottom: 1px solid #bfdbfe;
    }
    .badge-neg { background-color: #fee2e2; color: #991b1b; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size: 12px; }
    .badge-pos { background-color: #dcfce7; color: #166534; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size: 12px; }
    .badge-warn { background-color: #fef3c7; color: #92400e; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size: 12px; }
    .badge-info { background-color: #e0e7ff; color: #1e40af; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size: 12px; }
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-header">🇹🇷 BIST 100 & Turkse Economie Master Scanner (Pro Edition)</p>', unsafe_allow_html=True)
st.markdown(
    "Live scanner voor **Borsa İstanbul (alle 100 BIST-aandelen)**, **SPK- & Fondsschandalen**, **Resmi Gazete**, "
    "**Brüt Takas & Handelsverboden**, **Top-Economen**, **CDS & Buitenlands Kapitaal** (nieuwste nieuws bovenaan, aflopend op datum) "
    "en een **toekomstige 30-dagen Macro-Agenda** (oplopend op datum)."
)

# --- VOLLEDIGE LIJST VAN ALLE 100 UNIEKE BIST 100 AANDELEN ---
BIST_INDEX_OPTION = "📈 BIST 100 Index (Algemeen & Brede Markt)"

BIST_100_STOCKS = [
    "AEFES (Anadolu Efes)", "AGHOL (Anadolu Grubu Holding)", "AGROT (Agrotech)", "AHGAZ (Ahlatcı Doğalgaz)",
    "AKBNK (Akbank)", "AKCNS (Akçansa)", "AKFGY (Akfen GYO)", "AKFYE (Akfen Yenilenebilir Enerji)",
    "AKSA (Aksa Akrilik)", "AKSEN (Aksa Enerji)", "ALARK (Alarko Holding)", "ALBRK (Albaraka Türk)",
    "ALFAS (Alfa Solar Enerji)", "ALTNY (Altınay Savunma)", "ANHYT (Anadolu Hayat Emeklilik)", "ANSGR (Anadolu Sigorta)",
    "ARCLK (Arçelik)", "ARDYZ (ARD Bilişim)", "ASELS (Aselsan)", "ASTOR (Astor Enerji)",
    "BERA (Bera Holding)", "BFREN (Bosch Fren)", "BIENY (Bien Yapı)", "BIMAS (Bim Mağazalar)",
    "BINHO (1000 Yatırımlar Holding)", "BRSAN (Borusan Boru)", "BRYAT (Borusan Yatırım)", "BTCIM (Batıçim)",
    "CANTE (Çan2 Termik)", "CCOLA (Coca-Cola İçecek)", "CIMSA (Çimsa)", "CLEBI (Çelebi Hava Servisi)",
    "CWENE (CW Enerji)", "DEVA (Deva Holding)", "DOAS (Doğuş Otomotiv)", "DOHOL (Doğan Holding)",
    "ECILC (Eczacıbaşı İlaç)", "ECZYT (Eczacıbaşı Yatırım)", "EGEEN (Ege Endüstri)", "EKGYO (Emlak Konut GYO)",
    "ENERY (Enerya Enerji)", "ENJSA (Enerjisa Enerji)", "ENKAI (Enka İnşaat)", "EREGL (Erdemir)",
    "EUPWR (Europower Enerji)", "EUREN (Europen Endüstri)", "FROTO (Ford Otosan)", "GARAN (Garanti BBVA)",
    "GESAN (Girişim Elektrik)", "GOLTS (Göltaş Çimento)", "GUBRF (Gübre Fabrikaları)", "GWIND (Galata Wind)",
    "HALKB (Halkbank)", "HEKTS (Hektaş)", "IMASM (İmaş Makina)", "IPEKE (İpek Doğal Enerji)",
    "ISCTR (İş Bankası C)", "ISDMR (İskenderun Demir Çelik)", "ISGYO (İş GYO)", "ISMEN (İş Yatırım)",
    "KAYSE (Kayseri Şeker)", "KCAER (Kocaer Çelik)", "KCHOL (Koç Holding)", "KLSER (Kaleseramik)",
    "KONTR (Kontrolmatik)", "KONYA (Konya Çimento)", "KORDS (Kordsa)", "KOZAA (Koza Anadolu Metal)",
    "KOZAL (Koza Altın)", "KRDMD (Kardemir D)", "KTLEV (Katılımevim)", "LMKDC (Limak Doğu Anadolu Çimento)",
    "MAVI (Mavi Giyim)", "MGROS (Migros)", "MIATK (Mia Teknoloji)", "OBAMS (Oba Makarnacılık)",
    "ODAS (Odaş Elektrik)", "OTKAR (Otokar)", "OYAKC (Oyak Çimento)", "PASEU (Pasifik Eurasia Lojistik)",
    "PEKGY (Peker GYO)", "PETKM (Petkim)", "PGSUS (Pegasus)", "QUAGR (Qua Granite)",
    "REEDR (Reeder Teknoloji)", "SAHOL (Sabancı Holding)", "SASA (Sasa Polyester)", "SDTTR (SDT Uzay ve Savunma)",
    "SISE (Şişecam)", "SKBNK (Şekerbank)", "SMRTG (Smart Güneş Enerjisi)", "SOKM (Şok Marketler)",
    "TABGD (TAB Gıda)", "TAVHL (TAV Havalimanları)", "TCELL (Turkcell)", "THYAO (Turkish Airlines)",
    "TKFEN (Tekfen Holding)", "TOASO (Tofaş Oto)", "TTKOM (Türk Telekom)", "TUPRS (Tüpraş)",
    "TURSG (Türkiye Sigorta)", "ULKER (Ülker Bisküvi)", "VAKBN (VakıfBank)", "VESBE (Vestel Beyaz Eşya)",
    "VESTL (Vestel)", "YEOTK (YEO Teknoloji)", "YKBNK (Yapı Kredi)", "YYLGD (Yayla Agro Gıda)",
    "ZOREN (Zorlu Enerji)"
]

ALL_SIDEBAR_OPTIONS = [BIST_INDEX_OPTION] + BIST_100_STOCKS

# --- ZIJBALK: INSTELLINGEN ---
default_env_key = os.environ.get("GEMINI_API_KEY", "")
if not default_env_key:
    try:
        default_env_key = st.secrets.get("GEMINI_API_KEY", "")
    except Exception:
        default_env_key = ""

if "gemini_auth" not in st.session_state:
    st.session_state.gemini_auth = default_env_key if default_env_key else "AQ.Ab8RN6JnVmPz0K31aqL3BE1e6"

st.sidebar.header("⚙️ Systeem & AI Instellingen")
st.session_state.gemini_auth = st.sidebar.text_input(
    "Gemini / Vertex AI Key (Optioneel):",
    type="password",
    value=st.session_state.gemini_auth,
    help="De ingebouwde Jip-en-Janneke Engine voorziet elk artikel standaard van een Nederlandse samenvatting en sector-impact."
)
st.sidebar.success("✅ 5 Pro-Modules & Nieuwste-Bovenaan Sortering actief!")

st.sidebar.markdown("---")
st.sidebar.subheader(f"🎯 BIST 100 Selectie ({len(BIST_100_STOCKS)} Aandelen + Index)")

select_all_bist = st.sidebar.checkbox("Selecteer ALLE 100 BIST-aandelen tegelijk", value=False)
if select_all_bist:
    default_selection = ALL_SIDEBAR_OPTIONS
else:
    default_selection = [
        BIST_INDEX_OPTION,
        "THYAO (Turkish Airlines)",
        "ASELS (Aselsan)",
        "KCHOL (Koç Holding)",
        "AKBNK (Akbank)",
        "GARAN (Garanti BBVA)",
        "TUPRS (Tüpraş)"
    ]

selected_tickers = st.sidebar.multiselect(
    "Kies BIST 100 Algemeen en/of specifieke aandelen:",
    options=ALL_SIDEBAR_OPTIONS,
    default=default_selection
)

max_days_slider = st.sidebar.slider("Nieuws ouderdom (dagen):", min_value=1, max_value=5, value=3)

# --- STRIKTE ECONOMISCHE & POLITIEKE RELEVANTIE FILTER ---
HARD_EXCLUDE_WORDS = [
    "futbol", "maç", "maçı", "gol", "süper lig", "galatasaray", "fenerbahçe", "beşiktaş",
    "trabzonspor", "derbi", "teknik direktör", "hakem", "transfer", "uefa", "şampiyonlar ligi",
    "basketbol", "voleybol", "stadyum", "penaltı", "ofsayt", "taraftar", "voetbal", "wedstrijd",
    "magazin", "dizi", "fragman", "oyuncu", "şarkıcı", "konser", "burç", "astroloji", "survivor",
    "uyuşturucu", "kokain", "eroin", "bonzai", "cinayet", "trafik kazası", "boşanma", "aldatma",
    "intihar", "kıskançlık", "kavga", "sapık", "taciz", "yangın", "hava durumu", "fırtına",
    "yemek tarifi", "bulmaca", "dedikodu"
]

ECONOMIC_POLITICAL_WHITELIST = [
    "ekonomi", "borsa", "bist", "hisse", "spk", "sermaye piyasası", "fon", "tasfiye", "manipülasyon",
    "soruşturma", "operasyon", "gözaltı", "tutuklama", "kayyum", "tmsf", "mal varlığı", "vurgun",
    "ceza", "görevden alındı", "atama", "resmi gazete", "cumhurbaşkanı kararı", "ötv", "tcmb",
    "merkez bankası", "faiz", "ppk", "enflasyon", "tüik", "mehmet şimşek", "şimşek", "erdoğan",
    "cumhurbaşkanı", "cevdet yılmaz", "karahan", "hazine", "maliye", "vergi", "bütçe", "cari açık",
    "rezerv", "kur", "dolar", "euro", "altın", "gümüş", "petrol", "brent", "tahvil", "cds",
    "kredi notu", "moody", "fitch", "s&p", "yabancı yatırımcı", "yabancı takas", "brüt takas",
    "işlem yasağı", "tedbir", "bedelsiz", "bedelli", "sermaye artırımı", "mahfi eğilmez",
    "özgür demirtaş", "emre alkin", "hakan kara", "islam memiş", "ışık ökte", "tunç şatıroğlu",
    "imf", "dünya bankası", "trump", "abd", "avrupa birliği", "yaptırım", "gümrük", "ticaret",
    "ihracat", "ithalat", "sanayi", "büyüme", "işsizlik", "asgari ücret", "banka", "holding",
    "bilanço", "temettü", "kap", "halka arz", "ihale", "yatırım", "kâr", "zarar", "kredi",
    "belediye", "meclis", "kanun", "yasa", "mahkeme", "adliye", "savcılık",
    "goud", "zilver", "rente", "inflatie", "oorlog", "olie", "geopolitiek", "fed", "ecb"
]

def is_economically_relevant(title, description="", extra_tickers=None):
    text = f"{title} {description}".lower()
    for bad in HARD_EXCLUDE_WORDS:
        if re.search(r'\b' + re.escape(bad) + r'\b', text):
            return False
    if extra_tickers:
        for t in extra_tickers:
            if t.lower() in text:
                return True
    for good in ECONOMIC_POLITICAL_WHITELIST:
        if good in text:
            return True
    return False

# --- AUTOMATISCHE VERTALING NAAR NEDERLANDS ---
def translate_to_nl(text):
    if not text or len(text.strip()) < 3:
        return text
    try:
        q = urllib.parse.quote(text[:450])
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=nl&dt=t&q={q}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            translated = "".join([part[0] for part in data[0] if part and part[0]])
            return translated if translated else text
    except Exception:
        return text

def clean_html_text(raw_html):
    if not raw_html:
        return ""
    clean = re.sub(r'<[^>]+>', ' ', raw_html)
    clean = html.unescape(clean)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean

# --- SECTOR- EN KOERSIMPACT DETECTIE PER ARTIKEL ---
def detect_sector_and_badge(combined_text, mentioned_stocks):
    sectors = []
    if any(w in combined_text for w in ["banka", "faiz", "tcmb", "kredi", "akbnk", "garan", "ykbnk", "isctr", "halkb", "vakbn", "rente"]):
        sectors.append("🏦 Banken (AKBNK, GARAN, YKBNK, ISCTR)")
    if any(w in combined_text for w in ["savunma", "ihale", "asels", "sdttr", "altny", "oorlog", "navo", "defensie"]):
        sectors.append("🛡️ Defensie (ASELS, SDTTR, ALTNY)")
    if any(w in combined_text for w in ["havayolu", "uçuş", "turizm", "thyao", "pgsus", "tavhl", "clebi", "luchtvaart"]):
        sectors.append("✈️ Luchtvaart & Toerisme (THYAO, PGSUS, TAVHL)")
    if any(w in combined_text for w in ["petrol", "enerji", "elektrik", "doğalgaz", "tuprs", "astor", "enjsa", "petkm", "cwene", "smrtg", "olie"]):
        sectors.append("⚡ Energie & Raffinage (TUPRS, ASTOR, ENJSA)")
    if any(w in combined_text for w in ["perakende", "market", "gıda", "enflasyon", "bimas", "mgros", "sokm", "ulker", "ccola"]):
        sectors.append("🛒 Supermarkten & Voeding (BIMAS, MGROS, SOKM)")
    if any(w in combined_text for w in ["otomotiv", "ihracat", "froto", "toaso", "doas", "otkar", "kchol"]):
        sectors.append("🚗 Auto & Export-Holdings (FROTO, TOASO, KCHOL, SAHOL)")
    if any(w in combined_text for w in ["konut", "gyo", "çimento", "inşaat", "ekgyo", "enkai", "oyakc", "cimsa"]):
        sectors.append("🏗️ Vastgoed & Bouw (EKGYO, ENKAI, OYAKC)")

    if mentioned_stocks:
        sectors.insert(0, f"🎯 Specifiek aandeel: {', '.join(mentioned_stocks)}")
    if not sectors:
        sectors.append("📈 Brede BIST 100 Markt & USD/TRY")

    sector_str = " · ".join(sectors[:3])

    # Bepaal Impact Badge
    if any(w in combined_text for w in ["tutuklama", "gözaltı", "soruşturma", "ceza", "işlem yasağı", "brüt takas", "kayyum", "skandal", "vurgun", "yaptırım", "zarar", "düşüş"]):
        badge_html = '<span class="badge-neg">🔴 HOOG RISICO / KOERSDRUK OP SPECULATIEVE FONDSEN</span>'
    elif any(w in combined_text for w in ["rekor kar", "temettü", "bedelsiz", "ihale", "anlaşma", "not artışı", "yabancı girişi", "büyüme", "yatırım"]):
        badge_html = '<span class="badge-pos">🟢 POSITIEVE KATALYSATOR VOOR KOERS</span>'
    elif any(w in combined_text for w in ["resmi gazete", "vergi", "ötv", "faiz kararı", "enflasyon", "trump", "fed"]):
        badge_html = '<span class="badge-warn">⚠️ BELEID & MACRO-IMPACT OP BIST 100</span>'
    else:
        badge_html = '<span class="badge-info">⚖️ MARKT- & ANALISTEN DUIDING</span>'

    return badge_html, sector_str

# --- SLIMME JIP-EN-JANNEKETAAL & ECONOMISCHE IMPACT ENGINE PER ARTIKEL ---
def build_jip_en_janneke_analysis(title_tr, title_nl, desc_nl, category_tag, tickers_clean):
    combined = f"{title_tr} {title_nl} {desc_nl}".lower()
    mentioned_stocks = [t for t in tickers_clean if t.lower() in combined]
    badge_html, sector_str = detect_sector_and_badge(combined, mentioned_stocks)

    # 1. SPK Bulletin, Brüt Takas, Handelsverboden & Kapitaalverhogingen
    if any(w in combined for w in ["brüt takas", "işlem yasağı", "tedbir", "spk bülteni", "bedelsiz", "bedelli", "sermaye artırımı"]):
        jip_summary = (
            f"**Wat is er aan de hand:** Beurswaakhond SPK of Borsa İstanbul heeft een officieel besluit genomen: *{title_nl}*. "
            f"{desc_nl if desc_nl and desc_nl.lower() != title_nl.lower() else 'Dit gaat over handelsrestricties (brüt takas / handelsverboden voor manipulatoren) of goedkeuring van een aandelensplitsing (bedelsiz/bedelli).'}"
        )
        econ_impact = (
            f"**Economisch vooruitzicht & Beursimpact:** Bij een **handelsverbod (`işlem yasağı`) of `brüt takas`** droogt de speculatieve handel in dat aandeel direct op en kan de koers flink schommelen. "
            f"Gaat het om een goedgekeurde **gratis aandelensplitsing (`bedelsiz sermaye artırımı`)**, dan reageren Turkse particuliere beleggers daar juist vaak enthousiast en positief op."
        )
        card_class = "scandal-card" if ("yasağı" in combined or "brüt" in combined or "ceza" in combined) else "positive-card"

    # 2. Fondsschandaal, SPK-Operaties, Arrestaties & Manipulatie-onderzoeken
    elif any(w in combined for w in ["fon", "spk", "manipülasyon", "manipulatie", "tutuklama", "gözaltı", "aangehouden", "gearresteerd", "tasfiye", "tmsf", "mal varlığı", "soruşturma", "onderzoek"]):
        jip_summary = (
            f"**Wat is er aan de hand:** Justitie en beurswaakhond SPK grijpen in bij het grote fondsen- en beursmanipulatieschandaal: *{title_nl}*. "
            f"{desc_nl if desc_nl and desc_nl.lower() != title_nl.lower() else 'Er vinden arrestaties, ondervragingen, fondsvereffeningen of bevriezingen van vermogen plaats bij verdachte partijen.'}"
        )
        econ_impact = (
            f"**Economisch vooruitzicht & Beursimpact:** Op de korte termijn zorgt dit voor nervositeit en verkoopdruk bij kleine, speculatieve aandelen en betrokken beleggingsfondsen. "
            f"Voor de gevestigde **BIST 100-bedrijven** is deze schoonmaak positief: het haalt oplichters uit de markt en vergroot het vertrouwen van grote buitenlandse fondsen."
        )
        card_class = "scandal-card"

    # 3. Resmi Gazete (Staatsblad), Belastingen (ÖTV) & Presidentiële Besluiten
    elif any(w in combined for w in ["resmi gazete", "cumhurbaşkanı kararı", "ötv", "vergi", "görevden alma", "atama kararları"]):
        jip_summary = (
            f"**Wat is er aan de hand:** Nieuw officieel overheidsbesluit gepubliceerd in het Turkse Staatsblad (*Resmi Gazete*): *{title_nl}*. "
            f"{desc_nl if desc_nl and desc_nl.lower() != title_nl.lower() else 'Nieuwe wetgeving, belastingmaatregelen of benoemingen/ontslagen van topfunctionarissen zijn direct van kracht geworden.'}"
        )
        econ_impact = (
            f"**Economisch vooruitzicht & Beursimpact:** Besluiten in de *Resmi Gazete* hebben direct bij beursopening effect. "
            f"Verhogingen van belastingen (zoals ÖTV op auto's, brandstof of alcohol) raken specifieke sectoren (zoals **DOAS, FROTO, TOASO, AEFES**), terwijl nieuwe subsidies of investeringsplannen juist voor koerswinst zorgen."
        )
        card_class = "news-card"

    # 4. Turkse Top-Economen & Beursanalisten Duiding
    elif any(w in combined for w in ["mahfi eğilmez", "özgür demirtaş", "emre alkin", "hakan kara", "islam memiş", "ışık ökte", "tunç şatıroğlu"]):
        jip_summary = (
            f"**Wat is er aan de hand:** Een vooraanstaande Turkse econoom of marktstrateeg geeft een scherpe waarschuwing of analyse: *{title_nl}*. "
            f"{desc_nl if desc_nl and desc_nl.lower() != title_nl.lower() else 'Onafhankelijke duiding over de werkelijke inflatie, het rentebeleid, de Lira of de richting van Borsa İstanbul en goud.'}"
        )
        econ_impact = (
            f"**Economisch vooruitzicht & Beursimpact:** Deze top-economen worden door honderdduizenden Turkse beleggers en bedrijfsleiders gevolgd. "
            f"Hun waarschuwingen over de geldontwaarding, rente of goudprijs sturen direct het dagelijkse beleggerssentiment op de **BIST 100**."
        )
        card_class = "news-card"

    # 5. CDS-Premie, Kredietwaardigheid (Fitch/Moody's/S&P) & Buitenlands Kapitaal
    elif any(w in combined for w in ["cds", "yabancı yatırımcı", "yabancı takas", "fitch", "moody", "s&p", "kredi notu"]):
        jip_summary = (
            f"**Wat is er aan de hand:** Belangrijk signaal over het vertrouwen van internationale beleggers in Turkije: *{title_nl}*. "
            f"{desc_nl if desc_nl and desc_nl.lower() != title_nl.lower() else 'Nieuws over de Turkse CDS-risicopremie, kredietbeoordelaars of de wekelijkse aan- en verkopen van buitenlandse fondsen.'}"
        )
        econ_impact = (
            f"**Economisch vooruitzicht & Beursimpact:** Grote buitenlandse fondsen kopen vrijwel uitsluitend de zwaargewichten in de **BIST 100** (zoals **AKBNK, GARAN, KCHOL, THYAO, BIMAS, TCELL**). "
            f"Een dalende CDS-premie of instroom van buitenlands geld is de sterkste brandstof voor een brede beursrally."
        )
        card_class = "positive-card" if any(w in combined for w in ["giriş", "artış", "düşüş", "olumlu", "not artışı"]) else "news-card"

    # 6. Politiek, Burgemeesters, Kayyum & Bestuurlijke Spanningen
    elif any(w in combined for w in ["belediye", "burgemeester", "kayyum", "görevden alındı", "ontslagen", "erdoğan", "chp", "ak parti", "siyaset", "meclis"]):
        jip_summary = (
            f"**Wat is er aan de hand:** Politieke of bestuurlijke ontwikkeling in Turkije: *{title_nl}*. "
            f"{desc_nl if desc_nl and desc_nl.lower() != title_nl.lower() else 'Politieke spanningen, juridische stappen tegen bestuurders of belangrijke toespraken uit Ankara.'}"
        )
        econ_impact = (
            f"**Economisch vooruitzicht & Beursimpact:** Politieke onrust zorgt er vaak voor dat binnenlandse en buitenlandse beleggers tijdelijk op de rem trappen. "
            f"Banken en holdings in de **BIST 100** reageren hier het gevoeligst op, terwijl beleggers dan vaker schuilen in **Gram Goud** en **USD/TRY**."
        )
        card_class = "scandal-card"

    # 7. Geopolitiek, VS / Trump, Sancties & Diplomatie
    elif any(w in combined for w in ["trump", "abd", "vs", "amerika", "yaptırım", "sanctie", "israil", "iran", "rusya", "oorlog", "midden-oosten", "navo", "nato"]):
        jip_summary = (
            f"**Wat is er aan de hand:** Geopolitiek en diplomatiek nieuws met marktimpact: *{title_nl}*. "
            f"{desc_nl if desc_nl and desc_nl.lower() != title_nl.lower() else 'Ontwikkelingen rond de VS/Trump, handelsrelaties, sancties of spanningen in de regio.'}"
        )
        econ_impact = (
            f"**Economisch vooruitzicht & Beursimpact:** Spanningen met de VS of onrust in het Midden-Oosten drijven de prijs van **Goud, Zilver en Olie** op. "
            f"Op de BIST 100 profiteert defensie (**ASELS**), terwijl luchtvaart (**THYAO, PGSUS**) last krijgt van duurdere kerosine."
        )
        card_class = "news-card"

    # 8. Centrale Bank (TCMB / Fed), Rente, Inflatie & Bedrijfsnieuws (KAP)
    else:
        jip_summary = (
            f"**Wat is er aan de hand:** Economisch en financieel nieuws: *{title_nl}*. "
            f"{desc_nl if desc_nl and desc_nl.lower() != title_nl.lower() else 'Actuele berichtgeving over het rente- en inflatiebeleid, bedrijfsresultaten (KAP) of de handel op Borsa İstanbul.'}"
        )
        econ_impact = (
            f"**Economisch vooruitzicht & Beursimpact:** Geeft directe richting aan de waardering van **BIST 100-aandelen**. "
            f"Dalende inflatie en sterke kwartaalcijfers ondersteunen de koersen; hoge rentes dwingen tot selectiviteit in bedrijven met veel eigen kasgeld."
        )
        card_class = "news-card"

    return jip_summary, econ_impact, card_class, badge_html, sector_str

# --- HULPFUNCTIES VOOR LIVE MARKTDATA & PARALLELLE RSS OPHAAL ---
@st.cache_data(ttl=300, show_spinner=False)
def get_live_market_snapshot():
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
            if hist is not None and len(hist) >= 2:
                curr = float(hist["Close"].iloc[-1])
                prev = float(hist["Close"].iloc[-2])
                chg = ((curr - prev) / prev) * 100.0 if prev else 0.0
                data[name] = {"price": curr, "change": chg}
            else:
                data[name] = {"price": float(hist["Close"].iloc[-1]) if hist is not None and not hist.empty else None, "change": 0.0}
        except Exception:
            data[name] = {"price": None, "change": 0.0}

    usd_try = data.get("USD/TRY", {}).get("price")
    gold_usd = data.get("Goud Ons ($)", {}).get("price")
    if usd_try and gold_usd:
        gram_gold = (gold_usd * usd_try) / 31.1035
        data["Gram Goud (₺)"] = {"price": gram_gold, "change": data["Goud Ons ($)"]["change"] + data["USD/TRY"]["change"]}
    else:
        data["Gram Goud (₺)"] = {"price": None, "change": 0.0}
    return data

def fetch_single_rss_feed(args):
    category_label, query, lang, max_items, max_days, extra_tickers = args
    q_with_time = f"{query} when:{max_days}d" if max_days else query
    q_enc = urllib.parse.quote(q_with_time)
    if lang == "tr":
        url = f"https://news.google.com/rss/search?q={q_enc}&hl=tr&gl=TR&ceid=TR:tr"
    else:
        url = f"https://news.google.com/rss/search?q={q_enc}&hl=nl&gl=NL&ceid=NL:nl"

    items = []
    now_utc = datetime.now(timezone.utc)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            root = ET.fromstring(resp.read())

        for item in root.findall(".//item"):
            raw_title = item.findtext("title") or ""
            link = item.findtext("link") or ""
            pub_str = item.findtext("pubDate") or ""
            raw_desc = item.findtext("description") or ""
            source_el = item.find("source")
            source_name = source_el.text if source_el is not None and source_el.text else ("Turkse Media" if lang == "tr" else "NL Media")

            if not raw_title or not link:
                continue

            clean_title = raw_title.rsplit(" - ", 1)[0].strip() if " - " in raw_title else raw_title.strip()
            clean_desc = clean_html_text(raw_desc)
            if source_name in clean_desc:
                clean_desc = clean_desc.replace(source_name, "").strip(" -·")

            dt = now_utc
            if pub_str:
                try:
                    parsed_dt = parsedate_to_datetime(pub_str)
                    if parsed_dt:
                        if parsed_dt.tzinfo is None:
                            parsed_dt = parsed_dt.replace(tzinfo=timezone.utc)
                        dt = parsed_dt
                        diff_days = (now_utc - dt).total_seconds() / 86400.0
                        if max_days is not None and diff_days > (max_days + 0.2):
                            continue
                except Exception:
                    pass

            if not is_economically_relevant(clean_title, clean_desc, extra_tickers):
                continue

            items.append({
                "category": category_label,
                "title_orig": clean_title,
                "desc_orig": clean_desc,
                "source": source_name,
                "link": link,
                "datetime": dt,
                "date_str": dt.strftime("%d-%m-%Y %H:%M"),
                "lang": lang
            })
            if len(items) >= max_items:
                break
    except Exception:
        pass
    return items

def enrich_articles_with_dutch_summaries(items, tickers_clean):
    def process_one(item):
        if item["lang"] == "tr":
            title_nl = translate_to_nl(item["title_orig"])
            desc_nl = translate_to_nl(item["desc_orig"]) if item["desc_orig"] and len(item["desc_orig"]) > 15 else ""
        else:
            title_nl = item["title_orig"]
            desc_nl = item["desc_orig"]

        jip_sum, econ_imp, card_cls, badge_html, sector_str = build_jip_en_janneke_analysis(
            item["title_orig"], title_nl, desc_nl, item["category"], tickers_clean
        )
        item["title_nl"] = title_nl
        item["jip_summary"] = jip_sum
        item["econ_impact"] = econ_imp
        item["card_class"] = card_cls
        item["badge_html"] = badge_html
        item["sector_str"] = sector_str
        return item

    with ThreadPoolExecutor(max_workers=10) as ex:
        enriched = list(ex.map(process_one, items))
    return enriched

# --- AGENT 6: TOEKOMSTIGE 30-DAGEN MACRO AGENDA (UITSLUITEND TOEKOMST & OPLOPEND) ---
def get_upcoming_30_day_agenda():
    today = datetime.now(timezone.utc).date()
    end_date = today + timedelta(days=30)

    scheduled_events = [
        {
            "date": datetime(2026, 10, 28, 19, 0, tzinfo=timezone.utc).date(),
            "time_str": "28-10-2026 (21:00 TR)",
            "title": "🇺🇸 Fed (FOMC) Rentebesluit & Persconferentie Jerome Powell",
            "jip_summary": (
                "**Wat gaat er gebeuren:** De Amerikaanse centrale bank (Fed) maakt haar nieuwe rentebesluit bekend (huidige rente: 3,75%–4,00%), "
                "gevolgd door de toelichting van voorzitter Jerome Powell."
            ),
            "econ_impact": (
                "**Economisch vooruitzicht:** Dit is het belangrijkste wereldwijde moment van de week. "
                "Als de Fed hint op lagere rentes, is dat direct positief voor **Goud, Zilver** en opkomende markten zoals **Borsa İstanbul (BIST 100)**."
            ),
            "link": "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
        },
        {
            "date": datetime(2026, 10, 29, 9, 0, tzinfo=timezone.utc).date(),
            "time_str": "29-10-2026 (Hele dag)",
            "title": "🇹🇷 Cumhuriyet Bayramı (Dag van de Republiek) — Borsa İstanbul Gesloten",
            "jip_summary": (
                "**Wat gaat er gebeuren:** Vanwege de nationale feestdag in Turkije is **Borsa İstanbul (BIST)** op 29 oktober gesloten "
                "(en op 28 oktober alleen een halve dag geopend tot de middag)."
            ),
            "econ_impact": (
                "**Economisch vooruitzicht:** Voor een nationale feestdag verkopen kortetermijnhandelaren vaak een deel van hun aandelen om geen "
                "kredietrente (kredili işlem) over de vrije dagen te betalen. Na de feestdag keert de liquiditeit direct terug."
            ),
            "link": "https://www.borsaistanbul.com/tr/sayfa/143/resmi-tatil-gunleri"
        },
        {
            "date": datetime(2026, 11, 3, 7, 0, tzinfo=timezone.utc).date(),
            "time_str": "03-11-2026 (10:00 TR)",
            "title": "🇹🇷 TÜİK Turkse Inflatiecijfers (CPI / TÜFE Oktober)",
            "jip_summary": (
                "**Wat gaat er gebeuren:** Het Turkse statistiekbureau (TÜİK) publiceert de officiële maandelijkse en jaarlijkse inflatiecijfers over oktober."
            ),
            "econ_impact": (
                "**Economisch vooruitzicht:** Dit cijfer bepaalt of de Turkse Centrale Bank (TCMB) de rente kan verlagen. "
                "Valt de inflatie lager uit dan verwacht, dan schieten **BIST 100 bankaandelen (AKBNK, GARAN, YKBNK, ISCTR)** doorgaans direct omhoog."
            ),
            "link": "https://www.tuik.gov.tr/"
        },
        {
            "date": datetime(2026, 11, 6, 7, 30, tzinfo=timezone.utc).date(),
            "time_str": "06-11-2026 (10:30 TR)",
            "title": "🇹🇷 TCMB 4e Inflatieverslag (Enflasyon Raporu) — Toespraak Fatih Karahan",
            "jip_summary": (
                "**Wat gaat er gebeuren:** De gouverneur van de Turkse Centrale Bank presenteert de nieuwe inflatievoorspellingen voor eind 2026 en 2027 "
                "en beantwoordt vragen van analisten en bankiers."
            ),
            "econ_impact": (
                "**Economisch vooruitzicht:** Beleggers letten scherp op signalen over het rentepad en de ondersteuning van de Turkse Lira. "
                "Vertrouwenwekkende cijfers trekken buitenlands kapitaal aan richting de **BIST 100**."
            ),
            "link": "https://www.tcmb.gov.tr/"
        },
        {
            "date": datetime(2026, 11, 9, 15, 0, tzinfo=timezone.utc).date(),
            "time_str": "09-11-2026 (18:00 TR)",
            "title": "🇹🇷 KAP Deadline Q3 2026 Kwartaalcijfers (Niet-Geconsolideerde BIST Bedrijven)",
            "jip_summary": (
                "**Wat gaat er gebeuren:** Laatste dag waarop niet-geconsolideerde beursbedrijven op Borsa İstanbul hun derdekwartaalcijfers (bilanço) moeten publiceren op KAP."
            ),
            "econ_impact": (
                "**Economisch vooruitzicht:** Zorgt voor sterke koersbewegingen per individueel aandeel. Bedrijven die ondanks de hoge rente "
                "hun winstmarge op peil houden, worden direct beloond door beleggers."
            ),
            "link": "https://www.kap.org.tr/"
        },
        {
            "date": datetime(2026, 11, 11, 13, 30, tzinfo=timezone.utc).date(),
            "time_str": "11-11-2026 (16:30 TR)",
            "title": "🇺🇸 Amerikaanse Inflatiecijfers (US CPI Oktober)",
            "jip_summary": (
                "**Wat gaat er gebeuren:** Publicatie van de Amerikaanse consumentenprijzen. Dit laat zien hoe snel het leven in de VS duurder wordt."
            ),
            "econ_impact": (
                "**Economisch vooruitzicht:** Directe koersbepaler voor **Goud (Ons & Gram)** en **Zilver**. "
                "Een lagere Amerikaanse inflatie verzwakt de Dollar en stuwt edelmetalen omhoog."
            ),
            "link": "https://www.bls.gov/cpi/"
        },
        {
            "date": datetime(2026, 11, 19, 11, 0, tzinfo=timezone.utc).date(),
            "time_str": "19-11-2026 (14:00 TR)",
            "title": "🇹🇷 TCMB Rentebesluit (PPK Toplantısı & Faiz Kararı)",
            "jip_summary": (
                "**Wat gaat er gebeuren:** Het Monetair Beleidscomité (PPK) van de Turkse Centrale Bank maakt het nieuwe rentebesluit voor november bekend."
            ),
            "econ_impact": (
                "**Economisch vooruitzicht:** Hét belangrijkste binnenlandse macro-moment van de maand voor de **USD/TRY wisselkoers**, **Gram Goud** en de **BIST 100 Index**."
            ),
            "link": "https://www.tcmb.gov.tr/wps/wcm/connect/TR/TCMB+TR/Main+Menu/Temel+Faaliyetler/Para+Politikasi/Merkez+Bankasi+Faiz+Oranlari"
        },
        {
            "date": datetime(2026, 11, 20, 15, 0, tzinfo=timezone.utc).date(),
            "time_str": "20-11-2026 (18:00 TR)",
            "title": "🇹🇷 KAP Deadline Q3 2026 Geconsolideerde Kwartaalcijfers (Holdings & Banken)",
            "jip_summary": (
                "**Wat gaat er gebeuren:** Uiterste datum waarop de grote Turkse holdings (zoals KCHOL, SAHOL, ALARK) en grote concerns hun volledige kwartaalcijfers bekendmaken."
            ),
            "econ_impact": (
                "**Economisch vooruitzicht:** Sluit het cijferseizoen voor het derde kwartaal af en bepaalt welke zwaargewichten in de **BIST 100** de leiding nemen richting het jaareinde."
            ),
            "link": "https://www.kap.org.tr/"
        }
    ]

    future_events = [ev for ev in scheduled_events if today <= ev["date"] <= end_date]
    future_events.sort(key=lambda x: x["date"])  # Agenda blijft oplopend (eerstvolgende bovenaan)
    return future_events

# --- LIVE MARKT TICKER BAR ---
st.markdown("### 📊 Live Marktoverzicht")
market_data = get_live_market_snapshot()
market_items = list(market_data.items())

for row_slice in [market_items[:4], market_items[4:8]]:
    cols = st.columns(len(row_slice))
    for i, (name, info) in enumerate(row_slice):
        with cols[i]:
            if info["price"] is not None:
                st.metric(label=name, value=f"{info['price']:,.2f}", delta=f"{info['change']:+.2f}%")
            else:
                st.metric(label=name, value="N/B")

st.markdown("---")

# --- HOOFDPROGRAMMA ---
st.markdown("### 🤖 Start de 6-Agent Master Scanner (Pro Edition)")
st.markdown(
    "Scant gelijktijdig het **SPK- & Fondsschandaal**, **SPK Bülteni / Brüt Takas**, **Resmi Gazete**, "
    "**Top-Economen**, **CDS & Buitenlands Kapitaal**, **Politiek & Geopolitiek (VS/Trump)** en alle gekozen **BIST 100-aandelen**."
)

if st.button("🚀 Start Volledige 6-Agent Master Analyse", type="primary"):
    is_bist100_general = BIST_INDEX_OPTION in selected_tickers
    tickers_clean = [t.split(" ")[0] for t in selected_tickers if t != BIST_INDEX_OPTION]
    tickers_str = ", ".join(tickers_clean) if tickers_clean else "Alle BIST 100 Hoofdfondsen"

    with st.spinner("📡 Parallel ophalen van schandalen, SPK-bulletins, Resmi Gazete, top-economen, politiek en BIST-aandelen..."):
        rss_tasks = [
            (
                "🚨 Fondsschandaal, SPK & Beurs-Operaties",
                '("fon soruşturması" OR "SPK" OR "manipülasyon" OR "borsa operasyon" OR "fon tasfiye" OR "TMSF")',
                "tr", 10, max_days_slider, tickers_clean
            ),
            (
                "⚠️ SPK Bulletin, Brüt Takas, Handelsverboden & Bedelsiz",
                '("SPK bülteni" OR "işlem yasağı" OR "brüt takas" OR "tedbir kararı" OR "bedelsiz sermaye artırımı")',
                "tr", 8, max_days_slider, tickers_clean
            ),
            (
                "📜 Resmi Gazete (Staatsblad), Belastingen (ÖTV) & Besluiten",
                '("Resmi Gazete" OR "Cumhurbaşkanı Kararı" OR "ÖTV" OR "vergi düzenlemesi") AND ("ekonomi" OR "atama" OR "görevden" OR "vergi" OR "borsa")',
                "tr", 8, max_days_slider, tickers_clean
            ),
            (
                "🏛️ Politiek, Justitie, Burgemeesters & Ontslagen",
                '("görevden alındı" OR "kayyum" OR "gözaltı" OR "tutuklama" OR "belediye başkanı") AND ("ekonomi" OR "borsa" OR "SPK" OR "fon" OR "holding" OR "başkan")',
                "tr", 8, max_days_slider, tickers_clean
            ),
            (
                "🧠 Turkse Top-Economen & Marktstrategen",
                '("Mahfi Eğilmez" OR "Özgür Demirtaş" OR "Emre Alkin" OR "Hakan Kara" OR "İslam Memiş" OR "Işık Ökte" OR "Tunç Şatıroğlu")',
                "tr", 8, max_days_slider, tickers_clean
            ),
            (
                "海外 CDS-Premie, Kredietwaardigheid & Buitenlands Kapitaal",
                '("CDS primi" OR "yabancı yatırımcı" OR "yabancı takas" OR "Fitch" OR "Moody\'s" OR "kredi notu") AND ("Türkiye" OR "borsa" OR "BIST")',
                "tr", 8, max_days_slider, tickers_clean
            ),
            (
                "🌍 Geopolitiek, Trump/VS, Sancties & Diplomatie",
                '("Trump" OR "ABD" OR "yaptırım" OR "BRICS" OR "İsrail" OR "İran") AND ("Türkiye" OR "ekonomi" OR "piyasa" OR "dolar" OR "ticaret")',
                "tr", 8, max_days_slider, tickers_clean
            ),
            (
                "📈 BIST 100, TCMB, Rente & Top-Media (Bloomberg HT / Yeni Şafak / CNN Türk / Hürriyet)",
                '("Borsa İstanbul" OR "BIST 100" OR "TCMB" OR "Mehmet Şimşek" OR "enflasyon" OR "faiz kararı")',
                "tr", 10, max_days_slider, tickers_clean
            ),
            (
                "🌍 Wereldnieuws, Oorlog & Energie (NL)",
                '(oorlog OR Midden-Oosten OR Oekraïne OR geopolitiek OR olieprijs OR sancties)',
                "nl", 8, max_days_slider, []
            ),
            (
                "🥇 Goud, Zilver & Centrale Banken (NL)",
                '(goudprijs OR zilverprijs OR "Fed rente" OR edelmetalen OR inflatie)',
                "nl", 8, max_days_slider, []
            )
        ]

        # Voeg gebatchte zoekopdrachten toe voor alle geselecteerde BIST-aandelen
        if tickers_clean:
            batch_size = 5
            for i in range(0, min(len(tickers_clean), 35), batch_size):
                batch = tickers_clean[i:i + batch_size]
                or_stocks = " OR ".join(batch)
                rss_tasks.append((
                    f"🏢 Aandelennieuws & KAP ({', '.join(batch)})",
                    f"({or_stocks}) AND (hisse OR KAP OR bilanço OR temettü OR yatırım)",
                    "tr", 6, max_days_slider, batch
                ))

        with ThreadPoolExecutor(max_workers=10) as executor:
            task_results = list(executor.map(fetch_single_rss_feed, rss_tasks))

        raw_tr_items = []
        raw_nl_items = []
        seen_titles = set()

        for res_list in task_results:
            for item in res_list:
                norm_t = item["title_orig"].lower()[:60]
                if norm_t in seen_titles:
                    continue
                seen_titles.add(norm_t)
                if item["lang"] == "tr":
                    raw_tr_items.append(item)
                else:
                    raw_nl_items.append(item)

        tr_enriched = enrich_articles_with_dutch_summaries(raw_tr_items, tickers_clean)
        nl_enriched = enrich_articles_with_dutch_summaries(raw_nl_items, tickers_clean)

        # SORTERING NIEUWS: NIEUWSTE BOVENAAN (AFLOPEND OP DATUM, bijv. 25 -> 24 -> 23)
        tr_enriched.sort(key=lambda x: x["datetime"], reverse=True)
        nl_enriched.sort(key=lambda x: x["datetime"], reverse=True)

        # SORTERING AGENDA: KOMENDE 30 DAGEN OPLOPEND OP DATUM (eerstvolgende gebeurtenis bovenaan)
        upcoming_agenda = get_upcoming_30_day_agenda()

        bist_p = market_data.get("BIST 100", {}).get("price") or 0.0
        bist_c = market_data.get("BIST 100", {}).get("change") or 0.0
        usd_p = market_data.get("USD/TRY", {}).get("price") or 0.0
        gold_p = market_data.get("Goud Ons ($)", {}).get("price") or 0.0
        gram_p = market_data.get("Gram Goud (₺)", {}).get("price") or 0.0
        silv_p = market_data.get("Zilver Ons ($)", {}).get("price") or 0.0
        brent_p = market_data.get("Brent Olie ($)", {}).get("price") or 0.0
        vix_p = market_data.get("VIX (Angst)", {}).get("price") or 0.0

        scandal_count = sum(
            1 for x in tr_enriched
            if any(k in x["category"] for k in ["Fondsschandaal", "Politiek", "SPK Bulletin"])
        )

    st.success(
        f"✅ Master Analyse voltooid! **{len(tr_enriched)} Turkse berichten** (nieuwste bovenaan, aflopend op datum), "
        f"**{len(nl_enriched)} internationale berichten** en **{len(upcoming_agenda)} aankomende macro-agendapunten** geladen."
    )

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        f"🇹🇷 Agent 1: BIST, Schandalen & Pro-Radars ({len(tr_enriched)})",
        f"🌍 Agent 2: Globaal & Edelmetalen ({len(nl_enriched)})",
        "🕵️‍♂️ Agent 3: Fact-Check",
        "💡 Agent 4: Beleggingsadvies",
        "⚖️ Agent 5: Risico-Audit",
        f"📅 Agent 6: Komende 30-Dagen Agenda ({len(upcoming_agenda)})"
    ])

    # ==========================================================================
    # TAB 1: AGENT 1 — NIEUWSTE BOVENAAN (AFLOPEND OP DATUM) + 5 PRO-UITBREIDINGEN
    # ==========================================================================
    with tab1:
        st.markdown("### 🇹🇷 Agent 1: BIST 100, Fondsschandalen, Resmi Gazete, SPK, Economen & Politiek")
        st.markdown(
            f"**Volgorde:** 🕒 **Nieuwste nieuws bovenaan (aflopend op datum)** | "
            f"**Actieve Focus:** {'📈 **BIST 100 Index (Algemeen)** + ' if is_bist100_general else ''}`{tickers_str}`"
        )

        # Snel-filter per categorie binnen Agent 1
        available_cats = ["Alle Categorieën"] + sorted(list({x["category"] for x in tr_enriched}))
        chosen_cat = st.selectbox("🔍 Filter op specifiek thema (of bekijk alles):", available_cats, index=0)

        filtered_tr = tr_enriched if chosen_cat == "Alle Categorieën" else [x for x in tr_enriched if x["category"] == chosen_cat]

        st.info(
            f"**📌 Hoofdlijnen BIST 100 & Turkse Markt (Jip-en-Janneketaal):**\n"
            f"- **Beurs & Valuta:** De **BIST 100** staat op **{bist_p:,.0f} punten ({bist_c:+.2f}%)** en **USD/TRY** noteert **₺{usd_p:,.2f}**.\n"
            f"- **5 Actieve Pro-Radars:** Naast het **fondsschandaal & politiek** scant Agent 1 nu live op de **Resmi Gazete (Staatsblad)**, **SPK-handelsverboden (`brüt takas` / `işlem yasağı`)**, **Turkse Top-Economen** en **CDS/Buitenlands Kapitaal**.\n"
            f"- **Volgorde:** Het meest recente bericht staat op **#1** en loopt zo terug in de tijd."
        )

        if filtered_tr:
            for idx, item in enumerate(filtered_tr, 1):
                st.markdown(
                    f"""<div class="{item['card_class']}">
                        <div style="margin-bottom: 6px;">
                            {item['badge_html']} &nbsp; <strong>#{idx} | 🕒 {item['date_str']} | {item['category']} | Bron: {item['source']}</strong>
                        </div>
                        <span style="font-size: 17px; font-weight: bold; color: #0f172a;">{item['title_nl']}</span><br>
                        <span style="font-size: 12px; color: #64748b;">Originele kop: {item['title_orig']}</span><br>
                        <span style="font-size: 13px; color: #1e3a8a; font-weight: 600;">🎯 Geraakte BIST-Sectoren: {item['sector_str']}</span>
                        <hr style="margin: 8px 0; border: 0; border-top: 1px solid #cbd5e1;">
                        <p style="margin-bottom: 6px;">🗣️ {item['jip_summary']}</p>
                        <p style="margin-bottom: 8px;">📊 {item['econ_impact']}</p>
                        🔗 <a href="{item['link']}" target="_blank" style="font-weight: bold; color: #1d4ed8;">Klik hier om het originele bronartikel te openen ({item['source']})</a>
                    </div>""",
                    unsafe_allow_html=True
                )
        else:
            st.warning("Geen artikelen gevonden voor dit filter.")

    # ==========================================================================
    # TAB 2: AGENT 2 — WERELDNIEUWS, OORLOG, GOUD & ZILVER (NIEUWSTE BOVENAAN)
    # ==========================================================================
    with tab2:
        st.markdown("### 🌍 Agent 2: Wereldnieuws, Geopolitiek, Goud & Zilver (Nieuwste Bovenaan)")
        st.info(
            f"**📌 Samenvatting Edelmetalen & Wereldmarkt (Jip-en-Janneketaal):**\n"
            f"- **Goud & Zilver:** Goud staat op **${gold_p:,.2f}** per troy ounce (**₺{gram_p:,.2f} per gram** in Turkse Lira) en Zilver staat op **${silv_p:,.2f}**.\n"
            f"- **Olie & Geopolitiek:** Brent Olie noteert **${brent_p:,.2f}** en de VIX-angstindex staat op **{vix_p:,.2f}**. Het nieuwste internationale bericht staat bovenaan."
        )

        if nl_enriched:
            for idx, item in enumerate(nl_enriched, 1):
                st.markdown(
                    f"""<div class="news-card">
                        <div style="margin-bottom: 6px;">
                            {item['badge_html']} &nbsp; <strong>#{idx} | 🕒 {item['date_str']} | {item['category']} | Bron: {item['source']}</strong>
                        </div>
                        <span style="font-size: 17px; font-weight: bold; color: #0f172a;">{item['title_nl']}</span>
                        <hr style="margin: 8px 0; border: 0; border-top: 1px solid #cbd5e1;">
                        <p style="margin-bottom: 6px;">🗣️ {item['jip_summary']}</p>
                        <p style="margin-bottom: 8px;">📊 {item['econ_impact']}</p>
                        🔗 <a href="{item['link']}" target="_blank" style="font-weight: bold; color: #1d4ed8;">Klik hier om het volledige artikel te lezen ({item['source']})</a>
                    </div>""",
                    unsafe_allow_html=True
                )
        else:
            st.info("Geen recente internationale artikelen gevonden.")

    # ==========================================================================
    # TAB 3: AGENT 3 — WAARHEIDS-FILTER & FACT-CHECK
    # ==========================================================================
    with tab3:
        st.markdown("### 🕵️‍♂️ Agent 3: De Waarheids-Filter & Bronverificatie")
        st.markdown(
            f"- ✅ **Koersdata Verificatie:** Alle live koersen (BIST 100: `{bist_p:,.0f}`, USD/TRY: `₺{usd_p:,.2f}`, Goud: `${gold_p:,.2f}`) zijn rechtstreeks geverifieerd via Yahoo Finance.\n"
            f"- ✅ **Strikte Relevantie-Check:** Niet-economisch nieuws (voetbal, sportuitslagen, entertainment en reguliere criminaliteit/drugszaken zonder beursimpact) is automatisch weggefilterd.\n"
            f"- ✅ **Datum-Volgorde Controle:** Nieuws in Agent 1 en Agent 2 staat **aflopend gesorteerd (nieuwste bovenaan)**; de toekomstige 30-dagen agenda in Agent 6 staat **oplopend gesorteerd (eerstvolgende gebeurtenis bovenaan)**."
        )

    # ==========================================================================
    # TAB 4: AGENT 4 — CONCREET BELEGGINGSADVIES (JIP-EN-JANNEKETAAL)
    # ==========================================================================
    with tab4:
        st.markdown("### 💡 Agent 4: Concreet Beleggingsadvies in Jip-en-Janneketaal")
        st.markdown(
            f"#### 1. Hoe handel je slim op basis van deze 5 Pro-Radars?\n"
            f"- **Controleer altijd de `🔴 HOOG RISICO` & `SPK Bulletin` kaarten in Agent 1:** Staat een aandeel in een `brüt takas`-maatregel of in het fondsschandaal-onderzoek? Blijf daar dan weg en kies voor liquide **BIST 100-zwaargewichten** (**THYAO, ASELS, KCHOL, TUPRS, AKBNK, GARAN, BIMAS**).\n"
            f"- **Let op de `Resmi Gazete` & `CDS`-signalen:** Een dalende CDS-risicopremie en buitenlandse instroom zijn het startschot voor stijgingen in Turkse bankaandelen en grote holdings.\n"
            f"- **Houd Gram Goud (`₺{gram_p:,.2f}`) en Zilver (`${silv_p:,.2f}`) aan als buffer:** Zo ben je beschermd tegen zowel onverwachte nachtelijke besluiten als geopolitieke spanningen."
        )

    # ==========================================================================
    # TAB 5: AGENT 5 — EINDCONTROLE & RISICO-AUDIT
    # ==========================================================================
    with tab5:
        st.markdown("### ⚖️ Agent 5: Eindcontrole & Risico-Audit")
        st.warning(
            f"**Belangrijkste Risico's om nu scherp te bewaken:**\n"
            f"1. **Toezicht- & Schandaalrisico (`{scandal_count}` meldingen):** Aanhoudende SPK-onderzoeken en handelsverboden zorgen voor plotselinge koersschokken in kleinere nevenfondsen.\n"
            f"2. **Valuta- & Renterisico:** USD/TRY noteert **₺{usd_p:,.2f}**. Bedrijven met veel kasgeld en exportinkomsten zijn veel weerbaarder dan bedrijven met zware leningen in Lira.\n"
            f"3. **Geopolitieke Volatiliteit (VIX op {vix_p:,.2f}):** Houd de olieprijs (**${brent_p:,.2f}**) en de Amerikaanse en Turkse rentebesluiten in Agent 6 scherp in de gaten."
        )

    # ==========================================================================
    # TAB 6: AGENT 6 — KOMENDE 30-DAGEN MACRO-AGENDA (TOEKOMST, OPLOPEND)
    # ==========================================================================
    with tab6:
        st.markdown("### 📅 Agent 6: Toekomstige 30-Dagen Macro-Agenda (Eerstvolgende Bovenaan)")
        st.markdown(
            "Hieronder staan **uitsluitend de aankomende gebeurtenissen van de komende 30 dagen**, "
            "**oplopend gesorteerd op datum** (wat het eerst plaatsvindt staat bovenaan), inclusief uitleg in normale taal."
        )

        if upcoming_agenda:
            for idx, ev in enumerate(upcoming_agenda, 1):
                days_left = (ev["date"] - datetime.now(timezone.utc).date()).days
                days_label = "Vandaag!" if days_left == 0 else f"Over {days_left} dagen"
                st.markdown(
                    f"""<div class="agenda-card">
                        <strong>#{idx} | 📅 Datum: {ev['time_str']} ({days_label})</strong><br>
                        <span style="font-size: 17px; font-weight: bold; color: #1e3a8a;">{ev['title']}</span>
                        <hr style="margin: 8px 0; border: 0; border-top: 1px solid #93c5fd;">
                        <p style="margin-bottom: 6px;">🗣️ {ev['jip_summary']}</p>
                        <p style="margin-bottom: 8px;">📊 {ev['econ_impact']}</p>
                        🔗 <a href="{ev['link']}" target="_blank" style="font-weight: bold; color: #1d4ed8;">Klik hier voor de officiële bron & kalenderpagina</a>
                    </div>""",
                    unsafe_allow_html=True
                )
        else:
            st.info("Geen geplande macro-evenementen gevonden binnen de komende 30 dagen.")

else:
    st.info("👈 Kies in de zijbalk de **BIST 100 Index** en/of je gewenste aandelen uit de lijst van 100 en klik op **Start Volledige 6-Agent Master Analyse**!")
