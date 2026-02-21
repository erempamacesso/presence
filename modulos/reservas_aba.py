import streamlit as st
import pandas as pd
import datetime
from streamlit_calendar import calendar

# --- GESTORES COM PRIVILÉGIO TOTAL ---
GESTORES = ["Lilian Jordão", "Jackson Carvalho", "Lylian Cabral"]

def exibir_reservas(supabase, lista_professores_antiga, aulas_opcoes, espacos, arg1=None, arg2=None, arg3=None):
    st.title("📅 Sistema de Reservas")
    
    # ---------------------------------------------------------
    # PARTE 0: PREPARAÇÃO DE DADOS (Busca nomes no Banco)
    # ---------------------------------------------------------
    lista_pessoas = []
    try:
        res_prof = supabase.table("professores_matriculas").select("professor").execute()
        if res_prof.data:
            lista_pessoas = sorted(list(set([p['professor'] for p in res_prof.data])))
    except Exception as e:
        st.error(f"Erro ao buscar lista no banco: {e}")
        lista_pessoas = lista_professores_antiga

    opcoes_professores = ["-- Selecione --"] + lista_pessoas

    # Definição das Abas
    aba_cal, aba_lista, aba_nova, aba_cancelar, aba_assinatura = st.tabs([
        "🗓️ Calendário Mensal", "📋 Lista Diária", "✍️ Nova Reserva", "❌ Gerenciar", "🔑 Assinatura"
    ])

    # =========================================================
    # INÍCIO - ABA 1: CALENDÁRIO MENSAL (TEXTO COMPLETO)
    # =========================================================
    with aba_cal:
        # Estilo CSS para forçar a quebra de linha (Wrap) nas células
        estilo_custom = "<style>.fc-event-title { white-space: normal !important; word-wrap: break-word !important; } .fc-daygrid-event { white-space: normal !important; }</style>"
        st.markdown(estilo_custom, unsafe_allow_code=True)

        st.subheader("Visão Geral do Mês")
        
        try:
            # Busca apenas reservas ativas no banco
            res_cal = supabase.table("reservas").select("*").eq("status", "Ativa").execute()
            
            if res_cal.data:
                eventos_lista = []
                for r in res_cal.data:
                    # Captura os dados tratando possíveis valores nulos
                    prof_nome = r.get('professor', '---')
                    esp_nome = r.get('espaco', '---')
                    # Tenta buscar a coluna 'periodo' ou 'aula' conforme o seu banco
                    horario_info = r.get('periodo') or r.get('aula') or "S/H"
                    equip_info = r.get('equipamentos')

                    # Monta o título que vai aparecer no quadrado azul
                    txt_titulo = f"{horario_info} - {prof_nome} - {esp_nome}"
                    
                    # Se houver equipamento, adiciona ao título para o teste de "estouro"
                    if equip_info and str(equip_info).strip() not in ["", "None", "NULL"]:
                        txt_titulo += f" | 🛠️ {equip_info}"
                    
                    eventos_lista.append({
                        "title": txt_titulo,
                        "start": r['data_reserva'],
                        "end": r['data_reserva'],
                        "backgroundColor": "#1f77b4",
                        "borderColor": "#1f77b4"
                    })
                
                # Configurações do Calendário
                opcoes_visuais = {
                    "locale": "pt-br",
                    "headerToolbar": {
                        "left": "today prev,next",
                        "center": "title",
                        "right": "dayGridMonth,timeGridWeek"
                    },
                    "initialView": "dayGridMonth",
                    "eventDisplay": "block",
                    "buttonText": {"today": "Hoje", "month": "Mês", "week": "Semana"}
                }
                
                # Renderiza o componente
                calendar(events=eventos_lista, options=opcoes_visuais)
            else:
                st.info("Nenhuma reserva ativa encontrada para exibir no calendário.")
                
        except Exception as e:
            st.error(f"Erro ao carregar os eventos do calendário: {e}")
    # =========================================================
    # FIM - ABA 1
    # =========================================================

    # =========================================================
    # ABA 2: LISTA DIÁRIA (TESTE DE TODOS OS ESPAÇOS)
    # =========================================================
    with aba_lista:
        st.subheader("Visão Diária por Espaço")
        data_filtro = st.date_input("Ver detalhes do dia:", value=datetime.date.today(), key="data_lista_ok")
        
        try:
            res = supabase.table("reservas").select("*").eq("data_reserva", str(data_filtro)).execute()
            df_dia = pd.DataFrame(res.data) if res.data else pd.DataFrame()

            for espaco_escola in espacos:
                if not df_dia.empty and 'espaco' in df_dia.columns:
                    df_espaco = df_dia[df_dia['espaco'] == espaco_escola].copy()
                else:
                    df_espaco = pd.DataFrame()

                status_icone = "🔴" if not df_espaco.empty else "⚪"
                with st.expander(f"{status_icone} {espaco_escola} ({len(df_espaco)} reservas)", expanded=not df_espaco.empty):
                    if not df_espaco.empty:
                        # Colunas dinâmicas para evitar erro "not in index"
                        cols_banco = df_espaco.columns.tolist()
                        col_exibir = [c for c in ['periodo', 'professor', 'equipamentos', 'status'] if c in cols_banco]
                        
                        df_mostra = df_espaco[col_exibir].copy()
                        st.dataframe(df_mostra, use_container_width=True, hide_index=True)
                    else:
                        st.info(f"Espaço '{espaco_escola}' livre.")
        except Exception as e:
            st.error(f"Erro na lista: {e}")

    # =========================================================
    # ABA 3: NOVA RESERVA (CORRIGIDA PARA 'PERIODO')
    # =========================================================
    with aba_nova:
        st.subheader("Agendar Espaço")
        with st.form("form_nova_reserva"):
            c1, c2 = st.columns(2)
            with c1:
                d_res = st.date_input("Data:", value=datetime.date.today())
                a_res = st.selectbox("Aula/Período:", aulas_opcoes)
                p_res = st.selectbox("Professor:", opcoes_professores)
            with c2:
                e_res = st.selectbox("Espaço:", ["-- Selecione --"] + espacos)
                eq_res = st.text_input("Equipamentos:", placeholder="Ex: Data show")
                o_res = st.text_input("Observações:")
            
            if st.form_submit_button("💾 Confirmar Reserva"):
                if p_res == "-- Selecione --" or e_res == "-- Selecione --":
                    st.warning("Preencha Professor e Espaço.")
                else:
                    # Checagem usando 'periodo' que é sua coluna real
                    conf = supabase.table("reservas").select("id").eq("data_reserva", str(d_res)).eq("periodo", a_res).eq("espaco", e_res).eq("status", "Ativa").execute()
                    if conf.data:
                        st.error("🚨 Conflito! Este espaço já está reservado neste horário.")
                    else:
                        dados_insert = {
                            "data_reserva": str(d_res),
                            "periodo": a_res, # Usando periodo
                            "professor": p_res,
                            "espaco": e_res,
                            "equipamentos": eq_res,
                            "obs": o_res,
                            "status": "Ativa"
                        }
                        supabase.table("reservas").insert(dados_insert).execute()
                        st.success("✅ Reservado com sucesso!")
                        st.rerun()

    # =========================================================
    # ABA 4: GERENCIAR / CANCELAR (CORRIGIDA)
    # =========================================================
    with aba_cancelar:
        st.subheader("Cancelar uma Reserva")
        d_can = st.date_input("Data da reserva:", value=datetime.date.today(), key="d_can")
        try:
            res_at = supabase.table("reservas").select("*").eq("data_reserva", str(d_can)).eq("status", "Ativa").execute()
            if res_at.data:
                # Monta lista usando 'periodo' para o usuário identificar
                op_c = {f"{r.get('periodo','S/H')} - {r['espaco']} ({r['professor']})": r['id'] for r in res_at.data}
                sel_c = st.selectbox("Selecione para cancelar:", ["-- Selecione --"] + list(op_c.keys()))
                
                if sel_c != "-- Selecione --":
                    res_id = op_c[sel_c]
                    senha = st.text_input("Sua Matrícula:", type="password")
                    if st.button("🗑️ Confirmar Cancelamento"):
                        # Verifica se a matrícula existe
                        verif = supabase.table("professores_matriculas").select("professor").eq("matricula", senha).execute()
                        if verif.data:
                            user_nome = verif.data[0]['professor']
                            # Busca quem reservou
                            quem_reservou = next(r['professor'] for r in res_at.data if r['id'] == res_id)
                            
                            if user_nome in GESTORES or user_nome == quem_reservou:
                                supabase.table("reservas").update({"status": "Cancelada", "cancelado_por": user_nome}).eq("id", res_id).execute()
                                st.success(f"Cancelado por {user_nome}!")
                                st.rerun()
                            else:
                                st.error("Você não tem permissão para cancelar esta reserva.")
                        else:
                            st.error("Matrícula não cadastrada.")
            else:
                st.info("Nenhuma reserva ativa para este dia.")
        except Exception as e:
            st.error(f"Erro ao carregar gerenciamento: {e}")

    # =========================================================
    # ABA 5: ASSINATURA (IGUAL)
    # =========================================================
    with aba_assinatura:
        st.subheader("Cadastro de Assinatura")
        p_sel = st.selectbox("Seu Nome:", opcoes_professores, key="cad_nome")
        m_nova = st.text_input("Nova Matrícula (Senha):", type="password")
        if st.button("💾 Salvar"):
            if p_sel != "-- Selecione --" and m_nova:
                supabase.table("professores_matriculas").upsert({"professor": p_sel, "matricula": m_nova}).execute()
                st.success("✅ Salvo!")
