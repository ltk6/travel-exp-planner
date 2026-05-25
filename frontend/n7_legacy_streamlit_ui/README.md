# N7 Legacy UI Module (Streamlit — Deprecated)

> [!IMPORTANT]
> N7 (Streamlit UI) is the **legacy frontend** of the project. It has been superseded by **N16 (Next.js Web App)** and is no longer actively maintained.
> The canonical frontend is now located at `frontend/n16_web_ui/`. See the [N16 README](../web/README.md).

N7 was the original Streamlit-based frontend for Travel Experience Planner. It managed the interactive user flow, captured travel preferences through multiple input modes, sent requests to the backend API (N8), and rendered ranked location and activity results in a single-page script-rerun model.

The Streamlit approach had fundamental limitations for this project:

- **Blocking UI**: Every backend call froze the entire interface until the response returned, making it painful for slow AI pipelines (N1 embedding + N4 ranking + N5 LLM generation).
- **No async image loading**: Large Base64 image blobs had to be embedded directly in the API response, causing slow initial renders.
- **No persistent routing**: Each page rerun re-executed the full script. Multi-step flows (questionnaire → results → activity drawer) were awkward to manage.
- **Limited state control**: Session state was fragile and hard to share across conceptual "pages".

These limitations motivated the migration to Next.js (N16).

---

## Entry Point

```python
app.py
```

## Module Structure

```
frontend/n7_legacy_streamlit_ui/
├── app.py          # Main Streamlit app entry point
├── state.py        # Session state initialization helpers
├── styles/         # Custom CSS injected via st.markdown
├── views/          # Input view and result view renderers
└── requirements.txt
```

## Request Behavior

When the user submitted input, N7 sent a `POST` request to:

```text
http://localhost:{API_PORT}/recommend
```

with:

- JSON body from the active input view
- `X-Internal-Key` header for protected API access
- a `60` second request timeout

## State Flow

N7 used Streamlit session state to manage three phases:

1. **Input mode**: show the active input interface and collect a payload
2. **Pending request**: send the payload to N8 and wait for a response
3. **Result mode**: render ranked recommendation results

Main session keys:

| Key | Purpose |
|---|---|
| `mode` | Current phase (`input` / `results`) |
| `payload` | Captured user input ready to send |
| `results` | Ranked locations returned by N8 |
| `activity_results` | Activity lists per location |

## Runtime Notes

- Page layout was configured as `wide`, sidebar starts collapsed
- Styling and view rendering were delegated to `styles/`, `views/`, and `state.py`
- To run the legacy interface: `legacy_run.bat`

---

## Migration to N16

The project frontend is now **N16 — Next.js Web App** (`frontend/n16_web_ui/`).

Key improvements over N7:

| Aspect | N7 Streamlit | N16 Next.js |
|---|---|---|
| UI rendering | Script-rerun (blocking) | React 19 + async |
| Image loading | Embedded Base64 in JSON | Lazy-loaded JPEGs via `/api/images/` |
| State management | `st.session_state` | Zustand store |
| Routing | Single page, no URL changes | App Router (multi-page) |
| Auth & history | Not supported | `/profile` with full auth flow |
| Explore mode | Not supported | `/explore` grid view |

See [frontend/n16_web_ui/README.md](../web/README.md) for the current frontend documentation.
