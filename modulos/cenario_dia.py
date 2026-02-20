import streamlit as st
import pandas as pd
import datetime

def exibir_cenario(supabase):
    st.title("Cenário do Dia")
    
    # --- CONFIGURAÇÃO DE DATAS ---
    TRIMESTRES = {
        "1º Tri": (datetime.date(2026, 2, 2), datetime.date(2026, 5, 20)),
        "2º Tri": (datetime.date(2026, 5, 21), datetime.date(2026, 9, 11)),
        "3º Tri": (datetime.date(2026, 9, 12), datetime.date(2026, 12, 30))
    }

    # 1. Calendário sem teclado (Date Input é de toque)
    data_hoje = st.date_input("Data de Análise:", value=datetime.date.today(), format="DD/MM/YYYY")
    
    # ... (Métricas permanecem as mesmas aqui) ...
    st.divider()

    # --- 2. O TERMÔMETRO (LAYOUT MOBILE-FRIENDLY) ---
    st.subheader("🌡️ Termômetro de Evolução")
    
    # Seleção de Trimestre por Botões (Não abre teclado)
    periodo_sel = st.pills("Período:", options=list(TRIMESTRES.keys()), default="1º Tri")
    inicio_tri, fim_tri = TRIMESTRES[periodo_sel]

    # --- FILTRO DE TURMAS SEM TECLADO ---
    try:
        res_t = supabase.table("alunos").select("turma").execute().data
        lista_turmas = sorted(list(set([t['turma'] for t in res_t if t.get('turma')])))
        
        st.write("📁 **Selecione a Turma:**")
        # Usando segmented_control ou pills para as turmas (Botões clicáveis)
        turma_escolhida = st.segmented_control(
            "Turmas disponíveis:", 
            options=lista_turmas, 
            label_visibility="collapsed"
        )
        
        if turma_escolhida:
            # Busca os alunos SÓ daquela turma
            res_a = supabase.table("alunos").select("nome").eq("turma", turma_escolhida).order("nome").execute().data
            lista_alunos = [a['nome'] for a in res_a]
            
            # Aqui para o aluno, como a lista é grande, usamos o Selectbox 
            # Mas ele só aparece APÓS escolher a turma, diminuindo o esforço.
            aluno_escolhido = st.selectbox(f"👤 Alunos da {turma_escolhida}:", ["-- Selecione o Aluno --"] + lista_alunos)
            
            if aluno_escolhido != "-- Selecione o Aluno --":
                # ... (Lógica do gráfico térmico permanece igual) ...
                st.info(f"Gerando análise para {aluno_escolhido}...")
        else:
            st.info("Toque em uma turma acima para ver os alunos.")

    except Exception as e:
        st.error(f"Erro ao carregar filtros: {e}")
