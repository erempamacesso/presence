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
                        
                        # --- LÓGICA DE TRADUÇÃO DE TURMA PARA SÉRIE ---
                        turma = aluno_data.get('turma', '')
                        serie_aluno = "1º Ano" # Valor padrão
                        
                        if "1" in turma: serie_aluno = "1º Ano"
                        elif "2" in turma: serie_aluno = "2º Ano"
                        elif "3" in turma: serie_aluno = "3º Ano"
                        
                        # 2. Busca prova ativa na base AVALIADOR usando a série traduzida
                        res_p = db_provas.table("modelos_prova").select("*").eq("ativa", True).eq("serie", serie_aluno).limit(1).execute()
                        
                        if res_p.data:
                            prova_ativa = res_p.data[0]
                            
                            # --- 🔒 NOVA TRAVA DE SEGURANÇA: Verifica se o aluno já fez a prova ---
                            # Converte o ID do aluno para string pois na tabela resultados_provas ele é text
                            ja_fez = db_provas.table("resultados_provas") \
                                .select("id") \
                                .eq("aluno_id", str(aluno_data['id'])) \
                                .eq("prova_id", prova_ativa['id']) \
                                .limit(1) \
                                .execute()
                            
                            if ja_fez.data:
                                # Se encontrou registro, exibe o aviso e bloqueia
                                st.warning(f"⚠️ Olá, {aluno_data['nome']}! Nosso sistema registra que você já enviou esta avaliação. Não é permitido refazer a prova.")
                            else:
                                # Se não encontrou, libera o acesso
                                st.session_state.prova_config = prova_ativa
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
            
            # --- CORREÇÃO DAS ALTERNATIVAS (CÓDIGO NOVO E BLINDADO) ---
            opcoes_dict = q.get('alternativas', {}) 
            # Pega as letras disponíveis para essa questão específica
            letras_disponiveis = [letra for letra in ["A", "B", "C", "D", "E"] if opcoes_dict.get(letra)]
            
            # Função para limpar sujeira (caso o texto no banco já tenha "A) ")
            def limpar_texto(texto):
                return re.sub(r'^[A-Ea-e]\s*[\)\.\-]\s*', '', str(texto)).strip()

            escolha = st.radio(
                f"Selecione a alternativa da Q{i+1}:", 
                options=letras_disponiveis, 
                format_func=lambda x: limpar_texto(opcoes_dict.get(x, "")),
                index=None, 
                key=f"q_id_{q['id']}"
            )
            
            if escolha:
                # Agora salvamos direto a escolha, que é a letra pura (A, B, C...)
                st.session_state.respostas[q['id']] = escolha 
            
            st.write("---")
            
        entregar = st.form_submit_button("✅ FINALIZAR E ENVIAR PROVA", use_container_width=True)

    if entregar:
        # 1. Primeiro, calculamos o total de acertos e a nota final
        acertos_totais = 0
        for q in st.session_state.questoes:
            resposta_dada = st.session_state.respostas.get(q['id'])
            if resposta_dada == q['resposta_correta']:
                acertos_totais += 1
                
        nota_final = acertos_totais * st.session_state.prova_config.get('valor_questao', 1.0)
        
        # 2. Preparamos a lista com os resultados questão por questão
        lista_resultados = []
        
        for q in st.session_state.questoes:
            resposta_dada = st.session_state.respostas.get(q['id'])
            acertou = (resposta_dada == q['resposta_correta'])
            
            linha = {
                # Transformando o ID do aluno em texto porque na sua tabela aluno_id é text
                "aluno_id": str(st.session_state.aluno['id']), 
                "prova_id": st.session_state.prova_config['id'],
                "questao_id": q['id'],
                "resposta_aluno": resposta_dada,
                "acertou": acertou,
                "acertos": acertos_totais # Salvamos o total de acertos da prova aqui também!
            }
            lista_resultados.append(linha)
        
        # 3. Enviamos tudo de uma vez para o banco de dados
        try:
            db_provas.table("resultados_provas").insert(lista_resultados).execute()
            
            st.success(f"🎉 Prova enviada com sucesso! Você acertou {acertos_totais} questões. Nota: {nota_final}")
            st.balloons()
            time.sleep(5)
            
            # Limpa estado e volta pro login para o próximo aluno
            for key in list(st.session_state.keys()): 
                del st.session_state[key]
            st.rerun()
            
        except Exception as e:
            st.error(f"Erro ao salvar resultado: {e}")