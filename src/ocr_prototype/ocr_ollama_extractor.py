#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Protótipo de Extração OCR com Ollama
Combina OCR tradicional com análise de IA para extração precisa de questões ENEM.

Features:
- Conversão PDF → Imagens de alta qualidade
- OCR multi-engine (Tesseract + EasyOCR)
- Análise com modelos Ollama para validação e estruturação
- Integração com ENEM Structural Guardrails
- Comparação com extração textual tradicional
"""

import fitz  # PyMuPDF
import cv2
import numpy as np
from PIL import Image
import pytesseract
import easyocr
import requests
import json
import re
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class QuestionRegion:
    """Região identificada como questão"""
    bbox: Tuple[int, int, int, int]  # x, y, width, height
    page_num: int
    question_number: Optional[int] = None
    confidence: float = 0.0

@dataclass
class ExtractedQuestion:
    """Questão extraída via OCR"""
    number: int
    text: str
    alternatives: Dict[str, str]
    bbox: Tuple[int, int, int, int]
    page_num: int
    confidence: float
    extraction_method: str

class OllamaClient:
    """Cliente para comunicação com Ollama"""
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
    
    def is_available(self) -> bool:
        """Verifica se o Ollama está disponível"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def list_models(self) -> List[str]:
        """Lista modelos disponíveis"""
        try:
            response = requests.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                data = response.json()
                return [model['name'] for model in data.get('models', [])]
            return []
        except:
            return []
    
    def pull_model(self, model_name: str) -> bool:
        """Baixa um modelo se necessário"""
        try:
            response = requests.post(
                f"{self.base_url}/api/pull",
                json={"name": model_name},
                stream=True
            )
            
            for line in response.iter_lines():
                if line:
                    status = json.loads(line.decode('utf-8'))
                    if 'status' in status:
                        logger.info(f"Downloading {model_name}: {status['status']}")
                    if status.get('status') == 'success':
                        return True
            return False
        except Exception as e:
            logger.error(f"Erro ao baixar modelo {model_name}: {e}")
            return False
    
    def analyze_text(self, text: str, prompt: str, model: str = "llama3.2") -> str:
        """Analisa texto usando modelo Ollama"""
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": f"{prompt}\n\nTexto para análise:\n{text}",
                    "stream": False
                },
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json().get('response', '')
            return ""
        except Exception as e:
            logger.error(f"Erro na análise com Ollama: {e}")
            return ""

class OCROllamaExtractor:
    """Extrator principal que combina OCR + Ollama"""
    
    def __init__(self):
        self.ollama = OllamaClient()
        self.setup_ocr()
        self.setup_ollama()
    
    def setup_ocr(self):
        """Configura engines de OCR"""
        # Tesseract config para português
        self.tesseract_config = '--oem 3 --psm 6 -l por'
        
        # EasyOCR para português
        try:
            self.easyocr_reader = easyocr.Reader(['pt'], gpu=False)
            logger.info("EasyOCR inicializado com sucesso")
        except Exception as e:
            logger.warning(f"Erro ao inicializar EasyOCR: {e}")
            self.easyocr_reader = None
    
    def setup_ollama(self):
        """Configura conexão com Ollama"""
        if not self.ollama.is_available():
            logger.warning("Ollama não está disponível. Continuando apenas com OCR.")
            return
        
        models = self.ollama.list_models()
        logger.info(f"Modelos Ollama disponíveis: {models}")
        
        # Modelo preferido para análise de texto
        self.preferred_model = None
        for model in ['llama3.2', 'llama2', 'mistral', 'phi']:
            if any(model in m for m in models):
                self.preferred_model = next(m for m in models if model in m)
                break
        
        # Se nenhum modelo disponível, tenta baixar llama3.2
        if not self.preferred_model and not models:
            logger.info("Tentando baixar modelo llama3.2...")
            if self.ollama.pull_model("llama3.2"):
                self.preferred_model = "llama3.2"
        
        logger.info(f"Modelo selecionado: {self.preferred_model}")
    
    def pdf_to_images(self, pdf_path: str, dpi: int = 300) -> List[np.ndarray]:
        """Converte PDF em imagens de alta qualidade"""
        logger.info(f"Convertendo PDF para imagens: {pdf_path}")
        
        doc = fitz.open(pdf_path)
        images = []
        
        for page_num in range(doc.page_count):
            page = doc[page_num]
            
            # Matriz de transformação para alta resolução
            zoom = dpi / 72  # 72 DPI é padrão
            matrix = fitz.Matrix(zoom, zoom)
            
            # Renderizar página como imagem
            pix = page.get_pixmap(matrix=matrix)
            
            # Converter para numpy array
            img_data = pix.tobytes("ppm")
            nparr = np.frombuffer(img_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            images.append(img)
            logger.info(f"Página {page_num + 1} convertida: {img.shape}")
        
        doc.close()
        return images
    
    def detect_question_regions(self, image: np.ndarray, page_num: int) -> List[QuestionRegion]:
        """Detecta regiões que contêm questões usando análise de layout"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Detectar texto "QUESTÃO" usando template matching
        regions = []
        
        # OCR rápido para encontrar "QUESTÃO XX"
        text_data = pytesseract.image_to_data(
            gray, 
            config=self.tesseract_config,
            output_type=pytesseract.Output.DICT
        )
        
        for i, word in enumerate(text_data['text']):
            if 'QUESTÃO' in word.upper() or 'QUESTAO' in word.upper():
                # Procura número da questão próximo
                for j in range(i+1, min(i+5, len(text_data['text']))):
                    next_word = text_data['text'][j]
                    if next_word.isdigit():
                        question_num = int(next_word)
                        
                        # Calcular bounding box da região
                        x = text_data['left'][i]
                        y = text_data['top'][i]
                        w = text_data['width'][i]
                        h = text_data['height'][i]
                        
                        # Expandir região para capturar questão completa
                        # (ajustar baseado no layout ENEM)
                        expanded_h = min(800, image.shape[0] - y)  # Altura típica de questão
                        
                        region = QuestionRegion(
                            bbox=(x, y, w, expanded_h),
                            page_num=page_num,
                            question_number=question_num,
                            confidence=float(text_data['conf'][i]) / 100.0
                        )
                        
                        regions.append(region)
                        break
        
        logger.info(f"Página {page_num + 1}: {len(regions)} regiões de questão detectadas")
        return regions
    
    def extract_text_from_region(self, image: np.ndarray, region: QuestionRegion) -> str:
        """Extrai texto de uma região específica usando múltiplos OCRs"""
        x, y, w, h = region.bbox
        roi = image[y:y+h, x:x+w]
        
        results = []
        
        # Tesseract
        try:
            text_tesseract = pytesseract.image_to_string(roi, config=self.tesseract_config)
            results.append(("tesseract", text_tesseract))
        except Exception as e:
            logger.warning(f"Erro Tesseract: {e}")
        
        # EasyOCR
        if self.easyocr_reader:
            try:
                ocr_result = self.easyocr_reader.readtext(roi)
                text_easyocr = ' '.join([item[1] for item in ocr_result])
                results.append(("easyocr", text_easyocr))
            except Exception as e:
                logger.warning(f"Erro EasyOCR: {e}")
        
        # Retorna o melhor resultado (mais longo por enquanto)
        if results:
            best_result = max(results, key=lambda x: len(x[1]))
            return best_result[1]
        
        return ""
    
    def analyze_with_ollama(self, raw_text: str) -> Optional[ExtractedQuestion]:
        """Analisa texto extraído usando Ollama para estruturar questão"""
        if not self.preferred_model:
            return None
        
        prompt = """
        Você é um especialista em análise de questões do ENEM. Analise o texto extraído via OCR e estruture-o no formato correto.

        Tarefas:
        1. Identifique o número da questão
        2. Extraia o enunciado completo
        3. Identifique as alternativas A, B, C, D, E
        4. Corrija erros comuns de OCR (caracteres mal reconhecidos)
        5. Preserve fórmulas químicas e matemáticas

        Responda APENAS no formato JSON:
        {
            "question_number": 91,
            "question_text": "Enunciado completo...",
            "alternatives": {
                "A": "Alternativa A...",
                "B": "Alternativa B...",
                "C": "Alternativa C...",
                "D": "Alternativa D...",
                "E": "Alternativa E..."
            },
            "confidence": 0.95
        }
        """
        
        try:
            response = self.ollama.analyze_text(raw_text, prompt, self.preferred_model)
            
            # Tentar extrair JSON da resposta
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return data
            
            return None
        except Exception as e:
            logger.error(f"Erro na análise Ollama: {e}")
            return None
    
    def extract_questions_from_pdf(self, pdf_path: str) -> List[ExtractedQuestion]:
        """Pipeline principal de extração"""
        logger.info(f"Iniciando extração OCR+Ollama para: {pdf_path}")
        
        # 1. Converter PDF para imagens
        images = self.pdf_to_images(pdf_path)
        
        extracted_questions = []
        
        # 2. Processar cada página
        for page_num, image in enumerate(images):
            logger.info(f"Processando página {page_num + 1}")
            
            # 3. Detectar regiões de questões
            regions = self.detect_question_regions(image, page_num)
            
            # 4. Extrair texto de cada região
            for region in regions:
                raw_text = self.extract_text_from_region(image, region)
                
                if not raw_text.strip():
                    continue
                
                logger.info(f"Texto extraído Q{region.question_number}: {len(raw_text)} chars")
                
                # 5. Analisar com Ollama se disponível
                ollama_result = None
                if self.preferred_model:
                    ollama_result = self.analyze_with_ollama(raw_text)
                
                # 6. Criar questão estruturada
                if ollama_result:
                    question = ExtractedQuestion(
                        number=ollama_result['question_number'],
                        text=ollama_result['question_text'],
                        alternatives=ollama_result['alternatives'],
                        bbox=region.bbox,
                        page_num=page_num,
                        confidence=ollama_result.get('confidence', 0.8),
                        extraction_method="OCR+Ollama"
                    )
                else:
                    # Fallback: estruturação básica sem Ollama
                    question = self._basic_structure_extraction(raw_text, region)
                
                if question:
                    extracted_questions.append(question)
        
        logger.info(f"Extração concluída: {len(extracted_questions)} questões")
        return extracted_questions
    
    def _basic_structure_extraction(self, text: str, region: QuestionRegion) -> Optional[ExtractedQuestion]:
        """Estruturação básica sem Ollama"""
        # Regex simples para alternativas
        alternatives = {}
        for letter in ['A', 'B', 'C', 'D', 'E']:
            pattern = f r'{letter}\)(.*?)(?=[BCDE]\)|$)'
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                alternatives[letter] = match.group(1).strip()
        
        # Extrair enunciado (antes das alternativas)
        first_alt_pos = text.find('A)')
        if first_alt_pos > 0:
            question_text = text[:first_alt_pos].strip()
        else:
            question_text = text.strip()
        
        if not question_text or len(alternatives) < 3:
            return None
        
        return ExtractedQuestion(
            number=region.question_number or 0,
            text=question_text,
            alternatives=alternatives,
            bbox=region.bbox,
            page_num=region.page_num,
            confidence=region.confidence,
            extraction_method="OCR Basic"
        )
    
    def compare_with_traditional(self, pdf_path: str) -> Dict:
        """Compara resultados OCR vs extração textual tradicional"""
        # Extração OCR
        ocr_questions = self.extract_questions_from_pdf(pdf_path)
        
        # Extração textual tradicional (usando nosso parser atual)
        try:
            from src.enem_ingestion.parser import EnemParser
            traditional_parser = EnemParser()
            traditional_questions = traditional_parser.parse_pdf(pdf_path)
        except:
            traditional_questions = []
        
        return {
            'ocr_method': {
                'count': len(ocr_questions),
                'questions': ocr_questions
            },
            'traditional_method': {
                'count': len(traditional_questions),
                'questions': traditional_questions
            },
            'comparison': {
                'ocr_advantage': len(ocr_questions) - len(traditional_questions),
                'pdf_path': pdf_path
            }
        }

def main():
    """Função principal para teste do protótipo"""
    extractor = OCROllamaExtractor()
    
    # Teste com arquivo específico
    test_file = "data/downloads/2024/2024_PV_reaplicacao_PPL_D2_CD5.pdf"
    
    if Path(test_file).exists():
        results = extractor.compare_with_traditional(test_file)
        
        print("=" * 80)
        print("COMPARAÇÃO OCR+OLLAMA vs EXTRAÇÃO TRADICIONAL")
        print("=" * 80)
        print(f"Arquivo: {test_file}")
        print(f"OCR Method: {results['ocr_method']['count']} questões")
        print(f"Traditional Method: {results['traditional_method']['count']} questões")
        print(f"Vantagem OCR: {results['comparison']['ocr_advantage']} questões")
        
        # Mostrar primeiras questões OCR
        for i, q in enumerate(results['ocr_method']['questions'][:3]):
            print(f"\n--- QUESTÃO {q.number} (OCR) ---")
            print(f"Método: {q.extraction_method}")
            print(f"Confiança: {q.confidence:.2f}")
            print(f"Texto: {q.text[:200]}...")
            print(f"Alternativas: {list(q.alternatives.keys())}")
    
    else:
        print(f"Arquivo de teste não encontrado: {test_file}")

if __name__ == "__main__":
    main()