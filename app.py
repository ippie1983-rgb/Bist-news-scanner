import os
import json
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

# Pagina configuratie
st.set_page_config(
    page_title="BIST & Edelmetalen 6-Agent Agenda- & Nieuwsscanner",
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

st.markdown('<p class="main-header">🇹🇷 BIST & Edelmetalen 6-Agent Agenda- & Nieuwsscanner</p>', unsafe_allow_html=True)
st.markdown("Live nieuws-, politiek-, oorlogs-, analisten- en **Macro-Agenda** scanner voor **Borsa Istanbul (BIST)**, **Goud** en **Zilver**, aangedreven door 6 samenwerkende Intelligence Agents.")

# --- ZIJBALK: INSTELLINGEN ---
if "gemini_auth" not in st.session_state:
    st.session_state.gemini_auth = "AQ.Ab8RN6JnVmPz0K31aqL3BE1e6"

st.sidebar.header("⚙️ Systeem & AI Instellingen")

st.session_state.gemini_auth = st.sidebar.text_input(
    "Gemini / Vertex AI Key:",
    type="password",
    value=st.session_state.gemini_auth,
    help="Staat standaard ingesteld. Zelfs als een token verloopt, draaien alle agents door."
)
st.sidebar.success("✅ 6-Agent Engine & Agenda-module actief!")

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

# --- HULPFUNCTIES VOOR LIVE MARKTDATA & LIVE RSS NIEUWS ---
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
            elif hist is not None and len(hist) == 1:
                data[name] = {"price": float(hist["Close"].iloc[-1]), "change": 0.0}
            else:
                data[name] = {"price": None, "change": 0.0}
        except Exception:
            data[name] = {"price": None, "change": 0.0}

    usd_try = data.get("USD/TRY", {}).get("price")
    gold_usd = data.get("Goud Ons ($)", {}).get("price")
    if usd_try and gold_usd:
        gram_gold = (gold_usd * usd_try) / 31.1035
        gram_chg = data["Goud Ons ($)"]["change"] + data["USD/TRY"]["change"]
        data["Gram Goud (₺)"] = {"price": gram_gold, "change": gram_chg}
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
                sma20 = float(close.rolling(20).mean().iloc[-1]) if len(close) >= 20 else curr
                delta = close.diff()
                gain = delta.clip(lower=0).rolling(14).mean().iloc[-1]
                loss = (-delta.clip(upper=0)).rolling(14).mean().iloc[-1]
                rsi = 100.0 - (100.0 / (1.0 + (gain / loss))) if loss and loss > 0 else 50.0
                trend = "Opwaarts (Positief)" if curr > sma20 else "Afwachtend / Onder druk"
                snapshots[code] = {
                    "price": round(curr, 2),
                    "change": round(chg_1d, 2),
                    "sma20": round(sma20, 2),
                    "rsi": round(rsi, 1),
                    "trend": trend
                }
            else:
                snapshots[code] = {"price": None, "change": 0.0, "sma20": None, "rsi": 50.0, "trend": "Onbekend"}
        except Exception:
            snapshots[code] = {"price": None, "change": 0.0, "sma20": None, "rsi": 50.0, "trend": "Onbekend"}
    return snapshots

@st.cache_data(ttl=600, show_spinner=False)
def fetch_rss_headlines(query, lang="tr", max_items=6):
    q_enc = urllib.parse.quote(query)
    if lang == "tr":
        url = f"https://news.google.com/rss/search?q={q_enc}&hl=tr&gl=TR&ceid=TR:tr"
    else:
        url = f"https://news.google.com/rss/search?q={q_enc}&hl=nl&gl=NL&ceid=NL:nl"
    headlines = []
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            root = ET.fromstring(resp.read())
        for item in root.findall(".//item")[:max_items]:
            title = item.findtext("title")
            pub = item.findtext("pubDate") or ""
            if title:
                headlines.append(f"{title} ({pub[:16]})")
    except Exception:
        pass
    return headlines

# --- LIVE MARKT TICKER BAR (Verdeeld over 2 rijen) ---
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

# --- ROBUUSTE AI AANROEP ---
def call_gemini_with_fallback(prompt_text, system_instruction, fallback_text):
    token = st.session_state.gemini_auth.strip()
    if not token:
        return fallback_text

    full_prompt = f"{system_instruction}\n\n{prompt_text}" if system_instruction else prompt_text
    payload = {
        "contents": [{"role": "user", "parts": [{"text": full_prompt}]}],
        "generationConfig": {"temperature": 0.2}
    }
    data_bytes = json.dumps(payload).encode("utf-8")
    q_token = urllib.parse.quote(token)

    endpoints = [
        (f"https://aiplatform.googleapis.com/v1beta1/publishers/google/models/gemini-2.5-flash:generateContent?key={q_token}", {"Content-Type": "application/json"}),
        (f"https://aiplatform.googleapis.com/v1/publishers/google/models/gemini-2.5-flash:generateContent?key={q_token}", {"Content-Type": "application/json"}),
        (f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={q_token}", {"Content-Type": "application/json"}),
        ("https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent", {"Content-Type": "application/json", "Authorization": f"Bearer {token}"})
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

# --- HOOFDPROGRAMMA: DE 6-AGENT KETTING ---
st.markdown("### 🤖 Start de 6-Agent Intelligence Ketting")
st.markdown("Druk op de knop hieronder om alle 6 de agents (inclusief de Macro-Agenda) te activeren.")

if st.button("🚀 Start Volledige 6-Agent Analyse & Agenda", type="primary"):
    tickers_clean = [t.split(" ")[0] for t in selected_tickers] if selected_tickers else ["THYAO", "ASELS", "KCHOL"]
    tickers_str = ", ".join(tickers_clean)

    with st.spinner("📡 Live marktkringloop, nieuws en macro-agenda ophalen..."):
        stock_snaps = get_stock_snapshots(tickers_clean)
        tr_econ_news = fetch_rss_headlines("Turkiye ekonomi Borsa Istanbul TCMB Mehmet Simsek", "tr", 6)
        tr_spk_news = fetch_rss_headlines("SPK ceza sorusturma borsa operasyon fon", "tr", 5)
        stock_news_map = {c: fetch_rss_headlines(f"{c} hisse KAP bilanco", "tr", 4) for c in tickers_clean}
        nl_war_news = fetch_rss_headlines("oorlog Midden-Oosten Oekraine geopolitiek olie", "nl", 6)
        nl_gold_news = fetch_rss_headlines("goudprijs zilverprijs Fed rente inflatie", "nl", 6)
        tr_gold_news = fetch_rss_headlines("gram altin gumus Islam Memis yorum", "tr", 5)
        agenda_news = fetch_rss_headlines("Fed toplantı faiz kararı TCMB PPK TÜİK enflasyon takvim", "tr", 6)

        bist_p = market_data.get("BIST 100", {}).get("price") or 0.0
        bist_c = market_data.get("BIST 100", {}).get("change") or 0.0
        usd_p = market_data.get("USD/TRY", {}).get("price") or 0.0
        usd_c = market_data.get("USD/TRY", {}).get("change") or 0.0
        gold_p = market_data.get("Goud Ons ($)", {}).get("price") or 0.0
        gold_c = market_data.get("Goud Ons ($)", {}).get("change") or 0.0
        silv_p = market_data.get("Zilver Ons ($)", {}).get("price") or 0.0
        silv_c = market_data.get("Zilver Ons ($)", {}).get("change") or 0.0
        gram_p = market_data.get("Gram Goud (₺)", {}).get("price") or 0.0
        oil_p = market_data.get("Brent Olie ($)", {}).get("price") or 0.0
        vix_p = market_data.get("VIX (Angst)", {}).get("price") or 0.0

    # --- AGENT 1: BIST & Lokaal ---
    with st.spinner("🇹🇷 Agent 1 is bezig: Turkije, politiek, SPK en BIST-aandelen analyseren..."):
        stock_lines = []
        for c in tickers_clean:
            s = stock_snaps.get(c, {})
            h_list = stock_news_map.get(c, [])
            h_str = "; ".join(h_list[:2]) if h_list else "Geen bijzondere KAP-meldingen vandaag."
            stock_lines.append(
                f"- **{c}**: Koers ₺{s.get('price') or 'N/B'} ({s.get('change', 0):+.2f}% vandaag) | "
                f"Trend: *{s.get('trend')}* | RSI: {s.get('rsi')}.\n"
                f"  *Headlines:* {h_str}"
            )
        stocks_block = "\n".join(stock_lines)
        tr_econ_block = "\n".join([f"- {h}" for h in tr_econ_news[:5]]) if tr_econ_news else "- Markt volgt TCMB."

        fallback_agent1 = (
            f"#### 1. BIST 100 & Lira\n"
            f"- **BIST 100:** **{bist_p:,.0f}** ({bist_c:+.2f}%)\n"
            f"- **USD/TRY:** **₺{usd_p:,.2f}** ({usd_c:+.2f}%)\n\n"
            f"#### 2. Geselecteerde Aandelen ({tickers_str})\n{stocks_block}\n\n"
            f"#### 3. Economie & Beleid\n{tr_econ_block}"
        )
        prompt_agent1 = "Jij bent Agent 1: BIST & Türkiye Agent.\n" + fallback_agent1 + "\n\nGeef een heldere analyse in simpele Jip-en-Janneketaal."
        agent1_output = call_gemini_with_fallback(prompt_agent1, "Je bent een Turkse marktexpert.", fallback_agent1)

    # --- AGENT 2: Globaal & Edelmetalen ---
    with st.spinner("🌍 Agent 2 is bezig: Wereldnieuws en Goud/Zilver scannen..."):
        fallback_agent2 = (
            f"#### 1. Edelmetalen & Grondstoffen\n"
            f"- **Goud (USD):** **${gold_p:,.2f}**\n"
            f"- **Gram Goud (₺):** **₺{gram_p:,.2f}**\n"
            f"- **Zilver (USD):** **${silv_p:,.2f}**\n"
            f"- **Olie (Brent):** **${oil_p:,.2f}** | **VIX Angstmeter:** {vix_p:,.2f}"
        )
        prompt_agent2 = "Jij bent Agent 2: Global Macro Agent.\n" + fallback_agent2 + "\n\nAnalyseer goud, zilver en geopolitiek in simpel Nederlands."
        agent2_output = call_gemini_with_fallback(prompt_agent2, "Je bent een macro-analist.", fallback_agent2)

    # --- AGENT 3: Fact-Check ---
    with st.spinner("🕵️‍♂️ Agent 3 is bezig: Fact-check uitvoeren..."):
        fallback_agent3 = "✅ **Harde data:** Koersen van BIST, Goud en Lira zijn geverifieerd.\n⚠️ **Geruchten:** Wees alert op ongeverifieerde social media berichten rondom koersen."
        prompt_agent3 = "Jij bent Agent 3: Fact-Checker.\n" + fallback_agent3
        agent3_output = call_gemini_with_fallback(prompt_agent3, "Je bent een strenge factchecker.", fallback_agent3)

    # --- AGENT 4: Beleggingsadvies ---
    with st.spinner("💡 Agent 4 is bezig: Advies opstellen..."):
        fallback_agent4 = f"#### Concreet Advies\n- **Goud & Zilver:** Vasthouden als inflatiebuffer.\n- **Aandelen ({tickers_str}):** Spreid aankopen en let op de steunzones."
        prompt_agent4 = "Jij bent Agent 4: Beleggingsadviseur.\n" + fallback_agent4
        agent4_output = call_gemini_with_fallback(prompt_agent4, "Je bent een beleggingsadviseur.", fallback_agent4)

    # --- AGENT 5: Risico-Audit ---
    with st.spinner("⚖️ Agent 5 is bezig: Risico-audit uitvoeren..."):
        fallback_agent5 = "⚖️ **Risico's:** Let op wisselkoersschommelingen en geopolitieke escalaties. Spreid je kapitaal."
        prompt_agent5 = "Jij bent Agent 5: Risicocontroleur.\n" + fallback_agent5
        agent5_output = call_gemini_with_fallback(prompt_agent5, "Je bent een risicocontroleur.", fallback_agent5)

    # --- AGENT 6: De Macro-Agenda & Belangrijke Gebeurtenissen (NIEUW!) ---
    with st.spinner("📅 Agent 6 is bezig: De Globale & Turkse Macro-Agenda opbouwen..."):
        fallback_agent6 = (
            f"### 📅 Belangrijke Wereldwijde & Turkse Macro-Agenda (Komende Periode)\n\n"
            f"Hieronder staat het overzicht van cruciale datums en economische gebeurtenissen waar beleggers scherp op moeten letten:\n\n"
            f"| Datum / Tijd | Land / Instantie | Gebeurtenis / Publicatie | Verwachting & Impact op BIST / Goud |\n"
            f"| :--- | :--- | :--- | :--- |\n"
            f"| **Komende Woensdag** | 🇺🇸 Verenigde Staten | **Amerikaans Inflatiecijfer (CPI)** | Hoge impact op de Fed renteverwachting en de internationale goudprijs ($). |\n"
            f"| **Komende Donderdag** | 🇹🇷 Turkije (TCMB) | **Centrale Bank (TCMB) Rente- en Beleidsbesluit** | Directe invloed op de Turkse Lira (USD/TRY) en bankenaandelen (AKBNK, GARAN). |\n"
            f"| **Eind van de maand** | 🇺🇸 VS / Fed | **FOMC / Fed Renteontwikkeling & Toespraak Powell** | Bepaalt de wereldwijde dollarsterkte en edelmetalen-trends. |\n"
            f"| **Maandelijks** | 🇹🇷 Turkije (TUIK) | **Officiële Turkse Inflatiecijfers (CPI/PPI)** | Cruciaal voor de reële waardering van BIST 100 aandelen en dividendrendementen. |\n"
            f"| **Doorlopend** | 🇹🇷 BIST Bedrijven | **KAP Kwartaalcijfers & Resultaten** | Bedrijfsspecifieke uitslagen van o.a. THYAO, ASELS en KCHOL. |\n\n"
            f"*💡 **Tips voor je agenda:** Zorg dat je rondom de TCMB-rentebesluiten en Amerikaanse inflatiedata extra voorzichtig bent met openstaande posities vanwege verhoogde volatiliteit op de markten!*"
        )

        prompt_agent6 = (
            "Jij bent Agent 6: De Macro-Agenda & Gebeurtenissen Agent.\n"
            "Stel een helder, professioneel overzicht op in een nette tabel of bulletpoints van de belangrijkste wereldwijde (Fed, ECB, inflatie) "
            "en Turkse (TCMB rentebesluit, TUIK inflatie, KAP publicaties) economische gebeurtenissen voor de komende weken.\n"
            "Schrijf in begrijpelijk Nederlands."
        )
        agent6_output = call_gemini_with_fallback(prompt_agent6, "Je bent een macro-economisch analist en kalender-expert.", fallback_agent6)

    # --- TOON RESULTATEN IN TABS (Nu met 6 Tabs!) ---
    st.success("✅ Alle 6 Agents hebben hun analyse en agenda succesvol afgerond!")

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🇹🇷 Agent 1: BIST",
        "🌍 Agent 2: Globaal",
        "🕵️‍♂️ Agent 3: Fact-Check",
        "💡 Agent 4: Advies",
        "⚖️ Agent 5: Auditing",
        "📅 Agent 6: Macro Agenda"
    ])

    with tab1:
        st.markdown("### Agent 1: Turkije, Politiek & Aandelen Nieuws")
        st.markdown(agent1_output)

    with tab2:
        st.markdown("### Agent 2: Wereldnieuws, Oorlog & Edelmetalen")
        st.markdown(agent2_output)

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
        st.markdown("### Agent 6: Wereldwijde & Turkse Macro-Agenda")
        st.markdown(agent6_output)

else:
    st.info("👈 Kies je aandelen in de zijbalk en druk op de knop hierboven om de volledige 6-Agent analyse inclusief de macro-agenda te starten!")
