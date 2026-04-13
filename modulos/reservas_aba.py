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

    # Definição das Abas (AGORA COM 5 ABAS)
    aba_cal, aba_minhas, aba_nova, aba_cancelar, aba_assinatura = st.tabs([
        "🗓️ Calendário", "👩‍🏫 Minhas Reservas", "✍️ Nova Reserva", "❌ Gerenciar", "🔑 Assinatura"
    ])


    # =========================================================
    # ABA 1: CALENDÁRIO (MODO LISTA MENSAL CLEAN - FOCADO EM MOBILE)
    # =========================================================
    with aba_cal:
        
        # Apagamos o st.subheader("Visão Geral do Mês") para poupar espaço precioso na tela do celular
        
        with st.spinner("Carregando agenda mensal..."):
            try:
                # 1. BURLANDO O LIMITE DO SUPABASE
                todas_reservas_ativas = []
                inicio = 0
                tamanho_pagina = 1000
                
                while True:
                    res_pagina = supabase.table("reservas").select("*").eq("status", "Ativa").range(inicio, inicio + tamanho_pagina - 1).execute()
                    if not res_pagina.data:
                        break
                    todas_reservas_ativas.extend(res_pagina.data)
                    if len(res_pagina.data) < tamanho_pagina:
                        break
                    inicio += tamanho_pagina

                if todas_reservas_ativas:
                    # 2. AGRUPAMENTO INTELIGENTE
                    reservas_agrupadas = {}
                    
                    for r in todas_reservas_ativas:
                        prof = r.get('professor', 'Prof').strip()
                        espaco = r.get('espaco', 'Espaço')
                        aula = r.get('periodo', r.get('horario', r.get('aula', '')))
                        equipamentos = r.get('equipamentos', '')
                        raw_data = r.get('data_reserva') or r.get('data') or ""
                        
                        if not raw_data: continue
                        
                        data_str = str(raw_data).strip()
                        data_valida = None
                        try:
                            dt_obj = pd.to_datetime(data_str, format="%Y-%m-%d")
                            data_valida = dt_obj.strftime("%Y-%m-%d")
                        except ValueError:
                            try:
                                dt_obj = pd.to_datetime(data_str, format="%d/%m/%Y")
                                data_valida = dt_obj.strftime("%Y-%m-%d")
                            except ValueError:
                                try:
                                    dt_obj = pd.to_datetime(data_str, dayfirst=True)
                                    data_valida = dt_obj.strftime("%Y-%m-%d")
                                except: pass
                                    
                        if not data_valida: continue 

                        chave = (data_valida, prof)
                        if chave not in reservas_agrupadas:
                            reservas_agrupadas[chave] = []
                        
                        reservas_agrupadas[chave].append({
                            "espaco": espaco,
                            "aula": aula,
                            "equip": equipamentos
                        })

                    # 3. PREPARAÇÃO DOS EVENTOS (Com Títulos Compactos)
                    eventos = []
                    todos_profs = sorted(list(set(p for d, p in reservas_agrupadas.keys())))
                    mapa_cores = {prof: CORES_PROFESSORES[i % len(CORES_PROFESSORES)] for i, prof in enumerate(todos_profs)}
                    
                    for (data_fmt, prof), lista_detalhes in reservas_agrupadas.items():
                        resumo_espacos = {}
                        todos_equipamentos = set()
                        
                        for det in lista_detalhes:
                            esp = det["espaco"]
                            if esp not in resumo_espacos: resumo_espacos[esp] = []
                            
                            aula_curta = str(det["aula"]).replace(" Aula", "").strip()
                            if aula_curta: resumo_espacos[esp].append(aula_curta)
                                
                            eq_raw = str(det["equip"]).strip()
                            if eq_raw and eq_raw != "-":
                                for e in eq_raw.split(","): todos_equipamentos.add(e.strip())

                        partes_texto = []
                        for esp, aulas in resumo_espacos.items():
                            aulas_ordenadas = ", ".join(sorted(set(aulas)))
                            partes_texto.append(f"{esp} [{aulas_ordenadas}]" if aulas_ordenadas else f"{esp}")
                                
                        titulo_completo = f"{prof} | {' + '.join(partes_texto)}"
                        if todos_equipamentos:
                            titulo_completo += f" 🔌 {', '.join(sorted(todos_equipamentos))}"
                        
                        eventos.append({
                            "title": titulo_completo,
                            "start": data_fmt,
                            "backgroundColor": mapa_cores.get(prof, "#1f77b4"),
                            "borderColor": mapa_cores.get(prof, "#1f77b4"),
                            "allDay": True,
                        })
                    
                    # 4. CONFIGURAÇÃO CLEAN E DIRETA
                    calendar_options = {
                        "locale": "pt-br",
                        "initialView": "listMonth", # FIXADO EM LISTA MENSAL
                        "height": 650, # Altura boa para celular
                        "headerToolbar": {
                            "left": "prev,next", # Apenas setinhas
                            "center": "title",   # Título (ex: abril de 2026) centralizado
                            "right": "today"     # Botão pequeno "Hoje"
                        },
                        "buttonText": {
                            "today": "Hoje",
                        },
                        # Esconde a data alternativa redundante na lista para limpar a tela
                        "listDayAltFormat": False,
                    }
                    
                    # 5. MÁGICA CSS PARA DIMINUIR A FONTE NO CELULAR
                    custom_css = """
                    .fc-toolbar-title {
                        font-size: 1.1rem !important; 
                        text-transform: capitalize;
                        color: #333;
                    }
                    .fc-button {
                        padding: 0.2rem 0.5rem !important;
                        font-size: 0.85rem !important;
                    }
                    .fc-list-day-text {
                        font-size: 0.95rem !important;
                        font-weight: bold !important;
                    }
                    .fc-list-event-title {
                        font-size: 0.85rem !important;
                    }
                    .fc-list-event-time {
                        display: none !important; /* Esconde qualquer resquício do "all-day" */
                    }
                    """
                    
                    calendar(events=eventos, options=calendar_options, custom_css=custom_css)
                else:
                    st.info("Nenhuma reserva ativa para exibir na agenda.")
                    
            except Exception as e:
                st.error(f"Erro ao processar agenda: {e}")

    # =========================================================
    # ABA 3: MINHAS RESERVAS (INTERFACE LISTA CLEAN & MOBILE)
    # =========================================================
    with aba_minhas:
        st.info("Consulte sua agenda pessoal. As reservas canceladas aparecerão em vermelho.")
        
        prof_busca = st.selectbox("Selecione seu nome para ver sua agenda:", opcoes_professores, key="aba_minhas_prof")
        
        if prof_busca != "-- Selecione --":
            with st.spinner("Buscando sua agenda completa..."):
                try:
                    # 1. BURLANDO O LIMITE DO SUPABASE (Paginação)
                    todas_reservas_prof = []
                    inicio = 0
                    tamanho_pagina = 1000
                    
                    while True:
                        # Busca TUDO do professor (Ativas e Canceladas)
                        res_pagina = supabase.table("reservas").select("*").ilike("professor", f"%{prof_busca.strip()}%").range(inicio, inicio + tamanho_pagina - 1).execute()
                        if not res_pagina.data:
                            break
                        todas_reservas_prof.extend(res_pagina.data)
                        if len(res_pagina.data) < tamanho_pagina:
                            break
                        inicio += tamanho_pagina

                    if todas_reservas_prof:
                        # 2. AGRUPAMENTO POR DATA E STATUS
                        agrupamento_prof = {}
                        
                        for r in todas_reservas_prof:
                            status_bd = r.get("status", "Ativa")
                            espaco = r.get("espaco", "")
                            aula = r.get("periodo", r.get("horario", r.get("aula", "")))
                            equip = r.get("equipamentos", "")
                            raw_data = r.get("data_reserva") or r.get("data") or ""
                            
                            # Parser de data
                            data_str = str(raw_data).strip()
                            data_valida = None
                            try:
                                dt_obj = pd.to_datetime(data_str, format="%Y-%m-%d")
                                data_valida = dt_obj.strftime("%Y-%m-%d")
                            except ValueError:
                                try:
                                    dt_obj = pd.to_datetime(data_str, format="%d/%m/%Y")
                                    data_valida = dt_obj.strftime("%Y-%m-%d")
                                except ValueError:
                                    try:
                                        dt_obj = pd.to_datetime(data_str, dayfirst=True)
                                        data_valida = dt_obj.strftime("%Y-%m-%d")
                                    except: pass
                                        
                            if not data_valida: continue
                            
                            # Agrupa por Data e por Status (Ativa/Cancelada)
                            chave = (data_valida, status_bd)
                            if chave not in agrupamento_prof:
                                agrupamento_prof[chave] = []
                                
                            agrupamento_prof[chave].append({
                                "espaco": espaco,
                                "aula": aula,
                                "equip": equip
                            })
                            
                        # 3. CONSTRUINDO OS EVENTOS DA AGENDA
                        eventos_prof = []
                        
                        for (data_fmt, status), lista_detalhes in agrupamento_prof.items():
                            resumo_espacos = {}
                            todos_equipamentos = set()
                            
                            for det in lista_detalhes:
                                esp = det["espaco"]
                                if esp not in resumo_espacos: resumo_espacos[esp] = []
                                
                                aula_curta = str(det["aula"]).replace(" Aula", "").strip()
                                if aula_curta: resumo_espacos[esp].append(aula_curta)
                                    
                                eq_raw = str(det["equip"]).strip()
                                if eq_raw and eq_raw != "-":
                                    for e in eq_raw.split(","): todos_equipamentos.add(e.strip())

                            partes_texto = []
                            for esp, aulas in resumo_espacos.items():
                                aulas_ordenadas = ", ".join(sorted(set(aulas)))
                                partes_texto.append(f"{esp} [{aulas_ordenadas}]" if aulas_ordenadas else f"{esp}")
                                    
                            titulo_completo = " + ".join(partes_texto)
                            if todos_equipamentos:
                                titulo_completo += f" 🔌 {', '.join(sorted(todos_equipamentos))}"
                                
                            # Lógica Visual: Canceladas ficam vermelhas, Ativas ficam azuis
                            if status != "Ativa":
                                titulo_completo = f"❌ CANCELADA | {titulo_completo}"
                                cor = "#e53935" # Vermelho forte
                            else:
                                cor = "#1f77b4" # Azul padrão limpo
                                
                            eventos_prof.append({
                                "title": titulo_completo,
                                "start": data_fmt,
                                "backgroundColor": cor,
                                "borderColor": cor,
                                "allDay": True,
                            })

                        # 4. CONFIGURAÇÃO CLEAN DO CALENDÁRIO
                        calendar_options = {
                            "locale": "pt-br",
                            "initialView": "listMonth", 
                            "height": 650,
                            "headerToolbar": {
                                "left": "prev,next",
                                "center": "title",
                                "right": "today,listMonth,listYear" # <--- NOVIDADE AQUI
                            },
                            "buttonText": {
                                "today": "Hoje",
                                "listMonth": "Mês",
                                "listYear": "Ano" # Permite ver o ano todo de uma vez!
                            },
                            "listDayAltFormat": False,
                        }
                        
                        # 5. O MESMO CSS MÁGICO PARA CELULAR
                        custom_css = """
                        .fc-toolbar-title {
                            font-size: 1.1rem !important; 
                            text-transform: capitalize;
                            color: #333;
                        }
                        .fc-button {
                            padding: 0.2rem 0.5rem !important;
                            font-size: 0.85rem !important;
                        }
                        .fc-list-day-text {
                            font-size: 0.95rem !important;
                            font-weight: bold !important;
                        }
                        .fc-list-event-title {
                            font-size: 0.85rem !important;
                        }
                        .fc-list-event-time {
                            display: none !important;
                        }
                        """
                        
                        # A key precisa ser dinâmica para recarregar se mudar o professor
                        calendar(events=eventos_prof, options=calendar_options, custom_css=custom_css, key=f"cal_prof_{prof_busca}")
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