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
from telas.boletim_siepe import mostrar_tela_boletim
from telas.analise_dados import mostrar_tela_analise
from telas.biblioteca_questoes import mostrar_tela_biblioteca
from telas.gerar_modelo_prova import mostrar_tela_gerar_modelo
from telas.provas_elaboradas import mostrar_tela_provas_elaboradas
from telas.lista_matriculas import mostrar_tela_lista_matriculas
from telas.diagnosticos_ia import mostrar_tela_diagnosticos

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

# --- FUNÇÃO DE SINCRONIZAÇÃO DE NOTAS ---
def sincronizar_atividades_online(turma_sel, unidade_sel, atividade_id_origem):
    """
    Busca notas na tabela 'resultados' e salva na 'notas_atividades' coluna AT1
    """
    try:
        # 1. Busca os resultados da atividade online
        res = supabase.table("resultados").select("aluno_id, nota").eq("atividade_id", atividade_id_origem).execute()
        
        if not res.data:
            st.warning(f"Nenhum resultado encontrado para a atividade {atividade_id_origem}")
            return

        # 2. Prepara os dados para o Upsert na nova tabela
        dados_upsert = []
        for r in res.data:
            dados_upsert.append({
                "aluno_id": r["aluno_id"],
                "turma": turma_sel,
                "unidade": unidade_sel,
                "at1": float(r["nota"])
            })
        
        # 3. Faz o Upsert (Se o aluno já tiver linha lá, ele só atualiza a AT1)
        supabase.table("notas_atividades").upsert(dados_upsert, on_conflict="aluno_id, unidade").execute()
        st.success(f"✅ {len(dados_upsert)} notas sincronizadas com sucesso para AT1!")
        
    except Exception as e:
        st.error(f"Erro na sincronização: {e}")

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
            "Boletim Final "
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
    mostrar_tela_biblioteca(supabase)

elif menu == "Provas Elaboradas":
    mostrar_tela_provas_elaboradas(supabase)

elif menu == "Lista de Matrículas":
    mostrar_tela_lista_matriculas(supabase_alunos)

elif menu == "Central de Avisos":
    st.title("📲 Disparador de WhatsApp")
    if not WHATSAPP_LOCAL:
        st.warning("Biblioteca 'pywhatkit' não instalada para disparos.")
    # Lógica de envio em massa...

elif menu == "Diagnósticos IA":
    mostrar_tela_diagnosticos(supabase)

elif menu == "Boletim Final SIEPE":
    mostrar_tela_boletim(supabase, supabase_alunos)