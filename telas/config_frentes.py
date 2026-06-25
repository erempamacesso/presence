# Mapeamento canônico de assunto → frente para Química vestibular
# Valores espelhados do banco: "Química Geral", "Físico-Química", "Química Orgânica"

FRENTES = ["Química Geral", "Físico-Química", "Química Orgânica"]

ASSUNTOS_POR_FRENTE = {
    "Química Geral": [
        "CALCULO DE DE MASSA MOLECULAR/MOLAR",
        "Classificação de Sistemas e Misturas",
        "Estequiometria (Cálculos em Reações)",
        "Grandezas Químicas e Mol",
        "Massa Molar e Molecular",
        "RELAÇÕES ESTEQUIOMÉTRICAS",
        "RELAÇÕES MOLARES E TRANSFORMAÇÕES DE UNIDADES",
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
    ],
    "Físico-Química": [
        "Densidade",
        "Diluição de Soluções",
        "Estudo dos Gases",
        "Mistura de Soluções",
        "Radioatividade",
        "Solubilidade e Cristalização",
        "Soluções (Concentração)",
        "Soluções Verdadeiras - Coeficiente de Solubilidade",
        "Soluções Verdadeiras - Concentração Molar",
        "Soluções Verdadeiras - Curvas de Solubilidade",
        "Soluções Verdadeiras - Concentração Comum",
        "Soluções Verdadeiras - Densidade",
        "Soluções Verdadeiras - Purificação e Recristalização",
        "Soluções Verdadeiras - Relação entre Concentrações",
        "Soluções Verdadeiras - Soluto e Solvente",
        "Soluções Verdadeiras - Título Percentual",
        "Termoquímica",
        "Cinética Química",
        "Equilíbrio Químico",
        "Equilíbrio Iônico",
        "Propriedades Coligativas",
        "Eletroquímica",
        "Pilhas e Baterias",
        "Eletrólise",
    ],
    "Química Orgânica": [
        "Classificação de Cadeias Carbônicas",
        "Funções Orgânicas Mistas",
        "Funções Orgânicas Nitrogenadas",
        "Funções Orgânicas Oxigenadas",
        "Hibridização do Carbono",
        "Introdução à Química Orgânica",
        "Nomenclatura Hidrocarbonetos IUPAC",
        "Cadeias Carbônicas",
        "Hidrocarbonetos",
        "Alcoóis e Fenóis",
        "Éteres",
        "Aldeídos e Cetonas",
        "Ácidos Carboxílicos e Ésteres",
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
    if not assunto:
        return None
    assunto_lower = assunto.strip().lower()
    # Busca exata
    for key, frente in FRENTE_POR_ASSUNTO.items():
        if key.lower() == assunto_lower:
            return frente
    # Busca parcial
    for key, frente in FRENTE_POR_ASSUNTO.items():
        if assunto_lower in key.lower() or key.lower() in assunto_lower:
            return frente
    return None
