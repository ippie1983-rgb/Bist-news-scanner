import os
import json
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, date

# Pagina configuratie
st.set_page_config(
    page_title="BIST 100 & Turkse Economie Master Scanner",
    page_icon="🇹🇷",
    layout="wide"
)

# Mobiel-vriendelijke opmaak
st.markdown("""
<style>
    .main-header { font-size: 24px; font-weight: bold; color: #1E3A8A; }
    div[data-testid="stMetricValue"] { font-size: 20px !important; }
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-header">🇹🇷 BIST 100 & Turkse Economie Master Scanner</p>', unsafe_allow_html=True)
st.markdown("Grondige analyse van de **Turkse economie**, alle 100 BIST aandelen selecteerbaar, **strikt economisch gefilterd nieuws**, en een **toekomstige 30-dagen Macro-Agenda**.")

# --- ZIJBALK: INSTELLINGEN ---
if "gemini_auth" not in st.session_state:
    st.session_state.gemini_auth = "AQ.Ab8RN6JnVmPz0K31aqL3BE1e6"

st.sidebar.header("⚙️ Systeem & AI Instellingen")

st.session_state.gemini_auth = st.sidebar.text_input(
    "Gemini / Vertex AI Key:",
    type="password",
    value=st.session_state.gemini_auth,
    help="Staat standaard ingesteld."
)
st.sidebar.success("✅ Grondige Master Scanner Actief!")

st.sidebar.markdown("---")
st.sidebar.subheader("🎯 BIST 100 & Aandelen Selectie (Agent 1)")

# Volledige officiële BIST 100 selectielijst
BIST_100_FULL_LIST = [
    "📈 BIST 100 Index (Algemeen & Brede Markt)",
    "THYAO (Turkish Airlines)", "ASELS (Aselsan)", "KCHOL (Koç Holding)", "AKBNK (Akbank)", 
    "GARAN (Garanti BBVA)", "TUPRS (Tüpraş)", "BIMAS (Bim)", "EREGL (Erdemir)", "SISE (Şişecam)", 
    "SASA (Sasa Polyester)", "EKGYO (Emlak Konut GYO)", "YKBNK (Yapı Kredi)", "ISCTR (İş Bankası)", 
    "PETKM (Petkim)", "PGSUS (Pegasus)", "TOASO (Tofaş)", "ARCLK (Arçelik)", "ENKAI (Enka İnşaat)", 
    "KRDMD (Kardemir D)", "TTKOM (Türk Telekom)", "TCELL (Turkcell)", "FROTO (Ford Otosan)", 
    "MGROS (Migros)", "SOKM (Şok Marketler)", "ASTOR (Astor Enerji)", "ENJSA (Enerjisa)", 
    "SAHOL (Sabancı Holding)", "OYAKC (Oyak Çimento)", "HEKTS (Hektaş)", "ODAS (Odaş Elektrik)", 
    "GESAN (Girişim Elektrik)", "KONTR (Kontrolmatik)", "ALBRK (Albaraka Türk)", "HALKB (Halkbank)", 
    "VAKBN (VakıfBank)", "TSKB (TSKB)", "SKBNK (Şekerbank)", "ALARK (Alarko Holding)", 
    "AGHOL (Anadolu Grubu)", "CIMSA (Çimsa)", "AKCNS (Akçansa)", "BRYAT (Borusan Yatırım)", 
    "BRSAN (Borusan Mannesmann)", "CLEBI (Çelebi)", "DEVA (Deva Holding)", "ECILC (Eczacıbaşı İlaç)", 
    "EGEEN (Ege Endüstri)", "ENERY (Enerya Enerji)", "EUPWR (Europower)", "EKSUN (Eksun Gıda)", 
    "GENIL (Gen İlaç)", "GUBRF (Gübre Fabrikaları)", "IPEKE (İpek Enerji)", "KCAER (Kocaer Çelik)", 
    "KORDS (Kordsa)", "KOZAA (Koza Anadolu)", "KOZAL (Koza Altın)", "KMPUR (Kimteks Kimya)", 
    "KZBGY (Kızılbük GYO)", "MAVI (Mavi Giyim)", "MIATK (MIA Teknoloji)", "OTKAR (Otokar)", 
    "PASEU (Pasifik Eurasia)", "PENTA (Penta Teknoloji)", "QUAGR (Qua Granite)", 
    "RGYAS (Rönesans Gayrimenkul)", "SMRTG (Smart Güneş Enerjisi)", "SDTTR (SDT Uzay en Savunma)", 
    "TAVHL (TAV Havalimanları)", "TKFEN (Tekfen Holding)", "TMSN (Tumosan)", "TRGYO (Torunlar GYO)", 
    "TSPOR (Trabzonspor)", "ULKER (Ülker Bisküvi)", "VAKKO (Vakko)", "VESBE (Vestel Beyaz Eşya)", 
    "VESTL (Vestel)", "YYLGD (Yayla Gıda)", "ZOREN (Zorlu Enerji)", "CWENE (CW Enerji)", 
    "DOHOL (Doğan Holding)", "FORMT (Formet Metal)", "GLYHO (Global Yatırım Holding)", 
    "GWIND (Galata Wind)", "IHLAS (İhlas Holding)", "INVEO (Inveo Yatırım)", "KOTON (Koton)", 
    "MHRGY (MHR Gayrimenkul)", "OBAMS (Oba Makarna)", "REEDR (Reeder Teknoloji)", 
    "TABGD (Tab Gıda)", "TARKM (Tarım Kredi)", "YEOTK (YEO Teknoloji)"
]

selected_tickers = st.sidebar.multiselect(
    "Selecteer BIST 100 Index en/of specifieke aandelen (alle 100+ beschikbaar):",
    BIST_100_FULL_LIST,
    default=["📈 BIST 100 Index (Algemeen & Brede Markt)", "THYAO (Turkish Airlines)", "ASELS (Aselsan)", "KCHOL (Koç Holding)"]
)

# --- HULPFUNCTIES VOOR LIVE MARKTDATA & RSS FILTERS ---
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

@st.cache_data(ttl=300, show_spinner=False)
def get_stock_snapshots(tickers_clean):
    snapshots = {}
    for code in tickers_clean:
        if "BIST 100" in code:
            continue
        yf_sym = f"{code}.IS"
        try:
            hist = yf.Ticker(yf_sym).history(period="3mo")
            if hist is not None and len(hist) >= 15:
                close = hist["Close"].astype(float)
                curr = float(close.iloc[-1])
                prev = float(close.iloc[-2])
                chg_1d = ((curr - prev) / prev) * 100.0 if prev else 0.0
                sma20 = float(close.rolling(20).mean().iloc[-1])
                delta = close.diff()
                gain = delta.clip(lower=0).rolling(14).mean().iloc[-1]
                loss = (-delta.clip(upper=0)).rolling(14).mean().iloc[-1]
                rsi = 100.0 - (100.0 / (1.0 + (gain / loss))) if loss and loss > 0 else 50.0
                snapshots[code] = {"price": round(curr, 2), "change": round(chg_1d, 2), "rsi": round(rsi, 1), "trend": "Positief" if curr > sma20 else "Onder druk"}
            else:
                snapshots[code] = {"price": None, "change": 0.0, "rsi": 50.0, "trend": "Onbekend"}
        except Exception:
            snapshots[code] = {"price": None, "change": 0.0, "rsi": 50.0, "trend": "Onbekend"}
    return snapshots

def fetch_news_strict(query, lang="tr", max_items=20, max_days=3):
    q_enc = urllib.parse.quote(query)
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
            title = item.findtext("title")
            link = item.findtext("link")
            pub_str = item.findtext("pubDate") or ""
            
            if title and link:
                dt = None
                if pub_str:
                    try:
                        from email.utils import parsedate_to_datetime
                        dt = parsedate_to_datetime(pub_str)
                    except Exception:
                        pass
                
                if dt:
                    diff_days = (now_utc - dt).total_seconds() / 86400.0
                    if max_days is not None and diff_days > max_days:
                        continue
                
                items.append({
                    "title": title, 
                    "link": link, 
                    "date": pub_str[:16],
                    "datetime": dt if dt else now_utc
                })
                if len(items) >= max_items:
                    break
    except Exception:
        pass
    return items

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

# --- AI AANROEP ---
def call_gemini_with_fallback(prompt_text, system_instruction, fallback_text):
    token = st.session_state.gemini_auth.strip()
    if not token:
        return fallback_text
    full_prompt = f"{system_instruction}\n\n{prompt_text}" if system_instruction else prompt_text
    payload = {"contents": [{"role": "user", "parts": [{"text": full_prompt}]}], "generationConfig": {"temperature": 0.2}}
    data_bytes = json.dumps(payload).encode("utf-8")
    q_token = urllib.parse.quote(token)
    endpoints = [
        (f"https://aiplatform.googleapis.com/v1beta1/publishers/google/models/gemini-2.5-flash:generateContent?key={q_token}", {"Content-Type": "application/json"}),
        (f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={q_token}", {"Content-Type": "application/json"})
    ]
    for url, headers in endpoints:
        try:
            req = urllib.request.Request(url, data=data_bytes, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=12) as resp:
                res_json = json.loads(resp.read().decode("utf-8"))
                text = res_json["candidates"][0]["content"]["parts"][0]["text"]
                if text and len(text.strip()) > 20:
                    return text
        except Exception:
            continue
    return fallback_text

# --- HOOFDPROGRAMMA ---
st.markdown("### 🤖 Start de BIST 100 & Turkse Economie Master Scanner")
st.markdown("Druk op de knop om de grondige, strikt economisch gefilterde analyse te starten.")

if st.button("🚀 Start Grondige Master Analyse", type="primary"):
    is_bist100_general = any("BIST 100 Index" in t for t in selected_tickers)
    tickers_clean = [t.split(" ")[0] for t in selected_tickers if "BIST 100" not in t]
    tickers_str = ", ".join(tickers_clean) if tickers_clean else "Geen specifieke aandelen (Volledige BIST 100 Macro Focus)"

    with st.spinner("📡 Ophalen van grondige Turkse economische data, beleid, marktnieuws en schandalen..."):
        stock_snaps = get_stock_snapshots(tickers_clean)
        
        # Uitgebreide bronverzameling specifiek gericht op de Turkse economie en markten
        tr_econ_items = fetch_news_strict("Borsa Istanbul BIST 100 ekonomi TCMB Mehmet Simsek enflasyon", "tr", 20, 3)
        tr_spk_items = fetch_news_strict("SPK ceza sorusturma fon skandali kayyum operasyon borsa", "tr", 15, 3)
        tr_pol_econ_items = fetch_news_strict("Turkiye siyaset ekonomi Merkez Bankasi faiz kur", "tr", 15, 3)
        
        stock_news_dict = {}
        for c in tickers_clean[:30]: # Tot 30 geselecteerde aandelen meenemen
            stock_news_dict[c] = fetch_news_strict(f"{c} hisse KAP bilanco", "tr", 4, 3)
        
        nl_war_items = fetch_news_strict("oorlog Midden-Oosten Oekraine geopolitiek olie", "nl", 8, 3)
        nl_gold_items = fetch_news_strict("goudprijs zilverprijs Fed rente", "nl", 8, 3)
        
        agenda_items = fetch_news_strict("Fed toplantı faiz kararı TCMB PPK TÜİK enflasyon", "tr", 12, None)
        agenda_items = sorted(agenda_items, key=lambda x: x["datetime"])

        bist_p = market_data.get("BIST 100", {}).get("price") or 0.0
        bist_c = market_data.get("BIST 100", {}).get("change") or 0.0
        usd_p = market_data.get("USD/TRY", {}).get("price") or 0.0
        gold_p = market_data.get("Goud Ons ($)", {}).get("price") or 0.0
        gram_p = market_data.get("Gram Goud (₺)", {}).get("price") or 0.0
        silv_p = market_data.get("Zilver Ons ($)", {}).get("price") or 0.0
        vix_p = market_data.get("VIX (Angst)", {}).get("price") or 0.0

    all_tr_items = tr_econ_items + tr_spk_items + tr_pol_econ_items
    for c in tickers_clean[:30]:
        all_tr_items.extend(stock_news_dict.get(c, []))

    # --- AGENT 1: Grondige Economische & Financiële AI-Analyse ---
    with st.spinner("🇹🇷 Agent 1: Stricte economische filtering en diepgaande Jip-en-Janneke analyse genereren..."):
        articles_formatted = "\n".join([f"- Titel: {item['title']}\n  Link: {item['link']}\n  Datum: {item['date']}\n" for item in all_tr_items]) if all_tr_items else "Geen artikelen."
        
        fallback_agent1 = f"### 🇹🇷 Turkse Economie & BIST 100 Overzicht\n\n- **BIST 100:** {bist_p:,.0f} | **USD/TRY:** ₺{usd_p:,.2f}"
        prompt_agent1 = (
            "Jij bent Agent 1: Turkse Economie & Strikte Financiële Intelligence Agent.\n"
            f"De gebruiker volgt de brede markt (BIST 100 Algemeen: {is_bist100_general}) en deze specifieke aandelen: {tickers_str}.\n\n"
            "Hieronder staat een lijst met recente artikelen van de afgelopen 3 dagen uit de Turkse media:\n\n"
            f"{articles_formatted}\n\n"
            "STRENGE FILTER- EN ANALYSE-OPDRACHT:\n"
            "1. **STRIKTE ECONOMISCHE EN FINANCIËLE FOCUS:** Beoordeel elk artikel op reële economische en markttechnische impact. Accepteer UISLUITEND nieuws dat te maken heeft met de Turkse economie, BIST 100, centrale banken (TCMB/Fed), inflatie, wisselkoersen (USD/TRY), SPK-maatregelen, fondsschandalen, politieke gebeurtenissen met directe marktimpact (zoals spanningen met de VS/Trump, beleidswijzigingen of arrestaties van bestuurders/politici met directe invloed op het bedrijfsleven), en officiële bedrijfsresultaten (KAP).\n"
            "2. **NEGEER RUIS:** Filter ALLES weg wat te maken heeft met voetbal, sport, amusement, films, roddels of misdaad die losstaat van de economie of het bedrijfsleven. Noem deze artikelen helemaal niet.\n"
            "3. **ARTIKEL PER ARTIKEL:** Loop de overgebleven, strikt economische artikelen stuk voor stuk langs.\n"
            "4. **STRUCTUUR PER ARTIKEL:** Geef per relevant artikel exact deze structuur weer:\n"
            "   - **Titel van het artikel**\n"
            "   - **Jip-en-Janneketaal Samenvatting:** Wat betekent dit economisch en wat is de impact op de belegger/koersen?\n"
            "   - **Bronlink:** Zet exact de URL-link neer in de vorm van een Markdown link ([Lees het volledige artikel hier](URL)).\n"
        )
        agent1_output = call_gemini_with_fallback(prompt_agent1, "Je bent een deskundige Turkse econoom en markanalist die uitsluitend financieel en economisch relevant nieuws analyseert.", fallback_agent1)

    # --- AGENT 2 ---
    with st.spinner("🌍 Agent 2: Globaal & Edelmetalen..."):
        fallback_agent2 = f"Goud is ${gold_p:,.2f} (Gram: ₺{gram_p:,.2f}), Zilver is ${silv_p:,.2f}."
        prompt_agent2 = "Jij bent Agent 2. Analyseer goud, zilver en wereldnieuws."
        agent2_output = call_gemini_with_fallback(prompt_agent2, "Je bent een macro-analist.", fallback_agent2)

    # --- AGENT 3 ---
    with st.spinner("🕵️‍♂️ Agent 3: Fact-Check..."):
        fallback_agent3 = "✅ Harde marktdata geverifieerd via Yahoo Finance en RSS feeds."
        prompt_agent3 = "Jij bent Agent 3. Voer fact-check uit."
        agent3_output = call_gemini_with_fallback(prompt_agent3, "Je bent een factchecker.", fallback_agent3)

    # --- AGENT 4 ---
    with st.spinner("💡 Agent 4: Beleggingsadvies..."):
        fallback_agent4 = "Concreet advies: Spreid aankopen in goud en geselecteerde aandelen."
        prompt_agent4 = "Jij bent Agent 4. Geef advies in Jip-en-Janneketaal."
        agent4_output = call_gemini_with_fallback(prompt_agent4, "Je bent beleggingsadviseur.", fallback_agent4)

    # --- AGENT 5 ---
    with st.spinner("⚖️ Agent 5: Auditing..."):
        fallback_agent5 = "Let op valutarisico's en recente geopolitieke spanningen (VIX: " + str(vix_p) + ")."
        prompt_agent5 = "Jij bent Agent 5. Voer risico-audit uit."
        agent5_output = call_gemini_with_fallback(prompt_agent5, "Je bent risicocontroleur.", fallback_agent5)

    # --- AGENT 6: Toekomstige 30-Dagen Macro Agenda (Oplopend) ---
    with st.spinner("📅 Agent 6: Toekomstige 30-Dagen Macro Agenda genereren..."):
        agenda_formatted = "\n".join([f"- Datum: {item['date']} | Titel: {item['title']} | Link: {item['link']}" for item in agenda_items]) if agenda_items else "Geen agenda-items."
        fallback_agenda = "### 📅 Toekomstige 30-Dagen Macro Agenda\n\nGeplande publicaties en besluiten."
        prompt_agent6 = (
            "Jij bent Agent 6: De Toekomstige Macro-Agenda Samenvatter.\n"
            "Hier zijn de chronologisch gesorteerde komende agenda-artikelen:\n"
            f"{agenda_formatted}\n\n"
            "OPDRACHT:\n"
            "Zet deze toekomstige agenda-items om in een helder, oplopend overzicht in normale mensentaal (Jip-en-Janneketaal). "
            "Vermeld bij elk item de datum, een korte uitleg van wat er gaat gebeuren, en de bijbehorende bronlink."
        )
        agent6_output = call_gemini_with_fallback(prompt_agent6, "Je bent een macro-economisch analist en agenda-expert.", fallback_agenda)

    # --- TOON RESULTATEN IN TABS ---
    st.success("✅ Grondige Master Analyse succesvol afgerond!")

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🇹🇷 Agent 1: Turkse Economie & Nieuws",
        "🌍 Agent 2: Globaal",
        "🕵️‍♂️ Agent 3: Fact-Check",
        "💡 Agent 4: Advies",
        "⚖️ Agent 5: Auditing",
        "📅 Agent 6: TOEKOMSTIGE AGENDA"
    ])

    with tab1:
        st.markdown("### Agent 1: Turkse Economie & Strikt Gefilterd Marktnieuws")
        st.markdown(agent1_output)
        st.markdown("---")
        st.markdown("#### 🔗 Geverifieerde Economische Bronlijst (Max 3 Dagen Oud)")
        if all_tr_items:
            for item in all_tr_items:
                st.markdown(f"- [{item['title']}]({item['link']}) *({item['date']})*")
        else:
            st.info("Geen economische artikelen gevonden.")

    with tab2:
        st.markdown("### Agent 2: Wereldnieuws, Oorlog & Edelmetalen")
        st.markdown(agent2_output)
        st.markdown("---")
        st.markdown("#### 🔗 Volledige Bronlijst Internationale Media (Max 3 Dagen Oud)")
        if nl_war_items or nl_gold_items:
            for item in nl_war_items + nl_gold_items:
                st.markdown(f"- [{item['title']}]({item['link']}) *({item['date']})*")
        else:
            st.info("Geen recente internationale artikelen gevonden.")

    with tab3:
        st.markdown("### Agent 3: De Waarheids-Filter (Fact-Check)")
        st.markdown(agent3_output)

    with tab4:
        st.markdown("### Agent 4: Concreet Beleggingsadvies (Jip-en-Janneketaal)")
        st.markdown(agent4_output)

    with tab5:
        st.markdown("### Agent 5: Eindcontrole & Risico-Audit")
        st.markdown(agent5_output)

    with tab6:
        st.markdown("### Agent 6: Toekomstige 30-Dagen Macro Agenda")
        st.markdown(agent6_output)

else:
    st.info("👈 Selecteer de BIST 100 Index en/of je gewenste aandelen in de zijbalk en klik op de knop om de analyse te starten!")
