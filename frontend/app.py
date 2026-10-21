"""
Streamlit client for the Multi-model AI Server (Part 6) - the final project UI.

This app is only a CLIENT: it calls the local FastAPI server, which loads the models
locally and runs inference on the machine. No remote inference API is used.

This UI focuses on OCR (the main use case). The backend still exposes the classification
and detection endpoints - they are simply not surfaced here; call them directly from
Swagger UI (<http://127.0.0.1:8000/docs>).

Run the server first:
    uvicorn main:app --reload --port 8000
Then this UI:
    streamlit run app.py
"""

from __future__ import annotations

import io
import os

import requests
import streamlit as st
from PIL import Image, ImageDraw

# ---------------------------------------------------------------------------
# Page + styling
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Multi-model AI Server", page_icon="🧠", layout="wide")

CSS = """
<style>
:root {
  --accent: #5b8cff; --accent2: #22d3ee; --card: #131a2b; --line: #263149; --muted: #97a3c2;
}
.block-container { padding-top: 1.6rem; padding-bottom: 3rem; }
.hero {
  background: linear-gradient(120deg, #16224a 0%, #0e1730 60%);
  border: 1px solid var(--line); border-radius: 18px; padding: 26px 30px; margin-bottom: 18px;
}
.hero h1 { margin: 0; font-size: 30px; color: #eef2ff; letter-spacing: .2px; }
.hero p  { margin: 6px 0 0; color: var(--muted); font-size: 15px; }
.chip {
  display: inline-block; padding: 4px 12px; border-radius: 999px; font-size: 12.5px;
  border: 1px solid var(--line); color: var(--muted); margin-right: 6px; margin-top: 8px;
}
.chip.on  { color: #34d399; border-color: #1f6b4d; }
.chip.warn{ color: #fbbf24; border-color: #7a5a12; }
.chip.off { color: #f87171; border-color: #7f2b2b; }
.metric {
  background: var(--card); border: 1px solid var(--line); border-radius: 14px;
  padding: 14px 16px; text-align: center;
}
.metric .v { font-size: 22px; font-weight: 800; color: #eef2ff; }
.metric .k { font-size: 12px; color: var(--muted); text-transform: uppercase; letter-spacing: .06em; }
.stButton>button { border-radius: 10px; font-weight: 700; }
</style>
"""

st.markdown(CSS, unsafe_allow_html=True)

DEFAULT_BACKEND_URL = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000")

SAMPLES = {
    "Invoice 1 (AWS GST)": "https://imgv2-2-f.scribdassets.com/img/document/558034587/original/cf20b8ea94/1?v=1",
    "Invoice 2 (small)": (
        "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcS5YP2LMDSFPIh2c36w9MILmGcfO5vAletMNbkBD0OqBtCciXk7c11yG5Ba&s=10"
    ),
    "Invoice 3 (cloudfront)": (
        "https://d2czqxs5dso3qv.cloudfront.net/images/85f1e89b-dea6-4c9c-aa6e-9051527a67f8.png"
    ),
}


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------
def backend_url() -> str:
    return st.session_state.get("backend_url", DEFAULT_BACKEND_URL).rstrip("/")


def api_get(path: str):
    try:
        r = requests.get(backend_url() + path, timeout=15)
        r.raise_for_status()
        return r.json(), None
    except Exception as exc:  # noqa: BLE001
        return None, str(exc)


def api_post_file(path: str, filename: str, content: bytes, data: dict):
    try:
        r = requests.post(
            backend_url() + path,
            files={"file": (filename, content, "image/png")},
            data=data,
            timeout=600,
        )
        return r.status_code, r.json()
    except Exception as exc:  # noqa: BLE001
        return None, {"error": {"code": "CONNECTION", "message": str(exc)}}


def download_image(url: str):
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
    r.raise_for_status()
    return r.content


# ---------------------------------------------------------------------------
# Sidebar: connection + controls
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### ⚙️ Control panel")
    st.text_input("Backend URL", value=DEFAULT_BACKEND_URL, key="backend_url")

    health, err = api_get("/health")
    if health:
        st.markdown(
            f'<span class="chip on">● connected</span>'
            f'<span class="chip">device: {health["device"]}</span>'
            f'<span class="chip {"warn" if health["mock"] else "on"}">'
            f'{"MOCK mode" if health["mock"] else "real models"}</span>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown('<span class="chip off">● offline</span>', unsafe_allow_html=True)
        st.caption(f"Start the server: `uvicorn main:app --port 8000`\n\n{err}")

    devices_payload, _ = api_get("/devices")
    device_options = (devices_payload or {}).get("devices", ["cpu"])
    device = st.selectbox("Compute device", device_options, index=0, help="CPU or GPU (cuda)")

    ocr_models, _ = api_get("/ocr/models")
    ocr_models = ocr_models or []
    usable = [m for m in ocr_models if device in m["devices"]]
    model_names = [m["name"] for m in usable]
    default_index = model_names.index("rapidocr") if "rapidocr" in model_names else 0
    ocr_model = st.selectbox(
        "OCR model",
        model_names or ["<none available>"],
        index=default_index,
        help="Models incompatible with the selected device are hidden.",
    )
    if ocr_model and ocr_model != "<none available>":
        spec = next((m for m in usable if m["name"] == ocr_model), None)
        if spec:
            st.caption(spec["description"])

    st.divider()
    st.markdown("### 🧩 Loaded models")
    status, _ = api_get("/models")
    if status:
        for m in status["models"]:
            state = ", ".join(m["loaded_on"]) if m["loaded_on"] else "—"
            st.markdown(
                f'<span class="chip {"on" if m["loaded"] else ""}">{m["name"]}: {state}</span>',
                unsafe_allow_html=True,
            )
        if st.button("Unload all models", use_container_width=True):
            for m in status["models"]:
                if m["loaded"]:
                    requests.post(backend_url() + f"/models/{m['name']}/unload", timeout=30)
            st.toast("Released all models")
            st.rerun()
    else:
        st.caption("Server not reachable.")


# ---------------------------------------------------------------------------
# Hero header
# ---------------------------------------------------------------------------
mock_chip = (
    f'<span class="chip {"warn" if (health or {}).get("mock") else "on"}">'
    f'{"mock" if (health or {}).get("mock") else "live"}</span>'
)
st.markdown(
    f"""
    <div class="hero">
      <h1>🧠 Multi-model AI Server</h1>
      <p>FastAPI backend serving a <b>lightweight OCR</b> stack, loaded and executed locally.
      Pick a device, upload an invoice, read the recognized text. Classification and detection
      remain available on the API (see <code>/docs</code>).</p>
      <div>
        <span class="chip {'on' if health else 'off'}">{'● server online' if health else '● server offline'}</span>
        <span class="chip">engine: OCR · {device}</span>
        {mock_chip}
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# OCR
# ---------------------------------------------------------------------------
left, right = st.columns([1.05, 1.2], gap="large")

with left:
    st.markdown("#### 1. Choose an image")
    uploaded = st.file_uploader("Upload an invoice / document", type=["png", "jpg", "jpeg", "bmp", "webp"])

    st.caption("…or load a sample invoice:")
    cols = st.columns(len(SAMPLES))
    for col, (label, url) in zip(cols, SAMPLES.items()):
        if col.button(label, use_container_width=True):
            try:
                st.session_state["ocr_bytes"] = download_image(url)
                st.session_state["ocr_name"] = label
                st.toast(f"Loaded {label}")
            except Exception as exc:  # noqa: BLE001
                st.error(f"Could not download sample: {exc}")

    if uploaded is not None:
        st.session_state["ocr_bytes"] = uploaded.getvalue()
        st.session_state["ocr_name"] = uploaded.name

    image_bytes = st.session_state.get("ocr_bytes")
    if image_bytes:
        st.image(image_bytes, caption=st.session_state.get("ocr_name", "image"), use_container_width=True)

    run = st.button("🚀  Run OCR", type="primary", use_container_width=True,
                    disabled=not (image_bytes and ocr_model and ocr_model != "<none available>"))

with right:
    st.markdown("#### 2. Results")
    if run:
        with st.spinner("Running OCR on the local server… (first run may load the model)"):
            code, payload = api_post_file(
                "/ocr/upload",
                st.session_state.get("ocr_name", "image.png"),
                image_bytes,
                {"model": ocr_model, "device": device},
            )

        if code != 200:
            st.error(f"HTTP {code} — {(payload or {}).get('error', {}).get('message', 'Request failed')}")
            if isinstance(payload, dict) and "error" in payload:
                st.json(payload["error"])
        else:
            st.session_state["ocr_result"] = payload

    result = st.session_state.get("ocr_result")
    if not result:
        st.info("Upload or pick an image, then press **Run OCR**.")
    else:
        m1, m2, m3, m4 = st.columns(4)
        for col, key, val in (
            (m1, "model", result["model"]),
            (m2, "engine", result["engine"]),
            (m3, "device", result["device"]),
            (m4, "time", f'{result["elapsed_ms"]:.0f} ms'),
        ):
            col.markdown(f'<div class="metric"><div class="v">{val}</div><div class="k">{key}</div></div>',
                         unsafe_allow_html=True)

        if result.get("items"):
            annotated = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            draw = ImageDraw.Draw(annotated)
            for item in result["items"]:
                pts = [tuple(p) for p in item["box"]]
                draw.polygon(pts, outline=(34, 211, 238), width=2)
            st.image(annotated, caption="Detected text regions", use_container_width=True)

        st.markdown("##### Extracted text")
        st.code(result.get("text") or "(no text)", language="text")
        st.download_button("⬇️  Download text", result.get("text") or "", file_name="ocr.txt")

        if result.get("items"):
            st.markdown("##### Text items")
            st.dataframe(
                [{"text": i["text"], "score": round(i["score"], 3)} for i in result["items"]],
                use_container_width=True,
                hide_index=True,
            )
        if result.get("lines"):
            st.markdown("##### Lines")
            st.dataframe(
                [{"#": n + 1, "text": t} for n, t in enumerate(result["lines"])],
                use_container_width=True,
                hide_index=True,
            )

st.caption("All models run locally on this machine · built with FastAPI + Streamlit")
