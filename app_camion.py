from datetime import datetime
import json
import os
import tempfile
import time
import requests
import streamlit as st
from fpdf import FPDF

# ==========================================
# 1. CONFIGURAZIONE PAGINA STREAMLIT
# ==========================================
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

def pulisci_testo(testo):
    """Rimuove caratteri strani che fanno crashare il generatore PDF o accavallare i testi."""
    if not testo: return ""
    testo = str(testo).replace("€", "EUR").replace("’", "'").replace("“", '"').replace("”", '"').replace("\n", " ")
    return testo.encode('latin-1', 'ignore').decode('latin-1')

# CSS Personalizzato
st.markdown(
    """
    <style>
    .main { padding: 1.5rem; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    .stButton>button { width: 100%; border-radius: 4px; height: 2.8em; font-weight: 600; background-color: #1e3a8a; color: white; border: none; }
    .stButton>button:hover { background-color: #1e293b; color: white; }
    div[data-testid="stMetricValue"] { font-size: 1.6rem; font-weight: 700; color: #0f172a; }
    </style>
""", unsafe_allow_html=True)


# ==========================================
# 2. BARRA LATERALE DINAMICA (MENU)
# ==========================================
st.sidebar.title("📌 Navigazione")
pagina_selezionata = st.sidebar.radio(
    "", 
    ["📊 Preventivi & Pedaggi", "📄 Lettera di Vettura (Bolla)", "📜 Cronologia"]
)

st.sidebar.markdown("---")
st.sidebar.header("🏢 Dati Aziendali (Vettore)")
vettore_nome = st.sidebar.text_input("Ragione Sociale Vettore", value="APOSTOL TRASPORTI DI APOSTOL C.")
vettore_piva = st.sidebar.text_input("P.IVA / C.F.", value="01595470111")
vettore_indirizzo = st.sidebar.text_input("Indirizzo Sede", value="VIA EMILIO BIONE 8 - LA SPEZIA (SP)")
vettore_albo = st.sidebar.text_input("N° Iscrizione Albo", value="SP/3602624/M")
logo_caricato = st.sidebar.file_uploader("Logo Aziendale (Opzionale)", type=["jpg", "jpeg", "png"])

# VARIABILI DINAMICHE SOLO PER LA BOLLA
default_trattore = "GD613CR"
default_rimorchio = "XA762KF"
default_autista = "APOSTOL CATALIN"

if pagina_selezionata == "📄 Lettera di Vettura (Bolla)":
    st.sidebar.markdown("---")
    st.sidebar.header("🚛 Veicolo e Autista (Predefiniti)")
    default_trattore = st.sidebar.text_input("Targa Trattore", value="GD613CR")
    default_rimorchio = st.sidebar.text_input("Targa Rimorchio", value="XA762KF")
    default_autista = st.sidebar.text_input("Nome Autista", value="APOSTOL CATALIN")


# ==========================================
# 3. MOTORE API ANTI-BLOCCO
# ==========================================
def ottieni_coordinate(indirizzo):
    if not indirizzo or not indirizzo.strip(): return None, None
    try:
        url_nom = "https://nominatim.openstreetmap.org/search"
        res_nom = requests.get(url_nom, params={"q": indirizzo, "format": "json", "limit": 1}, headers={"User-Agent": f"ApostolApp_{int(time.time())}"}, timeout=4)
        if res_nom.status_code == 200 and res_nom.json(): return float(res_nom.json()[0]["lat"]), float(res_nom.json()[0]["lon"])
    except: pass
    try:
        url_pho = "https://photon.komoot.io/api/"
        res_pho = requests.get(url_pho, params={"q": indirizzo, "limit": 1}, timeout=5)
        if res_pho.status_code == 200 and res_pho.json().get("features"):
            coords = res_pho.json()["features"][0]["geometry"]["coordinates"]
            return float(coords[1]), float(coords[0])
    except: pass
    st.error(f"❌ Impossibile trovare la località '{indirizzo}'. Riprova tra poco.")
    return None, None

def calcola_rotta(lat1, lon1, lat2, lon2):
    url = f"http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=false"
    for _ in range(3):
        try:
            res = requests.get(url, timeout=5)
            if res.status_code == 200 and res.json().get("routes"): return round(res.json()["routes"][0]["distance"] / 1000, 1)
            elif res.status_code == 429: time.sleep(1.5); continue
        except: time.sleep(1); continue
    st.error("❌ Troppe richieste. Impossibile calcolare i Km ora.")
    return None

# ==========================================
# 4. PAGINE DELL'APPLICAZIONE
# ==========================================
st.title("Apostol Trasporti - Suite Gestionale")

# ------------------------------------------
# PAGINA 1: PREVENTIVI
# ------------------------------------------
if pagina_selezionata == "📊 Preventivi & Pedaggi":
    st.subheader("Calcolo Preventivo Tratta & Pedaggi")
    col_l, col_r = st.columns([1, 1], gap="large")

    with col_l:
        st.markdown("#### 1. Dati Cliente & Perimetro")
        cliente_nome = st.text_input("Cliente / Committente", value="ACME S.r.l.")
        partenza = st.text_input("Partenza (Es. La Spezia)", value="La Spezia")
        destinazione = st.text_input("Destinazione (Es. Parma)", value="Parma")
        tipo_viaggio = st.radio("Tipologia Viaggio", options=["Solo Andata", "Andata e Ritorno"], horizontal=True)

        st.markdown("#### 2. Parametri Costo")
        classe_veicolo = st.selectbox("Classe Veicolo (Pedaggio)", options=["Auto / Furgone", "Camion 3 Assi", "Autotreno / Bilico (4 Assi)", "Bilico Heavy (5+ Assi)"], index=3)
        costi_pedaggio = {"Auto / Furgone": 0.09, "Camion 3 Assi": 0.14, "Autotreno / Bilico (4 Assi)": 0.19, "Bilico Heavy (5+ Assi)": 0.23}
        stima_pedaggio_km = costi_pedaggio[classe_veicolo]
        tariffa_km = st.number_input("Tariffa Trasporto (EUR/Km)", value=1.70, step=0.05)
        btn_calc = st.button("CALCOLA TRATTA E PREVENTIVO", type="primary")

    with col_r:
        st.markdown("#### Risultato Calcolo")
        if btn_calc:
            if not partenza or not destinazione or not cliente_nome:
                st.error("Riempi i campi obbligatori.")
            else:
                with st.spinner("Calcolo in corso..."):
                    lat1, lon1 = ottieni_coordinate(partenza)
                    if lat1: time.sleep(0.5)
                    lat2, lon2 = ottieni_coordinate(destinazione)

                    if lat1 and lat2:
                        km_singoli = calcola_rotta(lat1, lon1, lat2, lon2)
                        if km_singoli:
                            moltiplicatore = 2 if tipo_viaggio == "Andata e Ritorno" else 1
                            km_totali = round(km_singoli * moltiplicatore, 1)
                            pedaggio_stimato = round((km_totali * 0.85) * stima_pedaggio_km, 2)
                            costo_trasporto = round(km_totali * tariffa_km, 2)
                            totale_imponibile = round(costo_trasporto + pedaggio_stimato, 2)
                            iva_22 = round(totale_imponibile * 0.22, 2)
                            totale_generale = round(totale_imponibile + iva_22, 2)

                            salva_in_cronologia({
                                "Data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                                "Tipo": "Preventivo",
                                "Cliente": cliente_nome,
                                "Tratta": f"{partenza} -> {destinazione}",
                                "Totale (EUR)": f"EUR {totale_generale:.2f}"
                            })

                            m1, m2 = st.columns(2)
                            m1.metric("Distanza Totale", f"{km_totali} Km")
                            m2.metric("Pedaggio Stimato", f"EUR {pedaggio_stimato:.2f}")
                            st.metric("Totale Preventivo (IVA Inclusa)", f"EUR {totale_generale:.2f}")

                            # PDF PREVENTIVO CON STILE UNIFICATO
                            pdf = FPDF()
                            pdf.add_page()
                            # Logo
                            if logo_caricato is not None:
                                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                                    tmp.write(logo_caricato.getvalue())
                                    try: pdf.image(tmp.name, x=10, y=10, w=35)
                                    except: pass
                            
                            # Intestazione Standard
                            pdf.set_font("Helvetica", "B", 12)
                            pdf.cell(0, 5, pulisci_testo(vettore_nome).upper(), ln=True, align="R")
                            pdf.set_font("Helvetica", "", 8)
                            pdf.cell(0, 4, f"Sede: {pulisci_testo(vettore_indirizzo)[:50]} - P.IVA: {pulisci_testo(vettore_piva)}", ln=True, align="R")
                            pdf.cell(0, 4, f"Albo: {pulisci_testo(vettore_albo)}", ln=True, align="R")
                            pdf.ln(8)

                            # Banda Blu Titolo
                            pdf.set_fill_color(30, 58, 138)
                            pdf.set_text_color(255, 255, 255)
                            pdf.set_font("Helvetica", "B", 11)
                            pdf.cell(190, 7, " PREVENTIVO TRASPORTO MERCI", ln=True, fill=True)
                            pdf.set_text_color(0, 0, 0)
                            pdf.ln(4)

                            # Corpo Preventivo
                            pdf.set_font("Helvetica", "", 9)
                            pdf.cell(95, 5, f"Cliente: {pulisci_testo(cliente_nome)}", border=1)
                            pdf.cell(95, 5, f"Data: {datetime.now().strftime('%d/%m/%Y')}", border=1, ln=True)
                            pdf.cell(95, 5, f"Partenza: {pulisci_testo(partenza)}", border=1)
                            pdf.cell(95, 5, f"Destinazione: {pulisci_testo(destinazione)}", border=1, ln=True)
                            pdf.cell(190, 5, f"Viaggio: {tipo_viaggio} ({km_totali} Km) - Classe: {classe_veicolo}", border=1, ln=True)
                            
                            pdf.ln(5)
                            pdf.set_font("Helvetica", "B", 9)
                            pdf.cell(130, 6, "Voce di Costo", border=1, fill=True)
                            pdf.cell(60, 6, "Importo (EUR)", border=1, ln=True, align="R", fill=True)
                            
                            pdf.set_font("Helvetica", "", 9)
                            pdf.cell(130, 6, f"Servizio Trasporto ({km_totali} Km x {tariffa_km:.2f} EUR/Km)", border=1)
                            pdf.cell(60, 6, f"{costo_trasporto:.2f}", border=1, ln=True, align="R")
                            pdf.cell(130, 6, f"Stima Pedaggio Autostradale", border=1)
                            pdf.cell(60, 6, f"{pedaggio_stimato:.2f}", border=1, ln=True, align="R")

                            pdf.set_font("Helvetica", "B", 10)
                            pdf.cell(130, 7, "TOTALE IMPONIBILE", border=1)
                            pdf.cell(60, 7, f"{totale_imponibile:.2f}", border=1, ln=True, align="R")
                            pdf.cell(130, 7, "IVA 22%", border=1)
                            pdf.cell(60, 7, f"{iva_22:.2f}", border=1, ln=True, align="R")
                            pdf.cell(130, 8, "TOTALE GENERALE", border=1)
                            pdf.cell(60, 8, f"{totale_generale:.2f} EUR", border=1, ln=True, align="R")

                            pdf_bytes = pdf.output(dest="S").encode("latin-1", "replace")
                            st.download_button("📥 SCARICA PREVENTIVO PDF", data=pdf_bytes, file_name=f"Preventivo_{pulisci_testo(cliente_nome)}.pdf", mime="application/pdf")

# ------------------------------------------
# PAGINA 2: LETTERA DI VETTURA (BOLLA)
# ------------------------------------------
elif pagina_selezionata == "📄 Lettera di Vettura (Bolla)":
    st.subheader("Generazione Lettera di Vettura / Documento di Trasporto")

    col_b1, col_b2, col_b3 = st.columns(3)
    with col_b1:
        committente = st.text_input("Committente (Es. SILT Srl)", value="SILT Srl")
        comm_indirizzo = st.text_input("Indirizzo Comm.", value="Piazza G. Alessi, 2 - Genova")
        comm_piva = st.text_input("P.IVA Comm.", value="03441250101")
    with col_b2:
        ritiro_luogo = st.text_input("Luogo Ritiro (Terminal)", value="MOLO FORNELLI LSCT")
        scarico_luogo = st.text_input("Luogo Scarico", value="CONTREPAIR SANTO STEFANO M.")
        booking_ref = st.text_input("N° Booking / Ref", value="8572")
    with col_b3:
        n_container = st.text_input("N° Container / Sigillo", value="ONEU 504737 / 3")
        tipo_container = st.selectbox("Tipo Container", ["40 HC", "20 Box", "45 High Cube", "Merce Sfusa"])
        peso_kg = st.text_input("Peso Tot. (Kg)", value="30.115")
        merce_desc = st.text_input("Desc. Merce", value="MERCE VARIA")

    st.markdown("---")
    st.markdown("#### Registro Caricatori")
    caricatore1 = st.text_input("1° Caricatore", value="MAZZOLENI C/O ZANO - MONTAGNANA (PD)")
    caricatore2 = st.text_input("2° Caricatore (Opzionale)", value="")

    if st.button("GENERA LETTERA DI VETTURA (PDF)", type="primary"):
        pdf_b = FPDF()
        pdf_b.add_page()

        # Logo (Stessa logica)
        if logo_caricato is not None:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                tmp.write(logo_caricato.getvalue())
                try: pdf_b.image(tmp.name, x=10, y=10, w=35)
                except: pass

        # Intestazione Standard (Identica al Preventivo per stile unificato)
        pdf_b.set_font("Helvetica", "B", 12)
        pdf_b.cell(0, 5, pulisci_testo(vettore_nome).upper(), ln=True, align="R")
        pdf_b.set_font("Helvetica", "", 8)
        pdf_b.cell(0, 4, f"Sede: {pulisci_testo(vettore_indirizzo)[:50]} - P.IVA: {pulisci_testo(vettore_piva)}", ln=True, align="R")
        pdf_b.cell(0, 4, f"Albo: {pulisci_testo(vettore_albo)} | Data: {datetime.now().strftime('%d/%m/%Y')}", ln=True, align="R")
        pdf_b.ln(8)

        # Banda Blu Titolo - Stile Unificato
        pdf_b.set_fill_color(30, 58, 138)
        pdf_b.set_text_color(255, 255, 255)
        pdf_b.set_font("Helvetica", "B", 11)
        pdf_b.cell(190, 7, " LETTERA DI VETTURA / DOCUMENTO DI TRASPORTO", ln=True, fill=True)
        pdf_b.set_text_color(0, 0, 0)
        pdf_b.ln(4)

        # ====== FIX SOVRASCRIZIONE ======
        # Invece di sovrapporre righe, calcoliamo le altezze e blocchiamo i box (Multi_cell)
        y_start = pdf_b.get_y()

        # BOX SINISTRO: COMMITTENTE
        pdf_b.set_xy(10, y_start)
        pdf_b.set_font("Helvetica", "B", 8)
        pdf_b.cell(92, 5, "COMMITTENTE", border=1, fill=True, ln=True)
        pdf_b.set_font("Helvetica", "", 8)
        testo_comm = f"Ragione Soc: {pulisci_testo(committente)}\nIndirizzo: {pulisci_testo(comm_indirizzo)}\nP.IVA: {pulisci_testo(comm_piva)}"
        pdf_b.multi_cell(92, 5, testo_comm, border=1)
        y_end_sinistra = pdf_b.get_y()

        # BOX DESTRO: VETTORE
        pdf_b.set_xy(105, y_start)
        pdf_b.set_font("Helvetica", "B", 8)
        pdf_b.cell(95, 5, "VETTORE ED ESECUTORE", border=1, fill=True, ln=True)
        pdf_b.set_xy(105, y_start + 5) # Riposiziona il cursore sotto il titolo destro
        pdf_b.set_font("Helvetica", "", 8)
        testo_vet = f"Mezzo: {pulisci_testo(default_trattore)} / {pulisci_testo(default_rimorchio)}\nAutista: {pulisci_testo(default_autista)}\nRef / Booking: {pulisci_testo(booking_ref)}"
        pdf_b.multi_cell(95, 5, testo_vet, border=1)
        y_end_destra = pdf_b.get_y()

        # Riprendiamo a scrivere sotto il box più lungo (anti-accavallamento)
        pdf_b.set_y(max(y_end_sinistra, y_end_destra) + 4)

        # TRATTA E CARICO
        pdf_b.set_font("Helvetica", "B", 8)
        pdf_b.cell(190, 5, " SPECIFICHE DI CARICO", border=1, ln=True, fill=True)
        pdf_b.set_font("Helvetica", "", 8)
        
        # Uso stringhe formattate con limiti massimi per evitare di uscire dalle celle
        pdf_b.cell(95, 6, f"Ritiro: {pulisci_testo(ritiro_luogo)[:50]}", border=1)
        pdf_b.cell(95, 6, f"Scarico: {pulisci_testo(scarico_luogo)[:50]}", border=1, ln=True)
        
        pdf_b.cell(60, 6, f"Merce: {pulisci_testo(merce_desc)[:30]}", border=1)
        pdf_b.cell(45, 6, f"Cont: {pulisci_testo(tipo_container)}", border=1)
        pdf_b.cell(50, 6, f"Sigillo/N°: {pulisci_testo(n_container)[:20]}", border=1)
        pdf_b.cell(35, 6, f"Peso: {pulisci_testo(peso_kg)} Kg", border=1, ln=True)

        pdf_b.ln(4)

        # REGISTRO ORARI E FIRME
        pdf_b.set_font("Helvetica", "B", 8)
        pdf_b.cell(80, 5, "PUNTO DI CARICO / SCARICO", border=1, fill=True)
        pdf_b.cell(50, 5, "ORA ARRIVO / PARTENZA", border=1, align="C", fill=True)
        pdf_b.cell(60, 5, "SIGILLI / NOTE / FIRMA", border=1, align="C", fill=True, ln=True)

        pdf_b.set_font("Helvetica", "", 8)
        punti = []
        if caricatore1: punti.append(f"1° Carico: {caricatore1}")
        if caricatore2: punti.append(f"2° Carico: {caricatore2}")
        if ritiro_luogo: punti.append(f"Ritiro: {ritiro_luogo}")
        if scarico_luogo: punti.append(f"Scarico: {scarico_luogo}")

        for p in punti:
            # Tronco a 55 caratteri per garantire che entri sempre in una riga singola
            testo_troncato = pulisci_testo(p)[:55]
            pdf_b.cell(80, 8, testo_troncato, border=1)
            pdf_b.cell(50, 8, "", border=1)
            pdf_b.cell(60, 8, "", border=1, ln=True)

        pdf_b.ln(4)

        # FIRME FINALI
        pdf_b.set_font("Helvetica", "B", 8)
        pdf_b.cell(95, 5, "Firma Vettore / Autista", border="LRT", ln=False)
        pdf_b.cell(95, 5, "Firma Ricevitore / Destinatario", border="LRT", ln=True)
        pdf_b.set_font("Helvetica", "", 8)
        pdf_b.cell(95, 12, "", border="LRB", ln=False)
        pdf_b.cell(95, 12, "", border="LRB", ln=True)

        pdf_b.ln(3)
        pdf_b.set_font("Helvetica", "", 6)
        pdf_b.multi_cell(190, 3, "CONDIZIONI DI TRASPORTO: Il trasporto è eseguito nel rispetto delle disposizioni legislative sulla circolazione stradale. Il ricevitore è tenuto a verificare integrità e numero di sigillo in presenza dell'autista. Merci assicurate secondo polizza vettoriale italiana.")

        pdf_bytes_b = pdf_b.output(dest="S").encode("latin-1", "replace")
        st.download_button("📥 SCARICA BOLLA (PDF)", data=pdf_bytes_b, file_name=f"Bolla_{pulisci_testo(booking_ref)}.pdf", mime="application/pdf")

# ------------------------------------------
# PAGINA 3: CRONOLOGIA
# ------------------------------------------
elif pagina_selezionata == "📜 Cronologia":
    st.subheader("Storico Preventivi Generati")
    cronologia = carica_cronologia()
    if cronologia:
        st.dataframe(cronologia, use_container_width=True)
    else:
        st.info("Nessun preventivo registrato finora.")
