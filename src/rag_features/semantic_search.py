#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de busca semântica para questões do ENEM usando embeddings
SOLID Architecture - Single Responsibility Principle

Suporta:
- ChromaDB: Armazenamento vetorial otimizado (preferido)
- SQLite: Fallback para desenvolvimento/teste
- Mock: Para testes unitários
"""

import numpy as np
import asyncio
import hashlib
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod
import logging
import os
import json
import sqlite3
from datetime import datetime
from dataclasses import dataclass

from sqlalchemy import create_engine, text as sa_text
from openai import OpenAI
import redis

logger = logging.getLogger(__name__)

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.warning("sentence-transformers não disponível, usando implementação mock")

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
    logger.info("ChromaDB disponível - usando armazenamento vetorial otimizado")
except ImportError:
    CHROMADB_AVAILABLE = False
    logger.warning("chromadb não disponível, usando SQLite como fallback")

# Interface para abstração da busca semântica
class SemanticSearchInterface(ABC):
    """Interface para sistemas de busca semântica"""
    
    @abstractmethod
    async def search_questions(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Busca questões por similaridade semântica"""
        pass
    
    @abstractmethod
    async def add_questions_to_index(self, questions: List[Dict[str, Any]]) -> bool:
        """Adiciona questões ao índice de busca"""
        pass

@dataclass
class QuestionEmbedding:
    """Dados de embedding de uma questão"""
    id: str
    text: str
    subject: str
    year: int
    embedding: List[float]
    metadata: Dict[str, Any]

class MockEmbeddingModel:
    """Mock para modelo de embeddings quando sentence-transformers não está disponível"""
    
    def __init__(self, dimension=384):
        self.dimension = dimension
    
    def encode(self, texts: List[str]) -> np.ndarray:
        """Gera embeddings mock baseados no hash do texto"""
        embeddings = []
        for text in texts:
            # Gerar embedding determinístico baseado no hash do texto
            hash_val = hash(text)
            embedding = []
            for i in range(self.dimension):
                embedding.append(((hash_val + i) % 1000) / 1000.0)
            embeddings.append(embedding)
        return np.array(embeddings)

class ChromaDBSemanticSearch(SemanticSearchInterface):
    """Sistema de busca semântica usando ChromaDB para armazenamento vetorial otimizado"""
    
    def __init__(self, 
                 model_name: str = "neuralmind/bert-base-portuguese-cased",
                 collection_name: str = "enem_questions",
                 persist_directory: str = "./data/chromadb"):
        self.model_name = model_name
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        self.model = None
        self.client = None
        self.collection = None
        self._initialized = False
        
    async def initialize(self):
        """Inicializa ChromaDB e modelo de embeddings"""
        if self._initialized:
            return
            
        try:
            logger.info("Inicializando ChromaDB Semantic Search...")
            
            # Configurar ChromaDB
            os.makedirs(self.persist_directory, exist_ok=True)
            self.client = chromadb.PersistentClient(path=self.persist_directory)
            
            # Criar ou obter collection
            try:
                self.collection = self.client.get_collection(name=self.collection_name)
                logger.info(f"Collection existente carregada: {self.collection_name}")
            except:
                self.collection = self.client.create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine"}  # Usar cosine similarity
                )
                logger.info(f"Nova collection criada: {self.collection_name}")
            
            # Carregar modelo de embeddings
            logger.info(f"Carregando modelo: {self.model_name}")
            if SENTENCE_TRANSFORMERS_AVAILABLE:
                self.model = SentenceTransformer(self.model_name)
                logger.info("Modelo de embeddings carregado com sucesso")
            else:
                raise ImportError("sentence-transformers é obrigatório para ChromaDB")
                
            self._initialized = True
            logger.info("ChromaDB Semantic Search inicializado com sucesso")
            
        except Exception as e:
            logger.error(f"Erro ao inicializar ChromaDB: {e}")
            raise
    
    async def search_questions(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Busca questões por similaridade semântica usando ChromaDB"""
        if not self._initialized:
            await self.initialize()
        
        try:
            # Gerar embedding da query
            query_embedding = self.model.encode([query])
            
            # Buscar no ChromaDB
            results = self.collection.query(
                query_embeddings=query_embedding.tolist(),
                n_results=limit,
                include=['metadatas', 'documents', 'distances']
            )
            
            # Formatear resultados
            formatted_results = []
            for i in range(len(results['ids'][0])):
                result = {
                    'id': results['ids'][0][i],
                    'text': results['documents'][0][i],
                    'similarity': 1.0 - results['distances'][0][i],  # ChromaDB retorna distância
                    'metadata': results['metadatas'][0][i]
                }
                formatted_results.append(result)
            
            logger.info(f"Encontradas {len(formatted_results)} questões similares")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Erro na busca semântica: {e}")
            return []
    
    async def add_questions_to_index(self, questions: List[Dict[str, Any]]) -> bool:
        """Adiciona questões ao índice ChromaDB"""
        if not self._initialized:
            await self.initialize()
        
        try:
            # Preparar dados para inserção
            documents = []
            metadatas = []
            ids = []
            
            for question in questions:
                documents.append(question.get('text', ''))
                metadatas.append({
                    'subject': question.get('subject', ''),
                    'year': question.get('year', 0),
                    'difficulty': question.get('difficulty', 'unknown'),
                    'question_type': question.get('question_type', 'unknown')
                })
                ids.append(str(question.get('id', question.get('question_id', ''))))
            
            # Gerar embeddings
            logger.info(f"Gerando embeddings para {len(documents)} questões...")
            embeddings = self.model.encode(documents)
            
            # Adicionar ao ChromaDB
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids,
                embeddings=embeddings.tolist()
            )
            
            logger.info(f"Indexadas {len(questions)} questões no ChromaDB")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao adicionar questões ao índice: {e}")
            return False

class EnemSemanticSearch(SemanticSearchInterface):
    """Sistema de busca semântica para questões do ENEM - Implementação com SQLite fallback"""
    
    def __init__(self, model_name="neuralmind/bert-base-portuguese-cased", use_mock=False):
        """
        Inicializa o sistema de busca semântica
        
        Args:
            model_name: Nome do modelo de embeddings
            use_mock: Se True, usa implementação mock para testes
        """
        self.model_name = model_name
        self.use_mock = use_mock or not SENTENCE_TRANSFORMERS_AVAILABLE
        self.model = None
        self.db_path = "./data/semantic_search.db"
        self._initialized = False
        self.questions: List[QuestionEmbedding] = []
        
    async def initialize(self):
        """Inicializa componentes do sistema de busca"""
        try:
            # Carregar modelo de embeddings
            if self.use_mock:
                logger.info("Inicializando com modelo mock para testes")
                self.model = MockEmbeddingModel()
            else:
                logger.info(f"Carregando modelo: {self.model_name}")
                if SENTENCE_TRANSFORMERS_AVAILABLE:
                    self.model = SentenceTransformer(self.model_name)
                else:
                    logger.warning("Usando modelo mock - instale sentence-transformers para produção")
                    self.model = MockEmbeddingModel()
            
            # Configurar persistência
            os.makedirs("./data", exist_ok=True)
            await self._initialize_storage()
            
            self._initialized = True
            logger.info("Sistema de busca semântica inicializado com sucesso")
            
        except Exception as e:
            logger.error(f"Erro ao inicializar busca semântica: {e}")
            raise
        
    async def _initialize_storage(self):
        """Inicializa sistema de armazenamento"""
        try:
            # Criar tabela SQLite se não existir
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS question_embeddings (
                    id TEXT PRIMARY KEY,
                    text TEXT NOT NULL,
                    subject TEXT,
                    year INTEGER,
                    embedding TEXT NOT NULL,
                    metadata TEXT,
                    created_at TEXT
                )
            """)
            conn.commit()
            conn.close()
            logger.info("Armazenamento de embeddings inicializado")
        except Exception as e:
            logger.error(f"Erro ao inicializar armazenamento: {e}")
            raise
    
    async def search_questions(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Busca questões por similaridade semântica
        
        Args:
            query: Texto de busca
            limit: Número máximo de resultados
            
        Returns:
            Lista de questões ordenadas por similaridade
        """
        if not self._initialized:
            await self.initialize()
            
        try:
            # Gerar embedding da query
            query_embedding = self.model.encode([query])[0]
            
            # Carregar embeddings do banco
            conn = sqlite3.connect(self.db_path)
            cursor = conn.execute("""
                SELECT id, text, subject, year, embedding, metadata 
                FROM question_embeddings
            """)
            
            similarities = []
            for row in cursor:
                question_id, text, subject, year, embedding_json, metadata_json = row
                embedding = json.loads(embedding_json)
                
                # Calcular similaridade coseno
                similarity = self._cosine_similarity(query_embedding, embedding)
                
                similarities.append({
                    'id': question_id,
                    'question_text': text,
                    'similarity_score': similarity,
                    'metadata': {
                        'subject': subject,
                        'year': year,
                        **(json.loads(metadata_json) if metadata_json else {})
                    }
                })
            
            conn.close()
            
            # Ordenar por similaridade e limitar resultados
            similarities.sort(key=lambda x: x['similarity_score'], reverse=True)
            results = similarities[:limit]
            
            logger.info(f"Busca semântica retornou {len(results)} resultados")
            return results
            
        except Exception as e:
            logger.error(f"Erro na busca semântica: {e}")
            return []
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calcula similaridade coseno entre dois vetores"""
        try:
            vec1_np = np.array(vec1)
            vec2_np = np.array(vec2)
            
            dot_product = np.dot(vec1_np, vec2_np)
            norm1 = np.linalg.norm(vec1_np)
            norm2 = np.linalg.norm(vec2_np)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            return float(dot_product / (norm1 * norm2))
        except Exception:
            return 0.0
    
    async def add_questions_to_index(self, questions: List[Dict[str, Any]]) -> bool:
        """
        Adiciona questões ao índice de busca
        
        Args:
            questions: Lista de questões com campos id, statement, subject, year
            
        Returns:
            True se sucesso, False caso contrário
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            conn = sqlite3.connect(self.db_path)
            
            for question in questions:
                # Preparar texto para embedding
                text = question.get('statement', '')
                if question.get('subject'):
                    text = f"Matéria: {question['subject']}. {text}"
                
                # Gerar embedding
                embedding = self.model.encode([text])[0].tolist()
                
                # Preparar metadados
                metadata = {
                    'indexed_at': datetime.now().isoformat(),
                    'has_images': question.get('has_images', False),
                    'difficulty': question.get('difficulty', 'medium')
                }
                
                # Salvar no banco
                conn.execute("""
                    INSERT OR REPLACE INTO question_embeddings 
                    (id, text, subject, year, embedding, metadata, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(question['id']),
                    text,
                    question.get('subject', ''),
                    question.get('year', 0),
                    json.dumps(embedding),
                    json.dumps(metadata),
                    datetime.now().isoformat()
                ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Indexadas {len(questions)} questões com sucesso")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao indexar questões: {e}")
            return False
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """
        Retorna estatísticas da coleção de questões
        
        Returns:
            Dicionário com estatísticas da coleção
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.execute("SELECT COUNT(*) FROM question_embeddings")
            count = cursor.fetchone()[0]
            conn.close()
            
            return {
                'total_questions': count,
                'model_name': self.model_name,
                'storage_type': 'sqlite' if self.use_mock else 'sqlite_with_real_embeddings',
                'status': 'active' if count > 0 else 'empty',
                'db_path': self.db_path
            }
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas: {e}")
            return {'status': 'error', 'message': str(e)}
    
    async def clear_collection(self):
        """Remove todas as questões da coleção"""
        if not self._initialized:
            await self.initialize()
        
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("DELETE FROM question_embeddings")
            conn.commit()
            conn.close()
            logger.info("Coleção limpa com sucesso")
            
        except Exception as e:
            logger.error(f"Erro ao limpar coleção: {e}")
            
    def is_initialized(self) -> bool:
        """Verifica se o sistema está inicializado"""
        return self._initialized
    
    async def search_by_subject(self, query: str, subject: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Busca questões por similaridade semântica filtrada por matéria
        
        Args:
            query: Texto de busca
            subject: Matéria para filtrar
            limit: Número máximo de resultados
            
        Returns:
            Lista de questões da matéria ordenadas por similaridade
        """
        all_results = await self.search_questions(query, limit * 2)  # Buscar mais para filtrar
        filtered_results = [r for r in all_results if r['metadata'].get('subject', '').lower() == subject.lower()]
        return filtered_results[:limit]

class PgVectorSearch(SemanticSearchInterface):
    """Busca semântica usando pgvector no PostgreSQL existente"""

    EMBEDDING_MODEL = "text-embedding-3-small"

    def __init__(
        self,
        database_url: str,
        openai_api_key: str,
        redis_url: str = "redis://localhost:6380/1",
    ) -> None:
        self._engine = create_engine(database_url)
        self._openai = OpenAI(api_key=openai_api_key)
        try:
            self._redis = redis.from_url(redis_url)
        except Exception:
            self._redis = None
            logger.warning("Redis indisponível — cache de query embeddings desativado")

    def _get_query_embedding(self, query: str) -> List[float]:
        """Gera embedding via OpenAI com cache Redis (TTL 1h)."""
        cache_key = f"query_emb:{hashlib.sha256(query.encode()).hexdigest()}"

        if self._redis:
            cached = self._redis.get(cache_key)
            if cached:
                try:
                    return json.loads(cached)
                except (json.JSONDecodeError, ValueError):
                    pass  # entrada corrompida — regenera via OpenAI

        response = self._openai.embeddings.create(
            model=self.EMBEDDING_MODEL,
            input=query,
        )
        if not response.data:
            raise ValueError("OpenAI retornou lista de embeddings vazia")
        embedding = response.data[0].embedding

        if self._redis:
            self._redis.setex(cache_key, 3600, json.dumps(embedding))

        return embedding

    async def search_questions(
        self,
        query: str,
        limit: int = 10,
        year: Optional[int] = None,
        subject: Optional[str] = None,
        chunk_type: str = "full",
        search_mode: str = "hybrid",
    ) -> List[Dict[str, Any]]:
        if search_mode == "semantic":
            return await self._search_semantic(query, limit, year, subject, chunk_type)
        elif search_mode == "text":
            return await self._search_text(query, limit, year, subject, chunk_type)
        else:
            return await self._search_hybrid(query, limit, year, subject, chunk_type)

    async def _search_semantic(
        self,
        query: str,
        limit: int = 10,
        year: Optional[int] = None,
        subject: Optional[str] = None,
        chunk_type: str = "full",
    ) -> List[Dict[str, Any]]:
        embedding = await asyncio.to_thread(self._get_query_embedding, query)

        subject_filter = "AND q.subject = :subject" if subject else ""
        year_filter = "AND em.year = :year" if year else ""

        sql = sa_text(f"""
            SELECT
                q.id AS question_id,
                q.question_text,
                q.subject,
                em.year,
                qc.id AS chunk_id,
                qc.chunk_type,
                qc.content AS chunk_content,
                1 - (qc.embedding <=> CAST(:embedding AS vector)) AS similarity_score
            FROM enem_questions.question_chunks qc
            JOIN enem_questions.questions q ON q.id = qc.question_id
            LEFT JOIN enem_questions.exam_metadata em ON em.id = q.exam_metadata_id
            WHERE qc.chunk_type = :chunk_type
              AND qc.embedding IS NOT NULL
              {subject_filter}
              {year_filter}
            ORDER BY qc.embedding <=> CAST(:embedding AS vector)
            LIMIT :limit_val
        """)

        params: Dict[str, Any] = {
            "embedding": str(embedding),
            "limit_val": limit,
            "chunk_type": chunk_type,
        }
        if subject:
            params["subject"] = subject
        if year:
            params["year"] = year

        def _run_query() -> list:
            with self._engine.connect() as conn:
                result = conn.execute(sql, params)
                return result.fetchall()

        rows = await asyncio.to_thread(_run_query)

        seen: Dict[int, Dict[str, Any]] = {}
        for row in rows:
            r = row._mapping
            qid = r["question_id"]
            if qid not in seen:
                seen[qid] = {
                    "question_id": qid,
                    "chunk_id": str(r["chunk_id"]),
                    "full_text": r["chunk_content"],
                    "subject": r["subject"],
                    "year": r["year"],
                    "similarity_score": r["similarity_score"],
                }

        return list(seen.values())

    async def _search_text(
        self,
        query: str,
        limit: int = 10,
        year: Optional[int] = None,
        subject: Optional[str] = None,
        chunk_type: str = "full",
    ) -> List[Dict[str, Any]]:
        subject_filter = "AND q.subject = :subject" if subject else ""
        year_filter = "AND em.year = :year" if year else ""

        sql = sa_text(f"""
            SELECT
                q.id AS question_id,
                q.question_text,
                q.subject,
                em.year,
                qc.id AS chunk_id,
                qc.chunk_type,
                qc.content AS chunk_content,
                ts_rank(qc.tsv_content, plainto_tsquery('portuguese_unaccent', :query)) AS text_score
            FROM enem_questions.question_chunks qc
            JOIN enem_questions.questions q ON q.id = qc.question_id
            LEFT JOIN enem_questions.exam_metadata em ON em.id = q.exam_metadata_id
            WHERE qc.chunk_type = :chunk_type
              AND qc.tsv_content @@ plainto_tsquery('portuguese_unaccent', :query)
              {subject_filter}
              {year_filter}
            ORDER BY text_score DESC
            LIMIT :limit_val
        """)

        params: Dict[str, Any] = {
            "query": query,
            "limit_val": limit,
            "chunk_type": chunk_type,
        }
        if subject:
            params["subject"] = subject
        if year:
            params["year"] = year

        def _run_query() -> list:
            with self._engine.connect() as conn:
                result = conn.execute(sql, params)
                return result.fetchall()

        rows = await asyncio.to_thread(_run_query)

        seen: Dict[int, Dict[str, Any]] = {}
        for row in rows:
            r = row._mapping
            qid = r["question_id"]
            if qid not in seen:
                seen[qid] = {
                    "question_id": qid,
                    "chunk_id": str(r["chunk_id"]),
                    "full_text": r["chunk_content"],
                    "subject": r["subject"],
                    "year": r["year"],
                    "similarity_score": min(float(r["text_score"]), 1.0),
                }

        return list(seen.values())

    async def _search_hybrid(
        self,
        query: str,
        limit: int = 10,
        year: Optional[int] = None,
        subject: Optional[str] = None,
        chunk_type: str = "full",
    ) -> List[Dict[str, Any]]:
        K = 60
        rrf_pool = limit * 3

        vector_results = await self._search_semantic(
            query, limit=rrf_pool, year=year, subject=subject, chunk_type=chunk_type,
        )
        text_results = await self._search_text(
            query, limit=rrf_pool, year=year, subject=subject, chunk_type=chunk_type,
        )

        # If text search returns nothing, fall back to semantic-only
        if not text_results:
            return vector_results[:limit]

        # If semantic search returns nothing, fall back to text-only
        if not vector_results:
            return text_results[:limit]

        # Assign ranks (1-indexed)
        vector_ranks = {r["question_id"]: i + 1 for i, r in enumerate(vector_results)}
        text_ranks = {r["question_id"]: i + 1 for i, r in enumerate(text_results)}

        # Build result map from both sources
        result_map: Dict[Any, Dict[str, Any]] = {}
        for r in vector_results:
            result_map[r["question_id"]] = r
        for r in text_results:
            if r["question_id"] not in result_map:
                result_map[r["question_id"]] = r

        # Compute RRF scores
        all_ids = set(vector_ranks) | set(text_ranks)
        max_rrf = 1 / (K + 1) + 1 / (K + 1)  # theoretical max (rank 1 in both)
        rrf_scored = []
        for qid in all_ids:
            v_rank = vector_ranks.get(qid, rrf_pool + 1)
            t_rank = text_ranks.get(qid, rrf_pool + 1)
            rrf_score = 1 / (K + v_rank) + 1 / (K + t_rank)
            normalized = rrf_score / max_rrf  # normalize to 0-1
            entry = result_map[qid].copy()
            entry["similarity_score"] = round(normalized, 6)
            rrf_scored.append(entry)

        rrf_scored.sort(key=lambda x: x["similarity_score"], reverse=True)
        return rrf_scored[:limit]

    async def add_questions_to_index(self, questions: List[Dict[str, Any]]) -> bool:
        raise NotImplementedError(
            "Indexação feita pelo IngestionPipeline. "
            "Use: python -m src.enem_ingestion.ingestion_pipeline"
        )


def create_semantic_search() -> SemanticSearchInterface:
    """
    Factory function para criar instância de busca semântica.
    VECTOR_STORE env var seleciona implementação:
      - pgvector (default): usa PostgreSQL + pgvector
      - chromadb: usa ChromaDB (requer chromadb + sentence-transformers)
      - sqlite: fallback SQLite
    """
    vector_store = os.getenv("VECTOR_STORE", "pgvector")

    if vector_store == "pgvector":
        logger.info("Criando instância PgVectorSearch (pgvector)")
        return PgVectorSearch(
            database_url=os.getenv(
                "DATABASE_URL",
                "postgresql://postgres:postgres123@localhost:5433/teachershub_enem",
            ),
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6380/1"),
        )

    if vector_store == "chromadb" and CHROMADB_AVAILABLE and SENTENCE_TRANSFORMERS_AVAILABLE:
        logger.info("Criando instância ChromaDB - performance otimizada")
        return ChromaDBSemanticSearch()

    logger.info("Criando instância SQLite fallback")
    return EnemSemanticSearch(use_mock=not SENTENCE_TRANSFORMERS_AVAILABLE)

# Instância global lazy — evita conexão ao banco durante import
_semantic_search_instance = None


def get_semantic_search() -> SemanticSearchInterface:
    """Retorna instância global (lazy singleton)."""
    global _semantic_search_instance
    if _semantic_search_instance is None:
        _semantic_search_instance = create_semantic_search()
    return _semantic_search_instance


# Backwards-compat alias
semantic_search_instance = None

# Script de teste para execução direta
async def test_rag_system():
    """Testa o sistema RAG com dados de exemplo"""
    print("=== TESTE DO SISTEMA RAG ===")
    
    # Criar instância de busca
    search = create_semantic_search()
    await search.initialize()
    
    # Dados de teste (questões do ENEM exemplo)
    sample_questions = [
        {
            "id": "enem_2023_001",
            "text": "A energia solar é uma fonte renovável que pode ser convertida em eletricidade através de painéis fotovoltaicos. Qual é o principal componente responsável por esta conversão?",
            "subject": "fisica",
            "year": 2023,
            "difficulty": "medio"
        },
        {
            "id": "enem_2023_002", 
            "text": "O aquecimento global é causado principalmente pelo aumento de gases do efeito estufa na atmosfera. Quais são as principais fontes desses gases?",
            "subject": "geografia",
            "year": 2023,
            "difficulty": "facil"
        },
        {
            "id": "enem_2022_001",
            "text": "A fotossíntese é o processo pelo qual as plantas convertem energia luminosa em energia química. Qual é a equação química que representa este processo?",
            "subject": "biologia", 
            "year": 2022,
            "difficulty": "medio"
        }
    ]
    
    # Indexar questões
    print(f"Indexando {len(sample_questions)} questões...")
    success = await search.add_questions_to_index(sample_questions)
    print(f"Indexação: {'✅ Sucesso' if success else '❌ Falha'}")
    
    # Teste de busca
    test_queries = [
        "energia renovável",
        "gases do efeito estufa", 
        "processo de fotossíntese",
        "física moderna"
    ]
    
    for query in test_queries:
        print(f"\n🔍 Buscando: '{query}'")
        results = await search.search_questions(query, limit=2)
        
        for i, result in enumerate(results, 1):
            print(f"  {i}. [ID: {result['id']}] Similaridade: {result['similarity']:.3f}")
            print(f"     Matéria: {result['metadata'].get('subject', 'N/A')}")
            print(f"     Ano: {result['metadata'].get('year', 'N/A')}")
            print(f"     Texto: {result['text'][:100]}...")
    
    print("\n✅ Teste concluído!")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_rag_system())