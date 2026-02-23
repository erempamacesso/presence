import streamlit as st
import pandas as pd
import datetime
import re  # <--- ERRO CORRIGIDO: Importação necessária para o cálculo de estoque
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
    # INÍCIO - ABA 3: NOVA RESERVA (PILLS + ESTOQUE + SALA)
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
        col_eq1, col_eq2, col_eq3 = st.columns(3)
        with col_eq1:
            qtd_datashow = st.number_input("🎥 Datashow (Máx 5)", min_value=0, max_value=5, value=0, key="aba3_qtd_data")
        with col_eq2:
            qtd_som = st.number_input("🔊 Caixa de Som (Máx 3)", min_value=0, max_value=3, value=0, key="aba3_qtd_som")
        with col_eq3:
            qtd_mic = st.number_input("🎤 Microfone (Máx 2)", min_value=0, max_value=2, value=0, key="aba3_qtd_mic")
            
        obs = st.text_input("Observações:", key="aba3_obs")
        
        if st.button("💾 Confirmar Reserva", type="primary"):
            if not aulas_selecionadas:
                st.warning("⚠️ Selecione pelo menos uma aula clicando nos botões azuis.")
            elif professor == "-- Selecione --":
                st.warning("⚠️ Selecione o professor.")
            elif espaco == "-- Selecione --" and not usar_na_sala:
                st.warning("⚠️ Selecione um espaço ou marque 'Usarei na sala de aula'.")
            elif qtd_datashow == 0 and qtd_som == 0 and qtd_mic == 0 and usar_na_sala:
                st.warning("⚠️ Se vai usar na própria sala, você precisa selecionar pelo menos um equipamento!")
            else:
                sucesso_total = True
                aulas_com_conflito_espaco = []
                aulas_sem_estoque = []
                
                equip_list = []
                if qtd_datashow > 0: equip_list.append(f"{qtd_datashow}x Datashow")
                if qtd_som > 0: equip_list.append(f"{qtd_som}x Som")
                if qtd_mic > 0: equip_list.append(f"{qtd_mic}x Microfone")
                equipamentos_texto = ", ".join(equip_list)
                
                for aula in aulas_selecionadas:
                    pode_salvar = True
                    
                    if espaco != "Sala de Aula":
                        conflito_espaco = supabase.table("reservas").select("*").eq("data_reserva", str(data_res)).eq("periodo", aula).eq("espaco", espaco).eq("status", "Ativa").execute()
                        if conflito_espaco.data:
                            aulas_com_conflito_espaco.append(aula)
                            pode_salvar = False
                            sucesso_total = False
                    
                    if pode_salvar and (qtd_datashow > 0 or qtd_som > 0 or qtd_mic > 0):
                        todas_reservas_aula = supabase.table("reservas").select("equipamentos").eq("data_reserva", str(data_res)).eq("periodo", aula).eq("status", "Ativa").execute()
                        
                        uso_atual = {"Datashow": 0, "Som": 0, "Microfone": 0}
                        
                        for r in todas_reservas_aula.data:
                            eq_str = r.get("equipamentos", "")
                            if eq_str:
                                # Aqui o 're' importado é utilizado
                                matches = re.findall(r"(\d+)x\s*(Datashow|Som|Microfone)", str(eq_str), re.IGNORECASE)
                                for qtd, item in matches:
                                    item_norm = item.capitalize()
                                    if item_norm in uso_atual:
                                        uso_atual[item_norm] += int(qtd)
                        
                        if (qtd_datashow + uso_atual["Datashow"]) > ESTOQUE["Datashow"] or \
                           (qtd_som + uso_atual["Som"]) > ESTOQUE["Som"] or \
                           (qtd_mic + uso_atual["Microfone"]) > ESTOQUE["Microfone"]:
                            
                            aulas_sem_estoque.append(aula)
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
                
                if aulas_com_conflito_espaco:
                    st.error(f"❌ O espaço '{espaco}' já está reservado nestas aulas: {', '.join(aulas_com_conflito_espaco)}.")
                
                if aulas_sem_estoque:
                    st.error(f"⚠️ Equipamento insuficiente no estoque para as aulas: {', '.join(aulas_sem_estoque)}.")
                
                if sucesso_total:
                    st.success("✅ Reserva(s) realizada(s) com sucesso!")
                    chaves_para_limpar = ["aba3_data", "aba3_aulas", "aba3_prof", "aba3_usar_sala", "aba3_espaco", "aba3_qtd_data", "aba3_qtd_som", "aba3_qtd_mic", "aba3_obs"]
                    for chave in chaves_para_limpar:
                        if chave in st.session_state:
                            del st.session_state[chave]
                    st.rerun()

    # =========================================================
    # INÍCIO - ABA 4: GERENCIAR / CANCELAR
    # =========================================================
    with aba_cancelar:
        st.subheader("Gerenciar Reservas")
        d_can = st.date_input("Data da reserva que deseja alterar:", value=datetime.date.today(), format="DD/MM/YYYY", key="aba4_data")
        
        try:
            res_at = supabase.table("reservas").select("*").eq("data_reserva", str(d_can)).eq("status", "Ativa").execute()
            
            if res_at.data:
                opcoes_res = {}
                for r in res_at.data:
                    eq_txt = f" | 🛠️ {r['equipamentos']}" if r.get('equipamentos') and str(r.get('equipamentos')).strip() else ""
                    texto = f"{r.get('periodo', 'S/H')} - {r.get('espaco', '---')} ({r.get('professor', '---')}){eq_txt}"
                    opcoes_res[texto] = r

                st.write("**1. Selecione a(s) reserva(s) que deseja alterar:**")
                reservas_selecionadas = st.multiselect(
                    "Reservas encontradas:", 
                    options=list(opcoes_res.keys()),
                    placeholder="Clique aqui e escolha uma ou mais reservas...",
                    key="aba4_multiselect"
                )
                
                if reservas_selecionadas:
                    st.write("**2. O que deseja fazer?**")
                    if len(reservas_selecionadas) == 1:
                        acao = st.radio("Escolha a ação:", ["❌ Cancelar a Reserva (Liberar Espaço e Equipamentos)", "✏️ Editar/Remover apenas Equipamentos"], label_visibility="collapsed", key="aba4_acao")
                        res_unica = opcoes_res[reservas_selecionadas[0]]
                        equip_atual = res_unica.get('equipamentos', '') or ""
                        novo_equip = equip_atual
                        if "Editar" in acao:
                            novo_equip = st.text_input("Equipamentos desta reserva:", value=str(equip_atual), key="aba4_equip")
                    else:
                        acao = st.radio("Ação em Lote:", ["❌ Cancelar Todas as Selecionadas", "🧹 Limpar Equipamentos de Todas"], label_visibility="collapsed", key="aba4_acao")
                    
                    st.divider()
                    st.write("**3. Assinatura Eletrônica**")
                    st.warning("🔒 **AVISO DE PRIVACIDADE E SEGURANÇA:** Sua Matrícula funciona como a sua senha pessoal.")
                    senha = st.text_input("Sua Matrícula (Senha):", type="password", key="aba4_senha")
                    
                    if st.button("💾 Confirmar Ação", type="primary"):
                        if not senha:
                            st.warning("⚠️ Digite sua matrícula para confirmar.")
                        else:
                            verif = supabase.table("professores_matriculas").select("professor").eq("matricula", senha).execute()
                            if verif.data:
                                user_nome = verif.data[0]['professor']
                                sem_permissao = []
                                for sel in reservas_selecionadas:
                                    res_dados = opcoes_res[sel]
                                    if user_nome not in GESTORES and user_nome != res_dados['professor']:
                                        sem_permissao.append(res_dados.get('periodo', 'Aula Indefinida'))
                                
                                if sem_permissao:
                                    st.error(f"⛔ Sem permissão para alterar reservas de outro professor: {', '.join(sem_permissao)}")
                                else:
                                    for sel in reservas_selecionadas:
                                        id_r = opcoes_res[sel]['id']
                                        if "Cancelar" in acao:
                                            supabase.table("reservas").update({"status": "Cancelada", "cancelado_por": user_nome}).eq("id", id_r).execute()
                                        elif "Editar" in acao:
                                            supabase.table("reservas").update({"equipamentos": novo_equip}).eq("id", id_r).execute()
                                        elif "Limpar" in acao:
                                            supabase.table("reservas").update({"equipamentos": ""}).eq("id", id_r).execute()
                                    st.success(f"✅ Operação realizada por {user_nome}!")
                                    st.rerun()
                            else:
                                st.error("❌ Matrícula incorreta.")
            else:
                st.info("Nenhuma reserva ativa encontrada para esta data.")
        except Exception as e:
            st.error(f"Erro ao carregar reservas: {e}")

    # =========================================================
    # INÍCIO - ABA 5: ASSINATURA
    # =========================================================
    with aba_assinatura:
        st.subheader("Cadastro de Assinatura Eletrônica")
        st.warning("🔒 **AVISO DE PRIVACIDADE E SEGURANÇA:** Sua Matrícula funciona como senha.")
        nome_prof = st.selectbox("Seu Nome:", opcoes_professores, key="aba5_nome")
        matricula_prof = st.text_input("Sua Matrícula (Senha):", type="password", key="aba5_matricula")
        
        if st.button("💾 Salvar Assinatura", type="primary"):
            if nome_prof == "-- Selecione --" or not matricula_prof:
                st.error("⚠️ Preencha todos os campos.")
            else:
                try:
                    verif = supabase.table("professores_matriculas").select("*").eq("professor", nome_prof).execute()
                    if verif.data:
                        supabase.table("professores_matriculas").update({"matricula": matricula_prof}).eq("professor", nome_prof).execute()
                    else:
                        supabase.table("professores_matriculas").insert({"professor": nome_prof, "matricula": matricula_prof}).execute()
                    st.success(f"✅ Assinatura de {nome_prof} cadastrada!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar assinatura: {e}")
