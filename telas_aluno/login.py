# telas_aluno/login.py
import streamlit as st

def mostrar_tela_login(db_alunos, logo_lardiao_b64, C_CARD_BG, C_BORDER, C_PRIMARY, C_TEXT_MUTED):
    st.markdown(f"""
        <style>
        .login-card-unificado {{
            background-color: {C_CARD_BG}; max-width: 450px; margin: auto;
            padding: 30px; border-radius: 25px; border: 1px solid {C_BORDER};
            box-shadow: 0 10px 25px rgba(0,0,0,0.05); text-align: center;
        }}
        .title-portal {{ color: {C_PRIMARY}; font-size: 24px; font-weight: 800; margin-top: 15px; font-family: sans-serif; }}
        div[data-baseweb="input"] {{ border-radius: 12px !important; border: 1px solid {C_BORDER} !important; }}
        </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([0.1, 1, 0.1])
    
    with col2:
        st.markdown(f"""
            <div class="login-card-unificado">
                <img src="data:image/png;base64,{logo_lardiao_b64}" width="135">
                <div class="title-portal">SISTEMA DE ATIVIDADES</div>
                <div style="color: {C_TEXT_MUTED}; margin-bottom: 25px;">do Prof. Lardião</div>
            </div>
        """, unsafe_allow_html=True)

        with st.container():
            st.markdown('<div style="margin-top: -100px; padding: 0 30px 40px 30px;">', unsafe_allow_html=True)
            
            matricula = st.text_input("Digite sua matrícula:", label_visibility="collapsed", placeholder="Sua Matrícula (7 números)", max_chars=7)
            st.write("") 
            
            if st.button("ACESSAR SISTEMA PRO", use_container_width=True, type="primary"):
                if matricula:
                    mat_limpa = str(matricula).strip()
                    if len(mat_limpa) != 7 or not mat_limpa.isdigit():
                        st.warning("⚠️ Ops! A matrícula deve conter exatamente 7 números.")
                    else:
                        with st.spinner("Buscando dados no servidor..."):
                            try:
                                res = db_alunos.table("alunos").select("*").eq("numero_matricula", mat_limpa).execute()
                                if res.data and len(res.data) > 0:
                                    st.session_state.aluno = res.data[0]
                                    st.session_state.etapa = "ante_sala"
                                    st.rerun() 
                                else:
                                    st.error(f"❌ Matrícula '{mat_limpa}' não encontrada.")
                            except Exception as e:
                                st.error("Erro ao conectar com o banco de dados das matrículas.")
                                st.code(f"Detalhes do erro: {e}")
                else:
                    st.warning("⚠️ Por favor, digite sua matrícula antes de acessar.")
            
            st.markdown("""
                <br>
                <a href="#" style="color: #94a3b8; text-decoration: none; font-size: 13px;">Dúvidas ou problemas? Clique aqui.</a>
                </div>
            """, unsafe_allow_html=True)