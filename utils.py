"""
Utility functions for Round 1B
"""

import logging
from typing import Dict, Any

def setup_logging():
    """Configure logging."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )

def validate_input(input_config: Dict[str, Any]) -> bool:
    """Validate input configuration."""
    
    required_fields = ['documents', 'persona', 'job_to_be_done']
    
    for field in required_fields:
        if field not in input_config:
            raise ValueError(f"Missing required field: {field}")
    
    # Validate documents
    documents = input_config['documents']
    if not isinstance(documents, list) or len(documents) == 0:
        raise ValueError("Documents must be a non-empty list")
    
    for doc in documents:
        if 'filename' not in doc:
            raise ValueError("Each document must have a filename")
    
    # Validate persona
    persona = input_config['persona']
    if 'role' not in persona:
        raise ValueError("Persona must have a role")
    
    # Validate job_to_be_done
    job = input_config['job_to_be_done']
    if 'task' not in job:
        raise ValueError("Job to be done must have a task")
    
    return True

def validate_output(result: Dict[str, Any]) -> bool:
    """Validate output format."""
    
    required_fields = ['metadata', 'extracted_sections', 'subsection_analysis']
    
    for field in required_fields:
        if field not in result:
            raise ValueError(f"Missing required output field: {field}")
    
    # Validate metadata
    metadata = result['metadata']
    metadata_fields = ['input_documents', 'persona', 'job_to_be_done', 'processing_timestamp']
    
    for field in metadata_fields:
        if field not in metadata:
            raise ValueError(f"Missing metadata field: {field}")
    
    # Validate extracted_sections
    sections = result['extracted_sections']
    if not isinstance(sections, list):
        raise ValueError("extracted_sections must be a list")
    
    for section in sections:
        required_section_fields = ['document', 'section_title', 'importance_rank', 'page_number']
        for field in required_section_fields:
            if field not in section:
                raise ValueError(f"Missing section field: {field}")
    
    # Validate subsection_analysis
    subsections = result['subsection_analysis']
    if not isinstance(subsections, list):
        raise ValueError("subsection_analysis must be a list")
    
    for subsection in subsections:
        required_subsection_fields = ['document', 'refined_text', 'page_number']
        for field in required_subsection_fields:
            if field not in subsection:
                raise ValueError(f"Missing subsection field: {field}")
    
    return True
