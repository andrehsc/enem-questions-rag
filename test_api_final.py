#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json

def test_api():
    base_url = "http://localhost:8001"
    
    print("Testando ENEM Questions RAG API via Docker...")
    print("=" * 50)
    
    # Test 1: Health check
    print("\n1. HEALTH CHECK")
    try:
        response = requests.get(f"{base_url}/health", timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   DB Connected: {data.get('database_connected')}")
            print(f"   Total Questions: {data.get('total_questions')}")
        else:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"   Failed: {e}")
    
    # Test 2: Stats
    print("\n2. ESTATISTICAS")
    try:
        response = requests.get(f"{base_url}/stats", timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Questoes: {data.get('total_questions')}")
            print(f"   Alternativas: {data.get('total_alternatives')}")
            print(f"   Gabaritos: {data.get('total_answer_keys')}")
            years = data.get('questions_by_year', {})
            print(f"   Anos: {list(years.keys())}")
            subjects = data.get('questions_by_subject', {})
            print(f"   Materias: {list(subjects.keys())}")
        else:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"   Failed: {e}")
    
    # Test 3: List questions
    print("\n3. LISTAR QUESTOES")
    try:
        response = requests.get(f"{base_url}/questions?page=1&size=3", timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Total: {data.get('total')}")
            print(f"   Pagina: {data.get('page')}")
            print(f"   Itens: {len(data.get('items', []))}")
        else:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"   Failed: {e}")
    
    # Test 4: Get specific question
    print("\n4. QUESTAO ESPECIFICA")
    try:
        response = requests.get(f"{base_url}/questions/1", timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   ID: {data.get('id')}")
            print(f"   Ano: {data.get('exam_year')}")
            answer_key = data.get('answer_key', {})
            print(f"   Materia: {answer_key.get('subject')}")
            print(f"   Resposta: {answer_key.get('correct_answer')}")
            print(f"   Alternativas: {len(data.get('alternatives', []))}")
        else:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"   Failed: {e}")
    
    print("\n" + "=" * 50)
    print("TESTE CONCLUIDO!")
    print(f"API: {base_url}")
    print(f"Docs: {base_url}/docs")
    print(f"Home: {base_url}/")
    print("=" * 50)

if __name__ == "__main__":
    test_api()
