import streamlit as st
import pandas as pd
import io

def mostrar_tela_boletim(supabase, supabase_alunos):
    st.title("📝 Meu Registro Pessoal de Notas")
    st.info("AT1 e AT2: Simulados Online (Automático) | AT3, AT4 e AT5: Notas Diversas (Manual)")

    try:
        # 1. Busca todos os alunos
        res_a = supabase_alunos.table("alunos").select("*").execute()
        
        if res_a.data:
            df_todos = pd.DataFrame(res_a.data)
            col_t = 'turma' if 'turma' in df_todos.columns else ('serie' if 'serie' in df_todos.columns else None)
            col_n = 'nome' if 'nome' in df_todos.columns else ('Nome' if 'Nome' in df_todos.columns else ('aluno' if 'aluno' in df_todos.columns else None))
            
            if col_t and col_n:
                turmas_list = sorted(df_todos[col_t].dropna().unique())
                turma_sel = st.selectbox("Selecione a Turma:", turmas_list)
                
                if turma_sel:
                    state_key = f"tabela_notas_{turma_sel}"
                    editor_key = f"editor_notas_{turma_sel}"
                    
                    # AT1 e AT2 sempre travadas por serem automáticas
                    locked_cols = ['AT1', 'AT2']

                    if state_key not in st.session_state:
                        with st.spinner(f"Sincronizando Simulados para {turma_sel}..."):
                            df_turma = df_todos[df_todos[col_t] == turma_sel].copy()
                            df_turma = df_turma.rename(columns={"id": "aluno_id"})
                            ano_ref = "2º ano" if "2º" in turma_sel else ("3º ano" if "3º" in turma_sel else "")
                            
                            def buscar_nota_simulado(termo_simulado):
                                mapa_notas = {}
                                if ano_ref:
                                    res_p = supabase.table("modelos_prova").select("id, valor_questao")\
                                        .ilike("titulo", f"%{ano_ref}%{termo_simulado}%").execute()
                                    
                                    if res_p.data:
                                        p_id = res_p.data[0]['id']
                                        v_q = float(res_p.data[0]['valor_questao'])
                                        res_r = supabase.table("resultados_provas").select("aluno_id, acertou")\
                                            .eq("prova_id", p_id).execute()
                                        
                                    if res_r.data:
                                        df_r = pd.DataFrame(res_r.data)
                                        df_r['pts'] = df_r['acertou'].apply(lambda x: 1 if x is True else 0)
                                        df_c = df_r.groupby('aluno_id')['pts'].sum().reset_index()
                                        
                                        # 1. Calcula a nota bruta (acertos * valor da questao)
                                        df_c['nota_bruta'] = df_c['pts'] * v_q
                                        
                                        # 2. Aplica a mágica: Arredonda para múltiplos de 0.5
                                        df_c['nota_arredondada'] = (df_c['nota_bruta'] * 2).round() / 2
                                        
                                        # 3. Monta o dicionário final para a tabela
                                        mapa_notas = dict(zip(df_c['aluno_id'].astype(str), df_c['nota_arredondada']))
                                        
                                        return mapa_notas

                            mapa_at1 = buscar_nota_simulado("1º Simulado")
                            mapa_at2 = buscar_nota_simulado("2º Simulado")

                            df_base = df_turma[['aluno_id', col_n]].copy().rename(columns={col_n: 'nome'})
                            df_base['AT1'] = df_base['aluno_id'].astype(str).map(mapa_at1).fillna(0.0)
                            df_base['AT2'] = df_base['aluno_id'].astype(str).map(mapa_at2).fillna(0.0)
                            
                            for c in ['AT3', 'AT4', 'AT5', 'N2']:
                                df_base[c] = 0.0
                            
                            st.session_state[state_key] = df_base.sort_values('nome').reset_index(drop=True)

                    # --- CÁLCULOS DINÂMICOS ---
                    if editor_key in st.session_state:
                        edicoes = st.session_state[editor_key].get("edited_rows", {})
                        for row_idx, alteracoes in edicoes.items():
                            for col_name, valor in alteracoes.items():
                                st.session_state[state_key].at[row_idx, col_name] = float(valor) if valor is not None else 0.0

                    st.session_state[state_key]['N1'] = st.session_state[state_key][['AT1', 'AT2', 'AT3', 'AT4', 'AT5']].sum(axis=1).round(1)
                    st.session_state[state_key]['Média Final'] = ((st.session_state[state_key]['N1'] + st.session_state[state_key]['N2']) / 2).round(1)

                    # --- DATA EDITOR COM ALTURA DINÂMICA ---
                    st.subheader(f"Planilha de Notas - {turma_sel}")
                    
                    config_cols = {
                        "aluno_id": None, "nome": st.column_config.TextColumn("Estudante", disabled=True, width="medium"),
                        "N1": st.column_config.NumberColumn("Σ N1", disabled=True, width="small"),
                        "Média Final": st.column_config.NumberColumn("Média", disabled=True, width="small"),
                    }
                    
                    for c in ['AT1', 'AT2', 'AT3', 'AT4', 'AT5', 'N2']:
                        travada = (c in locked_cols)
                        config_cols[c] = st.column_config.NumberColumn(
                            f"{c} 🔒" if travada else c, 
                            min_value=0.0, max_value=10.0, step=0.1, format="%.1f",
                            disabled=travada, width="small"
                        )

                    # --- O AJUSTE ESTÁ AQUI ---
                    # Calculamos a altura: (nº de linhas + 1 do header) * 35 pixels + 3 de borda
                    altura_dinamica = (len(st.session_state[state_key]) + 1) * 35 + 3

                    st.data_editor(
                        st.session_state[state_key],
                        key=editor_key,
                        hide_index=True,
                        column_config=config_cols,
                        use_container_width=True,
                        height=altura_dinamica  # <--- Aplicando a altura calculada
                    )
                    
                    # --- BOTÕES DE AÇÃO ---
                    col_b1, col_b2, col_b3 = st.columns([2, 2, 1])
                    
                    with col_b1:
                        if st.button("💾 Salvar no Banco (notas_atividades)", type="primary", use_container_width=True):
                            with st.spinner("Registrando notas..."):
                                df_save = st.session_state[state_key].copy()
                                dados_upsert = []
                                for _, r in df_save.iterrows():
                                    dados_upsert.append({
                                        "aluno_id": r['aluno_id'],
                                        "turma": turma_sel,
                                        "unidade": "1º Bimestre",
                                        "at1": float(r['AT1']),
                                        "at2": float(r['AT2']),
                                        "at3": float(r['AT3']),
                                        "at4": float(r['AT4']),
                                        "at5": float(r['AT5']),
                                        "prova": float(r['N2'])
                                    })
                                try:
                                    supabase.table("notas_atividades").upsert(dados_upsert, on_conflict="aluno_id, unidade").execute()
                                    st.success(f"✅ Notas da turma {turma_sel} salvas!")
                                except Exception as e:
                                    st.error(f"Erro ao salvar: {e}")

                    with col_b2:
                        output = io.BytesIO()
                        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                            df_exp = st.session_state[state_key].drop(columns=['aluno_id'], errors='ignore')
                            df_exp.to_excel(writer, sheet_name="Notas", index=False)
                        st.download_button("📥 Baixar Planilha", output.getvalue(), f"Notas_{turma_sel}.xlsx", use_container_width=True)

                    with col_b3:
                        if st.button("🔄 Recarregar", use_container_width=True):
                            if state_key in st.session_state: del st.session_state[state_key]
                            st.rerun()

    except Exception as e:
        st.error(f"Ocorreu um erro: {e}")