from datetime import datetime
import os
import requests
import streamlit as st
from fpdf import FPDF

# 1. CONFIGURAZIONE PAGINA STREAMLIT
st.set_page_config(
    page_title="LogiCalc B2B - Calcolo Tratte & Preventivi",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# TARIFFA AZIENDALE FISSA
TARIFFA_KM_FISSA = 1.65

# Custom CSS per l'interfaccia web
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


# 2. FUNZIONI API GEOLOCALIZZAZIONE E PERCORSO
def ottieni_coordinate(indirizzo):
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
    url = f"http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=false"
    try:
        response = requests.get(url).json()
        if response and "routes" in response and len(response["routes"]) > 0:
            distanza_m = response["routes"][0]["distance"]
            return round(distanza_m / 1000, 1)
    except Exception:
        return None
    return None


# 3. INTERFACCIA STREAMLIT
st.title("LogiCalc B2B - Sistema Calcolo Tratte e Preventivi")
st.caption("Piattaforma professionale per la stima dei costi di trasporto stradale")
st.markdown("---")

col_left, col_right = st.columns([1, 1], gap="large")

with col_left:
    st.subheader("Dati Anagrafici e Tratta")

    # NUOVO CAMPO: Nome Cliente / Mittente personalizzabile
    nome_mittente = st.text_input(
        "Nome Cliente / Mittente",
        value="ACME S.r.l.",
        help="Inserire la ragione sociale o il nome del cliente intestatario del documento.",
    )

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
        st.text_input(
            "Tariffa / Km (EUR)",
            value=f"{TARIFFA_KM_FISSA:.2f} (Fissa)",
            disabled=True,
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
                        costo_tratta = km * TARIFFA_KM_FISSA
                        totale_imponibile = costo_tratta + spese_extra
                        iva_22 = totale_imponibile * 0.22
                        totale_generale = totale_imponibile + iva_22

                        m1, m2 = st.columns(2)
                        m1.metric("Distanza Totale", f"{km} Km")
                        m2.metric("Totale Preventivo (IVA inc.)", f"EUR {totale_generale:.2f}")

                        st.success("Calcolo del preventivo completato.")

                        # ==========================================
                        # PDF STILE GESTIONALE / ERP ITALIANO
                        # ==========================================
                        pdf = FPDF(orientation="P", unit="mm", format="A4")
                        pdf.set_margins(10, 10, 10)
                        pdf.add_page()

                        # RICERCA E INSERIMENTO AUTOMATICO LOGO AZIENDALE
                        if os.path.exists("logo.jpg"):
                            pdf.image("logo.jpg", x=10, y=10, w=35)
                        elif os.path.exists("logo.png"):
                            pdf.image("logo.png", x=10, y=10, w=35)

                        # Intestazione Dati Azienda in alto a destra
                        pdf.set_font("Helvetica", "B", 12)
                        pdf.cell(0, 5, "LOGICALC LOGISTICS S.R.L.", ln=True, align="R")
                        pdf.set_font("Helvetica", "", 8)
                        pdf.cell(0, 4, "Via Trasporti Nazionali 15", ln=True, align="R")
                        pdf.cell(0, 4, "20100 Milano (MI) - P.IVA 01234567890", ln=True, align="R")
                        pdf.ln(6)

                        # Barra Titolo Documento
                        pdf.set_fill_color(220, 220, 220)
                        pdf.set_font("Helvetica", "B", 10)
                        pdf.cell(190, 6, " PREVENTIVO DI TRASPORTO / ORDINE", border=1, ln=True, fill=True)

                        # Box Intestatario e Luogo di Destinazione
                        y_boxes = pdf.get_y()
                        box_h = 24

                        pdf.rect(10, y_boxes, 95, box_h)
                        pdf.rect(105, y_boxes, 95, box_h)

                        # --- COLONNA SINISTRA: INTESTATARIO / ORIGINE ---
                        pdf.set_xy(12, y_boxes + 2)
                        pdf.set_font("Helvetica", "", 7)
                        pdf.set_text_color(100, 100, 100)
                        pdf.cell(91, 3, "INTESTATARIO / ORIGINE", ln=False)

                        # NOME MITTENTE PERSONALIZZATO
                        pdf.set_xy(12, y_boxes + 6)
                        pdf.set_font("Helvetica", "B", 8)
                        pdf.set_text_color(0, 0, 0)
                        valore_mittente = nome_mittente.strip().upper() if nome_mittente else "CLIENTE B2B"
                        pdf.cell(91, 4, valore_mittente, ln=False)

                        pdf.set_xy(12, y_boxes + 11)
                        pdf.set_font("Helvetica", "", 8)
                        pdf.multi_cell(91, 4, f"Partenza: {partenza.title()}")

                        # --- COLONNA DESTRA: LUOGO DI DESTINAZIONE ---
                        pdf.set_xy(107, y_boxes + 2)
                        pdf.set_font("Helvetica", "", 7)
                        pdf.set_text_color(100, 100, 100)
                        pdf.cell(91, 3, "LUOGO DI DESTINAZIONE", ln=False)

                        pdf.set_xy(107, y_boxes + 6)
                        pdf.set_font("Helvetica", "B", 8)
                        pdf.set_text_color(0, 0, 0)
                        pdf.cell(91, 4, "DESTINATARIO MERCI", ln=False)

                        pdf.set_xy(107, y_boxes + 11)
                        pdf.set_font("Helvetica", "", 8)
                        pdf.multi_cell(91, 4, f"Destinazione: {destinazione.title()}")

                        # Riposizionamento del cursore sotto i due box
                        pdf.set_xy(10, y_boxes + box_h)

                        # Griglia Dati Documento
                        pdf.set_font("Helvetica", "", 6)
                        pdf.set_text_color(80, 80, 80)

                        cols_w = [35, 30, 30, 45, 50]

                        pdf.cell(cols_w[0], 3, "NUMERO PREVENTIVO", border="LRT", align="C")
                        pdf.cell(cols_w[1], 3, "DATA DOC.", border="LRT", align="C")
                        pdf.cell(cols_w[2], 3, "COD. CLIENTE", border="LRT", align="C")
                        pdf.cell(cols_w[3], 3, "MODALITA DI PAGAMENTO", border="LRT", align="C")
                        pdf.cell(cols_w[4], 3, "DISTANZA CALCOLATA", border="LRT", align="C", ln=True)

                        pdf.set_font("Helvetica", "B", 8)
                        pdf.set_text_color(0, 0, 0)
                        data_oggi = datetime.now().strftime("%d/%m/%Y")
                        cod_ref = f"PRV-{int(km)}"

                        pdf.cell(cols_w[0], 5, cod_ref, border="LRB", align="C")
                        pdf.cell(cols_w[1], 5, data_oggi, border="LRB", align="C")
                        pdf.cell(cols_w[2], 5, "CLI-0012", border="LRB", align="C")
                        pdf.cell(cols_w[3], 5, "BONIFICO BANCARIO D.F.", border="LRB", align="C")
                        pdf.cell(cols_w[4], 5, f"{km} Km", border="LRB", align="C", ln=True)

                        pdf.ln(1)

                        # Intestazione Tabella Prodotti / Servizi
                        col_tbl = [20, 85, 12, 18, 22, 18, 15]
                        pdf.set_font("Helvetica", "B", 7)
                        pdf.set_fill_color(230, 230, 230)

                        pdf.cell(col_tbl[0], 5, "CODICE", border=1, align="C", fill=True)
                        pdf.cell(col_tbl[1], 5, "DESCRIZIONE", border=1, align="L", fill=True)
                        pdf.cell(col_tbl[2], 5, "U.M.", border=1, align="C", fill=True)
                        pdf.cell(col_tbl[3], 5, "QUANTITA", border=1, align="C", fill=True)
                        pdf.cell(col_tbl[4], 5, "PREZZO", border=1, align="C", fill=True)
                        pdf.cell(col_tbl[5], 5, "IMPONIBILE", border=1, align="C", fill=True)
                        pdf.cell(col_tbl[6], 5, "PERC IVA", border=1, align="C", fill=True, ln=True)

                        y_start_table = pdf.get_y()

                        # Righe della Tabella
                        pdf.set_font("Helvetica", "", 8)

                        # Riga 1: Trasporto
                        pdf.cell(col_tbl[0], 5, "TRASP-01", align="C")
                        pdf.cell(col_tbl[1], 5, "Servizio trasporto merci su strada", align="L")
                        pdf.cell(col_tbl[2], 5, "Km", align="C")
                        pdf.cell(col_tbl[3], 5, f"{km}", align="C")
                        pdf.cell(col_tbl[4], 5, f"{TARIFFA_KM_FISSA:.2f}", align="R")
                        pdf.cell(col_tbl[5], 5, f"{costo_tratta:.2f}", align="R")
                        pdf.cell(col_tbl[6], 5, "22%", align="C", ln=True)

                        # Riga 2: Pedaggi / Spese Extra
                        pdf.cell(col_tbl[0], 5, "PED-01", align="C")
                        pdf.cell(col_tbl[1], 5, "Pedaggi autostradali e spese accessorie", align="L")
                        pdf.cell(col_tbl[2], 5, "Pz", align="C")
                        pdf.cell(col_tbl[3], 5, "1", align="C")
                        pdf.cell(col_tbl[4], 5, f"{spese_extra:.2f}", align="R")
                        pdf.cell(col_tbl[5], 5, f"{spese_extra:.2f}", align="R")
                        pdf.cell(col_tbl[6], 5, "22%", align="C", ln=True)

                        # Griglia verticale continua (Stile ERP)
                        table_height = 140
                        pdf.rect(10, y_start_table, 190, table_height)

                        x_curr = 10
                        for w in col_tbl[:-1]:
                            x_curr += w
                            pdf.line(x_curr, y_start_table, x_curr, y_start_table + table_height)

                        pdf.set_xy(10, y_start_table + table_height + 2)

                        # Riquadro Totali in Basso
                        pdf.set_font("Helvetica", "", 6)
                        pdf.set_text_color(80, 80, 80)

                        pdf.cell(40, 3, "IMPONIBILE TRASPORTO", border="LRT", align="C")
                        pdf.cell(40, 3, "PEDAGGI / EXTRA", border="LRT", align="C")
                        pdf.cell(35, 3, "TOTALE IMPONIBILE", border="LRT", align="C")
                        pdf.cell(35, 3, "TOTALE IVA (22%)", border="LRT", align="C")
                        pdf.cell(40, 3, "TOTALE PREVENTIVO", border="LRT", align="C", ln=True)

                        pdf.set_font("Helvetica", "B", 8)
                        pdf.set_text_color(0, 0, 0)
                        pdf.cell(40, 5, f"Euro {costo_tratta:.2f}", border="LRB", align="C")
                        pdf.cell(40, 5, f"Euro {spese_extra:.2f}", border="LRB", align="C")
                        pdf.cell(35, 5, f"Euro {totale_imponibile:.2f}", border="LRB", align="C")
                        pdf.cell(35, 5, f"Euro {iva_22:.2f}", border="LRB", align="C")

                        pdf.set_font("Helvetica", "BI", 10)
                        pdf.cell(40, 5, f"Euro {totale_generale:.2f}", border="LRB", align="C", ln=True)

                        # Note Legali
                        pdf.ln(3)
                        pdf.set_font("Helvetica", "", 6)
                        pdf.set_text_color(100, 100, 100)
                        pdf.multi_cell(
                            190,
                            3,
                            "Privacy e Condizioni: Documento generato da sistema informativo B2B. I dati riportati sono da ritenersi "
                            "esclusivamente indicativi e soggetti a conferma all'atto del conferimento dell'ordine di trasporto. "
                            "Validita del presente preventivo: 30 giorni dalla data di emissione.",
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
                            label="SCARICA PREVENTIVO UFFICIALE (PDF)",
                            data=pdf_bytes,
                            file_name=f"Preventivo_{partenza.split(',')[0]}_{destinazione.split(',')[0]}.pdf",
                            mime="application/pdf",
                        )
                    else:
                        st.error("Impossibile calcolare il percorso tra le località specificate.")
                else:
                    st.error("Impossibile individuare gli indirizzi indicati.")
    else:
        st.info("Compilare i campi a sinistra per generare il preventivo.")
