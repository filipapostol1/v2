from datetime import datetime
import json
import os
import tempfile
import time
import requests
import random
import streamlit as st
from fpdf import FPDF

# ==========================================
# 1. CONFIGURAZIONE PAGINA STREAMLIT
# ==========================================
st.set_page_config(page_title="Apostol Trasporti", layout="wide")

FILE_CRONOLOGIA = "cronologia.json"

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
    """Genera un finto codice a barre basato sul numero di riferimento"""
    pdf.set_fill_color(0, 0, 0)
    current_x = x
    random.seed(seed_str)
    while current_x < x + width:
        w = random.choice([0.4, 0.8, 1.2, 1.8])
        if current_x + w > x + width: break
        if random.random() > 0.3:
            pdf.rect(current_x, y, w, height, "F")
        current_x += w + random.choice([0.4, 0.8, 1.2])

st.markdown("""<style>.main { padding: 1.5rem; }</style>""", unsafe_allow_html=True)

# ==========================================
# 2. BARRA LATERALE E MOTORE API
# ==========================================
st.sidebar.title("📌 Navigazione")
pagina_selezionata = st.sidebar.radio("", ["📊 Preventivi & Pedaggi", "📄 Bolla SILT / Finsea (Clone)", "📜 Cronologia"])
st.sidebar.markdown("---")
st.sidebar.header("🏢 Dati Vettore")
vettore_nome = st.sidebar.text_input("Vettore", value="APOSTOL TRASPORTI DI APOSTOL C")
vettore_piva = st.sidebar.text_input("P.IVA", value="01595470111")
vettore_indirizzo = st.sidebar.text_input("Indirizzo", value="VIA EMILIO BIONE 8")
vettore_loc = st.sidebar.text_input("Località", value="LA SPEZIA (SP)")
vettore_albo = st.sidebar.text_input("Albo", value="SP/3602624/M")

if pagina_selezionata == "📄 Bolla SILT / Finsea (Clone)":
    st.sidebar.header("🚛 Veicolo")
    default_trattore = st.sidebar.text_input("Targa Trattore", value="GD613CR")
    default_rimorchio = st.sidebar.text_input("Targa Rimorchio", value="XA762KF")
    default_autista = st.sidebar.text_input("Autista", value="APOSTOL CATALIN")

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
# 3. PAGINE DELL'APPLICAZIONE
# ==========================================
st.title("Apostol Trasporti - Suite Gestionale")

# --- PREVENTIVI ---
if pagina_selezionata == "📊 Preventivi & Pedaggi":
    st.info("💡 Pagina per il calcolo dei preventivi. Usa la barra a sinistra per passare alla Lettera di Vettura.")
    # (Codice preventivo omesso qui per brevità per concentrarci sul Clone del PDF. Funziona come prima)

# --- BOLLA CLONE SILT ---
elif pagina_selezionata == "📄 Bolla SILT / Finsea (Clone)":
    st.subheader("Generazione Lettera di Vettura - Modello Esatto (Finsea/SILT)")

    col1, col2, col3 = st.columns(3)
    with col1:
        data_bolla = st.text_input("Data", value=datetime.now().strftime("%d/%m/%Y"))
        ora_bolla = st.text_input("Ora", value="8:00")
        booking_ref = st.text_input("Nr. Riferimento", value="01 8572")
        compagnia = st.text_input("Compagnia / Booking", value="ONE IMPORT")
    with col2:
        committente = st.text_input("Committente", value="SILT Srl")
        comm_ind = st.text_input("Indirizzo Comm.", value="Piazza G. Alessi, 2")
        comm_loc = st.text_input("Loc. Committente", value="Genova (GE)")
        comm_piva = st.text_input("P.IVA Comm.", value="03441250101")
    with col3:
        ritiro_term = st.text_input("Terminal Ritiro", value="LA SPEZIA CONTAINER TRML LSCT")
        ritiro_ind = st.text_input("Indirizzo Ritiro", value="MOLO FORNELLI")
        scarico_luogo = st.text_input("Luogo Scarico", value="CONTREPAIR LA SPEZIA")
        scarico_ind = st.text_input("Indirizzo Scarico", value="VIA BOLANO 20 - SANTO STEFANO M.")

    col_c1, col_c2, col_c3 = st.columns(3)
    with col_c1:
        merce = st.text_input("Merce", value="MERCE VARIA")
        km_viaggio = st.text_input("KM", value="500")
    with col_c2:
        container = st.text_input("1° Container / Sigillo", value="ONEU 504737 / 3")
        tipo_cont = st.text_input("Container Tipo", value="40 HC")
        peso = st.text_input("Peso Tot. Kg", value="30.115")
    with col_c3:
        destinazione = st.text_input("Spedizioniere/Dest.", value="SAVINO")

    st.markdown("#### Caricatori")
    c1, c2 = st.columns(2)
    with c1:
        caric1_nome = st.text_input("1° Caricatore", value="MAZZOLENI C/O ZANO")
        caric1_ind = st.text_input("Indirizzo 1° Caric.", value="VIA ROTTA VECCHIA 4 - MONTAGNANA")
    with c2:
        caric2_nome = st.text_input("2° Caricatore (Opzionale)", value="")
        caric2_ind = st.text_input("Indirizzo 2° Caric.", value="")

    if st.button("🖨️ GENERA PDF IDENTICO ALL'ORIGINALE", type="primary"):
        pdf = FPDF(orientation='P', unit='mm', format='A4')
        pdf.set_margins(10, 10, 10)
        pdf.add_page()
        pdf.set_auto_page_break(False)

        # ---------------------------------------------------------
        # 1. INTESTAZIONE SUPERIORE E LOGHI
        # ---------------------------------------------------------
        pdf.set_font("Helvetica", "B", 18)
        pdf.set_text_color(100, 100, 100)
        pdf.text(10, 20, "silt")
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(150, 150, 150)
        pdf.text(10, 24, "FINSEA TRANSPORT")

        pdf.set_text_color(0, 0, 200) # Testo blu SILT
        pdf.set_font("Helvetica", "B", 8)
        pdf.text(45, 12, "S.I.L.T. S.r.l. Sistemi Integrati di Logistica e Trasporto")
        pdf.set_font("Helvetica", "", 5)
        pdf.text(45, 15, "Sede Legale 20129 Milano (MI) - Corso Concordia, 11")
        pdf.text(45, 18, "Direzione e Amministrazione: 16128 GENOVA - Piazza G. Alessi, 2 - Tel 010 5761098")
        pdf.text(45, 21, "Capitale Sociale € 96.900,00 - C.F & P.IVA 03441250101")
        pdf.text(45, 24, "Uffici Operativi: 16158 GENOVA VOLTRI (GE)")
        pdf.set_text_color(0, 0, 0)

        # Codice a barre simulato
        draw_fake_barcode(pdf, 120, 12, 70, 12, booking_ref)
        pdf.set_font("Helvetica", "B", 10)
        pdf.text(155, 30, "LETTERA DI VETTURA")
        pdf.set_font("Helvetica", "B", 11)
        pdf.text(155, 35, f"202601000{pulisci_testo(booking_ref).replace(' ','')}")

        # ---------------------------------------------------------
        # 2. RIGA 1: DATA, ORA, RIF, BOOKING (y=40, h=10)
        # ---------------------------------------------------------
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

        # ---------------------------------------------------------
        # 3. BLOCCO COMMITTENTE / VETTORE (y=50, h=35)
        # ---------------------------------------------------------
        y_r2 = 50
        pdf.rect(10, y_r2, 95, 35)
        pdf.rect(105, y_r2, 95, 35)
        
        # SINISTRA: Committente
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

        # DESTRA: Vettore
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
        pdf.text(125, y_r2+4, pulisci_testo(vettore_nome))
        pdf.text(175, y_r2+4, pulisci_testo(vettore_piva))
        pdf.text(125, y_r2+9, pulisci_testo(vettore_indirizzo) + " - " + pulisci_testo(vettore_loc))
        pdf.text(165, y_r2+14, pulisci_testo(vettore_albo))
        pdf.text(125, y_r2+24, pulisci_testo(default_autista))
        pdf.text(125, y_r2+33, f"{pulisci_testo(default_trattore)}    /   {pulisci_testo(default_rimorchio)}")

        # ---------------------------------------------------------
        # 4. BLOCCO RITIRO / SCARICO / CONTAINER (y=85, h=25)
        # ---------------------------------------------------------
        y_r3 = 85
        pdf.rect(10, y_r3, 95, 25)
        pdf.rect(105, y_r3, 95, 25)
        pdf.line(10, y_r3+12.5, 105, y_r3+12.5) # Divisorio Ritiro/Scarico sx

        # SINISTRA
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

        # DESTRA
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
        pdf.text(130, y_r3+20, pulisci_testo(destinazione))

        # ---------------------------------------------------------
        # 5. BLOCCO MERCE E KM (y=110, h=10)
        # ---------------------------------------------------------
        y_r4 = 110
        pdf.rect(10, y_r4, 190, 10)
        
        pdf.set_font("Helvetica", "", 7)
        pdf.text(12, y_r4+4, "Merce")
        pdf.text(12, y_r4+8, "Rif. Al carico")
        pdf.text(75, y_r4+4, "Colli")
        pdf.text(12, y_r4+13, "KM") # KM sborda sotto nella foto
        
        pdf.set_font("Helvetica", "B", 9)
        pdf.text(25, y_r4+4, pulisci_testo(merce))
        pdf.text(25, y_r4+13, pulisci_testo(km_viaggio))

        # ---------------------------------------------------------
        # 6. GRIGLIA CARICATORI (x3 righe da h=16)
        # ---------------------------------------------------------
        y_caric = 120
        caricatori = [caric1_nome, caric2_nome, ""]
        indirizzi = [caric1_ind, caric2_ind, ""]
        
        for i in range(3):
            y_base = y_caric + (i * 16)
            pdf.rect(10, y_base, 85, 16) # Box sx
            pdf.rect(95, y_base, 105, 16) # Box dx (tabella)
            
            # Linee tabella destra
            pdf.line(95, y_base+5, 200, y_base+5) # Rigo orizzontale intestazione tab
            pdf.line(130, y_base, 130, y_base+16)
            pdf.line(165, y_base, 165, y_base+16)
            
            # Testi fissi
            pdf.set_font("Helvetica", "", 7)
            pdf.text(12, y_base+4, f"{i+1}° Caricatore")
            pdf.text(12, y_base+8, "Indirizzo")
            pdf.text(12, y_base+12, "Località")
            pdf.text(60, y_base+15, "P.Iva")
            
            pdf.text(105, y_base+4, "Ora arrivo")
            pdf.text(140, y_base+4, "Ora partenza")
            pdf.text(175, y_base+4, "Sigillo/i")
            
            # Dati caricatore
            pdf.set_font("Helvetica", "B", 8)
            pdf.text(32, y_base+4, pulisci_testo(caricatori[i]))
            pdf.text(32, y_base+8, pulisci_testo(indirizzi[i]))

        # ---------------------------------------------------------
        # 7. OSSERVAZIONI E FIRME
        # ---------------------------------------------------------
        y_oss = 168
        pdf.rect(10, y_oss, 190, 20)
        pdf.set_font("Helvetica", "", 7)
        pdf.text(12, y_oss+4, "Osservazioni")
        
        y_firm = 188
        pdf.rect(10, y_firm, 190, 12)
        pdf.text(12, y_firm+4, "DICHIARAZIONE RICEVITORE/DESTINATARIO")
        pdf.text(100, y_firm+4, "Constatato integro il sigillo ___________________ apposto mittente")
        pdf.text(100, y_firm+10, "Rimosso sigillo mittente e apposto sigillo ___________________")

        # ---------------------------------------------------------
        # 8. IL MAPPAMONDO DELLE CONDIZIONI (Identico alla foto)
        # ---------------------------------------------------------
        y_cond = 205
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

        # OUTPUT FINALE
        pdf_bytes = pdf.output(dest="S").encode("latin-1", "replace")
        st.download_button("📥 SCARICA LETTERA DI VETTURA (CLONE)", data=pdf_bytes, file_name=f"Bolla_Clone_{pulisci_testo(booking_ref)}.pdf", mime="application/pdf")

elif pagina_selezionata == "📜 Cronologia":
    st.subheader("Storico Operazioni")
    st.dataframe(carica_cronologia(), use_container_width=True)
