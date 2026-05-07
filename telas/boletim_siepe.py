import streamlit as st
import pandas as pd
import io
import math
from siepe_api import SiepeClient

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
    
    # CONFIGURAÇÃO DE IDS POR TURMA
    MAPA_IDS_SIEPE = {
        "2º A": {
            "turma_id": "2483",       # ID capturado no console
            "disciplina_id": "1132",  # Química
            "ew_base": "122549628",   # Valores dinâmicos (expiram)
            "ew_id": "126982310",     
            "dummy": "1778106821147",
            "bimestre": "1"
        }
        # Adicione outras turmas aqui conforme capturar os IDs
    }

    try:
        res_a = supabase_alunos.table("alunos").select("*").execute()
        if not res_a.data:
            st.warning("Nenhum aluno encontrado.")
            return

        df_todos = pd.DataFrame(res_a.data)
        col_t = 'turma' if 'turma' in df_todos.columns else 'serie'
        turmas_list = sorted(df_todos[col_t].dropna().unique())
        turma_sel = st.selectbox("Selecione a Turma:", turmas_list)

        if turma_sel:
            state_key = f"tabela_notas_{turma_sel}"
            
            if state_key not in st.session_state:
                df_base = df_todos[df_todos[col_t] == turma_sel].copy().rename(columns={"id": "aluno_id"})
                for c in ['AT1', 'AT2', 'AT3', 'AT4', 'AT5', 'N2']:
                    df_base[c] = df_base.get(c, 0.0)
                st.session_state[state_key] = df_base.sort_values('nome').reset_index(drop=True)

            df_view = st.session_state[state_key]
            
            df_editado = st.data_editor(
                df_view,
                key=f"editor_{turma_sel}",
                hide_index=True,
                use_container_width=True
            )
            st.session_state[state_key] = df_editado

            col_b1, col_b2, col_b3 = st.columns(3)
            
            with col_b1:
                if st.button("💾 Salvar no Banco", use_container_width=True):
                    # Lógica de persistência no Supabase aqui
                    st.success("Dados salvos no banco pessoal.")

            with col_b2:
                # Busca a configuração específica para a turma selecionada
                config_siepe = MAPA_IDS_SIEPE.get(turma_sel)
                
                if not config_siepe:
                    st.error(f"⚠️ Configure os IDs do SIEPE para a turma '{turma_sel}' no código!")
                else:
                    if st.button("🚀 Sincronizar com SIEPE", type="primary", use_container_width=True):
                        client = SiepeClient()
                        with st.spinner("Conectando ao portal..."):
                            logado, msg = client.fazer_login(st.secrets["SIEPE_USER"], st.secrets["SIEPE_PASS"])
                            if logado:
                                sucesso, res = client.sincronizar_dataframe_ao_siepe(df_editado, config_siepe)
                                if sucesso: st.success(res)
                                else: st.error(res)
                            else:
                                st.error(msg)

            with col_b3:
                if st.button("🔄 Recarregar", use_container_width=True):
                    del st.session_state[state_key]
                    st.rerun()

    except Exception as e:
        st.error(f"Erro no sistema: {e}")