import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from supabase import create_client, Client
import time
import re
import random 

# ... (Configurações iniciais e conexão permanecem iguais) ...
@st.cache_resource
def init_connections():
    db_alunos = create_client(st.secrets["SUPABASE_URL_ALUNOS"], st.secrets["SUPABASE_KEY_ALUNOS"])
    db_provas = create_client(st.secrets["SUPABASE_URL_PROVAS"], st.secrets["SUPABASE_KEY_PROVAS"])
    return db_alunos, db_provas

db_alunos, db_provas = init_connections()

# --- ESTADO ---
for key in ['etapa', 'aluno', 'prova_config', 'tempo_final', 'questoes', 'respostas']:
    if key not in st.session_state:
        st.session_state[key] = "login" if key == 'etapa' else {} if key == 'respostas' else None

# ... (Lógica de Login e Instruções igual até o botão INICIAR) ...

# ==========================================
# ETAPA 2: INSTRUÇÕES (ONDE O SORTEIO ACONTECE)
# ==========================================
if st.session_state.etapa == "instrucoes":
    aluno = st.session_state.aluno
    prova = st.session_state.prova_config
    
    if st.button("INICIAR PROVA", type="primary", use_container_width=True):
        st.session_state.tempo_final = datetime.now() + timedelta(minutes=prova['tempo_duracao'])
        
        # 1. Baixa TODAS as questões do banco selecionado (o pool de 15 ou 20)
        ids = prova.get('questoes_ids', [])
        res_q = db_provas.table("questoes").select("*").in_("id", ids).execute()
        pool_questoes = res_q.data
        
        # 2. LÓGICA DE SORTEIO POR ALUNO
        # Usamos o ID do aluno para garantir que, se ele atualizar a página, 
        # as questões sorteadas continuem sendo as mesmas para ele.
        random.seed(str(st.session_state.aluno['id']))
        random.shuffle(pool_questoes)
        
        # Pegamos apenas a quantidade definida no 'qtd_sorteio'
        n_sorteio = prova.get('qtd_sorteio', len(pool_questoes))
        questoes_sorteadas = pool_questoes[:n_sorteio]
        
        st.session_state.questoes = questoes_sorteadas
        st.session_state.etapa = "em_prova"
        st.rerun()

# ==========================================
# ETAPA 3: PROVA (RANDOMIZAÇÃO DE ALTERNATIVAS)
# ==========================================
elif st.session_state.etapa == "em_prova":
    import streamlit.components.v1 as components
    # (Contador visual aqui...)
    
    with st.form("form_prova", clear_on_submit=False):
        for i, q in enumerate(st.session_state.questoes):
            st.markdown(f"**QUESTÃO {i+1}**")
            st.markdown(q['enunciado'], unsafe_allow_html=True)
            
            opcoes = q.get('alternativas', {})
            letras_disponiveis = [l for l in ["A", "B", "C", "D", "E"] if opcoes.get(l)]
            
            # RANDOMIZAÇÃO DAS ALTERNATIVAS (Semente única por Questão + Aluno)
            random.seed(f"{st.session_state.aluno['id']}-{q['id']}")
            ordem_alternativas = letras_disponiveis.copy()
            random.shuffle(ordem_alternativas)

            def limpar(t): return re.sub(r'^[A-Ea-e]\s*[\)\.\-]\s*', '', str(t)).strip()

            escolha = st.radio(
                f"Sua resposta para a Q{i+1}:",
                options=ordem_alternativas,
                format_func=lambda x: limpar(opcoes.get(x, "")),
                index=None, key=f"q_{q['id']}"
            )
            if escolha: st.session_state.respostas[q['id']] = escolha
            st.divider()
            
        enviar = st.form_submit_button("✅ FINALIZAR E ENVIAR", use_container_width=True, type="primary")

    if enviar:
        if len(st.session_state.respostas) < len(st.session_state.questoes):
            st.warning("Responda todas antes de enviar!")
        else:
            # Cálculo de nota baseado no valor individual configurado
            valor_cada = st.session_state.prova_config.get('valor_questao', 1.0)
            acertos = 0
            for q in st.session_state.questoes:
                if st.session_state.respostas.get(q['id']) == q['resposta_correta']:
                    acertos += 1
            
            nota_final = acertos * valor_cada
            # (Lógica de salvar no banco igual à anterior...)