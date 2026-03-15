import streamlit as st
from supabase import create_client

# --- 1. CONFIGURAÇÃO E ESTILO (O visual que você gostou) ---
st.set_page_config(page_title="Portal do Aluno - EREMPAM", layout="wide")

st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(135deg, #e0eafc 0%, #cfdef3 100%);
    }
    .card-aluno {
        background: rgba(255, 255, 255, 0.8);
        padding: 30px;
        border-radius: 20px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        backdrop-filter: blur(10px);
        border: 1px solid white;
        text-align: center;
        margin-bottom: 20px;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. CONEXÃO ---
def init_db():
    return create_client(st.secrets["SUPABASE_URL_ALUNOS"], st.secrets["SUPABASE_KEY_ALUNOS"]), \
           create_client(st.secrets["SUPABASE_URL_PROVAS"], st.secrets["SUPABASE_KEY_PROVAS"])

db_alunos, db_provas = init_db()

# --- 3. LÓGICA DE NAVEGAÇÃO ---
if 'aluno' not in st.session_state:
    st.markdown('<div class="card-aluno"><h1>🎓 Bem-vindo ao EREMPAM</h1><p>Identifique-se para começar sua prova</p></div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        matricula = st.text_input("Sua Matrícula:", placeholder="Digite aqui...")
        if st.button("🚀 Acessar Avaliação", use_container_width=True):
            res = db_alunos.table("alunos").select("*").eq("matricula", matricula).execute()
            if res.data:
                st.session_state.aluno = res.data[0]
                st.rerun()
            else:
                st.error("Matrícula não encontrada!")

else:
    aluno = st.session_state.aluno
    st.sidebar.title(f"👋 Olá, {aluno['nome'].split()[0]}")
    st.sidebar.info(f"📍 {aluno['turma']}")

    if 'prova_feita' not in st.session_state:
        st.markdown(f'<div class="card-aluno"><h2>📚 Prova de Hoje</h2><p>Boa sorte, {aluno["nome"]}!</p></div>', unsafe_allow_html=True)
        
        # Filtro automático pela série (1º, 2º ou 3º)
        serie = "1º Ano" if "1º" in aluno['turma'] else "2º Ano" if "2º" in aluno['turma'] else "3º Ano"
        questoes = db_provas.table("questoes").select("*").eq("serie", serie).execute().data

        if not questoes:
            st.warning("Nenhuma prova disponível para sua série no momento.")
        else:
            respostas = {}
            for i, q in enumerate(questoes):
                with st.container():
                    st.markdown(f"### Questão {i+1}")
                    st.markdown(q['enunciado'], unsafe_allow_html=True)
                    opts = q['alternativas']
                    respostas[q['id']] = st.radio("Escolha:", list(opts.keys()), 
                                                 format_func=lambda x: f"{x}) {opts[x]}", 
                                                 key=f"q_{q['id']}")
                    st.divider()

            if st.button("✅ Finalizar e Ver Diagnóstico", type="primary"):
                st.session_state.prova_feita = True
                st.session_state.questoes_prova = questoes
                st.session_state.respostas_aluno = respostas
                st.rerun()
    
    # --- FEEDBACK DIAGNÓSTICO ---
    else:
        st.markdown('<div class="card-aluno"><h1>🎯 Seu Resultado</h1></div>', unsafe_allow_html=True)
        acertos = 0
        qs = st.session_state.questoes_prova
        resps = st.session_state.respostas_aluno

        for q in qs:
            r = resps[q['id']]
            correta = q['resposta_correta']
            justs = q.get('justificativas', {})
            
            with st.expander(f"{'✅' if r == correta else '❌'} {q['assunto']}"):
                if r == correta:
                    st.success("Você acertou!")
                    acertos += 1
                else:
                    st.error(f"Você marcou {r}, mas a correta era {correta}")
                
                feedback = justs.get(r, "Analise sua resposta com calma.")
                st.info(f"💡 **Diagnóstico:** {feedback}")

        st.metric("Nota Final", f"{(acertos/len(qs))*10:.1f}")
        if st.button("Sair"):
            del st.session_state.aluno
            del st.session_state.prova_feita
            st.rerun()