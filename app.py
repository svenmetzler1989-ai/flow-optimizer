import streamlit as st
import pandas as pd
import numpy as np
import random
import time

# =====================================================================
# 1. KONFIGURATION OCH DESIGN (Specsavers Tema - SÄKRAD FÖR NYA STREAMLIT)
# =====================================================================
st.set_page_config(
    page_title="Specsavers WMS Flow Optimizer",
    page_icon="🟩",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 🛠️ BUGGFIX: Använder st.html istället för st.markdown med unsafe_html
st.html("""
    <style>
    .reportview-container { background: #f0f2f6; }
    .sidebar .sidebar-content { background: #ffffff; }
    div.stButton > button:first-child {
        background-color: #006643;
        color: white;
        border-radius: 6px;
    }
    </style>
""")

st.title("🟩 Specsavers WMS Flow Optimizer")
st.subheader("AI-Driven Driftstyrning & Resursallokering i Real-Time")


# =====================================================================
# 2. STARTPARAMETRAR OCH VOLYMER (INKLUSIVE NEDERLÄNDERNA)
# =====================================================================
START_INBOUND_STOCK = 6       
START_INBOUND_NON = 1         
START_PUTAWAY_STOCK = 120     
START_PUTAWAY_NON = 40        
START_PICK_STOCK = 12500      # Något höjd för att räcka till det förlängda kvällsskiftet
START_PICK_NON = 750          
START_PACK = 450              

if "total_packat_historik" not in st.session_state:
    st.session_state.total_packat_historik = 0
if "inventering_rader_klara" not in st.session_state:
    st.session_state.inventering_rader_klara = 0

@st.cache_data
def fetch_live_data():
    return {
        "inbound_stock": START_INBOUND_STOCK,
        "inbound_non_stock": START_INBOUND_NON,
        "putaway_stock": START_PUTAWAY_STOCK,
        "putaway_non_stock": START_PUTAWAY_NON,
        "queue_pick_stock": START_PICK_STOCK,       
        "queue_pick_non_stock": START_PICK_NON,
        "queue_pack": START_PACK
    }


# =====================================================================
# 3. MEDARBETARDATABAS (⚡ JUSTERAT PLOCKTEMPO TILL 100 RADER/H)
# =====================================================================
if 'medarbetare_info' not in st.session_state:
    medarbetare_info = {
        "EMP-101": {"namn": "Anna", "pick_speed": 102, "pack_speed": 95, "putaway_speed": 85, "start_zon": "Plock Stock"},
        "EMP-102": {"namn": "Per", "pick_speed": 98, "pack_speed": 125, "putaway_speed": 75, "start_zon": "Packning"},
        "EMP-103": {"namn": "Lars", "pick_speed": 100, "pack_speed": 110, "putaway_speed": 95, "start_zon": "Putaway Stock"},
        "EMP-104": {"namn": "Elin", "pick_speed": 101, "pack_speed": 100, "putaway_speed": 80, "start_zon": "Plock Non-Stock"},
        "EMP-105": {"namn": "Mikael", "pick_speed": 99, "pack_speed": 105, "putaway_speed": 70, "start_zon": "Inbound Stock"},
    }
    # Skapa resterande 10 medarbetare med ett kontrollerat plocktempo runt 100 rader/h
    start_zoner_pool = ["Plock Stock", "Packning", "Plock Stock", "Putaway Stock", "Plock Non-Stock"]
    for i in range(106, 116):
        emp_id = f"EMP-{i}"
        medarbetare_info[emp_id] = {
            "namn": f"Medarbetare {i}",
            "pick_speed": random.randint(97, 103), # Justerat till ca 100 rader i timmen
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
# 4. KONTROLLPANEL & SIDOPANEL (Layout och tidsräknare)
# =====================================================================
st.sidebar.image("https://wikimedia.org", width=180)
st.sidebar.markdown("## ⚙️ Skiftsinställningar")

if 'sim_minutes' not in st.session_state:
    st.session_state.sim_minutes = 360 # Startar skiftet kl 06:00

# Räkna ut aktuell klocktid baserat på simulerade minuter
timmar = int(st.session_state.sim_minutes // 60)
minuter = int(st.session_state.sim_minutes % 60)
klocktid = f"{timmar:02d}:{minuter:02d}"

st.sidebar.markdown(f"### 🕒 Produktionsklocka: `{klocktid}`")

# Kontroller för att starta, pausa och återställa
live_sim = st.sidebar.toggle("▶️ Aktivera Live-Simulering", value=False)
live_sim_speed = 1.0 

if st.sidebar.button("🔄 Återställ Skiftet till 06:00"):
    st.session_state.sim_minutes = 360
    st.session_state.morgondagens_pack = 0
    st.session_state.retur_notis = False
    st.session_state.db_data = fetch_live_data()
    st.session_state.placering = {emp_id: info["start_zon"] for emp_id, info in st.session_state.medarbetare_info.items()}
    st.rerun()


# =====================================================================
# 5. REALTIDSBERÄKNING AV GRUPPKAPACITET FÖR ALLA STATIONER
# =====================================================================
p_in_stock = list(st.session_state.placering.values()).count("Inbound Stock")
p_in_non = list(st.session_state.placering.values()).count("Inbound Non-Stock")
p_put_stock = list(st.session_state.placering.values()).count("Putaway Stock")
p_put_non = list(st.session_state.placering.values()).count("Putaway Non-Stock")
p_pick_stock = list(st.session_state.placering.values()).count("Plock Stock")
p_pick_non = list(st.session_state.placering.values()).count("Plock Non-Stock")
p_pack = list(st.session_state.placering.values()).count("Packning")
p_inventering = list(st.session_state.placering.values()).count("Inventering")

total_in_stock_speed_h = p_in_stock * 1.7
total_in_non_speed_h = p_in_non * 1.7
total_put_stock_speed_h = sum([st.session_state.medarbetare_info[eid]["putaway_speed"] for eid, loc in st.session_state.placering.items() if loc == "Putaway Stock"])
total_put_non_speed_h = sum([st.session_state.medarbetare_info[eid]["putaway_speed"] for eid, loc in st.session_state.placering.items() if loc == "Putaway Non-Stock"])
total_pick_stock_speed_h = sum([st.session_state.medarbetare_info[eid]["pick_speed"] for eid, loc in st.session_state.placering.items() if loc == "Plock Stock"])
total_pick_non_speed_h = sum([st.session_state.medarbetare_info[eid]["pick_speed"] for eid, loc in st.session_state.placering.items() if loc == "Plock Non-Stock"])
total_pack_speed_h = p_pack * 110.0

step_in_stock = total_in_stock_speed_h / 6.0
step_in_non = total_in_non_speed_h / 6.0
step_put_stock = total_put_stock_speed_h / 6.0
step_put_non = total_put_non_speed_h / 6.0
step_pick_stock = total_pick_stock_speed_h / 6.0
step_pick_non = total_pick_non_speed_h / 6.0
step_pack = total_pack_speed_h / 6.0

st.sidebar.markdown("---")
st.sidebar.markdown("### 📊 Aktuell Bemanningsstatus")
st.sidebar.markdown(f"📥 **Inbound (ST/NON):** `{p_in_stock + p_in_non} pers` (Låst 1+1)")
st.sidebar.markdown(f"🛒 **Kärna (Plock/Pack):** `{p_pick_stock + p_pack} pers` (50/50 Balans)")
st.sidebar.markdown(f"🔍 **Inventering:** `{p_inventering} pers` (Övertalig stöttning)")


# =====================================================================
# 6. SIMULERINGSLOGIK (RASTER, INVENTERING & DRIFT TILL 14:15 / 22:45)
# =====================================================================
if "just_clicked" not in st.session_state:
    st.session_state.just_clicked = False
if "morgondagens_pack" not in st.session_state:
    st.session_state.morgondagens_pack = 0
if "retur_notis" not in st.session_state:
    st.session_state.retur_notis = False
if "retur_start_tid" not in st.session_state:
    st.session_state.retur_start_tid = 0
if "totalt_inkommande_non" not in st.session_state:
    st.session_state.totalt_inkommande_non = 1

# Förlängd simulering till kl 23:30 (1410 minuter) för att se kvällsskiftets efterarbete
if live_sim and st.session_state.sim_minutes < 1410:
    if st.session_state.just_clicked:
        st.session_state.just_clicked = False  
    else:
        st.session_state.sim_minutes += 10  
    
    m = st.session_state.sim_minutes
    
    # ⏱️ KONTROLLERA OM DET ÄR RAST JUST NU (Produktionen fryser under dessa tider)
    ar_det_rast = (
        (480 <= m < 495) or    # Dag: Frukost 08:00 - 08:15
        (660 <= m < 690) or    # Dag: Lunch 11:00 - 11:30
        (780 <= m < 795) or    # Dag: Fika 13:00 - 13:15
        (990 <= m < 1005) or   # Kväll: Rast 16:30 - 16:45
        (1170 <= m < 1200) or  # Kväll: Rast 19:30 - 20:00
        (1290 <= m < 1305)     # Kväll: Rast 21:30 - 21:45
    )

    if st.session_state.retur_notis and m - st.session_state.retur_start_tid >= 120:
        st.session_state.retur_notis = False

    # --- DYNAMISK AI-AUTOPILOT: SMART RESURSREGLERING ---
    current_placering = st.session_state.placering
    all_emps = list(st.session_state.medarbetare_info.keys())
    
    def get_count(zon): return list(st.session_state.placering.values()).count(zon)
    
    rörlig_personal_pool = []
    
    for emp in all_emps:
        # 🚨 EFTER KL 22:45 (Kvällsskiftet är slut, flytta ALLA till Sortering och Putaway)
        if m >= 1365:
            st.session_state.placering[emp] = "Putaway Stock" if get_count("Putaway Stock") < 8 else "Sortering"
            continue

        # A. 📥 LÅST DRIFT FÖR INBOUND & PUTAWAY KEDJORNA (1 person per flöde)
        if st.session_state.db_data["inbound_stock"] > 0 and get_count("Inbound Stock") < 1:
            st.session_state.placering[emp] = "Inbound Stock"
            continue
        elif st.session_state.db_data["inbound_stock"] == 0 and st.session_state.db_data["putaway_stock"] > 0 and get_count("Putaway Stock") < 1:
            st.session_state.placering[emp] = "Putaway Stock"
            continue

        if st.session_state.db_data["inbound_non_stock"] > 0 and get_count("Inbound Non-Stock") < 1:
            st.session_state.placering[emp] = "Inbound Non-Stock"
            continue
        elif st.session_state.db_data["inbound_non_stock"] == 0 and st.session_state.db_data["putaway_non_stock"] > 0 and get_count("Putaway Non-Stock") < 1:
            st.session_state.placering[emp] = "Putaway Non-Stock"
            continue

        # B. 📦 LÖPANDE SORTERING & PALLISERING (Alltid 2-3 personer)
        mål_sorterare = 3 if st.session_state.db_data["queue_pack"] > 300 else 2
        if get_count("Sortering") < mål_sorterare:
            st.session_state.placering[emp] = "Sortering"
            continue

        # C. 🛒 PLOCK NON-STOCK (Max 2 personer vid behov)
        elif st.session_state.db_data["queue_pick_non_stock"] > 0 and get_count("Plock Non-Stock") < 2:
            st.session_state.placering[emp] = "Plock Non-Stock"
            continue
            
        # D. 🚛 UTLASTNING INFÖR TRANSPORTAVGÅNG (Kl 13:30 - 14:30)
        elif 810 <= m < 870:
            if get_count("Utlastning") < 2:
                st.session_state.placering[emp] = "Utlastning"
                continue
            elif get_count("Transport") < 1:
                st.session_state.placering[emp] = "Transport"
                continue

        # E. 🛑 RETUR-REGLERING (Max 1 person vid aktiv avvikelse)
        elif st.session_state.retur_notis and get_count("Returer") < 1:
            st.session_state.placering[emp] = "Returer"
            continue

        # Återströmning till rörliga poolen
        if current_placering[emp] in ["Inbound Stock", "Inbound Non-Stock", "Putaway Stock", "Putaway Non-Stock", "Plock Non-Stock", "Returer", "Transport", "Utlastning", "Sortering", "Inventering"]:
            st.session_state.placering[emp] = "Plock Stock"

        rörlig_personal_pool.append(emp)

    # ⚖️ REGLERINGSMOTORN (Styr basen 50/50 och flyttar överblivna till Inventering)
    total_kärna = len(rörlig_personal_pool)
    if total_kärna > 0 and m < 1365:
        # Räkna ut hur många packare som behövs (Max 11 st pga fysiska bord)
        if st.session_state.db_data["queue_pack"] > 250:
            mål_packare = min(11, int(total_kärna * 0.70))
        elif st.session_state.db_data["queue_pack"] < 50:
            mål_packare = max(1, int(total_kärna * 0.20))
        else:
            mål_packare = min(11, int(total_kärna / 2))

        # Tilldela roller och skicka de som blir över (över max 11 packbord) till Inventering
        for rörlig_idx, emp_id in enumerate(rörlig_personal_pool):
            if rörlig_idx < mål_packare:
                st.session_state.placering[emp_id] = "Packning"
            elif rörlig_idx < 11:
                st.session_state.placering[emp_id] = "Plock Stock"
            else:
                # 🛠️ NY MODUL: Skicka övertalig personal till Inventering så ingen står still!
                st.session_state.placering[emp_id] = "Inventering"

    # --- BERÄKNA PRODUKTION LIVE UTIFRÅN TEMPO OCH RASTER ---
    # Om det är rast produceras absolut ingenting under dessa 10 minuter
    if ar_det_rast:
        plockat_stock = 0
        plockat_non = 0
        packat = 0
        inlagrat_stock = 0
        inlagrat_non = 0
        inventerat_rader = 0
    else:
        # Garantera hög produktivitet fram till 14:15 (dag) och till 22:45 (kväll)
        if m <= 855 or (960 <= m < 1365):
            hastighets_boost = 1.60
        else:
            hastighets_boost = 0.50 # Avstannande efter skiftets produktiva slut
            
        plockat_stock = int(min(step_pick_stock * hastighets_boost, st.session_state.db_data["queue_pick_stock"]))
        plockat_non = int(min(step_pick_non, st.session_state.db_data["queue_pick_non_stock"]))
        
        packat = int(min(step_pack * hastighets_boost, st.session_state.db_data["queue_pack"] + plockat_stock + plockat_non))
        inlagrat_stock = int(min(step_put_stock * 4, st.session_state.db_data["putaway_stock"]))
        inlagrat_non = int(min(step_put_non * 4, st.session_state.db_data["putaway_non_stock"]))
        inventerat_rader = p_inventering * 4 # Varje person inventerar 4 rader per 10 minuter

    # Verkställ produktionen i köerna
    st.session_state.db_data["queue_pick_stock"] = max(0, st.session_state.db_data["queue_pick_stock"] - plockat_stock)
    st.session_state.db_data["queue_pick_non_stock"] = max(0, st.session_state.db_data["queue_pick_non_stock"] - plockat_non)
    
    total_nyplockat = plockat_stock + plockat_non
    st.session_state.db_data["queue_pack"] = max(0, st.session_state.db_data["queue_pack"] + total_nyplockat - packat)
    
    # Spara historik över totalt packade paket under dagen
    st.session_state.total_packat_historik += packat
    st.session_state.inventering_rader_klara += inventerat_rader

    st.session_state.db_data["putaway_stock"] = max(0, st.session_state.db_data["putaway_stock"] - inlagrat_stock)
    st.session_state.db_data["putaway_non_stock"] = max(0, st.session_state.db_data["putaway_non_stock"] - inlagrat_non)

    # Släpp på totalt 2-3 Non-Stock pallar under dagen
    if m in [420, 720, 1020] and st.session_state.totalt_inkommande_non < 3:
        st.session_state.db_data["inbound_non_stock"] += 1
        st.session_state.totalt_inkommande_non += 1
    
    if p_in_stock > 0 and st.session_state.db_data["inbound_stock"] > 0:
        st.session_state.db_data["inbound_stock"] = max(0, st.session_state.db_data["inbound_stock"] - 1)
        st.session_state.db_data["putaway_stock"] += random.randint(14, 24)

    if p_in_non > 0 and st.session_state.db_data["inbound_non_stock"] > 0:
        st.session_state.db_data["inbound_non_stock"] = max(0, st.session_state.db_data["inbound_non_stock"] - 1)
        st.session_state.db_data["putaway_non_stock"] += random.randint(10, 15)

    if random.random() > 0.98 and not st.session_state.retur_notis and m < 1100:
        st.session_state.retur_notis = True
        st.session_state.retur_start_tid = m


# =====================================================================
# 6B. AI FLÖDESASSISTENT (KONTROLLPANEL FÖR EVENTUELLA AVVIKELSER)
# =====================================================================
st.markdown("### 🚦 AI Flödesassistent (Autopilot Aktiv)")

if st.session_state.retur_notis:
    st.warning("⚠️ **AVVIKELSEVARNING: KUNDRETUR REGISTRERAD (1-2%)**")
    st.markdown("En ny retursändning blockerar terminalytan. Autopiloten kommer att styra om nästa lediga kapacitet automatiskt.")
    if st.button("Rensa retur-notis manuellt"):
        st.session_state.retur_notis = False
        st.session_state.just_clicked = True
        st.rerun()

if st.session_state.sim_minutes > 870:
    st.info("🚛 **TRANSPORT STATUS:** Klockan har passerat 14:30. Dagens huvudbil har avgått. Godset slussas till morgondagens utlastning.")
else:
    st.success("🤖 **AUTOPILOT STATUS:** Övervakar flödesköerna live. Resurser omfördelas proaktivt på lagret.")

st.markdown("---")


# =====================================================================
# 7. VISUELL MÅLUPPFYLLNAD (Real-Time KPI)
# =====================================================================
def visa_status_graf(titel, nuvarande, start_varde):
    procent = min(1.0, max(0.0, 1.0 - (nuvarande / max(start_varde, 1))))
    st.markdown(f"**{titel}** — {int(procent*100)}%")
    st.progress(procent)

st.subheader("🎯 Visuell Måluppfyllnad (Real-Time KPI)")
col_g1, col_g2 = st.columns(2)
with col_g1:
    visa_status_graf("🛒 Kunduppdrag: Plock STOCK (Mål: 10 000 rader)", st.session_state.db_data["queue_pick_stock"], 10000)
    visa_status_graf("⚡ Kunduppdrag: Plock NON-STOCK", st.session_state.db_data["queue_pick_non_stock"], START_PICK_NON)
with col_g2:
    visa_status_graf("🏁 Slutsteg: Packning (Försegling)", st.session_state.db_data["queue_pack"], START_PACK)
    visa_status_graf("📥 Inlagring: Putaway STOCK (Kartonger)", st.session_state.db_data["putaway_stock"], START_PUTAWAY_STOCK)

st.markdown("---")


# =====================================================================
# 8. REALTIDSSTATUS (IMI Siffror från databasen)
# =====================================================================
st.subheader("📊 Aktuell IMI-Status (Köer just nu)")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Inbound STOCK (Pallar)", f"{st.session_state.db_data['inbound_stock']} st")
col2.metric("Putaway STOCK (Kartonger)", f"{st.session_state.db_data['putaway_stock']} st")
col3.metric("Plockkö STOCK (Rader)", f"{st.session_state.db_data['queue_pick_stock']} rader")
col4.metric("Väntar vid PACKSTATIONER", f"{st.session_state.db_data['queue_pack']} order")

col_n1, col_n2, col_n3 = st.columns(3)
col_n1.metric("Inbound NON-STOCK (Pallar)", f"{st.session_state.db_data['inbound_non_stock']} st")
col_n2.metric("Putaway NON-STOCK (Kartonger)", f"{st.session_state.db_data['putaway_non_stock']} st")
col_n3.metric("Plockkö NON-STOCK (Order)", f"{st.session_state.db_data['queue_pick_non_stock']} order")

st.markdown("---")


# =====================================================================
# 9. MEDARBETARSTATUS (Snygg, scannbar Kanban-layout för Chromebook)
# =====================================================================
with st.expander("👥 Se personalens placeringar (Styrs automatiskt av AI-Autopilot)", expanded=True):
    st.markdown("### 🏬 Aktuell resursfördelning på golvet")
    ROLLER_LIST = ["Inbound Stock", "Inbound Non-Stock", "Putaway Stock", "Putaway Non-Stock", "Plock Stock", "Plock Non-Stock", "Packning", "Sortering", "Utlastning", "Transport", "Returer"]
    
    matris_cols = st.columns(4)
    for idx, zon in enumerate(ROLLER_LIST):
        with matris_cols[idx % 4]:
            folk_i_zon = [st.session_state.medarbetare_info[eid]["namn"] for eid, loc in st.session_state.placering.items() if loc == zon]
            st.markdown(f"**📍 {zon}**")
            if folk_i_zon:
                namn_str = ", ".join(folk_i_zon)
                st.success(f"👥 {namn_str} ({len(folk_i_zon)} pers)")
            else:
                st.caption("✨ Ledig / Obemannad")
            st.markdown("")


# =====================================================================
# 10. SYSTEMDIAGNOS OCH AUTOMATISERAD FLÖDESANALYS
# =====================================================================
st.markdown("---")
st.subheader("🧠 Systemdiagnos & AI-Flödesanalys")
col_diag1, col_diag2 = st.columns(2)

with col_diag1:
    st.markdown("##### ⚙️ Resursallokering")
    if st.session_state.sim_minutes < 810:
        st.info("🔄 **Normaldrift:** AI-Autopiloten prioriterar kärnflödet (Inbound, Plock och Pack) för att hålla ledtiderna nere.")
    elif st.session_state.sim_minutes >= 810 and st.session_state.sim_minutes <= 870:
        st.warning("⚡ **Transportförberedelse:** Personal har automatiskt styrts om till Sortering och Utlastning inför bilens avgång kl 14:30.")
    else:
        st.error("🔒 **Eftermiddagsfas:** Dagens bil har avgått. Personal har flyttats till Returer och Putaway-buffertar.")

with col_diag2:
    st.markdown("##### 🚨 Flaskhalsanalys")
    if st.session_state.db_data['queue_pack'] > 600 and st.session_state.db_data['queue_pick_stock'] > 2000:
        st.error(f"⚠️ **Aktiv Flaskhals:** Högt tryck vid packborden ({st.session_state.db_data['queue_pack']} order väntar). Autopiloten maximerar packkapaciteten.")
    elif st.session_state.db_data['queue_pick_stock'] < 1000 and st.session_state.db_data['queue_pick_stock'] > 0:
        st.warning(f"📉 **Plockkö Minimerad:** Endast {st.session_state.db_data['queue_pick_stock']} rader kvar. AI slussar löpande över plockare till packstationerna.")
    elif st.session_state.db_data['putaway_stock'] > 300:
        st.warning(f"📦 **Lagerbuffert:** Stor mängd kartonger ({st.session_state.db_data['putaway_stock']} st) i Putaway. AI styr ledig kapacitet hit för inlagring.")
    else:
        st.success("✅ **Balanserat Flöde:** Inga kritiska flaskhalsar identifierade i lagerkedjan just nu.")


# =====================================================================
# 11. DETALJERAD TIDSPROGNOS FÖR SKIFTET (JUSTERAD TEXT TILL 100/H)
# =====================================================================
p_sort = list(st.session_state.placering.values()).count("Sortering")
p_utlastning = list(st.session_state.placering.values()).count("Utlastning")
p_transport = list(st.session_state.placering.values()).count("Transport")
p_retur = list(st.session_state.placering.values()).count("Returer")

total_sort_speed = p_sort * 150  

time_pick_stock = st.session_state.db_data['queue_pick_stock'] / max(total_pick_stock_speed_h, 0.1)
time_pack = st.session_state.db_data['queue_pack'] / max(total_pack_speed_h, 0.1)

st.markdown("---")
st.markdown("### 📊 Detaljerad tidsprognos för skiftet")
prognos_data = {
    "Processflöde": [
        "Inbound: Stock (35 min/pall)", "Inbound: Non-Stock (35 min/pall)", 
        "Inlagring: Putaway Stock (4 kart/h block)", "Inlagring: Putaway Non-Stock (4 kart/h block)", 
        "Plock: Stock (100 rader/h snitt)", "Packning (110 paket/h snitt)", # ⚡ Uppdaterad text
        "Sortering & Pallning", "Utlastning & Transport", "Returer"
    ],
    "Aktuell Bemanning (Antal)": [p_in_stock, p_in_non, p_put_stock, p_put_non, p_pick_stock, p_pack, p_sort, (p_utlastning + p_transport), p_retur],
    "Total Gruppkapacitet / timme": [
        f"{round(total_in_stock_speed_h, 1)} pallar", f"{round(total_in_non_speed_h, 1)} pallar", 
        f"{total_put_stock_speed_h * 4} kartonger", f"{total_put_non_speed_h * 4} kartonger", 
        f"{total_pick_stock_speed_h} rader", f"{total_pack_speed_h} paket",
        f"{total_sort_speed} paket", f"{p_utlastning * 4} pallar", "Löpande"
    ],
    "Tid till tomt (Timmar)": [
        round(st.session_state.db_data['inbound_stock']/max(total_in_stock_speed_h,0.1), 1), 
        round(st.session_state.db_data['inbound_non_stock']/max(total_in_non_speed_h,0.1), 1), 
        round(st.session_state.db_data['putaway_stock']/max(total_put_stock_speed_h * 4, 0.1), 1), 
        round(st.session_state.db_data['putaway_non_stock']/max(total_put_non_speed_h * 4, 0.1), 1), 
        round(time_pick_stock, 1), round(time_pack, 1),
        "Automatisk", "Klar 14:30", "Löpande"
    ]
}
st.table(prognos_data)


# =====================================================================
# 12-14. SPECSAVERS EUROPEAN SHIPPING HUB (NEDERLÄNDERNA TILLAGD)
# =====================================================================
st.markdown("---")
st.subheader("🌐 Specsavers Nordic & European Shipping Hub")
col_sh1, col_sh2, col_sh3, col_sh4 = st.columns(4)
with col_sh1: 
    # 🇳🇱 Nederländerna är nu officiellt adderat till transportmålet
    st.metric(label="Dagligen: SE / NO / FI / NL", value="1 pall / land", delta="Inklusive Nederländerna")
with col_sh2: 
    st.metric(label="Månadsbuffert: Danmark", value="14 pallar", delta="Sektion D Säkrad", delta_color="off")
with col_sh3:
    # 🔥 NY LAYOUT: Visar det exakta totala antalet packade paket live under dagen
    st.metric(label="Totalt packade paket idag", value=f"{st.session_state.total_packat_historik:,} st".replace(",", " "), delta="Ackumulerat flöde")
with col_sh4:
    st.metric(label="Klara inventerade rader", value=f"{st.session_state.inventering_rader_klara} st", delta="Kvalitetssäkrat")


# =====================================================================
# 15. EKONOMISKT UTFALL (OPTIMERAD P&L UTAN LOGISKA FEL)
# =====================================================================
st.markdown("---")
st.subheader("💰 Skiftets Ekonomiska Utfall (Real-Time P&L)")

# Maskerade, säkrade tariffer baserade på era partneravtal
PRIS_IN_STOCK = 85.00     # Höjt per pall för att matcha inlagringsvärdet
PRIS_IN_NON = 95.00       
PRIS_OUT_ORDER = 5.80     # Justerad intäkt per plockad rad
PRIS_PACK_BOX = 6.50      # Justerad intäkt per packat paket

LON_OPERATOR = 325.0     
LON_LEADER = 355.0       

# Drifttimmar (Simuleringen pågår aktivt under produktiv tid kl 06:00 till 16:30, max 10.5h)
effektiva_timmar = min(10.5, max(0.1, (st.session_state.sim_minutes - 360) / 60.0))

# 1. Ackumulerad lönekostnad baserat på faktisk arbetad tid
kostnad_personal = int((14 * LON_OPERATOR * effektiva_timmar) + (1 * LON_LEADER * effektiva_timmar))

# 2. Löpande bruttointäkt (Värdet av all utförd produktion)
intakt_in_stock = (6 - st.session_state.db_data["inbound_stock"]) * PRIS_IN_STOCK
intakt_in_non = (1 - st.session_state.db_data["inbound_non_stock"]) * PRIS_IN_NON
intakt_plock = (10000 - st.session_state.db_data["queue_pick_stock"]) * PRIS_OUT_ORDER

# Räkna med både avklarade paket och paket sparade till morgondagen
totalt_packat_antal = (START_PACK - st.session_state.db_data["queue_pack"]) + st.session_state.morgondagens_pack
intakt_pack = max(0, totalt_packat_antal * PRIS_PACK_BOX)

totala_intakter = int(max(0, intakt_in_stock + intakt_in_non + intakt_plock + intakt_pack))

# Matematisk marginalberäkning
netto_resultat = totala_intakter - kostnad_personal

col_fin1, col_fin2, col_fin3 = st.columns(3)
with col_fin1:
    st.metric(label="Löpande Bruttointäkter (Fakturerbart)", value=f"{totala_intakter:,} kr".replace(",", " "), delta="Utförd produktion")
with col_fin2:
    st.metric(label="Ackumulerad Operativ Kostnad (Löner)", value=f"{kostnad_personal:,} kr".replace(",", " "), delta="15 pers på skiftet", delta_color="inverse")
with col_fin3:
    if netto_resultat >= 0:
        st.metric(label="Nettoresultat (Marginal)", value=f"+ {netto_resultat:,} kr".replace(",", " "), delta="🟢 Positivt kassaflöde")
    else:
        st.metric(label="Nettoresultat (Marginal)", value=f"{netto_resultat:,} kr".replace(",", " "), delta="🔴 Kostnadstäckningsfas")

st.info(
    "💡 **Ledningsinsikt:** Denna kalkylator körs med maskerade tariffer för att skydda kommersiella avtal. "
    "AI-Autopiloten minimerar flaskhalsar vid packborden och stänger automatiskt av returstationen efter 2 timmar "
    "för att hålla nettomarginalerna maximalt lönsamma under hela dygnet."
)

if live_sim:
    time.sleep(5)
    st.rerun()

