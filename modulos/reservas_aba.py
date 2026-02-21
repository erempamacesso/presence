import streamlit as st
import pandas as pd
import datetime
from streamlit_calendar import calendar # <-- COMPONENTE DO CALENDÁRIO VISUAL

# --- GESTORES COM PRIVILÉGIO TOTAL ---
# Apenas os nomes. As matrículas (senhas) virão do banco de dados!
GESTORES = ["Lilian Jordão", "Jackson Carvalho", "Lylian Cabral"]

def exibir_reservas(supabase, lista_professores_antiga, aulas_opcoes, espacos, arg1=None, arg2=None, arg3=None):
    st.title("📅 Sistema de Reservas")
    
    # -----------------------------------------
    # 1. BUSCAR TODOS OS NOMES DO BANCO DE DADOS
    # -----------------------------------------
    lista_pessoas = []
    try:
        res_prof = supabase.table("professores_matriculas").select("professor").order("professor").execute()
        if res_prof.data:
            # Pega os nomes, tira duplicatas e organiza em ordem alfabética
            lista_pessoas = sorted(list(set([p['professor'] for p in res_prof.data])))
    except Exception as e:
        st.error(f"Erro ao buscar lista no banco: {e}")
        lista_pessoas = lista_professores_antiga # Fallback caso dê erro na internet

    # -----------------------------------------
    # 2. CRIANDO AS ABAS
    # -----------------------------------------
    aba_cal, aba_lista, aba_nova, aba_cancelar, aba_assinatura = st.tabs([
        "🗓️ Calendário Mensal", 
        "📋 Lista Diária", 
        "✍️ Nova Reserva", 
        "❌ Gerenciar/Cancelar",
        "🔑 Cadastrar Assinatura"
    ])

    # -----------------------------------------
    # ABA 1: CALENDÁRIO MENSAL (Visual e Dinâmico)
    # -----------------------------------------
    with aba_cal:
        st.subheader("Visão Geral do Mês")
        st.info("💡 Legenda: [Aula] - [Professor]")
        
        try:
            # Busca apenas reservas ativas
            res_cal = supabase.table("reservas").select("*").eq("status", "Ativa").execute()
            
            if res_cal.data:
                eventos = []
                for r in res_cal.data:
                    # Formato limpo: Apenas a Aula e o Nome do Professor
                    titulo_limpo = f"{r['aula']} - {r['professor']}"
                    
                    eventos.append({
                        "title": titulo_limpo,
                        "start": r['data_reserva'],
                        "end": r['data_reserva'],
                        "backgroundColor": "#1f77b4" # Cor do bloco
                    })
                
                # Configurações do Calendário Visual
                calendar_options = {
                    "headerToolbar": {
                        "left": "today prev,next",
                        "center": "title",
                        "right": "dayGridMonth,timeGridWeek"
                    },
                    "initialView": "dayGridMonth",
                }
                
                # Renderiza o calendário na tela
                calendar(events=eventos, options=calendar_options)
            else:
                st.info("Nenhuma reserva encontrada para exibir no calendário.")
                
        except Exception as e:
            st.error(f"Erro ao carregar calendário: {e}")
