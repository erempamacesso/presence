import streamlit as st
import pandas as pd

def exibir_importacao(supabase):
    st.title("📤 Gestão e Importação de Dados")
    
    aba_planilha, aba_texto = st.tabs(["📁 Upload do Excel Oficial", "📝 Colar Lista Rápida (Apenas Nomes)"])

    # ==========================================
    # ABA 1: UPLOAD DO EXCEL COM RELATÓRIO DE DIFF
    # ==========================================
    with aba_planilha:
        st.subheader("Importação e Atualização em Massa (Excel)")
        st.info("O sistema fará uma varredura cruzando o Excel com o banco atual e emitirá um relatório das mudanças.")
        
        arquivo = st.file_uploader("Suba a planilha oficial da secretaria (.xlsx)", type=["xlsx"])
        
        if arquivo:
            if st.button("🚀 Iniciar Sincronização e Gerar Relatório", type="primary"):
                with st.spinner("Analisando dados e cruzando informações..."):
                    try:
                        # 1. Puxa o estado atual do banco para poder comparar
                        res_banco = supabase.table("alunos").select("nome, turma").execute()
                        banco_dict = {str(item['nome']).upper().strip(): item.get('turma', 'Sem Turma') for item in res_banco.data}
                        
                        xl = pd.ExcelFile(arquivo)
                        abas_turmas = [a for a in xl.sheet_names if "EM45" in a]
                        
                        if not abas_turmas:
                            st.error("Nenhuma aba com o padrão 'EM45' foi encontrada no arquivo.")
                        else:
                            dados_upsert = []
                            
                            # Variáveis para o Relatório
                            relatorio_inseridos = []
                            relatorio_transferidos = []
                            nomes_processados_neste_excel = set()
                            duplicados_excel = 0
                            
                            barra = st.progress(0)
                            
                            # 2. Varredura do Excel
                            for i, nome_aba in enumerate(abas_turmas):
                                # Extrai a turma
                                sigla = str(nome_aba).split('-')[-1].strip()
                                if len(sigla) >= 2:
                                    turma_nova = f"{sigla[0]}º {sigla[-1]}"
                                else:
                                    turma_nova = nome_aba
                                    
                                df = pd.read_excel(xl, sheet_name=nome_aba)
                                
                                for _, linha in df.iterrows():
                                    if pd.isna(linha.get('Nome')):
                                        continue
                                        
                                    nome_limpo = str(linha['Nome']).upper().strip()
                                    
                                    # Evita que o mesmo aluno seja processado duas vezes se estiver duplicado no Excel
                                    if nome_limpo in nomes_processados_neste_excel:
                                        duplicados_excel += 1
                                        continue
                                    nomes_processados_neste_excel.add(nome_limpo)
                                    
                                    # LÓGICA DE AUDITORIA (O Relatório)
                                    if nome_limpo not in banco_dict:
                                        # É um aluno inédito
                                        relatorio_inseridos.append({"Nome": nome_limpo, "Turma Atribuída": turma_nova})
                                    else:
                                        # O aluno já existe. A turma mudou?
                                        turma_antiga = banco_dict[nome_limpo]
                                        if turma_antiga != turma_nova:
                                            relatorio_transferidos.append({
                                                "Nome": nome_limpo,
                                                "Turma Antiga": turma_antiga,
                                                "Nova Turma": turma_nova
                                            })
                                    
                                    # Tratamento de datas e sexo
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
                                
                                barra.progress((i + 1) / len(abas_turmas))
                            
                            # 3. Executa a gravação no banco de fato
                            if dados_upsert:
                                supabase.table("alunos").upsert(dados_upsert, on_conflict="nome").execute()
                            
                            # 4. EXIBIÇÃO DO RELATÓRIO FINAL
                            st.divider()
                            st.subheader("📋 Relatório de Sincronização")
                            
                            # Métricas visuais
                            c1, c2, c3 = st.columns(3)
                            c1.metric("Novos Alunos Cadastrados", len(relatorio_inseridos))
                            c2.metric("Mudanças de Sala", len(relatorio_transferidos))
                            c3.metric("Total Processado", len(dados_upsert))
                            
                            if duplicados_excel > 0:
                                st.warning(f"⚠️ **{duplicados_excel} ocorrências duplicadas** foram encontradas dentro da sua planilha Excel e foram ignoradas (o sistema manteve apenas a primeira ocorrência).")
                            
                            st.success("O Banco de Dados foi atualizado com sucesso e as datas de nascimento/sexo foram preenchidas para todos os alunos válidos da planilha.")
                            
                            # Tabelas expansíveis para detalhamento
                            if relatorio_inseridos:
                                with st.expander(f"➕ Ver lista de {len(relatorio_inseridos)} novos alunos inseridos", expanded=False):
                                    st.dataframe(pd.DataFrame(relatorio_inseridos), use_container_width=True, hide_index=True)
                            
                            if relatorio_transferidos:
                                with st.expander(f"🔄 Ver lista de {len(relatorio_transferidos)} alunos que mudaram de sala", expanded=False):
                                    st.dataframe(pd.DataFrame(relatorio_transferidos), use_container_width=True, hide_index=True)

                    except Exception as e:
                        st.error(f"❌ Ocorreu um erro crítico durante o processamento: {e}")

    # ==========================================
    # ABA 2: COLAR NOMES (MANTIDA IGUAL PARA INSERÇÕES RÁPIDAS)
    # ==========================================
    with aba_texto:
        st.subheader("Adicionar Novatos em Lote")
        st.write("Cole os nomes dos alunos (um por linha), escolha a turma e o sistema fará o filtro automático. (⚠️ Não insere data/sexo).")
        
        col1, col2 = st.columns([2, 1])
        with col1:
            texto_nomes = st.text_area("Lista de Nomes (Cole aqui):", height=200)
        with col2:
            opcoes_turmas = ["1º A", "1º B", "1º C", "1º D", "1º E", "2º A", "2º B", "2º C", "2º D", "3º A", "3º B", "3º C", "3º D"]
            turma_selecionada = st.selectbox("Selecione a Turma:", opcoes_turmas)
        
        if st.button("🔍 Verificar Nomes"):
            if not texto_nomes.strip():
                st.warning("⚠️ Cole pelo menos um nome na caixa de texto.")
            else:
                lista_digitada = [n.upper().strip() for n in texto_nomes.split('\n') if n.strip()]
                res = supabase.table("alunos").select("nome").execute()
                nomes_no_banco = {str(item['nome']).upper().strip() for item in res.data}
                
                novatos = [{"nome": n, "turma": turma_selecionada} for n in lista_digitada if n not in nomes_no_banco]
                
                st.session_state['lista_novatos'] = novatos
                st.session_state['total_digitado'] = len(lista_digitada)

        if 'lista_novatos' in st.session_state:
            novatos = st.session_state['lista_novatos']
            total = st.session_state['total_digitado']
            
            st.divider()
            
            if novatos:
                st.success(f"✅ Dos {total} nomes colados, encontramos **{len(novatos)} novatos** para a turma {turma_selecionada}.")
                with st.expander("👀 Ver Lista", expanded=True):
                    st.dataframe(pd.DataFrame(novatos), use_container_width=True)
                
                if st.button("💾 Salvar Novatos no Banco", type="primary"):
                    try:
                        supabase.table("alunos").insert(novatos).execute()
                        st.success("🎉 Alunos salvos com sucesso!")
                        del st.session_state['lista_novatos']
                    except Exception as e:
                        st.error(f"❌ Erro ao salvar: {e}")
            else:
                st.info(f"ℹ️ Todos os {total} nomes já estão cadastrados. Nenhum aluno novo.")
