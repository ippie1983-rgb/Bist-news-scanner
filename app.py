import os
import json
import streamlit as st
import yfinance as yf
import pandas as pd
import urllib.request
import urllib.parse

# Pagina configuratie
st.set_page_config(
    page_title="BIST & Edelmetalen 5-Agent Nieuws- en Analistenscanner",
    page_icon="🇹🇷",
    layout="wide"
)

# Stijlvolle opmaak
st.markdown("""
<style>
    .main-header { font-size: 26px; font-weight: bold; color: #1E3A8A; }
    .sub-header { font-size: 18px; font-weight: bold; color: #374151; }
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-header">🇹🇷 BIST & Edelmetalen 5-Agent Nieuws- en Analistenscanner</p>', unsafe_allow_html=True)
st.markdown("Een krachtige nieuws- en analistenscanner voor **Borsa Istanbul (BIST)**, **Goud** en **Zilver**, aangedreven door 5 gespecialiseerde AI-agents.")

# --- ZIJBALK: SESSIE-GEHEUGEN VOOR DE AQ TOKEN ---
if "aq_token" not in st.session_state:
    st.session_state.aq_token = ""

st.sidebar.header("⚙️ Systeem & AI Instellingen")

st.session_state.aq_token = st.sidebar.text_input(
    "Gemini API Key / AQ Token:",
    type="password",
    value=st.session_state.aq_token,
    help="Wordt automatisch vastgehouden in het geheugen van de app."
)

if not st.session_state.aq_token:
    st.sidebar.error("⚠️ Vul hier je AQ-code in om te starten.")
else:
    st.sidebar.success("✅ Token succesvol geladen in geheugen!")

st.sidebar.markdown("---")
st.sidebar.subheader("🎯 Aandelen Selectie (Agent 1)")
selected_tickers = st.sidebar.multiselect(
    "Kies BIST aandelen om specifiek te volgen:",
    ["THYAO (Turkish Airlines)", "ASELS (Aselsan)", "KCHOL (Koç Holding)", "AKBNK (Akbank)", "TUPRS (Tüpraş)", "BIMAS (Bim)", "SASA (Sasa Polyester)", "GARAN (Garanti BBVA)"],
    default=["THYAO (Turkish Airlines)", "ASELS (Aselsan)", "KCHOL (Koç Holding)"]
)

# --- LIVE MARKT TICKER BAR ---
st.markdown("### 📊 Live Marktoverzicht")
ticker_symbols = {
    "BIST 100": "XU100.IS",
    "USD/TRY": "USDTRY=X",
    "EUR/TRY": "EURTRY=X",
    "Goud Ons ($)": "GC=F",
    "Zilver Ons ($)": "SI=F",
    "Brent Olie ($)": "BZ=F",
    "VIX (Angst)": "^VIX"
}

cols = st.columns(len(ticker_symbols))
for i, (name, symbol) in enumerate(ticker_symbols.items()):
    with cols[i]:
        try:
            t_data = yf.Ticker(symbol).history(period="2d")
            if not t_data.empty:
                current_price = t_data['Close'].iloc[-1]
                prev_price = t_data['Close'].iloc[-2]
                change = ((current_price - prev_price) / prev_price) * 100
                st.metric(label=name, value=f"{current_price:,.2f}", delta=f"{change:+.2f}%")
            else:
                st.metric(label=name, value="N/B")
        except Exception:
            st.metric(label=name, value="Fout bij laden")

st.markdown("---")

# Hulpfunctie met de beproefde URL parameter aanroep
def run_gemini_agent(prompt_text, system_instruction=""):
    token = st.session_state.aq_token.strip()
    if not token:
        return "❌ Fout: Geen token aanwezig in de sessie."
    
    models_to_try = ['gemini-2.5-flash', 'gemini-1.5-flash', 'gemini-1.5-pro']
    last_error = None
    
    for model_name in models_to_try:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={urllib.parse.quote(token)}"
            
            payload = {
                "contents": [{"parts": [{"text": prompt_text}]}],
                "generationConfig": {"temperature": 0.2}
            }
            if system_instruction:
                payload["system_instruction"] = {"parts": [{"text": system_instruction}]}
            
            req = urllib.request.Request(
                url, 
                data=json.dumps(payload).encode("utf-8"), 
                headers={"Content-Type": "application/json"}, 
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=25) as resp:
                res_json = json.loads(resp.read().decode("utf-8"))
                return res_json["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            last_error = str(e)
            continue
            
    return f"❌ Fout bij aanroepen van AI Agents: {last_error}"

# --- HOOFDPROGRAMMA: DE 5-AGENT KETTING ---
st.markdown("### 🤖 Start de 5-Agent Intelligence Ketting")
st.markdown("Druk op de knop hieronder om alle 5 de agents achter elkaar te laten samenwerken: van nieuwsverzameling tot eindcontrole.")

if st.button("🚀 Start Volledige 5-Agent Analyse", type="primary"):
    if not st.session_state.aq_token:
        st.error("Voer eerst je token in via de zijbalk.")
    else:
        tickers_clean = [t.split(" ")[0] for t in selected_tickers]
        
        # --- AGENT 1 ---
        with st.spinner("🇹🇷 Agent 1 is bezig: Turkije, politiek, aanhoudingen en BIST-aandelen scannen..."):
            prompt_agent1 = f"""
            Jij bent Agent 1: BIST, Türkiye & Aandelen Intelligence Agent.
            Geef een grondige analyse van de huidige situatie rondom Turkije, Borsa Istanbul (BIST), de Turkse economie, politiek, toespraken, en eventuele aanhoudingen, invallen, fondsschandalen of SPK-maatregelen.
            Focus ook specifiek op deze BIST aandelen: {tickers_clean}.
            
            TAAL & STIJL:
            - Schrijf in 100% begrijpelijk Nederlands (Jip-en-Janneketaal) voor een leek die geen econoom is.
            - Leg moeilijke termen direct in een simpele zin uit.
            """
            agent1_output = run_gemini_agent(prompt_agent1, "Je bent een deskundige Turkse marktexpert die in simpele taal communiceert.")
        
        # --- AGENT 2 ---
        with st.spinner("🌍 Agent 2 is bezig: Internationaal nieuws, oorlogsdreiging en Goud/Zilver analisten scannen..."):
            prompt_agent2 = f"""
            Jij bent Agent 2: Global Macro, War & Gold/Silver Meta-Analyst.
            Analyseer het internationale nieuws over:
            1. Geopolitiek en oorlogsdreiging (Midden-Oosten, Oekraïne, etc.) en de impact op Turkije en edelmetalen.
            2. Goud en Zilver drivers (Fed rente, Amerikaanse inflatie, Dollar index, centrale banken).
            3. Wat zeggen internationale en Turkse topanalisten hierover?
            
            TAAL & STIJL:
            - Schrijf in 100% begrijpelijk Nederlands (Jip-en-Janneketaal) voor een leek.
            """
            agent2_output = run_gemini_agent(prompt_agent2, "Je bent een macro- en edelmetaalanalist die complexe wereldgebeurtenissen uitlegt in begrijpelijke taal.")

        # --- AGENT 3 ---
        with st.spinner("🕵️‍♂️ Agent 3 is bezig: Fake news filter en bronnencontrole uitvoeren..."):
            prompt_agent3 = f"""
            Jij bent Agent 3: Fake News, Rumor & Source Verification Agent (De Waarheids-Filter).
            Neem de bevindingen van Agent 1 en Agent 2:
            - Agent 1 bevindingen: {agent1_output}
            - Agent 2 bevindingen: {agent2_output}
            
