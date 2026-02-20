import streamlit as st
import pandas as pd
import datetime

def exibir_cenario(supabase):
    st.title("📊 Cenário do Dia")
    
    # --- CALENDÁRIO PE 2026 ---
    TRIMESTRES = {
        "1º Trimestre": (datetime.date(2026, 2, 2), datetime.date(2026, 5, 20)),
        "2º Trimestre": (datetime.date(2026, 5, 21), datetime.date(2026, 9, 11)),
        "3º Trimestre": (datetime.date(2026, 9, 12), datetime.date(2026, 12, 30))
    }
    RECESSO = (datetime.date(2026, 7, 10), datetime.date(2026, 7, 24))

    # --- 1. CENSO EM TEMPO REAL ---
    # Correção: Forçando o formato brasileiro DD/MM/YYYY no calendário
    data_hoje = st.date_input("Data de Análise:", value=datetime.date.today(), format="DD/MM/YYYY")
    hoje_iso = data_hoje.isoformat()

    try:
        res_total = supabase.table("alunos").select("id", count="exact").execute()
        total_alunos = res_total.count if res_total.count else 0
        
        res_freq = supabase.table("frequencia").select("*").eq("data_chamada", hoje_iso).execute()
        df_presentes_hoje = pd.DataFrame(res_freq.data)
        
        # Trocamos 'aluno_id' por 'aluno_nome' que sabemos que existe no seu banco
n_presentes = len(df_presentes_hoje.drop_duplicates(subset=['aluno_nome'])) if not df_presentes_hoje.empty else 0
        n_faltas = total_alunos - n_presentes
        perc = (n_presentes / total_alunos * 100) if total_alunos > 0 else 0

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Presentes Agora", n_presentes)
        c2.metric("Ausentes", n_faltas, delta=f"{n_faltas} faltas", delta_color="inverse")
        c3.metric("% Presença", f"{perc:.1f}%")
        c4.metric("Matrícula Total", total_alunos)

        if RECESSO[0] <= data_hoje <= RECESSO[1]:
            st.info("ℹ️ Período de Recesso Escolar")

    except Exception as e:
        st.error(f"Erro na integração dos dados: {e}")

    st.divider()

    # --- 2. TERMÔMETRO DE ASSIDUIDADE (FILTRO INTELIGENTE) ---
    st.subheader("🌡️ Termômetro de Evolução (Faltas)")
    
    # Correção: Usando radio horizontal para evitar erros de versão do Streamlit
    periodo_sel = st.radio("Selecione o Trimestre:", options=list(TRIMESTRES.keys()), horizontal=True)
    inicio_tri, fim_tri = TRIMESTRES[periodo_sel]

    st.write("### 🔍 Raio-X do Aluno")
    
    # Correção: Filtro Turma -> Aluno (Cascata)
    col_turma, col_aluno = st.columns(2)
    
    with col_turma:
        # Busca apenas as turmas disponíveis
        res_turmas = supabase.table("alunos").select("turma").execute().data
        lista_turmas = sorted(list(set([t['turma'] for t in res_turmas if t.get('turma')])))
        turma_escolhida = st.selectbox("1. Selecione a Turma:", ["-- Selecione --"] + lista_turmas)

    with col_aluno:
        aluno_escolhido = "-- Selecione --"
        if turma_escolhida != "-- Selecione --":
            # Busca os alunos SÓ daquela turma
            res_alunos = supabase.table("alunos").select("nome").eq("turma", turma_escolhida).order("nome").execute().data
            lista_alunos = [a['nome'] for a in res_alunos]
            aluno_escolhido = st.selectbox("2. Selecione o Aluno:", ["-- Selecione --"] + lista_alunos)
        else:
            st.selectbox("2. Selecione o Aluno:", ["Escolha uma turma primeiro..."], disabled=True)

    # Se um aluno foi selecionado, exibe o termômetro
    if aluno_escolhido != "-- Selecione --" and aluno_escolhido != "Escolha uma turma primeiro...":
        nome_aluno = aluno_escolhido
        
        presencas_tri = supabase.table("frequencia").select("data_chamada")\
            .eq("aluno_nome", nome_aluno)\
            .gte("data_chamada", str(inicio_tri))\
            .lte("data_chamada", str(fim_tri)).execute().data

        if presencas_tri:
            df_tri = pd.DataFrame(presencas_tri)
            df_tri['data_chamada'] = pd.to_datetime(df_tri['data_chamada'])
            df_tri['mes'] = df_tri['data_chamada'].dt.strftime('%m - %b')
            contagem = df_tri.groupby('mes').size().reset_index(name='dias_presenca')

            st.markdown(f"**Frequência Mensal: {nome_aluno} no {periodo_sel}**")
            
            for _, row in contagem.iterrows():
                dias = row['dias_presenca']
                if dias >= 18: cor, label = "#00ced1", "Frio (Excelente)"
                elif dias >= 15: cor, label = "#ffa500", "Morno (Atenção)"
                else: cor, label = "#ff4b4b", "QUENTE (Risco Crítico)"

                st.markdown(f"""
                    <div style="margin-bottom:10px">
                        <small>{row['mes']}</small>
                        <div style="width: 100%; background-color: #f0f2f6; border-radius: 8px;">
                            <div style="width: {min(dias*5, 100)}%; background-color: {cor}; 
                                        padding: 5px; color: white; text-align: right; border-radius: 8px; font-size: 11px;">
                                {dias} presenças - {label}
                            </div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.warning("🚨 Nenhuma presença registrada para este aluno no período.")

    st.divider()

    # --- 3. CENÁRIO POR TURMA ---
    if 'df_presentes_hoje' in locals() and not df_presentes_hoje.empty:
        st.subheader("🏫 Presença por Turma (Hoje)")
        df_turmas = df_presentes_hoje.groupby('turma').size().reset_index(name='Presentes')
        st.bar_chart(df_turmas.set_index('turma'))
