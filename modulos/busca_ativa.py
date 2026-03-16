import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import unicodedata
from urllib.parse import quote
import streamlit.components.v1 as components  
from fpdf import FPDF 

# --- 1. FUNÇÕES DE APOIO ---
def limpar_texto_absoluto(texto):
    if not texto: return ""
    texto = str(texto).strip().lower()
    if "." in texto: texto = texto.rsplit(".", 1)[0]
    nfkd = unicodedata.normalize('NFKD', texto)
    sem_acento = "".join([c for c in nfkd if not unicodedata.combining(c)])
    return "".join(filter(str.isalnum, sem_acento))

@st.cache_data(ttl=300)
def listar_arquivos_bucket(_supabase):
    try:
        arquivos = _supabase.storage.from_('fotos-alunos').list(path=None, options={'limit': 5000})
        mapa = {}
        if arquivos:
            for arq in arquivos:
                nome_original = arq.get('name')
                if nome_original:
                    nome_sem_ext = nome_original.rsplit('.', 1)[0] if '.' in nome_original else nome_original
                    mapa[limpar_texto_absoluto(nome_sem_ext)] = nome_original
        return mapa
    except Exception:
        return {}

def gerar_pdf_relatorio(df, titulo_relatorio, data_hoje):
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        pdf.cell(190, 10, "Relatorio de Busca Ativa", ln=True, align="C")
        pdf.set_font("Arial", "", 10)
        pdf.cell(190, 10, f"Gerado em: {data_hoje}", ln=True, align="C")
        pdf.ln(10)
        
        pdf.set_font("Arial", "B", 12)
        titulo_safe = str(titulo_relatorio).encode('latin-1', 'replace').decode('latin-1')
        pdf.cell(190, 10, titulo_safe.upper(), ln=True, align="L")
        pdf.ln(5)
        
        pdf.set_fill_color(230, 230, 230)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(100, 10, " Estudante", 1, 0, "L", True)
        pdf.cell(40, 10, " Turma", 1, 0, "C", True)
        pdf.cell(50, 10, " Info", 1, 1, "C", True)
        
        pdf.set_font("Arial", "", 10)
        for _, row in df.iterrows():
            nome = str(row.get('Aluno', row.get('nome', ''))).encode('latin-1', 'replace').decode('latin-1')
            turma = str(row.get('turma', '')).encode('latin-1', 'replace').decode('latin-1')
            info = str(row.get('Faltas', 'S/R')).encode('latin-1', 'replace').decode('latin-1')
            
            pdf.cell(100, 10, f" {nome[:45]}", 1)
            pdf.cell(40, 10, f" {turma}", 1, 0, "C")
            pdf.cell(50, 10, f" {info}", 1, 1, "C")
            
        saida = pdf.output(dest='S')
        return saida.encode('latin-1') if isinstance(saida, str) else bytes(saida)
    except Exception as e:
        return f"Erro PDF: {e}".encode('utf-8')

# --- 2. TELA PRINCIPAL DA BUSCA ATIVA ---
def exibir_busca_ativa(supabase):
    # Garantir que o título apareça logo de cara
    st.title("🔎 Busca Ativa")
    st.caption("Inteligência de Dados para Prevenção Escolar")
    
    fuso = pytz.timezone('America/Recife')
    hoje = datetime.now(fuso).strftime('%Y-%m-%d')
    data_hora_atual = datetime.now(fuso).strftime('%d/%m/%Y %H:%M')

    # --- MÉTRICAS ---
    st.subheader(f"📊 Resumo do Dia: {datetime.now(fuso).strftime('%d/%m/%Y')}")
    col1, col2, col3 = st.columns(3)

    try:
        # Faltas
        res_f = supabase.table("frequencia").select("id", count="exact").eq("data_chamada", hoje).eq("status", "F").execute()
        # Evasões
        res_e = supabase.table("evasoes").select("id", count="exact").eq("data_registro", hoje).execute()
        # Presentes
        res_p = supabase.table("frequencia").select("*").eq("data_chamada", hoje).eq("status", "P").execute()

        col1.metric("Faltas (Entrada)", res_f.count if res_f.count else 0)
        col2.metric("Evasões (Em aula)", res_e.count if res_e.count else 0)
        col3.metric("Presentes Agora", len(res_p.data) if res_p.data else 0)
    except Exception as e:
        st.error(f"Erro ao conectar com as métricas: {e}")

    st.markdown("---")

    # --- ABAS ---
    # Se essa linha não rodar, a tela fica em branco.
    abas = st.tabs(["🚨 Alertas & Ranking", "🗺️ Mapa de Evasões", "📝 Registrar Ação"])

    with abas[0]:
        st.subheader("🏆 Alunos com Mais Faltas")
        
        try:
            res_hist = supabase.table("frequencia").select("aluno_nome, turma").eq("status", "F").execute()
            if res_hist.data:
                df_hist = pd.DataFrame(res_hist.data)
                
                col_t, col_s = st.columns([1, 2])
                with col_t:
                    turma_sel = st.selectbox("📍 Turma:", ["Todas"] + sorted(df_hist['turma'].unique().tolist()))
                with col_s:
                    min_f = st.slider("Mínimo de faltas:", 1, 20, 3)

                if turma_sel != "Todas":
                    df_hist = df_hist[df_hist['turma'] == turma_sel]

                ranking = df_hist['aluno_nome'].value_counts().reset_index()
                ranking.columns = ['Aluno', 'Faltas']
                ranking = ranking[ranking['Faltas'] >= min_f].sort_values(by='Faltas', ascending=False)

                if not ranking.empty:
                    # Adicionando a turma de volta para o ranking
                    df_turmas = df_hist.drop_duplicates('aluno_nome')[['aluno_nome', 'turma']]
                    ranking = ranking.merge(df_turmas, left_on='Aluno', right_on='aluno_nome').drop('aluno_nome', axis=1)
                    
                    st.dataframe(ranking, use_container_width=True, hide_index=True)
                    
                    # Botão de PDF para a Busca Ativa
                    pdf_data = gerar_pdf_relatorio(ranking, f"Ranking de Faltas (Min: {min_f})", data_hora_atual)
                    st.download_button("📄 Baixar Relatório em PDF", pdf_data, f"ranking_faltas_{hoje}.pdf", "application/pdf", use_container_width=True)
                else:
                    st.info("Nenhum aluno atingiu esse limite de faltas.")
        except Exception as e:
            st.error(f"Erro no ranking: {e}")

        st.markdown("---")
        st.subheader("❌ Abandono (Presença Zero)")
        
        try:
            # Lógica: Alunos que existem mas não têm nenhum 'P' na frequência
            res_todos = supabase.table("alunos").select("nome, turma").execute()
            res_com_p = supabase.table("frequencia").select("aluno_nome").eq("status", "P").execute()
            
            if res_todos.data:
                df_todos = pd.DataFrame(res_todos.data)
                nomes_p = [x['aluno_nome'] for x in res_com_p.data] if res_com_p.data else []
                
                df_zero = df_todos[~df_todos['nome'].isin(nomes_p)].copy()
                df_zero.rename(columns={'nome': 'Aluno'}, inplace=True)
                df_zero['Faltas'] = "ZERO PRESENÇA"

                if not df_zero.empty:
                    st.warning(f"Encontrados {len(df_zero)} alunos sem nenhuma presença registrada.")
                    st.dataframe(df_zero[['Aluno', 'turma']], use_container_width=True, hide_index=True)
                    
                    pdf_z = gerar_pdf_relatorio(df_zero, "Relatorio de Presenca Zero (Abandono)", data_hora_atual)
                    st.download_button("📄 Baixar Relatório de Abandono", pdf_z, f"abandono_{hoje}.pdf", "application/pdf", use_container_width=True)
                else:
                    st.success("Todos os alunos possuem ao menos uma presença registrada.")
        except Exception as e:
            st.error(f"Erro ao processar abandono: {e}")

    with abas[1]:
        st.subheader("🗺️ Mapa de Fugas")
        st.info("Esta aba analisa os horários e turmas com maior índice de evasão.")
        # [Aqui vai o seu código de gráficos que você já tinha...]

    with abas[2]:
        st.subheader("📝 Registrar Ação")
        # [Aqui vai o seu formulário de registro de ação...]

# --- 3. DICA PARA O SEU MENU PRINCIPAL ---
# No seu arquivo que gerencia as páginas, certifique-se de que está assim:
# if pagina_selecionada == "Busca Ativa":
#     exibir_busca_ativa(supabase)