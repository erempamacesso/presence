import streamlit as st
import pandas as pd

def mostrar_tela_desempenho(supabase_chamada, supabase_av):
    aluno = st.session_state.aluno
    st.markdown(f"### 📊 Histórico de Aprendizagem")
    st.write(f"Olá, **{aluno['nome']}**! Aqui está o resumo das suas avaliações.")

    # ==========================================
    # 1. NOTAS OFICIAIS (PROJETO SIGEREMPAM)
    # ==========================================
    st.markdown("#### 📅 Notas do Trimestre (Diário de Classe)")
    try:
        # Busca as notas na tabela do projeto de chamada
        res_notas = supabase_chamada.table("notas_atividades")\
            .select("*")\
            .eq("aluno_id", str(aluno['id']))\
            .execute()
        
        if res_notas.data:
            # Pegamos o registro mais recente ou filtramos por unidade se necessário
            notas = res_notas.data[0] 
            
            # Cálculo de Médias (Lógica padrão de N1 e N2)
            n1 = sum([
                notas.get('at1', 0) or 0, 
                notas.get('at2', 0) or 0, 
                notas.get('at3', 0) or 0, 
                notas.get('at4', 0) or 0, 
                notas.get('at5', 0) or 0
            ])
            n2 = notas.get('prova', 0) or 0
            media = (n1 + n2) / 2

            # Layout de Métricas
            cols = st.columns(6)
            campos = ['at1', 'at2', 'at3', 'at4', 'at5', 'prova']
            for i, campo in enumerate(campos):
                valor = notas.get(campo, 0) or 0
                cols[i].metric(campo.upper(), f"{valor:.1f}")

            # Resumo Visual
            st.markdown("---")
            c_res1, c_res2, c_res3 = st.columns([1, 1, 2])
            
            c_res1.markdown(f"**Soma Atividades (N1):**\n## {n1:.1f}")
            
            cor_media = "#00C896" if media >= 6 else "#FF4B4B"
            c_res2.markdown(f"**Média Final:**\n<h2 style='color:{cor_media};'>{media:.1f}</h2>", unsafe_allow_html=True)
            
            with c_res3:
                st.markdown("**Progresso para Aprovação**")
                st.progress(min(media/10, 1.0))
        else:
            st.info("As notas deste trimestre ainda não foram lançadas pelo professor.")
            
    except Exception as e:
        st.error(f"Não foi possível carregar as notas do diário: {e}")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("---")

    # ==========================================
    # 2. ATIVIDADES DO PORTAL (PROJETO AVALIADOR)
    # ==========================================
    st.markdown("#### ✅ Atividades e Simulados Concluídos")
    try:
        # 1. Busca os resultados
        res_res = supabase_av.table("resultados_provas")\
            .select("*")\
            .eq("aluno_id", str(aluno['id']))\
            .order("created_at", desc=True)\
            .execute()

        if res_res.data:
            # 2. Busca informações das provas para mostrar o título
            ids_provas = list(set([r['prova_id'] for r in res_res.data]))
            res_mod = supabase_av.table("modelos_prova")\
                .select("id, titulo, materia")\
                .in_("id", ids_provas)\
                .execute()
            
            mapa_provas = {p['id']: p for p in res_mod.data}

            # 3. Renderiza os cards
            for r in res_res.data:
                info = mapa_provas.get(r['prova_id'], {})
                titulo = info.get('titulo', f"Atividade {r['prova_id']}")
                materia = info.get('materia', "Geral")
                
                # Formatação de data amigável
                try:
                    data_conclusao = pd.to_datetime(r['created_at']).strftime('%d/%m/%Y às %H:%M')
                except:
                    data_conclusao = r['created_at']

                with st.expander(f"📝 {titulo} - {materia}"):
                    col1, col2 = st.columns(2)
                    
                    # Nota/Pontuação
                    pontos = r.get('pontuacao', 0)
                    col1.metric("Sua Pontuação", f"{pontos}")
                    
                    # Detalhes
                    col2.write(f"**Finalizado em:** {data_conclusao}")
                    col2.write(f"**Status:** Processado com sucesso ✅")
                    
                    if st.button("Ver Detalhes/Revisão", key=f"rev_{r['id']}"):
                        st.info("A revisão detalhada das questões estará disponível em breve.")
        else:
            st.info("Você ainda não realizou simulados ou atividades neste portal.")
            
    except Exception as e:
        st.warning(f"Erro ao carregar histórico de atividades: {e}")