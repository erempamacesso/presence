# Mapeamento canônico de assunto → frente para Química vestibular
# Frente 1 = Química Geral | Frente 2 = Físico-Química | Frente 3 = Química Orgânica

FRENTES = ["Frente 1", "Frente 2", "Frente 3"]

FRENTE_DESCRICAO = {
    "Frente 1": "Química Geral",
    "Frente 2": "Físico-Química",
    "Frente 3": "Química Orgânica",
}

ASSUNTOS_POR_FRENTE = {
    "Frente 1": [
        "Matéria e Propriedades",
        "Misturas e Separação de Misturas",
        "Atomística",
        "Modelos Atômicos",
        "Tabela Periódica",
        "Ligações Químicas",
        "Geometria Molecular",
        "Polaridade e Forças Intermoleculares",
        "Funções Inorgânicas",
        "Ácidos e Bases",
        "Sais e Óxidos",
        "Nomenclatura Inorgânica",
        "Reações Inorgânicas",
        "Estequiometria",
        "Gases",
    ],
    "Frente 2": [
        "Termoquímica",
        "Cinética Química",
        "Equilíbrio Químico",
        "Equilíbrio Iônico",
        "Soluções",
        "Concentração de Soluções",
        "Propriedades Coligativas",
        "Eletroquímica",
        "Pilhas e Baterias",
        "Eletrólise",
        "Radioatividade",
    ],
    "Frente 3": [
        "Introdução à Química Orgânica",
        "Cadeias Carbônicas",
        "Hidrocarbonetos",
        "Funções Orgânicas Oxigenadas",
        "Alcoóis e Fenóis",
        "Éteres",
        "Aldeídos e Cetonas",
        "Ácidos Carboxílicos e Ésteres",
        "Funções Orgânicas Nitrogenadas",
        "Aminas e Amidas",
        "Reações Orgânicas",
        "Isomeria",
        "Polímeros",
        "Bioquímica",
        "Petróleo e Combustíveis",
    ],
}

# Dicionário invertido: assunto → frente esperada
FRENTE_POR_ASSUNTO: dict[str, str] = {
    assunto: frente
    for frente, assuntos in ASSUNTOS_POR_FRENTE.items()
    for assunto in assuntos
}


def sugerir_frente(assunto: str) -> str | None:
    """Retorna a frente esperada para um assunto (case-insensitive, correspondência parcial)."""
    assunto_lower = assunto.strip().lower()
    for key, frente in FRENTE_POR_ASSUNTO.items():
        if key.lower() == assunto_lower:
            return frente
    # Busca parcial
    for key, frente in FRENTE_POR_ASSUNTO.items():
        if assunto_lower in key.lower() or key.lower() in assunto_lower:
            return frente
    return None
