import streamlit as st
import pandas as pd
import datetime

def exibir_cenario(supabase):
    st.title("📊 Cenário do Dia (Nova Versão)") 
    
    # --- CALENDÁRIO PE 2026 ---
    TRIMESTRES = {
        "1º Tri": (datetime.date(2026, 2, 2), datetime.date(2026, 5, 20)),
        "2º Tri": (datetime.date(2026, 5, 21), datetime.date(2026, 9, 11)),
        "3º Tri": (datetime.date(2026, 9, 12), datetime.date(2026, 12, 30))
    }
    RECESSO = (datetime.date(2026, 7, 10), datetime.date(2026, 7, 24))

    # ==========================================
    # 1. DIVISÃO DA TELA (70% Esq / 30% Dir)
    # ==========================================
    col_esq, col_dir = st.columns([7, 3], gap="large")

    # ==========================================
    # 2. BUSCA DE DADOS GLOBAL (Corrigido para contar só "P")
    # ==========================================
    with col_esq:
        data_hoje = st.date_input("Data de Análise:", value=datetime.date.today(), format="DD/MM/YYYY")
    
    hoje_iso = data_hoje.isoformat()
    df_presentes_hoje = pd.DataFrame()
    n_presentes, total_alunos, n_faltas, perc = 0, 0, 0, 0

    try:
        # Pega o total de alunos na escola
        res_total = supabase.table("alunos").select("id", count="exact").execute()
        total_alunos = res_total.count if res_total.count else 0
        
        # CORREÇÃO: Puxa APENAS quem tem status "P" na data selecionada
        res_freq = supabase.table("frequencia").select("*").eq("data_chamada", hoje_iso).eq("status", "P").execute()
        
        if res_freq.data:
            df_presentes_hoje = pd.DataFrame(res_freq.data)
            col_nome = next((c for c in ['aluno_nome', 'nome_aluno'] if c in df_presentes_hoje.columns), None)
            if col_nome:
                n_presentes = len(df_presentes_hoje[col_nome].unique())
            else:
                n_presentes = len(df_presentes_hoje)
                
        # Calcula as faltas subtraindo os presentes do total de matrículas
        n_faltas = total_alunos - n_presentes
        perc = (n_presentes / total_alunos * 100) if total_alunos > 0 else 0
    except Exception as e:
        st.error(f"⚠️ Erro na conexão: {e}")

    # ==========================================
    # 3. LADO ESQUERDO (Gráficos e Censo)
    # ==========================================
    with col_esq:
        st.divider()
        # --- CENSO ---
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Presentes", n_presentes)
        c2.metric("Ausentes", n_faltas, delta=f"{n_faltas}", delta_color="inverse")
        c3.metric("% Freq", f"{perc:.1f}%")
        c4.metric("Matrícula", total_alunos)

        if RECESSO[0] <= data_hoje <= RECESSO[1]:
            st.info("ℹ️ Período de Recesso Escolar")

        st.divider()

       # --- GRÁFICO DE TURMAS ---
        try:
            if not df_presentes_hoje.empty and 'turma' in df_presentes_hoje.columns:
                st.subheader("🏫 Presença por Turma (Hoje)")
                df_turmas = df_presentes_hoje.groupby('turma').size().reset_index(name='Presentes')
                
                # O parâmetro color="turma" é a mágica que dá uma cor pra cada sala!
                st.bar_chart(
                    data=df_turmas,
                    x="turma",
                    y="Presentes",
                    color="turma" 
                )
            else:
                st.info("Aguardando registros de chamada para gerar o gráfico.")
        except:
            pass

    # ==========================================
    # 4. LADO DIREITO (Tabela + Novo Ranking de Faltas)
    # ==========================================
    with col_dir:
        # --- TABELA DE PRESENTES ---
        st.subheader("📋 Presentes por Sala")
        
        if not df_presentes_hoje.empty and 'turma' in df_presentes_hoje.columns:
            df_resumo = df_presentes_hoje.groupby('turma').size().reset_index(name='Qtd')
            df_resumo = df_resumo.sort_values(by='turma')
            
            st.dataframe(
                df_resumo,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "turma": st.column_config.TextColumn("Turma"),
                    "Qtd": st.column_config.NumberColumn("Qtd")
                }
            )
        else:
            st.info("Nenhuma presença registrada hoje.")

        st.divider()

        # --- NOVO: RANKING DE FALTAS ---
        st.subheader("🚨 Ranking de Faltas")
        st.caption("Acumulado de ausências por estudante")

        try:
            # Puxa a lista de turmas para gerar os botões (Pills)
            # Para evitar erro se a coluna turma estiver vazia em algum lugar
            res_t_raw = supabase.table("alunos").select("turma").execute().data
            lista_turmas = []
            if res_t_raw:
                lista_turmas = sorted(list(set([t['turma'] for t in res_t_raw if t.get('turma')])))
            
            # Usando st.pills
            turma_rank = st.pills("Selecione a Turma:", options=lista_turmas)
            
            if turma_rank:
                # 1. Puxa todos os alunos da turma para garantir que todos apareçam (mesmo os com 0 faltas)
                res_a = supabase.table("alunos").select("nome").eq("turma", turma_rank).execute().data
                df_alunos = pd.DataFrame(res_a)
                
                # 2. Puxa só as FALTAS ("F") dessa turma na tabela de frequência
                res_f = supabase.table("frequencia").select("aluno_nome").eq("turma", turma_rank).eq("status", "F").execute().data
                
                if not df_alunos.empty:
                    df_alunos = df_alunos.rename(columns={'nome': 'aluno_nome'})
                    
                    if res_f:
                        # Conta as faltas
                        df_faltas = pd.DataFrame(res_f)
                        contagem_faltas = df_faltas.groupby('aluno_nome').size().reset_index(name='Faltas')
                        
                        # Junta com a lista de todos os alunos (quem não tiver falta fica com 0)
                        df_ranking = pd.merge(df_alunos, contagem_faltas, on='aluno_nome', how='left').fillna(0)
                    else:
                        # Se ninguém faltou ainda
                        df_ranking = df_alunos.copy()
                        df_ranking['Faltas'] = 0

                    # 3. Organiza o Ranking (Do maior número de faltas para o menor)
                    df_ranking = df_ranking.sort_values(by=['Faltas', 'aluno_nome'], ascending=[False, True])
                    
                    # 4. Adiciona o Ícone
                    df_ranking['Ícone'] = "👤"
                    df_ranking = df_ranking[['Ícone', 'aluno_nome', 'Faltas']] # Reordena as colunas
                    
                    # 5. Exibe a mini-tabela formatada
                    st.dataframe(
                        df_ranking,
                        use_container_width=True,
                        hide_index=True,
                        height=400, # Altura fixa para caber bonitinho na lateral
                        column_config={
                            "Ícone": st.column_config.TextColumn("", width="small"),
                            "aluno_nome": st.column_config.TextColumn("Estudante"),
                            "Faltas": st.column_config.NumberColumn("Faltas Acumuladas", format="%d")
                        }
                    )
        except Exception as e:
            st.error(f"Erro ao gerar ranking: {e}")
