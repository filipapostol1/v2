from datetime import datetime
import json
import os
import requests
import streamlit as st
from fpdf import FPDF
from PIL import Image
import io

# ==========================================
# 0. CHIAVE API CENTRALIZZATA 
# ==========================================
API_KEY_DEFAULT = "INSERISCI_QUI_LA_TUA_CHIAVE_API"
ORS_API_KEY = st.secrets.get("ORS_API_KEY", API_KEY_DEFAULT)

# ==========================================
# 1. CONFIGURAZIONE PAGINA & SETUP INIZIALE
# ==========================================
st.set_page_config(page_title="Apostol Trasporti - ERP", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
        [data-testid="collapsedControl"] { display: none; }
        section[data-testid="stSidebar"] { display: none; }
        .main { padding-top: 1rem; }
    </style>
""", unsafe_allow_html=True)

FILE_CRONOLOGIA = "cronologia.json"

# Inizializzazione variabili globali in session_state
if 'vettore_nome' not in st.session_state: st.session_state.vettore_nome = "APOSTOL TRASPORTI DI APOSTOL C"
if 'vettore_piva' not in st.session_state: st.session_state.vettore_piva = "01595470111"
if 'vettore_indirizzo' not in st.session_state: st.session_state.vettore_indirizzo = "VIA EMILIO BIONE 8"
if 'vettore_loc' not in st.session_state: st.session_state.vettore_loc = "LA SPEZIA"
if 'vettore_prov' not in st.session_state: st.session_state.vettore_prov = "SP"
if 'vettore_albo' not in st.session_state: st.session_state.vettore_albo = "SP/3602624/M"
if 'autista' not in st.session_state: st.session_state.autista = "APOSTOL CATALIN"
if 'trattore' not in st.session_state: st.session_state.trattore = "GD613CR"
if 'rimorchio' not in st.session_state: st.session_state.rimorchio = "XA762KF"
if 'logo_bytes' not in st.session_state: st.session_state.logo_bytes = None
if 'km_suggeriti' not in st.session_state: st.session_state.km_suggeriti = 0.0

def carica_cronologia():
    if os.path.exists(FILE_CRONOLOGIA):
        try:
            with open(FILE_CRONOLOGIA, "r", encoding="utf-8") as f: return json.load(f)
        except: return []
    return []

def salva_in_cronologia(record):
    cronologia = carica_cronologia()
    cronologia.insert(0, record)
    with open(FILE_CRONOLOGIA, "w", encoding="utf-8") as f:
        json.dump(cronologia, f, ensure_ascii=False, indent=4)

def pulisci_testo(testo):
    if not testo: return ""
    return str(testo).replace("€", "EUR").encode('latin-1', 'replace').decode('latin-1')

def ottieni_coordinate(indirizzo):
    try:
        url_nom = "https://nominatim.openstreetmap.org/search"
        q_str = f"{indirizzo}, Italia" if "italia" not in indirizzo.lower() else indirizzo
        res_nom = requests.get(url_nom, params={"q": q_str, "format": "json", "limit": 1}, headers={"User-Agent": "ApostolTruckApp/2.0"}, timeout=5)
        if res_nom.status_code == 200 and res_nom.json(): 
            return float(res_nom.json()[0]["lat"]), float(res_nom.json()[0]["lon"])
    except: pass
    return None, None

def calcola_rotta_camion(lat1, lon1, lat2, lon2):
    if ORS_API_KEY and ORS_API_KEY != "INSERISCI_QUI_LA_TUA_CHIAVE_API":
        try:
            headers = {'Authorization': ORS_API_KEY, 'Content-Type': 'application/json'}
            body = {"coordinates": [[lon1, lat1], [lon2, lat2]]}
            res = requests.post("https://api.openrouteservice.org/v2/directions/driving-hgv/json", json=body, headers=headers, timeout=8)
            if res.status_code == 200:
                return round(res.json()["routes"][0]["summary"]["distance"] / 1000.0, 1)
        except: pass
    try:
        url = f"http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=false"
        res = requests.get(url, timeout=5)
        if res.status_code == 200: 
            return round(res.json()["routes"][0]["distance"] / 1000.0, 1)
    except: pass
    return None

def stima_pedaggio_autostrada(km_totali, classe_veicolo):
    tariffe = {"Bilico (4/5 Assi)": 0.19, "Camion (3 Assi)": 0.14, "Auto / Furgone": 0.09}
    return round((km_totali * 0.75) * tariffe.get(classe_veicolo, 0.19), 2)

# ==========================================
# 2. DASHBOARD CENTRALE
# ==========================================
st.title("🚛 Gestionale Trasporti & Preventivi")
st.markdown("---")

tab_impostazioni, tab_preventivi, tab_bolla, tab_cronologia = st.tabs([
    "⚙️ Impostazioni Azienda", 
    "📊 Preventivi & Percorsi", 
    "📄 Bolle / DDT", 
    "📜 Cronologia"
])

# --- TAB 1: IMPOSTAZIONI ---
with tab_impostazioni:
    col_img1, col_img2 = st.columns([1, 2])
    with col_img1:
        uploaded_logo = st.file_uploader("Carica Logo Aziendale", type=["png", "jpg", "jpeg"])
        if uploaded_logo: st.session_state.logo_bytes = uploaded_logo.read()
        if st.session_state.logo_bytes: st.image(st.session_state.logo_bytes, width=200)
    with col_img2: st.info("Modulo configurato.")

    st.markdown("---")
    col_v1, col_v2 = st.columns(2)
    with col_v1:
        st.session_state.vettore_nome = st.text_input("Ragione Sociale Vettore", value=st.session_state.vettore_nome)
        st.session_state.vettore_piva = st.text_input("Partita IVA", value=st.session_state.vettore_piva)
        st.session_state.vettore_indirizzo = st.text_input("Indirizzo", value=st.session_state.vettore_indirizzo)
        c_loc, c_pr = st.columns([3,1])
        st.session_state.vettore_loc = c_loc.text_input("Località", value=st.session_state.vettore_loc)
        st.session_state.vettore_prov = c_pr.text_input("Prov", value=st.session_state.vettore_prov)
        st.session_state.vettore_albo = st.text_input("Iscrizione Albo", value=st.session_state.vettore_albo)
    with col_v2:
        st.session_state.autista = st.text_input("Nome Autista", value=st.session_state.autista)
        st.session_state.trattore = st.text_input("Targa Trattore", value=st.session_state.trattore)
        st.session_state.rimorchio = st.text_input("Targa Rimorchio", value=st.session_state.rimorchio)

# --- TAB 2: PREVENTIVI ---
with tab_preventivi:
    st.subheader("Configurazione Viaggio e Preventivo")
    col_p1, col_p2 = st.columns([1, 1], gap="large")

    with col_p1:
        cliente_nome = st.text_input("Nome Cliente / Committente", value="ACME S.r.l.")
        partenza = st.text_input("Indirizzo/Città Partenza", value="Via Sommacampagna 61, Verona")
        destinazione = st.text_input("Indirizzo/Città Destinazione", value="Via Tiburtina 1000, Roma")
        tipo_viaggio = st.radio("Tipologia Viaggio", options=["Solo Andata", "Andata e Ritorno"], horizontal=True)
        
        if st.button("📍 Ottieni Stima KM da Mappa", use_container_width=True):
            if partenza and destinazione:
                with st.spinner("Calcolo rotte..."):
                    lat1, lon1 = ottieni_coordinate(partenza)
                    lat2, lon2 = ottieni_coordinate(destinazione)
                    if lat1 and lat2:
                        km_calc = calcola_rotta_camion(lat1, lon1, lat2, lon2)
                        if km_calc:
                            st.session_state.km_suggeriti = km_calc * 2 if tipo_viaggio == "Andata e Ritorno" else km_calc
                            st.success(f"Stima Mappa completata: {st.session_state.km_suggeriti} Km")
                        else:
                            st.error("Errore API di routing.")
                    else:
                        st.error("Coordinate non trovate.")

    with col_p2:
        km_finali = st.number_input("KM Effettivi da Fatturare", value=float(st.session_state.km_suggeriti), step=5.0)
        classe_veicolo = st.selectbox("Mezzo Utilizzato", options=["Bilico (4/5 Assi)", "Camion (3 Assi)", "Auto / Furgone"])
        tariffa_km = st.number_input("Tariffa (EUR al Km)", value=1.70, step=0.05)
        
        pedaggio_stimato = stima_pedaggio_autostrada(km_finali, classe_veicolo)
        costo_trasporto = round(km_finali * tariffa_km, 2)
        imponibile = round(costo_trasporto + pedaggio_stimato, 2)
        iva = round(imponibile * 0.22, 2)
        totale = round(imponibile + iva, 2)

        c_m1, c_m2, c_m3 = st.columns(3)
        c_m1.metric("Trasporto", f"€ {costo_trasporto:.2f}")
        c_m2.metric("Pedaggi", f"€ {pedaggio_stimato:.2f}")
        c_m3.metric("TOTALE + IVA", f"€ {totale:.2f}")

        if st.button("🖨️ GENERA PREVENTIVO (PDF)", type="primary", use_container_width=True):
            if km_finali > 0:
                salva_in_cronologia({
                    "Data": datetime.now().strftime("%d/%m/%Y %H:%M"), "Tipo": "Preventivo",
                    "Cliente": cliente_nome, "Tratta": f"{partenza} -> {destinazione}", "Totale": f"EUR {totale:.2f}"
                })
                pdf = FPDF(orientation='P', unit='mm', format='A4')
                pdf.add_page()
                if st.session_state.logo_bytes:
                    img = Image.open(io.BytesIO(st.session_state.logo_bytes))
                    img.save("temp_logo.png")
                    pdf.image("temp_logo.png", x=10, y=10, w=40)
                else:
                    pdf.set_font("Helvetica", "B", 14)
                    pdf.text(10, 20, pulisci_testo(st.session_state.vettore_nome))
                pdf.set_font("Helvetica", "", 9)
                pdf.text(10, 30, f"P.IVA: {pulisci_testo(st.session_state.vettore_piva)}")
                pdf.text(10, 35, f"{pulisci_testo(st.session_state.vettore_indirizzo)} - {pulisci_testo(st.session_state.vettore_loc)}")
                
                pdf.set_font("Helvetica", "B", 14)
                pdf.text(120, 20, "PREVENTIVO DI TRASPORTO")
                pdf.set_font("Helvetica", "", 10)
                pdf.text(120, 27, f"Data emissione: {datetime.now().strftime('%d/%m/%Y')}")

                pdf.set_line_width(0.3)
                pdf.rect(10, 50, 90, 30)
                pdf.rect(105, 50, 95, 30)
                pdf.set_font("Helvetica", "B", 8)
                pdf.text(12, 55, "SPETT.LE COMMITTENTE:")
                pdf.set_font("Helvetica", "", 10)
                pdf.text(12, 63, pulisci_testo(cliente_nome))
                
                pdf.set_font("Helvetica", "B", 8)
                pdf.text(107, 55, "DETTAGLI TRATTA E MEZZO:")
                pdf.set_font("Helvetica", "", 9)
                pdf.text(107, 62, f"Partenza: {pulisci_testo(partenza)[:40]}")
                pdf.text(107, 68, f"Destinazione: {pulisci_testo(destinazione)[:40]}")

                y_tab = 90
                pdf.set_fill_color(230, 230, 230)
                pdf.rect(10, y_tab, 190, 8, "DF")
                pdf.set_font("Helvetica", "B", 9)
                pdf.text(12, y_tab + 5, "DESCRIZIONE DEL SERVIZIO")
                pdf.text(165, y_tab + 5, "IMPORTO (EUR)")
                pdf.set_font("Helvetica", "", 9)
                pdf.rect(10, y_tab+8, 190, 30)
                pdf.text(12, y_tab + 16, f"Servizio trasporto ({km_finali} Km x {tariffa_km:.2f} EUR/Km)")
                pdf.text(165, y_tab + 16, f"{costo_trasporto:.2f}")
                pdf.text(12, y_tab + 26, "Rimborso spese pedaggio autostradale stimato")
                pdf.text(165, y_tab + 26, f"{pedaggio_stimato:.2f}")

                y_tot = y_tab + 45
                pdf.rect(120, y_tot, 80, 24)
                pdf.set_font("Helvetica", "B", 9)
                pdf.text(122, y_tot + 6, "IMPONIBILE")
                pdf.text(165, y_tot + 6, f"{imponibile:.2f}")
                pdf.text(122, y_tot + 14, "IVA (22%)")
                pdf.text(165, y_tot + 14, f"{iva:.2f}")
                pdf.set_font("Helvetica", "B", 10)
                pdf.text(122, y_tot + 22, "TOTALE")
                pdf.text(165, y_tot + 22, f"{totale:.2f}")

                pdf_bytes = pdf.output(dest='S').encode('latin-1', 'replace')
                st.download_button("📥 SCARICA PREVENTIVO", data=pdf_bytes, file_name=f"Preventivo.pdf", mime="application/pdf")

# --- TAB 3: BOLLA / DDT (Rifatto stile SILT / Lettera di Vettura Intermodale) ---
with tab_bolla:
    st.subheader("Lettera di Vettura (Layout Strutturato Avanzato)")
    
    with st.expander("📝 DATI PRINCIPALI (Intestazione)", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        data_bolla = c1.text_input("Data", value=datetime.now().strftime("%d/%m/%Y"))
        ora_bolla = c2.text_input("Ora", value="08:00")
        booking_ref = c3.text_input("Nr. Riferimento", value="01 8572")
        compagnia = c4.text_input("Compagnia / Booking", value="ONE IMPORT")
        doc_num = st.text_input("Numero Lettera di Vettura", value="20260100008572")

    with st.expander("🏢 COMMITTENTE E LUOGHI", expanded=True):
        c_com1, c_com2 = st.columns(2)
        with c_com1:
            committente = st.text_input("Committente", value="SILT Srl")
            comm_ind = st.text_input("Indirizzo Comm.", value="Piazza G. Alessi, 2")
            comm_loc = st.text_input("Località Comm.", value="Genova")
            comm_prov = st.text_input("Provincia Comm.", value="GE")
            comm_tel = st.text_input("Tel Comm.", value="010/8597200")
            comm_piva = st.text_input("P.IVA Comm.", value="03441250101")
            comm_email = st.text_input("Email Comm.", value="silt@siltgoa.it")
            comm_albo = st.text_input("I.Albo n° Comm.", value="MI889714E")
        with c_com2:
            ritiro_term = st.text_input("Term.Rit. / Caric.", value="LA SPEZIA CONTAINER TRML LSCT")
            ritiro_ind = st.text_input("Indirizzo Ritiro", value="MOLO FORNELLI")
            ritiro_loc = st.text_input("Località Ritiro", value="LA SPEZIA")
            st.markdown("---")
            scarico_luogo = st.text_input("Luogo scarico", value="CONTREPAIR LA SPEZIA")
            scarico_ind = st.text_input("Indirizzo Scarico", value="VIA BOLANO 20")
            scarico_loc = st.text_input("Località Scarico", value="SANTO STEFANO MAGRA")

    with st.expander("🚚 MEZZO E MERCE", expanded=True):
        c_mez1, c_mez2 = st.columns(2)
        with c_mez1:
            container1 = st.text_input("1° Container / Sigillo", value="ONEU 504737 / 3")
            container2 = st.text_input("2° Container / Sigillo", value="")
            tipo_cont = st.text_input("Container tipo", value="40 HC")
            peso = st.text_input("Peso Tot. Kg", value="30.115")
        with c_mez2:
            merce = st.text_input("Merce", value="MERCE VARIA")
            colli = st.text_input("Colli", value="")
            km_viaggio = st.text_input("KM", value="500")
            spedizioniere = st.text_input("Spedizioniere", value="SAVINO")

    with st.expander("📦 CARICATORI (Fino a 3)", expanded=False):
        c_car1, c_car2, c_car3 = st.columns(3)
        with c_car1:
            caric1_nome = st.text_input("1° Caricatore", value="MAZZOLENI C/O ZANO")
            caric1_ind = st.text_input("Ind. 1° Caric.", value="VIA ROTTA VECCHIA 4")
            caric1_loc = st.text_input("Loc. 1° Caric.", value="MONTAGNANA (PD)")
            caric1_tel = st.text_input("Tel 1", value="")
            caric1_piva = st.text_input("P.IVA 1", value="")
        with c_car2:
            caric2_nome = st.text_input("2° Caricatore", value="")
            caric2_ind = st.text_input("Ind. 2° Caric.", value="")
            caric2_loc = st.text_input("Loc. 2° Caric.", value="")
            caric2_tel = st.text_input("Tel 2", value="")
            caric2_piva = st.text_input("P.IVA 2", value="")
        with c_car3:
            caric3_nome = st.text_input("3° Caricatore", value="")
            caric3_ind = st.text_input("Ind. 3° Caric.", value="")
            caric3_loc = st.text_input("Loc. 3° Caric.", value="")
            caric3_tel = st.text_input("Tel 3", value="")
            caric3_piva = st.text_input("P.IVA 3", value="")
            
    osservazioni = st.text_area("Osservazioni", value="")

    if st.button("🖨️ STAMPA LETTERA DI VETTURA (PDF ESATTO)", type="primary", use_container_width=True):
        
        salva_in_cronologia({
            "Data": datetime.now().strftime("%d/%m/%Y %H:%M"), "Tipo": "Emissione Lettera Vettura",
            "Cliente": committente, "Tratta": f"Rif: {booking_ref}", "Totale": "-"
        })

        # --- CREAZIONE PDF ---
        pdf = FPDF(orientation='P', unit='mm', format='A4')
        pdf.set_margins(10, 10, 10)
        pdf.add_page()
        pdf.set_auto_page_break(False)

        # Intestazione Personalizzata Vettore o Logo (CORRETTO SENZA TAGLIO)
        if st.session_state.logo_bytes:
            img = Image.open(io.BytesIO(st.session_state.logo_bytes))
            img.save("temp_logo_bolla.png")
            pdf.image("temp_logo_bolla.png", x=10, y=10, w=35)
        else:
            pdf.set_font("Helvetica", "B", 13)
            pdf.text(10, 15, pulisci_testo(st.session_state.vettore_nome))

        pdf.set_font("Helvetica", "B", 10)
        pdf.text(150, 18, "LETTERA DI VETTURA")
        pdf.set_font("Helvetica", "B", 11)
        pdf.text(150, 23, pulisci_testo(doc_num))

        y_offset = 30
        pdf.set_line_width(0.2)

        # 1. Riga Data / Ora
        pdf.rect(10, y_offset, 190, 8)
        pdf.line(40, y_offset, 40, y_offset+8)
        pdf.line(70, y_offset, 70, y_offset+8)
        pdf.line(110, y_offset, 110, y_offset+8)
        
        pdf.set_font("Helvetica", "", 7)
        pdf.text(12, y_offset+3, "Data")
        pdf.text(42, y_offset+3, "Ora")
        pdf.text(72, y_offset+3, "Nr. Riferimento")
        pdf.text(112, y_offset+3, "Compagnia / Booking")
        
        pdf.set_font("Helvetica", "B", 10)
        pdf.text(12, y_offset+7, pulisci_testo(data_bolla))
        pdf.text(42, y_offset+7, pulisci_testo(ora_bolla))
        pdf.text(72, y_offset+7, pulisci_testo(booking_ref))
        pdf.text(130, y_offset+7, pulisci_testo(compagnia))

        # 2. Sezione Committente / Vettore
        y2 = y_offset + 8
        h2 = 30
        pdf.rect(10, y2, 190, h2)
        pdf.line(105, y2, 105, y2+h2) # Linea verticale centrale

        # -- Left Side (Committente)
        pdf.set_font("Helvetica", "", 7)
        pdf.text(12, y2+4, "Committ.")
        pdf.text(12, y2+8, "Indirizzo")
        pdf.text(12, y2+12, "Località")
        pdf.text(12, y2+16, "Telefono")
        pdf.text(12, y2+20, "E-mail")
        pdf.text(12, y2+24, "I.Albo n°")
        pdf.text(65, y2+16, "P.Iva")

        pdf.set_font("Helvetica", "B", 8)
        pdf.text(35, y2+4, pulisci_testo(committente))
        pdf.text(35, y2+8, pulisci_testo(comm_ind))
        pdf.text(35, y2+12, pulisci_testo(comm_loc))
        pdf.text(95, y2+12, pulisci_testo(comm_prov))
        pdf.text(35, y2+16, pulisci_testo(comm_tel))
        pdf.text(35, y2+20, pulisci_testo(comm_email))
        pdf.text(35, y2+24, pulisci_testo(comm_albo))
        pdf.text(75, y2+16, pulisci_testo(comm_piva))

        # -- Right Side (Vettore)
        pdf.set_font("Helvetica", "", 7)
        pdf.text(107, y2+4, "Vettore")
        pdf.text(107, y2+8, "Località")
        pdf.text(107, y2+12, "Telefono")
        pdf.text(107, y2+16, "E-mail")
        pdf.text(107, y2+20, "Autista")
        pdf.text(107, y2+24, "Rgs vett.")
        pdf.text(107, y2+28, "I.Albo n°")
        pdf.text(160, y2+12, "I.Albo n°")

        pdf.set_font("Helvetica", "B", 7)
        pdf.text(125, y2+4, f"{pulisci_testo(st.session_state.vettore_nome)[:35]} P.I. {pulisci_testo(st.session_state.vettore_piva)}")
        pdf.text(125, y2+8, f"{pulisci_testo(st.session_state.vettore_indirizzo)}   {pulisci_testo(st.session_state.vettore_loc)}")
        pdf.text(190, y2+8, pulisci_testo(st.session_state.vettore_prov))
        pdf.text(173, y2+12, pulisci_testo(st.session_state.vettore_albo))
        pdf.set_font("Helvetica", "B", 8)
        pdf.text(125, y2+20, pulisci_testo(st.session_state.autista))

        # 3. Sezione Ritiro / Veicolo
        y3 = y2 + h2
        h3 = 12
        pdf.rect(10, y3, 190, h3)
        pdf.line(105, y3, 105, y3+h3)
        
        pdf.set_font("Helvetica", "", 7)
        pdf.text(12, y3+4, "Term.Rit. / Caric.")
        pdf.text(12, y3+8, "Indirizzo")
        pdf.text(12, y3+11.5, "Località")
        pdf.set_font("Helvetica", "B", 8)
        pdf.text(35, y3+4, pulisci_testo(ritiro_term))
        pdf.text(35, y3+8, pulisci_testo(ritiro_ind))
        pdf.text(35, y3+11.5, pulisci_testo(ritiro_loc))

        pdf.set_font("Helvetica", "", 7)
        pdf.text(107, y3+4, "Veicolo")
        pdf.text(107, y3+8, "1° Container")
        pdf.set_font("Helvetica", "B", 8)
        pdf.text(130, y3+4, f"{pulisci_testo(st.session_state.trattore)}   /   {pulisci_testo(st.session_state.rimorchio)}")
        pdf.text(130, y3+8, pulisci_testo(container1))

        # 4. Sezione Scarico / Container
        y4 = y3 + h3
        h4 = 12
        pdf.rect(10, y4, 190, h4)
        pdf.line(105, y4, 105, y4+h4)
        
        pdf.set_font("Helvetica", "", 7)
        pdf.text(12, y4+4, "Luogo scarico")
        pdf.text(12, y4+8, "Indirizzo")
        pdf.text(12, y4+11.5, "Località")
        pdf.set_font("Helvetica", "B", 8)
        pdf.text(35, y4+4, pulisci_testo(scarico_luogo))
        pdf.text(35, y4+8, pulisci_testo(scarico_ind))
        pdf.text(35, y4+11.5, pulisci_testo(scarico_loc))

        pdf.set_font("Helvetica", "", 7)
        pdf.text(107, y4+4, "2° Container")
        pdf.text(107, y4+8, "Container tipo")
        pdf.text(160, y4+8, "Peso Tot.Kg")
        pdf.set_font("Helvetica", "B", 8)
        pdf.text(130, y4+4, pulisci_testo(container2))
        pdf.text(130, y4+8, pulisci_testo(tipo_cont))
        pdf.set_font("Helvetica", "B", 10)
        pdf.text(180, y4+8, pulisci_testo(peso))

        # 5. Sezione Merce / Destinazione
        y5 = y4 + h4
        h5 = 15
        pdf.rect(10, y5, 190, h5)
        pdf.line(105, y5, 105, y5+h5)

        pdf.set_font("Helvetica", "", 7)
        pdf.text(12, y5+4, "Merce")
        pdf.text(80, y5+4, "Colli")
        pdf.text(12, y5+14, "KM")
        pdf.set_font("Helvetica", "B", 9)
        pdf.text(35, y5+4, pulisci_testo(merce))
        pdf.text(90, y5+4, pulisci_testo(colli))
        pdf.text(35, y5+14, pulisci_testo(km_viaggio))

        pdf.set_font("Helvetica", "", 7)
        pdf.text(107, y5+4, "Destinazione")
        pdf.text(107, y5+8, "Porto sbarco")
        pdf.text(107, y5+12, "Spedizioniere")
        pdf.set_font("Helvetica", "B", 8)
        pdf.text(130, y5+12, pulisci_testo(spedizioniere))

        # 6. Griglia Caricatori (3 Blocchi)
        y6 = y5 + h5
        for i, caric in enumerate([
            (caric1_nome, caric1_ind, caric1_loc, caric1_tel, caric1_piva),
            (caric2_nome, caric2_ind, caric2_loc, caric2_tel, caric2_piva),
            (caric3_nome, caric3_ind, caric3_loc, caric3_tel, caric3_piva)
        ]):
            hc = 18
            yc = y6 + (i * hc)
            pdf.rect(10, yc, 190, hc)
            pdf.line(105, yc, 105, yc+hc)
            
            # Griglia destra Orari e Sigilli
            pdf.line(105, yc+6, 200, yc+6)
            pdf.line(136, yc, 136, yc+hc)
            pdf.line(168, yc, 168, yc+hc)
            pdf.set_font("Helvetica", "", 7)
            pdf.text(113, yc+4, "Ora arrivo")
            pdf.text(142, yc+4, "Ora partenza")
            pdf.text(178, yc+4, "Sigillo/i")

            pdf.text(12, yc+4, f"{i+1}° Caricatore")
            pdf.text(12, yc+8, "Indirizzo")
            pdf.text(12, yc+12, "Località")
            pdf.text(12, yc+16, "Telefono")
            pdf.text(65, yc+16, "P.Iva")

            pdf.set_font("Helvetica", "B", 8)
            pdf.text(30, yc+4, pulisci_testo(caric[0]))
            pdf.text(30, yc+8, pulisci_testo(caric[1]))
            pdf.text(30, yc+12, pulisci_testo(caric[2]))
            pdf.text(30, yc+16, pulisci_testo(caric[3]))
            pdf.text(75, yc+16, pulisci_testo(caric[4]))

        # 7. Osservazioni e Dichiarazione
        y7 = y6 + (18 * 3)
        h7 = 25
        pdf.rect(10, y7, 190, h7)
        pdf.set_font("Helvetica", "", 7)
        pdf.text(12, y7+4, "Osservazioni")
        pdf.set_font("Helvetica", "", 8)
        pdf.set_xy(12, y7+6)
        pdf.multi_cell(185, 4, pulisci_testo(osservazioni))

        pdf.line(10, y7+h7-8, 200, y7+h7-8)
        pdf.set_font("Helvetica", "", 8)
        pdf.text(12, y7+h7-3, "DICHIARAZIONE RICEVITORE/DESTINATARIO")
        pdf.text(105, y7+h7-4, "Constatato integro il sigillo ___________________ apposto mittente")
        pdf.text(105, y7+h7-1, "Rimosso sigillo mittente e apposto sigillo ______________________")

        # 8. CONDIZIONI PARTICOLARI (Testo Legale)
        y8 = y7 + h7 + 2
        pdf.set_font("Helvetica", "B", 7)
        pdf.text(10, y8, "CONDIZIONI PARTICOLARI DI TRASPORTO")
        pdf.set_font("Helvetica", "", 6)
        testo_legale = (
            "Il trasporto va eseguito nel rispetto delle disposizioni legislative e regolamentari poste a tutela della sicurezza stradale, in "
            "particolare modo rispetto agli art. 61 (sagoma limite), 62 (massa limite), 142 (limite di velocità), 164 (sistemazione del carico), "
            "167 (trasporto di cose), 174 (durata della guida) del D.LGS. 30 aprile 1992, N. 258.\n"
            "1) Il caricatore è tenuto ad applicare i sigilli al container in presenza dell'autista.\n"
            "2) Il ricevitore è tenuto a verificare l'integrità e il numero del sigillo e a rimuoverlo in presenza dell'autista.\n"
            "3) Il vettore accetta e riconsegna il container nello stato in cui si trova... il vettore, pertanto, non è responsabile della quantità "
            "e qualità e stivaggio della merce... ogni riserva deve essere manifestata all'autista.\n"
            "4) Il vettore è responsabile delle perdite e/o avarie imputabili in base alle norme vigenti...\n"
            "5) Il trattore con il semirimorchio ed il container, arrivando in tempo utile per le operazioni, dovranno essere lasciati liberi "
            "entro i termini previsti dal contratto collettivo nazionale.\n"
            "6) Il caricatore è solo responsabile della veridicità del peso dichiarato riferito alla merce affidata al vettore...\n"
            "7) L'autista non è tenuto a partecipare in nessuna maniera alle operazioni di carico e/o scarico, ivi compresa l'eventuale scopertura containers open top.\n"
            "8) Le merci trasportate a mezzo autocarro sono assicurate per un importo massimo di euro 30.000,00 alle condizioni generali..."
        )
        pdf.set_xy(10, y8+2)
        pdf.multi_cell(190, 2.5, testo_legale)

        pdf_bytes = pdf.output(dest='S').encode('latin-1', 'replace')
        st.download_button("📥 SCARICA LETTERA DI VETTURA (FORMATO INTERMODALE)", data=pdf_bytes, file_name=f"Bolla_{pulisci_testo(doc_num)}.pdf", mime="application/pdf")

# --- TAB 4: CRONOLOGIA ---
with tab_cronologia:
    st.subheader("Storico Operazioni")
    dati = carica_cronologia()
    if dati: st.dataframe(dati, use_container_width=True)
    else: st.info("Nessuna operazione.")
