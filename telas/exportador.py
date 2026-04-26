# utils/exportador.py (ou onde você preferir salvar)
from docx import Document
from io import BytesIO
import re

def limpar_conteudo(dado):
    """Limpa dicionários ou tags HTML para o Word ficar perfeito"""
    if isinstance(dado, dict):
        return dado.get('texto', list(dado.values())[0] if dado else "")
    texto_limpo = re.sub(r'<[^>]+>', '', str(dado))
    return texto_limpo.strip()

def gerar_prova_word(titulo_prova, questoes):
    """Cria o documento Word em memória usando as questões do banco"""
    doc = Document()
    
    # Cabeçalho
    doc.add_heading(f'Avaliação: {titulo_prova}', 0)
    doc.add_paragraph('Nome: __________________________________________________ Turma: _______')
    doc.add_paragraph('\n')

    # Adicionando as questões
    for i, q in enumerate(questoes, 1):
        # Limpa o enunciado antes de colocar no Word
        enunciado = limpar_conteudo(q.get('enunciado', ''))
        doc.add_paragraph(f"{i}) {enunciado}")
        
        # Puxa as alternativas (verifica 'alternativas' ou 'opcoes')
        opcoes = q.get('alternativas') or q.get('opcoes') or {} 
        
        # Garante a ordem correta das letras (A, B, C, D, E)
        for letra in ["A", "B", "C", "D", "E"]:
            if letra in opcoes:
                texto_alt = limpar_conteudo(opcoes[letra])
                doc.add_paragraph(f"    ({letra}) {texto_alt}")
        
        doc.add_paragraph('\n') # Espaço entre as questões

    # Salva na memória
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    
    return buffer