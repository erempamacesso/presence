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
            "Planilha de Notas"
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
    st.title("📄 Gerar Novo Modelo de Prova")
    
    # --- CONFIGURAÇÕES BÁSICAS DA PROVA ---
    c1, c2 = st.columns([3, 1])
    titulo = c1.text_input("Título da Prova", placeholder="Ex: 1ª Avaliação de Química - 2º Bimestre")
    valor = c2.number_input("Valor por questão", min_value=0.1, value=1.0, step=0.1)
    
    # Puxa as questões do banco para podermos selecionar
    res_q = supabase.table("questoes").select("id, serie, assunto, enunciado").order("id", desc=True).execute()
    
    if res_q.data:
        df_sel = pd.DataFrame(res_q.data)
        
        # Função rápida para limpar o HTML do enunciado (criado pelo editor) e deixar só o texto puro no menu
        def clean_html(raw_html):
            if not raw_html: return ""
            cleanr = re.compile('<.*?>')
            cleantext = re.sub(cleanr, '', str(raw_html))
            return cleantext[:60] + "..." if len(cleantext) > 60 else cleantext
        
        # Cria um dicionário para mapear o texto bonito para o ID da questão
        opcoes_dict = {}
        for _, row in df_sel.iterrows():
            serie_txt = row.get('serie', 'Geral')
            assunto_txt = row.get('assunto', '')
            enunciado_limpo = clean_html(row.get('enunciado', ''))
            
            # Como a opção vai aparecer na tela para você
            texto_exibicao = f"[{serie_txt}] {assunto_txt} | {enunciado_limpo}"
            # Se der nomes duplicados por coincidência, adicionamos o ID invisível para diferenciar
            texto_exibicao = f"{texto_exibicao} (ID:{row['id']})"
            
            opcoes_dict[texto_exibicao] = row['id']
        
        st.divider()
        st.subheader("📚 Selecione as Questões")
        
        # Filtro opcional para limpar a tela
        series_disponiveis = ["Todas"] + sorted(list(df_sel['serie'].dropna().unique()))
        filtro_s = st.selectbox("Filtrar lista de seleção por Série (Opcional):", series_disponiveis)
        
        opcoes_exibicao = list(opcoes_dict.keys())
        if filtro_s != "Todas":
            opcoes_exibicao = [op for op in opcoes_exibicao if f"[{filtro_s}]" in op]
        
        # O campo de múltipla escolha
        selecionadas = st.multiselect(
            "Busque e adicione as questões para esta prova:", 
            options=opcoes_exibicao,
            help="Você pode digitar parte do assunto ou do texto para encontrar a questão mais rápido."
        )
        
        st.info(f"Quantidade de questões selecionadas para esta prova: **{len(selecionadas)}**")
        
        # --- BOTÃO DE SALVAR PROVA ---
        st.write("---")
        if st.button("🔨 Gerar Prova e Salvar", type="primary", use_container_width=True):
            if not titulo:
                st.error("❌ Dê um título para a prova!")
            elif len(selecionadas) == 0:
                st.error("❌ Selecione pelo menos 1 questão!")
            else:
                # Pega os IDs reais das questões selecionadas usando nosso dicionário
                ids_selecionados = [opcoes_dict[opt] for opt in selecionadas]
                
                dados_prova = {
                    "titulo": titulo, 
                    "questoes_ids": ids_selecionados, 
                    "valor_questao": float(valor), 
                    "ativa": True
                }
                
                try:
                    supabase.table("modelos_prova").insert(dados_prova).execute()
                    st.success(f"✅ Prova '{titulo}' gerada com sucesso contendo {len(selecionadas)} questões!")
                    st.balloons()
                except Exception as e:
                    st.error(f"Erro ao salvar a prova no banco: {e}")
    else:
        st.warning("Não há questões cadastradas no banco de dados. Vá em 'Cadastrar Questões' primeiro.")

elif menu == "Provas Elaboradas":
    st.title("📂 Gerenciamento de Provas Elaboradas")
    
    # Busca todas as provas cadastradas no banco
    res_m = supabase.table("modelos_prova").select("*").order("id", desc=True).execute()
    
    if res_m.data:
        df_provas = pd.DataFrame(res_m.data)
        st.write(f"Total de provas criadas: **{len(df_provas)}**")
        st.divider()
        
        # Lista cada prova em um "cartão" (container)
        for index, prova in df_provas.iterrows():
            # Define cor e texto do status
            is_ativa = prova.get('ativa', False)
            status_texto = "🟢 ATIVA (Aberta para os alunos)" if is_ativa else "🔴 INATIVA (Fechada)"
            
            # Calcula dados básicos
            qtd_questoes = len(prova.get('questoes_ids', []))
            valor_q = prova.get('valor_questao', 0)
            valor_total = qtd_questoes * valor_q
            
            with st.container(border=True):
                c1, c2, c3 = st.columns([3, 1, 1.2])
                
                with c1:
                    st.subheader(f"📝 {prova['titulo']}")
                    st.write(f"**Quantidade:** {qtd_questoes} questões | **Por questão:** {valor_q} pts | **Total:** {valor_total:.1f} pts")
                    st.markdown(f"**Status atual:** {status_texto}")
                
                with c2:
                    st.write("") # Espaçamento
                    # Botão para ativar/desativar a prova
                    texto_btn = "⏸️ Desativar" if is_ativa else "▶️ Ativar"
                    if st.button(texto_btn, key=f"tog_{prova['id']}", use_container_width=True):
                        novo_status = not is_ativa
                        try:
                            supabase.table("modelos_prova").update({"ativa": novo_status}).eq("id", prova['id']).execute()
                            time.sleep(0.5)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao mudar status: {e}")
                            
                with c3:
                    st.write("") # Espaçamento
                    # Botão para excluir a prova
                    if st.button("🗑️ Excluir Prova", key=f"del_p_{prova['id']}", type="primary", use_container_width=True):
                        try:
                            # 1. Primeiro apagamos os resultados dessa prova (se houver) para evitar erros de dependência
                            supabase.table("resultados_provas").delete().eq("prova_id", prova['id']).execute()
                            # 2. Depois apagamos o modelo da prova
                            supabase.table("modelos_prova").delete().eq("id", prova['id']).execute()
                            
                            st.success("Prova excluída com sucesso!")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao excluir: {e}")
    else:
        st.info("Nenhuma prova elaborada ainda. Vá na aba 'Gerar Modelo de Prova' para criar a primeira!")


elif menu == "Lista de Matrículas":
    st.title("👥 Listas por Turma (PDF)")
    st.write("Visualize a listagem de alunos com o número de matrícula oficial.")

    try:
        # Busca os alunos
        res_a = supabase_alunos.table("alunos").select("*").execute()
        
        if res_a.data:
            df_alunos = pd.DataFrame(res_a.data)
            
            # --- MAPEAMENTO EXATO (Baseado no seu Supabase) ---
            col_t = 'turma' 
            col_n = 'nome' 
            col_m = 'numero_matricula' # <-- Agora sim, o nome exato!

            if col_t not in df_alunos.columns or col_n not in df_alunos.columns:
                st.error("Erro técnico: Colunas 'nome' ou 'turma' não encontradas. Verifique o banco.")
            else:
                # Seletor de Turma
                turmas_disponiveis = sorted(df_alunos[col_t].dropna().unique())
                turma_selecionada = st.selectbox("Selecione a Turma:", turmas_disponiveis)

                # Filtro e Ordenação por Nome
                df_turma = df_alunos[df_alunos[col_t] == turma_selecionada].sort_values(by=col_n).reset_index(drop=True)
                
                # Adiciona o número de ordem (1, 2, 3...)
                df_turma['Nº'] = df_turma.index + 1 
                
                # Prepara colunas para exibição na tela
                colunas_tela = ['Nº']
                if col_m in df_alunos.columns:
                    colunas_tela.append(col_m)
                colunas_tela.append(col_n)

                st.write(f"Total de alunos na turma: **{len(df_turma)}**")
                
                # Exibe a tabela formatada (Trocando na tela para ficar bonito)
                df_exibir = df_turma[colunas_tela].copy()
                if col_m in df_alunos.columns:
                    df_exibir = df_exibir.rename(columns={col_m: "Matrícula"})
                
                st.dataframe(df_exibir, use_container_width=False, hide_index=True)

                st.divider()

                # --- GERAÇÃO DO PDF ---
                import tempfile 
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font('Arial', 'B', 14)
                pdf.cell(0, 10, 'EREMPAM - LISTAGEM DE MATRICULAS', ln=True, align='C')
                
                t_limpa = unicodedata.normalize('NFKD', str(turma_selecionada)).encode('ASCII', 'ignore').decode('ASCII')
                pdf.set_font('Arial', 'B', 12)
                pdf.cell(0, 10, f'TURMA: {t_limpa}', ln=True, align='L')
                pdf.ln(5)

                # Cabeçalho do PDF
                pdf.set_font('Arial', 'B', 10)
                pdf.cell(12, 8, 'N', border=1, align='C')
                
                larg_nome = 110
                if col_m in df_alunos.columns:
                    pdf.cell(35, 8, 'MATRICULA', border=1, align='C')
                    larg_nome = 95
                    
                pdf.cell(larg_nome, 8, 'NOME DO ALUNO', border=1, align='C')
                pdf.cell(35, 8, 'OBSERVACAO', border=1, align='C')
                pdf.ln()

                # Linhas do PDF
                pdf.set_font('Arial', '', 10)
                for row in df_turma.itertuples():
                    pdf.cell(12, 8, str(getattr(row, 'Nº')), border=1, align='C')
                    
                    if col_m in df_alunos.columns:
                        # Pega o valor da matrícula diretamente
                        val_m = str(getattr(row, col_m))
                        pdf.cell(35, 8, val_m, border=1, align='C')
                        
                    nome_p = unicodedata.normalize('NFKD', str(getattr(row, col_n))).encode('ASCII', 'ignore').decode('ASCII')[:35]
                    pdf.cell(larg_nome, 8, nome_p, border=1, align='L')
                    pdf.cell(35, 8, '', border=1, align='C')
                    pdf.ln()

                # Download
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    pdf.output(tmp.name)
                    with open(tmp.name, "rb") as f:
                        pdf_bytes = f.read()

                st.download_button(
                    label="📥 Baixar PDF da Turma",
                    data=pdf_bytes,
                    file_name=f"Matriculas_{t_limpa.replace(' ', '_')}.pdf",
                    mime="application/pdf",
                    type="primary",
                    use_container_width=True
                )
        else:
            st.warning("Nenhum dado encontrado na tabela de alunos.")

    except Exception as e:
        st.error(f"Erro ao processar matrículas: {e}")

elif menu == "Central de Avisos":
    st.title("📲 Disparador de WhatsApp")
    if not WHATSAPP_LOCAL:
        st.warning("Biblioteca 'pywhatkit' não instalada para disparos.")
    # Lógica de envio em massa...


elif menu == "Diagnósticos IA":
    st.title("🤖 Importar Diagnósticos Pedagógicos")
    st.write("Vincule feedbacks gerados por Inteligência Artificial aos alunos após uma prova.")
    
    # Puxa as provas para o professor selecionar
    res_provas = supabase.table("modelos_prova").select("id, titulo").order("id", desc=True).execute()
    
    if res_provas.data:
        c1, c2 = st.columns([1, 1.5], gap="large")
        
        # ==========================================
        # LADO ESQUERDO: SELEÇÃO E INSTRUÇÕES
        # ==========================================
        with c1:
            st.subheader("1️⃣ Selecione a Prova")
            # Cria dicionário para o selectbox associar o Título ao ID
            provas_dict = {p['titulo']: p['id'] for p in res_provas.data}
            prova_selecionada = st.selectbox("Vincular feedbacks à qual prova?", list(provas_dict.keys()))
            prova_id = provas_dict[prova_selecionada]
            
            st.divider()
            st.markdown("**Como usar?**")
            st.write("1. Exporte a planilha de notas e erros para o ChatGPT/Gemini.")
            st.write("2. Peça para a IA gerar um diagnóstico curto para cada aluno em formato JSON.")
            st.write("3. O formato **obrigatório** deve ser:")
            st.code('{\n  "123": "O aluno precisa revisar o assunto X.",\n  "124": "Excelente desempenho!"\n}', language="json")
            st.caption("*Onde '123' e '124' são os IDs ou Matrículas dos alunos.*")
            
        # ==========================================
        # LADO DIREITO: SALVAR NO BANCO
        # ==========================================
        with c2:
            st.subheader("2️⃣ Importar Diagnósticos")
            json_input = st.text_area("Cole o JSON da IA aqui:", height=250, placeholder='{\n  "ID_DO_ALUNO": "Feedback gerado pela IA..."\n}')
            
            if st.button("💾 Salvar Feedbacks no Banco", type="primary", use_container_width=True):
                if not json_input.strip():
                    st.warning("⚠️ Cole o código JSON antes de tentar salvar.")
                else:
                    try:
                        dados_ia = json.loads(json_input)
                        count = 0
                        
                        with st.spinner("Salvando feedbacks no banco de dados..."):
                            for al_id, txt in dados_ia.items():
                                supabase.table("feedback_ia_alunos").insert({
                                    "aluno_id": str(al_id), # CORREÇÃO: Força string para evitar erro de tipo
                                    "prova_id": str(prova_id),
                                    "diagnostico_pedagogico": txt,
                                    "revisado_professor": True
                                }).execute()
                                count += 1
                                
                        st.success(f"✅ {count} feedbacks salvos na tabela 'feedback_ia_alunos' para a prova '{prova_selecionada}'!")
                        st.balloons()
                        
                    except json.JSONDecodeError:
                        st.error("❌ Erro: O texto colado não é um JSON válido. Verifique se faltam aspas, vírgulas ou chaves ({}).")
                    except Exception as e:
                        st.error("❌ Erro ao salvar no banco. Mensagem:")
                        st.code(str(e))
    else:
        st.warning("Nenhuma prova encontrada. Crie uma prova primeiro na aba 'Gerar Modelo de Prova'.")

# BLOCO DAS NOTAS TRIMESTRE #

elif menu == "PLANILHA DE NOTAS":
    st.title("🏫 Consolidação de Notas SIEPE")
    st.write("Importe provas para colunas específicas para travá-las, ou digite manualmente as notas de projetos.")

    try:
        # 1. Busca todos os alunos
        res_a = supabase_alunos.table("alunos").select("*").execute()
        
        if res_a.data:
            df_todos = pd.DataFrame(res_a.data)
            col_t = 'turma' if 'turma' in df_todos.columns else ('serie' if 'serie' in df_todos.columns else None)
            col_n = 'nome' if 'nome' in df_todos.columns else ('Nome' if 'Nome' in df_todos.columns else ('aluno' if 'aluno' in df_todos.columns else None))
            
            if col_t and col_n:
                turmas_list = sorted(df_todos[col_t].dropna().unique())
                turma_sel = st.selectbox("Selecione a Turma:", turmas_list)
                
                if turma_sel:
                    # =====================================================================
                    # 🧠 GESTÃO DE ESTADO E TRAVAMENTO
                    # =====================================================================
                    state_key = f"tabela_notas_{turma_sel}"
                    locked_key = f"colunas_travadas_{turma_sel}"
                    editor_key = f"editor_notas_{turma_sel}"
                    
                    # Inicializa a tabela se não existir
                    if state_key not in st.session_state:
                        df_base = pd.DataFrame()
                        df_base['nome'] = df_todos[df_todos[col_t] == turma_sel].sort_values(by=col_n)[col_n].values
                        for col in ['AT1', 'AT2', 'AT3', 'AT4', 'AT5', 'N1', 'N2', 'Média Final']:
                            df_base[col] = 0.0
                        st.session_state[state_key] = df_base
                    
                    # Inicializa lista de colunas travadas (vazia no início)
                    if locked_key not in st.session_state:
                        st.session_state[locked_key] = []

                    # Sincroniza edições manuais
                    if editor_key in st.session_state:
                        edicoes = st.session_state[editor_key].get("edited_rows", {})
                        for row_idx, alteracoes in edicoes.items():
                            for col_name, valor in alteracoes.items():
                                st.session_state[state_key].at[row_idx, col_name] = float(valor) if valor is not None else 0.0

                    # Cálculos Automáticos
                    st.session_state[state_key]['N1'] = st.session_state[state_key][['AT1', 'AT2', 'AT3', 'AT4', 'AT5']].sum(axis=1).round(1)
                    st.session_state[state_key]['Média Final'] = ((st.session_state[state_key]['N1'] + st.session_state[state_key]['N2']) / 2).round(1)

                    # =====================================================================
                    # 📥 IMPORTAÇÃO E TRAVAMENTO DINÂMICO
                    # =====================================================================
                    st.divider()
                    with st.expander("📥 Importar Prova e Travar Coluna", expanded=False):
                        res_p = supabase.table("modelos_prova").select("id, titulo, valor_questao").order("id", desc=True).execute()
                        
                        if res_p.data:
                            provas_dict = {p['titulo']: p for p in res_p.data}
                            col_i1, col_i2 = st.columns(2)
                            
                            prova_escolhida = col_i1.selectbox("Selecione a Prova:", list(provas_dict.keys()))
                            coluna_alvo = col_i2.selectbox("Destino (Travar coluna):", ['AT1', 'AT2', 'AT3', 'AT4', 'AT5', 'N2'])
                            
                            if st.button(f"🔒 Importar e Travar {coluna_alvo}", use_container_width=True):
                                p_obj = provas_dict[prova_escolhida]
                                res_res = supabase.table("resultados_provas").select("*").eq("prova_id", p_obj['id']).execute()
                                
                                if res_res.data:
                                    # Processamento das notas
                                    df_res = pd.DataFrame(res_res.data)
                                    df_res['acertos'] = df_res['acertou'].apply(lambda x: 1 if x is True else 0)
                                    df_calc = df_res.groupby('aluno_id')['acertos'].sum().reset_index()
                                    df_calc['nota'] = df_calc['acertos'] * float(p_obj['valor_questao'])
                                    
                                    # Mapeamento para nomes
                                    res_n = supabase_alunos.table("alunos").select("id, nome").in_("id", df_calc['aluno_id'].astype(str).tolist()).execute()
                                    mapa = {str(item['id']): item['nome'] for item in res_n.data}
                                    df_calc['nome_aluno'] = df_calc['aluno_id'].astype(str).map(mapa)
                                    mapa_notas = dict(zip(df_calc['nome_aluno'], df_calc['nota']))
                                    
                                    # Grava na memória e TRAVA a coluna
                                    st.session_state[state_key][coluna_alvo] = st.session_state[state_key]['nome'].map(mapa_notas).fillna(0.0)
                                    if coluna_alvo not in st.session_state[locked_key]:
                                        st.session_state[locked_key].append(coluna_alvo)
                                    
                                    st.success(f"✅ Coluna {coluna_alvo} preenchida e bloqueada!")
                                    st.rerun()

                    # =====================================================================
                    # 📝 EDITOR DE NOTAS (COM TRAVAMENTO DINÂMICO)
                    # =====================================================================
                    st.subheader(f"Notas: {turma_sel}")
                    
                    # Construção dinâmica das configurações de colunas
                    config_colunas = {
                        "nome": st.column_config.TextColumn("Estudante", disabled=True, width="medium"),
                        "N1": st.column_config.NumberColumn("N1 (Soma)", disabled=True, width="small"),
                        "Média Final": st.column_config.NumberColumn("Média", disabled=True, width="small"),
                    }
                    
                    # Colunas de Notas (AT1 a AT5 e N2)
                    for c in ['AT1', 'AT2', 'AT3', 'AT4', 'AT5', 'N2']:
                        # Se a coluna estiver na lista de travadas, disabled = True
                        esta_travada = c in st.session_state[locked_key]
                        label = f"{c} 🔒" if esta_travada else c
                        
                        config_colunas[c] = st.column_config.NumberColumn(
                            label, 
                            min_value=0.0, 
                            max_value=10.0, 
                            format="%.1f", 
                            disabled=esta_travada, # 👈 AQUI ACONTECE A MÁGICA
                            width="small"
                        )

                    st.data_editor(
                        st.session_state[state_key],
                        key=editor_key,
                        hide_index=True,
                        use_container_width=False, # 👈 LARGURA MÍNIMA
                        column_config=config_colunas,
                        height=(len(st.session_state[state_key]) + 1) * 35 + 40
                    )
                    
                    if st.button("🔓 Resetar Travas desta Turma", type="secondary"):
                        st.session_state[locked_key] = []
                        st.rerun()

                    # =====================================================================
                    # 📥 EXPORTAÇÃO
                    # =====================================================================
                    st.divider()
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        st.session_state[state_key].to_excel(writer, sheet_name="SIEPE", index=False)
                    
                    st.download_button(
                        label="📥 Baixar Planilha para o SIEPE",
                        data=output.getvalue(),
                        file_name=f"SIEPE_{turma_sel}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        type="primary"
                    )

            else:
                st.error("Colunas de 'turma' ou 'nome' não encontradas.")
        else:
            st.info("Nenhum aluno encontrado.")
            
    except Exception as e:
        st.error(f"Erro no Boletim: {e}")