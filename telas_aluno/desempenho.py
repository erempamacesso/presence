import streamlit as st
import pandas as pd

def mostrar_tela_desempenho(supabase, supabase_av):
    st.markdown(f"### 📊 Meu Desempenho Acadêmico")
    st.write(f"Olá, **{st.session_state.aluno['nome']}**! Aqui você acompanha suas notas registradas e atividades concluídas.")

    # ==========================================
    # ABA 1: NOTAS DO BIMESTRE (PROJETO CHAMADA)
    # ==========================================
    try:
        # Busca as notas usando o ID do aluno logado
        res_notas = supabase.table("notas_atividades")\
            .select("*")\
            .eq("aluno_id", str(st.session_state.aluno['id']))\
            .eq("unidade", "1º Bimestre")\
            .execute()

        if res_notas.data:
            notas = res_notas.data[0]
            
            # Cálculos automáticos
            n1 = sum([notas.get('at1',0), notas.get('at2',0), notas.get('at3',0), notas.get('at4',0), notas.get('at5',0)])
            n2 = notas.get('prova', 0)
            media = (n1 + n2) / 2

            st.markdown("---")
            st.subheader("📅 1º Trimestre")

            # LINHA ÚNICA COM TODOS OS CAMPOS
            c1, c2, c3, c4, c5, c6 = st.columns(6)
            
            with c1: st.metric("AT1", f"{notas.get('at1', 0):.1f}")
            with c2: st.metric("AT2", f"{notas.get('at2', 0):.1f}")
            with c3: st.metric("AT3", f"{notas.get('at3', 0):.1f}")
            with c4: st.metric("AT4", f"{notas.get('at4', 0):.1f}")
            with c5: st.metric("AT5", f"{notas.get('at5', 0):.1f}")
            with c6: st.metric("PROVA", f"{n2:.1f}")

            # RESUMO FINAL
            st.markdown("---")
            col_res1, col_res2 = st.columns(2)
            
            with col_res1:
                st.markdown(f"**Soma das Atividades (N1):**")
                st.title(f"{n1:.1f}")
            
            with col_res2:
                cor_media = "#00C896" if media >= 6 else "#FF4B4B"
                st.markdown(f"**Média Final:**")
                st.markdown(f"<h1 style='color:{cor_media}; margin-top:-15px;'>{media:.1f}</h1>", unsafe_allow_html=True)

            st.progress(min(media/10, 1.0))
            
        else:
            st.info("Nenhuma nota registrada para o 1º Trimestre ainda.")

    except Exception as e:
        st.error(f"Erro ao carregar as notas: {e}")

    # ==========================================
    # ABA 2: ATIVIDADES CONCLUÍDAS (PROJETO AVALIADOR)
    # ==========================================
    st.markdown("---")
    st.subheader("✅ Atividades e Simulados Concluídos")

    try:
        # 1. Busca os RESULTADOS do aluno na tabela resultados_provas
        res_resultados = supabase_av.table("resultados_provas")\
            .select("*")\
            .eq("aluno_id", str(st.session_state.aluno['id']))\
            .execute()

        if res_resultados.data:
            # Pega todos os IDs de provas que o aluno já fez
            prova_ids = [r['prova_id'] for r in res_resultados.data]
            
            # 2. Busca os NOMES dessas provas na tabela modelos_prova
            res_modelos = supabase_av.table("modelos_prova")\
                .select("id, titulo, materia, serie")\
                .in_("id", prova_ids)\
                .execute()
                
            # Cria um dicionário para cruzar os dados facilmente (id_da_prova -> dados_da_prova)
            dicionario_provas = {p['id']: p for p in res_modelos.data} if res_modelos.data else {}

            # 3. Exibe na tela
            for resultado in res_resultados.data:
                id_prova = resultado['prova_id']
                dados_prova = dicionario_provas.get(id_prova, {})
                
                titulo = dados_prova.get('titulo', 'Atividade Sem Título')
                materia = dados_prova.get('materia', 'Geral')
                serie = dados_prova.get('serie', 'Série não informada')
                pontuacao = resultado.get('pontuacao', 0)
                
                # Formata a data de conclusão
                data_crua = resultado.get('created_at', '')
                data_formatada = "Data desconhecida"
                if data_crua:
                    try:
                        # Pega apenas a parte YYYY-MM-DD e inverte para DD/MM/YYYY
                        dt_obj = pd.to_datetime(data_crua).tz_convert(None)
                        data_formatada = dt_obj.strftime("%d/%m/%Y às %H:%M")
                    except:
                        data_formatada = str(data_crua)[:10]

                # Desenha o card da atividade concluída
                with st.expander(f"📝 {titulo} - {materia}"):
                    col_a, col_b = st.columns(2)
                    col_a.metric("Sua Pontuação", f"{pontuacao}")
                    col_b.write(f"**Série/Turma:** {serie}")
                    col_b.write(f"**Concluído em:** {data_formatada}")
                    st.success("✅ Atividade registrada no sistema!")
        else:
            st.info("Você ainda não concluiu nenhum simulado ou atividade.")

    except Exception as e:
        st.error(f"Aguardando sincronização com o sistema de provas...")