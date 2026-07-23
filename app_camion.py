import os
import requests
import streamlit as st
from fpdf import FPDF

# 1. CONFIGURAZIONE PAGINA
st.set_page_config(
    page_title="LogiCalc - Gestione Tratte Camion", page_icon="🚛", layout="wide"
)

# Custom CSS per lo stile dell'interfaccia
st.markdown(
    """
    <style>
    .main { padding: 2rem; }
    .stButton>button { width: 100%; border-radius: 8px; height: 3em; font-weight: bold; }
    </style>
""",
    unsafe_allow_html=True,
)


# 2. FUNZIONI DI GEOLOCALIZZAZIONE E CALCOLO ROTTA (API GRATUITE)
def ottieni_coordinate(citta):
    """Ottiene Latitudine e Longitudine da un nome di città (OpenStreetMap)"""
    url = f"https://nominatim.openstreetmap.org/search?q={citta}&format=json&limit=1"
    headers = {"User-Agent": "LogiCalcApp/1.0"}
    try:
        response = requests.get(url, headers=headers).json()
        if response:
            return float(response[0]["lat"]), float(response[0]["lon"])
    except Exception:
        return None, None
    return None, None


def calcola_rotta(lat1, lon1, lat2, lon2):
    """Calcola distanza (in km) e tempo reale tramite OSRM"""
    url = f"http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=false"
    try:
        response = requests.get(url).json()
        if response and "routes" in response and len(response["routes"]) > 0:
            distanza_m = response["routes"][0]["distance"]
            durata_s = response["routes"][0]["duration"]

            km = round(distanza_m / 1000, 1)

            # Conversione secondi in ore e minuti
            ore = int(durata_s // 3600)
            minuti = int((durata_s % 3600) // 60)
            tempo_str = f"{ore}h {minuti}m" if ore > 0 else f"{minuti}m"

            return km, tempo_str
    except Exception:
        return None, None
    return None, None


# 3. INTERFACCIA UTENTE (STREAMLIT)
st.title("🚛 LogiCalc B2B — Calcolatore Tratte & Preventivi")
st.caption("Software di calcolo margini per trasporti su gomma")
st.markdown("---")

col_left, col_right = st.columns([1, 1], gap="large")

with col_left:
    st.subheader("📍 Dettagli del Viaggio")

    partenza = st.text_input(
        "Città di Partenza", value="Milano", help="Es. Milano, Roma, Bologna..."
    )
    destinazione = st.text_input(
        "Città di Arrivo", value="Roma", help="Es. Napoli, Verona, Bari..."
    )

    st.subheader("💶 Parametri Economici")
    col_e1, col_e2 = st.columns(2)
    with col_e1:
        tariffa_km = st.number_input(
            "Tariffa / Km (€)", value=1.65, step=0.05, format="%.2f"
        )
    with col_e2:
        spese_extra = st.number_input(
            "Spese Extra / Pedaggi (€)", value=50.0, step=10.0, format="%.2f"
        )

    st.markdown("###")
    calcola_btn = st.button("🚀 CALCOLA PREZZO E DISTANZA", type="primary")

with col_right:
    st.subheader("📊 Risultato & Preventivo")

    if calcola_btn:
        if not partenza or not destinazione:
            st.error("Inserisci sia la città di partenza che quella di destinazione.")
        else:
            with st.spinner("Calcolo rotta stradale in corso..."):
                lat1, lon1 = ottieni_coordinate(partenza)
                lat2, lon2 = ottieni_coordinate(destinazione)

                if lat1 and lat2:
                    km, tempo = calcola_rotta(lat1, lon1, lat2, lon2)

                    if km:
                        # Calcolo Totale al centesimo
                        totale_viaggio = (km * tariffa_km) + spese_extra

                        # Display Metriche
                        m1, m2, m3 = st.columns(3)
                        m1.metric("Distanza Reale", f"{km} Km")
                        m2.metric("Tempo Stimato", tempo)
                        m3.metric("Totale Incasso", f"€ {totale_viaggio:.2f}")

                        st.success("✅ Rotta calcolata con successo!")

                        # --- GENERAZIONE PDF ---
                        pdf = FPDF()
                        pdf.add_page()

                        # Inserimento Logo (se presente nella stessa cartella del file)
                        if os.path.exists("logo.png"):
                            pdf.image("logo.png", x=10, y=8, w=35)
                        elif os.path.exists("logo.jpg"):
                            pdf.image("logo.jpg", x=10, y=8, w=35)

                        pdf.set_font("Arial", "B", 18)
                        pdf.ln(10)
                        pdf.cell(
                            0, 15, "PREVENTIVO TRASPORTO MERCI", ln=True, align="C"
                        )
                        pdf.set_font("Arial", "I", 10)
                        pdf.cell(
                            0,
                            5,
                            "Documento generato automaticamente da LogiCalc",
                            ln=True,
                            align="C",
                        )
                        pdf.ln(15)

                        # Dettagli Preventivo
                        pdf.set_font("Arial", size=12)
                        pdf.cell(
                            0,
                            10,
                            f"Tratta: {partenza.upper()} -> {destinazione.upper()}",
                            ln=True,
                        )
                        pdf.cell(0, 10, f"Distanza Calcolata: {km} Km", ln=True)
                        pdf.cell(
                            0,
                            10,
                            f"Tempo Stimato di Percorrenza: {tempo}",
                            ln=True,
                        )
                        pdf.cell(
                            0,
                            10,
                            f"Tariffa applicata: {tariffa_km:.2f} Euro/Km",
                            ln=True,
                        )
                        pdf.cell(
                            0,
                            10,
                            f"Costi Extra / Pedaggi: {spese_extra:.2f} Euro",
                            ln=True,
                        )
                        pdf.ln(10)

                        pdf.set_font("Arial", "B", 14)
                        pdf.cell(
                            0,
                            12,
                            f"TOTALE PREVENTIVO: Euro {totale_viaggio:.2f}",
                            border=1,
                            ln=True,
                            align="C",
                        )

                        # Conversione PDF per Streamlit
                        pdf_out = pdf.output(dest="S")
                        if isinstance(pdf_out, str):
                            pdf_bytes = pdf_out.encode("latin-1", errors="replace")
                        else:
                            pdf_bytes = bytes(pdf_out)

                        st.markdown("---")
                        st.download_button(
                            label="📄 SCARICA PREVENTIVO PDF",
                            data=pdf_bytes,
                            file_name=f"Preventivo_{partenza}_{destinazione}.pdf",
                            mime="application/pdf",
                        )
                    else:
                        st.error(
                            "Impossibile calcolare la rotta tra queste due località."
                        )
                else:
                    st.error(
                        "Una o entrambe le città non sono state trovate. Verifica la grafia."
                    )
    else:
        st.info(
            "Compila i dati a sinistra e clicca sul pulsante per calcolare il preventivo."
        )
