import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import unicodedata
from urllib.parse import quote
from fpdf import FPDF 
import traceback # Para capturar e mostrar o erro exato na tela

# ==========================================
# 1. FUNÇÕES DE APOIO
# ==========================================
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
        if arquivos:
            for arq in arquivos:
                nome_original = arq.get('name')
                if nome_original:
                    nome_sem_ext = nome_original.rsplit('.', 1)[0] if '.' in nome_original else nome_original
                    mapa[limpar_texto_absoluto(nome_sem_ext)] = nome_original
        return mapa
    except Exception:
        return {}

def gerar_pdf_relatorio(df, titulo_relatorio, data_hoje):
    try:
        colunas = list(df.columns)
        is_heatmap = 'Total de Fugas' in colunas
        
        orientacao = 'L' if is_heatmap else 'P'
        largura_pagina = 277 if is_heatmap else 190
        
        # Inicia o FPDF
        pdf = FPDF(orientation=orientacao, unit='mm', format='A4')
        pdf.set_auto_page_break(auto=True, margin=15)
        
        has_turma = "Turma" in colunas
        turmas = sorted(df['Turma'].unique().tolist()) if has_turma else [None]

        for turma in turmas:
            pdf.add_page()
            
            # Cabeçalho Geral
            pdf.set_font("Helvetica", "B", 16)
            pdf.cell(0, 10, "RELATORIO DE BUSCA ATIVA", ln=1, align="C")
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
            
            # ==========================================
            # LAYOUT 1: MAPA DE CALOR (COM TEXTO VERTICAL 90º)
            # ==========================================
            if is_heatmap:
                w_aluno = 65
                w_total = 12
                w_data = 8 # Largura fina
                
                pdf.set_fill_color(200, 200, 200)
                pdf.set_font("Helvetica", "B", 8)
                
                # Células iniciais do cabeçalho
                pdf.cell(w_aluno, 20, " Estudante", border=1, align="L", fill=True)
                pdf.cell(w_total, 20, " Total", border=1, align="C", fill=True)
                
                curr_x = pdf.get_x()
                curr_y = pdf.get_y()
                cols_dados = [c for c in colunas if c not in ['Turma', 'Aluno', 'Total de Fugas']]
                
                # Desenhando as datas na vertical
                for data_col in cols_dados:
                    if curr_x + w_data > 280: break 
                    
                    pdf.set_xy(curr_x, curr_y)
                    pdf.cell(w_data, 20, "", border=1, fill=True)
                    
                    with pdf.rotation(90, x=curr_x + (w_data/2) + 1.5, y=curr_y + 18):
                        pdf.text(curr_x + (w_data/2) + 1.5, curr_y + 18, str(data_col))
                    
                    curr_x += w_data
                
                # CORREÇÃO DEFINITIVA AQUI: Usando o valor direto da margem (10) em vez do comando get_margin()
                pdf.set_xy(10, curr_y + 20)
                
                # Linhas dos alunos
                for _, row in df_turma.iterrows():
                    pdf.set_font("Helvetica", "", 8)
                    pdf.set_fill_color(255, 255, 255)
                    nome = str(row.get('Aluno', ''))[:35].encode('latin-1', 'replace').decode('latin-1')
                    pdf.cell(w_aluno, 7, f" {nome}", border=1, align="L")
                    
                    pdf.set_font("Helvetica", "B", 8)
                    pdf.cell(w_total, 7, str(row.get('Total de Fugas', 0)), border=1, align="C")
                    
                    pdf.set_font("Helvetica", "B", 8)
                    for data_col in cols_dados:
                        if pdf.get_x() + w_data > 280: break
                        
                        val = row.get(data_col, 0)
                        try: val = int(val)
                        except: val = 0
                        
                        # Cores baseadas na gravidade
                        if val == 0: pdf.set_fill_color(255, 255, 255)
                        elif val == 1: pdf.set_fill_color(255, 245, 150)
                        elif val == 2: pdf.set_fill_color(255, 200, 100)
                        elif val >= 3: pdf.set_fill_color(255, 120, 120)
                        
                        fill = True if val > 0 else False
                        
                        txt_val = str(val) if val > 0 else ""
                        pdf.cell(w_data, 7, txt_val, border=1, align="C", fill=fill)
                    pdf.ln()

            # ==========================================
            # LAYOUT 2: TABELAS NORMAIS
            # ==========================================
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
                        nome = str(row.get('Aluno', '')).encode('latin-1', 'replace').decode('latin-1')
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

    st.title("🔎 Busca Ativa")
    
    fuso = pytz.timezone('America/Recife')
    hoje = datetime.now(fuso).strftime('%Y-%m-%d')
    data_hora_atual = datetime.now(fuso).strftime('%d/%m/%Y %H:%M')

    # --- MÉTRICAS ---
    st.subheader(f"📊 Resumo do Dia: {datetime.now(fuso).strftime('%d/%m/%Y')}")
    c1, c2, c3 = st.columns(3)

    try:
        res_f = supabase.table("frequencia").select("id", count="exact").eq("data_chamada", hoje).eq("status", "F").execute()
        res_e = supabase.table("evasoes").select("id", count="exact").eq("data_registro", hoje).execute()
        res_p = supabase.table("frequencia").select("id", count="exact").eq("data_chamada", hoje).eq("status", "P").execute()

        c1.metric("Faltas (Entrada)", res_f.count or 0)
        c2.metric("Evasões (Em aula)", res_e.count or 0)
        c3.metric("Presentes Agora", res_p.count or 0)
    except: st.error("Erro ao carregar métricas.")

    # --- ABAS ---
    aba_ranking, aba_zero, aba_lista, aba_registro = st.tabs([
        "🚨 Alertas & Ranking", "❌ Presença Zero", "🗺️ Mapa de Intensidade", "📝 Registrar Ação"
    ])

    with aba_ranking:
        st.subheader("🏆 Alunos com Mais Faltas")
        try:
            res_h = supabase.table("frequencia").select("aluno_nome, turma").eq("status", "F").execute()
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
                    
                    pdf_r = gerar_pdf_relatorio(rk, f"Ranking de Faltas", data_hora_atual)
                    
                    # Checagem Inteligente
                    if isinstance(pdf_r, bytes):
                        st.download_button("📄 Baixar PDF", pdf_r, "ranking.pdf", "application/pdf", use_container_width=True)
                    else:
                        st.error("⚠️ Ocorreu um erro interno ao gerar o PDF.")
                        st.code(pdf_r)
            else: st.info("Sem registros.")
        except Exception as e: st.error(f"Erro: {e}")

    with aba_zero:
        st.subheader("❌ Abandono (Presença Zero)")
        try:
            r_todos = supabase.table("alunos").select("nome, turma").execute()
            r_com_p = supabase.table("frequencia").select("aluno_nome").eq("status", "P").execute()
            if r_todos.data:
                df_todos = pd.DataFrame(r_todos.data)
                n_p = [x['aluno_nome'] for x in r_com_p.data] if r_com_p.data else []
                df_z = df_todos[~df_todos['nome'].isin(n_p)].copy()
                df_z.rename(columns={'nome': 'Aluno', 'turma': 'Turma'}, inplace=True)
                if not df_z.empty:
                    st.warning(f"Alunos em risco: {len(df_z)}")
                    st.dataframe(df_z.sort_values(by=['Turma', 'Aluno']), use_container_width=True, hide_index=True)
                    pdf_z = gerar_pdf_relatorio(df_z, "Abandono Escolar", data_hora_atual)
                    
                    if isinstance(pdf_z, bytes):
                        st.download_button("📄 Baixar Relatório", pdf_z, "abandono.pdf", "application/pdf", use_container_width=True)
                    else:
                        st.error("⚠️ Ocorreu um erro interno ao gerar o PDF.")
                        st.code(pdf_z)
                else: st.success("Nenhum abandono detectado.")
        except Exception as e: st.error(f"Erro: {e}")

    with aba_lista:
        st.subheader("🗺️ Mapa de Intensidade de Evasões")
        col_i, col_f = st.columns(2)
        d_i = col_i.date_input("Início", datetime.now(fuso).date() - pd.Timedelta(days=7))
        d_f = col_f.date_input("Fim", datetime.now(fuso).date())
        
        try:
            res_e_mapa = supabase.table("evasoes").select("aluno_nome, turma, aula_periodo, data_registro")\
                .gte("data_registro", d_i.strftime('%Y-%m-%d'))\
                .lte("data_registro", d_f.strftime('%Y-%m-%d')).execute()

            if res_e_mapa.data:
                df_m = pd.DataFrame(res_e_mapa.data)
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
                
                pdf_e = gerar_pdf_relatorio(m_ev, "Mapa de Evasoes", data_hora_atual)
                
                # Exibe o botão se OK, ou exibe o código do erro na tela se falhar!
                if isinstance(pdf_e, bytes):
                    st.download_button("📄 Baixar Mapa (PDF)", pdf_e, "mapa_evasoes.pdf", use_container_width=True, type="primary")
                else:
                    st.error("⚠️ Não foi possível gerar o PDF. Tire um print do erro abaixo:")
                    st.code(pdf_e)
                    
            else: st.success("Sem evasões no período.")
        except Exception as e: st.error(f"Erro: {e}")

    with aba_registro:
        st.subheader("➕ Registrar Ação / Ocorrência")
        try:
            r_al = supabase.table("alunos").select("id, nome, turma").order("nome").execute()
            if r_al.data:
                df_al = pd.DataFrame(r_al.data)
                t_escolhida = st.selectbox("Selecione a Turma:", sorted(df_al['turma'].unique()))
                al_da_t = df_al[df_al['turma'] == t_escolhida]
                al_dict = dict(zip(al_da_t['nome'], al_da_t['id']))
                n_escolhido = st.selectbox("Selecione o Estudante:", list(al_dict.keys()))

                with st.form("form_oc"):
                    t_ac = st.selectbox("Ação:", ["Ligação para Família", "Advertência", "Suspensão", "Visita Domiciliar", "Conselho Tutelar"])
                    mot = st.text_area("Motivo:")
                    mat = st.text_input("Sua Matrícula:")
                    if st.form_submit_button("🚨 Gravar", type="primary"):
                        if mot and mat:
                            supabase.table("ocorrencias_disciplinares").insert({
                                "aluno_id": al_dict[n_escolhido], "aluno_nome": n_escolhido,
                                "turma": t_escolhida, "tipo_ocorrencia": t_ac,
                                "motivo": mot, "quem_registrou": mat, "status": "Ativa"
                            }).execute()
                            st.success("Gravado!")
                            st.balloons()
                        else: st.warning("Preencha tudo.")
        except Exception as e: st.error(f"Erro: {e}")

if __name__ == "__main__":
    pass