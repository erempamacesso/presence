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
    st.session_state.autenticado = True # Mudar para False se desejar tela de login real

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
        res_alunos_base = supabase_alunos.table("alunos").select("id, turma, nome").execute()
        
        if res_raw.data and res_alunos_base.data:
            df_raw = pd.DataFrame(res_raw.data)
            df_alunos_base = pd.DataFrame(res_alunos_base.data)
            df_raw['aluno_id'] = df_raw['aluno_id'].astype(str)
            df_alunos_base['id'] = df_alunos_base['id'].astype(str)
            
            st.subheader("🎯 Visão Geral")
            col_k1, col_k2 = st.columns(2)
            col_k1.metric("Total de Respostas", len(df_raw))
            col_k2.metric("Alunos Participantes", df_raw['aluno_id'].nunique())
    except Exception as e:
        st.info("Aguardando dados de respostas...")

    st.divider()
    st.subheader("🏆 Desempenho por Aluno e Relatórios")
    
    res_p_modelos = supabase.table("modelos_prova").select("id, titulo, valor_questao, questoes_ids").order("id", desc=True).execute()
    
    if res_p_modelos.data:
        provas_dict = {p['titulo']: p for p in res_p_modelos.data}
        prova_nome = st.selectbox("Selecione a Prova para detalhar:", list(provas_dict.keys()))
        prova_obj = provas_dict[prova_nome]
        id_prova, valor_q = prova_obj['id'], float(prova_obj.get('valor_questao', 1.0))
        ids_questoes_prova = prova_obj.get('questoes_ids', [])

        res_res = supabase.table("resultados_provas").select("*").eq("prova_id", id_prova).execute()
        
        if res_res.data:
            df_res = pd.DataFrame(res_res.data)
            df_res['aluno_id'] = df_res['aluno_id'].astype(str)
            df_res['pontos'] = df_res['acertou'].apply(lambda x: 1 if x is True else 0)
            
            df_notas = df_res.groupby('aluno_id').agg(total_acertos=('pontos', 'sum')).reset_index()
            df_notas['nota_final'] = df_notas['total_acertos'] * valor_q
            
            res_al = supabase_alunos.table("alunos").select("id, nome, turma").in_("id", df_notas['aluno_id'].tolist()).execute()
            df_alunos_nomes = pd.DataFrame(res_al.data)
            df_alunos_nomes['id'] = df_alunos_nomes['id'].astype(str)
            
            df_tela = pd.merge(df_alunos_nomes, df_notas, left_on="id", right_on="aluno_id")
            st.dataframe(df_tela[["nome", "turma", "total_acertos", "nota_final"]].sort_values("nome"), use_container_width=True)

            if st.button("📊 Gerar Relatório .XLSX Completo"):
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    for turma in sorted(df_tela['turma'].unique()):
                        df_turma = df_tela[df_tela['turma'] == turma].copy()
                        df_turma.to_excel(writer, sheet_name=f"Turma {turma}", index=False)
                st.download_button("📥 Baixar Excel", output.getvalue(), f"Relatorio_{prova_nome}.xlsx")
        else:
            st.info("Sem respostas para esta avaliação.")

elif menu == "Cadastrar Questões":
    st.title("🖊️ Cadastro de Questões (Upload de Imagens)")
    
    # --- FUNÇÃO DE UPLOAD PARA O SUPABASE STORAGE ---
    def upload_imagem(arquivo_upload):
        if arquivo_upload is not None:
            try:
                # Gera um nome único para o arquivo
                nome_unico = f"{int(time.time())}_{arquivo_upload.name.replace(' ', '_')}"
                # Faz o upload para o bucket 'imagens'
                res = supabase.storage.from_("imagens").upload(
                    path=nome_unico, 
                    file=arquivo_upload.getvalue(),
                    file_options={"content-type": arquivo_upload.type}
                )
                # Pega a URL pública
                return supabase.storage.from_("imagens").get_public_url(nome_unico)
            except Exception as e:
                st.error(f"Erro no upload da imagem: {e}")
                return ""
        return ""

    tab1, tab2 = st.tabs(["📝 Cadastro Individual", "⚡ Importação Flash"])
    
    with tab1:
        with st.form("form_nova_questao_upload", clear_on_submit=True):
            st.subheader("1️⃣ Enunciado")
            enunciado = st_quill(placeholder="Digite o enunciado...", html=True, key="quill_up")
            
            col_m, col_a = st.columns(2)
            materia = col_m.selectbox("Disciplina", ["Matemática", "Português", "Física", "Química", "Biologia", "História", "Geografia"])
            assunto = col_a.text_input("Assunto")

            st.divider()
            st.subheader("2️⃣ Alternativas (Faça Upload da Imagem ou digite o texto)")
            
            # Arrays para segurar os uploads temporariamente
            textos_alts = {}
            arquivos_alts = {}
            
            for letra in ["A", "B", "C", "D", "E"]:
                c_txt, c_up = st.columns([2, 1])
                textos_alts[letra] = c_txt.text_input(f"Texto da {letra})", key=f"t_{letra}")
                # BOTÃO DE CARREGAR IMAGEM
                arquivos_alts[letra] = c_up.file_uploader(f"Anexar Img {letra}", type=['png', 'jpg', 'jpeg'], key=f"f_{letra}")

            st.divider()
            st.subheader("3️⃣ Resposta Correta")
            correta = st.radio("Selecione a correta:", ["A", "B", "C", "D", "E"], horizontal=True)
            
            btn_salvar = st.form_submit_button("💾 Salvar na Biblioteca e Fazer Upload", type="primary")

            if btn_salvar:
                if not enunciado or len(enunciado) < 5:
                    st.error("Preencha o enunciado!")
                else:
                    with st.spinner("Fazendo upload das imagens e salvando..."):
                        alts_dados = {}
                        
                        # Processa cada alternativa
                        for letra in ["A", "B", "C", "D", "E"]:
                            # Se tiver arquivo, faz upload e pega a URL. Se não, URL fica vazia.
                            url_final = upload_imagem(arquivos_alts[letra])
                            alts_dados[letra] = {
                                "texto": textos_alts[letra],
                                "imagem": url_final
                            }

                        dados_final = {
                            "enunciado": enunciado,
                            "materia": materia,
                            "assunto": assunto,
                            "alternativas": alts_dados,
                            "correta": correta,
                            "revisada": True
                        }
                        
                        try:
                            supabase.table("questoes").insert(dados_final).execute()
                            st.success("✅ Questão e imagens salvas com sucesso!")
                        except Exception as e:
                            st.error(f"Erro ao salvar no banco: {e}")

    with tab2:
        st.subheader("⚡ Importador Flash")
        json_input = st.text_area("JSON de Questões:")
        if st.button("🚀 Iniciar Importação"):
            try:
                for q in json.loads(json_input): supabase.table("questoes").insert(q).execute()
                st.success("Importado!")
            except: st.error("Erro JSON")

elif menu == "Biblioteca de Questões":
    st.title("📚 Biblioteca de Questões")
    
    res_q = supabase.table("questoes").select("*").order("id", desc=True).execute()
    
    if res_q.data:
        df_q = pd.DataFrame(res_q.data)
        
        # Proteção de colunas
        if 'serie' not in df_q.columns: df_q['serie'] = "Geral"
        if 'assunto' not in df_q.columns: df_q['assunto'] = ""
        
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            filtro_serie = st.multiselect("Filtrar por Série:", options=sorted(df_q['serie'].dropna().unique()))
        with col_f2:
            busca_assunto = st.text_input("Buscar por Assunto:")

        if filtro_serie: df_q = df_q[df_q['serie'].isin(filtro_serie)]
        if busca_assunto: df_q = df_q[df_q['assunto'].str.contains(busca_assunto, case=False, na=False)]

        st.write(f"Total de questões encontradas: **{len(df_q)}**")
        st.divider()

        for index, row in df_q.iterrows():
            str_serie = row.get('serie', '')
            str_assunto = row.get('assunto', '')
            
            # --- ALTERAÇÃO AQUI: Removi o ID e a numeração do título do expander ---
            with st.expander(f"📖 {str_serie} | Assunto: {str_assunto}"):
                st.markdown(row['enunciado'], unsafe_allow_html=True)
                
                st.write("**Alternativas:**")
                
                alts = row.get('alternativas', {})
                if isinstance(alts, str):
                    try:
                        alts = json.loads(alts.replace("'", '"'))
                    except:
                        alts = {}
                
                resposta_certa = row.get('resposta_correta', 'A')

                if isinstance(alts, dict):
                    for letra in ["A", "B", "C", "D"]:
                        item = alts.get(letra, "")
                        
                        if isinstance(item, dict):
                            txt_alt = item.get("texto", "")
                            url_img = item.get("imagem", "")
                        else:
                            txt_alt = str(item)
                            url_img = ""

                        cor = "green" if letra == resposta_certa else "black"
                        marcador = "✅" if letra == resposta_certa else "⚪"
                        
                        st.markdown(f"<span style='color:{cor}'>{marcador} **{letra})** {txt_alt}</span>", unsafe_allow_html=True)
                        
                        if url_img:
                            st.image(url_img, width=200)
                
                st.divider()
                # O ID continua sendo usado apenas "por baixo dos panos" no botão de excluir
                if st.button("🗑️ Excluir Questão", key=f"del_{row['id']}", type="secondary"):
                    try:
                        supabase.table("questoes").delete().eq("id", row['id']).execute()
                        st.success("Questão removida!")
                        time.sleep(0.5)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao excluir: {e}")
    else:
        st.info("Nenhuma questão na biblioteca.")

elif menu == "Gerar Modelo de Prova":
    st.title("📄 Gerar Nova Prova")
    # Lógica de criação de modelos de prova...

elif menu == "Provas Elaboradas":
    st.title("📂 Gerenciamento de Provas")
    # Listagem de provas com botões Editar, Ativar/Desativar e Excluir...

elif menu == "Lista de Matrículas":
    st.title("👥 Listas por Turma (PDF)")
    # Geração de PDF de frequência...

elif menu == "Central de Avisos":
    st.title("📲 Disparador de WhatsApp")
    if not WHATSAPP_LOCAL:
        st.warning("Biblioteca 'pywhatkit' não instalada para disparos.")
    # Lógica de envio em massa...

elif menu == "Diagnósticos IA":
    st.title("🤖 Importar Diagnósticos Pedagógicos")
    # Lógica de colagem do JSON da IA para feedback dos alunos...

elif menu == "Boletim Final SIEPE":
    st.title("🏫 Consolidação de Notas SIEPE")
    # Editor de notas AT1-AT5 e N2...