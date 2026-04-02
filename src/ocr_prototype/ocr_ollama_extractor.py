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
        # Tesseract config para português (se disponível)
        self.tesseract_config = '--oem 3 --psm 6 -l por'
        self.tesseract_available = self._check_tesseract()
        
        # Verificar se GPU está disponível
        gpu_available = self._check_gpu_availability()
        
        # EasyOCR para português
        try:
            if gpu_available:
                logger.info("GPU detectada - usando EasyOCR com aceleração GPU")
                self.easyocr_reader = easyocr.Reader(['pt'], gpu=True)
            else:
                logger.info("GPU não disponível - usando EasyOCR com CPU")
                self.easyocr_reader = easyocr.Reader(['pt'], gpu=False)
            logger.info("EasyOCR inicializado com sucesso")
        except Exception as e:
            logger.warning(f"Erro ao inicializar EasyOCR: {e}")
            # Fallback para CPU se GPU falhar
            try:
                logger.info("Tentando fallback para CPU...")
                self.easyocr_reader = easyocr.Reader(['pt'], gpu=False)
                logger.info("EasyOCR inicializado com CPU")
            except Exception as e2:
                logger.error(f"Falha completa no EasyOCR: {e2}")
                self.easyocr_reader = None
    
    def _check_gpu_availability(self) -> bool:
        """Verifica se GPU/CUDA está disponível"""
        try:
            import torch
            cuda_available = torch.cuda.is_available()
            if cuda_available:
                gpu_count = torch.cuda.device_count()
                gpu_name = torch.cuda.get_device_name(0) if gpu_count > 0 else "Unknown"
                logger.info(f"CUDA disponível: {gpu_count} GPU(s) detectada(s) - {gpu_name}")
                return True
            else:
                logger.info("CUDA não disponível")
                return False
        except ImportError:
            logger.info("PyTorch não instalado - verificando TensorFlow...")
            try:
                import tensorflow as tf
                gpus = tf.config.experimental.list_physical_devices('GPU')
                if gpus:
                    logger.info(f"TensorFlow GPU disponível: {len(gpus)} GPU(s)")
                    return True
                else:
                    logger.info("TensorFlow: Nenhuma GPU detectada")
                    return False
            except ImportError:
                logger.info("Nem PyTorch nem TensorFlow instalados - usando CPU")
                return False
        except Exception as e:
            logger.warning(f"Erro ao verificar GPU: {e}")
            return False
    
    def _check_tesseract(self) -> bool:
        """Verifica se Tesseract está disponível"""
        import subprocess
        import os
        
        # Configurar caminho do Tesseract no Windows
        if os.name == 'nt':  # Windows
            tesseract_paths = [
                r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                "tesseract"  # Se estiver no PATH
            ]
            
            for path in tesseract_paths:
                try:
                    if os.path.exists(path) or path == "tesseract":
                        pytesseract.pytesseract.tesseract_cmd = path
                        # Testar se funciona
                        result = subprocess.run([path, '--version'], capture_output=True, check=True, text=True)
                        logger.info(f"Tesseract encontrado e configurado: {path}")
                        
                        # Verificar se português está disponível
                        try:
                            langs_result = subprocess.run([path, '--list-langs'], capture_output=True, check=True, text=True)
                            available_langs = langs_result.stdout.strip().split('\n')[1:]  # Skip header
                            
                            if 'por' in available_langs:
                                logger.info("Tesseract: Modelo português disponível")
                                self.tesseract_config = '--oem 3 --psm 6 -l por'
                            else:
                                logger.warning("Tesseract: Modelo português não encontrado, usando inglês")
                                self.tesseract_config = '--oem 3 --psm 6 -l eng'
                        except:
                            logger.warning("Não foi possível verificar idiomas, usando configuração padrão")
                            self.tesseract_config = '--oem 3 --psm 6'
                        
                        return True
                except Exception as e:
                    logger.debug(f"Caminho {path} falhou: {e}")
                    continue
        else:
            # Linux/Mac - tentar usar diretamente
            try:
                result = subprocess.run(['tesseract', '--version'], capture_output=True, check=True, text=True)
                logger.info("Tesseract disponível (sistema Unix)")
                
                # Verificar se português está disponível
                langs_result = subprocess.run(['tesseract', '--list-langs'], capture_output=True, check=True, text=True)
                available_langs = langs_result.stdout.strip().split('\n')[1:]  # Skip header
                
                if 'por' in available_langs:
                    logger.info("Tesseract: Modelo português disponível")
                else:
                    logger.warning("Tesseract: Modelo português não encontrado, usando inglês")
                    self.tesseract_config = '--oem 3 --psm 6 -l eng'
                
                return True
            except Exception as e:
                logger.warning(f"Tesseract não encontrado: {e}. Usando apenas EasyOCR.")
                return False
        
        logger.warning("Tesseract não encontrado em nenhum caminho. Usando apenas EasyOCR.")
        return False
    
    def setup_ollama(self):
        """Configura conexão com Ollama"""
        if not self.ollama.is_available():
            logger.warning("Ollama não está disponível. Continuando apenas com OCR.")
            return
        
        models = self.ollama.list_models()
        logger.info(f"Modelos Ollama disponíveis: {models}")
        
        # Verificar se GPU está disponível para Ollama
        gpu_available = self._check_gpu_availability()
        if gpu_available:
            logger.info("GPU detectada - Ollama poderá usar aceleração GPU se configurado")
        
        # Modelo preferido para análise de texto
        self.preferred_model = None
        for model in ['llama3.2', 'llama2', 'mistral', 'phi', 'deepseek-r1']:
            if any(model in m for m in models):
                self.preferred_model = next(m for m in models if model in m)
                break
        
        # Se nenhum modelo disponível, tenta baixar llama3.2
        if not self.preferred_model and not models:
            logger.info("Tentando baixar modelo llama3.2...")
            if self.ollama.pull_model("llama3.2"):
                self.preferred_model = "llama3.2"
        
        logger.info(f"Modelo selecionado: {self.preferred_model}")
        
        # Informações sobre GPU para Ollama
        if gpu_available:
            logger.info("💡 Para usar GPU no Ollama, certifique-se de ter NVIDIA Container Toolkit ou Ollama GPU instalado")
            logger.info("💡 Execute: ollama serve com GPU configurada para melhor performance")
    
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
        """Detecta regiões que contêm questões usando análise de layout melhorada para ENEM"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        height, width = image.shape[:2]
        
        regions = []
        
        # Estratégia melhorada: usar EasyOCR primeiro (mais preciso para layout ENEM)
        if self.easyocr_reader:
            try:
                logger.info(f"Detectando questões com EasyOCR na página {page_num + 1}")
                results = self.easyocr_reader.readtext(gray)
                
                # ALGORITMO MELHORADO para detectar padrões variados de "QUESTÃO XX"
                question_headers = []
                for i, (bbox, text, confidence) in enumerate(results):
                    # Múltiplos padrões de detecção de cabeçalhos
                    text_upper = text.upper().strip()
                    
                    # PADRÃO 1: "QUESTÃO XX" direto no texto
                    direct_match = re.search(r'QUEST[AÃ]O\s+(\d+)', text_upper)
                    if direct_match:
                        question_num = int(direct_match.group(1))
                        question_headers.append({
                            'bbox': bbox,
                            'number': question_num,
                            'confidence': confidence,
                            'y_pos': int(min(p[1] for p in bbox)),
                            'pattern': 'direct'
                        })
                        continue
                    
                    # PADRÃO 2: "QUESTÃO" separado do número
                    if ('QUESTÃO' in text_upper or 'QUESTAO' in text_upper) and confidence > 0.75:
                        # Procurar número da questão nos próximos resultados OCR
                        question_num = None
                        
                        # Primeiro: verificar se há números no próprio texto
                        numbers = re.findall(r'\d+', text)
                        if numbers:
                            question_num = int(numbers[0])
                        else:
                            # Buscar nos próximos 4 elementos OCR
                            for j in range(i+1, min(i+5, len(results))):
                                next_bbox, next_text, next_conf = results[j]
                                
                                # Verificar se está próximo verticalmente (mesma linha)
                                current_y = int(min(p[1] for p in bbox))
                                next_y = int(min(p[1] for p in next_bbox))
                                
                                if abs(current_y - next_y) < 50:  # Mesmo nível vertical
                                    numbers = re.findall(r'^(\d+)$', next_text.strip())  # Número isolado
                                    if numbers:
                                        question_num = int(numbers[0])
                                        break
                        
                        # VALIDAÇÃO FLEXÍVEL de números de questão
                        if question_num is not None:
                            # Aceitar questões de 1-180 (cobrindo todo o espectro ENEM)
                            if 1 <= question_num <= 180:
                                question_headers.append({
                                    'bbox': bbox,
                                    'number': question_num,
                                    'confidence': confidence,
                                    'y_pos': int(min(p[1] for p in bbox)),
                                    'pattern': 'separated'
                                })
                    
                    # PADRÃO 3: Apenas números em destaque (para casos como "02", "39")
                    elif re.match(r'^\d{1,3}$', text_upper) and confidence > 0.9:
                        question_num = int(text_upper)
                        
                        # Verificar se há "QUESTÃO" próximo (antes ou depois)
                        has_question_nearby = False
                        
                        # Buscar "QUESTÃO" nas proximidades
                        for j in range(max(0, i-3), min(i+4, len(results))):
                            if j == i:
                                continue
                                
                            nearby_bbox, nearby_text, nearby_conf = results[j]
                            if 'QUEST' in nearby_text.upper():
                                # Verificar proximidade vertical
                                current_y = int(min(p[1] for p in bbox))
                                nearby_y = int(min(p[1] for p in nearby_bbox))
                                
                                if abs(current_y - nearby_y) < 60:  # Mesmo bloco visual
                                    has_question_nearby = True
                                    break
                        
                        if has_question_nearby and 1 <= question_num <= 180:
                            question_headers.append({
                                'bbox': bbox,
                                'number': question_num,
                                'confidence': confidence,
                                'y_pos': int(min(p[1] for p in bbox)),
                                'pattern': 'number_only'
                            })
                
                # Ordenar por posição vertical
                question_headers.sort(key=lambda x: x['y_pos'])
                
                logger.info(f"Encontrados {len(question_headers)} cabeçalhos de questão")
                
                # Criar regiões baseadas no layout típico do ENEM com altura otimizada
                for idx, header in enumerate(question_headers):
                    bbox = header['bbox']
                    x1, y1 = int(min(p[0] for p in bbox)), int(min(p[1] for p in bbox))
                    x2, y2 = int(max(p[0] for p in bbox)), int(max(p[1] for p in bbox))
                    
                    # CORREÇÃO: Detectar coluna baseado na posição do cabeçalho da questão
                    is_left_column = x1 < width // 2
                    
                    # ESTRATÉGIA CORRIGIDA: Delimitação precisa por questão individual
                    
                    # 1. POSICIONAMENTO HORIZONTAL baseado na coluna
                    if width > 1000:  # Layout de duas colunas detectado
                        if is_left_column:  # Coluna esquerda
                            region_x = 20  # Margem esquerda mínima
                            region_width = (width // 2) - 40  # Largura da coluna esquerda
                        else:  # Coluna direita
                            region_x = (width // 2) + 20  # Início da coluna direita
                            region_width = (width // 2) - 40  # Largura da coluna direita
                    else:  # Layout de uma coluna
                        region_x = 20
                        region_width = width - 40
                    
                    # 2. POSICIONAMENTO VERTICAL - Início da questão
                    region_y = max(0, y1 - 20)  # Margem superior aumentada
                    
                    # 3. ALTURA DA QUESTÃO - Delimitação melhorada
                    if idx < len(question_headers) - 1:
                        # Encontrar PRÓXIMA questão na MESMA coluna
                        next_questions_same_column = []
                        
                        for j in range(idx + 1, len(question_headers)):
                            next_header = question_headers[j]
                            next_x = int(min(p[0] for p in next_header['bbox']))
                            next_y = next_header['y_pos']
                            next_is_left = next_x < width // 2
                            
                            # Verificar se está na mesma coluna
                            if next_is_left == is_left_column:
                                next_questions_same_column.append(next_y)
                        
                        if next_questions_same_column:
                            # Próxima questão na mesma coluna - usar como limite
                            next_y_same_col = min(next_questions_same_column)
                            region_height = next_y_same_col - region_y - 30  # Margem entre questões
                        else:
                            # Não há mais questões nesta coluna - usar espaço até o final
                            region_height = height - region_y - 30
                    else:
                        # Última questão - usar espaço restante
                        region_height = height - region_y - 30
                    
                    # 4. ANÁLISE REFINADA do conteúdo para ajustar altura
                    try:
                        # Procurar padrão das alternativas na região para validar altura
                        search_height = min(region_height + 200, height - region_y)
                        temp_region = gray[region_y:region_y + search_height, 
                                         region_x:region_x + region_width]
                        
                        if temp_region.size > 0:
                            temp_results = self.easyocr_reader.readtext(temp_region)
                            
                            # Encontrar alternativas e próximos cabeçalhos
                            last_alternative_y = 0
                            next_question_y = None
                            
                            for temp_bbox, temp_text, temp_conf in temp_results:
                                if temp_conf > 0.6:
                                    temp_y = int(max(p[1] for p in temp_bbox))
                                    
                                    # Detectar alternativas (A, B, C, D, E)
                                    if re.match(r'^[ABCDE]\)', temp_text.strip()):
                                        last_alternative_y = max(last_alternative_y, temp_y)
                                    
                                    # Detectar próximo cabeçalho "QUESTÃO"
                                    elif 'QUESTÃO' in temp_text.upper() and temp_y > 100:
                                        # Verificar se é questão diferente da atual
                                        numbers = re.findall(r'\d+', temp_text)
                                        if numbers and int(numbers[0]) != header['number']:
                                            if next_question_y is None or temp_y < next_question_y:
                                                next_question_y = temp_y
                            
                            # Ajustar altura baseada nos achados
                            if next_question_y is not None:
                                # Encontrou próxima questão - parar antes dela
                                region_height = min(region_height, next_question_y - region_y - 40)
                            elif last_alternative_y > 0:
                                # Encontrou alternativas - usar como referência
                                estimated_height = last_alternative_y - region_y + 60  # Margem após alternativas
                                region_height = min(region_height, estimated_height)
                    
                    except Exception as e:
                        logger.debug(f"Erro na análise refinada: {e}")
                    
                    # 5. LIMITES DE SEGURANÇA
                    region_height = max(300, min(region_height, 1000))  # Altura mínima e máxima
                    region_height = min(region_height, height - region_y)
                    region_width = min(region_width, width - region_x)
                    
                    # 6. VALIDAR E CRIAR REGIÃO
                    if region_width > 200 and region_height > 250:  # Validação de região mínima
                        region = QuestionRegion(
                            bbox=(region_x, region_y, region_width, region_height),
                            page_num=page_num,
                            question_number=header['number'],
                            confidence=header['confidence']
                        )
                        regions.append(region)
                        logger.info(f"Região Q{header['number']} (col {'esq' if is_left_column else 'dir'}): x={region_x}, y={region_y}, w={region_width}, h={region_height}")
                    else:
                        logger.warning(f"Região rejeitada Q{header['number']}: w={region_width}, h={region_height} (muito pequena)")
                
            except Exception as e:
                logger.warning(f"Erro no EasyOCR para detecção: {e}")
        
        # Fallback com Tesseract se EasyOCR falhou
        if not regions and self.tesseract_available:
            try:
                logger.info("Fallback para Tesseract com algoritmo otimizado")
                text_data = pytesseract.image_to_data(
                    gray, 
                    config=self.tesseract_config,
                    output_type=pytesseract.Output.DICT
                )
                
                # Encontrar cabeçalhos de questão
                question_headers = []
                for i, word in enumerate(text_data['text']):
                    if 'QUESTÃO' in word.upper() or 'QUESTAO' in word.upper():
                        # Procura número da questão próximo
                        for j in range(i+1, min(i+5, len(text_data['text']))):
                            next_word = text_data['text'][j]
                            if next_word.isdigit() and int(next_word) >= 91:
                                question_num = int(next_word)
                                x = text_data['left'][i]
                                y = text_data['top'][i]
                                conf = float(text_data['conf'][i]) / 100.0
                                
                                question_headers.append({
                                    'number': question_num,
                                    'x': x,
                                    'y': y,
                                    'confidence': conf
                                })
                                break
                
                # Ordenar por posição vertical
                question_headers.sort(key=lambda x: x['y'])
                
                # Criar regiões com mesmo algoritmo otimizado
                for idx, header in enumerate(question_headers):
                    x, y = header['x'], header['y']
                    
                    # Layout baseado em colunas
                    if width > 1000:  # Duas colunas
                        if x < width // 2:
                            region_x, region_width = 30, width // 2 - 80
                        else:
                            region_x, region_width = width // 2 + 30, width // 2 - 80
                    else:
                        region_x, region_width = 30, width - 60
                    
                    region_y = max(0, y - 15)
                    
                    # Calcular altura baseada na próxima questão ou espaço disponível
                    if idx < len(question_headers) - 1:
                        next_y = question_headers[idx + 1]['y']
                        same_column = (x < width // 2) == (question_headers[idx + 1]['x'] < width // 2) if width > 1000 else True
                        
                        if same_column:
                            region_height = next_y - region_y - 30
                        else:
                            region_height = min(height - region_y - 30, 800)
                    else:
                        region_height = height - region_y - 30
                    
                    # Limites de segurança
                    region_height = max(300, min(region_height, 1000))
                    region_height = min(region_height, height - region_y)
                    region_width = min(region_width, width - region_x)
                    
                    if region_width > 100 and region_height > 200:
                        region = QuestionRegion(
                            bbox=(region_x, region_y, region_width, region_height),
                            page_num=page_num,
                            question_number=header['number'],
                            confidence=header['confidence']
                        )
                        regions.append(region)
                        logger.info(f"Região Tesseract para Q{header['number']}: x={region_x}, y={region_y}, w={region_width}, h={region_height}")
                    
            except Exception as e:
                logger.warning(f"Erro no Tesseract para detecção: {e}")
        
        logger.info(f"Página {page_num + 1}: {len(regions)} regiões de questão detectadas com algoritmo melhorado")
        return regions
    
    def _detect_horizontal_line_end(self, image: np.ndarray, start_y: int, start_x: int, max_width: int) -> int:
        """Detecta o final da linha horizontal ao lado da questão"""
        try:
            # Procurar linha horizontal na região do cabeçalho da questão
            search_height = 50  # Altura da região de busca
            search_y = max(0, start_y - 25)
            search_region = image[search_y:search_y + search_height, start_x:max_width]
            
            if search_region.size == 0:
                return 0
            
            # Detectar linhas usando HoughLinesP
            edges = cv2.Canny(search_region, 50, 150, apertureSize=3)
            lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=50, minLineLength=100, maxLineGap=10)
            
            if lines is not None:
                # Encontrar a linha horizontal mais longa
                longest_line_end = 0
                for line in lines:
                    x1, y1, x2, y2 = line[0]
                    # Verificar se é uma linha aproximadamente horizontal
                    if abs(y2 - y1) < 10:  # Tolerância para linhas horizontais
                        line_end = max(x1, x2) + start_x
                        longest_line_end = max(longest_line_end, line_end)
                
                return longest_line_end
            
            return 0
        except Exception as e:
            logger.debug(f"Erro na detecção de linha horizontal: {e}")
            return 0
    
    def _detect_horizontal_separator(self, image: np.ndarray, start_y: int, end_y: int) -> int:
        """Detecta linha horizontal que separa duas questões"""
        try:
            if end_y <= start_y:
                return 0
                
            # Região entre duas questões
            separator_region = image[start_y:end_y, :]
            
            if separator_region.size == 0:
                return 0
            
            # Detectar linhas horizontais na região separadora
            edges = cv2.Canny(separator_region, 30, 100)
            lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=30, minLineLength=200, maxLineGap=20)
            
            if lines is not None:
                # Encontrar linha horizontal no meio da região
                separator_candidates = []
                for line in lines:
                    x1, y1, x2, y2 = line[0]
                    if abs(y2 - y1) < 5:  # Linha horizontal
                        line_y = (y1 + y2) // 2 + start_y
                        line_length = abs(x2 - x1)
                        separator_candidates.append((line_y, line_length))
                
                if separator_candidates:
                    # Escolher a linha mais longa (mais provável de ser separadora)
                    separator_candidates.sort(key=lambda x: x[1], reverse=True)
                    return separator_candidates[0][0]
            
            return 0
        except Exception as e:
            logger.debug(f"Erro na detecção de separador: {e}")
            return 0
    
    def extract_text_tesseract(self, image: np.ndarray) -> str:
        """Extrai texto usando Tesseract com configuração otimizada"""
        if not self.tesseract_available:
            return ""
        
        try:
            # Pré-processamento da imagem para melhor OCR
            # Converter para escala de cinza se necessário
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image.copy()
            
            # Aplicar filtros para melhorar qualidade do OCR
            # Redução de ruído
            denoised = cv2.fastNlMeansDenoising(gray)
            
            # Aumento de contraste
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            enhanced = clahe.apply(denoised)
            
            # Binarização adaptativa
            binary = cv2.adaptiveThreshold(enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
            
            # Extrair texto
            text = pytesseract.image_to_string(binary, config=self.tesseract_config)
            return text.strip()
            
        except Exception as e:
            logger.warning(f"Erro na extração Tesseract: {e}")
            return ""

    def extract_text_from_region(self, image: np.ndarray, region: QuestionRegion) -> str:
        """Extrai texto de uma região específica usando múltiplos OCRs com pré-processamento melhorado"""
        x, y, w, h = region.bbox
        
        # Validar coordenadas da região
        height, width = image.shape[:2]
        x = max(0, min(x, width - 1))
        y = max(0, min(y, height - 1))
        w = max(1, min(w, width - x))
        h = max(1, min(h, height - y))
        
        roi = image[y:y+h, x:x+w]
        
        # Verificar se a região é válida
        if roi.size == 0:
            logger.warning(f"Região inválida para Q{region.question_number}: {region.bbox}")
            return ""
        
        results = []
        
        # Tesseract com pré-processamento
        if self.tesseract_available:
            try:
                text_tesseract = self.extract_text_tesseract(roi)
                if text_tesseract:
                    results.append(("tesseract", text_tesseract))
            except Exception as e:
                logger.warning(f"Erro Tesseract: {e}")
        
        # EasyOCR
        if self.easyocr_reader:
            try:
                ocr_result = self.easyocr_reader.readtext(roi)
                if ocr_result:
                    # Ordenar por posição vertical para manter ordem de leitura
                    ocr_result.sort(key=lambda x: min(p[1] for p in x[0]))
                    text_easyocr = ' '.join([item[1] for item in ocr_result if item[2] > 0.5])  # Filtrar baixa confiança
                    if text_easyocr:
                        results.append(("easyocr", text_easyocr))
            except Exception as e:
                logger.warning(f"Erro EasyOCR: {e}")
        
        # Escolher melhor resultado baseado em heurísticas
        if results:
            # Priorizar resultado com mais texto estruturado (alternativas A, B, C, D, E)
            scored_results = []
            for method, text in results:
                score = len(text)  # Base: comprimento do texto
                
                # Bonus para presença de alternativas
                alternatives_found = len(re.findall(r'[ABCDE]\)', text))
                score += alternatives_found * 50
                
                # Bonus para presença de "QUESTÃO"
                if 'QUESTÃO' in text.upper() or 'QUESTAO' in text.upper():
                    score += 100
                
                # Bonus para números de questão válidos
                question_numbers = re.findall(r'QUEST[AÃ]O\s+(\d+)', text.upper())
                if question_numbers:
                    score += 150
                
                scored_results.append((score, method, text))
            
            # Retornar o melhor resultado
            best_result = max(scored_results, key=lambda x: x[0])
            logger.info(f"Usando OCR {best_result[1]} para questão {region.question_number} (score: {best_result[0]})")
            return best_result[2]
        
        logger.warning(f"Nenhum OCR conseguiu extrair texto da região Q{region.question_number}: {region.bbox}")
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
    
    def extract_questions_from_pdf(self, pdf_path: str, save_images: bool = True, output_dir: str = "reports", max_pages: int = None) -> List[ExtractedQuestion]:
        """Pipeline principal de extração com relatório detalhado"""
        logger.info(f"Iniciando extração OCR+Ollama para: {pdf_path}")
        
        # Criar diretório de relatórios se não existir
        from pathlib import Path
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        images_path = output_path / "extracted_images"
        images_path.mkdir(exist_ok=True)
        
        # 1. Converter PDF para imagens
        images = self.pdf_to_images(pdf_path, dpi=150)  # Reduzir DPI para teste
        
        # IGNORAR PRIMEIRA PÁGINA (contém apenas metadados do caderno)
        if len(images) > 1:
            images = images[1:]  # Remove primeira página
            logger.info(f"IGNORANDO PRIMEIRA PÁGINA (metadados do caderno)")
            logger.info(f"Processando páginas 2-{len(images)+1} do PDF original")
        
        if max_pages:
            images = images[:max_pages]
            logger.info(f"LIMITANDO A {max_pages} PÁGINAS PARA TESTE DETALHADO")
        
        extracted_questions = []
        detailed_report = []
        
        # Informações do PDF
        pdf_name = Path(pdf_path).name
        detailed_report.append(f"# RELATÓRIO DETALHADO DE EXTRAÇÃO OCR+OLLAMA")
        detailed_report.append(f"")
        detailed_report.append(f"## 📄 INFORMAÇÕES DO CADERNO")
        detailed_report.append(f"- **Arquivo:** {pdf_name}")
        detailed_report.append(f"- **Data de Extração:** {__import__('datetime').datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        detailed_report.append(f"- **Total de Páginas no PDF:** {len(images) + 1}")  # +1 porque removemos a primeira
        detailed_report.append(f"- **Páginas Processadas:** {len(images)} (excluindo página 1 com metadados)")
        detailed_report.append(f"- **Expectativa:** 90-95 questões por caderno ENEM")
        detailed_report.append(f"- **Modo:** Teste detalhado com primeira página ignorada")
        detailed_report.append("")
        
        # Identificar caderno pelos padrões ENEM
        caderno_info = self._identify_caderno_info(pdf_name)
        if caderno_info:
            detailed_report.append(f"## 🎯 IDENTIFICAÇÃO DO CADERNO")
            for key, value in caderno_info.items():
                detailed_report.append(f"- **{key}:** {value}")
            detailed_report.append("")
        
        # 2. Processar cada página (começando da página 2 do PDF original)
        for page_num, image in enumerate(images):
            original_page_num = page_num + 2  # +2 porque removemos página 1 e índice é 0-based
            logger.info(f"Processando página {original_page_num} (índice {page_num + 1} de {len(images)})")
            
            detailed_report.append(f"---")
            detailed_report.append(f"")
            detailed_report.append(f"## 📄 PÁGINA {original_page_num} (do PDF original)")
            detailed_report.append(f"**Dimensões da imagem:** {image.shape[1]}x{image.shape[0]} pixels")
            detailed_report.append(f"**Tamanho do arquivo convertido:** ~{(image.nbytes / 1024 / 1024):.1f} MB")
            detailed_report.append("")
            
            # Salvar imagem da página completa
            if save_images:
                page_img_path = images_path / f"pagina_{original_page_num:02d}_completa.png"
                cv2.imwrite(str(page_img_path), image)
                detailed_report.append(f"**🖼️ Imagem da página completa:** `{page_img_path.relative_to(output_path)}`")
                detailed_report.append("")
            
            # 3. Detectar regiões de questões
            regions = self.detect_question_regions(image, page_num)
            
            detailed_report.append(f"### 🔍 DETECÇÃO DE REGIÕES")
            detailed_report.append(f"**Regiões de questão detectadas:** {len(regions)}")
            detailed_report.append("")
            
            if not regions:
                detailed_report.append("⚠️ **NENHUMA QUESTÃO DETECTADA NESTA PÁGINA**")
                detailed_report.append("")
                continue
            
            # 4. Extrair texto de cada região
            for region_idx, region in enumerate(regions):
                detailed_report.append(f"### 📝 QUESTÃO DETECTADA #{region_idx + 1}")
                detailed_report.append(f"")
                detailed_report.append(f"#### 📊 METADADOS DA DETECÇÃO")
                detailed_report.append(f"- **Número identificado:** Q{region.question_number}")
                detailed_report.append(f"- **Página original PDF:** {original_page_num}")
                detailed_report.append(f"- **Posição (x,y,largura,altura):** {region.bbox}")
                detailed_report.append(f"- **Confiança da detecção:** {region.confidence:.2f}")
                detailed_report.append("")
                
                # Extrair região da imagem
                x, y, w, h = region.bbox
                roi = image[y:y+h, x:x+w]
                
                # Salvar imagem da região
                if save_images:
                    region_img_path = images_path / f"pagina_{original_page_num:02d}_questao_Q{region.question_number}_{region_idx+1}.png"
                    cv2.imwrite(str(region_img_path), roi)
                    detailed_report.append(f"**🖼️ Imagem da região extraída:** `{region_img_path.relative_to(output_path)}`")
                    detailed_report.append(f"- **Dimensões da região:** {roi.shape[1]}x{roi.shape[0]} pixels")
                    detailed_report.append("")
                
                # Extrair texto com ambos OCRs
                detailed_report.append("#### 🔤 EXTRAÇÃO OCR DETALHADA")
                detailed_report.append("")
                
                # Tesseract
                if self.tesseract_available:
                    try:
                        text_tesseract = pytesseract.image_to_string(roi, config=self.tesseract_config)
                        detailed_report.append("**🔍 TESSERACT OCR:**")
                        detailed_report.append("```")
                        detailed_report.append(text_tesseract.strip() if text_tesseract.strip() else "(nenhum texto detectado)")
                        detailed_report.append("```")
                        detailed_report.append(f"*Caracteres extraídos: {len(text_tesseract)}*")
                        detailed_report.append("")
                    except Exception as e:
                        detailed_report.append(f"**🔍 TESSERACT:** ❌ Erro: {e}")
                        detailed_report.append("")
                
                # EasyOCR
                if self.easyocr_reader:
                    try:
                        ocr_result = self.easyocr_reader.readtext(roi)
                        detailed_report.append("**🤖 EASYOCR (GPU):**")
                        if ocr_result:
                            detailed_report.append("```")
                            for bbox_ocr, text_ocr, conf_ocr in ocr_result:
                                detailed_report.append(f"[Confiança: {conf_ocr:.3f}] {text_ocr}")
                            detailed_report.append("```")
                            total_chars = sum(len(item[1]) for item in ocr_result)
                            detailed_report.append(f"*Caracteres extraídos: {total_chars} | Fragmentos: {len(ocr_result)}*")
                        else:
                            detailed_report.append("```")
                            detailed_report.append("(nenhum texto detectado)")
                            detailed_report.append("```")
                        detailed_report.append("")
                    except Exception as e:
                        detailed_report.append(f"**🤖 EASYOCR:** ❌ Erro: {e}")
                        detailed_report.append("")
                
                # Texto final escolhido
                raw_text = self.extract_text_from_region(image, region)
                
                if not raw_text.strip():
                    detailed_report.append("#### ⚠️ TEXTO FINAL")
                    detailed_report.append("**Status:** Nenhum texto extraído")
                    detailed_report.append("")
                    continue
                
                detailed_report.append("#### ✅ TEXTO FINAL SELECIONADO")
                detailed_report.append("```")
                detailed_report.append(raw_text.strip())
                detailed_report.append("```")
                detailed_report.append(f"*Caracteres finais: {len(raw_text)}*")
                detailed_report.append("")
                
                logger.info(f"Texto extraído Q{region.question_number}: {len(raw_text)} chars")
                
                # 5. Analisar com Ollama se disponível
                ollama_result = None
                if self.preferred_model:
                    detailed_report.append("#### 🧠 ANÁLISE OLLAMA (IA)")
                    ollama_result = self.analyze_with_ollama(raw_text)
                    
                    if ollama_result:
                        detailed_report.append("**✅ RESULTADO ESTRUTURADO:**")
                        detailed_report.append("```json")
                        detailed_report.append(json.dumps(ollama_result, indent=2, ensure_ascii=False))
                        detailed_report.append("```")
                    else:
                        detailed_report.append("**❌ OLLAMA:** Falhou na estruturação (possível erro de formato JSON)")
                    detailed_report.append("")
                
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
                        detailed_report.append("#### 🔧 ESTRUTURAÇÃO BÁSICA (SEM IA)")
                        detailed_report.append(f"- **Questão:** {question.number}")
                        detailed_report.append(f"- **Método:** {question.extraction_method}")
                        detailed_report.append(f"- **Alternativas encontradas:** {list(question.alternatives.keys())}")
                        detailed_report.append("")
                
                if question:
                    extracted_questions.append(question)
                    
                    # Adicionar ao relatório final estruturado
                    detailed_report.append("#### 🎯 QUESTÃO FINAL ESTRUTURADA")
                    detailed_report.append(f"- **Número:** Q{question.number}")
                    detailed_report.append(f"- **Método:** {question.extraction_method}")
                    detailed_report.append(f"- **Confiança:** {question.confidence:.2f}")
                    detailed_report.append("")
                    detailed_report.append("**📝 Enunciado:**")
                    detailed_report.append("```")
                    detailed_report.append(question.text)
                    detailed_report.append("```")
                    detailed_report.append("")
                    detailed_report.append("**🔤 Alternativas:**")
                    for alt_key, alt_text in question.alternatives.items():
                        detailed_report.append(f"- **{alt_key})** {alt_text}")
                    detailed_report.append("")
                else:
                    detailed_report.append("#### ❌ QUESTÃO NÃO ESTRUTURADA")
                    detailed_report.append("Não foi possível estruturar esta questão (possível texto incompleto ou sem alternativas)")
                    detailed_report.append("")
                
                detailed_report.append("---")
        
        # Resumo final
        detailed_report.append("")
        detailed_report.append("# 📊 RESUMO FINAL DA EXTRAÇÃO")
        detailed_report.append("")
        detailed_report.append(f"## 🎯 ESTATÍSTICAS")
        detailed_report.append(f"- **Total de questões extraídas:** {len(extracted_questions)}")
        detailed_report.append(f"- **Páginas processadas:** {len(images)}")
        detailed_report.append(f"- **Expectativa ENEM:** 90-95 questões por caderno")
        detailed_report.append(f"- **Taxa de extração:** {(len(extracted_questions) / 90 * 100):.1f}% do esperado")
        detailed_report.append("")
        
        if extracted_questions:
            question_numbers = [q.number for q in extracted_questions]
            detailed_report.append(f"## 📋 QUESTÕES IDENTIFICADAS")
            detailed_report.append(f"**Números das questões:** {sorted(set(question_numbers))}")
            detailed_report.append("")
        
        # Salvar relatório
        report_path = output_path / f"relatorio_detalhado_{Path(pdf_path).stem}.md"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(detailed_report))
        
        logger.info(f"Relatório detalhado salvo em: {report_path}")
        logger.info(f"Extração concluída: {len(extracted_questions)} questões")
        
        return extracted_questions
    
    def _identify_caderno_info(self, filename: str) -> Dict[str, str]:
        """Identifica informações do caderno ENEM pelo nome do arquivo"""
        info = {}
        
        # Padrões comuns ENEM
        patterns = {
            'Ano': r'(\d{4})',
            'Dia': r'D(\d)',
            'Aplicação': r'(PV|PPL|reaplicacao)',
            'Caderno': r'CD(\d+)',
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, filename)
            if match:
                info[key] = match.group(1)
        
        return info
    
    def _basic_structure_extraction(self, text: str, region: QuestionRegion) -> Optional[ExtractedQuestion]:
        """Estruturação básica sem Ollama"""
        # Regex simples para alternativas
        alternatives = {}
        for letter in ['A', 'B', 'C', 'D', 'E']:
            pattern = fr'{letter}\)(.*?)(?=[BCDE]\)|$)'
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
    
    def compare_with_traditional(self, pdf_path: str, generate_detailed_report: bool = True) -> Dict:
        """Compara resultados OCR vs extração textual tradicional"""
        # Extração OCR com relatório detalhado
        if generate_detailed_report:
            ocr_questions = self.extract_questions_from_pdf(pdf_path, save_images=True, output_dir="reports")
        else:
            ocr_questions = self.extract_questions_from_pdf(pdf_path, save_images=False, output_dir="reports")
        
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

def test_gpu_setup():
    """Função para testar configuração de GPU"""
    print("🔧 TESTE DE CONFIGURAÇÃO GPU")
    print("="*40)
    
    # Teste PyTorch CUDA
    try:
        import torch
        print(f"✅ PyTorch versão: {torch.__version__}")
        print(f"✅ CUDA disponível: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"✅ GPU: {torch.cuda.get_device_name(0)}")
            print(f"✅ VRAM total: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
        print()
    except ImportError:
        print("❌ PyTorch não instalado")
    
    # Teste EasyOCR com GPU
    print("🔍 TESTANDO EASYOCR COM GPU...")
    try:
        import easyocr
        reader = easyocr.Reader(['pt'], gpu=True)
        print("✅ EasyOCR GPU inicializado com sucesso")
        
        # Teste rápido
        import numpy as np
        test_image = np.ones((100, 300, 3), dtype=np.uint8) * 255
        results = reader.readtext(test_image)
        print(f"✅ Teste de extração concluído: {len(results)} resultados")
        
    except Exception as e:
        print(f"❌ Erro no EasyOCR GPU: {e}")
        print("   Tentando fallback CPU...")
        try:
            reader = easyocr.Reader(['pt'], gpu=False)
            print("✅ EasyOCR CPU funcionando")
        except Exception as e2:
            print(f"❌ Erro completo no EasyOCR: {e2}")
    
    print("\n" + "="*40)

def main():
    """Função principal para teste do protótipo"""
    # Teste GPU primeiro
    test_gpu_setup()
    
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