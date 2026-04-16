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
            margin-top: 35vh; /* Altura do peito na foto */
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
            text-align: left !important; /* <--- Texto na esquerda! */
            width: 100% !important;
            padding-bottom: 8px !important;
        }}
        
        input::placeholder {{
            color: white !important;
            opacity: 1 !important;
            text-align: left !important; /* <--- Placeholder na esquerda! */
        }}

        div[data-testid="InputInstructions"] {{ display: none !important; }}

        /* BOTÃO ENTRAR NO CENTRO */
        div[data-testid="stFormSubmitButton"] {{
            display: flex;
            justify-content: center; /* Mantém o botão no meio */
            width: 100%;
            margin-top: 1.5rem !important;
        }}

        div[data-testid="stFormSubmitButton"] > button {{
            background: rgba(255, 255, 255, 0.2) !important;
            backdrop-filter: blur(5px) !important;
            -webkit-backdrop-filter: blur(5px) !important;
            color: white !important;
            font-weight: 700 !important;
            border: 1px solid rgba(255, 255, 255, 0.5) !important;
            border-radius: 30px !important;
            padding: 0.6rem 3rem !important;
            width: auto !important;
            transition: 0.3s;
        }}

        div[data-testid="stFormSubmitButton"] > button:hover {{
            background: rgba(255, 255, 255, 0.35) !important;
            transform: scale(1.02) !important;
        }}

        /* TEXTOS ABAIXO DO BOTÃO (2 linhas de distância) */
        .textos-abaixo {{
            text-align: center;
            margin-top: 2rem; /* Cria o espaço em branco abaixo do botão */
        }}

        .titulo-escola {{
            font-size: 2rem; /* Bem grande para chamar atenção */
            font-weight: 900;
            color: white;
            margin-bottom: 0px;
            letter-spacing: 2px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.5); /* Sombrinha para leitura clara */
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

    # Os textos agora estão fora do rodapé e ficam acompanhando o formulário logo abaixo dele!
    st.markdown("""
        <div class="textos-abaixo">
            <p class="titulo-escola">EREMPAM</p>
            <p class="subtitulo-eco">ECOSSISTEMA DO ALUNO</p>
        </div>
    """, unsafe_allow_html=True)