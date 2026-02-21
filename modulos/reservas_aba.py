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
    # INÍCIO - ABA 1: CALENDÁRIO MENSAL
    # =========================================================
    with aba_cal:
        st.subheader("Visão Geral do Mês")
        try:
            res_cal = supabase.table("reservas").select("*").eq("status", "Ativa").execute()
            if res_cal.data:
                eventos = []
                for r in res_cal.data:
                    prof = r.get('professor', '')
                    espaco = r.get('espaco', '')
                    equip = r.get('equipamentos')
                    
                    if equip and str(equip).strip() not in ["", "None"]:
                        titulo_limpo = f"{prof} - {espaco} - {equip}"
                    else:
                        titulo_limpo = f"{prof} - {espaco}"
                    
                    eventos.append({
                        "title": titulo_limpo,
                        "start": r['data_reserva'],
                        "end": r['data_reserva'],
                        "backgroundColor": "#1f77b4"
                    })
                
                calendar_options = {
                    "locale": "pt-br",
                    "headerToolbar": {"left": "today prev,next", "center": "title", "right": "dayGridMonth,timeGridWeek"},
                    "initialView": "dayGridMonth",
                    "buttonText": {"today": "Hoje", "month": "Mês", "week": "Semana"}
                }
                calendar(events=eventos, options=calendar_options)
            else:
                st.info("Nenhuma reserva encontrada.")
        except Exception as e:
            st.error(f"Erro ao carregar calendário: {e}")
    # =========================================================
    # FIM - ABA 1
    # =========================================================

   # =========================================================
    # ABA 2: LISTA DIÁRIA - TESTE DE ESPAÇOS (RESERVÁVEIS VS RESERVADOS)
    # =========================================================
    with aba_lista:
        st.subheader("Visão Diária por Espaço")
        
        # Calendário que abre automaticamente no dia de hoje
        data_filtro = st.date_input("Ver detalhes do dia:", value=datetime.date.today(), key="data_teste_espacos")
        
        try:
            # Busca as reservas do banco para o dia selecionado
            res = supabase.table("reservas").select("*").eq("data_reserva", str(data_filtro)).execute()
            df_dia = pd.DataFrame(res.data) if res.data else pd.DataFrame()

            # Iteramos por TODOS os espaços cadastrados na sua lista 'espacos'
            # Isso garante que mesmo os vazios apareçam na tela
            for espaco_escola in espacos:
                
                # Filtramos as reservas que pertencem a este espaço específico
                if not df_dia.empty and 'espaco' in df_dia.columns:
                    df_espaco = df_dia[df_dia['espaco'] == espaco_escola].copy()
                else:
                    df_espaco = pd.DataFrame()

                # Criamos o expansor para cada espaço da escola
                status_icone = "🔴" if not df_espaco.empty else "⚪"
                label_expander = f"{status_icone} {espaco_escola} ({len(df_espaco)} reservas)"
                
                with st.expander(label_expander, expanded=not df_espaco.empty):
                    if not df_espaco.empty:
                        # Seleção de colunas baseada no seu banco
                        col_exibir = []
                        existentes = df_espaco.columns.tolist()
                        
                        if 'periodo' in existentes: col_exibir.append('periodo')
                        if 'professor' in existentes: col_exibir.append('professor')
                        if 'equipamentos' in existentes: col_exibir.append('equipamentos')
                        if 'status' in existentes: col_exibir.append('status')

                        # Formatação para exibição
                        df_final = df_espaco[col_exibir].copy()
                        if 'status' in df_final.columns:
                            df_final['status'] = df_final['status'].apply(lambda x: "🟢 Ativa" if x == "Ativa" else "❌")

                        st.dataframe(
                            df_final.rename(columns={
                                'periodo': 'Aula/Horário',
                                'professor': 'Professor',
                                'equipamentos': 'Equipamentos (Data Show/Som)',
                                'status': 'Situação'
                            }),
                            use_container_width=True,
                            hide_index=True
                        )
                    else:
                        # Se o espaço está na sua lista mas não tem reserva no banco
                        st.info(f"O espaço '{espaco_escola}' está disponível para reserva neste dia.")

        except Exception as e:
            st.error(f"Erro ao processar visão diária: {e}")

    # =========================================================
    # FIM - ABA 2
    # =========================================================
    
   # =========================================================
    # INÍCIO - ABA 3: NOVA RESERVA (COM BOTÕES PILL)
    # =========================================================
    with aba_nova:
        st.subheader("Agendar Espaço")
        
        # Criamos o formulário
        with st.form("form_nova_reserva"):
            # Seleção de Aula usando Botões Pill (Segmented Control)
            # Isso substitui o selectbox antigo por botões clicáveis lado a lado
            st.write("**Selecione a Aula:**")
            a_res = st.segmented_control(
                "Aulas disponíveis:",
                options=aulas_opcoes,
                selection_mode="single", # Permite selecionar apenas uma aula
                label_visibility="collapsed"
            )
            
            st.divider() # Uma linha fina para separar
            
            c1, c2 = st.columns(2)
            with c1:
                d_res = st.date_input("Data:", value=datetime.date.today())
                p_res = st.selectbox("Professor:", opcoes_professores)
            with c2:
                # Carrega os espaços definidos na sua lista
                e_res = st.selectbox("Espaço:", ["-- Selecione --"] + espacos)
                eq_res = st.text_input("Equipamentos:", placeholder="Ex: Data show")
            
            o_res = st.text_input("Observações:")
            
            if st.form_submit_button("💾 Confirmar Reserva"):
                # Validação: Agora verificamos se a_res (o pill) foi clicado
                if not a_res or p_res == "-- Selecione --" or e_res == "-- Selecione --":
                    st.warning("⚠️ Por favor, selecione a Aula, o Professor e o Espaço.")
                else:
                    # Verifica conflito usando a coluna 'periodo' do seu banco
                    conf = supabase.table("reservas").select("id").eq("data_reserva", str(d_res)).eq("periodo", a_res).eq("espaco", e_res).eq("status", "Ativa").execute()
                    
                    if conf.data:
                        st.error(f"🚨 Conflito! O {e_res} já está reservado para a {a_res}.")
                    else:
                        # Insere os dados usando os nomes de coluna do seu Supabase
                        supabase.table("reservas").insert({
                            "data_reserva": str(d_res),
                            "periodo": a_res,
                            "professor": p_res,
                            "espaco": e_res,
                            "equipamentos": eq_res,
                            "obs": o_res,
                            "status": "Ativa"
                        }).execute()
                        st.success(f"✅ Sucesso! {e_res} reservado para {p_res} ({a_res}).")
                        st.rerun()
    # =========================================================
    # FIM - ABA 3
    # =========================================================


    # =========================================================
    # INÍCIO - ABA 4: GERENCIAR / CANCELAR
    # =========================================================
    with aba_cancelar:
        st.subheader("Cancelar uma Reserva")
        d_can = st.date_input("Data para cancelar:", value=datetime.date.today(), key="d_can")
        try:
            # Carrega matrículas para conferência
            res_m = supabase.table("professores_matriculas").select("*").execute()
            m_db = {str(r['matricula']): r['professor'] for r in res_m.data} if res_m.data else {}

            res_at = supabase.table("reservas").select("*").eq("data_reserva", str(d_can)).eq("status", "Ativa").execute()
            if res_at.data:
                op_c = {f"{r['aula']} - {r['espaco']} ({r['professor']})": r['id'] for r in res_at.data}
                sel_c = st.selectbox("Escolha a reserva:", ["-- Selecione --"] + list(op_c.keys()))
                if sel_c != "-- Selecione --":
                    id_c = op_c[sel_c]
                    prof_r = next(r['professor'] for r in res_at.data if r['id'] == id_c)
                    senha = st.text_input("Sua Matrícula (Assinatura):", type="password")
                    if st.button("🗑️ Confirmar Cancelamento"):
                        if senha in m_db:
                            u_nome = m_db[senha]
                            if u_nome in GESTORES or u_nome == prof_r:
                                supabase.table("reservas").update({"status": "Cancelada", "cancelado_por": u_nome}).eq("id", id_c).execute()
                                st.success("Cancelado!")
                                st.rerun()
                            else: st.error("Sem permissão.")
                        else: st.error("Matrícula não encontrada.")
            else: st.info("Sem reservas ativas.")
        except Exception as e: st.error(f"Erro: {e}")
    # =========================================================
    # FIM - ABA 4
    # =========================================================


    # =========================================================
    # INÍCIO - ABA 5: CADASTRAR ASSINATURA
    # =========================================================
    with aba_assinatura:
        st.subheader("Cadastro de Assinatura")
        p_sel = st.selectbox("Seu Nome:", opcoes_professores, key="cad_nome")
        m_nova = st.text_input("Sua Matrícula (Senha):", type="password")
        if st.button("💾 Salvar Assinatura"):
            if p_sel != "-- Selecione --" and m_nova.isdigit():
                try:
                    ex = supabase.table("professores_matriculas").select("id").eq("professor", p_sel).execute()
                    if ex.data: supabase.table("professores_matriculas").update({"matricula": m_nova}).eq("professor", p_sel).execute()
                    else: supabase.table("professores_matriculas").insert({"professor": p_sel, "matricula": m_nova}).execute()
                    st.success("✅ Cadastrada!")
                except Exception as e: st.error(f"Erro: {e}")
            else: st.warning("Dados inválidos.")
    # =========================================================
    # FIM - ABA 5
    # =========================================================
