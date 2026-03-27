import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import unicodedata
from urllib.parse import quote
from fpdf import FPDF 

# ==========================================
# 1. FUNÇÕES DE APOIO
# ==========================================
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
        
        # O PULO DO GATO: Verifica se o Dataframe tem a coluna Turma para fazer as quebras de página
        colunas = list(df.columns)
        has_turma = "Turma" in colunas

        if has_turma:
            turmas = sorted(df['Turma'].unique().tolist())
        else:
            turmas = [None] # Roda uma vez só caso não tenha turma separada

        # Loop que cria uma página nova para cada Turma
        for idx, turma in enumerate(turmas):
            pdf.add_page()
            pdf.set_font("Arial", "B", 16)
            pdf.cell(190, 10, "Relatorio de Busca Ativa", ln=True, align="C")
            pdf.set_font("Arial", "", 10)
            pdf.cell(190, 10, f"Gerado em: {data_hoje}", ln=True, align="C")
            pdf.ln(8)
            
            pdf.set_font("Arial", "B", 12)
            titulo_safe = str(titulo_relatorio).encode('latin-1', 'replace').decode('latin-1')
            
            # Ajusta o título para incluir a Turma atual
            if turma:
                if "Turma" in titulo_safe:
                    titulo_tela = titulo_safe
                else:
                    titulo_tela = f"{titulo_safe} - Turma: {turma}"
            else:
                titulo_tela = titulo_safe
                
            pdf.cell(190, 10, titulo_tela.upper(), ln=True, align="L")
            pdf.ln(5)
            
            pdf.set_fill_color(230, 230, 230)
            pdf.set_font("Arial", "B", 9)
            
            # Filtra os dados só para a turma da página atual
            df_turma = df[df['Turma'] == turma] if has_turma else df
            
            # Lógica dinâmica de colunas para suportar o Mapa de Evolução
            if "Aluno" in colunas and has_turma:
                cols_to_print = [c for c in df_turma.columns if c != 'Turma']
                
                # Cálculo de largura para caber todas as colunas de datas
                w_aluno = 70
                w_remaining = 190 - w_aluno
                num_cols = len(cols_to_print) - 1
                w_col = w_remaining / num_cols if num_cols > 0 else 0
                
                # Cabeçalho da Tabela
                pdf.cell(w_aluno, 8, " Estudante", 1, 0, "L", True)
                for col in cols_to_print:
                    if col == "Aluno": continue
                    header_str = "Total" if col == "Total de Fugas" else str(col)
                    pdf.cell(w_col, 8, f"{header_str[:10]}", 1, 0, "C", True)
                pdf.ln()
                
                # Linhas da Tabela
                pdf.set_font("Arial", "", 8)
                for _, row in df_turma.iterrows():
                    nome = str(row.get('Aluno', '')).encode('latin-1', 'replace').decode('latin-1')
                    pdf.cell(w_aluno, 8, f" {nome[:35]}", 1, 0, "L")
                    
                    for col in cols_to_print:
                        if col == "Aluno": continue
                        val = str(row.get(col, '')).encode('latin-1', 'replace').decode('latin-1')
                        pdf.cell(w_col, 8, f"{val[:15]}", 1, 0, "C")
                    pdf.ln()
            else:
                # Fallback genérico original para caso passe uma tabela diferente
                cols_print = colunas[:4]
                w_col = 190 / len(cols_print) if cols_print else 190
                for col in cols_print:
                    pdf.cell(w_col, 8, str(col)[:15], 1, 0, "C", True)
                pdf.ln()
                pdf.set_font("Arial", "", 8)
                for _, row in df_turma.iterrows():
                    for col in cols_print:
                        val = str(row[col]).encode('latin-1', 'replace').decode('latin-1')
                        pdf.cell(w_col, 8, f" {val[:20]}", 1, 0, "L")
                    pdf.ln()
                    
        saida = pdf.output(dest='S')
        return saida.encode('latin-1') if isinstance(saida, str) else bytes(saida)
    except Exception as e:
        return f"Erro PDF: {e}".encode('utf-8')

# ==========================================
# 2. TELA PRINCIPAL
# ==========================================
def exibir_busca_ativa(supabase):
    # --- CSS INJETADO PARA ABAS TIPO "FICHÁRIO" (ARREDONDADAS) ---
    st.markdown("""
        <style>
        div[data-testid="stTabNav"] {
            gap: 5px;
            border-bottom: 2px solid #e0e0e0;
            padding-bottom: 0;
        }
        button[data-testid="stTab"] {
            border: 1px solid #d3d3d3;
            border-bottom: none;
            border-radius: 12px 12px 0 0; 
            padding: 10px 20px;
            background-color: #f8f9fa;
            font-size: 16px;
            color: #555;
            transition: 0.3s;
        }
        button[data-testid="stTab"]:hover {
            background-color: #e9ecef;
        }
        button[data-testid="stTab"][aria-selected="true"] {
            background-color: white;
            border-top: 4px solid #FF4B4B;
            border-left: 1px solid #d3d3d3;
            border-right: 1px solid #d3d3d3;
            color: #FF4B4B;
            font-weight: bold;
            box-shadow: 0px 4px 0px white inset; /* Disfarça a borda inferior */
        }
        </style>
    """, unsafe_allow_html=True)

    st.title("🔎 Busca Ativa")
    st.caption("Inteligência de Dados para Prevenção Escolar")
    
    fuso = pytz.timezone('America/Recife')
    hoje = datetime.now(fuso).strftime('%Y-%m-%d')
    data_hora_atual = datetime.now(fuso).strftime('%d/%m/%Y %H:%M')

    # --- MÉTRICAS DE HOJE ---
    st.subheader(f"📊 Resumo do Dia: {datetime.now(fuso).strftime('%d/%m/%Y')}")
    col1, col2, col3 = st.columns(3)

    try:
        res_faltas = supabase.table("frequencia").select("id", count="exact").eq("data_chamada", hoje).eq("status", "F").execute()
        total_faltas = res_faltas.count if res_faltas.count else 0
        
        res_evasoes = supabase.table("evasoes").select("id", count="exact").eq("data_registro", hoje).execute()
        total_evasoes = res_evasoes.count if res_evasoes.count else 0

        res_pres = supabase.table("frequencia").select("id", count="exact").eq("data_chamada", hoje).eq("status", "P").execute()
        total_presentes = res_pres.count if res_pres.count else 0

        col1.metric("Faltas (Entrada)", total_faltas)
        col2.metric("Evasões (Em aula)", total_evasoes)
        col3.metric("Presentes Agora", total_presentes)
    except Exception as e:
        st.error(f"Erro ao carregar métricas: {e}")

    # --- NOVO: ALERTA E LISTA DE ALUNOS PRESENTES SEM FOTO ---
    try:
        # Busca nomes E turmas dos alunos com presença (P) hoje
        res_pres_dados = supabase.table("frequencia").select("aluno_nome, turma").eq("data_chamada", hoje).eq("status", "P").execute()
        
        if res_pres_dados.data:
            mapa_fotos = listar_arquivos_bucket(supabase)
            lista_sem_foto = []
            
            for item in res_pres_dados.data:
                nome = item.get('aluno_nome', '')
                turma = item.get('turma', 'S/T')
                if nome:
                    nome_limpo = limpar_texto_absoluto(nome)
                    prim_limpo = limpar_texto_absoluto(nome.split()[0])
                    
                    # Se não achar o nome completo E não achar o primeiro nome no bucket
                    if not mapa_fotos.get(nome_limpo) and not mapa_fotos.get(prim_limpo):
                        lista_sem_foto.append({"Aluno": nome, "Turma": turma})
            
            if lista_sem_foto:
                st.warning(f"📸 **Atenção:** {len(lista_sem_foto)} aluno(s) presente(s) hoje estão sem foto no fotograma.")
                
                # Expander para não poluir muito a tela principal
                with st.expander("👀 Ver lista de alunos sem foto"):
                    df_sem_foto = pd.DataFrame(lista_sem_foto)
                    # Organiza por Turma e depois pelo Nome
                    df_sem_foto = df_sem_foto.sort_values(by=['Turma', 'Aluno'])
                    st.dataframe(df_sem_foto, use_container_width=True, hide_index=True)
                    
    except Exception as e:
        pass # Falha silenciosa para não quebrar a UI caso haja erro

    st.markdown("---")

    # ==========================================
    # AS 4 ABAS SOLICITADAS
    # ==========================================
    aba_ranking, aba_zero, aba_lista, aba_registro = st.tabs([
        "🚨 Alertas & Ranking", 
        "❌ Presença Zero", 
        "🗺️ Mapa de Intensidade", 
        "📝 Registrar Ação"
    ])

    # ------------------------------------------
    # ABA 1: RANKING DE FALTAS (COM PDF)
    # ------------------------------------------
    with aba_ranking:
        st.subheader("🏆 Alunos com Mais Faltas")
        
        try:
            res_hist = supabase.table("frequencia").select("aluno_nome, turma").eq("status", "F").execute()
            if res_hist.data:
                df_hist = pd.DataFrame(res_hist.data)
                
                col_t, col_s = st.columns([1, 2])
                with col_t:
                    turma_sel = st.selectbox("📍 Turma:", ["Todas"] + sorted(df_hist['turma'].unique().tolist()), key="rank_turma")
                with col_s:
                    min_f = st.slider("Mínimo de faltas:", 1, 20, 3)

                if turma_sel != "Todas":
                    df_hist = df_hist[df_hist['turma'] == turma_sel]

                ranking = df_hist['aluno_nome'].value_counts().reset_index()
                ranking.columns = ['Aluno', 'Faltas']
                ranking = ranking[ranking['Faltas'] >= min_f].sort_values(by='Faltas', ascending=False)

                if not ranking.empty:
                    df_turmas = df_hist.drop_duplicates('aluno_nome')[['aluno_nome', 'turma']]
                    ranking = ranking.merge(df_turmas, left_on='Aluno', right_on='aluno_nome').drop('aluno_nome', axis=1)
                    ranking.rename(columns={'turma': 'Turma'}, inplace=True)
                    
                    ranking = ranking.sort_values(by=['Turma', 'Faltas'], ascending=[True, False])
                    
                    st.dataframe(ranking, use_container_width=True, hide_index=True)
                    
                    pdf_data = gerar_pdf_relatorio(ranking, f"Ranking de Faltas - Turma: {turma_sel}", data_hora_atual)
                    st.download_button("📄 Baixar Relatório em PDF", pdf_data, f"ranking_faltas_{hoje}.pdf", "application/pdf", use_container_width=True)
                else:
                    st.info("Nenhum aluno atingiu esse limite de faltas na turma selecionada.")
            else:
                st.info("Nenhum registro de falta encontrado no sistema.")
        except Exception as e:
            st.error(f"Erro no ranking: {e}")

    # ------------------------------------------
    # ABA 2: PRESENÇA ZERO (ABANDONO)
    # ------------------------------------------
    with aba_zero:
        st.subheader("❌ Abandono (Presença Zero)")
        st.caption("Alunos que nunca tiveram uma presença registrada no sistema.")
        
        try:
            res_todos = supabase.table("alunos").select("nome, turma").execute()
            res_com_p = supabase.table("frequencia").select("aluno_nome").eq("status", "P").execute()
            
            if res_todos.data:
                df_todos = pd.DataFrame(res_todos.data)
                nomes_p = [x['aluno_nome'] for x in res_com_p.data] if res_com_p.data else []
                
                df_zero = df_todos[~df_todos['nome'].isin(nomes_p)].copy()
                df_zero.rename(columns={'nome': 'Aluno', 'turma': 'Turma'}, inplace=True)
                df_zero = df_zero.sort_values(by=['Turma', 'Aluno'])
                df_zero['Faltas'] = "ZERO PRESENÇA"

                if not df_zero.empty:
                    st.warning(f"Encontrados {len(df_zero)} alunos sem nenhuma presença registrada.")
                    st.dataframe(df_zero[['Aluno', 'Turma']], use_container_width=True, hide_index=True)
                    
                    pdf_z = gerar_pdf_relatorio(df_zero, "Relatorio de Presenca Zero (Abandono)", data_hora_atual)
                    st.download_button("📄 Baixar Relatório de Abandono", pdf_z, f"abandono_{hoje}.pdf", "application/pdf", use_container_width=True)
                else:
                    st.success("Todos os alunos possuem ao menos uma presença registrada.")
        except Exception as e:
            st.error(f"Erro ao processar abandono: {e}")

    # ------------------------------------------
    # ABA 3: MAPA DE INTENSIDADE / FUGAS
    # ------------------------------------------
    with aba_lista:
        st.subheader("🗺️ Mapa de Intensidade de Evasões")
        st.write("Acompanhe o comportamento (frequência salteada) dos estudantes em um período de tempo.")

        col_f1, col_f2 = st.columns([1, 2])
        with col_f1:
            data_inicio = st.date_input("Data Inicial", datetime.now(fuso).date() - pd.Timedelta(days=7), format="DD/MM/YYYY")
            data_fim = st.date_input("Data Final", datetime.now(fuso).date(), format="DD/MM/YYYY")
        
        try:
            res_turmas_evas = supabase.table("evasoes").select("turma").execute()
            lista_t = sorted(list(set([t['turma'] for t in res_turmas_evas.data if t.get('turma')]))) if res_turmas_evas.data else []
            
            with col_f2:
                turma_filtro = st.selectbox("Selecione a Turma:", ["Geral (Todas as Turmas)"] + lista_t, key="lista_turma")

            # INCLUÍDA A DATA DE REGISTRO NA CONSULTA!
            query = supabase.table("evasoes").select("aluno_nome, turma, aula_periodo, data_registro")\
                .gte("data_registro", data_inicio.strftime('%Y-%m-%d'))\
                .lte("data_registro", data_fim.strftime('%Y-%m-%d'))
            
            if turma_filtro != "Geral (Todas as Turmas)":
                query = query.eq("turma", turma_filtro)
                
            res_evas_mapa = query.execute()

            if res_evas_mapa.data:
                df_mapa = pd.DataFrame(res_evas_mapa.data)
                
                # --- O CÓDIGO DO MAPA DE CALOR COMEÇA AQUI ---
                df_mapa['data_dt'] = pd.to_datetime(df_mapa['data_registro'])
                
                # Cria a Tabela Dinâmica contando as fugas por dia
                mapa_evolucao = df_mapa.pivot_table(
                    index=['turma', 'aluno_nome'], 
                    columns='data_dt', 
                    values='aula_periodo', 
                    aggfunc='count'
                ).fillna(0).astype(int)
                
                # Calcula o Total de Fugas no período
                mapa_evolucao['Total de Fugas'] = mapa_evolucao.sum(axis=1)
                
                mapa_evolucao = mapa_evolucao.reset_index()
                mapa_evolucao.rename(columns={'turma': 'Turma', 'aluno_nome': 'Aluno'}, inplace=True)
                
                # Renomeia as colunas de data (de formato DateTime para String 'DD/MM')
                novas_colunas = []
                colunas_datas = []
                for c in mapa_evolucao.columns:
                    if isinstance(c, pd.Timestamp):
                        str_data = c.strftime('%d/%m')
                        novas_colunas.append(str_data)
                        colunas_datas.append(str_data)
                    else:
                        novas_colunas.append(c)
                mapa_evolucao.columns = novas_colunas
                
                # Reorganiza a ordem de visualização
                ordem_colunas = ['Turma', 'Aluno', 'Total de Fugas'] + colunas_datas
                mapa_evolucao = mapa_evolucao[ordem_colunas]
                mapa_evolucao = mapa_evolucao.sort_values(by=['Turma', 'Total de Fugas'], ascending=[True, False])

                # Exibe na tela COM GRADIENTE DE CORES!
                st.dataframe(
                    mapa_evolucao.style.background_gradient(subset=colunas_datas, cmap='YlOrRd'),
                    use_container_width=True, 
                    hide_index=True
                )
                
                # Botão do PDF. Ele vai separar 1 página por Turma automaticamente!
                pdf_evas = gerar_pdf_relatorio(mapa_evolucao, f"Mapa de Evolucao de Evasoes", data_hora_atual)
                st.download_button(
                    label="📄 Baixar Mapa de Evasões (Separado por Turma)", 
                    data=pdf_evas, 
                    file_name=f"mapa_evasoes_{hoje}.pdf", 
                    mime="application/pdf", 
                    use_container_width=True,
                    type="primary"
                )
            else:
                st.success("Nenhuma evasão encontrada para os filtros selecionados.")
                
        except Exception as e:
            st.error(f"Erro ao gerar lista geral: {e}")

    # ------------------------------------------
    # ABA 4: REGISTRAR NOVA OCORRÊNCIA
    # ------------------------------------------
    with aba_registro:
        st.subheader("➕ Registrar Nova Ocorrência")
        
        try:
            # 1. Carregar Alunos
            res_alunos = supabase.table("alunos").select("id, nome, turma").order("nome").execute()
            df_alunos = pd.DataFrame(res_alunos.data) if res_alunos.data else pd.DataFrame()
            
            if not df_alunos.empty:
                col_sel1, col_sel2 = st.columns(2)
                
                with col_sel1:
                    turmas_disponiveis = sorted(df_alunos['turma'].dropna().unique().tolist())
                    turma_escolhida = st.selectbox("1. Selecione a Turma:", turmas_disponiveis)
                
                with col_sel2:
                    alunos_da_turma = df_alunos[df_alunos['turma'] == turma_escolhida]
                    aluno_dict = dict(zip(alunos_da_turma['nome'], alunos_da_turma['id']))
                    aluno_nome_escolhido = st.selectbox("2. Selecione o Estudante:", list(aluno_dict.keys()))
                
                st.markdown("---")
                
                # Layout Foto (Esquerda) e Formulário (Direita) - Igual ao Print 4
                col_foto, col_form = st.columns([1, 2.5])
                
                with col_foto:
                    mapa_fotos = listar_arquivos_bucket(supabase)
                    url_base = f"{supabase.supabase_url}/storage/v1/object/public/fotos-alunos/"
                    foto_fallback = "https://cdn-icons-png.flaticon.com/512/149/149071.png"
                    
                    nome_limpo = limpar_texto_absoluto(aluno_nome_escolhido)
                    prim_limpo = limpar_texto_absoluto(aluno_nome_escolhido.split()[0]) if aluno_nome_escolhido else ""
                    nome_arq = mapa_fotos.get(nome_limpo) or mapa_fotos.get(prim_limpo)
                    
                    url_final = f"{url_base}{quote(nome_arq)}" if nome_arq else foto_fallback
                    
                    st.markdown(f"""
                        <div style="background-color: #e9ecef; border-radius: 10px; padding: 15px; text-align: center;">
                            <img src="{url_final}" style="width: 100%; border-radius: 8px; object-fit: cover;">
                            <p style="margin-top: 10px; font-weight: bold; font-size: 14px; margin-bottom: 0;">{aluno_nome_escolhido}</p>
                            <p style="font-size: 12px; color: #666; margin-top: 0;">{turma_escolhida}</p>
                        </div>
                    """, unsafe_allow_html=True)

                with col_form:
                    with st.form("form_ocorrencias", clear_on_submit=True):
                        # Baseado na sua tabela ocorrencias_disciplinares
                        tipo_acao = st.selectbox("Tipo de Ação:", ["Advertência", "Suspensão", "Visita Domiciliar", "Conselho Tutelar", "Ligação para Família", "Outros"])
                        motivo = st.text_area("Motivo da ocorrência:")
                        matricula = st.text_input("Sua Matrícula (Assinatura):")
                        
                        btn_salvar = st.form_submit_button("🚨 Gravar Ocorrência", type="primary", use_container_width=True)
                        
                        if btn_salvar:
                            if not motivo.strip() or not matricula.strip():
                                st.warning("⚠️ O motivo e a matrícula são obrigatórios.")
                            else:
                                id_aluno = aluno_dict[aluno_nome_escolhido]
                                
                                dados_insert = {
                                    "aluno_id": id_aluno,
                                    "aluno_nome": aluno_nome_escolhido,
                                    "turma": turma_escolhida,
                                    "tipo_ocorrencia": tipo_acao,
                                    "motivo": motivo,
                                    "quem_registrou": matricula,
                                    "status": "Ativa"
                                }
                                
                                supabase.table("ocorrencias_disciplinares").insert(dados_insert).execute()
                                st.success("✅ Ocorrência registrada com sucesso!")
                                st.balloons()
            else:
                st.warning("Nenhum aluno cadastrado no sistema para registrar ocorrências.")
        except Exception as e:
            st.error(f"Erro ao carregar o formulário de registro: {e}")

if __name__ == "__main__":
    st.warning("Rode através do seu menu principal `app.py` para garantir a conexão com o banco.")