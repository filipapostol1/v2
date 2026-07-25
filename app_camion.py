from datetime import datetime
import json
import os
import tempfile
import requests
import streamlit as st
from fpdf import FPDF

# 1. CONFIGURAZIONE PAGINA
st.set_page_config(
    page_title="Apostol Trasporti - Suite Gestionale",
    layout="wide",
    initial_sidebar_state="expanded",
)

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
    cronologia.insert(0, record)
    with open(FILE_CRONOLOGIA, "w", encoding="utf-8") as f:
        json.dump(cronologia, f, ensure_ascii=False, indent=4)


# CSS
st.markdown(
    """
    <style>
    .main { padding: 1.5rem; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
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
    div[data-testid="stMetricValue"] { font-size: 1.6rem; font-weight: 700; color: #0f172a; }
    </style>
""",
    unsafe_allow_html=True,
)

# ==========================================
# 2. BARRA LATERALE: AZIENDA & MEZZI
# ==========================================
st.sidebar.header("⚙️ Dati Vettore (Azienda)")

vettore_nome = st.sidebar.text_input(
    "Ragione Sociale Vettore",
    value="APOSTOL TRASPORTI DI APOSTOL C.",
)
vettore_piva = st.sidebar.text_input("P.IVA / C.F.", value="01595470111")
vettore_indirizzo = st.sidebar.text_input(
    "Indirizzo Sede", value="VIA EMILIO BIONE 8 - LA SPEZIA (SP)"
)
vettore_albo = st.sidebar.text_input("N° Iscrizione Albo", value="SP/3602624/M")

st.sidebar.markdown("---")
st.sidebar.header("🚛 Dati Mezzo & Autista Predefiniti")
default_trattore = st.sidebar.text_input("Targa Trattore / Motrice", value="GD613CR")
default_rimorchio = st.sidebar.text_input("Targa Rimorchio", value="XA762KF")
default_autista = st.sidebar.text_input("Nome Autista", value="APOSTOL CATALIN")

logo_caricato = st.sidebar.file_uploader(
    "Carica Logo Aziendale (PNG/JPG)", type=["jpg", "jpeg", "png"]
)


# 3. GEOLOCALIZZAZIONE
def ottieni_coordinate(indirizzo):
    url = f"https://nominatim.openstreetmap.org/search?q={indirizzo}&format=json&limit=1"
    headers = {"User-Agent": "ApostolLogistics/2.0"}
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


# 4. INTERFACCIA A SCHEDE (TABS)
st.title("Apostol Trasporti - Suite Gestionale")
tab1, tab2, tab3 = st.tabs(
    ["📊 Preventivi & Pedaggi", "📄 Lettera di Vettura (Bolla)", "📜 Cronologia"]
)

# ==========================================
# TAB 1: PREVENTIVI & CALCOLO PEDAGGI
# ==========================================
with tab1:
    st.subheader("Calcolo Preventivo Tratta & Pedaggi Autostradali")

    col_l, col_r = st.columns([1, 1], gap="large")

    with col_l:
        st.markdown("#### 1. Dati Cliente & Perimetro")
        cliente_nome = st.text_input("Cliente / Committente", value="ACME S.r.l.")
        partenza = st.text_input("Partenza (Es. La Spezia)", value="La Spezia")
        destinazione = st.text_input("Destinazione (Es. Parma)", value="Parma")

        tipo_viaggio = st.radio(
            "Tipologia Viaggio", options=["Solo Andata", "Andata e Ritorno"], horizontal=True
        )

        st.markdown("#### 2. Parametri Veicolo & Costi Pedaggio")
        classe_veicolo = st.selectbox(
            "Classe Veicolo (Stima Pedaggio Autostradale)",
            options=[
                "Auto / Furgone (2 Assi)",
                "Camion 3 Assi",
                "Autotreno / Bilico (4 Assi)",
                "Bilico Heavy (5+ Assi - Standard CEE)",
            ],
            index=3,
        )

        # Stima costo pedaggio al Km basato sulla classe veicolo italiana
        costi_pedaggio_km = {
            "Auto / Furgone (2 Assi)": 0.09,
            "Camion 3 Assi": 0.14,
            "Autotreno / Bilico (4 Assi)": 0.19,
            "Bilico Heavy (5+ Assi - Standard CEE)": 0.23,
        }
        stima_pedaggio_km = costi_pedaggio_km[classe_veicolo]

        col_p1, col_p2 = st.columns(2)
        with col_p1:
            tariffa_km = st.number_input("Tariffa Trasporto (€/Km)", value=1.70, step=0.05)
        with col_p2:
            spese_extra = st.number_input("Spese Accessorie / Sosta (€)", value=30.0, step=10.0)

        btn_calc = st.button("CALCOLA TRATTA E PEDAGGIO", type="primary")

    with col_r:
        st.markdown("#### Risultato Calcolo")
        if btn_calc:
            lat1, lon1 = ottieni_coordinate(partenza)
            lat2, lon2 = ottieni_coordinate(destinazione)

            if lat1 and lat2:
                km_singoli = calcola_rotta(lat1, lon1, lat2, lon2)
                if km_singoli:
                    moltiplicatore = 2 if tipo_viaggio == "Andata e Ritorno" else 1
                    km_totali = round(km_singoli * moltiplicatore, 1)

                    # Calcolo Pedaggio stimato su quota autostradale (~85% della tratta)
                    km_autostrada = km_totali * 0.85
                    pedaggio_stimato = round(km_autostrada * stima_pedaggio_km, 2)

                    costo_trasporto = round(km_totali * tariffa_km, 2)
                    totale_imponibile = round(costo_trasporto + pedaggio_stimato + spese_extra, 2)
                    iva_22 = round(totale_imponibile * 0.22, 2)
                    totale_generale = round(totale_imponibile + iva_22, 2)

                    # Salvataggio
                    salva_in_cronologia({
                        "Data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                        "Tipo": "Preventivo",
                        "Cliente": cliente_nome,
                        "Tratta": f"{partenza} -> {destinazione} ({tipo_viaggio})",
                        "Km": km_totali,
                        "Pedaggio Est.": f"€ {pedaggio_stimato:.2f}",
                        "Totale (€)": f"€ {totale_generale:.2f}",
                    })

                    m1, m2 = st.columns(2)
                    m1.metric("Distanza Totale", f"{km_totali} Km")
                    m2.metric("Pedaggio Stimato", f"EUR {pedaggio_stimato:.2f}")

                    st.metric("Totale Preventivo (IVA Inclusa)", f"EUR {totale_generale:.2f}")

                    # PDF PREVENTIVO
                    pdf = FPDF()
                    pdf.add_page()
                    pdf.set_font("Helvetica", "B", 12)
                    pdf.cell(0, 6, vettore_nome.upper(), ln=True, align="R")
                    pdf.set_font("Helvetica", "", 8)
                    pdf.cell(0, 4, f"{vettore_indirizzo} - P.IVA {vettore_piva}", ln=True, align="R")
                    pdf.ln(8)

                    pdf.set_fill_color(30, 58, 138)
                    pdf.set_text_color(255, 255, 255)
                    pdf.set_font("Helvetica", "B", 11)
                    pdf.cell(190, 7, " PREVENTIVO TRASPORTO MERCI", ln=True, fill=True)
                    pdf.set_text_color(0, 0, 0)

                    pdf.ln(4)
                    pdf.set_font("Helvetica", "", 9)
                    pdf.cell(95, 5, f"Cliente: {cliente_nome}", border=1)
                    pdf.cell(95, 5, f"Data: {datetime.now().strftime('%d/%m/%Y')}", border=1, ln=True)
                    pdf.cell(95, 5, f"Partenza: {partenza}", border=1)
                    pdf.cell(95, 5, f"Destinazione: {destinazione}", border=1, ln=True)
                    pdf.cell(190, 5, f"Tipologia Viaggio: {tipo_viaggio} ({km_totali} Km) - Veicolo: {classe_veicolo}", border=1, ln=True)

                    pdf.ln(5)
                    pdf.set_font("Helvetica", "B", 9)
                    pdf.cell(130, 6, "Voce di Costo", border=1)
                    pdf.cell(60, 6, "Importo (€)", border=1, ln=True, align="R")

                    pdf.set_font("Helvetica", "", 9)
                    pdf.cell(130, 6, f"Servizio Trasporto su Strada ({km_totali} Km x {tariffa_km:.2f} €/Km)", border=1)
                    pdf.cell(60, 6, f"{costo_trasporto:.2f}", border=1, ln=True, align="R")

                    pdf.cell(130, 6, f"Stima Pedaggio Autostradale ({classe_veicolo})", border=1)
                    pdf.cell(60, 6, f"{pedaggio_stimato:.2f}", border=1, ln=True, align="R")

                    if spese_extra > 0:
                        pdf.cell(130, 6, "Spese Accessorie / Sosta", border=1)
                        pdf.cell(60, 6, f"{spese_extra:.2f}", border=1, ln=True, align="R")

                    pdf.set_font("Helvetica", "B", 10)
                    pdf.cell(130, 7, "TOTALE IMPONIBILE", border=1)
                    pdf.cell(60, 7, f"{totale_imponibile:.2f}", border=1, ln=True, align="R")
                    pdf.cell(130, 7, "IVA 22%", border=1)
                    pdf.cell(60, 7, f"{iva_22:.2f}", border=1, ln=True, align="R")
                    pdf.cell(130, 8, "TOTALE GENERALE", border=1)
                    pdf.cell(60, 8, f"{totale_generale:.2f} EUR", border=1, ln=True, align="R")

                    pdf_out = pdf.output(dest="S")
                    pdf_bytes = pdf_out.encode("latin-1", errors="replace") if isinstance(pdf_out, str) else bytes(pdf_out)

                    st.download_button(
                        "SCARICA PREVENTIVO PDF",
                        data=pdf_bytes,
                        file_name=f"Preventivo_{cliente_nome.replace(' ', '_')}.pdf",
                        mime="application/pdf",
                    )
                else:
                    st.error("Errore nel calcolo del percorso.")
            else:
                st.error("Località non trovate.")

# ==========================================
# TAB 2: LETTERA DI VETTURA (BOLLA DDT)
# ==========================================
with tab2:
    st.subheader("Generazione Lettera di Vettura / Bolla di Accompagnamento")

    col_b1, col_b2, col_b3 = st.columns(3)
    with col_b1:
        committente = st.text_input("Committente (Es. SILT Srl)", value="SILT Srl")
        comm_indirizzo = st.text_input("Indirizzo Committente", value="Piazza G. Alessi, 2 - Genova")
        comm_piva = st.text_input("P.IVA Committente", value="03441250101")
    with col_b2:
        ritiro_luogo = st.text_input("Luogo Ritiro / Terminal", value="MOLO FORNELLI LSCT")
        ritiro_loc = st.text_input("Località Ritiro", value="LA SPEZIA")
        scarico_luogo = st.text_input("Luogo Scarico / Consegna", value="CONTREPAIR LA SPEZIA")
        scarico_loc = st.text_input("Località Scarico", value="SANTO STEFANO MAGRA")
    with col_b3:
        n_container = st.text_input("N° Container / Sigillo", value="ONEU 504737 / 3")
        tipo_container = st.selectbox("Tipo Container", ["40 HC", "20 Box", "45 High Cube", "Merce Sfusa"])
        peso_kg = st.text_input("Peso Totale (Kg)", value="30.115")
        merce_desc = st.text_input("Descrizione Merce", value="MERCE VARIA")

    st.markdown("---")
    st.markdown("#### 🚚 Dati Mezzo & Registro Caricatori")

    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
        targa_trattore = st.text_input("Targa Trattore", value=default_trattore)
        targa_rimorchio = st.text_input("Targa Rimorchio", value=default_rimorchio)
    with col_m2:
        nome_autista = st.text_input("Autista", value=default_autista)
        booking_ref = st.text_input("N° Booking / Riferimento", value="8572")
    with col_m3:
        caricatore1 = st.text_input("1° Caricatore", value="MAZZOLENI C/O ZANO - MONTAGNANA (PD)")
        caricatore2 = st.text_input("2° Caricatore (Opzionale)", value="")

    btn_gen_bolla = st.button("GENERA LETTERA DI VETTURA (PDF)", type="primary")

    if btn_gen_bolla:
        pdf_b = FPDF(orientation="P", unit="mm", format="A4")
        pdf_b.set_margins(8, 8, 8)
        pdf_b.add_page()

        # Intestazione Bolla
        pdf_b.set_font("Helvetica", "B", 10)
        pdf_b.cell(120, 4, vettore_nome.upper(), ln=False)
        pdf_b.set_font("Helvetica", "B", 11)
        pdf_b.cell(74, 4, "LETTERA DI VETTURA", align="R", ln=True)

        pdf_b.set_font("Helvetica", "", 7)
        pdf_b.cell(120, 3, f"Sede: {vettore_indirizzo} - P.IVA: {vettore_piva}", ln=False)
        data_bolla = datetime.now().strftime("%d/%m/%Y")
        pdf_b.cell(74, 3, f"Data: {data_bolla} | N° Ref: {booking_ref}", align="R", ln=True)
        pdf_b.cell(120, 3, f"Iscrizione Albo: {vettore_albo}", ln=True)

        pdf_b.ln(3)

        # Tabella Committente e Vettore
        y_top = pdf_b.get_y()
        pdf_b.rect(8, y_top, 95, 22)
        pdf_b.rect(103, y_top, 99, 22)

        pdf_b.set_xy(10, y_top + 1)
        pdf_b.set_font("Helvetica", "B", 7)
        pdf_b.cell(91, 3, "COMMITTENTE", ln=True)
        pdf_b.set_font("Helvetica", "", 7)
        pdf_b.cell(91, 3, f"Ragione Soc: {committente}", ln=True)
        pdf_b.cell(91, 3, f"Indirizzo: {comm_indirizzo}", ln=True)
        pdf_b.cell(91, 3, f"P.IVA: {comm_piva}", ln=True)

        pdf_b.set_xy(105, y_top + 1)
        pdf_b.set_font("Helvetica", "B", 7)
        pdf_b.cell(95, 3, "VETTORE ED ESECUTORE", ln=True)
        pdf_b.set_font("Helvetica", "", 7)
        pdf_b.cell(95, 3, f"Mezzo: {targa_trattore} / {targa_rimorchio}", ln=True)
        pdf_b.cell(95, 3, f"Autista: {nome_autista}", ln=True)
        pdf_b.cell(95, 3, f"Booking / Ref: {booking_ref}", ln=True)

        pdf_b.set_xy(8, y_top + 24)

        # Dettagli Ritiro e Consegna
        pdf_b.set_font("Helvetica", "B", 7)
        pdf_b.set_fill_color(230, 230, 230)
        pdf_b.cell(194, 4, " TRATTA E SPECIFICHE CARICO", border=1, ln=True, fill=True)

        pdf_b.set_font("Helvetica", "", 7)
        pdf_b.cell(97, 4, f"Luogo Ritiro: {ritiro_luogo} ({ritiro_loc})", border=1)
        pdf_b.cell(97, 4, f"Luogo Scarico: {scarico_luogo} ({scarico_loc})", border=1, ln=True)

        pdf_b.cell(48, 4, f"Merce: {merce_desc}", border=1)
        pdf_b.cell(49, 4, f"Container: {tipo_container}", border=1)
        pdf_b.cell(50, 4, f"N° Container: {n_container}", border=1)
        pdf_b.cell(47, 4, f"Peso Tot. Kg: {peso_kg}", border=1, ln=True)

        pdf_b.ln(3)

        # TABELLA UNIFICATA: REGISTRO ORARI E FIRME (COLONNA UNICA PER ORARI)
        pdf_b.set_font("Helvetica", "B", 8)
        pdf_b.set_fill_color(220, 220, 220)
        pdf_b.cell(85, 5, "Punto di Carico / Scarico", border=1, fill=True)
        # COLONNA UNIFICATA RICHIESTA DA TUO PADRE
        pdf_b.cell(55, 5, "ORA ARRIVO / PARTENZA", border=1, align="C", fill=True)
        pdf_b.cell(54, 5, "SIGILLI / NOTE / FIRMA", border=1, align="C", fill=True, ln=True)

        pdf_b.set_font("Helvetica", "", 8)

        punti = [
            f"1° Caricatore: {caricatore1}",
            f"2° Caricatore: {caricatore2 if caricatore2 else 'N/A'}",
            f"Terminal Ritiro: {ritiro_luogo}",
            f"Luogo Consegna / Scarico: {scarico_luogo}",
        ]

        for p in punti:
            pdf_b.cell(85, 8, p[:48], border=1)
            pdf_b.cell(55, 8, "", border=1)  # Spazio unico per annotare sia Arrivo che Partenza
            pdf_b.cell(54, 8, "", border=1, ln=True)

        pdf_b.ln(3)

        # Spazio Osservazioni e Dichiarazione Ricevitore
        pdf_b.set_font("Helvetica", "B", 7)
        pdf_b.cell(194, 4, "OSSERVAZIONI E NOTE DI TRASPORTO", border="LRT", ln=True)
        pdf_b.set_font("Helvetica", "", 7)
        pdf_b.cell(194, 8, " ", border="LRB", ln=True)

        pdf_b.ln(2)
        pdf_b.cell(97, 6, "Firma Vettore / Autista: ______________________", border=1)
        pdf_b.cell(97, 6, "Firma Ricevitore / Destinatario: ______________________", border=1, ln=True)

        # Note Legali
        pdf_b.ln(2)
        pdf_b.set_font("Helvetica", "", 5)
        pdf_b.multi_cell(
            194,
            2.5,
            "CONDIZIONI PARTICOLARI DI TRASPORTO: Il trasporto va eseguito nel rispetto delle disposizioni legislative e regolamentari poste a tutela della sicurezza della circolazione stradale. "
            "Il ricevitore è tenuto a verificare l'integrità e il numero del sigillo ed a rimuoverlo in presenza dell'autista. Il caricatore è responsabile della veridicità del peso dichiarato. "
            "Le merci trasportate sono assicurate secondo le condizioni della polizza italiana autocarro.",
        )

        pdf_bolla_out = pdf_b.output(dest="S")
        pdf_bolla_bytes = (
            pdf_bolla_out.encode("latin-1", errors="replace")
            if isinstance(pdf_bolla_out, str)
            else bytes(pdf_bolla_out)
        )

        st.download_button(
            "SCARICA LETTERA DI VETTURA (PDF)",
            data=pdf_bolla_bytes,
            file_name=f"Bolla_{booking_ref}_{data_bolla.replace('/', '-')}.pdf",
            mime="application/pdf",
        )

# ==========================================
# TAB 3: CRONOLOGIA GENERALE
# ==========================================
with tab3:
    st.subheader("📜 Storico Operazioni Registrate")
    cronologia = carica_cronologia()
    if cronologia:
        st.dataframe(cronologia, use_container_width=True)
    else:
        st.caption("Nessun dato registrato in cronologia.")
