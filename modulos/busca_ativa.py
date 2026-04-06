import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import unicodedata
from urllib.parse import quote
from fpdf import FPDF 
import traceback

# ==========================================
# 1. FUNÇÕES DE APOIO
# ==========================================
def limpar_texto(texto):
    """Padronização idêntica ao Fotograma para bater com as fotos do GitHub"""
    if not texto: return ""
    if "." in str(texto): texto = str(texto).rsplit('.', 1)[0]
    nfkd = unicodedata.normalize('NFKD', str(texto))
    texto_limpo = "".join([c for c in nfkd if not unicodedata.combining(c)]).lower()
    return "".join(filter(str.isalnum, texto_limpo))

@st.cache_data(ttl=3600)
def carregar_fotos_github_busca_ativa():
    try:
        import github
        from github import Github, Auth
        
        if "GITHUB_TOKEN" not in st.secrets:
            return {}
            
        auth = Auth.Token(st.secrets["GITHUB_TOKEN"])
        g = Github(auth=auth)
        repo = g.get_repo("erempamacesso/presence")
        contents = repo.get_contents("alunos_fotos")
        
        return {limpar_texto(arq.name): arq.download_url for arq in contents}
    except Exception:
        return {}

def gerar_pdf_relatorio(df, titulo_relatorio, data_hoje):
    try:
        colunas = list(df.columns)
        is_heatmap = 'Total de Fugas' in colunas
        
        orientacao = 'P' 
        largura_pagina = 190
        
        pdf = FPDF(orientation=orientacao, unit='mm', format='A4')
        pdf.set_auto_page_break(auto=True, margin=15)
        
        has_turma = "Turma" in colunas
        turmas = sorted(df['Turma'].unique().tolist()) if has_turma else [None]

        for turma in turmas:
            pdf.add_page()
            
            pdf.set_font("Helvetica", "B", 16)
            pdf.cell(0, 10, "RELATORIO DE FUGA DE AULA", ln=1, align="C")
            pdf.set_font("Helvetica", "", 10)
            pdf.cell(0, 5, f"Gerado em: {data_hoje}", ln=1, align="C")
            pdf.ln(5)
            
            pdf.set_font("Helvetica", "B", 12)
            titulo_safe = str(titulo_relatorio).encode('latin-1', 'replace').decode('latin-1')
            if turma:
                titulo_tela = titulo_safe if "Turma" in titulo_safe else f"{titulo_safe} - Turma: {turma}"
            else:
                titulo_tela = titulo_safe
                
            pdf.cell(0, 10, titulo_tela.upper(), ln=1, align="L")
            pdf.ln(5)
            
            df_turma = df[df['Turma'] == turma] if has_turma else df
            
            if is_heatmap:
                w_aluno = 60
                w_total = 10
                w_data = 5.2 
                
                pdf.set_fill_color(200, 200, 200)
                pdf.set_font("Helvetica", "B", 8)
                
                pdf.cell(w_aluno, 20, " Estudante", border=1, align="L", fill=True)
                pdf.cell(w_total, 20, " Total", border=1, align="C", fill=True)
                
                curr_x = pdf.get_x()
                curr_y = pdf.get_y()
                cols_dados = [c for c in colunas if c not in ['Turma', 'Aluno', 'Total de Fugas']]
                
                for data_col in cols_dados:
                    if curr_x + w_data > 195: break 
                    
                    pdf.set_xy(curr_x, curr_y)
                    pdf.cell(w_data, 20, "", border=1, fill=True)
                    
                    with pdf.rotation(90, x=curr_x + (w_data/2) + 1.5, y=curr_y + 18):
                        pdf.text(curr_x + (w_data/2) + 1.5, curr_y + 18, str(data_col))
                    
                    curr_x += w_data
                
                pdf.set_xy(10, curr_y + 20)
                
                for _, row in df_turma.iterrows():
                    pdf.set_font("Helvetica", "", 7)
                    pdf.set_fill_color(255, 255, 255)
                    nome = str(row.get('Aluno', ''))[:32].encode('latin-1', 'replace').decode('latin-1')
                    pdf.cell(w_aluno, 6, f" {nome}", border=1, align="L")
                    
                    pdf.set_font("Helvetica", "B", 8)
                    pdf.cell(w_total, 6, str(row.get('Total de Fugas', 0)), border=1, align="C")
                    
                    pdf.set_font("Helvetica", "B", 8)
                    for data_col in cols_dados:
                        if pdf.get_x() + w_data > 195: break
                        
                        val = row.get(data_col, 0)
                        try: val = int(val)
                        except: val = 0
                        
                        if val == 0: pdf.set_fill_color(255, 255, 255)
                        elif val == 1: pdf.set_fill_color(255, 245, 150)
                        elif val == 2: pdf.set_fill_color(255, 200, 100)
                        elif val >= 3: pdf.set_fill_color(255, 120, 120)
                        
                        fill = True if val > 0 else False
                        txt_val = str(val) if val > 0 else ""
                        pdf.cell(w_data, 6, txt_val, border=1, align="C", fill=fill)
                    pdf.ln()
            else:
                pdf.set_fill_color(230, 230, 230)
                pdf.set_font("Helvetica", "B", 9)
                
                if "Aluno" in colunas and has_turma:
                    cols_to_print = [c for c in df_turma.columns if c != 'Turma']
                    w_aluno = 70
                    w_remaining = largura_pagina - w_aluno
                    num_cols = len(cols_to_print) - 1
                    w_col = w_remaining / num_cols if num_cols > 0 else 0
                    
                    pdf.cell(w_aluno, 8, " Estudante", border=1, align="L", fill=True)
                    for col in cols_to_print:
                        if col == "Aluno": continue
                        pdf.cell(w_col, 8, f"{str(col)[:10]}", border=1, align="C", fill=True)
                    pdf.ln()
                    
                    pdf.set_font("Helvetica", "", 8)
                    for _, row in df_turma.iterrows():
                        nome = str(row.get('Aluno', ''))[:35].encode('latin-1', 'replace').decode('latin-1')
                        pdf.cell(w_aluno, 8, f" {nome[:35]}", border=1, align="L")
                        for col in cols_to_print:
                            if col == "Aluno": continue
                            val = str(row.get(col, '')).encode('latin-1', 'replace').decode('latin-1')
                            pdf.cell(w_col, 8, f"{val[:15]}", border=1, align="C")
                        pdf.ln()
                else:
                    cols_print = colunas[:4]
                    w_col = largura_pagina / len(cols_print) if cols_print else largura_pagina
                    for col in cols_print:
                        pdf.cell(w_col, 8, str(col)[:15], border=1, align="C", fill=True)
                    pdf.ln()
                    pdf.set_font("Helvetica", "", 8)
                    for _, row in df_turma.iterrows():
                        for col in cols_print:
                            val = str(row[col]).encode('latin-1', 'replace').decode('latin-1')
                            pdf.cell(w_col, 8, f" {val[:20]}", border=1, align="L")
                        pdf.ln()
        
        return bytes(pdf.output())
    except Exception as e:
        return f"ERRO INTERNO DO PDF:\n{traceback.format_exc()}"

# ==========================================
# 2. TELA PRINCIPAL
# ==========================================
def exibir_busca_ativa(supabase):
    st.markdown("""
        <style>
        div[data-testid="stTabNav"] { gap: 5px; border-bottom: 2px solid #e0e0e0; }
        button[data-testid="stTab"] {
            border: 1px solid #d3d3d3; border-bottom: none; border-radius: 12px 12px 0 0; 
            padding: 10px 20px; background-color: #f8f9fa; transition: 0.3s;
        }
        button[data-testid="stTab"][aria-selected="true"] {
            background-color: white; border-top: 4px solid #FF4B4B; color: #FF4B4B; font-weight: bold;
        }
        </style>
    """, unsafe_allow_html=True)

    st.title("🔎 Busca Ativa e Monitorização")

    # Calculamos as datas primeiro para usar na verificação de presenças
    fuso = pytz.timezone('America/Recife')
    hoje_date = datetime.now(fuso).date()
    hoje_str = hoje_date.strftime('%Y-%m-%d')
    data_hora_atual = datetime.now(fuso).strftime('%d/%m/%Y %H:%M')

    if st.button("🔄 Atualizar Fotos do GitHub", key="btn_limpa_cache_ba"):
        st.cache_data.clear()
        st.rerun()

    # Prepara a função de cache do GitHub
    mapa_fotos_github = carregar_fotos_github_busca_ativa()

    # ==========================================
    # VERIFICAÇÃO DE ALUNOS PRESENTES SEM FOTO
    # ==========================================
    try:
        # Puxa APENAS quem teve a chamada feita HOJE e está com status P (Presente)
        res_presencas = supabase.table("frequencia").select("aluno_nome, turma").eq("data_chamada", hoje_str).eq("status", "P").execute()
        df_presentes = pd.DataFrame(res_presencas.data)
    except Exception as e:
        df_presentes = pd.DataFrame()
        st.error(f"Erro ao carregar lista de presentes de hoje: {e}")

    if not df_presentes.empty:
        # Filtra os presentes verificando se o nome não está no mapa de fotos
        df_sem_foto = df_presentes[~df_presentes['aluno_nome'].apply(lambda x: limpar_texto(x) in mapa_fotos_github)]
        qtd_sem_foto = len(df_sem_foto)
        
        if qtd_sem_foto > 0:
            st.warning(f"📸 **Aviso Visual:** Existem **{qtd_sem_foto}** estudantes PRESENTES HOJE na escola que estão sem foto no sistema.")
            
            with st.expander("🛠️ Ver lista de estudantes presentes sem foto (Clique para abrir)"):
                st.write("Estes alunos estão na escola hoje, aproveite para atualizar as fotos!")
                
                # Formatando a tabela para ficar mais bonita
                df_exibicao = df_sem_foto.rename(columns={'aluno_nome': 'Estudante', 'turma': 'Turma'})
                st.dataframe(df_exibicao.sort_values(by=['Turma', 'Estudante']), use_container_width=True, hide_index=True)
        else:
            st.success("📸 **Excelente!** Todos os estudantes presentes hoje já possuem foto no sistema.")
    else:
        st.info("📸 **Aguardando Chamada:** A chamada de hoje ainda não foi registada ou não há alunos presentes.")

    st.divider()

    # 👇 Filtro Global de Período
    st.subheader("📅 Filtro de Período Geral")
    col_di, col_df = st.columns(2)
    # Por padrão, do primeiro dia do mês atual até hoje
    primeiro_dia_mes = hoje_date.replace(day=1)
    d_i = col_di.date_input("Data Inicial", primeiro_dia_mes)
    d_f = col_df.date_input("Data Final", hoje_date)
    
    d_i_str = d_i.strftime('%Y-%m-%d')
    d_f_str = d_f.strftime('%Y-%m-%d')

    # --- MÉTRICAS ---
    st.subheader(f"📊 Resumo do Período: {d_i.strftime('%d/%m/%Y')} a {d_f.strftime('%d/%m/%Y')}")
    c1, c2, c3 = st.columns(3)

    try:
        # As métricas agora respeitam as datas escolhidas
        res_f = supabase.table("frequencia").select("id", count="exact").gte("data_chamada", d_i_str).lte("data_chamada", d_f_str).eq("status", "F").execute()
        res_e = supabase.table("evasoes").select("id", count="exact").gte("data_registro", d_i_str).lte("data_registro", d_f_str).execute()
        res_p = supabase.table("frequencia").select("id", count="exact").gte("data_chamada", d_i_str).lte("data_chamada", d_f_str).eq("status", "P").execute()

        c1.metric("Faltas (Entrada)", res_f.count or 0)
        c2.metric("Evasões (Em aula)", res_e.count or 0)
        c3.metric("Presenças no Período", res_p.count or 0)
    except: st.error("Erro ao carregar métricas.")

    # --- ABAS ---
    aba_ranking, aba_zero, aba_lista, aba_registro = st.tabs([
        "🚨 Alertas & Ranking", "❌ Presença Zero", "🗺️ Mapa de Intensidade", "📝 Registar Ação"
    ])

    with aba_ranking:
        st.subheader("🏆 Alunos com Mais Faltas no Período")
        try:
            # Filtro aplicado na consulta
            res_h = supabase.table("frequencia").select("aluno_nome, turma").gte("data_chamada", d_i_str).lte("data_chamada", d_f_str).eq("status", "F").execute()
            if res_h.data:
                df_h = pd.DataFrame(res_h.data)
                col_t, col_s = st.columns([1, 2])
                with col_t:
                    t_sel = st.selectbox("📍 Turma:", ["Todas"] + sorted(df_h['turma'].unique().tolist()), key="rk_t")
                with col_s:
                    m_f = st.slider("Mínimo de faltas:", 1, 20, 3)

                if t_sel != "Todas": df_h = df_h[df_h['turma'] == t_sel]
                rk = df_h['aluno_nome'].value_counts().reset_index()
                rk.columns = ['Aluno', 'Faltas']
                rk = rk[rk['Faltas'] >= m_f].sort_values(by='Faltas', ascending=False)

                if not rk.empty:
                    df_ts = df_h.drop_duplicates('aluno_nome')[['aluno_nome', 'turma']]
                    rk = rk.merge(df_ts, left_on='Aluno', right_on='aluno_nome').drop('aluno_nome', axis=1)
                    rk.rename(columns={'turma': 'Turma'}, inplace=True)
                    st.dataframe(rk.sort_values(by=['Turma', 'Faltas'], ascending=[True, False]), use_container_width=True, hide_index=True)
                    
                    pdf_r = gerar_pdf_relatorio(rk, f"Ranking de Faltas ({d_i.strftime('%d/%m')} a {d_f.strftime('%d/%m')})", data_hora_atual)
                    
                    if isinstance(pdf_r, bytes):
                        st.download_button("📄 Baixar PDF", pdf_r, "ranking.pdf", "application/pdf", use_container_width=True)
                    else:
                        st.error("⚠️ Ocorreu um erro interno ao gerar o PDF.")
                        st.code(pdf_r)
            else: st.info("Sem registos no período selecionado.")
        except Exception as e: st.error(f"Erro: {e}")

    with aba_zero:
        st.subheader("❌ Abandono (Presença Zero no Período)")
        try:
            r_todos = supabase.table("alunos").select("nome, turma").execute()
            # Puxa apenas as presenças ocorridas no período
            r_com_p = supabase.table("frequencia").select("aluno_nome").gte("data_chamada", d_i_str).lte("data_chamada", d_f_str).eq("status", "P").execute()
            
            if r_todos.data:
                df_todos = pd.DataFrame(r_todos.data)
                n_p = [x['aluno_nome'] for x in r_com_p.data] if r_com_p.data else []
                # Filtra os alunos que NÃO apareceram na lista de presentes do período
                df_z = df_todos[~df_todos['nome'].isin(n_p)].copy()
                df_z.rename(columns={'nome': 'Aluno', 'turma': 'Turma'}, inplace=True)
                if not df_z.empty:
                    st.warning(f"Alunos em risco no período: {len(df_z)}")
                    st.dataframe(df_z.sort_values(by=['Turma', 'Aluno']), use_container_width=True, hide_index=True)
                    pdf_z = gerar_pdf_relatorio(df_z, f"Abandono Escolar ({d_i.strftime('%d/%m')} a {d_f.strftime('%d/%m')})", data_hora_atual)
                    
                    if isinstance(pdf_z, bytes):
                        st.download_button("📄 Baixar Relatório", pdf_z, "abandono.pdf", "application/pdf", use_container_width=True)
                    else:
                        st.error("⚠️ Ocorreu um erro interno ao gerar o PDF.")
                        st.code(pdf_z)
                else: st.success("Nenhum abandono detetado neste período.")
        except Exception as e: st.error(f"Erro: {e}")

    with aba_lista:
        st.subheader("🗺️ Mapa de Intensidade de Evasões")
        
        try:
            r_turmas = supabase.table("alunos").select("turma").execute()
            lista_turmas = ["Geral (Todas as Turmas)"]
            if r_turmas.data:
                lista_turmas += sorted(list(set([x['turma'] for x in r_turmas.data if x['turma']])))
                
            t_escolhida = st.selectbox("Selecione a Turma:", lista_turmas)

            # Usa as datas globais escolhidas lá no topo
            res_e_mapa = supabase.table("evasoes").select("aluno_nome, turma, aula_periodo, data_registro")\
                .gte("data_registro", d_i_str)\
                .lte("data_registro", d_f_str).execute()

            if res_e_mapa.data:
                df_m = pd.DataFrame(res_e_mapa.data)
                
                if t_escolhida != "Geral (Todas as Turmas)":
                    df_m = df_m[df_m['turma'] == t_escolhida]
                
                if not df_m.empty:
                    df_m['data_dt'] = pd.to_datetime(df_m['data_registro'])
                    
                    m_ev = df_m.pivot_table(index=['turma', 'aluno_nome'], columns='data_dt', values='aula_periodo', aggfunc='count').fillna(0).astype(int)
                    m_ev['Total de Fugas'] = m_ev.select_dtypes(include=['number']).sum(axis=1)
                    
                    m_ev = m_ev.reset_index()
                    m_ev.rename(columns={'turma': 'Turma', 'aluno_nome': 'Aluno'}, inplace=True)
                    
                    cols_datas = []
                    novas_cols = []
                    for c in m_ev.columns:
                        if isinstance(c, pd.Timestamp):
                            sd = c.strftime('%d/%m')
                            novas_cols.append(sd)
                            cols_datas.append(sd)
                        else: novas_cols.append(c)
                    m_ev.columns = novas_cols
                    
                    ordem = ['Turma', 'Aluno', 'Total de Fugas'] + cols_datas
                    m_ev = m_ev[ordem].sort_values(by=['Turma', 'Total de Fugas'], ascending=[True, False])

                    st.markdown("**Legenda de Gravidade:** 🟢 `0 Fugas` | 🟡 `1 Fuga` | 🟠 `2 Fugas` | 🔴 `3+ Fugas`")
                    
                    df_exibicao = m_ev.style.format(lambda v: "" if v == 0 else v, subset=cols_datas)\
                                            .background_gradient(subset=cols_datas, cmap='YlOrRd')
                    
                    st.dataframe(df_exibicao, use_container_width=True, hide_index=True)
                    
                    titulo_pdf = "Relatorio de Fuga de Aula"
                    if t_escolhida != "Geral (Todas as Turmas)":
                        titulo_pdf += f" - Turma {t_escolhida}"
                        
                    pdf_e = gerar_pdf_relatorio(m_ev, titulo_pdf, data_hora_atual)
                    
                    if isinstance(pdf_e, bytes):
                        st.download_button("📄 Baixar Mapa (PDF)", pdf_e, f"mapa_evasoes_{hoje_str}.pdf", use_container_width=True, type="primary")
                    else:
                        st.error("⚠️ Não foi possível gerar o PDF. Tire um print do erro abaixo:")
                        st.code(pdf_e)
                else:
                    st.info(f"Nenhuma evasão encontrada para a turma {t_escolhida} neste período.")
            else: 
                st.success("Sem evasões no período geral.")
        except Exception as e: st.error(f"Erro: {e}")

    with aba_registro:
        st.subheader("➕ Registar Ação / Ocorrência")
        try:
            r_al = supabase.table("alunos").select("id, nome, turma").order("nome").execute()
            if r_al.data:
                df_al = pd.DataFrame(r_al.data)
                
                # Chaves únicas para os selectboxes desta aba não entrarem em conflito com os da outra
                t_escolhida_reg = st.selectbox("Selecione a Turma:", sorted(df_al['turma'].dropna().unique()), key="reg_turma")
                al_da_t = df_al[df_al['turma'] == t_escolhida_reg]
                al_dict = dict(zip(al_da_t['nome'], al_da_t['id']))
                n_escolhido = st.selectbox("Selecione o Estudante:", list(al_dict.keys()), key="reg_aluno")

                with st.form("form_oc"):
                    t_ac = st.selectbox("Ação:", ["Ligação para Família", "Advertência", "Suspensão", "Visita Domiciliar", "Conselho Tutelar"])
                    mot = st.text_area("Motivo:")
                    mat = st.text_input("Sua Matrícula:")
                    if st.form_submit_button("🚨 Gravar", type="primary"):
                        if mot and mat:
                            supabase.table("ocorrencias_disciplinares").insert({
                                "aluno_id": al_dict[n_escolhido], "aluno_nome": n_escolhido,
                                "turma": t_escolhida_reg, "tipo_ocorrencia": t_ac,
                                "motivo": mot, "quem_registrou": mat, "status": "Ativa",
                                "data_registro": hoje_str # Garante que o registro usa o dia de hoje
                            }).execute()
                            st.success("Gravado com Sucesso!")
                            st.balloons()
                        else: st.warning("Preencha todos os campos obrigatórios.")
        except Exception as e: st.error(f"Erro: {e}")

if __name__ == "__main__":
    pass