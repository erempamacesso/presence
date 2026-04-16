import streamlit as st
import base64
import os

def mostrar_tela_login(supabase_conn):
    # ---------------------------------------------------------
    # 1. FUNÇÃO PARA CARREGAR IMAGEM DE FUNDO (BASE64)
    # ---------------------------------------------------------
    def get_base64_image(file_name):
        # Tenta encontrar o arquivo na raiz ou dentro da pasta de telas
        paths_to_try = [
            file_name, 
            os.path.join("telas_app_aluno", file_name)
        ]
        
        for path in paths_to_try:
            if os.path.exists(path):
                try:
                    with open(path, "rb") as f:
                        data = f.read()
                    return base64.b64encode(data).decode()
                except:
                    continue
        return None

    # Nome do arquivo que você subiu (FUNDO_APP.jpg ou FUNDO_APP.png)
    # O código tenta os dois formatos para garantir
    img_b64 = get_base64_image("FUNDO_APP.jpg") or get_base64_image("FUNDO_APP.png")
    
    # Define o estilo do fundo: Se achar a imagem, usa ela. Senão, fundo azul escuro.
    bg_style = f"url('data:image/jpeg;base64,{img_b64}')" if img_b64 else "none"

    # ---------------------------------------------------------
    # 2. MÁGICA DO CSS: VISUAL MODERNO
    # ---------------------------------------------------------
    st.markdown(f"""
        <style>
        /* Fundo da Tela com Overlay Escurecido */
        .stApp {{
            background: linear-gradient(rgba(0, 0, 0, 0.75), rgba(0, 0, 0, 0.85)), 
                        {bg_style} no-repeat center center fixed !important;
            background-size: cover !important;
        }}

        /* Oculta menu e header */
        header {{visibility: hidden;}}
        #MainMenu {{visibility: hidden;}}

        /* Cartão de Vidro (Glassmorphism) */
        div[data-testid="stForm"] {{
            background: rgba(255, 255, 255, 0.07) !important;
            backdrop-filter: blur(20px) !important;
            -webkit-backdrop-filter: blur(20px) !important;
            border: 1px solid rgba(255, 255, 255, 0.15) !important;
            border-radius: 28px !important;
            padding: 3rem 2rem !important;
            box-shadow: 0 15px 50px rgba(0, 0, 0, 0.5) !important;
            max-width: 450px;
            margin: auto;
        }}

        /* Títulos Estilizados */
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
            margin-bottom: 2rem;
            text-transform: uppercase;
        }}

        /* Labels e Inputs */
        label {{ color: #e2e8f0 !important; font-weight: 500 !important; }}
        
        div[data-baseweb="input"] {{
            border-radius: 12px !important;
            background-color: rgba(255, 255, 255, 0.95) !important;
            border: 2px solid transparent !important;
        }}

        /* Botão Principal */
        div[data-testid="stFormSubmitButton"] > button {{
            background: linear-gradient(90deg, #4facfe 0%, #00f2fe 100%) !important;
            color: #0a192f !important;
            font-weight: 800 !important;
            font-size: 1.1rem !important;
            border: none !important;
            border-radius: 14px !important;
            padding: 0.7rem !important;
            width: 100% !important;
            transition: all 0.3s ease !important;
            text-transform: uppercase;
            margin-top: 1rem;
        }}
        
        div[data-testid="stFormSubmitButton"] > button:hover {{
            transform: translateY(-3px) !important;
            box-shadow: 0 8px 25px rgba(79, 172, 254, 0.5) !important;
        }}
        </style>
    """, unsafe_allow_html=True)

    # ---------------------------------------------------------
    # 3. INTERFACE DE LOGIN
    # ---------------------------------------------------------
    st.markdown('<p class="titulo-eco">ECOSSISTEMA DO ALUNO</p>', unsafe_allow_html=True)
    st.markdown('<p class="subtitulo-eco">EREMPAM</p>', unsafe_allow_html=True)

    with st.form("login_aluno"):
        st.markdown("<p style='text-align: center; color: white;'>👋 Bem-vindo(a)! Digite seus dados para acessar.</p>", unsafe_allow_html=True)
        
        matricula = st.text_input("Número de Matrícula", placeholder="Digite sua matrícula...")
        data_nasc = st.date_input("Data de Nascimento", format="DD/MM/YYYY")
        
        if st.form_submit_button("ENTRAR NO ECOSSISTEMA"):
            if not matricula:
                st.warning("Por favor, preencha a matrícula.")
            else:
                try:
                    # Consulta ao Supabase
                    res = supabase_conn.table("alunos").select("*").eq("matricula", matricula).execute()
                    
                    if res.data:
                        aluno = res.data[0]
                        # Verifica se a data de nascimento bate (Formato do DB: YYYY-MM-DD)
                        if str(aluno.get('data_nascimento')) == str(data_nasc):
                            st.session_state.aluno = aluno
                            st.session_state.etapa = "ante_sala" # Muda para o Hub
                            st.rerun()
                        else:
                            st.error("❌ Data de nascimento não confere.")
                    else:
                        st.error("❌ Aluno não encontrado com esta matrícula.")
                except Exception as e:
                    st.error(f"🚨 Erro de conexão: {e}")