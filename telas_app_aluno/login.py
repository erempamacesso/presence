import streamlit as st
import base64

def mostrar_tela_login(supabase_conn):
    # 1. Função para ler a imagem do seu D: e transformar em código que o navegador entende
    def get_base64_image(file_path):
        try:
            with open(file_path, "rb") as f:
                data = f.read()
            return base64.b64encode(data).decode()
        except Exception as e:
            return None

    # Caminho que você passou
    path_fundo = r"D:\argos-erempam\fundo_app.png"
    img_b64 = get_base64_image(path_fundo)
    
    # Define o fundo: Se a imagem existir, usa ela. Se não, usa uma cor sólida escura.
    bg_image_style = f"url('data:image/png;base64,{img_b64}')" if img_b64 else "#0a192f"

    # ==========================================
    # MÁGICA DO CSS: VISUAL MODERNO COM FUNDO LOCAL
    # ==========================================
    st.markdown(f"""
        <style>
        /* 1. Imagem de fundo com camada escura (Overlay) */
        .stApp {{
            background: linear-gradient(rgba(0, 0, 0, 0.7), rgba(0, 0, 0, 0.85)), 
                        {bg_image_style} no-repeat center center fixed !important;
            background-size: cover !important;
        }}

        /* 2. Ocultar o cabeçalho padrão */
        header {{visibility: hidden;}}

        /* 3. Estilizando o Cartão de Vidro (Glassmorphism) */
        div[data-testid="stForm"] {{
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(15px);
            -webkit-backdrop-filter: blur(15px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 24px;
            padding: 3rem 2rem;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
            max-width: 450px;
            margin: auto;
        }}

        /* 4. Títulos e Textos */
        .titulo-eco {{
            text-align: center;
            font-size: 2.2rem;
            font-weight: 800;
            background: linear-gradient(90deg, #00f2fe 0%, #4facfe 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-family: 'Segoe UI', sans-serif;
        }}
        
        .subtitulo-eco {{
            text-align: center;
            color: #a0aec0;
            letter-spacing: 2px;
            margin-bottom: 2rem;
        }}

        /* 5. Inputs brancos arredondados */
        div[data-baseweb="input"] {{
            border-radius: 12px !important;
            background-color: white !important;
        }}

        /* 6. Botão Estilizado */
        div[data-testid="stFormSubmitButton"] > button {{
            background: linear-gradient(90deg, #4facfe 0%, #00f2fe 100%) !important;
            color: #0a192f !important;
            font-weight: bold !important;
            border-radius: 12px !important;
            border: none !important;
            width: 100% !important;
            height: 50px;
            transition: 0.3s;
        }}
        
        div[data-testid="stFormSubmitButton"] > button:hover {{
            transform: scale(1.02);
            box-shadow: 0 5px 15px rgba(79, 172, 254, 0.4);
        }}
        </style>
    """, unsafe_allow_html=True)

    # --- RENDERIZAÇÃO DA TELA ---
    st.markdown('<p class="titulo-eco">ECOSSISTEMA DO ALUNO</p>', unsafe_allow_html=True)
    st.markdown('<p class="subtitulo-eco">EREMPAM</p>', unsafe_allow_html=True)

    with st.form("login_aluno"):
        st.markdown("<p style='text-align:center;'>👋 Bem-vindo(a)!</p>", unsafe_allow_html=True)
        matricula = st.text_input("Número de Matrícula", placeholder="Digite sua matrícula...")
        nascimento = st.date_input("Data de Nascimento", format="DD/MM/YYYY")
        
        if st.form_submit_button("ENTRAR NO ECOSSISTEMA"):
            # Aqui entra sua lógica de validação com o supabase_conn
            st.success("Validando acesso...")