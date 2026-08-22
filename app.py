import streamlit as st
import time
import requests
import random

# =====================================================================
# 1. LIVE-KOPPLING TILL DIN SUPABASE-DATABAS (Helt felsäker version)
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
    
    # Fallback med era exakta ingångsvolymer för skiftet (Mål/Startvärden)
    return {
        "queue_pick_stock": 4500, "queue_pick_non_stock": 800, "queue_pack": 400,
        "inbound_stock": 6, "inbound_non_stock": 2, "putaway_stock": 120, "putaway_non_stock": 20
    }

# =====================================================================
# 2. HEMSIDANS GRUNDFORMAT
# =====================================================================
st.set_page_config(page_title="Specsavers Shift Control Room", layout="wide")
st.title("👓 Specsavers Core Control Room")
st.caption("Visuell flödesoptimering och måluppfyllnad i realtid")
st.markdown("---")

# Fasta ursprungsvolymer för att kunna räkna ut % mot målet (Hur mycket vi har betat av)
START_PICK_STOCK = 4500
START_PICK_NON = 800
START_PACK = 400
START_PUTAWAY = 120

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

# =====================================================================
# 4. DEMOKONTROLLER & MINNE
# =====================================================================
st.sidebar.header("🕹️ Demo-kontroller")
live_sim = st.sidebar.toggle("▶️ Starta Live-Simulering", value=False)

if 'db_data' not in st.session_state:
    st.session_state.db_data = fetch_live_data()

if 'placering' not in st.session_state:
    st.session_state.placering = {emp_id: info["start_zon"] for emp_id, info in st.session_state.medarbetare_info.items()}

# =====================================================================
# 5. GRAFER OCH MÅLUPPFYLLNAD (Plock & Pack status mot målet)
# =====================================================================
st.subheader("🎯 Måluppfyllnad (Hur mycket har vi plockat/packat klart?)")

# Räkna ut procentuell framgång (Max 100%)
progress_pick_stock = min(1.0, max(0.0, 1.0 - (st.session_state.db_data["queue_pick_stock"] / START_PICK_STOCK)))
progress_pick_non = min(1.0, max(0.0, 1.0 - (st.session_state.db_data["queue_pick_non_stock"] / START_PICK_NON)))
progress_pack = min(1.0, max(0.0, 1.0 - (st.session_state.db_data["queue_pack"] / START_PACK)))
progress_putaway = min(1.0, max(0.0, 1.0 - (st.session_state.db_data["putaway_stock"] / START_PUTAWAY)))

# Visa snygga progress bars som fylls i live
col_g1, col_g2 = st.columns(2)
with col_g1:
    st.markdown(f"📦 **Kunduppdrag: Plock STOCK** ({int(progress_pick_stock*100)}% klart till dagens mål)")
    st.progress(progress_pick_stock)
    
    st.markdown(f"⚡ **Kunduppdrag: Plock NON-STOCK** ({int(progress_pick_non*100)}% klart till dagens mål)")
    st.progress(progress_pick_non)

with col_g2:
    st.markdown(f"🏁 **Slutsteg: Packning (Försegling)** ({int(progress_pack*100)}% klart till dagens mål)")
    st.progress(progress_pack)
    
    st.markdown(f"📥 **Inlagring: Putaway STOCK** ({int(progress_putaway*100)}% klart till dagens mål)")
    st.progress(progress_putaway)

st.markdown("---")

# =====================================================================
# 6. REALTIDSTATUS (Siffrorna från Supabase)
# =====================================================================
st.subheader("📊 Aktuell IMI-Status (Köer just nu)")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Inbound STOCK", f"{st.session_state.db_data['inbound_stock']} st")
col2.metric("Putaway STOCK", f"{st.session_state.db_data['putaway_stock']} rader")
col3.metric("Plockkö STOCK", f"{st.session_state.db_data['queue_pick_stock']} order")
col4.metric("Väntar vid PACKSTATIONER", f"{st.session_state.db_data['queue_pack']} order")

st.markdown("---")

# =====================================================================
# 7. EXTREMT ÖVERSIKTLIG PERSONALSTYRNING (Drop-down & Expander)
# =====================================================================
st.subheader("👥 Medarbetaröversikt & Kodzonshantering")

# Vi gömmer listan i en "Expander" som man kan klicka på för att öppna/stänga!
with st.expander("🔍 Klicka här för att visa/ändra kodzoner på de 30 medarbetarna", expanded=False):
    st.write("Här kan du ändra avdelningskod live på vem som helst:")
    ROLLER = ["Inbound Stock", "Inbound Non-Stock", "Putaway Stock", "Putaway Non-Stock", "Plock Stock", "Plock Non-Stock", "Packning"]
    
    # Visas snyggt i 3 kolumner inuti den stängda fliken
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

# EN DROP-DOWN FÖR ATT KOLLA EN SPECIFIK MEDARBETARE LIVE
st.markdown("### 🔍 Slå upp specifik personalkod")
valda_emp = st.selectbox("Välj en medarbetare för att granska effektivitet och nuvarande orderzon:", emp_list)
valda_info = st.session_state.medarbetare_info[valda_emp]
valda_zon = st.session_state.placering[valda_emp]

col_emp_v1, col_emp_v2, col_emp_v3 = st.columns(3)
col_emp_v1.info(f"**Namn:** {valda_info['namn']} ({valda_emp})")
col_emp_v2.success(f"**Aktiv Kodzon just nu:** {valda_zon}")
if "Plock" in valda_zon:
    hastighet_text = f"{valda_info['pick_speed']} order / timme"
elif "Pack" in valda_zon:
    hastighet_text = f"{valda_info['pack_speed']} paket / timme"
else:
    hastighet_text = f"{valda_info['putaway_speed']} rader / timme"
col_emp_v3.metric("Individuell Löpande Effektivitet", hastighet_text)


# =====================================================================
# 8. BERÄKNA TOTAL KAPACITET UTIFRÅN DE 30 INSTÄMPPLINGARNA
# =====================================================================
p_in_stock = list(st.session_state.placering.values()).count("Inbound Stock")
p_in_non = list(st.session_state.placering.values()).count("Inbound Non-Stock")
p_put_stock = list(st.session_state.placering.values()).count("Putaway Stock")
p_put_non = list(st.session_state.placering.values()).count("Putaway Non-Stock")
p_pick_stock = list(st.session_state.placering.values()).count("Plock Stock")
p_pick_non = list(st.session_state.placering.values()).count("Plock Non-Stock")
p_pack = list(st.session_state.placering.values()).count("Packning")

total_pick_stock_speed = sum(st.session_state.medarbetare_info[emp]["pick_speed"] for emp in st.session_state.medarbetare_info if st.session_state.placering[emp] == "Plock Stock")
total_pick_non_speed = sum(st.session_state.medarbetare_info[emp]["pick_speed"] for emp in st.session_state.medarbetare_info if st.session_state.placering[emp] == "Plock Non-Stock")
total_pack_speed = sum(st.session_state.medarbetare_info[emp]["pack_speed"] for emp in st.session_state.medarbetare_info if st.session_state.placering[emp] == "Packning")
total_put_stock_speed = sum(st.session_state.medarbetare_info[emp]["putaway_speed"] for emp in st.session_state.medarbetare_info if st.session_state.placering[emp] == "Putaway Stock")
total_put_non_speed = sum(st.session_state.medarbetare_info[emp]["putaway_speed"] for emp in st.session_state.medarbetare_info if st.session_state.placering[emp] == "Putaway Non-Stock")

total_in_stock_speed = p_in_stock * 1.71
total_in_non_speed = p_in_non * 5.0

# Prestandamål och inställningar i sidopanelen
st.sidebar.markdown("---")
st.sidebar.header("⚙️ Skiftets Tempo")
speed_pick = st.sidebar.slider("Plockhastighet (Justera globalt snitt %)", 40, 150, 100)
live_sim_speed = st.sidebar.slider("Simuleringshastighet (Demo-tempo)", 10, 100, 40)

SPEED_INBOUND_STOCK = 1.71  
SPEED_INBOUND_NON_STOCK = 5.0  
SPEED_PUTAWAY_STOCK = 80         
SPEED_PUTAWAY_NON_STOCK = 120    
SPEED_PACK = 110                 

# =====================================================================
# 9. SIMULERINGSLOGIK
# =====================================================================
if live_sim:
    plockat_stock = int(total_pick_stock_speed / live_sim_speed)
    plockat_non = int(total_pick_non_speed / live_sim_speed)
    packat = int(total_pack_speed / live_sim_speed)
    inlagrat_stock = int(total_put_stock_speed / live_sim_speed)
    inlagrat_non = int(total_put_non_speed / live_sim_speed)

    st.session_state.db_data["queue_pick_stock"] = max(0, st.session_state.db_data["queue_pick_stock"] - plockat_stock)
    st.session_state.db_data["queue_pick_non_stock"] = max(0, st.session_state.db_data["queue_pick_non_stock"] - plockat_non)
    st.session_state.db_data["queue_pack"] = max(0, st.session_state.db_data["queue_pack"] + (plockat_stock + plockat_non) - packat)
    st.session_state.db_data["putaway_stock"] = max(0, st.session_state.db_data["putaway_stock"] - inlagrat_stock)
    st.session_state.db_data["putaway_non_stock"] = max(0, st.session_state.db_data["putaway_non_stock"] - inlagrat_non)
    
    if p_in_stock > 0 and st.session_state.db_data["inbound_stock"] > 0 and random.random() > 0.6:
        st.session_state.db_data["inbound_stock"] -= 1

# =====================================================================
# 10. TIDSKALKYLER OCH DIAGNOSMOTOR
# =====================================================================
time_pick_stock = st.session_state.db_data['queue_pick_stock'] / max(total_pick_stock_speed, 0.1)
time_pack = st.session_state.db_data['queue_pack'] / max(total_pack_speed, 0.1)

st.markdown("---")
st.subheader("🧠 Systemdiagnos & AI-Rekommendationer")

def flytta_medarbetare_till(avdelning_från, avdelning_till):
    for emp, lokation in st.session_state.placering.items():
        if lokation == avdelning_från:
            st.session_state.placering[emp] = avdelning_till
            st.toast(f"✅ Medarbetare flyttades till {avdelning_till}!", icon="🏃")
            break

# Flaskhals A: Packborden
if time_pack > time_pick_stock and st.session_state.db_data['queue_pack'] > 600:
    st.error("🚨 **PRODUKTIONSSTOPP: FLASKHALS VID PACKBORDEN!**")
    st.markdown(f"**Analys:** Med nuvarande bemanning växer packkön. Det står **{st.session_state.db_data['queue_pack']} order** på vagnarna.")
    st.info("💡 **Rekommendation:** Flytta resurser till Packning.")
    if st.button("🏃 Verkställ: Flytta 1 person till Packning", key="btn_pack"):
        flytta_medarbetare_till("Plock Stock", "Packning")
        st.rerun()

# Flaskhals B: Plockkön
elif time_pick_stock > 3.5:
    st.warning("⚠️ **FLASKHALS DETEKTERAD: PLOCKKÖN SLÄPAR**")
    st.markdown(f"**Analys:** Gårdagens orderbörda kräver **{time_pick_stock:.1f} timmar** med nuvarande plockstyrka.")
    st.info("💡 **Rekommendation:** Öka antalet plockare.")
    if st.button("🏃 Verkställ: Flytta 1 person till Plock Stock", key="btn_pick"):
        flytta_medarbetare_till("Inbound Stock", "Plock Stock")
        st.rerun()

else:
    st.success("✅ **FLÖDET ÄR OPTIMALT BALANSERAT**")
    st.write("Alla 30 medarbetarkoder arbetar i perfekt symmetri.")

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
    time.sleep(3)
    st.rerun()
