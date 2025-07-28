"""
Semantic matching engine for persona-content alignment
"""

import re
import numpy as np
from typing import Dict, Any, List
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import logging

class SemanticMatcher:
    """Semantic matching between content and persona requirements."""
    
    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2),
            lowercase=True
        )
        self.persona_keywords_cache = {}
    
    def calculate_relevance(self, section: Dict[str, Any], 
                          persona_profile: Dict[str, Any]) -> float:
        """Calculate relevance score between section and persona."""
        
        # Combine section text
        section_text = self._prepare_section_text(section)
        
        # Prepare persona text
        persona_text = self._prepare_persona_text(persona_profile)
        
        # Calculate semantic similarity
        similarity_score = self._calculate_semantic_similarity(section_text, persona_text)
        
        # Calculate keyword overlap
        keyword_score = self._calculate_keyword_overlap(section, persona_profile)
        
        # Calculate focus area alignment
        focus_score = self._calculate_focus_alignment(section, persona_profile)
        
        # Combine scores with weights
        final_score = (
            0.4 * similarity_score +
            0.3 * keyword_score +
            0.3 * focus_score
        )
        
        return min(1.0, final_score)
    
    def _prepare_section_text(self, section: Dict[str, Any]) -> str:
        """Prepare section text for analysis."""
        parts = []
        
        # Add section title (higher weight)
        title = section.get('section_title', '')
        if title:
            parts.extend([title] * 3)  # Repeat for emphasis
        
        # Add text content
        content = section.get('text_content', '')
        if content:
            parts.append(content)
        
        return ' '.join(parts)
    
    def _prepare_persona_text(self, persona_profile: Dict[str, Any]) -> str:
        """Prepare persona requirements text."""
        parts = []
        
        # Add role (high weight)
        role = persona_profile.get('role', '')
        parts.extend([role] * 2)
        
        # Add task (high weight)
        task = persona_profile.get('task', '')
        parts.extend([task] * 2)
        
        # Add keywords
        keywords = persona_profile.get('persona_keywords', [])
        task_keywords = persona_profile.get('task_keywords', [])
        parts.extend(keywords)
        parts.extend(task_keywords)
        
        # Add focus areas
        focus_areas = persona_profile.get('focus_areas', [])
        parts.extend(focus_areas)
        
        return ' '.join(parts)
    
    def _calculate_semantic_similarity(self, text1: str, text2: str) -> float:
        """Calculate TF-IDF cosine similarity."""
        
        try:
            # Prepare texts
            texts = [text1, text2]
            
            # Vectorize
            tfidf_matrix = self.vectorizer.fit_transform(texts)
            
            # Calculate similarity
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            
            return float(similarity)
            
        except Exception as e:
            logging.warning(f"Error calculating semantic similarity: {e}")
            return 0.0
    
    def _calculate_keyword_overlap(self, section: Dict[str, Any], 
                                 persona_profile: Dict[str, Any]) -> float:
        """Calculate keyword overlap score."""
        
        # Extract section keywords
        section_text = section.get('text_content', '') + ' ' + section.get('section_title', '')
        section_words = set(re.findall(r'\b\w{4,}\b', section_text.lower()))
        
        # Get persona keywords
        persona_keywords = set(persona_profile.get('persona_keywords', []))
        task_keywords = set(persona_profile.get('task_keywords', []))
        all_persona_keywords = persona_keywords.union(task_keywords)
        
        if not all_persona_keywords:
            return 0.0
        
        # Calculate overlap
        overlap = len(section_words.intersection(all_persona_keywords))
        max_possible = len(all_persona_keywords)
        
        return overlap / max_possible if max_possible > 0 else 0.0
    
    def _calculate_focus_alignment(self, section: Dict[str, Any], 
                                 persona_profile: Dict[str, Any]) -> float:
        """Calculate alignment with persona focus areas."""
        
        focus_areas = persona_profile.get('focus_areas', [])
        if not focus_areas:
            return 0.5  # Neutral score
        
        section_text = (section.get('text_content', '') + ' ' + 
                       section.get('section_title', '')).lower()
        
        matches = 0
        for focus_area in focus_areas:
            if focus_area.lower() in section_text:
                matches += 1
        
        return matches / len(focus_areas) if focus_areas else 0.0
    
    def get_section_keywords(self, section: Dict[str, Any]) -> List[str]:
        """Extract keywords from section."""
        text = section.get('text_content', '') + ' ' + section.get('section_title', '')
        
        # Extract meaningful words (4+ characters)
        words = re.findall(r'\b\w{4,}\b', text.lower())
        
        # Filter common words and return unique keywords
        common_words = {'with', 'from', 'they', 'have', 'this', 'that', 'will', 'been', 'were'}
        keywords = [word for word in set(words) if word not in common_words]
        
        return keywords[:20]  # Top 20 keywords
