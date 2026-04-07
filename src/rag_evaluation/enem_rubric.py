"""ENEM-specific G-Eval rubric for question generation evaluation.

Defines the rubric and factory for creating GEval metrics
that assess generated ENEM questions on pedagogical quality.
"""

ENEM_RUBRIC = """Avalie a questão ENEM gerada com base nos critérios abaixo.

Critérios de avaliação:
1. Formato ENEM: A questão tem texto-base/contexto quando necessário,
   enunciado com comando claro, e exatamente 5 alternativas (A-E)?
2. Qualidade pedagógica: O enunciado é claro e avalia competência
   cognitiva? As alternativas são plausíveis e bem redigidas?
3. Fidelidade ao conteúdo: A questão reflete com precisão o tema
   e informações do contexto fornecido?
4. Distratores: As alternativas incorretas são plausíveis mas
   claramente distinguíveis da resposta correta?

Escala de avaliação:
1: Questão irrelevante ou mal formatada — falta alternativas, enunciado confuso, ou sem relação com o tema
2: Questão parcialmente adequada — tem estrutura básica mas falta elementos ENEM (distratores fracos, enunciado vago)
3: Questão adequada — segue formato ENEM, conteúdo correto, mas poderia ter distratores melhores ou enunciado mais preciso
4: Questão excelente — padrão ENEM completo, pedagogicamente sólida, distratores plausíveis, enunciado claro com comando de ação"""


def create_enem_geval(eval_llm):
    """Create G-Eval metric with ENEM rubric.

    Args:
        eval_llm: DeepEvalBaseLLM-compatible instance (Ollama, GPT-4o, etc.)

    Returns:
        GEval metric configured with ENEM rubric.
    """
    from deepeval.metrics import GEval
    from deepeval.test_case import LLMTestCaseParams

    return GEval(
        name="ENEM Question Quality",
        criteria=ENEM_RUBRIC,
        evaluation_params=[
            LLMTestCaseParams.INPUT,
            LLMTestCaseParams.ACTUAL_OUTPUT,
        ],
        threshold=0.5,  # Minimum acceptable: 2/4 = 0.5
        model=eval_llm,
    )
