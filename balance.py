"""Pestaña Estado de Situación (Balance General).

Resumen (tarjetas + totales) arriba; el detalle editable de cada
categoría vive dentro de su expander "Ver detalle" respectivo.
"""
import streamlit as st
import notion_client as nc


def _card_html(label, value, color="#00d4ff", big=False):
    value_size = "1.7rem" if big else "1.05rem"
    return f"""
        <div style="
            background: linear-gradient(145deg, {color}14, transparent);
            border: 1px solid {color}55;
            border-radius: 14px;
            padding: 12px 14px;
            box-shadow: 0 0 18px {color}1a;
            margin-bottom: 6px;
            overflow: hidden;
        ">
            <div style="color:#9fd8ff; font-size:0.8rem; white-space:nowrap;
                        overflow:hidden; text-overflow:ellipsis;">{label}</div>
            <div style="color:{color}; font-family:'SF Mono','Courier New',monospace;
                        font-size:{value_size}; font-weight:700; white-space:nowrap;">
                ${value:,.0f}
            </div>
        </div>
    """


def render_balance(tasa_cop: float, tasa_clp: float, precio_btc: float):
    st.subheader("🏦 Estado de Situación")

    BLUE = "#00d4ff"
    ORANGE = "#ffa500"

    # --- Placeholders para las cajas anchas de Total Activos / Total Pasivos ---
    ra1, ra2 = st.columns(2)
    ph_total_activos = ra1.empty()
    ph_total_pasivos = ra2.empty()

    st.write("")

    cb1, cb2, cb3, cb4 = st.columns(4)

    # --- Activos Corrientes ---
    with cb1:
        ph_corr = st.empty()
        with st.expander("Ver detalle"):
            usd_efectivo = st.number_input("USD Efectivo 💵", value=0.0)
            usdt_binance = st.number_input("USDT Binance 🏦", value=1625.0)
            usd_zinli = st.number_input("USD Zinli 🇵🇦", value=10.0)
            usd_paypal = st.number_input("USD Paypal 🇺🇸", value=206.5)
            usd_bdv = st.number_input("USD BDV 🇻🇪", value=20.0)
            cop_efectivo = st.number_input("COP Efectivo 🇨🇴", value=0.0)
            st.caption(f"→ ${(cop_efectivo / tasa_cop if tasa_cop else 0):,.0f}")
            clp_bice = st.number_input("CLP BICE 🇨🇱", value=43986.0)
            st.caption(f"→ ${(clp_bice / tasa_clp if tasa_clp else 0):,.0f}")
            clp_mp = st.number_input("CLP MercadoPago 🇨🇱", value=1689443.0)
            st.caption(f"→ ${(clp_mp / tasa_clp if tasa_clp else 0):,.0f}")

        act_corr = (usd_efectivo + usdt_binance + usd_zinli + usd_paypal + usd_bdv +
                    (cop_efectivo / tasa_cop if tasa_cop else 0) +
                    (clp_bice / tasa_clp if tasa_clp else 0) +
                    (clp_mp / tasa_clp if tasa_clp else 0))
        ph_corr.markdown(_card_html("🔹 Corrientes", act_corr, BLUE), unsafe_allow_html=True)

    # --- Activos No Corrientes ---
    with cb2:
        ph_no_corr = st.empty()
        with st.expander("Ver detalle"):
            try:
                level_up = nc.get_level_up_inventario_activo()
                level_up_auto = True
            except Exception:
                level_up = st.number_input("🎮 Level Up (manual, Notion no disponible)", value=1936.0)
                level_up_auto = False
            if level_up_auto:
                st.write(f"🎮 Level Up (auto): ${level_up:,.0f}")
            btc_inv = st.number_input("₿ Bitcoin", value=0.004125217, format="%.9f")
            st.caption(f"→ ${(btc_inv * precio_btc):,.0f}")
            karla = st.number_input("Karla Switch CxC (CLP)", value=200000.0)
            st.caption(f"→ ${(karla / tasa_clp if tasa_clp else 0):,.0f}")

        act_no_corr = (level_up + btc_inv * precio_btc + (karla / tasa_clp if tasa_clp else 0))
        ph_no_corr.markdown(_card_html("🔹 No Corrientes", act_no_corr, BLUE), unsafe_allow_html=True)

    # --- Pasivos Circulantes ---
    with cb3:
        ph_circ = st.empty()
        with st.expander("Ver detalle"):
            pasivo_alex = st.number_input("Alexandra García", value=2510.0)

        pas_circ = pasivo_alex
        ph_circ.markdown(_card_html("🔸 Circulantes", pas_circ, ORANGE), unsafe_allow_html=True)

    # --- Pasivos No Circulantes ---
    with cb4:
        ph_no_circ = st.empty()
        with st.expander("Ver detalle"):
            pasivo_carlos = st.number_input("Carlos Verdugo (CLP)", value=1722552.0)
            st.caption(f"→ ${(pasivo_carlos / tasa_clp if tasa_clp else 0):,.0f}")

        pas_no_circ = (pasivo_carlos / tasa_clp if tasa_clp else 0)
        ph_no_circ.markdown(_card_html("🔸 No Circulantes", pas_no_circ, ORANGE), unsafe_allow_html=True)

    # --- Totales (llenan los placeholders de arriba) ---
    total_activos = act_corr + act_no_corr
    total_pasivos = pas_circ + pas_no_circ

    ph_total_activos.markdown(_card_html("💠 Total Activos", total_activos, BLUE, big=True), unsafe_allow_html=True)
    ph_total_pasivos.markdown(_card_html("🔶 Total Pasivos", total_pasivos, ORANGE, big=True), unsafe_allow_html=True)

    # --- Balance General ---
    balance_general = total_activos - total_pasivos
    color = "#00ff9d" if balance_general >= 0 else "#ff4d4d"
    st.markdown(f"""
        <div style="
            border: 1px solid {color}55;
            border-radius: 14px;
            padding: 14px 16px;
            margin-top: 10px;
            background: linear-gradient(145deg, {color}14, transparent);
            box-shadow: 0 0 18px {color}22;
        ">
            <div style="color:#9fd8ff; font-size:0.9rem;">Balance General</div>
            <div style="color:{color}; font-family:'SF Mono','Courier New',monospace;
                        font-size:1.6rem; font-weight:700; text-shadow:0 0 10px {color}66;">
                ${balance_general:,.0f}
            </div>
        </div>
    """, unsafe_allow_html=True)
