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
        # Busca na tabela correta: professores_matriculas
        res_prof = supabase.table("professores_matriculas").select("professor").execute()
        if res_prof.data:
            lista_pessoas = sorted(list(set([p.get('professor', '') for p in res_prof.data if p.get('professor')])))
    except Exception as e:
        st.error(f"Erro ao buscar lista de professores: {e}")
        lista_pessoas = lista_professores_antiga

    opcoes_professores = ["-- Selecione --"] + lista_pessoas

    # Definição das Abas
    aba_cal, aba_lista, aba_nova, aba_cancelar, aba_assinatura = st.tabs([
        "🗓️ Calendário Mensal", "📋 Lista Diária", "✍️ Nova Reserva", "❌ Gerenciar", "🔑 Assinatura"
    ])

    # =========================================================
    # ABA 1: CALENDÁRIO MENSAL
    # =========================================================
    with aba_cal:
        st.subheader("Visão Geral do Mês")
        try:
            res_cal = supabase.table("reservas").select("*").eq("status", "Ativa").execute()
            if res_cal.data:
                eventos = []
                for r in res_cal.data:
                    prof = r.get('professor', 'Prof. Sem Nome')
                    espaco = r.get('espaco', 'Sem Espaço')
                    equip = r.get('equipamentos', '')
                    data_evento = r.get('data_reserva', r.get('data', ''))
                    
                    if data_evento:
                        titulo_limpo = f"{prof} - {espaco}"
                        if equip and str(equip).strip() not in ["", "None"]:
                            titulo_limpo += f" ({equip})"
                        
                        eventos.append({
                            "title": titulo_limpo,
                            "start": data_evento,
                            "end": data_evento,
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
                st.info("Nenhuma reserva ativa encontrada.")
        except Exception as e:
            st.error(f"Erro ao carregar calendário: {e}")

    # =========================================================
    # ABA 2: LISTA DIÁRIA
    # =========================================================
    with aba_lista:
        st.subheader("Visão Diária por Espaço")
        d_lista = st.date_input("Ver detalhes do dia:", value=datetime.date.today(), format="DD/MM/YYYY", key="d_lista")
        
        try:
            res_lista = supabase.table("reservas").select("*").execute()
            if res_lista.data:
                reservas_por_espaco = {}
                for r in res_lista.data:
                    data_r = r.get("data_reserva", r.get("data", ""))
                    if str(data_r) == str(d_lista):
                        esp = r.get("espaco", "Sem Espaço")
                        if esp not in reservas_por_espaco:
                            reservas_por_espaco[esp] = []
                        reservas_por_espaco[esp].append(r)
                
                if reservas_por_espaco:
                    for espaco, lista_res in reservas_por_espaco.items():
                        with st.expander(f"📍 {espaco} ({len(lista_res)} reservas)", expanded=True):
                            dados_tabela = []
                            for r in lista_res:
                                status_bd = r.get("status", "Ativa")
                                situacao_icone = "🟢 Ativa" if status_bd == "Ativa" else "❌ Cancelada"
                                dados_tabela.append({
                                    "Aula/Horário": r.get("periodo", r.get("horario", r.get("aula", ""))),
                                    "Professor": r.get("professor", ""),
                                    "Equipamentos": r.get("equipamentos", "") or "-",
                                    "Situação": situacao_icone,
                                    "Cancelado Por": r.get("cancelado_por", "-") if status_bd != "Ativa" else "-"
                                })
                            st.dataframe(pd.DataFrame(dados_tabela).sort_values("Aula/Horário"), use_container_width=True, hide_index=True)
                else:
                    st.info(f"📅 Nenhuma reserva encontrada para {d_lista.strftime('%d/%m/%Y')}.")
        except Exception as e:
            st.error(f"Erro ao carregar lista: {e}")

    # =========================================================
    # ABA 3: NOVA RESERVA
    # =========================================================
    with aba_nova:
        st.subheader("Agendar Espaço / Equipamento")
        ESTOQUE = {"Datashow": 5, "Som": 3, "Microfone": 2}
        
        data_res = st.date_input("Data:", value=datetime.date.today(), format="DD/MM/YYYY", key="aba3_data")
        lista_9_aulas = ["1ª Aula", "2ª Aula", "3ª Aula", "4ª Aula", "5ª Aula", "6ª Aula", "7ª Aula", "8ª Aula", "9ª Aula"]
        
        st.write("**Selecione a(s) Aula(s):**")
        aulas_selecionadas = st.segmented_control("Aulas:", options=lista_9_aulas, selection_mode="multi", key="aba3_aulas")
        
        disp_data, disp_som, disp_mic = ESTOQUE["Datashow"], ESTOQUE["Som"], ESTOQUE["Microfone"]
        
        if aulas_selecionadas:
            uso_dia = supabase.table("reservas").select("*").eq("status", "Ativa").eq("data_reserva", str(data_res)).execute()
            if uso_dia.data:
                uso_por_aula = {a: {"Datashow": 0, "Som": 0, "Microfone": 0} for a in aulas_selecionadas}
                for r in uso_dia.data:
                    p = r.get("periodo", r.get("horario", r.get("aula", "")))
                    if p in uso_por_aula:
                        eq_str = str(r.get("equipamentos", ""))
                        matches = re.findall(r"(\d+)x\s*(Datashow|Som|Microfone)", eq_str, re.IGNORECASE)
                        for qtd, item in matches:
                            item_norm = "Som" if item.lower() == "som" else item.capitalize()
                            uso_por_aula[p][item_norm] += int(qtd)
                
                disp_data -= max([uso_por_aula[a]["Datashow"] for a in aulas_selecionadas])
                disp_som -= max([uso_por_aula[a]["Som"] for a in aulas_selecionadas])
                disp_mic -= max([uso_por_aula[a]["Microfone"] for a in aulas_selecionadas])

        col1, col2 = st.columns(2)
        with col1:
            professor = st.selectbox("Professor:", opcoes_professores, key="aba3_prof")
            usar_na_sala = st.checkbox("Usarei na sala de aula", key="aba3_usar_sala")
        with col2:
            espaco = "Sala de Aula" if usar_na_sala else st.selectbox("Espaço:", ["-- Selecione --", "Auditório", "Laboratório", "Biblioteca", "Quadra"], key="aba3_espaco")

        opcoes_eq = [f"{i}x Datashow" for i in range(1, disp_data + 1)] + \
                    [f"{i}x Som" for i in range(1, disp_som + 1)] + \
                    [f"{i}x Microfone" for i in range(1, disp_mic + 1)]
        
        st.caption(f"📦 Estoque disponível: {disp_data} Datashow | {disp_som} Som | {disp_mic} Mic")
        equipamentos_selecionados = st.multiselect("Equipamentos:", options=opcoes_eq, key="aba3_equipamentos")
        obs = st.text_input("Observações:", key="aba3_obs")

        if st.button("💾 Confirmar Reserva", type="primary"):
            if not aulas_selecionadas or professor == "-- Selecione --" or (espaco == "-- Selecione --" and not usar_na_sala):
                st.warning("⚠️ Preencha os campos obrigatórios.")
            else:
                sucesso = True
                for aula in aulas_selecionadas:
                    # Validação de duplicidade
                    check = supabase.table("reservas").select("id").eq("data_reserva", str(data_res)).eq("periodo", aula).eq("professor", professor).eq("status", "Ativa").execute()
                    if check.data:
                        st.error(f"❌ Você já tem reserva na {aula}.")
                        sucesso = False; break
                    
                    if espaco != "Sala de Aula":
                        check_esp = supabase.table("reservas").select("id").eq("data_reserva", str(data_res)).eq("periodo", aula).eq("espaco", espaco).eq("status", "Ativa").execute()
                        if check_esp.data:
                            st.error(f"❌ O espaço {espaco} já está ocupado na {aula}.")
                            sucesso = False; break
                    
                    if sucesso:
                        supabase.table("reservas").insert({
                            "data_reserva": str(data_res), "periodo": aula, "espaco": espaco,
                            "professor": professor, "equipamentos": ", ".join(equipamentos_selecionados),
                            "observacoes": obs, "status": "Ativa"
                        }).execute()
                
                if sucesso:
                    st.success("✅ Reserva realizada!")
                    time.sleep(1); st.rerun()

    # =========================================================
    # ABA 4: GERENCIAR / CANCELAR (REVISADA)
    # =========================================================
    with aba_cancelar:
        st.subheader("Cancelar Reservas")
        data_alvo = st.date_input("1. Data da reserva:", value=datetime.date.today(), format="DD/MM/YYYY", key="aba4_data")
        
        res_dia = supabase.table("reservas").select("*").eq("status", "Ativa").execute()
        dados_filtrados = [r for r in res_dia.data if str(r.get("data_reserva", r.get("data", ""))) == str(data_alvo)] if res_dia.data else []

        if dados_filtrados:
            df_cancel = pd.DataFrame(dados_filtrados)
            professores_do_dia = sorted(df_cancel['professor'].unique().tolist())
            prof_sel = st.selectbox("Selecione seu nome:", ["-- Selecione --"] + professores_do_dia, key="aba4_prof")
            
            if prof_sel != "-- Selecione --":
                minhas_reservas = df_cancel[df_cancel['professor'] == prof_sel]
                ids_para_cancelar = []
                
                for _, row in minhas_reservas.iterrows():
                    txt = f"📍 {row['espaco']} | ⏰ {row.get('periodo', row.get('aula', 'Horário'))}"
                    if st.checkbox(txt, key=f"chk_{row['id']}"):
                        ids_para_cancelar.append(row['id'])
                
                if ids_para_cancelar:
                    senha_input = st.text_input("Sua Matrícula (Senha):", type="password", key="pw_cancel")
                    if st.button("❌ Confirmar Cancelamentos", type="primary"):
                        # BUSCA FLEXÍVEL DE SENHA
                        res_senha = supabase.table("professores_matriculas").select("matricula").ilike("professor", f"{prof_sel.strip()}%").execute()
                        senha_correta = res_senha.data[0].get('matricula') if res_senha.data else None
                        
                        if prof_sel in GESTORES or (senha_correta and str(senha_input).strip() == str(senha_correta).strip()):
                            for id_c in ids_para_cancelar:
                                supabase.table("reservas").update({"status": "Cancelada", "cancelado_por": prof_sel}).eq("id", id_c).execute()
                            st.success("✅ Cancelado!"); time.sleep(1); st.rerun()
                        else:
                            st.error("⚠️ Senha incorreta.")
        else:
            st.info("Nenhuma reserva ativa para este dia.")

    # =========================================================
    # ABA 5: ASSINATURA (REVISADA)
    # =========================================================
    with aba_assinatura:
        st.subheader("Cadastro de Assinatura")
        nome_prof = st.selectbox("Seu Nome:", opcoes_professores, key="aba5_nome")
        matricula_prof = st.text_input("Defina sua Matrícula (Senha):", type="password", key="aba5_matricula")
        
        if st.button("💾 Salvar Assinatura", type="primary"):
            if nome_prof == "-- Selecione --" or not matricula_prof:
                st.error("⚠️ Preencha os campos.")
            else:
                try:
                    # Upsert (Atualiza ou insere)
                    verif = supabase.table("professores_matriculas").select("id").eq("professor", nome_prof.strip()).execute()
                    if verif.data:
                        supabase.table("professores_matriculas").update({"matricula": matricula_prof.strip()}).eq("professor", nome_prof.strip()).execute()
                    else:
                        supabase.table("professores_matriculas").insert({"professor": nome_prof.strip(), "matricula": matricula_prof.strip()}).execute()
                    st.success("✅ Salvo!"); time.sleep(1); st.rerun()
                except Exception as e:
                    st.error(f"Erro: {e}")