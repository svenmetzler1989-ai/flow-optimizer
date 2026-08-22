import streamlit as st
import time
import requests
import random

# =====================================================================
# 1. DESIGN OCH ANPASSAD BAKGRUNDSFÄRG (Specsavers Pro Theme)
# =====================================================================
st.set_page_config(page_title="Specsavers Core Control Room", layout="wide")

st.markdown("""
    <style>
    /* Ändrar huvudbakgrunden till en mjuk, modern ljusgrå färg */
    .stApp {
        background-color: #f8fafc;
    }
    
    /* GÖR ATT ALLA METRIC-KORT BLIR EXTREMT SNYGGA MED SKUGGA OCH VIT BAKGRUND */
    [data-testid="stMetricBlock"] {
        background-color: #ffffff !important;
        border-radius: 12px !important;
        padding: 20px !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03) !important;
        border: 1px solid #e2e8f0 !important;
    }
    
    /* Snyggare runda expanders för medarbetarlistan */
    .stExpander {
        background-color: #ffffff !important;
        border-radius: 12px !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02) !important;
        border: 1px solid #e2e8f0 !important;
    }
    
    /* Gör tabellerna renare */
    .stTable {
        background-color: #ffffff !important;
        border-radius: 12px !important;
        overflow: hidden;
    }
    </style>
""", unsafe_allow_html=True)

st.title("👓 Specsavers Live Core Optimizer")
st.caption("Avancerad flödesoptimering med automatisk lagerkedja och visuell målstyrning")
st.markdown("---")

# =====================================================================
# 2. LIVE-KOPPLING TILL DIN SUPABASE-DATABAS
# =====================================================================
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except:
    st.error("⚠️ Kom ihåg att lägga till dina Supabase-nycklar i Streamlit Secrets!")
    st.stop()

def fetch_live_data():
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    url = f"{SUPABASE_URL}/rest/v1/imi_live_data?select=*"
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        if isinstance(data, list) and len(data) > 0:
            row = data[0]
            if "inbound_stock" in row: return row
    except: pass
    
    return {
        "queue_pick_stock": 4500, "queue_pick_non_stock": 800, "queue_pack": 400,
        "inbound_stock": 6, "inbound_non_stock": 2, "putaway_stock": 120, "putaway_non_stock": 20
    }

START_PICK_STOCK = 4500
START_PICK_NON = 800
START_PACK = 400
START_PUTAWAY_STOCK = 120
START_PUTAWAY_NON = 20

# =====================================================================
# 3. MEDARBETARDATABAS (30 Personer)
# =====================================================================
if 'medarbetare_info' not in st.session_state:
    medarbetare_info = {
        "EMP-101": {"namn": "Anna", "pick_speed": 115, "pack_speed": 95, "putaway_speed": 85, "start_zon": "Plock Stock"},
        "EMP-102": {"namn": "Per", "pick_speed": 85, "pack_speed": 125, "putaway_speed": 75, "start_zon": "Packning"},
        "EMP-103": {"namn": "Lars", "pick_speed": 100, "pack_speed": 110, "putaway_speed": 95, "start_zon": "Putaway Stock"},
        "EMP-104": {"namn": "Elin", "pick_speed": 105, "pack_speed": 100, "putaway_speed": 80, "start_zon": "Plock Non-Stock"},
        "EMP-105": {"namn": "Mikael", "pick_speed": 95, "pack_speed": 105, "putaway_speed": 70, "start_zon": "Inbound Stock"},
    }
    start_zoner_pool = ["Plock Stock", "Packning", "Plock Stock", "Inbound Stock", "Putaway Stock", "Plock Non-Stock"]
    for i in range(106, 131):
        emp_id = f"EMP-{i}"
        medarbetare_info[emp_id] = {
            "namn": f"Medarbetare {i}",
            "pick_speed": random.randint(95, 110),
            "pack_speed": random.randint(100, 115),
            "putaway_speed": random.randint(75, 85),
            "start_zon": random.choice(start_zoner_pool)
        }
    st.session_state.medarbetare_info = medarbetare_info

if 'placering' not in st.session_state:
    st.session_state.placering = {emp_id: info["start_zon"] for emp_id, info in st.session_state.medarbetare_info.items()}

if 'db_data' not in st.session_state:
    st.session_state.db_data = fetch_live_data()

# =====================================================================
# 4. SIDOPANEL: DEMOKONTROLLER OCH VEM SOM GÖR VAD
# =====================================================================
st.sidebar.header("🕹️ Demo-kontroller")
live_sim = st.sidebar.toggle("▶️ Starta Live-Simulering", value=False)
live_sim_speed = st.sidebar.slider("Simuleringshastighet (Demo-tempo)", 10, 100, 40)

p_in_stock = list(st.session_state.placering.values()).count("Inbound Stock")
p_in_non = list(st.session_state.placering.values()).count("Inbound Non-Stock")
p_put_stock = list(st.session_state.placering.values()).count("Putaway Stock")
p_put_non = list(st.session_state.placering.values()).count("Putaway Non-Stock")
p_pick_stock = list(st.session_state.placering.values()).count("Plock Stock")
p_pick_non = list(st.session_state.placering.values()).count("Plock Non-Stock")
p_pack = list(st.session_state.placering.values()).count("Packning")

st.sidebar.markdown("---")
st.sidebar.header("👥 Bemanningsöversikt (Vem gör vad)")
st.sidebar.markdown(f"📥 **Inbound Stock:** `{p_in_stock} pers`  \n(Mål: 35 min / pall)")
st.sidebar.markdown(f"📥 **Inbound Non-Stock:** `{p_in_non} pers`")
st.sidebar.markdown(f"🧱 **Putaway Stock:** `{p_put_stock} pers`  \n(Mål: 80 rader/h)")
st.sidebar.markdown(f"🧱 **Putaway Non-Stock:** `{p_put_non} pers`")
st.sidebar.markdown(f"🛒 **Plock Stock:** `{p_pick_stock} pers`  \n(Mål: 100 order/h)")
st.sidebar.markdown(f"⚡ **Plock Non-Stock:** `{p_pick_non} pers`")
st.sidebar.markdown(f"📦 **Packning:** `{p_pack} pers`  \n(Mål: 110 paket/h)")

# =====================================================================
# 5. KAPACITETSBERÄKNINGAR UTIFRÅN INSTÄMPPLINGARNA
# =====================================================================
total_pick_stock_speed = sum(st.session_state.medarbetare_info[emp]["pick_speed"] for emp in st.session_state.medarbetare_info if st.session_state.placering[emp] == "Plock Stock")
total_pick_non_speed = sum(st.session_state.medarbetare_info[emp]["pick_speed"] for emp in st.session_state.medarbetare_info if st.session_state.placering[emp] == "Plock Non-Stock")
total_pack_speed = sum(st.session_state.medarbetare_info[emp]["pack_speed"] for emp in st.session_state.medarbetare_info if st.session_state.placering[emp] == "Packning")
total_put_stock_speed = sum(st.session_state.medarbetare_info[emp]["putaway_speed"] for emp in st.session_state.medarbetare_info if st.session_state.placering[emp] == "Putaway Stock")
total_put_non_speed = sum(st.session_state.medarbetare_info[emp]["putaway_speed"] for emp in st.session_state.medarbetare_info if st.session_state.placering[emp] == "Putaway Non-Stock")

total_in_stock_speed = p_in_stock * 1.71
total_in_non_speed = p_in_non * 5.0

# Skapa minne för simulerad tid (Startar kl 06:00 = 360 minuter från midnatt)
if 'sim_minutes' not in st.session_state:
    st.session_state.sim_minutes = 360

visnings_timme = st.session_state.sim_minutes // 60
visnings_minut = st.session_state.sim_minutes % 60
klocktid = f"{visnings_timme:02d}:{visnings_minut:02d}"

if st.session_state.sim_minutes < 870:
    aktivt_skift = "Formiddagsskift (06:00 - 14:30)"
elif st.session_state.sim_minutes < 1380:
    aktivt_skift = "Eftermiddagsskift (14:30 - 23:00)"
else:
    aktivt_skift = "Skift slut för dagen"
    live_sim = False

st.sidebar.markdown("---")
st.sidebar.subheader("⏰ Produktionsklocka")
st.sidebar.info(f"**Aktuell Tid:** {klocktid}  \n**Skift:** {aktivt_skift}")

if st.sidebar.button("🔄 Återställ klockan till 06:00"):
    st.session_state.sim_minutes = 360
    st.rerun()

# =====================================================================
# 6. SIMULERINGSLOGIK MED AUTOMATISK LAGERKEDJA & AI-BESLUTSSTÖD
# =====================================================================
if live_sim and st.session_state.sim_minutes < 1380:
    st.session_state.sim_minutes += 10
    
    plockat_stock = int(total_pick_stock_speed / live_sim_speed)
    plockat_non = int(total_pick_non_speed / live_sim_speed)
    packat = int(total_pack_speed / live_sim_speed)
    inlagrat_stock = int(total_put_stock_speed / live_sim_speed)
    inlagrat_non = int(total_put_non_speed / live_sim_speed)

    st.session_state.db_data["queue_pick_stock"] = max(0, st.session_state.db_data["queue_pick_stock"] - plockat_stock)
    st.session_state.db_data["queue_pack"] = max(0, st.session_state.db_data["queue_pack"] + (plockat_stock + plockat_non) - packat)
    st.session_state.db_data["putaway_stock"] = max(0, st.session_state.db_data["putaway_stock"] - inlagrat_stock)
    st.session_state.db_data["putaway_non_stock"] = max(0, st.session_state.db_data["putaway_non_stock"] - inlagrat_non)

    # 📥 Simulerat inflöde: Chans att det plötsligt rullar in nya pallar mitt under skiftet!
    if random.random() > 0.95:
        st.session_state.db_data["inbound_stock"] += random.randint(1, 3)
        st.toast("🚚 Ny leverans! Fler pallar har landat på Inbound Stock.", icon="🚚")

    # LAGERKEDJA: Inbound Stock betas av
    if p_in_stock > 0 and st.session_state.db_data["inbound_stock"] > 0 and random.random() > 0.7:
        st.session_state.db_data["inbound_stock"] -= 1
        st.session_state.db_data["putaway_stock"] += 20  

    # LAGERKEDJA: Inbound Non-Stock betas av
    if p_in_non > 0 and st.session_state.db_data["inbound_non_stock"] > 0 and random.random() > 0.5:
        st.session_state.db_data["inbound_non_stock"] -= 1
        st.session_state.db_data["putaway_non_stock"] += 10

    # Lagerkedja för Non-Stock plock
    if inlagrat_non > 0 and st.session_state.db_data["putaway_non_stock"] > 0:
        st.session_state.db_data["queue_pick_non_stock"] = max(0, st.session_state.db_data["queue_pick_non_stock"] - plockat_non + int(inlagrat_non * 0.8))
    else:
        st.session_state.db_data["queue_pick_non_stock"] = max(0, st.session_state.db_data["queue_pick_non_stock"] - plockat_non)

# HÄR LÄGGER VI IN DINA NYA AI-VARNINGSTRIANGLAR OCH GODKÄNNANDE-KNAPPAR
st.markdown("### 🚦 AI Flödesassistent (Beslutsstöd)")

# Hjälpfunktion för att manuellt styra om första lediga medarbetare via knapp
def flytta_en_person(fran_zon, till_zon):
    for emp, lokation in st.session_state.placering.items():
        if lokation == fran_zon:
            st.session_state.placering[emp] = till_zon
            st.toast(f"🏃 {st.session_state.medarbetare_info[emp]['namn']} omstyrd till {till_zon}!", icon="✅")
            st.rerun()
            break

# SCENARIO 1: Inbound Stock är helt klart, men personal står kvar där
if st.session_state.db_data["inbound_stock"] == 0 and p_in_stock > 0:
    st.warning("⚠️ **FLÖDESVARNING: INBOUND STOCK ÄR KLART!**")
    st.markdown(f"Det finns inga pallar kvar på Inbound, men **{p_in_stock} medarbetare** står kvar på zonen utan arbetsuppgifter.")
    if st.button("🏃 Verkställ: Flytta 1 ledig medarbetare till Putaway Stock", key="ai_move_in_to_put"):
        flytta_en_person("Inbound Stock", "Putaway Stock")

# SCENARIO 2: Plock Stock är helt klart, men personal plockar fortfarande luft
if st.session_state.db_data["queue_pick_stock"] == 0 and p_pick_stock > 0:
    st.warning("⚠️ **FLÖDESVARNING: PLOCK STOCK ÄR TOMT!**")
    st.markdown(f"Målet för Plock Stock är nått! Flytta dina **{p_pick_stock} plockare** till packstationerna för att stänga skiftet.")
    if st.button("🏃 Verkställ: Flytta 1 ledig plockare till Packning", key="ai_move_pick_to_pack"):
        flytta_en_person("Plock Stock", "Packning")

# SCENARIO 3: Det har kommit in nya pallar på Inbound, men ingen jobbar där
if st.session_state.db_data["inbound_stock"] > 0 and p_in_stock == 0:
    st.info("💡 **FLÖDESREKOMMENDATION: NYTT GODS PÅ INBOUND**")
    st.markdown(f"Det ligger **{st.session_state.db_data['inbound_stock']} pallar** på Inbound Stock, men ingen personal är tilldelad. Risk för stockning i mottagningen.")
    if p_pack > 2: # Flytta bara om vi har tillräckligt med packare
        if st.button("🏃 Verkställ: Flytta 1 medarbetare från Packning till Inbound Stock", key="ai_move_pack_to_in"):
            flytta_en_person("Packning", "Inbound Stock")

st.markdown("---")


# =====================================================================
# 7. FUNKTION FÖR ATT SKAPA SMARTA, FÄRGKODADE GRAFER
# =====================================================================
def visa_status_graf(titel, nuvarande, start_varde):
    procent = min(1.0, max(0.0, 1.0 - (nuvarande / max(start_varde, 1))))
    
    if procent == 1.0:
        farg = "🟢 Målet Nått!"
        farg_kod = "green"
    elif procent >= 0.75:
        farg = "🟡 Nära Målet (Guldläge)"
        farg_kod = "orange"
    else:
        farg = "🔴 Under Målet (Kräver resurser)"
        farg_kod = "red"
        
    st.markdown(f"**{titel}** | Status: :{farg_kod}[{farg}] — {int(procent*100)}%")
    st.progress(procent)

st.subheader("🎯 Visuell Måluppfyllnad (Real-Time KPI)")
col_g1, col_g2 = st.columns(2)

with col_g1:
    visa_status_graf("🛒 Kunduppdrag: Plock STOCK", st.session_state.db_data["queue_pick_stock"], START_PICK_STOCK)
    visa_status_graf("⚡ Kunduppdrag: Plock NON-STOCK", st.session_state.db_data["queue_pick_non_stock"], START_PICK_NON)
    visa_status_graf("⚡ Inlagring: Putaway NON-STOCK", st.session_state.db_data["putaway_non_stock"], START_PUTAWAY_NON)

with col_g2:
    visa_status_graf("🏁 Slutsteg: Packning (Försegling)", st.session_state.db_data["queue_pack"], START_PACK)
    visa_status_graf("📥 Inlagring: Putaway STOCK", st.session_state.db_data["putaway_stock"], START_PUTAWAY_STOCK)

st.markdown("---")

# =====================================================================
# 8. REALTIDSTATUS (Inklusive alla Non-Stock-volymer)
# =====================================================================
st.subheader("📊 Aktuell IMI-Status (Köer just nu)")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Inbound STOCK (Pallar)", f"{st.session_state.db_data['inbound_stock']} st")
col2.metric("Putaway STOCK (Rader)", f"{st.session_state.db_data['putaway_stock']} rader")
col3.metric("Plockkö STOCK (Order)", f"{st.session_state.db_data['queue_pick_stock']} order")
col4.metric("Väntar vid PACKSTATIONER", f"{st.session_state.db_data['queue_pack']} order")

# Extra rad för Non-Stock-volymerna under de ordinarie mätarna
col_n1, col_n2, col_n3, col_n4 = st.columns(4)
col_n1.metric("Inbound NON-STOCK (Pallar)", f"{st.session_state.db_data['inbound_non_stock']} st")
col_n2.metric("Putaway NON-STOCK (Rader)", f"{st.session_state.db_data['putaway_non_stock']} rader")
col_n3.metric("Plockkö NON-STOCK (Order)", f"{st.session_state.db_data['queue_pick_non_stock']} order")
col_n4.empty() # Lämnas tom för att behålla symmetrin i gränssnittet

st.markdown("---")

# =====================================================================
# 9. GÖMD MEDARBETARHANTERING (Expander & Uppslag med namn)
# =====================================================================
with st.expander("🔍 Hantera och ställ om de 30 medarbetarkoderna (Klicka för att öppna)", expanded=False):
    ROLLER = ["Inbound Stock", "Inbound Non-Stock", "Putaway Stock", "Putaway Non-Stock", "Plock Stock", "Plock Non-Stock", "Packning"]
    emp_list = list(st.session_state.medarbetare_info.keys())
    c_emp1, c_emp2, c_emp3 = st.columns(3)
    
    with c_emp1:
        for emp_id in emp_list[:10]:
            info = st.session_state.medarbetare_info[emp_id]
            st.session_state.placering[emp_id] = st.selectbox(f"👤 {info['namn']} ({emp_id})", ROLLER, index=ROLLER.index(st.session_state.placering[emp_id]), key=f"sel_{emp_id}")
    with c_emp2:
        for emp_id in emp_list[10:20]:
            info = st.session_state.medarbetare_info[emp_id]
            st.session_state.placering[emp_id] = st.selectbox(f"👤 {info['namn']} ({emp_id})", ROLLER, index=ROLLER.index(st.session_state.placering[emp_id]), key=f"sel_{emp_id}")
    with c_emp3:
        for emp_id in emp_list[20:30]:
            info = st.session_state.medarbetare_info[emp_id]
            st.session_state.placering[emp_id] = st.selectbox(f"👤 {info['namn']} ({emp_id})", ROLLER, index=ROLLER.index(st.session_state.placering[emp_id]), key=f"sel_{emp_id}")

    st.markdown("### 🔍 Slå upp specifik medarbetare live")
    namn_val_lista = [f"{st.session_state.medarbetare_info[eid]['namn']} ({eid})" for eid in emp_list]
    valt_namn_med_id = st.selectbox("Välj en medarbetare för att granska effektivitet:", namn_val_lista)
    
    # Hittar rätt ID baserat på valet i rullistan
    valt_id = [eid for eid in emp_list if st.session_state.medarbetare_info[eid]['namn'] in valt_namn_med_id][0]
    valda_info = st.session_state.medarbetare_info[valt_id]
    valda_zon = st.session_state.placering[valt_id]
    
    col_e1, col_e2 = st.columns(2)
    col_e1.write(f"**Medarbetare:** {valda_info['namn']} | **Zon:** {valda_zon}")
    col_e2.write(f"**Klockad kapacitet:** {valda_info['pick_speed']} order/h plock | {valda_info['pack_speed']} paket/h pack")

# =====================================================================
# 10. TIDSKALKYLER OCH DIAGNOSMOTOR (AI-Åtgärdsförslag)
# =====================================================================
time_pick_stock = st.session_state.db_data['queue_pick_stock'] / max(total_pick_stock_speed, 0.1)
time_pack = st.session_state.db_data['queue_pack'] / max(total_pack_speed, 0.1)

st.subheader("🧠 Systemdiagnos & AI-Rekommendationer")

def flytta_medarbetare_till(avdelning_från, avdelning_till):
    for emp, lokation in st.session_state.placering.items():
        if lokation == avdelning_från:
            st.session_state.placering[emp] = avdelning_till
            st.toast(f"✅ Personal omstyrd till {avdelning_till}!", icon="🏃")
            break

if time_pack > time_pick_stock and st.session_state.db_data['queue_pack'] > 600:
    st.error("🚨 **PRODUKTIONSSTOPP: FLASKHALS VID PACKBORDEN!**")
    st.info("💡 **Rekommendation:** Flytta resurser till Packning.")
    if st.button("🏃 Verkställ: Flytta 1 person till Packning", key="btn_pack"):
        flytta_medarbetare_till("Plock Stock", "Packning")
        st.rerun()
elif time_pick_stock > 3.5:
    st.warning("⚠️ **FLASKHALS DETEKTERAD: PLOCKKÖN SLÄPAR**")
    st.info("💡 **Rekommendation:** Öka antalet plockare.")
    if st.button("🏃 Verkställ: Flytta 1 person till Plock Stock", key="btn_pick"):
        flytta_medarbetare_till("Inbound Stock", "Plock Stock")
        st.rerun()
else:
    st.success("✅ **FLÖDET ÄR OPTIMALT BALANSERAT**")

# =====================================================================
# 11. PROCESS-PROGNOS (TABELLEN LÄNGST NER)
# =====================================================================
st.markdown("### 📊 Detaljerad tidsprognos för skiftet")
prognos_data = {
    "Processflöde": ["Inbound: Stock (35 min/pall)", "Inlagring: Putaway Stock (80 rader/h)", "Plock: Stock (100 order/h snitt)", "Packning (110 paket/h snitt)"],
    "Aktuell Bemanning (Antal)": [p_in_stock, p_put_stock, p_pick_stock, p_pack],
    "Total Gruppkapacitet / timme": [
        f"{round(total_in_stock_speed, 1)} pallar", 
        f"{total_put_stock_speed} rader", 
        f"{total_pick_stock_speed} order", 
        f"{total_pack_speed} paket"
    ],
    "Tid till tomt (Timmar)": [
        round(st.session_state.db_data['inbound_stock']/max(total_in_stock_speed,0.1), 1), 
        round(st.session_state.db_data['putaway_stock']/max(total_put_stock_speed,0.1), 1), 
        round(time_pick_stock, 1), 
        round(time_pack, 1)
    ]
}
st.table(prognos_data)

if live_sim:
    time.sleep(2)
    st.rerun()
