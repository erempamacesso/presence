import streamlit as st
import base64
import os

def mostrar_ante_sala():
    # Puxa o nome COMPLETO do aluno que logou
    aluno = st.session_state.get('aluno', {})
    nome_completo = aluno.get('nome', 'Estudante') 
    
    # ---------------------------------------------------------
    # 1. FUNÇÃO PARA CARREGAR IMAGENS (CORRIGIDA)
    # ---------------------------------------------------------
    def get_asset_image(file_name):
        # Tenta encontrar o arquivo dentro de telas_app_aluno/assets/
        caminho = os.path.join("telas_app_aluno", "assets", file_name)
        
        if os.path.exists(caminho):
            try:
                with open(caminho, "rb") as f:
                    return base64.b64encode(f.read()).decode()
            except Exception as e:
                return None
        return None

    # Tentando carregar o fundo (testa png e jpg)
    bg_img = get_asset_image("fundo_app.png") or get_asset_image("fundo_app.jpg")
    # Carregando a prancheta
    prancheta_img = get_asset_image("prancheta.png")
    
    bg_style = f"url('data:image/png;base64,{bg_img}')" if bg_img else "none"
    icon_style = f"url('data:image/png;base64,{prancheta_img}')" if prancheta_img else "none"

    # ---------------------------------------------------------
    # 2. MÁGICA DO CSS (AJUSTADO)
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
            font-weight: 500;
        }}

        /* ESTILO DOS BOTÕES EM GRADE */
        div[data-testid="stButton"] > button {{
            height: 160px !important;
            border-radius: 25px !important;
            font-size: 1.1rem !important;
            font-weight: 800 !important;
            transition: all 0.3s ease !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            display: flex !important;
            align-items: flex-end !important;
            justify-content: center !important;
            padding-bottom: 20px !important;
        }}

        /* BOTÃO DE INSCRIÇÃO COM A PRANCHETA REALISTA */
        button[kind="primary"] {{
            background-image: {icon_style} !important;
            background-repeat: no-repeat !important;
            background-position: center 25px !important;
            background-size: 70px !important; 
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

        /* BOTÕES SECUNDÁRIOS (EVITA O ERRO DE ID DUPLICADO) */
        button[kind="secondary"] {{
            background: rgba(255, 255, 255, 0.03) !important;
            color: rgba(255, 255, 255, 0.2) !important;
        }}

        /* ESTILO DO BOTÃO SAIR */
        .area-sair div[data-testid="stButton"] > button {{
            height: 45px !important;
            background: transparent !important;
            border: 1px solid rgba(255, 255, 255, 0.2) !important;
            color: white !important;
            align-items: center !important;
            padding-bottom: 0 !important;
            font-size: 0.9rem !important;
        }}
        </style>
    """, unsafe_allow_html=True)

    # ---------------------------------------------------------
    # 3. CONTEÚDO DA TELA
    # ---------------------------------------------------------
    st.markdown(f'<p class="boas-vindas">Olá, {nome_completo}!</p>', unsafe_allow_html=True)
    st.markdown('<p class="subtitulo-ante">Painel do Estudante EREMPAM</p>', unsafe_allow_html=True)
    
    # GRADE DE BOTÕES (LINHA 1)
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Botão principal - Identificado pelo texto único
        if st.button("INSCRIÇÕES", type="primary", use_container_width=True):
            st.session_state.etapa = "inscricao_feira"
            st.rerun()
            
    with col2:
        # Resolvendo o erro com key="btn_breve_1"
        st.button("EM BREVE", key="btn_breve_1", type="secondary", use_container_width=True, disabled=True)
        
    with col3:
        # Resolvendo o erro com key="btn_breve_2"
        st.button("EM BREVE", key="btn_breve_2", type="secondary", use_container_width=True, disabled=True)

    # ESPAÇAMENTO PARA O BOTÃO SAIR
    st.write("<br>" * 3, unsafe_allow_html=True)
    
    # BOTÃO SAIR CENTRALIZADO
    _, col_sair, _ = st.columns([1, 1, 1])
    with col_sair:
        st.markdown('<div class="area-sair">', unsafe_allow_html=True)
        if st.button("SAIR DA CONTA", key="btn_sair_final", use_container_width=True):
            st.session_state.clear()
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)