import streamlit as st
import pandas as pd
import unicodedata
from urllib.parse import quote
import time
from fpdf import FPDF
from datetime import datetime

# ==========================================
# FUNÇÕES AUXILIARES
# ==========================================

def calcular_idade(data_nascimento):
    if not data_nascimento: return ""
    try:
        # Tenta converter garantindo o formato dia/mes/ano se for string
        if isinstance(data_nascimento, str):
            dt_nasc = pd.to_datetime(data_nascimento, dayfirst=True, errors='coerce')
        else:
            dt_nasc = pd.to_datetime(data_nascimento)
            
        if pd.isnat(dt_nasc): return "" # Se a conversão falhar, retorna vazio

        hoje = datetime.now()
        idade = hoje.year - dt_nasc.year - ((hoje.month, hoje.day) < (dt_nasc.month, dt_nasc.day))
        return f"{idade} anos"
    except:
        return ""

# No loop de exibição (exibir_fotograma), altere a parte da data para esta:

                                # --- AREA DA DATA E IDADE ---
                                # IMPORTANTE: Verifique se no Supabase o nome é 'Data de nascimento' ou 'data_nascimento'
                                # Vou usar .get() para não dar erro se o nome estiver levemente diferente
                                raw_date = aluno.get('data_nascimento') or aluno.get('Data de nascimento')
                                
                                if raw_date:
                                    try:
                                        dt_obj = pd.to_datetime(raw_date, dayfirst=True)
                                        dt_formatada = dt_obj.strftime('%d/%m/%Y')
                                        idade = calcular_idade(dt_obj)
                                        legenda = f"{dt_formatada} • {idade}"
                                    except:
                                        legenda = "--/--/----"
                                else:
                                    legenda = "Sem data"

                                st.markdown(f"<p style='text-align:center; font-size:9px; color:gray; margin-top:0px;'>{legenda}</p>", unsafe_allow_html=True)


# ==========================================
# GERADOR DE PDF ATUALIZADO
# ==========================================
def gerar_pdf_mapa_sala_com_fotos(alunos, turma, mapa_fotos, supabase_url):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    
    pdf.set_font("Arial", style='B', size=16)
    pdf.cell(0, 10, txt=f"Mapa de Sala - Turma {turma}", ln=True, align='C')
    pdf.ln(5)

    largura_col = 45 
    altura_linha = 45 # Aumentei levemente (5mm) para caber as 3 linhas de texto sem apertar
    
    start_x = pdf.get_x()
    start_y = pdf.get_y()
    
    x = start_x
    y = start_y
    
    for i, aluno in enumerate(alunos):
        # Tratamento de Nome
        nome_completo = str(aluno['nome']).encode('latin-1', 'ignore').decode('latin-1')
        partes_nome = nome_completo.split()
        nome_curto = " ".join(partes_nome[:2]) if len(partes_nome) > 1 else partes_nome[0]
        
        # Dados Extras
        data_nasc = aluno.get('data_nascimento', '')
        # Formata data para DD/MM/AAAA se existir
        data_formatada = pd.to_datetime(data_nasc).strftime('%d/%m/%Y') if data_nasc else ""
        idade_str = calcular_idade(data_nasc)
        info_extra = f"{data_formatada} - {idade_str}"

        pdf.set_xy(x, y)
        pdf.cell(largura_col, altura_linha, txt="", border=1)
        
        chave = limpar_texto(aluno['nome'])
        foto_arq = mapa_fotos.get(chave)
        
        # Imagem
        if foto_arq:
            url_img = f"{supabase_url}/storage/v1/object/public/fotos-alunos/{quote(foto_arq)}"
            img_size = 22
            img_x = x + (largura_col - img_size) / 2
            img_y = y + 3
            try:
                pdf.image(url_img, x=img_x, y=img_y, w=img_size, h=img_size)
            except:
                pass
        
        # Texto: Nome
        pdf.set_font("Arial", style='B', size=8)
        pdf.set_xy(x, y + 27)
        pdf.cell(largura_col, 5, txt=nome_curto, border=0, align='C')
        
        # Texto: Data e Idade (Fonte menor)
        pdf.set_font("Arial", size=7)
        pdf.set_xy(x, y + 32)
        pdf.cell(largura_col, 5, txt=info_extra, border=0, align='C')
        
        # Lógica de Grade
        if (i + 1) % 6 == 0:
            x = start_x
            y += altura_linha
            if y > 160: 
                pdf.add_page()
                x = start_x
                y = pdf.get_y()
        else:
            x += largura_col
            
    return bytes(pdf.output(dest='S'))

# ==========================================
# TELA PRINCIPAL (FOTOGRAMA)
# ==========================================
def exibir_fotograma(supabase):
    st.title("📸 Fotograma (Mapa de Sala)")
    
    try:
        res_turmas = supabase.table("alunos").select("turma").execute()
        lista_turmas = sorted(list(set([r['turma'] for r in res_turmas.data if r.get('turma')])))
        
        if lista_turmas:
            col_pills, col_btn = st.columns([8, 2], vertical_alignment="bottom")
            with col_pills:
                turma_sel = st.pills("Selecione a Turma:", options=lista_turmas)
            
            if turma_sel:
                alunos = supabase.table("alunos").select("*").eq("turma", turma_sel).order("nome").execute().data
                mapa_fotos = listar_arquivos_bucket(supabase)
                supabase_url = st.secrets['SUPABASE_URL']
                
                # Botão PDF
                with col_btn:
                    if st.button("⚙️ Gerar PDF", use_container_width=True):
                        pdf_bytes = gerar_pdf_mapa_sala_com_fotos(alunos, turma_sel, mapa_fotos, supabase_url)
                        st.download_button("📥 Baixar", data=pdf_bytes, file_name=f"Mapa_{turma_sel}.pdf", mime="application/pdf", use_container_width=True)

                st.divider()

                # Grade de Fotos
                num_cols = 6
                for i in range(0, len(alunos), num_cols):
                    linha_alunos = alunos[i : i + num_cols]
                    cols = st.columns(num_cols)
                    
                    for j, aluno in enumerate(linha_alunos):
                        with cols[j]:
                            with st.container(border=True):
                                chave = limpar_texto(aluno['nome'])
                                foto_arq = mapa_fotos.get(chave)
                                
                                if foto_arq:
                                    url_base = f"{supabase_url}/storage/v1/object/public/fotos-alunos/{quote(foto_arq)}"
                                    st.image(url_base, use_container_width=True)
                                else:
                                    st.markdown("<div style='height:80px; background:#f9f9f9; display:flex; align-items:center; justify-content:center; border-radius:8px; border: 1px dashed #ccc; font-size:24px;'>👤</div>", unsafe_allow_html=True)
                                
                                # Nome do Aluno
                                st.markdown(f"<p style='text-align:center; font-size:10px; font-weight:bold; margin-bottom:0px;'>{aluno['nome']}</p>", unsafe_allow_html=True)
                                
                                # Data e Idade (Legenda sutil)
                                dt_nasc = aluno.get('data_nascimento', '')
                                dt_formatada = pd.to_datetime(dt_nasc).strftime('%d/%m/%Y') if dt_nasc else "--/--/----"
                                idade = calcular_idade(dt_nasc)
                                st.markdown(f"<p style='text-align:center; font-size:9px; color:gray; margin-top:0px;'>{dt_formatada} • {idade}</p>", unsafe_allow_html=True)
        else:
            st.warning("Nenhuma turma encontrada.")
    except Exception as e:
        st.error(f"Erro: {e}")
