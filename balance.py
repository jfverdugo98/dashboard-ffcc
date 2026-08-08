"""Pestaña Estado de Situación (Balance General).

Los ítems viven en Notion (base 'Balance General': Item | Categoría |
Liquidez | Monto). La moneda de cada ítem se infiere del prefijo de su
nombre (USD/COP/CLP/BTC, default USD si no hay prefijo reconocido).
Editar montos o agregar/quitar ítems se hace en Notion -- la app solo
lee y calcula, salvo el formulario rápido de "agregar ítem" que sí
escribe de vuelta a Notion.
"""
import streamlit as st
import pandas as pd
import notion_client as nc

LIQUIDEZ_OPCIONES = ["Corriente", "No Corriente", "Circulante", "No Circulante"]


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


def _convertir_usd(monto, moneda, tasa_cop, tasa_clp, precio_btc):
    if moneda == "COP":
        return monto / tasa_cop if tasa_cop else 0
    if moneda == "CLP":
        return monto / tasa_clp if tasa_clp else 0
    if moneda == "BTC":
        return monto * precio_btc
    return monto  # USD (incluye USDT)


def _detalle_df(items):
    return pd.DataFrame([{
        "Item": it["item"],
        "Monto": (f"{it['monto']:,.8f} BTC" if it["moneda"] == "BTC"
                  else f"{it['monto']:,.0f} {it['moneda']}"),
        "Monto USD": f"${it['monto_usd']:,.2f}",
    } for it in items])


def render_balance(tasa_cop: float, tasa_clp: float, precio_btc: float):
    st.subheader("🏦 Estado de Situación")

    BLUE = "#00d4ff"
    ORANGE = "#ffa500"

    try:
        items = nc.get_balance_items()
        for it in items:
            it["monto_usd"] = _convertir_usd(it["monto"], it["moneda"], tasa_cop, tasa_clp, precio_btc)
        error = None
    except Exception as e:
        items, error = [], str(e)

    if error:
        st.error(f"No se pudo leer la base de Balance General en Notion: {error}")
        return

    def _bucket(categoria, liquidez):
        return [it for it in items if it["categoria"] == categoria and it["liquidez"] == liquidez]

    act_corr_items = _bucket("Activo", "Corriente")
    act_no_corr_items = _bucket("Activo", "No Corriente")
    pas_circ_items = _bucket("Pasivo", "Circulante")
    pas_no_circ_items = _bucket("Pasivo", "No Circulante")

    # Level Up (inventario aún no vendido) se calcula en vivo desde Notion,
    # no vive en la base de Balance General -- se agrega como ítem sintético.
    try:
        level_up = nc.get_level_up_inventario_activo()
        act_no_corr_items = act_no_corr_items + [{
            "item": "🎮 Level Up (auto)",
            "categoria": "Activo",
            "liquidez": "No Corriente",
            "monto": level_up,
            "moneda": "USD",
            "monto_usd": level_up,
        }]
    except Exception:
        pass

    act_corr = sum(it["monto_usd"] for it in act_corr_items)
    act_no_corr = sum(it["monto_usd"] for it in act_no_corr_items)
    pas_circ = sum(it["monto_usd"] for it in pas_circ_items)
    pas_no_circ = sum(it["monto_usd"] for it in pas_no_circ_items)

    # --- Placeholders para las cajas anchas de Total Activos / Total Pasivos ---
    ra1, ra2 = st.columns(2)
    ph_total_activos = ra1.empty()
    ph_total_pasivos = ra2.empty()

    st.write("")

    cb1, cb2, cb3, cb4 = st.columns(4)

    with cb1:
        st.markdown(_card_html("🔹 Corrientes", act_corr, BLUE), unsafe_allow_html=True)
        with st.expander("Ver detalle"):
            if act_corr_items:
                st.dataframe(_detalle_df(act_corr_items), hide_index=True, use_container_width=True)
            else:
                st.caption("Sin ítems.")

    with cb2:
        st.markdown(_card_html("🔹 No Corrientes", act_no_corr, BLUE), unsafe_allow_html=True)
        with st.expander("Ver detalle"):
            if act_no_corr_items:
                st.dataframe(_detalle_df(act_no_corr_items), hide_index=True, use_container_width=True)
            else:
                st.caption("Sin ítems.")

    with cb3:
        st.markdown(_card_html("🔸 Circulantes", pas_circ, ORANGE), unsafe_allow_html=True)
        with st.expander("Ver detalle"):
            if pas_circ_items:
                st.dataframe(_detalle_df(pas_circ_items), hide_index=True, use_container_width=True)
            else:
                st.caption("Sin ítems.")

    with cb4:
        st.markdown(_card_html("🔸 No Circulantes", pas_no_circ, ORANGE), unsafe_allow_html=True)
        with st.expander("Ver detalle"):
            if pas_no_circ_items:
                st.dataframe(_detalle_df(pas_no_circ_items), hide_index=True, use_container_width=True)
            else:
                st.caption("Sin ítems.")

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

    # --- Agregar nuevo ítem (escribe directo a Notion) ---
    with st.expander("➕ Agregar ítem al Balance General"):
        st.caption("El prefijo del nombre define la moneda: USD, COP, CLP o BTC. Sin prefijo = USD.")
        with st.form("form_balance_item", clear_on_submit=True):
            fc1, fc2 = st.columns(2)
            f_item = fc1.text_input("Item (ej: CLP Cuenta Ahorro)")
            f_monto = fc2.number_input("Monto", value=0.0, step=1.0, format="%.8f")
            fc3, fc4 = st.columns(2)
            f_categoria = fc3.selectbox("Categoría", ["Activo", "Pasivo"])
            f_liquidez = fc4.selectbox("Liquidez", LIQUIDEZ_OPCIONES)
            if st.form_submit_button("Guardar en Notion"):
                if f_item.strip():
                    nc.add_balance_item(f_item.strip(), f_categoria, f_liquidez, f_monto)
                    st.success("Ítem guardado en Notion.")
                    st.rerun()
                else:
                    st.error("El nombre del ítem no puede estar vacío.")
