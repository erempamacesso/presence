import streamlit as st
import pandas as pd
import datetime

def exibir_importacao(supabase):
    st.title("📤 Sincronização Inteligente (Secretaria)")
    
    st.info("""
        **Como funciona:**
        1. Suba a planilha oficial (Certifique-se que a 1ª linha seja o cabeçalho: `Matrícula, Nome, Data de nascimento, Sexo`).
        2. Na aba **Checagem Prévia**, verifique se a leitura das salas está correta.
        3. Na aba **Sincronização**, revise as diferenças e aprove a atualização do banco.
    """)

    arquivo = st.file_uploader("Suba o arquivo Excel Oficial (.xlsx ou .xls)", type=["xlsx", "xls"])
    
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

            dados_excel = []
            resumo_leitura = []

            for nome_aba in abas_turmas:
                # Extrai a turma do nome da aba (Ex: EM45-1IA -> 1º A)
                sigla = nome_aba.split('-')[-1].strip()
                turma_format = f"{sigla[0]}º {sigla[-1]}" if len(sigla) >= 2 else nome_aba
                
                # Lê a aba sabendo que a primeira linha é o cabeçalho
                df = pd.read_excel(xl, sheet_name=nome_aba, header=0)
                
                # Remove linhas sem nome
                if 'Nome' in df.columns:
                    df = df.dropna(subset=['Nome'])
                else:
                    st.error(f"Coluna 'Nome' não encontrada na aba {nome_aba}.")
                    continue
                
                # Tenta buscar a coluna Situação, se ela existir. Como você apagou, ele vai ignorar isso.
                col_situacao = [col for col in df.columns if 'SITUAÇÃO' in col.upper() or 'SITUACAO' in col.upper()]
                if col_situacao:
                    nome_col_sit = col_situacao[0]
                    df = df[df[nome_col_sit].astype(str).str.upper().str.contains("MATRICULADO", na=False)]

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
                
                resumo_leitura.append({"Aba Original": nome_aba, "Turma": turma_format, "Qtd Alunos": qtd_aba})

            df_global_excel = pd.DataFrame(dados_excel)
            df_global_excel = df_global_excel.drop_duplicates(subset=['nome'], keep='last')
            
        except Exception as e:
            st.error(f"Erro ao ler a planilha: {e}")
            return

        # ==========================================
        # CRIAÇÃO DAS ABAS (NOVIDADE AQUI!)
        # ==========================================
        aba_checagem, aba_sinc = st.tabs(["📊 1. Checagem Prévia da Planilha", "🔄 2. Sincronização com o Banco"])

        # --- ABA 1: CHECAGEM PRÉVIA ---
        with aba_checagem:
            st.subheader("Contagem de Alunos Lidos do Excel")
            st.write("Verifique se os números abaixo batem com o que você espera por turma.")
            
            # Mostra a tabela de resumo
            st.dataframe(pd.DataFrame(resumo_leitura), use_container_width=True, hide_index=True)
            st.success(f"**Total Geral Lidos do Arquivo:** {len(df_global_excel)} alunos")
            
            st.divider()
            st.write("🤔 **Dúvida sobre alguma turma?** Veja a lista de nomes que o sistema encontrou nela:")
            turma_escolhida = st.selectbox("Escolha a turma para visualizar:", options=["Selecione..."] + sorted(list(df_global_excel['turma'].unique())))
            
            if turma_escolhida != "Selecione...":
                df_filtro = df_global_excel[df_global_excel['turma'] == turma_escolhida]
                st.dataframe(df_filtro[['nome', 'matricula']], hide_index=True, use_container_width=True)

        # --- ABA 2: SINCRONIZAÇÃO E DIFERENÇAS ---
        with aba_sinc:
            st.subheader("Conferência com o Banco de Dados (Supabase)")
            
            with st.spinner("Buscando dados no Supabase..."):
                res_banco = supabase.table("alunos").select("*").execute()
                df_banco = pd.DataFrame(res_banco.data) if res_banco.data else pd.DataFrame(columns=["nome", "turma", "matricula", "data_nascimento", "sexo"])

            nomes_excel = set(df_global_excel['nome'])
            nomes_banco = set(df_banco['nome']) if not df_banco.empty else set()

            # 1. NOVOS
            nomes_novos = nomes_excel - nomes_banco
            df_novos = df_global_excel[df_global_excel['nome'].isin(nomes_novos)]

            # 2. REMOVIDOS
            nomes_removidos = nomes_banco - nomes_excel
            df_removidos = df_banco[df_banco['nome'].isin(nomes_removidos)]

            # 3. ALTERADOS
            nomes_comuns = nomes_excel & nomes_banco
            lista_alterados = []
            lista_upsert_final = df_novos.to_dict('records')

            for nome in nomes_comuns:
                dado_excel = df_global_excel[df_global_excel['nome'] == nome].iloc[0]
                dado_banco = df_banco[df_banco['nome'] == nome].iloc[0]
                
                mudou = False
                alteracoes = []
                
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
                
                lista_upsert_final.append(dado_excel.to_dict())

            df_alterados = pd.DataFrame(lista_alterados)

            # Exibindo os Resultados
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

            # BOTÃO DE EXECUÇÃO FINAL
            st.divider()
            if len(nomes_novos) > 0 or len(nomes_removidos) > 0 or len(df_alterados) > 0:
                st.warning("⚠️ **Atenção:** A operação abaixo é irreversível. Revise os dados antes de prosseguir.")
                
                if st.button("🚨 APROVAR E SINCRONIZAR COM O BANCO DE DADOS", type="primary", use_container_width=True):
                    with st.spinner("Sincronizando dados..."):
                        try:
                            # 1. EXCLUSÕES
                            if nomes_removidos:
                                for nome_remover in nomes_removidos:
                                    supabase.table("alunos").delete().eq("nome", nome_remover).execute()
                            
                            # 2. INSERÇÕES E ATUALIZAÇÕES
                            if lista_upsert_final:
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