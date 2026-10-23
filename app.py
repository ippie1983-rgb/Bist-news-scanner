
import json
import urllib.request
import urllib.error

import streamlit as st
import yfinance as yf

# =========================================================
# BIST & EDELMETALEN SCANNER — 5 AI AGENTS
# =========================================================

st.set_page_config(
    page_title="BIST & Edelmetalen 5-Agent Scanner",
    page_icon="🇹🇷",
    layout="wide"
)

st.markdown("""
<style>
.main-header {
    font-size: 26px;
    font-weight: bold;
    color: #1E3A8A;
}
div[data-testid="stMetricValue"] {
    font-size: 22px !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown(
    '<p class="main-header">🇹🇷 BIST & Edelmetalen 5-Agent Scanner</p>',
    unsafe_allow_html=True
)
st.markdown(
    "Nieuws, marktanalyses, fact-checks en risicoanalyse voor "
    "**Borsa Istanbul, goud en zilver**."
)

# =========================================================
# INSTELLINGEN
# =========================================================

if "aq_token" not in st.session_state:
    st.session_state.aq_token = ""

st.sidebar.header("⚙️ Systeem & AI-instellingen")

st.session_state.aq_token = st.sidebar.text_input(
    "Gemini API Key:",
    type="password",
    value=st.session_state.aq_token,
    help="Vul hier je geldige Google Gemini API-sleutel in."
)

if st.session_state.aq_token.strip():
    st.sidebar.success("Sleutel ingevoerd. Geldigheid wordt bij gebruik getest.")
else:
    st.sidebar.info("Vul je API-sleutel in om de agents te starten.")

st.sidebar.markdown("---")
st.sidebar.subheader("🎯 Aandelenselectie")

available_tickers = [
    "THYAO (Turkish Airlines)",
    "ASELS (Aselsan)",
    "KCHOL (Koç Holding)",
    "AKBNK (Akbank)",
    "TUPRS (Tüpraş)",
    "BIMAS (Bim)",
    "SASA (Sasa Polyester)",
    "GARAN (Garanti BBVA)",
    "SISE (Şişecam)",
    "PETKM (Petkim)"
]

selected_tickers = st.sidebar.multiselect(
    "Kies BIST-aandelen:",
    available_tickers,
    default=[
        "THYAO (Turkish Airlines)",
        "ASELS (Aselsan)",
        "KCHOL (Koç Holding)",
        "SISE (Şişecam)",
        "PETKM (Petkim)"
    ]
)

# =========================================================
# MARKTINDICATOREN
# =========================================================

st.markdown("### 📊 Markt- en prijsindicaties")

ticker_symbols = {
    "BIST 100": "XU100.IS",
    "USD/TRY": "USDTRY=X",
    "EUR/TRY": "EURTRY=X",
    "Goud ons ($)": "GC=F",
    "Zilver ons ($)": "SI=F",
    "Brent olie ($)": "BZ=F",
    "VIX (angstindex)": "^VIX"
}


def render_tickers(items):
    columns = st.columns(4)

    for i, (name, symbol) in enumerate(items):
        with columns[i % 4]:
            try:
                data = yf.Ticker(symbol).history(
                    period="5d",
                    auto_adjust=False
                )

                if data.empty or "Close" not in data:
                    st.metric(name, "N/B")
                    continue

                prices = data["Close"].dropna()

                if prices.empty:
                    st.metric(name, "N/B")
                    continue

                current = float(prices.iloc[-1])

                if len(prices) >= 2:
                    previous = float(prices.iloc[-2])
                    change = (
                        (current - previous) / previous * 100
                        if previous != 0 else 0
                    )
                    st.metric(
                        name,
                        f"{current:,.2f}",
                        f"{change:+.2f}%"
                    )
                else:
                    st.metric(name, f"{current:,.2f}")

            except Exception:
                st.metric(name, "Niet beschikbaar")


render_tickers(list(ticker_symbols.items()))

st.caption(
    "Marktgegevens van Yahoo Finance kunnen vertraagd zijn. "
    "Controleer actuele beurskoersen bij je broker."
)

st.markdown("---")

# =========================================================
# GEMINI API — AUTHENTICATIE EN FOUTAFHANDELING
# =========================================================

def run_gemini_agent(prompt_text, system_instruction=""):
    token = st.session_state.aq_token.strip()

    if not token:
        raise RuntimeError("Geen API-sleutel ingevuld.")

    # Gebruik eerst het primaire model.
    # Een tweede model wordt alleen geprobeerd bij een modelprobleem,
    # niet bij een ongeldige sleutel of ontbrekende rechten.
    models = ["gemini-2.5-flash"]

    last_error = "Onbekende fout."

    for model_name in models:
        url = (
            "https://generativelanguage.googleapis.com/v1beta/"
            f"models/{model_name}:generateContent"
        )

        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": token
        }

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt_text}]
                }
            ],
            "generationConfig": {
                "temperature": 0.2
            }
        }

        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST"
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=60
            ) as response:
                result = json.loads(
                    response.read().decode("utf-8")
                )

            candidates = result.get("candidates", [])

            if not candidates:
                raise RuntimeError(
                    "Gemini heeft geen analyse teruggegeven."
                )

            parts = candidates[0].get("content", {}).get("parts", [])

            answer = "\n".join(
                part["text"]
                for part in parts
                if "text" in part
            ).strip()

            if not answer:
                raise RuntimeError(
                    "Gemini heeft een leeg antwoord teruggegeven."
                )

            return answer

        except urllib.error.HTTPError as error:
            details = error.read().decode(
                "utf-8", errors="replace"
            )

            try:
                parsed = json.loads(details)
                details = parsed.get("error", {}).get(
                    "message", details
                )
            except (json.JSONDecodeError, AttributeError):
                pass

            last_error = f"HTTP {error.code}: {details}"

            if error.code in (400, 401, 403):
                break

            if error.code not in (404, 429, 500, 502, 503):
                break

        except urllib.error.URLError as error:
            last_error = f"Verbindingsfout: {error.reason}"
            break

        except (json.JSONDecodeError, KeyError, IndexError) as error:
            last_error = f"Onverwacht API-antwoord: {error}"
            break

        except TimeoutError:
            last_error = "De verbinding duurde te lang."
            break

        except Exception as error:
            last_error = str(error)
            break

    raise RuntimeError(
        f"Gemini-aanroep mislukt. {last_error}"
    )


# =========================================================
# START VAN DE VIJF AGENTS
# =========================================================

st.markdown("### 🤖 De 5-Agent Intelligence-ketting")

st.write(
    "Agent 1 onderzoekt Turkije en BIST. Agent 2 onderzoekt "
    "de wereldmarkt. Agent 3 controleert de beweringen. "
    "Agent 4 maakt een analyse en Agent 5 controleert de risico's."
)

start_analysis = st.button(
    "🚀 Start volledige 5-Agent analyse",
    type="primary"
)

if start_analysis:

    if not st.session_state.aq_token.strip():
        st.error("Vul eerst je Gemini API-sleutel in.")
        st.stop()

    if not selected_tickers:
        st.warning("Selecteer minimaal één aandeel.")
        st.stop()

    tickers_clean = [
        ticker.split(" ")[0]
        for ticker in selected_tickers
    ]
    tickers_str = ", ".join(tickers_clean)

    try:
        # AGENT 1
        with st.spinner(
            "🇹🇷 Agent 1: Turkije, politiek en BIST onderzoeken..."
        ):
            agent1_output = run_gemini_agent(
                f"""
Je bent Agent 1: Turkije- en BIST-analist.

Onderzoek de actuele situatie rond:
- De Turkse economie, inflatie, rente en wisselkoers.
- Politiek nieuws, toespraken, aanhoudingen en maatregelen.
- BIST, fondsschandalen en mogelijke gedwongen verkopen.
- De aandelen: {tickers_str}.

Gebruik actuele bronnen als je daar daadwerkelijk toegang toe hebt.
Verzin geen nieuws, koersen, cijfers of bronnen.
Vermeld datums en onderscheid feiten van verwachtingen.
Leg alles uit in begrijpelijk Nederlands.
""",
                "Je bent een kritische Turkije- en BIST-analist. "
                "Je verzint geen feiten."
            )

        # AGENT 2
        with st.spinner(
            "🌍 Agent 2: Wereldmarkt, goud en zilver onderzoeken..."
        ):
            agent2_output = run_gemini_agent(
                """
Je bent Agent 2: internationale macro- en edelmetaalanalist.

Onderzoek:
1. Geopolitiek en oorlogsdreiging.
2. Amerikaanse rente, inflatie en dollar.
3. Goud en zilver in USD en de mogelijke invloed op Turkse lira.
4. Internationale economische ontwikkelingen en verwachtingen.

Gebruik actuele bronnen als je daar daadwerkelijk toegang toe hebt.
Verzin geen actuele gebeurtenissen of analistenverwachtingen.
Vermeld onzekerheden en schrijf in eenvoudig Nederlands.
""",
                "Je bent een kritische internationale macro-econoom "
                "en edelmetaalanalist."
            )

        # AGENT 3
        with st.spinner(
            "🕵️ Agent 3: Feiten en bronnen controleren..."
        ):
            agent3_output = run_gemini_agent(
                f"""
Je bent Agent 3: de onafhankelijke factchecker.

Controleer deze bevindingen kritisch.

AGENT 1:
{agent1_output}

AGENT 2:
{agent2_output}

Beoordeel de belangrijkste beweringen afzonderlijk:
- Bevestigd door betrouwbare bronnen.
- Aannemelijk, maar niet voldoende bevestigd.
- Onbevestigd gerucht.
- Onjuist of misleidend.

Maak duidelijk welke beweringen je niet zelfstandig kunt verifiëren.
Neem beweringen van andere agents niet automatisch als waarheid aan.
Maak geen bronnen of bevestigingen op.
Schrijf in helder Nederlands.
""",
                "Je bent een strenge, onafhankelijke factchecker."
            )

        # AGENT 4
        with st.spinner(
            "💡 Agent 4: Beleggingsscenario's opstellen..."
        ):
            agent4_output = run_gemini_agent(
                f"""
Je bent Agent 4: beleggingsstrateeg.

Aandelen: {tickers_str}

INTERNATIONALE ANALYSE:
{agent2_output}

FEITENCONTROLE:
{agent3_output}

Geef per geselecteerd aandeel een scenario voor ongeveer
één maand:
- Positief scenario.
- Neutraal scenario.
- Negatief scenario.
- Welke feiten of cijfers het scenario kunnen veranderen.
- Kopen, vasthouden of afwachten, met duidelijke argumenten.

Bespreek ook goud en zilver.
Verzin geen actuele koersen, koersdoelen of kwartaalcijfers.
Als belangrijke gegevens ontbreken, vermeld dat uitdrukkelijk.
Maak duidelijk dat dit geen gegarandeerd rendement is.
Schrijf in eenvoudig Nederlands.
""",
                "Je bent een voorzichtige beleggingsstrateeg. "
                "Je benoemt zowel kansen als risico's."
            )

        # AGENT 5
        with st.spinner(
            "⚖️ Agent 5: Eindcontrole en risico-audit..."
        ):
            agent5_output = run_gemini_agent(
                f"""
Je bent Agent 5: onafhankelijke eindcontroleur.

Controleer het onderstaande advies op:
- Onbevestigde beweringen.
- Ontbrekende informatie.
- Tegenstrijdigheden.
- Te optimistische verwachtingen.
- Risico's van Turkse lira, politiek en beursliquiditeit.
- Mogelijke verliezen en alternatieve scenario's.

ADVIES:
{agent4_output}

FACTCHECK:
{agent3_output}

Geef een eindconclusie in begrijpelijk Nederlands.
Maak onderscheid tussen feiten, aannames en verwachtingen.
Presenteer het advies niet als zekerheid.
""",
                "Je bent een kritische risicocontroleur. "
                "Je verdoezelt onzekerheden nooit."
            )

        # RESULTATEN
        st.success(
            "Alle vijf agents hebben daadwerkelijk een antwoord teruggegeven."
        )

        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "🇹🇷 Agent 1: BIST",
            "🌍 Agent 2: Wereld",
            "🕵️ Agent 3: Fact-check",
            "💡 Agent 4: Advies",
            "⚖️ Agent 5: Eindcontrole"
        ])

        with tab1:
            st.markdown("### Turkije en BIST")
            st.markdown(agent1_output)

        with tab2:
            st.markdown("### Internationale markt")
            st.markdown(agent2_output)

        with tab3:
            st.markdown("### Feiten en bronnen")
            st.markdown(agent3_output)

        with tab4:
            st.markdown("### Beleggingsscenario's")
            st.markdown(agent4_output)

        with tab5:
            st.markdown("### Eindcontrole en risico's")
            st.markdown(agent5_output)

    except Exception as error:
        st.error(
            "De analyse is gestopt omdat een agent niet goed werkte."
        )
        st.code(str(error))
        st.info(
            "Controleer de foutmelding hierboven. De app meldt niet "
            "dat alle agents klaar zijn wanneer een stap mislukt."
        )

else:
    st.info(
        "Vul je API-sleutel in en klik op "
        "'Start volledige 5-Agent analyse'."
    )
