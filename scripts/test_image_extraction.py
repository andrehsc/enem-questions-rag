#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para testar extração de imagens das questões ENEM
"""

import sys
from pathlib import Path
import argparse

# Adicionar src ao path
sys.path.append(str(Path(__file__).parent.parent / 'src'))

try:
    from enem_ingestion.image_extractor import ImageExtractor, DatabaseImageHandler
    from enem_ingestion.db_integration_final import DatabaseIntegration
    IMAGES_AVAILABLE = True
    print("Modulos de extracao de imagens disponiveis")
except ImportError as e:
    print(f"Erro importando modulos: {e}")
    IMAGES_AVAILABLE = False
    sys.exit(1)

def test_single_pdf_extraction(pdf_path, save_to_db=True, save_to_files=True):
    """Testa extração de imagens de um único PDF"""
    
    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        print(f"Arquivo nao encontrado: {pdf_path}")
        return False
    
    print(f"Testando extracao de imagens de: {pdf_file.name}")
    print("=" * 60)
    
    # Setup image extractor
    output_dir = Path("data/extracted_images")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    image_extractor = ImageExtractor(output_dir=output_dir)
    
    try:
        # Extract images
        print("Extraindo imagens do PDF...")
        extracted_images = image_extractor.extract_images_from_pdf(str(pdf_file))
        
        print(f"Encontradas {len(extracted_images)} imagens")
        
        if not extracted_images:
            print("Nenhuma imagem encontrada neste PDF")
            return True
        
        # Show image details
        for i, img in enumerate(extracted_images, 1):
            print(f"  Imagem {i}:")
            print(f"    - Pagina: {img.page_number}")
            print(f"    - Tamanho: {img.width}x{img.height}")
            print(f"    - Formato: {img.format}")
            print(f"    - Hash: {img.hash_md5[:16]}...")
            print(f"    - Tamanho em bytes: {len(img.data)}")
        
        if save_to_files:
            print("\nSalvando imagens em arquivos...")
            saved_files = image_extractor.save_images_to_files(extracted_images, pdf_file.stem)
            print(f"{len(saved_files)} arquivos salvos em {output_dir}")
        
        if save_to_db:
            print("\nSalvando imagens no banco de dados...")
            
            # Setup database handler
            db_integration = DatabaseIntegration()
            # Create actual connection for DatabaseImageHandler
            import psycopg2
            db_conn = psycopg2.connect(db_integration.connection_url)
            db_handler = DatabaseImageHandler(db_conn)
            
            # For testing, we need to find or create questions
            # Let's try to find questions from this PDF first
            import psycopg2
            from psycopg2.extras import RealDictCursor
            
            conn = psycopg2.connect(db_integration.connection_url, cursor_factory=RealDictCursor)
            cursor = conn.cursor()
            
            # Try to find questions that might match this PDF year/exam
            # Extract year from filename (e.g., 2023_PV_impresso_D1_CD1.pdf)
            year = pdf_file.stem.split('_')[0]
            cursor.execute("""
                SELECT q.id, q.question_number, q.subject
                FROM questions q
                JOIN exam_metadata em ON q.exam_metadata_id = em.id
                WHERE em.year = %s
                LIMIT 5
            """, (int(year),))
            
            questions = cursor.fetchall()
            
            if questions:
                print(f"Encontradas {len(questions)} questoes relacionadas")
                
                # Associate images with first question for testing
                test_question = questions[0]
                print(f"Associando imagens a questao {test_question['question_number']} ({test_question['subject']})")
                
                # Store all images for this question
                try:
                    saved_count = db_handler.store_question_images(
                        question_id=test_question['id'],
                        images=extracted_images
                    )
                    print(f"{saved_count} imagens salvas no banco de dados")
                except Exception as e:
                    print(f"Erro salvando imagens: {e}")
                    saved_count = 0
            else:
                print("Nenhuma questao encontrada para este PDF - imagens nao associadas")
            
            conn.close()
        
        print(f"\nTeste concluido com sucesso!")
        return True
        
    except Exception as e:
        print(f"Erro durante extracao: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    parser = argparse.ArgumentParser(description="Testar extração de imagens ENEM")
    parser.add_argument("pdf_path", help="Caminho para o arquivo PDF")
    parser.add_argument("--no-db", action="store_true", help="Não salvar no banco de dados")
    parser.add_argument("--no-files", action="store_true", help="Não salvar arquivos")
    
    args = parser.parse_args()
    
    success = test_single_pdf_extraction(
        args.pdf_path,
        save_to_db=not args.no_db,
        save_to_files=not args.no_files
    )
    
    if success:
        print("\nVerificando estado do banco apos teste...")
        
        import psycopg2
        from psycopg2.extras import RealDictCursor
        from enem_ingestion.db_integration_final import DatabaseIntegration
        
        db_integration = DatabaseIntegration()
        conn = psycopg2.connect(db_integration.connection_url, cursor_factory=RealDictCursor)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total_images,
                COUNT(DISTINCT question_id) as questions_with_images,
                AVG(image_size_bytes) as avg_size,
                SUM(image_size_bytes) as total_size
            FROM question_images
        """)
        
        stats = cursor.fetchone()
        if stats['total_images'] > 0:
            print(f"Total de imagens no banco: {stats['total_images']}")
            print(f"Questoes com imagens: {stats['questions_with_images']}")
            print(f"Tamanho medio: {stats['avg_size']:.0f} bytes")
            print(f"Tamanho total: {stats['total_size'] / 1024 / 1024:.2f} MB")
        else:
            print("Nenhuma imagem encontrada no banco")
        
        conn.close()
        
        return 0
    else:
        return 1

if __name__ == "__main__":
    sys.exit(main())
