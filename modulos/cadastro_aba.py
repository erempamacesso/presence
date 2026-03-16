import streamlit as st
import pandas as pd
import unicodedata
import time
import re

# --- FUNÇÕES DE UTILITÁRIO ---

def limpar_texto(texto):
    """Padronização para nomes de arquivos e chaves de busca"""
    if not texto: return ""
    if "." in str(texto): texto = str(texto).rsplit('.', 1)[0]
    nfkd = unicodedata.normalize('NFKD', str(texto))
    texto_limpo = "".join([c for c in nfkd if not unicodedata.combining(c)]).lower()
    return "".join(filter(str.isalnum, texto_limpo))

def formatar_turma(nome_aba):
    """Transforma '1A', '1 A', '1ºA', '1 ANO A', '1-A' automaticamente em '1º A'"""
    nome = str(nome_aba).strip().upper()
    
    # Arranca palavras extras, espaços e pontuações para sobrar só (ex: '1A')
    limpo = re.sub(r'(º|ANO|SÉRIE|SERIE|-)', '', nome).replace(" ", "")
    
    # Se sobrou exatamente um número seguido de uma letra (ex: 1A, 9C)...
    match = re.match(r'^(\d+)([A-Z])$', limpo)
    if match:
        return f"{match.group(1)}º {match.group(2)}"
    
    return nome # Se for "Maternal", devolve do jeito que veio

def listar_arquivos_bucket(supabase):
    try:
        arquivos = supabase.storage.from_('fotos-alunos').list(path=None, options={'limit': 5000})
        mapa = {limpar_texto(arq['name']): arq['name'] for arq in arquivos}
        return mapa
    except: return {}

# --- FUNÇÃO PRINCIPAL DE INTERFACE ---

def exibir_cadastro(supabase):
    st.title("👤 Sistema de Gestão Escolar")
    
    aba_busca, aba_gerenciar, aba_excel, aba_manual, aba_sinc = st.tabs([
        "🔍 Localizar Aluno", 
        "📸 Fotos e Turmas", 
        "📁 Atualização Excel", 
        "➕ Cadastro Avulso",
        "🔄 Sincronizar Matrículas"
    ])

    # =========================================================
    # ABA 1: LOCALIZAR ALUNO
    # =========================================================
    with aba_busca:
        st.subheader("Consulta Rápida de Alunos")
        nome_busca = st.text_input("Digite o nome ou parte do nome:").strip().upper()

        if nome_busca:
            with st.spinner("Buscando no sistema..."):
                res = supabase.table("alunos").select("nome, turma").ilike("nome", f"%{nome_busca}%").execute()
                
                if res.data:
                    st.success(f"Encontrados {len(res.data)} aluno(s)")
                    df_res = pd.DataFrame(res.data)
                    df_res.columns = ["Nome Completo", "Turma Atual"]
                    st.dataframe(df_res, use_container_width=True, hide_index=True)
                else:
                    st.warning(f"⚠️ Aluno '{nome_busca}' não encontrado no sistema.")

    # =========================================================
    # ABA 2: GERENCIAR TURMAS E FOTOS
    # =========================================================
    with aba_gerenciar:
        res_t = supabase.table("alunos").select("turma").execute()
        lista_turmas = sorted(list(set([x['turma'] for x in res_t.data if x['turma']])))
        
        col_t1, col_t2 = st.columns([3, 1])
        with col_t2:
            # BOTÃO DE FAXINA PARA CONSERTAR O BANCO DE DADOS
            if st.button("🧹 Padronizar Todas as Turmas", help="Use isso se turmas antigas como '1A' ainda estiverem aparecendo"):
                with st.spinner("Limpando banco de dados..."):
                    todos = supabase.table("alunos").select("id, turma").execute().data
                    corrigidos = 0
                    for al in todos:
                        turma_corrigida = formatar_turma(al['turma'])
                        if turma_corrigida != al['turma']:
                            supabase.table("alunos").update({"turma": turma_corrigida}).eq("id", al['id']).execute()
                            corrigidos += 1
                    st.success(f"Faxina concluída! {corrigidos} alunos foram atualizados.")
                    time.sleep(1.5)
                    st.rerun()

        with col_t1:
            if lista_turmas:
                turma_sel = st.selectbox("Selecione a Turma para gerenciar:", lista_turmas)
                alunos = supabase.table("alunos").select("*").eq("turma", turma_sel).order("nome").execute().data
                mapa_fotos = listar_arquivos_bucket(supabase)

                st.write(f"Exibindo **{len(alunos)}** alunos")

                for aluno in alunos:
                    with st.container(border=True):
                        c1, c2, c3 = st.columns([1, 2, 2])
                        uid, nome_aluno, chave = aluno['id'], aluno['nome'], limpar_texto(aluno['nome'])
                        foto_real = mapa_fotos.get(chave)
                        
                        with c1:
                            if foto_real:
                                url = supabase.storage.from_('fotos-alunos').get_public_url(foto_real)
                                st.image(url, width=80)
                            else:
                                st.caption("🟡 Sem Foto")

                        with c2:
                            st.markdown(f"**{nome_aluno}**")
                            nova_t = st.selectbox("Mudar Turma:", lista_turmas, index=lista_turmas.index(aluno['turma']), key=f"t_{uid}")
                            if nova_t != aluno['turma']:
                                supabase.table("alunos").update({"turma": nova_t}).eq("id", uid).execute()
                                st.toast("Turma atualizada!")
                                time.sleep(0.5)
                                st.rerun()
                            
                            with st.popover("🗑️ Opções Críticas"):
                                if st.button("Excluir Aluno Permanentemente", key=f"del_{uid}", type="primary"):
                                    if foto_real: supabase.storage.from_('fotos-alunos').remove([foto_real])
                                    supabase.table("alunos").delete().eq("id", uid).execute()
                                    st.rerun()

                        with c3:
                            foto_nova = st.file_uploader("Trocar Foto (.png)", type=["png"], key=f"up_{uid}")
                            if foto_nova and st.button("Salvar Foto", key=f"btn_{uid}"):
                                nome_arquivo = f"{chave}.png"
                                supabase.storage.from_('fotos-alunos').upload(
                                    path=nome_arquivo, file=foto_nova.getvalue(),
                                    file_options={"content-type": "image/png", "upsert": "true"}
                                )
                                st.rerun()
                            elif foto_real:
                                if st.button("🗑️ Remover Foto", key=f"del_pic_{uid}"):
                                    supabase.storage.from_('fotos-alunos').remove([foto_real])
                                    st.rerun()
            else:
                st.warning("Nenhum dado encontrado. Use as abas de importação.")

    # =========================================================
    # ABA 3: ATUALIZAÇÃO EXCEL (GERAL)
    # =========================================================
    with aba_excel:
        st.subheader("📁 Sincronização Total via Planilha")
        st.info("O sistema lerá cada aba (ex: 1A, 1B) e vinculará os alunos formatando a turma automaticamente.")
        
        arquivo = st.file_uploader("Suba a planilha da secretaria (.xlsx)", type=["xlsx"])
        
        if arquivo:
            try:
                xl = pd.ExcelFile(arquivo)
                abas = xl.sheet_names
                st.write(f"📊 Turmas detectadas nas abas: {', '.join(abas)}")

                if st.button("🚀 Iniciar Sincronização Geral", type="primary"):
                    res_db = supabase.table("alunos").select("id, nome").execute()
                    df_db = pd.DataFrame(res_db.data) if res_db.data else pd.DataFrame(columns=['id', 'nome'])
                    mapa_nomes_db = {limpar_texto(row['nome']): row['id'] for _, row in df_db.iterrows()}
                    
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    lista_novos = []
                    lista_atualizados = []

                    for i, nome_aba in enumerate(abas):
                        turma_formatada = formatar_turma(nome_aba)
                        status_text.text(f"Processando Turma: {turma_formatada}...")
                        
                        df_turma = xl.parse(nome_aba)
                        
                        colunas_upper = [str(c).strip().upper() for c in df_turma.columns]
                        if "NOME" not in colunas_upper:
                            df_turma = xl.parse(nome_aba, header=None)
                            df_turma.rename(columns={0: 'Matrícula', 1: 'Nome', 2: 'Data de nascimento'}, inplace=True)
                        else:
                            df_turma.columns = [str(c).strip() for c in df_turma.columns]
                        
                        for _, row in df_turma.iterrows():
                            nome_aluno = str(row.get('Nome', '')).strip()
                            matricula = str(row.get('Matrícula', '')).strip()
                            data_nasc = str(row.get('Data de nascimento', ''))
                            
                            if not nome_aluno or nome_aluno.lower() == 'nan':
                                continue

                            chave = limpar_texto(nome_aluno)
                            
                            try:
                                data_formatada = pd.to_datetime(data_nasc, dayfirst=True).strftime('%Y-%m-%d')
                            except:
                                data_formatada = None

                            dados = {
                                "nome": nome_aluno.upper(),
                                "turma": turma_formatada,
                                "numero_matricula": matricula,
                                "data_nascimento": data_formatada
                            }

                            if chave in mapa_nomes_db:
                                supabase.table("alunos").update(dados).eq("id", mapa_nomes_db[chave]).execute()
                                lista_atualizados.append({"Nome": nome_aluno.upper(), "Turma": turma_formatada, "Status": "Atualizado"})
                            else:
                                supabase.table("alunos").insert(dados).execute()
                                lista_novos.append({"Nome": nome_aluno.upper(), "Turma": turma_formatada, "Status": "Novo Cadastro"})
                        
                        progress_bar.progress((i + 1) / len(abas))

                    status_text.success("✅ Sincronização concluída!")
                    
                    st.divider()
                    st.subheader("📝 Relatório da Operação")
                    col1, col2 = st.columns(2)
                    col1.metric("Novos Alunos", len(lista_novos))
                    col2.metric("Atualizados", len(lista_atualizados))

                    if lista_novos:
                        with st.expander("🔍 Ver detalhes dos NOVOS alunos adicionados"):
                            st.table(pd.DataFrame(lista_novos))
                    if lista_atualizados:
                        with st.expander("🔍 Ver detalhes dos alunos que receberam MATRÍCULA"):
                            st.table(pd.DataFrame(lista_atualizados))
                            
                    st.balloons()
            
            except Exception as e:
                st.error(f"Erro crítico: {e}")

    # =========================================================
    # ABA 4: CADASTRO MANUAL
    # =========================================================
    with aba_manual:
        st.subheader("Cadastrar Aluno Individualmente")
        with st.form("f_manual", clear_on_submit=True):
            n = st.text_input("Nome Completo:")
            t = st.text_input("Turma:")
            if st.form_submit_button("Cadastrar"):
                if n and t:
                    turma_formatada = formatar_turma(t)
                    supabase.table("alunos").insert({"nome": n.upper().strip(), "turma": turma_formatada}).execute()
                    st.success(f"Aluno cadastrado na turma {turma_formatada}!")
                    time.sleep(1)
                    st.rerun()

    # =========================================================
    # ABA 5: AUDITORIA, SINCRONIZAÇÃO E LIMPEZA (EXPURGO)
    # =========================================================
    with aba_sinc:
        st.subheader("🔄 Auditoria e Limpeza de Dados")
        
        tab_pendencia, tab_limpeza = st.tabs(["🔎 Matrículas Faltantes", "🗑️ Alunos Fora da Planilha"])

        # --- SUB-ABA 1: MATRÍCULAS FALTANTES (O que já tínhamos) ---
        with tab_pendencia:
            st.markdown("### Verificar quem está sem matrícula")
            res_t = supabase.table("alunos").select("turma").execute()
            lista_turmas_audit = sorted(list(set([x['turma'] for x in res_t.data if x['turma']])))
            
            if lista_turmas_audit:
                turma_audit = st.selectbox("Selecione a Turma:", ["Todas as Turmas"] + lista_turmas_audit, key="sel_audit")
                if st.button("Verificar Pendências", key="btn_audit"):
                    query = supabase.table("alunos").select("nome, turma, numero_matricula")
                    if turma_audit != "Todas as Turmas":
                        query = query.eq("turma", turma_audit)
                    
                    res_audit = query.order("nome").execute()
                    df_audit = pd.DataFrame(res_audit.data) if res_audit.data else pd.DataFrame()
                    
                    if not df_audit.empty:
                        df_audit['mat_limpa'] = df_audit['numero_matricula'].fillna("").astype(str).str.strip().str.lower()
                        df_pendentes = df_audit[df_audit['mat_limpa'].isin(["", "nan", "null", "none"])]
                        if not df_pendentes.empty:
                            st.warning(f"⚠️ {len(df_pendentes)} alunos sem matrícula.")
                            st.dataframe(df_pendentes[['nome', 'turma']], use_container_width=True, hide_index=True)
                        else:
                            st.success("✅ Tudo em ordem!")

        # --- SUB-ABA 2: LIMPEZA DE ALUNOS QUE SAÍRAM (EXPURGO) ---
        with tab_limpeza:
            st.markdown("### 🎯 Caçar Alunos fora da Planilha")
            st.info("Suba a planilha atualizada. O sistema dirá quem está no banco de dados mas NÃO está no arquivo (alunos que provavelmente saíram da escola).")
            
            arquivo_limpeza = st.file_uploader("Suba a planilha oficial para comparação (.xlsx)", type=["xlsx"], key="up_limpeza")
            
            if arquivo_limpeza:
                if st.button("🔍 Comparar Banco vs Planilha", type="primary"):
                    # 1. Pegar todos os nomes da PLANILHA
                    xl = pd.ExcelFile(arquivo_limpeza)
                    nomes_planilha = set()
                    for aba in xl.sheet_names:
                        df_aba = xl.parse(aba)
                        # Tenta achar a coluna Nome
                        col_nome = next((c for c in df_aba.columns if str(c).strip().upper() == "NOME"), None)
                        if col_nome:
                            nomes_planilha.update([limpar_texto(n) for n in df_aba[col_nome].dropna()])
                        else:
                            # Se não tem cabeçalho (caso do 1B), pega a segunda coluna (índice 1)
                            df_aba = xl.parse(aba, header=None)
                            nomes_planilha.update([limpar_texto(n) for n in df_aba[1].dropna()])

                    # 2. Pegar todos os nomes do BANCO
                    res_db = supabase.table("alunos").select("id, nome, turma").execute()
                    alunos_db = res_db.data if res_db.data else []
                    
                    # 3. Cruzar dados
                    sobrando = []
                    for al in alunos_db:
                        if limpar_texto(al['nome']) not in nomes_planilha:
                            sobrando.append(al)
                    
                    if sobrando:
                        st.error(f"🚨 Detectados {len(sobrando)} alunos que estão no banco mas não na planilha!")
                        df_sobrando = pd.DataFrame(sobrando)
                        st.dataframe(df_sobrando[['nome', 'turma']], use_container_width=True, hide_index=True)
                        
                        st.divider()
                        st.warning("Deseja excluir estes alunos permanentemente?")
                        if st.button("🔥 EXCLUIR TODOS OS ALUNOS LISTADOS ACIMA", type="secondary"):
                            ids_para_deletar = [str(a['id']) for a in sobrando]
                            # Deleta em lotes (Supabase suporta .in_)
                            for i in range(0, len(ids_para_deletar), 100):
                                lote = ids_para_deletar[i:i+100]
                                supabase.table("alunos").delete().in_("id", lote).execute()
                            
                            st.success("✅ Faxina concluída! Os alunos foram removidos.")
                            time.sleep(2)
                            st.rerun()
                    else:
                        st.success("✅ O banco de dados está perfeitamente sincronizado com a planilha! Ninguém sobrando.")