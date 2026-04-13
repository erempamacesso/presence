import streamlit as st
import pandas as pd
import datetime
import re
import time
from streamlit_calendar import calendar

# --- GESTORES COM PRIVILÉGIO TOTAL ---
GESTORES = ["Lilian Jordão", "Jackson Carvalho", "Lylian Cabral"]

# Paleta de cores para diferenciar professores no calendário
CORES_PROFESSORES = [
    "#1f77b4", "#d62728", "#2ca02c", "#ff7f0e", "#9467bd",
    "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
    "#aec7e8", "#ffbb78", "#98df8a", "#ff9896", "#c5b0d5"
]

def exibir_reservas(supabase, lista_professores_antiga, aulas_opcoes, espacos, arg1=None, arg2=None, arg3=None):
    st.title("📅 Sistema de Reservas")
    
    # ---------------------------------------------------------
    # PARTE 0: PREPARAÇÃO DE DADOS (Busca nomes no Banco)
    # ---------------------------------------------------------
    lista_pessoas = []
    try:
        res_prof = supabase.table("professores_matriculas").select("professor").execute()
        if res_prof.data:
            lista_pessoas = sorted(list(set([p.get('professor', '') for p in res_prof.data if p.get('professor')])))
    except Exception as e:
        st.error(f"Erro ao buscar lista de professores: {e}")
        lista_pessoas = lista_professores_antiga

    opcoes_professores = ["-- Selecione --"] + lista_pessoas

    # Definição das Abas (AGORA COM 6 ABAS)
    aba_cal, aba_lista, aba_minhas, aba_nova, aba_cancelar, aba_assinatura = st.tabs([
        "🗓️ Calendário", "📋 Lista Diária", "👩‍🏫 Minhas Reservas", "✍️ Nova Reserva", "❌ Gerenciar", "🔑 Assinatura"
    ])

    # =========================================================
    # ABA 1: CALENDÁRIO MENSAL
    # =========================================================
    with aba_cal:
        st.subheader("Visão Geral do Mês")
        try:
            # Aumentando o limite para puxar as reservas futuras (ex: agosto)
            res_cal = supabase.table("reservas").select("*").eq("status", "Ativa").limit(5000).execute()
            if res_cal.data:
                eventos = []
                todos_profs = sorted(set(r.get('professor', '') for r in res_cal.data if r.get('professor')))
                mapa_cores = {prof: CORES_PROFESSORES[i % len(CORES_PROFESSORES)] for i, prof in enumerate(todos_profs)}
                
                for r in res_cal.data:
                    prof = r.get('professor', 'Prof. Sem Nome')
                    espaco = r.get('espaco', 'Sem Espaço')
                    equip = r.get('equipamentos', '')
                    periodo = r.get('periodo', r.get('horario', r.get('aula', '')))
                    
                    data_evento = r.get('data_reserva') or r.get('data') or ''
                    if not data_evento: continue
                    
                    try:
                        data_fmt = str(pd.to_datetime(str(data_evento), errors='coerce').date())
                        if data_fmt == "NaT": continue
                    except Exception:
                        continue
                    
                    titulo_limpo = f"{prof} - {espaco}"
                    if periodo: titulo_limpo += f" | {periodo}"
                    if equip and str(equip).strip() not in ["", "None", "nan"]: titulo_limpo += f" ({equip})"
                    
                    try:
                        data_fim = str((pd.to_datetime(data_fmt) + pd.Timedelta(days=1)).date())
                    except Exception:
                        data_fim = data_fmt
                    
                    eventos.append({
                        "title": titulo_limpo,
                        "start": data_fmt,
                        "end": data_fim,
                        "backgroundColor": mapa_cores.get(prof, "#1f77b4"),
                        "borderColor": mapa_cores.get(prof, "#1f77b4"),
                        "allDay": True
                    })
                
                if eventos:
                    calendar_options = {
                        "locale": "pt-br",
                        "headerToolbar": {"left": "today prev,next", "center": "title", "right": "dayGridMonth,timeGridWeek,listWeek"},
                        "initialView": "dayGridMonth",
                        "buttonText": {"today": "Hoje", "month": "Mês", "week": "Semana", "list": "Lista"},
                        "eventDisplay": "block",
                        "dayMaxEvents": False
                    }
                    calendar(events=eventos, options=calendar_options)
                    
                    st.divider()
                    st.caption("**Legenda de professores:**")
                    cols_leg = st.columns(5)
                    for i, (prof, cor) in enumerate(mapa_cores.items()):
                        with cols_leg[i % 5]:
                            st.markdown(f"<span style='background:{cor}; color:white; padding:2px 8px; border-radius:4px; font-size:11px;'>{prof}</span>", unsafe_allow_html=True)
                else:
                    st.info("Nenhuma reserva ativa encontrada.")
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
                    data_r = r.get("data_reserva") or r.get("data") or ""
                    try:
                        data_r_fmt = str(pd.to_datetime(str(data_r), errors='coerce').date())
                    except Exception:
                        data_r_fmt = str(data_r)
                    
                    if data_r_fmt == str(d_lista):
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
    # ABA 3: MINHAS RESERVAS (ORDEM CRESCENTE E TABELA LONGA)
    # =========================================================
    with aba_minhas:
        st.subheader("👩‍🏫 Histórico Completo do Professor")
        st.info("Visualização de todas as reservas vinculadas ao nome. Ordem: Da mais antiga para a mais futura.")
        
        prof_busca = st.selectbox("Selecione o nome para conferir:", opcoes_professores, key="aba_minhas_prof")
        
        if prof_busca != "-- Selecione --":
            try:
                # Busca com limite alto (5000) para garantir que pegue o ano todo
                res_hist = supabase.table("reservas").select("*").ilike("professor", f"%{prof_busca.strip()}%").limit(5000).execute()
                
                if res_hist.data:
                    dados_hist = []
                    for r in res_hist.data:
                        status_bd = r.get("status", "Ativa")
                        situacao_icone = "🟢 Ativa" if status_bd == "Ativa" else "❌ Cancelada"
                        
                        raw_data = r.get("data_reserva") or r.get("data") or ""
                        try:
                            dt_obj = pd.to_datetime(str(raw_data), errors='coerce')
                            if pd.isnull(dt_obj):
                                data_formatada = str(raw_data)
                                data_ordenacao = pd.to_datetime("2099-12-31") # Joga pro fim se der erro
                            else:
                                data_formatada = dt_obj.strftime("%d/%m/%Y")
                                data_ordenacao = dt_obj
                        except Exception:
                            data_formatada = str(raw_data)
                            data_ordenacao = pd.to_datetime("2099-12-31")
                            
                        dados_hist.append({
                            "_data_sort": data_ordenacao,
                            "Data": data_formatada,
                            "Aula/Horário": r.get("periodo", r.get("horario", r.get("aula", ""))),
                            "Espaço": r.get("espaco", ""),
                            "Equipamentos": r.get("equipamentos", "") or "-",
                            "Situação": situacao_icone,
                            "Observações": r.get("observacoes", "") or "-"
                        })
                    
                    # --- ORDENAÇÃO CRESCENTE (Data mais antiga -> Data mais futura) ---
                    df_hist = pd.DataFrame(dados_hist).sort_values(by=["_data_sort", "Aula/Horário"], ascending=[True, True])
                    df_hist = df_hist.drop(columns=["_data_sort"])
                    
                    st.success(f"✅ Exibindo {len(df_hist)} registros para '{prof_busca}'.")
                    
                    # --- TABELA MAIS LONGA (Altura definida para 800 pixels) ---
                    st.dataframe(
                        df_hist, 
                        use_container_width=True, 
                        hide_index=True,
                        height=800  # Aqui definimos a tabela mais longa visualmente
                    )
                else:
                    st.warning(f"⚠️ Nenhuma reserva encontrada no banco para '{prof_busca}'.")
            except Exception as e:
                st.error(f"Erro ao carregar histórico: {e}")

    
# =========================================================
    # ABA 4: NOVA RESERVA (SISTEMA ANTI-FANTASMA)
    # =========================================================
    with aba_nova:
        st.subheader("Agendar Espaço / Equipamento")
        ESTOQUE = {"Datashow": 5, "Som": 3, "Microfone": 2}
        
        col_data1, col_data2 = st.columns(2)
        with col_data1:
            data_res = st.date_input("Data da Reserva (Início):", value=datetime.date.today(), format="DD/MM/YYYY", key="n_data_ini")
        with col_data2:
            recorrente = st.checkbox("🔄 Repetir semanalmente", key="n_recorrente")
            if recorrente:
                data_fim = st.date_input("Repetir até o dia:", value=data_res + datetime.timedelta(weeks=4), format="DD/MM/YYYY", key="n_data_fim")
            else:
                data_fim = data_res

        lista_9_aulas = ["1ª Aula", "2ª Aula", "3ª Aula", "4ª Aula", "5ª Aula", "6ª Aula", "7ª Aula", "8ª Aula", "9ª Aula"]
        st.write("**Selecione a(s) Aula(s):**")
        aulas_selecionadas = st.segmented_control("Aulas:", options=lista_9_aulas, selection_mode="multi", key="n_aulas")
        
        # --- BUSCA DE PROFESSOR LIMPA ---
        professor_raw = st.selectbox("Professor:", opcoes_professores, key="n_prof_select")
        professor = professor_raw.strip() if professor_raw != "-- Selecione --" else "-- Selecione --"
        
        col_sala1, col_sala2 = st.columns(2)
        with col_sala1:
            usar_na_sala = st.checkbox("Usarei na sala de aula", key="n_sala_check")
        with col_sala2:
            espaco = "Sala de Aula" if usar_na_sala else st.selectbox(
                "Espaço:", ["-- Selecione --", "Auditório", "Laboratório", "Biblioteca", "Quadra"],
                key="n_espaco_select"
            )

        equipamentos_selecionados = st.multiselect("Equipamentos:", ["1x Datashow", "2x Datashow", "1x Som", "1x Microfone"], key="n_eq")
        obs = st.text_input("Observações:", key="n_obs")

        if st.button("💾 Confirmar Reserva", type="primary"):
            if not aulas_selecionadas or professor == "-- Selecione --" or (espaco == "-- Selecione --" and not usar_na_sala):
                st.warning("⚠️ Preencha os campos obrigatórios.")
            elif data_fim < data_res:
                st.error("⚠️ Data final inválida.")
            else:
                # 1. Gerar lista de datas
                datas_para_reservar = []
                temp_data = data_res
                while temp_data <= data_fim:
                    datas_para_reservar.append(temp_data)
                    if not recorrente: break
                    temp_data += datetime.timedelta(days=7)
                
                sucessos = 0
                
                with st.spinner("Validando disponibilidades..."):
                    for d in datas_para_reservar:
                        data_str = str(d)
                        for aula in aulas_selecionadas:
                            # --- VERIFICAÇÃO ULTRA-RIGOROSA (Anti-Fantasma) ---
                            # Usamos .ilike para ignorar espaços extras e maiúsculas/minúsculas
                            
                            # A. Verificando se o Professor já está ocupado
                            check_prof = supabase.table("reservas").select("id, espaco")\
                                .eq("data_reserva", data_str)\
                                .eq("periodo", aula)\
                                .ilike("professor", f"%{professor}%")\
                                .eq("status", "Ativa")\
                                .execute()
                            
                            if check_prof.data:
                                item = check_prof.data[0]
                                st.error(f"❌ Conflito: {professor} já tem reserva no dia {d.strftime('%d/%m/%Y')} na {aula} (Espaço: {item['espaco']}).")
                                st.info(f"💡 Dica: Procure no Supabase pelo ID: {item['id']} para resolver.")
                                continue

                            # B. Verificando se o Espaço já está ocupado (exceto sala de aula)
                            if espaco != "Sala de Aula":
                                check_esp = supabase.table("reservas").select("id, professor")\
                                    .eq("data_reserva", data_str)\
                                    .eq("periodo", aula)\
                                    .eq("espaco", espaco)\
                                    .eq("status", "Ativa")\
                                    .execute()
                                
                                if check_esp.data:
                                    item_e = check_esp.data[0]
                                    st.error(f"❌ O espaço {espaco} já está reservado por {item_e['professor']} no dia {d.strftime('%d/%m/%Y')} na {aula}.")
                                    continue

                            # Se passou nas validações, insere
                            try:
                                supabase.table("reservas").insert({
                                    "data_reserva": data_str,
                                    "periodo": aula,
                                    "espaco": espaco,
                                    "professor": professor,
                                    "equipamentos": ", ".join(equipamentos_selecionados),
                                    "observacoes": obs,
                                    "status": "Ativa"
                                }).execute()
                                sucessos += 1
                            except Exception as e:
                                st.error(f"Erro ao inserir no banco: {e}")

                if sucessos > 0:
                    st.success(f"✅ {sucessos} reserva(s) criada(s)!")
                    time.sleep(1.5)
                    st.rerun()

    # =========================================================
    # ABA 5: GERENCIAR / CANCELAR
    # =========================================================
    with aba_cancelar:
        st.subheader("Cancelar Reservas")
        data_alvo = st.date_input("1. Data da reserva:", value=datetime.date.today(), format="DD/MM/YYYY", key="aba4_data")
        
        res_dia = supabase.table("reservas").select("*").eq("status", "Ativa").execute()
        dados_filtrados = []
        if res_dia.data:
            for r in res_dia.data:
                data_r = r.get("data_reserva") or r.get("data") or ""
                try:
                    data_r_fmt = str(pd.to_datetime(str(data_r), errors='coerce').date())
                except Exception:
                    data_r_fmt = str(data_r)
                if data_r_fmt == str(data_alvo):
                    dados_filtrados.append(r)

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
                        res_senha = supabase.table("professores_matriculas").select("matricula").ilike("professor", f"{prof_sel.strip()}%").execute()
                        senha_correta = res_senha.data[0].get('matricula') if res_senha.data else None
                        
                        if prof_sel in GESTORES or (senha_correta and str(senha_input).strip() == str(senha_correta).strip()):
                            for id_c in ids_para_cancelar:
                                supabase.table("reservas").update({"status": "Cancelada", "cancelado_por": prof_sel}).eq("id", id_c).execute()
                            st.success("✅ Cancelado!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("⚠️ Senha incorreta.")
        else:
            st.info("Nenhuma reserva ativa para este dia.")

    # =========================================================
    # ABA 6: ASSINATURA
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
                    verif = supabase.table("professores_matriculas").select("id").eq("professor", nome_prof.strip()).execute()
                    if verif.data:
                        supabase.table("professores_matriculas").update({"matricula": matricula_prof.strip()}).eq("professor", nome_prof.strip()).execute()
                    else:
                        supabase.table("professores_matriculas").insert({"professor": nome_prof.strip(), "matricula": matricula_prof.strip()}).execute()
                    st.success("✅ Salvo!")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro: {e}")