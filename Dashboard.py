import streamlit as st
import pandas as pd
import datetime
import io
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

def exibir_cenario(supabase):
    st.title("📊 Cenário do Dia") 
    
    # --- CALENDÁRIO PE 2026 ---
    TRIMESTRES = {
        "1º Tri": (datetime.date(2026, 2, 2), datetime.date(2026, 5, 20)),
        "2º Tri": (datetime.date(2026, 5, 21), datetime.date(2026, 9, 11)),
        "3º Tri": (datetime.date(2026, 9, 12), datetime.date(2026, 12, 30))
    }
    RECESSO = (datetime.date(2026, 7, 10), datetime.date(2026, 7, 24))

    # ==========================================
    # 1. DIVISÃO DA TELA SUPERIOR (70% Esq / 30% Dir)
    # ==========================================
    col_esq, col_dir = st.columns([7, 3], gap="large")

    # ==========================================
    # 2. BUSCA DE DADOS GLOBAL
    # ==========================================
    with col_esq:
        data_hoje = st.date_input("Data de Análise:", value=datetime.date.today(), format="DD/MM/YYYY")
    
    hoje_iso = data_hoje.isoformat()
    df_presentes_hoje = pd.DataFrame()
    df_matriculas = pd.DataFrame()
    n_presentes, total_alunos, n_faltas, perc = 0, 0, 0, 0

    try:
        # Pega todos os alunos para calcular Matrícula e distribuição por turmas
        res_total = supabase.table("alunos").select("id, turma").execute()
        
        if res_total.data:
            df_matriculas = pd.DataFrame(res_total.data)
            total_alunos = len(df_matriculas)
        else:
            total_alunos = 0
        
        # Pega presentes do dia
        res_freq = supabase.table("frequencia").select("*").eq("data_chamada", hoje_iso).eq("status", "P").execute()
        
        if res_freq.data:
            df_presentes_hoje = pd.DataFrame(res_freq.data)
            col_nome = next((c for c in ['aluno_nome', 'nome_aluno'] if c in df_presentes_hoje.columns), None)
            
            if col_nome:
                n_presentes = len(df_presentes_hoje[col_nome].unique())
            else:
                n_presentes = len(df_presentes_hoje)
                
        # Cálculos de faltas e percentual
        n_faltas = total_alunos - n_presentes
        perc = (n_presentes / total_alunos * 100) if total_alunos > 0 else 0
        
    except Exception as e:
        st.error(f"⚠️ Erro na conexão: {e}")

    # ==========================================
    # 3. LADO ESQUERDO (Gráficos e Censo)
    # ==========================================
    with col_esq:
        st.divider()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Presentes", n_presentes)
        c2.metric("Ausentes do Dia", n_faltas, delta=f"{n_faltas}", delta_color="inverse")
        c3.metric("% Freq", f"{perc:.1f}%")
        c4.metric("Matrícula Geral", total_alunos)

        if RECESSO[0] <= data_hoje <= RECESSO[1]:
            st.info("ℹ️ Período de Recesso Escolar")

        st.divider()
        
        # ==========================================
        # 🆕 NOVA SEÇÃO: DETALHAMENTO DE MATRÍCULAS (ACORDEÃO)
        # ==========================================
        if not df_matriculas.empty and 'turma' in df_matriculas.columns:
            # Função rápida para identificar o ano baseado no nome da turma
            def identificar_ano(turma):
                turma_str = str(turma).upper()
                if '1' in turma_str: return "1º Ano"
                if '2' in turma_str: return "2º Ano"
                if '3' in turma_str: return "3º Ano"
                return "Outras"
            
            df_matriculas['serie'] = df_matriculas['turma'].apply(identificar_ano)
            resumo_series = df_matriculas.groupby(['serie', 'turma']).size().reset_index(name='qtd')
            
            # Divide os botões de expansão em 3 colunas para economizar ainda mais espaço na tela
            col_s1, col_s2, col_s3 = st.columns(3)
            colunas_disp = {"1º Ano": col_s1, "2º Ano": col_s2, "3º Ano": col_s3}
            
            for serie in ["1º Ano", "2º Ano", "3º Ano"]:
                df_serie_atual = resumo_series[resumo_series['serie'] == serie].sort_values(by='turma')
                
                if not df_serie_atual.empty:
                    total_serie = df_serie_atual['qtd'].sum()
                    with colunas_disp[serie].expander(f"🎓 {serie} (Total: {total_serie})"):
                        for _, row in df_serie_atual.iterrows():
                            # Mostra de forma limpa: Ex: "1º A: 35 alunos"
                            st.markdown(f"**{row['turma']}**: {row['qtd']} alunos")
        
        st.divider()

        # Gráfico esticado para mostrar todas as turmas
        try:
            if not df_presentes_hoje.empty and 'turma' in df_presentes_hoje.columns:
                st.subheader("🏫 Presença por Turma")
                df_turmas = df_presentes_hoje.groupby('turma').size().reset_index(name='Presentes')
                
                # O parâmetro height=400 estica o gráfico para baixo, dando espaço para o Eixo X
                st.bar_chart(
                    data=df_turmas,
                    x="turma",
                    y="Presentes",
                    color="turma",
                    height=450, 
                    use_container_width=True
                )
            else:
                st.info("Aguardando registros de chamada para gerar o gráfico.")
        except:
            pass

    # ==========================================
    # 4. LADO DIREITO (Tabela de Presentes)
    # ==========================================
    with col_dir:
        st.subheader("📋 Resumo por Sala")
        
        if not df_presentes_hoje.empty and 'turma' in df_presentes_hoje.columns:
            df_resumo = df_presentes_hoje.groupby('turma').size().reset_index(name='Qtd')
            df_resumo = df_resumo.sort_values(by='turma')
            
            st.dataframe(
                df_resumo,
                use_container_width=True,
                hide_index=True,
                height=530, # 👇 A mágica está aqui! Altura travada para caber as 13 turmas sem scroll
                column_config={
                    "turma": st.column_config.TextColumn("Turma"),
                    "Qtd": st.column_config.NumberColumn("Presentes")
                }
            )
        else:
            st.info("Nenhuma presença registrada.")

    # ==========================================
    # 5. ÁREA INFERIOR (Alunos Ausentes no Dia)
    # ==========================================
    st.divider() 
    st.subheader(f"🚨 Estudantes Ausentes ({data_hoje.strftime('%d/%m/%Y')})")
    st.caption("Selecione uma turma para ver quem faltou hoje e baixar o relatório.")

    try:
        # Busca todas as turmas para montar os botões (pills)
        res_t_raw = supabase.table("alunos").select("turma").execute().data
        lista_turmas = []
        if res_t_raw:
            lista_turmas = sorted(list(set([t['turma'] for t in res_t_raw if t.get('turma')])))
        
        if lista_turmas:
            # O st.pills substitui o selectbox
            turma_selecionada = st.pills("Turmas disponíveis:", options=lista_turmas)
            
            if turma_selecionada:
                # Busca na tabela de frequência apenas quem tirou falta (F) hoje
                res_f = supabase.table("frequencia") \
                    .select("aluno_nome") \
                    .eq("data_chamada", hoje_iso) \
                    .eq("turma", turma_selecionada) \
                    .eq("status", "F") \
                    .execute().data
                
                if res_f:
                    df_faltosos = pd.DataFrame(res_f)
                    df_faltosos = df_faltosos.sort_values(by="aluno_nome")
                    
                    # ---------------------------------------------------------
                    # 🚀 NOVA LÓGICA: MOTOR DE GERAÇÃO DO PDF EM MEMÓRIA
                    # ---------------------------------------------------------
                    buffer = io.BytesIO()
                    pdf = canvas.Canvas(buffer, pagesize=A4)
                    
                    # Título do PDF
                    pdf.setFont("Helvetica-Bold", 16)
                    pdf.drawString(50, 800, f"Relatório de Estudantes Ausentes - {turma_selecionada}")
                    
                    # Data
                    pdf.setFont("Helvetica", 12)
                    pdf.drawString(50, 780, f"Data da Falta: {data_hoje.strftime('%d/%m/%Y')}")
                    
                    # Subtítulo da lista
                    y_pos = 740
                    pdf.setFont("Helvetica-Bold", 12)
                    pdf.drawString(50, y_pos, f"Total de ausentes: {len(df_faltosos)} estudantes")
                    y_pos -= 20
                    
                    # Listando os nomes
                    pdf.setFont("Helvetica", 12)
                    for idx, row in df_faltosos.iterrows():
                        pdf.drawString(60, y_pos, f"• {row['aluno_nome']}")
                        y_pos -= 20
                        
                        # Se a página acabar, cria uma nova folha automaticamente
                        if y_pos < 50:
                            pdf.showPage()
                            y_pos = 800
                            pdf.setFont("Helvetica", 12)
                            
                    pdf.save()
                    buffer.seek(0)
                    pdf_bytes = buffer.getvalue()
                    # ---------------------------------------------------------

                    # Tratamento visual da tabela na tela
                    df_exibicao = df_faltosos.copy()
                    df_exibicao['Ícone'] = "❌"
                    df_exibicao = df_exibicao[['Ícone', 'aluno_nome']] 
                    
                    # Centraliza a tabela e o botão para manter a elegância visual
                    col_vazia1, col_tabela, col_vazia2 = st.columns([1, 2, 1])
                    with col_tabela:
                        st.dataframe(
                            df_exibicao,
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                "Ícone": st.column_config.TextColumn("", width="small"),
                                "aluno_nome": st.column_config.TextColumn("Nome do Estudante")
                            }
                        )
                        
                        # 📥 BOTÃO DE DOWNLOAD DO PDF
                        st.download_button(
                            label="📥 Baixar Lista em PDF",
                            data=pdf_bytes,
                            file_name=f"Faltas_{turma_selecionada}_{data_hoje.strftime('%d_%m_%Y')}.pdf",
                            mime="application/pdf",
                            type="primary",
                            use_container_width=True
                        )
                else:
                    st.success(f"🎉 Excelente! Nenhuma falta registrada para a turma {turma_selecionada} hoje.")
                    
    except Exception as e:
        st.error(f"Erro ao carregar lista de ausentes: {e}")