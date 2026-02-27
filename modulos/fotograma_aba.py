import streamlit as st
import pandas as pd
import unicodedata
from urllib.parse import quote
from fpdf import FPDF
from datetime import datetime

# ==========================================
# 🚩 MARCADORES DE CONFIGURAÇÃO (AJUSTE AQUI)
# ==========================================
# Se o nome da coluna no seu Supabase for diferente, mude apenas aqui:
COLUNA_BANCO_NOME = "nome"
COLUNA_BANCO_DATA = "data_nascimento"  # ou "Data de nascimento"

# ==========================================
# FUNÇÕES AUXILIARES
# ==========================================
def calcular_idade(data_nascimento):
    """Calcula a idade subtraindo a data de nascimento da data de HOJE"""
    if not data_nascimento or pd.isna(data_nascimento): 
        return ""
    try:
        # Força a conversão da data (dayfirst=True para evitar confusão entre 01/05 e 05/01)
        dt_nasc = pd.to_datetime(data_nascimento, dayfirst=True, errors='coerce')
        
        if pd.isnat(dt_nasc): 
            return ""
            
        hoje = datetime.now()
        # Lógica matemática: Subtrai anos e ajusta se o aniversário ainda não passou no ano atual
        idade = hoje.year - dt_nasc.year - ((hoje.month, hoje.day) < (dt_nasc.month, dt_nasc.day))
        
        return f"{idade} anos"
    except:
        return ""

def limpar_texto(texto):
    if not texto: return ""
    nfkd = unicodedata.normalize('NFKD', str(texto))
    return "".join([c for c in nfkd if not unicodedata.combining(c)]).lower().replace(" ", "")

@st.cache_data(ttl=600)
def listar_arquivos_bucket(_supabase):
    try:
        arquivos = _supabase.storage.from_('fotos-alunos').list(path=None, options={'limit': 5000})
        return {limpar_texto(arq['name']): arq['name'] for arq in arquivos}
    except: return {}

# ==========================================
# GERADOR DE PDF
# ==========================================
def gerar_pdf_mapa_sala_com_fotos(alunos, turma, mapa_fotos, supabase_url):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    
    pdf.set_font("Arial", style='B', size=16)
    pdf.cell(0, 10, txt=f"Mapa de Sala - Turma {turma}", ln=True, align='C')
    pdf.ln(5)

    largura_col = 45 
    altura_linha = 46 
    
    start_x, start_y = pdf.get_x(), pdf.get_y()
    x, y = start_x, start_y
    
    for i, aluno in enumerate(alunos):
        # 1. Dados do Aluno
        nome_original = aluno.get(COLUNA_BANCO_NOME, 'Sem Nome')
        raw_date = aluno.get(COLUNA_BANCO_DATA) or aluno.get('Data de nascimento')
        
        # 2. Formatação da Legenda
        idade_texto = calcular_idade(raw_date)
        try:
            dt_obj = pd.to_datetime(raw_date, dayfirst=True)
            dt_fmt = dt_obj.strftime('%d/%m/%Y')
        except:
            dt_fmt = "--/--/----"
        
        # O TERMO QUE VOCÊ PEDIU: "DATA - XX anos"
        legenda = f"{dt_fmt} - {idade_texto}" if idade_texto else dt_fmt

        # 3. Nome Curto (2 primeiros nomes)
        nome_pdf = str(nome_original).encode('latin-1', 'ignore').decode('latin-1')
        partes = nome_pdf.split()
        nome_curto = " ".join(partes[:2]) if len(partes) > 1 else partes[0]

        # 4. Desenho do Quadrado
        pdf.set_xy(x, y)
        pdf.cell(largura_col, altura_linha, txt="", border=1)
        
        # Foto
        chave_foto = limpar_texto(nome_original)
        foto_arq = mapa_fotos.get(chave_foto)
        if foto_arq:
            url_img = f"{supabase_url}/storage/v1/object/public/fotos-alunos/{quote(foto_arq)}"
            try:
                pdf.image(url_img, x=x + (largura_col - 22)/2, y=y + 3, w=22, h=22)
            except: pass
        
        # Texto: Nome (Negrito)
        pdf.set_font("Arial", style='B', size=8)
        pdf.set_xy(x, y + 27)
        pdf.cell(largura_col, 5, txt=nome_curto, border=0, align='C')
        
        # Texto: Data e Idade (Normal)
        pdf.set_font("Arial", size=7)
        pdf.set_xy(x, y + 33)
        pdf.cell(largura_col, 5, txt=legenda, border=0, align='C')
        
        # Lógica de Posicionamento
        if (i + 1) % 6 == 0:
            x = start_x
            y += altura_linha
            if y > 160: pdf.add_page(); y = pdf.get_y()
        else:
            x += largura_col
            
    return bytes(pdf.output(dest='S'))

# ==========================================
# TELA PRINCIPAL
# ==========================================
def exibir_fotograma(supabase):
    st.title("📸 Fotograma (Mapa de Sala)")
    
    try:
        res_turmas = supabase.table("alunos").select("turma").execute()
        lista_turmas = sorted(list(set([r['turma'] for r in res_turmas.data if r.get('turma')])))
        
        if lista_turmas:
            turma_sel = st.pills("Selecione a Turma:", options=lista_turmas)
            
            if turma_sel:
                alunos = supabase.table("alunos").select("*").eq("turma", turma_sel).order("nome").execute().data
                mapa_fotos = listar_arquivos_bucket(supabase)
                supabase_url = st.secrets['SUPABASE_URL']
                
                # Botão de Gerar PDF
                if st.button("⚙️ Gerar PDF", type="primary"):
                    pdf_bytes = gerar_pdf_mapa_sala_com_fotos(alunos, turma_sel, mapa_fotos, supabase_url)
                    st.download_button("📥 Baixar PDF Agora", data=pdf_bytes, file_name=f"Mapa_{turma_sel}.pdf")

                st.divider()

                # Exibição na Tela
                grid = st.columns(6)
                for idx, aluno in enumerate(alunos):
                    with grid[idx % 6]:
                        with st.container(border=True):
                            # Foto
                            chave = limpar_texto(aluno[COLUNA_BANCO_NOME])
                            foto_arq = mapa_fotos.get(chave)
                            if foto_arq:
                                st.image(f"{supabase_url}/storage/v1/object/public/fotos-alunos/{quote(foto_arq)}")
                            else:
                                st.markdown("<div style='height:70px; background:#eee; border-radius:5px;'></div>", unsafe_allow_html=True)
                            
                            # Nome
                            st.markdown(f"**{aluno[COLUNA_BANCO_NOME]}**")
                            
                            # Data e Idade
                            raw_date = aluno.get(COLUNA_BANCO_DATA) or aluno.get('Data de nascimento')
                            idade = calcular_idade(raw_date)
                            try:
                                dt_exibicao = pd.to_datetime(raw_date, dayfirst=True).strftime('%d/%m/%Y')
                            except:
                                dt_exibicao = "--/--/----"
                            
                            st.caption(f"{dt_exibicao} - {idade}")
        else:
            st.warning("Nenhuma turma encontrada.")
    except Exception as e:
        st.error(f"Erro: {e}")
