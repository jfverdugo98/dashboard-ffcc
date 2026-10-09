"""Pestaña Flujo de Caja: Level Up, Clases, Remesas y Otros."""
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, datetime, timedelta
import calendar

import notion_client as nc
import manual_store as ms
import fx
from cards import card_button

CANALES_CLP = {"Superprof.cl", "Tus Clases"}

MESES_ES = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio",
            "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

PIE_COLOR_MAP = {
    "🎮 Level Up": "#ff00aa",
    "📚 Clases": "#00d4ff",
    "💱 Remesas": "#00ff9d",
    "🧾 Otros": "#9d4edd",
}


def _month_bounds(d: date):
    last_day = calendar.monthrange(d.year, d.month)[1]
    return date(d.year, d.month, 1), date(d.year, d.month, last_day)


def _period_label(start: date, end: date):
    today = date.today()
    if start.year == end.year and start.month == end.month:
        first_of_month = date(start.year, start.month, 1)
        last_of_month = date(start.year, start.month, calendar.monthrange(start.year, start.month)[1])
        if start == first_of_month and end == last_of_month:
            nombre_mes = MESES_ES[start.month]
            if start.year == today.year and start.month == today.month:
                return f"📅 Mes actual ({nombre_mes})"
            return f"📅 {nombre_mes} {start.year}"
    return "📅 Fecha Personalizada"


def _sort_desc(items):
    """Ordena una lista de dicts con clave 'fecha' (ISO) de más reciente
    a más antigua. Sirve solo como orden por defecto -- el usuario puede
    reordenar haciendo click en los encabezados de las tablas."""
    return sorted(items, key=lambda x: x.get("fecha") or "", reverse=True)


def _short_date(iso_str):
    if not iso_str:
        return ""
    d = datetime.strptime(iso_str[:10], "%Y-%m-%d")
    return d.strftime("%d/%m")


def render_cashflow(tasa_clp: float):
    titulo_ph = st.empty()

    today = date.today()
    opciones = ["Este mes", "Mes anterior", "Este año", "Rango personalizado"]
    periodo = st.radio("Período", opciones, index=0, horizontal=True,
                       key="cf_periodo", label_visibility="collapsed")

    if periodo == "Este mes":
        start, end = _month_bounds(today)
    elif periodo == "Mes anterior":
        start, end = _month_bounds(date(today.year, today.month, 1) - timedelta(days=1))
    elif periodo == "Este año":
        start, end = date(today.year, 1, 1), today
    else:
        c1, c2 = st.columns(2)
        d0, d1 = _month_bounds(today)
        start = c1.date_input("Desde", value=d0, key="cf_start")
        end = c2.date_input("Hasta", value=d1, key="cf_end")

    if periodo in ("Este mes", "Mes anterior"):
        sufijo = f" ({MESES_ES[start.month]}" + (f" {start.year})" if start.year != today.year else ")")
    elif periodo == "Este año":
        sufijo = f" {start.year}"
    else:
        sufijo = f" ({start:%d/%m/%Y} – {end:%d/%m/%Y})"
    titulo_ph.subheader(f"💰 Flujo de Caja{sufijo}")

    if start > end:
        st.error("El rango de fechas es inválido (Desde > Hasta).")
        return

    # --- Level Up (Notion, USD) -- usa Utilidad, no Precio venta ---
    try:
        ventas = nc.get_level_up_ventas(start, end)
        total_level_up = sum(v["utilidad"] for v in ventas)
        error_level_up = None
    except Exception as e:
        ventas, total_level_up, error_level_up = [], 0, str(e)

    # --- Clases particulares (Notion) ---
    # Superprof.cl / Tus Clases cobran en CLP (se convierte con el tipo de
    # cambio histórico del día de la clase); Preply / Superprof.com ya
    # vienen en USD directo.
    try:
        clases = nc.get_clases(start, end)
        fx_hist = fx.clp_history(start, end)

        def _clase_usd(c):
            if c["canal"] in CANALES_CLP:
                d = date.fromisoformat(c["fecha"][:10]) if c["fecha"] else start
                rate = fx.rate_on(fx_hist, d, tasa_clp)
                return c["valor_clp"] / rate if rate else 0
            return c["valor_usd"] or 0

        for c in clases:
            c["valor_usd_resuelto"] = _clase_usd(c)
        total_clases_ingresos = sum(c["valor_usd_resuelto"] for c in clases)
        error_clases = None
    except Exception as e:
        clases, total_clases_ingresos, error_clases = [], 0, str(e)

    # --- Gastos Operativos (Notion) -- se restan de los ingresos de Clases ---
    try:
        gastos = nc.get_gastos_operativos(start, end)

        def _gasto_usd(g):
            if g["monto_usd"]:
                return g["monto_usd"]
            if g["monto_clp"]:
                d = date.fromisoformat(g["fecha"][:10]) if g["fecha"] else start
                rate = fx.rate_on(fx_hist, d, tasa_clp)
                return g["monto_clp"] / rate if rate else 0
            return 0

        for g in gastos:
            g["monto_usd_resuelto"] = _gasto_usd(g)
        total_gastos = sum(g["monto_usd_resuelto"] for g in gastos)
        error_gastos = None
    except Exception as e:
        gastos, total_gastos, error_gastos = [], 0, str(e)

    total_clases_usd = total_clases_ingresos - total_gastos

    # --- Remesas (Notion si existe, si no, manual local) ---
    try:
        remesas = nc.get_remesas(start, end)
        remesas_source = "notion"
    except Exception:
        remesas, remesas_source = [], "manual"
    if not remesas and remesas_source != "notion":
        remesas = [
            {"fecha": e["fecha"], "nombre": e["nota"] or "Remesa", "monto": e["monto"]}
            for e in ms.entries_in_range("remesas", start, end)
        ]
    total_remesas = sum(r["monto"] for r in remesas)

    # --- Otros (manual, siempre local) ---
    otros = ms.entries_in_range("otros", start, end)
    total_otros = sum(o["monto"] for o in otros)

    total_general = total_level_up + total_clases_usd + total_remesas + total_otros

    abierto = st.session_state.get("cf_detalle")
    cajas = [
        ("levelup", "🎮 Level Up", total_level_up, error_level_up),
        ("clases", "📚 Clases", total_clases_usd, error_clases or error_gastos),
        ("remesas", "💱 Remesas", total_remesas, None),
        ("otros", "🧾 Otros", total_otros, None),
    ]
    for col, (clave, label, total, err) in zip(st.columns(4), cajas):
        with col:
            if card_button(label, total, key=f"cf_{clave}", selected=(abierto == clave)):
                st.session_state["cf_detalle"] = None if abierto == clave else clave
                st.rerun()
            if err:
                st.caption("⚠️ Notion no disponible")

    # Detalle de la caja seleccionada (a todo el ancho del panel)
    if abierto == "levelup":
        st.markdown("**Detalle: 🎮 Level Up**")
        if ventas:
            st.dataframe(pd.DataFrame([{
                "Fecha": _short_date(v["fecha"]),
                "Venta": v["venta"],
                "Utilidad": f"${v['utilidad']:,.2f}",
            } for v in _sort_desc(ventas)]), hide_index=True, use_container_width=True)
            st.caption(f"Total: ${total_level_up:,.2f}")
        else:
            st.caption("Sin ventas en este rango.")
    elif abierto == "clases":
        st.markdown("**Detalle: 📚 Clases Particulares**")
        if clases:
            st.dataframe(pd.DataFrame([{
                "Fecha": _short_date(c["fecha"]),
                "Nombre": c["nombre"],
                "Canal": c["canal"],
                "Valor": (f"{c['valor_clp']:,.0f} CLP" if c["canal"] in CANALES_CLP
                          else f"${c['valor_usd']:,.2f}"),
                "Valor USD": f"${c['valor_usd_resuelto']:,.2f}",
            } for c in _sort_desc(clases)]), hide_index=True, use_container_width=True)
            st.caption(f"Total ingresos: ${total_clases_ingresos:,.2f}")
        else:
            st.caption("Sin clases en este rango.")
        st.markdown("**🧾 Gastos Operativos**")
        if gastos:
            st.dataframe(pd.DataFrame([{
                "Fecha": _short_date(g["fecha"]),
                "Item": g["item"],
                "Monto": (f"${g['monto_usd']:,.2f}" if g["monto_usd"]
                          else f"{g['monto_clp']:,.0f} CLP"),
                "Monto USD": f"${g['monto_usd_resuelto']:,.2f}",
            } for g in _sort_desc(gastos)]), hide_index=True, use_container_width=True)
            st.caption(f"Total gastos: ${total_gastos:,.2f}")
        else:
            st.caption("Sin gastos en este rango.")
        st.caption(f"**Utilidad neta Clases (Ingresos − Gastos): ${total_clases_usd:,.2f}**")
    elif abierto == "remesas":
        st.markdown("**Detalle: 💱 Cambios y Remesas**")
        if remesas:
            st.dataframe(pd.DataFrame([{
                "Fecha": _short_date(r["fecha"]),
                "Nombre": r["nombre"],
                "Monto": f"${r['monto']:,.2f}",
            } for r in _sort_desc(remesas)]), hide_index=True, use_container_width=True)
            st.caption(f"Total: ${total_remesas:,.2f}")
        else:
            st.caption("Sin remesas en este rango.")
    elif abierto == "otros":
        st.markdown("**Detalle: 🧾 Otros**")
        if otros:
            st.dataframe(pd.DataFrame([{
                "Fecha": _short_date(o["fecha"]),
                "Nota": o.get("nota", ""),
                "Monto": f"${o['monto']:,.2f}",
            } for o in _sort_desc(otros)]), hide_index=True, use_container_width=True)
            st.caption(f"Total: ${total_otros:,.2f}")
        else:
            st.caption("Sin entradas en este rango.")

    st.markdown("---")
    st.metric("Total Flujo de Caja", f"${total_general:,.0f}")

    # --- Gráfico de torta ---
    pie_data = pd.DataFrame({
        "Categoría": ["🎮 Level Up", "📚 Clases", "💱 Remesas", "🧾 Otros"],
        "Monto": [total_level_up, total_clases_usd, total_remesas, total_otros],
    })
    pie_data = pie_data[pie_data["Monto"] > 0]
    if not pie_data.empty:
        fig = px.pie(pie_data, names="Categoría", values="Monto", hole=0.45,
                     color="Categoría", color_discrete_map=PIE_COLOR_MAP)
        fig.update_traces(
            textinfo="percent+label",
            hovertemplate="%{label}<br>%{percent}<br>$%{value:,.0f}<extra></extra>",
        )
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#9fd8ff",
            showlegend=False,
            margin=dict(t=10, b=10, l=10, r=10),
            height=280,
        )
        st.plotly_chart(fig, use_container_width=True)

    with st.expander("➕ Agregar entrada manual — Otros"):
        with st.form("form_otros", clear_on_submit=True):
            fc1, fc2, fc3 = st.columns(3)
            f_fecha = fc1.date_input("Fecha", value=today)
            f_monto = fc2.number_input("Monto (USD)", value=0.0, step=1.0)
            f_nota = fc3.text_input("Nota")
            if st.form_submit_button("Guardar"):
                ms.add_entry("otros", f_fecha, f_monto, "USD", f_nota)
                st.success("Entrada guardada.")
                st.rerun()

        entries = ms.get_entries("otros")
        if entries:
            st.write("Entradas registradas:")
            for i, e in enumerate(entries):
                ec1, ec2 = st.columns([5, 1])
                ec1.write(f"{e['fecha']} — ${e['monto']:,.2f} — {e['nota']}")
                if ec2.button("🗑️", key=f"del_otros_{i}"):
                    ms.delete_entry("otros", i)
                    st.rerun()

    if remesas_source != "notion":
        with st.expander("➕ Agregar entrada manual — Remesas"):
            st.caption("REMESAS_DS no configurado: guardando localmente.")
            with st.form("form_remesas", clear_on_submit=True):
                fc1, fc2, fc3 = st.columns(3)
                f_fecha = fc1.date_input("Fecha", value=today, key="rem_fecha")
                f_monto = fc2.number_input("Monto (USD)", value=0.0, step=1.0, key="rem_monto")
                f_nota = fc3.text_input("Nota", key="rem_nota")
                if st.form_submit_button("Guardar"):
                    ms.add_entry("remesas", f_fecha, f_monto, "USD", f_nota)
                    st.success("Entrada guardada.")
                    st.rerun()
