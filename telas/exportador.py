# telas/exportador.py
from docx import Document
from io import BytesIO
import re

def limpar_conteudo(dado):
    """Limpa dicionários ou tags HTML para o Word ficar perfeito e sem sujeira"""
    if isinstance(dado, dict):
        return dado.get('texto', list(dado.values())[0] if dado else "")
    texto_limpo = re.sub(r'<[^>]+>', '', str(dado))
    return texto_limpo.strip()

def gerar_prova_word(titulo_prova, questoes):
    """
    Função que cria o documento Word em memória usando as questões do banco.
    """
    doc = Document()
    
    # Cabeçalho básico
    doc.add_heading(f'Avaliação: {titulo_prova}', 0)
    doc.add_paragraph('Nome: __________________________________________________ Turma: _______')
    doc.add_paragraph('\n') # Espaço

    # Adicionando as questões
    for i, q in enumerate(questoes, 1):
        # Enunciado limpo
        enunciado = limpar_conteudo(q.get('enunciado', ''))
        doc.add_paragraph(f"{i}) {enunciado}")
        
        # Alternativas (A, B, C, D, E)
        # Verifica se sua coluna chama 'alternativas' ou 'opcoes'
        opcoes = q.get('alternativas') or q.get('opcoes') or {} 
        
        if opcoes:
            for letra in ["A", "B", "C", "D", "E"]:
                if letra in opcoes:
                    texto_alt = limpar_conteudo(opcoes[letra])
                    doc.add_paragraph(f"    ({letra}) {texto_alt}")
        
        doc.add_paragraph('\n') # Espaço entre as questões

    # Salva o documento na memória (não cria lixo no servidor)
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    
    return buffer