import streamlit as st
from supabase import create_client
from streamlit_quill import st_quill
import plotly.express as px
import pandas as pd
import uuid

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Gestão EREMPAM - Provas", layout="wide")

# --- CONEXÃO COM SUPABASE (SECRETS) ---
# Use as chaves do seu banco de PROVAS aqui
URL = st.secrets["SUPABASE_URL_PROVAS"]
KEY = st.secrets["SUPABASE_KEY_PROVAS"]
supabase = create_client(URL, KEY)

# --- SISTEMA DE LOGIN SIMPLES ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.title("🔐 Acesso Administrativo")
    senha = st.text_input("Digite a senha de gestão:", type="password")
    if st.button("Entrar"):
        if senha == "erempam2024": # Altere para sua senha de preferência
            st.session_state.autenticado = True
            st.rerun()
        else:
            st.error("Senha incorreta.")
    st.stop()

# --- MENU LATERAL ---
menu = st.sidebar.radio("Navegação", ["📊 Dashboard Diagnóstico", "📝 Cadastrar Questões", "📜 Gerar Modelo de Prova"])

# --- 1. DASHBOARD DIAGNÓSTICO ---
if menu == "📊 Dashboard Diagnóstico":
    st.title("📊 Diagnóstico em Tempo Real")
    
    try:
        # Busca dados da View que criamos via SQL
        res = supabase.table("dashboard_diagnostico").select("*").execute()
        df = pd.DataFrame(res.data)
        
        if not df.empty:
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Acertos por Assunto")
                fig = px.bar(df, x="assunto", y="perc_acerto", color="serie", barmode="group", text_auto='.1f')
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.subheader("Engajamento por Turma")
                fig2 = px.pie(df, values='total_respostas', names='serie', hole=.4)
                st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Nenhum dado de resposta encontrado ainda.")
    except:
        st.warning("Aguardando respostas dos alunos ou criação da View no SQL.")

# --- 2. CADASTRO DE QUESTÕES (COM DIAGNÓSTICO) ---
elif menu == "📝 Cadastrar Questões":
    st.title("🖋️ Elaborador de Questões Profissional")
    
    with st.form("nova_questao", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1: serie = st.selectbox("Série/Ano", ["1º Ano", "2º Ano", "3º Ano"])
        with col2: assunto = st.text_input("Assunto (ex: Funções)")
        with col3: dificuldade = st.select_slider("Dificuldade", options=["Fácil", "Média", "Difícil"])
        
        st.write("### Enunciado (ReactQuill)")
        enunciado_html = st_quill(placeholder="Cole aqui o texto da questão...", html=True, key="quill_editor")
        
        st.divider()
        st.write("### Alternativas e Diagnósticos 🧠")
        st.caption("Escreva a alternativa e, ao lado, o feedback que o aluno receberá se marcar esta opção.")
        
        # Usando colunas para organizar o layout (Texto da Letra | Diagnóstico)
        col_A_txt, col_A_fb = st.columns([1, 2])
        with col_A_txt: a = st.text_input("Letra A")
        with col_A_fb: fb_a = st.text_input("Diagnóstico A", placeholder="Ex: Esqueceu o sinal negativo...", key="fb_a")

        col_B_txt, col_B_fb = st.columns([1, 2])
        with col_B_txt: b = st.text_input("Letra B")
        with col_B_fb: fb_b = st.text_input("Diagnóstico B", placeholder="Ex: Faltou converter a unidade...", key="fb_b")

        col_C_txt, col_C_fb = st.columns([1, 2])
        with col_C_txt: c = st.text_input("Letra C")
        with col_C_fb: fb_c = st.text_input("Diagnóstico C", placeholder="Ex: Correto! Aplicou a fórmula certa.", key="fb_c")

        col_D_txt, col_D_fb = st.columns([1, 2])
        with col_D_txt: d = st.text_input("Letra D")
        with col_D_fb: fb_d = st.text_input("Diagnóstico D", placeholder="Ex: Confundiu velocidade com aceleração...", key="fb_d")
        
        correta = st.selectbox("Qual é a Correta?", ["A", "B", "C", "D"])
        
        if st.form_submit_button("💾 Salvar no Banco de Dados"):
            dados = {
                "enunciado": enunciado_html,
                "alternativas": {"A": a, "B": b, "C": c, "D": d},
                "justificativas": {"A": fb_a, "B": fb_b, "C": fb_c, "D": fb_d}, # <-- O PULO DO GATO AQUI
                "resposta_correta": correta,
                "serie": serie,
                "assunto": assunto,
                "dificuldade": dificuldade
            }
            supabase.table("questoes").insert(dados).execute()
            st.success("Questão com inteligência diagnóstica cadastrada com sucesso!")

# --- 3. GERADOR DE PROVAS ---
elif menu == "📜 Gerar Modelo de Prova":
    st.title("🎲 Gerar Novo Modelo de Prova")
    st.write("Agrupe questões existentes para criar uma prova ativa.")
    
    res_q = supabase.table("questoes").select("id, assunto, serie").execute()
    df_q = pd.DataFrame(res_q.data)
    
    if not df_q.empty:
        titulo = st.text_input("Título da Prova (ex: 1º Simulado Bimestral)")
        serie_prova = st.selectbox("Série alvo", ["1º Ano", "2º Ano", "3º Ano"])
        
        # Filtra questões da série selecionada
        questoes_disponiveis = df_q[df_q['serie'] == serie_prova]
        selecionadas = st.multiselect("Selecione as questões:", 
                                      options=questoes_disponiveis['id'].tolist(),
                                      format_func=lambda x: f"ID: {x} | Assunto: {questoes_disponiveis[questoes_disponiveis['id']==x]['assunto'].values[0]}")
        
        if st.button("🚀 Publicar Prova para Alunos"):
            if selecionadas and titulo:
                # Criamos o modelo de prova que o App_Aluno vai ler
                supabase.table("modelos_prova").insert({
                    "titulo": titulo,
                    "serie": serie_prova,
                    "questoes_ids": selecionadas, # JSONB no banco
                    "ativa": True
                }).execute()
                st.success(f"Prova '{titulo}' está ONLINE para o {serie_prova}!")
            else:
                st.error("Dê um título e selecione ao menos uma questão.")