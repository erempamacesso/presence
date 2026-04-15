import streamlit as st
import pandas as pd

def mostrar_tela_desempenho(db_alunos, db_provas):
    st.subheader("📊 Histórico de Aprendizagem")
    aluno = st.session_state.aluno
    aluno_id = str(aluno['id'])

    try:
        # 1. BUSCA NOTAS DOS FORMULÁRIOS ONLINE (AT1 e AT2)
        # Buscamos da tabela resultados_provas e somamos por prova_id
        res_provas = db_provas.table("resultados_provas").select("prova_id, acertos").eq("aluno_id", aluno_id).execute()
        
        notas_validas = []
        if res_provas.data:
            # Agrupa para pegar apenas uma nota por prova (caso o aluno tenha enviado mais de uma vez)
            vistas = set()
            for r in res_provas.data:
                p_id = r.get('prova_id')
                if p_id not in vistas:
                    notas_validas.append(float(r.get('acertos', 0)))
                    vistas.add(p_id)

        at1 = notas_validas[0] if len(notas_validas) > 0 else 0.0
        at2 = notas_validas[1] if len(notas_validas) > 1 else 0.0

        # 2. BUSCA NOTAS MANUAIS (AT3, AT4 e Prova)
        at3, at4, n2 = 0.0, 0.0, 0.0
        
        # Usamos um try/except interno aqui para o caso do cache do banco ainda estar offline
        try:
            res_notas = db_alunos.table("notas_atividades").select("*").eq("aluno_id", aluno_id).execute()
            if res_notas.data:
                dados = res_notas.data[0]
                at3 = float(dados.get('at3', 0))
                at4 = float(dados.get('at4', 0))
                n2 = float(dados.get('prova', 0))
        except:
            st.warning("⚠️ Nota do Diário de Classe em sincronização...")

        # 3. CÁLCULOS
        soma_n1 = at1 + at2 + at3 + at4
        media = (soma_n1 + n2) / 2 if (soma_n1 + n2) > 0 else 0.0

        # 4. EXIBIÇÃO DA TABELA (Conforme seu Print 3)
        st.markdown("### 📅 Notas do Trimestre")
        
        dados_tabela = {
            "AT1 🔒": [at1],
            "AT2 🔒": [at2],
            "AT3": [at3],
            "AT4": [at4],
            "N2 (Prova)": [n2],
            "Σ N1": [soma_n1],
            "Média": [media]
        }

        df = pd.DataFrame(dados_tabela)
        
        # Estilização para parecer um boletim
        st.dataframe(
            df.style.format("{:.1f}"),
            hide_index=True,
            use_container_width=True
        )

        st.info("💡 **AT1 e AT2** são preenchidas automaticamente assim que você finaliza os simulados online.")

    except Exception as e:
        st.error(f"Erro ao processar desempenho: {e}")