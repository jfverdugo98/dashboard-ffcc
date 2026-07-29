# Dashboard Financiero ⚡

Dashboard en Streamlit con dos secciones:

- **Flujo de Caja** — Level Up y Clases particulares automatizados desde Notion,
  Remesas desde Notion, y Otros manual.
- **Estado de Situación** — activos/pasivos con tasas de cambio en tiempo real
  (yfinance) e inventario de Level Up automatizado desde Notion.

## Correr localmente

```bash
pip install -r requirements.txt
streamlit run app.py
```

Necesitas `.streamlit/secrets.toml` con tu `NOTION_TOKEN` y los `*_DS` IDs
(ver `secrets.toml.example`). Ese archivo nunca se sube a git.

## Deploy a Streamlit Community Cloud

1. Sube este repo a GitHub (puede ser privado).
2. Entra a [share.streamlit.io](https://share.streamlit.io) con tu cuenta y
   elige "New app" → selecciona el repo, branch `main`, archivo `app.py`.
3. En **Advanced settings → Secrets**, pega el contenido de tu
   `secrets.toml` local (NOTION_TOKEN y los DS IDs).
4. Deploy. La URL queda fija — ábrela desde Safari en el iPhone y usa
   "Compartir → Agregar a inicio" para que se sienta como app nativa.
