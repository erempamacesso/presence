# telas_aluno/login.py
import streamlit as st
import base64
import os

def mostrar_tela_login(db_alunos):
    # ==========================================
    # CARREGA LOGO EM BASE64
    # ==========================================
    logo_lardiao_b64 = ""
    logo_path = "logo_lardiao.png"
    
    if os.path.exists(logo_path):
        try:
            with open(logo_path, "rb") as f:
                logo_lardiao_b64 = base64.b64encode(f.read()).decode()
        except Exception as e:
            st.warning(f"⚠️ Não foi possível carregar o logo: {e}")

    # ==========================================
    # INJEÇÃO DE CSS (CHAVES DUPLAS PARA NÃO DAR ERRO)
    # ==========================================
    st.markdown(f"""
        <style>
        /* Fundo e Centralização */
        [data-testid="stAppViewContainer"] {{
            background: linear-gradient(135deg, #0b132b, #1c2541, #0b132b);
            display: flex !important;
            justify-content: center !important;
            align-items: center !important;
        }}
        
        [data-testid="stHeader"] {{
            visibility: hidden;
        }}

        /* Card Glassmorphism */
        .glass-container {{
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(15px);
            -webkit-backdrop-filter: blur(15px);
            border-radius: 20px 20px 0px 0px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-bottom: none;
            padding: 30px;
            text-align: center;
        }}
        
        .logo-img {{
            width: 160px !important; 
            height: auto !important;
            margin: 0 auto 15px auto;
            display: block;
            filter: drop-shadow(0px 4px 8px rgba(0,0,0,0.6));
        }}

        .glass-footer {{
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(15px);
            -webkit-backdrop-filter: blur(15px);
            border-radius: 0px 0px 20px 20px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            padding: 10px 30px 40px 30px;
            text-align: center;
        }}

        /* CORREÇÃO DO TEXTO DO INPUT (BRANCO NO FUNDO ESCURO) */
        div[data-baseweb="input"] {{
            background-color: rgba(255, 255, 255, 0.1) !important;
            border: 1px solid rgba(255, 255, 255, 0.2) !important;
            border-radius: 10px !important;
        }}

        div[data-baseweb="input"] input {{
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
            text-align: center !important;
            font-size: 18px !important;
        }}

        /* Botão */
        div[data-testid="stButton"] > button {{
            background: linear-gradient(90deg, #00b4d8, #0077b6) !important;
            color: white !important;
            border-radius: 10px !important;
            font-weight: bold !important;
            height: 50px;
            border: none !important;
            box-shadow: 0 4px 15px rgba(0, 180, 216, 0.3) !important;
        }}

        .ajuda-link {{
            color: #00b4d8;
            text-decoration: none;
            font-size: 13px;
        }}
        </style>
    """, unsafe_allow_html=True)

    # ==========================================
    # ESTRUTURA DA TELA
    # ==========================================
    _, col2, _ = st.columns([1, 2, 1])

    with col2:
        img_tag = f'<img src="data:image/png;base64,{logo_lardiao_b64}" class="logo-img">' if logo_lardiao_b64 else ''
        st.markdown(f"""
            <div class="glass-container">
                {img_tag}
                <h2 style="color:white; margin:0;">Portal do Aluno</h2>
                <p style="color:#94a3b8;">Acesse suas provas e resultados</p>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown('<div class="glass-footer">', unsafe_allow_html=True)
        
        # O label do Streamlit sumiria no fundo escuro, então usamos o placeholder
        matricula = st.text_input("Matrícula", label_visibility="collapsed", placeholder="Digite sua matrícula aqui...")
        
        st.write("") 
        
        if st.button("🚀 ENTRAR NO PORTAL", use_container_width=True):
            if matricula:
                mat_limpa = str(matricula).strip()
                if len(mat_limpa) != 7 or not mat_limpa.isdigit():
                    st.warning("⚠️ A matrícula deve conter 7 números.")
                else:
                    with st.spinner("Validando..."):
                        try:
                            res = db_alunos.table("alunos").select("*").eq("numero_matricula", mat_limpa).execute()
                            if res.data:
                                st.session_state.aluno = res.data[0]
                                st.session_state.etapa = "ante_sala"
                                st.rerun() 
                            else:
                                st.error("❌ Matrícula não encontrada.")
                        except Exception as e:
                            st.error("Erro na conexão.")
            else:
                st.warning("⚠️ Digite a matrícula.")
                
        st.markdown('<br><a href="#" class="ajuda-link">Esqueceu a matrícula? Fale com o professor.</a></div>', unsafe_allow_html=True)