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
    # ABA 1: CALENDÁRIO MENSAL (COM TEXTO MULTILINHA)
    # =========================================================
    with aba_cal:
        st.markdown("""
            <style>
                .fc-event-title { white-space: normal !important; word-wrap: break-word !important; }
                .fc-daygrid-event { white-space: normal !important; align-items: flex-start !important; }
            </style>
        """, unsafe_allow_code=True)

        st.subheader("Visão Geral do Mês")
        try:
            # Busca apenas reservas ativas
            res_cal = supabase.table("reservas").select("*").eq("status", "Ativa").execute()
            
            if res_cal.data:
                eventos = []
                for r in res_cal.data:
                    prof = r.get('professor', '---')
                    esp = r.get('espaco', '---')
                    # Prioriza 'periodo' que é o que está preenchido no seu banco
                    horario = r.get('periodo') or r.get('aula') or "S/H"
                    equip = r.get('equipamentos')
                    
                    titulo = f"{horario} - {prof} - {esp}"
                    if equip and str(equip).strip() not in ["", "None", "NULL", "None"]:
                        titulo += f" - 🛠️ {equip}"
                    
                    eventos.append({
                        "title": titulo,
                        "start": r['data_reserva'],
                        "end": r['data_reserva'],
                        "backgroundColor": "#1f77b4"
                    })
                
                calendar(events=eventos, options={
                    "locale": "pt-br",
                    "initialView": "dayGridMonth",
                    "eventDisplay": "block",
                })
            else:
                st.info("Nenhuma reserva ativa.")
        except Exception as e:
            st.error(f"Erro no calendário: {e}")

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
