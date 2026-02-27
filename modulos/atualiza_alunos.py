# ==========================================
    # ABA 1: UPLOAD DE MÚLTIPLOS CSVS OU EXCEL
    # ==========================================
    with aba_planilha:
        st.subheader("Importação e Atualização em Massa")
        st.info("O sistema fará uma varredura cruzando as planilhas com o banco atual e emitirá um relatório das mudanças.")
        
        # MUDANÇA AQUI: accept_multiple_files=True permite selecionar os 13 arquivos de uma vez
        arquivos = st.file_uploader("Suba as planilhas da secretaria (.csv ou .xlsx)", type=["xlsx", "csv"], accept_multiple_files=True)
        
        if arquivos:
            if st.button("🚀 Iniciar Sincronização e Gerar Relatório", type="primary"):
                with st.spinner("Analisando dados e cruzando informações..."):
                    try:
                        res_banco = supabase.table("alunos").select("nome, turma").execute()
                        banco_dict = {str(item['nome']).upper().strip(): item.get('turma', 'Sem Turma') for item in res_banco.data}
                        
                        dados_upsert = []
                        relatorio_inseridos = []
                        relatorio_transferidos = []
                        nomes_processados_nesta_leva = set()
                        duplicados_planilha = 0
                        
                        barra = st.progress(0)
                        
                        # Loop que passa por cada um dos 13 arquivos
                        for i, arquivo in enumerate(arquivos):
                            # Extrai a turma do nome do arquivo (ex: "...EM45-1IA.csv" -> "1º A")
                            nome_arquivo = arquivo.name.replace('.csv', '').replace('.xlsx', '')
                            sigla = nome_arquivo.split('-')[-1].strip()
                            
                            if len(sigla) >= 2:
                                turma_nova = f"{sigla[0]}º {sigla[-1]}"
                            else:
                                turma_nova = sigla
                                
                            # Lê o arquivo dependendo do formato
                            if arquivo.name.endswith('.csv'):
                                df = pd.read_csv(arquivo)
                            else:
                                df = pd.read_excel(arquivo)
                            
                            for _, linha in df.iterrows():
                                if pd.isna(linha.get('Nome')):
                                    continue
                                    
                                nome_limpo = str(linha['Nome']).upper().strip()
                                
                                if nome_limpo in nomes_processados_nesta_leva:
                                    duplicados_planilha += 1
                                    continue
                                nomes_processados_nesta_leva.add(nome_limpo)
                                
                                if nome_limpo not in banco_dict:
                                    relatorio_inseridos.append({"Nome": nome_limpo, "Turma Atribuída": turma_nova})
                                else:
                                    turma_antiga = banco_dict[nome_limpo]
                                    if turma_antiga != turma_nova:
                                        relatorio_transferidos.append({
                                            "Nome": nome_limpo,
                                            "Turma Antiga": turma_antiga,
                                            "Nova Turma": turma_nova
                                        })
                                
                                try:
                                    dt_nasc = pd.to_datetime(linha['Data de nascimento'], dayfirst=True).strftime('%Y-%m-%d')
                                except:
                                    dt_nasc = None
                                
                                sexo = str(linha.get('Sexo', '')).upper().strip()
                                sexo = sexo if sexo in ['M', 'F'] else None

                                dados_upsert.append({
                                    "nome": nome_limpo,
                                    "turma": turma_nova,
                                    "data_nascimento": dt_nasc,
                                    "sexo": sexo
                                })
                            
                            barra.progress((i + 1) / len(arquivos))
                        
                        # Grava no banco e exibe relatório
                        if dados_upsert:
                            supabase.table("alunos").upsert(dados_upsert, on_conflict="nome").execute()
                        
                        st.divider()
                        st.subheader("📋 Relatório de Sincronização")
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Novos Alunos Cadastrados", len(relatorio_inseridos))
                        c2.metric("Mudanças de Sala", len(relatorio_transferidos))
                        c3.metric("Total Processado", len(dados_upsert))
                        
                        if duplicados_planilha > 0:
                            st.warning(f"⚠️ **{duplicados_planilha} ocorrências duplicadas** ignoradas.")
                        
                        st.success("O Banco de Dados foi atualizado com sucesso!")
                        
                        if relatorio_inseridos:
                            with st.expander(f"➕ Ver lista de {len(relatorio_inseridos)} novos alunos"):
                                st.dataframe(pd.DataFrame(relatorio_inseridos), use_container_width=True, hide_index=True)
                        if relatorio_transferidos:
                            with st.expander(f"🔄 Ver lista de {len(relatorio_transferidos)} alunos transferidos"):
                                st.dataframe(pd.DataFrame(relatorio_transferidos), use_container_width=True, hide_index=True)

                    except Exception as e:
                        st.error(f"❌ Ocorreu um erro: {e}")
