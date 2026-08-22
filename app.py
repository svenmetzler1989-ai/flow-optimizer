import streamlit as st

# 1. INSTÄLLNINGAR FÖR HEMSIDAN
st.set_page_config(page_title="Specsavers Optimizer", layout="wide")

# Snygg rubrik högst upp
st.title("👓 Specsavers Flödes-Optimering")
st.subheader("Realtidssystem för personalsupport (Prototyp)")
st.markdown("---")

# 2. SIDOPANEL: HÄR STYR DU PERSONALEN
st.sidebar.header("👥 Dagens Bemanning")
st.sidebar.write("Ställ in hur många som jobbar just nu:")

p_pick = st.sidebar.slider("Personal på Plock & Pack", 1, 30, 18)
p_inbound = st.sidebar.slider("Personal på Inbound", 1, 30, 6)
p_putaway = st.sidebar.slider("Personal på Inlagring (Putaway)", 1, 30, 6)

# Visa totalen så du har koll på dina 30 personer
total_staff = p_pick + p_inbound + p_putaway
st.sidebar.info(f"Totalt schemalagda: {total_staff} av 30 personer")

# 3. INTERAKTIV DATA (Här simulerar vi databasen live på skärmen)
st.markdown("### 📊 Aktuell arbetsbörda (Hämtas live från IMI)")
st.write("Under presentationen kan du ändra siffrorna nedan för att visa hur AI:n reagerar direkt.")

col1, col2, col3 = st.columns(3)

with col1:
    orders = st.number_input("Order kvar i plockkön:", value=5200, step=100)
    st.metric(label="🛒 Plockstatus", value=f"{orders} order")

with col2:
    pallets = st.number_input("Pallar som väntar på Inbound:", value=28, step=1)
    st.metric(label="📥 Inboundstatus", value=f"{pallets} pallar")

with col3:
    putaway = st.number_input("Inlagringsrader kvar (Putaway):", value=450, step=50)
    st.metric(label="📦 Inlagringsstatus", value=f"{putaway} rader")

st.markdown("---")

# 4. MATEMATIKEN OCH LOGIKEN (AI-Hjärnan)
# Vi räknar ut hur mycket varje person hinner med per timme
PICK_SPEED = 45      # En person hinner 45 order i timmen
INBOUND_SPEED = 3    # En person hinner packa upp 3 pallar i timmen
PUTAWAY_SPEED = 40   # En person hinner registrera och lägga undan 40 rader i timmen

# Hur mycket hinner hela avdelningen med på en timme?
total_pick_capacity = p_pick * PICK_SPEED
total_inbound_capacity = p_inbound * INBOUND_SPEED
total_putaway_capacity = p_putaway * PUTAWAY_SPEED

# Hur många timmars arbete ligger kvar på hög? (Siffran delas med kapaciteten)
hours_left_pick = orders / max(total_pick_capacity, 1)
hours_left_inbound = pallets / max(total_inbound_capacity, 1)
hours_left_putaway = putaway / max(total_putaway_capacity, 1)

# 5. PRESENTATION AV ANALYSEN
st.markdown("### 🧠 Gruppledarens AI-Beslutsstöd")

# Vi skapar tre snygga boxar som visar tidsåtgången
b1, b2, b3 = st.columns(3)
b1.write(f"Tid till tom kö i Plock: **{hours_left_pick:.1f} timmar**")
b2.write(f"Tid till tom brygga på Inbound: **{hours_left_inbound:.1f} timmar**")
b3.write(f"Tid till tom golvyta i Inlagring: **{hours_left_putaway:.1f} timmar**")

st.write("")

# SMART REKOMMENDATION (Här känner systemet av flaskhalsar)
if hours_left_pick > 3.5 and hours_left_inbound < 1.5 and p_inbound > 2:
    st.error("🚨 **KRITISK FLASKHALS: PLOCKET SÄCKAR IHOP!**")
    st.markdown(f"**Analys:** Med nuvarande tempo kommer plocket att ta {hours_left_pick:.1f} timmar. Lastbilarna till Norge/Finland kommer att missas!")
    st.info("💡 **Åtgärdsförslag:** Flytta omedelbart **2 personer från Inbound till Plock & Pack**.")

elif hours_left_inbound > 4.0 and hours_left_pick < 2.0 and p_pick > 10:
    st.warning("⚠️ **VARNING: INBOUND BLIR ÖVERFULLT!**")
    st.markdown(f"**Analys:** Lastbilarna har öst av gods. Det tar {hours_left_inbound:.1f} timmar att beta av. Det finns risk för stopp på mottagningsytan.")
    st.info("💡 **Åtgärdsförslag:** Flytta **2-3 personer från Plock till Inbound** tillfälligt.")

elif hours_left_putaway > 3.0 and hours_left_inbound < 1.0 and p_inbound > 2:
    st.warning("📦 **FLASKHALS: VAROR LIGGER PÅ GOLVET (PUTAWAY)!**")
    st.markdown("**Analys:** Godset är mottaget på inbound, men har inte kommit upp på hyllorna än. Plockarna kommer inte hitta varorna i systemet!")
    st.info("💡 **Åtgärdsförslag:** Flytta **1 person från Inbound till Inlagring (Putaway)**.")

else:
    st.success("✅ **OPTIMAL BALANS PÅ LAGRET!**")
    st.write("Just nu matchar din personalfördelning arbetsbördan perfekt. Inga åtgärder krävs.")
