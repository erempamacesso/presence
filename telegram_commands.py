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
# COMANDOS DO BOT
# =========================================

commands = {

    "commands": [

        {
            "command": "start",

            "description":
            "Iniciar atendimento"
        },

        {
            "command": "menu",

            "description":
            "Abrir menu principal"
        },

        {
            "command": "atrasos",

            "description":
            "Consultar atrasos"
        },

        {
            "command": "sair",

            "description":
            "Desvincular Telegram"
        }

    ]

}

# =========================================
# URL TELEGRAM
# =========================================

url = (
    f"https://api.telegram.org/bot{TOKEN}/setMyCommands"
)

# =========================================
# ENVIO
# =========================================

response = requests.post(

    url,

    json=commands

)

# =========================================
# RESULTADO
# =========================================

print(
    response.json()
)