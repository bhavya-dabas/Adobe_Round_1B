#!/usr/bin/env python3
"""
Adobe Hackathon Round 1B - Persona-Driven Document Intelligence
Advanced document analyst that extracts relevant content based on persona and job requirements
"""

import os
import sys
import json
import time
import logging
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

from persona_analyzer import PersonaDocumentAnalyzer
from utils import setup_logging, validate_input, validate_output

def process_document_collection(input_path: str, output_path: str) -> Dict[str, Any]:
    """Process a document collection based on persona and job requirements."""
    try:
        start_time = time.time()
        
        # Load input configuration
        with open(input_path, 'r', encoding='utf-8') as f:
            input_config = json.load(f)
        
        # Validate input format
        validate_input(input_config)
        
        # Initialize persona analyzer
        analyzer = PersonaDocumentAnalyzer()
        
        # Process documents
        result = analyzer.analyze_documents(input_config)
        
        # Validate output format
        validate_output(result)
        
        # Save results
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        processing_time = time.time() - start_time
        logging.info(f"Processed collection in {processing_time:.2f}s")
        
        return result
        
    except Exception as e:
        logging.error(f"Error processing collection: {str(e)}")
        # Return empty structure on error
        return {
            "metadata": {
                "input_documents": [],
                "persona": "",
                "job_to_be_done": "",
                "processing_timestamp": datetime.utcnow().isoformat()
            },
            "extracted_sections": [],
            "subsection_analysis": []
        }

def main():
    """Main entry point for Docker container."""
    setup_logging()
    
    input_path = "/app/input/challenge1b_input.json"
    output_path = "/app/output/challenge1b_output.json"
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Check if input file exists
    if not os.path.exists(input_path):
        logging.error(f"Input file not found: {input_path}")
        return
    
    logging.info("Starting persona-driven document analysis...")
    
    result = process_document_collection(input_path, output_path)
    
    logging.info(f"✓ Analysis complete. Results saved to: {output_path}")
    
    # Print summary
    sections_count = len(result.get('extracted_sections', []))
    subsections_count = len(result.get('subsection_analysis', []))
    logging.info(f"📊 Extracted {sections_count} sections and {subsections_count} subsections")

if __name__ == "__main__":
    main()
