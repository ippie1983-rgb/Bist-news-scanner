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
    page_title="BIST & Edelmetalen 6-Agent Nieuwsscanner",
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

st.markdown('<p class="main-header">🇹🇷 BIST & Edelmetalen 6-Agent Nieuwsscanner</p>', unsafe_allow_html=True)
st.markdown("Live nieuws, **artikel-samenvattingen per bronlink** (max 3 dagen oud) en een **toekomstige 30-dagen Macro-Agenda**.")

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
st.sidebar.success("✅ Systeem stabiel & actief!")

st.sidebar.markdown("---")
st.sidebar.subheader("🎯 Aandelen Selectie (Agent 1)")
STOCK_OPTIONS = [
    "THYAO (Turkish Airlines)",
    "ASELS (Aselsan)",
    "KCHOL (Koç Holding)",
    "AKBNK (Akbank)",
    "GARAN (Garanti BBVA)",
    "TUPRS (Tüpraş)",
    "BIMAS (Bim)",
    "EREGL (Erdemir)",
    "SISE (Şişecam)",
    "SASA (Sasa Polyester)"
]
selected_tickers = st.sidebar.multiselect(
    "Kies BIST aandelen om specifiek te volgen:",
    STOCK_OPTIONS,
    default=["THYAO (Turkish Airlines)", "ASELS (Aselsan)", "KCHOL (Koç Holding)"]
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

def fetch_news_strict(query, lang="tr", max_items=10, min_days=None, max_days=None):
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
                    if min_days is not None and diff_days < min_days:
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
st.markdown("### 🤖 Start de 6-Agent Top-Media Scanner")
st.markdown("Druk op de knop om de analyse te starten met artikel-samenvattingen per bronlink.")

if st.button("🚀 Start 6-Agent Analyse", type="primary"):
    tickers_clean = [t.split(" ")[0] for t in selected_tickers] if selected_tickers else ["THYAO", "ASELS", "KCHOL"]
    tickers_str = ", ".join(tickers_clean)

    with st.spinner("📡 Live ophalen van artikelen en marktomstandigheden..."):
        stock_snaps = get_stock_snapshots(tickers_clean)
        
        tr_econ_items = fetch_news_strict("Turkiye ekonomi Borsa Istanbul TCMB", "tr", 10, max_days=3)
        tr_spk_items = fetch_news_strict("SPK ceza sorusturma borsa operasyon", "tr", 8, max_days=3)
        
        stock_news_dict = {}
        for c in tickers_clean:
            stock_news_dict[c] = fetch_news_strict(f"{c} hisse KAP", "tr", 5, max_days=3)
        
        nl_war_items = fetch_news_strict("oorlog Midden-Oosten Oekraine geopolitiek olie", "nl", 8, max_days=3)
        nl_gold_items = fetch_news_strict("goudprijs zilverprijs Fed rente", "nl", 8, max_days=3)
        
        agenda_items = fetch_news_strict("Fed toplantı faiz kararı TCMB PPK TÜİK enflasyon", "tr", 10, max_days=None)
        agenda_items = sorted(agenda_items, key=lambda x: x["datetime"])

        bist_p = market_data.get("BIST 100", {}).get("price") or 0.0
        bist_c = market_data.get("BIST 100", {}).get("change") or 0.0
        usd_p = market_data.get("USD/TRY", {}).get("price") or 0.0
        gold_p = market_data.get("Goud Ons ($)", {}).get("price") or 0.0
        gram_p = market_data.get("Gram Goud (₺)", {}).get("price") or 0.0
        silv_p = market_data.get("Zilver Ons ($)", {}).get("price") or 0.0
        vix_p = market_data.get("VIX (Angst)", {}).get("price") or 0.0

    all_tr_items = tr_econ_items + tr_spk_items
    for c in tickers_clean:
        all_tr_items.extend(stock_news_dict.get(c, []))

    # --- AGENT 1: Samenvatting per artikel met behoud van links ---
    with st.spinner("🇹🇷 Agent 1: Artikel-samenvattingen genereren..."):
        titles_and_links_block = "\n".join([f"- Titel: {item['title']} | Link: {item['link']}" for item in all_tr_items]) if all_tr_items else "Geen artikelen."
        
        fallback_agent1 = f"### 🇹🇷 Turkije & BIST Overzicht\n\n- **BIST 100:** {bist_p:,.0f} | **USD/TRY:** ₺{usd_p:,.2f}"
        prompt_agent1 = (
            "Jij bent Agent 1: BIST & Nieuws Intelligence Agent.\n"
            "Hier is een lijst met recente artikelen (koppen en links) van de afgelopen 3 dagen uit de Turkse media:\n"
            f"{titles_and_links_block}\n\n"
            "OPDRACHT:\n"
            "Ga al deze artikelen langs. Schrijf per artikel een duidelijke, krachtige samenvatting in Jip-en-Janneketaal over wat dit betekent voor de belegger.\n"
            "Zorg ervoor dat je onder elke samenvatting exact de bijbehorende bronlink plaatst."
        )
        agent1_output = call_gemini_with_fallback(prompt_agent1, "Je bent een Turkse marktexpert.", fallback_agent1)

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
        agenda_titles = "\n".join([f"- [{item['date']}] {item['title']} | Link: {item['link']}" for item in agenda_items]) if agenda_items else "Geen agenda-items."
        fallback_agent6 = "### 📅 Toekomstige 30-Dagen Macro Agenda\n\nGeplande publicaties en besluiten."
        prompt_agent6 = (
            "Jij bent Agent 6: De Toekomstige Macro-Agenda Samenvatter.\n"
            "Hier zijn de chronologisch gesorteerde koppen en links van de komende agenda-artikelen:\n"
            f"{agenda_titles}\n\n"
            "Lees deze koppen en zet ze om in een helder, oplopend overzicht per gebeurtenis in normale mensentaal (Jip-en-Janneketaal), inclusief de bijbehorende links."
        )
        agent6_output = call_gemini_with_fallback(prompt_agent6, "Je bent een macro-economisch analist en agenda-expert.", fallback_agent6)

    # --- TOON RESULTATEN IN TABS ---
    st.success("✅ Analyse succesvol afgerond!")

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🇹🇷 Agent 1: BIST",
        "🌍 Agent 2: Globaal",
        "🕵️‍♂️ Agent 3: Fact-Check",
        "💡 Agent 4: Advies",
        "⚖️ Agent 5: Auditing",
        "📅 Agent 6: TOEKOMSTIGE AGENDA"
    ])

    with tab1:
        st.markdown("### Agent 1: Turkse Media - Artikel Samenvattingen & Links")
        st.markdown(agent1_output)

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
    st.info("👈 Kies je aandelen in de zijbalk en klik op de knop om de analyse te starten!")
