import streamlit as st
import yfinance as yf
import google.generativeai as genai
import pandas as pd
from datetime import datetime

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

# --- ZIJBALK: API SLEUTEL & CONFIGURATIE ---
st.sidebar.header("⚙️ Instellingen & API Key")

# Veld voor een echte AIza... sleutel
api_key_input = st.sidebar.text_input(
    "Google Gemini API Key (AIza...)",
    type="password",
    value="",
    help="Plak hier je permanente API-sleutel die begint met AIza..."
)

if not api_key_input:
    st.sidebar.error("⚠️ Vul je permanente API-sleutel (AIza...) hierboven in om de agents te laten werken.")
else:
    try:
        genai.configure(api_key=api_key_input)
        st.sidebar.success("✅ API-sleutel succesvol ingesteld!")
    except Exception as e:
        st.sidebar.error(f"Fout bij instellen sleutel: {e}")

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

# Officiële, stabiele hulpfunctie via de Google SDK
def run_gemini_agent(prompt_text, system_instruction=""):
    if not api_key_input:
        return "❌ Fout: Geen API Key ingevoerd in de zijbalk."
    
    models_to_try = ['gemini-2.5-flash', 'gemini-1.5-flash', 'gemini-1.5-pro']
    last_error = None
    
    for model_name in models_to_try:
        try:
            model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=system_instruction
            )
            response = model.generate_content(prompt_text)
            return response.text
        except Exception as e:
            last_error = str(e)
            continue
            
    return f"❌ Fout bij aanroepen van AI Agents: {last_error}"

# --- HOOFDPROGRAMMA: DE 5-AGENT KETTING ---
st.markdown("### 🤖 Start de 5-Agent Intelligence Ketting")
st.markdown("Druk op de knop hieronder om alle 5 de agents achter elkaar te laten samenwerken: van nieuwsverzameling tot eindcontrole.")

if st.button("🚀 Start Volledige 5-Agent Analyse", type="primary"):
    if not api_key_input:
        st.error("Voer eerst je permanente API Key in via de zijbalk.")
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
            
            Controleer kritisch of deze berichten betrouwbaar zijn of dat het kan gaan om onbevestigde geruchten of paniekzaaierij.
            Geef elk belangrijk punt een duidelijk stempel:
            - ✅ Betrouwbaar / Waarschijnlijk
            - ⚠️ Onbevestigd Gerucht (Voorzichtig!)
            - ❌ Onbetrouwbaar / Speculatie
            
            TAAL & STIJL:
            - Schrijf in helder, simpel Nederlands.
            """
            agent3_output = run_gemini_agent(prompt_agent3, "Je bent een strenge factchecker die geruchten en speculaties kritisch bekijkt.")

        # --- AGENT 4 ---
        with st.spinner("💡 Agent 4 is bezig: Concreet beleggingsadvies in simpele taal opstellen..."):
            prompt_agent4 = f"""
            Jij bent Agent 4: Master Strategy & Plain-Dutch Investment Advisor (De Hoofd-Adviseur).
            Gebruik de inzichten van Agent 3 om een helder, praktisch advies op te stellen in simpele Jip-en-Janneketaal voor een niet-econoom.
            
            Geef antwoord op:
            1. Wat betekent dit voor **Goud & Zilver** (zowel in USD als Gram in Turkse Lira)?
            2. Wat betekent dit voor de **BIST 100 en jouw geselecteerde aandelen ({tickers_clean})**? (Kopen, Vasthouden, Winst nemen of Even afwachten — inclusief een simpele "Waarom?").
            3. Wat is de verwachting voor de korte termijn?
            """
            agent4_output = run_gemini_agent(prompt_agent4, "Je bent een toegankelijke beleggingsadviseur die complexe marktinformatie vertaalt naar begrijpelijke mensentaal.")

        # --- AGENT 5 ---
        with st.spinner("⚖️ Agent 5 is bezig: Eindcontrole en risico-audit uitvoeren (Devil's Advocate)..."):
            prompt_agent5 = f"""
            Jij bent Agent 5: Chief Auditor & Strategy Controller (De Eind-Controleur / Devil's Advocate).
            Jij controleert het werk van Agent 1, 2, 3 en het advies van Agent 4.
            - Agent 4 advies: {agent4_output}
            
            Controleer kritisch op blinde vlekken of risico's en geef een definitief, gecontroleerd eindoordeel in simpele taal.
            """
            agent5_output = run_gemini_agent(prompt_agent5, "Je bent een kritische risicocontroleur en eindbaas die alle beleggingsadviezen streng narekent op risico's.")

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
    st.info("👈 Voer je permanente API-sleutel in de zijbalk in, kies je favoriete aandelen en klik op de knop hierboven om de scanner te starten!")
