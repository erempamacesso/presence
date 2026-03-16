import streamlit as st
import pandas as pd
import unicodedata
import time

# --- FUNÇÕES DE UTILITÁRIO ---

def limpar_texto(texto):
    """Padronização para nomes de arquivos e chaves de busca"""
    if not texto: return ""
    # Remove extensão se houver
    if "." in str(texto): texto = str(texto).rsplit('.', 1)[0]
    nfkd = unicodedata.normalize('NFKD', str(texto))
    texto_limpo = "".join([c for c in nfkd if not unicodedata.combining(c)]).lower()
    return "".join(filter(str.isalnum, texto_limpo))

def listar_arquivos_bucket(supabase):
    try:
        arquivos = supabase.storage.from_('fotos-alunos').list(path=None, options={'limit': 5000})
        mapa = {limpar_texto(arq['name']): arq['name'] for arq in arquivos}
        return mapa
    except: return {}

# --- FUNÇÃO PRINCIPAL DE INTERFACE ---

def exibir_cadastro(supabase):
    st.title("👤 Sistema de Gestão Escolar")
    
    # Organização Profissional das Abas
    aba_busca, aba_gerenciar, aba_excel, aba_manual = st.tabs([
        "🔍 Localizar Aluno", 
        "📸 Fotos e Turmas", 
        "📁 Atualização Excel", 
        "➕ Cadastro Avulso"
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
    # ABA 3: ATUALIZAÇÃO EXCEL (COM RELATÓRIO DE OPERAÇÕES)
    # =========================================================
    with aba_excel:
        st.subheader("📁 Sincronização Total via Planilha")
        st.info("O sistema lerá cada aba (ex: 1A, 1B) e vinculará os alunos automaticamente.")
        
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
                    
                    # Listas para o relatório final
                    lista_novos = []
                    lista_atualizados = []

                    for i, nome_aba in enumerate(abas):
                        status_text.text(f"Processando Turma: {nome_aba}...")
                        df_turma = xl.parse(nome_aba)
                        df_turma.columns = [c.strip() for c in df_turma.columns]
                        
                        for _, row in df_turma.iterrows():
                            nome_aluno = str(row.get('Nome', '')).strip()
                            matricula = str(row.get('Matrícula', ''))
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
                                "turma": nome_aba,
                                "numero_matricula": matricula,
                                "data_nascimento": data_formatada
                            }

                            if chave in mapa_nomes_db:
                                supabase.table("alunos").update(dados).eq("id", mapa_nomes_db[chave]).execute()
                                lista_atualizados.append({"Nome": nome_aluno.upper(), "Turma": nome_aba, "Status": "Matrícula Atualizada"})
                            else:
                                supabase.table("alunos").insert(dados).execute()
                                lista_novos.append({"Nome": nome_aluno.upper(), "Turma": nome_aba, "Status": "Novo Cadastro"})
                        
                        progress_bar.progress((i + 1) / len(abas))

                    status_text.success("✅ Sincronização concluída!")
                    
                    # --- EXIBIÇÃO DO RELATÓRIO ---
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
                    supabase.table("alunos").insert({"nome": n.upper().strip(), "turma": t.upper().strip()}).execute()
                    st.success("Aluno cadastrado!")
                    time.sleep(1)
                    st.rerun()

# =========================================================
    # ABA 5: SINCRONIZAÇÃO FORÇADA DE MATRÍCULAS
    # =========================================================
    with aba_manual: # Se você quiser criar uma nova: st.tabs([... , "🔄 Sincronizar Matrículas"])
        pass # Apenas marcador

    # Nota: Adicione "Aba Sincronizar" na sua lista de st.tabs lá no início do código
    # aba_busca, aba_gerenciar, aba_excel, aba_manual, aba_sinc = st.tabs([...])
    
    with aba_sinc:
        st.subheader("🔄 Sincronização Forçada de Matrículas")
        st.warning("Esta ferramenta busca alunos pelo nome e preenche a matrícula que estiver faltando.")
        
        arquivo_sinc = st.file_uploader("Suba a planilha completa (.xlsx)", type=["xlsx"], key="sinc_up")
        
        if arquivo_sinc:
            xl_sinc = pd.ExcelFile(arquivo_sinc)
            
            if st.button("🔍 Cruzar Dados e Atualizar Matrículas", type="primary"):
                # 1. Pegar todos os alunos do banco que NÃO TÊM matrícula
                res = supabase.table("alunos").select("id, nome").is_("numero_matricula", "null").execute()
                # Se o filtro de null falhar, pegamos todos para garantir:
                if not res.data:
                    res = supabase.table("alunos").select("id, nome").execute()
                
                alunos_db = res.data
                mapa_db = {limpar_texto(a['nome']): a['id'] for a in alunos_db}
                
                sucesso = []
                falha = []
                
                progress = st.progress(0)
                abas = xl_sinc.sheet_names
                
                for idx, nome_aba in enumerate(abas):
                    df_aba = xl_sinc.parse(nome_aba)
                    df_aba.columns = [c.strip() for c in df_aba.columns]
                    
                    for _, row in df_aba.iterrows():
                        nome_planilha = str(row.get('Nome', '')).strip()
                        matricula = str(row.get('Matrícula', ''))
                        
                        if nome_planilha and matricula and matricula != 'nan':
                            chave_planilha = limpar_texto(nome_planilha)
                            
                            if chave_planilha in mapa_db:
                                id_banco = mapa_db[chave_planilha]
                                # ATUALIZAÇÃO APENAS DA MATRÍCULA
                                supabase.table("alunos").update({"numero_matricula": matricula}).eq("id", id_banco).execute()
                                sucesso.append({"Nome": nome_planilha.upper(), "Matrícula": matricula, "Turma": nome_aba})
                    
                    progress.progress((idx + 1) / len(abas))
                
                st.success(f"✅ Finalizado! {len(sucesso)} matrículas foram vinculadas com sucesso.")
                
                if sucesso:
                    with st.expander("📄 Ver alunos atualizados"):
                        st.dataframe(pd.DataFrame(sucesso))