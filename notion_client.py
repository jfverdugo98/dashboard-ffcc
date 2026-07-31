"""Cliente delgado para leer datos financieros desde Notion.

Usa la API 2025-09-03 (modelo de "data sources"): cada base de Notion
puede exponer varias vistas/fuentes internas, y se consulta cada una
por su data_source_id (no el database_id de la URL).
"""
import streamlit as st
import requests
from datetime import date

NOTION_VERSION = "2025-09-03"
BASE_URL = "https://api.notion.com/v1"


def _headers():
    return {
        "Authorization": f"Bearer {st.secrets['NOTION_TOKEN']}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def _query_all(data_source_id, filter_payload=None):
    """Pagina sobre /data_sources/{id}/query y devuelve todas las filas."""
    results = []
    payload = {"page_size": 100}
    if filter_payload:
        payload["filter"] = filter_payload

    cursor = None
    while True:
        if cursor:
            payload["start_cursor"] = cursor
        resp = requests.post(
            f"{BASE_URL}/data_sources/{data_source_id}/query",
            headers=_headers(),
            json=payload,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        results.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")
    return results


def _prop_number(props, name):
    val = props.get(name, {})
    t = val.get("type")
    if t == "number":
        return val.get("number") or 0
    if t == "formula":
        return val.get("formula", {}).get("number") or 0
    if t == "rollup":
        return val.get("rollup", {}).get("number") or 0
    return 0


def _prop_date(props, name):
    val = props.get(name, {}).get("date")
    if not val:
        return None
    return val.get("start")


def _prop_title(props, name):
    title = props.get(name, {}).get("title", [])
    return title[0]["plain_text"] if title else ""


def _prop_select(props, name):
    sel = props.get(name, {}).get("select")
    return sel["name"] if sel else None


def _date_range_filter(date_property, start: date, end: date):
    return {
        "and": [
            {"property": date_property, "date": {"on_or_after": start.isoformat()}},
            {"property": date_property, "date": {"on_or_before": end.isoformat()}},
        ]
    }


@st.cache_data(ttl=300, show_spinner=False)
def get_level_up_ventas(start: date, end: date):
    """Ventas de Level Up en el rango de fechas. Retorna lista de dicts."""
    ds_id = st.secrets["LEVEL_UP_VENTAS_DS"]
    rows = _query_all(ds_id, _date_range_filter("Fecha de venta", start, end))
    out = []
    for r in rows:
        p = r["properties"]
        out.append({
            "fecha": _prop_date(p, "Fecha de venta"),
            "venta": _prop_title(p, "Venta"),
            "precio_venta": _prop_number(p, "Precio venta"),
            "comision": _prop_number(p, "Comision"),
            "utilidad": _prop_number(p, "Utilidad "),
        })
    return out


@st.cache_data(ttl=300, show_spinner=False)
def get_clases(start: date, end: date):
    """Clases particulares y asesorías en el rango de fechas.

    Cada fila trae Valor (CLP) y Valor USD por separado -- son
    mutuamente excluyentes según el canal: Superprof.cl/Tus Clases
    cobran en CLP, Preply/Superprof.com en USD."""
    ds_id = st.secrets["CLASES_DS"]
    rows = _query_all(ds_id, _date_range_filter("Fecha", start, end))
    out = []
    for r in rows:
        p = r["properties"]
        out.append({
            "fecha": _prop_date(p, "Fecha"),
            "nombre": _prop_title(p, "Nombre"),
            "valor_clp": _prop_number(p, "Valor"),
            "valor_usd": _prop_number(p, "Valor USD"),
            "canal": _prop_select(p, "Canal"),
        })
    return out


@st.cache_data(ttl=300, show_spinner=False)
def get_gastos_operativos(start: date, end: date):
    """Gastos operativos asociados a clases particulares. Monto (CLP) y
    Monto USD son mutuamente excluyentes según cómo se pagó el gasto."""
    ds_id = st.secrets["GASTOS_OPERATIVOS_DS"]
    rows = _query_all(ds_id, _date_range_filter("Fecha", start, end))
    out = []
    for r in rows:
        p = r["properties"]
        out.append({
            "fecha": _prop_date(p, "Fecha"),
            "item": _prop_title(p, "Item"),
            "monto_clp": _prop_number(p, "Monto"),
            "monto_usd": _prop_number(p, "Monto USD"),
        })
    return out


@st.cache_data(ttl=300, show_spinner=False)
def get_level_up_inventario_activo():
    """Costo total del inventario de Level Up que aún no se ha vendido
    (activo no corriente para el Estado de Situación)."""
    ds_id = st.secrets["LEVEL_UP_INVENTARIO_DS"]
    rows = _query_all(ds_id)
    total = 0
    for r in rows:
        p = r["properties"]
        estado = p.get("Estado", {}).get("status", {})
        estado_nombre = estado.get("name") if estado else None
        if estado_nombre != "Vendido":
            total += _prop_number(p, "Costo total")
    return total


@st.cache_data(ttl=300, show_spinner=False)
def get_remesas(start: date, end: date):
    """Remesas/cambios registrados en Notion. Los montos siempre están
    en USD. Si REMESAS_DS no está configurado, retorna lista vacía."""
    ds_id = st.secrets.get("REMESAS_DS", "")
    if not ds_id:
        return []
    rows = _query_all(ds_id, _date_range_filter("Fecha", start, end))
    out = []
    for r in rows:
        p = r["properties"]
        out.append({
            "fecha": _prop_date(p, "Fecha"),
            "nombre": _prop_title(p, "Nombre"),
            "monto": _prop_number(p, "Monto"),
        })
    return out


def add_remesa(fecha: date, nombre: str, monto: float):
    """Crea una nueva fila en la base de Remesas de Notion (monto en USD)."""
    ds_id = st.secrets.get("REMESAS_DS", "")
    if not ds_id:
        raise ValueError("REMESAS_DS no está configurado en secrets.toml")
    payload = {
        "parent": {"type": "data_source_id", "data_source_id": ds_id},
        "properties": {
            "Nombre": {"title": [{"text": {"content": nombre}}]},
            "Fecha": {"date": {"start": fecha.isoformat()}},
            "Monto": {"number": monto},
        },
    }
    resp = requests.post(f"{BASE_URL}/pages", headers=_headers(), json=payload, timeout=15)
    resp.raise_for_status()
    get_remesas.clear()
    return resp.json()
