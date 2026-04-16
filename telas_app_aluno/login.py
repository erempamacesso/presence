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
    # 2. MÁGICA DO CSS: VISUAL MINIMALISTA E INCLUSIVO
    # ---------------------------------------------------------
    st.markdown(f"""
        <style>
        /* Fundo da Tela */
        .stApp {{
            /* Escureci um pouquinho menos (0.6) para a foto brilhar mais */
            background: linear-gradient(rgba(0, 0, 0, 0.6), rgba(0, 0, 0, 0.8)), 
                        {bg_style} no-repeat center top fixed !important;
            background-size: cover !important;
        }}

        header {{visibility: hidden;}}
        #MainMenu {{visibility: hidden;}}

        /* 1. REMOVENDO O BOX TRANSLÚCIDO DO FORMULÁRIO */
        div[data-testid="stForm"] {{
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            backdrop-filter: none !important;
            -webkit-backdrop-filter: none !important;
            padding: 2rem 1rem !important;
            max-width: 400px;
            margin: auto;
            margin-top: 5vh; /* Empurra um pouco pra baixo */
        }}

        /* Títulos */
        .titulo-eco {{
            text-align: center;
            font-size: 2.5rem;
            font-weight: 900;
            background: linear-gradient(90deg, #00f2fe 0%, #4facfe 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0px;
            font-family: 'Segoe UI', sans-serif;
            letter-spacing: -1px;
        }}
        
        .subtitulo-eco {{
            text-align: center;
            font-size: 1.1rem;
            color: #a0aec0;
            letter-spacing: 4px;
            margin-bottom: 3rem;
        }}

        /* 2. INPUT FLUTUANTE (SÓ A LINHA EMBAIXO) */
        div[data-baseweb="input"] {{
            background-color: transparent !important;
            border: none !important;
            border-bottom: 2px solid rgba(255, 255, 255, 0.5) !important;
            border-radius: 0px !important;
        }}
        
        /* Quando clica para digitar, a linha fica azul */
        div[data-baseweb="input"]:focus-within {{
            border-bottom: 2px solid #00f2fe !important;
        }}

        /* Centralizando e pintando o texto digitado de branco */
        input {{
            color: white !important;
            font-size: 1.2rem !important;
            text-align: center !important;
            font-weight: bold !important;
        }}
        
        /* Cor do texto de dica (placeholder) */
        input::placeholder {{
            color: rgba(255, 255, 255, 0.6) !important;
        }}

        /* Botão Minimalista */
        div[data-testid="stFormSubmitButton"] > button {{
            background: linear-gradient(90deg, #4facfe 0%, #00f2fe 100%) !important;
            color: #0a192f !important;
            font-weight: 800 !important;
            font-size: 1.1rem !important;
            border: none !important;
            border-radius: 30px !important; /* Bem redondinho */
            padding: 0.5rem !important;
            width: 100% !important;
            margin-top: 2rem !important;
            transition: all 0.3s ease !important;
        }}
        div[data-testid="stFormSubmitButton"] > button:hover {{
            transform: scale(1.05) !important;
            box-shadow: 0 5px 20px rgba(0, 242, 254, 0.5) !important;
        }}
        </style>
    """, unsafe_allow_html=True)

    # ---------------------------------------------------------
    # 3. INTERFACE DE LOGIN SIMPLIFICADA
    # ---------------------------------------------------------
    st.markdown('<p class="titulo-eco">ECOSSISTEMA DO ALUNO</p>', unsafe_allow_html=True)
    st.markdown('<p class="subtitulo-eco">EREMPAM</p>', unsafe_allow_html=True)

    with st.form("login_aluno"):
        st.markdown("<p style='text-align: center; color: white; font-size:1.1rem;'>👋 Digite sua matrícula para acessar</p>", unsafe_allow_html=True)
        
        # label_visibility="collapsed" esconde o nome em cima da caixa e deixa só a linha
        matricula = st.text_input("Matrícula", placeholder="Ex: 12345678", label_visibility="collapsed")
        
        if st.form_submit_button("ENTRAR"):
            if not matricula:
                st.warning("⚠️ Por favor, digite sua matrícula.")
            else:
                try:
                    # Busca APENAS pela matrícula agora
                    res = supabase_conn.table("alunos").select("*").eq("matricula", matricula).execute()
                    
                    if res.data:
                        st.session_state.aluno = res.data[0] # Salva os dados do aluno na sessão
                        st.session_state.etapa = "ante_sala" # Manda para o Hub
                        st.rerun()
                    else:
                        st.error("❌ Matrícula não encontrada no sistema.")
                except Exception as e:
                    st.error(f"🚨 Erro de conexão: {e}")