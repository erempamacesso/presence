import requests
import toml

# =========================================
# SECRETS
# =========================================

secrets = toml.load(
    ".streamlit/secrets.toml"
)

TOKEN = secrets[
    "TELEGRAM_BOT_TOKEN"
]

# =========================================
# CHAT ID
# =========================================

CHAT_ID = "376565054"

# =========================================
# MENSAGEM
# =========================================

mensagem = """
🚨 TESTE DE NOTIFICAÇÃO

Seu sistema de atrasos
está funcionando 😄🔥
"""

# =========================================
# ENVIO
# =========================================

url = (
    f"https://api.telegram.org/bot{TOKEN}/sendMessage"
)

response = requests.post(

    url,

    json={

        "chat_id": CHAT_ID,

        "text": mensagem

    }

)

print(
    response.json()
)