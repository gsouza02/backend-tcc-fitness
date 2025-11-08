from openai import OpenAI
import os
from dotenv import load_dotenv
import json

# Carrega variáveis do .env
load_dotenv()

# Inicializa o cliente
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Faz a requisição
response = client.responses.create(
    model="gpt-4o-mini-2024-07-18",
    input="""
Você é uma IA de prescrição de treinos. Sua única tarefa é gerar, a partir das respostas de anamnese descritas abaixo, um JSON válido que represente um programa de treino completo. Leia todo o enunciado antes de responder. REQUISITOS OBRIGATÓRIOS 1. A resposta deve ser EXCLUSIVAMENTE um JSON bem formatado, sem comentários, cabeçalhos, explicações ou texto adicional. 2. Siga exatamente o esquema: { "programaTreino": { "nomePrograma": "string obrigatória", "descricaoPrograma": "string obrigatória" }, "treinos": [ { "nome": "string obrigatória", "descricao": "string obrigatória", "duracaoMinutos": inteiro >= 10, "dificuldade": "iniciante" | "intermediario" | "avancado", "exercicios": [ { "idExercicio": inteiro >= 1, "series": inteiro >= 1, "repeticoes": inteiro >= 1, "descansoSegundos": inteiro >= 15 } ] } ] } 3. Todos os campos devem estar preenchidos com valores coerentes com as respostas da anamnese. 4. Gere pelo menos 1 treino e entre 3 e 10 exercícios por treino. 5. Use apenas números inteiros para campos numéricos. 6. Nomes e descrições precisam refletir objetivos, restrições, nível de experiência, tempo disponível e equipamentos do usuário. 8. Exercícios devem ser compatíveis com as condições e equipamento informados. Ajuste séries, repetições e descanso conforme o nível/objetivo (ex.: hipertrofia, resistência, emagrecimento). 9. Se houver lesões ou limitações, adapte a seleção de exercícios e descreva isso no campo descricao do treino. 10. Sempre retorne um JSON sintaticamente válido (aberturas/fechamentos corretos, aspas em strings, vírgulas adequadas). PROCESSO DE GERAÇÃO - Primeiro, interprete o perfil do usuário (idade, experiência, disponibilidade, objetivos, lesões, equipamentos). - Determine a dificuldade adequada ("iniciante", "intermediario" ou "avancado"). - Defina nome e descrição do programa resumindo o objetivo principal e a abordagem. - Para cada treino: • Defina nome e descrição específicos, destacando foco muscular, objetivo do dia e recomendações. • Escolha exercícios compatíveis; variem grupos musculares conforme os objetivos. • Ajuste séries, repetições e descanso para refletir intensidade e tempo disponível. • Mantenha a duração total aproximada coerente com o tempo informado. ANAMNESE DO USUÁRIO idade: 21 sexo: masculino peso atual em kg: 82 experiencia com treino: avançada quanto tempo você treina com regularidade: 5 anos quantos dias por semana você tem disponivel: 4 quanto tempo por treino você tem disponivel: 1h30 qual sao seus objetivos com o treino: hipertrofia tem algum objetivo especifico: ficar parecido com o david laid você possui alguma lesão ou limitação física: dor na panturrilha você possui alguma condição médica que devemos considerar: aprisionamento tipo V na panturrilha existe algum exercicio que não gosta ou não consegue realizar: Elevação Pélvica quais equipamentos você tem acesso para treinar: Todos equipamentos especificos você tem na sua academia: Supino Inclinado Artiuclado, Pendulo
"""
)

# Mostra no console
print("✅ Requisição concluída! Salvando resposta em 'response_gpt.json'...")

# Converte o objeto response em dicionário JSON serializável
response_dict = response.model_dump()

# Salva em arquivo JSON
with open("response_gpt.json", "w", encoding="utf-8") as f:
    json.dump(response_dict, f, ensure_ascii=False, indent=2)

print("💾 Arquivo 'response_gpt.json' criado com sucesso!")
