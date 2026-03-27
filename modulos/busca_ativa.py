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
def limpar_texto_absoluto(texto):
    if not texto: return ""
    texto = str(texto).strip().lower()
    if "." in texto: texto = texto.rsplit(".", 1)[0]
    nfkd = unicodedata.normalize('NFKD', texto)
    sem_acento = "".join([c for c in nfkd if not unicodedata.combining(c)])
    return "".join(filter(str.isalnum, sem_acento))

def gerar_pdf_relatorio(df, titulo_relatorio, data_hoje):
    try:
        colunas = list(df.columns)
        is_heatmap = 'Total de Fugas' in colunas
        
        orientacao = 'L' if is_heatmap else 'P'
        largura_pagina = 277 if is_heatmap else 190
        
        pdf = FPDF(orientation=orientacao, unit='mm', format='A4')
        pdf.set_auto_page_break(auto=True, margin=15)
        
        has_turma = "Turma" in colunas
        turmas = sorted(df['Turma'].unique().tolist()) if has_turma else [None]

        for turma in turmas:
            pdf.add_page()
            
            # Cabeçalho
            pdf.set_font("Helvetica", "B", 16)
            pdf.cell(0, 10, "RELATORIO DE BUSCA ATIVA", ln=1, align="C")
            pdf.set_font("Helvetica", "", 10)
            pdf.cell(0, 5, f"Gerado em: {data_hoje}", ln=1, align="C")
            pdf.ln(5)
            
            pdf.set_font("Helvetica", "B", 12)
            titulo_safe = str(titulo_relatorio).encode('latin-1', 'replace').decode('latin-1')
            if turma:
                titulo_tela = f"{titulo_safe} - Turma: {turma}"
            else:
                titulo_tela = titulo_safe
                
            pdf.cell(0, 10, titulo_tela.upper(), ln=1, align="L")
            pdf.ln(5)
            
            df_turma = df[df['Turma'] == turma] if has_turma else df
            
            if is_heatmap:
                w_aluno = 65
                w_total = 12
                w_data = 8
                
                pdf.set_fill_color(200, 200, 200)
                pdf.set_font("Helvetica", "B", 8)
                
                pdf.cell(w_aluno, 20, " Estudante", border=1, align="L", fill=True)
                pdf.cell(w_total, 20, " Total", border=1, align="C", fill=True)
                
                curr_x = pdf.get_x()
                curr_y = pdf.get_y()
                cols_dados = [c for c in colunas if c not in ['Turma', 'Aluno', 'Total de Fugas']]
                
                for data_col in cols_dados:
                    if curr_x + w_data > 280: break 
                    pdf.set_xy(curr_x, curr_y)
                    pdf.cell(w_data, 20, "", border=1, fill=True)
                    
                    # Rotação corrigida
                    with pdf.rotation(90, x=curr_x + (w_data/2) + 1.5, y=curr_y + 18):
                        pdf.text(curr_x + (w_data/2) + 1.5, curr_y + 18, str(data_col))
                    curr_x += w_data
                
                # CORREÇÃO AQUI: Usando pdf.l_margin em vez de get_margin()
                pdf.set_xy(pdf.l_margin, curr_y + 20)
                
                for _, row in df_turma.iterrows():
                    pdf.set_font("Helvetica", "", 8)
                    pdf.set_fill_color(255, 255, 255)
                    nome = str(row.get('Aluno', ''))[:35].encode('latin-1', 'replace').decode('latin-1')
                    pdf.cell(w_aluno, 7, f" {nome}", border=1, align="L")
                    
                    pdf.set_font("Helvetica", "B", 8)
                    pdf.cell(w_total, 7, str(row.get('Total de Fugas', 0)), border=1, align="C")
                    
                    for data_col in cols_dados:
                        if pdf.get_x() + w_data > 280: break
                        val = row.get(data_col, 0)
                        try: val = int(val)
                        except: val = 0
                        
                        if val == 0: pdf.set_fill_color(255, 255, 255)
                        elif val == 1: pdf.set_fill_color(255, 245, 150)
                        elif val == 2: pdf.set_fill_color(255, 200, 100)
                        else: pdf.set_fill_color(255, 120, 120)
                        
                        fill = True if val > 0 else False
                        txt_val = str(val) if val > 0 else ""
                        pdf.cell(w_data, 7, txt_val, border=1, align="C", fill=fill)
                    pdf.ln()
            else:
                # Layout de tabela normal (Ranking / Abandono)
                pdf.set_fill_color(230, 230, 230)
                pdf.set_font("Helvetica", "B", 9)
                cols_to_print = [c for c in df_turma.columns if c != 'Turma']
                w_aluno = 80
                w_col = (largura_pagina - w_aluno) / (len(cols_to_print)-1) if len(cols_to_print) > 1 else 30
                
                for col in cols_to_print:
                    w = w_aluno if col == "Aluno" else w_col
                    pdf.cell(w, 8, str(col), border=1, align="C", fill=True)
                pdf.ln()
                
                pdf.set_font("Helvetica", "", 9)
                for _, row in df_turma.iterrows():
                    for col in cols_to_print:
                        w = w_aluno if col == "Aluno" else w_col
                        txt = str(row[col]).encode('latin-1', 'replace').decode('latin-1')
                        pdf.cell(w, 8, txt[:40], border=1, align="L" if col=="Aluno" else "C")
                    pdf.ln()
        
        return bytes(pdf.output())
    except Exception as e:
        return f"ERRO NO PDF:\n{traceback.format_exc()}"

# ==========================================
# 2. TELA PRINCIPAL (STREAMLIT)
# ==========================================
def exibir_busca_ativa(supabase):
    st.title("🔎 Busca Ativa")
    
    fuso = pytz.timezone('America/Recife')
    hoje = datetime.now(fuso).strftime('%Y-%m-%d')
    data_hora_atual = datetime.now(fuso).strftime('%d/%m/%Y %H:%M')

    # Abas
    aba_ranking, aba_zero, aba_lista, aba_registro = st.tabs([
        "🚨 Ranking", "❌ Abandono", "🗺️ Mapa Evasão", "📝 Registrar"
    ])

    # --- ABA RANKING ---
    with aba_ranking:
        try:
            res = supabase.table("frequencia").select("aluno_nome, turma").eq("status", "F").execute()
            if res.data:
                df = pd.DataFrame(res.data)
                rk = df['aluno_nome'].value_counts().reset_index()
                rk.columns = ['Aluno', 'Faltas']
                # Adiciona turma de volta
                df_aux = df.drop_duplicates('aluno_nome')[['aluno_nome', 'turma']]
                rk = rk.merge(df_aux, left_on='Aluno', right_on='aluno_nome').drop('aluno_nome', axis=1)
                rk.rename(columns={'turma': 'Turma'}, inplace=True)
                
                st.dataframe(rk, use_container_width=True, hide_index=True)
                
                pdf_bytes = gerar_pdf_relatorio(rk, "Ranking de Faltas", data_hora_atual)
                if isinstance(pdf_bytes, bytes):
                    st.download_button("📄 Baixar PDF Ranking", pdf_bytes, "ranking.pdf", "application/pdf")
                else:
                    st.error(pdf_bytes)
        except Exception as e: st.error(f"Erro: {e}")

    # --- ABA MAPA (Onde estava o erro) ---
    with aba_lista:
        st.subheader("Mapa de Intensidade")
        try:
            res_e = supabase.table("evasoes").select("aluno_nome, turma, data_registro").execute()
            if res_e.data:
                df_m = pd.DataFrame(res_e.data)
                df_m['data_dt'] = pd.to_datetime(df_m['data_registro']).dt.strftime('%d/%m')
                m_ev = df_m.pivot_table(index=['turma', 'aluno_nome'], columns='data_dt', aggfunc='size', fill_value=0)
                m_ev['Total de Fugas'] = m_ev.sum(axis=1)
                m_ev = m_ev.reset_index().rename(columns={'turma': 'Turma', 'aluno_nome': 'Aluno'})
                
                st.dataframe(m_ev, use_container_width=True)
                
                pdf_bytes = gerar_pdf_relatorio(m_ev, "Mapa de Evasões", data_hora_atual)
                if isinstance(pdf_bytes, bytes):
                    st.download_button("📄 Baixar PDF Mapa", pdf_bytes, "mapa_evasoes.pdf", "application/pdf")
                else:
                    st.error(pdf_bytes)
        except Exception as e: st.error(f"Erro: {e}")

if __name__ == "__main__":
    pass