import streamlit as st
import base64
import os

def mostrar_tela_login(supabase_conn):
    # ---------------------------------------------------------
    # 1. FUNÇÃO PARA CARREGAR IMAGEM DE FUNDO
    # ---------------------------------------------------------
    def get_base64_image(file_name):
        paths_to_try = [file_name, os.path.join("telas_app_aluno", file_name)]
        for path in paths_to_try:
            if os.path.exists(path):
                try:
                    with open(path, "rb") as f:
                        return base64.b64encode(f.read()).decode()
                except:
                    continue
        return None

    img_b64 = get_base64_image("fundo_app.png") or get_base64_image("fundo_app.jpg")
    bg_style = f"url('data:image/jpeg;base64,{img_b64}')" if img_b64 else "none"

    # ---------------------------------------------------------
    # 2. MÁGICA DO CSS: AJUSTES FINAIS DE LAYOUT
    # ---------------------------------------------------------
    st.markdown(f"""
        <style>
        .stApp {{
            background: linear-gradient(rgba(0, 0, 0, 0.4), rgba(0, 0, 0, 0.7)), 
                        {bg_style} no-repeat center top fixed !important;
            background-size: cover !important;
        }}

        header {{visibility: hidden;}}
        
        /* O formulário Invisível */
        div[data-testid="stForm"] {{
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            padding: 0 !important;
            max-width: 320px; 
            margin: auto;
            margin-top: 35vh; 
            display: flex;
            flex-direction: column;
        }}

        /* Removendo o fundo branco padrão do Streamlit */
        div[data-baseweb="input"], div[data-baseweb="base-input"] {{
            background-color: transparent !important;
            border: none !important;
        }}

        /* LINHA DE DIGITAÇÃO ALINHADA À ESQUERDA */
        input[type="text"] {{
            background-color: transparent !important;
            color: white !important;
            border-bottom: 2px solid rgba(255, 255, 255, 0.8) !important;
            border-radius: 0px !important;
            font-size: 1.3rem !important;
            text-align: left !important; 
            width: 100% !important;
            padding-bottom: 8px !important;
        }}
        
        input::placeholder {{
            color: white !important;
            opacity: 1 !important;
            text-align: left !important; 
        }}

        div[data-testid="InputInstructions"] {{ display: none !important; }}

        /* ========================================================= */
        /* A SOLUÇÃO DEFINITIVA PARA O BOTÃO CENTRALIZADO            */
        /* ========================================================= */
        
        /* 1. A caixa que guarda o botão precisa ocupar a tela toda */
        div[data-testid="stFormSubmitButton"] {{
            width: 100% !important;
            text-align: center !important;
            display: block !important;
            margin-top: 2rem !important;
        }}

        /* 2. O botão em si é forçado a ter margens iguais dos lados */
        div[data-testid="stFormSubmitButton"] > button {{
            background: rgba(255, 255, 255, 0.2) !important;
            backdrop-filter: blur(5px) !important;
            -webkit-backdrop-filter: blur(5px) !important;
            color: white !important;
            font-weight: 700 !important;
            border: 1px solid rgba(255, 255, 255, 0.5) !important;
            border-radius: 30px !important;
            padding: 0.6rem 3rem !important;
            
            /* O Segredo: */
            width: fit-content !important; 
            margin: 0 auto !important; 
            display: block !important;
            
            transition: 0.3s;
        }}

        div[data-testid="stFormSubmitButton"] > button:hover {{
            background: rgba(255, 255, 255, 0.35) !important;
            transform: scale(1.02) !important;
        }}

        /* TEXTOS ABAIXO DO BOTÃO */
        .textos-abaixo {{
            text-align: center;
            margin-top: 2rem; 
            width: 100%;
        }}

        .titulo-escola {{
            font-size: 2rem; 
            font-weight: 900;
            color: white;
            margin-bottom: 0px;
            letter-spacing: 2px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.5); 
        }}
        
        .subtitulo-eco {{
            font-size: 1.1rem;
            font-weight: 700;
            background: linear-gradient(90deg, #00f2fe 0%, #4facfe 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: 1px;
            margin-top: 5px;
        }}
        </style>
    """, unsafe_allow_html=True)

    # ---------------------------------------------------------
    # 3. INTERFACE DE LOGIN
    # ---------------------------------------------------------
    with st.form("login_aluno"):
        matricula = st.text_input("Matrícula", placeholder="Matrícula", label_visibility="collapsed")
        
        if st.form_submit_button("ENTRAR"):
            if matricula:
                try:
                    res = supabase_conn.table("alunos").select("*").eq("matricula", matricula).execute()
                    if res.data:
                        st.session_state.aluno = res.data[0]
                        st.session_state.etapa = "ante_sala"
                        st.rerun()
                    else:
                        st.error("Matrícula não encontrada.")
                except Exception as e:
                    st.error(f"Erro: {e}")

    # Textos lá no fundo
    st.markdown("""
        <div class="textos-abaixo">
            <p class="titulo-escola">EREMPAM</p>
            <p class="subtitulo-eco">ECOSSISTEMA DO ALUNO</p>
        </div>
    """, unsafe_allow_html=True)