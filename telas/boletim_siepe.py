import streamlit as st
import pandas as pd
import io
import math
from siepe_api import SiepeClient

# --- CONFIGURAÇÃO GLOBAL DE IDS POR TURMA ---
MAPA_IDS_SIEPE = {
    "2º A": {
        "turma_id": "2483",       
        "disciplina_id": "1132",  
        "ew_base": "",            
        "ew_id": "",              
        "dummy": "",              
        "bimestre": "1"
    },
}

# --- FUNÇÃO OFICIAL DE ARREDONDAMENTO SIEPE ---
def arredondar_siepe(nota):
    if pd.isna(nota) or nota is None: return 0.0
    nota = float(nota)
    inteiro = math.floor(nota)
    decimal = round((nota - inteiro) * 10)
    if decimal in [0, 1]: return float(inteiro)
    elif decimal in [2, 3, 4, 5, 6]: return float(inteiro + 0.5)
    else: return float(inteiro + 1)

def mostrar_tela_boletim(supabase, supabase_alunos):
    st.title("📝 Meu Registro Pessoal de Notas")
    st.info("AT1-AT2: Simulados | AT3-AT5: Diversas | N2: Prova")
    st.caption("💡 Células vazias (NP) não somam pontos. Para um zero real, digite 0.")

    try:
        # 1. Busca alunos do banco
        res_a = supabase_alunos.table("alunos").select("*").execute()
        
        if not res_a.data:
            st.warning("Nenhum aluno encontrado no banco.")
            return

        df_todos = pd.DataFrame(res_a.data)
        col_t = 'turma' if 'turma' in df_todos.columns else ('serie' if 'serie' in df_todos.columns else 'turma')
        col_n = 'nome' if 'nome' in df_todos.columns else 'Nome'
        
        turmas_list = sorted(df_todos[col_t].dropna().unique())
        turma_sel = st.selectbox("Selecione a Turma:", turmas_list)
        
        if turma_sel:
            state_key = f"tabela_notas_{turma_sel}"
            editor_key = f"editor_notas_{turma_sel}"

            # --- CARREGAMENTO INICIAL DE DADOS ---
            if state_key not in st.session_state:
                with st.spinner(f"Carregando {turma_sel}..."):
                    df_turma = df_todos[df_todos[col_t] == turma_sel].copy()
                    df_turma = df_turma.rename(columns={"id": "aluno_id"})
                    ano_ref = "2º ano" if "2º" in turma_sel else ("3º ano" if "3º" in turma_sel else "")
                    
                    def buscar_nota_simulado(termo_simulado, limite_nota=4.0):
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
                                    df_c['n_arr'] = (df_c['pts'] * v_q).clip(upper=limite_nota).apply(arredondar_siepe)
                                    mapa_notas = dict(zip(df_c['aluno_id'].astype(str), df_c['n_arr']))
                        return mapa_notas

                    mapa_at1 = buscar_nota_simulado("1º Simulado")
                    mapa_at2 = buscar_nota_simulado("2º Simulado")

                    res_notas = supabase.table("notas_atividades").select("*").eq("turma", turma_sel).eq("unidade", "1º Bimestre").execute()
                    m3, m4, m5, mn2, mrec = {}, {}, {}, {}, {}
                    if res_notas.data:
                        for r in res_notas.data:
                            aid = str(r['aluno_id'])
                            m3[aid], m4[aid], m5[aid], mn2[aid], mrec[aid] = r.get('at3'), r.get('at4'), r.get('at5'), r.get('prova'), r.get('rec')

                    df_base = df_turma[['aluno_id', col_n]].copy().rename(columns={col_n: 'nome'})
                    
                    df_base['AT1'] = df_base['aluno_id'].astype(str).map(mapa_at1)
                    df_base['AT2'] = df_base['aluno_id'].astype(str).map(mapa_at2)
                    df_base['AT3'] = df_base['aluno_id'].astype(str).map(m3)
                    df_base['AT4'] = df_base['aluno_id'].astype(str).map(m4)
                    df_base['AT5'] = df_base['aluno_id'].astype(str).map(m5)
                    df_base['N2']  = df_base['aluno_id'].astype(str).map(mn2)
                    df_base['Rec'] = df_base['aluno_id'].astype(str).map(mrec)
                    
                    st.session_state[state_key] = df_base.sort_values('nome').reset_index(drop=True)

            # --- LÓGICA DE IMPORTAR E SOMAR ---
            with st.expander("📥 Importar e SOMAR Notas (N2) via CSV"):
                arquivo_csv = st.file_uploader("Upload CSV", type="csv", key=f"up_{turma_sel}")
                if arquivo_csv and st.button("🚀 Processar e Somar"):
                    try:
                        df_csv = pd.read_csv(arquivo_csv, encoding='latin-1', sep=None, engine='python')
                        if 'QUÍMICA' in df_csv.columns:
                            df_csv['QUÍMICA'] = pd.to_numeric(df_csv['QUÍMICA'], errors='coerce').fillna(0.0)
                            df_atual = st.session_state[state_key].copy()
                            df_csv['n_match'] = df_csv['Name'].astype(str).str.strip().str.lower()
                            df_atual['n_match'] = df_atual['nome'].astype(str).str.strip().str.lower()
                            mapa_csv = dict(zip(df_csv['n_match'], df_csv['QUÍMICA']))
                            
                            for idx, row in df_atual.iterrows():
                                nome = row['n_match']
                                if nome in mapa_csv:
                                    v_atual = float(row['N2']) if pd.notna(row['N2']) else 0.0
                                    df_atual.at[idx, 'N2'] = v_atual + float(mapa_csv[nome])
                            
                            st.session_state[state_key] = df_atual.drop(columns=['n_match'])
                            st.rerun()
                    except Exception as e: st.error(f"Erro no CSV: {e}")

            # --- PERSISTÊNCIA DAS EDIÇÕES ---
            if editor_key in st.session_state:
                edicoes = st.session_state[editor_key].get("edited_rows", {})
                for row_idx, alteracoes in edicoes.items():
                    for col_name, valor in alteracoes.items():
                        st.session_state[state_key].at[row_idx, col_name] = float(valor) if valor is not None else None

            # --- CÁLCULOS E ESTILO ---
            df_view = st.session_state[state_key].copy()
            
            df_view['N1'] = df_view[['AT1', 'AT2', 'AT3', 'AT4', 'AT5']].sum(axis=1, min_count=1).apply(
                lambda x: arredondar_siepe(x) if pd.notna(x) else None
            )

            def calcular_media_segura(row):
                n1, n2 = row['N1'], row['N2']
                if pd.isna(n1) and pd.isna(n2): return None
                v1 = n1 if pd.notna(n1) else 0.0
                v2 = n2 if pd.notna(n2) else 0.0
                return arredondar_siepe((v1 + v2) / 2)

            df_view['Média'] = df_view.apply(calcular_media_segura, axis=1)

            def estilo(val):
                try:
                    if pd.notna(val) and float(val) > 0:
                        return 'color: #1E40AF; font-weight: bold; background-color: #EFF6FF;'
                    return 'color: #9CA3AF;'
                except: return ''

            df_estilizado = df_view.style.map(estilo, subset=['AT1', 'AT2', 'AT3', 'AT4', 'AT5', 'N2', 'N1', 'Média', 'Rec'])

            # --- EDITOR DE DADOS ---
            config_cols = {
                "aluno_id": None, "nome": st.column_config.TextColumn("ESTUDANTE", disabled=True, width="medium"),
                "AT1": st.column_config.NumberColumn("AT1", format="%.1f", disabled=True),
                "AT2": st.column_config.NumberColumn("AT2", format="%.1f", disabled=True),
                "AT3": st.column_config.NumberColumn("AT3", format="%.1f", min_value=0.0, max_value=10.0),
                "AT4": st.column_config.NumberColumn("AT4", format="%.1f", min_value=0.0, max_value=10.0),
                "AT5": st.column_config.NumberColumn("AT5", format="%.1f", min_value=0.0, max_value=10.0),
                "N2": st.column_config.NumberColumn("N2 (PROVA)", format="%.1f", min_value=0.0, max_value=10.0),
                "N1": st.column_config.NumberColumn("Σ N1 🔒", disabled=True, format="%.1f"),
                "Média": st.column_config.NumberColumn("MÉDIA 🔒", disabled=True, format="%.1f"),
                "Rec": st.column_config.NumberColumn("REC", format="%.1f", min_value=0.0, max_value=10.0),
            }

            st.data_editor(
                df_estilizado, key=editor_key, hide_index=True, column_config=config_cols, 
                use_container_width=True, height=(len(df_view) + 1) * 35 + 45,
                column_order=("nome", "AT1", "AT2", "AT3", "AT4", "AT5", "N2", "N1", "Média", "Rec")
            )

            # --- BOTÕES DE AÇÃO ---
            c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
            with c1:
                if st.button("💾 Salvar no Banco", type="primary", use_container_width=True):
                    dados_limpos = []
                    for _, r in df_view.iterrows():
                        limpar = lambda x: float(x) if pd.notna(x) else None
                        dados_limpos.append({
                            "aluno_id": r['aluno_id'], "turma": turma_sel, "unidade": "1º Bimestre",
                            "at1": limpar(r['AT1']), "at2": limpar(r['AT2']), "at3": limpar(r['AT3']),
                            "at4": limpar(r['AT4']), "at5": limpar(r['AT5']), "prova": limpar(r['N2']),
                            "rec": limpar(r['Rec'])
                        })
                    supabase.table("notas_atividades").upsert(dados_limpos, on_conflict="aluno_id, unidade").execute()
                    st.success("✅ Salvo com sucesso!")

            with c2:
                cfg = MAPA_IDS_SIEPE.get(turma_sel)
                if cfg and st.button("🚀 Sincronizar SIEPE", use_container_width=True):
                    client = SiepeClient()
                    with st.spinner("Enviando..."):
                        u, s = st.secrets["SIEPE_USER"], st.secrets["SIEPE_PASS"]
                        log, _ = client.fazer_login(u, s)
                        if log and client.iniciar_robo_navegacao():
                            suc, msg = client.sincronizar_dataframe_ao_siepe_final(df_view, cfg)
                            st.success(msg) if suc else st.error(msg)

            with c3:
                out = io.BytesIO()
                with pd.ExcelWriter(out, engine='xlsxwriter') as writer:
                    df_view.drop(columns=['aluno_id']).to_excel(writer, index=False)
                st.download_button("📥 Excel", out.getvalue(), f"Notas_{turma_sel}.xlsx", use_container_width=True)

            with c4:
                if st.button("🔄", use_container_width=True):
                    del st.session_state[state_key]
                    st.rerun()

    except Exception as e:
        st.error(f"Erro geral: {e}")