import streamlit as st
import pandas as pd
import io
import math

# --- FUNÇÃO OFICIAL DE ARREDONDAMENTO SIEPE ---
def arredondar_siepe(nota):
    """
    Regra de arredondamento:
    ,0 e ,1 -> ,0
    ,2 a ,6 -> ,5
    ,7 a ,9 -> +1,0 (próximo número inteiro)
    """
    if pd.isna(nota) or nota is None:
        return 0.0
        
    nota = float(nota)
    inteiro = math.floor(nota)
    decimal = round((nota - inteiro) * 10)
    
    if decimal in [0, 1]:
        return float(inteiro)
    elif decimal in [2, 3, 4, 5, 6]:
        return float(inteiro + 0.5)
    else: # 7, 8, 9, 10
        return float(inteiro + 1)


import streamlit as st
import pandas as pd
import io
import math

# --- FUNÇÃO OFICIAL DE ARREDONDAMENTO SIEPE ---
def arredondar_siepe(nota):
    if pd.isna(nota) or nota is None:
        return 0.0
        
    nota = float(nota)
    inteiro = math.floor(nota)
    decimal = round((nota - inteiro) * 10)
    
    if decimal in [0, 1]:
        return float(inteiro)
    elif decimal in [2, 3, 4, 5, 6]:
        return float(inteiro + 0.5)
    else: 
        return float(inteiro + 1)

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
            
            # PROTEÇÃO: Se a coluna id_siepe não existir no banco ainda, cria uma vazia
            if 'id_siepe' not in df_todos.columns:
                df_todos['id_siepe'] = ""
            
            if col_t and col_n:
                turmas_list = sorted(df_todos[col_t].dropna().unique())
                turma_sel = st.selectbox("Selecione a Turma:", turmas_list)
                
                if turma_sel:
                    state_key = f"tabela_notas_{turma_sel}"
                    editor_key = f"editor_notas_{turma_sel}"
                    locked_cols = ['AT1', 'AT2']

                    # --- INICIALIZAÇÃO DO ESTADO DA TURMA ---
                    if state_key not in st.session_state:
                        with st.spinner(f"Sincronizando dados de {turma_sel}..."):
                            df_turma = df_todos[df_todos[col_t] == turma_sel].copy()
                            df_turma = df_turma.rename(columns={"id": "aluno_id"})
                            ano_ref = "2º ano" if "2º" in turma_sel else ("3º ano" if "3º" in turma_sel else "")
                            
                            def buscar_nota_simulado(termo_simulado, limite_nota=10.0):
                                mapa_notas = {}
                                if ano_ref:
                                    res_p = supabase.table("modelos_prova").select("id, valor_questao")\
                                        .ilike("titulo", f"%{ano_ref}%{termo_simulado}%").execute()
                                    if res_p.data:
                                        p_id = res_p.data[0]['id']
                                        v_q = float(res_p.data[0].get('valor_questao') or 1.0)
                                        res_r = supabase.table("resultados_provas").select("aluno_id, acertou").eq("prova_id", p_id).execute()
                                        if res_r.data:
                                            df_r = pd.DataFrame(res_r.data)
                                            df_r['pts'] = df_r['acertou'].apply(lambda x: 1 if x is True else 0)
                                            df_c = df_r.groupby('aluno_id')['pts'].sum().reset_index()
                                            df_c['nota_arredondada'] = (df_c['pts'] * v_q).clip(upper=limite_nota).apply(arredondar_siepe)
                                            mapa_notas = dict(zip(df_c['aluno_id'].astype(str), df_c['nota_arredondada']))
                                return mapa_notas

                            mapa_at1 = buscar_nota_simulado("1º Simulado", limite_nota=4.0)
                            mapa_at2 = buscar_nota_simulado("2º Simulado", limite_nota=4.0)

                            # INJEÇÃO: Incluímos o 'id_siepe' no DataFrame Base
                            df_base = df_turma[['aluno_id', col_n, 'id_siepe']].copy().rename(columns={col_n: 'nome'})
                            df_base['AT1'] = df_base['aluno_id'].astype(str).map(mapa_at1).fillna(0.0)
                            df_base['AT2'] = df_base['aluno_id'].astype(str).map(mapa_at2).fillna(0.0)
                            
                            # Busca notas manuais
                            res_notas_salvas = supabase.table("notas_atividades").select("*").eq("turma", turma_sel).eq("unidade", "1º Bimestre").execute()
                            mapa_at3, mapa_at4, mapa_at5, mapa_n2 = {}, {}, {}, {}
                            
                            if res_notas_salvas.data:
                                for r in res_notas_salvas.data:
                                    aid = str(r['aluno_id'])
                                    mapa_at3[aid], mapa_at4[aid], mapa_at5[aid] = float(r.get('at3') or 0.0), float(r.get('at4') or 0.0), float(r.get('at5') or 0.0)
                                    mapa_n2[aid] = float(r.get('prova') or 0.0)
                            
                            df_base['AT3'] = df_base['aluno_id'].astype(str).map(mapa_at3).fillna(0.0)
                            df_base['AT4'] = df_base['aluno_id'].astype(str).map(mapa_at4).fillna(0.0)
                            df_base['AT5'] = df_base['aluno_id'].astype(str).map(mapa_at5).fillna(0.0)
                            df_base['N2']  = df_base['aluno_id'].astype(str).map(mapa_n2).fillna(0.0)
                            
                            st.session_state[state_key] = df_base.sort_values('nome').reset_index(drop=True)

                    # --- ÁREA DE IMPORTAÇÃO CSV (LÓGICA ADITIVA) ---
                    st.subheader(f"Planilha de Notas - {turma_sel}")
                    
                    with st.expander("📥 Importar e SOMAR Notas de Prova (N2) via CSV", expanded=False):
                        arquivo_csv = st.file_uploader("Upload do CSV (Ex: csv_3a.csv)", type="csv", key=f"up_{turma_sel}")
                        
                        if arquivo_csv:
                            try:
                                df_csv = pd.read_csv(arquivo_csv, encoding='latin-1', sep=None, engine='python')
                                if 'QUÍMICA' in df_csv.columns:
                                    df_csv['QUÍMICA'] = pd.to_numeric(df_csv['QUÍMICA'], errors='coerce').fillna(0.0)
                                
                                if st.button("🚀 Somar Notas do CSV ao N2 Atual", use_container_width=True):
                                    df_atual = st.session_state[state_key].copy()
                                    df_csv['n_match'] = df_csv['Name'].astype(str).str.strip().str.lower()
                                    df_atual['n_match'] = df_atual['nome'].astype(str).str.strip().str.lower()
                                    mapa_csv = dict(zip(df_csv['n_match'], df_csv['QUÍMICA']))
                                    
                                    count = 0
                                    for idx, row in df_atual.iterrows():
                                        nome_aluno = row['n_match']
                                        if nome_aluno in mapa_csv:
                                            valor_existente = float(row['N2']) if not pd.isna(row['N2']) else 0.0
                                            nota_csv = float(mapa_csv[nome_aluno])
                                            df_atual.at[idx, 'N2'] = valor_existente + nota_csv
                                            count += 1
                                    
                                    st.session_state[state_key] = df_atual.drop(columns=['n_match'])
                                    st.success(f"✅ {count} notas processadas e somadas com sucesso!")
                                    st.rerun()
                                    
                            except Exception as e:
                                st.error(f"Erro no processamento do CSV: {e}")

                    # --- CÁLCULOS DINÂMICOS E ESTILIZAÇÃO ---
                    if editor_key in st.session_state:
                        edicoes = st.session_state[editor_key].get("edited_rows", {})
                        for row_idx, alteracoes in edicoes.items():
                            for col_name, valor in alteracoes.items():
                                st.session_state[state_key].at[row_idx, col_name] = float(valor) if valor is not None else 0.0

                    df_view = st.session_state[state_key].copy()
                    df_view['N1'] = df_view[['AT1', 'AT2', 'AT3', 'AT4', 'AT5']].sum(axis=1).apply(arredondar_siepe)
                    df_view['Média Final'] = ((df_view['N1'] + df_view['N2']) / 2).apply(arredondar_siepe)

                    def aplicar_cores(val):
                        try:
                            return 'color: #1d4ed8; font-weight: bold;' if float(val) > 0 else 'color: #9ca3af;'
                        except: return ''

                    df_estilizado = df_view.style.map(aplicar_cores, subset=['AT1', 'AT2', 'N1', 'Média Final'])

                    # --- CONFIGURAÇÃO E EXIBIÇÃO DO EDITOR ---
                    config_cols = {
                        "aluno_id": None, 
                        "id_siepe": None, # INJEÇÃO: Oculta o ID do SIEPE na tela
                        "nome": st.column_config.TextColumn("Estudante", disabled=True, width="medium"),
                        "N1": st.column_config.NumberColumn("Σ N1 🔒", disabled=True, format="%.1f"),
                        "Média Final": st.column_config.NumberColumn("Média 🔒", disabled=True, format="%.1f"),
                    }
                    for c in ['AT1', 'AT2', 'AT3', 'AT4', 'AT5', 'N2']:
                        travada = (c in locked_cols)
                        config_cols[c] = st.column_config.NumberColumn(
                            f"{c} 🔒" if travada else c, 
                            min_value=0.0, max_value=10.0, step=0.1, format="%.1f", 
                            disabled=travada
                        )

                    st.data_editor(
                        df_estilizado, 
                        key=editor_key, 
                        hide_index=True, 
                        column_config=config_cols, 
                        use_container_width=True, 
                        height=(len(df_view)+1)*35+5
                    )
                    
                    # --- NOVO ALINHAMENTO DE QUATRO COLUNAS DE BOTÕES (Indentação corrigida) ---
                    col_b1, col_b2, col_b3, col_b4 = st.columns([2, 2, 2, 1])
                    
                    with col_b1:
                        if st.button("💾 Salvar no Banco (notas_atividades)", type="primary", use_container_width=True):
                            with st.spinner("Salvando no banco de dados..."):
                                dados_upsert = []
                                for _, r in df_view.iterrows():
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
                                supabase.table("notas_atividades").upsert(dados_upsert, on_conflict="aluno_id, unidade").execute()
                                st.success("✅ Notas salvas no banco!")

                    with col_b2:
                        if st.button("🚀 Sincronizar Direto com SIEPE", use_container_width=True):
                            from siepe_api import SiepeClient
                            
                            with st.spinner("Autenticando no SIEPE..."):
                                client = SiepeClient()
                                usuario = st.secrets["SIEPE_USER"]
                                senha = st.secrets["SIEPE_PASS"]
                                
                                logado, msg_log = client.fazer_login(usuario, senha)
                                
                                if logado:
                                    # INJEÇÃO: Mapeamento de turmas. Substitua os valores abaixo pelos seus reais.
                                    mapa_turmas_siepe = {
                                        "2º ANO INTEGRAL - A": {"id": "2483", "ew_base": "133670472", "ew_id": "138398494"},
                                        "2º ANO INTEGRAL - B": {"id": "2483", "ew_base": "122549628", "ew_id": "126982310"},
                                        "3º ANO INTEGRAL - A": {"id": "2482", "ew_base": "122549628", "ew_id": "126982310"}
                                    }
                                    
                                    dados_turma = mapa_turmas_siepe.get(turma_sel, {})
                                    
                                    if not dados_turma:
                                        st.error(f"⚠️ Configure os IDs do SIEPE para a turma '{turma_sel}' no código!")
                                    else:
                                        contexto_requisicao = {
                                            "turma_id": dados_turma["id"],       
                                            "disciplina_id": "1132",  
                                            "ew_base": dados_turma["ew_base"],
                                            "ew_id": dados_turma["ew_id"],
                                            "bimestre": "1"
                                        }
                                        sucesso_envio, msg_envio = client.sincronizar_dataframe_ao_siepe(df_view, contexto_requisicao)
                                        if sucesso_envio:
                                            st.success(f"✅ {msg_envio}")
                                        else:
                                            st.error(f"❌ Erro no envio: {msg_envio}")
                                else:
                                    st.error("❌ Falha de Login: Verifique usuário e senha no Secrets.")   

                    with col_b3:
                        output = io.BytesIO()
                        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                            # Remove o id_siepe também na hora de exportar o Excel
                            df_export = df_view.drop(columns=['aluno_id', 'id_siepe'], errors='ignore')
                            df_export.to_excel(writer, sheet_name="Notas", index=False)
                        st.download_button("📥 Baixar Excel", output.getvalue(), f"Notas_{turma_sel}.xlsx", use_container_width=True)

                    with col_b4:
                        if st.button("🔄 Recarregar", use_container_width=True):
                            del st.session_state[state_key]
                            st.rerun()

    except Exception as e:
        st.error(f"Erro geral: {e}")