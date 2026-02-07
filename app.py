import streamlit as st
import time

# ==================================================
# CONFIGURAÇÃO DA PÁGINA
# ==================================================
st.set_page_config(
    page_title="Registro de Presença",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ==================================================
# CSS – LAYOUT TOTEM LIMPO
# ==================================================
st.markdown("""
<style>

/* RESET */
html, body {
    margin: 0;
    padding: 0;
    background: black;
    overflow: hidden;
}

.block-container {
    padding: 0 !important;
    margin: 0 !important;
    max-width: 100% !important;
}

header, footer, #MainMenu {
    display: none !important;
}

/* TÍTULO */
.titulo {
    color: white;
    font-size: 20px;
    font-weight: bold;
    text-align: center;
    margin: 10px 0;
}

/* CAMERA */
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
    max-height: 60vh !important;
    object-fit: cover !important;
}

/* BOTÃO (NORMAL, SEM FLUTUAR) */
div[data-testid="stCameraInput"] button {
    width: 80% !important;
    height: 60px !important;
    margin: 16px auto !important;
    display: block !important;

    background: #D32F2F !important;
    border-radius: 30px !important;
    border: 3px solid white !important;

    color: transparent !important;
    position: relative !important;
}

/* TEXTO BOTÃO */
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

/* TARJA DE STATUS */
.status-bar {
    width: 100%;
    padding: 14px;
    text-align: center;
    font-size: 20px;
    font-weight: bold;
    color: white;
}

.status-verde { background: #2ecc71; }
.status-amarelo { background: #f1c40f; color: #333; }
.status-vermelho { background: #e74c3c; }

</style>
""", unsafe_allow_html=True)

# ==================================================
# ESTADO
# ==================================================
if "status" not in st.session_state:
    st.session_state.status = None

# ==================================================
# INTERFACE
# ==================================================
st.markdown('<div class="titulo">Aproxime o rosto e toque no botão</div>', unsafe_allow_html=True)

foto = st.camera_input("", label_visibility="hidden")

# ==================================================
# PROCESSAMENTO (SIMULAÇÃO)
# ==================================================
if foto is not None and st.session_state.status is None:
    """
    Aqui você substitui pela sua lógica real:
    resultado = reconhecer_rosto(foto)
    """

    # SIMULAÇÃO
    resultado = "novo"  
    # opções: "novo", "duplicado", "erro"

    st.session_state.status = resultado

# ==================================================
# TARJA DE FEEDBACK
# ==================================================
if st.session_state.status == "novo":
    st.markdown("""
    <div class="status-bar status-verde">
        ✅ ACESSO REGISTRADO
    </div>
    """, unsafe_allow_html=True)
    time.sleep(2)

elif st.session_state.status == "duplicado":
    st.markdown("""
    <div class="status-bar status-amarelo">
        ⚠️ FREQUÊNCIA JÁ REGISTRADA
    </div>
    """, unsafe_allow_html=True)
    time.sleep(2)

elif st.session_state.status == "erro":
    st.markdown("""
    <div class="status-bar status-vermelho">
        ❌ NÃO CADASTRADO
    </div>
    """, unsafe_allow_html=True)
    time.sleep(2)

# ==================================================
# RESET
# ==================================================
if st.session_state.status is not None:
    st.session_state.status = None
    st.experimental_rerun()
