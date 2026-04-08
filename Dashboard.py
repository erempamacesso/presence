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
import unicodedata
import io
from streamlit_option_menu import option_menu

# --- PROTEÇÃO PARA O WHATSAPP ---
try:
    import pywhatkit as kit
    WHATSAPP_LOCAL = True
except ImportError:
    WHATSAPP_LOCAL = False
              
# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Gestão EREMPAM - Provas", layout="wide")

# --- 2. CONEXÃO COM SUPABASE ---
URL_P = st.secrets["SUPABASE_URL_PROVAS"]
KEY_P = st.secrets["SUPABASE_KEY_PROVAS"]
supabase = create_client(URL_P, KEY_P)

URL_A = st.secrets["SUPABASE_URL_ALUNOS"]
KEY_A = st.secrets["SUPABASE_KEY_ALUNOS"]
supabase_alunos = create_client(URL_A, KEY_A)

# --- 3. SISTEMA DE LOGIN (ESTADO) ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = True # Mude para False se quiser tela de senha

if not st.session_state.autenticado:
    st.title("🔒 Acesso Restrito")
    senha = st.text_input("Digite a senha de acesso:", type="password")
    if st.button("Entrar"):
        if senha == st.secrets.get("SENHA_SISTEMA", "123"):
            st.session_state.autenticado = True
            st.rerun()
        else:
            st.error("Senha incorreta.")
    st.stop()

# --- 4. MENU LATERAL ---
with st.sidebar:
    st.title("🎮 Painel do Professor")
    
    menu = option_menu(
        menu_title="Navegação",  
        options=[
            "Análise de Dados", 
            "Cadastrar Questões", 
            "Biblioteca de Questões", 
            "Gerar Modelo de Prova",
            "Provas Elaboradas",
            "Lista de Matrículas",
            "Central de Avisos",
            "Diagnósticos IA",
            "Boletim Final SIEPE"
        ],
        icons=[
            "bar-chart-fill", "pencil-square", "book", "file-earmark-text",
            "folder-check", "people-fill", "bell-fill", "robot", "bank"
        ],
        menu_icon="cast",
        default_index=0,
        styles={
            "container": {"padding": "0!important", "background-color": "transparent"},
            "icon": {"color": "#ff9800", "font-size": "18px"}, 
            "nav-link": {"font-size": "15px", "text-align": "left", "margin":"0px"},
            "nav-link-selected": {"background-color": "#4CAF50"}, 
        }
    )
    st.sidebar.divider()
    if st.sidebar.button("🚪 Sair do Sistema", use_container_width=True):
        st.session_state.autenticado = False
        st.rerun()

# --- 5. LÓGICA DAS PÁGINAS ---

if menu == "Análise de Dados":
    st.title("📊 Análise de Dados e Notas")
    
    try:
        res_raw = supabase.table("resultados_provas").select("aluno_id, questao_id, acertou").execute()
        if res_raw.data:
            df_raw = pd.DataFrame(res_raw.data)
            st.subheader("🎯 Visão Geral")
            col_k1, col_k2 = st.columns(2)
            col_k1.metric("Total de Respostas", len(df_raw))
            col_k2.metric("Alunos Participantes", df_raw['aluno_id'].nunique())
    except:
        st.info("Aguardando dados de respostas para gerar estatísticas.")

    st.divider()
    st.subheader("🏆 Desempenho por Aluno")
    
    res_p_modelos = supabase.table("modelos_prova").select("id, titulo, valor_questao").order("id", desc=True).execute()
    
    if res_p_modelos.data:
        provas_dict = {p['titulo']: p for p in res_p_modelos.data}
        prova_nome = st.selectbox("Selecione a Prova para detalhar:", list(provas_dict.keys()))
        prova_obj = provas_dict[prova_nome]
        id_prova = prova_obj['id']
        valor_q = float(prova_obj.get('valor_questao', 1.0))

        res_res = supabase.table("resultados_provas").select("*").eq("prova_id", id_prova).execute()
        
        if res_res.data:
            df_res = pd.DataFrame(res_res.data)
            df_res['pontos'] = df_res['acertou'].apply(lambda x: 1 if x is True else 0)
            
            df_notas = df_res.groupby('aluno_id').agg(total_acertos=('pontos', 'sum')).reset_index()
            df_notas['nota_final'] = df_notas['total_acertos'] * valor_q
            
            # Buscar nomes dos alunos
            ids_alunos = df_notas['aluno_id'].unique().tolist()
            res_al = supabase_alunos.table("alunos").select("id, nome, turma").in_("id", ids_alunos).execute()
            df_alunos_nomes = pd.DataFrame(res_al.data)
            
            df_tela = pd.merge(df_alunos_nomes, df_notas, left_on="id", right_on="aluno_id")
            st.dataframe(df_tela[["nome", "turma", "total_acertos", "nota_final"]].sort_values("nome"), use_container_width=True)

            if st.button("📊 Exportar Relatório Excel por Turma"):
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    for turma in sorted(df_tela['turma'].unique()):
                        df_turma = df_tela[df_tela['turma'] == turma].copy()
                        df_turma.to_excel(writer, sheet_name=f"Turma {turma}", index=False)
                st.download_button("📥 Baixar Excel", output.getvalue(), f"Notas_{prova_nome}.xlsx")
        else:
            st.info("Nenhum aluno respondeu esta prova ainda.")

elif menu == "Cadastrar Questões":
    st.title("🖊️ Cadastro de Questões")
    
    tab1, tab2 = st.tabs(["Individual", "Importação Flash (JSON)"])
    
    with tab1:
        with st.form("form_questao", clear_on_submit=True):
            enunciado = st_quill(placeholder="Escreva o enunciado aqui...")
            col1, col2 = st.columns(2)
            materia = col1.selectbox("Disciplina", ["Matemática", "Português", "Física", "Química", "Biologia", "História", "Geografia"])
            assunto = col2.text_input("Assunto (ex: Trigonometria)")
            
            st.write("Alternativas:")
            a = st.text_input("A)")
            b = st.text_input("B)")
            c = st.text_input("C)")
            d = st.text_input("D)")
            e = st.text_input("E)")
            
            correta = st.radio("Alternativa Correta", ["A", "B", "C", "D", "E"], horizontal=True)
            
            if st.form_submit_button("💾 Salvar Questão"):
                nova_q = {
                    "enunciado": enunciado, "materia": materia, "assunto": assunto,
                    "alternativas": {"A": a, "B": b, "C": c, "D": d, "E": e},
                    "correta": correta, "revisada": True
                }
                supabase.table("questoes").insert(nova_q).execute()
                st.success("Questão salva com sucesso!")

    with tab2:
        st.info("Cole aqui o JSON gerado pela IA para importar várias questões de uma vez.")
        json_txt = st.text_area("JSON de Questões:", height=250)
        if st.button("🚀 Importar em Massa"):
            try:
                lista_q = json.loads(json_txt)
                for q in lista_q:
                    supabase.table("questoes").insert(q).execute()
                st.success(f"✅ {len(lista_q)} questões importadas!")
            except Exception as error:
                st.error(f"Erro no JSON: {error}")

elif menu == "Biblioteca de Questões":
    st.title("📚 Biblioteca de Questões")
    
    # Filtros
    res_q = supabase.table("questoes").select("*").order("id", desc=True).execute()
    if res_q.data:
        df_q = pd.DataFrame(res_q.data)
        
        filtro_mat = st.multiselect("Filtrar por Disciplina:", df_q['materia'].unique())
        if filtro_mat:
            df_q = df_q[df_q['materia'].isin(filtro_mat)]
            
        for index, row in df_q.iterrows():
            with st.expander(f"ID {row['id']} - {row['materia']} | {row['assunto']}"):
                st.markdown(row['enunciado'], unsafe_allow_html=True)
                for letra, texto in row['alternativas'].items():
                    cor = "green" if letra == row['correta'] else "black"
                    st.markdown(f"<span style='color:{cor}'>**{letra})** {texto}</span>", unsafe_allow_html=True)
                
                if st.button("🗑️ Excluir", key=f"del_{row['id']}"):
                    supabase.table("questoes").delete().eq("id", row['id']).execute()
                    st.rerun()

elif menu == "Gerar Modelo de Prova":
    st.title("📄 Gerar Nova Prova")
    
    with st.form("gerar_prova"):
        titulo = st.text_input("Título da Prova (ex: 1º Simulado 2024)")
        valor_q = st.number_input("Valor de cada questão:", value=1.0)
        
        res_q = supabase.table("questoes").select("id, materia, assunto").execute()
        df_q = pd.DataFrame(res_q.data)
        
        selecionadas = st.multiselect("Selecione as questões (por ID):", 
                                      df_q.apply(lambda x: f"{x['id']} - {x['materia']} ({x['assunto']})", axis=1))
        
        if st.form_submit_button("🔨 Criar Modelo"):
            ids = [int(s.split(" - ")[0]) for s in selecionadas]
            novo_modelo = {
                "titulo": titulo,
                "questoes_ids": ids,
                "valor_questao": valor_q,
                "ativa": True
            }
            supabase.table("modelos_prova").insert(novo_modelo).execute()
            st.success("Prova criada e pronta para aplicação!")

elif menu == "Provas Elaboradas":
    st.title("📂 Gerenciamento de Provas")
    res_m = supabase.table("modelos_prova").select("*").order("id", desc=True).execute()
    if res_m.data:
        for m in res_m.data:
            c1, c2, c3 = st.columns([3, 1, 1])
            status = "✅ Ativa" if m['ativa'] else "❌ Inativa"
            c1.write(f"**{m['titulo']}** ({len(m['questoes_ids'])} questões) - {status}")
            
            if c2.button("Alternar Status", key=f"tog_{m['id']}"):
                supabase.table("modelos_prova").update({"ativa": not m['ativa']}).eq("id", m['id']).execute()
                st.rerun()
            
            if c3.button("🗑️ Apagar", key=f"del_m_{m['id']}"):
                supabase.table("modelos_prova").delete().eq("id", m['id']).execute()
                st.rerun()

elif menu == "Lista de Matrículas":
    st.title("👥 Listas por Turma")
    res_al = supabase_alunos.table("alunos").select("turma").execute()
    if res_al.data:
        turmas = sorted(list(set([a['turma'] for a in res_al.data])))
        turma_sel = st.selectbox("Escolha a Turma:", turmas)
        
        if st.button("📄 Gerar PDF de Frequência"):
            res_turma = supabase_alunos.table("alunos").select("nome").eq("turma", turma_sel).order("nome").execute()
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 14)
            pdf.cell(200, 10, f"Lista de Frequência - Turma {turma_sel}", ln=True, align='C')
            pdf.ln(10)
            pdf.set_font("Arial", size=11)
            for i, aluno in enumerate(res_turma.data, 1):
                pdf.cell(0, 8, f"{i}. _________________________________________________ {aluno['nome']}", ln=True)
            
            pdf_out = pdf.output(dest='S').encode('latin-1')
            b64 = base64.b64encode(pdf_out).decode('latin-1')
            href = f'<a href="data:application/pdf;base64,{b64}" download="Frequencia_{turma_sel}.pdf">📥 Baixar PDF</a>'
            st.markdown(href, unsafe_allow_html=True)

elif menu == "Central de Avisos":
    st.title("📲 Disparador de WhatsApp")
    st.warning("O disparo via automação requer o WhatsApp Web aberto no servidor (uso local).")
    
    msg = st.text_area("Mensagem:", "Olá! Passando para lembrar do simulado amanhã.")
    turma_aviso = st.text_input("Turma (ex: 3º A):")
    
    if st.button("🚀 Iniciar Disparo"):
        res_whats = supabase_alunos.table("alunos").select("nome, telefone").eq("turma", turma_aviso).execute()
        if res_whats.data:
            for al in res_whats.data:
                st.write(f"Enviando para {al['nome']}...")
                # Lógica pywhatkit (se disponível)
                time.sleep(2)
            st.success("Fila de disparos concluída!")

elif menu == "Diagnósticos IA":
    st.title("🤖 Importar Diagnósticos Pedagógicos")
    
    res_p = supabase.table("modelos_prova").select("id, titulo").execute()
    if res_p.data:
        prova_id = st.selectbox("Vincular feedbacks à prova:", {p['titulo']: p['id'] for p in res_p.data}.values())
        
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("1️⃣ Instruções")
            st.write("1. Exporte as notas para o ChatGPT/Gemini.\n2. Peça feedbacks curtos em JSON.\n3. Formato: `{'ID_ALUNO': 'Texto'}`")
            
        with c2:
            st.subheader("2️⃣ Importar")
            json_input = st.text_area("Cole o JSON aqui:", height=200)
            if st.button("💾 Salvar no Banco"):
                try:
                    dados_ia = json.loads(json_input)
                    for al_id, txt in dados_ia.items():
                        supabase.table("feedback_ia_alunos").insert({
                            "aluno_id": str(al_id), "prova_id": str(prova_id),
                            "diagnostico_pedagogico": txt, "revisado_professor": True
                        }).execute()
                    st.success("Feedbacks salvos!")
                except Exception as e:
                    st.error(f"Erro: {e}")

elif menu == "Boletim Final SIEPE":
    st.title("🏫 Consolidação SIEPE")
    st.info("Aqui você visualiza a média final consolidada para lançamento no sistema oficial.")
    # Implementar lógica de cálculo de médias N1, N2, N3...