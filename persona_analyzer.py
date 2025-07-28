"""
Core persona-driven document analysis engine
"""

import os
import re
import json
import logging
from typing import List, Dict, Any, Tuple
from datetime import datetime
from collections import defaultdict

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import sent_tokenize, word_tokenize

# Import Round 1A extractor
from pdf_extractor import PDFExtractor
from semantic_matcher import SemanticMatcher
from relevance_scorer import RelevanceScorer

class PersonaDocumentAnalyzer:
    """Main persona-driven document analysis engine."""
    
    def __init__(self):
        self.pdf_extractor = PDFExtractor()
        self.semantic_matcher = SemanticMatcher()
        self.relevance_scorer = RelevanceScorer()
        self.processed_documents = {}
        
        # Initialize NLTK data
        self._init_nltk()
    
    def _init_nltk(self):
        """Initialize NLTK resources."""
        try:
            nltk.data.find('tokenizers/punkt')
            nltk.data.find('corpora/stopwords')
        except LookupError:
            nltk.download('punkt', quiet=True)
            nltk.download('stopwords', quiet=True)
    
    def analyze_documents(self, input_config: Dict[str, Any]) -> Dict[str, Any]:
        """Main analysis pipeline."""
        
        # Extract configuration
        documents = input_config['documents']
        persona = input_config['persona']
        job_to_be_done = input_config['job_to_be_done']
        
        logging.info(f"Analyzing {len(documents)} documents for {persona['role']}")
        
        # Step 1: Extract content from all PDFs
        all_sections = self._extract_all_documents(documents)
        
        # Step 2: Analyze persona requirements
        persona_profile = self._analyze_persona(persona, job_to_be_done)
        
        # Step 3: Match sections to persona needs
        relevant_sections = self._match_sections_to_persona(all_sections, persona_profile)
        
        # Step 4: Rank sections by importance
        ranked_sections = self._rank_sections(relevant_sections, persona_profile)
        
        # Step 5: Extract detailed subsections
        subsection_analysis = self._extract_subsections(ranked_sections[:20])  # Top 20 sections
        
        # Step 6: Format output
        result = self._format_output(
            documents, persona, job_to_be_done,
            ranked_sections, subsection_analysis
        )
        
        return result
    
    def _extract_all_documents(self, documents: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """Extract structured content from all PDFs."""
        all_sections = []
        
        for doc_info in documents:
            filename = doc_info['filename']
            pdf_path = f"/app/input/{filename}"
            
            if not os.path.exists(pdf_path):
                logging.warning(f"PDF not found: {pdf_path}")
                continue
            
            logging.info(f"Extracting content from {filename}")
            
            # Use Round 1A extractor for basic structure
            outline = self.pdf_extractor.extract_outline(pdf_path)
            
            # Extract full text content with sections
            sections = self._extract_detailed_sections(pdf_path, outline)
            
            # Add document info to each section
            for section in sections:
                section['document'] = filename
                section['document_title'] = doc_info.get('title', filename)
            
            all_sections.extend(sections)
            self.processed_documents[filename] = sections
        
        logging.info(f"Extracted {len(all_sections)} total sections")
        return all_sections
    
    def _extract_detailed_sections(self, pdf_path: str, outline: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract detailed text content for each section."""
        sections = []
        
        try:
            # Extract full text with page information
            full_text_by_page = self.pdf_extractor.extract_full_text_by_page(pdf_path)
            
            # Process title
            if outline['title']:
                sections.append({
                    'section_title': outline['title'],
                    'section_type': 'title',
                    'page_number': 0,
                    'text_content': outline['title'],
                    'heading_level': 'title'
                })
            
            # Process outline headings with associated content
            for heading in outline['outline']:
                # Extract text content for this section
                section_text = self._extract_section_text(
                    full_text_by_page, 
                    heading['page'], 
                    heading['text']
                )
                
                sections.append({
                    'section_title': heading['text'],
                    'section_type': 'heading',
                    'page_number': heading['page'],
                    'text_content': section_text,
                    'heading_level': heading['level']
                })
            
            # Extract additional content sections (paragraphs, lists, etc.)
            content_sections = self._extract_content_sections(full_text_by_page)
            sections.extend(content_sections)
            
        except Exception as e:
            logging.error(f"Error extracting sections from {pdf_path}: {e}")
        
        return sections
    
    def _extract_section_text(self, full_text_by_page: Dict[int, str], 
                            start_page: int, heading_text: str) -> str:
        """Extract text content associated with a heading."""
        
        # Get text from current page
        page_text = full_text_by_page.get(start_page, "")
        
        # Find heading position and extract following content
        lines = page_text.split('\n')
        section_text = []
        found_heading = False
        
        for line in lines:
            line = line.strip()
            if heading_text.lower() in line.lower():
                found_heading = True
                continue
            
            if found_heading:
                # Stop at next heading or empty line patterns
                if (len(line) > 0 and 
                    not re.match(r'^[A-Z\s]{10,}$', line) and  # Not all caps header
                    not re.match(r'^\d+\.', line)):  # Not numbered section
                    section_text.append(line)
                elif len(section_text) > 3:  # Got some content
                    break
        
        # Also check next page if current section is short
        if len(' '.join(section_text)) < 200 and start_page + 1 in full_text_by_page:
            next_page_text = full_text_by_page[start_page + 1]
            next_lines = next_page_text.split('\n')[:10]  # First 10 lines
            section_text.extend([line.strip() for line in next_lines if line.strip()])
        
        return ' '.join(section_text)
    
    def _extract_content_sections(self, full_text_by_page: Dict[int, str]) -> List[Dict[str, Any]]:
        """Extract additional content sections (non-heading text blocks)."""
        content_sections = []
        
        for page_num, page_text in full_text_by_page.items():
            # Split into paragraphs
            paragraphs = re.split(r'\n\s*\n', page_text)
            
            for i, paragraph in enumerate(paragraphs):
                paragraph = paragraph.strip()
                
                # Skip short paragraphs or headers
                if len(paragraph) < 100:
                    continue
                
                # Skip if looks like heading (all caps, short, etc.)
                if (paragraph.isupper() and len(paragraph) < 50) or \
                   re.match(r'^\d+\.?\s*[A-Z]', paragraph):
                    continue
                
                content_sections.append({
                    'section_title': f"Content Block {page_num}-{i}",
                    'section_type': 'content',
                    'page_number': page_num,
                    'text_content': paragraph,
                    'heading_level': 'content'
                })
        
        return content_sections
    
    def _analyze_persona(self, persona: Dict[str, str], 
                        job_to_be_done: Dict[str, str]) -> Dict[str, Any]:
        """Analyze persona to understand their needs and priorities."""
        
        role = persona['role']
        task = job_to_be_done['task']
        
        # Extract key terms and concepts
        persona_keywords = self._extract_keywords(role)
        task_keywords = self._extract_keywords(task)
        
        # Determine focus areas based on persona type
        focus_areas = self._determine_focus_areas(role, task)
        
        return {
            'role': role,
            'task': task,
            'persona_keywords': persona_keywords,
            'task_keywords': task_keywords,
            'focus_areas': focus_areas,
            'priority_weights': self._get_priority_weights(role)
        }
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract important keywords from text."""
        # Basic keyword extraction
        words = word_tokenize(text.lower())
        stop_words = set(stopwords.words('english'))
        
        # Filter meaningful words
        keywords = [word for word in words 
                   if word.isalpha() and 
                   len(word) > 3 and 
                   word not in stop_words]
        
        return keywords
    
    def _determine_focus_areas(self, role: str, task: str) -> List[str]:
        """Determine focus areas based on role and task."""
        
        role_lower = role.lower()
        task_lower = task.lower()
        
        focus_areas = []
        
        # Role-based focus areas
        if 'researcher' in role_lower or 'phd' in role_lower:
            focus_areas.extend(['methodology', 'results', 'data', 'analysis', 'conclusions'])
        elif 'student' in role_lower:
            focus_areas.extend(['concepts', 'examples', 'definitions', 'practice'])
        elif 'analyst' in role_lower:
            focus_areas.extend(['trends', 'metrics', 'performance', 'comparison'])
        elif 'manager' in role_lower or 'professional' in role_lower:
            focus_areas.extend(['process', 'best practices', 'guidelines', 'implementation'])
        
        # Task-based focus areas
        if 'review' in task_lower:
            focus_areas.extend(['summary', 'overview', 'key points'])
        elif 'analyze' in task_lower:
            focus_areas.extend(['data', 'statistics', 'comparison'])
        elif 'prepare' in task_lower or 'plan' in task_lower:
            focus_areas.extend(['steps', 'requirements', 'guidelines'])
        
        return list(set(focus_areas))  # Remove duplicates
    
    def _get_priority_weights(self, role: str) -> Dict[str, float]:
        """Get priority weights for different content types based on role."""
        
        role_lower = role.lower()
        
        if 'researcher' in role_lower:
            return {
                'methodology': 0.3,
                'results': 0.25,
                'introduction': 0.15,
                'conclusion': 0.2,
                'references': 0.1
            }
        elif 'student' in role_lower:
            return {
                'concepts': 0.35,
                'examples': 0.25,
                'summary': 0.2,
                'exercises': 0.2
            }
        elif 'analyst' in role_lower:
            return {
                'data': 0.3,
                'trends': 0.25,
                'metrics': 0.25,
                'conclusions': 0.2
            }
        else:
            return {
                'overview': 0.25,
                'details': 0.25,
                'examples': 0.25,
                'summary': 0.25
            }
    
    def _match_sections_to_persona(self, sections: List[Dict[str, Any]], 
                                 persona_profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Match document sections to persona requirements."""
        
        relevant_sections = []
        
        for section in sections:
            # Calculate relevance score
            relevance_score = self.semantic_matcher.calculate_relevance(
                section, persona_profile
            )
            
            if relevance_score > 0.3:  # Threshold for relevance
                section['relevance_score'] = relevance_score
                relevant_sections.append(section)
        
        logging.info(f"Found {len(relevant_sections)} relevant sections")
        return relevant_sections
    
    def _rank_sections(self, sections: List[Dict[str, Any]], 
                      persona_profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Rank sections by importance to the persona."""
        
        # Calculate comprehensive scores
        for section in sections:
            importance_score = self.relevance_scorer.calculate_importance(
                section, persona_profile
            )
            section['importance_score'] = importance_score
        
        # Sort by importance score
        ranked_sections = sorted(sections, 
                               key=lambda x: x['importance_score'], 
                               reverse=True)
        
        # Assign importance ranks
        for i, section in enumerate(ranked_sections):
            section['importance_rank'] = i + 1
        
        return ranked_sections
    
    def _extract_subsections(self, top_sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract detailed subsections from top-ranked sections."""
        
        subsections = []
        
        for section in top_sections:
            # Split section text into meaningful subsections
            text_content = section['text_content']
            
            # Split by sentences for detailed analysis
            sentences = sent_tokenize(text_content)
            
            # Group sentences into meaningful chunks
            chunks = self._group_sentences_into_chunks(sentences)
            
            for chunk in chunks:
                if len(chunk.strip()) > 50:  # Minimum chunk size
                    subsections.append({
                        'document': section['document'],
                        'section_title': section['section_title'],
                        'refined_text': chunk.strip(),
                        'page_number': section['page_number'],
                        'parent_importance_rank': section['importance_rank']
                    })
        
        return subsections
    
    def _group_sentences_into_chunks(self, sentences: List[str], 
                                   max_chunk_size: int = 300) -> List[str]:
        """Group sentences into meaningful chunks."""
        
        chunks = []
        current_chunk = []
        current_length = 0
        
        for sentence in sentences:
            sentence_length = len(sentence)
            
            if current_length + sentence_length > max_chunk_size and current_chunk:
                chunks.append(' '.join(current_chunk))
                current_chunk = [sentence]
                current_length = sentence_length
            else:
                current_chunk.append(sentence)
                current_length += sentence_length
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks
    
    def _format_output(self, documents: List[Dict[str, str]], 
                      persona: Dict[str, str], 
                      job_to_be_done: Dict[str, str],
                      ranked_sections: List[Dict[str, Any]], 
                      subsection_analysis: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Format final output according to specification."""
        
        return {
            "metadata": {
                "input_documents": [doc['filename'] for doc in documents],
                "persona": persona['role'],
                "job_to_be_done": job_to_be_done['task'],
                "processing_timestamp": datetime.utcnow().isoformat(),
                "total_sections_analyzed": len(ranked_sections),
                "top_sections_selected": min(50, len(ranked_sections))
            },
            "extracted_sections": [
                {
                    "document": section['document'],
                    "section_title": section['section_title'],
                    "importance_rank": section['importance_rank'],
                    "page_number": section['page_number'],
                    "heading_level": section.get('heading_level', 'unknown'),
                    "relevance_score": round(section.get('relevance_score', 0), 3)
                }
                for section in ranked_sections[:50]  # Top 50 sections
            ],
            "subsection_analysis": subsection_analysis[:100]  # Top 100 subsections
        }
