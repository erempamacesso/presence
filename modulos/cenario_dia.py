import streamlit as st
import pandas as pd
import datetime

def exibir_cenario(supabase):
    st.title("📊 Cenário do Dia")
    
    # --- CALENDÁRIO PE 2026 (DATA FIXA PARA ANÁLISE) ---
    TRIMESTRES = {
        "1º Trimestre": (datetime.date(2026, 2, 2), datetime.date(2026, 5, 20)),
        "2º Trimestre": (datetime.date(2026, 5, 21), datetime.date(2026, 9, 11)),
        "3º Trimestre": (datetime.date(2026, 9, 12), datetime.date(2026, 12, 30))
    }
    RECESSO = (datetime.date(2026, 7, 10), datetime.date(2026, 7, 24))

    # --- 1. CENSO EM TEMPO REAL ---
    data_hoje = st.date_input("Data de Análise:", value=datetime.date.today())
    hoje_iso = data_hoje.isoformat()

    try:
        # Busca matriculados
        res_total = supabase.table("alunos").select("id", count="exact").execute()
        total_alunos = res_total.count if res_total.count else 0
        
        # Busca quem ESTÁ presente (com base no seu app externo)
        res_freq = supabase.table("frequencia").select("*").eq("data_chamada", hoje_iso).execute()
        df_presentes_hoje = pd.DataFrame(res_freq.data)
        
        n_presentes = len(df_presentes_hoje.drop_duplicates(subset=['aluno_id'])) if not df_presentes_hoje.empty else 0
        n_faltas = total_alunos - n_presentes
        perc = (n_presentes / total_alunos * 100) if total_alunos > 0 else 0

        # Layout de métricas
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Presentes Agora", n_presentes)
        c2.metric("Ausentes", n_faltas, delta=f"{n_faltas} faltas", delta_color="inverse")
        c3.metric("% Presença", f"{perc:.1f}%")
        c4.metric("Matrícula Total", total_alunos)

        if RECESSO[0] <= data_hoje <= RECESSO[1]:
            st.info("ℹ️ Período de Recesso Escolar")

    except Exception as e:
        st.error(f"Erro na integração: {e}")

    st.divider()

    # --- 2. TERMÔMETRO DE ASSIDUIDADE (ANÁLISE DE FALTAS) ---
    st.subheader("🌡️ Termômetro de Evolução (Faltas)")
    
    periodo_sel = st.segmented_control("Trimestre:", options=list(TRIMESTRES.keys()), default="1º Trimestre")
    inicio_tri, fim_tri = TRIMESTRES[periodo_sel]

    # Busca lista de alunos para seleção
    res_alunos = supabase.table("alunos").select("nome, turma").order("nome").execute().data
    lista_selecao = [f"{a['nome']} ({a['turma']})" for a in res_alunos]
    
    aluno_escolhido = st.selectbox("Selecione o Aluno para Raio-X:", ["-- Selecione --"] + lista_selecao)

    if aluno_escolhido != "-- Selecione --":
        nome_aluno = aluno_escolhido.split(" (")[0]
        
        # Lógica Inversa: Para saber faltas, precisamos saber quantos dias letivos houve 
        # e subtrair as presenças que o app externo registrou.
        # Mas para o "Termômetro", vamos focar em mostrar a CONSTÂNCIA de presença:
        
        presencas_tri = supabase.table("frequencia").select("data_chamada")\
            .eq("aluno_nome", nome_aluno)\
            .gte("data_chamada", str(inicio_tri))\
            .lte("data_chamada", str(fim_tri)).execute().data

        if presencas_tri:
            df_tri = pd.DataFrame(presencas_tri)
            df_tri['data_chamada'] = pd.to_datetime(df_tri['data_chamada'])
            df_tri['mes'] = df_tri['data_chamada'].dt.strftime('%m - %b')
            contagem = df_tri.groupby('mes').size().reset_index(name='dias_presenca')

            st.write(f"Frequência Mensal no {periodo_sel}")
            
            for _, row in contagem.iterrows():
                # Aqui invertemos: se tiver poucas presenças no mês, "esquenta"
                # (Considerando uma média de 20 dias letivos por mês)
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
            st.error("🚨 Nenhuma presença registrada para este aluno no período.")

    st.divider()

    # --- 3. CENÁRIO POR TURMA ---
    if not df_presentes_hoje.empty:
        st.subheader("🏫 Presença por Turma (Hoje)")
        df_turmas = df_presentes_hoje.groupby('turma').size().reset_index(name='Presentes')
        st.bar_chart(df_turmas.set_index('turma'))
