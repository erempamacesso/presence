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

    # Usando o nome em minúsculo como você alertou
    img_b64 = get_base64_image("fundo_app.png") or get_base64_image("fundo_app.jpg")
    bg_style = f"url('data:image/jpeg;base64,{img_b64}')" if img_b64 else "none"

    # ---------------------------------------------------------
    # 2. MÁGICA DO CSS: ESTILO LIMPO E CENTRALIZADO
    # ---------------------------------------------------------
    st.markdown(f"""
        <style>
        .stApp {{
            background: linear-gradient(rgba(0, 0, 0, 0.4), rgba(0, 0, 0, 0.7)), 
                        {bg_style} no-repeat center top fixed !important;
            background-size: cover !important;
        }}

        header {{visibility: hidden;}}
        
        /* Centralizando o formulário e os itens dentro dele */
        div[data-testid="stForm"] {{
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            padding: 0 !important;
            max-width: 300px; 
            margin: auto;
            margin-top: 38vh;
            display: flex;
            flex-direction: column;
            align-items: center; /* Centraliza o botão e o input */
        }}

        /* Removendo fundos do Streamlit */
        div[data-baseweb="input"], div[data-baseweb="base-input"] {{
            background-color: transparent !important;
            border: none !important;
        }}

        /* Estilizando a linha de entrada */
        input[type="text"] {{
            background-color: transparent !important;
            color: white !important;
            border-bottom: 2px solid rgba(255, 255, 255, 0.8) !important;
            border-radius: 0px !important;
            font-size: 1.3rem !important;
            text-align: center !important; /* Texto da matrícula no centro */
            width: 100% !important;
        }}
        
        /* Cor branca para o placeholder "Matrícula" */
        input::placeholder {{
            color: white !important;
            opacity: 1 !important;
        }}

        /* Esconder instruções "Press Enter" */
        div[data-testid="InputInstructions"] {{ display: none !important; }}

        /* Botão Entrar Centralizado e Translúcido */
        div[data-testid="stFormSubmitButton"] {{
            display: flex;
            justify-content: center;
            width: 100%;
        }}

        div[data-testid="stFormSubmitButton"] > button {{
            background: rgba(255, 255, 255, 0.2) !important;
            backdrop-filter: blur(5px) !important;
            -webkit-backdrop-filter: blur(5px) !important;
            color: white !important;
            font-weight: 700 !important;
            border: 1px solid rgba(255, 255, 255, 0.5) !important;
            border-radius: 30px !important;
            padding: 0.6rem 3rem !important; /* Largura fixa para o botão */
            width: auto !important;
            margin-top: 2rem !important;
            transition: 0.3s;
        }}

        .footer-titulos {{
            position: fixed;
            bottom: 25px;
            left: 0;
            width: 100%;
            text-align: center;
        }}

        .titulo-eco {{
            font-size: 1.8rem;
            font-weight: 900;
            background: linear-gradient(90deg, #00f2fe 0%, #4facfe 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0px;
        }}
        
        .subtitulo-eco {{
            font-size: 0.9rem;
            color: rgba(255, 255, 255, 0.6);
            letter-spacing: 3px;
        }}
        </style>
    """, unsafe_allow_html=True)

    # ---------------------------------------------------------
    # 3. INTERFACE
    # ---------------------------------------------------------
    with st.form("login_aluno"):
        # Placeholder agora em branco e texto centralizado
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

    st.markdown("""
        <div class="footer-titulos">
            <p class="titulo-eco">EREMPAM</p>
            <p class="subtitulo-eco">ECOSSISTEMA DO ALUNO</p>
        </div>
    """, unsafe_allow_html=True)