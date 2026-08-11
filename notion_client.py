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


def _prop_relation_ids(props, name):
    rel = props.get(name, {}).get("relation", [])
    return [r["id"] for r in rel]


def _date_range_filter(date_property, start: date, end: date):
    return {
        "and": [
            {"property": date_property, "date": {"on_or_after": start.isoformat()}},
            {"property": date_property, "date": {"on_or_before": end.isoformat()}},
        ]
    }


def _get_item_costs(item_ids):
    """Costo total real de cada ítem de inventario, leído directo de la
    página del ítem (no vía el rollup 'Costo Inventario' de la venta,
    que puede quedar desactualizado en Notion tras editar el ítem --
    es un rollup de 3 niveles y la API a veces devuelve el valor stale)."""
    costs = {}
    for item_id in item_ids:
        resp = requests.get(f"{BASE_URL}/pages/{item_id}", headers=_headers(), timeout=15)
        resp.raise_for_status()
        costs[item_id] = _prop_number(resp.json()["properties"], "Costo total")
    return costs


@st.cache_data(ttl=300, show_spinner=False)
def get_level_up_ventas(start: date, end: date):
    """Ventas de Level Up en el rango de fechas. Retorna lista de dicts.

    La Utilidad se recalcula aquí (precio_venta - comision - costo real
    de los artículos vinculados) en vez de leer el campo 'Utilidad' de
    Notion, que depende de un rollup de fórmulas anidadas propenso a
    quedar desactualizado."""
    ds_id = st.secrets["LEVEL_UP_VENTAS_DS"]
    rows = _query_all(ds_id, _date_range_filter("Fecha de venta", start, end))

    parsed = []
    all_item_ids = set()
    for r in rows:
        p = r["properties"]
        item_ids = _prop_relation_ids(p, "Inventario (Artículos)")
        all_item_ids.update(item_ids)
        parsed.append({
            "fecha": _prop_date(p, "Fecha de venta"),
            "venta": _prop_title(p, "Venta"),
            "precio_venta": _prop_number(p, "Precio venta"),
            "comision": _prop_number(p, "Comision"),
            "item_ids": item_ids,
        })

    costos = _get_item_costs(all_item_ids)

    out = []
    for row in parsed:
        costo_inventario = sum(costos.get(i, 0) for i in row["item_ids"])
        out.append({
            "fecha": row["fecha"],
            "venta": row["venta"],
            "precio_venta": row["precio_venta"],
            "comision": row["comision"],
            "costo_inventario": costo_inventario,
            "utilidad": row["precio_venta"] - row["comision"] - costo_inventario,
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


_MONEDAS_CONOCIDAS = {"USD": "USD", "USDT": "USD", "COP": "COP", "CLP": "CLP", "BTC": "BTC"}


def _parse_moneda(item_title: str):
    """La moneda va como prefijo del nombre del item (ej. 'CLP BICE').
    Si no hay prefijo reconocido, se asume USD."""
    primera_palabra = item_title.strip().split(" ")[0].upper() if item_title.strip() else ""
    return _MONEDAS_CONOCIDAS.get(primera_palabra, "USD")


@st.cache_data(ttl=300, show_spinner=False)
def get_balance_items():
    """Ítems del Estado de Situación (Balance General) desde Notion.
    Categoría: Activo/Pasivo. Liquidez: Corriente/No Corriente (activos)
    o Circulante/No Circulante (pasivos). La moneda se infiere del
    prefijo del nombre del item (USD si no hay prefijo reconocido)."""
    ds_id = st.secrets["BALANCE_GENERAL_DS"]
    rows = _query_all(ds_id)
    out = []
    for r in rows:
        p = r["properties"]
        item = _prop_title(p, "Item")
        out.append({
            "item": item,
            "categoria": _prop_select(p, "Categoría"),
            "liquidez": _prop_select(p, "Liquidez"),
            "monto": _prop_number(p, "Monto"),
            "moneda": _parse_moneda(item),
        })
    return out


def add_balance_item(item: str, categoria: str, liquidez: str, monto: float):
    """Crea un nuevo ítem en la base de Balance General de Notion.
    El nombre del item debe empezar con el prefijo de moneda (USD/COP/
    CLP/BTC) si no es USD, ej. 'CLP Cuenta Ahorro'."""
    ds_id = st.secrets["BALANCE_GENERAL_DS"]
    payload = {
        "parent": {"type": "data_source_id", "data_source_id": ds_id},
        "properties": {
            "Item": {"title": [{"text": {"content": item}}]},
            "Categoría": {"select": {"name": categoria}},
            "Liquidez": {"select": {"name": liquidez}},
            "Monto": {"number": monto},
        },
    }
    resp = requests.post(f"{BASE_URL}/pages", headers=_headers(), json=payload, timeout=15)
    resp.raise_for_status()
    get_balance_items.clear()
    return resp.json()
