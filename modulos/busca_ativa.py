import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import unicodedata
import calendar
import os
from pathlib import Path

# ==========================================
# 1. FUNÇÕES DE LIMPEZA (IDÊNTICAS AO FOTOGRAMA)
# ==========================================
def limpar_texto(texto):
    """
    ESSA É A FUNÇÃO CORRETA DO FOTOGRAMA!
    Remove acentos, converte pra minúscula, remove espaços e caracteres especiais.
    """
    if not texto:
        return ""
    if "." in str(texto):
        texto = str(texto).rsplit(".", 1)[0]
    nfkd = unicodedata.normalize("NFKD", str(texto))
    texto_limpo = "".join(c for c in nfkd if not unicodedata.combining(c)).lower()
    return "".join(filter(str.isalnum, texto_limpo))


def normalizar(nome):
    """Função original do busca_ativa - mantida para compatibilidade"""
    if not nome: return ""
    nfkd = unicodedata.normalize('NFKD', str(nome))
    nome_limpo = "".join([c for c in nfkd if not unicodedata.combining(c)]).upper()
    return " ".join(nome_limpo.split())


# ==========================================
# 2. BUSCAR FOTOS (USANDO PYGITHUB - COMO FOTOGRAMA)
# ==========================================
@st.cache_data(ttl=3600)
def listar_fotos_github_correto():
    """
    FUNÇÃO CORRIGIDA: Usa PyGithub como o fotograma faz.
    Mais confiável, autenticada e funciona 100%!
    """
    try:
        # Verifica se tem token do GitHub
        if "GITHUB_TOKEN" not in st.secrets:
            st.warning("⚠️ GITHUB_TOKEN não configurado. Tentando com requests...")
            return listar_fotos_github_fallback()

        from github import Github, Auth

        auth = Auth.Token(st.secrets["GITHUB_TOKEN"])
        g = Github(auth=auth)
        repo = g.get_repo("erempamacesso/presence")
        contents = repo.get_contents("alunos_fotos")

        mapa = {}
        for arq in contents:
            nome_arquivo = getattr(arq, "name", None)
            download_url = getattr(arq, "download_url", None)

            if nome_arquivo and download_url:
                # ✅ USA limpar_texto() - MESMA FUNÇÃO DO FOTOGRAMA
                mapa[limpar_texto(nome_arquivo)] = str(download_url)

        return mapa

    except ImportError:
        st.warning("⚠️ PyGithub não instalada. Tentando fallback...")
        return listar_fotos_github_fallback()
    except Exception as e:
        st.warning(f"⚠️ Erro ao buscar fotos: {e}. Tentando fallback...")
        return listar_fotos_github_fallback()


@st.cache_data(ttl=3600)
def listar_fotos_github_fallback():
    """
    Fallback com requests (se PyGithub não estiver disponível)
    """
    import requests
    
    mapa = {}
    try:
        # Tenta com GitHub API
        api_url = "https://api.github.com/repos/erempamacesso/presence/contents/alunos_fotos"
        response = requests.get(api_url, timeout=10)
        
        if response.status_code == 200:
            arquivos = response.json()
            for arquivo in arquivos:
                if arquivo['type'] == 'file' and arquivo['name'].lower().endswith('.png'):
                    nome_arquivo = arquivo['name']
                    # ✅ USA limpar_texto() - MESMA FUNÇÃO
                    mapa[limpar_texto(nome_arquivo)] = arquivo['download_url']
    except:
        pass
    
    return mapa


# ==========================================
# 3. FALLBACK LOCAL
# ==========================================
def listar_nomes_com_foto_local():
    """Função original que tenta pasta local"""
    caminho_base = Path(__file__).resolve().parent.parent
    pasta_fotos_1 = caminho_base / "alunos_fotos"
    pasta_fotos_2 = Path("alunos_fotos").resolve()

    pasta_ativa = None
    if pasta_fotos_1.exists() and pasta_fotos_1.is_dir():
        pasta_ativa = pasta_fotos_1
    elif pasta_fotos_2.exists() and pasta_fotos_2.is_dir():
        pasta_ativa = pasta_fotos_2

    if not pasta_ativa:
        return None 
        
    try:
        nomes_fotos = set()
        for arquivo in pasta_ativa.iterdir():
            if arquivo.suffix.lower() in ['.png', '.jpg', '.jpeg']:
                # ✅ USA limpar_texto() - MESMA FUNÇÃO
                nomes_fotos.add(limpar_texto(arquivo.stem))
        return nomes_fotos
    except:
        return None


def exibir_busca_ativa(supabase, supabase_alunos):
    st.title("🕵️ Busca Ativa e Gestão de Frequência")

    tz = pytz.timezone('America/Recife')
    hoje = datetime.now(tz)
    
    try:
        # 1. CARREGA LISTA GERAL DE ALUNOS
        res_al = supabase_alunos.table("alunos").select("id, nome, turma").execute()
        if not res_al.data:
            st.error("Erro: Tabela de alunos não encontrada.")
            return
        
        df_al = pd.DataFrame(res_al.data)
        # ✅ USA limpar_texto() para criar coluna de busca
        df_al['nome_limpo'] = df_al['nome'].apply(limpar_texto)

        # ==========================================
        # ✅ LÓGICA DE FOTOS CORRIGIDA (COMO FOTOGRAMA)
        # ==========================================
        try:
            hoje_str = hoje.strftime('%Y-%m-%d')
            
            # 1º PASSO: Quem veio hoje?
            res_pres_hoje = supabase.table("frequencia").select("aluno_nome").eq(
                "data_chamada", hoje_str
            ).eq("status", "P").execute()
            
            if not res_pres_hoje.data:
                st.info("📋 Nenhum aluno presente registrado hoje.")
            else:
                # 2º PASSO: Buscar mapa de fotos (GitHub com fallback)
                # ✅ TENTA GITHUB PRIMEIRO (como fotograma faz)
                mapa_fotos = listar_fotos_github_correto()
                
                # Se GitHub falhou, tenta pasta local
                if not mapa_fotos:
                    nomes_com_foto = listar_nomes_com_foto_local()
                    if nomes_com_foto:
                        mapa_fotos = {nome: None for nome in nomes_com_foto}
                
                # 3º PASSO: Cruzar presentes com fotos
                if mapa_fotos:
                    # ✅ CRÍTICO: Limpar nomes dos presentes com mesma função
                    nomes_presentes_hoje = [limpar_texto(p['aluno_nome']) for p in res_pres_hoje.data]
                    
                    # Alunos presentes que NÃO têm foto
                    df_presentes = df_al[df_al['nome_limpo'].isin(nomes_presentes_hoje)]
                    df_sem_foto = df_presentes[~df_presentes['nome_limpo'].isin(mapa_fotos.keys())]
                    
                    # EXIBIR RESULTADO
                    if not df_sem_foto.empty:
                        st.error(f"📸 **Atenção:** Identificamos **{len(df_sem_foto)}** alunos presentes hoje sem foto no GitHub.")
                        with st.expander("📍 Ver Lista para Fotografar"):
                            for t, g in df_sem_foto.groupby('turma'):
                                alunos_lista = g.sort_values('nome')['nome'].tolist()
                                st.write(f"**{t}:** {', '.join(alunos_lista)}")
                    else:
                        st.success("✅ Show! Todos os alunos presentes hoje já possuem foto.")
                        st.metric("📸 Fotos Reconhecidas", len(mapa_fotos))
                else:
                    st.warning("⚠️ Não foi possível localizar a galeria de fotos (GitHub e pasta local indisponíveis).")
                    
        except Exception as e_foto:
            st.error(f"🚨 Erro ao verificar fotos: {e_foto}")
        # ==========================================

        #===============
        # 2. FILTROS
        #============
        st.markdown("### 📅 Filtros de Pesquisa")
        c1, c2, c3 = st.columns([1, 1, 2])
        meses_br = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
        with c1:
            mes_nome = st.selectbox("Mês", meses_br, index=hoje.month - 1)
            mes_num = meses_br.index(mes_nome) + 1
        with c2:
            ano_sel = st.selectbox("Ano", [2025, 2026], index=1)
        with c3:
            turma_sel = st.selectbox("Selecione a Turma:", sorted(df_al['turma'].dropna().unique().tolist()))

        # 3. BUSCA DE DADOS MENSAL
        ultimo_dia = calendar.monthrange(ano_sel, mes_num)[1]
        data_ini, data_fim = f"{ano_sel}-{mes_num:02d}-01", f"{ano_sel}-{mes_num:02d}-{ultimo_dia}"

        res_mensal = supabase.table("frequencia").select("aluno_nome, data_chamada").eq(
            "status", "P"
        ).eq("turma", turma_sel).filter(
            "data_chamada", "gte", data_ini
        ).filter(
            "data_chamada", "lte", data_fim
        ).execute()

        df_p_mes = pd.DataFrame(res_mensal.data) if res_mensal.data else pd.DataFrame()
        presencas_mes_set = set()
        if not df_p_mes.empty:
            # ✅ USA limpar_texto()
            df_p_mes['nome_limpo'] = df_p_mes['aluno_nome'].apply(limpar_texto)
            for _, r in df_p_mes.iterrows():
                presencas_mes_set.add((r['nome_limpo'], str(r['data_chamada']).split("-")[2]))

        # 4. INTERFACE EM ABAS
        abas = st.tabs(["📊 Ranking", "❌ Presença Zero", "🚩 Gazeando", "🚨 Ocorrências", "📅 Diário"])
        df_t = df_al[df_al['turma'] == turma_sel].copy()

        # --- ABA 0: RANKING ---
        with abas[0]:
            st.subheader(f"Resumo de Faltas - {mes_nome}")
            contagem = df_p_mes.groupby('nome_limpo').size().reset_index(name='presencas') if not df_p_mes.empty else pd.DataFrame(columns=['nome_limpo', 'presencas'])
            df_rank = pd.merge(df_t, contagem, on='nome_limpo', how='left').fillna(0)
            dias_letivos = df_p_mes['data_chamada'].nunique() if not df_p_mes.empty else 0
            df_rank['faltas'] = dias_letivos - df_rank['presencas']
            st.dataframe(df_rank[['nome', 'presencas', 'faltas']].sort_values('faltas', ascending=False), use_container_width=True, hide_index=True)

        # --- ABA 1: PRESENÇA ZERO ---
        with abas[1]:
            st.subheader("🚫 Alunos que não compareceram no mês")
            nomes_com_presenca = df_p_mes['nome_limpo'].unique() if not df_p_mes.empty else []
            df_zero = df_t[~df_t['nome_limpo'].isin(nomes_com_presenca)]
            if not df_zero.empty:
                st.warning(f"Identificados {len(df_zero)} alunos com 0% de frequência.")
                st.dataframe(df_zero[['nome', 'turma']], use_container_width=True, hide_index=True)
            else:
                st.success("Nenhum aluno com presença zero este mês!")

        # --- ABA 2: GAZEANDO (Risco de Evasão) ---
        with abas[2]:
            st.subheader("🚩 Alerta de Frequência Crítica")
            if not df_p_mes.empty:
                df_gaze = pd.merge(df_t, contagem, on='nome_limpo', how='left').fillna(0)
                df_gaze['pct'] = (df_gaze['presencas'] / dias_letivos) * 100
                df_critico = df_gaze[(df_gaze['presencas'] > 0) & (df_gaze['pct'] < 70)]
                if not df_critico.empty:
                    st.error("Alunos que frequentam raramente (Menos de 70% de presença)")
                    st.dataframe(df_critico[['nome', 'presencas', 'pct']].sort_values('pct'), use_container_width=True, hide_index=True)
                else:
                    st.success("Nenhum aluno em situação crítica de 'Gazeando'.")
            else: st.info("Dados insuficientes para calcular alertas.")

        # --- ABA 3: OCORRÊNCIAS ---
        with abas[3]:
            st.subheader("📝 Registrar Busca Ativa")
            with st.form("nova_oc"):
                aluno_oc = st.selectbox("Estudante:", df_t['nome'].tolist())
                tipo = st.selectbox("Tipo:", ["Falta Constante", "Abandono", "Saúde", "Visita Domiciliar", "Outros"])
                relato = st.text_area("Relato da Conversa/Situação:")
                if st.form_submit_button("Salvar Registro"):
                    try:
                        supabase.table("ocorrencias").insert({
                            "aluno_nome": aluno_oc, "tipo": tipo, "descricao": relato,
                            "data_registro": hoje.strftime('%Y-%m-%d'), "turma": turma_sel
                        }).execute()
                        st.success("Ocorrência registrada!")
                    except: st.error("Erro: Verifique se a tabela 'ocorrencias' existe no Supabase.")

        # --- ABA 4: DIÁRIO MENSAL ---
        with abas[4]:
            st.subheader(f"📅 Mapa: {turma_sel}")
            dias = [f"{d:02d}" for d in range(1, ultimo_dia + 1)]
            matriz = []
            for _, aluno in df_t.sort_values('nome').iterrows():
                linha = {"Estudante": aluno['nome']}
                for d in dias:
                    if (aluno['nome_limpo'], d) in presencas_mes_set: linha[d] = "✅"
                    else:
                        try:
                            dt = datetime(ano_sel, mes_num, int(d)).date()
                            if dt > hoje.date(): linha[d] = " "
                            elif dt.weekday() >= 5: linha[d] = "-"
                            else: linha[d] = "❌"
                        except: linha[d] = " "
                matriz.append(linha)
            st.dataframe(pd.DataFrame(matriz), use_container_width=True, hide_index=True, column_config={d: st.column_config.TextColumn(d, width=35) for d in dias})

    except Exception as e:
        st.error(f"Erro geral: {e}")