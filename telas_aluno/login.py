# telas_aluno/login.py
import streamlit as st
import base64
import os

def mostrar_tela_login(db_alunos):
    # ==========================================\
    # CARREGA LOGO EM BASE64
    # ==========================================\
    logo_lardiao_b64 = ""
    logo_path = "logo_lardiao.png"
    
    if os.path.exists(logo_path):
        try:
            with open(logo_path, "rb") as f:
                logo_lardiao_b64 = base64.b64encode(f.read()).decode()
        except Exception as e:
            st.warning(f"⚠️ Não foi possível carregar o logo: {e}")
    else:
        # Fallback caso a imagem não exista para não quebrar a tela
        pass 

    # ==========================================\
    # INJEÇÃO DE CSS AVANÇADO (HTML/CSS)
    # Efeito Glassmorphism + Cores Harmonizadas
    # ==========================================\
    st.markdown(f"""
        <style>
        /* Fundo geral da aplicação (Azul Escuro Espacial) */
        [data-testid="stAppViewContainer"] {{
            background: linear-gradient(135deg, #0b132b, #1c2541, #0b132b);
            color: #ffffff;
            /* Trava para forçar centralização e tirar barra de rolagem */
            display: flex !important;
            justify-content: center !important;
            align-items: center !important;
        }}
        
        /* Esconde o header padrão do Streamlit para ficar limpo */
        [data-testid="stHeader"] {{
            background-color: transparent !important;
        }}

        /* Container do Logo e Títulos */
        .glass-container {{
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(15px);
            -webkit-backdrop-filter: blur(15px);
            border-radius: 20px 20px 0px 0px;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
            border-left: 1px solid rgba(255, 255, 255, 0.1);
            border-right: 1px solid rgba(255, 255, 255, 0.1);
            padding: 40px 30px 20px 30px;
            text-align: center;
        }}
        
        /* CORREÇÃO AQUI: Chaves duplas colocadas para o Python não quebrar */
        .logo-img {{
            width: 80px !important;    /* Força o tamanho pequeno */
            height: auto !important;   /* Mantém a proporção */
            max-width: 80px !important; 
            margin-bottom: 10px;
            filter: drop-shadow(0px 4px 6px rgba(0,0,0,0.5));
            display: block;
            margin-left: auto;
            margin-right: auto;
        }}
        
        .titulo-login {{
            font-size: 26px;
            font-weight: 700;
            color: #ffffff;
            margin: 0;
            letter-spacing: 1px;
        }}
        
        .subtitulo-login {{
            font-size: 14px;
            color: #94a3b8;
            margin-top: 5px;
            margin-bottom: 20px;
        }}

        /* Estilizando o Input nativo do Streamlit */
        div[data-baseweb="input"] {{
            background-color: rgba(255, 255, 255, 0.08) !important;
            border: 1px solid rgba(255, 255, 255, 0.2) !important;
            border-radius: 10px !important;
        }}
        
        div[data-baseweb="input"] input {{
            color: #ffffff !important;
            font-size: 18px !important;
            text-align: center !important;
            letter-spacing: 2px;
        }}
        
        div[data-baseweb="input"] input::placeholder {{
            color: rgba(255, 255, 255, 0.4) !important;
        }}

        /* Estilizando o texto do label (matrícula) */
        label[data-testid="stWidgetLabel"] p {{
            color: #e2e8f0 !important;
            font-size: 15px !important;
            font-weight: 500 !important;
        }}

        /* Estilizando o botão nativo do Streamlit (Ciano Vibrante) */
        div[data-testid="stButton"] > button {{
            background: linear-gradient(90deg, #00b4d8, #0077b6) !important;
            color: white !important;
            border: none !important;
            border-radius: 10px !important;
            font-weight: 700 !important;
            font-size: 16px !important;
            padding: 0.6rem 0 !important;
            width: 100%;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(0, 180, 216, 0.4) !important;
        }}
        
        div[data-testid="stButton"] > button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(0, 180, 216, 0.6) !important;
            background: linear-gradient(90deg, #48cae4, #0096c7) !important;
            color: white !important;
        }}

        /* Container inferior para fechar o "Card" */
        .glass-footer {{
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(15px);
            -webkit-backdrop-filter: blur(15px);
            border-radius: 0px 0px 20px 20px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            border-left: 1px solid rgba(255, 255, 255, 0.1);
            border-right: 1px solid rgba(255, 255, 255, 0.1);
            padding: 0px 30px 40px 30px;
            text-align: center;
        }}
        
        .ajuda-link {{
            color: #00b4d8;
            text-decoration: none;
            font-size: 13px;
            font-weight: 500;
            transition: 0.2s;
        }}
        .ajuda-link:hover {{
            color: #48cae4;
            text-decoration: underline;
        }}
        </style>
    """, unsafe_allow_html=True)
    # ==========================================\
    # ESTRUTURA DA TELA (Centralizada)
    # ==========================================\
    # Usamos 3 colunas para centralizar o card no meio da tela
    col1, col2, col3 = st.columns([1, 1.2, 1])

    with col2:
        # --- TOPO DO CARD (HTML) ---
        img_tag = f'<img src="data:image/png;base64,{logo_lardiao_b64}" class="logo-img">' if logo_lardiao_b64 else ''
        st.markdown(f"""
            <div class="glass-container">
                {img_tag}
                <h2 style="font-size: 22px; margin-top: 10px;">Portal do Aluno</h2>
                <p class="subtitulo-login">Acesse suas provas e resultados</p>
            </div>
        """, unsafe_allow_html=True)
        
        # --- MEIO DO CARD (WIDGETS DO STREAMLIT) ---
        # Colocamos os inputs do Streamlit logo abaixo do topo HTML,
        # o CSS vai fazer parecer que é uma coisa só!
        st.markdown('<div class="glass-footer">', unsafe_allow_html=True)
        
        matricula = st.text_input("🔑 Digite sua Matrícula", placeholder="Ex: 1234567")
        
        st.write("") # Espaçinho
        
        if st.button("🚀 ENTRAR NO PORTAL", use_container_width=True):
            if matricula:
                mat_limpa = str(matricula).strip()
                if len(mat_limpa) != 7 or not mat_limpa.isdigit():
                    st.warning("⚠️ Ops! A matrícula deve conter exatamente 7 números.")
                else:
                    with st.spinner("Conectando ao servidor..."):
                        try:
                            res = db_alunos.table("alunos").select("*").eq("numero_matricula", mat_limpa).execute()
                            if res.data and len(res.data) > 0:
                                st.session_state.aluno = res.data[0]
                                st.session_state.etapa = "ante_sala"
                                st.rerun() 
                            else:
                                st.error(f"❌ Matrícula '{mat_limpa}' não encontrada.")
                        except Exception as e:
                            st.error("Erro ao conectar com o banco de dados.")
            else:
                st.warning("⚠️ Por favor, digite sua matrícula antes de acessar.")
                
        # --- RODAPÉ DO CARD (HTML) ---
        st.markdown("""
            <br>
            <a href="#" class="ajuda-link">Esqueceu a matrícula? Fale com o professor.</a>
            </div> """, unsafe_allow_html=True)