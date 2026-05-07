import streamlit as st
import pandas as pd
import io
import math
from siepe_api import SiepeClient

# --- CONFIGURAÇÃO GLOBAL DE IDS POR TURMA ---
# Note que agora não precisamos mais do EWBase, EWId e dummy aqui, 
# pois o robô vai pegar sozinho! Mas mantive a estrutura para não quebrar nada.
MAPA_IDS_SIEPE = {
    "2º A": {
        "turma_id": "2483",       # ID para salvar a nota
        "disciplina_id": "1132",  # Química
        "ew_base": "",            # O robô vai preencher
        "ew_id": "",              # O robô vai preencher
        "dummy": "",              # O robô vai preencher
        "bimestre": "1"
    },
    # Adicione as próximas turmas aqui...
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
    st.info("AT1 e AT2: Simulados Online | AT3, AT4 e AT5: Notas Diversas | N2: Prova")
    st.caption("💡 Dica: Notas maiores que zero ficam em **azul** automaticamente.")

    try:
        # 1. Busca alunos do banco
        res_a = supabase_alunos.table("alunos").select("*").execute()
        
        if not res_a.data:
            st.warning("Nenhum aluno encontrado no banco.")
            return

        df_todos = pd.DataFrame(res_a.data)
        col_t = 'turma' if 'turma' in df_todos.columns else ('serie' if 'serie' in df_todos.columns else None)
        col_n = 'nome' if 'nome' in df_todos.columns else 'Nome'
        
        if not col_t:
            st.error("Coluna de turma não encontrada.")
            return

        turmas_list = sorted(df_todos[col_t].dropna().unique())
        turma_sel = st.selectbox("Selecione a Turma:", turmas_list)
        
        if turma_sel:
            state_key = f"tabela_notas_{turma_sel}"
            editor_key = f"editor_notas_{turma_sel}"
            locked_cols = ['AT1', 'AT2']

            # --- INICIALIZAÇÃO E BUSCA DE DADOS ---
            if state_key not in st.session_state:
                with st.spinner(f"Carregando dados de {turma_sel}..."):
                    df_turma = df_todos[df_todos[col_t] == turma_sel].copy()
                    df_turma = df_turma.rename(columns={"id": "aluno_id"})
                    ano_ref = "2º ano" if "2º" in turma_sel else ("3º ano" if "3º" in turma_sel else "")
                    
                    # Função interna para buscar simulados
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
                                    df_c['nota_arredondada'] = (df_c['pts'] * v_q).clip(upper=limite_nota).apply(arredondar_siepe)
                                    mapa_notas = dict(zip(df_c['aluno_id'].astype(str), df_c['nota_arredondada']))
                        return mapa_notas

                    mapa_at1 = buscar_nota_simulado("1º Simulado")
                    mapa_at2 = buscar_nota_simulado("2º Simulado")

                    df_base = df_turma[['aluno_id', col_n]].copy().rename(columns={col_n: 'nome'})
                    df_base['AT1'] = df_base['aluno_id'].astype(str).map(mapa_at1).fillna(0.0)
                    df_base['AT2'] = df_base['aluno_id'].astype(str).map(mapa_at2).fillna(0.0)
                    
                    # Busca notas manuais já salvas
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

            # --- ÁREA DE IMPORTAÇÃO CSV ---
            with st.expander("📥 Importar e SOMAR Notas de Prova (N2) via CSV"):
                arquivo_csv = st.file_uploader("Upload CSV", type="csv", key=f"up_{turma_sel}")
                if arquivo_csv:
                    if st.button("🚀 Processar e Somar CSV"):
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
                                        df_atual.at[idx, 'N2'] = float(row['N2']) + float(mapa_csv[nome])
                                
                                st.session_state[state_key] = df_atual.drop(columns=['n_match'])
                                st.success("Notas somadas!")
                                st.rerun()
                        except Exception as e: st.error(f"Erro no CSV: {e}")

            # --- EDITOR DE DADOS ---
            # Sincroniza edições manuais com o state
            if editor_key in st.session_state:
                edicoes = st.session_state[editor_key].get("edited_rows", {})
                for row_idx, alteracoes in edicoes.items():
                    for col_name, valor in alteracoes.items():
                        st.session_state[state_key].at[row_idx, col_name] = float(valor) if valor is not None else 0.0

            df_view = st.session_state[state_key].copy()
            df_view['N1'] = df_view[['AT1', 'AT2', 'AT3', 'AT4', 'AT5']].sum(axis=1).apply(arredondar_siepe)
            df_view['Média Final'] = ((df_view['N1'] + df_view['N2']) / 2).apply(arredondar_siepe)

            # --- LÓGICA DE CORES ---
            def aplicar_estilo_notas(val):
                try:
                    if float(val) > 0:
                        return 'color: #1E40AF; font-weight: bold; background-color: #EFF6FF;'
                    return 'color: #9CA3AF;'
                except:
                    return ''

            colunas_notas = ['AT1', 'AT2', 'AT3', 'AT4', 'AT5', 'N1', 'N2', 'Média Final']
            df_estilizado = df_view.style.map(aplicar_estilo_notas, subset=[c for c in colunas_notas if c in df_view.columns])

            # Configuração das colunas no Editor
            config_cols = {
                "aluno_id": None, 
                "nome": st.column_config.TextColumn("Estudante", disabled=True, width="medium"),
                "N1": st.column_config.NumberColumn("Σ N1 🔒", disabled=True, format="%.1f"),
                "Média Final": st.column_config.NumberColumn("Média 🔒", disabled=True, format="%.1f"),
            }
            for c in ['AT1', 'AT2', 'AT3', 'AT4', 'AT5', 'N2']:
                config_cols[c] = st.column_config.NumberColumn(c, min_value=0.0, max_value=10.0, step=0.1, format="%.1f", disabled=(c in locked_cols))

            # --- CORREÇÃO DA ROLAGEM: Calcula a altura para mostrar todos de uma vez ---
            altura_tabela = (len(df_view) + 1) * 36 + 10 

            st.data_editor(
                df_estilizado, 
                key=editor_key, 
                hide_index=True, 
                column_config=config_cols, 
                use_container_width=True,
                height=altura_tabela
            )
            
            # --- BOTÕES DE AÇÃO ---
            col_b1, col_b2, col_b3, col_b4 = st.columns([2, 2, 2, 1])
            
            with col_b1:
                if st.button("💾 Salvar no Banco", type="primary", use_container_width=True):
                    dados_upsert = []
                    for _, r in df_view.iterrows():
                        dados_upsert.append({
                            "aluno_id": r['aluno_id'], "turma": turma_sel, "unidade": "1º Bimestre",
                            "at1": float(r['AT1']), "at2": float(r['AT2']), "at3": float(r['AT3']),
                            "at4": float(r['AT4']), "at5": float(r['AT5']), "prova": float(r['N2'])
                        })
                    supabase.table("notas_atividades").upsert(dados_upsert, on_conflict="aluno_id, unidade").execute()
                    st.success("✅ Salvo!")

            # =========================================================================
            # AQUI ESTÁ A NOVA MÁGICA: O BOTÃO TOTALMENTE AUTOMATIZADO DO ROBÔ
            # =========================================================================
            with col_b2:
                config_siepe = MAPA_IDS_SIEPE.get(turma_sel)
                if not config_siepe:
                    st.warning("⚠️ Turma sem IDs no mapa.")
                else:
                    if st.button("🚀 Sincronizar SIEPE Automático", use_container_width=True):
                        client = SiepeClient()
                        with st.spinner("Conectando e navegando pelas telas invisíveis..."):
                            usuario = st.secrets["SIEPE_USER"]
                            senha = st.secrets["SIEPE_PASS"]
                            
                            logado, msg = client.fazer_login(usuario, senha)
                            if logado:
                                st.info("Login OK! Iniciando navegação robótica...")
                                
                                # O robô vai fazer o caminho invisível até a aba de notas
                                sucesso_nav = client.iniciar_robo_navegacao()
                                
                                if sucesso_nav:
                                    st.info("Aba de Notas aberta. Enviando dados...")
                                    # Passamos o config_siepe junto para ele saber qual a disciplina e a turma correta
                                    sucesso_envio, msg_envio = client.sincronizar_dataframe_ao_siepe_final(df_view, config_siepe)
                                    
                                    if sucesso_envio:
                                        st.success(msg_envio)
                                    else:
                                        st.error(msg_envio)
                                else:
                                    st.error("Erro na navegação automática. O portal pode ter mudado algo.")
                            else:
                                st.error(f"Falha no login: {msg}")

            with col_b3:
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_view.drop(columns=['aluno_id']).to_excel(writer, index=False)
                st.download_button("📥 Excel", output.getvalue(), f"Notas_{turma_sel}.xlsx", use_container_width=True)

            with col_b4:
                if st.button("🔄", use_container_width=True):
                    del st.session_state[state_key]
                    st.rerun()

    except Exception as e:
        st.error(f"Erro geral: {e}")