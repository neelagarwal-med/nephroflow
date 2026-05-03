import streamlit as st
import numpy as np
import requests

# ==========================================
# 1. Core Physiology Engine
# ==========================================
def calculate_bsa(weight_kg: float, height_cm: float) -> float:
    """Calculates Body Surface Area (BSA) using the Du Bois & Du Bois formula."""
    return 0.007184 * np.power(weight_kg, 0.425) * np.power(height_cm, 0.725)

def calculate_hydration(age, weight, height, ckd_stage, baseline_limit, temp, humidity, altitude, outdoors_ratio):
    bsa = calculate_bsa(weight, height)
    baseline_iwl = 400.0 * bsa # Standard baseline estimate: 400 mL/m^2/day
    
    env_offset = 0.0

    # Heat & Humidity Adjustment
    if temp > 30.0:
        degrees_above_30 = temp - 30.0
        heat_driven_loss = baseline_iwl * (0.15 * degrees_above_30)
        
        # High humidity impairs evaporative cooling, increasing sweat rate
        if humidity > 70.0:
            heat_driven_loss *= 1.15  
            
        env_offset += heat_driven_loss

    # Altitude Adjustment (Respiratory loss)
    if altitude > 0:
        respiratory_baseline = baseline_iwl * 0.33
        altitude_multiplier = 0.10 * (altitude / 1000.0)
        env_offset += (respiratory_baseline * altitude_multiplier)

    # Behavioral Scaling
    env_offset *= outdoors_ratio

    # Clinical Safety Rails for Late-Stage CKD
    if ckd_stage in [4, 5]:
        env_offset *= 0.5 # Conservative multiplier due to impaired GFR

    recommended_total = baseline_limit + env_offset
    absolute_ceiling = baseline_limit * 1.30 # Max safety threshold: Baseline + 30%

    hit_ceiling = False
    if recommended_total > absolute_ceiling:
        recommended_total = absolute_ceiling
        env_offset = absolute_ceiling - baseline_limit
        hit_ceiling = True

    return {
        "bsa": bsa,
        "baseline_iwl": baseline_iwl,
        "env_offset": env_offset,
        "total": recommended_total,
        "hit_ceiling": hit_ceiling,
        "ceiling_max": absolute_ceiling
    }

@st.cache_data(ttl=600) # Cache weather for 10 minutes to avoid API spam
def get_weather_by_zip(zip_code: str, api_key: str):
    """Fetches real-time temperature and humidity from OpenWeatherMap."""
    url = f"https://api.openweathermap.org/data/2.5/weather?zip={zip_code},us&appid={api_key}&units=metric"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        return {
            "temp": data["main"]["temp"],
            "humidity": data["main"]["humidity"],
            "city": data["name"]
        }, None
    except requests.exceptions.RequestException as e:
        return None, f"Could not fetch weather. Please check your ZIP code or API key."

# ==========================================
# 2. Streamlit User Interface
# ==========================================
st.set_page_config(page_title="NephroFlow", page_icon="💧", layout="wide")

st.title("💧 NephroFlow: IWL Adjustment Engine")
st.markdown("A real-time Insensible Water Loss (IWL) adjustment calculator for CKD patients.")

# --- Patient-Friendly Education Section ---
with st.expander("🗣️ Patient Guide: What does this mean for me?", expanded=True):
    st.markdown("""
    **Welcome to NephroFlow!** Managing your fluid intake is a critical part of protecting your kidney health. 
    
    * **What is this tool?** When the weather gets hot, you lose water through sweat and breathing without even realizing it (we call this "Insensible Water Loss"). This tool helps you and your doctor figure out exactly how much *extra* water you need to drink on hot days to stay safe.
    * **Why do we need the weather?** A 70-degree day in an air-conditioned office requires a very different fluid plan than a 95-degree day spent working outside in the sun.
    * **The Safety Ceiling:** Your kidneys are currently working hard to filter your blood. Drinking *too much* water can be just as dangerous as drinking too little. This calculator has built-in safety limits to ensure we never recommend more fluid than your body can safely handle.
    """)

# --- SIDEBAR: About the Developer ---
st.sidebar.header("👨‍⚕️ About the Developer")
st.sidebar.markdown("""
**Neel Agarwal** *Medical Student* **The Ohio State University College of Medicine**

**Clinical Focus:** Nephrology, Urology, and Geriatric Medicine. 

*For any feedback - neel.agarwal@osumc.edu*
""")
st.sidebar.divider()

# --- SIDEBAR: Patient Profile Inputs ---
st.sidebar.header("👤 Patient Profile")
age = st.sidebar.number_input("Age", min_value=18, max_value=120, value=65)
weight = st.sidebar.number_input("Weight (kg)", min_value=40.0, max_value=200.0, value=70.0)
height = st.sidebar.number_input("Height (cm)", min_value=140.0, max_value=220.0, value=175.0)
ckd_stage = st.sidebar.selectbox("CKD Stage", [1, 2, 3, 4, 5], index=3) # Default to Stage 4
baseline_limit = st.sidebar.number_input("Baseline Daily Limit (mL)", min_value=500, max_value=3000, value=1500)

st.sidebar.divider()

# --- SIDEBAR: Environmental Inputs ---
st.sidebar.header("🌍 Environmental Data")

weather_mode = st.sidebar.radio("How would you like to enter weather data?", ["Live (via ZIP Code)", "Manual Input"])

# Fallback values to prevent crashes
temp = 35.0
humidity = 45.0

if weather_mode == "Live (via ZIP Code)":
    # Safely try to load the hidden API key
    try:
        owm_api_key = st.secrets["OWM_API_KEY"]
    except KeyError:
        owm_api_key = None
        st.sidebar.error("⚠️ API Key not found. Please add 'OWM_API_KEY' to your Streamlit secrets.")

    zip_code = st.sidebar.text_input("US ZIP Code", value="43215")
    
    if owm_api_key and zip_code:
        weather_data, error = get_weather_by_zip(zip_code, owm_api_key)
        if error:
            st.sidebar.error(error)
        else:
            temp = weather_data["temp"]
            humidity = weather_data["humidity"]
            st.sidebar.success(f"📍 **{weather_data['city']}**\n\n🌡️ {temp:.1f}°C | 💧 {humidity}%")

elif weather_mode == "Manual Input":
    temp = st.sidebar.slider("Temperature (°C)", min_value=-10.0, max_value=50.0, value=35.0)
    humidity = st.sidebar.slider("Humidity (%)", min_value=0.0, max_value=100.0, value=45.0)

# Altitude is now exposed in BOTH modes to ensure real data is used, no simulations.
altitude = st.sidebar.slider("Altitude (m above sea level)", min_value=0.0, max_value=5000.0, value=200.0)

# --- SIDEBAR: Behavioral Inputs ---
st.sidebar.divider()
st.sidebar.header("🏢 Behavioral Data")
# Updated to Hours for real-world usability
outdoors_hours = st.sidebar.slider(
    "Time Spent Outdoors (Hours)", 
    min_value=0.0, max_value=24.0, value=4.0, step=0.5,
    help="0 hours = 100% Indoors in A/C. 24 hours = 100% Outdoors."
)
outdoors_ratio = outdoors_hours / 24.0 # Converts hours to ratio for the math engine

# ==========================================
# 3. Scientific Explanation Section
# ==========================================
with st.expander("📚 The Clinical Science: Understanding IWL in CKD", expanded=False):
    st.markdown("""
    ### What is Insensible Water Loss (IWL)?
    IWL refers to fluid lost daily that cannot be easily measured. This occurs primarily through **cutaneous diffusion** (sweat) and the **respiratory tract** (breathing). 
    
    ### Why is this critical for CKD Patients?
    In healthy individuals, the kidneys autoregulate fluid balance by altering urine concentration. In **Chronic Kidney Disease (Stages 4-5)**, the Glomerular Filtration Rate (GFR) is severely compromised. These patients cannot efficiently excrete excess fluid. 

    If a patient on a strict fluid restriction experiences extreme heat but overcompensates by drinking too much water, they risk **fluid overload, pulmonary edema, and dilutional hyponatremia**. 

    ### The NephroFlow Mathematical Model
    1. **Body Surface Area (BSA):** We utilize the Du Bois & Du Bois formula:
       $$BSA = 0.007184 \\times weight^{0.425} \\times height^{0.725}$$
    2. **Baseline Scaling:** Normal baseline IWL is estimated at $400 \\text{ mL/m}^2/\\text{day}$.
    3. **Environmental Triggers:** The algorithm dynamically scales this baseline up for temperatures exceeding $30^\\circ\\text{C}$, high humidity (which impairs evaporative cooling), and high altitude.
    4. **The Safety Ceiling:** To prevent fatal fluid overload, the engine enforces a strict mathematical cap. Total fluid intake cannot exceed **Baseline + 30%**, regardless of environmental severity.
    """)

# ==========================================
# 4. Execution & Visualization
# ==========================================
results = calculate_hydration(age, weight, height, ckd_stage, baseline_limit, temp, humidity, altitude, outdoors_ratio)

st.divider()

# Top Metric Cards
col1, col2, col3 = st.columns(3)
col1.metric("Body Surface Area (BSA)", f"{results['bsa']:.2f} m²")
col2.metric("Baseline IWL Estimate", f"{results['baseline_iwl']:.0f} mL/day")
col3.metric("Calculated Env. Offset", f"+{results['env_offset']:.0f} mL")

# Main Output
st.subheader("Clinical Hydration Prescription")

if results['hit_ceiling']:
    st.error(f"⚠️ **CLINICAL SAFETY CEILING TRIGGERED**")
    st.write(f"The environmental conditions requested an adjustment that exceeded the patient's maximum safety threshold of **{results['ceiling_max']:.0f} mL**. To prevent fluid overload, the total recommended intake has been strictly capped.")
else:
    st.success("✅ Adjusted intake is within safe clinical parameters.")

st.metric(
    label="Recommended Total Daily Fluid Intake", 
    value=f"{results['total']:.0f} mL",
    delta=f"{results['env_offset']:.0f} mL environmental adjustment",
    delta_color="off"
)