import streamlit as st
import pandas as pd
import datetime

def formatar_turma(nome_aba):
    """Transforma 'EM45-1IA' em '1º A'"""
    sigla = nome_aba.split('-')[-1].strip() if '-' in nome_aba else nome_aba.strip()
    if len(sigla) >= 2 and sigla[0].isdigit():
        return f"{sigla[0]}º {sigla[-1]}"
    return nome_aba

def exibir_importacao(supabase):
    st.title("📤 Sincronização em Passos")

    # ==========================================
    # GERENCIAMENTO DE ESTADO (Para não perder os dados ao clicar em botões)
    # ==========================================
    if 'df_excel' not in st.session_state:
        st.session_state['df_excel'] = None
    if 'resumo_turmas' not in st.session_state:
        st.session_state['resumo_turmas'] = None

    # ==========================================
    # 1º PASSO: CARREGAR O EXCEL
    # ==========================================
    st.header("1º Passo: Carregar a Planilha")
    st.write("A planilha deve ter a primeira linha com: Matrícula, Nome, Data de nascimento, Sexo")
    
    arquivo = st.file_uploader("Suba o arquivo Excel (.xlsx ou .xls)", type=["xlsx", "xls"])

    if arquivo:
        if st.button("Ler Planilha", type="primary"):
            with st.spinner("Lendo abas..."):
                try:
                    xl = pd.ExcelFile(arquivo)
                    abas = [a for a in xl.sheet_names if "EM45" in a]
                    
                    if not abas:
                        st.error("Nenhuma aba contendo 'EM45' foi encontrada.")
                        return

                    dados_lidos = []
                    resumo = []

                    for aba in abas:
                        df = pd.read_excel(xl, sheet_name=aba, header=0)
                        
                        # LIMPEZA DOS NOMES DAS COLUNAS (Tira espaços e deixa maiúsculo)
                        df.columns = df.columns.str.strip().str.upper()
                        
                        # Verifica se a coluna NOME existe após a limpeza
                        if 'NOME' not in df.columns:
                            st.warning(f"Aba {aba} ignorada: Coluna 'Nome' não encontrada.")
                            continue

                        # Remove linhas onde o nome está vazio
                        df = df.dropna(subset=['NOME'])
                        turma_formatada = formatar_turma(aba)

                        qtd = 0
                        for _, linha in df.iterrows():
                            nome = str(linha['NOME']).upper().strip()
                            if nome == "NAN" or not nome: continue

                            # Busca flexível por Matrícula, Data e Sexo
                            matricula = linha.get('MATRÍCULA', linha.get('MATRICULA', None))
                            matricula = str(matricula).strip() if pd.notna(matricula) else None
                            if matricula == "nan" or matricula == "None": matricula = None

                            dt_nasc = None
                            col_data = linha.get('DATA DE NASCIMENTO', linha.get('DATA', None))
                            try:
                                dt = pd.to_datetime(col_data, dayfirst=True)
                                if pd.notna(dt): dt_nasc = dt.strftime('%Y-%m-%d')
                            except: pass

                            sexo = str(linha.get('SEXO', '')).upper().strip()
                            sexo = sexo[0] if sexo in ['M', 'F', 'MASCULINO', 'FEMININO'] else None

                            dados_lidos.append({
                                "nome": nome,
                                "turma": turma_formatada,
                                "matricula": matricula,
                                "data_nascimento": dt_nasc,
                                "sexo": sexo
                            })
                            qtd += 1

                        resumo.append({"Turma": turma_formatada, "Qtd Alunos Lidos": qtd})

                    # Salva na memória do Streamlit
                    st.session_state['df_excel'] = pd.DataFrame(dados_lidos).drop_duplicates(subset=['nome'], keep='last')
                    st.session_state['resumo_turmas'] = pd.DataFrame(resumo)
                    
                    st.success("Planilha lida com sucesso! Vá para o Passo 2.")
                
                except Exception as e:
                    st.error(f"Erro ao processar: {e}")

    # ==========================================
    # 2º PASSO: CONFERÊNCIA POR TURMA
    # ==========================================
    if st.session_state['df_excel'] is not None:
        st.divider()
        st.header("2º Passo: Conferência por Turma")
        
        df_excel = st.session_state['df_excel']
        df_resumo = st.session_state['resumo_turmas']
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.write("**Resumo de Leitura**")
            st.dataframe(df_resumo, hide_index=True)
            st.info(f"**Total Geral:** {len(df_excel)} alunos")
            
        with col2:
            turmas_disp = sorted(df_excel['turma'].unique())
            turma_sel = st.selectbox("Selecione a turma para conferir os nomes:", ["Escolha..."] + turmas_disp)
            
            if turma_sel != "Escolha...":
                df_filtrado = df_excel[df_excel['turma'] == turma_sel]
                st.write(f"Alunos na turma **{turma_sel}**:")
                st.dataframe(df_filtrado[['nome', 'matricula', 'data_nascimento']], hide_index=True, use_container_width=True)

        # ==========================================
        # 3º PASSO: CRUZAMENTO DE DADOS
        # ==========================================
        st.divider()
        st.header("3º Passo: Cruzamento com o SIGEREMPAM")
        st.write("Agora vamos comparar a lista que você acabou de conferir com o banco de dados atual.")
        
        if st.button("🔍 Iniciar Cruzamento", type="primary"):
            with st.spinner("Buscando dados no Supabase e comparando..."):
                res_banco = supabase.table("alunos").select("*").execute()
                df_banco = pd.DataFrame(res_banco.data) if res_banco.data else pd.DataFrame(columns=["nome", "turma", "matricula", "data_nascimento", "sexo"])

                nomes_excel = set(df_excel['nome'])
                nomes_banco = set(df_banco['nome']) if not df_banco.empty else set()

                # A) TRANSFERIDOS (Estão no Banco, não estão no Excel)
                nomes_saíram = nomes_banco - nomes_excel
                df_transferidos = df_banco[df_banco['nome'].isin(nomes_saíram)]

                # B) NOVATOS (Estão no Excel, não estão no Banco)
                nomes_novatos = nomes_excel - nomes_banco
                df_novatos = df_excel[df_excel['nome'].isin(nomes_novatos)]

                # C) ATUALIZAÇÕES / DADOS FALTANDO (Estão nos dois)
                nomes_comuns = nomes_excel & nomes_banco
                lista_atualizar = []
                
                for nome in nomes_comuns:
                    d_ex = df_excel[df_excel['nome'] == nome].iloc[0]
                    d_bd = df_banco[df_banco['nome'] == nome].iloc[0]
                    
                    motivos = []
                    
                    if d_ex['turma'] != d_bd.get('turma'):
                        motivos.append(f"Turma: {d_bd.get('turma')} ➔ {d_ex['turma']}")
                        
                    if pd.notna(d_ex['matricula']) and str(d_ex['matricula']) != str(d_bd.get('matricula', 'None')):
                        motivos.append("Matrícula nova/corrigida")
                        
                    if pd.notna(d_ex['data_nascimento']) and d_ex['data_nascimento'] != d_bd.get('data_nascimento'):
                        motivos.append("Data nasc. nova/corrigida")
                        
                    if pd.notna(d_ex['sexo']) and d_ex['sexo'] != d_bd.get('sexo'):
                        motivos.append("Sexo novo/corrigido")
                        
                    if motivos:
                        lista_atualizar.append({
                            "Nome": nome,
                            "Turma Atual": d_ex['turma'],
                            "O que precisa atualizar": " | ".join(motivos)
                        })

                df_atualizar = pd.DataFrame(lista_atualizar)

                # --- EXIBINDO OS RESULTADOS ---
                st.subheader("Resultados do Cruzamento")
                
                tab1, tab2, tab3 = st.tabs([
                    f"🔴 A) Transferidos/Saíram ({len(df_transferidos)})", 
                    f"🟢 B) Novatos ({len(df_novatos)})", 
                    f"🟡 C) Atualizar Dados ({len(df_atualizar)})"
                ])
                
                with tab1:
                    st.write("Alunos que estão no SIGEREMPAM mas não constam na sua planilha nova.")
                    if not df_transferidos.empty: st.dataframe(df_transferidos[['nome', 'turma']], hide_index=True)
                    else: st.success("Nenhum aluno para remover.")
                
                with tab2:
                    st.write("Alunos novos que vieram na planilha e precisam entrar no SIGEREMPAM.")
                    if not df_novatos.empty: st.dataframe(df_novatos[['nome', 'turma']], hide_index=True)
                    else: st.success("Nenhum aluno novo.")
                    
                with tab3:
                    st.write("Alunos que já existem, mas mudaram de turma ou estavam sem matrícula/data/sexo no SIGEREMPAM.")
                    if not df_atualizar.empty: st.dataframe(df_atualizar, hide_index=True)
                    else: st.success("Nenhum dado pendente de atualização.")