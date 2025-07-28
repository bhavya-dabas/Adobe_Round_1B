"""
Enhanced PDF extraction engine building on Round 1A
"""

import re
import statistics
from collections import defaultdict, Counter
from typing import List, Dict, Any, Tuple, Optional

from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextLine, LTTextBox, LTChar, LTPage
import pytesseract
from PIL import Image
import fitz  # PyMuPDF

class PDFExtractor:
    """Enhanced PDF extraction engine with full text capabilities."""
    
    def __init__(self):
        self.font_stats = {}
        self.page_count = 0
    
    def extract_outline(self, pdf_path: str) -> Dict[str, Any]:
        """Extract structured outline (from Round 1A)."""
        
        lines = self._extract_text_lines(pdf_path)
        
        if not lines:
            lines = self._ocr_fallback(pdf_path)
        
        title = self._detect_title(lines)
        headings = self._classify_headings(lines)
        outline = self._assign_hierarchy(headings)
        
        return {
            "title": title,
            "outline": outline
        }
    
    def extract_full_text_by_page(self, pdf_path: str) -> Dict[int, str]:
        """Extract full text content organized by page."""
        
        full_text = {}
        
        try:
            for page_num, page in enumerate(extract_pages(pdf_path), 0):
                page_text = []
                
                for element in page:
                    if isinstance(element, (LTTextBox, LTTextLine)):
                        text = element.get_text().strip()
                        if text:
                            page_text.append(text)
                
                full_text[page_num] = '\n'.join(page_text)
        
        except Exception as e:
            # Fallback to PyMuPDF
            try:
                doc = fitz.open(pdf_path)
                for page_num in range(doc.page_count):
                    page = doc[page_num]
                    full_text[page_num] = page.get_text()
                doc.close()
            except Exception as e2:
                print(f"Error extracting full text: {e2}")
        
        return full_text
    
    def _extract_text_lines(self, pdf_path: str) -> List[Dict[str, Any]]:
        """Extract text lines with metadata (from Round 1A)."""
        lines = []
        font_sizes = []
        
        try:
            for page_num, page in enumerate(extract_pages(pdf_path), 0):
                self.page_count = page_num + 1
                
                for element in page:
                    if isinstance(element, (LTTextBox, LTTextLine)):
                        text = element.get_text().strip()
                        if not text or len(text) < 2:
                            continue
                        
                        font_info = self._get_font_info(element)
                        if not font_info:
                            continue
                        
                        font_sizes.append(font_info['size'])
                        
                        line_data = {
                            'text': self._clean_text(text),
                            'page': page_num,
                            'font_size': font_info['size'],
                            'font_name': font_info['name'],
                            'is_bold': font_info['is_bold'],
                            'is_italic': font_info['is_italic'],
                            'x0': element.x0,
                            'y0': element.y0,
                            'x1': element.x1,
                            'y1': element.y1,
                            'char_count': len(text)
                        }
                        
                        lines.append(line_data)
        
        except Exception as e:
            print(f"Error extracting text: {e}")
            return []
        
        if font_sizes:
            self.font_stats = {
                'median': statistics.median(font_sizes),
                'mean': statistics.mean(font_sizes),
                'mode': Counter(font_sizes).most_common(1)[0][0]
            }
        
        return lines
    
    def _get_font_info(self, element) -> Optional[Dict[str, Any]]:
        """Extract font information."""
        try:
            for line in element:
                if hasattr(line, '_objs'):
                    for char in line._objs:
                        if isinstance(char, LTChar):
                            return {
                                'size': round(char.height, 1),
                                'name': char.fontname or '',
                                'is_bold': 'bold' in (char.fontname or '').lower(),
                                'is_italic': 'italic' in (char.fontname or '').lower()
                            }
            
            return {
                'size': round(element.height * 0.7, 1),
                'name': '',
                'is_bold': False,
                'is_italic': False
            }
            
        except Exception:
            return None
    
    def _clean_text(self, text: str) -> str:
        """Clean extracted text."""
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def _ocr_fallback(self, pdf_path: str) -> List[Dict[str, Any]]:
        """OCR fallback for scanned PDFs."""
        lines = []
        
        try:
            doc = fitz.open(pdf_path)
            
            for page_num in range(min(doc.page_count, 50)):
                page = doc[page_num]
                
                text_content = page.get_text()
                if len(text_content.strip()) > 20:
                    continue
                
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                
                ocr_data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
                
                for i, text in enumerate(ocr_data['text']):
                    if not text.strip():
                        continue
                    
                    confidence = int(ocr_data['conf'][i])
                    if confidence < 30:
                        continue
                    
                    height = int(ocr_data['height'][i])
                    estimated_font_size = max(8, min(height * 0.75, 72))
                    
                    line_data = {
                        'text': self._clean_text(text),
                        'page': page_num,
                        'font_size': estimated_font_size,
                        'font_name': '',
                        'is_bold': False,
                        'is_italic': False,
                        'x0': int(ocr_data['left'][i]),
                        'y0': int(ocr_data['top'][i]),
                        'x1': int(ocr_data['left'][i]) + int(ocr_data['width'][i]),
                        'y1': int(ocr_data['top'][i]) + int(ocr_data['height'][i]),
                        'char_count': len(text)
                    }
                    
                    lines.append(line_data)
            
            doc.close()
            
        except Exception as e:
            print(f"OCR fallback failed: {e}")
        
        return lines
    
    def _detect_title(self, lines: List[Dict[str, Any]]) -> str:
        """Detect document title."""
        if not lines:
            return ""
        
        first_page_lines = [line for line in lines if line['page'] == 0]
        
        if not first_page_lines:
            return ""
        
        first_page_lines.sort(key=lambda x: -x['y0'])
        
        candidates = []
        
        for line in first_page_lines[:10]:
            text = line['text']
            
            if (len(text) > 5 and 
                len(text) < 200 and 
                not text.lower().startswith(('page', 'chapter', 'section')) and
                line['font_size'] >= self.font_stats.get('median', 12)):
                
                candidates.append((text, line['font_size'], line['y0']))
        
        if candidates:
            candidates.sort(key=lambda x: (-x[1], -x[2]))
            return candidates[0][0]
        
        for line in first_page_lines:
            if len(line['text']) > 10:
                return line['text']
        
        return ""
    
    def _classify_headings(self, lines: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Classify headings."""
        headings = []
        
        if not self.font_stats:
            return headings
        
        base_font_size = self.font_stats.get('mode', 12)
        
        for line in lines:
            if self._is_likely_heading(line, base_font_size):
                headings.append({
                    'text': line['text'],
                    'page': line['page'],
                    'font_size': line['font_size'],
                    'y_position': line['y0']
                })
        
        return headings
    
    def _is_likely_heading(self, line: Dict[str, Any], base_font_size: float) -> bool:
        """Check if line is likely a heading."""
        text = line['text']
        font_size = line['font_size']
        
        if len(text) < 3 or len(text) > 200:
            return False
        
        if font_size < base_font_size * 1.05:
            return False
        
        if re.match(r'^\d+$', text):
            return False
        
        score = 0
        
        if text.istitle():
            score += 2
        
        if line.get('is_bold', False):
            score += 2
            
        if re.match(r'^\d+\.?\s+', text):
            score += 2
        
        if text.isupper() and len(text) < 50:
            score += 1
        
        return score >= 2
    
    def _assign_hierarchy(self, headings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Assign heading hierarchy."""
        if not headings:
            return []
        
        font_sizes = sorted(set(h['font_size'] for h in headings), reverse=True)
        
        size_to_level = {}
        for i, size in enumerate(font_sizes[:3]):
            size_to_level[size] = f"H{i + 1}"
        
        outline = []
        for heading in headings:
            level = size_to_level.get(heading['font_size'])
            if level:
                outline.append({
                    'level': level,
                    'text': heading['text'],
                    'page': heading['page']
                })
        
        outline.sort(key=lambda x: (x['page'], x.get('y_position', 0)))
        
        return outline
