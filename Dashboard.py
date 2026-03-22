import streamlit as st
from supabase import create_client
from streamlit_quill import st_quill
import plotly.express as px
import pandas as pd
import json
import pytz
from fpdf import FPDF
import base64
import re
from datetime import datetime
import time

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Gestão EREMPAM - Provas", layout="wide")

# --- 2. CONEXÃO COM SUPABASE ---
try:
    URL_P = st.secrets["SUPABASE_URL_PROVAS"]
    KEY_P = st.secrets["SUPABASE_KEY_PROVAS"]
    supabase = create_client(URL_P, KEY_P)

    URL_A = st.secrets["SUPABASE_URL_ALUNOS"]
    KEY_A = st.secrets["SUPABASE_KEY_ALUNOS"]
    supabase_alunos = create_client(URL_A, KEY_A)
except Exception as e:
    st.error(f"Erro ao carregar segredos do Supabase: {e}")
    st.stop()

# --- 3. SISTEMA DE LOGIN ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.title("🔐 Acesso Administrativo - EREMPAM")
    senha = st.text_input("Digite a senha de gestão:", type="password")
    if st.button("Entrar"):
        if senha == "erempam2024": 
            st.session_state.autenticado = True
            st.rerun()
        else:
            st.error("Senha incorreta.")
    st.stop()

# --- 4. MENU LATERAL ---
st.sidebar.title("🎮 Painel do Professor")
menu = st.sidebar.radio("Navegação", [
    "📊 Análise de Dados", 
    "📝 Cadastrar Questões", 
    "📚 Biblioteca de Questões", 
    "📜 Gerar Modelo de Prova",
    "📂 Provas Elaboradas"
])

# --- 5. LÓGICA DO DASHBOARD ---
if menu == "📊 Análise de Dados":
    st.title("📊 Análise de Dados e Diagnóstico")
    
    try:
        res_view = supabase.table("dashboard_diagnostico").select("*").execute()
        res_raw = supabase.table("resultados_provas").select("aluno_id").execute()
        res_alunos_base = supabase_alunos.table("alunos").select("id, turma").execute()
        
        df = pd.DataFrame(res_view.data)
        df_raw = pd.DataFrame(res_raw.data)
        df_alunos_base = pd.DataFrame(res_alunos_base.data)

        if not df.empty:
            # Tratamento de Strings para extração
            df['serie_curta'] = df['serie'].astype(str).str.extract(r'(1º|2º|3º)')
            df['letra_turma'] = df['serie'].astype(str).str.extract(r'([A-E])')
            df['serie_curta'] = df['serie_curta'].fillna("N/A")
            df['letra_turma'] = df['letra_turma'].fillna("Geral")

            st.markdown("### 🎯 Visão Geral")
            kpi1, kpi2, kpi3 = st.columns(3)
            
            total_estudantes_unicos = df_raw['aluno_id'].nunique() if not df_raw.empty else 0
            media_geral = df['perc_acerto'].mean()
            # Correção idxmax: só calcula se houver dados
            melhor_assunto = df.loc[df['perc_acerto'].idxmax()]['assunto'] if not df.empty else "N/A"

            kpi1.metric("Estudantes Únicos", int(total_estudantes_unicos))
            kpi2.metric("Média de Acertos", f"{media_geral:.1f}%")
            kpi3.metric("Assunto Domínio", str(melhor_assunto).upper())
            
            st.divider()
            
            # Filtros de Gráfico
            lista_series_filtro = sorted([s for s in df['serie_curta'].unique() if s != "N/A"])
            serie_foco = st.selectbox("🎯 Selecione a Série para detalhar:", ["Todas"] + lista_series_filtro)
            
            df_filtrado = df.copy()
            if serie_foco != "Todas":
                df_filtrado = df_filtrado[df_filtrado['serie_curta'] == serie_foco]

            col1, col2 = st.columns(2)
            with col1:
                st.subheader(f"Desempenho por Turma")
                fig = px.bar(df_filtrado, x="assunto", y="perc_acerto", color="letra_turma",
                             barmode="group", text_auto='.1f', color_discrete_sequence=px.colors.qualitative.Bold)
                st.plotly_chart(fig, use_container_width=True)
                
            with col2:
                st.subheader(f"Engajamento ({serie_foco})")
                if not df_raw.empty and not df_alunos_base.empty:
                    # Garantir que IDs são strings para o merge
                    df_raw['aluno_id'] = df_raw['aluno_id'].astype(str)
                    df_alunos_base['id'] = df_alunos_base['id'].astype(str)
                    
                    df_join = pd.merge(df_raw, df_alunos_base, left_on="aluno_id", right_on="id")
                    
                    if serie_foco != "Todas":
                        prefixo = serie_foco[0]
                        df_join = df_join[df_join['turma'].astype(str).str.startswith(prefixo)]
                    
                    if not df_join.empty:
                        df_pizza = df_join.groupby("turma").size().reset_index(name='total')
                        fig2 = px.pie(df_pizza, values='total', names='turma', hole=.4)
                        st.plotly_chart(fig2, use_container_width=True)
                    else:
                        st.info("Sem dados para esta série.")
        else:
            st.info("Aguardando dados de respostas para gerar análise.")

    except Exception as e:
        st.error(f"Erro ao processar Dashboard: {e}")

# --- 6. CADASTRO DE QUESTÕES ---
elif menu == "📝 Cadastrar Questões":
    st.title("🖊️ Criador de Atv. online")
    
    col_c1, col_c2, col_c3 = st.columns(3)
    serie_ctx = col_c1.selectbox("Série/Ano", ["1º Ano", "2º Ano", "3º Ano"])
    assunto_ctx = col_c2.text_input("Assunto Base")
    diff_ctx = col_c3.select_slider("Dificuldade", options=["Fácil", "Média", "Difícil"])

    with st.expander("🚀 IMPORTADOR JSON", expanded=True):
        json_input = st.text_area("Cole o JSON da IA aqui:", height=200)
        if st.button("📥 Importar em Lote"):
            try:
                lista_q = json.loads(json_input)
                if isinstance(lista_q, dict): lista_q = [lista_q]
                
                for q in lista_q:
                    # Lógica para detectar correta caso não venha explícito
                    letra_correta = q.get("resposta_correta", "A")
                    if "justificativas" in q:
                        for letra, fb in q["justificativas"].items():
                            if any(w in fb.lower() for w in ["corret", "parabéns", "exato"]):
                                letra_correta = letra
                    
                    supabase.table("questoes").insert({
                        "enunciado": q["enunciado"],
                        "alternativas": q["alternativas"],
                        "justificativas": q.get("justificativas", {}),
                        "resposta_correta": letra_correta,
                        "serie": q.get("serie", serie_ctx),
                        "assunto": q.get("assunto", assunto_ctx if assunto_ctx else "Geral"),
                        "dificuldade": q.get("dificuldade", diff_ctx)
                    }).execute()
                st.success("Questões importadas!")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"Erro no JSON: {e}")

# --- 9. PROVAS ELABORADAS ---
elif menu == "📂 Provas Elaboradas":
    st.title("📂 Gerenciar Provas")
    fuso = pytz.timezone('America/Recife')
    agora = datetime.now(fuso)
    
    res_provas = supabase.table("modelos_prova").select("*").order("id", desc=True).execute()
    
    if res_provas.data:
        for prova in res_provas.data:
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
                
                # Tratamento de Datas Nulas ou Inválidas
                dt_limite_raw = prova.get('data_limite')
                prazo_encerrado = False
                dt_str = "Sem prazo"
                
                if dt_limite_raw:
                    try:
                        # Limpa o formato da data para o fromisoformat
                        clean_dt = dt_limite_raw.split('+')[0].replace('Z', '')
                        dt_obj = datetime.fromisoformat(clean_dt).replace(tzinfo=pytz.UTC).astimezone(fuso)
                        dt_str = dt_obj.strftime('%d/%m/%Y %H:%M')
                        prazo_encerrado = agora > dt_obj
                    except:
                        dt_str = "Erro na data"

                c1.markdown(f"**{prova.get('titulo')}**")
                c1.caption(f"Série: {prova.get('serie')} | Fim: {dt_str}")
                
                status = "🟢 ATIVA" if prova.get('ativa') else "🔴 INATIVA"
                c2.write(status)
                
                # Engajamento
                p_id = prova.get('id')
                res_resp = supabase.table("resultados_provas").select("aluno_id", count="exact").eq("prova_id", p_id).execute()
                qtd = res_resp.count if res_resp.count is not None else 0
                c3.metric("Respostas", qtd)
                
                # Ações
                if c4.button("Alternar Status", key=f"btn_{p_id}"):
                    novo = not prova.get('ativa')
                    supabase.table("modelos_prova").update({"ativa": novo}).eq("id", p_id).execute()
                    st.rerun()