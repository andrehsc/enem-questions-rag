#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Documentação adicional para a API ENEM Questions RAG
Contém exemplos e schemas customizados para o Swagger
"""

# Exemplos de responses para documentação
EXAMPLES = {
    "question_example": {
        "id": 1,
        "exam_year": 2023,
        "exam_type": "ENEM",
        "number": 45,
        "statement": "O Brasil é um país de dimensões continentais, caracterizado por uma grande diversidade de paisagens naturais e uma rica biodiversidade. Considerando as características do território brasileiro, analise as afirmações a seguir sobre os biomas brasileiros.",
        "alternatives": [
            {
                "id": 1,
                "letter": "A",
                "text": "A Amazônia é o maior bioma brasileiro em extensão territorial.",
                "order": 1
            },
            {
                "id": 2,
                "letter": "B", 
                "text": "O Cerrado é considerado a savana mais biodiversa do mundo.",
                "order": 2
            },
            {
                "id": 3,
                "letter": "C",
                "text": "A Mata Atlântica é o bioma mais preservado do Brasil.",
                "order": 3
            },
            {
                "id": 4,
                "letter": "D",
                "text": "O Pantanal é a maior planície alagável do planeta.",
                "order": 4
            },
            {
                "id": 5,
                "letter": "E",
                "text": "A Caatinga ocupa exclusivamente a região Sul do Brasil.",
                "order": 5
            }
        ],
        "answer_key": {
            "id": 1,
            "correct_answer": "B",
            "subject": "Geografia",
            "language_option": None
        },
        "metadata": {
            "exam_year": 2023,
            "exam_type": "ENEM",
            "application_type": "PRIMEIRO DIA",
            "language": "PORTUGUES"
        }
    },
    
    "questions_list_example": {
        "items": [
            {
                "id": 1,
                "exam_year": 2023,
                "exam_type": "ENEM",
                "number": 45,
                "subject": "Geografia",
                "correct_answer": "B",
                "statement_preview": "O Brasil é um país de dimensões continentais, caracterizado por uma grande diversidade de paisagens naturais..."
            },
            {
                "id": 2,
                "exam_year": 2023,
                "exam_type": "ENEM", 
                "number": 46,
                "subject": "História",
                "correct_answer": "A",
                "statement_preview": "A Revolução Industrial do século XVIII trouxe profundas transformações nas sociedades europeias..."
            }
        ],
        "total": 2452,
        "page": 1,
        "size": 2, 
        "pages": 1226,
        "has_next": True,
        "has_prev": False
    },
    
    "stats_example": {
        "total_questions": 2452,
        "total_alternatives": 12260,
        "total_answer_keys": 4308,
        "years_available": [2009, 2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023],
        "exam_types": ["ENEM"],
        "subjects": ["Ciências da Natureza", "Ciências Humanas", "Linguagens", "Matemática", "Geografia", "História", "Filosofia", "Sociologia", "Física", "Química", "Biologia"]
    }
}

# Tags para organização da documentação
TAGS_METADATA = [
    {
        "name": "questions",
        "description": "Operações relacionadas às questões do ENEM. Inclui listagem, busca e recuperação de questões específicas.",
    },
    {
        "name": "search",
        "description": "Busca textual avançada nas questões. Suporte a busca em português com acentos e termos compostos.",
    },
    {
        "name": "statistics", 
        "description": "Estatísticas e informações agregadas sobre o conjunto de dados disponível.",
    },
    {
        "name": "health",
        "description": "Endpoints para monitoramento da saúde da API e conectividade com banco de dados.",
    },
]

# Configurações adicionais do OpenAPI
OPENAPI_EXTRA = {
    "info": {
        "termsOfService": "https://enemrag.com/terms/",
        "contact": {
            "name": "Equipe ENEM RAG",
            "url": "https://enemrag.com/contact/",
            "email": "api@enemrag.com"
        },
        "license": {
            "name": "MIT License",
            "url": "https://opensource.org/licenses/MIT"
        }
    },
    "servers": [
        {
            "url": "http://localhost:8000",
            "description": "Servidor de desenvolvimento"
        },
        {
            "url": "https://api.enemrag.com",
            "description": "Servidor de produção"
        }
    ],
    "externalDocs": {
        "description": "Documentação completa",
        "url": "https://docs.enemrag.com"
    }
}
