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

    # --- 1. MÉTRICAS RÁPIDAS (HOJE) - FICA FIXO NO TOPO ---
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

    # ==========================================
    # CRIANDO AS ABAS
    # ==========================================
    aba_ranking, aba_mapa = st.tabs(["🚨 Alertas & Ranking de Faltas", "🗺️ Mapa de Evasões"])

    # ==========================================
    # ABA 1: ALERTA INTERNO E RANKING DE FALTAS
    # ==========================================
    with aba_ranking:
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

        # --- 3. RANKING DINÂMICO DE FALTAS ---
        st.subheader("🏆 Ranking de Alunos Faltosos (Últimos 5 dias)")
        
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
                
                ranking = ranking[ranking['Faltas'] >= min_faltas]
                
                if ranking.empty:
                    st.success(f"Nenhum aluno com {min_faltas} ou mais faltas! 🎉")
                else:
                    df_turmas = df_hist.drop_duplicates('aluno_nome')[['aluno_nome', 'turma']]
                    ranking = ranking.merge(df_turmas, left_on='Aluno', right_on='aluno_nome').drop('aluno_nome', axis=1)

                    mapa_fotos = listar_arquivos_bucket(supabase)
                    url_base = f"{st.secrets['SUPABASE_URL']}/storage/v1/object/public/fotos-alunos/"
                    foto_fallback = "https://cdn-icons-png.flaticon.com/512/149/149071.png"

                    def buscar_url_foto(nome_aluno):
                        nome_limpo = limpar_texto_absoluto(nome_aluno)
                        prim_limpo = limpar_texto_absoluto(nome_aluno.split()[0])
                        nome_arq = mapa_fotos.get(nome_limpo) or mapa_fotos.get(prim_limpo)
                        if nome_arq:
                            return f"{url_base}{quote(nome_arq)}"
                        return foto_fallback

                    ranking['Foto'] = ranking['Aluno'].apply(buscar_url_foto)
                    ranking = ranking.sort_values(by=['Faltas', 'turma'], ascending=[False, True])

                    # ==========================================
                    # TABELA HTML CUSTOMIZADA PARA FOTOS GRANDES
                    # ==========================================
                    html_table = """
                    <style>
                        .ranking-table {width: 100%; border-collapse: collapse; text-align: left; font-family: sans-serif; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1);}
                        .ranking-table th {background-color: #f0f2f6; padding: 12px; border-bottom: 2px solid #ddd; color: #31333F;}
                        .ranking-table td {padding: 10px; border-bottom: 1px solid #f0f2f6; vertical-align: middle; color: #31333F;}
                        .foto-aluno {width: 65px; height: 65px; object-fit: cover; border-radius: 50%; border: 2px solid #e0e0e0;}
                        .alerta-bar-bg {width: 100%; background-color: #ffe0e0; border-radius: 5px; height: 12px; margin-top: 5px;}
                        .alerta-bar-fg {height: 12px; border-radius: 5px; background-color: #ff4b4b;}
                    </style>
                    <table class="ranking-table">
                        <tr>
                            <th style="width: 80px;">📸 Foto</th>
                            <th>Nome do Estudante</th>
                            <th>Turma</th>
                            <th>🔥 Nível de Alerta</th>
                        </tr>
                    """
                    
                    for _, row in ranking.iterrows():
                        pct = (row['Faltas'] / 5) * 100 # Calcula porcentagem da barra (max 5)
                        pct = min(pct, 100) # Garante que não passe de 100%
                        
                        html_table += f"""
                        <tr>
                            <td><img src="{row['Foto']}" class="foto-aluno"></td>
                            <td style="font-weight: 600;">{row['Aluno']}</td>
                            <td>{row['turma']}</td>
                            <td>
                                <div style="font-size: 14px; font-weight: bold;">{row['Faltas']} faltas</div>
                                <div class="alerta-bar-bg"><div class="alerta-bar-fg" style="width: {pct}%;"></div></div>
                            </td>
                        </tr>
                        """
                    html_table += "</table>"
                    
                    # Renderiza o HTML no Streamlit
                    st.markdown(html_table, unsafe_allow_html=True)

            else:
                st.info("Ainda não há histórico de faltas acumulado.")
        except Exception as e:
            st.error(f"Erro ao gerar ranking visual: {e}")


    # ==========================================
    # ABA 2: MAPA DE COMPORTAMENTO DE EVASÕES
    # ==========================================
    with aba_mapa:
        st.subheader("🗺️ Mapa de Evasões por Turma")
        st.write("Analise o padrão de fuga: quais alunos gazeiam mais e de quais aulas eles fogem.")

        col_f1, col_f2 = st.columns([1, 2])

        with col_f1:
            hoje_data = datetime.now(fuso).date()
            data_inicio = st.date_input("Data Inicial", hoje_data - pd.Timedelta(days=7), format="DD/MM/YYYY")
            data_fim = st.date_input("Data Final", hoje_data, format="DD/MM/YYYY")

        with col_f2:
            try:
                res_turmas = supabase.table("evasoes").select("turma").execute()
                if res_turmas.data:
                    lista_turmas = sorted(list(set([t['turma'] for t in res_turmas.data if t.get('turma')])))
                    turma_selecionada = st.selectbox("Selecione a Turma para analisar:", ["Todas as Turmas"] + lista_turmas)
                else:
                    turma_selecionada = "Todas as Turmas"
                    st.info("Nenhuma evasão registrada ainda para listar turmas.")
            except Exception as e:
                turma_selecionada = "Todas as Turmas"
                st.error(f"Erro ao buscar turmas: {e}")

        st.caption(f"📍 Analisando o período de **{data_inicio.strftime('%d/%m/%Y')}** a **{data_fim.strftime('%d/%m/%Y')}** | Turma: **{turma_selecionada}**")

        # --- LÓGICA DO MAPA DE EVASÕES ---
        try:
            # 1. Busca os dados filtrados por data
            query = supabase.table("evasoes").select("aluno_nome, turma, aula_periodo, data_registro")\
                .gte("data_registro", data_inicio.strftime('%Y-%m-%d'))\
                .lte("data_registro", data_fim.strftime('%Y-%m-%d'))
            
            # 2. Filtra por turma se não for "Todas as Turmas"
            if turma_selecionada != "Todas as Turmas":
                query = query.eq("turma", turma_selecionada)
                
            res_evas_mapa = query.execute()

            if res_evas_mapa.data:
                df_mapa = pd.DataFrame(res_evas_mapa.data)
                
                # 3. Agrupa os dados para gerar o resumo
                resumo_evas = df_mapa.groupby(['turma', 'aluno_nome']).agg(
                    Total_Evasoes=('aula_periodo', 'count'),
                    Aulas_Evadidas=('aula_periodo', lambda x: ', '.join(x.unique()))
                ).reset_index()
                
                # 4. ORDENAÇÃO: 1º por Turma, 2º por Nome do Aluno (Alfabético)
                resumo_evas = resumo_evas.sort_values(by=['turma', 'aluno_nome'], ascending=[True, True])
                
                # 5. Renomeia as colunas para o visual ficar bonito
                resumo_evas.columns = ['Turma', 'Nome do Aluno', 'Total de Fugas', 'Aulas Gazeáveis (Histórico)']

                st.dataframe(
                    resumo_evas, 
                    use_container_width=True, 
                    hide_index=True
                )
            else:
                st.success("Tudo certo por aqui! Nenhuma evasão encontrada para os filtros selecionados. 🎉")
                
        except Exception as e:
            st.error(f"Erro ao gerar tabela de evasões: {e}")
