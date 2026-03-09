import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import unicodedata
from urllib.parse import quote
import streamlit.components.v1 as components  
from fpdf import FPDF 

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
        res_faltas = supabase.table("frequencia").select("id", count="exact").eq("data_chamada", hoje).eq("status", "F").execute()
        total_faltas = res_faltas.count if res_faltas.count else 0
        
        res_evasoes = supabase.table("evasoes").select("id", count="exact").eq("data_registro", hoje).execute()
        total_evasoes = res_evasoes.count if res_evasoes.count else 0

        res_pres = supabase.table("frequencia").select("*").eq("data_chamada", hoje).eq("status", "P").execute()
        total_presentes = len(res_pres.data) if res_pres.data else 0

        col1.metric("Faltas (Entrada)", total_faltas)
        col2.metric("Evasões (Em aula)", total_evasoes)
        col3.metric("Presentes Agora", total_presentes)
        
        # --- ALUNOS PRESENTES SEM FOTO + GERADOR DE PDF ---
        if res_pres.data:
            df_presentes = pd.DataFrame(res_pres.data)
            coluna_nome = 'aluno_nome' if 'aluno_nome' in df_presentes.columns else 'nome'
            mapa_fotos_atual = listar_arquivos_bucket(supabase)
            
            sem_foto = []
            for _, aluno in df_presentes.iterrows():
                nome_aluno = aluno[coluna_nome]
                if limpar_texto_absoluto(nome_aluno) not in mapa_fotos_atual:
                    sem_foto.append({"Estudante": nome_aluno, "Turma": aluno.get('turma', 'N/A')})
            
            if sem_foto:
                with st.expander(f"⚠️ {len(sem_foto)} Alunos presentes hoje não possuem foto"):
                    st.info("Estes alunos estão na escola. Ótima oportunidade para atualizar o sistema!")
                    st.dataframe(pd.DataFrame(sem_foto), use_container_width=True, hide_index=True)
                    
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
                            nome_pdf = s['Estudante'].encode('latin-1', 'replace').decode('latin-1')
                            turma_pdf = s['Turma'].encode('latin-1', 'replace').decode('latin-1')
                            pdf.cell(130, 10, f" {nome_pdf}", 1)
                            pdf.cell(60, 10, f" {turma_pdf}", 1, 1, "C")
                        
                        pdf_bytes = pdf.output(dest='S').encode('latin-1')
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
    aba_ranking, aba_mapa, aba_registros = st.tabs(["🚨 Alertas & Ranking", "🗺️ Mapa de Evasões 2.0", "📝 Registrar Ação"])

    # ==========================================
    # ABA 1: ALERTA INTERNO E RANKING DE FALTAS
    # ==========================================
    with aba_ranking:
        st.subheader("🚨 Alerta de Evasão Interna")
        st.write("Alunos que deram presença na entrada, mas foram registrados saindo de alguma aula.")

        try:
            pres_hoje = supabase.table("frequencia").select("aluno_nome, turma").eq("data_chamada", hoje).eq("status", "P").execute()
            evas_hoje = supabase.table("evasoes").select("aluno_nome, turma, aula_periodo").eq("data_registro", hoje).execute()

            if pres_hoje.data and evas_hoje.data:
                df_pres = pd.DataFrame(pres_hoje.data)
                df_evas = pd.DataFrame(evas_hoje.data)
                fugoes_internos = df_evas[df_evas['aluno_nome'].isin(df_pres['aluno_nome'])]
                
                if not fugoes_internos.empty:
                    st.warning(f"Atenção: {len(fugoes_internos)} alunos entraram na escola mas não estão em sala.")
                    st.dataframe(fugoes_internos[['aluno_nome', 'turma', 'aula_periodo']], use_container_width=True, hide_index=True)
                else:
                    st.success("Nenhuma evasão interna detectada hoje.")
            else:
                st.info("Aguardando registros para cruzar dados hoje.")
        except Exception as e:
            st.error(f"Erro no processamento: {e}")

        st.markdown("---")
        st.subheader("🏆 Histórico de Faltas por Turma")
        
        try:
            res_hist = supabase.table("frequencia").select("aluno_nome, turma").eq("status", "F").execute()
            
            if res_hist.data:
                df_hist = pd.DataFrame(res_hist.data)
                lista_turmas = sorted(df_hist['turma'].dropna().unique().tolist())
                
                col_turma, col_slider = st.columns([1, 2])
                with col_turma:
                    turma_selecionada = st.selectbox("📍 Filtrar por Turma:", ["Todas as Turmas"] + lista_turmas)
                with col_slider:
                    min_faltas = st.slider("Filtrar a partir de quantas faltas?", min_value=1, max_value=20, value=2)
                
                if turma_selecionada != "Todas as Turmas":
                    df_hist = df_hist[df_hist['turma'] == turma_selecionada]

                if df_hist.empty:
                    st.success(f"Nenhuma falta registrada para a turma selecionada! 🎉")
                else:
                    ranking = df_hist['aluno_nome'].value_counts().reset_index()
                    ranking.columns = ['Aluno', 'Faltas']
                    ranking = ranking[ranking['Faltas'] >= min_faltas]

                    if ranking.empty:
                        st.info("Nenhum aluno atingiu esse número de faltas com os filtros atuais.")
                    else:
                        df_turmas = df_hist.drop_duplicates('aluno_nome')[['aluno_nome', 'turma']]
                        ranking = ranking.merge(df_turmas, left_on='Aluno', right_on='aluno_nome').drop('aluno_nome', axis=1)
                        ranking = ranking.sort_values(by='Aluno', ascending=True)

                        mapa_fotos = listar_arquivos_bucket(supabase)
                        url_base = f"{st.secrets['SUPABASE_URL']}/storage/v1/object/public/fotos-alunos/"
                        foto_fallback = "https://cdn-icons-png.flaticon.com/512/149/149071.png"

                        def buscar_url_foto(nome_aluno):
                            nome_limpo = limpar_texto_absoluto(nome_aluno)
                            prim_limpo = limpar_texto_absoluto(nome_aluno.split()[0])
                            nome_arq = mapa_fotos.get(nome_limpo) or mapa_fotos.get(prim_limpo)
                            if nome_arq:
                                return f"{url_base}{quote(nome_arq)}"
                            return foto_fallback

                        ranking['Foto'] = ranking['Aluno'].apply(buscar_url_foto)

                        html_table = """
                        <style>
                            body { font-family: sans-serif; margin: 0; padding: 0; background-color: transparent;}
                            .ranking-table {width: 100%; border-collapse: collapse; text-align: left; background: white; border-radius: 8px; overflow: hidden; border: 1px solid #ddd;}
                            .ranking-table th {background-color: #f0f2f6; padding: 12px; border-bottom: 2px solid #ddd; color: #31333F; font-size: 14px;}
                            .ranking-table td {padding: 10px; border-bottom: 1px solid #f0f2f6; vertical-align: middle; color: #31333F; font-size: 14px;}
                            .foto-aluno {width: 65px; height: 65px; object-fit: cover; border-radius: 50%; border: 2px solid #e0e0e0;}
                            .alerta-bar-bg {width: 100%; background-color: #ffe0e0; border-radius: 5px; height: 12px; margin-top: 5px;}
                            .alerta-bar-fg {height: 12px; border-radius: 5px; background-color: #ff4b4b;}
                        </style>
                        <table class="ranking-table">
                            <tr>
                                <th style="width: 80px;">📸 Foto</th>
                                <th>Nome do Estudante</th>
                                <th>Turma</th>
                                <th>🔥 Histórico de Faltas</th>
                            </tr>
                        """
                        
                        for _, row in ranking.iterrows():
                            pct = (row['Faltas'] / 10) * 100 
                            pct = min(pct, 100) 
                            html_table += f"""
                            <tr>
                                <td><img src="{row['Foto']}" class="foto-aluno"></td>
                                <td style="font-weight: 600;">{row['Aluno']}</td>
                                <td>{row['turma']}</td>
                                <td>
                                    <div style="font-size: 14px; font-weight: bold;">{row['Faltas']} faltas acumuladas</div>
                                    <div class="alerta-bar-bg"><div class="alerta-bar-fg" style="width: {pct}%;"></div></div>
                                </td>
                            </tr>
                            """
                        html_table += "</table>"
                        altura_tabela = min(len(ranking) * 90 + 50, 600)
                        components.html(html_table, height=altura_tabela, scrolling=True)

            else:
                st.info("Ainda não há histórico de faltas acumulado.")
        except Exception as e:
            st.error(f"Erro ao gerar tabela visual: {e}")

    # ==========================================
    # ABA 2: MAPA DE COMPORTAMENTO DE EVASÕES 2.0 (NOVO)
    # ==========================================
    with aba_mapa:
        st.subheader("🗺️ Inteligência e Mapa de Evasões")
        st.write("Analise o padrão de fuga visualmente para tomar decisões estratégicas.")

        # Filtros de Data
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            hoje_data = datetime.now(fuso).date()
            data_inicio = st.date_input("Data Inicial", hoje_data - pd.Timedelta(days=15), format="DD/MM/YYYY")
        with col_f2:
            data_fim = st.date_input("Data Final", hoje_data, format="DD/MM/YYYY")

        st.caption(f"📍 Analisando período: **{data_inicio.strftime('%d/%m/%Y')}** a **{data_fim.strftime('%d/%m/%Y')}**")

        try:
            # Puxando as evasões do banco no período
            query = supabase.table("evasoes").select("aluno_nome, turma, aula_periodo, data_registro")\
                .gte("data_registro", data_inicio.strftime('%Y-%m-%d'))\
                .lte("data_registro", data_fim.strftime('%Y-%m-%d'))
            
            res_evas = query.execute()

            if res_evas.data:
                df_mapa = pd.DataFrame(res_evas.data)
                
                # --- GRÁFICOS VISUAIS ---
                col_graf1, col_graf2 = st.columns(2)
                
                with col_graf1:
                    st.write("**⏰ Horários Mais Críticos**")
                    # Contagem por período de aula
                    graf_aulas = df_mapa['aula_periodo'].value_counts().reset_index()
                    graf_aulas.columns = ['Período/Aula', 'Fugas']
                    st.bar_chart(graf_aulas.set_index('Período/Aula'), color="#ff4b4b")

                with col_graf2:
                    st.write("**📈 Evolução nos Últimos Dias**")
                    # Contagem por dia
                    graf_dias = df_mapa['data_registro'].value_counts().reset_index()
                    graf_dias.columns = ['Data', 'Fugas']
                    graf_dias = graf_dias.sort_values('Data')
                    st.line_chart(graf_dias.set_index('Data'), color="#4b8bff")

                st.markdown("---")
                
                col_graf3, col_graf4 = st.columns([1, 2])
                
                with col_graf3:
                    st.write("**🏆 Top Turmas com Mais Evasões**")
                    graf_turmas = df_mapa['turma'].value_counts().reset_index()
                    graf_turmas.columns = ['Turma', 'Total Fugas']
                    st.dataframe(graf_turmas, use_container_width=True, hide_index=True)

                with col_graf4:
                    st.write("**🕵️ Tabela de Alunos Fujões**")
                    # Agrupando por aluno como era no mapa original
                    resumo_evas = df_mapa.groupby(['turma', 'aluno_nome']).agg(
                        Total_Evasoes=('aula_periodo', 'count'),
                        Aulas_Evadidas=('aula_periodo', lambda x: ', '.join(x.unique()))
                    ).reset_index()
                    resumo_evas = resumo_evas.sort_values(by=['Total_Evasoes'], ascending=False)
                    resumo_evas.columns = ['Turma', 'Nome do Aluno', 'Qtd de Fugas', 'Aulas Gazeadas']
                    st.dataframe(resumo_evas, use_container_width=True, hide_index=True)

            else:
                st.success("🎉 Tudo tranquilo por aqui! Nenhuma evasão registrada nesse período.")
                
        except Exception as e:
            st.error(f"Erro ao processar dados de evasão: {e}")

    # ==========================================
    # ABA 3: REGISTRO DE AÇÃO (BUSCA ATIVA)
    # ==========================================
    with aba_registros:
        st.subheader("📝 Registrar Ação da Equipe")
        st.write("Adicione um novo registro no histórico do estudante para ativar o alerta no Fotograma.")

        try:
            res_alunos = supabase.table("alunos").select("id, nome, turma").order("nome").execute()
            if res_alunos.data:
                
                def formatar_aluno(aluno):
                    return f"{aluno['nome']} (Turma: {aluno['turma']})"

                with st.form("form_busca_ativa", clear_on_submit=True):
                    aluno_selecionado = st.selectbox("1. Selecione o Estudante:", options=res_alunos.data, format_func=formatar_aluno)
                    
                    acao = st.text_area("2. O que foi feito? (Ex: Ligação para a mãe, visita domiciliar, encaminhamento ao conselho)", height=100)
                    
                    col_status, col_resp = st.columns(2)
                    with col_status:
                        status = st.selectbox("3. Status Atual:", ["Em acompanhamento", "Alerta", "Resolvido", "Evasão Confirmada"])
                    with col_resp:
                        responsavel = st.text_input("4. Quem está registrando? (Seu Nome/Cargo)")

                    submit = st.form_submit_button("💾 Salvar Registro de Ação", type="primary", use_container_width=True)

                    if submit:
                        if not acao.strip() or not responsavel.strip():
                            st.warning("⚠️ Por favor, preencha a ação realizada e o responsável.")
                        else:
                            dados_insert = {
                                "aluno_id": aluno_selecionado['id'],
                                "acao_realizada": acao,
                                "status_atual": status,
                                "quem_registrou": responsavel
                            }
                            supabase.table("historico_busca_ativa").insert(dados_insert).execute()
                            st.success(f"✅ Ação registrada com sucesso para {aluno_selecionado['nome']}!")
                            st.info("O Fotograma já foi atualizado com a moldura de status.")
            else:
                st.warning("Nenhum aluno cadastrado no sistema ainda.")
        except Exception as e:
            st.error(f"Erro ao carregar o formulário: {e}")
