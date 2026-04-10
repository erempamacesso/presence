import streamlit as st
import pandas as pd
import numpy as np

def exibir_importacao(supabase):
    st.title("📤 Sistema de Sincronização SIGERPAM")
    st.markdown("---")

    # 1. UPLOAD DO ARQUIVO
    arquivo = st.file_uploader("Suba a planilha oficial do SIEPE (.xls ou .xlsx)", type=["xls", "xlsx"])

    if not arquivo:
        return

    try:
        xl = pd.ExcelFile(arquivo)
        abas_turmas = [a for a in xl.sheet_names if "EM45" in a]

        if not abas_turmas:
            st.error("Nenhuma aba com 'EM45' encontrada na planilha.")
            return

        # 2. LEITURA DA PLANILHA
        dados_lidos = []

        for aba in abas_turmas:
            sigla = aba.split('-')[-1].strip() if '-' in aba else aba.strip()
            turma_f = f"{sigla[0]}º {sigla[-1]}" if len(sigla) >= 2 and sigla[0].isdigit() else aba

            df = pd.read_excel(xl, sheet_name=aba, header=0)
            df.columns = df.columns.str.strip().str.upper()

            col_nome       = next((c for c in df.columns if "NOME"        in c), None)
            col_matricula  = next((c for c in df.columns if "MATR"        in c), None)
            col_nascimento = next((c for c in df.columns if "NASCIMENTO"  in c or "NASC" in c), None)
            col_sexo       = next((c for c in df.columns if "SEXO"        in c), None)
            col_situacao   = next((c for c in df.columns if "SITUA"       in c), None)

            if not col_nome:
                continue

            df = df.dropna(subset=[col_nome])

            for _, linha in df.iterrows():
                nome_limpo = str(linha[col_nome]).strip().upper()
                if not nome_limpo or nome_limpo == "NAN":
                    continue

                matricula = str(linha[col_matricula]).strip() if col_matricula and pd.notna(linha[col_matricula]) else ""
                
                nascimento = ""
                if col_nascimento and pd.notna(linha[col_nascimento]):
                    try:
                        nascimento = pd.to_datetime(linha[col_nascimento], dayfirst=True).strftime('%Y-%m-%d')
                    except:
                        nascimento = str(linha[col_nascimento]).strip()

                sexo_raw = linha[col_sexo] if col_sexo and pd.notna(linha.get(col_sexo)) else None
                sexo = str(sexo_raw)[0].upper() if sexo_raw else ""

                situacao = str(linha[col_situacao]).strip().upper() if col_situacao and pd.notna(linha.get(col_situacao)) else "NÃO INFORMADA"

                dados_lidos.append({
                    "nome":             nome_limpo,
                    "turma":            turma_f,
                    "numero_matricula": matricula,
                    "data_nascimento":  nascimento,
                    "sexo":             sexo,
                    "situacao":         situacao,
                })

        if not dados_lidos:
            st.error("Nenhum aluno válido foi encontrado.")
            return

        df_excel = pd.DataFrame(dados_lidos).drop_duplicates(subset=["nome"])

        # 3. ABAS DA INTERFACE
        tab_raio_x, tab_cruzamento, tab_sincronismo = st.tabs([
            "🔍 1. Raio-X da Planilha",
            "📊 2. Cruzamento com o Banco",
            "🚀 3. Sincronizar",
        ])

        # ==========================================
        # ABA 1 — RAIO-X
        # ==========================================
        with tab_raio_x:
            st.subheader("Resumo por Turma (Lido do Excel)")
            resumo = df_excel.groupby("turma").size().reset_index(name="Total de Alunos")
            st.dataframe(resumo, hide_index=True, use_container_width=True)

        # ==========================================
        # ABA 2 — CRUZAMENTO E MESCLAGEM
        # ==========================================
        with tab_cruzamento:
            st.subheader("Comparação com o Banco de Dados")

            if st.button("🔍 Iniciar Cruzamento", type="primary"):
                with st.spinner("Analisando e mesclando dados..."):
                    res_bd = supabase.table("alunos").select("nome, turma, numero_matricula, data_nascimento, sexo").execute()
                    df_bd = pd.DataFrame(res_bd.data) if res_bd.data else pd.DataFrame(columns=["nome", "turma", "numero_matricula", "data_nascimento", "sexo"])

                nomes_excel = set(df_excel["nome"])
                nomes_bd    = set(df_bd["nome"]) if not df_bd.empty else set()

                novos        = nomes_excel - nomes_bd
                transferidos = nomes_bd - nomes_excel

                # 💡 A MÁGICA ACONTECE AQUI: Mesclando Excel com o Banco
                df_final = df_excel.copy()
                
                if not df_bd.empty:
                    df_bd_idx = df_bd.set_index("nome")
                    df_final_idx = df_final.set_index("nome")

                    # Se o Excel veio vazio, mas o Banco tem a info, salva a info do banco!
                    for col in ["numero_matricula", "data_nascimento", "sexo"]:
                        df_final_idx[col] = df_final_idx[col].replace(r'^\s*$', np.nan, regex=True) # Troca vazio por NaN
                        if col in df_bd_idx.columns:
                            df_final_idx[col] = df_final_idx[col].fillna(df_bd_idx[col])

                    df_final = df_final_idx.reset_index()

                # Substitui os NaN de volta por string vazia para exibição na tela
                df_final = df_final.fillna("")

                # Detectar quem AINDA está com dado faltando (mesmo após juntar Excel + Banco)
                def campo_vazio(val):
                    return val is None or str(val).strip() == "" or str(val).strip().upper() in ("NAN", "NONE", "NAT")

                mask_incompletos = df_final.apply(
                    lambda r: campo_vazio(r.get("numero_matricula")) or campo_vazio(r.get("data_nascimento")) or campo_vazio(r.get("sexo")),
                    axis=1
                )
                df_incompletos = df_final[mask_incompletos].copy()

                st.session_state["_cruzamento"] = {
                    "df_final":       df_final,
                    "novos":          novos,
                    "transferidos":   transferidos,
                    "df_incompletos": df_incompletos,
                }

                m1, m2, m3 = st.columns(3)
                m1.metric("🟢 Alunos Novos", len(novos))
                m2.metric("🔴 Transferidos (Saíram)", len(transferidos))
                m3.metric("🟡 Incompletos (Sem dados no Excel/Banco)", len(df_incompletos))

                st.divider()
                st.success("Cruzamento finalizado! Avance para a Aba 3 para revisar, editar e sincronizar.")

        # ==========================================
        # ABA 3 — SINCRONIZAR (COM TABELA EDITÁVEL)
        # ==========================================
        with tab_sincronismo:
            if "_cruzamento" not in st.session_state:
                st.info("⬅️ Primeiro execute o cruzamento na Aba 2.")
                return

            dados          = st.session_state["_cruzamento"]
            novos          = dados["novos"]
            transferidos   = dados["transferidos"]
            df_final       = dados["df_final"]
            df_incompletos = dados["df_incompletos"]

            tem_mudanca = bool(novos or transferidos)
            df_editado = pd.DataFrame()

            # 💡 TABELA EDITÁVEL: Aparece só se tiver aluno incompleto
            if not df_incompletos.empty:
                st.warning("✏️ **DADOS FALTANTES ENCONTRADOS!**")
                st.write("Os alunos abaixo não possuem Matrícula, Data de Nascimento ou Sexo nem no Excel nem no Banco. **Você pode digitar diretamente na tabela abaixo antes de salvar:**")
                
                # Editor de dados interativo do Streamlit
                df_editado = st.data_editor(
                    df_incompletos[["nome", "turma", "numero_matricula", "data_nascimento", "sexo"]],
                    disabled=["nome", "turma"], # Bloqueia nome e turma para o usuário não quebrar a sincronização
                    hide_index=True,
                    use_container_width=True,
                    key="editor_dados"
                )
                st.divider()

            if not tem_mudanca and df_incompletos.empty:
                st.success("✅ O banco de dados já está 100% atualizado e sem nenhum dado faltando. Nenhuma ação necessária.")
                return

            st.subheader("Aplicar Alterações no SIGERPAM")
            st.error("🔴 **ATENÇÃO:** Alunos transferidos serão removidos e os dados editados/mesclados serão salvos.")
            
            confirmar = st.button("🚀 CONFIRMAR E SINCRONIZAR AGORA", type="primary")

            if confirmar:
                with st.spinner("Atualizando o Banco de Dados..."):
                    erros = []

                    # 1. Se o usuário digitou algo na tabela editável, nós juntamos no df_final
                    if not df_editado.empty:
                        df_final_idx = df_final.set_index("nome")
                        df_editado_idx = df_editado.set_index("nome")
                        df_final_idx.update(df_editado_idx) # Substitui com os dados que o usuário digitou
                        df_final = df_final_idx.reset_index()

                    # 2. REMOVER TRANSFERIDOS
                    if transferidos:
                        try:
                            supabase.table("alunos").delete().in_("nome", list(transferidos)).execute()
                        except Exception as e:
                            erros.append(f"Erro ao remover transferidos: {e}")

                    # 3. ATUALIZAR TODOS OS ALUNOS (Upsert Geral)
                    # Isso garante que quem mudou de turma, atualizou no Excel ou foi digitado na tela será salvo.
                    registros_para_salvar = df_final[["nome", "turma", "numero_matricula", "data_nascimento", "sexo"]].to_dict("records")
                    
                    # Limpeza final de vazios para o Supabase aceitar
                    for r in registros_para_salvar:
                        for k, v in list(r.items()):
                            if str(v).strip() in ("", "NAN", "NAT", "NONE"):
                                r[k] = None

                    try:
                        # Mandamos a escola inteira. O Upsert ignora quem está igual, atualiza quem mudou e insere os novos!
                        supabase.table("alunos").upsert(registros_para_salvar, on_conflict="nome").execute()
                    except Exception as e:
                        erros.append(f"Erro ao salvar alunos: {e}")

                    if erros:
                        for err in erros:
                            st.error(err)
                    else:
                        st.success("🎉 Sincronização concluída com sucesso! Banco 100% atualizado.")
                        st.balloons()
                        del st.session_state["_cruzamento"]

    except Exception as e:
        st.error(f"Erro crítico no processamento: {e}")