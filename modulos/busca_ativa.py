import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import unicodedata
from urllib.parse import quote

# --- FUNÇÕES DE APOIO PARA AS FOTOS ---
def limpar_texto_absoluto(texto):
    if not texto: return ""
    texto = str(texto).strip().lower()
    if "." in texto: texto = texto.rsplit(".", 1)[0]
    nfkd = unicodedata.normalize('NFKD', texto)
    sem_acento = "".join([c for c in nfkd if not unicodedata.combining(c)])
    return "".join(filter(str.isalnum, sem_acento))

@st.cache_data(ttl=300)
def listar_arquivos_bucket(_supabase):
    try:
        arquivos = _supabase.storage.from_('fotos-alunos').list(path=None, options={'limit': 5000})
        mapa = {}
        for arq in arquivos:
            nome_original = arq.get('name')
            if nome_original:
                nome_sem_ext = nome_original.rsplit('.', 1)[0] if '.' in nome_original else nome_original
                mapa[limpar_texto_absoluto(nome_sem_ext)] = nome_original
        return mapa
    except: return {}


def exibir_busca_ativa(supabase):
    st.title("🔎 Painel de Busca Ativa")
    st.caption("Inteligência de Dados para Prevenção ao Abandono Escolar")
    st.markdown("---")

    fuso = pytz.timezone('America/Recife')
    hoje = datetime.now(fuso).strftime('%Y-%m-%d')

    # --- 1. MÉTRICAS RÁPIDAS (HOJE) ---
    st.subheader(f"📊 Resumo do Dia: {datetime.now(fuso).strftime('%d/%m/%Y')}")
    
    col1, col2, col3 = st.columns(3)

    try:
        res_faltas = supabase.table("frequencia").select("id", count="exact").eq("data_chamada", hoje).eq("status", "F").execute()
        total_faltas = res_faltas.count if res_faltas.count else 0
        
        res_evasoes = supabase.table("evasoes").select("id", count="exact").eq("data_registro", hoje).execute()
        total_evasoes = res_evasoes.count if res_evasoes.count else 0

        res_pres = supabase.table("frequencia").select("id", count="exact").eq("data_chamada", hoje).eq("status", "P").execute()
        total_presentes = res_pres.count if res_pres.count else 0

        col1.metric("Faltas (Entrada)", total_faltas)
        col2.metric("Evasões (Em aula)", total_evasoes)
        col3.metric("Presentes Agora", total_presentes)
    except:
        st.error("Erro ao carregar métricas.")

    st.markdown("---")

    # --- 2. CRUZAMENTO CRÍTICO: EVASÃO INTERNA ---
    st.subheader("🚨 Alerta de Evasão Interna")
    st.write("Alunos que deram presença na entrada, mas foram registrados saindo de alguma aula.")

    try:
        pres_hoje = supabase.table("frequencia").select("aluno_nome, turma").eq("data_chamada", hoje).eq("status", "P").execute()
        evas_hoje = supabase.table("evasoes").select("aluno_nome, turma, aula_periodo").eq("data_registro", hoje).execute()

        if pres_hoje.data and evas_hoje.data:
            df_pres = pd.DataFrame(pres_hoje.data)
            df_evas = pd.DataFrame(evas_hoje.data)
            fugoes_internos = df_evas[df_evas['aluno_nome'].isin(df_pres['aluno_nome'])]
            
            if not fugoes_internos.empty:
                st.warning(f"Atenção: {len(fugoes_internos)} alunos entraram na escola mas não estão em sala.")
                st.dataframe(fugoes_internos[['aluno_nome', 'turma', 'aula_periodo']], use_container_width=True, hide_index=True)
            else:
                st.success("Nenhuma evasão interna detectada hoje.")
        else:
            st.info("Aguardando registros para cruzar dados hoje.")
    except Exception as e:
        st.error(f"Erro no processamento: {e}")

    st.markdown("---")

    # --- 3. RANKING DINÂMICO DE FALTAS (COM FOTOS E BARRAS) ---
    st.subheader("🏆 Ranking de Alunos Faltosos (Últimos 5 dias)")
    
    # SLIDER PARA FILTRAGEM (A MÁGICA ACONTECE AQUI)
    min_faltas = st.slider(
        "Filtrar a partir de quantas faltas?", 
        min_value=1, 
        max_value=5, 
        value=3, 
        help="Deslize para ver apenas os alunos que atingiram este número de faltas."
    )

    try:
        res_hist = supabase.table("frequencia").select("aluno_nome, turma").eq("status", "F").execute()
        
        if res_hist.data:
            df_hist = pd.DataFrame(res_hist.data)
            ranking = df_hist['aluno_nome'].value_counts().reset_index()
            ranking.columns = ['Aluno', 'Faltas']
            
            # Aplica o filtro do SLIDER
            ranking = ranking[ranking['Faltas'] >= min_faltas]
            
            if ranking.empty:
                st.success(f"Nenhum aluno com {min_faltas} ou mais faltas! 🎉")
            else:
                # Recupera a turma
                df_turmas = df_hist.drop_duplicates('aluno_nome')[['aluno_nome', 'turma']]
                ranking = ranking.merge(df_turmas, left_on='Aluno', right_on='aluno_nome').drop('aluno_nome', axis=1)

                # --- LÓGICA INTELIGENTE DE FOTOS ---
                mapa_fotos = listar_arquivos_bucket(supabase)
                url_base = f"{st.secrets['SUPABASE_URL']}/storage/v1/object/public/fotos-alunos/"
                foto_fallback = "https://cdn-icons-png.flaticon.com/512/149/149071.png"

                def buscar_url_foto(nome_aluno):
                    nome_limpo = limpar_texto_absoluto(nome_aluno)
                    prim_limpo = limpar_texto_absoluto(nome_aluno.split()[0])
                    # Tenta achar no bucket igual fizemos na chamada
                    nome_arq = mapa_fotos.get(nome_limpo) or mapa_fotos.get(prim_limpo)
                    if nome_arq:
                        return f"{url_base}{quote(nome_arq)}"
                    return foto_fallback

                # Aplica a função de fotos para criar a coluna
                ranking['Foto'] = ranking['Aluno'].apply(buscar_url_foto)

                # Ordena e organiza as colunas
                ranking = ranking.sort_values(by=['Faltas', 'turma'], ascending=[False, True])
                ranking = ranking[['Foto', 'Aluno', 'turma', 'Faltas']]

                # --- TABELA VISUAL PREMIUM (COMPACTA E COM MAPA DE CALOR) ---
                st.dataframe(
                    ranking,
                    use_container_width=True,
                    hide_index=True, # Tira o índice (0, 1, 2)
                    column_config={
                        "Foto": st.column_config.ImageColumn("📸", width="small"),
                        "Aluno": st.column_config.TextColumn("Nome do Estudante", width="medium"),
                        "turma": st.column_config.TextColumn("Turma", width="small"),
                        "Faltas": st.column_config.ProgressColumn(
                            "🔥 Nível de Alerta",
                            help="Mapa de calor: indica gravidade de aproximação de 5 faltas",
                            format="%d faltas",
                            min_value=0,
                            max_value=5
                        )
                    }
                )
        else:
            st.info("Ainda não há histórico de faltas acumulado.")
    except Exception as e:
        st.error(f"Erro ao gerar ranking visual: {e}")
