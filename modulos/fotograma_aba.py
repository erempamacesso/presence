import streamlit as st
import pandas as pd
import unicodedata
from urllib.parse import quote
from fpdf import FPDF
from datetime import datetime

# ==========================================
# 🚩 CONFIGURAÇÃO DE COLUNAS (MARCADORES)
# ==========================================
COLUNA_NOME = "nome"
COLUNA_DATA = "data_nascimento"  # ou "Data de nascimento"

# ==========================================
# FUNÇÕES DE TRATAMENTO
# ==========================================
def limpar_texto(texto):
    """Padronização rigorosa para não perder o vínculo com as fotos"""
    if not texto: return ""
    if "." in str(texto): texto = str(texto).rsplit('.', 1)[0]
    nfkd = unicodedata.normalize('NFKD', str(texto))
    texto_limpo = "".join([c for c in nfkd if not unicodedata.combining(c)]).lower()
    return "".join(filter(str.isalnum, texto_limpo))

def calcular_idade_completa(data_nascimento):
    """Calcula a idade real baseada no dia de hoje"""
    if not data_nascimento or pd.isna(data_nascimento): return ""
    try:
        dt_nasc = pd.to_datetime(data_nascimento, dayfirst=True, errors='coerce')
        if pd.isnat(dt_nasc): return ""
        
        hoje = datetime.now()
        idade = hoje.year - dt_nasc.year - ((hoje.month, hoje.day) < (dt_nasc.month, dt_nasc.day))
        return f"{idade} anos"
    except:
        return ""

# OTIMIZAÇÃO: Guarda a lista de fotos por 10 minutos (600s) para não travar o carregamento
@st.cache_data(ttl=600)
def listar_arquivos_bucket(_supabase):
    try:
        arquivos = _supabase.storage.from_('fotos-alunos').list(path=None, options={'limit': 5000})
        return {limpar_texto(arq['name']): arq['name'] for arq in arquivos}
    except:
        return {}

# ==========================================
# GERADOR DE PDF
# ==========================================
def gerar_pdf_mapa_sala_com_fotos(alunos, turma, mapa_fotos, supabase_url):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    
    pdf.set_font("Arial", style='B', size=16)
    pdf.cell(0, 10, txt=f"Mapa de Sala - Turma {turma}", ln=True, align='C')
    pdf.ln(5)

    largura_col, altura_linha = 45, 48 
    start_x, start_y = pdf.get_x(), pdf.get_y()
    x, y = start_x, start_y
    
    for i, aluno in enumerate(alunos):
        nome_completo = aluno.get(COLUNA_NOME, "Sem Nome")
        raw_date = aluno.get(COLUNA_DATA) or aluno.get('Data de nascimento')
        
        idade_str = calcular_idade_completa(raw_date)
        try:
            dt_fmt = pd.to_datetime(raw_date, dayfirst=True).strftime('%d/%m/%Y') if raw_date else ""
        except:
            dt_fmt = ""
        
        legenda_pdf = f"{dt_fmt} - {idade_str}" if (dt_fmt and idade_str) else (dt_fmt or idade_str)

        pdf.set_xy(x, y)
        pdf.cell(largura_col, altura_linha, txt="", border=1)
        
        chave_busca = limpar_texto(nome_completo)
        foto_nome_arquivo = mapa_fotos.get(chave_busca)
        
        if foto_nome_arquivo:
            url_img = f"{supabase_url}/storage/v1/object/public/fotos-alunos/{quote(foto_nome_arquivo)}"
            try:
                pdf.image(url_img, x=x + (largura_col - 22)/2, y=y + 3, w=22, h=22)
            except: pass
        
        pdf.set_font("Arial", style='B', size=8)
        pdf.set_xy(x, y + 28)
        partes = str(nome_completo).encode('latin-1', 'ignore').decode('latin-1').split()
        nome_curto = " ".join(partes[:2]) if len(partes) > 1 else partes[0]
        pdf.cell(largura_col, 5, txt=nome_curto, border=0, align='C')
        
        pdf.set_font("Arial", size=7)
        pdf.set_xy(x, y + 34)
        pdf.cell(largura_col, 5, txt=legenda_pdf, border=0, align='C')
        
        if (i + 1) % 6 == 0:
            x = start_x
            y += altura_linha
            if y > 150: pdf.add_page(); y = pdf.get_y()
        else:
            x += largura_col
            
    return bytes(pdf.output(dest='S'))

# ==========================================
# TELA DO APP
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
                
                with col_btn:
                    if st.button("⚙️ Gerar PDF", use_container_width=True):
                        with st.spinner("Gerando arquivo..."):
                            pdf_bytes = gerar_pdf_mapa_sala_com_fotos(alunos, turma_sel, mapa_fotos, supabase_url)
                            st.download_button("📥 Baixar PDF", data=pdf_bytes, file_name=f"Mapa_{turma_sel}.pdf")

                st.divider()

                # LÓGICA RÁPIDA DE RENDERIZAÇÃO (Blocos de 6)
                num_cols = 6
                for i in range(0, len(alunos), num_cols):
                    linha_alunos = alunos[i : i + num_cols]
                    cols = st.columns(num_cols)
                    
                    for j, aluno in enumerate(linha_alunos):
                        with cols[j]:
                            with st.container(border=True):
                                nome = aluno.get(COLUNA_NOME, "Sem Nome")
                                chave = limpar_texto(nome)
                                foto_arq = mapa_fotos.get(chave)
                                
                                # 1. Renderiza a Foto
                                if foto_arq:
                                    st.image(f"{supabase_url}/storage/v1/object/public/fotos-alunos/{quote(foto_arq)}", use_container_width=True)
                                else:
                                    st.markdown("<div style='height:80px; background:#f0f0f0; border-radius:5px; display:flex; align-items:center; justify-content:center; font-size:24px;'>👤</div>", unsafe_allow_html=True)
                                
                                # 2. Renderiza o Nome Completo (Formatado para caber bonito)
                                st.markdown(f"<p style='text-align:center; font-size:10px; font-weight:bold; margin-top:5px; margin-bottom:0px; line-height:1.2;'>{nome}</p>", unsafe_allow_html=True)
                                
                                # 3. Renderiza Data e Idade na mesma linha
                                raw_date = aluno.get(COLUNA_DATA) or aluno.get('Data de nascimento')
                                idade = calcular_idade_completa(raw_date)
                                try:
                                    dt_fmt = pd.to_datetime(raw_date, dayfirst=True).strftime('%d/%m/%Y') if raw_date else "--/--/----"
                                except:
                                    dt_fmt = "--/--/----"
                                
                                texto_legenda = f"{dt_fmt} - {idade}" if idade else dt_fmt
                                st.markdown(f"<p style='text-align:center; font-size:9px; color:gray; margin-top:2px;'>{texto_legenda}</p>", unsafe_allow_html=True)
                                
        else:
            st.warning("Nenhuma turma encontrada.")
    except Exception as e:
        st.error(f"Erro inesperado: {e}")
