
# -*- coding: utf-8 -*-
"""
cv_extractor.py
CV Extraction Pipeline - Converts PDF CVs to structured JSON
Uses OpenAI Vision API with secure configuration from .env file
"""

import base64
from src.config.config2 import Config
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List
from openai import OpenAI
import time
import logging
import configparser 
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CVExtractor:
    """
    CV Extraction Pipeline
    Extracts structured data from CV PDFs using OpenAI Vision API
    Reads API key securely from config
    """
    
    # Enhanced extraction prompt - all skills together, exact dates only
    EXTRACTION_PROMPT = """Extract all information from this CV/Resume image and return it as JSON.

CRITICAL RULES:
1. Perform OCR to read all text (support both Arabic and English)
2. Clean and correct OCR errors ONLY (fix typos like "J o h n" → "John")
3. Extract ONLY information that is VISIBLE in the image
4. DO NOT add, invent, assume, or make up ANY information
5. DO NOT calculate or infer dates - use EXACT dates from CV or null
6. If information is unclear or missing, use null
7. For technical skills: combine ALL skills into ONE array

Return this exact JSON structure:

{
  "name": "extract exact full name from CV or null",
  "contact": {
    "email": "extract exact email from CV or null",
    "phone": "extract exact phone from CV or null",
    "linkedin": "extract exact linkedin url from CV or null",
    "github": "extract exact github url from CV or null",
    "location": "extract exact location from CV or null",
    "website": "extract exact website from CV or null"
  },
  "summary": "extract exact professional summary from CV or null",
  "technical_skills": [
    "list ALL technical skills from CV in ONE array",
    "include: programming languages, frameworks, databases, tools, technologies",
    "example: Python, JavaScript, React, Django, PostgreSQL, Docker, AWS, Git"
  ],
  "work_experience": [
    {
      "title": "extract exact job title from CV",
      "company": "extract exact company name from CV",
      "location": "extract exact location from CV or null",
      "start_date": "extract EXACT start date from CV (do not calculate or change format)",
      "end_date": "extract EXACT end date from CV or 'Present' if currently working",
      "duration": "extract exact duration from CV or null (do not calculate)",
      "responsibilities": ["extract exact responsibilities from CV"],
      "technologies": ["extract exact technologies mentioned from CV"],
      "achievements": ["extract exact achievements from CV or null"]
    }
  ],
  "education": [
    {
      "degree": "extract exact degree name from CV",
      "field": "extract exact field of study from CV",
      "institution": "extract exact university/college name from CV",
      "location": "extract exact location from CV or null",
      "graduation_year": "extract EXACT year from CV (do not calculate)",
      "gpa": "extract exact GPA from CV or null",
      "honors": ["extract exact honors/awards from CV or null"]
    }
  ],
  "projects": [
    {
      "name": "extract exact project name from CV",
      "description": "extract exact description from CV",
      "technologies": ["extract exact technologies from CV"],
      "role": "extract exact role from CV or null",
      "link": "extract exact link from CV or null"
    }
  ],
  "certifications": [
    {
      "name": "extract exact certification name from CV",
      "issuer": "extract exact issuing organization from CV",
      "date": "extract EXACT date from CV or null (do not calculate)",
      "credential_id": "extract exact ID from CV or null"
    }
  ],
  "languages": [
    {
      "language": "extract exact language name from CV",
      "proficiency": "extract exact proficiency level from CV (Native/Fluent/Intermediate/Basic)"
    }
  ],
  "years_experience": "extract EXACT years from CV or null (do not calculate)",
  "soft_skills": ["extract exact soft skills from CV or null"],
  "interests": ["extract exact interests/hobbies from CV or null"]
}

REMEMBER: 
- Extract ONLY what you see in the CV
- DO NOT make up or calculate dates
- DO NOT infer or assume information
- Put ALL technical skills in one array
- Fix OCR errors but keep original information
- Return only valid JSON"""
    

    def __init__(self, config):
        """
        Initialize CV Extractor with secure configuration
        
        Args:
            config: Configuration object from config.py (reads .env securely)
        """
        self.config = config
        
        # Initialize OpenAI client with API key from config
        self.client = OpenAI(api_key=config.api_key)
        

        print(f"CVExtractor initialized successfully")
        print(f"Model: {config.model}")
        print(f"Output directory: {config.output_dir.absolute()}")
        print(f"API Key: {'*' * 20} (loaded securely from .env)")
    
    def pdf_to_base64_images(self, pdf_path: str) -> List[str]:
        """
        Convert PDF pages to base64 encoded images
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            List of base64 encoded image strings
        """
        try:
            import fitz  # PyMuPDF
            from io import BytesIO
            from PIL import Image
            
            pdf_document = fitz.open(pdf_path)
            base64_images = []
            
            for page_num in range(pdf_document.page_count):
                # Get page and convert to image
                page = pdf_document[page_num]
                pix = page.get_pixmap(matrix=fitz.Matrix(150/72, 150/72))
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                
                # Convert to base64
                buffered = BytesIO()
                img.save(buffered, format="JPEG", quality=85)
                img_base64 = base64.b64encode(buffered.getvalue()).decode()
                base64_images.append(img_base64)
            
            pdf_document.close()
            return base64_images
            
        except Exception as e:
            print(f"Error converting PDF to images: {e}")
            return []
    
    def extract_from_image(self, image_base64: str) -> Optional[Dict]:
        """
        Extract CV data from single image using OpenAI Vision
        Uses model and settings from secure config
        
        Args:
            image_base64: Base64 encoded image string
            
        Returns:
            Extracted CV data as dictionary or None if failed
        """
        try:
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": self.EXTRACTION_PROMPT
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_base64}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                response_format={"type": "json_object"}
            )
            
            cv_data = json.loads(response.choices[0].message.content)
            return cv_data
            
        except Exception as e:
            print(f"Error extracting data from image: {e}")
            return None
    
    def merge_pages(self, page_data_list: List[Dict]) -> Optional[Dict]:
        """
        Merge CV data from multiple pages into one complete CV
        Uses cheaper model for merging to save costs
        
        Args:
            page_data_list: List of CV data dictionaries from each page
            
        Returns:
            Merged CV data dictionary or None if failed
        """
        if not page_data_list:
            return None
        
        if len(page_data_list) == 1:
            return page_data_list[0]
        
        try:
            merge_prompt = f"""Merge these CV data from multiple pages into ONE complete CV.

RULES:
- Remove duplicates
- Combine related information intelligently
- Keep the most complete and accurate data
- DO NOT add or invent any information
- Keep exact dates and information as they are
- Combine technical_skills arrays into one complete array

Pages data:
{json.dumps(page_data_list, indent=2, ensure_ascii=False)}

Return ONE merged JSON with the same structure."""
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # Use cheaper model for merging
                messages=[
                    {
                        "role": "user",
                        "content": merge_prompt
                    }
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            merged_data = json.loads(response.choices[0].message.content)
            return merged_data
            
        except Exception as e:
            print(f"Error merging pages, using first page data: {e}")
            return page_data_list[0]
    
    def process_cv(self, pdf_path: str) -> Optional[Dict]:
        """
        Main CV processing pipeline
        PDF -> Images -> Extract -> Merge -> Save
        
        Args:
            pdf_path: Path to CV PDF file
            
        Returns:
            Final structured CV data or None if failed
        """
        pdf_path = Path(pdf_path)
        
        # Validate file exists
        if not pdf_path.exists():
            print(f"Error: File not found: {pdf_path}")
            return None
        
        print(f"\nProcessing CV: {pdf_path.name}")
        print("-" * 60)
        
        # Step 1: Convert PDF to images
        print("Step 1: Converting PDF to images...")
        images = self.pdf_to_base64_images(str(pdf_path))
        if not images:
            print("Failed to convert PDF to images")
            return None
        
        print(f"Successfully converted {len(images)} page(s)")
        
        # Step 2: Extract data from each page
        print("\nStep 2: Extracting data from pages...")
        page_data_list = []
        for i, img in enumerate(images, 1):
            print(f"  Extracting page {i}/{len(images)}...")
            data = self.extract_from_image(img)
            if data:
                page_data_list.append(data)
                print(f"  Page {i} extracted successfully")
            else:
                print(f"  Failed to extract page {i}")
        
        if not page_data_list:
            print("Error: No data extracted from any page")
            return None
        
        # Step 3: Merge multi-page data
        print("\nStep 3: Merging pages...")
        final_data = self.merge_pages(page_data_list)
        
        if not final_data:
            print("Error: Failed to merge page data")
            return None
        
        # Step 4: Add metadata
        final_data['filename'] = pdf_path.name
        final_data['extraction_timestamp'] = datetime.now().isoformat()
        final_data['extraction_method'] = f'OpenAI Vision ({self.config.model})'
        final_data['total_pages'] = len(images)
        
        
        # Display summary
        print("\n" + "=" * 60)
        print("EXTRACTION SUMMARY:")
        print("=" * 60)
        print(f"Name: {final_data.get('name', 'N/A')}")
        contact = final_data.get('contact', {})
        print(f"Email: {contact.get('email', 'N/A')}")
        print(f"Phone: {contact.get('phone', 'N/A')}")
        skills = final_data.get('technical_skills', [])
        print(f"Technical Skills: {len(skills)} skills")
        print(f"Work Experience: {len(final_data.get('work_experience', []))} entries")
        print(f"Education: {len(final_data.get('education', []))} entries")
        print(f"Projects: {len(final_data.get('projects', []))} entries")
        print("=" * 60)
        
        return final_data
    
    def _generate_raw_text(self, cv_data: Dict) -> str:
        """Generate raw text representation of CV data for reference"""
        lines = []
        lines.append(f"Name: {cv_data.get('name', 'N/A')}")
        lines.append(f"\nContact Information:")
        contact = cv_data.get('contact', {})
        for key, value in contact.items():
            lines.append(f"  {key}: {value}")
        
        lines.append(f"\nSummary: {cv_data.get('summary', 'N/A')}")
        
        skills = cv_data.get('technical_skills', [])
        lines.append(f"\nTechnical Skills ({len(skills)}):")
        for skill in skills:
            lines.append(f"  - {skill}")
        
        return "\n".join(lines)
    
    def process_batch(self, pdf_paths: List[str]) -> List[Dict]:
        """
        Process multiple CV files in batch
        
        Args:
            pdf_paths: List of PDF file paths
            
        Returns:
            List of successfully extracted CV data
        """
        results = []
        total = len(pdf_paths)
        
        print(f"\n{'='*60}")
        print(f"BATCH PROCESSING: {total} CVs")
        print(f"{'='*60}\n")
        
        for i, path in enumerate(pdf_paths, 1):
            print(f"\n[CV {i}/{total}]")
            result = self.process_cv(path)
            
            if result:
                results.append(result)
            
            # Rate limiting between requests
            if i < total:
                print("\nWaiting 2 seconds before next CV...")
                time.sleep(2)
        
        print(f"\n{'='*60}")
        print(f"BATCH COMPLETE")
        print(f"Successfully processed: {len(results)}/{total}")
        print(f"{'='*60}\n")
        
        return results
    
    config = configparser.ConfigParser()
    config.read(".env")

def extract_cvs(cv_files: list) -> Dict:
    """
    Process CV files and merge with existing all_extracted_cvs.json
    Returns dict of all CVs (existing + new)
    """
    config = Config('.env')
    extractor = CVExtractor(config)

    valid_files = [f for f in cv_files if Path(f).exists()]

    if not valid_files:
        logger.error("No valid CV files found")
        return {}

    # Extract new CVs
    extracted_cvs = extractor.process_batch(valid_files)
    new_cvs_dict = {cv.get('filename'): cv for cv in extracted_cvs}

    # Load existing CVs if any
    all_cvs_file =  "Json/all_extracted_cvs.json"
    if all_cvs_file.exists():
        with open(all_cvs_file, 'r', encoding='utf-8') as f:
            all_cvs = json.load(f)
    else:
        all_cvs = {}

    # Merge new CVs
    all_cvs.update(new_cvs_dict)

    # Save merged CVs
    with open(all_cvs_file, 'w', encoding='utf-8') as f:
        json.dump(all_cvs, f, indent=2, ensure_ascii=False)

    logger.info(f"Total CVs after merge: {len(all_cvs)}")
    
    return all_cvs














