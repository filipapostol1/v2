from datetime import datetime
import json
import os
import time
import requests
import random
import streamlit as st
from fpdf import FPDF

# ==========================================
# 1. CONFIGURAZIONE PAGINA & SETUP INIZIALE
# ==========================================
st.set_page_config(page_title="Apostol Trasporti - ERP", layout="wide", initial_sidebar_state="collapsed")

# Nascondiamo forzatamente la sidebar di Streamlit con CSS
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
if 'vettore_loc' not in st.session_state: st.session_state.vettore_loc = "LA SPEZIA (SP)"
if 'vettore_albo' not in st.session_state: st.session_state.vettore_albo = "SP/3602624/M"
if 'autista' not in st.session_state: st.session_state.autista = "APOSTOL CATALIN"
if 'trattore' not in st.session_state: st.session_state.trattore = "GD613CR"
if 'rimorchio' not in st.session_state: st.session_state.rimorchio = "XA762KF"

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
    return str(testo).replace("€", "EUR").replace("’", "'").replace("“", '"').replace("”", '"').encode('latin-1', 'replace').decode('latin-1')

def draw_fake_barcode(pdf, x, y, width, height, seed_str):
    pdf.set_fill_color(0, 0, 0)
    current_x = x
    random.seed(seed_str)
    while current_x < x + width:
        w = random.choice([0.4, 0.8, 1.2, 1.8])
        if current_x + w > x + width: break
        if random.random() > 0.3:
            pdf.rect(current_x, y, w, height, "F")
        current_x += w + random.choice([0.4, 0.8, 1.2])

def ottieni_coordinate(indirizzo):
    try:
        url_nom = "https://nominatim.openstreetmap.org/search"
        res_nom = requests.get(url_nom, params={"q": indirizzo, "format": "json", "limit": 1}, headers={"User-Agent": "AppApostol"}, timeout=3)
        if res_nom.status_code == 200 and res_nom.json(): return float(res_nom.json()[0]["lat"]), float(res_nom.json()[0]["lon"])
    except: pass
    return None, None

def calcola_rotta(lat1, lon1, lat2, lon2):
    try:
        url = f"http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=false"
        res = requests.get(url, timeout=4)
        if res.status_code == 200: return round(res.json()["routes"][0]["distance"] / 1000, 1)
    except: pass
    return None

# ==========================================
# 2. DASHBOARD CENTRALE
# ==========================================
st.title("🚛 Apostol Trasporti - Dashboard Gestionale")
st.markdown("---")

# Creazione delle schede (Tabs)
tab_impostazioni, tab_preventivi, tab_bolla, tab_cronologia = st.tabs([
    "⚙️ Impostazioni Dati Base", 
    "📊 Calcolo Preventivi", 
    "📄 Generazione Bolla", 
    "📜 Cronologia"
])

# --- TAB 1: IMPOSTAZIONI ---
with tab_impostazioni:
    st.subheader("Dati Aziendali e Flotta")
    st.info("I dati inseriti qui verranno utilizzati in automatico per generare Preventivi e Lettere di Vettura.")
    
    col_v1, col_v2 = st.columns(2)
    with col_v1:
        st.markdown("**Dati Vettore**")
        st.session_state.vettore_nome = st.text_input("Ragione Sociale Vettore", value=st.session_state.vettore_nome)
        st.session_state.vettore_piva = st.text_input("Partita IVA", value=st.session_state.vettore_piva)
        st.session_state.vettore_indirizzo = st.text_input("Indirizzo", value=st.session_state.vettore_indirizzo)
        st.session_state.vettore_loc = st.text_input("Località", value=st.session_state.vettore_loc)
        st.session_state.vettore_albo = st.text_input("Iscrizione Albo", value=st.session_state.vettore_albo)
    
    with col_v2:
        st.markdown("**Dati Autista e Veicolo di Default**")
        st.session_state.autista = st.text_input("Nome Autista", value=st.session_state.autista)
        st.session_state.trattore = st.text_input("Targa Trattore", value=st.session_state.trattore)
        st.session_state.rimorchio = st.text_input("Targa Rimorchio", value=st.session_state.rimorchio)

# --- TAB 2: PREVENTIVI ---
with tab_preventivi:
    st.subheader("Calcolo e Generazione Preventivo")
    col_p1, col_p2 = st.columns([1, 1], gap="large")

    with col_p1:
        cliente_nome = st.text_input("Nome Cliente / Committente", value="ACME S.r.l.")
        partenza = st.text_input("Luogo di Partenza", value="La Spezia")
        destinazione = st.text_input("Luogo di Destinazione", value="Parma")
        tipo_viaggio = st.radio("Tipologia", options=["Solo Andata", "Andata e Ritorno"], horizontal=True)
        
        st.markdown("---")
        manual_km_check = st.checkbox("📍 Inserisci KM Manualmente (Salta mappa)")
        km_manuali = st.number_input("Distanza Singola Tratta (Km)", min_value=1.0, value=100.0, step=1.0) if manual_km_check else 0.0

        classe_veicolo = st.selectbox("Mezzo Utilizzato", options=["Auto / Furgone", "Camion (3 Assi)", "Bilico (4/5 Assi)"])
        
        # Tariffe pedaggio aggiornate e più realistiche
        costi_pedaggio = {"Auto / Furgone": 0.10, "Camion (3 Assi)": 0.16, "Bilico (4/5 Assi)": 0.25}
        stima_pedaggio_km = costi_pedaggio[classe_veicolo]
        
        col_tar1, col_tar2 = st.columns(2)
        with col_tar1:
            tariffa_km = st.number_input("Tariffa (EUR al Km)", value=1.70, step=0.05)
        with col_tar2:
            # Nuovo campo per forzare il pedaggio esatto!
            pedaggio_manuale = st.number_input("Pedaggio Esatto (Lascia 0 per stima automatica)", value=0.0, step=5.0)
        
        btn_calc = st.button("🧮 CALCOLA E GENERA PDF PREVENTIVO", type="primary", use_container_width=True)

    with col_p2:
        if btn_calc:
            if not cliente_nome or (not manual_km_check and (not partenza or not destinazione)):
                st.error("Inserisci Cliente, Partenza e Destinazione.")
            else:
                with st.spinner("Calcolo rotta in corso..."):
                    km_singoli = None
                    if manual_km_check:
                        km_singoli = km_manuali
                    else:
                        lat1, lon1 = ottieni_coordinate(partenza)
                        if lat1: time.sleep(0.3)
                        lat2, lon2 = ottieni_coordinate(destinazione)
                        if lat1 and lat2: km_singoli = calcola_rotta(lat1, lon1, lat2, lon2)

                    if not km_singoli and not manual_km_check:
                        st.error("Calcolo mappa fallito. Spunta la casella per i Km manuali.")
                    else:
                        if not km_singoli: km_singoli = km_manuali
                        moltiplicatore = 2 if tipo_viaggio == "Andata e Ritorno" else 1
                        km_totali = round(km_singoli * moltiplicatore, 1)
                        
                        # LOGICA PEDAGGIO AGGIORNATA
                        if pedaggio_manuale > 0:
                            pedaggio_finale = round(pedaggio_manuale, 2)
                        else:
                            # Stima: calcoliamo che in media l'85% del tragitto sia autostradale
                            pedaggio_finale = round(km_totali * 0.85 * stima_pedaggio_km, 2)
                            
                        costo_trasporto = round(km_totali * tariffa_km, 2)
                        imponibile = round(costo_trasporto + pedaggio_finale, 2)
                        iva = round(imponibile * 0.22, 2)
                        totale = round(imponibile + iva, 2)

                        salva_in_cronologia({
                            "Data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                            "Tipo": "Preventivo",
                            "Cliente": cliente_nome,
                            "Tratta": f"{partenza} -> {destinazione}",
                            "Totale": f"EUR {totale:.2f}"
                        })

                        st.success("Calcolo Completato!")
                        st.metric("Distanza Totale (Km)", f"{km_totali}")
                        c_m1, c_m2 = st.columns(2)
                        c_m1.metric("Trasporto (EUR)", f"{costo_trasporto:.2f}")
                        
                        # Mostriamo se è stimato o esatto
                        label_pedaggio = "Pedaggio Inserito Manualmente (EUR)" if pedaggio_manuale > 0 else "Pedaggio Stimato (EUR)"
                        c_m2.metric(label_pedaggio, f"{pedaggio_finale:.2f}")
                        
                        st.metric("TOTALE FINALE (IVA Inc.)", f"EUR {totale:.2f}")

                        # PDF Preventivo
                        pdf = FPDF(orientation='P', unit='mm', format='A4')
                        pdf.add_page()
                        
                        pdf.set_font("Helvetica", "B", 14)
                        pdf.text(10, 20, pulisci_testo(st.session_state.vettore_nome))
                        pdf.set_font("Helvetica", "", 9)
                        pdf.text(10, 25, f"P.IVA: {pulisci_testo(st.session_state.vettore_piva)}")
                        pdf.text(10, 30, f"{pulisci_testo(st.session_state.vettore_indirizzo)} - {pulisci_testo(st.session_state.vettore_loc)}")
                        pdf.text(10, 35, f"Albo Trasportatori: {pulisci_testo(st.session_state.vettore_albo)}")

                        pdf.set_font("Helvetica", "B", 16)
                        pdf.text(110, 25, "PREVENTIVO DI TRASPORTO")
                        pdf.set_font("Helvetica", "", 10)
                        pdf.text(110, 32, f"Data emissione: {datetime.now().strftime('%d/%m/%Y')}")

                        pdf.set_line_width(0.3)
                        pdf.rect(10, 45, 90, 30)
                        pdf.rect(110, 45, 90, 30)

                        pdf.set_font("Helvetica", "B", 8)
                        pdf.text(12, 50, "SPETT.LE COMMITTENTE:")
                        pdf.set_font("Helvetica", "", 10)
                        pdf.text(12, 57, pulisci_testo(cliente_nome))
                        
                        pdf.set_font("Helvetica", "B", 8)
                        pdf.text(112, 50, "DETTAGLI TRATTA E MEZZO:")
                        pdf.set_font("Helvetica", "", 9)
                        pdf.text(112, 57, f"Partenza: {pulisci_testo(partenza)}")
                        pdf.text(112, 63, f"Destinazione: {pulisci_testo(destinazione)}")
                        pdf.text(112, 69, f"Tipologia: {tipo_viaggio}  |  Mezzo: {classe_veicolo}")

                        y_tab = 90
                        pdf.set_fill_color(220, 220, 220)
                        pdf.rect(10, y_tab, 190, 8, "DF")
                        
                        pdf.set_font("Helvetica", "B", 9)
                        pdf.text(12, y_tab + 5, "DESCRIZIONE DEL SERVIZIO")
                        pdf.text(165, y_tab + 5, "IMPORTO (EUR)")

                        pdf.set_font("Helvetica", "", 9)
                        pdf.line(10, y_tab+8, 10, y_tab+38) 
                        pdf.line(200, y_tab+8, 200, y_tab+38) 
                        pdf.line(160, y_tab+8, 160, y_tab+38) 

                        pdf.text(12, y_tab + 16, f"Servizio di trasporto merce ({km_totali} Km x {tariffa_km:.2f} EUR/Km)")
                        pdf.text(170, y_tab + 16, f"{costo_trasporto:.2f}")

                        # Adatta il testo del PDF in base a se il pedaggio è stimato o esatto
                        testo_riga_pedaggio = "Rimborso spese pedaggio autostradale (Stimato)" if pedaggio_manuale == 0 else "Rimborso spese pedaggio autostradale (Consuntivo)"
                        pdf.text(12, y_tab + 24, testo_riga_pedaggio)
                        pdf.text(170, y_tab + 24, f"{pedaggio_finale:.2f}")
                        
                        pdf.line(10, y_tab+38, 200, y_tab+38)

                        y_tot = y_tab + 45
                        pdf.rect(120, y_tot, 80, 25)
                        pdf.line(120, y_tot+8, 200, y_tot+8)
                        pdf.line(120, y_tot+16, 200, y_tot+16)
                        pdf.line(160, y_tot, 160, y_tot+25)

                        pdf.set_font("Helvetica", "B", 9)
                        pdf.text(122, y_tot + 6, "IMPONIBILE")
                        pdf.text(165, y_tot + 6, f"{imponibile:.2f}")
                        
                        pdf.text(122, y_tot + 14, "IVA (22%)")
                        pdf.text(165, y_tot + 14, f"{iva:.2f}")

                        pdf.set_font("Helvetica", "B", 10)
                        pdf.text(122, y_tot + 22, "TOTALE")
                        pdf.text(165, y_tot + 22, f"{totale:.2f}")

                        pdf.set_font("Helvetica", "I", 8)
                        pdf.text(10, y_tot + 40, "Il presente preventivo ha validita' di 15 giorni dalla data di emissione.")
                        
                        pdf_bytes = pdf.output(dest='S').encode('latin-1', 'replace')
                        st.download_button("📥 SCARICA PREVENTIVO (PDF)", data=pdf_bytes, file_name=f"Preventivo_{pulisci_testo(cliente_nome)}.pdf", mime="application/pdf")

# --- TAB 3: BOLLA CLONE ---
with tab_bolla:
    st.subheader("Generazione Lettera di Vettura (Modello Esatto)")
    
    c1, c2, c3 = st.columns(3)
    with c1:
        data_bolla = st.text_input("Data", value=datetime.now().strftime("%d/%m/%Y"))
        ora_bolla = st.text_input("Ora", value="8:00")
        booking_ref = st.text_input("Nr. Riferimento", value="01 8572")
        compagnia = st.text_input("Compagnia / Booking", value="ONE IMPORT")
    with c2:
        committente = st.text_input("Committente", value="SILT Srl")
        comm_ind = st.text_input("Indirizzo Comm.", value="Piazza G. Alessi, 2")
        comm_loc = st.text_input("Loc. Committente", value="Genova (GE)")
        comm_piva = st.text_input("P.IVA Comm.", value="03441250101")
    with c3:
        ritiro_term = st.text_input("Terminal Ritiro", value="LA SPEZIA CONTAINER TRML LSCT")
        ritiro_ind = st.text_input("Indirizzo Ritiro", value="MOLO FORNELLI")
        scarico_luogo = st.text_input("Luogo Scarico", value="CONTREPAIR LA SPEZIA")
        scarico_ind = st.text_input("Indirizzo Scarico", value="VIA BOLANO 20 - SANTO STEFANO M.")

    c4, c5, c6 = st.columns(3)
    with c4:
        merce = st.text_input("Merce", value="MERCE VARIA")
        km_viaggio = st.text_input("KM", value="500")
    with c5:
        container = st.text_input("1° Container / Sigillo", value="ONEU 504737 / 3")
        tipo_cont = st.text_input("Container Tipo", value="40 HC")
        peso = st.text_input("Peso Tot. Kg", value="30.115")
    with c6:
        destinazione_merce = st.text_input("Spedizioniere/Dest.", value="SAVINO")

    st.markdown("#### Caricatori")
    c7, c8 = st.columns(2)
    with c7:
        caric1_nome = st.text_input("1° Caricatore", value="MAZZOLENI C/O ZANO")
        caric1_ind = st.text_input("Indirizzo 1° Caric.", value="VIA ROTTA VECCHIA 4 - MONTAGNANA")
    with c8:
        caric2_nome = st.text_input("2° Caricatore (Opzionale)", value="")
        caric2_ind = st.text_input("Indirizzo 2° Caric.", value="")

    if st.button("🖨️ GENERA BOLLA (MODELLO CLONATO)", type="primary", use_container_width=True):
        salva_in_cronologia({
            "Data": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "Tipo": "Emissione Bolla",
            "Cliente": committente,
            "Tratta": f"Rif: {booking_ref}",
            "Totale": "-"
        })

        pdf = FPDF(orientation='P', unit='mm', format='A4')
        pdf.set_margins(10, 10, 10)
        pdf.add_page()
        pdf.set_auto_page_break(False)

        # 1. INTESTAZIONE DINAMICA
        nome_logo = pulisci_testo(st.session_state.vettore_nome).split()[0].lower() if st.session_state.vettore_nome else "logo"
        
        pdf.set_font("Helvetica", "B", 18)
        pdf.set_text_color(100, 100, 100)
        pdf.text(10, 20, nome_logo)
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(150, 150, 150)
        pdf.text(10, 24, "TRANSPORT")

        pdf.set_text_color(0, 0, 200)
        pdf.set_font("Helvetica", "B", 8)
        pdf.text(45, 12, pulisci_testo(st.session_state.vettore_nome))
        pdf.set_font("Helvetica", "", 6)
        pdf.text(45, 16, f"Indirizzo: {pulisci_testo(st.session_state.vettore_indirizzo)} - {pulisci_testo(st.session_state.vettore_loc)}")
        pdf.text(45, 20, f"P.IVA / C.F.: {pulisci_testo(st.session_state.vettore_piva)}")
        pdf.text(45, 24, f"Iscrizione Albo: {pulisci_testo(st.session_state.vettore_albo)}")
        pdf.set_text_color(0, 0, 0)

        draw_fake_barcode(pdf, 120, 12, 70, 12, booking_ref)
        pdf.set_font("Helvetica", "B", 10)
        pdf.text(155, 30, "LETTERA DI VETTURA")
        pdf.set_font("Helvetica", "B", 11)
        pdf.text(155, 35, f"202601000{pulisci_testo(booking_ref).replace(' ','')}")

        # 2. RIGA 1
        y_r1 = 40
        pdf.set_line_width(0.2)
        pdf.rect(10, y_r1, 190, 10)
        pdf.line(40, y_r1, 40, y_r1+10)
        pdf.line(70, y_r1, 70, y_r1+10)
        pdf.line(100, y_r1, 100, y_r1+10)

        pdf.set_font("Helvetica", "", 6)
        pdf.text(12, y_r1+3, "Data")
        pdf.text(42, y_r1+3, "Ora")
        pdf.text(72, y_r1+3, "Nr. Riferimento")
        pdf.text(102, y_r1+3, "Compagnia Booking")

        pdf.set_font("Helvetica", "B", 10)
        pdf.text(12, y_r1+8, pulisci_testo(data_bolla))
        pdf.text(45, y_r1+8, pulisci_testo(ora_bolla))
        pdf.text(80, y_r1+8, pulisci_testo(booking_ref))
        pdf.text(130, y_r1+8, pulisci_testo(compagnia))

        # 3. BLOCCO COMMITTENTE / VETTORE
        y_r2 = 50
        pdf.rect(10, y_r2, 95, 35)
        pdf.rect(105, y_r2, 95, 35)
        
        pdf.set_font("Helvetica", "", 7)
        pdf.text(12, y_r2+4, "Committ.")
        pdf.text(12, y_r2+9, "Indirizzo")
        pdf.text(12, y_r2+14, "Località")
        pdf.text(12, y_r2+19, "Telefono")
        pdf.text(50, y_r2+19, "P.Iva")
        pdf.text(12, y_r2+24, "E-mail")
        pdf.text(12, y_r2+29, "I.Albo n°")

        pdf.set_font("Helvetica", "B", 8)
        pdf.text(35, y_r2+4, pulisci_testo(committente))
        pdf.set_font("Helvetica", "B", 10)
        pdf.text(35, y_r2+9, pulisci_testo(comm_ind))
        pdf.set_font("Helvetica", "B", 8)
        pdf.text(35, y_r2+14, pulisci_testo(comm_loc))
        pdf.text(60, y_r2+19, pulisci_testo(comm_piva))

        pdf.set_font("Helvetica", "", 7)
        pdf.text(107, y_r2+4, "Vettore")
        pdf.text(170, y_r2+4, "P.I.")
        pdf.text(107, y_r2+9, "Località")
        pdf.text(107, y_r2+14, "Telefono")
        pdf.text(150, y_r2+14, "I.Albo n°")
        pdf.text(107, y_r2+19, "E-mail")
        pdf.text(107, y_r2+24, "Autista")
        pdf.text(107, y_r2+29, "Rgs vett.")
        pdf.text(107, y_r2+33, "Veicolo")

        pdf.set_font("Helvetica", "B", 8)
        nome_vett_troncato = pulisci_testo(st.session_state.vettore_nome)[:28]
        pdf.text(125, y_r2+4, nome_vett_troncato)
        pdf.text(175, y_r2+4, pulisci_testo(st.session_state.vettore_piva))
        pdf.text(125, y_r2+9, f"{pulisci_testo(st.session_state.vettore_indirizzo)} - {pulisci_testo(st.session_state.vettore_loc)}")
        pdf.text(165, y_r2+14, pulisci_testo(st.session_state.vettore_albo))
        pdf.text(125, y_r2+24, pulisci_testo(st.session_state.autista))
        pdf.text(125, y_r2+33, f"{pulisci_testo(st.session_state.trattore)}   /   {pulisci_testo(st.session_state.rimorchio)}")

        # 4. BLOCCO RITIRO / SCARICO
        y_r3 = 85
        pdf.rect(10, y_r3, 95, 25)
        pdf.rect(105, y_r3, 95, 25)
        pdf.line(10, y_r3+12.5, 105, y_r3+12.5)

        pdf.set_font("Helvetica", "", 7)
        pdf.text(12, y_r3+4, "Term.Rit. / Caric.")
        pdf.text(12, y_r3+8, "Indirizzo")
        pdf.text(12, y_r3+12, "Località")
        pdf.text(12, y_r3+16, "Luogo scarico")
        pdf.text(12, y_r3+20, "Indirizzo")
        pdf.text(12, y_r3+24, "Località")
        
        pdf.set_font("Helvetica", "B", 8)
        pdf.text(35, y_r3+4, pulisci_testo(ritiro_term))
        pdf.text(35, y_r3+8, pulisci_testo(ritiro_ind))
        pdf.text(35, y_r3+16, pulisci_testo(scarico_luogo))
        pdf.text(35, y_r3+20, pulisci_testo(scarico_ind))

        pdf.set_font("Helvetica", "", 7)
        pdf.text(107, y_r3+4, "1° Container")
        pdf.text(107, y_r3+8, "2° Container")
        pdf.text(107, y_r3+12, "Container tipo")
        pdf.text(165, y_r3+12, "Peso Tot.Kg")
        pdf.text(107, y_r3+16, "Destinazione")
        pdf.text(107, y_r3+20, "Spedizioniere")
        pdf.text(107, y_r3+24, "M/N")
        
        pdf.set_font("Helvetica", "B", 9)
        pdf.text(130, y_r3+4, pulisci_testo(container))
        pdf.text(130, y_r3+12, pulisci_testo(tipo_cont))
        pdf.set_font("Helvetica", "B", 10)
        pdf.text(182, y_r3+12, pulisci_testo(peso))
        pdf.set_font("Helvetica", "B", 9)
        pdf.text(130, y_r3+20, pulisci_testo(destinazione_merce))

        # 5. BLOCCO MERCE E KM 
        y_r4 = 110
        pdf.rect(10, y_r4, 190, 15)
        pdf.set_font("Helvetica", "", 7)
        pdf.text(12, y_r4+4, "Merce")
        pdf.text(12, y_r4+8, "Rif. Al carico")
        pdf.text(75, y_r4+4, "Colli")
        pdf.text(12, y_r4+13, "KM")
        
        pdf.set_font("Helvetica", "B", 9)
        pdf.text(25, y_r4+4, pulisci_testo(merce))
        pdf.text(25, y_r4+13, pulisci_testo(km_viaggio))

        # 6. GRIGLIA CARICATORI 
        y_caric = 125
        caricatori = [caric1_nome, caric2_nome, ""]
        indirizzi = [caric1_ind, caric2_ind, ""]
        
        for i in range(3):
            y_base = y_caric + (i * 16)
            pdf.rect(10, y_base, 85, 16)
            pdf.rect(95, y_base, 105, 16)
            
            pdf.line(95, y_base+5, 200, y_base+5)
            pdf.line(130, y_base, 130, y_base+16)
            pdf.line(165, y_base, 165, y_base+16)
            
            pdf.set_font("Helvetica", "", 7)
            pdf.text(12, y_base+4, f"{i+1}° Caricatore")
            pdf.text(12, y_base+8, "Indirizzo")
            pdf.text(12, y_base+12, "Località")
            pdf.text(60, y_base+15, "P.Iva")
            
            pdf.text(105, y_base+4, "Ora arrivo")
            pdf.text(140, y_base+4, "Ora partenza")
            pdf.text(175, y_base+4, "Sigillo/i")
            
            pdf.set_font("Helvetica", "B", 8)
            pdf.text(32, y_base+4, pulisci_testo(caricatori[i]))
            pdf.text(32, y_base+8, pulisci_testo(indirizzi[i]))

        # 7. OSSERVAZIONI E FIRME
        y_oss = 173
        pdf.rect(10, y_oss, 190, 20)
        pdf.set_font("Helvetica", "", 7)
        pdf.text(12, y_oss+4, "Osservazioni")
        
        y_firm = 193
        pdf.rect(10, y_firm, 190, 12)
        pdf.text(12, y_firm+4, "DICHIARAZIONE RICEVITORE/DESTINATARIO")
        pdf.text(100, y_firm+4, "Constatato integro il sigillo ___________________ apposto mittente")
        pdf.text(100, y_firm+10, "Rimosso sigillo mittente e apposto sigillo ___________________")

        # 8. CONDIZIONI 
        y_cond = 210
        pdf.set_xy(10, y_cond)
        pdf.set_font("Helvetica", "B", 7)
        pdf.cell(190, 4, "CONDIZIONI PARTICOLARI DI TRASPORTO", ln=True)
        testo_condizioni = """Il trasporto va eseguito nel rispetto delle disposizioni legislative e regolamentari poste a tutela della sicurezza di circolazione stradale e sicurezza sociale, in particolar modo rispetto agli art. 61 (sagoma limite), 62 (massa limite), 142 (limite di velocità), 164 (sistemazione del carico sui veicoli), 167 (trasporto di cose sui veicoli e rimorchi), 174 (durata della guida degli autoveicoli adibiti al trasporto di persone e cose) del D.LGS. 30 aprile 1992, N. 258
1) Il caricatore è tenuto ad applicare i sigilli al container in presenza dell'autista.
2) Il ricevitore è tenuto a verificare l'integrità e il numero del sigillo e a rimuoverlo in presenza dell'autista.
3) Il vettore accetta e riconsegna il container nello stato in cui si trova, limitandosi a verificare il sigillo e le condizioni esterne, il vettore, pertanto, non è responsabile della quantità e della qualità e stivaggio della merce trasportata ma solo dell'integrità del sigillo ed ogni riserva o contestazione deve essere immediatamente manifestata all'autista.
4) Il vettore è responsabile delle perdite e/o avarie, in quanto a lui imputabili in base alle norme vigenti e l'avente diritto dichiara di rinunciare ad ogni e qualsiasi domanda verso il vettore per i danni eccedenti la responsabilità.
5) Il trattore con il semirimorchio ed il container, arrivando in tempo utile per le operazioni di carico e/o scarico, dovranno essere lasciati liberi entro i termini di franchigia previsti dall'accordo collettivo nazionale
6) Il caricatore è solo responsabile della veridicità del peso dichiarato riferito alla merce affidata al vettore di conseguenza sono a suo esclusivo carico, indipendentemente dal vincolo della solidarietà, le eventuali sanzioni per violazioni della norma vigente in materia di limiti di peso.
7) L'autista non è tenuto a partecipare in nessuna maniera alle operazioni di carico e/o scarico, ivi compresa l'eventuale scopertura o copertura di containers open top.
8) Le merci trasportate a mezzo autocarro sono assicurate per un importo massimo di euro 30.000,00 , alle condizioni, generali della polizza italiana autocarro (edizione 1972). Per un importo eccedente tale cifra, non ci riterremo responsabili se non tempestivamente preavvisati."""
        
        pdf.set_font("Helvetica", "", 5.5)
        pdf.multi_cell(190, 2.8, testo_condizioni)

        pdf_bytes = pdf.output(dest='S').encode('latin-1', 'replace')
        st.download_button("📥 SCARICA LETTERA DI VETTURA", data=pdf_bytes, file_name=f"Bolla_{pulisci_testo(booking_ref)}.pdf", mime="application/pdf")

# --- TAB 4: CRONOLOGIA ---
with tab_cronologia:
    st.subheader("Storico delle Operazioni")
    dati_cronologia = carica_cronologia()
    if dati_cronologia:
        st.dataframe(dati_cronologia, use_container_width=True)
    else:
        st.info("Nessuna operazione registrata finora.")
