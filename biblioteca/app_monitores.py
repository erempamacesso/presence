import streamlit as st
from supabase import create_client
import requests
import qrcode
from io import BytesIO

# --- CONFIGURAÇÃO DOS DOIS BANCOS ---
# Os segredos devem estar no seu secrets.toml ou no painel do Streamlit
URL_ALUNOS = st.secrets["supabase_alunos_url"]
KEY_ALUNOS = st.secrets["supabase_alunos_key"]
URL_BIBLIO = st.secrets["supabase_biblio_url"]
KEY_BIBLIO = st.secrets["supabase_biblio_key"]

db_alunos = create_client(URL_ALUNOS, KEY_ALUNOS)
db_biblio = create_client(URL_BIBLIO, KEY_BIBLIO)

st.title("📚 Portal do Monitor - Cadastro de Obras")

# --- FUNÇÃO PARA BUSCAR LIVRO VIA GOOGLE BOOKS ---
def buscar_livro_isbn(isbn):
    url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}"
    response = requests.get(url).json()
    if "items" in response:
        info = response["items"][0]["volumeInfo"]
        return {
            "titulo": info.get("title", "Sem título"),
            "autor": ", ".join(info.get("authors", ["Desconhecido"])),
            "capa": info.get("imageLinks", {}).get("thumbnail", ""),
            "categoria": ", ".join(info.get("categories", ["Geral"]))
        }
    return None

# --- UI DE CADASTRO ---
with st.container(border=True):
    isbn_input = st.text_input("Escaneie ou digite o ISBN do Livro")
    
    if isbn_input:
        dados = buscar_livro_isbn(isbn_input)
        if dados:
            st.image(dados["capa"], width=100)
            titulo = st.text_input("Título", value=dados["titulo"])
            autor = st.text_input("Autor", value=dados["autor"])
            cat = st.text_input("Categoria", value=dados["categoria"])
            qtd = st.number_input("Quantidade de exemplares", min_value=1, value=1)
            
            if st.button("Confirmar Cadastro e Gerar Etiqueta"):
                # 1. Salvar no Banco 2 (Biblioteca)
                novo_livro = {
                    "isbn": isbn_input,
                    "titulo": titulo,
                    "autor": autor,
                    "categoria": cat,
                    "capa_url": dados["capa"], # Link direto do Google
                    "quantidade_total": qtd,
                    "quantidade_disponivel": qtd
                }
                
                res = db_biblio.table("livros").insert(novo_livro).execute()
                
                if res.data:
                    id_gerado = res.data[0]["id"]
                    st.success(f"Livro '{titulo}' cadastrado com sucesso!")
                    
                    # 2. Gerar QR Code da Etiqueta
                    qr_data = f"LIB:{id_gerado}"
                    img_qr = qrcode.make(qr_data)
                    
                    buf = BytesIO()
                    img_qr.save(buf, format="PNG")
                    st.image(buf, caption=f"Etiqueta para: {titulo}")
                    st.download_button("Baixar Etiqueta QR", buf.getvalue(), f"etiqueta_{id_gerado}.png")
        else:
            st.error("Livro não encontrado na base do Google. Digite manualmente.")