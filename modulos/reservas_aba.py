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
    # INÍCIO - ABA 3: NOVA RESERVA (PILLS + CHECKBOX "SALA DE AULA")
    # =========================================================
    with aba_nova:
        st.subheader("Agendar Espaço / Equipamento")
        
        # 1. ESCOLHA DE DATA E HORÁRIO (AULAS EM FORMATO PILL)
        st.write("**1. Escolha a Data e Horário:**")
        col_data, col_vazia = st.columns(2)
        with col_data:
            data_res = st.date_input("Data:", value=datetime.date.today(), format="DD/MM/YYYY", key="aba3_data")
        
        lista_9_aulas = ["1ª Aula", "2ª Aula", "3ª Aula", "4ª Aula", "5ª Aula", "6ª Aula", "7ª Aula", "8ª Aula", "9ª Aula"]
        
        st.write("**Selecione a(s) Aula(s):** *(Toque para selecionar várias)*")
        # --- OS BOTÕES PILLS ESTÃO DE VOLTA AQUI ---
        aulas_selecionadas = st.segmented_control(
            "Aulas:", 
            options=lista_9_aulas, 
            selection_mode="multi",
            label_visibility="collapsed",
            key="aba3_aulas"
        )
        
        st.divider()
        
        # 2. ESCOLHA DE PROFESSOR, ESPAÇO E EQUIPAMENTOS
        st.write("**2. Dados da Reserva:**")
        col1, col2 = st.columns(2)
        
        with col1:
            professor = st.selectbox("Professor:", opcoes_professores, key="aba3_prof")
            
            # --- O NOVO CHECKBOX PARA A SALA DE AULA ---
            usar_na_sala = st.checkbox("Usarei na sala de aula (Apenas Equipamentos)", key="aba3_usar_sala")
            
        with col2:
            if usar_na_sala:
                # Se marcou, o espaço vira automaticamente "Sala de Aula" e o campo fica cinza (desativado)
                espaco = "Sala de Aula"
                st.text_input("Espaço:", value="Sala de Aula (Própria)", disabled=True, key="aba3_espaco_disabled")
            else:
                # Se não marcou, mostra a lista normal de espaços (sem Multimídia)
                espaco = st.selectbox("Espaço:", ["-- Selecione --", "Auditório", "Laboratório", "Biblioteca", "Quadra"], key="aba3_espaco")
                
            equipamentos = st.text_input("Equipamentos:", placeholder="Ex: 1x Data show", key="aba3_equip")
            
        obs = st.text_input("Observações:", key="aba3_obs")
        
        st.write("") # Dá um espacinho visual
        
        if st.button("💾 Confirmar Reserva", type="primary"):
            # Validações básicas
            if not aulas_selecionadas:
                st.warning("⚠️ Selecione pelo menos uma aula clicando nos botões azuis.")
            elif professor == "-- Selecione --":
                st.warning("⚠️ Selecione o professor.")
            elif espaco == "-- Selecione --" and not usar_na_sala:
                st.warning("⚠️ Selecione um espaço ou marque 'Usarei na sala de aula'.")
            else:
                sucesso_total = True
                aulas_com_conflito = []
                
                # Para cada aula que o professor selecionou nos botões
                for aula in aulas_selecionadas:
                    
                    # --- A MÁGICA DO CONFLITO: Ignora se for na própria sala ---
                    if espaco != "Sala de Aula":
                        conflito = supabase.table("reservas").select("*").eq("data_reserva", str(data_res)).eq("periodo", aula).eq("espaco", espaco).eq("status", "Ativa").execute()
                        
                        if conflito.data:
                            aulas_com_conflito.append(aula)
                            sucesso_total = False
                            continue # Pula para a próxima aula
                    
                    # Se passou pelo conflito (ou se é na própria sala), salva a reserva!
                    try:
                        dados_insert = {
                            "data_reserva": str(data_res),
                            "periodo": aula,
                            "espaco": espaco,
                            "professor": professor,
                            "equipamentos": equipamentos,
                            "obs": obs, # Certifique-se de que o nome no seu banco é "obs" ou "observacoes"
                            "status": "Ativa"
                        }
                        supabase.table("reservas").insert(dados_insert).execute()
                    except Exception as e:
                        st.error(f"Erro ao salvar a {aula}: {e}")
                        sucesso_total = False
                
                # Mensagens finais
                if aulas_com_conflito:
                    st.error(f"❌ O espaço '{espaco}' já está reservado para as aulas: {', '.join(aulas_com_conflito)}.")
                
                if sucesso_total:
                    st.success("✅ Reserva(s) realizada(s) com sucesso!")
                    
                    # --- LIMPEZA DE MEMÓRIA PARA REINICIAR A TELA ---
                    chaves_para_limpar = ["aba3_data", "aba3_aulas", "aba3_prof", "aba3_usar_sala", "aba3_espaco", "aba3_equip", "aba3_obs"]
                    for chave in chaves_para_limpar:
                        if chave in st.session_state:
                            del st.session_state[chave]
                            
                    st.rerun()
    # =========================================================
    # FIM - ABA 3
    # =========================================================

   # =========================================================
    # INÍCIO - ABA 4: GERENCIAR / CANCELAR (COM AVISO DE PRIVACIDADE)
    # =========================================================
    with aba_cancelar:
        st.subheader("Gerenciar Reservas")
        
        # O campo de data com key específica
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
                
                # Multiselect para escolher várias reservas
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
                        equip_atual = res_unica.get('equipamentos', '')
                        if equip_atual is None: equip_atual = ""
                        
                        novo_equip = equip_atual
                        if "Editar" in acao:
                            novo_equip = st.text_input("Equipamentos desta reserva (apague o que não for mais usar):", value=str(equip_atual), key="aba4_equip")
                    else:
                        acao = st.radio("Ação em Lote:", ["❌ Cancelar Todas as Selecionadas", "🧹 Limpar Equipamentos de Todas (Devolver equipamentos)"], label_visibility="collapsed", key="aba4_acao")
                    
                    st.divider()
                    st.write("**3. Assinatura Eletrônica**")
                    
                    # --- AVISO GRITANTE DE SEGURANÇA ADICIONADO AQUI ---
                    st.warning("🔒 **AVISO DE PRIVACIDADE E SEGURANÇA:**\n\nSua **Matrícula** funciona como a sua **senha pessoal** neste sistema. Fique tranquilo(a): ela **NÃO será exposta** em nenhuma tela pública, relatório ou tabela. \n\nSua única finalidade é garantir a segurança da sua agenda, permitindo que **apenas você** (ou a gestão da escola) possa cancelar ou alterar as reservas feitas em seu nome.")
                    
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
                                    
                                    # Limpeza da memória
                                    chaves_aba4 = ["aba4_multiselect", "aba4_acao", "aba4_equip", "aba4_senha"]
                                    for chave in chaves_aba4:
                                        if chave in st.session_state:
                                            del st.session_state[chave]
                                    
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
    # INÍCIO - ABA 5: ASSINATURA (COM AVISO DE PRIVACIDADE)
    # =========================================================
    with aba_assinatura:
        st.subheader("Cadastro de Assinatura Eletrônica")
        
        # --- AVISO GRITANTE DE SEGURANÇA E PRIVACIDADE ---
        st.warning("🔒 **AVISO DE PRIVACIDADE E SEGURANÇA:**\n\nSua **Matrícula** funciona como a sua **senha pessoal** neste sistema. Fique tranquilo(a): ela **NÃO será exposta** em nenhuma tela pública, relatório ou tabela. \n\nSua única finalidade é garantir a segurança da sua agenda, permitindo que **apenas você** (ou a gestão da escola) possa cancelar ou alterar as reservas feitas em seu nome.")
        
        st.write("Preencha os dados abaixo para registrar sua assinatura no sistema:")
        
        # Adicionando 'key' aos campos para podermos limpar a tela depois
        nome_prof = st.selectbox("Seu Nome:", opcoes_professores, key="aba5_nome")
        matricula_prof = st.text_input("Sua Matrícula (Senha):", type="password", key="aba5_matricula")
        
        if st.button("💾 Salvar Assinatura", type="primary"):
            if nome_prof == "-- Selecione --":
                st.error("⚠️ Selecione seu nome na lista.")
            elif not matricula_prof:
                st.error("⚠️ Digite sua matrícula.")
            else:
                try:
                    # Verifica se o professor já tem senha cadastrada
                    verif = supabase.table("professores_matriculas").select("*").eq("professor", nome_prof).execute()
                    
                    if verif.data:
                        # Se já tem, ATUALIZA a senha
                        supabase.table("professores_matriculas").update({"matricula": matricula_prof}).eq("professor", nome_prof).execute()
                    else:
                        # Se não tem, CRIA uma nova
                        supabase.table("professores_matriculas").insert({"professor": nome_prof, "matricula": matricula_prof}).execute()
                        
                    st.success(f"✅ Assinatura de {nome_prof} cadastrada/atualizada com sucesso!")
                    
                    # --- LIMPEZA DE MEMÓRIA PARA PROTEGER OS DADOS ---
                    chaves_aba5 = ["aba5_nome", "aba5_matricula"]
                    for chave in chaves_aba5:
                        if chave in st.session_state:
                            del st.session_state[chave]
                            
                    # Reinicia a tela para apagar os campos visuais
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Erro ao salvar assinatura: {e}")
    # =========================================================
    # FIM - ABA 5
    # =========================================================
