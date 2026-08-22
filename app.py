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
    """Hämtar sekundfärsk data från din nyss uppdaterade Supabase-tabell"""
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    url = f"{SUPABASE_URL}/rest/v1/imi_live_data?select=*"
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        if data and len(data) > 0: 
            return data[0] # Hämtar den raden du nyss uppdaterade
    except: 
        pass
    
    # Högkvalitativ reserv (Fallback) med dina exakta siffror om uppkopplingen bryts
    return {
        "queue_pick_stock": 4500, "queue_pick_non_stock": 800, "queue_pack": 400,
        "inbound_stock": 6, "inbound_non_stock": 2, "putaway_stock": 120, "putaway_non_stock": 20
    }

# =====================================================================
# 2. HEMSIDANS GRUNDINSTÄLLNINGAR & FORMAT
# =====================================================================
st.set_page_config(page_title="Specsavers Core Optimizer", layout="wide")
st.title("👓 Specsavers Flödes-Optimering (Live-Demo)")
st.caption("Intelligent beslutsstöd kopplat i realtid mot din Supabase-databas")
st.markdown("---")

# =====================================================================
# 3. SIDOPANEL: BEMANNING PER SPECIFIK ROLL (Max 30 personer)
# =====================================================================
st.sidebar.header("🕹️ Demo-kontroller")
live_sim = st.sidebar.toggle("▶️ Starta Live-Simulering", value=False)
if live_sim:
    st.sidebar.caption("🔄 Sidan uppdateras och hämtar ny data var 3:e sekund...")

st.sidebar.markdown("---")
st.sidebar.header("👥 Aktiv Bemanning (Skift)")

st.sidebar.subheader("📥 Inbound & Inlagring")
p_in_stock = st.sidebar.slider("Inbound Stock", 0, 10, 3)
p_in_non = st.sidebar.slider("Inbound Non-Stock", 0, 5, 1)
# HÄR ÄR DITT BESLUT: Max 2 personer på Putaway Stock eftersom 20-30 pall/vecka räcker gott och väl
p_put_stock = st.sidebar.slider("Putaway Stock (Max 2 räcker)", 0, 2, 2) 
p_put_non = st.sidebar.slider("Putaway Non-Stock", 0, 5, 1)

st.sidebar.subheader("🛒 Produktion (Plock & Pack)")
p_pick_stock = st.sidebar.slider("Plock Stock", 0, 25, 14)
p_pick_non = st.sidebar.slider("Plock Non-Stock", 0, 15, 3)
p_pack = st.sidebar.slider("Packstationer (Packare)", 0, 25, 6)

# Räkna ut totalen live
total_staff = p_in_stock + p_in_non + p_put_stock + p_put_non + p_pick_stock + p_pick_non + p_pack
st.sidebar.info(f"Totalt fördelad personal: {total_staff} av 30 personer")

# Prestationstakt (Går att justera live på mötet för att simulera trögt flöde)
st.sidebar.markdown("---")
st.sidebar.header("⏱️ Prestationstakt (Performance)")
speed_pick = st.sidebar.slider("Plockhastighet (Order/h per person)", 15, 60, 45)
speed_pack = st.sidebar.slider("Packhastighet (Order/h per person)", 20, 80, 55)

# =====================================================================
# 4. DATAHANTERING (Hämta från Supabase eller kör simulering)
# =====================================================================
if 'db_data' not in st.session_state:
    st.session_state.db_data = fetch_live_data()

# Om du slår på live-simuleringen tickar siffrorna realistiskt utifrån din bemanning
if live_sim:
    # Nya order trillar in på tvåskiftet (mål 6000-10000 om dagen)
    st.session_state.db_data["queue_pick_stock"] += random.randint(15, 45) - int((p_pick_stock * speed_pick) / 1200)
    st.session_state.db_data["queue_pick_non_stock"] += random.randint(5, 20) - int((p_pick_non * speed_pick) / 1200)
    
    # Det som plockas skickas vidare till pack-kön!
    total_plockat = int(((p_pick_stock + p_pick_non) * speed_pick) / 1200)
    total_packat = int((p_pack * speed_pack) / 1200)
    st.session_state.db_data["queue_pack"] += total_plockat - total_packat
    
    # Inbound rör sig långsamt eftersom det bara är 20-30 pallar i veckan
    if random.random() > 0.8:
        st.session_state.db_data["inbound_stock"] = max(0, st.session_state.db_data["inbound_stock"] + random.choice([-1, 0, 1]))

# =====================================================================
# 5. VISA DIN NYA VERKLIGHETSTROGNA STATUS PÅ SKÄRMEN
# =====================================================================
st.subheader("📊 Aktuell IMI-Status (Baserat på era volymer)")

# Rad 1: Inbound & Putaway
st.markdown("#### 📥 Varumottagning & Inlagring")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Inbound STOCK (Pallar på bryggan)", f"{st.session_state.db_data['inbound_stock']} st")
col2.metric("Inbound NON-STOCK (Enstaka gods)", f"{st.session_state.db_data['inbound_non_stock']} st")
col3.metric("Putaway STOCK (Rader kvar på golv)", f"{st.session_state.db_data['putaway_stock']} rader")
col4.metric("Putaway NON-STOCK (Rader kvar)", f"{st.session_state.db_data['putaway_non_stock']} rader")

# Rad 2: Plock & Pack
st.markdown("#### 🛒 Produktion (6 000 - 10 000 Orderbörda)")
col5, col6, col7 = st.columns(3)
col5.metric("Plockkö STOCK", f"{st.session_state.db_data['queue_pick_stock']} order")
col6.metric("Plockkö NON-STOCK", f"{st.session_state.db_data['queue_pick_non_stock']} order")
col7.metric("Väntar vid PACKSTATIONER", f"{st.session_state.db_data['queue_pack']} order")

st.markdown("---")

# =====================================================================
# 6. TIDSKALKYLER OCH DIAGNOSMOTOR (AI-HJÄRNAN)
# =====================================================================
time_pick_stock = st.session_state.db_data['queue_pick_stock'] / max(p_pick_stock * speed_pick, 1)
time_pick_non = st.session_state.db_data['queue_pick_non_stock'] / max(p_pick_non * speed_pick, 1)
time_pack = st.session_state.db_data['queue_pack'] / max(p_pack * speed_pack, 1)

st.subheader("🧠 Systemdiagnos & AI-Rekommendationer")

# DETEKTERA OM PRODUKTIONEN ÄR LÅNGSAM OCH VARFÖR
if speed_pick < 35:
    st.error("🚨 **PRODUKTIONSVARNING: TRÖGT FLÖDE I GÅNGARNA!**")
    st.markdown(f"**Orsaksanalys:** Plockhastigheten har sjunkit till tröga **{speed_pick} order/h per person**. Detta indikerar trängsel på plockytan eller att ni just nu kör den månatliga **Danmark-leveransen** (tyngre orderstruktur).")
    st.info(f"💡 **Omedelbar åtgärd:** Eftersom inlagringen flyter på bra med dina {p_put_stock} personer, bör du flytta **2 personer från Inbound Stock till Plock Stock** för att hålla tidsplanen.")

# DETEKTERA PROPP VID PACKNINGEN
elif time_pack > time_pick_stock and st.session_state.db_data['queue_pack'] > 600:
    st.error("🚨 **PRODUKTIONSSTOPP: FLASKHALS VID PACKBORDEN!**")
    st.markdown(f"**Orsaksanalys:** Plockarna levererar snabbare än packstationerna hinner försegla kartongerna. Det står **{st.session_state.db_data['queue_pack']} order** på vagnarna och blockerar golvet.")
    st.info("💡 **Omedelbar åtgärd:** Sätt tillfälligt stopp för plockare. **Flytta 2 personer från Plock Stock till Packstationerna** direkt.")

# DETEKTERA OM NON-STOCK LIGGER OCH VÄNTAR FÖR LÄNGE
elif time_pick_non > 2.5:
    st.warning("⚠️ **AVVIKELSE: NON-STOCK-ORDER SLÄPAR EFTER!**")
    st.markdown(f"**Orsaksanalys:** Direktordrarna (Non-Stock) har en beräknad ledtid på {time_pick_non:.1f} timmar. Eftersom dessa ska med dagens lastbilar till Norge/Finland/NL brådskar det.")
    st.info("💡 **Omedelbar åtgärd:** Förstärk direktflödet. **Flytta 1 person från Inbound Stock till Plock Non-Stock**.")

else:
    st.success("✅ **FLÖDET ÄR OPTIMALT BALANSERAT**")
    st.write("Produktionstakten är hög, inlagringen är stabil på 2 personer, och alla avdelningar jobbar i perfekt symetri.")

# =====================================================================
# 7. TIDSPROGNOS-TABELL
# =====================================================================
st.markdown("### 📊 Detaljerad tidsprognos för skiftet")
prognos_data = {
    "Processflöde": ["Plock: Stock", "Plock: Non-Stock", "Packning (Slutsteg)", "Inlagring: Stock", "Inlagring: Non-Stock"],
    "Bemanning (Antal)": [p_pick_stock, p_pick_non, p_pack, p_put_stock, p_put_non],
    "Kapacitet / timme": [p_pick_stock*speed_pick, p_pick_non*speed_pick, p_pack*speed_pack, p_put_stock*40, p_put_non*40],
    "Tid till tomt (Timmar)": [round(time_pick_stock, 1), round(time_pick_non, 1), round(time_pack, 1), round(st.session_state.db_data['putaway_stock']/max(p_put_stock*40,1),1), round(st.session_state.db_data['putaway_non_stock']/max(p_put_non*40,1),1)]
}
st.table(prognos_data)

# Automatisk uppdatering (loop)
if live_sim:
    time.sleep(3)
    st.rerun()
