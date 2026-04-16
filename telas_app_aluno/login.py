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

    img_b64 = get_base64_image("fundo_app.jpg") or get_base64_image("fundo_app.png")
    bg_style = f"url('data:image/jpeg;base64,{img_b64}')" if img_b64 else "none"

    # ---------------------------------------------------------
    # 2. MÁGICA DO CSS: ESTILO GOVERNO PE (CLEAN)
    # ---------------------------------------------------------
    st.markdown(f"""
        <style>
        /* Fundo da Tela */
        .stApp {{
            background: linear-gradient(rgba(0, 0, 0, 0.4), rgba(0, 0, 0, 0.7)), 
                        {bg_style} no-repeat center top fixed !important;
            background-size: cover !important;
        }}

        header {{visibility: hidden;}}
        #MainMenu {{visibility: hidden;}}

        /* 1. FORMULÁRIO INVISÍVEL NO MEIO DA TELA */
        div[data-testid="stForm"] {{
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            padding: 0 !important;
            max-width: 320px; /* Mais estreitinho para ficar elegante no mobile */
            margin: auto;
            margin-top: 35vh; /* Empurra o formulário para a barriga do pessoal, liberando os rostos */
        }}

        /* 2. MATANDO O BLOCO BRANCO DO STREAMLIT */
        div[data-baseweb="input"], 
        div[data-baseweb="base-input"] {{
            background-color: transparent !important;
            border: none !important;
        }}

        /* 3. A LINHA DO INPUT (ESTILO REFERÊNCIA) */
        input[type="text"] {{
            background-color: transparent !important;
            color: white !important;
            border-bottom: 2px solid rgba(255, 255, 255, 0.8) !important;
            border-radius: 0px !important;
            padding-bottom: 8px !important;
            font-size: 1.2rem !important;
            text-align: left !important;
        }}
        
        input[type="text"]:focus {{
            border-bottom: 2px solid #00f2fe !important;
            box-shadow: none !important;
        }}

        /* Esconder o "Press Enter to submit" chato do Streamlit */
        div[data-testid="InputInstructions"] {{
            display: none !important;
        }}

        /* 4. BOTÃO TRANSLÚCIDO (VIDRO FOSCO) */
        div[data-testid="stFormSubmitButton"] > button {{
            background: rgba(255, 255, 255, 0.2) !important; /* Transparente clarinho */
            backdrop-filter: blur(5px) !important; /* Embaça o fundo atrás do botão */
            -webkit-backdrop-filter: blur(5px) !important;
            color: white !important;
            font-weight: 600 !important;
            font-size: 1.1rem !important;
            border: 1px solid rgba(255, 255, 255, 0.4) !important; /* Bordinha branca fina */
            border-radius: 30px !important;
            padding: 0.6rem !important;
            width: 100% !important;
            margin-top: 2rem !important;
            letter-spacing: 1px;
            transition: all 0.3s ease !important;
        }}
        
        div[data-testid="stFormSubmitButton"] > button:hover {{
            background: rgba(255, 255, 255, 0.35) !important;
            transform: scale(1.02) !important;
        }}

        /* 5. TÍTULOS FIXOS LÁ NO PÉ DA PÁGINA (NAS PERNAS DO CADEIRANTE) */
        .footer-titulos {{
            position: fixed;
            bottom: 30px;
            left: 0;
            width: 100%;
            text-align: center;
            z-index: 99;
        }}

        .titulo-eco {{
            font-size: 2rem;
            font-weight: 900;
            background: linear-gradient(90deg, #00f2fe 0%, #4facfe 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0px;
            font-family: 'Segoe UI', sans-serif;
            letter-spacing: -1px;
        }}
        
        .subtitulo-eco {{
            font-size: 1rem;
            color: rgba(255, 255, 255, 0.7);
            letter-spacing: 4px;
            margin: 0;
        }}
        </style>
    """, unsafe_allow_html=True)

    # ---------------------------------------------------------
    # 3. INTERFACE DE LOGIN SIMPLIFICADA
    # ---------------------------------------------------------
    
    # O Form fica no centro da tela (Foi empurrado para baixo pelo CSS margin-top)
    with st.form("login_aluno"):
        # label_visibility="collapsed" remove o texto de cima, deixando só a linha
        matricula = st.text_input("Matrícula", placeholder="Matrícula", label_visibility="collapsed")
        
        if st.form_submit_button("ENTRAR"):
            if not matricula:
                st.warning("⚠️ Informe sua matrícula.")
            else:
                try:
                    res = supabase_conn.table("alunos").select("*").eq("matricula", matricula).execute()
                    if res.data:
                        st.session_state.aluno = res.data[0]
                        st.session_state.etapa = "ante_sala"
                        st.rerun()
                    else:
                        st.error("❌ Matrícula não encontrada.")
                except Exception as e:
                    st.error(f"🚨 Erro: {e}")

    # Textos lá no fundo da tela (Independentes da posição do formulário)
    st.markdown("""
        <div class="footer-titulos">
            <p class="titulo-eco">ECOSSISTEMA DO ALUNO</p>
            <p class="subtitulo-eco">EREMPAM</p>
        </div>
    """, unsafe_allow_html=True)