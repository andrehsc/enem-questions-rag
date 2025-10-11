#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de diagn√≥stico e solu√ß√£o de problemas Docker/API
"""

import subprocess
import sys
import time
import requests
import json
from datetime import datetime

def run_command(cmd, timeout=30):
    """Executa comando e retorna resultado"""
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=timeout,
            encoding='utf-8'
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Timeout"
    except Exception as e:
        return -1, "", str(e)

def check_docker():
    """Verifica se Docker est√° funcionando"""
    print("Ì¥ç Verificando Docker...")
    
    # Verificar vers√£o
    code, out, err = run_command("docker --version")
    if code != 0:
        print(f"‚ùå Docker n√£o encontrado: {err}")
        return False
    print(f"‚úÖ Docker instalado: {out.strip()}")
    
    # Verificar Docker Compose
    code, out, err = run_command("docker-compose --version")
    if code != 0:
        print(f"‚ùå Docker Compose n√£o encontrado: {err}")
        return False
    print(f"‚úÖ Docker Compose instalado: {out.strip()}")
    
    # Verificar se Docker est√° rodando
    code, out, err = run_command("docker info", timeout=10)
    if code != 0:
        print(f"‚ùå Docker n√£o est√° rodando: {err}")
        return False
    
    print("‚úÖ Docker est√° funcionando")
    return True

def check_containers():
    """Verifica status dos containers"""
    print("\nÌ¥ç Verificando containers...")
    
    code, out, err = run_command("docker-compose ps")
    if code != 0:
        print(f"‚ùå Erro ao verificar containers: {err}")
        return False
    
    print("Ì≥ä Status dos containers:")
    print(out)
    return True

def start_infrastructure():
    """Inicia infraestrutura Docker"""
    print("\nÌ∫Ä Iniciando infraestrutura...")
    
    # Parar containers existentes
    print("Ìªë Parando containers existentes...")
    run_command("docker-compose down", timeout=60)
    
    # Iniciar containers
    print("‚ñ∂Ô∏è Iniciando containers...")
    code, out, err = run_command("docker-compose up -d", timeout=120)
    
    if code != 0:
        print(f"‚ùå Erro ao iniciar containers: {err}")
        return False
    
    print("‚úÖ Containers iniciados")
    print(out)
    
    # Aguardar inicializa√ß√£o
    print("‚è≥ Aguardando inicializa√ß√£o...")
    time.sleep(30)
    
    return True

def check_services():
    """Verifica se servi√ßos est√£o respondendo"""
    print("\nÌ¥ç Verificando servi√ßos...")
    
    services = {
        "PostgreSQL": ("localhost", 5432, "tcp"),
        "Redis": ("localhost", 6379, "tcp"),
        "API": ("http://localhost:8000/health", None, "http")
    }
    
    for service, (host, port, protocol) in services.items():
        if protocol == "http":
            try:
                response = requests.get(host, timeout=10)
                if response.status_code == 200:
                    print(f"‚úÖ {service}: OK")
                else:
                    print(f"‚ùå {service}: HTTP {response.status_code}")
            except Exception as e:
                print(f"‚ùå {service}: {str(e)}")
        elif protocol == "tcp":
            import socket
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                result = sock.connect_ex((host, port))
                sock.close()
                if result == 0:
                    print(f"‚úÖ {service}: Porta {port} aberta")
                else:
                    print(f"‚ùå {service}: Porta {port} fechada")
            except Exception as e:
                print(f"‚ùå {service}: {str(e)}")

def test_api_endpoints():
    """Testa endpoints da API"""
    print("\nÌ¥ç Testando API endpoints...")
    
    endpoints = [
        "/",
        "/health", 
        "/stats",
        "/questions?limit=5"
    ]
    
    base_url = "http://localhost:8000"
    
    for endpoint in endpoints:
        try:
            url = base_url + endpoint
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                print(f"‚úÖ {endpoint}: OK")
            else:
                print(f"‚ùå {endpoint}: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"‚ùå {endpoint}: {str(e)}")

def show_logs():
    """Mostra logs dos containers"""
    print("\nÌ≥ã Logs dos containers:")
    
    containers = ["api", "postgres", "redis"]
    
    for container in containers:
        print(f"\n--- Logs do {container} ---")
        code, out, err = run_command(f"docker-compose logs --tail=10 {container}")
        if code == 0:
            print(out)
        else:
            print(f"Erro ao obter logs: {err}")

def cleanup_docker():
    """Limpa recursos Docker desnecess√°rios"""
    print("\nÌ∑π Limpando Docker...")
    
    # Parar containers
    run_command("docker-compose down -v")
    
    # Limpar sistema
    run_command("docker system prune -f")
    
    print("‚úÖ Limpeza conclu√≠da")

def main():
    """Fun√ß√£o principal"""
    print("=" * 60)
    print("Ì¥ß DIAGN√ìSTICO ENEM RAG API - DOCKER")
    print("=" * 60)
    print(f"Ì≥Ö Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Menu de op√ß√µes
    while True:
        print("\nÌ≥ã Op√ß√µes dispon√≠veis:")
        print("1. ‚úÖ Verificar Docker")
        print("2. Ì≥ä Status containers")  
        print("3. Ì∫Ä Iniciar infraestrutura")
        print("4. Ì¥ç Verificar servi√ßos")
        print("5. ÔøΩÔøΩÔøΩ Testar API")
        print("6. Ì≥ã Ver logs")
        print("7. Ì∑π Limpar Docker")
        print("8. Ì¥Ñ Diagn√≥stico completo")
        print("9. ‚ùå Sair")
        
        choice = input("\nÌ±â Escolha uma op√ß√£o (1-9): ").strip()
        
        if choice == "1":
            check_docker()
        elif choice == "2":
            check_containers()
        elif choice == "3":
            start_infrastructure()
        elif choice == "4":
            check_services()
        elif choice == "5":
            test_api_endpoints()
        elif choice == "6":
            show_logs()
        elif choice == "7":
            cleanup_docker()
        elif choice == "8":
            # Diagn√≥stico completo
            print("\nÌ¥Ñ Executando diagn√≥stico completo...")
            if check_docker():
                cleanup_docker()
                if start_infrastructure():
                    check_containers()
                    check_services()
                    test_api_endpoints()
            show_logs()
            print("\n‚úÖ Diagn√≥stico completo finalizado")
        elif choice == "9":
            print("Ì±ã Saindo...")
            break
        else:
            print("‚ùå Op√ß√£o inv√°lida")

if __name__ == "__main__":
    main()
