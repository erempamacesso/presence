import streamlit as st
import time
import pandas as pd
from datetime import date

def exibir_reservas(supabase, LISTA_PROFESSORES, AULAS_OPCOES, ESPACOS_TOTAIS, TOTAL_DATASHOWS, TOTAL_CAIXAS, TOTAL_MICROFONES):
    st.title("📅 Sistema de Reservas")
    
    # --- ETAPA 1: DATA E AULAS ---
    col1, col2 = st.columns([1, 2])
    with col1:
        data_sel = st.date_input("Data da Consulta/Reserva:", value=date.today(), format="DD/MM/YYYY")
    
    with col2:
        st.write("Selecione as Aulas:")
        col_pills, col_all = st.columns([3, 1])
        with col_all:
            selecionar_tudo = st.checkbox("Dia Inteiro")
        
        with col_pills:
            default_aulas = AULAS_OPCOES if selecionar_tudo else []
            aulas_selecionadas = st.pills(
                "Aulas:", 
                options=AULAS_OPCOES, 
                selection_mode="multi",
                default=default_aulas,
                label_visibility="collapsed"
            )

    # --- BUSCA RESERVAS EXISTENTES ---
    reservas_dia = []
    try:
        # Busca todas as reservas da data selecionada para exibir na tabela abaixo
        res = supabase.table("reservas").select("*").eq("data_reserva", str(data_sel)).execute()
        reservas_dia = res.data
    except:
        pass

    # --- ABA DE VISUALIZAÇÃO (NOVIDADE) ---
    st.divider()
    st.subheader(f"📋 Reservas para o dia {data_sel.strftime('%d/%m/%Y')}")
    
    if reservas_dia:
        df_res = pd.DataFrame(reservas_dia)
        # Organiza as colunas para ficar legível
        df_view = df_res[['periodo', 'professor', 'espaco', 'equipamentos', 'observacoes']].copy()
        df_view.columns = ['Aula', 'Professor', 'Espaço', 'Equipamentos', 'Obs']
        # Ordena pelas aulas
        st.dataframe(df_view.sort_values(by='Aula'), use_container_width=True, hide_index=True)
    else:
        st.info("Não há reservas para este dia ainda.")

    st.divider()

    # --- ETAPA 2: FORMULÁRIO DE NOVA RESERVA ---
    if aulas_selecionadas:
        st.subheader("📝 Fazer Nova Reserva")
        
        # Filtra ocupação apenas para as aulas que o usuário selecionou agora
        reservas_conflito = [r for r in reservas_dia if r['periodo'] in aulas_selecionadas]
        
        espacos_ocupados = [r['espaco'] for r in reservas_conflito if r.get('espaco') and r['espaco'] != "Nenhum (Só Equipamento)"]
        espacos_disponiveis = [e for e in ESPACOS_TOTAIS if e not in espacos_ocupados]

        d_usados = sum(1 for r in reservas_conflito if r.get('equipamentos') and "Datashow" in r['equipamentos'])
        c_usadas = sum(1 for r in reservas_conflito if r.get('equipamentos') and "Caixa de Som" in r['equipamentos'])
        m_usados = sum(1 for r in reservas_conflito if r.get('equipamentos') and "Microfone" in r['equipamentos'])
        
        opcoes_equip = []
        if (TOTAL_DATASHOWS - d_usados) > 0: 
            opcoes_equip.append(f"Datashow ({TOTAL_DATASHOWS - d_usados} disponíveis)")
        if (TOTAL_CAIXAS - c_usadas) > 0: 
            opcoes_equip.append(f"Caixa de Som ({TOTAL_CAIXAS - c_usadas} disponíveis)")
        if (TOTAL_MICROFONES - m_usados) > 0: 
            opcoes_equip.append(f"Microfone ({TOTAL_MICROFONES - m_usados} disponíveis)")

        with st.form("form_reserva"):
            prof_sel = st.selectbox("👩‍🏫 Professor(a):", ["-- Selecione --"] + sorted(LISTA_PROFESSORES))
            esp_final = st.selectbox("📍 Espaço:", espacos_disponiveis if espacos_disponiveis else ["⚠️ Todos ocupados"])
            equip_sel = st.multiselect("💻 Equipamentos:", opcoes_equip)
            obs = st.text_area("📝 Observações:")
            
            if st.form_submit_button("Confirmar Reserva", use_container_width=True):
                if prof_sel != "-- Selecione --":
                    e_limpos = [e.split(" (")[0] for e in equip_sel]
                    for aula in aulas_selecionadas:
                        supabase.table("reservas").insert({
                            "data_reserva": str(data_sel), "periodo": aula, "professor": prof_sel,
                            "espaco": esp_final, "equipamentos": ", ".join(e_limpos) if e_limpos else "Nenhum", "observacoes": obs
                        }).execute()
                    st.success("Reserva concluída!")
                    time.sleep(1)
                    st.rerun()
    else:
        st.warning("Selecione as aulas acima para abrir o formulário de reserva.")
