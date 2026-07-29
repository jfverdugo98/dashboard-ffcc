"""Almacén simple en JSON para categorías sin automatización (Otros,
y Remesas mientras no exista su base en Notion).

Nota: en Streamlit Community Cloud este archivo vive en el filesystem
efímero del contenedor -- sobrevive reinicios normales de la app pero
se pierde si se hace un redeploy. Para persistencia robusta, migrar
la categoría a una base de Notion (como se hará con Remesas).
"""
import json
import os
from datetime import date

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
DATA_FILE = os.path.join(DATA_DIR, "manual_entries.json")


def _load_all():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        return json.load(f)


def _save_all(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2, default=str)


def get_entries(category: str):
    return _load_all().get(category, [])


def add_entry(category: str, fecha: date, monto: float, moneda: str, nota: str = ""):
    data = _load_all()
    data.setdefault(category, []).append({
        "fecha": fecha.isoformat(),
        "monto": monto,
        "moneda": moneda,
        "nota": nota,
    })
    _save_all(data)


def delete_entry(category: str, index: int):
    data = _load_all()
    entries = data.get(category, [])
    if 0 <= index < len(entries):
        entries.pop(index)
        _save_all(data)


def entries_in_range(category: str, start: date, end: date):
    out = []
    for e in get_entries(category):
        f = date.fromisoformat(e["fecha"])
        if start <= f <= end:
            out.append(e)
    return out
