#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de busca semântica para questões do ENEM usando embeddings
"""

import numpy as np
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings
import asyncio
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class EnemSemanticSearch:
    """Sistema de busca semântica para questões do ENEM"""
    
    def __init__(self, model_name="neuralmind/bert-base-portuguese-cased"):
        """
        Inicializa o sistema de busca semântica
        
        Args:
            model_name: Nome do modelo de embeddings (BERTimbau para português)
        """
        self.model = SentenceTransformer(model_name)
        self.chroma_client = chromadb.Client(Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory="./data/chroma_db"
        ))
        self.collection = None
        
    async def initialize_collection(self):
        """Inicializa a coleção ChromaDB"""
        try:
            self.collection = self.chroma_client.create_collection(
                name="enem_questions",
                metadata={"hnsw:space": "cosine"}
            )
            logger.info("Coleção ChromaDB inicializada")
        except Exception as e:
            # Coleção já existe
            self.collection = self.chroma_client.get_collection("enem_questions")
            logger.info("Coleção ChromaDB carregada")
    
    async def add_questions(self, questions: List[Dict[str, Any]]):
        """
        Adiciona questões à base de conhecimento
        
        Args:
            questions: Lista de questões com text, id, metadata
        """
        if not self.collection:
            await self.initialize_collection()
        
        texts = [q["text"] for q in questions]
        ids = [str(q["id"]) for q in questions]
        metadatas = [q.get("metadata", {}) for q in questions]
        
        # Gerar embeddings
        embeddings = self.model.encode(texts).tolist()
        
        # Adicionar à coleção
        self.collection.add(
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
            ids=ids
        )
        
        logger.info(f"Adicionadas {len(questions)} questões à base semântica")
    
    async def semantic_search(
        self, 
        query: str, 
        n_results: int = 10,
        filters: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Busca semântica por questões
        
        Args:
            query: Consulta em linguagem natural
            n_results: Número de resultados desejados
            filters: Filtros de metadata (ano, matéria, etc.)
        
        Returns:
            Lista de questões rankeadas por similaridade
        """
        if not self.collection:
            await self.initialize_collection()
        
        # Gerar embedding da consulta
        query_embedding = self.model.encode([query]).tolist()[0]
        
        # Buscar questões similares
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=filters
        )
        
        # Formatar resultados
        formatted_results = []
        for i in range(len(results['ids'][0])):
            formatted_results.append({
                'id': results['ids'][0][i],
                'text': results['documents'][0][i],
                'metadata': results['metadatas'][0][i],
                'similarity_score': 1 - results['distances'][0][i],  # Converter distância para similaridade
            })
        
        return formatted_results
    
    async def get_similar_questions(
        self, 
        question_id: str, 
        n_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Encontra questões similares a uma questão específica
        
        Args:
            question_id: ID da questão de referência
            n_results: Número de questões similares
        
        Returns:
            Lista de questões similares
        """
        if not self.collection:
            await self.initialize_collection()
        
        # Buscar a questão de referência
        reference = self.collection.get(ids=[question_id])
        if not reference['documents']:
            return []
        
        reference_text = reference['documents'][0]
        
        # Buscar questões similares
        return await self.semantic_search(
            query=reference_text,
            n_results=n_results + 1  # +1 para excluir a própria questão
        )
    
    def generate_embeddings_batch(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        Gera embeddings em lotes para eficiência
        
        Args:
            texts: Lista de textos
            batch_size: Tamanho do lote
        
        Returns:
            Lista de embeddings
        """
        embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_embeddings = self.model.encode(batch)
            embeddings.extend(batch_embeddings.tolist())
        
        return embeddings
    
    async def update_question_embedding(self, question_id: str, new_text: str):
        """Atualiza embedding de uma questão específica"""
        if not self.collection:
            await self.initialize_collection()
        
        new_embedding = self.model.encode([new_text]).tolist()[0]
        
        self.collection.update(
            ids=[question_id],
            embeddings=[new_embedding],
            documents=[new_text]
        )
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas da coleção"""
        if not self.collection:
            return {"error": "Collection not initialized"}
        
        count = self.collection.count()
        return {
            "total_questions": count,
            "model_name": self.model.get_sentence_embedding_dimension(),
            "embedding_dimension": self.model.get_sentence_embedding_dimension()
        }

# Instância global
semantic_search = EnemSemanticSearch()
