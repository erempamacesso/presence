import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from supabase import create_client, Client
import time
import re

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
# 2. CONEXÃO COM OS DOIS PROJETOS (IMPORTANTÍSSIMO)
# ==========================================
@st.cache_resource
def init_connections():
    # Conexão 1: Base de Alunos (SIGEREMPAM)
    db_alunos = create_client(st.secrets["SUPABASE_URL_ALUNOS"], st.secrets["SUPABASE_KEY_ALUNOS"])
    # Conexão 2: Base de Provas (AVALIADOR)
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
# ETAPA 1: LOGIN (Busca no Projeto Alunos)
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
                    # 1. Busca aluno na base SIGEREMPAM
                    res = db_alunos.table("alunos").select("*").eq("numero_matricula", matricula).execute()
                    
                    if res.data:
                        aluno_data = res.data[0]
                        st.session_state.aluno = aluno_data
                        
                        # --- 💡 LÓGICA DE TRADUÇÃO DE TURMA PARA SÉRIE ---
                        turma = aluno_data.get('turma', '')
                        serie_aluno = "1º Ano" # Valor padrão
                        
                        if "1" in turma: serie_aluno = "1º Ano"
                        elif "2" in turma: serie_aluno = "2º Ano"
                        elif "3" in turma: serie_aluno = "3º Ano"
                        # ------------------------------------------------
                        
                        # 2. Busca prova ativa na base AVALIADOR usando a série traduzida
                        res_p = db_provas.table("modelos_prova").select("*").eq("ativa", True).eq("serie", serie_aluno).limit(1).execute()
                        
                        if res_p.data:
                            st.session_state.prova_config = res_p.data[0]
                            st.session_state.etapa = "instrucoes"
                            st.rerun()
                        else:
                            st.warning(f"Olá {aluno_data['nome']}, não encontramos provas ativas para o {serie_aluno} ({turma}).")
                    else:
                        st.error("Matrícula não encontrada.")
                except Exception as e:
                    st.error(f"Erro ao conectar: {e}")

# ==========================================
# ETAPA 2: INSTRUÇÕES
# ==========================================
elif st.session_state.etapa == "instrucoes":
    aluno = st.session_state.aluno
    prova = st.session_state.prova_config
    
    st.header(f"👋 Bem-vindo(a), {aluno['nome']}!")
    
    with st.container(border=True):
        st.subheader(f"📝 {prova['titulo']}")
        st.write(f"**Série:** {prova['serie']} | **Duração:** {prova['tempo_duracao']} minutos")
        st.write(f"**Total de Questões:** {prova.get('qtd_questoes', 10)}")
        st.write(f"**Valor por Questão:** {prova.get('valor_questao', 1.0)} pontos")
        
        st.warning("⚠️ Uma vez iniciada, o tempo não para. Certifique-se de que sua conexão está estável.")
        
        if st.button("INICIAR PROVA AGORA", type="primary", use_container_width=True):
            st.session_state.tempo_final = datetime.now() + timedelta(minutes=prova['tempo_duracao'])
            # Busca as questões reais baseadas nos IDs salvos no modelo
            ids = prova.get('questoes_ids', [])
            res_q = db_provas.table("questoes").select("*").in_("id", ids).execute()
            st.session_state.questoes = res_q.data
            st.session_state.etapa = "em_prova"
            st.rerun()

# ==========================================
# ETAPA 3: REALIZAÇÃO DA PROVA
# ==========================================
elif st.session_state.etapa == "em_prova":
    import streamlit.components.v1 as components # Necessário para o cronômetro rodar

    # Cronômetro
    tempo_restante = st.session_state.tempo_final - datetime.now()
    segundos = int(tempo_restante.total_seconds())
    
    if segundos <= 0:
        st.error("⌛ TEMPO ESGOTADO!")
        # Lógica de envio automático poderia entrar aqui
        st.stop()
    
    # Cabeçalho Fixo
    col_a, col_b = st.columns([3, 1])
    with col_a:
        st.markdown(f"### ✍️ {st.session_state.prova_config['titulo']}")
        st.caption(f"Aluno: {st.session_state.aluno['nome']} | Turma: {st.session_state.aluno.get('turma', 'N/A')}")
    
    with col_b:
        # Cronômetro Dinâmico com HTML/JS
        html_cronometro = f"""
        <div style="font-family: sans-serif; text-align: center; background-color: #f8d7da; color: #721c24; padding: 10px; border-radius: 8px; border: 1px solid #f5c6cb;">
            <div style="font-size: 14px; font-weight: bold;">⏳ Tempo Restante</div>
            <div id="relogio" style="font-size: 24px; font-weight: bold; margin-top: 5px;"></div>
        </div>
        <script>
            // Pega o tempo do Python
            var segundosTotais = {segundos}; 
            
            var x = setInterval(function() {{
                var mins = Math.floor(segundosTotais / 60);
                var secs = Math.floor(segundosTotais % 60);
                
                // Adiciona o zero à esquerda
                var minsStr = mins < 10 ? "0" + mins : mins;
                var secsStr = secs < 10 ? "0" + secs : secs;
                
                document.getElementById("relogio").innerHTML = minsStr + ":" + secsStr;
                
                if (segundosTotais <= 0) {{
                    clearInterval(x);
                    document.getElementById("relogio").innerHTML = "ESGOTADO!";
                    document.getElementById("relogio").style.color = "red";
                }} else {{
                    segundosTotais--;
                }}
            }}, 1000);
        </script>
        """
        components.html(html_cronometro, height=85)

    st.divider()

    # Formulário de Questões
    with st.form("form_prova"):
        for i, q in enumerate(st.session_state.questoes):
            st.markdown(f"**QUESTÃO {i+1}**")
            st.markdown(q['enunciado'], unsafe_allow_html=True)
            
            # --- CORREÇÃO DAS ALTERNATIVAS ---
            # Puxa o dicionário/JSON da coluna 'alternativas'
            opcoes_dict = q.get('alternativas', {}) 
            
            # Transforma o dicionário em uma lista para o st.radio
            opcoes_lista = [f"{letra}) {texto}" for letra, texto in opcoes_dict.items()]
            
            escolha = st.radio(
                f"Selecione a alternativa da Q{i+1}:", 
                options=opcoes_lista, 
                index=None, 
                key=f"q_id_{q['id']}"
            )
            
            if escolha:
                st.session_state.respostas[q['id']] = escolha[0] # Salva só a letra (A, B...)
            
            st.write("---")
            
        entregar = st.form_submit_button("✅ FINALIZAR E ENVIAR PROVA", use_container_width=True)

    if entregar:
        # 1. Calcular Nota
        acertos = 0
        for q in st.session_state.questoes:
            if st.session_state.respostas.get(q['id']) == q['resposta_correta']:
                acertos += 1
        
        nota = acertos * st.session_state.prova_config.get('valor_questao', 1.0)
        
        # 2. Salvar no Banco (Projeto Provas)
        resultado = {
            "aluno_id": st.session_state.aluno['id'],
            "prova_id": st.session_state.prova_config['id'],
            "nota": nota,
            "respostas": st.session_state.respostas,
            "acertos": acertos
        }
        
        try:
            db_provas.table("resultados_provas").insert(resultado).execute()
            st.success(f"Prova enviada com sucesso! Nota calculada: {nota}")
            st.balloons()
            time.sleep(5)
            # Limpa estado e volta pro login
            for key in list(st.session_state.keys()): del st.session_state[key]
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao salvar resultado: {e}")