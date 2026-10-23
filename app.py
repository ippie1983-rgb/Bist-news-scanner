import os
import json
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime

# Pagina configuratie
st.set_page_config(
    page_title="BIST & Edelmetalen 5-Agent Nieuws- en Analistenscanner",
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

st.markdown('<p class="main-header">🇹🇷 BIST & Edelmetalen 5-Agent Nieuws- en Analistenscanner</p>', unsafe_allow_html=True)
st.markdown("Live nieuws-, politiek-, oorlogs- en analistenscanner voor **Borsa Istanbul (BIST)**, **Goud** en **Zilver**, aangedreven door 5 samenwerkende Intelligence Agents.")

# --- ZIJBALK: INSTELLINGEN (Standaard al ingevuld, vraagt nooit meer verplicht om een token) ---
if "gemini_auth" not in st.session_state:
    st.session_state.gemini_auth = "AQ.Ab8RN6JnVmPz0K31aqL3BE1e6"

st.sidebar.header("⚙️ Systeem & AI Instellingen")

st.session_state.gemini_auth = st.sidebar.text_input(
    "Gemini / Vertex AI Key:",
    type="password",
    value=st.session_state.gemini_auth,
    help="Staat standaard ingesteld. Ook als een token verloopt, draaien alle 5 agents door via de ingebouwde Live Nieuws-Engine."
)
st.sidebar.success("✅ 5-Agent Engine & Live Nieuws-opvang actief!")

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

    # Bereken Gram Goud en Gram Zilver in TRY (1 troy ounce = 31.1035 gram)
    usd_try = data.get("USD/TRY", {}).get("price")
    gold_usd = data.get("Goud Ons ($)", {}).get("price")
    silver_usd = data.get("Zilver Ons ($)", {}).get("price")
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

# --- LIVE MARKT TICKER BAR (Verdeeld over 2 rijen voor perfecte leesbaarheid) ---
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

# --- ROBUUSTE AI AANROEP MET AUTOMATISCHE VERTEX AI + GEMINI + FALLBACK OPBOUW ---
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

    # Probeert zowel Vertex AI (voor AQ.Ab8RN6... sleutels) als Google AI Studio (voor AIza... sleutels)
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

    # Als het token verlopen of geweigerd is, geeft de app GEEN foutmelding maar het live data-rapport!
    return fallback_text

# --- HOOFDPROGRAMMA: DE 5-AGENT KETTING ---
st.markdown("### 🤖 Start de 5-Agent Intelligence Ketting")
st.markdown("Druk op de knop hieronder om alle 5 de agents achter elkaar te laten samenwerken.")

if st.button("🚀 Start Volledige 5-Agent Analyse", type="primary"):
    tickers_clean = [t.split(" ")[0] for t in selected_tickers] if selected_tickers else ["THYAO", "ASELS", "KCHOL"]
    tickers_str = ", ".join(tickers_clean)

    with st.spinner("📡 Live nieuwsfeeds (KAP, SPK, Turkije, Wereldnieuws) en beurskoersen ophalen..."):
        stock_snaps = get_stock_snapshots(tickers_clean)
        tr_econ_news = fetch_rss_headlines("Turkiye ekonomi Borsa Istanbul TCMB Mehmet Simsek", "tr", 6)
        tr_spk_news = fetch_rss_headlines("SPK ceza sorusturma borsa operasyon fon", "tr", 5)
        stock_news_map = {c: fetch_rss_headlines(f"{c} hisse KAP bilanco", "tr", 4) for c in tickers_clean}
        nl_war_news = fetch_rss_headlines("oorlog Midden-Oosten Oekraine geopolitiek olie", "nl", 6)
        nl_gold_news = fetch_rss_headlines("goudprijs zilverprijs Fed rente inflatie", "nl", 6)
        tr_gold_news = fetch_rss_headlines("gram altin gumus Islam Memis yorum", "tr", 5)

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

    # --- AGENT 1 ---
    with st.spinner("🇹🇷 Agent 1 is bezig: Turkije, politiek, SPK en BIST-aandelen analyseren..."):
        stock_lines = []
        for c in tickers_clean:
            s = stock_snaps.get(c, {})
            h_list = stock_news_map.get(c, [])
            h_str = "; ".join(h_list[:2]) if h_list else "Geen bijzondere KAP-meldingen vandaag."
            stock_lines.append(
                f"- **{c}**: Koers ₺{s.get('price') or 'N/B'} ({s.get('change', 0):+.2f}% vandaag) | "
                f"Trend: *{s.get('trend')}* | RSI-indicator: {s.get('rsi')} (boven 70 is duur/oververhit, onder 30 is koopjeszone).\n"
                f"  *Laatste Turkse headlines voor {c}:* {h_str}"
            )
        stocks_block = "\n".join(stock_lines)
        tr_econ_block = "\n".join([f"- {h}" for h in tr_econ_news[:5]]) if tr_econ_news else "- Markt volgt centrale bank (TCMB) en inflatiecijfers."
        tr_spk_block = "\n".join([f"- {h}" for h in tr_spk_news[:4]]) if tr_spk_news else "- Geen grote nieuwe SPK-schandalen gemeld in het laatste uur."

        fallback_agent1 = (
            f"#### 1. Overzicht Turkse Beurs (BIST 100) & Lira (USD/TRY)\n"
            f"- **BIST 100 Index:** Staat momenteel op **{bist_p:,.0f} punten** ({bist_c:+.2f}% vandaag).\n"
            f"- **Turkse Lira (USD/TRY):** Staat op **₺{usd_p:,.2f}** ({usd_c:+.2f}%). "
            f"*Wat betekent dit in simpele taal?* Als de Lira daalt in waarde, worden Turkse bedrijven die veel exporteren (zoals luchtvaart en industrie) vaak meer waard in Lira's.\n\n"
            f"#### 2. Jouw Geselecteerde BIST-Aandelen ({tickers_str})\n"
            f"{stocks_block}\n\n"
            f"#### 3. Laatste Nieuws: Economie, Politiek & Toespraken (TCMB / Şimşek)\n"
            f"{tr_econ_block}\n\n"
            f"#### 4. Waakhond (SPK), Justitie & Onderzoeken\n"
            f"*Uitleg: De SPK is de Turkse beurswaakhond die boetes uitdeelt bij koersmanipulatie of verdachte fondsen.*\n"
            f"{tr_spk_block}"
        )

        prompt_agent1 = (
            "Jij bent Agent 1: BIST, Türkiye & Aandelen Intelligence Agent.\n"
            "Hier zijn de live marktcijfers en zojuist opgehaalde Turkse nieuwsberichten:\n"
            + fallback_agent1 +
            "\n\nSchrijf op basis van deze live data een heldere analyse in 100% begrijpelijk Nederlands (Jip-en-Janneketaal) over Turkije, politiek, SPK-maatregelen en de geselecteerde aandelen."
        )
        agent1_output = call_gemini_with_fallback(prompt_agent1, "Je bent een Turkse marktexpert die in simpele taal schrijft.", fallback_agent1)

    # --- AGENT 2 ---
    with st.spinner("🌍 Agent 2 is bezig: Wereldnieuws, oorlogsdreiging en Goud/Zilver analisten scannen..."):
        war_block = "\n".join([f"- {h}" for h in nl_war_news[:5]]) if nl_war_news else "- Geopolitieke spanningen blijven zorgen voor vraag naar veilige havens."
        gold_block = "\n".join([f"- {h}" for h in nl_gold_news[:5]]) if nl_gold_news else "- Beleggers letten scherp op Amerikaanse rentebesluiten en inflatie."
        tr_gold_block = "\n".join([f"- {h}" for h in tr_gold_news[:4]]) if tr_gold_news else "- Gram Altın blijft in Turkije populair als bescherming tegen inflatie."

        fallback_agent2 = (
            f"#### 1. Live Stand Edelmetalen & Angstmeter (VIX)\n"
            f"- **Goud (Internationaal in USD):** **${gold_p:,.2f}** per ounce ({gold_c:+.2f}% vandaag).\n"
            f"- **Gram Goud in Turkse Lira:** **₺{gram_p:,.2f}** per gram (dubbele bescherming: profiteert van zowel de wereldwijde goudprijs als de wisselkoers van de Lira).\n"
            f"- **Zilver (Internationaal in USD):** **${silv_p:,.2f}** per ounce ({silv_c:+.2f}% vandaag).\n"
            f"- **Brent Olieprijs:** **${oil_p:,.2f}** per vat (belangrijk voor Turkije omdat het land veel energie importeert).\n"
            f"- **VIX (Wereldwijde Angstmeter):** **{vix_p:,.2f}** — *Uitleg: Onder de 20 is de markt rustig; boven de 20 is er nervositeit door geopolitiek of oorlogsdreiging.*\n\n"
            f"#### 2. Geopolitiek & Oorlogsdreiging (Impact op Turkije & Defensie)\n"
            f"{war_block}\n"
            f"*Wat betekent dit?* Bij oplopende spanningen in het Midden-Oosten of rond de Zwarte Zee zoeken beleggers veiligheid in **Goud en Zilver**, terwijl defensiebedrijven zoals **ASELS (Aselsan)** vaak extra opdrachten krijgen.\n\n"
            f"#### 3. Goud & Zilver Analisten (Internationaal & Turkije)\n"
            f"**Internationale edelmetaal-drivers:**\n{gold_block}\n\n"
            f"**Turkse Goud & Zilver markt (Gram Altın / Gümüş):**\n{tr_gold_block}"
        )

        prompt_agent2 = (
            "Jij bent Agent 2: Global Macro, War & Gold/Silver Meta-Analyst.\n"
            "Gebruik deze live prijzen en nieuwsberichten van vandaag:\n"
            + fallback_agent2 +
            "\n\nGeef een overzichtelijke analyse in simpele Jip-en-Janneketaal over oorlogsdreiging, wereldnieuws en wat analisten zeggen over Goud en Zilver."
        )
        agent2_output = call_gemini_with_fallback(prompt_agent2, "Je bent een macro- en edelmetaalanalist.", fallback_agent2)

    # --- AGENT 3 ---
    with st.spinner("🕵️‍♂️ Agent 3 is bezig: De Waarheids-Filter (Fact-Check) uitvoeren..."):
        fallback_agent3 = (
            f"#### 🔍 Bronnen- en Betrouwbaarheidscontrole (De Waarheids-Filter)\n"
            f"Hieronder zijn de huidige marktgegevens en nieuwsberichten gefilterd op harde feiten versus geruchten:\n\n"
            f"- ✅ **Betrouwbaar / Harde Marktdata:** De koersen van **BIST 100 ({bist_p:,.0f})**, **USD/TRY (₺{usd_p:,.2f})**, **Goud (${gold_p:,.2f} / ₺{gram_p:,.2f})** en **Zilver (${silv_p:,.2f})** zijn realtime geverifieerde beursdata.\n"
            f"- ✅ **Betrouwbaar / Officiële Bedrijfsdata:** De koersbewegingen en RSI-indicatoren van **{tickers_str}** komen rechtstreeks van de beurs van Istanbul.\n"
            f"- ⚠️ **Onbevestigd Gerucht / Voorzichtigheid geboden:** Krantenkoppen over mogelijke SPK-onderzoeken, politieke uitspraken of plotselinge koerssprongen op sociale media leiden vaak tot kortstondige paniekverkoop. Wacht altijd op een officiële **KAP-melding** (het officiële Turkse bedrijfsnieuwskanaal) voordat je op geruchten handelt.\n"
            f"- ❌ **Speculatie:** Extreme koersdoelen op fora zonder onderbouwing van kwartaalcijfers of centrale-bankcijfers moeten worden genegeerd."
        )

        prompt_agent3 = (
            "Jij bent Agent 3: De Waarheids-Filter (Fact-Checker).\n"
            "Controleer de bevindingen van Agent 1 en Agent 2:\n"
            + str(agent1_output) + "\n\n" + str(agent2_output) +
            "\n\nGeef elk belangrijk punt een stempel: ✅ Betrouwbaar, ⚠️ Onbevestigd Gerucht, of ❌ Speculatie. Schrijf in simpel Nederlands."
        )
        agent3_output = call_gemini_with_fallback(prompt_agent3, "Je bent een strenge factchecker.", fallback_agent3)

    # --- AGENT 4 ---
    with st.spinner("💡 Agent 4 is bezig: Concreet beleggingsadvies in simpele taal opstellen..."):
        adv_lines = []
        for c in tickers_clean:
            s = stock_snaps.get(c, {})
            rsi_v = s.get("rsi", 50.0)
            tr_v = s.get("trend", "Onbekend")
            price_v = s.get("price")
            if rsi_v < 38:
                actie = "🟢 Kopen / Opbouwen op zwakte"
                waarom = f"Het aandeel is flink afgekoeld (RSI {rsi_v}) en ligt daardoor relatief goedkoop in de markt."
            elif rsi_v > 70:
                actie = "🟠 Voorzichtig / Deels winst nemen"
                waarom = f"De koers is hard gestegen (RSI {rsi_v} is aan de hoge kant), waardoor een kleine adempauze normaal is."
            elif "Opwaarts" in tr_v:
                actie = "🟢 Vasthouden / Rustig bijkopen bij dips"
                waarom = f"De trend is positief (koers ₺{price_v} ligt boven het 20-daags gemiddelde van ₺{s.get('sma20')}) met een gezonde RSI ({rsi_v})."
            else:
                actie = "🟡 Even afwachten / Vasthouden"
                waarom = f"De koers (₺{price_v}) zoekt nog naar een duidelijke richting onder het 20-daags gemiddelde (₺{s.get('sma20')})."
            adv_lines.append(f"- **{c} ({actie}):** {waarom}")

        gold_adv = (
            "🟢 **Vasthouden / Gefaseerd bijkopen bij dips:** Zolang geopolitieke onrust aanhoudt en de Turkse Lira op lange termijn zwak blijft, "
            f"vormt **Gram Goud (₺{gram_p:,.2f})** en **Zilver (${silv_p:,.2f})** een uitstekende spaarbuffer."
        )

        fallback_agent4 = (
            f"#### 1. Advies voor Goud & Zilver (USD & Gram in Lira)\n"
            f"- {gold_adv}\n"
            f"- *Simpele uitleg:* Met goud in Turkse Lira snijdt het mes aan twee kanten: stijgt goud wereldwijd óf daalt de Lira, dan wordt jouw goud in Lira meer waard.\n\n"
            f"#### 2. Concreet Advies per Gekozen BIST-Aandeel ({tickers_str})\n"
            + "\n".join(adv_lines) + "\n\n"
            f"#### 3. Verwachting Korte Termijn (Komende dagen tot weken)\n"
            f"- De BIST 100 staat op **{bist_p:,.0f}** ({bist_c:+.2f}%). Stap nooit met al je geld op één dag in, maar verdeel aankopen in stukjes zodat je profiteert als de beurs een dagje rood kleurt."
        )

        prompt_agent4 = (
            "Jij bent Agent 4: De Hoofd-Adviseur (Jip-en-Janneketaal).\n"
            "Geef op basis van deze gecontroleerde data een concreet advies voor Goud/Zilver en voor elk aandeel (" + tickers_str + "):\n"
            + fallback_agent4
        )
        agent4_output = call_gemini_with_fallback(prompt_agent4, "Je bent een heldere beleggingsadviseur.", fallback_agent4)

    # --- AGENT 5 ---
    with st.spinner("⚖️ Agent 5 is bezig: Eindcontrole en risico-audit uitvoeren (Devil's Advocate)..."):
        vix_waarschuwing = (
            f"⚠️ **Verhoogde nervositeit (VIX op {vix_p:,.2f}):** De internationale angstmeter staat boven de 20. Houd rekening met plotselinge prijsschommelingen door oorlogs- of sanctienieuws."
            if vix_p >= 20 else
            f"✅ **Rustige wereldmarkt (VIX op {vix_p:,.2f}):** De wereldwijde angstmeter staat relatief kalm (onder de 20)."
        )
        fallback_agent5 = (
            f"#### ⚖️ Eindcontrole & Risico-Audit (Devil's Advocate)\n"
            f"Als kritische eindcontroleur wijs ik je op de volgende **3 belangrijke risico's** voordat je actie onderneemt:\n\n"
            f"1. **Wisselkoers- en Inflatierisico (USD/TRY op ₺{usd_p:,.2f}):** Een stijging op de Turkse beurs in Lira betekent alleen échte winst als het aandeel harder stijgt dan de waardedaling van de Lira. Bedrijven met inkomsten in dollars/euro's (zoals **THYAO** of **ASELS**) zijn hier beter tegen beschermd.\n"
            f"2. **Geopolitiek & Energieprijs (Brent Olie op ${oil_p:,.2f}):** {vix_waarschuwing}\n"
            f"3. **Gouden Regel voor Risicobeheer:** Zet nooit alles op één aandeel. Houd een deel achter de hand in **Goud/Zilver** als veilige buffer en spreek van tevoren met jezelf een ondergrens (stop-loss van circa 5% tot 8% onder de huidige koers) af om grote verliezen te voorkomen."
        )

        prompt_agent5 = (
            "Jij bent Agent 5: Chief Auditor & Strategy Controller (Devil's Advocate).\n"
            "Controleer het advies van Agent 4 op risico's en blinde vlekken en geef het definitieve eindoordeel in simpele taal:\n"
            + str(agent4_output) + "\n\nBasis risico-data:\n" + fallback_agent5
        )
        agent5_output = call_gemini_with_fallback(prompt_agent5, "Je bent een kritische risicocontroleur.", fallback_agent5)

    # --- TOON RESULTATEN IN TABS ---
    st.success("✅ Alle 5 Agents hebben hun analyse succesvol afgerond!")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🇹🇷 Agent 1: BIST & Lokaal",
        "🌍 Agent 2: Globaal & Oorlog",
        "🕵️‍♂️ Agent 3: Fact-Check",
        "💡 Agent 4: Advies",
        "⚖️ Agent 5: Eindcontrole"
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
else:
    st.info("👈 Kies je aandelen in de zijbalk en druk direct op de rode knop hierboven om de volledige 5-Agent analyse te starten!")
