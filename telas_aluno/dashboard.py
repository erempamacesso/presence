import streamlit as st
import pandas as pd
from telas_aluno.desempenho import mostrar_tela_desempenho 

def mostrar_tela_dashboard(db_provas, supabase_provas_for_desempenho):
    aluno = st.session_state.aluno
    
    # Cabeçalho de Boas Vindas
    st.markdown(f"""
        <div style="margin-bottom: 20px; padding: 15px; background-color: #FFFFFF; border-radius: 15px; border: 1px solid #E2E8F0;">
            <h2 style="margin: 0; color: #1E293B;">👋 Olá, <span style="color: #00C896;">{aluno.get('nome').split()[0]}</span>!</h2>
            <p style="color: #64748b; margin: 0;">{aluno.get('turma')} | Matrícula: {aluno.get('numero_matricula')}</p>
        </div>
    """, unsafe_allow_html=True)

    # Criação das 3 abas
    tab_atividades, tab_concluidas, tab_perfil = st.tabs(["📝 Novas Atividades", "✅ Concluídas", "📊 Meu Desempenho"])

    with st.spinner("Buscando atividades..."):
        turma_bruta = str(aluno.get('turma', ''))
        serie_aluno = "1º Ano"
        if "2" in turma_bruta: serie_aluno = "2º Ano"
        elif "3" in turma_bruta: serie_aluno = "3º Ano"

        # Busca provas ativas para a série do aluno
        res_p = db_provas.table("modelos_prova").select("*").eq("ativa", True).eq("serie", serie_aluno).execute()
        provas_ativas = res_p.data
        
        # Verifica quais provas o aluno já fez
        ja_fez_dict = {}
        if provas_ativas:
            ids_ativas = [p['id'] for p in provas_ativas]
            res_JF = db_provas.table("resultados_provas").select("prova_id").eq("aluno_id", str(aluno.get('id', ''))).in_("prova_id", ids_ativas).execute()
            ja_fez_dict = {x['prova_id']: True for x in res_JF.data}

    # --- ABA 1: PROVAS PENDENTES ---
    with tab_atividades:
        tem_nova = False
        if provas_ativas:
            for p in provas_ativas:
                foi_feita = ja_fez_dict.get(p['id'], False)
                if not foi_feita:
                    tem_nova = True
                    with st.container(border=True):
                        col_t, col_b = st.columns([3, 1])
                        col_t.markdown(f"### {p['titulo']}")
                        col_t.caption(f"📚 Assunto: {p.get('assunto', 'Geral')} | ⏱️ {p.get('tempo_duracao', 0)} min")
                        
                        if col_b.button(f"🚀 Iniciar", key=f"start_{p['id']}", type="primary", use_container_width=True):
                            st.session_state.prova_config = p
                            st.session_state.etapa = "instrucoes"
                            st.rerun()
        
        if not tem_nova:
            st.info("🎉 Parabéns! Você não tem nenhuma atividade nova pendente.")

    # --- ABA 2: PROVAS CONCLUÍDAS (A QUE FALTAVA!) ---
    with tab_concluidas:
        tem_concluida = False
        if provas_ativas:
            for p in provas_ativas:
                foi_feita = ja_fez_dict.get(p['id'], False)
                if foi_feita:
                    tem_concluida = True
                    with st.container(border=True):
                        col_t, col_b = st.columns([3, 1])
                        col_t.markdown(f"### {p['titulo']}")
                        col_t.caption("✅ Atividade já realizada")
                        
                        # AQUI ESTÁ A MÁGICA! O botão que leva para o seu código de resultados
                        if col_b.button(f"🔍 Ver Resultado", key=f"res_{p['id']}", use_container_width=True):
                            st.session_state.prova_resultado = p
                            st.session_state.etapa = "ver_meu_resultado"
                            st.rerun()
        
        if not tem_concluida:
            st.info("Você ainda não concluiu nenhuma atividade desta lista.")

    # --- ABA 3: DESEMPENHO TRIMESTRAL ---
    with tab_perfil:
        mostrar_tela_desempenho(supabase_provas_for_desempenho)