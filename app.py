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
            if "inbound_stock" in row:
                return row
    except: 
        pass
    
    # FALLBACK: Om något saknas i Supabase kör vi dessa perfekta Specsavers-volymer
    return {
        "queue_pick_stock": 4500, 
        "queue_pick_non_stock": 800, 
        "queue_pack": 400,
        "inbound_stock": 6, 
        "inbound_non_stock": 2, 
        "putaway_stock": 120, 
        "putaway_non_stock": 20
    }

# =====================================================================
# 2. HEMSIDANS GRUNDFORMAT
# =====================================================================
st.set_page_config(page_title="Specsavers Full Skift Optimizer", layout="wide")
st.title("👓 Specsavers Flödes-Optimering (30-mannaskift)")
st.caption("Fullskaligt beslutsstöd baserat på 30 individuella personalkoder och realtidseffektivitet")
st.markdown("---")

# =====================================================================
# 3. SKAPAR 30 INDIVIDUELLA MEDARBETARE (Hela din personalstyrka)
# =====================================================================
medarbetare_info = {
    "EMP-101": {"namn": "Anna", "pick_speed": 115, "pack_speed": 95, "putaway_speed": 85, "start_zon": "Plock Stock"},
    "EMP-102": {"namn": "Per", "pick_speed": 85, "pack_speed": 125, "putaway_speed": 75, "start_zon": "Packning"},
    "EMP-103": {"namn": "Lars", "pick_speed": 100, "pack_speed": 110, "putaway_speed": 95, "start_zon": "Putaway Stock"},
    "EMP-104": {"namn": "Elin", "pick_speed": 105, "pack_speed": 100, "putaway_speed": 80, "start_zon": "Plock Non-Stock"},
    "EMP-105": {"namn": "Mikael", "pick_speed": 95, "pack_speed": 105, "putaway_speed": 70, "start_zon": "Inbound Stock"},
}

start_zoner_pool = ["Plock Stock", "Packning", "Plock Stock", "Inbound Stock", "Putaway Non-Stock", "Plock Non-Stock"]
for i in range(106, 131):
    emp_id = f"EMP-{i}"
    medarbetare_info[emp_id] = {
        "namn": f"Medarbetare {i}",
        "pick_speed": random.randint(90, 115),
        "pack_speed": random.randint(95, 120),
        "putaway_speed": random.randint(70, 90),
        "start_zon": random.choice(start_zoner_pool)
    }

# =====================================================================
# 4. DEMOKONTROLLER OCH MINNE FÖR PLACERING
# =====================================================================
st.sidebar.header("🕹️ Demo-kontroller")
live_sim = st.sidebar.toggle("▶️ Starta Live-Simulering", value=False)

if 'db_data' not in st.session_state:
    st.session_state.db_data = fetch_live_data()

if 'placering' not in st.session_state:
    st.session_state.placering = {emp_id: info["start_zon"] for emp_id, info in medarbetare_info.items()}

# =====================================================================
# 5. GRÄNSSNITT: REALTIDSTATUS HÖGST UPP
# =====================================================================
st.subheader("📊 Aktuell IMI-Status (Stora volymer)")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Inbound STOCK", f"{st.session_state.db_data['inbound_stock']} st")
col2.metric("Putaway STOCK", f"{st.session_state.db_data['putaway_stock']} rader")
col3.metric("Plockkö STOCK", f"{st.session_state.db_data['queue_pick_stock']} order")
col4.metric("Väntar vid PACKSTATIONER", f"{st.session_state.db_data['queue_pack']} order")

st.markdown("---")

# =====================================================================
# 6. CENTRERAD PERSONALSTYRNING (Live-redigering av 30 personer)
# =====================================================================
st.subheader("👥 Skiftets Medarbetarlista (30 aktiva personalkoder)")
st.write("Ändra avdelning direkt i listan nedan för att styra om ditt 30-mannateam:")

ROLLER = ["Inbound Stock", "Inbound Non-Stock", "Putaway Stock", "Putaway Non-Stock", "Plock Stock", "Plock Non-Stock", "Packning"]

emp_list = list(medarbetare_info.keys())
c_emp1, c_emp2, c_emp3 = st.columns(3)

with c_emp1:
    st.markdown("**Anställd 1 - 10**")
    for emp_id in emp_list[:10]:
        info = medarbetare_info[emp_id]
        st.session_state.placering[emp_id] = st.selectbox(
            f"👤 {info['namn']} ({emp_id})", ROLLER, 
            index=ROLLER.index(st.session_state.placering[emp_id]), key=f"sel_{emp_id}"
        )

with c_emp2:
    st.markdown("**Anställd 11 - 20**")
    for emp_id in emp_list[10:20]:
        info = medarbetare_info[emp_id]
        st.session_state.placering[emp_id] = st.selectbox(
            f"👤 {info['namn']} ({emp_id})", ROLLER, 
            index=ROLLER.index(st.session_state.placering[emp_id]), key=f"sel_{emp_id}"
        )

with c_emp3:
    st.markdown("**Anställd 21 - 30**")
    for emp_id in emp_list[20:30]:
        info = medarbetare_info[emp_id]
        st.session_state.placering[emp_id] = st.selectbox(
            f"👤 {info['namn']} ({emp_id})", ROLLER, 
            index=ROLLER.index(st.session_state.placering[emp_id]), key=f"sel_{emp_id}"
        )

# =====================================================================
# 7. BERÄKNA TOTAL KAPACITET UTIFRÅN DE 30 INSTÄMPPLINGARNA
# =====================================================================
p_in_stock = list(st.session_state.placering.values()).count("Inbound Stock")
p_in_non = list(st.session_state.placering.values()).count("Inbound Non-Stock")
p_put_stock = list(st.session_state.placering.values()).count("Putaway Stock")
p_put_non = list(st.session_state.placering.values()).count("Putaway Non-Stock")
p_pick_stock = list(st.session_state.placering.values()).count("Plock Stock")
p_pick_non = list(st.session_state.placering.values()).count("Plock Non-Stock")
p_pack = list(st.session_state.placering.values()).count("Packning")

total_pick_stock_speed = sum(medarbetare_info[emp]["pick_speed"] for emp in medarbetare_info if st.session_state.placering[emp] == "Plock Stock")
total_pick_non_speed = sum(medarbetare_info[emp]["pick_speed"] for emp in medarbetare_info if st.session_state.placering[emp] == "Plock Non-Stock")
total_pack_speed = sum(medarbetare_info[emp]["pack_speed"] for emp in medarbetare_info if st.session_state.placering[emp] == "Packning")
total_put_stock_speed = sum(medarbetare_info[emp]["putaway_speed"] for emp in medarbetare_info if st.session_state.placering[emp] == "Putaway Stock")
total_put_non_speed = sum(medarbetare_info[emp]["putaway_speed"] for emp in medarbetare_info if st.session_state.placering[emp] == "Putaway Non-Stock")

total_in_stock_speed = p_in_stock * 1.71
total_in_non_speed = p_in_non * 5.0

# Prestandamål och inställningar i sidopanelen
st.sidebar.markdown("---")
st.sidebar.header("⚙️ Skiftets Tempo")
speed_pick = st.sidebar.slider("Plockhastighet (Order/h per person)", 40, 150, 100)
live_sim_speed = st.sidebar.slider("Simuleringshastighet", 10, 100, 40)

SPEED_INBOUND_STOCK = 1.71  
SPEED_INBOUND_NON_STOCK = 5.0  
SPEED_PUTAWAY_STOCK = 80         
SPEED_PUTAWAY_NON_STOCK = 120    
SPEED_PACK = 110                 

# =====================================================================
# 8. SIMULERINGSLOGIK
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
# 9. TIDSKALKYLER OCH DIAGNOSMOTOR
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

# Flaskhals A: Packborden hinner inte med de 30 personerna
if time_pack > time_pick_stock and st.session_state.db_data['queue_pack'] > 600:
    st.error("🚨 **PRODUKTIONSSTOPP: FLASKHALS VID PACKBORDEN!**")
    st.markdown(f"**Analys:** Med nuvarande bemanning växer packkön oroväckande snabbt. Det står **{st.session_state.db_data['queue_pack']} order** på vagnarna.")
    st.info("💡 **Rekommendation:** Flytta omedelbart resurser till Packning för att öppna upp flödet.")
    if st.button("🏃 Verkställ: Flytta 1 person till Packning", key="btn_pack"):
        flytta_medarbetare_till("Plock Stock", "Packning")
        st.rerun()

# Flaskhals B: Plockkön är för stor för nuvarande plockare
elif time_pick_stock > 3.5:
    st.warning("⚠️ **FLASKHALS DETEKTERAD: PLOCKKÖN SLÄPAR**")
    st.markdown(f"**Analys:** Gårdagens orderbörda kräver **{time_pick_stock:.1f} timmar** att beta av med nuvarande plockstyrka. Risk för sena avgångar.")
    st.info("💡 **Rekommendation:** Öka antalet plockare genom att flytta personal från Inbound/Putaway.")
    if st.button("🏃 Verkställ: Flytta 1 person till Plock Stock", key="btn_pick"):
        flytta_medarbetare_till("Inbound Stock", "Plock Stock")
        st.rerun()

else:
    st.success("✅ **FLÖDET ÄR OPTIMALT BALANSERAT FÖR DITT 30-MANNA TEAM**")
    st.write("Alla 30 medarbetarkoder arbetar i perfekt symetri i detta nu.")

# =====================================================================
# 10. PROCESS-PROGNOS (TABELLEN LÄNGST NER)
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
