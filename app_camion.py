from datetime import datetime
import json
import os
import tempfile
import requests
import streamlit as st
from fpdf import FPDF

# 1. CONFIGURAZIONE PAGINA STREAMLIT
st.set_page_config(
    page_title="LogiCalc B2B - Calcolo Tratte & Preventivi",
    layout="wide",
    initial_sidebar_state="expanded",
)

# FILE PER SALVARE LA CRONOLOGIA LOCALE
FILE_CRONOLOGIA = "cronologia.json"


def carica_cronologia():
    if os.path.exists(FILE_CRONOLOGIA):
        try:
            with open(FILE_CRONOLOGIA, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def salva_in_cronologia(record):
    cronologia = carica_cronologia()
    cronologia.insert(0, record)  # Inserisce il più recente in cima
    with open(FILE_CRONOLOGIA, "w", encoding="utf-8") as f:
        json.dump(cronologia, f, ensure_ascii=False, indent=4)


# CSS Personalizzato
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

# ==========================================
# 2. BARRA LATERALE: DATI AZIENDA EMITTENTE
# ==========================================
st.sidebar.header("⚙️ Configurazione Azienda")
st.sidebar.caption("Dati dell'emittente del preventivo")

azienda_nome = st.sidebar.text_input(
    "Ragione Sociale",
    value="APOSTOL TRASPORTI S.R.L.",
)

azienda_indirizzo = st.sidebar.text_input(
    "Indirizzo Sede",
    value="Via Trasporti Nazionali 15, Milano",
)

azienda_piva = st.sidebar.text_input(
    "P.IVA / Codice Fiscale",
    value="P.IVA 01234567890",
)

tariffa_km = st.sidebar.number_input(
    "Tariffa Predefinita (€/Km)",
    value=1.65,
    step=0.05,
    format="%.2f",
)

logo_caricato = st.sidebar.file_uploader(
    "Carica Logo Aziendale (PNG/JPG)", type=["jpg", "jpeg", "png"]
)


# 3. FUNZIONI API GEOLOCALIZZAZIONE
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


# 4. INTERFACCIA PRINCIPALE
st.title("LogiCalc B2B - Calcolo Tratte & Preventivi")
st.caption(f"Piattaforma gestionale in uso da: **{azienda_nome}**")
st.markdown("---")

col_left, col_right = st.columns([1, 1], gap="large")

with col_left:
    st.subheader("1. Dati Cliente (Intestatario)")

    cliente_nome = st.text_input(
        "Ragione Sociale / Nome Cliente",
        value="ACME S.r.l.",
        help="Nome della società a cui è intestato il preventivo",
    )

    col_cli1, col_cli2 = st.columns(2)
    with col_cli1:
        cliente_indirizzo = st.text_input(
            "Indirizzo Sede Cliente",
            value="Via Industria 5, Bologna",
        )
    with col_cli2:
        cliente_piva = st.text_input(
            "P.IVA / C.F. Cliente",
            value="IT98765432109",
        )

    st.subheader("2. Dati Tratta e Trasporto")

    partenza = st.text_input(
        "Indirizzo / Città di Partenza (Origine)",
        value="Via Roma 1, Milano",
    )
    destinazione = st.text_input(
        "Indirizzo / Città di Arrivo (Destinazione)",
        value="Via Nazionale 10, Roma",
    )

    tipo_viaggio = st.radio(
        "Tipologia Tratta",
        options=["Solo Andata", "Andata e Ritorno"],
        horizontal=True,
    )

    st.subheader("3. Parametri Economici")

    col_e1, col_e2 = st.columns(2)
    with col_e1:
        st.text_input(
            "Tariffa / Km Applicata",
            value=f"{tariffa_km:.2f} €",
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
        if not partenza or not destinazione or not cliente_nome:
            st.error(
                "Errore: compilare la Ragione Sociale Cliente, la Partenza e la Destinazione."
            )
        else:
            with st.spinner("Calcolo percorso e generazione preventivo..."):
                lat1, lon1 = ottieni_coordinate(partenza)
                lat2, lon2 = ottieni_coordinate(destinazione)

                if lat1 and lat2:
                    km_singola_tratta = calcola_rotta(lat1, lon1, lat2, lon2)

                    if km_singola_tratta:
                        moltiplicatore = (
                            2 if tipo_viaggio == "Andata e Ritorno" else 1
                        )
                        km_totali = round(
                            km_singola_tratta * moltiplicatore, 1
                        )

                        costo_tratta = km_totali * tariffa_km
                        totale_imponibile = costo_tratta + spese_extra
                        iva_22 = totale_imponibile * 0.22
                        totale_generale = totale_imponibile + iva_22

                        # Salvataggio in Cronologia con tutti i dati puliti
                        ora_attuale = datetime.now().strftime(
                            "%d/%m/%Y %H:%M"
                        )
                        salva_in_cronologia(
                            {
                                "Data": ora_attuale,
                                "Cliente": cliente_nome,
                                "P.IVA Cliente": cliente_piva,
                                "Partenza": partenza,
                                "Destinazione": destinazione,
                                "Tipologia": tipo_viaggio,
                                "Km Totali": km_totali,
                                "Totale (€)": f"€ {totale_generale:.2f}",
                            }
                        )

                        m1, m2 = st.columns(2)
                        m1.metric(
                            f"Distanza ({tipo_viaggio})", f"{km_totali} Km"
                        )
                        m2.metric(
                            "Totale Preventivo (IVA inc.)",
                            f"EUR {totale_generale:.2f}",
                        )

                        st.success(
                            "Calcolo completato e preventivo salvato in cronologia!"
                        )

                        # GENERAZIONE PDF
                        pdf = FPDF(orientation="P", unit="mm", format="A4")
                        pdf.set_margins(10, 10, 10)
                        pdf.add_page()

                        # Logo
                        logo_path = None
                        if logo_caricato is not None:
                            with tempfile.NamedTemporaryFile(
                                delete=False, suffix=".png"
                            ) as tmp_file:
                                tmp_file.write(logo_caricato.getvalue())
                                logo_path = tmp_file.name
                        elif os.path.exists("logo.jpg"):
                            logo_path = "logo.jpg"
                        elif os.path.exists("logo.png"):
                            logo_path = "logo.png"

                        if logo_path:
                            try:
                                pdf.image(logo_path, x=10, y=10, w=35)
                            except Exception:
                                pass

                        # Intestazione Emittente
                        pdf.set_font("Helvetica", "B", 11)
                        pdf.cell(0, 5, azienda_nome.upper(), ln=True, align="R")
                        pdf.set_font("Helvetica", "", 8)
                        pdf.cell(0, 4, azienda_indirizzo, ln=True, align="R")
                        pdf.cell(0, 4, azienda_piva, ln=True, align="R")
                        pdf.ln(6)

                        # Titolo
                        pdf.set_fill_color(220, 220, 220)
                        pdf.set_font("Helvetica", "B", 10)
                        pdf.cell(
                            190,
                            6,
                            " PREVENTIVO DI TRASPORTO / ORDINE",
                            border=1,
                            ln=True,
                            fill=True,
                        )

                        # Box Dettagliati
                        y_boxes = pdf.get_y()
                        box_h = 28
                        pdf.rect(10, y_boxes, 95, box_h)
                        pdf.rect(105, y_boxes, 95, box_h)

                        # --- CLIENTE / INTESTATARIO ---
                        pdf.set_xy(12, y_boxes + 2)
                        pdf.set_font("Helvetica", "", 7)
                        pdf.set_text_color(100, 100, 100)
                        pdf.cell(91, 3, "CLIENTE / INTESTATARIO", ln=False)

                        pdf.set_xy(12, y_boxes + 6)
                        pdf.set_font("Helvetica", "B", 8)
                        pdf.set_text_color(0, 0, 0)
                        pdf.cell(91, 4, cliente_nome.upper(), ln=False)

                        pdf.set_xy(12, y_boxes + 11)
                        pdf.set_font("Helvetica", "", 8)
                        pdf.cell(91, 4, f"Sede: {cliente_indirizzo}", ln=False)

                        pdf.set_xy(12, y_boxes + 16)
                        pdf.cell(
                            91, 4, f"P.IVA/C.F.: {cliente_piva}", ln=False
                        )

                        pdf.set_xy(12, y_boxes + 21)
                        pdf.set_font("Helvetica", "I", 7)
                        pdf.cell(
                            91, 4, f"Partenza Merci: {partenza.title()}", ln=False
                        )

                        # --- DESTINAZIONE MERCI ---
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
                        pdf.multi_cell(
                            91, 4, f"Destinazione: {destinazione.title()}"
                        )

                        pdf.set_xy(10, y_boxes + box_h)

                        # Griglia Dati Documento
                        pdf.set_font("Helvetica", "", 6)
                        pdf.set_text_color(80, 80, 80)
                        cols_w = [35, 30, 30, 45, 50]

                        pdf.cell(
                            cols_w[0],
                            3,
                            "NUMERO PREVENTIVO",
                            border="LRT",
                            align="C",
                        )
                        pdf.cell(
                            cols_w[1], 3, "DATA DOC.", border="LRT", align="C"
                        )
                        pdf.cell(
                            cols_w[2],
                            3,
                            "COD. CLIENTE",
                            border="LRT",
                            align="C",
                        )
                        pdf.cell(
                            cols_w[3],
                            3,
                            "MODALITA DI PAGAMENTO",
                            border="LRT",
                            align="C",
                        )
                        pdf.cell(
                            cols_w[4],
                            3,
                            "TRATTA SELEZIONATA",
                            border="LRT",
                            align="C",
                            ln=True,
                        )

                        pdf.set_font("Helvetica", "B", 8)
                        pdf.set_text_color(0, 0, 0)
                        data_oggi = datetime.now().strftime("%d/%m/%Y")
                        cod_ref = f"PRV-{int(km_totali)}"

                        pdf.cell(cols_w[0], 5, cod_ref, border="LRB", align="C")
                        pdf.cell(
                            cols_w[1], 5, data_oggi, border="LRB", align="C"
                        )
                        pdf.cell(
                            cols_w[2], 5, "CLI-0012", border="LRB", align="C"
                        )
                        pdf.cell(
                            cols_w[3],
                            5,
                            "BONIFICO BANCARIO D.F.",
                            border="LRB",
                            align="C",
                        )
                        pdf.cell(
                            cols_w[4],
                            5,
                            f"{tipo_viaggio} ({km_totali} Km)",
                            border="LRB",
                            align="C",
                            ln=True,
                        )

                        pdf.ln(1)

                        # Tabella Servizi
                        col_tbl = [20, 85, 12, 18, 22, 18, 15]
                        pdf.set_font("Helvetica", "B", 7)
                        pdf.set_fill_color(230, 230, 230)

                        pdf.cell(
                            col_tbl[0],
                            5,
                            "CODICE",
                            border=1,
                            align="C",
                            fill=True,
                        )
                        pdf.cell(
                            col_tbl[1],
                            5,
                            "DESCRIZIONE",
                            border=1,
                            align="L",
                            fill=True,
                        )
                        pdf.cell(
                            col_tbl[2], 5, "U.M.", border=1, align="C", fill=True
                        )
                        pdf.cell(
                            col_tbl[3],
                            5,
                            "QUANTITA",
                            border=1,
                            align="C",
                            fill=True,
                        )
                        pdf.cell(
                            col_tbl[4],
                            5,
                            "PREZZO",
                            border=1,
                            align="C",
                            fill=True,
                        )
                        pdf.cell(
                            col_tbl[5],
                            5,
                            "IMPONIBILE",
                            border=1,
                            align="C",
                            fill=True,
                        )
                        pdf.cell(
                            col_tbl[6],
                            5,
                            "PERC IVA",
                            border=1,
                            align="C",
                            fill=True,
                            ln=True,
                        )

                        y_start_table = pdf.get_y()
                        pdf.set_font("Helvetica", "", 8)

                        # Riga Trasporto
                        pdf.cell(col_tbl[0], 5, "TRASP-01", align="C")
                        pdf.cell(
                            col_tbl[1],
                            5,
                            f"Servizio trasporto ({tipo_viaggio})",
                            align="L",
                        )
                        pdf.cell(col_tbl[2], 5, "Km", align="C")
                        pdf.cell(col_tbl[3], 5, f"{km_totali}", align="C")
                        pdf.cell(
                            col_tbl[4], 5, f"{tariffa_km:.2f}", align="R"
                        )
                        pdf.cell(
                            col_tbl[5], 5, f"{costo_tratta:.2f}", align="R"
                        )
                        pdf.cell(col_tbl[6], 5, "22%", align="C", ln=True)

                        # Riga Pedaggi
                        pdf.cell(col_tbl[0], 5, "PED-01", align="C")
                        pdf.cell(
                            col_tbl[1],
                            5,
                            "Pedaggi autostradali e spese accessorie",
                            align="L",
                        )
                        pdf.cell(col_tbl[2], 5, "Pz", align="C")
                        pdf.cell(col_tbl[3], 5, "1", align="C")
                        pdf.cell(
                            col_tbl[4], 5, f"{spese_extra:.2f}", align="R"
                        )
                        pdf.cell(
                            col_tbl[5], 5, f"{spese_extra:.2f}", align="R"
                        )
                        pdf.cell(col_tbl[6], 5, "22%", align="C", ln=True)

                        table_height = 135
                        pdf.rect(10, y_start_table, 190, table_height)

                        x_curr = 10
                        for w in col_tbl[:-1]:
                            x_curr += w
                            pdf.line(
                                x_curr,
                                y_start_table,
                                x_curr,
                                y_start_table + table_height,
                            )

                        pdf.set_xy(10, y_start_table + table_height + 2)

                        # Totali
                        pdf.set_font("Helvetica", "", 6)
                        pdf.set_text_color(80, 80, 80)

                        pdf.cell(
                            40,
                            3,
                            "IMPONIBILE TRASPORTO",
                            border="LRT",
                            align="C",
                        )
                        pdf.cell(
                            40, 3, "PEDAGGI / EXTRA", border="LRT", align="C"
                        )
                        pdf.cell(
                            35, 3, "TOTALE IMPONIBILE", border="LRT", align="C"
                        )
                        pdf.cell(
                            35, 3, "TOTALE IVA (22%)", border="LRT", align="C"
                        )
                        pdf.cell(
                            40,
                            3,
                            "TOTALE PREVENTIVO",
                            border="LRT",
                            align="C",
                            ln=True,
                        )

                        pdf.set_font("Helvetica", "B", 8)
                        pdf.set_text_color(0, 0, 0)
                        pdf.cell(
                            40,
                            5,
                            f"Euro {costo_tratta:.2f}",
                            border="LRB",
                            align="C",
                        )
                        pdf.cell(
                            40,
                            5,
                            f"Euro {spese_extra:.2f}",
                            border="LRB",
                            align="C",
                        )
                        pdf.cell(
                            35,
                            5,
                            f"Euro {totale_imponibile:.2f}",
                            border="LRB",
                            align="C",
                        )
                        pdf.cell(
                            35, 5, f"Euro {iva_22:.2f}", border="LRB", align="C"
                        )

                        pdf.set_font("Helvetica", "BI", 10)
                        pdf.cell(
                            40,
                            5,
                            f"Euro {totale_generale:.2f}",
                            border="LRB",
                            align="C",
                            ln=True,
                        )

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
                            file_name=f"Preventivo_{cliente_nome.replace(' ', '_')}.pdf",
                            mime="application/pdf",
                        )
                    else:
                        st.error(
                            "Impossibile calcolare il percorso tra le località specificate."
                        )
                else:
                    st.error("Impossibile individuare gli indirizzi indicati.")
    else:
        st.info("Compilare i campi a sinistra per generare il preventivo.")

# ==========================================
# 5. SEZIONE CRONOLOGIA PREVENTIVI ELABORATI
# ==========================================
st.markdown("---")
st.subheader("📜 Cronologia Preventivi Elaborati")

cronologia_dati = carica_cronologia()

if cronologia_dati:
    st.dataframe(cronologia_dati, use_container_width=True)
else:
    st.caption(
        "Nessun preventivo ancora salvato in cronologia. Effettua un calcolo per vederlo comparire qui."
    )
