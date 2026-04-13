# telas_aluno/dashboard.py
import streamlit as st
import pandas as pd
from telas_aluno.desempenho import mostrar_tela_desempenho # You already have this file

def mostrar_tela_dashboard(db_provas, supabase_provas_for_desempenho):
    aluno = st.session_state.aluno
    
    st.markdown(f"""
        <div style="margin-bottom: 20px; padding: 15px; background-color: #FFFFFF; border-radius: 15px; border: 1px solid #E2E8F0;">
            <h2 style="margin: 0; color: #1E293B;">👋 Olá, <span style="color: #00C896;">{aluno.get('nome').split()[0]}</span>!</h2>
            <p style="color: #64748b; margin: 0;">{aluno.get('turma')} | Matrícula: {aluno.get('numero_matricula')}</p>
        </div>
    """, unsafe_allow_html=True)

    tab_atividades, tab_perfil = st.tabs(["📝 Atividades Disponíveis", "📊 Meu Desempenho"])

    with tab_atividades:
        with st.spinner("Buscando atividades..."):
            turma_bruta = str(aluno.get('turma', ''))
            serie_aluno = "1º Ano"
            if "2" in turma_bruta: serie_aluno = "2º Ano"
            elif "3" in turma_bruta: serie_aluno = "3º Ano"

            res_p = db_provas.table("modelos_prova").select("*").eq("ativa", True).eq("serie", serie_aluno).execute()
            provas_ativas = res_p.data
            
            ja_fez_dict = {}
            if provas_ativas:
                ids_ativas = [p['id'] for p in provas_ativas]
                res_JF = db_provas.table("resultados_provas").select("prova_id").eq("aluno_id", str(aluno.get('id', ''))).in_("prova_id", ids_ativas).execute()
                ja_fez_dict = {x['prova_id']: True for x in res_JF.data}

            if provas_ativas:
                for p in provas_ativas:
                    foi_feita = ja_fez_dict.get(p['id'], False)
                    if not foi_feita:
                        with st.container(border=True):
                            col_t, col_b = st.columns([3, 1])
                            col_t.markdown(f"### {p['titulo']}")
                            col_t.caption(f"📚 Assunto: {p.get('assunto', 'Geral')}")
                            if col_b.button(f"🚀 Iniciar", key=f"start_{p['id']}", type="primary", use_container_width=True):
                                st.session_state.prova_config = p
                                st.session_state.etapa = "instrucoes"
                                st.rerun()
            else:
                st.info("Nenhuma atividade nova para sua série no momento.")

    with tab_perfil:
        # We call the function from your desempenho.py file here!
        mostrar_tela_desempenho(supabase_provas_for_desempenho)