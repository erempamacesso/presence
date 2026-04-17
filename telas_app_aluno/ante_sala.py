import streamlit as st
import base64
import os

def mostrar_ante_sala():
    # Puxa o nome COMPLETO do aluno
    aluno = st.session_state.get('aluno', {})
    nome_completo = aluno.get('nome', 'Estudante') 
    
    # ---------------------------------------------------------
    # 1. FUNÇÃO PARA CARREGAR IMAGENS DA PASTA ASSETS
    # ---------------------------------------------------------
    def get_asset_image(file_name):
        # Caminho atualizado para a pasta assets
        path = os.path.join("telas_app_aluno", "assets", file_name)
        if os.path.exists(path):
            try:
                with open(path, "rb") as f:
                    return base64.b64encode(f.read()).decode()
            except:
                return None
        return None

    bg_img = get_asset_image("fundo_app.png") or get_asset_image("fundo_app.jpg")
    prancheta_img = get_asset_image("prancheta.png")
    
    bg_style = f"url('data:image/jpeg;base64,{bg_img}')" if bg_img else "none"
    icon_style = f"url('data:image/png;base64,{prancheta_img}')" if prancheta_img else "none"

    # ---------------------------------------------------------
    # 2. CSS AVANÇADO: BOTÃO COM IMAGEM REALISTA
    # ---------------------------------------------------------
    st.markdown(f"""
        <style>
        .stApp {{
            background: linear-gradient(rgba(0, 0, 0, 0.85), rgba(0, 0, 0, 0.95)), 
                        {bg_style} no-repeat center top fixed !important;
            background-size: cover !important;
        }}

        header {{visibility: hidden;}}
        
        .boas-vindas {{
            text-align: center;
            font-size: 1.8rem;
            font-weight: 900;
            color: white;
            margin-top: 5vh;
            text-transform: uppercase;
            text-shadow: 2px 2px 10px rgba(0,0,0,0.8);
        }}

        .subtitulo-ante {{
            text-align: center;
            font-size: 1rem;
            color: #00f2fe; 
            margin-bottom: 3rem;
        }}

        /* CONFIGURAÇÃO DO BOTÃO COM IMAGEM */
        div[data-testid="stButton"] > button {{
            height: 160px !important; /* Aumentei um pouco para caber a imagem + texto */
            border-radius: 25px !important;
            font-size: 1.1rem !important;
            font-weight: 800 !important;
            transition: all 0.3s ease !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            
            /* Posicionamento do texto no fundo do botão */
            display: flex !important;
            align-items: flex-end !important;
            justify-content: center !important;
            padding-bottom: 15px !important;
        }}

        /* O BOTÃO DE INSCRIÇÃO (Primary) COM A PRANCHETA */
        button[kind="primary"] {{
            background-image: {icon_style} !important;
            background-repeat: no-repeat !important;
            background-position: center 20px !important; /* Imagem no topo */
            background-size: 80px !important; /* Ajuste o tamanho da prancheta aqui */
            background-color: rgba(255, 255, 255, 0.05) !important;
            color: white !important;
            backdrop-filter: blur(10px);
        }}

        button[kind="primary"]:hover {{
            background-color: rgba(255, 255, 255, 0.15) !important;
            transform: translateY(-5px) !important;
            border-color: #00f2fe !important;
            box-shadow: 0 10px 30px rgba(0, 242, 254, 0.3) !important;
        }}

        /* Botões Vazios */
        button[kind="secondary"] {{
            background: rgba(255, 255, 255, 0.03) !important;
            color: rgba(255, 255, 255, 0.2) !important;
        }}

        /* Estilo do Botão Sair */
        .botao-sair div[data-testid="stButton"] > button {{
            height: 45px !important;
            background: transparent !important;
            border: 1px solid rgba(255, 255, 255, 0.2) !important;
            color: white !important;
            align-items: center !important;
            padding-bottom: 0 !important;
        }}
        </style>
    """, unsafe_allow_html=True)

    # ---------------------------------------------------------
    # 3. INTERFACE
    # ---------------------------------------------------------
    st.markdown(f'<p class="boas-vindas">Olá, {nome_completo}!</p>', unsafe_allow_html=True)
    st.markdown('<p class="subtitulo-ante">Painel do Estudante EREMPAM</p>', unsafe_allow_html=True)
    
    # Grade de Botões
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("INSCRIÇÕES", type="primary", use_container_width=True):
            st.session_state.etapa = "inscricao_feira"
            st.rerun()
            
    with col2:
        st.button("EM BREVE", type="secondary", use_container_width=True, disabled=True)
        
    with col3:
        st.button("EM BREVE", type="secondary", use_container_width=True, disabled=True)

    # Botão Sair
    st.write("<br>" * 2, unsafe_allow_html=True)
    _, col_sair, _ = st.columns([1, 1, 1])
    with col_sair:
        st.markdown('<div class="botao-sair">', unsafe_allow_html=True)
        if st.button("SAIR DA CONTA", use_container_width=True):
            st.session_state.clear()
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)