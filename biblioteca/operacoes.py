import streamlit as st
from supabase import create_client

# Instanciando as duas conexões (puxando do seu secrets)
db_alunos = create_client(st.secrets["supabase_alunos_url"], st.secrets["supabase_alunos_key"])
db_biblio = create_client(st.secrets["supabase_biblio_url"], st.secrets["supabase_biblio_key"])

def tela_emprestimo():
    st.header("🔄 Novo Empréstimo")
    
    # 1. BUSCA O ALUNO NO BANCO 1
    busca_aluno = st.text_input("Digite a Matrícula ou Nome do Aluno")
    aluno_selecionado = None

    if busca_aluno:
        # Procuramos na sua tabela 'alunos' do Banco Principal
        res_aluno = db_alunos.table("alunos").select("id, nome, turma").ilike("nome", f"%{busca_aluno}%").execute()
        
        if res_aluno.data:
            opcoes = {f"{a['nome']} ({a['turma']})": a for a in res_aluno.data}
            escolha = st.selectbox("Confirme o Aluno:", options=list(opcoes.keys()))
            aluno_selecionado = opcoes[escolha]
            st.success(f"Aluno selecionado: {aluno_selecionado['nome']}")
        else:
            st.error("Aluno não encontrado no Banco Principal.")

    # 2. BUSCA O LIVRO NO BANCO 2 (Pelo ID do QR Code ou Nome)
    if aluno_selecionado:
        st.divider()
        id_livro_qr = st.text_input("Escaneie o QR Code do Livro (ID)")
        
        if id_livro_qr:
            # Remove o prefixo 'LIB:' se o monitor escanear o QR Code que geramos
            clean_id = id_livro_qr.replace("LIB:", "")
            
            res_livro = db_biblio.table("livros").select("*").eq("id", clean_id).execute()
            
            if res_livro.data:
                livro = res_livro.data[0]
                st.info(f"Livro: {livro['titulo']} | Disponível: {livro['quantidade_disponivel']}")
                
                if livro['quantidade_disponivel'] > 0:
                    if st.button("Confirmar Empréstimo"):
                        # REGISTRA NO BANCO 2
                        dados_emprestimo = {
                            "livro_id": livro['id'],
                            "aluno_id": aluno_selecionado['id'], # ID que veio do Banco 1
                            "numero_matricula": aluno_selecionado.get('numero_matricula', ''),
                            "data_devolucao_prevista": "2026-05-20", # Exemplo: 7 dias
                            "status": "ativo"
                        }
                        
                        # Salva o empréstimo
                        db_biblio.table("emprestimos").insert(dados_emprestimo).execute()
                        
                        # Atualiza o estoque no Banco 2
                        nova_qtd = livro['quantidade_disponivel'] - 1
                        db_biblio.table("livros").update({"quantidade_disponivel": nova_qtd}).eq("id", livro['id']).execute()
                        
                        st.balloons()
                        st.success("Empréstimo registrado com sucesso!")
                else:
                    st.warning("Este livro não tem exemplares disponíveis no momento.")