import streamlit as st
import pandas as pd
from supabase import create_client
import os
from dotenv import load_dotenv
import unicodedata
import time
from datetime import datetime, date
from streamlit_option_menu import option_menu
from urllib.parse import quote

# ==================================================
# 1. CONFIGURAÇÃO E CONEXÃO INTELIGENTE
# ==================================================
st.set_page_config(
    page_title="SIGPAM - EREMPAM", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

load_dotenv()

SUPABASE_URL = st.secrets.get("SUPABASE_URL") or os.getenv("SUPABASE_URL")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY") or os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("ERRO: Credenciais não encontradas. Verifique seu arquivo .env")
    st.stop()

try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error(f"Erro de Conexão: {e}")
    st.stop()

# ==================================================
# 2. CONFIGURAÇÃO DOS TRIMESTRES (2026)
# ==================================================
TRIMESTRES = {
    "1º Trimestre": (date(2026, 2, 2), date(2026, 5, 20)),
    "2º Trimestre": (date(2026, 5, 21), date(2026, 9, 11)),
    "3º Trimestre": (date(2026, 9, 12), date(2026, 12, 30))
}

# ==================================================
# 3. FUNÇÕES AUXILIARES
# ==================================================
def limpar_texto(texto):
    if not texto: return ""
    texto = str(texto)
    if "." in texto: texto = texto.rsplit(".", 1)[0]
    nfkd = unicodedata.normalize('NFKD', texto)
    sem_acento = "".join([c for c in nfkd if not unicodedata.combining(c)])
    return sem_acento.lower().replace(" ", "").replace("_", "").replace("-", "").strip()

def listar_arquivos_bucket():
    try:
        arquivos = supabase.storage.from_('fotos-alunos').list(path=None, options={'limit': 5000})
        mapa = {}
        if arquivos:
            for arq in arquivos:
                nome_real = arq.get('name') if isinstance(arq, dict) else getattr(arq, 'name', '')
                if not nome_real or nome_real == ".emptyFolderPlaceholder": continue
                chave = limpar_texto(nome_real)
                mapa[chave] = nome_real
        return mapa
    except Exception as e: 
        return {}

def get_foto_url(nome_real_arquivo):
    try:
        path_seguro = quote(nome_real_arquivo)
        url_base = f"{SUPABASE_URL}/storage/v1/object/public/fotos-alunos/{path_seguro}"
        return f"{url_base}?t={int(time.time())}"
    except: return None

# ==================================================
# 4. SIDEBAR
# ==================================================

if 'menu_atual' not in st.session_state:
    st.session_state['menu_atual'] = "Fotograma"

with st.sidebar:
    col_e, col_centro, col_d = st.columns([1, 1, 1])
    with col_centro:
        if os.path.exists("logo_erempam.png"):
            st.image("logo_erempam.png", use_container_width=True)
        else:
            st.markdown("<h1>🏫</h1>", unsafe_allow_html=True)
    
    st.markdown("<h3 style='text-align: center;'>SIGPAM</h3>", unsafe_allow_html=True)
    
    menu_escolhido = option_menu(
        menu_title=None,
        options=["Fotograma", "Frequência", "Reposicionar Estudante", "Cadastro", "Importação"],
        icons=["camera-fill", "clipboard-check-fill", "arrow-left-right", "person-plus-fill", "cloud-upload-fill"],
        default_index=0,
        styles={
            "container": {"padding": "0!important", "background-color": "#f0f2f6"},
            "nav-link-selected": {"background-color": "#ff4b4b"},
        }
    )

if st.session_state['menu_atual'] != menu_escolhido:
    st.session_state['menu_atual'] = menu_escolhido
    st.rerun()

# ==================================================
# 5. CONTEÚDO
# ==================================================

# --- FOTOGRAMA ---
if menu_escolhido == "Fotograma":
    st.title("📸 Mapa de Sala")
    try:
        res = supabase.table("alunos").select("turma").execute()
        lista_turmas = sorted(list(set([x['turma'] for x in res.data if x.get('turma')])))
    except: lista_turmas = []

    if not lista_turmas:
        st.warning("Nenhuma turma cadastrada.")
    else:
        turma_selecionada = st.selectbox("📂 Selecione a Turma:", lista_turmas)
        data_alunos = supabase.table("alunos").select("*").eq("turma", turma_selecionada).execute().data
        
        if data_alunos: data_alunos.sort(key=lambda x: x['nome']) 
        mapa_fotos = listar_arquivos_bucket()
        st.markdown("---")
        
        if not data_alunos:
            st.info("Turma vazia.")
        else:
            qtde_por_linha = 4
            for i in range(0, len(data_alunos), qtde_por_linha):
                batch = data_alunos[i : i + qtde_por_linha]
                cols = st.columns(qtde_por_linha)
                for idx, aluno in enumerate(batch):
                    with cols[idx]:
                        with st.container(border=True):
                            chave = limpar_texto(aluno['nome'])
                            arq_real = mapa_fotos.get(chave)
                            if arq_real:
                                st.image(get_foto_url(arq_real), use_container_width=True)
                            else:
                                st.markdown("<div style='height:80px; display:flex; align-items:center; justify-content:center; background:#f0f0f0; border-radius:5px;'>👤</div>", unsafe_allow_html=True)
                            st.markdown(f"<p style='text-align:center; font-weight:bold; font-size:12px; margin-top:5px;'>{aluno['nome']}</p>", unsafe_allow_html=True)

# --- FREQUÊNCIA (COM PAINEL GERAL DIÁRIO) ---
elif menu_escolhido == "Frequência":
    st.title("📊 Gestão de Frequência")

    # Busca TODOS os dados de frequência
    try:
        response = supabase.table("frequencia").select("*").execute()
        dados = response.data
    except Exception as e:
        st.error(f"Erro ao buscar dados: {e}")
        dados = []

    if not dados:
        st.warning("Ainda não há chamadas registradas no sistema.")
    else:
        # Prepara o DataFrame
        df = pd.DataFrame(dados)
        df['data_chamada'] = pd.to_datetime(df['data_chamada']).dt.date

        # CRIAÇÃO DAS ABAS
        aba1, aba2, aba3 = st.tabs(["📅 Visão Diária", "🚨 Busca Ativa (Trimestres)", "👤 Histórico do Aluno"])

        # --- ABA 1: VISÃO DIÁRIA ---
        with aba1:
            st.markdown("### Resumo do Dia")
            
            # Seletor de Data (Controla tudo nesta aba)
            data_selecionada = st.date_input("Data de Análise:", value=datetime.now())
            
            # 1. FILTRO GERAL POR DATA (Para o Painel da Escola)
            df_hoje_geral = df[df['data_chamada'] == data_selecionada]
            
            if df_hoje_geral.empty:
                st.info(f"Nenhuma chamada registrada em {data_selecionada.strftime('%d/%m/%Y')}.")
            else:
                # --- MÉTRICAS GERAIS DA ESCOLA ---
                total_alunos_hoje = len(df_hoje_geral)
                total_presentes_hoje = len(df_hoje_geral[df_hoje_geral['status'] == 'P'])
                total_faltas_hoje = len(df_hoje_geral[df_hoje_geral['status'] == 'F'])
                perc_hoje = int((total_presentes_hoje / total_alunos_hoje) * 100) if total_alunos_hoje > 0 else 0
                
                # Container Visual de Resumo
                with st.container(border=True):
                    st.markdown(f"**Situação da Escola em {data_selecionada.strftime('%d/%m/%Y')}**")
                    k1, k2, k3 = st.columns(3)
                    k1.metric("Alunos Presentes (Total)", total_presentes_hoje)
                    k2.metric("Alunos Faltosos", total_faltas_hoje, delta_color="inverse")
                    k3.metric("Adesão Geral", f"{perc_hoje}%")
                    
                    st.markdown("---")
                    st.markdown("**📊 Presença por Turma:**")
                    
                    # Calcula Presença por Turma
                    df_presencas_apenas = df_hoje_geral[df_hoje_geral['status'] == 'P']
                    if not df_presencas_apenas.empty:
                        # Agrupa e conta
                        resumo_turmas = df_presencas_apenas['turma'].value_counts().reset_index()
                        resumo_turmas.columns = ['Turma', 'Qtd Presentes']
                        resumo_turmas = resumo_turmas.sort_values(by='Turma')
                        
                        # Mostra em duas colunas: Gráfico e Tabela
                        rc1, rc2 = st.columns([2, 1])
                        with rc1:
                            st.bar_chart(resumo_turmas.set_index('Turma'), color="#4CAF50")
                        with rc2:
                            st.dataframe(resumo_turmas, use_container_width=True, hide_index=True)
                    else:
                        st.warning("Nenhum aluno presente registrado hoje.")

                # --- LISTAGEM DETALHADA ---
                st.markdown("### 📋 Detalhes da Chamada")
                turmas_disponiveis = sorted(df_hoje_geral['turma'].unique())
                turma_sel = st.selectbox("Filtrar Turma Específica:", ["Todas"] + turmas_disponiveis)

                df_detalhe = df_hoje_geral.copy()
                if turma_sel != "Todas":
                    df_detalhe = df_detalhe[df_detalhe['turma'] == turma_sel]

                # Tabela Colorida
                df_detalhe['Status Visual'] = df_detalhe['status'].apply(lambda x: "✅ Presente" if x == "P" else "❌ Falta")
                st.dataframe(
                    df_detalhe[['turma', 'aluno_nome', 'Status Visual']].sort_values(by=['turma', 'aluno_nome']),
                    use_container_width=True,
                    hide_index=True
                )

        # --- ABA 2: BUSCA ATIVA (COM TRIMESTRES) ---
        with aba2:
            st.markdown("### 🕵️‍♂️ Monitoramento de Faltas")
            st.info("Analise quem está faltando muito em cada período letivo.")
            
            # SELETOR DE PERÍODO
            opcoes_periodo = list(TRIMESTRES.keys()) + ["Personalizado"]
            escolha_periodo = st.radio("Selecione o Período:", options=opcoes_periodo, horizontal=True)
            
            # Lógica das Datas
            if escolha_periodo == "Personalizado":
                c1, c2 = st.columns(2)
                inicio = c1.date_input("Início", value=date(2026, 1, 1))
                fim = c2.date_input("Fim", value=datetime.now().date())
            else:
                inicio, fim = TRIMESTRES[escolha_periodo]
                st.success(f"🗓️ Período Selecionado: **{inicio.strftime('%d/%m/%Y')}** até **{fim.strftime('%d/%m/%Y')}**")
                
                if escolha_periodo == "2º Trimestre":
                    st.caption("ℹ️ *Atenção: O recesso escolar ocorre entre 10/07 e 24/07.*")

            st.divider()

            # Filtra pelo período
            mask = (df['data_chamada'] >= inicio) & (df['data_chamada'] <= fim)
            df_periodo = df.loc[mask]

            if not df_periodo.empty:
                # Conta apenas as FALTAS ("F")
                df_faltas = df_periodo[df_periodo['status'] == 'F']
                
                if not df_faltas.empty:
                    # Agrupa e Conta
                    ranking = df_faltas.groupby(['turma', 'aluno_nome']).size().reset_index(name='Total de Faltas')
                    ranking = ranking.sort_values(by='Total de Faltas', ascending=False)
                    
                    # FILTRO DE ALERTA
                    alerta = st.slider(f"⚠️ Mostrar alunos com mais de X faltas neste {escolha_periodo}:", 0, 20, 5)
                    ranking_critico = ranking[ranking['Total de Faltas'] >= alerta]
                    
                    if not ranking_critico.empty:
                        st.error(f"🚩 **{len(ranking_critico)} Alunos** em situação crítica:")
                        st.dataframe(ranking_critico, use_container_width=True, hide_index=True)
                    else:
                        st.success("🎉 Nenhum aluno atingiu esse limite de faltas neste período.")
                else:
                    st.success("🎉 Nenhuma falta registrada neste período! Frequência perfeita.")
            else:
                st.warning("📭 Sem dados de chamada lançados dentro destas datas.")

        # --- ABA 3: HISTÓRICO DO ALUNO ---
        with aba3:
            st.markdown("### 📄 Ficha Individual")
            
            lista_alunos = sorted(df['aluno_nome'].unique())
            aluno_search = st.selectbox("Pesquisar Aluno:", lista_alunos)
            
            if aluno_search:
                df_aluno = df[df['aluno_nome'] == aluno_search].sort_values(by='data_chamada', ascending=False)
                
                total_aulas = len(df_aluno)
                total_faltas = len(df_aluno[df_aluno['status'] == 'F'])
                freq_perc = 100 - ((total_faltas / total_aulas) * 100) if total_aulas > 0 else 0
                
                m1, m2, m3 = st.columns(3)
                m1.metric("Total de Aulas", total_aulas)
                m2.metric("Total de Faltas", total_faltas, delta_color="inverse")
                m3.metric("Frequência Global", f"{freq_perc:.1f}%")
                
                # Barra de Progresso
                cor_barra = ":green" if freq_perc >= 75 else ":red"
                st.write(f"Situação: **{freq_perc:.1f}%** de Presença {cor_barra}[{'▮'*int(freq_perc/5)}{'▯'*(20-int(freq_perc/5))}]")

                st.divider()
                st.write("Histórico Detalhado:")
                
                df_aluno['Status'] = df_aluno['status'].apply(lambda x: "🔴 Falta" if x == "F" else "🟢 Presente")
                df_aluno['Data'] = df_aluno['data_chamada'].apply(lambda x: x.strftime('%d/%m/%Y'))
                
                st.dataframe(
                    df_aluno[['Data', 'turma', 'Status']],
                    use_container_width=True,
                    hide_index=True
                )

# --- REPOSICIONAR ---
elif menu_escolhido == "Reposicionar Estudante":
    st.title("🔄 Reposicionar")
    try:
        res = supabase.table("alunos").select("turma").execute()
        lista_turmas = sorted(list(set([x['turma'] for x in res.data if x.get('turma')])))
    except: lista_turmas = []
    
    turma_origem = st.selectbox("Turma Atual:", lista_turmas)
    data_alunos = supabase.table("alunos").select("*").eq("turma", turma_origem).execute().data
    if data_alunos: data_alunos.sort(key=lambda x: x['nome'])
    mapa_fotos = listar_arquivos_bucket()
    
    st.divider()
    for aluno in data_alunos:
        c1, c2, c3 = st.columns([1, 4, 3])
        with c1:
            chave = limpar_texto(aluno['nome'])
            if mapa_fotos.get(chave): st.image(get_foto_url(mapa_fotos.get(chave)), width=40)
            else: st.markdown("👤")
        with c2: st.write(aluno['nome'])
        with c3:
            try: idx = lista_turmas.index(aluno['turma'])
            except: idx = 0
            nova = st.selectbox("Mudar", lista_turmas, index=idx, key=f"r_{aluno['id']}", label_visibility="collapsed")
            if nova != aluno['turma']:
                supabase.table("alunos").update({"turma": nova}).eq("id", aluno['id']).execute()
                st.toast(f"Movido para {nova}")
                time.sleep(0.5)
                st.rerun()

# --- CADASTRO ---
elif menu_escolhido == "Cadastro":
    st.title("👤 Novo Aluno")
    with st.form("form_cad"):
        nome = st.text_input("Nome")
        turma = st.text_input("Turma")
        if st.form_submit_button("Salvar"):
            supabase.table("alunos").insert({"nome": nome.upper().strip(), "turma": turma.upper().strip()}).execute()
            st.success("Salvo!")

# --- IMPORTAÇÃO ---
elif menu_escolhido == "Importação":
    st.title("📤 Importar Excel/CSV")
    arquivo = st.file_uploader("Arquivo", type=["csv", "xlsx"])
    if arquivo and st.button("Processar"):
        if arquivo.name.endswith('.csv'): df = pd.read_csv(arquivo)
        else: df = pd.read_excel(arquivo)
        df.columns = [str(c).lower().strip() for c in df.columns]
        count = 0
        bar = st.progress(0)
        for i, row in df.iterrows():
            bar.progress((i+1)/len(df))
            try:
                nome = str(row['nome']).upper().strip()
                t = row.get('turma', 'SEM TURMA')
                check = supabase.table("alunos").select("id").eq("nome", nome).execute()
                if not check.data:
                    supabase.table("alunos").insert({"nome": nome, "turma": str(t).strip()}).execute()
                    count += 1
            except: pass
        st.success(f"{count} alunos importados.")
        time.sleep(2)
        st.rerun()
