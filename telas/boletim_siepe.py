import streamlit as st
import pandas as pd
import io

def mostrar_tela_boletim(supabase, supabase_alunos):
    st.title("📝 Meu Registro Pessoal de Notas")
    st.write("As notas do **Simulado** (AT1) são puxadas automaticamente. Use as outras colunas para registros manuais ou importação de provas.")

    try:
        # 1. Busca todos os alunos
        res_a = supabase_alunos.table("alunos").select("*").execute()
        
        if res_a.data:
            df_todos = pd.DataFrame(res_a.data)
            col_t = 'turma' if 'turma' in df_todos.columns else ('serie' if 'serie' in df_todos.columns else None)
            col_n = 'nome' if 'nome' in df_todos.columns else ('Nome' if 'Nome' in df_todos.columns else ('aluno' if 'aluno' in df_todos.columns else None))
            
            if col_t and col_n:
                turmas_list = sorted(df_todos[col_t].dropna().unique())
                turma_sel = st.selectbox("Selecione a Turma para Gerenciar:", turmas_list)
                
                if turma_sel:
                    state_key = f"tabela_notas_{turma_sel}"
                    locked_key = f"colunas_travadas_{turma_sel}"
                    editor_key = f"editor_notas_{turma_sel}"
                    
                    if locked_key not in st.session_state:
                        st.session_state[locked_key] = ['AT1'] # AT1 já nasce travada

                    # =====================================================================
                    # 🤖 AUTOMAÇÃO DA AT1 (BUSCA SIMULADO DO ANO CORRESPONDENTE)
                    # =====================================================================
                    if state_key not in st.session_state:
                        with st.spinner(f"Sincronizando Simulado para {turma_sel}..."):
                            # Filtra alunos apenas desta turma
                            df_turma = df_todos[df_todos[col_t] == turma_sel].copy()
                            df_turma = df_turma.rename(columns={"id": "aluno_id"})

                            # Descobre o ano (2º ou 3º) pela string da turma
                            ano_ref = "2º ano" if "2º" in turma_sel else ("3º ano" if "3º" in turma_sel else "")
                            
                            nota_simulado_mapa = {}
                            if ano_ref:
                                # Busca o ID da prova que seja Simulado daquele ano
                                res_prova_id = supabase.table("modelos_prova")\
                                    .select("id, valor_questao")\
                                    .ilike("titulo", f"%{ano_ref}%Simulado%")\
                                    .execute()
                                
                                if res_prova_id.data:
                                    p_info = res_prova_id.data[0]
                                    # Busca os resultados dessa prova específica
                                    res_simulado = supabase.table("resultados_provas")\
                                        .select("aluno_id, acertou")\
                                        .eq("prova_id", p_info['id'])\
                                        .execute()
                                    
                                    if res_simulado.data:
                                        df_res = pd.DataFrame(res_simulado.data)
                                        df_res['pontos'] = df_res['acertou'].apply(lambda x: 1 if x is True else 0)
                                        df_calc = df_res.groupby('aluno_id')['pontos'].sum().reset_index()
                                        df_calc['nota_final'] = df_calc['pontos'] * float(p_info['valor_questao'])
                                        nota_simulado_mapa = dict(zip(df_calc['aluno_id'].astype(str), df_calc['nota_final']))

                            # Monta a tabela base
                            df_base = df_turma[['aluno_id', col_n]].copy()
                            df_base = df_base.rename(columns={col_n: 'nome'})
                            
                            # Preenche AT1 automaticamente com base no ID do aluno
                            df_base['AT1'] = df_base['aluno_id'].astype(str).map(nota_simulado_mapa).fillna(0.0)
                            
                            # Inicializa demais colunas vazias
                            for c in ['AT2', 'AT3', 'AT4', 'AT5', 'N2']:
                                df_base[c] = 0.0
                            
                            st.session_state[state_key] = df_base.sort_values('nome').reset_index(drop=True)

                    # =====================================================================
                    # ✍️ CÁLCULOS E EDIÇÃO
                    # =====================================================================
                    if editor_key in st.session_state:
                        edicoes = st.session_state[editor_key].get("edited_rows", {})
                        for row_idx, alteracoes in edicoes.items():
                            for col_name, valor in alteracoes.items():
                                st.session_state[state_key].at[row_idx, col_name] = float(valor) if valor is not None else 0.0

                    # Soma N1 (AT1 até AT5) e Média
                    st.session_state[state_key]['N1'] = st.session_state[state_key][['AT1', 'AT2', 'AT3', 'AT4', 'AT5']].sum(axis=1).round(1)
                    st.session_state[state_key]['Média Final'] = ((st.session_state[state_key]['N1'] + st.session_state[state_key]['N2']) / 2).round(1)

                    # =====================================================================
                    # 📥 IMPORTAÇÃO DE OUTRAS PROVAS
                    # =====================================================================
                    with st.expander("📥 Importar Outra Prova (AT2, AT3...)", expanded=False):
                        res_p = supabase.table("modelos_prova").select("id, titulo, valor_questao").order("id", desc=True).execute()
                        if res_p.data:
                            provas_dict = {p['titulo']: p for p in res_p.data}
                            c1, c2 = st.columns(2)
                            prova_esc = c1.selectbox("Selecione a Prova:", list(provas_dict.keys()), key="sel_prova_manual")
                            col_alvo = c2.selectbox("Destino:", ['AT2', 'AT3', 'AT4', 'AT5', 'N2'])
                            
                            if st.button(f"🔒 Importar para {col_alvo}", use_container_width=True):
                                p_obj = provas_dict[prova_esc]
                                res_res = supabase.table("resultados_provas").select("aluno_id, acertou").eq("prova_id", p_obj['id']).execute()
                                if res_res.data:
                                    df_r = pd.DataFrame(res_res.data)
                                    df_r['pts'] = df_r['acertou'].apply(lambda x: 1 if x is True else 0)
                                    df_c = df_r.groupby('aluno_id')['pts'].sum().reset_index()
                                    v_q = float(p_obj['valor_questao'])
                                    mapa_manual = dict(zip(df_c['aluno_id'].astype(str), df_c['pts'] * v_q))
                                    
                                    st.session_state[state_key][col_alvo] = st.session_state[state_key]['aluno_id'].astype(str).map(mapa_manual).fillna(0.0)
                                    if col_alvo not in st.session_state[locked_key]:
                                        st.session_state[locked_key].append(col_alvo)
                                    st.rerun()

                    # =====================================================================
                    # 📝 DATA EDITOR
                    # =====================================================================
                    st.subheader(f"Tabela de Notas: {turma_sel}")
                    
                    config_cols = {
                        "aluno_id": None, "id": None, "unidade": None, "turma": None, "data_atualizacao": None, "rec": None,
                        "nome": st.column_config.TextColumn("Estudante", disabled=True, width="medium"),
                        "N1": st.column_config.NumberColumn("N1 (Soma)", disabled=True, width="small"),
                        "Média Final": st.column_config.NumberColumn("Média", disabled=True, width="small"),
                    }
                    
                    for c in ['AT1', 'AT2', 'AT3', 'AT4', 'AT5', 'N2']:
                        travada = c in st.session_state[locked_key]
                        config_cols[c] = st.column_config.NumberColumn(
                            f"{c} 🔒" if travada else c, 
                            min_value=0.0, max_value=10.0, format="%.1f", 
                            disabled=travada, width="small"
                        )

                    st.data_editor(
                        st.session_state[state_key],
                        key=editor_key,
                        hide_index=True,
                        column_config=config_cols,
                        use_container_width=True,
                        height=400
                    )
                    
                    # =====================================================================
                    # 💾 AÇÕES
                    # =====================================================================
                    cb1, cb2, cb3 = st.columns([2, 2, 1])
                    with cb1:
                        if st.button("💾 Salvar Registros no Banco", type="primary", use_container_width=True):
                            # (Lógica de Upsert idêntica ao anterior, convertendo nomes de colunas)
                            df_save = st.session_state[state_key].copy().rename(columns={'AT1':'at1','AT2':'at2','AT3':'at3','AT4':'at4','N2':'prova'})
                            dados = []
                            for _, r in df_save.iterrows():
                                dados.append({
                                    "aluno_id": r['aluno_id'], "turma": turma_sel, "unidade": "1º Bimestre",
                                    "at1": r.get('at1',0.0), "at2": r.get('at2',0.0), "at3": r.get('at3',0.0), 
                                    "at4": r.get('at4',0.0), "prova": r.get('prova',0.0)
                                })
                            supabase.table("notas_atividades").upsert(dados, on_conflict="aluno_id, unidade").execute()
                            st.success("Salvo com sucesso!")

                    with cb2:
                        # Botão de Excel (já configurado antes)
                        output = io.BytesIO()
                        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                            df_exp = st.session_state[state_key].drop(columns=['aluno_id'], errors='ignore')
                            df_exp.to_excel(writer, sheet_name="Notas", index=False)
                        st.download_button("📥 Baixar Excel", output.getvalue(), f"Notas_{turma_sel}.xlsx", use_container_width=True)

                    with cb3:
                        if st.button("🔄 Recarregar", use_container_width=True):
                            del st.session_state[state_key]
                            st.rerun()

    except Exception as e:
        st.error(f"Erro no Registro: {e}")