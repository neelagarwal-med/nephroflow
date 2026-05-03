# 💧 NephroFlow: IWL Adjustment Engine

**NephroFlow** is a real-time clinical prototyping tool designed to calculate dynamic fluid intake adjustments for patients with Chronic Kidney Disease (CKD) based on environmental stress and Insensible Water Loss (IWL).

In healthy individuals, the kidneys autoregulate fluid balance. In advanced CKD (Stages 4-5), the Glomerular Filtration Rate (GFR) is severely compromised, making patients highly susceptible to fluid overload, pulmonary edema, and dilutional hyponatremia if they overcompensate for heat by drinking too much water. NephroFlow bridges the gap between static daily fluid limits and dynamic, real-world environmental conditions.

## 🌟 Key Features
* **Real-Time Environmental Integration:** Fetches live temperature and humidity data via the OpenWeatherMap API using the patient's ZIP code.
* **Physiological Modeling:** Calculates Body Surface Area (BSA) using the Du Bois & Du Bois formula to establish an accurate baseline IWL.
* **Dynamic Scaling:** Adjusts recommended fluid intake based on extreme heat (>30°C), high humidity (>70%), high altitude respiratory loss, and time spent outdoors.
* **Strict Clinical Safety Rails:** Enforces an absolute safety ceiling (Baseline Limit + 30%) and applies conservative adjustment multipliers for late-stage (Stage 4/5) CKD to prevent fatal fluid overload.

## 🛠️ Installation & Local Development

To run this application locally on your machine:

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/neelagarwal-med/nephroflow.git](https://github.com/neelagarwal-med/nephroflow.git)
   cd nephroflow
