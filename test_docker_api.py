#!/usr/bin/env python3

import requests
import json
import time

def test_dockerized_api():
    """Testa a API rodando no Docker"""
    base_url = "http://localhost:8001"
    
    print("Ì∞≥ Testando ENEM Questions RAG API via Docker...")
    print("=" * 60)
    
    # Test 1: Health check com banco real
    print("\n1Ô∏è‚É£ HEALTH CHECK")
    try:
        response = requests.get(f"{base_url}/health", timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Ì¥ó DB Connected: {data.get('database_connected')}")
            print(f"   Ì≥ä Total Questions: {data.get('total_questions')}")
            print(f"   ‚è∞ Timestamp: {data.get('timestamp')}")
        else:
            print(f"   ‚ùå Error: {response.text}")
    except Exception as e:
        print(f"   ‚ùå Failed: {e}")
    
    # Test 2: Estat√≠sticas completas
    print("\n2Ô∏è‚É£ ESTAT√çSTICAS")
    try:
        response = requests.get(f"{base_url}/stats", timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Ì≥ö Quest√µes: {data.get('total_questions')}")
            print(f"   Ì¥§ Alternativas: {data.get('total_alternatives')}")
            print(f"   ‚úÖ Gabaritos: {data.get('total_answer_keys')}")
            print(f"   Ì≥Ö Anos: {data.get('questions_by_year', {})}")
            print(f"   Ì≥ñ Mat√©rias: {list(data.get('questions_by_subject', {}).keys())}")
        else:
            print(f"   ‚ùå Error: {response.text}")
    except Exception as e:
        print(f"   ‚ùå Failed: {e}")
    
    # Test 3: Listar quest√µes paginadas
    print("\n3Ô∏è‚É£ LISTAR QUEST√ïES (Pagina√ß√£o)")
    try:
        response = requests.get(f"{base_url}/questions?page=1&size=5", timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Ì≥Ñ Total: {data.get('total')}")
            print(f"   Ì≥É P√°gina: {data.get('page')}")
            print(f"   Ì≥ã Itens: {len(data.get('items', []))}")
            if data.get('items'):
                first_item = data['items'][0]
                print(f"   Ì¥¢ Primeiro: ID {first_item.get('id')} - {first_item.get('exam_year')} - {first_item.get('subject')}")
        else:
            print(f"   ‚ùå Error: {response.text}")
    except Exception as e:
        print(f"   ‚ùå Failed: {e}")
    
    # Test 4: Quest√£o espec√≠fica
    print("\n4Ô∏è‚É£ QUEST√ÉO DETALHADA")
    try:
        response = requests.get(f"{base_url}/questions/1", timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Ì¥¢ ID: {data.get('id')}")
            print(f"   Ì≥Ö Ano: {data.get('exam_year')}")
            print(f"   Ì≥ñ Mat√©ria: {data.get('answer_key', {}).get('subject')}")
            print(f"   ‚úÖ Resposta: {data.get('answer_key', {}).get('correct_answer')}")
            print(f"   Ì≥ù Enunciado: {data.get('statement', '')[:100]}...")
            print(f"   Ì¥§ Alternativas: {len(data.get('alternatives', []))}")
        else:
            print(f"   ‚ùå Error: {response.text}")
    except Exception as e:
        print(f"   ‚ùå Failed: {e}")
    
    print("\n" + "=" * 60)
    print("Ìæâ TESTE CONCLU√çDO!")
    print(f"Ìºê API: {base_url}")
    print(f"Ì≥ö Docs: {base_url}/docs")
    print(f"Ìø† Home: {base_url}/")
    print("=" * 60)

if __name__ == "__main__":
    test_dockerized_api()
