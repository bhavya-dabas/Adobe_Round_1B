"""
Advanced relevance scoring for importance ranking
"""

import re
import math
from typing import Dict, Any, List
from collections import Counter

class RelevanceScorer:
    """Advanced scoring system for section importance."""
    
    def __init__(self):
        self.section_type_weights = {
            'title': 0.9,
            'heading': 0.8,
            'content': 0.7
        }
        
        self.heading_level_weights = {
            'title': 1.0,
            'H1': 0.9,
            'H2': 0.8,
            'H3': 0.7,
            'content': 0.6
        }
    
    def calculate_importance(self, section: Dict[str, Any], 
                           persona_profile: Dict[str, Any]) -> float:
        """Calculate comprehensive importance score."""
        
        # Base relevance score
        relevance_score = section.get('relevance_score', 0.0)
        
        # Content quality score
        content_quality = self._calculate_content_quality(section)
        
        # Position importance (earlier sections often more important)
        position_score = self._calculate_position_score(section)
        
        # Persona alignment score  
        persona_alignment = self._calculate_persona_alignment(section, persona_profile)
        
        # Section type importance
        type_score = self._calculate_type_score(section)
        
        # Length appropriateness
        length_score = self._calculate_length_score(section)
        
        # Combine scores with weights
        importance_score = (
            0.25 * relevance_score +      # Core relevance
            0.20 * content_quality +      # Content quality
            0.15 * persona_alignment +    # Persona fit
            0.15 * type_score +           # Section type
            0.15 * position_score +       # Document position
            0.10 * length_score           # Content length
        )
        
        return min(1.0, importance_score)
    
    def _calculate_content_quality(self, section: Dict[str, Any]) -> float:
        """Calculate content quality score."""
        
        text_content = section.get('text_content', '')
        section_title = section.get('section_title', '')
        
        if not text_content:
            return 0.1
        
        quality_score = 0.0
        
        # Text length (sweet spot around 200-800 characters)
        length = len(text_content)
        if 200 <= length <= 800:
            quality_score += 0.3
        elif 100 <= length < 200 or 800 < length <= 1500:
            quality_score += 0.2
        elif length > 50:
            quality_score += 0.1
        
        # Sentence structure
        sentences = re.split(r'[.!?]+', text_content)
        sentence_count = len([s for s in sentences if len(s.strip()) > 10])
        
        if 3 <= sentence_count <= 15:
            quality_score += 0.2
        elif sentence_count > 0:
            quality_score += 0.1
        
        # Vocabulary richness
        words = re.findall(r'\b\w+\b', text_content.lower())
        unique_words = set(words)
        
        if len(words) > 0:
            lexical_diversity = len(unique_words) / len(words)
            quality_score += min(0.3, lexical_diversity * 0.6)
        
        # Informative title
        if section_title and len(section_title) > 5:
            quality_score += 0.2
        
        return min(1.0, quality_score)
    
    def _calculate_position_score(self, section: Dict[str, Any]) -> float:
        """Calculate position-based importance."""
        
        page_number = section.get('page_number', 0)
        
        # Early pages are often more important
        if page_number == 0:
            return 1.0  # Title page
        elif page_number <= 2:
            return 0.9  # Introduction/overview
        elif page_number <= 5:
            return 0.8  # Early content
        elif page_number <= 10:
            return 0.7  # Mid content
        else:
            return 0.6  # Later content
    
    def _calculate_persona_alignment(self, section: Dict[str, Any], 
                                   persona_profile: Dict[str, Any]) -> float:
        """Calculate persona-specific alignment."""
        
        role = persona_profile.get('role', '').lower()
        task = persona_profile.get('task', '').lower()
        focus_areas = persona_profile.get('focus_areas', [])
        
        text_content = section.get('text_content', '').lower()
        section_title = section.get('section_title', '').lower()
        
        alignment_score = 0.0
        
        # Role-specific patterns
        if 'researcher' in role:
            research_keywords = ['method', 'result', 'analysis', 'data', 'study', 'research']
            matches = sum(1 for kw in research_keywords if kw in text_content)
            alignment_score += min(0.4, matches * 0.1)
            
        elif 'student' in role:
            student_keywords = ['example', 'concept', 'definition', 'explain', 'understand']
            matches = sum(1 for kw in student_keywords if kw in text_content)
            alignment_score += min(0.4, matches * 0.1)
            
        elif 'analyst' in role:
            analyst_keywords = ['trend', 'metric', 'performance', 'compare', 'analysis']
            matches = sum(1 for kw in analyst_keywords if kw in text_content)
            alignment_score += min(0.4, matches * 0.1)
        
        # Task alignment
        task_words = re.findall(r'\b\w{4,}\b', task)
        for task_word in task_words:
            if task_word in text_content or task_word in section_title:
                alignment_score += 0.1
        
        # Focus area alignment
        for focus_area in focus_areas:
            if focus_area.lower() in text_content or focus_area.lower() in section_title:
                alignment_score += 0.15
        
        return min(1.0, alignment_score)
    
    def _calculate_type_score(self, section: Dict[str, Any]) -> float:
        """Calculate section type importance."""
        
        section_type = section.get('section_type', 'content')
        heading_level = section.get('heading_level', 'content')
        
        # Base type score
        type_score = self.section_type_weights.get(section_type, 0.5)
        
        # Heading level adjustment
        level_weight = self.heading_level_weights.get(heading_level, 0.5)
        
        return (type_score + level_weight) / 2
    
    def _calculate_length_score(self, section: Dict[str, Any]) -> float:
        """Calculate length appropriateness score."""
        
        text_content = section.get('text_content', '')
        length = len(text_content)
        
        # Optimal length ranges
        if 150 <= length <= 500:
            return 1.0  # Perfect length
        elif 100 <= length < 150 or 500 < length <= 1000:
            return 0.8  # Good length
        elif 50 <= length < 100 or 1000 < length <= 2000:
            return 0.6  # Acceptable length
        elif length > 2000:
            return 0.4  # Too long
        else:
            return 0.2  # Too short
    
    def get_importance_explanation(self, section: Dict[str, Any], 
                                 persona_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed explanation of importance score."""
        
        return {
            'relevance_score': section.get('relevance_score', 0.0),
            'content_quality': self._calculate_content_quality(section),
            'position_score': self._calculate_position_score(section),
            'persona_alignment': self._calculate_persona_alignment(section, persona_profile),
            'type_score': self._calculate_type_score(section),
            'length_score': self._calculate_length_score(section),
            'final_importance': self.calculate_importance(section, persona_profile)
        }
