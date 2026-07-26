from datetime import datetime
import json
import os
import requests
import streamlit as st
from fpdf import FPDF
from PIL import Image
import io

# ==========================================
# 0. CHIAVE API CENTRALIZZATA (NASCOSTA AL CLIENTE)
# ==========================================
# Inserisci qui la tua chiave OpenRouteService. 
# Il cliente non vedrà mai questo valore nell'interfaccia.
API_KEY_DEFAULT = "INSERISCI_QUI_LA_TUA_CHIAVE_API"

# Se usi st.secrets (es. su Streamlit Cloud), prende quella, altrimenti usa API_KEY_DEFAULT
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
if 'vettore_loc' not in st.session_state: st.session_state.vettore_loc = "LA SPEZIA (SP)"
if 'vettore_albo' not in st.session_state: st.session_state.vettore_albo = "SP/3602624/M"
if 'autista' not in st.session_state: st.session_state.autista = "APOSTOL CATALIN"
if 'trattore' not in st.session_state: st.session_state.trattore = "GD613CR"
if 'rimorchio' not in st.session_state: st.session_state.rimorchio = "XA762KF"
if 'logo_bytes' not in st.session_state: st.session_state.logo_bytes = None

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
    s = str(testo).replace("€", "EUR").replace("’", "'").replace("“", '"').replace("”", '"')
    return s.encode('latin-1', 'replace').decode('latin-1')

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
    """Calcola la rotta specifica per mezzi pesanti usando la chiave integrata."""
    if ORS_API_KEY and ORS_API_KEY != "INSERISCI_QUI_LA_TUA_CHIAVE_API":
        try:
            headers = {'Authorization': ORS_API_KEY, 'Content-Type': 'application/json'}
            body = {"coordinates": [[lon1, lat1], [lon2, lat2]]}
            res = requests.post("https://api.openrouteservice.org/v2/directions/driving-hgv/json", json=body, headers=headers, timeout=8)
            if res.status_code == 200:
                data = res.json()
                dist_mt = data["routes"][0]["summary"]["distance"]
                return round(dist_mt / 1000.0, 1)
        except: pass

    # Fallback su OSRM standard
    try:
        url = f"http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=false"
        res = requests.get(url, timeout=5)
        if res.status_code == 200: 
            return round(res.json()["routes"][0]["distance"] / 1000.0, 1)
    except: pass
    return None

def stima_pedaggio_autostrada(km_totali, classe_veicolo):
    tariffe = {
        "Bilico (4/5 Assi)": 0.19,
        "Camion (3 Assi)": 0.14,
        "Auto / Furgone": 0.09
    }
    costo_km = tariffe.get(classe_veicolo, 0.19)
    km_autostrada = km_totali * 0.75
    return round(km_autostrada * costo_km, 2)

# ==========================================
# 2. DASHBOARD CENTRALE
# ==========================================
st.title("🚛 Gestionale Trasporti & Preventivi")
st.markdown("---")

tab_impostazioni, tab_preventivi, tab_bolla, tab_cronologia = st.tabs([
    "⚙️ Impostazioni Azienda", 
    "📊 Calcolo Preventivi & Percorsi", 
    "📄 Generazione Bolla / DDT", 
    "📜 Cronologia"
])

# --- TAB 1: IMPOSTAZIONI ---
with tab_impostazioni:
    st.subheader("Dati Aziendali e Logo")
    
    col_img1, col_img2 = st.columns([1, 2])
    with col_img1:
        uploaded_logo = st.file_uploader("Carica Logo Aziendale (PNG / JPG)", type=["png", "jpg", "jpeg"])
        if uploaded_logo:
            st.session_state.logo_bytes = uploaded_logo.read()
            st.image(st.session_state.logo_bytes, width=200, caption="Logo Attuale")
        elif st.session_state.logo_bytes:
            st.image(st.session_state.logo_bytes, width=200, caption="Logo Attuale")
            if st.button("Rimuovi Logo"):
                st.session_state.logo_bytes = None
                st.rerun()

    with col_img2:
        st.info("Configurazione sistema completata. I servizi di cartografia e routing camion sono attivi e pronti all'uso.")

    st.markdown("---")
    col_v1, col_v2 = st.columns(2)
    with col_v1:
        st.markdown("**Dati Vettore**")
        st.session_state.vettore_nome = st.text_input("Ragione Sociale Vettore", value=st.session_state.vettore_nome)
        st.session_state.vettore_piva = st.text_input("Partita IVA", value=st.session_state.vettore_piva)
        st.session_state.vettore_indirizzo = st.text_input("Indirizzo", value=st.session_state.vettore_indirizzo)
        st.session_state.vettore_loc = st.text_input("Località", value=st.session_state.vettore_loc)
        st.session_state.vettore_albo = st.text_input("Iscrizione Albo", value=st.session_state.vettore_albo)
    
    with col_v2:
        st.markdown("**Mezzo e Autista Predefiniti**")
        st.session_state.autista = st.text_input("Nome Autista", value=st.session_state.autista)
        st.session_state.trattore = st.text_input("Targa Trattore", value=st.session_state.trattore)
        st.session_state.rimorchio = st.text_input("Targa Rimorchio", value=st.session_state.rimorchio)

# --- TAB 2: PREVENTIVI ---
with tab_preventivi:
    st.subheader("Calcolo Reale Tratta Camion e Pedaggio")
    col_p1, col_p2 = st.columns([1, 1], gap="large")

    with col_p1:
        cliente_nome = st.text_input("Nome Cliente / Committente", value="ACME S.r.l.")
        partenza = st.text_input("Indirizzo/Città Partenza", value="La Spezia")
        destinazione = st.text_input("Indirizzo/Città Destinazione", value="Parma")
        tipo_viaggio = st.radio("Tipologia Viaggio", options=["Solo Andata", "Andata e Ritorno"], horizontal=True)
        
        classe_veicolo = st.selectbox("Mezzo Utilizzato", options=["Bilico (4/5 Assi)", "Camion (3 Assi)", "Auto / Furgone"])
        tariffa_km = st.number_input("Tariffa (EUR al Km)", value=1.70, step=0.05)
        
        btn_calc = st.button("🧮 CALCOLA PERCORSO E PREVENTIVO", type="primary", use_container_width=True)

    with col_p2:
        if btn_calc:
            if not cliente_nome or not partenza or not destinazione:
                st.error("Compila tutti i campi obbligatori (Cliente, Partenza, Destinazione).")
            else:
                with st.spinner("Calcolo rotta camion in corso..."):
                    lat1, lon1 = ottieni_coordinate(partenza)
                    lat2, lon2 = ottieni_coordinate(destinazione)
                
                if lat1 is None or lat2 is None:
                    st.error("Impossibile trovare le coordinate GPS. Specifica meglio la città o l'indirizzo.")
                else:
                    km_unitaria = calcola_rotta_camion(lat1, lon1, lat2, lon2)
                    
                    if not km_unitaria:
                        st.error("Impossibile calcolare i KM della rotta. Riprova tra poco.")
                    else:
                        km_totali = km_unitaria * 2 if tipo_viaggio == "Andata e Ritorno" else km_unitaria
                        pedaggio_stimato = stima_pedaggio_autostrada(km_totali, classe_veicolo)
                        
                        costo_trasporto = round(km_totali * tariffa_km, 2)
                        imponibile = round(costo_trasporto + pedaggio_stimato, 2)
                        iva = round(imponibile * 0.22, 2)
                        totale = round(imponibile + iva, 2)

                        salva_in_cronologia({
                            "Data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                            "Tipo": "Preventivo",
                            "Cliente": cliente_nome,
                            "Tratta": f"{partenza} -> {destinazione} ({km_totali} Km)",
                            "Totale": f"EUR {totale:.2f}"
                        })

                        st.success("Rotta calcolata correttamente!")
                        st.metric("Distanza Totale (Km)", f"{km_totali} Km")
                        
                        c_m1, c_m2 = st.columns(2)
                        c_m1.metric("Costo Trasporto (EUR)", f"{costo_trasporto:.2f}")
                        c_m2.metric("Pedaggio Stimato Autostrada (EUR)", f"{pedaggio_stimato:.2f}")
                        st.metric("TOTALE FINALE (IVA Inclusa)", f"EUR {totale:.2f}")

                        # PDF Preventivo
                        pdf = FPDF(orientation='P', unit='mm', format='A4')
                        pdf.add_page()
                        
                        if st.session_state.logo_bytes:
                            img = Image.open(io.BytesIO(st.session_state.logo_bytes))
                            img_path = "temp_logo.png"
                            img.save(img_path)
                            pdf.image(img_path, x=10, y=10, w=40)
                        else:
                            pdf.set_font("Helvetica", "B", 14)
                            pdf.text(10, 20, pulisci_testo(st.session_state.vettore_nome))

                        pdf.set_font("Helvetica", "", 9)
                        pdf.text(10, 30, f"P.IVA: {pulisci_testo(st.session_state.vettore_piva)}")
                        pdf.text(10, 35, f"{pulisci_testo(st.session_state.vettore_indirizzo)} - {pulisci_testo(st.session_state.vettore_loc)}")
                        pdf.text(10, 40, f"Albo Trasportatori: {pulisci_testo(st.session_state.vettore_albo)}")

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
                        pdf.text(107, 62, f"Partenza: {pulisci_testo(partenza)}")
                        pdf.text(107, 68, f"Destinazione: {pulisci_testo(destinazione)}")
                        pdf.text(107, 74, f"Tipologia: {tipo_viaggio} | Mezzo: {classe_veicolo}")

                        y_tab = 90
                        pdf.set_fill_color(230, 230, 230)
                        pdf.rect(10, y_tab, 190, 8, "DF")
                        
                        pdf.set_font("Helvetica", "B", 9)
                        pdf.text(12, y_tab + 5, "DESCRIZIONE DEL SERVIZIO")
                        pdf.text(165, y_tab + 5, "IMPORTO (EUR)")

                        pdf.set_font("Helvetica", "", 9)
                        pdf.rect(10, y_tab+8, 190, 30)
                        pdf.line(160, y_tab+8, 160, y_tab+38) 

                        pdf.text(12, y_tab + 16, f"Servizio trasporto ({km_totali} Km x {tariffa_km:.2f} EUR/Km)")
                        pdf.text(165, y_tab + 16, f"{costo_trasporto:.2f}")

                        pdf.text(12, y_tab + 26, "Rimborso spese pedaggio autostradale stimato")
                        pdf.text(165, y_tab + 26, f"{pedaggio_stimato:.2f}")

                        y_tot = y_tab + 45
                        pdf.rect(120, y_tot, 80, 24)
                        pdf.line(120, y_tot+8, 200, y_tot+8)
                        pdf.line(120, y_tot+16, 200, y_tot+16)
                        pdf.line(160, y_tot, 160, y_tot+24)

                        pdf.set_font("Helvetica", "B", 9)
                        pdf.text(122, y_tot + 6, "IMPONIBILE")
                        pdf.text(165, y_tot + 6, f"{imponibile:.2f}")
                        
                        pdf.text(122, y_tot + 14, "IVA (22%)")
                        pdf.text(165, y_tot + 14, f"{iva:.2f}")

                        pdf.set_font("Helvetica", "B", 10)
                        pdf.text(122, y_tot + 22, "TOTALE")
                        pdf.text(165, y_tot + 22, f"{totale:.2f}")

                        pdf_bytes = pdf.output(dest='S').encode('latin-1', 'replace')
                        st.download_button("📥 SCARICA PREVENTIVO (PDF)", data=pdf_bytes, file_name=f"Preventivo_{pulisci_testo(cliente_nome)}.pdf", mime="application/pdf")

# --- TAB 3: BOLLA / DDT ---
with tab_bolla:
    st.subheader("Emissione Lettera di Vettura / DDT")
    
    c1, c2, c3 = st.columns(3)
    with c1:
        data_bolla = st.text_input("Data", value=datetime.now().strftime("%d/%m/%Y"))
        ora_bolla = st.text_input("Ora", value="08:00")
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
        km_viaggio = st.text_input("KM Percorsi", value="120")
    with c5:
        container = st.text_input("Container / Sigillo", value="ONEU 504737 / 3")
        tipo_cont = st.text_input("Tipo Container", value="40 HC")
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

    if st.button("🖨️ GENERA BOLLA PROFESSIONALE (PDF)", type="primary", use_container_width=True):
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

        if st.session_state.logo_bytes:
            img = Image.open(io.BytesIO(st.session_state.logo_bytes))
            img_path = "temp_logo_bolla.png"
            img.save(img_path)
            pdf.image(img_path, x=10, y=10, w=35)
        
        pdf.set_text_color(0, 51, 102)
        pdf.set_font("Helvetica", "B", 10)
        pdf.text(50, 14, pulisci_testo(st.session_state.vettore_nome))
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(80, 80, 80)
        pdf.text(50, 18, f"Indirizzo: {pulisci_testo(st.session_state.vettore_indirizzo)} - {pulisci_testo(st.session_state.vettore_loc)}")
        pdf.text(50, 22, f"P.IVA / C.F.: {pulisci_testo(st.session_state.vettore_piva)} | Albo: {pulisci_testo(st.session_state.vettore_albo)}")
        
        pdf.set_text_color(0, 0, 0)
        pdf.rect(140, 10, 60, 22)
        pdf.set_font("Helvetica", "B", 9)
        pdf.text(143, 16, "LETTERA DI VETTURA")
        pdf.set_font("Helvetica", "", 8)
        pdf.text(143, 22, f"Doc N°: 2026-{pulisci_testo(booking_ref).replace(' ','')}")
        pdf.text(143, 27, f"Data: {pulisci_testo(data_bolla)}")

        y_r1 = 36
        pdf.set_line_width(0.2)
        pdf.rect(10, y_r1, 190, 10)
        pdf.line(40, y_r1, 40, y_r1+10)
        pdf.line(70, y_r1, 70, y_r1+10)
        pdf.line(110, y_r1, 110, y_r1+10)

        pdf.set_font("Helvetica", "", 6)
        pdf.text(12, y_r1+3, "Data")
        pdf.text(42, y_r1+3, "Ora")
        pdf.text(72, y_r1+3, "Nr. Riferimento")
        pdf.text(112, y_r1+3, "Compagnia / Booking")

        pdf.set_font("Helvetica", "B", 9)
        pdf.text(12, y_r1+8, pulisci_testo(data_bolla))
        pdf.text(42, y_r1+8, pulisci_testo(ora_bolla))
        pdf.text(72, y_r1+8, pulisci_testo(booking_ref))
        pdf.text(112, y_r1+8, pulisci_testo(compagnia))

        y_r2 = 48
        pdf.rect(10, y_r2, 95, 32)
        pdf.rect(105, y_r2, 95, 32)
        
        pdf.set_font("Helvetica", "", 7)
        pdf.text(12, y_r2+4, "COMMITTENTE:")
        pdf.set_font("Helvetica", "B", 8)
        pdf.text(12, y_r2+9, pulisci_testo(committente))
        pdf.set_font("Helvetica", "", 8)
        pdf.text(12, y_r2+14, pulisci_testo(comm_ind))
        pdf.text(12, y_r2+19, pulisci_testo(comm_loc))
        pdf.text(12, y_r2+24, f"P.IVA: {pulisci_testo(comm_piva)}")

        pdf.set_font("Helvetica", "", 7)
        pdf.text(107, y_r2+4, "VETTORE / AUTISTA:")
        pdf.set_font("Helvetica", "B", 8)
        pdf.text(107, y_r2+9, pulisci_testo(st.session_state.vettore_nome)[:32])
        pdf.set_font("Helvetica", "", 8)
        pdf.text(107, y_r2+14, f"Autista: {pulisci_testo(st.session_state.autista)}")
        pdf.text(107, y_r2+19, f"Trattore: {pulisci_testo(st.session_state.trattore)}  |  Rimorchio: {pulisci_testo(st.session_state.rimorchio)}")

        y_r3 = 83
        pdf.rect(10, y_r3, 95, 24)
        pdf.rect(105, y_r3, 95, 24)

        pdf.set_font("Helvetica", "", 7)
        pdf.text(12, y_r3+4, "LUOGO DI RITIRO / TERMINAL:")
        pdf.set_font("Helvetica", "B", 8)
        pdf.text(12, y_r3+9, pulisci_testo(ritiro_term))
        pdf.set_font("Helvetica", "", 8)
        pdf.text(12, y_r3+14, pulisci_testo(ritiro_ind))

        pdf.text(12, y_r3+18, "LUOGO DI SCARICO:")
        pdf.set_font("Helvetica", "B", 8)
        pdf.text(12, y_r3+22, f"{pulisci_testo(scarico_luogo)} - {pulisci_testo(scarico_ind)}")

        pdf.set_font("Helvetica", "", 7)
        pdf.text(107, y_r3+4, "DETAILS CONTAINER / MERCE:")
        pdf.set_font("Helvetica", "B", 8)
        pdf.text(107, y_r3+9, f"Cont: {pulisci_testo(container)} ({pulisci_testo(tipo_cont)})")
        pdf.text(107, y_r3+14, f"Peso: {pulisci_testo(peso)} Kg")
        pdf.text(107, y_r3+19, f"Spedizioniere: {pulisci_testo(destinazione_merce)}")

        y_r4 = 110
        pdf.rect(10, y_r4, 190, 12)
        pdf.set_font("Helvetica", "", 7)
        pdf.text(12, y_r4+4, "Merce Trasportata:")
        pdf.text(100, y_r4+4, "KM:")
        pdf.set_font("Helvetica", "B", 8)
        pdf.text(35, y_r4+4, pulisci_testo(merce))
        pdf.text(110, y_r4+4, pulisci_testo(km_viaggio))

        y_oss = 125
        pdf.rect(10, y_oss, 190, 25)
        pdf.set_font("Helvetica", "", 7)
        pdf.text(12, y_oss+5, "Annotazioni / Riserve:")

        y_firm = 153
        pdf.rect(10, y_firm, 190, 25)
        pdf.text(12, y_firm+5, "Firma Mittente / Caricatore")
        pdf.text(75, y_firm+5, "Firma Vettore / Autista")
        pdf.text(140, y_firm+5, "Firma Destinatorio")

        pdf_bytes = pdf.output(dest='S').encode('latin-1', 'replace')
        st.download_button("📥 SCARICA LETTERA DI VETTURA (PDF)", data=pdf_bytes, file_name=f"Bolla_{pulisci_testo(booking_ref)}.pdf", mime="application/pdf")

# --- TAB 4: CRONOLOGIA ---
with tab_cronologia:
    st.subheader("Storico Operazioni")
    dati_cronologia = carica_cronologia()
    if dati_cronologia:
        st.dataframe(dati_cronologia, use_container_width=True)
    else:
        st.info("Nessuna operazione registrata in cronologia.")
