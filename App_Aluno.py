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
# Deve ser a PRIMEIRA coisa do script
st.set_page_config(page_title="Portal do Aluno - EREMPAM", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
        [data-testid="stSidebar"] {display: none;}
        .stButton>button {border-radius: 8px; height: 3em;}
        .timer-container {
            position: sticky; top: 0; z-index: 999;
            background-color: white; padding: 10px 0;
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

try:
    db_alunos, db_provas = init_connections()
except Exception as e:
    st.error(f"Erro de Conexão: {e}")
    st.stop()

# ==========================================
# 3. ESTADO (INICIALIZAÇÃO)
# ==========================================
if 'etapa' not in st.session_state: st.session_state.etapa = "login"
if 'respostas' not in st.session_state: st.session_state.respostas = {}
if 'aluno' not in st.session_state: st.session_state.aluno = None
if 'prova_config' not in st.session_state: st.session_state.prova_config = None
if 'questoes' not in st.session_state: st.session_state.questoes = []
if 'tempo_final' not in st.session_state: st.session_state.tempo_final = None

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
                    
                    turma = str(aluno_data.get('turma', ''))
                    serie_aluno = "1º Ano"
                    if "2" in turma: serie_aluno = "2º Ano"
                    elif "3" in turma: serie_aluno = "3º Ano"
                    
                    # Busca prova ativa para a série
                    res_p = db_provas.table("modelos_prova").select("*").eq("ativa", True).eq("serie", serie_aluno).limit(1).execute()
                    
                    if res_p.data:
                        prova_ativa = res_p.data[0]
                        # Verifica se já enviou
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
# ETAPA 2: INSTRUÇÕES E SORTEIO
# ==========================================
elif st.session_state.etapa == "instrucoes":
    aluno = st.session_state.aluno
    prova = st.session_state.prova_config
    st.header(f"👋 Olá, {aluno['nome']}!")
    
    with st.container(border=True):
        st.subheader(f"📝 {prova['titulo']}")
        st.write(f"Série: {prova['serie']} | Tempo: {prova['tempo_duracao']} min")
        st.info("Ao clicar em iniciar, o tempo começará a contar e não poderá ser pausado.")
        
        if st.button("INICIAR PROVA", type="primary", use_container_width=True):
            # 1. Define tempo final
            st.session_state.tempo_final = datetime.now() + timedelta(minutes=prova['tempo_duracao'])
            
            # 2. Busca o POOL completo de questões
            ids = prova.get('questoes_ids', [])
            res_q = db_provas.table("questoes").select("*").in_("id", ids).execute()
            pool_questoes = res_q.data
            
            # 3. Lógica de SORTEIO (Ex: Pega 5 de 15)
            # Usamos o ID do aluno como semente para o sorteio ser fixo para ele
            random.seed(str(aluno['id']))
            random.shuffle(pool_questoes)
            
            # Quantidade definida no banco (ou tudo se não houver regra)
            n_sorteio = prova.get('qtd_sorteio', len(pool_questoes))
            st.session_state.questoes = pool_questoes[:n_sorteio]
            
            st.session_state.etapa = "em_prova"
            st.rerun()

# ==========================================
# ETAPA 3: EXECUÇÃO DA PROVA
# ==========================================
elif st.session_state.etapa == "em_prova":
    import streamlit.components.v1 as components
    
    # Validação de Segurança
    if not st.session_state.tempo_final:
        st.session_state.etapa = "login"
        st.rerun()

    restante = st.session_state.tempo_final - datetime.now()
    segs = int(restante.total_seconds())
    
    if segs <= 0:
        st.error("⌛ Tempo esgotado!")
        st.stop()

    # Cabeçalho Fixo
    col_a, col_b = st.columns([3, 1])
    with col_a:
        st.markdown(f"### ✍️ {st.session_state.prova_config['titulo']}")
        st.caption(f"Aluno: {st.session_state.aluno['nome']}")
    
    with col_b:
        html_cronometro = f"""
        <div style="font-family:sans-serif; text-align:center; background:#f8d7da; color:#721c24; padding:10px; border-radius:8px; border:1px solid #f5c6cb;">
            <div style="font-size:12px; font-weight:bold;">⏳ RESTAM</div>
            <div id="relogio" style="font-size:22px; font-weight:bold;"></div>
        </div>
        <script>
            var s = {segs};
            function tick() {{
                var m = Math.floor(s/60); var seg = s%60;
                document.getElementById("relogio").innerHTML = (m<10?"0"+m:m) + ":" + (seg<10?"0"+seg:seg);
                if (s > 0) {{ s--; setTimeout(tick, 1000); }}
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
            
            # Randomiza as alternativas por aluno+questão
            random.seed(f"{st.session_state.aluno['id']}-{q['id']}")
            ordem = letras.copy()
            random.shuffle(ordem)

            def limpar(t): return re.sub(r'^[A-Ea-e]\s*[\)\.\-]\s*', '', str(t)).strip()

            escolha = st.radio(
                "Selecione a resposta:",
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
            with st.spinner("Enviando respostas..."):
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
                        "acertos": acertos # Score total
                    })
                
                try:
                    db_provas.table("resultados_provas").insert(lista_res).execute()
                    st.success(f"🎉 Prova enviada! Acertos: {acertos}")
                    st.balloons()
                    time.sleep(3)
                    st.session_state.clear() # Limpa tudo para o próximo
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")