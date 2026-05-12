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
    st.info("AT1-AT2: Simulados | AT3-AT5: Diversas | N2: Prova | REC: Recuperação")

    try:
        # 1. Busca todos os alunos
        res_a = supabase_alunos.table("alunos").select("*").execute()
        if not res_a.data:
            st.warning("Nenhum aluno encontrado.")
            return
            
        df_alunos = pd.DataFrame(res_a.data)
        turmas = sorted(df_alunos['turma'].unique())
        
        col1, col2 = st.columns(2)
        turma_sel = col1.selectbox("Selecione a Turma:", turmas)
        unidade_sel = col2.selectbox("Selecione o Bimestre:", ["1", "2", "3", "4"])
        
        # 2. Busca notas existentes (Usando a coluna 'rec' correta)
        res_notas = supabase.table("notas_atividades")\
            .select("aluno_id, at3, at4, at5, prova, rec")\
            .eq("unidade", unidade_sel).execute()
        
        # Garantimos que a chave seja string para não ocultar as notas por erro de tipo
        notas_map = {str(n['aluno_id']): n for n in res_notas.data}
        
        # 3. Montagem da Tabela
        alunos_turma = df_alunos[df_alunos['turma'] == turma_sel].sort_values(by="nome")
        rows = []
        
        for _, aluno in alunos_turma.iterrows():
            id_a = str(aluno['id'])
            d_nota = notas_map.get(id_a, {})
            
            # Notas e Recuperação (lendo de 'rec')
            at3 = float(d_nota.get('at3', 0.0) or 0.0)
            at4 = float(d_nota.get('at4', 0.0) or 0.0)
            at5 = float(d_nota.get('at5', 0.0) or 0.0)
            n2  = float(d_nota.get('prova', 0.0) or 0.0)
            rec_valor = float(d_nota.get('rec', 0.0) or 0.0)
            
            at1, at2 = 0.0, 0.0 
            
            n1_final = arredondar_siepe(at1 + at2 + at3 + at4 + at5)
            media_bim = arredondar_siepe((n1_final + n2) / 2)
            media_final = max(media_bim, rec_valor) if rec_valor > 0 else media_bim

            rows.append({
                "aluno_id": id_a,
                "Nome": aluno['nome'],
                "AT1": at1, "AT2": at2, "AT3": at3, "AT4": at4, "AT5": at5,
                "N1": n1_final,
                "N2": n2,
                "Média": media_bim,
                "REC": rec_valor,
                "Média Final": media_final
            })
            
        df_view = pd.DataFrame(rows)

        # 4. Exibição e Edição (Sem as cores que causavam erro)
        st.subheader(f"📊 Boletim - {turma_sel}")
        edited_df = st.data_editor(
            df_view,
            column_config={
                "aluno_id": None,
                "N1": st.column_config.NumberColumn(disabled=True),
                "Média": st.column_config.NumberColumn(disabled=True),
                "Média Final": st.column_config.NumberColumn(disabled=True),
                "REC": st.column_config.NumberColumn("REC", min_value=0, max_value=10, step=0.5)
            },
            hide_index=True,
            use_container_width=True,
            key="editor_notas"
        )

        # 5. Ações: Salvar
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            if st.button("💾 Salvar Notas", type="primary", use_container_width=True):
                dados_limpos = []
                for _, r in edited_df.iterrows():
                    def limpar(v): return float(v) if pd.notna(v) else 0.0
                    dados_limpos.append({
                        "aluno_id": r['aluno_id'],
                        "unidade": unidade_sel,
                        "at3": limpar(r['AT3']),
                        "at4": limpar(r['AT4']),
                        "at5": limpar(r['AT5']),
                        "prova": limpar(r['N2']),
                        "rec": limpar(r['REC']) # Salva na coluna 'rec'
                    })
                try:
                    supabase.table("notas_atividades").upsert(dados_limpos, on_conflict="aluno_id, unidade").execute()
                    st.success("✅ Notas salvas com sucesso!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")

        with c3:
            out = io.BytesIO()
            with pd.ExcelWriter(out, engine='xlsxwriter') as writer:
                df_view.drop(columns=['aluno_id']).to_excel(writer, index=False)
            st.download_button("📥 Excel", out.getvalue(), f"Boletim_{turma_sel}.xlsx", use_container_width=True)

    except Exception as e:
        st.error(f"Ocorreu um erro no boletim: {e}")