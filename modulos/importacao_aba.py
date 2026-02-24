import streamlit as st
import pandas as pd

def exibir_importacao(supabase):
    st.title("📤 Gestão e Importação de Dados")
    
    # Criando abas para organizar a interface
    aba_planilha, aba_texto = st.tabs(["📁 Upload de Planilha", "📝 Colar Lista de Nomes (Rápido)"])

    # ==========================================
    # ABA 1: UPLOAD DE PLANILHA (CSV / EXCEL)
    # ==========================================
    with aba_planilha:
        st.subheader("Importação via Arquivo (Padrão SIGPAM)")
        with st.expander("📄 Ver Padrão de Arquivo Aceito"):
            st.write("O arquivo deve ser **CSV** ou **Excel** com as colunas: `nome`, `turma`")
            st.code("nome,turma\nJOAO SILVA,1º E")

        arquivo = st.file_uploader("Suba a lista completa da escola", type=["csv", "xlsx"])
        
        if arquivo:
            if st.button("🚀 Iniciar Sincronização de Arquivo"):
                try:
                    # Leitura flexível
                    if arquivo.name.endswith('.csv'):
                        try:
                            df = pd.read_csv(arquivo, encoding='utf-8')
                        except UnicodeDecodeError:
                            df = pd.read_csv(arquivo, encoding='latin-1', sep=None, engine='python')
                    else:
                        df = pd.read_excel(arquivo)

                    # Limpeza das colunas
                    df.columns = [str(c).lower().strip() for c in df.columns]
                    df = df.dropna(subset=['nome'])
                    
                    # Verificação em massa no banco (Filtro Global)
                    res = supabase.table("alunos").select("nome").execute()
                    nomes_no_banco = {str(item['nome']).upper().strip() for item in res.data}

                    novos_alunos = []
                    ja_existentes = 0

                    for _, row in df.iterrows():
                        nome_limpo = str(row['nome']).upper().strip()
                        turma_limpa = str(row['turma']).upper().strip()

                        if nome_limpo and nome_limpo != "NAN":
                            if nome_limpo not in nomes_no_banco:
                                novos_alunos.append({"nome": nome_limpo, "turma": turma_limpa})
                            else:
                                ja_existentes += 1
                    
                    # Inserção e Feedback
                    if novos_alunos:
                        supabase.table("alunos").insert(novos_alunos).execute()
                        st.success(f"✅ {len(novos_alunos)} novos alunos cadastrados com sucesso!")
                    else:
                        st.info("ℹ️ Nenhum aluno novo encontrado nesta planilha.")
                    
                    st.write(f"**Resumo:** {len(novos_alunos)} adicionados | {ja_existentes} ignorados (já existiam).")

                except Exception as e:
                    st.error(f"❌ Ocorreu um erro: {e}")

    # ==========================================
    # ABA 2: COLAR NOMES COM PRÉVIA E FILTRO
    # ==========================================
    with aba_texto:
        st.subheader("Adicionar Novatos em Lote")
        st.write("Cole os nomes dos alunos (um por linha), escolha a turma e o sistema fará o filtro automático.")
        
        # Layout da tela de inserção
        col1, col2 = st.columns([2, 1])
        with col1:
            texto_nomes = st.text_area("Lista de Nomes (Cole aqui):", height=200)
        with col2:
            # Você pode puxar essas turmas do banco depois, deixei fixo como exemplo
            opcoes_turmas = ["1º A", "1º B", "1º C", "1º D", "1º E", "2º A", "3º A"]
            turma_selecionada = st.selectbox("Selecione a Turma:", opcoes_turmas)
        
        # Botão para gerar a prévia
        if st.button("🔍 Verificar Nomes"):
            if not texto_nomes.strip():
                st.warning("⚠️ Cole pelo menos um nome na caixa de texto.")
            else:
                # 1. Limpa os nomes colados (divide por linha e ignora linhas vazias)
                lista_digitada = [n.upper().strip() for n in texto_nomes.split('\n') if n.strip()]
                
                # 2. Busca quem já existe no banco (Filtro Global)
                res = supabase.table("alunos").select("nome").execute()
                nomes_no_banco = {str(item['nome']).upper().strip() for item in res.data}
                
                # 3. Filtra apenas os novatos
                novatos = [{"nome": n, "turma": turma_selecionada} for n in lista_digitada if n not in nomes_no_banco]
                
                # Guarda no session_state para o botão de salvar não perder a lista
                st.session_state['lista_novatos'] = novatos
                st.session_state['total_digitado'] = len(lista_digitada)

        # 4. Exibe a prévia e o botão de confirmação SE a verificação já ocorreu
        if 'lista_novatos' in st.session_state:
            novatos = st.session_state['lista_novatos']
            total = st.session_state['total_digitado']
            
            st.divider()
            
            if novatos:
                st.success(f"✅ Filtro concluído! Dos {total} nomes colados, encontramos **{len(novatos)} novatos** para a turma {turma_selecionada}.")
                
                with st.expander("👀 Ver Lista de Prévia", expanded=True):
                    st.dataframe(pd.DataFrame(novatos), use_container_width=True)
                
                # Botão final de salvamento
                if st.button("💾 Confirmar e Salvar no Banco", type="primary"):
                    try:
                        supabase.table("alunos").insert(novatos).execute()
                        st.balloons()
                        st.success("🎉 Alunos salvos com sucesso!")
                        # Limpa o state após salvar
                        del st.session_state['lista_novatos']
                    except Exception as e:
                        st.error(f"❌ Erro ao salvar no banco: {e}")
            else:
                st.info(f"ℹ️ Todos os {total} nomes que você colou já estão cadastrados no sistema em alguma turma. Nenhum aluno novo para adicionar.")
