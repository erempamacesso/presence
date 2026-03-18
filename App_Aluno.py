import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from supabase import create_client, Client
import time
import re
import random 

# ==========================================
# 1. CONFIGURAÇÕES E ESTILO
# ==========================================
st.set_page_config(page_title="Portal do Aluno - EREMPAM", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
        [data-testid="stSidebar"] {display: none;}
        .stButton>button {border-radius: 8px; height: 3em;}
        .timer-container {
            position: sticky;
            top: 0;
            z-index: 999;
            background-color: white;
            padding: 10px 0;
            border-bottom: 2px solid #eee;
        }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. CONEXÃO
# ==========================================
@st.cache_resource
def init_connections():
    db_alunos = create_client(st.secrets["SUPABASE_URL_ALUNOS"], st.secrets["SUPABASE_KEY_ALUNOS"])
    db_provas = create_client(st.secrets["SUPABASE_URL_PROVAS"], st.secrets["SUPABASE_KEY_PROVAS"])
    return db_alunos, db_provas

db_alunos, db_provas = init_connections()

# ==========================================
# 3. ESTADO
# ==========================================
for key in ['etapa', 'aluno', 'prova_config', 'tempo_final', 'questoes', 'respostas']:
    if key not in st.session_state:
        if key == 'etapa': st.session_state[key] = "login"
        elif key == 'respostas': st.session_state[key] = {}
        else: st.session_state[key] = None

# ==========================================
# ETAPA 1: LOGIN
# ==========================================
if st.session_state.etapa == "login":
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🚀 Portal de Avaliações")
        matricula = st.text_input("Digite sua Matrícula")
        
        if st.button("ACESSAR SISTEMA", use_container_width=True):
            if matricula:
                res = db_alunos.table("alunos").select("*").eq("numero_matricula", matricula).execute()
                if res.data:
                    aluno_data = res.data[0]
                    st.session_state.aluno = aluno_data
                    
                    turma = aluno_data.get('turma', '')
                    serie_aluno = "1º Ano"
                    if "1" in turma: serie_aluno = "1º Ano"
                    elif "2" in turma: serie_aluno = "2º Ano"
                    elif "3" in turma: serie_aluno = "3º Ano"
                    
                    res_p = db_provas.table("modelos_prova").select("*").eq("ativa", True).eq("serie", serie_aluno).limit(1).execute()
                    
                    if res_p.data:
                        prova_ativa = res_p.data[0]
                        ja_fez = db_provas.table("resultados_provas").select("id").eq("aluno_id", str(aluno_data['id'])).eq("prova_id", prova_ativa['id']).limit(1).execute()
                        
                        if ja_fez.data:
                            st.warning("⚠️ Você já enviou esta avaliação.")
                        else:
                            st.session_state.prova_config = prova_ativa
                            st.session_state.etapa = "instrucoes"
                            st.rerun()
                    else:
                        st.warning(f"Sem provas ativas para o {serie_aluno}.")
                else:
                    st.error("Matrícula não encontrada.")

# ==========================================
# ETAPA 2: INSTRUÇÕES
# ==========================================
elif st.session_state.etapa == "instrucoes":
    aluno = st.session_state.aluno
    prova = st.session_state.prova_config
    st.header(f"👋 Olá, {aluno['nome']}!")
    
    with st.container(border=True):
        st.subheader(f"📝 {prova['titulo']}")
        st.write(f"Série: {prova['serie']} | Tempo: {prova['tempo_duracao']} min")
        
        if st.button("INICIAR PROVA", type="primary", use_container_width=True):
            st.session_state.tempo_final = datetime.now() + timedelta(minutes=prova['tempo_duracao'])
            ids = prova.get('questoes_ids', [])
            res_q = db_provas.table("questoes").select("*").in_("id", ids).execute()
            
            lista_q = res_q.data
            random.seed(str(st.session_state.aluno['id']))
            random.shuffle(lista_q)
            
            st.session_state.questoes = lista_q
            st.session_state.etapa = "em_prova"
            st.rerun()

# ==========================================
# ETAPA 3: PROVA (COM CONTADOR)
# ==========================================
elif st.session_state.etapa == "em_prova":
    import streamlit.components.v1 as components
    
    restante = st.session_state.tempo_final - datetime.now()
    segs = int(restante.total_seconds())
    
    if segs <= 0:
        st.error("⌛ Tempo esgotado!")
        st.stop()

    # --- CABEÇALHO COM CONTADOR ---
    col_a, col_b = st.columns([3, 1])
    with col_a:
        st.markdown(f"### ✍️ {st.session_state.prova_config['titulo']}")
        st.caption(f"Aluno: {st.session_state.aluno['nome']}")
    
    with col_b:
        # Renderização do cronômetro visual
        html_cronometro = f"""
        <div style="font-family: sans-serif; text-align: center; background-color: #f8d7da; color: #721c24; padding: 10px; border-radius: 8px; border: 1px solid #f5c6cb;">
            <div style="font-size: 12px; font-weight: bold;">⏳ TEMPO RESTANTE</div>
            <div id="relogio" style="font-size: 22px; font-weight: bold; margin-top: 2px;"></div>
        </div>
        <script>
            var s = {segs}; 
            function tick() {{
                var m = Math.floor(s / 60);
                var seg = s % 60;
                document.getElementById("relogio").innerHTML = (m<10?"0"+m:m) + ":" + (seg<10?"0"+seg:seg);
                if (s > 0) {{ s--; setTimeout(tick, 1000); }}
                else {{ document.getElementById("relogio").innerHTML = "FIM!"; }}
            }}
            tick();
        </script>
        """
        components.html(html_cronometro, height=90)

    st.divider()

    with st.form("form_prova", clear_on_submit=False):
        for i, q in enumerate(st.session_state.questoes):
            st.markdown(f"**QUESTÃO {i+1}**")
            st.markdown(q['enunciado'], unsafe_allow_html=True)
            
            opcoes = q.get('alternativas', {})
            letras = [l for l in ["A", "B", "C", "D", "E"] if opcoes.get(l)]
            
            # Embaralha alternativas (Semente: ID Aluno + ID Questão)
            random.seed(f"{st.session_state.aluno['id']}-{q['id']}")
            ordem = letras.copy()
            random.shuffle(ordem)

            def limpar(t):
                return re.sub(r'^[A-Ea-e]\s*[\)\.\-]\s*', '', str(t)).strip()

            escolha = st.radio(
                f"Escolha uma opção:",
                options=ordem,
                format_func=lambda x: limpar(opcoes.get(x, "")),
                index=None,
                key=f"q_{q['id']}"
            )
            if escolha:
                st.session_state.respostas[q['id']] = escolha
            st.divider()
            
        enviar = st.form_submit_button("✅ FINALIZAR E ENVIAR", use_container_width=True, type="primary")

    if enviar:
        if len(st.session_state.respostas) < len(st.session_state.questoes):
            st.warning("⚠️ Responda todas as questões antes de enviar!")
        else:
            acertos = 0
            for q in st.session_state.questoes:
                if st.session_state.respostas.get(q['id']) == q['resposta_correta']:
                    acertos += 1
            
            lista_res = []
            for q in st.session_state.questoes:
                resp = st.session_state.respostas.get(q['id'])
                lista_res.append({
                    "aluno_id": str(st.session_state.aluno['id']),
                    "prova_id": st.session_state.prova_config['id'],
                    "questao_id": q['id'],
                    "resposta_aluno": resp,
                    "acertou": (resp == q['resposta_correta']),
                    "acertos": acertos
                })
            
            try:
                db_provas.table("resultados_provas").insert(lista_res).execute()
                st.success(f"🎉 Prova enviada com sucesso! Você acertou {acertos} questões.")
                st.balloons()
                time.sleep(3)
                for k in list(st.session_state.keys()): del st.session_state[k]
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao salvar: {e}")