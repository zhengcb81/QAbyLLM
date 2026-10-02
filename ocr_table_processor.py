#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OCR和表格处理器
专门处理图片OCR和表格提取功能
"""

import os
import logging
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import tempfile
import base64
from enum import Enum

logger = logging.getLogger(__name__)

class OCREngine(Enum):
    """OCR引擎枚举"""
    TESSERACT = "tesseract"
    EASYOCR = "easyocr"
    PADDLEOCR = "paddleocr"

class TableEngine(Enum):
    """表格识别引擎枚举"""
    TABULA = "tabula"
    CAMELOT = "camelot"
    EXCALIBUR = "excalibur"

class OCRTableProcessor:
    """OCR和表格处理器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.ocr_engine = OCREngine(self.config.get('ocr', {}).get('engine', 'tesseract'))
        self.table_engine = TableEngine(self.config.get('tables', {}).get('engine', 'tabula'))
        self._init_engines()
    
    def _init_engines(self) -> None:
        """初始化引擎"""
        try:
            if self.ocr_engine == OCREngine.TESSERACT:
                self._init_tesseract()
            elif self.ocr_engine == OCREngine.EASYOCR:
                self._init_easyocr()
            elif self.ocr_engine == OCREngine.PADDLEOCR:
                self._init_paddleocr()
                
            if self.table_engine == TableEngine.TABULA:
                self._init_tabula()
            elif self.table_engine == TableEngine.CAMELOT:
                self._init_camelot()
                
        except ImportError as e:
            logger.warning(f"引擎初始化失败，某些功能可能不可用: {e}")
    
    def _init_tesseract(self) -> None:
        """初始化Tesseract OCR"""
        try:
            import pytesseract
            from PIL import Image
            self.tesseract_available = True
            logger.info("Tesseract OCR引擎初始化成功")
        except ImportError:
            self.tesseract_available = False
            logger.warning("Tesseract不可用，请安装pytesseract和Pillow")
    
    def _init_easyocr(self) -> None:
        """初始化EasyOCR"""
        try:
            import easyocr
            self.easyocr_reader = easyocr.Reader(['ch_sim', 'en'])
            self.easyocr_available = True
            logger.info("EasyOCR引擎初始化成功")
        except ImportError:
            self.easyocr_available = False
            logger.warning("EasyOCR不可用，请安装easyocr")
    
    def _init_paddleocr(self) -> None:
        """初始化PaddleOCR"""
        try:
            from paddleocr import PaddleOCR
            self.paddleocr = PaddleOCR(use_angle_cls=True, lang="ch")
            self.paddleocr_available = True
            logger.info("PaddleOCR引擎初始化成功")
        except ImportError:
            self.paddleocr_available = False
            logger.warning("PaddleOCR不可用，请安装paddleocr")
    
    def _init_tabula(self) -> None:
        """初始化Tabula"""
        try:
            import tabula
            self.tabula_available = True
            logger.info("Tabula表格引擎初始化成功")
        except ImportError:
            self.tabula_available = False
            logger.warning("Tabula不可用，请安装tabula-py")
    
    def _init_camelot(self) -> None:
        """初始化Camelot"""
        try:
            import camelot
            self.camelot_available = True
            logger.info("Camelot表格引擎初始化成功")
        except ImportError:
            self.camelot_available = False
            logger.warning("Camelot不可用，请安装camelot-py")
    
    def extract_text_from_image(self, image_path: str, **kwargs) -> Dict[str, Any]:
        """从图片提取文本"""
        try:
            if not os.path.exists(image_path):
                return self._create_error_result("图片文件不存在")
            
            start_time = self._get_current_time()
            
            if self.ocr_engine == OCREngine.TESSERACT and self.tesseract_available:
                text = self._tesseract_ocr(image_path, **kwargs)
            elif self.ocr_engine == OCREngine.EASYOCR and self.easyocr_available:
                text = self._easyocr_ocr(image_path, **kwargs)
            elif self.ocr_engine == OCREngine.PADDLEOCR and self.paddleocr_available:
                text = self._paddleocr_ocr(image_path, **kwargs)
            else:
                return self._create_error_result("没有可用的OCR引擎")
            
            processing_time = self._get_current_time() - start_time
            
            return {
                'success': True,
                'text': text,
                'engine': self.ocr_engine.value,
                'processing_time_seconds': processing_time,
                'error': None
            }
            
        except Exception as e:
            logger.error(f"OCR处理失败: {e}")
            return self._create_error_result(f"OCR处理失败: {e}")
    
    def extract_tables_from_pdf(self, pdf_path: str, **kwargs) -> Dict[str, Any]:
        """从PDF提取表格"""
        try:
            if not os.path.exists(pdf_path):
                return self._create_error_result("PDF文件不存在")
            
            start_time = self._get_current_time()
            
            if self.table_engine == TableEngine.TABULA and self.tabula_available:
                tables = self._tabula_extract(pdf_path, **kwargs)
            elif self.table_engine == TableEngine.CAMELOT and self.camelot_available:
                tables = self._camelot_extract(pdf_path, **kwargs)
            else:
                return self._create_error_result("没有可用的表格提取引擎")
            
            processing_time = self._get_current_time() - start_time
            
            return {
                'success': True,
                'tables': tables,
                'engine': self.table_engine.value,
                'processing_time_seconds': processing_time,
                'error': None
            }
            
        except Exception as e:
            logger.error(f"表格提取失败: {e}")
            return self._create_error_result(f"表格提取失败: {e}")
    
    def _tesseract_ocr(self, image_path: str, **kwargs) -> str:
        """使用Tesseract OCR"""
        import pytesseract
        from PIL import Image
        
        # 打开图片
        image = Image.open(image_path)
        
        # 配置参数
        config = kwargs.get('tesseract_config', '--psm 6')
        lang = kwargs.get('language', 'chi_sim+eng')
        
        # 执行OCR
        text = pytesseract.image_to_string(image, config=config, lang=lang)
        
        return text.strip()
    
    def _easyocr_ocr(self, image_path: str, **kwargs) -> str:
        """使用EasyOCR"""
        result = self.easyocr_reader.readtext(image_path)
        
        # 提取文本
        text = '\n'.join([item[1] for item in result])
        
        return text
    
    def _paddleocr_ocr(self, image_path: str, **kwargs) -> str:
        """使用PaddleOCR"""
        result = self.paddleocr.ocr(image_path, cls=True)
        
        # 提取文本
        text_lines = []
        for line in result:
            for word_info in line:
                text_lines.append(word_info[1][0])
        
        return '\n'.join(text_lines)
    
    def _tabula_extract(self, pdf_path: str, **kwargs) -> List[Dict[str, Any]]:
        """使用Tabula提取表格"""
        import tabula
        
        # 提取参数
        pages = kwargs.get('pages', 'all')
        multiple_tables = kwargs.get('multiple_tables', True)
        
        # 提取表格
        tables = tabula.read_pdf(pdf_path, 
                               pages=pages,
                               multiple_tables=multiple_tables,
                               lattice=kwargs.get('lattice', True))
        
        # 转换为标准格式
        result = []
        for i, table in enumerate(tables):
            result.append({
                'table_index': i,
                'data': table.to_dict('records'),
                'shape': table.shape,
                'columns': list(table.columns)
            })
        
        return result
    
    def _camelot_extract(self, pdf_path: str, **kwargs) -> List[Dict[str, Any]]:
        """使用Camelot提取表格"""
        import camelot
        
        # 提取参数
        pages = kwargs.get('pages', '1-end')
        flavor = kwargs.get('flavor', 'lattice')
        
        # 提取表格
        tables = camelot.read_pdf(pdf_path, 
                                pages=pages, 
                                flavor=flavor)
        
        # 转换为标准格式
        result = []
        for i, table in enumerate(tables):
            result.append({
                'table_index': i,
                'data': table.df.to_dict('records'),
                'shape': table.shape,
                'accuracy': table.accuracy,
                'page': table.page
            })
        
        return result
    
    def extract_text_from_pdf(self, pdf_path: str, **kwargs) -> Dict[str, Any]:
        """从PDF提取文本（包含OCR）"""
        try:
            # 首先尝试直接文本提取
            from pdfminer.high_level import extract_text
            
            start_time = self._get_current_time()
            text = extract_text(pdf_path)
            
            # 如果文本太少，尝试OCR
            if len(text.strip()) < 100:
                logger.info("文本提取结果较少，尝试使用OCR")
                
                # 将PDF转换为图片
                images = self._pdf_to_images(pdf_path)
                ocr_texts = []
                
                for img_path in images:
                    ocr_result = self.extract_text_from_image(img_path, **kwargs)
                    if ocr_result['success']:
                        ocr_texts.append(ocr_result['text'])
                    # 清理临时图片
                    os.remove(img_path)
                
                text = '\n\n'.join(ocr_texts)
            
            processing_time = self._get_current_time() - start_time
            
            return {
                'success': True,
                'text': text,
                'processing_time_seconds': processing_time,
                'used_ocr': len(text.strip()) > 100,  # 标记是否使用了OCR
                'error': None
            }
            
        except Exception as e:
            logger.error(f"PDF文本提取失败: {e}")
            return self._create_error_result(f"PDF文本提取失败: {e}")
    
    def _pdf_to_images(self, pdf_path: str, dpi: int = 300) -> List[str]:
        """将PDF转换为图片"""
        try:
            from pdf2image import convert_from_path
            
            images = convert_from_path(pdf_path, dpi=dpi)
            temp_files = []
            
            for i, image in enumerate(images):
                temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
                image.save(temp_file.name, 'JPEG')
                temp_files.append(temp_file.name)
                temp_file.close()
            
            return temp_files
            
        except ImportError:
            raise Exception("需要安装pdf2image来转换PDF为图片")
    
    def batch_ocr_process(self, image_folder: str, **kwargs) -> List[Dict[str, Any]]:
        """批量处理图片OCR"""
        results = []
        
        if not os.path.exists(image_folder):
            logger.error(f"图片文件夹不存在: {image_folder}")
            return results
        
        # 支持的图片格式
        image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif']
        
        for root, dirs, files in os.walk(image_folder):
            for file in files:
                if any(file.lower().endswith(ext) for ext in image_extensions):
                    image_path = os.path.join(root, file)
                    result = self.extract_text_from_image(image_path, **kwargs)
                    result['file_path'] = image_path
                    results.append(result)
        
        return results
    
    def _create_error_result(self, error_msg: str) -> Dict[str, Any]:
        """创建错误结果"""
        return {
            'success': False,
            'error': error_msg,
            'text': '',
            'tables': []
        }
    
    def _get_current_time(self) -> float:
        """获取当前时间"""
        import time
        return time.time()

# 测试代码
if __name__ == "__main__":
    # 创建处理器
    processor = OCRTableProcessor({
        'ocr': {'engine': 'tesseract'},
        'tables': {'engine': 'tabula'}
    })
    
    # 测试OCR功能（需要实际图片文件）
    print("=== OCR功能测试 ===")
    # result = processor.extract_text_from_image("test_image.jpg")
    # print(f"成功: {result['success']}, 文本长度: {len(result.get('text', ''))}")
    
    # 测试表格提取（需要实际PDF文件）
    print("\n=== 表格提取测试 ===")
    # result = processor.extract_tables_from_pdf("test_document.pdf")
    # print(f"成功: {result['success']}, 表格数量: {len(result.get('tables', []))}")
    
    print("\n=== 引擎状态 ===")
    print(f"Tesseract可用: {processor.tesseract_available}")
    print(f"EasyOCR可用: {processor.easyocr_available}")
    print(f"PaddleOCR可用: {processor.paddleocr_available}")
    print(f"Tabula可用: {processor.tabula_available}")
    print(f"Camelot可用: {processor.camelot_available}")