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
    # INÍCIO - ABA 2: LISTA DIÁRIA (COM COLUNA DE QUEM CANCELOU)
    # =========================================================
    with aba_lista:
        st.subheader("Visão Diária por Espaço")
        
        # Data no formato BR
        d_lista = st.date_input("Ver detalhes do dia:", value=datetime.date.today(), format="DD/MM/YYYY", key="d_lista")
        
        try:
            # Busca TODAS as reservas do dia (Ativas e Canceladas)
            res_lista = supabase.table("reservas").select("*").eq("data_reserva", str(d_lista)).execute()
            
            if res_lista.data:
                # Agrupa as reservas pelo nome do espaço
                reservas_por_espaco = {}
                for r in res_lista.data:
                    esp = r.get("espaco", "Sem Espaço")
                    if esp not in reservas_por_espaco:
                        reservas_por_espaco[esp] = []
                    reservas_por_espaco[esp].append(r)
                
                # Cria aquela barra "sanfona" (expander) para cada espaço
                for espaco, lista_res in reservas_por_espaco.items():
                    with st.expander(f"📍 {espaco} ({len(lista_res)} reservas)", expanded=True):
                        
                        # Prepara a lista que vai virar a tabela
                        dados_tabela = []
                        for r in lista_res:
                            status_bd = r.get("status", "Ativa")
                            
                            # Lógica para mostrar os ícones e quem cancelou
                            if status_bd == "Ativa":
                                situacao_icone = "🟢 Ativa"
                                quem_cancelou = "-" # Fica um tracinho se a aula está normal
                            else:
                                situacao_icone = "❌ Cancelada"
                                # Puxa o nome de quem cancelou (se não tiver, mostra 'Sistema')
                                quem_cancelou = r.get("cancelado_por", "Sistema")
                                
                            dados_tabela.append({
                                "Aula/Horário": r.get("periodo", ""),
                                "Professor": r.get("professor", ""),
                                "Equipamentos (Data Show/Som)": r.get("equipamentos", "") or "-",
                                "Situação": situacao_icone,
                                "Cancelado Por": quem_cancelou
                            })
                        
                        # Tenta ordenar da 1ª para a 9ª aula para ficar bonito
                        dados_tabela = sorted(dados_tabela, key=lambda x: x["Aula/Horário"])
                        
                        # Plota a tabela na tela ocupando a largura toda e escondendo o índice (0,1,2,3...)
                        st.dataframe(dados_tabela, use_container_width=True, hide_index=True)
                        
            else:
                st.info("📅 Nenhuma reserva encontrada para este dia.")
        except Exception as e:
            st.error(f"Erro ao carregar lista diária: {e}")
    # =========================================================
    # FIM - ABA 2
    # =========================================================
    
  # =========================================================
    # INÍCIO - ABA 3: NOVA RESERVA (COM LIMPEZA AUTOMÁTICA)
    # =========================================================
    with aba_nova:
        st.subheader("Agendar Espaço")
        
        espacos_filtrados = [e for e in espacos if e.lower() not in ['multimídia', 'multimidia']]
        
        st.write("**1. Escolha a Data e Horário:**")
        
        col_data, col_vazia = st.columns(2)
        with col_data:
            # Adicionamos 'key' para podermos limpar o campo depois
            d_res = st.date_input("Data:", value=datetime.date.today(), format="DD/MM/YYYY", key="aba3_data")
            
        lista_9_aulas = [
            "1ª Aula", "2ª Aula", "3ª Aula", "4ª Aula", "5ª Aula", 
            "6ª Aula", "7ª Aula", "8ª Aula", "9ª Aula"
        ]
        
        aulas_selecionadas = st.segmented_control(
            "Aulas:",
            options=lista_9_aulas,
            selection_mode="multi", 
            label_visibility="collapsed",
            key="aba3_aulas"
        )
        
        dia_todo = st.checkbox("Reservar o Dia Inteiro", key="aba3_diatodo")
        lista_final_aulas = lista_9_aulas if dia_todo else aulas_selecionadas

        st.divider()

        # =====================================================
        # LÓGICA DE CÁLCULO DE EQUIPAMENTOS DISPONÍVEIS
        # =====================================================
        estoque_total = {"Datashow": 5, "Aparelho de som": 3, "Microfones": 2}
        estoque_disp = {"Datashow": 5, "Aparelho de som": 3, "Microfones": 2}

        try:
            res_dia = supabase.table("reservas").select("periodo, equipamentos").eq("data_reserva", str(d_res)).eq("status", "Ativa").execute()
            
            if res_dia.data and lista_final_aulas:
                import re
                for equip in estoque_total.keys():
                    max_uso_concorrente = 0
                    
                    for aula in lista_final_aulas:
                        uso_nesta_aula = 0
                        reservas_aula = [r for r in res_dia.data if r.get('periodo') == aula]
                        
                        for r in reservas_aula:
                            eq_str = str(r.get('equipamentos', ''))
                            match = re.search(r'(\d+)x\s*' + equip[:4], eq_str, re.IGNORECASE)
                            if match:
                                uso_nesta_aula += int(match.group(1))
                            elif equip.lower() in eq_str.lower():
                                uso_nesta_aula += 1
                                
                        if uso_nesta_aula > max_uso_concorrente:
                            max_uso_concorrente = uso_nesta_aula
                            
                    disp = estoque_total[equip] - max_uso_concorrente
                    estoque_disp[equip] = max(0, disp)
        except Exception as e:
            st.error(f"Erro ao calcular disponibilidade: {e}")

        # =====================================================
        # CONTINUAÇÃO DO PREENCHIMENTO
        # =====================================================
        st.write("**2. Espaço e Equipamentos:**")
        c1, c2 = st.columns(2)
        with c1:
            p_res = st.selectbox("Professor:", opcoes_professores, key="aba3_prof")
            e_res = st.selectbox("Espaço:", ["-- Selecione --"] + espacos_filtrados, key="aba3_espaco")
            o_res = st.text_input("Observações:", key="aba3_obs")
            
        with c2:
            st.write("Equipamentos Disponíveis:")
            qtd_datashow = st.number_input(f"Datashow (Máx: {estoque_disp['Datashow']})", min_value=0, max_value=estoque_disp['Datashow'], value=0, key="aba3_qtd_data")
            qtd_som = st.number_input(f"Aparelho de som (Máx: {estoque_disp['Aparelho de som']})", min_value=0, max_value=estoque_disp['Aparelho de som'], value=0, key="aba3_qtd_som")
            qtd_mic = st.number_input(f"Microfones (Máx: {estoque_disp['Microfones']})", min_value=0, max_value=estoque_disp['Microfones'], value=0, key="aba3_qtd_mic")

        if st.button("💾 Confirmar Agendamento", type="primary"):
            if not lista_final_aulas:
                st.warning("⚠️ Selecione pelo menos uma aula.")
            elif p_res == "-- Selecione --" or e_res == "-- Selecione --":
                st.warning("⚠️ Selecione o Professor e o Espaço.")
            else:
                sucessos = 0
                conflitos = []
                
                lista_eq = []
                if qtd_datashow > 0: lista_eq.append(f"{qtd_datashow}x Datashow")
                if qtd_som > 0: lista_eq.append(f"{qtd_som}x Aparelho de som")
                if qtd_mic > 0: lista_eq.append(f"{qtd_mic}x Microfones")
                eq_str_final = ", ".join(lista_eq)
                
                for aula in lista_final_aulas:
                    conf = supabase.table("reservas").select("id").eq("data_reserva", str(d_res)).eq("periodo", aula).eq("espaco", e_res).eq("status", "Ativa").execute()
                    
                    if conf.data:
                        conflitos.append(aula)
                    else:
                        supabase.table("reservas").insert({
                            "data_reserva": str(d_res),
                            "periodo": aula,
                            "professor": p_res,
                            "espaco": e_res,
                            "equipamentos": eq_str_final,
                            "obs": o_res,
                            "status": "Ativa"
                        }).execute()
                        sucessos += 1
                
                if sucessos > 0:
                    st.success(f"✅ {sucessos} aula(s) reservada(s) com sucesso!")
                if conflitos:
                    st.error(f"🚨 Espaço ocupado na(s): {', '.join(conflitos)}")
                
                # SE DEU SUCESSO, LIMPA A MEMÓRIA DOS CAMPOS E REINICIA A TELA
                if sucessos > 0:
                    chaves_para_limpar = [
                        "aba3_data", "aba3_aulas", "aba3_diatodo", 
                        "aba3_prof", "aba3_espaco", "aba3_obs", 
                        "aba3_qtd_data", "aba3_qtd_som", "aba3_qtd_mic"
                    ]
                    for chave in chaves_para_limpar:
                        if chave in st.session_state:
                            del st.session_state[chave]
                            
                    st.rerun()
    # =========================================================
    # FIM - ABA 3
    # =========================================================


   # =========================================================
    # INÍCIO - ABA 4: GERENCIAR / CANCELAR (COM LIMPEZA AUTOMÁTICA)
    # =========================================================
    with aba_cancelar:
        st.subheader("Gerenciar Reservas")
        
        # O campo de data ganhou uma key específica
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
                
                # O multiselect ganhou uma key
                reservas_selecionadas = st.multiselect(
                    "Reservas encontradas:", 
                    options=list(opcoes_res.keys()),
                    placeholder="Clique aqui e escolha uma ou mais reservas...",
                    key="aba4_multiselect"
                )
                
                if reservas_selecionadas:
                    st.write("**2. O que deseja fazer?**")
                    
                    if len(reservas_selecionadas) == 1:
                        # Radio ganhou key
                        acao = st.radio("Escolha a ação:", ["❌ Cancelar a Reserva (Liberar Espaço e Equipamentos)", "✏️ Editar/Remover apenas Equipamentos"], label_visibility="collapsed", key="aba4_acao")
                        
                        res_unica = opcoes_res[reservas_selecionadas[0]]
                        equip_atual = res_unica.get('equipamentos', '')
                        if equip_atual is None: equip_atual = ""
                        
                        novo_equip = equip_atual
                        if "Editar" in acao:
                            # CORREÇÃO DO BUG: Adicionei a key "aba4_equip" para ele não puxar a data sem querer
                            novo_equip = st.text_input("Equipamentos desta reserva (apague o que não for mais usar):", value=str(equip_atual), key="aba4_equip")
                    else:
                        acao = st.radio("Ação em Lote:", ["❌ Cancelar Todas as Selecionadas", "🧹 Limpar Equipamentos de Todas (Devolver equipamentos)"], label_visibility="collapsed", key="aba4_acao")
                    
                    st.divider()
                    st.write("**3. Assinatura Eletrônica**")
                    
                    # Campo de senha ganhou key
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
                                    st.error(f"⛔ Sem permissão. Você não pode alterar reservas de outro professor: {', '.join(sem_permissao)}")
                                else:
                                    for sel in reservas_selecionadas:
                                        id_r = opcoes_res[sel]['id']
                                        
                                        if "Cancelar" in acao:
                                            supabase.table("reservas").update({"status": "Cancelada", "cancelado_por": user_nome}).eq("id", id_r).execute()
                                        elif "Editar" in acao:
                                            supabase.table("reservas").update({"equipamentos": novo_equip}).eq("id", id_r).execute()
                                        elif "Limpar" in acao:
                                            supabase.table("reservas").update({"equipamentos": ""}).eq("id", id_r).execute()
                                            
                                    st.success(f"✅ Operação realizada com sucesso por {user_nome}!")
                                    
                                    # --- O SEGREDO ESTÁ AQUI: LIMPEZA DA MEMÓRIA ---
                                    # Deleta todas as seleções da tela atual antes de reiniciar
                                    chaves_aba4 = ["aba4_multiselect", "aba4_acao", "aba4_equip", "aba4_senha"]
                                    for chave in chaves_aba4:
                                        if chave in st.session_state:
                                            del st.session_state[chave]
                                    
                                    # Reinicia a tela
                                    st.rerun()
                            else:
                                st.error("❌ Matrícula incorreta ou não cadastrada.")
            else:
                st.info("Nenhuma reserva ativa encontrada para esta data.")
        except Exception as e:
            st.error(f"Erro ao carregar reservas: {e}")
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
