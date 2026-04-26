from docx import Document
from io import BytesIO
import re

def limpar_conteudo(dado):
    """
    Limpa dicionários ou tags HTML para o Word ficar perfeito e sem sujeiras.
    """
    if isinstance(dado, dict):
        return dado.get('texto', list(dado.values())[0] if dado else "")
    
    # Remove as tags HTML (como <p>, <b>, etc)
    texto_limpo = re.sub(r'<[^>]+>', '', str(dado))
    return texto_limpo.strip()

def gerar_prova_word(titulo_prova, questoes):
    """
    Função (Motor) que cria o documento Word em memória usando as questões do banco.
    Não possui nenhuma interface do Streamlit (st.button, st.write, etc).
    """
    doc = Document()
    
    # Criando o Cabeçalho da Prova
    doc.add_heading(f'Avaliação: {titulo_prova}', 0)
    doc.add_paragraph('Nome: __________________________________________________ Turma: _______')
    doc.add_paragraph('\n') # Adiciona uma linha em branco

    # Lendo as questões e escrevendo no documento
    for i, q in enumerate(questoes, 1):
        # Escreve o Enunciado limpo
        enunciado = limpar_conteudo(q.get('enunciado', ''))
        doc.add_paragraph(f"{i}) {enunciado}")
        
        # Puxa as Alternativas (A, B, C, D, E)
        opcoes = q.get('alternativas') or q.get('opcoes') or {} 
        
        if opcoes:
            for letra in ["A", "B", "C", "D", "E"]:
                if letra in opcoes:
                    texto_alt = limpar_conteudo(opcoes[letra])
                    doc.add_paragraph(f"    ({letra}) {texto_alt}")
        
        # Adiciona um espaço extra entre uma questão e outra
        doc.add_paragraph('\n') 

    # Salva o documento na memória RAM (não cria lixo no seu computador/servidor)
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    
    return buffer