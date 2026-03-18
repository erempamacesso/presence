import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from supabase import create_client, Client
import time
import re
import random # <--- Essencial para o embaralhamento

# ==========================================
# 1. CONFIGURAÇÕES E ESTILO
# ==========================================
st.set_page_config(page_title="Portal do Aluno - EREMPAM", layout="wide", initial_sidebar_state="collapsed")

# CSS para esconder menu e dar um ar profissional
st.markdown("""
    <style>
        [data-testid="stSidebar"] {display: none;}
        .main .block-container {padding-top: 2rem;}
        .stButton>button {border-radius: 8px; height: 3em;}
        .prova-header {background-color: #f0f2f6; padding: 20px; border-radius: 10px; margin-bottom: 20px;}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. CONEXÃO COM OS DOIS PROJETOS
# ==========================================
@st.cache_resource
def init_connections():
    db_alunos = create_client(st.secrets["SUPABASE_URL_ALUNOS"], st.secrets["SUPABASE_KEY_ALUNOS"])
    db_provas = create_client(st.secrets["SUPABASE_URL_PROVAS"], st.secrets["SUPABASE_KEY_PROVAS"])
    return db_alunos, db_provas

db_alunos, db_provas = init_connections()

# ==========================================
# 3. INICIALIZAÇÃO DO ESTADO (MEMÓRIA)
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
        st.image("logo_erempam.png", width=150)
        st.title("🚀 Portal de Avaliações")
        
        matricula = st.text_input("Digite sua Matrícula", key="input_matricula_aluno")
        
        if st.button("ACESSAR SISTEMA", use_container_width=True, key="btn_login"):
            if matricula:
                try:
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
                                st.warning(f"⚠️ Olá, {aluno_data['nome']}! Você já enviou esta avaliação.")
                            else:
                                st.session_state.prova_config = prova_ativa
                                st.session_state.etapa = "instrucoes"
                                st.rerun()
                        else:
                            st.warning(f"Olá {aluno_data['nome']}, sem provas ativas para sua série.")
                    else:
                        st.error("Matrícula não encontrada.")
                except Exception as e:
                    st.error(f"Erro ao conectar: {e}")

# ==========================================
# ETAPA 2: INSTRUÇÕES E CARREGAMENTO (EMBARALHADO)
# ==========================================
elif st.session_state.etapa == "instrucoes":
    aluno = st.session_state.aluno
    prova = st.session_state.prova_config
    
    st.header(f"👋 Bem-vindo(a), {aluno['nome']}!")
    
    with st.container(border=True):
        st.subheader(f"📝 {prova['titulo']}")
        st.write(f"**Duração:** {prova['tempo_duracao']} minutos")
        
        if st.button("INICIAR PROVA AGORA", type="primary", use_container_width=True):
            st.session_state.tempo_final = datetime.now() + timedelta(minutes=prova['tempo_duracao'])
            
            # Busca as questões
            ids = prova.get('questoes_ids', [])
            res_q = db_provas.table("questoes").select("*").in_("id", ids).execute()
            lista_questoes = res_q.data
            
            # --- EMBARALHAR ORDEM DAS QUESTÕES ---
            random.seed(st.session_state.aluno['id']) 
            random.shuffle(lista_questoes)
            
            st.session_state.questoes = lista_questoes
            st.session_state.etapa = "em_prova"
            st.rerun()

# ==========================================
# ETAPA 3: REALIZAÇÃO DA PROVA (ALTERNATIVAS EMBARALHADAS)
# ==========================================
elif st.session_state.etapa == "em_prova":
    import streamlit.components.v1 as components

    tempo_restante = st.session_state.tempo_final - datetime.now()
    segundos = int(tempo_restante.total_seconds())
    
    if segundos <= 0:
        st.error("⌛ TEMPO ESGOTADO!")
        st.stop()
    
    col_a, col_b = st.columns([3, 1])
    with col_a:
        st.markdown(f"### ✍️ {st.session_state.prova_config['titulo']}")
    
    with col_b:
        html_cronometro = f"""
        <div style="font-family: sans-serif; text-align: center; background-color: #f8d7da; color: #721c24; padding: 10px; border-radius: 8px;">
            <div id="relogio" style="font-size: 24px; font-weight: bold;"></div>
        </div>
        <script>
            var segs = {segundos}; 
            setInterval(function() {{
                var m = Math.floor(segs / 60); var s = segs % 60;
                document.getElementById("relogio").innerHTML = (m<10?"0"+m:m) + ":" + (s<10?"0"+s:s);
                if (segs > 0) segs--;
            }}, 1000);
        </script>
        """
        components.html(html_cronometro, height=85)

    st.divider()

    with st.form("form_prova"):
        for i, q in enumerate(st.session_state.questoes):
            st.markdown(f"**QUESTÃO {i+1}**")
            st.markdown(q['enunciado'], unsafe_allow_html=True)
            
            # --- LÓGICA DE ALTERNATIVAS EMBARALHADAS ---
            opcoes_dict = q.get('alternativas', {}) 
            letras_originais = [l for l in ["A", "B", "C", "D", "E"] if opcoes_dict.get(l)]
            
            ordem_exibicao = letras_originais.copy()
            # Semente única por questão para o aluno
            random.seed(int(str(st.session_state.aluno['id']) + str(q['id'])))
            random.shuffle(ordem_exibicao)

            def limpar_texto(texto):
                return re.sub(r'^[A-Ea-e]\s*[\)\.\-]\s*', '', str(texto)).strip()

            escolha = st.radio(
                f"Selecione a opção da Q{i+1}:", 
                options=ordem_exibicao, 
                format_func=lambda x: limpar_texto(opcoes_dict.get(x, "")),
                index=None, 
                key=f"q_id_{q['id']}"
            )
            
            if escolha:
                st.session_state.respostas[q['id']] = escolha 
            st.write("---")
            
        entregar = st.form_submit_button("✅ FINALIZAR E ENVIAR PROVA", use_container_width=True)

    if entregar:
        acertos_totais = 0
        for q in st.session_state.questoes:
            if st.session_state.respostas.get(q['id']) == q['resposta_correta']:
                acertos_totais += 1
                
        nota_final = acertos_totais * st.session_state.prova_config.get('valor_questao', 1.0)
        lista_resultados = []
        
        for q in st.session_state.questoes:
            resp = st.session_state.respostas.get(q['id'])
            lista_resultados.append({
                "aluno_id": str(st.session_state.aluno['id']), 
                "prova_id": st.session_state.prova_config['id'],
                "questao_id": q['id'],
                "resposta_aluno": resp,
                "acertou": (resp == q['resposta_correta']),
                "acertos": acertos_totais
            })
        
        try:
            db_provas.table("resultados_provas").insert(lista_resultados).execute()
            st.success(f"🎉 Enviado! Acertos: {acertos_totais}. Nota: {nota_final}")
            st.balloons()
            time.sleep(5)
            for key in list(st.session_state.keys()): del st.session_state[key]
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao salvar: {e}")