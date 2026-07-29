"""Pestaña Flujo de Caja: Level Up, Clases, Remesas y Otros."""
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, datetime
import calendar

import notion_client as nc
import manual_store as ms

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


def _short_date(iso_str):
    if not iso_str:
        return ""
    d = datetime.strptime(iso_str[:10], "%Y-%m-%d")
    return d.strftime("%d/%m")


def render_cashflow(tasa_clp: float):
    st.subheader("💰 Flujo de Caja")

    today = date.today()
    default_start, default_end = _month_bounds(today)
    c1, c2 = st.columns(2)
    start = c1.date_input("Desde", value=default_start, key="cf_start")
    end = c2.date_input("Hasta", value=default_end, key="cf_end")

    if start > end:
        st.error("El rango de fechas es inválido (Desde > Hasta).")
        return

    st.caption(_period_label(start, end))

    # --- Level Up (Notion, USD) -- usa Utilidad, no Precio venta ---
    try:
        ventas = nc.get_level_up_ventas(start, end)
        total_level_up = sum(v["utilidad"] for v in ventas)
        error_level_up = None
    except Exception as e:
        ventas, total_level_up, error_level_up = [], 0, str(e)

    # --- Clases particulares (Notion, CLP -> USD) ---
    try:
        clases = nc.get_clases(start, end)
        total_clases_clp = sum(c["valor"] for c in clases)
        total_clases_usd = total_clases_clp / tasa_clp if tasa_clp else 0
        error_clases = None
    except Exception as e:
        clases, total_clases_usd, error_clases = [], 0, str(e)

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

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("🎮 Level Up", f"${total_level_up:,.0f}")
        if error_level_up:
            st.caption("⚠️ Notion no disponible")
    with m2:
        st.metric("📚 Clases", f"${total_clases_usd:,.0f}")
        if error_clases:
            st.caption("⚠️ Notion no disponible")
    with m3:
        st.metric("💱 Remesas", f"${total_remesas:,.0f}")
    with m4:
        st.metric("🧾 Otros", f"${total_otros:,.0f}")

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

    with st.expander("📋 Detalle de transacciones del período"):
        st.write("**🎮 Level Up**")
        if ventas:
            df = pd.DataFrame([{
                "Fecha": _short_date(v["fecha"]),
                "Venta": v["venta"],
                "Utilidad": f"${v['utilidad']:,.2f}",
            } for v in ventas])
            st.dataframe(df, hide_index=True, use_container_width=True)
        else:
            st.caption("Sin ventas en este rango.")

        st.write("**📚 Clases Particulares**")
        if clases:
            df = pd.DataFrame([{
                "Fecha": _short_date(c["fecha"]),
                "Nombre": c["nombre"],
                "Valor CLP": f"{c['valor']:,.0f}",
                "Valor USD": f"${(c['valor'] / tasa_clp if tasa_clp else 0):,.0f}",
                "Canal": c["canal"],
            } for c in clases])
            st.dataframe(df, hide_index=True, use_container_width=True)
        else:
            st.caption("Sin clases en este rango.")

        st.write("**💱 Cambios y Remesas**")
        if remesas:
            df = pd.DataFrame([{
                "Fecha": _short_date(r["fecha"]),
                "Nombre": r["nombre"],
                "Monto": f"${r['monto']:,.2f}",
            } for r in remesas])
            st.dataframe(df, hide_index=True, use_container_width=True)
        else:
            st.caption("Sin remesas en este rango.")
