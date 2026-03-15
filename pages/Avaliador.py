import streamlit as st
import os
from dotenv import load_dotenv
from supabase import create_client

# Configuração da página para ficar larga e bonita
st.set_page_config(page_title="EREMPAM - Avaliador", layout="wide")

# CSS Personalizado para a "Área do Aluno"
st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(135deg, #e0eafc 0%, #cfdef3 100%);
    }
    .card-aluno {
        background: rgba(255, 255, 255, 0.7);
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 8px 32px rgba(31, 38, 135, 0.1);
        backdrop-filter: blur(4px);
        border: 1px solid rgba(255, 255, 255, 0.18);
        margin-bottom: 25px;
    }
    .prova-item {
        background: white;
        padding: 15px;
        border-radius: 12px;
        margin-bottom: 10px;
        border-left: 6px solid #007bff;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    </style>
""", unsafe_allow_html=True)

# Conexão com as Bases (Puxando do seu .env)
load_dotenv()
supabase_alunos = create_client(os.getenv("SUPABASE_URL_ALUNOS"), os.getenv("SUPABASE_KEY_ALUNOS"))
supabase_provas = create_client(os.getenv("SUPABASE_URL_PROVAS"), os.getenv("SUPABASE_KEY_PROVAS"))

# --- INTERFACE ---
st.title("🎓 Portal de Avaliações EREMPAM")

# Sidebar para identificação (Puxando da Base 1)
with st.sidebar:
    st.header("Acesso Aluno")
    try:
        res = supabase_alunos.table("alunos").select("turma").execute()
        turmas = sorted(list(set([r['turma'] for r in res.data if r.get('turma')])))
        turma_sel = st.selectbox("Sua Turma:", turmas)
        
        res_n = supabase_alunos.table("alunos").select("nome").eq("turma", turma_sel).execute()
        nomes = [n['nome'] for n in res_n.data]
        aluno_nome = st.selectbox("Seu Nome:", nomes)
    except:
        st.error("Erro ao conectar na Base de Alunos.")

# Área Principal
st.markdown(f"""
    <div class="card-aluno">
        <h3>Bem-vindo, {aluno_nome}!</h3>
        <p>Selecione abaixo a prova que deseja realizar hoje.</p>
    </div>
""", unsafe_allow_html=True)

# Listagem de Provas (Puxando da Base 2)
st.subheader("📚 Provas Disponíveis")
try:
    # Tenta buscar as matérias cadastradas no Novo Projeto
    res_p = supabase_provas.table("questoes_prova").select("materia").execute()
    materias = list(set([p['materia'] for p in res_p.data])) if res_p.data else []
    
    if materias:
        for mat in materias:
            col_txt, col_btn = st.columns([3, 1])
            with col_txt:
                st.markdown(f"""<div class="prova-item"><b>Prova de {mat}</b></div>""", unsafe_allow_html=True)
            with col_btn:
                if st.button(f"Abrir {mat}", key=mat):
                    st.session_state.prova_atual = mat
                    st.write(f"Carregando prova de {mat}...")
    else:
        st.info("Nenhuma prova cadastrada no banco ainda.")
except:
    st.warning("Aguardando criação da tabela 'questoes_prova' no Supabase Novo.")