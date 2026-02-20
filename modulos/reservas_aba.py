import streamlit as st
from streamlit_calendar import calendar
import pandas as pd
from datetime import date
import time

def exibir_reservas(supabase, LISTA_PROFESSORES, AULAS_OPCOES, ESPACOS_TOTAIS, TOTAL_DATASHOWS, TOTAL_CAIXAS, TOTAL_MICROFONES):
    st.title("📅 Sistema de Reservas")
    
    tab_calendario, tab_lista, tab_nova_reserva = st.tabs([
        "🗓️ Calendário Mensal", 
        "📋 Lista Diária", 
        "📝 Nova Reserva"
    ])

    # --- ABA 1: CALENDÁRIO INTERATIVO ---
    with tab_calendario:
        try:
            # Busca todas as reservas para alimentar o calendário
            res_all = supabase.table("reservas").select("data_reserva, professor, espaco, periodo").execute()
            
            eventos = []
            for r in res_all.data:
                eventos.append({
                    "title": f"{r['periodo']} - {r['professor']}",
                    "start": r['data_reserva'],
                    "end": r['data_reserva'],
                    "description": r['espaco'],
                    "color": "#ff4b4b" if "Auditório" in r['espaco'] else "#3d66af"
                })

            calendar_options = {
                "headerToolbar": {"left": "prev,next", "center": "title", "right": "dayGridMonth"},
                "initialView": "dayGridMonth",
                "locale": "pt-br",
            }
            
            calendar(events=eventos, options=calendar_options, key="cal_interativo")
            st.caption("Toque nos dias para ver os detalhes (em visualização desktop ou tablet).")
        except Exception as e:
            st.error(f"Erro ao carregar calendário: {e}")

    # --- ABA 2: LISTA DIÁRIA ---
    with tab_lista:
        data_c = st.date_input("Ver detalhes do dia:", value=date.today(), key="data_detalhe")
        res_dia = supabase.table("reservas").select("*").eq("data_reserva", str(data_c)).execute()
        
        if res_dia.data:
            df = pd.DataFrame(res_dia.data)[['periodo', 'professor', 'espaco', 'equipamentos', 'observacoes']]
            df.columns = ['Aula', 'Professor', 'Espaço', 'Equipamentos', 'Obs']
            st.dataframe(df.sort_values(by='Aula'), use_container_width=True, hide_index=True)
        else:
            st.info("Nenhuma reserva para este dia.")

    # --- ABA 3: NOVA RESERVA ---
    with tab_nova_reserva:
        col_d, col_a = st.columns([1, 2])
        with col_d:
            data_r = st.date_input("Data da Reserva:", value=date.today(), key="data_nova")
        with col_a:
            tudo = st.checkbox("Dia Inteiro")
            aulas = st.pills("Aulas:", options=AULAS_OPCOES, selection_mode="multi", default=AULAS_OPCOES if tudo else [])

        if aulas:
            # Verificação de conflitos em tempo real
            res_conf = supabase.table("reservas").select("*").eq("data_reserva", str(data_r)).in_("periodo", aulas).execute().data
            ocupados = [r['espaco'] for r in res_conf if r['espaco'] != "Nenhum (Só Equipamento)"]
            disponiveis = [e for e in ESPACOS_TOTAIS if e not in ocupados]

            with st.form("f_reserva"):
                p = st.selectbox("Professor:", ["-- Selecione --"] + sorted(LISTA_PROFESSORES))
                e = st.selectbox("Espaço:", disponiveis if disponiveis else ["LOTADO"])
                equip = st.multiselect("Equipamentos:", ["Datashow", "Caixa de Som", "Microfone"])
                obs = st.text_area("Observações:")
                
                if st.form_submit_button("Confirmar Agendamento", use_container_width=True):
                    if p != "-- Selecione --":
                        for a in aulas:
                            supabase.table("reservas").insert({
                                "data_reserva": str(data_r), "periodo": a, "professor": p,
                                "espaco": e, "equipamentos": ", ".join(equip), "observacoes": obs
                            }).execute()
                        st.success("Reserva realizada!")
                        time.sleep(1)
                        st.rerun()
        else:
            st.warning("Selecione as aulas para habilitar o formulário.")
