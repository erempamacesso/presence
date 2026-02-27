import streamlit as st
import pandas as pd
import unicodedata
from urllib.parse import quote
from fpdf import FPDF
from datetime import datetime

# ==========================================
# 🚩 CONFIGURAÇÃO DE COLUNAS (MARCADORES)
# ==========================================
# Se o nome no seu banco for diferente, mude apenas aqui:
COLUNA_NOME = "nome"
COLUNA_DATA = "data_nascimento" 

# ==========================================
# FUNÇÕES DE TRATAMENTO (CORRIGIDAS)
# ==========================================
def limpar_texto(texto):
    """Padronização rigorosa para não perder o vínculo com as fotos"""
    if not texto: return ""
    # Remove extensões se houver no nome
    if "." in str(texto): texto = str(texto).rsplit('.', 1)[0]
    # Remove acentos e caracteres especiais
    nfkd = unicodedata.normalize('NFKD', str(texto))
    texto_limpo = "".join([c for c in nfkd if not unicodedata.combining(c)]).lower()
    # Mantém apenas letras e números (remove espaços e símbolos)
    return "".join(filter(str.isalnum, texto_limpo))

def calcular_idade_completa(data_nascimento):
    """Calcula a idade real baseada no dia de hoje"""
    if not data_nascimento: return ""
    try:
        # Tenta converter a data do banco (ajusta para padrão brasileiro se necessário)
        dt_nasc = pd.to_datetime(data_nascimento, dayfirst=True, errors='coerce')
        if pd.isnat(dt_nasc): return ""
        
        hoje = datetime.now()
        idade = hoje.year - dt_nasc.year - ((hoje.month, hoje.day) < (dt_nasc.month, dt_nasc.day))
        return f"{idade} anos"
    except:
        return ""

@st.cache_data(ttl=60) # Cache curto para atualizar rápido se você subir foto nova
def listar_arquivos_bucket(_supabase):
    try:
        # Lista os arquivos da pasta raiz do bucket
        arquivos = _supabase.storage.from_('fotos-alunos').list(path=None, options={'limit': 5000})
        # O MAPA precisa usar a mesma função limpar_texto para dar "match"
        return {limpar_texto(arq['name']): arq['name'] for arq in arquivos}
    except:
        return {}

# ==========================================
# GERADOR DE PDF (AJUSTADO)
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
        
        # Processamento de legenda
        idade_str = calcular_idade_completa(raw_date)
        try:
            dt_fmt = pd.to_datetime(raw_date, dayfirst=True).strftime('%d/%m/%Y')
        except:
            dt_fmt = "--/--/----"
        
        legenda_pdf = f"{dt_fmt} - {idade_str}" if idade_str else dt_fmt

        # Desenho do Box
        pdf.set_xy(x, y)
        pdf.cell(largura_col, altura_linha, txt="", border=1)
        
        # Lógica da Foto (O Match Crítico)
        chave_busca = limpar_texto(nome_completo)
        foto_nome_arquivo = mapa_fotos.get(chave_busca)
        
        if foto_nome_arquivo:
            url_img = f"{supabase_url}/storage/v1/object/public/fotos-alunos/{quote(foto_nome_arquivo)}"
            try:
                pdf.image(url_img, x=x + (largura_col - 22)/2, y=y + 3, w=22, h=22)
            except: pass
        
        # Nome e Legenda
        pdf.set_font("Arial", style='B', size=8)
        pdf.set_xy(x, y + 28)
        # Nome Curto para caber no PDF
        partes = nome_completo.split()
        nome_curto = " ".join(partes[:2]) if len(partes) > 1 else partes[0]
        pdf.cell(largura_col, 5, txt=nome_curto.encode('latin-1', 'ignore').decode('latin-1'), border=0, align='C')
        
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
    st.title("📸 Fotograma Escolar")
    
    try:
        # Busca turmas para o seletor
        res = supabase.table("alunos").select("turma").execute()
        lista_turmas = sorted(list(set([r['turma'] for r in res.data if r.get('turma')])))
        
        turma_sel = st.selectbox("Selecione a Turma:", [""] + lista_turmas)
        
        if turma_sel:
            alunos = supabase.table("alunos").select("*").eq("turma", turma_sel).order("nome").execute().data
            mapa_fotos = listar_arquivos_bucket(supabase)
            supabase_url = st.secrets['SUPABASE_URL']
            
            # Botão de PDF
            if st.button("🚀 Gerar PDF para Impressão"):
                pdf_bytes = gerar_pdf_mapa_sala_com_fotos(alunos, turma_sel, mapa_fotos, supabase_url)
                st.download_button("📥 Baixar PDF", data=pdf_bytes, file_name=f"Mapa_{turma_sel}.pdf")

            st.divider()

            # Grade de Alunos na Tela
            cols = st.columns(6)
            for idx, aluno in enumerate(alunos):
                with cols[idx % 6]:
                    with st.container(border=True):
                        nome = aluno[COLUNA_NOME]
                        chave = limpar_texto(nome)
                        foto_arq = mapa_fotos.get(chave)
                        
                        if foto_arq:
                            st.image(f"{supabase_url}/storage/v1/object/public/fotos-alunos/{quote(foto_arq)}")
                        else:
                            st.markdown("<div style='height:80px; background:#f0f0f0; border-radius:5px; display:flex; align-items:center; justify-content:center;'>👤</div>", unsafe_allow_html=True)
                        
                        st.markdown(f"**{nome.split()[0]}**") # Mostra só primeiro nome na grade para não poluir
                        
                        # Idade na Tela
                        raw_date = aluno.get(COLUNA_DATA) or aluno.get('Data de nascimento')
                        idade = calcular_idade_completa(raw_date)
                        try:
                            dt_fmt = pd.to_datetime(raw_date, dayfirst=True).strftime('%d/%m/%Y')
                        except:
                            dt_fmt = "--/--/----"
                        
                        st.caption(f"{dt_fmt}")
                        st.caption(f"**{idade}**")
                        
    except Exception as e:
        st.error(f"Erro inesperado: {e}")
