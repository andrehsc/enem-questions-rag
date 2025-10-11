"""
Pipeline automatizado para ingestão de questões do ENEM no PostgreSQL.

Este módulo implementa um sistema completo para:
- Download de provas do ENEM do site do INEP
- Parsing e extração de questões, alternativas e gabaritos
- Armazenamento estruturado no PostgreSQL
- Preparação para uso com RAG e Semantic Kernel

Compatível com TeachersHub para integração futura.
"""

__version__ = "0.1.0"
__author__ = "Andre"