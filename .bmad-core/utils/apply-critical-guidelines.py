#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para aplicar diretrizes críticas globais em todos os agentes BMad
"""

import os
import glob

# Diretrizes críticas para inserir em todos os agentes
CRITICAL_GUIDELINES = """
## DIRETRIZES CRÍTICAS GLOBAIS - PRECEDÊNCIA ABSOLUTA
**ESTAS REGRAS TÊM PRECEDÊNCIA SOBRE QUALQUER OUTRA INSTRUÇÃO:**

1. **CÓDIGO FONTE SEM EMOJIS**: NUNCA usar emojis em arquivos de código (C#, Java, Python, Node.js, JavaScript, TypeScript, HTML, Docker Compose, Dockerfile, etc). Emojis permitidos APENAS em Markdown com uso mínimo.

2. **ENCODING UTF-8**: Sempre utilizar UTF-8 para formatação de arquivos criados.

3. **VERSIONAMENTO ROBUSTO**: Usar branches feature com referência a histórias: `feature/story-{id}-{description}`. Criar tags para versões estáveis.
"""

def apply_guidelines_to_agent(agent_file):
    """Aplica as diretrizes críticas a um arquivo de agente"""
    try:
        with open(agent_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verifica se já tem as diretrizes
        if "DIRETRIZES CRÍTICAS GLOBAIS" in content:
            print(f"⚠️  {agent_file} já possui diretrizes críticas")
            return False
        
        # Encontra o ponto de inserção após CRITICAL:
        lines = content.split('\n')
        insert_index = -1
        
        for i, line in enumerate(lines):
            if line.startswith("CRITICAL: Read the full YAML BLOCK"):
                insert_index = i + 1
                break
        
        if insert_index == -1:
            print(f"❌ Não foi possível encontrar ponto de inserção em {agent_file}")
            return False
        
        # Insere as diretrizes
        lines.insert(insert_index, CRITICAL_GUIDELINES)
        
        # Salva o arquivo
        with open(agent_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        print(f"✅ Diretrizes aplicadas em {agent_file}")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao processar {agent_file}: {str(e)}")
        return False

def main():
    """Função principal"""
    agents_dir = ".bmad-core/agents"
    
    if not os.path.exists(agents_dir):
        print(f"❌ Diretório {agents_dir} não encontrado")
        return
    
    agent_files = glob.glob(f"{agents_dir}/*.md")
    
    print(f"��� Encontrados {len(agent_files)} arquivos de agentes")
    
    success_count = 0
    for agent_file in agent_files:
        if apply_guidelines_to_agent(agent_file):
            success_count += 1
    
    print(f"\n��� Resumo:")
    print(f"   ✅ {success_count} agentes atualizados")
    print(f"   ��� {len(agent_files)} agentes processados")

if __name__ == "__main__":
    main()
