import streamlit as st
import time
from datetime import date

def exibir_reservas(supabase, LISTA_PROFESSORES, AULAS_OPCOES, ESPACOS_TOTAIS, TOTAL_DATASHOWS, TOTAL_CAIXAS, TOTAL_MICROFONES):
    st.title("📅 Sistema de Reservas")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        data_sel = st.date_input("Data da Reserva:", value=date.today(), format="DD/MM/YYYY")
    with col2:
        selecionar_tudo = st.checkbox("Selecionar Dia Inteiro")
        aulas_selecionadas = st.pills("Aulas:", options=AULAS_OPCOES, selection_mode="multi", 
                                     default=AULAS_OPCOES if selecionar_tudo else [])

    if aulas_selecionadas:
        try:
            res_r = supabase.table("reservas").select("*").eq("data_reserva", str(data_sel)).in_("periodo", aulas_selecionadas).execute()
            reservas_dia = res_r.data
        except: reservas_dia = []

        # Lógica de Ocupação e Inventário
        espacos_ocupados = [r['espaco'] for r in reservas_dia if r.get('espaco') and r['espaco'] != "Nenhum (Só Equipamento)"]
        espacos_disponiveis = [e for e in ESPACOS_TOTAIS if e not in espacos_ocupados]
        
        d_usados = sum(1 for r in reservas_dia if r.get('equipamentos') and "Datashow" in r['equipamentos'])
        c_usadas = sum(1 for r in reservas_dia if r.get('equipamentos') and "Caixa de Som" in r['equipamentos'])
        m_usados = sum(1 for r in reservas_dia if r.get('equipamentos') and "Microfone" in r['equipamentos'])
        
        opcoes_equip = []
        if (TOTAL_DATASHOWS - d_usados) > 0: opcoes_equip.append(f"Datashow ({TOTAL_DATASHOWS - d_usados} disponíveis)")
        if (TOTAL_CAIXAS - c_usadas) > 0: opcoes_equip.append(f"Caixa de Som ({TOTAL_CAIXAS - c_usadas} disponíveis)")
        if (TOTAL_MICROFONES - m_usados) > 0: opcoes_equip.append(f"Microfone ({TOTAL_MICROFONES - m_usados} disponíveis)")

        with st.form("form_reserva"):
            prof_sel = st.selectbox("👩‍🏫 Professor(a):", ["-- Selecione --"] + sorted(LISTA_PROFESSORES))
            esp_final = st.selectbox("📍 Espaço:", espacos_disponiveis if espacos_disponiveis else ["⚠️ Todos ocupados"])
            equip_sel = st.multiselect("💻 Equipamentos:", opcoes_equip if opcoes_equip else ["Nenhum disponível"])
            obs = st.text_area("📝 Observações:")
            
            if st.form_submit_button("Confirmar Reserva", use_container_width=True):
                if prof_sel != "-- Selecione --":
                    e_limpos = [e.split(" (")[0] for e in equip_sel if "disponíve" in e]
                    for aula in aulas_selecionadas:
                        supabase.table("reservas").insert({
                            "data_reserva": str(data_sel), "periodo": aula, "professor": prof_sel,
                            "espaco": esp_final, "equipamentos": ", ".join(e_limpos) if e_limpos else "Nenhum", "observacoes": obs
                        }).execute()
                    st.success("Reserva concluída!")
                    st.balloons()
                    time.sleep(1)
                    st.rerun()
