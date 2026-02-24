import streamlit as st
import pandas as pd
import datetime

def exibir_cenario(supabase):
    # 👇 Se isso não aparecer na tela, o GitHub ainda não atualizou seu app!
    st.title("📊 Cenário do Dia (Nova Versão)") 
    
    # --- CALENDÁRIO PE 2026 ---
    TRIMESTRES = {
        "1º Tri": (datetime.date(2026, 2, 2), datetime.date(2026, 5, 20)),
        "2º Tri": (datetime.date(2026, 5, 21), datetime.date(2026, 9, 11)),
        "3º Tri": (datetime.date(2026, 9, 12), datetime.date(2026, 12, 30))
    }
    RECESSO = (datetime.date(2026, 7, 10), datetime.date(2026, 7, 24))

    # ==========================================
    # 1. DIVISÃO DA TELA IMEDIATAMENTE (70% Esq / 30% Dir)
    # ==========================================
    col_esq, col_dir = st.columns([7, 3], gap="large")

    # ==========================================
    # 2. BUSCA DE DADOS (Baseado na data escolhida)
    # ==========================================
    with col_esq:
        data_hoje = st.date_input("Data de Análise:", value=datetime.date.today(), format="DD/MM/YYYY")
    
    hoje_iso = data_hoje.isoformat()
    df_presentes_hoje = pd.DataFrame()
    n_presentes, total_alunos, n_faltas, perc = 0, 0, 0, 0

    try:
        res_total = supabase.table("alunos").select("id", count="exact").execute()
        total_alunos = res_total.count if res_total.count else 0
        
        res_freq = supabase.table("frequencia").select("*").eq("data_chamada", hoje_iso).execute()
        
        if res_freq.data:
            df_presentes_hoje = pd.DataFrame(res_freq.data)
            col_nome = next((c for c in ['aluno_nome', 'nome_aluno'] if c in df_presentes_hoje.columns), None)
            if col_nome:
                n_presentes = len(df_presentes_hoje[col_nome].unique())
            else:
                n_presentes = len(df_presentes_hoje)
                
        n_faltas = total_alunos - n_presentes
        perc = (n_presentes / total_alunos * 100) if total_alunos > 0 else 0
    except Exception as e:
        st.error(f"⚠️ Erro na conexão: {e}")

    # ==========================================
    # 3. PREENCHENDO O LADO ESQUERDO
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

        # --- TERMÔMETRO ---
        st.subheader("🌡️ Termômetro de Evolução")
        periodo_sel = st.pills("Selecione o Trimestre:", options=list(TRIMESTRES.keys()), default="1º Tri")
        inicio_tri, fim_tri = TRIMESTRES[periodo_sel]

        st.write("### 🔍 Raio-X por Aluno")
        try:
            res_t = supabase.table("alunos").select("turma").execute().data
            lista_turmas = sorted(list(set([t['turma'] for t in res_t if t.get('turma')])))
            turma_escolhida = st.segmented_control("Selecione a Turma:", options=lista_turmas)
            
            if turma_escolhida:
                res_a = supabase.table("alunos").select("nome").eq("turma", turma_escolhida).order("nome").execute().data
                lista_alunos = [a['nome'] for a in res_a]
                aluno_escolhido = st.selectbox(f"👤 Alunos do {turma_escolhida}:", ["-- Selecione --"] + lista_alunos)
                
                if aluno_escolhido != "-- Selecione --":
                    presencas_tri = supabase.table("frequencia").select("data_chamada")\
                        .eq("aluno_nome", aluno_escolhido)\
                        .gte("data_chamada", str(inicio_tri))\
                        .lte("data_chamada", str(fim_tri)).execute().data

                    if presencas_tri:
                        df_tri = pd.DataFrame(presencas_tri)
                        df_tri['data_chamada'] = pd.to_datetime(df_tri['data_chamada'])
                        df_tri['mes'] = df_tri['data_chamada'].dt.strftime('%m - %b')
                        contagem = df_tri.groupby('mes').size().reset_index(name='dias_presenca')

                        st.markdown(f"**Análise: {aluno_escolhido}**")
                        for _, row in contagem.iterrows():
                            dias = row['dias_presenca']
                            if dias >= 18: cor, lbl = "#00ced1", "Frio (Excelente)"
                            elif dias >= 15: cor, lbl = "#ffa500", "Morno (Atenção)"
                            else: cor, lbl = "#ff4b4b", "QUENTE (Risco)"

                            st.markdown(f"""
                                <div style="margin-bottom:10px">
                                    <small>{row['mes']}</small>
                                    <div style="width: 100%; background-color: #f0f2f6; border-radius: 8px;">
                                        <div style="width: {min(dias*5, 100)}%; background-color: {cor}; 
                                                padding: 5px; color: white; text-align: right; border-radius: 8px; font-size: 11px;">
                                            {dias} dias - {lbl}
                                        </div>
                                    </div>
                                </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.warning("🚨 Nenhuma presença neste período.")
            else:
                st.info("👆 Toque em uma turma para carregar os alunos.")
        except Exception as e:
            st.error(f"Erro ao carregar dados: {e}")

        st.divider()

        # --- GRÁFICO ---
        try:
            if not df_presentes_hoje.empty and 'turma' in df_presentes_hoje.columns:
                st.subheader("🏫 Presença por Turma (Hoje)")
                df_turmas = df_presentes_hoje.groupby('turma').size().reset_index(name='Presentes')
                st.bar_chart(df_turmas.set_index('turma'))
        except:
            pass

    # ==========================================
    # 4. PREENCHENDO O LADO DIREITO (TABELA)
    # ==========================================
    with col_dir:
        st.subheader("📋 Presentes por Sala")
        
        if not df_presentes_hoje.empty and 'turma' in df_presentes_hoje.columns:
            df_resumo = df_presentes_hoje.groupby('turma').size().reset_index(name='Qtd')
            df_resumo = df_resumo.sort_values(by='turma')
            
            # Altura ajustada para acompanhar o layout lateral
            st.dataframe(
                df_resumo,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "turma": st.column_config.TextColumn("Turma"),
                    "Qtd": st.column_config.NumberColumn("Qtd")
                },
                height=600 
            )
        else:
            st.info("Nenhuma presença registrada hoje.")
