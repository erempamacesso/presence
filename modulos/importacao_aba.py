import streamlit as st
import pandas as pd
import datetime

def exibir_importacao(supabase):
    st.title("📤 Sincronização Inteligente (Secretaria)")
    
    st.info("""
        **Como funciona:**
        1. Suba a planilha oficial (Certifique-se que a 1ª linha seja o cabeçalho: `Matrícula, Nome, Data de nascimento, Sexo`).
        2. O sistema lerá todas as abas e confrontará com o banco de dados.
        3. Você revisará as diferenças e aprovará a sincronização final.
    """)

    arquivo = st.file_uploader("Suba o arquivo Excel Oficial (.xlsx)", type=["xlsx"])
    
    if arquivo:
        # ==========================================
        # PASSO 1: LER A PLANILHA E CRIAR LISTA ÚNICA
        # ==========================================
        try:
            xl = pd.ExcelFile(arquivo)
            abas_turmas = [a for a in xl.sheet_names if "EM45" in a] # Pega só as abas de turma
            
            if not abas_turmas:
                st.warning("⚠️ Nenhuma aba com 'EM45' no nome foi encontrada.")
                return

            st.subheader("📊 1. Resumo da Leitura das Abas")
            
            dados_excel = []
            resumo_leitura = []

            for nome_aba in abas_turmas:
                # Extrai a turma do nome da aba (Ex: EM45-1IA -> 1º A)
                sigla = nome_aba.split('-')[-1].strip()
                turma_format = f"{sigla[0]}º {sigla[-1]}" if len(sigla) >= 2 else nome_aba
                
                # Lê a aba sabendo que a primeira linha é o cabeçalho (header=0)
                df = pd.read_excel(xl, sheet_name=nome_aba, header=0)
                
                # Remove linhas sem nome
                if 'Nome' in df.columns:
                    df = df.dropna(subset=['Nome'])
                else:
                    st.error(f"Coluna 'Nome' não encontrada na aba {nome_aba}.")
                    continue
                
                qtd_aba = 0
                for _, linha in df.iterrows():
                    nome_limpo = str(linha['Nome']).upper().strip()
                    if not nome_limpo or nome_limpo == "NAN":
                        continue
                        
                    # Tratamento de Matrícula
                    matricula = str(linha.get('Matrícula', '')).strip()
                    if matricula == "nan" or matricula == "None": matricula = None
                    
                    # Tratamento de Data
                    dt_nasc = None
                    try:
                        dt = pd.to_datetime(linha.get('Data de nascimento'), dayfirst=True)
                        if not pd.isna(dt):
                            dt_nasc = dt.strftime('%Y-%m-%d')
                    except: pass
                    
                    # Tratamento de Sexo
                    sexo = str(linha.get('Sexo', '')).upper().strip()
                    sexo = sexo[0] if sexo in ['M', 'F', 'MASCULINO', 'FEMININO'] else None

                    dados_excel.append({
                        "nome": nome_limpo,
                        "turma": turma_format,
                        "matricula": matricula,
                        "data_nascimento": dt_nasc,
                        "sexo": sexo
                    })
                    qtd_aba += 1
                
                resumo_leitura.append({"Aba Original": nome_aba, "Turma Identificada": turma_format, "Alunos Lidos": qtd_aba})

            # Exibe o resumo do que foi lido do Excel
            st.table(pd.DataFrame(resumo_leitura))
            
            df_global_excel = pd.DataFrame(dados_excel)
            # Proteção contra aluno duplicado na própria planilha da secretaria (mantém o último)
            df_global_excel = df_global_excel.drop_duplicates(subset=['nome'], keep='last')
            
            st.success(f"Total de alunos únicos lidos na planilha: **{len(df_global_excel)}**")

        except Exception as e:
            st.error(f"Erro ao ler a planilha: {e}")
            return

        # ==========================================
        # PASSO 2: CONFRONTO COM O SUPABASE
        # ==========================================
        st.divider()
        st.subheader("🔍 2. Conferência (O que vai mudar?)")
        
        with st.spinner("Buscando dados no Supabase..."):
            res_banco = supabase.table("alunos").select("*").execute()
            df_banco = pd.DataFrame(res_banco.data) if res_banco.data else pd.DataFrame(columns=["nome", "turma", "matricula", "data_nascimento", "sexo"])

        # Identificando as chaves (Nomes)
        nomes_excel = set(df_global_excel['nome'])
        nomes_banco = set(df_banco['nome']) if not df_banco.empty else set()

        # 1. NOVOS (Estão no Excel, não estão no Banco)
        nomes_novos = nomes_excel - nomes_banco
        df_novos = df_global_excel[df_global_excel['nome'].isin(nomes_novos)]

        # 2. REMOVIDOS (Estão no Banco, não estão no Excel)
        nomes_removidos = nomes_banco - nomes_excel
        df_removidos = df_banco[df_banco['nome'].isin(nomes_removidos)]

        # 3. ALTERADOS (Estão nos dois, mas algum dado mudou)
        nomes_comuns = nomes_excel & nomes_banco
        lista_alterados = []
        lista_upsert_final = df_novos.to_dict('records') # Já preparamos a lista de envio com os novos

        for nome in nomes_comuns:
            dado_excel = df_global_excel[df_global_excel['nome'] == nome].iloc[0]
            dado_banco = df_banco[df_banco['nome'] == nome].iloc[0]
            
            mudou = False
            alteracoes = []
            
            # Compara Turma, Matrícula, Data e Sexo
            if dado_excel['turma'] != dado_banco.get('turma'):
                mudou = True
                alteracoes.append(f"Turma: {dado_banco.get('turma')} ➔ {dado_excel['turma']}")
            
            if pd.notna(dado_excel['matricula']) and dado_excel['matricula'] != str(dado_banco.get('matricula', 'None')):
                mudou = True
                alteracoes.append("Matrícula atualizada")
                
            if pd.notna(dado_excel['data_nascimento']) and dado_excel['data_nascimento'] != dado_banco.get('data_nascimento'):
                mudou = True
                alteracoes.append("Data Nasc. atualizada")
                
            if mudou:
                lista_alterados.append({"Nome": nome, "O que mudou": " | ".join(alteracoes)})
            
            # Adiciona todos os alunos comuns na lista final (pois o upsert garante que fiquem idênticos ao Excel)
            lista_upsert_final.append(dado_excel.to_dict())

        df_alterados = pd.DataFrame(lista_alterados)

        # Exibindo os Resultados para o Usuário
        col1, col2, col3 = st.columns(3)
        col1.metric("Novos Alunos", len(nomes_novos))
        col2.metric("Alunos Transferidos (Excluir)", len(nomes_removidos))
        col3.metric("Alunos com Alterações", len(df_alterados))

        with st.expander("🆕 Ver Novos Alunos (Serão Inseridos)"):
            if not df_novos.empty: st.dataframe(df_novos[['nome', 'turma']], hide_index=True)
            else: st.info("Nenhum aluno novo.")

        with st.expander("🗑️ Ver Transferidos/Desistentes (Serão Removidos)"):
            if not df_removidos.empty: st.dataframe(df_removidos[['nome', 'turma']], hide_index=True)
            else: st.info("Nenhum aluno foi transferido.")

        with st.expander("🔄 Ver Alunos Alterados (Mudança de Turma, Matrícula, etc)"):
            if not df_alterados.empty: st.dataframe(df_alterados, hide_index=True)
            else: st.info("Nenhum dado divergente.")

        # ==========================================
        # PASSO 3: BOTÃO DE EXECUÇÃO FINAL
        # ==========================================
        st.divider()
        if len(nomes_novos) > 0 or len(nomes_removidos) > 0 or len(df_alterados) > 0:
            st.warning("⚠️ **Atenção:** A operação abaixo é irreversível. Revise os dados nas abas acima antes de prosseguir.")
            
            if st.button("🚨 APROVAR E SINCRONIZAR COM O BANCO DE DADOS", type="primary", use_container_width=True):
                with st.spinner("Sincronizando dados..."):
                    try:
                        # 1. EXCLUSÕES
                        if nomes_removidos:
                            for nome_remover in nomes_removidos:
                                supabase.table("alunos").delete().eq("nome", nome_remover).execute()
                        
                        # 2. INSERÇÕES E ATUALIZAÇÕES (Upsert)
                        # O upsert atualiza o aluno se o nome já existir, ou insere se não existir.
                        # Para isso funcionar perfeitamente, a coluna 'nome' precisa ser a chave primária ou única no Supabase.
                        if lista_upsert_final:
                            # Quebramos em lotes de 500 para não estourar limite da API
                            tamanho_lote = 500
                            for i in range(0, len(lista_upsert_final), tamanho_lote):
                                lote = lista_upsert_final[i:i + tamanho_lote]
                                supabase.table("alunos").upsert(lote, on_conflict="nome").execute()

                        st.success("✅ **Sincronização concluída com sucesso!** O banco agora é o espelho da planilha.")
                        st.balloons()
                        
                    except Exception as e:
                        st.error(f"❌ Erro crítico ao tentar gravar no banco: {e}")
        else:
            st.success("🎉 Seu banco de dados já está 100% igual à planilha! Nenhuma ação necessária.")