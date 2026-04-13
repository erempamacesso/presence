import streamlit as st
import pandas as pd
import io

# Trazemos a função de sincronizar para cá também, para não sujar o Dashboard
def sincronizar_atividades_online(supabase, turma_sel, unidade_sel, atividade_id_origem):
    try:
        res = supabase.table("resultados").select("aluno_id, nota").eq("atividade_id", atividade_id_origem).execute()
        if not res.data:
            st.warning(f"Nenhum resultado na atividade {atividade_id_origem}")
            return
        dados_upsert = [{"aluno_id": r["aluno_id"], "turma": turma_sel, "unidade": unidade_sel, "at1": float(r["nota"])} for r in res.data]
        supabase.table("notas_atividades").upsert(dados_upsert, on_conflict="aluno_id, unidade").execute()
        st.success("✅ Notas sincronizadas para AT1!")
    except Exception as e:
        st.error(f"Erro: {e}")

# Transformamos o bloco inteiro em uma função que recebe as conexões do banco
def mostrar_tela_boletim(supabase, supabase_alunos):
    st.title("🏫 Consolidação de Notas SIEPE")
    st.write("Resgate atividades online, importe provas para colunas específicas, ou digite manualmente.")

    try:
        res_a = supabase_alunos.table("alunos").select("*").execute()
        
        if res_a.data:
            df_todos = pd.DataFrame(res_a.data)
            col_t = 'turma' if 'turma' in df_todos.columns else ('serie' if 'serie' in df_todos.columns else None)
            col_n = 'nome' if 'nome' in df_todos.columns else ('Nome' if 'Nome' in df_todos.columns else ('aluno' if 'aluno' in df_todos.columns else None))
            
            if col_t and col_n:
                turmas_list = sorted(df_todos[col_t].dropna().unique())
                turma_sel = st.selectbox("Selecione a Turma:", turmas_list)
                
                if turma_sel:
                    # =====================================================================
                    # 📥 1. RESGATE DE ATIVIDADES ONLINE (Para AT1)
                    # =====================================================================
                    st.divider()
                    st.write("#### 🔄 Resgatar Atividade Online")
                    col_r1, col_r2 = st.columns([1, 2])
                    with col_r1:
                        id_ativ = st.text_input("ID da Ativ. Online (Ex: 10)")
                    with col_r2:
                        st.write("") 
                        if st.button("🔄 Resgatar p/ AT1", use_container_width=True):
                            if id_ativ:
                                # Note que agora passamos o 'supabase' para a função
                                sincronizar_atividades_online(supabase, turma_sel, "1º Bimestre", id_ativ)
                                if f"tabela_notas_{turma_sel}" in st.session_state:
                                    del st.session_state[f"tabela_notas_{turma_sel}"] 
                                st.rerun()
                            else:
                                st.error("Digite o ID da atividade.")

                    # =====================================================================
                    # 🧠 2. GESTÃO DE ESTADO E INTEGRAÇÃO COM BANCO
                    # =====================================================================
                    state_key = f"tabela_notas_{turma_sel}"
                    locked_key = f"colunas_travadas_{turma_sel}"
                    editor_key = f"editor_notas_{turma_sel}"
                    
                    if locked_key not in st.session_state:
                        st.session_state[locked_key] = []

                    if state_key not in st.session_state:
                        df_turma = df_todos[df_todos[col_t] == turma_sel].copy()
                        df_turma = df_turma.rename(columns={"id": "aluno_id"}) 
                        
                        res_notas = supabase.table("notas_atividades").select("*").eq("turma", turma_sel).eq("unidade", "1º Bimestre").execute()
                        df_notas = pd.DataFrame(res_notas.data)
                        
                        if not df_notas.empty:
                            df_base = pd.merge(df_turma[['aluno_id', col_n]], df_notas, on="aluno_id", how="left")
                            df_base = df_base.fillna(0.0) 
                        else:
                            df_base = df_turma[['aluno_id', col_n]].copy()
                            for c in ['at1', 'at2', 'at3', 'at4', 'prova', 'rec']: 
                                df_base[c] = 0.0
                            
                        df_base = df_base.rename(columns={col_n: 'nome', 'at1': 'AT1', 'at2': 'AT2', 'at3': 'AT3', 'at4': 'AT4', 'prova': 'N2'})
                        
                        if 'AT5' not in df_base.columns: df_base['AT5'] = 0.0
                        if 'N1' not in df_base.columns: df_base['N1'] = 0.0
                        if 'Média Final' not in df_base.columns: df_base['Média Final'] = 0.0
                            
                        st.session_state[state_key] = df_base.sort_values('nome').reset_index(drop=True)

                    # =====================================================================
                    # ✍️ 3. CAPTURA EDIÇÃO MANUAL E CÁLCULOS
                    # =====================================================================
                    if editor_key in st.session_state:
                        edicoes = st.session_state[editor_key].get("edited_rows", {})
                        for row_idx, alteracoes in edicoes.items():
                            for col_name, valor in alteracoes.items():
                                st.session_state[state_key].at[row_idx, col_name] = float(valor) if valor is not None else 0.0

                    st.session_state[state_key]['N1'] = st.session_state[state_key][['AT1', 'AT2', 'AT3', 'AT4', 'AT5']].sum(axis=1).round(1)
                    st.session_state[state_key]['Média Final'] = ((st.session_state[state_key]['N1'] + st.session_state[state_key]['N2']) / 2).round(1)

                    # =====================================================================
                    # 📥 4. IMPORTAÇÃO DE PROVAS (E TRAVAMENTO)
                    # =====================================================================
                    st.divider()
                    with st.expander("📥 Importar Prova Oficial e Travar Coluna", expanded=False):
                        res_p = supabase.table("modelos_prova").select("id, titulo, valor_questao").order("id", desc=True).execute()
                        
                        if res_p.data:
                            provas_dict = {p['titulo']: p for p in res_p.data}
                            col_i1, col_i2 = st.columns(2)
                            
                            prova_escolhida = col_i1.selectbox("Selecione a Prova:", list(provas_dict.keys()))
                            coluna_alvo = col_i2.selectbox("Destino (Travar coluna):", ['AT1', 'AT2', 'AT3', 'AT4', 'AT5', 'N2'])
                            
                            if st.button(f"🔒 Importar e Travar {coluna_alvo}", use_container_width=True):
                                p_obj = provas_dict[prova_escolhida]
                                res_res = supabase.table("resultados_provas").select("*").eq("prova_id", p_obj['id']).execute()
                                
                                if res_res.data:
                                    df_res = pd.DataFrame(res_res.data)
                                    df_res['acertos'] = df_res['acertou'].apply(lambda x: 1 if x is True else 0)
                                    df_calc = df_res.groupby('aluno_id')['acertos'].sum().reset_index()
                                    df_calc['nota'] = df_calc['acertos'] * float(p_obj['valor_questao'])
                                    
                                    res_n = supabase_alunos.table("alunos").select("id, nome").in_("id", df_calc['aluno_id'].astype(str).tolist()).execute()
                                    mapa = {str(item['id']): item['nome'] for item in res_n.data}
                                    df_calc['nome_aluno'] = df_calc['aluno_id'].astype(str).map(mapa)
                                    mapa_notas = dict(zip(df_calc['nome_aluno'], df_calc['nota']))
                                    
                                    st.session_state[state_key][coluna_alvo] = st.session_state[state_key]['nome'].map(mapa_notas).fillna(0.0)
                                    if coluna_alvo not in st.session_state[locked_key]:
                                        st.session_state[locked_key].append(coluna_alvo)
                                    
                                    st.success(f"✅ Coluna {coluna_alvo} preenchida e bloqueada!")
                                    st.rerun()

                    # =====================================================================
                    # 📝 5. EDITOR DE NOTAS (COM TRAVAMENTO DINÂMICO)
                    # =====================================================================
                    st.subheader(f"Planilha de Notas: {turma_sel}")
                    
                    config_colunas = {
                        "aluno_id": None, 
                        "id": None,
                        "unidade": None,
                        "turma": None,
                        "data_atualizacao": None,
                        "rec": None,
                        "nome": st.column_config.TextColumn("Estudante", disabled=True, width="medium"),
                        "N1": st.column_config.NumberColumn("N1 (Soma)", disabled=True, width="small"),
                        "Média Final": st.column_config.NumberColumn("Média", disabled=True, width="small"),
                    }
                    
                    for c in ['AT1', 'AT2', 'AT3', 'AT4', 'AT5', 'N2']:
                        esta_travada = c in st.session_state[locked_key]
                        label = f"{c} 🔒" if esta_travada else c
                        config_colunas[c] = st.column_config.NumberColumn(
                            label, min_value=0.0, max_value=10.0, format="%.1f", disabled=esta_travada, width="small"
                        )

                    st.data_editor(
                        st.session_state[state_key],
                        key=editor_key,
                        hide_index=True,
                        use_container_width=False,
                        column_config=config_colunas,
                        height=(len(st.session_state[state_key]) + 1) * 35 + 40
                    )
                    
                    # =====================================================================
                    # 💾 6. BOTÕES DE AÇÃO (SALVAR NO BANCO E BAIXAR)
                    # =====================================================================
                    col_b1, col_b2, col_b3 = st.columns([2, 2, 1])
                    
                    with col_b1:
                        if st.button("💾 Salvar Planilha no Banco de Dados", type="primary", use_container_width=True):
                            with st.spinner("Salvando notas..."):
                                df_salvar = st.session_state[state_key].copy()
                                df_salvar = df_salvar.rename(columns={'AT1': 'at1', 'AT2': 'at2', 'AT3': 'at3', 'AT4': 'at4', 'N2': 'prova'})
                                
                                dados_upsert = []
                                for _, row in df_salvar.iterrows():
                                    dados_upsert.append({
                                        "aluno_id": row['aluno_id'],
                                        "turma": turma_sel,
                                        "unidade": "1º Bimestre",
                                        "at1": row.get('at1', 0.0), 
                                        "at2": row.get('at2', 0.0), 
                                        "at3": row.get('at3', 0.0), 
                                        "at4": row.get('at4', 0.0), 
                                        "prova": row.get('prova', 0.0)
                                    })
                                
                                try:
                                    supabase.table("notas_atividades").upsert(dados_upsert, on_conflict="aluno_id, unidade").execute()
                                    st.success("✅ Notas salvas permanentemente!")
                                except Exception as e:
                                    st.error(f"Erro ao salvar: {e}")

                    with col_b2:
                        output = io.BytesIO()
                        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                            df_export = st.session_state[state_key].drop(columns=['aluno_id', 'id', 'unidade', 'turma', 'data_atualizacao', 'rec'], errors='ignore')
                            df_export.to_excel(writer, sheet_name="SIEPE", index=False)
                        
                        st.download_button(
                            label="📥 Baixar Planilha para o SIEPE",
                            data=output.getvalue(),
                            file_name=f"SIEPE_{turma_sel}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            type="secondary",
                            use_container_width=True
                        )
                        
                    with col_b3:
                        if st.button("🔓 Resetar Travas", type="secondary", use_container_width=True):
                            st.session_state[locked_key] = []
                            st.rerun()

            else:
                st.error("Colunas de 'turma' ou 'nome' não encontradas.")
        else:
            st.info("Nenhum aluno encontrado.")
            
    except Exception as e:
        st.error(f"Erro no Boletim: {e}")
    