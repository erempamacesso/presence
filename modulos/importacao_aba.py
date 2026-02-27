import streamlit as st
import pandas as pd

def exibir_importacao(supabase):
    st.title("📤 Gestão e Importação de Dados")
    
    # Criando abas para organizar a interface
    aba_planilha, aba_texto = st.tabs(["📁 Upload do Excel Oficial", "📝 Colar Lista Rápida (Apenas Nomes)"])

    # ==========================================
    # ABA 1: UPLOAD DO EXCEL MULTI-ABAS (NOVO)
    # ==========================================
    with aba_planilha:
        st.subheader("Importação e Atualização em Massa (Excel)")
        st.info("O sistema lerá as abas (ex: 1 - EM45-1IA), atualizará turmas de alunos existentes e adicionará as datas de nascimento e sexo.")
        
        arquivo = st.file_uploader("Suba a planilha oficial da secretaria (.xlsx)", type=["xlsx"])
        
        if arquivo:
            if st.button("🚀 Iniciar Sincronização Global"):
                try:
                    xl = pd.ExcelFile(arquivo)
                    abas = xl.sheet_names
                    
                    # Filtra apenas as abas que têm "EM45" no nome
                    abas_turmas = [a for a in abas if "EM45" in a]
                    
                    if not abas_turmas:
                        st.error("Nenhuma aba com o padrão 'EM45' foi encontrada no arquivo.")
                    else:
                        barra = st.progress(0)
                        st.write(f"📊 Processando {len(abas_turmas)} turmas...")
                        
                        sucesso_total = 0
                        
                        for i, nome_aba in enumerate(abas_turmas):
                            # 1. Extrai a turma do nome da aba (ex: "1 - EM45-1IA" -> "1º A")
                            sigla = nome_aba.split('-')[-1].strip() # Pega "1IA"
                            if len(sigla) >= 2:
                                turma_formatada = f"{sigla[0]}º {sigla[-1]}" # Formata para "1º A"
                            else:
                                turma_formatada = nome_aba # Fallback
                                
                            # 2. Lê a aba
                            df = pd.read_excel(xl, sheet_name=nome_aba)
                            dados_upsert = []
                            
                            # 3. Prepara os dados
                            for _, linha in df.iterrows():
                                if pd.isna(linha.get('Nome')): # Pula linhas vazias
                                    continue
                                    
                                nome_limpo = str(linha['Nome']).upper().strip()
                                
                                # Trata a data de nascimento
                                try:
                                    dt_nasc = pd.to_datetime(linha['Data de nascimento'], dayfirst=True).strftime('%Y-%m-%d')
                                except:
                                    dt_nasc = None
                                
                                # Trata o sexo
                                sexo = str(linha.get('Sexo', '')).upper().strip()
                                sexo = sexo if sexo in ['M', 'F'] else None

                                dados_upsert.append({
                                    "nome": nome_limpo,
                                    "turma": turma_formatada,
                                    "data_nascimento": dt_nasc,
                                    "sexo": sexo
                                })
                            
                            # 4. Envia para o banco usando UPSERT
                            if dados_upsert:
                                supabase.table("alunos").upsert(dados_upsert, on_conflict="nome").execute()
                                sucesso_total += len(dados_upsert)
                                
                            barra.progress((i + 1) / len(abas_turmas))
                            
                        st.success(f"🎉 Sincronização concluída! {sucesso_total} registros processados (inseridos ou atualizados).")
                        st.balloons()
                        
                except Exception as e:
                    st.error(f"❌ Ocorreu um erro ao processar o arquivo: {e}")

    # ==========================================
    # ABA 2: COLAR NOMES COM PRÉVIA (MANTIDA IGUAL AO SEU CÓDIGO)
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
