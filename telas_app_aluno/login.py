import streamlit as st
import time

def mostrar_tela_login(supabase_conn):
    # ==========================================
    # MÁGICA DO CSS: VISUAL MODERNO (REACT STYLE)
    # ==========================================
    st.markdown("""
        <style>
        /* 1. Imagem de fundo cobrindo tudo com sobreposição escura */
        .stApp {
            /* DEPOIS TROQUE O LINK ABAIXO PELA SUA IMAGEM GERADA POR IA */
            background: linear-gradient(rgba(10, 25, 47, 0.75), rgba(10, 25, 47, 0.85)), 
                        url('https://images.unsplash.com/photo-1550751827-4bd374c3f58b?q=80&w=2070&auto=format&fit=crop') no-repeat center center fixed !important;
            background-size: cover !important;
        }

        /* 2. Ocultar o cabeçalho padrão do Streamlit para ficar tela limpa */
        header {visibility: hidden;}

        /* 3. Estilizando o Form para virar um Cartão de Vidro (Glassmorphism) */
        div[data-testid="stForm"] {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid rgba(255, 255, 255, 0.15);
            border-radius: 24px;
            padding: 3rem 2rem;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
        }

        /* 4. Textos dentro do form */
        div[data-testid="stForm"] p, div[data-testid="stForm"] label {
            color: #e2e8f0 !important;
            font-weight: 500 !important;
        }

        /* 5. Títulos do Ecossistema */
        .titulo-eco {
            text-align: center;
            font-size: 2.5rem;
            font-weight: 900;
            background: linear-gradient(90deg, #00f2fe 0%, #4facfe 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0px;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            letter-spacing: -1px;
        }
        
        .subtitulo-eco {
            text-align: center;
            font-size: 1.2rem;
            font-weight: 400;
            color: #a0aec0;
            letter-spacing: 4px;
            margin-bottom: 2rem;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }

        /* 6. Inputs arredondados e modernos */
        div[data-baseweb="input"] {
            border-radius: 12px !important;
            background-color: rgba(255, 255, 255, 0.9) !important;
            border: 2px solid transparent !important;
            transition: all 0.3s ease !important;
        }
        div[data-baseweb="input"]:focus-within {
            border: 2px solid #4facfe !important;
            box-shadow: 0 0 10px rgba(79, 172, 254, 0.5) !important;
        }

        /* 7. Botão Principal com Efeito Hover */
        div[data-testid="stFormSubmitButton"] > button {
            background: linear-gradient(90deg, #4facfe 0%, #00f2fe 100%) !important;
            color: #0a192f !important;
            font-weight: 800 !important;
            font-size: 1.1rem !important;
            border: none !important;
            border-radius: 12px !important;
            padding: 0.8rem !important;
            transition: all 0.3s ease !important;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        div[data-testid="stFormSubmitButton"] > button:hover {
            transform: translateY(-3px) !important;
            box-shadow: 0 8px 20px rgba(79, 172, 254, 0.4) !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # ==========================================
    # CONSTRUÇÃO DA TELA
    # ==========================================
    # Usando colunas vazias nas laterais para centralizar no Desktop, mas mantendo bom no Mobile
    col1, col2, col3 = st.columns([1, 2.5, 1])
    
    with col2:
        # Títulos injetados com HTML puro para aplicar o gradiente
        st.markdown('<div class="titulo-eco">ECOSSISTEMA DO ALUNO</div>', unsafe_allow_html=True)
        st.markdown('<div class="subtitulo-eco">EREMPAM</div>', unsafe_allow_html=True)
        
        with st.form("form_login_eco"):
            st.markdown("<p style='text-align: center; font-size: 1.2rem; margin-bottom: 1rem;'>👋 Bem-vindo(a)!</p>", unsafe_allow_html=True)
            
            matricula = st.text_input("👤 Número de Matrícula", placeholder="Digite sua matrícula...")
            nascimento = st.text_input("📅 Data de Nascimento", placeholder="DD/MM/AAAA")
            
            st.write("") # Espaçamento
            submit_login = st.form_submit_button("Entrar no Ecossistema", use_container_width=True)
            
            if submit_login:
                if not matricula or not nascimento:
                    st.error("⚠️ Preencha a matrícula e a data de nascimento.")
                else:
                    try:
                        # Logica de verificação no banco de dados (Ajuste conforme suas colunas exatas)
                        res = supabase_conn.table("alunos").select("*").eq("matricula", matricula.strip()).eq("data_nascimento", nascimento.strip()).execute()
                        
                        if res.data:
                            st.success(f"✅ Autenticado com sucesso! Entrando...")
                            st.session_state.aluno = res.data[0]
                            time.sleep(1)
                            # ENVIA PARA A ANTE-SALA
                            st.session_state.etapa = "ante_sala"
                            st.rerun()
                        else:
                            st.error("❌ Credenciais inválidas. Tente novamente.")
                    except Exception as e:
                        st.error(f"🚨 Erro no servidor: {e}")