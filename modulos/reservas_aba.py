import streamlit as st
import time
from datetime import date

def exibir_reservas(supabase, LISTA_PROFESSORES, AULAS_OPCOES, ESPACOS_TOTAIS, TOTAL_DATASHOWS, TOTAL_CAIXAS, TOTAL_MICROFONES):
    st.title("📅 Sistema de Reservas")
    
    # ETAPA 1: DATA E AULAS
    col1, col2 = st.columns([1, 2])
    with col1:
        # Data em formato brasileiro
        data_sel = st.date_input("Data da Reserva:", value=date.today(), format="DD/MM/YYYY")
    
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

    # BUSCA RESERVAS EXISTENTES PARA EVITAR CONFLITOS
    reservas_dia = []
    if aulas_selecionadas:
        try:
            res = supabase.table("reservas").select("*").eq("data_reserva", str(data_sel)).in_("periodo", aulas_selecionadas).execute()
            reservas_dia = res.data
        except:
            pass

    # LÓGICA DE ESPAÇOS E EQUIPAMENTOS (ESTOQUE REAL)
    espacos_ocupados = [r['espaco'] for r in reservas_dia if r.get('espaco') and r['espaco'] != "Nenhum (Só Equipamento)"]
    espacos_disponiveis = [e for e in ESPACOS_TOTAIS if e not in espacos_ocupados]

    # Contagem de Equipamentos Usados
    d_usados = sum(1 for r in reservas_dia if r.get('equipamentos') and "Datashow" in r['equipamentos'])
    c_usadas = sum(1 for r in reservas_dia if r.get('equipamentos') and "Caixa de Som" in r['equipamentos'])
    m_usados = sum(1 for r in reservas_dia if r.get('equipamentos') and "Microfone" in r['equipamentos'])
    
    opcoes_equip = []
    if (TOTAL_DATASHOWS - d_usados) > 0: 
        opcoes_equip.append(f"Datashow ({TOTAL_DATASHOWS - d_usados} disponíveis)")
    if (TOTAL_CAIXAS - c_usadas) > 0: 
        opcoes_equip.append(f"Caixa de Som ({TOTAL_CAIXAS - c_usadas} disponíveis)")
    if (TOTAL_MICROFONES - m_usados) > 0: 
        opcoes_equip.append(f"Microfone ({TOTAL_MICROFONES - m_usados} disponíveis)")

    st.divider()

    # ETAPA 2: FORMULÁRIO DE RESERVA
    with st.form("form_reserva"):
        prof_sel = st.selectbox("👩‍🏫 Professor(a):", ["-- Selecione --"] + sorted(LISTA_PROFESSORES))
        
        # Seleção de Espaço
        if not espacos_disponiveis:
            st.error("⚠️ Todos os espaços ocupados nestas aulas!")
            esp_final = "Lotado"
        else:
            esp_final = st.selectbox("📍 Espaço:", espacos_disponiveis)
        
        # Seleção de Equipamentos
        if not opcoes_equip:
            st.warning("💻 Equipamentos: Nenhum disponível")
            equip_sel = []
        else:
            equip_sel = st.multiselect("💻 Equipamentos (Opcional):", opcoes_equip)
            
        obs = st.text_area("📝 Observações:")
        
        # Botão centralizado de confirmação
        if st.form_submit_button("Confirmar Reserva", use_container_width=True):
            if prof_sel != "-- Selecione --" and aulas_selecionadas:
                # Limpa o texto dos equipamentos para salvar apenas o nome (ex: "Datashow")
                e_limpos = [e.split(" (")[0] for e in equip_sel]
                
                try:
                    for aula in aulas_selecionadas:
                        dados = {
                            "data_reserva": str(data_sel),
                            "periodo": aula, # Nome da coluna no seu Supabase
                            "professor": prof_sel,
                            "espaco": esp_final,
                            "equipamentos": ", ".join(e_limpos) if e_limpos else "Nenhum",
                            "observacoes": obs
                        }
                        supabase.table("reservas").insert(dados).execute()
                    
                    st.success(f"🎉 Reserva realizada com sucesso!")
                    st.balloons()
                    time.sleep(2)
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar no banco de dados: {e}")
            else:
                st.warning("Por favor, selecione seu nome e as aulas desejadas.")
