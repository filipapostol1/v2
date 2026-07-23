from datetime import datetime
import os
import requests
import streamlit as st
from fpdf import FPDF

# 1. CONFIGURAZIONE PAGINA
st.set_page_config(
    page_title="LogiCalc B2B - Calcolo Tratte & Preventivi",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Custom CSS per un'interfaccia sobria e professionale
st.markdown(
    """
    <style>
    .main { padding: 2rem; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    .stButton>button { 
        width: 100%; 
        border-radius: 4px; 
        height: 2.8em; 
        font-weight: 600; 
        background-color: #1e3a8a; 
        color: white; 
        border: none;
    }
    .stButton>button:hover { background-color: #1e293b; color: white; }
    div[data-testid="stMetricValue"] { font-size: 1.8rem; font-weight: 700; color: #0f172a; }
    </style>
""",
    unsafe_allow_html=True,
)


# 2. FUNZIONI API (GEOLOCALIZZAZIONE E CALCOLO DISTANZA)
def ottieni_coordinate(indirizzo):
    """Richiede le coordinate geografiche tramite OpenStreetMap Nominatim."""
    url = f"https://nominatim.openstreetmap.org/search?q={indirizzo}&format=json&limit=1"
    headers = {"User-Agent": "LogiCalcB2B/1.0"}
    try:
        response = requests.get(url, headers=headers).json()
        if response:
            return float(response[0]["lat"]), float(response[0]["lon"])
    except Exception:
        return None, None
    return None, None


def calcola_rotta(lat1, lon1, lat2, lon2):
    """Calcola esclusivamente la distanza stradale (Km) tramite OSRM."""
    url = f"http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=false"
    try:
        response = requests.get(url).json()
        if response and "routes" in response and len(response["routes"]) > 0:
            distanza_m = response["routes"][0]["distance"]
            km = round(distanza_m / 1000, 1)
            return km
    except Exception:
        return None
    return None


# 3. INTERFACCIA UTENTE (STREAMLIT)
st.title("LogiCalc B2B - Sistema Calcolo Tratte e Preventivi")
st.caption("Piattaforma professionale per la stima dei costi di trasporto stradale")
st.markdown("---")

col_left, col_right = st.columns([1, 1], gap="large")

with col_left:
    st.subheader("Dettagli della Tratta")

    partenza = st.text_input(
        "Indirizzo / Città di Partenza",
        value="Via Roma 1, Milano",
        help="Inserire l'indirizzo completo o la città di origine.",
    )
    destinazione = st.text_input(
        "Indirizzo / Città di Arrivo",
        value="Via Nazionale 10, Roma",
        help="Inserire l'indirizzo completo o la città di destinazione.",
    )

    st.subheader("Parametri Economici")
    col_e1, col_e2 = st.columns(2)
    with col_e1:
        tariffa_km = st.number_input(
            "Tariffa per Chilometro (EUR)",
            value=1.65,
            step=0.05,
            format="%.2f",
        )
    with col_e2:
        spese_extra = st.number_input(
            "Pedaggi e Costi Accessori (EUR)",
            value=50.0,
            step=10.0,
            format="%.2f",
        )

    st.markdown("###")
    calcola_btn = st.button("CALCOLA PREVENTIVO E DISTANZA", type="primary")

with col_right:
    st.subheader("Riepilogo Elaborazione")

    if calcola_btn:
        if not partenza or not destinazione:
            st.error("Errore: inserire sia il punto di partenza sia la destinazione.")
        else:
            with st.spinner("Calcolo distanza e generazione documento in corso..."):
                lat1, lon1 = ottieni_coordinate(partenza)
                lat2, lon2 = ottieni_coordinate(destinazione)

                if lat1 and lat2:
                    km = calcola_rotta(lat1, lon1, lat2, lon2)

                    if km:
                        costo_tratta = km * tariffa_km
                        totale_viaggio = costo_tratta + spese_extra

                        # Visualizzazione Metrime (Solo Distanza e Importo)
                        m1, m2 = st.columns(2)
                        m1.metric("Distanza Totale", f"{km} Km")
                        m2.metric("Importo Totale", f"EUR {totale_viaggio:.2f}")

                        st.success("Calcolo della distanza eseguito con successo.")

                        # ==========================================
                        # GENERAZIONE DOCUMENTO PDF FORMALE
                        # ==========================================
                        pdf = FPDF()
                        pdf.add_page()
                        pdf.set_auto_page_break(auto=True, margin=15)

                        # LOGO AZIENDALE (se presente nella cartella)
                        if os.path.exists("logo.png"):
                            pdf.image("logo.png", x=12, y=10, w=35)
                        elif os.path.exists("logo.jpg"):
                            pdf.image("logo.jpg", x=12, y=10, w=35)

                        # INTESTAZIONE DOCUMENTO
                        pdf.set_font("Arial", "B", 15)
                        pdf.set_text_color(30, 58, 138)  # Blu Istituzionale
                        pdf.cell(
                            0,
                            8,
                            "PREVENTIVO DI TRASPORTO MERCI",
                            ln=True,
                            align="R",
                        )

                        pdf.set_font("Arial", "", 9)
                        pdf.set_text_color(100, 116, 139)
                        data_oggi = datetime.now().strftime("%d/%m/%Y")
                        codice_ref = f"PRV-{datetime.now().strftime('%Y%m%d')}-{int(km)}"
                        pdf.cell(
                            0,
                            5,
                            f"Data di emissione: {data_oggi} | Riferimento: {codice_ref}",
                            ln=True,
                            align="R",
                        )
                        pdf.ln(14)

                        # SEZIONE 1: DATI DEL TRASPORTO
                        pdf.set_fill_color(241, 245, 249)
                        pdf.set_draw_color(203, 213, 225)
                        pdf.set_font("Arial", "B", 10)
                        pdf.set_text_color(30, 58, 138)
                        pdf.cell(
                            0,
                            7,
                            "  1. SPECIFICHE DEL TRAGITTO",
                            ln=True,
                            fill=True,
                            border=1,
                        )

                        pdf.set_font("Arial", "", 9)
                        pdf.set_text_color(15, 23, 42)
                        pdf.cell(
                            95,
                            8,
                            f"  Origine: {partenza.title()}",
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
                            190,
                            8,
                            f"  Distanza percorsa calcolata: {km} Km",
                            border="LBR",
                            ln=True,
                        )

                        pdf.ln(8)

                        # SEZIONE 2: PROSPETTO ECONOMICO
                        pdf.set_fill_color(30, 58, 138)
                        pdf.set_text_color(255, 255, 255)
                        pdf.set_font("Arial", "B", 9)

                        # Intestazione Tabella
                        pdf.cell(90, 8, "  Descrizione Voce", border=1, fill=True)
                        pdf.cell(30, 8, "Quantita", border=1, fill=True, align="C")
                        pdf.cell(35, 8, "Prezzo Unitario", border=1, fill=True, align="C")
                        pdf.cell(35, 8, "Importo Totale", border=1, fill=True, align="C", ln=True)

                        # Corpo Tabella
                        pdf.set_text_color(15, 23, 42)
                        pdf.set_font("Arial", "", 9)

                        # Voce 1: Chilometraggio
                        pdf.cell(90, 8, "  Servizio di trasporto stradale", border=1)
                        pdf.cell(30, 8, f"{km} Km", border=1, align="C")
                        pdf.cell(35, 8, f"EUR {tariffa_km:.2f}", border=1, align="C")
                        pdf.cell(35, 8, f"EUR {costo_tratta:.2f}", border=1, align="R", ln=True)

                        # Voce 2: Pedaggi / Oneri Accessori
                        pdf.cell(90, 8, "  Pedaggi autostradali e oneri accessori", border=1)
                        pdf.cell(30, 8, "1 A corpo", border=1, align="C")
                        pdf.cell(35, 8, f"EUR {spese_extra:.2f}", border=1, align="C")
                        pdf.cell(35, 8, f"EUR {spese_extra:.2f}", border=1, align="R", ln=True)

                        # TOTALE PREVENTIVO
                        pdf.ln(4)
                        pdf.set_font("Arial", "B", 10)
                        pdf.cell(120, 9, "", border=0)
                        pdf.set_fill_color(224, 231, 255)
                        pdf.set_draw_color(30, 58, 138)
                        pdf.cell(
                            70,
                            9,
                            f" TOTALE NETTO: EUR {totale_viaggio:.2f}",
                            border=1,
                            fill=True,
                            align="C",
                            ln=True,
                        )

                        # CONDIZIONI E NOTE LEGALI
                        pdf.ln(12)
                        pdf.set_font("Arial", "B", 8)
                        pdf.set_text_color(71, 85, 105)
                        pdf.cell(0, 4, "Condizioni di Fornitura:", ln=True)
                        pdf.set_font("Arial", "", 8)
                        pdf.set_text_color(100, 116, 139)
                        pdf.cell(
                            0,
                            4,
                            "1. Il presente preventivo ha validita pari a 30 giorni dalla data di emissione.",
                            ln=True,
                        )
                        pdf.cell(
                            0,
                            4,
                            "2. Documento elaborato tramite sistema aziendale automatizzato LogiCalc B2B.",
                            ln=True,
                        )

                        # Conversione PDF
                        pdf_out = pdf.output(dest="S")
                        pdf_bytes = (
                            pdf_out.encode("latin-1", errors="replace")
                            if isinstance(pdf_out, str)
                            else bytes(pdf_out)
                        )

                        st.markdown("---")
                        st.download_button(
                            label="SCARICA PREVENTIVO UFFICIALE (PDF)",
                            data=pdf_bytes,
                            file_name=f"Preventivo_{partenza.split(',')[0]}_{destinazione.split(',')[0]}.pdf",
                            mime="application/pdf",
                        )
                    else:
                        st.error("Impossibile calcolare il percorso tra le località specificate.")
                else:
                    st.error("Impossibile individuare gli indirizzi indicati. Verificare la correttezza dei dati.")
    else:
        st.info("Compilare i campi a sinistra per generare la stima e il relativo preventivo.")
