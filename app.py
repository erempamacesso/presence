import streamlit as st
import time

# ===============================
# CONFIGURAÇÃO DA PÁGINA
# ===============================
st.set_page_config(
    page_title="Registro de Presença",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ===============================
# CSS – MODO TOTEM (CELULAR)
# ===============================

st.markdown("""
<style>

/* RESET TOTAL */
html, body {
    margin: 0;
    padding: 0;
    height: 100%;
    background: black;
    overflow: hidden;
}

.block-container {
    padding: 0 !important;
    margin: 0 !important;
    max-width: 100% !important;
}

/* REMOVE BLOCOS VAZIOS DO STREAMLIT */
div[data-testid="stVerticalBlock"]:empty {
    display: none !important;
    height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
}

/* ESCONDE HEADER */
header, footer, #MainMenu {
    display: none !important;
}

/* CAMERA COLADA NO TOPO */
div[data-testid="stCameraInput"] {
    width: 100vw !important;
    height: 70vh !important;
    margin: 0 !important;
    padding: 0 !important;
    display: flex;
    justify-content: center;
    align-items: center;
    background: black;
}

/* CONTAINER INTERNO */
div[data-testid="stCameraInput"] > div {
    width: 100% !important;
    height: 100% !important;
}

/* VIDEO */
div[data-testid="stCameraInput"] video,
div[data-testid="stCameraInput"] img {
    width: 100% !important;
    height: 100% !important;
    object-fit: cover !important;
}

/* BOTÃO */
div[data-testid="stCameraInput"] button {
    width: 80% !important;
    height: 60px !important;
    margin: 16px auto 0 auto !important;
    display: block !important;

    background: #D32F2F !important;
    border-radius: 30px !important;
    border: 3px solid white !important;

    color: transparent !important;
    position: relative !important;
}

/* TEXTO DO BOTÃO */
div[data-testid="stCameraInput"] button::after {
    content: "REGISTRAR PRESENÇA";
    color: white;
    font-size: 18px;
    font-weight: bold;
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
}

</style>
""", unsafe_allow_html=True)

/* TÍTULO */
.titulo {
    color: white;
    font-size: 22px;
    font-weight: bold;
    margin: 16px 0 8px 0;
    text-align: center;
}

/* CÂMERA */
div[data-testid="stCameraInput"] {
    width: 100%;
    display: flex;
    justify-content: center;
    background: black;
}

div[data-testid="stCameraInput"] > div {
    width: 100% !important;
    max-width: 480px !important;
}

div[data-testid="stCameraInput"] video,
div[data-testid="stCameraInput"] img {
    width: 100% !important;
    height: auto !important;
    max-height: 60vh !important;
    object-fit: cover !important;
}

/* BOTÃO */
div[data-testid="stCameraInput"] button {
    width: 75% !important;
    height: 60px !important;
    margin: 18px auto !important;
    display: block !important;

    background: #D32F2F !important;
    border-radius: 30px !important;
    border: 3px solid white !important;

    color: transparent !important;
    position: relative !important;
}

/* TEXTO DO BOTÃO */
div[data-testid="stCameraInput"] button::after {
    content: "REGISTRAR PRESENÇA";
    color: white;
    font-size: 18px;
    font-weight: bold;
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
}

/* OVERLAY DE FEEDBACK */
.overlay {
    position: fixed;
    inset: 0;
    z-index: 9999;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    color: white;
    font-family: sans-serif;
}

.overlay.sucesso {
    background: #2ecc71;
}

.overlay.erro {
    background: #e74c3c;
}

.icon {
    font-size: 72px;
    margin-bottom: 20px;
}

.msg {
    font-size: 32px;
    font-weight: bold;
    text-align: center;
}

</style>
""", unsafe_allow_html=True)

# ===============================
# ESTADO
# ===============================
if "status" not in st.session_state:
    st.session_state.status = None

# ===============================
# INTERFACE
# ===============================
st.markdown('<div class="app-container">', unsafe_allow_html=True)
st.markdown('<div class="titulo">Aproxime o rosto e toque no botão</div>', unsafe_allow_html=True)

# CÂMERA
foto = st.camera_input("")

# ===============================
# PROCESSAMENTO
# ===============================
if foto is not None and st.session_state.status is None:
    # 👉 AQUI ENTRA SEU RECONHECIMENTO FACIAL REAL
    # Exemplo:
    # resultado = reconhecer_rosto(foto)
    # if resultado == "ok":

    reconhecimento_ok = True  # <-- simulação

    if reconhecimento_ok:
        st.session_state.status = "sucesso"
    else:
        st.session_state.status = "erro"

# ===============================
# OVERLAY DE RESULTADO
# ===============================
if st.session_state.status == "sucesso":
    st.markdown("""
    <div class="overlay sucesso">
        <div class="icon">✅</div>
        <div class="msg">PRESENÇA<br>REGISTRADA</div>
    </div>
    """, unsafe_allow_html=True)

    time.sleep(2)
    st.session_state.status = None
    st.experimental_rerun()

elif st.session_state.status == "erro":
    st.markdown("""
    <div class="overlay erro">
        <div class="icon">❌</div>
        <div class="msg">ROSTO NÃO<br>RECONHECIDO</div>
    </div>
    """, unsafe_allow_html=True)

    time.sleep(2)
    st.session_state.status = None
    st.experimental_rerun()

st.markdown('</div>', unsafe_allow_html=True)

