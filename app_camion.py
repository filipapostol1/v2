from datetime import datetime
import os
import requests
import streamlit as st
from fpdf import FPDF

# 1. CONFIGURAZIONE PAGINA
st.set_page_config(
    page_title="LogiCalc - Gestione Tratte Camion", page_icon="🚛", layout="wide"
)

# Custom CSS per lo stile dell'interfaccia web
st.markdown(
    """
    <style>
    .main { padding: 2rem; }
    .stButton>button { width: 100%; border-radius: 8px; height: 3em; font-weight: bold; }
    </style>
""",
    unsafe_allow_html=True,
)


# 2. FUNZIONI API (GEOLOCALIZZAZIONE E ROTTA)
def ottieni_coordinate(citta):
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
    url = f"http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=false"
    try:
        response = requests.get(url).json()
        if response and "routes" in response and len(response["routes"]) > 0:
            distanza_m = response["routes"][0]["distance"]
            durata_s = response["routes"][0]["duration"]

            km = round(distanza_m / 1000, 1)
            ore = int(durata_s // 3600)
            minuti = int((durata_s % 3600) // 60)
            tempo_str = f"{ore}h {minuti}m" if ore > 0 else f"{minuti}m"

            return km, tempo_str
    except Exception:
        return None, None
    return None, None


# 3. INTERFACCIA STREAMLIT
st.title("🚛 LogiCalc B2B — Calcolatore Tratte & Preventivi")
st.caption("Software di calcolo margini e generazione preventivi ufficiali")
st.markdown("---")

col_left, col_right = st.columns([1, 1], gap="large")

with col_left:
    st.subheader("📍 Dettagli del Viaggio")
    partenza = st.text_input("Città di Partenza", value="Milano")
    destinazione = st.text_input("Città di Arrivo", value="Roma")

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
            with st.spinner("Calcolo rotta stradale e generazione layout PDF..."):
                lat1, lon1 = ottieni_coordinate(partenza)
                lat2, lon2 = ottieni_coordinate(destinazione)

                if lat1 and lat2:
                    km, tempo = calcola_rotta(lat1, lon1, lat2, lon2)

                    if km:
                        costo_tratta = km * tariffa_km
                        totale_viaggio = costo_tratta + spese_extra

                        # Display Metriche web
                        m1, m2, m3 = st.columns(3)
                        m1.metric("Distanza Reale", f"{km} Km")
                        m2.metric("Tempo Stimato", tempo)
                        m3.metric("Totale Incasso", f"€ {totale_viaggio:.2f}")

                        st.success("✅ Rotta calcolata con successo!")

                        # ==========================================
                        # 📄 GENERAZIONE PDF SCHEMATIZATO E PROF
                        # ==========================================
                        pdf = FPDF()
                        pdf.add_page()
                        pdf.set_auto_page_break(auto=True, margin=15)

                        # LOGO AZIENDALE (Se presente)
                        if os.path.exists("logo.png"):
                            pdf.image("logo.png", x=10, y=10, w=35)
                        elif os.path.exists("logo.jpg"):
                            pdf.image("logo.jpg", x=10, y=10, w=35)

                        # INTESTAZIONE DESTRO (Titolo e Data)
                        pdf.set_font("Arial", "B", 16)
                        pdf.set_text_color(30, 58, 138)  # Blu scuro B2B
                        pdf.cell(
                            0,
                            8,
                            "PREVENTIVO DI TRASPORTO",
                            ln=True,
                            align="R",
                        )

                        pdf.set_font("Arial", "", 9)
                        pdf.set_text_color(100, 100, 100)
                        data_oggi = datetime.now().strftime("%d/%m/%Y")
                        codice_ref = f"PREV-{datetime.now().strftime('%Y%m%d')}-{int(km)}"
                        pdf.cell(
                            0,
                            5,
                            f"Data: {data_oggi} | Rif: {codice_ref}",
                            ln=True,
                            align="R",
                        )
                        pdf.ln(12)

                        # SCHEDA DETTAGLI TRASPORTO (Box Grigio)
                        pdf.set_fill_color(241, 245, 249)
                        pdf.set_draw_color(203, 213, 225)
                        pdf.set_font("Arial", "B", 10)
                        pdf.set_text_color(30, 58, 138)
                        pdf.cell(
                            0,
                            7,
                            "  1. DETTAGLI DELLA TRATTA",
                            ln=True,
                            fill=True,
                            border=1,
                        )

                        pdf.set_font("Arial", "", 10)
                        pdf.set_text_color(15, 23, 42)
                        pdf.cell(
                            95,
                            8,
                            f"  Partenza: {partenza.title()}",
                            border="L",
                        )
                        pdf.cell(
                            95,
                            8,
                            f"  Destinazione: {destinazione.title()}",
                            border="R",
                            ln=True,
                        )
                        pdf.cell(
                            95, 8, f"  Distanza calcolata: {km} Km", border="LB"
                        )
                        pdf.cell(
                            95,
                            8,
                            f"  Tempo di percorrenza stimato: {tempo}",
                            border="RB",
                            ln=True,
                        )

                        pdf.ln(8)

                        # TABELLA PRODOTTI / COSTI
                        pdf.set_fill_color(30, 58, 138)
                        pdf.set_text_color(255, 255, 255)
                        pdf.set_font("Arial", "B", 10)

                        # Header Tabella
                        pdf.cell(90, 8, "  Descrizione Servizio", border=1, fill=True)
                        pdf.cell(30, 8, "Q.ta / Km", border=1, fill=True, align="C")
                        pdf.cell(35, 8, "Prezzo Unit.", border=1, fill=True, align="C")
                        pdf.cell(35, 8, "Importo", border=1, fill=True, align="C", ln=True)

                        # Righe Tabella
                        pdf.set_text_color(15, 23, 42)
                        pdf.set_font("Arial", "", 10)

                        # Riga 1: Trasporto
                        pdf.cell(90, 8, "  Trasporto stradale merci", border=1)
                        pdf.cell(30, 8, f"{km} Km", border=1, align="C")
                        pdf.cell(35, 8, f"E {tariffa_km:.2f} /Km", border=1, align="C")
                        pdf.cell(35, 8, f"E {costo_tratta:.2f}", border=1, align="R", ln=True)

                        # Riga 2: Pedaggi / Extra
                        pdf.cell(90, 8, "  Pedaggi autostradali & costi accessori", border=1)
                        pdf.cell(30, 8, "1", border=1, align="C")
                        pdf.cell(35, 8, f"E {spese_extra:.2f}", border=1, align="C")
                        pdf.cell(35, 8, f"E {spese_extra:.2f}", border=1, align="R", ln=True)

                        # BOX TOTALE
                        pdf.ln(4)
                        pdf.set_font("Arial", "B", 11)
                        pdf.cell(120, 10, "", border=0)  # Spazio vuoto a sinistra
                        pdf.set_fill_color(224, 231, 255)
                        pdf.set_draw_color(30, 58, 138)
                        pdf.cell(
                            70,
                            10,
                            f" TOTALE PREVENTIVO: E {totale_viaggio:.2f}",
                            border=1,
                            fill=True,
                            align="C",
                            ln=True,
                        )

                        # NOTE FINALI IN PIE DI PAGINA
                        pdf.ln(12)
                        pdf.set_font("Arial", "I", 8)
                        pdf.set_text_color(100, 116, 139)
                        pdf.cell(
                            0,
                            4,
                            "Note: Il presente preventivo ha validita 30 giorni dalla data di emissione.",
                            ln=True,
                        )
                        pdf.cell(
                            0,
                            4,
                            "I tempi di percorrenza sono stime basate sulle condizioni di traffico standard.",
                            ln=True,
                        )
                        pdf.cell(
                            0,
                            4,
                            "Documento generato automaticamente via sistema LogiCalc B2B.",
                            ln=True,
                        )

                        # Output PDF
                        pdf_out = pdf.output(dest="S")
                        pdf_bytes = (
                            pdf_out.encode("latin-1", errors="replace")
                            if isinstance(pdf_out, str)
                            else bytes(pdf_out)
                        )

                        st.markdown("---")
                        st.download_button(
                            label="📄 SCARICA PREVENTIVO UFFICIALE (PDF)",
                            data=pdf_bytes,
                            file_name=f"Preventivo_{partenza}_{destinazione}.pdf",
                            mime="application/pdf",
                        )
                    else:
                        st.error("Impossibile calcolare la rotta tra queste due località.")
                else:
                    st.error("Una o entrambe le città non sono state trovate.")
    else:
        st.info("Compila i dati a sinistra e clicca sul pulsante per calcolare il preventivo.")
