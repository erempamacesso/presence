import streamlit as st
import pandas as pd

def mostrar_tela_desempenho(db_alunos, db_provas):
    st.subheader("📊 Meu Desempenho")
    aluno = st.session_state.aluno
    aluno_id = str(aluno['id'])
    
    # Extrai a turma do aluno para encontrar o simulado correto (ex: "2º ano")
    turma_aluno = str(aluno.get('turma', '')).lower()
    ano_ref = "2º ano" if "2º" in turma_aluno else ("3º ano" if "3º" in turma_aluno else "1º ano")
    
    st.write(f"Olá, **{aluno['nome']}**! Acompanhe suas notas abaixo.")

    # =========================================================================
    # 1. FUNÇÃO DINÂMICA: BUSCA A NOTA CALCULADA DOS SIMULADOS (AT1 e AT2)
    # =========================================================================
    def buscar_nota_simulado_aluno(termo_simulado):
        try:
            # Rota 1: Acha qual é a prova de acordo com a série e o termo (ex: "1º Simulado")
            res_p = db_provas.table("modelos_prova").select("id, valor_questao")\
                .ilike("titulo", f"%{ano_ref}%{termo_simulado}%").execute()
            
            if res_p.data:
                p_id = res_p.data[0]['id']
                # Pega o peso/valor de cada questão (se não tiver, assume 1.0 por segurança)
                v_q = float(res_p.data[0].get('valor_questao') or 1.0)
                
                # Rota 2: Busca apenas as respostas deste aluno para esta prova
                res_r = db_provas.table("resultados_provas").select("acertou")\
                    .eq("prova_id", p_id).eq("aluno_id", aluno_id).execute()
                
                if res_r.data:
                    # Conta quantas questões ele acertou (onde 'acertou' é True)
                    qtd_acertos = sum(1 for r in res_r.data if r.get('acertou') is True)
                    
                    # Retorna a Nota Calculada (Acertos × Valor da Questão)
                    return qtd_acertos * v_q
        except Exception:
            pass # Se algo der errado (prova não existe, etc), silenciosamente retorna 0.0
        
        return 0.0

    # =========================================================================
    # 2. EXECUÇÃO DOS CÁLCULOS
    # =========================================================================
    with st.spinner("Calculando desempenho..."):
        # AT1 e AT2 calculadas em tempo real (não ocupam espaço no notas_atividades)
        at1 = buscar_nota_simulado_aluno("1º Simulado")
        at2 = buscar_nota_simulado_aluno("2º Simulado")

        # Busca AT3, AT4, AT5 e N2 (Prova) lançadas no sistema pelo professor
        at3, at4, at5, n2 = 0.0, 0.0, 0.0, 0.0
        try:
            res_notas = db_alunos.table("notas_atividades").select("*").eq("aluno_id", aluno_id).execute()
            if res_notas.data:
                dados = res_notas.data[0]
                at3 = float(dados.get('at3', 0.0) or 0.0)
                at4 = float(dados.get('at4', 0.0) or 0.0)
                at5 = float(dados.get('at5', 0.0) or 0.0)
                n2  = float(dados.get('prova', 0.0) or 0.0)
        except Exception:
            pass # Mantém zerado caso o professor ainda não tenha criado a planilha

        # Matemática da Escola
        soma_n1 = at1 + at2 + at3 + at4 + at5
        media_final = (soma_n1 + n2) / 2

        # =========================================================================
        # 3. EXIBIÇÃO DA TABELA VISUAL
        # =========================================================================
        # Construindo o dataframe idêntico ao painel do professor
        df_notas = pd.DataFrame({
            "AT1 🔒": [at1],
            "AT2 🔒": [at2],
            "AT3": [at3],
            "AT4": [at4],
            "AT5": [at5],
            "Σ N1": [soma_n1],
            "N2 (Prova)": [n2],
            "Média Final": [media_final]
        })

        # Formatação chique: Transforma todos os números em 1 casa decimal (ex: 7.5, 0.0)
        df_notas_formatado = df_notas.map(lambda x: f"{x:.1f}")

        st.markdown("### 📅 Notas do Trimestre")
        
        # Desenha a tabela na tela sem a coluna de índices (0)
        st.dataframe(df_notas_formatado, hide_index=True, use_container_width=True)

        st.caption("🔒 *As colunas AT1 e AT2 são sincronizadas automaticamente com os simulados realizados. Elas refletem a sua pontuação já calculada.*")