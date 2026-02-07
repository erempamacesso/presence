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

/* CONTAINER PRINCIPAL */
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

/* ESCONDE HEADER / MENU */
header, footer, #MainMenu {
    display: none !important;
}

/* TÍTULO */
.titulo {
    color: white;
    font-size: 22px;
    font-weight: bold;
    margin: 12px 0;
    text-align: center;
}

/* ÁREA DA CÂMERA */
div[data-testid="stCameraInput"] {
    width: 100vw !important;
    margin: 0 !important;
    padding: 0 !important;
    display: flex;
    justify-content: center;
    background: black;
}

/* CONTAINER INTERNO */
div[data-testid="stCameraInput"] > div {
    width: 100% !important;
    max-width: 480px !important;
}

/* VÍDEO / FOTO */
div[data-testid="stCameraInput"] video,
div[data-testid="stCameraInput"] img {
    width: 100% !important;
    height: auto !important;
    max-height: 65vh !important;
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

.overlay.sucesso { background: #2ecc71; }
.overlay.erro { background: #e74c3c; }

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
st.markdown('<div class="titulo">Aproxime o rosto e toque no botão</div>', unsafe_allow_html=True)

# CÂMERA
foto = st.camera_input("", label_visibility="hidden")

# ===============================
# PROCESSAMENTO (SIMULADO)
# ===============================
if foto is not None and st.session_state.status is None:
    # 👉 AQUI entra seu reconhecimento facial real
    reconhecimento_ok = True  # simulação

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
