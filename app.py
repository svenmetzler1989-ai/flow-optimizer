import streamlit as st
import time
import requests
import random

# 1. DATABAS-ANSLUTNING
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
        if data and len(data) > 0: return data[0]
    except: pass
    return {
        "queue_pick_stock": 4500, "queue_pick_non_stock": 800, "queue_pack": 400,
        "inbound_stock": 6, "inbound_non_stock": 2, "putaway_stock": 120, "putaway_non_stock": 20
    }

# 2. HEMSIDANS INSTÄLLNINGAR
st.set_page_config(page_title="Specsavers Core Optimizer", layout="wide")
st.title("👓 Specsavers Flödes-Optimering (Live-Demo)")
st.caption("Intelligent beslutsstöd kopplat i realtid mot din Supabase-databas")
st.markdown("---")

# 3. SIDOPANEL: DEMOKONTROLLER
st.sidebar.header("🕹️ Demo-kontroller")
live_sim = st.sidebar.toggle("▶️ Starta Live-Simulering", value=False)

# Kom ihåg föregående personalfördelning i Streamlits minne
if 'p_pick_stock' not in st.session_state: st.session_state.p_pick_stock = 14
if 'p_pick_non' not in st.session_state: st.session_state.p_pick_non = 3
if 'p_pack' not in st.session_state: st.session_state.p_pack = 6
if 'p_in_stock' not in st.session_state: st.session_state.p_in_stock = 3
if 'p_in_non' not in st.session_state: st.session_state.p_in_non = 1
if 'p_put_stock' not in st.session_state: st.session_state.p_put_stock = 2
if 'p_put_non' not in st.session_state: st.session_state.p_put_non = 1

st.sidebar.markdown("---")
st.sidebar.header("👥 Aktiv Bemanning (Skift)")

# Använd session_state för att reglagen ska kunna ändras automatiskt av knapparna!
p_in_stock = st.sidebar.slider("Inbound Stock", 0, 10, st.session_state.p_in_stock, key="slider_in_stock")
p_in_non = st.sidebar.slider("Inbound Non-Stock", 0, 5, st.session_state.p_in_non, key="slider_in_non")
p_put_stock = st.sidebar.slider("Putaway Stock (Max 2)", 0, 2, st.session_state.p_put_stock, key="slider_put_stock") 
p_put_non = st.sidebar.slider("Putaway Non-Stock", 0, 5, st.session_state.p_put_non, key="slider_put_non")

st.sidebar.subheader("🛒 Produktion (Plock & Pack)")
p_pick_stock = st.sidebar.slider("Plock Stock", 0, 25, st.session_state.p_pick_stock, key="slider_pick_stock")
p_pick_non = st.sidebar.slider("Plock Non-Stock", 0, 15, st.session_state.p_pick_non, key="slider_pick_non")
p_pack = st.sidebar.slider("Packstationer (Packare)", 0, 25, st.session_state.p_pack, key="slider_pack")

# Spara valet tillbaka till minnet direkt när man drar i reglaget
st.session_state.p_pick_stock = p_pick_stock
st.session_state.p_pick_non = p_pick_non
st.session_state.p_pack = p_pack
st.session_state.p_in_stock = p_in_stock
st.session_state.p_in_non = p_in_non
st.session_state.p_put_stock = p_put_stock
st.session_state.p_put_non = p_put_non

total_staff = p_in_stock + p_in_non + p_put_stock + p_put_non + p_pick_stock + p_pick_non + p_pack
st.sidebar.info(f"Totalt fördelad personal: {total_staff} av 30 personer")

st.sidebar.markdown("---")
st.sidebar.header("⏱️ Prestationstakt (Performance)")
speed_pick = st.sidebar.slider("Plockhastighet (Order/h)", 15, 60, 45)
speed_pack = st.sidebar.slider("Packhastighet (Order/h)", 20, 80, 55)

# 4. DATAHANTERING
if 'db_data' not in st.session_state:
    st.session_state.db_data = fetch_live_data()

if live_sim:
    # Simulera inkommande flöde minus vad din inställda personal faktiskt hinner med
    st.session_state.db_data["queue_pick_stock"] = max(0, st.session_state.db_data["queue_pick_stock"] + random.randint(15, 40) - int((p_pick_stock * speed_pick) / 1200))
    st.session_state.db_data["queue_pick_non_stock"] = max(0, st.session_state.db_data["queue_pick_non_stock"] + random.randint(5, 20) - int((p_pick_non * speed_pick) / 1200))
    
    total_plockat = int(((p_pick_stock + p_pick_non) * speed_pick) / 1200)
    total_packat = int((p_pack * speed_pack) / 1200)
    st.session_state.db_data["queue_pack"] = max(0, st.session_state.db_data["queue_pack"] + total_plockat - total_packat)

# 5. VISA NYCKELTAL
st.subheader("📊 Aktuell IMI-Status (Baserat på era volymer)")
st.markdown("#### 📥 Varumottagning & Inlagring")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Inbound STOCK (Pallar)", f"{st.session_state.db_data['inbound_stock']} st")
col2.metric("Inbound NON-STOCK (Gods)", f"{st.session_state.db_data['inbound_non_stock']} st")
col3.metric("Putaway STOCK (Rader)", f"{st.session_state.db_data['putaway_stock']} rader")
col4.metric("Putaway NON-STOCK (Rader)", f"{st.session_state.db_data['putaway_non_stock']} rader")

st.markdown("#### 🛒 Produktion")
col5, col6, col7 = st.columns(3)
col5.metric("Plockkö STOCK", f"{st.session_state.db_data['queue_pick_stock']} order")
col6.metric("Plockkö NON-STOCK", f"{st.session_state.db_data['queue_pick_non_stock']} order")
col7.metric("Väntar vid PACKSTATIONER", f"{st.session_state.db_data['queue_pack']} order")
st.markdown("---")

# 6. TIDSKALKYLER OCH BESLUTSSTÖD
time_pick_stock = st.session_state.db_data['queue_pick_stock'] / max(p_pick_stock * speed_pick, 1)
time_pick_non = st.session_state.db_data['queue_pick_non_stock'] / max(p_pick_non * speed_pick, 1)
time_pack = st.session_state.db_data['queue_pack'] / max(p_pack * speed_pack, 1)

st.subheader("🧠 Systemdiagnos & AI-Rekommendationer")

# Skapa funktioner för knapparna som ändrar personalstyrkan live!
def utför_åtgärd(flytta_från, flytta_till, antal=2):
    if st.session_state[flytta_från] >= antal:
        st.session_state[flytta_från] -= antal
        st.session_state[flytta_till] += antal
        st.toast(f"✅ Flyttade {antal} personer till {flytta_till}!", icon="🏃")

# LOGIKEN KÄNNER AV OM DU HAR VERKSTÄLLT ÅTGÄRDEN
if speed_pick < 35:
    st.error("🚨 **PRODUKTIONSVARNING: TRÖGT FLÖDE (DANMARK-KÖRNING)**")
    st.info("💡 **Åtgärdsförslag:** Flytta **2 personer från Inbound Stock till Plock Stock**.")
    if st.button("🏃 Verkställ personaljustering omedelbart", key="btn_slow"):
        utför_åtgärd('p_in_stock', 'p_pick_stock', 2)
        st.rerun()

elif time_pack > time_pick_stock and st.session_state.db_data['queue_pack'] > 600:
    st.error("🚨 **PRODUKTIONSSTOPP: FLASKHALS VID PACKBORDEN!**")
    st.info("💡 **Åtgärdsförslag:** Flytta **2 personer från Plock Stock till Packstationerna** direkt.")
    if st.button("🏃 Verkställ personaljustering omedelbart", key="btn_pack"):
        utför_åtgärd('p_pick_stock', 'p_pack', 2)
        st.rerun()

elif time_pick_non > 2.5:
    st.warning("⚠️ **AVVIKELSE: NON-STOCK-ORDER SLÄPAR EFTER!**")
    st.info("💡 **Åtgärdsförslag:** Flytta **1 person från Inbound Stock till Plock Non-Stock**.")
    if st.button("🏃 Verkställ personaljustering omedelbart", key="btn_non"):
        utför_åtgärd('p_in_stock', 'p_pick_non', 1)
        st.rerun()

else:
    st.success("✅ **FLÖDET ÄR OPTIMALT BALANSERAT**")
    st.write("Dina senaste justeringar betar av köerna i perfekt takt just nu.")

# 7. PROGNOS-TABELL
st.markdown("### 📊 Detaljerad tidsprognos för skiftet")
prognos_data = {
    "Processflöde": ["Plock: Stock", "Plock: Non-Stock", "Packning (Slutsteg)", "Inlagring: Stock", "Inlagring: Non-Stock"],
    "Bemanning (Antal)": [p_pick_stock, p_pick_non, p_pack, p_put_stock, p_put_non],
    "Kapacitet / timme": [p_pick_stock*speed_pick, p_pick_non*speed_pick, p_pack*speed_pack, p_put_stock*40, p_put_non*40],
    "Tid till tomt (Timmar)": [round(time_pick_stock, 1), round(time_pick_non, 1), round(time_pack, 1), round(st.session_state.db_data['putaway_stock']/max(p_put_stock*40,1),1), round(st.session_state.db_data['putaway_non_stock']/max(p_put_non*40,1),1)]
}
st.table(prognos_data)

if live_sim:
    time.sleep(3)
    st.rerun()
