import streamlit as st
import time
import pandas as pd
from datetime import date

def exibir_reservas(supabase, LISTA_PROFESSORES, AULAS_OPCOES, ESPACOS_TOTAIS, TOTAL_DATASHOWS, TOTAL_CAIXAS, TOTAL_MICROFONES):
    st.title("📅 Sistema de Reservas")
    
    # Criando as abas conforme solicitado
    tab_visualizar, tab_nova_reserva = st.tabs(["📋 Agendamentos Previstos", "📝 Fazer Nova Reserva"])

    # --- ABA DA ESQUERDA: VISUALIZAR ---
    with tab_visualizar:
        data_consulta = st.date_input("Consultar data:", value=date.today(), format="DD/MM/YYYY", key="data_cons")
        
        try:
            res = supabase.table("reservas").select("*").eq("data_reserva", str(data_consulta)).execute()
            reservas_dia = res.data
            
            if reservas_dia:
                df_res = pd.DataFrame(reservas_dia)
                df_view = df_res[['periodo', 'professor', 'espaco', 'equipamentos', 'observacoes']].copy()
                df_view.columns = ['Aula', 'Professor', 'Espaço', 'Equipamentos', 'Observação']
                st.dataframe(df_view.sort_values(by='Aula'), use_container_width=True, hide_index=True)
            else:
                st.info(f"Nenhum agendamento para o dia {data_consulta.strftime('%d/%m/%Y')}.")
        except Exception as e:
            st.error(f"Erro ao carregar reservas: {e}")

    # --- ABA DA DIREITA: NOVA RESERVA ---
    with tab_nova_reserva:
        col_data, col_aulas = st.columns([1, 2])
        
        with col_data:
            data_res = st.date_input("Data da Reserva:", value=date.today(), format="DD/MM/YYYY", key="data_res")
        
        with col_aulas:
            selecionar_tudo = st.checkbox("Dia Inteiro", key="check_total")
            default_aulas = AULAS_OPCOES if selecionar_tudo else []
            aulas_sel = st.pills("Selecione as Aulas:", options=AULAS_OPCOES, selection_mode="multi", default=default_aulas)

        if not aulas_sel:
            st.warning("⚠️ Selecione pelo menos uma aula para continuar.")
        else:
            # Lógica de Conflitos para as aulas selecionadas
            try:
                res_conflito = supabase.table("reservas").select("*").eq("data_reserva", str(data_res)).in_("periodo", aulas_sel).execute().data
                
                espacos_ocupados = [r['espaco'] for r in res_conflito if r.get('espaco') and r['espaco'] != "Nenhum (Só Equipamento)"]
                espacos_disponiveis = [e for e in ESPACOS_TOTAIS if e not in espacos_ocupados]
                
                # Estoque de equipamentos
                d_usados = sum(1 for r in res_conflito if r.get('equipamentos') and "Datashow" in r['equipamentos'])
                c_usadas = sum(1 for r in res_conflito if r.get('equipamentos') and "Caixa de Som" in r['equipamentos'])
                m_usados = sum(1 for r in res_conflito if r.get('equipamentos') and "Microfone" in r['equipamentos'])
                
                opcoes_equip = []
                if (TOTAL_DATASHOWS - d_usados) > 0: opcoes_equip.append(f"Datashow ({TOTAL_DATASHOWS - d_usados} disp.)")
                if (TOTAL_CAIXAS - c_usadas) > 0: opcoes_equip.append(f"Caixa de Som ({TOTAL_CAIXAS - c_usadas} disp.)")
                if (TOTAL_MICROFONES - m_usados) > 0: opcoes_equip.append(f"Microfone ({TOTAL_MICROFONES - m_usados} disp.)")

                with st.form("form_final"):
                    prof = st.selectbox("👩‍🏫 Professor(a):", ["-- Selecione --"] + sorted(LISTA_PROFESSORES))
                    esp = st.selectbox("📍 Espaço:", espacos_disponiveis if espacos_disponiveis else ["⚠️ Tudo Lotado"])
                    equip = st.multiselect("💻 Equipamentos:", opcoes_equip)
                    obs = st.text_area("📝 Observações:")
                    
                    if st.form_submit_button("Confirmar Agendamento", use_container_width=True):
                        if prof != "-- Selecione --":
                            e_nomes = [e.split(" (")[0] for e in equip]
                            for aula in aulas_sel:
                                supabase.table("reservas").insert({
                                    "data_reserva": str(data_res), "periodo": aula, "professor": prof,
                                    "espaco": esp, "equipamentos": ", ".join(e_nomes) if e_nomes else "Nenhum", "observacoes": obs
                                }).execute()
                            st.success("✅ Reserva gravada!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("Selecione seu nome!")
            except Exception as e:
                st.error(f"Erro na verificação: {e}")
