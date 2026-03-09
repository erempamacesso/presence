import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import unicodedata
from urllib.parse import quote
import streamlit.components.v1 as components  
from fpdf import FPDF # Importação necessária para o PDF

# --- FUNÇÕES DE APOIO PARA AS FOTOS ---
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
        for arq in arquivos:
            nome_original = arq.get('name')
            if nome_original:
                nome_sem_ext = nome_original.rsplit('.', 1)[0] if '.' in nome_original else nome_original
                mapa[limpar_texto_absoluto(nome_sem_ext)] = nome_original
        return mapa
    except: return {}

def exibir_busca_ativa(supabase):
    st.title("🔎 Busca Ativa")
    st.caption("Inteligência de Dados para Prevenção Escolar")
    st.markdown("---")

    fuso = pytz.timezone('America/Recife')
    hoje = datetime.now(fuso).strftime('%Y-%m-%d')

    # --- 1. MÉTRICAS RÁPIDAS (HOJE) ---
    st.subheader(f"📊 Resumo do Dia: {datetime.now(fuso).strftime('%d/%m/%Y')}")
    
    col1, col2, col3 = st.columns(3)

    try:
        # Puxamos as faltas
        res_faltas = supabase.table("frequencia").select("id", count="exact").eq("data_chamada", hoje).eq("status", "F").execute()
        total_faltas = res_faltas.count if res_faltas.count else 0
        
        # Puxamos as evasões
        res_evasoes = supabase.table("evasoes").select("id", count="exact").eq("data_registro", hoje).execute()
        total_evasoes = res_evasoes.count if res_evasoes.count else 0

        # Puxamos as presenças
        res_pres = supabase.table("frequencia").select("*").eq("data_chamada", hoje).eq("status", "P").execute()
        total_presentes = len(res_pres.data) if res_pres.data else 0

        col1.metric("Faltas (Entrada)", total_faltas)
        col2.metric("Evasões (Em aula)", total_evasoes)
        col3.metric("Presentes Agora", total_presentes)
        
        # --- BLOCO: ALUNOS PRESENTES SEM FOTO + GERADOR DE PDF ---
        if res_pres.data:
            df_presentes = pd.DataFrame(res_pres.data)
            coluna_nome = 'aluno_nome' if 'aluno_nome' in df_presentes.columns else 'nome'
            mapa_fotos = listar_arquivos_bucket(supabase)
            
            sem_foto = []
            for _, aluno in df_presentes.iterrows():
                nome_aluno = aluno[coluna_nome]
                if limpar_texto_absoluto(nome_aluno) not in mapa_fotos:
                    sem_foto.append({"Estudante": nome_aluno, "Turma": aluno.get('turma', 'N/A')})
            
            if sem_foto:
                with st.expander(f"⚠️ {len(sem_foto)} Alunos presentes hoje não possuem foto"):
                    st.info("Estes alunos estão na escola. Ótima oportunidade para atualizar o sistema!")
                    st.dataframe(pd.DataFrame(sem_foto), use_container_width=True, hide_index=True)
                    
                    # Gerar PDF em memória
                    try:
                        pdf = FPDF()
                        pdf.add_page()
                        pdf.set_font("Arial", "B", 16)
                        pdf.cell(190, 10, "Pendencias de Fotos - Alunos Presentes", ln=True, align="C")
                        pdf.set_font("Arial", "", 10)
                        pdf.cell(190, 10, f"Data: {datetime.now(fuso).strftime('%d/%m/%Y')} | Total: {len(sem_foto)}", ln=True, align="C")
                        pdf.ln(10)
                        pdf.set_fill_color(230, 230, 230)
                        pdf.set_font("Arial", "B", 12)
                        pdf.cell(130, 10, " Nome do Estudante", 1, 0, "L", True)
                        pdf.cell(60, 10, " Turma", 1, 1, "C", True)
                        pdf.set_font("Arial", "", 11)
                        for s in sem_foto:
                            pdf.cell(130, 10, f" {s['Estudante']}", 1)
                            pdf.cell(60, 10, f" {s['Turma']}", 1, 1, "C")
                        
                        pdf_bytes = pdf.output(dest='S').encode('latin-1', errors='replace')
                        st.download_button(
                            label="📄 Baixar Lista para Impressão (PDF)",
                            data=pdf_bytes,
                            file_name=f"fotos_pendentes_{hoje}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                    except Exception as e_pdf:
                        st.error(f"Erro ao gerar botão de PDF: {e_pdf}")

    except Exception as e:
        st.error(f"Erro ao carregar métricas: {e}")

    st.markdown("---")

    # ==========================================
    # CRIANDO AS ABAS
    # ==========================================
    aba_ranking, aba_mapa, aba_registros = st.tabs(["🚨 Alertas & Ranking", "🗺️ Mapa de Evasões", "📝 Registrar Ação"])

    with aba_ranking:
        st.subheader("🚨 Alerta de Evasão Interna")
        try:
            pres_hoje = supabase.table("frequencia").select("aluno_nome, turma").eq("data_chamada", hoje).eq("status", "P").execute()
            evas_hoje = supabase.table("evasoes").select("aluno_nome, turma, aula_periodo").eq("data_registro", hoje).execute()
            if pres_hoje.data and evas_hoje.data:
                df_pres = pd.DataFrame(pres_hoje.data)
                df_evas = pd.DataFrame(evas_hoje.data)
                fugoes = df_evas[df_evas['aluno_nome'].isin(df_pres['aluno_nome'])]
                if not fugoes.empty:
                    st.warning(f"Atenção: {len(fugoes)} alunos entraram na escola mas não estão em sala.")
                    st.dataframe(fugoes[['aluno_nome', 'turma', 'aula_periodo']], use_container_width=True, hide_index=True)
                else:
                    st.success("Nenhuma evasão interna detectada hoje.")
        except: pass

        st.markdown("---")
        st.subheader("🏆 Histórico de Faltas por Turma")
        try:
            res_hist = supabase.table("frequencia").select("aluno_nome, turma").eq("status", "F").execute()
            if res_hist.data:
                df_hist = pd.DataFrame(res_hist.data)
                lista_turmas = sorted(df_hist['turma'].dropna().unique().tolist())
                turma_sel = st.selectbox("📍 Selecione a Turma:", ["Todas as Turmas"] + lista_turmas)
                if turma_sel != "Todas as Turmas":
                    df_hist = df_hist[df_hist['turma'] == turma_sel]
                
                ranking = df_hist['aluno_nome'].value_counts().reset_index()
                ranking.columns = ['Aluno', 'Faltas']
                df_turmas = df_hist.drop_duplicates('aluno_nome')[['aluno_nome', 'turma']]
                ranking = ranking.merge(df_turmas, left_on='Aluno', right_on='aluno_nome').drop('aluno_nome', axis=1).sort_values(by='Aluno')

                mapa_f = listar_arquivos_bucket(supabase)
                url_b = f"{st.secrets['SUPABASE_URL']}/storage/v1/object/public/fotos-alunos/"
                
                html_table = "<style>.foto{width:60px;height:60px;border-radius:50%;object-fit:cover;}.tab{width:100%;border-collapse:collapse;} .tab td, .tab th{padding:10px;border-bottom:1px solid #ddd;}</style><table class='tab'><tr><th>Foto</th><th>Nome</th><th>Turma</th><th>Faltas</th></tr>"
                for _, r in ranking.iterrows():
                    n_limpo = limpar_texto_absoluto(r['Aluno'])
                    arq = mapa_f.get(n_limpo)
                    f_url = f"{url_b}{quote(arq)}" if arq else "https://cdn-icons-png.flaticon.com/512/149/149071.png"
                    html_table += f"<tr><td><img src='{f_url}' class='foto'></td><td>{r['Aluno']}</td><td>{r['turma']}</td><td>{r['Faltas']}</td></tr>"
                html_table += "</table>"
                components.html(html_table, height=400, scrolling=True)
        except: pass

    # Aba de Mapa e Registros permanecem com a lógica que você já tem
    with aba_mapa:
        st.info("Mapa de comportamento de evasões em desenvolvimento.")
    with aba_registros:
        st.info("Área de registro de ações da equipe.")
