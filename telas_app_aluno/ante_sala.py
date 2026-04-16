import streamlit as st
import base64
import os

def mostrar_ante_sala():
    # Puxa o nome do aluno que logou (Pega só o primeiro nome)
    aluno = st.session_state.get('aluno', {})
    nome = aluno.get('nome', 'Estudante').split()[0] 
    
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
    # 2. MÁGICA DO CSS: ESTILO ANTE-SALA (VIDRO E DARK MODE)
    # ---------------------------------------------------------
    st.markdown(f"""
        <style>
        /* Fundo bem mais escuro para focar no botão (Opacidade 0.8 a 0.95) */
        .stApp {{
            background: linear-gradient(rgba(0, 0, 0, 0.80), rgba(0, 0, 0, 0.95)), 
                        {bg_style} no-repeat center top fixed !important;
            background-size: cover !important;
        }}

        header {{visibility: hidden;}}
        
        /* Títulos de Boas-Vindas */
        .boas-vindas {{
            text-align: center;
            font-size: 2.5rem;
            font-weight: 900;
            color: white;
            margin-top: 5vh;
            margin-bottom: 0px;
            letter-spacing: 1px;
            text-shadow: 2px 2px 10px rgba(0,0,0,0.8);
        }}

        .subtitulo-ante {{
            text-align: center;
            font-size: 1.1rem;
            color: #00f2fe; /* Azul neon para dar um charme */
            font-weight: 500;
            margin-bottom: 3rem;
            letter-spacing: 1px;
        }}

        /* CAIXA DE VIDRO DO CARTÃO (Container) */
        /* Captura as caixas com borda do Streamlit */
        [data-testid="stVerticalBlockBorderWrapper"] {{
            background: rgba(255, 255, 255, 0.05) !important;
            backdrop-filter: blur(15px) !important;
            -webkit-backdrop-filter: blur(15px) !important;
            border: 1px solid rgba(255, 255, 255, 0.15) !important;
            border-radius: 20px !important;
            padding: 1rem !important;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.6) !important;
        }}

        /* Textos dentro da caixa */
        [data-testid="stVerticalBlockBorderWrapper"] h3 {{
            color: white !important;
            text-align: center !important;
            font-weight: 800 !important;
        }}
        [data-testid="stVerticalBlockBorderWrapper"] p {{
            color: rgba(255, 255, 255, 0.7) !important;
            text-align: center !important;
            font-size: 0.95rem !important;
        }}

        /* BOTÃO PRINCIPAL (Inscrições) */
        button[kind="primary"] {{
            background: linear-gradient(90deg, #4facfe 0%, #00f2fe 100%) !important;
            color: #0a192f !important;
            font-weight: 800 !important;
            font-size: 1.1rem !important;
            border: none !important;
            border-radius: 30px !important;
            padding: 0.8rem !important;
            transition: all 0.3s ease !important;
            letter-spacing: 1px;
        }}
        button[kind="primary"]:hover {{
            transform: scale(1.05) !important;
            box-shadow: 0 8px 25px rgba(0, 242, 254, 0.5) !important;
        }}

        /* BOTÃO SECUNDÁRIO (Sair da Conta) */
        button[kind="secondary"] {{
            background: rgba(255, 255, 255, 0.1) !important;
            backdrop-filter: blur(5px) !important;
            color: white !important;
            font-weight: 600 !important;
            border: 1px solid rgba(255, 255, 255, 0.3) !important;
            border-radius: 30px !important;
            padding: 0.5rem !important;
            transition: all 0.3s ease !important;
        }}
        button[kind="secondary"]:hover {{
            background: rgba(255, 50, 50, 0.3) !important; /* Fica avermelhado ao passar o mouse */
            border-color: rgba(255, 50, 50, 0.5) !important;
        }}
        </style>
    """, unsafe_allow_html=True)

    # ---------------------------------------------------------
    # 3. INTERFACE DA ANTE-SALA
    # ---------------------------------------------------------
    st.markdown(f'<p class="boas-vindas">Olá, {nome}! 👋</p>', unsafe_allow_html=True)
    st.markdown('<p class="subtitulo-ante">Bem-vindo ao Ecossistema. O que deseja fazer hoje?</p>', unsafe_allow_html=True)
    
    # 3 colunas para manter o cartão no centro (ideal para PC e Mobile)
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # CARTÃO ÚNICO: EVENTOS E FEIRAS
        with st.container(border=True):
            st.markdown("### 🎪 Eventos e Feiras")
            st.write("Inscreva seu grupo em feiras de ciências, olimpíadas e mostras de conhecimentos da escola.")
            
            st.write("") # Pequeno respiro antes do botão
            
            # Botão Primary (Puxa o CSS do degradê azul)
            if st.button("ACESSAR INSCRIÇÕES", type="primary", use_container_width=True):
                st.session_state.etapa = "inscricao_feira"
                st.rerun()
        
        st.write("") 
        st.write("") 
        
        # BOTÃO DE SAIR (Fica fora da caixa de vidro, discreto embaixo)
        # Botão Secondary (Puxa o CSS transparente que fica vermelho no hover)
        if st.button("🚪 Sair da Conta", type="secondary", use_container_width=True):
            st.session_state.clear()
            st.rerun()