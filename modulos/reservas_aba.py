# =========================================================
    # ABA 3: NOVA RESERVA (PILLS + ESTOQUE + SALA)
    # =========================================================
    with aba_nova:
        st.subheader("Agendar Espaço / Equipamento")
        
        # Configuração de estoque máximo
        ESTOQUE = {"Datashow": 5, "Som": 3, "Microfone": 2}
        
        # 1. ESCOLHA DE DATA E HORÁRIO
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
        
        # 2. ESCOLHA DE PROFESSOR E ESPAÇO
        st.write("**2. Dados da Reserva:**")
        col1, col2 = st.columns(2)
        
        with col1:
            # O campo do professor NÃO será limpo no sucesso
            professor = st.selectbox("Professor:", opcoes_professores, key="aba3_prof")
            usar_na_sala = st.checkbox("Usarei na sala de aula (Apenas Equipamentos)", key="aba3_usar_sala")
            
        with col2:
            if usar_na_sala:
                espaco = "Sala de Aula"
                st.text_input("Espaço:", value="Sala de Aula (Própria)", disabled=True, key="aba3_espaco_disabled")
            else:
                espaco = st.selectbox("Espaço:", ["-- Selecione --", "Auditório", "Laboratório", "Biblioteca", "Quadra"], key="aba3_espaco")
                
        # 3. ESCOLHA DOS EQUIPAMENTOS
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
                st.warning("⚠️ Selecione pelo menos uma aula nos botões azuis.")
            elif professor == "-- Selecione --":
                st.warning("⚠️ Selecione o professor.")
            elif espaco == "-- Selecione --" and not usar_na_sala:
                st.warning("⚠️ Selecione um espaço ou marque 'Usarei na sala de aula'.")
            elif qtd_datashow == 0 and qtd_som == 0 and qtd_mic == 0 and usar_na_sala:
                st.warning("⚠️ Selecione pelo menos um equipamento para usar na sala.")
            else:
                sucesso_total = True
                aulas_com_conflito_espaco = []
                aulas_sem_estoque = []
                
                # Formata texto dos equipamentos para o banco
                equip_list = []
                if qtd_datashow > 0: equip_list.append(f"{qtd_datashow}x Datashow")
                if qtd_som > 0: equip_list.append(f"{qtd_som}x Som")
                if qtd_mic > 0: equip_list.append(f"{qtd_mic}x Microfone")
                equipamentos_texto = ", ".join(equip_list)
                
                # Loop para processar cada aula selecionada
                for aula in aulas_selecionadas:
                    pode_salvar = True
                    
                    # Verificação de Conflito de Espaço (se não for sala comum)
                    if espaco != "Sala de Aula":
                        conflito = supabase.table("reservas").select("*").eq("data_reserva", str(data_res)).eq("periodo", aula).eq("espaco", espaco).eq("status", "Ativa").execute()
                        if conflito.data:
                            aulas_com_conflito_espaco.append(aula)
                            pode_salvar = False
                            sucesso_total = False
                    
                    # Verificação de Estoque de Equipamentos
                    if pode_salvar and (qtd_datashow > 0 or qtd_som > 0 or qtd_mic > 0):
                        res_estoque = supabase.table("reservas").select("equipamentos").eq("data_reserva", str(data_res)).eq("periodo", aula).eq("status", "Ativa").execute()
                        uso_atual = {"Datashow": 0, "Som": 0, "Microfone": 0}
                        
                        for r in res_estoque.data:
                            eq_str = r.get("equipamentos", "")
                            if eq_str:
                                matches = re.findall(r"(\d+)x\s*(Datashow|Som|Microfone)", str(eq_str), re.IGNORECASE)
                                for qtd, item in matches:
                                    uso_atual[item.capitalize()] += int(qtd)
                        
                        if (qtd_datashow + uso_atual["Datashow"]) > ESTOQUE["Datashow"] or \
                           (qtd_som + uso_atual["Som"]) > ESTOQUE["Som"] or \
                           (qtd_mic + uso_atual["Microfone"]) > ESTOQUE["Microfone"]:
                            aulas_sem_estoque.append(aula)
                            pode_salvar = False
                            sucesso_total = False
                    
                    # Gravação no Banco de Dados
                    if pode_salvar:
                        try:
                            supabase.table("reservas").insert({
                                "data_reserva": str(data_res), "periodo": aula, "espaco": espaco,
                                "professor": professor, "equipamentos": equipamentos_texto,
                                "observacoes": obs, "status": "Ativa"
                            }).execute()
                        except Exception as e:
                            st.error(f"Erro ao salvar a {aula}: {e}")
                            sucesso_total = False
                
                # Alertas de erro/conflito
                if aulas_com_conflito_espaco:
                    st.error(f"❌ Espaço ocupado na(s): {', '.join(aulas_com_conflito_espaco)}")
                if aulas_sem_estoque:
                    st.error(f"⚠️ Sem estoque de equipamentos na(s): {', '.join(aulas_sem_estoque)}")
                
                # --- LÓGICA DE SUCESSO E LIMPEZA (CABELINHO DE SAPO) ---
                if sucesso_total:
                    st.success(f"✅ Reserva realizada com sucesso para {professor}!")
                    
                    # Definimos as chaves que devem voltar ao estado inicial (Exceto Professor e Data)
                    chaves_para_limpar = [
                        "aba3_aulas", "aba3_usar_sala", "aba3_espaco", 
                        "aba3_qtd_data", "aba3_qtd_som", "aba3_qtd_mic", "aba3_obs"
                    ]
                    
                    for chave in chaves_para_limpar:
                        if chave in st.session_state:
                            # Reseta listas (aulas)
                            if chave == "aba3_aulas":
                                st.session_state[chave] = []
                            # Reseta números para 0
                            elif "qtd" in chave:
                                st.session_state[chave] = 0
                            # Reseta checkbox para Falso
                            elif "usar_sala" in chave:
                                st.session_state[chave] = False
                            # Remove os demais para resetar o widget
                            else:
                                del st.session_state[chave]
                    
                    # Recarrega a página com o estado limpo (mas mantendo o professor)
                    st.rerun()
