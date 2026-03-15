import streamlit as st
import os
from dotenv import load_dotenv
from supabase import create_client

# Configurações Visuais Estilo Mobile
st.set_page_config(page_title="Prova EREMPAM", layout="centered")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .card-login {
        background: white;
        padding: 40px;
        border-radius: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        text-align: center;
    }
    .stTextInput>div>div>input {
        text-align: center;
        font-size: 20px;
        border-radius: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# Conexões (Base 1 para Alunos, Base 2 para Provas)
load_dotenv()
supabase_alunos = create_client(os.getenv("SUPABASE_URL_ALUNOS"), os.getenv("SUPABASE_KEY_ALUNOS"))
supabase_provas = create_client(os.getenv("SUPABASE_URL_PROVAS"), os.getenv("SUPABASE_KEY_PROVAS"))

# --- LÓGICA DE NAVEGAÇÃO ---
if 'aluno_logado' not in st.session_state:
    st.markdown("<div class='card-login'>", unsafe_allow_html=True)
    st.image("logo_erempam.png", width=150)
    st.header("Login do Estudante")
    
    matricula = st.text_input("Digite sua Matrícula", placeholder="Ex: 2024001")
    
    if st.button("ACESSAR PROVA", use_container_width=True):
        # 1. TESTE COM MATRÍCULA FICTÍCIA
        if matricula == "9999":
            st.session_state.aluno_logado = {
                "nome": "ALUNO TESTE",
                "turma": "Turma de Demonstração",
                "id": "9999"
            }
            st.rerun()
            
        # 2. BUSCA REAL NO BANCO (Para quando você atualizar amanhã)
        else:
            try:
                # Aqui ele busca na Base 1 (SIGEREMPAM)
                res = supabase_alunos.table("alunos").select("*").eq("id", matricula).execute()
                if res.data:
                    st.session_state.aluno_logado = res.data[0]
                    st.rerun()
                else:
                    st.error("Matrícula não encontrada no sistema.")
            except:
                st.error("O sistema de matrículas está em manutenção. Tente a matrícula 9999.")
    
    st.markdown("</div>", unsafe_allow_html=True)

else:
    # --- ÁREA DA PROVA ---
    aluno = st.session_state.aluno_logado
    
    st.success(f"📖 Aluno: {aluno['nome']} | {aluno['turma']}")
    
    st.subheader("📝 Avaliações do Dia")
    
    # Busca questões na BASE 2 (AVALIADOR)
    try:
        questoes = supabase_provas.table("questoes_prova").select("*").execute()
        if questoes.data:
            # Mostra a prova de forma bonita
            for q in questoes.data:
                with st.container(border=True):
                    st.write(f"**{q['pergunta']}**")
                    st.radio("Escolha a opção correta:", 
                             [q['opt_a'], q['opt_b'], q['opt_c'], q['opt_d']], 
                             key=f"q_{q['id']}")
            
            if st.button("Finalizar e Enviar Prova"):
                st.balloons()
                st.success("Prova enviada com sucesso!")
        else:
            st.info("Nenhuma questão cadastrada para esta turma ainda.")
    except:
        st.warning("Conectado ao banco, mas a tabela de questões ainda não existe.")

    if st.button("Sair"):
        del st.session_state.aluno_logado
        st.rerun()