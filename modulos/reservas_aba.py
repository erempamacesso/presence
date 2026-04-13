import streamlit as st
import pandas as pd
import datetime
import re
import time
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
    # INÍCIO - ABA 2: LISTA DIÁRIA
    # =========================================================
    with aba_lista:
        st.subheader("Visão Diária por Espaço")
        
        d_lista = st.date_input("Ver detalhes do dia:", value=datetime.date.today(), format="DD/MM/YYYY", key="d_lista")
        
        try:
            res_lista = supabase.table("reservas").select("*").eq("data_reserva", str(d_lista)).execute()
            
            if res_lista.data:
                reservas_por_espaco = {}
                for r in res_lista.data:
                    esp = r.get("espaco", "Sem Espaço")
                    if esp not in reservas_por_espaco:
                        reservas_por_espaco[esp] = []
                    reservas_por_espaco[esp].append(r)
                
                for espaco, lista_res in reservas_por_espaco.items():
                    with st.expander(f"📍 {espaco} ({len(lista_res)} reservas)", expanded=True):
                        dados_tabela = []
                        for r in lista_res:
                            status_bd = r.get("status", "Ativa")
                            
                            if status_bd == "Ativa":
                                situacao_icone = "🟢 Ativa"
                                quem_cancelou = "-"
                            else:
                                situacao_icone = "❌ Cancelada"
                                quem_cancelou = r.get("cancelado_por", "Sistema")
                                
                            dados_tabela.append({
                                "Aula/Horário": r.get("periodo", ""),
                                "Professor": r.get("professor", ""),
                                "Equipamentos (Data Show/Som)": r.get("equipamentos", "") or "-",
                                "Situação": situacao_icone,
                                "Cancelado Por": quem_cancelou
                            })
                        
                        dados_tabela = sorted(dados_tabela, key=lambda x: x["Aula/Horário"])
                        st.dataframe(dados_tabela, use_container_width=True, hide_index=True)
                        
            else:
                st.info("📅 Nenhuma reserva encontrada para este dia.")
        except Exception as e:
            st.error(f"Erro ao carregar lista diária: {e}")
    
    # =========================================================
    # INÍCIO - ABA 3: NOVA RESERVA
    # =========================================================
    with aba_nova:
        st.subheader("Agendar Espaço / Equipamento")
        
        ESTOQUE = {"Datashow": 5, "Som": 3, "Microfone": 2}
        
        st.write("**1. Escolha a Data e Horário:**")
        col_data, col_vazia = st.columns(2)
        with col_data:
            data_res = st.date_input("Data:", value=datetime.date.today(), format="DD/MM/YYYY", key="aba3_data")
        
        lista_9_aulas = ["1ª Aula", "2ª Aula", "3ª Aula", "4ª Aula", "5ª Aula", "6ª Aula", "7ª Aula", "8ª Aula", "9ª Aula"]
        
        st.write("**Selecione a(s) Aula(s):** *(Toque para selecionar várias)*")
        aulas_selecionadas = st.segmented_control(
            "Aulas:", 
            options=lista_9_aulas, 
            selection_mode="multi",
            label_visibility="collapsed",
            key="aba3_aulas"
        )
        
        # --- LÓGICA DE ESTOQUE DINÂMICO ---
        disp_data = ESTOQUE["Datashow"]
        disp_som = ESTOQUE["Som"]
        disp_mic = ESTOQUE["Microfone"]
        
        if aulas_selecionadas:
            uso_dia = supabase.table("reservas").select("periodo, equipamentos").eq("data_reserva", str(data_res)).eq("status", "Ativa").in_("periodo", aulas_selecionadas).execute()
            
            if uso_dia.data:
                uso_por_aula = {a: {"Datashow": 0, "Som": 0, "Microfone": 0} for a in aulas_selecionadas}
                for r in uso_dia.data:
                    p = r["periodo"]
                    eq_str = str(r.get("equipamentos", ""))
                    if eq_str and p in uso_por_aula:
                        matches = re.findall(r"(\d+)x\s*(Datashow|Som|Microfone)", eq_str, re.IGNORECASE)
                        for qtd, item in matches:
                            item_norm = "Som" if item.lower() == "som" else item.capitalize()
                            uso_por_aula[p][item_norm] += int(qtd)
                
                max_uso_data = max([uso_por_aula[a]["Datashow"] for a in aulas_selecionadas])
                max_uso_som = max([uso_por_aula[a]["Som"] for a in aulas_selecionadas])
                max_uso_mic = max([uso_por_aula[a]["Microfone"] for a in aulas_selecionadas])
                
                disp_data = max(0, ESTOQUE["Datashow"] - max_uso_data)
                disp_som = max(0, ESTOQUE["Som"] - max_uso_som)
                disp_mic = max(0, ESTOQUE["Microfone"] - max_uso_mic)
        
        st.divider()
        
        st.write("**2. Dados da Reserva:**")
        col1, col2 = st.columns(2)
        
        with col1:
            professor = st.selectbox("Professor:", opcoes_professores, key="aba3_prof")
            usar_na_sala = st.checkbox("Usarei na sala de aula (Apenas Equipamentos)", key="aba3_usar_sala")
            
        with col2:
            if usar_na_sala:
                espaco = "Sala de Aula"
                st.text_input("Espaço:", value="Sala de Aula (Própria)", disabled=True, key="aba3_espaco_disabled")
            else:
                espaco = st.selectbox("Espaço:", ["-- Selecione --", "Auditório", "Laboratório", "Biblioteca", "Quadra"], key="aba3_espaco")
                
        st.write("**3. Equipamentos Necessários:**")
        
        opcoes_eq = []
        for i in range(1, disp_data + 1): opcoes_eq.append(f"{i}x Datashow")
        for i in range(1, disp_som + 1): opcoes_eq.append(f"{i}x Som")
        for i in range(1, disp_mic + 1): opcoes_eq.append(f"{i}x Microfone")
        
        if aulas_selecionadas:
            st.caption(f"📦 Restam no estoque nestas aulas: **{disp_data} Datashow | {disp_som} Som | {disp_mic} Mic**")
        else:
            st.caption("Selecione a(s) aula(s) acima para ver a disponibilidade do estoque.")

        equipamentos_selecionados = st.multiselect(
            "Selecione os equipamentos na caixa abaixo:",
            options=opcoes_eq,
            placeholder="Clique aqui para ver os equipamentos disponíveis...",
            key="aba3_equipamentos"
        )
            
        obs = st.text_input("Observações:", key="aba3_obs")
        
        if st.button("💾 Confirmar Reserva", type="primary"):
            tipos_selecionados = []
            erro_multiplo_eq = False
            for eq in equipamentos_selecionados:
                tipo = eq.split("x ")[1] 
                if tipo in tipos_selecionados:
                    erro_multiplo_eq = True
                tipos_selecionados.append(tipo)
                
            if not aulas_selecionadas:
                st.warning("⚠️ Selecione pelo menos uma aula clicando nos botões azuis.")
            elif professor == "-- Selecione --":
                st.warning("⚠️ Selecione o professor.")
            elif espaco == "-- Selecione --" and not usar_na_sala:
                st.warning("⚠️ Selecione um espaço ou marque 'Usarei na sala de aula'.")
            elif not equipamentos_selecionados and usar_na_sala:
                st.warning("⚠️ Se vai usar na própria sala, você precisa selecionar pelo menos um equipamento!")
            elif erro_multiplo_eq:
                st.warning("⚠️ Selecione apenas UMA quantidade para cada equipamento (Ex: não marque '1x Datashow' e '2x Datashow' juntos).")
            else:
                sucesso_total = True
                aulas_com_conflito_espaco = []
                aulas_com_duplicata_prof = []
                
                equipamentos_texto = ", ".join(equipamentos_selecionados)
                
                for aula in aulas_selecionadas:
                    pode_salvar = True
                    
                    duplicata = supabase.table("reservas").select("id").eq("data_reserva", str(data_res)).eq("periodo", aula).eq("professor", professor).eq("status", "Ativa").execute()
                    if duplicata.data:
                        aulas_com_duplicata_prof.append(aula)
                        pode_salvar = False
                        sucesso_total = False

                    if pode_salvar and espaco != "Sala de Aula":
                        conflito_espaco = supabase.table("reservas").select("id").eq("data_reserva", str(data_res)).eq("periodo", aula).eq("espaco", espaco).eq("status", "Ativa").execute()
                        if conflito_espaco.data:
                            aulas_com_conflito_espaco.append(aula)
                            pode_salvar = False
                            sucesso_total = False
                    
                    if pode_salvar:
                        try:
                            dados_insert = {
                                "data_reserva": str(data_res),
                                "periodo": aula,
                                "espaco": espaco,
                                "professor": professor,
                                "equipamentos": equipamentos_texto,
                                "observacoes": obs,
                                "status": "Ativa"
                            }
                            supabase.table("reservas").insert(dados_insert).execute()
                        except Exception as e:
                            st.error(f"Erro ao salvar a {aula}: {e}")
                            sucesso_total = False
                
                if aulas_com_duplicata_prof:
                    st.error(f"🛡️ **Bloqueio de Duplicata:** {professor}, você já possui uma reserva ativa para a {', '.join(aulas_com_duplicata_prof)} neste dia.")
                
                if aulas_com_conflito_espaco:
                    st.error(f"❌ O espaço '{espaco}' já está reservado por outra pessoa nestas aulas: {', '.join(aulas_com_conflito_espaco)}.")
                
                if sucesso_total:
                    st.success("✅ Reserva(s) realizada(s) com sucesso!")
                    
                    chaves_para_limpar = [
                        "aba3_aulas", "aba3_usar_sala", "aba3_espaco", 
                        "aba3_equipamentos", "aba3_obs"
                    ]
                    
                    for chave in chaves_para_limpar:
                        if chave in st.session_state:
                            del st.session_state[chave]
                            
                    time.sleep(1.5) 
                    
                    st.rerun()
    
    # =========================================================
    # INÍCIO - ABA 4: GERENCIAR / CANCELAR
    # =========================================================
    # --- Dentro da aba_cancelar ---
    with aba_cancelar:
        st.subheader("Cancelar Reserva")
    
    # Busca todas as reservas para mostrar na lista de exclusão
    res_todas = supabase.table("reservas").select("*").execute()
    df_cancel = pd.DataFrame(res_todas.data)

    if not df_cancel.empty:
        # Filtro para facilitar achar a reserva
        prof_sel = st.selectbox("Selecione seu nome para ver suas reservas:", ["-- Selecione --"] + sorted(df_cancel['professor'].unique().tolist()))
        
        if prof_sel != "-- Selecione --":
            minhas_reservas = df_cancel[df_cancel['professor'] == prof_sel]
            
            for _, row in minhas_reservas.iterrows():
                col1, col2 = st.columns([3, 1])
                col1.write(f"📍 {row['espaco']} | ⏰ {row['horario']} | 📅 {row['data']}")
                
                if col2.button("❌ Excluir", key=f"del_{row['id']}"):
                    senha_input = st.text_input("Confirme sua Matrícula (Senha):", type="password", key=f"pw_{row['id']}")
                    
                    if st.button("Confirmar Exclusão", key=f"conf_{row['id']}"):
                        # 🔍 O SEGREDO: Busca a senha ignorando espaços
                        res_senha = supabase.table("professores_matriculas").select("matricula").eq("professor", prof_sel.strip()).execute()
                        
                        senha_correta = res_senha.data[0]['matricula'] if res_senha.data else None
                        
                        # Se for GESTOR ou a senha bater
                        if prof_sel in GESTORES or str(senha_input) == str(senha_correta):
                            supabase.table("reservas").delete().eq("id", row['id']).execute()
                            st.success("Reserva excluída!")
                            st.rerun()
                        else:
                            st.error("⚠️ Senha incorreta ou sem permissão.")

    # =========================================================
    # INÍCIO - ABA 5: ASSINATURA
    # =========================================================
    # --- Dentro da aba_assinatura ---
        with aba_assinatura:
            st.subheader("Cadastro de Assinatura Eletrônica")
        st.info("Escolha seu nome na lista oficial da escola para criar sua senha.")
        
        # IMPORTANTE: Use a lista_professores_antiga aqui, para permitir novos cadastros!
        nome_prof = st.selectbox("Seu Nome:", ["-- Selecione --"] + lista_professores_antiga, key="aba5_nome")
        matricula_prof = st.text_input("Defina sua Matrícula (Senha):", type="password", key="aba5_matricula")
        
        if st.button("💾 Salvar Assinatura", type="primary"):
            if nome_prof == "-- Selecione --" or not matricula_prof:
                st.error("⚠️ Preencha todos os campos.")
            else:
                try:
                    # Limpa o nome para evitar erros de espaço
                    nome_limpo = nome_prof.strip()
                    
                    # Verifica se já existe para decidir entre UPDATE ou INSERT
                    verif = supabase.table("professores_matriculas").select("*").eq("professor", nome_limpo).execute()
                    
                    if verif.data:
                        supabase.table("professores_matriculas").update({"matricula": matricula_prof}).eq("professor", nome_limpo).execute()
                    else:
                        supabase.table("professores_matriculas").insert({"professor": nome_limpo, "matricula": matricula_prof}).execute()
                    
                    st.success(f"✅ Assinatura de {nome_limpo} salva com sucesso!")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")
