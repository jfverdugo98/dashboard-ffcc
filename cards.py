"""Cajas clicables (estilo neón): al pasar el cursor se vuelven rosa neón y
al hacer click abren/cierran su detalle. El estilo vive en CARDS_CSS
(inyectado desde app.py) y se engancha por el prefijo de la key:
cb_<color>_... = caja normal, cbon_<color>_... = caja seleccionada."""
import streamlit as st

CARDS_CSS = """
<style>
[class*="st-key-cb_"] button, [class*="st-key-cbon_"] button {
    --c: #00d4ff;
    width: 100%; height: auto; min-height: 84px;
    display: block; text-align: left;
    padding: 12px 14px;
    border-radius: 14px;
    border: 1px solid color-mix(in srgb, var(--c) 35%, transparent);
    background: linear-gradient(145deg, color-mix(in srgb, var(--c) 8%, transparent), transparent);
    box-shadow: 0 0 18px color-mix(in srgb, var(--c) 10%, transparent);
    transition: all .25s ease;
    cursor: pointer;
}
[class*="st-key-cb_orange"] button, [class*="st-key-cbon_orange"] button { --c: #ffa500; }
[class*="st-key-cb_"] button p, [class*="st-key-cbon_"] button p {
    display: block; margin: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
[class*="st-key-cb_"] button p:first-child, [class*="st-key-cbon_"] button p:first-child {
    color: #9fd8ff; font-size: 0.8rem; font-weight: 400;
}
[class*="st-key-cb_"] button p:last-child, [class*="st-key-cbon_"] button p:last-child {
    color: var(--c); font-family: 'SF Mono','Courier New',monospace;
    font-size: 1.05rem; font-weight: 700; margin-top: 4px;
}
[class*="st-key-cb_"] button > div, [class*="st-key-cbon_"] button > div,
[class*="st-key-cb_"] button span, [class*="st-key-cbon_"] button span,
[class*="st-key-cb_"] button [data-testid="stMarkdownContainer"],
[class*="st-key-cbon_"] button [data-testid="stMarkdownContainer"] {
    display: block !important; width: 100%; text-align: left; justify-content: flex-start;
}
/* hover y seleccionada: rosa neón */
[class*="st-key-cb_"] button:hover, [class*="st-key-cbon_"] button,
[class*="st-key-cb_"] button:focus-visible {
    border-color: #ff00aa;
    background: linear-gradient(145deg, rgba(255,0,170,0.18), rgba(255,0,170,0.03));
    box-shadow: 0 0 24px rgba(255,0,170,0.45);
    transform: translateY(-2px);
}
[class*="st-key-cb_"] button:hover p:last-child, [class*="st-key-cbon_"] button p:last-child,
[class*="st-key-cb_"] button:focus-visible p:last-child {
    color: #ff4dc4; text-shadow: 0 0 10px rgba(255,0,170,0.6);
}
</style>
"""


def card_button(label, value, key, color="blue", selected=False):
    """Dibuja una caja clicable; devuelve True si se hizo click."""
    prefix = "cbon" if selected else "cb"
    text = f"{label}\n\n\\${value:,.0f}"
    return st.button(text, key=f"{prefix}_{color}_{key}", use_container_width=True)
