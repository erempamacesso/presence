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
    # ABA 3: ATUALIZAÇÃO EXCEL (DETECÇÃO AUTOMÁTICA DE TURMAS)
    # =========================================================
    with aba_excel:
        st.subheader("📁 Sincronização Total via Planilha")
        st.info("O sistema lerá cada aba (ex: 1A, 1B) e cadastrará os alunos na turma correspondente.")
        
        arquivo = st.file_uploader("Suba a planilha da secretaria (.xlsx)", type=["xlsx"])
        
        if arquivo:
            try:
                # 1. Carregar o arquivo Excel completo (todas as abas)
                xl = pd.ExcelFile(arquivo)
                abas = xl.sheet_names
                st.write(f"📊 Abas detectadas: {', '.join(abas)}")

                if st.button("🚀 Iniciar Sincronização Geral", type="primary"):
                    # 2. Buscar alunos atuais para evitar duplicados
                    res_db = supabase.table("alunos").select("id, nome").execute()
                    df_db = pd.DataFrame(res_db.data) if res_db.data else pd.DataFrame(columns=['id', 'nome'])
                    mapa_nomes_db = {limpar_texto(row['nome']): row['id'] for _, row in df_db.iterrows()}
                    
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    total_novos = 0
                    total_updates = 0

                    for i, nome_aba in enumerate(abas):
                        status_text.text(f"Processando Turma: {nome_aba}...")
                        df_turma = xl.parse(nome_aba)
                        
                        # Padronizar colunas para evitar erros de maiúsculo/minúsculo
                        df_turma.columns = [c.strip() for c in df_turma.columns]
                        
                        registros_turma = []
                        
                        for _, row in df_turma.iterrows():
                            # Extrair dados conforme seu print
                            nome_aluno = str(row.get('Nome', '')).strip()
                            matricula = str(row.get('Matrícula', ''))
                            data_nasc = str(row.get('Data de nascimento', ''))
                            
                            if not nome_aluno or nome_aluno.lower() == 'nan':
                                continue

                            chave = limpar_texto(nome_aluno)
                            
                            # Formatar data para o Supabase (YYYY-MM-DD)
                            try:
                                data_formatada = pd.to_datetime(data_nasc, dayfirst=True).strftime('%Y-%m-%d')
                            except:
                                data_formatada = None

                            dados = {
                                "nome": nome_aluno.upper(),
                                "turma": nome_aba, # Nome da aba vira a turma automaticamente
                                "numero_matricula": matricula,
                                "data_nascimento": data_formatada
                            }

                            if chave in mapa_nomes_db:
                                # UPDATE: Já existe, vamos atualizar matrícula e data
                                supabase.table("alunos").update(dados).eq("id", mapa_nomes_db[chave]).execute()
                                total_updates += 1
                            else:
                                # INSERT: Aluno novo
                                supabase.table("alunos").insert(dados).execute()
                                total_novos += 1
                        
                        progress_bar.progress((i + 1) / len(abas))

                    st.success("✅ Sincronização concluída com sucesso!")
                    col1, col2 = st.columns(2)
                    col1.metric("Novos Alunos", total_novos)
                    col2.metric("Matrículas Atualizadas", total_updates)
                    st.balloons()
            
            except Exception as e:
                st.error(f"Erro crítico no processamento: {e}")

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
