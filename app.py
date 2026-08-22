import streamlit as st
import time
import requests
import random

# =====================================================================
# 1. LIVE-KOPPLING TILL DIN SUPABASE-DATABAS
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
        if data and len(data) > 0: 
            return data[0]  # Hämtar den första raden från tabellen
    except: 
        pass
    
    # Exakt dina startsiffror om anslutningen sviktar under demot
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
st.set_page_config(page_title="Specsavers Core Optimizer", layout="wide")
st.title("👓 Specsavers Flödes-Optimering (Live-Demo)")
st.caption("Intelligent beslutsstöd med era exakta prestandamål och tidsstandarder")
st.markdown("---")

# =====================================================================
# 3. SIDOPANEL: INSTÄLLNINGAR & BEMANNING
# =====================================================================
st.sidebar.header("🕹️ Demo-kontroller")
live_sim = st.sidebar.toggle("▶️ Starta Live-Simulering", value=False)

if 'p_pick_stock' not in st.session_state: st.session_state.p_pick_stock = 14
if 'p_pick_non' not in st.session_state: st.session_state.p_pick_non = 3
if 'p_pack' not in st.session_state: st.session_state.p_pack = 6
if 'p_in_stock' not in st.session_state: st.session_state.p_in_stock = 3
if 'p_in_non' not in st.session_state: st.session_state.p_in_non = 1
if 'p_put_stock' not in st.session_state: st.session_state.p_put_stock = 2
if 'p_put_non' not in st.session_state: st.session_state.p_put_non = 1

st.sidebar.markdown("---")
st.sidebar.header("👥 Aktiv Bemanning (Skift)")

st.sidebar.subheader("📥 Inbound & Inlagring")
p_in_stock = st.sidebar.slider("Inbound Stock", 0, 10, st.session_state.p_in_stock, key="slider_in_stock")
p_in_non = st.sidebar.slider("Inbound Non-Stock", 0, 5, st.session_state.p_in_non, key="slider_in_non")
p_put_stock = st.sidebar.slider("Putaway Stock (Max 2)", 0, 2, st.session_state.p_put_stock, key="slider_put_stock") 
p_put_non = st.sidebar.slider("Putaway Non-Stock", 0, 5, st.session_state.p_put_non, key="slider_put_non")

st.sidebar.subheader("🛒 Produktion (Plock & Pack)")
p_pick_stock = st.sidebar.slider("Plock Stock", 0, 25, st.session_state.p_pick_stock, key="slider_pick_stock")
p_pick_non = st.sidebar.slider("Plock Non-Stock", 0, 15, st.session_state.p_pick_non, key="slider_pick_non")
p_pack = st.sidebar.slider("Packstationer (Packare)", 0, 25, st.session_state.p_pack, key="slider_pack")

# Synka minnet med skärmen
st.session_state.p_pick_stock = p_pick_stock
st.session_state.p_pick_non = p_pick_non
st.session_state.p_pack = p_pack
st.session_state.p_in_stock = p_in_stock
st.session_state.p_in_non = p_in_non
st.session_state.p_put_stock = p_put_stock
st.session_state.p_put_non = p_put_non

total_staff = p_in_stock + p_in_non + p_put_stock + p_put_non + p_pick_stock + p_pick_non + p_pack
st.sidebar.info(f"Totalt fördelad personal: {total_staff} av 30 personer")

# =====================================================================
# 4. FASTSTÄLLDA EFFEKTIVITETSMÅL (Era exakta siffror!)
# =====================================================================
st.sidebar.markdown("---")
st.sidebar.header("⏱️ Fabriksinställda Prestandamål")

# Inbound & Inlagring (35 min per stockpall = ca 1.71 pallar/timme)
SPEED_INBOUND_STOCK = 1.71  
SPEED_INBOUND_NON_STOCK = 5.0  
SPEED_PUTAWAY_STOCK = 40
SPEED_PUTAWAY_NON_STOCK = 90  

# Grundhastigheten startar på 100 order i timmen per person
speed_pick = st.sidebar.slider("Plockhastighet (Order/h per person)", 40, 150, 100)

# Packhastighet: 110 paket i timmen per person
SPEED_PACK = 110  

# =====================================================================
# 5. DATAHANTERING OCH SIMULERING
# =====================================================================
if 'db_data' not in st.session_state:
    st.session_state.db_data = fetch_live_data()

if live_sim:
    # Plock och pack tuggar på utifrån era snabba plockmål (100 st/h)
    st.session_state.db_data["queue_pick_stock"] = max(0, st.session_state.db_data["queue_pick_stock"] + random.randint(30, 80) - int((p_pick_stock * speed_pick) / 1200))
    st.session_state.db_data["queue_pick_non_stock"] = max(0, st.session_state.db_data["queue_pick_non_stock"] + random.randint(10, 40) - int((p_pick_non * speed_pick) / 1200))
    
    total_plockat = int(((p_pick_stock + p_pick_non) * speed_pick) / 1200)
    total_packat = int((p_pack * SPEED_PACK) / 1200)
    st.session_state.db_data["queue_pack"] = max(0, st.session_state.db_data["queue_pack"] + total_plockat - total_packat)
    
    if random.random() > 0.8:
        st.session_state.db_data["inbound_stock"] = max(0, st.session_state.db_data["inbound_stock"] - int((p_in_stock * SPEED_INBOUND_STOCK) / 10))
        st.session_state.db_data["inbound_non_stock"] = max(0, st.session_state.db_data["inbound_non_stock"] - int((p_in_non * SPEED_INBOUND_NON_STOCK) / 10))

# =====================================================================
# 6. VISA AKTUELLT LÄGE PÅ SKÄRMEN
# =====================================================================
st.subheader("📊 Aktuell IMI-Status (Baserat på era volymer)")
st.markdown("#### 📥 Varumottagning & Inlagring")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Inbound STOCK (Pallar)", f"{st.session_state.db_data['inbound_stock']} st", help="Mål: 35 minuter per pall")
col2.metric("Inbound NON-STOCK (Gods)", f"{st.session_state.db_data['inbound_non_stock']} st")
col3.metric("Putaway STOCK (Rader)", f"{st.session_state.db_data['putaway_stock']} rader")
col4.metric("Putaway NON-STOCK (Rader)", f"{st.session_state.db_data['putaway_non_stock']} rader")

st.markdown("#### 🛒 Produktion")
col5, col6, col7 = st.columns(3)
col5.metric("Plockkö STOCK", f"{st.session_state.db_data['queue_pick_stock']} order", help="Mål: 100 order per timme/person")
col6.metric("Plockkö NON-STOCK", f"{st.session_state.db_data['queue_pick_non_stock']} order")
col7.metric("Väntar vid PACKSTATIONER", f"{st.session_state.db_data['queue_pack']} order", help="Mål: 110 paket per timme/person")
st.markdown("---")

# =====================================================================
# 7. EXAKTA TIDSKALKYLER (AI-HJÄRNAN)
# =====================================================================
time_in_stock = st.session_state.db_data['inbound_stock'] / max(p_in_stock * SPEED_INBOUND_STOCK, 0.1)
time_in_non = st.session_state.db_data['inbound_non_stock'] / max(p_in_non * SPEED_INBOUND_NON_STOCK, 0.1)
time_put_stock = st.session_state.db_data['putaway_stock'] / max(p_put_stock * SPEED_PUTAWAY_STOCK, 0.1)
time_put_non = st.session_state.db_data['putaway_non_stock'] / max(p_put_non * SPEED_PUTAWAY_NON_STOCK, 0.1)

time_pick_stock = st.session_state.db_data['queue_pick_stock'] / max(p_pick_stock * speed_pick, 0.1)
time_pick_non = st.session_state.db_data['queue_pick_non_stock'] / max(p_pick_non * speed_pick, 0.1)
time_pack = st.session_state.db_data['queue_pack'] / max(p_pack * SPEED_PACK, 0.1)

st.subheader("🧠 Systemdiagnos & AI-Rekommendationer")

def utför_åtgärd(flytta_från, flytta_till, antal=2):
    if st.session_state[flytta_från] >= antal:
        st.session_state[flytta_från] -= antal
        st.session_state[flytta_till] += antal
        st.toast(f"✅ Flyttade {antal} personer till {flytta_till}!", icon="🏃")

# TRÖGT FLÖDE / DANMARK-KÖRNING (Varnar om tempot ramlar långt under era 100 order/h)
if speed_pick < 75:
    st.error("🚨 **PRODUKTIONSVARNING: TRÖGT FLÖDE I GÅNGARNA**")
    st.markdown(f"**Orsaksanalys:** Plockhastigheten har fallit till tröga **{speed_pick} order/h** (Mål: 100). Detta beror på trängsel eller den månatliga **Danmark-körningen**.")
    st.info("💡 **Åtgärdsförslag:** Flytta **2 personer från Inbound Stock till Plock Stock** för att stötta upp.")
    if st.button("🏃 Verkställ personaljustering omedelbart", key="btn_slow"):
        utför_åtgärd('p_in_stock', 'p_pick_stock', 2)
        st.rerun()

# KROCK VID PACKBORDEN (Balanserad mot 100 plock/h och 110 pack/h)
elif time_pack > time_pick_stock and st.session_state.db_data['queue_pack'] > 600:
    st.error("🚨 **PRODUKTIONSSTOPP: FLASKHALS VID PACKBORDEN!**")
    st.markdown(f"**Analys:** Plockarna är extremt snabba (**100 order/h**). Packarna hinner inte med flödet trots sin höga kapacitet. Packkön växer.")
    st.info("💡 **Åtgärdsförslag:** Öka kapaciteten direkt. **Flytta 2 personer från Plock Stock till Packstationerna**.")
    if st.button("🏃 Verkställ personaljustering omedelbart", key="btn_pack"):
        utför_åtgärd('p_pick_stock', 'p_pack', 2)
        st.rerun()

# BRÅDSKANDE NON-STOCK
elif time_pick_non > 2.5:
    st.warning("⚠️ **AVVIKELSE: NON-STOCK-ORDER SLÄPAR EFTER!**")
    st.markdown(f"**Orsaksanalys:** Ledtiden för Non-Stock plock är uppe i {time_pick_non:.1f} timmar. Dessa brådskar till dagens bilar.")
    st.info("💡 **Åtgärdsförslag:** Flytta **1 person från Inbound Stock till Plock Non-Stock**.")
    if st.button("🏃 Verkställ personaljustering omedelbart", key="btn_non"):
        utför_åtgärd('p_in_stock', 'p_pick_non', 1)
        st.rerun()

        
# =====================================================================
# 8. PRESTATIONSTABELL
# =====================================================================
st.markdown("### 📊 Detaljerad tidsprognos för skiftet")
prognos_data = {
    "Processflöde": ["Inbound: Stock (35 min/pall)", "Inbound: Non-Stock (Snabb)", "Inlagring: Putaway Stock", "Inlagring: Putaway Non-Stock", "Plock: Stock (Mål: 100/h)", "Plock: Non-Stock", "Packning (Mål: 110/h)"],
    "Bemanning": [p_in_stock, p_in_non, p_put_stock, p_put_non, p_pick_stock, p_pick_non, p_pack],
    "Kapacitet / timme": [
        f"{round(p_in_stock*SPEED_INBOUND_STOCK, 1)} pallar", 
        f"{round(p_in_non*SPEED_INBOUND_NON_STOCK, 1)} pallar", 
        f"{p_put_stock*SPEED_PUTAWAY_STOCK} rader", 
        f"{p_put_non*SPEED_PUTAWAY_NON_STOCK} rader", 
        f"{p_pick_stock*speed_pick} order", 
        f"{p_pick_non*speed_pick} order", 
        f"{p_pack*SPEED_PACK} paket"
    ],
    "Tid till tomt (Timmar)": [
        round(time_in_stock, 1), 
        round(time_in_non, 1), 
        round(time_put_stock, 1), 
        round(time_put_non, 1), 
        round(time_pick_stock, 1), 
        round(time_pick_non, 1), 
        round(time_pack, 1)
    ]
}
st.table(prognos_data)

if live_sim:
    time.sleep(3)
    st.rerun()
