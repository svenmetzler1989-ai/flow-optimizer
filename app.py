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
# 3. MEDARBETARDATABAS (NAMNGIVEN OCH KALIBRERAD FÖR 15 PERSONER)
# =====================================================================
if 'medarbetare_info' not in st.session_state:
    # 👥 Alla 15 unika medarbetare har nu fått sina riktiga namn
    medarbetare_info = {
        "EMP-101": {"namn": "Anna", "pick_speed": 91, "pack_speed": 95, "putaway_speed": 85, "start_zon": "Plock Stock"},
        "EMP-102": {"namn": "Per", "pick_speed": 89, "pack_speed": 105, "putaway_speed": 75, "start_zon": "Packning"},
        "EMP-103": {"namn": "Lars", "pick_speed": 90, "pack_speed": 100, "putaway_speed": 95, "start_zon": "Putaway Stock"},
        "EMP-104": {"namn": "Elin", "pick_speed": 92, "pack_speed": 98, "putaway_speed": 80, "start_zon": "Plock Non-Stock"},
        "EMP-105": {"namn": "Mikael", "pick_speed": 88, "pack_speed": 102, "putaway_speed": 70, "start_zon": "Inbound Stock"},
        "EMP-106": {"namn": "Karin", "pick_speed": 90, "pack_speed": 97, "putaway_speed": 78, "start_zon": "Packning"},
        "EMP-107": {"namn": "Anders", "pick_speed": 93, "pack_speed": 103, "putaway_speed": 82, "start_zon": "Plock Stock"},
        "EMP-108": {"namn": "Johan", "pick_speed": 87, "pack_speed": 101, "putaway_speed": 84, "start_zon": "Putaway Stock"},
        "EMP-109": {"namn": "Sara", "pick_speed": 91, "pack_speed": 104, "putaway_speed": 76, "start_zon": "Plock Non-Stock"},
        "EMP-110": {"namn": "Nils", "pick_speed": 89, "pack_speed": 96, "putaway_speed": 80, "start_zon": "Plock Stock"},
        "EMP-111": {"namn": "Emma", "pick_speed": 92, "pack_speed": 102, "putaway_speed": 85, "start_zon": "Packning"},
        "EMP-112": {"namn": "Sven", "pick_speed": 88, "pack_speed": 99, "putaway_speed": 79, "start_zon": "Plock Stock"},
        "EMP-113": {"namn": "Maria", "pick_speed": 90, "pack_speed": 105, "putaway_speed": 81, "start_zon": "Packning"},
        "EMP-114": {"namn": "Olof", "pick_speed": 91, "pack_speed": 98, "putaway_speed": 83, "start_zon": "Plock Stock"},
        "EMP-115": {"namn": "Linda", "pick_speed": 89, "pack_speed": 100, "putaway_speed": 77, "start_zon": "Plock Stock"}
    }
    st.session_state.medarbetare_info = medarbetare_info

if 'placering' not in st.session_state:
    st.session_state.placering = {emp_id: info["start_zon"] for emp_id, info in st.session_state.medarbetare_info.items()}

if 'db_data' not in st.session_state:
    st.session_state.db_data = fetch_live_data()

# Officiell lista över alla tillgängliga zoner i lagerlayouten
LAGER_ZONER = [
    "Plock Stock", "Packning", "Inbound Stock", "Inbound Non-Stock", 
    "Putaway Stock", "Putaway Non-Stock", "Plock Non-Stock", 
    "Sortering", "Utlastning", "Transport", "Returer", "Inventering", "Städning"
]

# Sidopanels-meny för manuell omplacering (om användaren vill överstyra AI)
st.sidebar.markdown("### 🛠️ Manuell Resursstyrning")
valda_pers = st.sidebar.multiselect("Välj medarbetare att flytta:", list(st.session_state.medarbetare_info.keys()))
ny_zon = st.sidebar.selectbox("Välj ny station/zon:", LAGER_ZONER)
if st.sidebar.button("Verkställ manuell flytt"):
    for vp in valda_pers:
        st.session_state.placering[vp] = ny_zon
    st.session_state.just_clicked = True
    st.sidebar.success(f"Flyttade {len(valda_pers)} personer till {ny_zon}!")


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
p_sort = list(st.session_state.placering.values()).count("Sortering")
p_utlastning = list(st.session_state.placering.values()).count("Utlastning")
p_transport = list(st.session_state.placering.values()).count("Transport")
p_retur = list(st.session_state.placering.values()).count("Returer")
p_inventering = list(st.session_state.placering.values()).count("Inventering")
p_stadning = list(st.session_state.placering.values()).count("Städning")

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
col_side1, col_side2 = st.sidebar.columns(2)
with col_side1:
    st.markdown(f"📥 **Inbound St:** `{p_in_stock} p`\n📥 **Inbound Non:** `{p_in_non} p`\n🔼 **Putaway St:** `{p_put_stock} p`\n🔼 **Putaway Non:** `{p_put_non} p`\n🛒 **Plock Stock:** `{p_pick_stock} p`\n🛒 **Plock Non:** `{p_pick_non} p`\n📦 **Packning:** `{p_pack} p`")
with col_side2:
    st.markdown(f"🧩 **Sortering:** `{p_sort} p`\n🚛 **Utlastning:** `{p_utlastning} p`\n🚚 **Transport:** `{p_transport} p`\n↩️ **Returer:** `{p_retur} p`\n🔍 **Inventering:** `{p_inventering} p`\n🧹 **Städning:** `{p_stadning} p`")


# =====================================================================
# 6. SIMULERINGSLOGIK (PACK 100/H, PLOCK 90/H & SÄKRAD DRIFT TILL 22:45)
# =====================================================================
if "just_clicked" not in st.session_state:
    st.session_state.just_clicked = False
if "morgondagens_pack" not in st.session_state:
    st.session_state.morgondagens_pack = 0
if "retur_notis" not in st.session_state:
    st.session_state.retur_notis = False
if "retur_start_tid" not in st.session_state:
    st.session_state.retur_start_tid = 0

if "inventering_startad" not in st.session_state:
    st.session_state.inventering_startad = False
if "inventering_start_tid" not in st.session_state:
    st.session_state.inventering_start_tid = 0
if "inventering_klar_for_dagen" not in st.session_state:
    st.session_state.inventering_klar_for_dagen = False

if live_sim and st.session_state.sim_minutes < 1410:
    if st.session_state.just_clicked:
        st.session_state.just_clicked = False  
    else:
        st.session_state.sim_minutes += 10  
    
    m = st.session_state.sim_minutes
    
    # ⏱️ RAST-MOTOR: All produktion fryser under rasterna
    ar_det_rast = (
        (480 <= m < 495) or (660 <= m < 690) or (780 <= m < 795) or
        (990 <= m < 1005) or (1170 <= m < 1200) or (1290 <= m < 1305)
    )

    # ⏱️ RETURTIMER: Stängs av automatiskt efter 1.5 timme (90 minuter) för att spara resurser
    if st.session_state.retur_notis:
        if m - st.session_state.retur_start_tid >= 90:
            st.session_state.retur_notis = False

    if st.session_state.inventering_startad and not st.session_state.inventering_klar_for_dagen:
        if m - st.session_state.inventering_start_tid >= 150:
            st.session_state.inventering_klar_for_dagen = True

    # --- DYNAMISK AI-AUTOPILOT: SMART RESURSREGLERING ---
    current_placering = st.session_state.placering
    all_emps = list(st.session_state.medarbetare_info.keys())
    
    def get_count(zon): return list(st.session_state.placering.values()).count(zon)
    
    rörlig_personal_pool = []
    
    for emp in all_emps:
        # 🚨 EFTER KL 22:45 (Skiftet slutar. Slutför Sortering och Putaway)
        if m >= 1365:
            st.session_state.placering[emp] = "Putaway Stock" if get_count("Putaway Stock") < 8 else "Sortering"
            continue

        # A. LÅST DRIFT FÖR INBOUND & PUTAWAY KEDJORNA (1 person per flödeskedja)
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

        # B. LÖPANDE SORTERING & PALLISERING (Alltid 2-3 personer)
        mål_sorterare = 3 if st.session_state.db_data["queue_pack"] > 300 else 2
        if get_count("Sortering") < mål_sorterare:
            st.session_state.placering[emp] = "Sortering"
            continue

        # C. PLOCK NON-STOCK (Max 2 personer vid behov fram till kl 21:30)
        elif st.session_state.db_data["queue_pick_non_stock"] > 0 and get_count("Plock Non-Stock") < 2 and m < 1290:
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

        # E. ↩️ RETUR-REGLERING (Max 1 person styrs hit under tidtagning)
        elif st.session_state.retur_notis and get_count("Returer") < 1:
            st.session_state.placering[emp] = "Returer"
            continue

        # 🔍 F. INVENTERING UNDER DAGEN (Max 1 person, max 2.5 timmar totalt)
        elif not st.session_state.inventering_klar_for_dagen and get_count("Inventering") < 1:
            if not st.session_state.inventering_startad:
                st.session_state.inventering_startad = True
                st.session_state.inventering_start_tid = m
            st.session_state.placering[emp] = "Inventering"
            continue

        # Återströmning till rörliga poolen
        if current_placering[emp] in ["Inbound Stock", "Inbound Non-Stock", "Putaway Stock", "Putaway Non-Stock", "Plock Non-Stock", "Returer", "Transport", "Utlastning", "Sortering", "Inventering", "Städning"]:
            st.session_state.placering[emp] = "Plock Stock"

        rörlig_personal_pool.append(emp)

    # ⚖️ REGLERINGSMOTORN (Trögrörlig parering, reagerar endast vid stor volym)
    total_kärna = len(rörlig_personal_pool)
    if total_kärna > 0 and m < 1365:
        if m >= 1290 or st.session_state.db_data["queue_pick_stock"] == 0:
            mål_packare = min(11, total_kärna)
            for rörlig_idx, emp_id in enumerate(rörlig_personal_pool):
                if rörlig_idx < mål_packare:
                    st.session_state.placering[emp_id] = "Packning"
                else:
                    st.session_state.placering[emp_id] = "Städning"
        else:
            if st.session_state.db_data["queue_pack"] > 3000:
                mål_packare = min(11, int(total_kärna * 0.80))
            elif st.session_state.db_data["queue_pack"] > 1500:
                mål_packare = min(11, int(total_kärna * 0.45))
            elif st.session_state.db_data["queue_pack"] < 300:
                mål_packare = max(1, int(total_kärna * 0.15))
            else:
                mål_packare = min(11, max(2, int(total_kärna * 0.25)))

            for rörlig_idx, emp_id in enumerate(rörlig_personal_pool):
                if rörlig_idx < mål_packare:
                    st.session_state.placering[emp_id] = "Packning"
                else:
                    st.session_state.placering[emp_id] = "Plock Stock"

    # --- BERÄKNA PRODUKTION LIVE UTIFRÅN TEMPO ---
    if ar_det_rast:
        plockat_stock = plockat_non = packat = inlagrat_stock = inlagrat_non = inventerat_rader = 0
    else:
        # 🛠️ PERFEKT TIDSSYNKRONISERING: Boosten borttagen helt så att tempot är 90 (plock) och 100 (pack)
        hastighets_boost = 1.00 
            
        plockat_stock = int(min(step_pick_stock * hastighets_boost, st.session_state.db_data["queue_pick_stock"]))
        plockat_non = int(min(step_pick_non, st.session_state.db_data["queue_pick_non_stock"]))
        
        # ⚡ NY PACKTAKT: Dynamiskt beräknad baserat på 100 paket/h per anställd
        step_pack_100 = (p_pack * 100.0) / 6.0
        packat = int(min(step_pack_100 * hastighets_boost, st.session_state.db_data["queue_pack"] + plockat_stock + plockat_non))
        
        inlagrat_stock = int(min(step_put_stock * 4, st.session_state.db_data["putaway_stock"]))
        inlagrat_non = int(min(step_put_non * 4, st.session_state.db_data["putaway_non_stock"]))
        inventerat_rader = p_inventering * 5 

    # Verkställ produktionen
    st.session_state.db_data["queue_pick_stock"] = max(0, st.session_state.db_data["queue_pick_stock"] - plockat_stock)
    st.session_state.db_data["queue_pick_non_stock"] = max(0, st.session_state.db_data["queue_pick_non_stock"] - plockat_non)
    
    total_nyplockat = plockat_stock + plockat_non
    st.session_state.db_data["queue_pack"] = max(0, st.session_state.db_data["queue_pack"] + total_nyplockat - packat)
    
    st.session_state.total_packat_historik += packat
    st.session_state.inventering_rader_klara += inventerat_rader

    st.session_state.db_data["putaway_stock"] = max(0, st.session_state.db_data["putaway_stock"] - inlagrat_stock)
    st.session_state.db_data["putaway_non_stock"] = max(0, st.session_state.db_data["putaway_non_stock"] - inlagrat_non)

    # Inkommande gods under dagen
    if m <= 1100 and random.random() > 0.93:
        st.session_state.db_data["inbound_stock"] += random.randint(1, 2)
    
    if m in [540, 900] and st.session_state.totalt_inkommande_non < 3:
        st.session_state.db_data["inbound_non_stock"] += 1
        st.session_state.totalt_inkommande_non += 1


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
# 11. DETALJERAD TIDSPROGNOS FÖR SKIFTET (UPPDATERADE MÅLTAL)
# =====================================================================
total_sort_speed = p_sort * 150  

time_pick_stock = st.session_state.db_data['queue_pick_stock'] / max(total_pick_stock_speed_h, 0.1)
time_pack = st.session_state.db_data['queue_pack'] / max((p_pack * 100.0), 0.1) # Baserat på 100/h

st.markdown("---")
st.markdown("### 📊 Detaljerad tidsprognos för skiftet")
prognos_data = {
    "Processflöde": [
        "Inbound: Stock (35 min/pall)", "Inbound: Non-Stock (35 min/pall)", 
        "Inlagring: Putaway Stock (4 kart/h)", "Inlagring: Putaway Non-Stock (4 kart/h)", 
        "Plock: Stock (90 rader/h snitt)", "Packning (100 paket/h snitt)", # ⚡ Uppdaterade tempon
        "Sortering & Pallning", "Utlastning & Transport", "Returer",
        "Inventering (Kvalitetssäkring)", "Städning (5S Miljödrift)"
    ],
    "Aktuell Bemanning (Antal)": [p_in_stock, p_in_non, p_put_stock, p_put_non, p_pick_stock, p_pack, p_sort, (p_utlastning + p_transport), p_retur, p_inventering, p_stadning],
    "Total Gruppkapacitet / timme": [
        f"{round(total_in_stock_speed_h, 1)} pallar", f"{round(total_in_non_speed_h, 1)} pallar", 
        f"{total_put_stock_speed_h * 4} kartonger", f"{total_put_non_speed_h * 4} kartonger", 
        f"{total_pick_stock_speed_h} rader", f"{p_pack * 100} paket", # ⚡ Visar 100/h
        f"{total_sort_speed} paket", f"{p_utlastning * 4} pallar", "Löpande",
        f"{p_inventering * 30} rader", "Löpande"
    ],
    "Tid till tomt (Timmar)": [
        round(st.session_state.db_data['inbound_stock']/max(total_in_stock_speed_h,0.1), 1), 
        round(st.session_state.db_data['inbound_non_stock']/max(total_in_non_speed_h,0.1), 1), 
        round(st.session_state.db_data['putaway_stock']/max(total_put_stock_speed_h * 4, 0.1), 1), 
        round(st.session_state.db_data['putaway_non_stock']/max(total_put_non_speed_h * 4, 0.1), 1), 
        round(time_pick_stock, 1), round(time_pack, 1),
        "Automatisk", "Klar 14:30", "Löpande (Max 1.5h)", # ⚡ Uppdaterad text
        "Max 2.5h / dag", "Löpande"
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
# 15. EKONOMISKT UTFALL (UPPDATERAD MED EXAKT 289 KR/H OPERATÖRSLÖN)
# =====================================================================
st.markdown("---")
st.subheader("💰 Skiftets Ekonomiska Utfall (Real-Time P&L)")

PRIS_IN_STOCK = 75.00     
PRIS_IN_NON = 85.00       
PRIS_OUT_ORDER = 1.15     
PRIS_PACK_BOX = 3.20      
PRIS_INVENTERING_RAD = 15.00 

# ⚡ KORREKTA LÖNER: 289 kr/h för lagret och 355 kr/h för dig som gruppledare
LON_OPERATOR = 289.0     
LON_LEADER = 355.0       

effektiva_timmar = min(16.75, max(0.1, (st.session_state.sim_minutes - 360) / 60.0))

# Räknar ut kostnaden baserat på 14 operatörer och 1 gruppledare (dig)
kostnad_personal = int((14 * LON_OPERATOR * effektiva_timmar) + (1 * LON_LEADER * effektiva_timmar))

intakt_in_stock = (6 - st.session_state.db_data["inbound_stock"]) * PRIS_IN_STOCK
intakt_in_non = (3 - st.session_state.db_data["inbound_non_stock"]) * PRIS_IN_NON
intakt_plock = (12500 - st.session_state.db_data["queue_pick_stock"]) * PRIS_OUT_ORDER
intakt_pack = max(0, st.session_state.total_packat_historik * PRIS_PACK_BOX)
intakt_inventering = st.session_state.inventering_rader_klara * PRIS_INVENTERING_RAD

totala_intakter = int(max(0, intakt_in_stock + intakt_in_non + intakt_plock + intakt_pack + intakt_inventering))
netto_resultat = totala_intakter - kostnad_personal

col_fin1, col_fin2, col_fin3 = st.columns(3)
with col_fin1:
    st.metric(label="Löpande Bruttointäkter", value=f"{totala_intakter:,} kr".replace(",", " "), delta="All utförd produktion")
with col_fin2:
    st.metric(label="Ackumulerad Operativ Kostnad", value=f"{kostnad_personal:,} kr".replace(",", " "), delta="14 op á 289kr + 1 GL", delta_color="inverse")
with col_fin3:
    if netto_resultat >= 0:
        st.metric(label="Nettoresultat (Marginal)", value=f"+ {netto_resultat:,} kr".replace(",", " "), delta="🟢 Positivt kassaflöde")
    else:
        st.metric(label="Nettoresultat (Marginal)", value=f"{netto_resultat:,} kr".replace(",", " "), delta="🔴 Kostnadstäckningsfas")

st.info(
    f"🔍 **Inventeringsrapport:** Gruppen har kvalitetssäkrat `{st.session_state.inventering_rader_klara}` orderrader "
    f"vilket har tillfört `{intakt_inventering:,} kr` till skiftets bruttoresultat under den tidsbegränsade 2.5-timmarssessionen."
)

if live_sim:
    time.sleep(5)
    st.rerun()





