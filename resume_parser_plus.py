import os
os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'expandable_segments:True'

import gc
import torch

gc.collect()
torch.cuda.empty_cache()

from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
from qwen_vl_utils import process_vision_info
from pdf2image import convert_from_path
from PIL import Image
import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import re


class PreciseCVExtractor:
    def _init_(self, model_name: str = "Qwen/Qwen2-VL-7B-Instruct"):
        print("=" * 60)
        print(" Loading Precise CV Extractor")
        print("=" * 60)

        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()

            gpu_name = torch.cuda.get_device_name(0)
            gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1e9
            free_memory = torch.cuda.mem_get_info()[0] / 1e9
            print(f"GPU: {gpu_name} ({gpu_memory:.1f} GB)")
            print(f"Free Memory: {free_memory:.1f} GB")

        print(f"Loading 7B model...")

        try:
            self.model = Qwen2VLForConditionalGeneration.from_pretrained(
                model_name,
                torch_dtype=torch.float16,
                device_map="auto",
                trust_remote_code=True,
                low_cpu_mem_usage=True,
            )

            self.model.eval()

        except Exception as e:
            print(f"Error: {e}")
            raise

        self.processor = AutoProcessor.from_pretrained(model_name, trust_remote_code=True)
        self.model_name = model_name

        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        print(f"✓ Model loaded!")

        self.output_dir = Path("extracted_cvs_precise")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def create_strict_extraction_prompt(self) -> str:
        return """STRICT CV EXTRACTION - EXTRACT ONLY WHAT EXISTS

 CRITICAL RULES:
1. Extract ONLY text that is VISIBLY WRITTEN in the CV
2. NEVER invent or add dates that don't exist
3. NEVER add job descriptions - read ALL bullet points completely
4. If something doesn't exist → use null or []
5. DO NOT mix technical skills with soft skills
6. DO NOT include soft skills (leadership, communication, teamwork)

═══════════════════════════════════════════════════════════

{
  "personal_info": {
    "name": "exact full name or null",
    "job_title": "exact title or null"
  },
  "contact_info": {
    "email": "exact email or null",
    "phone": "exact phone or null",
    "location": "exact location or null",
    "linkedin": "exact URL or null",
    "github": "exact URL or null"
  },
  "education": [
    {
      "degree": "exact degree name",
      "field": "exact major/specialization",
      "institution": "exact university name",
      "start_date": "ONLY if written (2018 or Jan 2018) or null",
      "end_date": "ONLY if written (2022 or Present) or null"
    }
  ],
  "experience": [
    {
      "job_title": "exact job title",
      "company": "exact company name",
      "location": "exact location or null",
      "start_date": "ONLY if written or null",
      "end_date": "ONLY if written or null",
      "responsibilities": [
        "Read ALL bullet points COMPLETELY",
        "Copy EACH bullet point EXACTLY",
        "Do NOT summarize or shorten",
        "Include EVERY responsibility listed"
      ]
    }
  ],
  "projects": [
    {
      "name": "exact project name",
      "description": "exact full description",
      "date": "ONLY if mentioned or null"
    }
  ],
  "technical_skills": [
    "ONLY from 'Skills' or 'Technical Skills' section",
    "Do NOT extract from projects/experience",
    "Do NOT include soft skills",
    "Flat array, no categories"
  ],
  "certifications": [
    {
      "name": "exact name",
      "issuer": "exact issuer or null",
      "date": "ONLY if written or null"
    }
  ],
  "languages": [
    {
      "language": "exact language",
      "proficiency": "exact level"
    }
  ]
}

═══════════════════════════════════════════════════════════

 DATES RULES:
• No date visible → null
• Only year → "2020"
• Month + year → "Jan 2020"
• NEVER guess dates
• Use "Present" ONLY if written

 SKILLS RULES:
• Extract ONLY from labeled skills section
• IGNORE: leadership, communication, teamwork, problem-solving
• Keep ONLY: Python, Java, AWS, Docker, etc.
• One skill ONE time (no duplicates)

 RESPONSIBILITIES RULES:
• Read the COMPLETE job description
• Copy EVERY bullet point EXACTLY
• Do NOT skip any points
• Do NOT paraphrase

REMEMBER: Extract ONLY what you can SEE. Nothing more."""

    def pdf_to_images(self, pdf_path: str, dpi: int = 200) -> List[Image.Image]:
        return convert_from_path(pdf_path, dpi=dpi)

    def extract_from_image(self, image: Image.Image, page_num: int = 1) -> Dict:
        try:
            max_size = 1024
            if max(image.size) > max_size:
                ratio = max_size / max(image.size)
                new_size = tuple(int(dim * ratio) for dim in image.size)
                image = image.resize(new_size, Image.Resampling.LANCZOS)

            messages = [{
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": self.create_strict_extraction_prompt()}
                ]
            }]

            text = self.processor.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True
            )
            image_inputs, video_inputs = process_vision_info(messages)
            inputs = self.processor(
                text=[text],
                images=image_inputs,
                videos=video_inputs,
                padding=True,
                return_tensors="pt"
            )
            inputs = inputs.to(self.model.device)

            with torch.no_grad():
                generated_ids = self.model.generate(
                    **inputs,
                    max_new_tokens=2000,
                    temperature=0.2,
                    do_sample=True,
                    top_p=0.95,
                    repetition_penalty=1.1
                )

            generated_ids_trimmed = [
                out_ids[len(in_ids):]
                for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
            ]
            output_text = self.processor.batch_decode(
                generated_ids_trimmed,
                skip_special_tokens=True,
                clean_up_tokenization_spaces=False
            )[0]

            del inputs, generated_ids, generated_ids_trimmed, image_inputs, video_inputs
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.synchronize()

            result = self.parse_and_clean_json(output_text)
            return result

        except Exception as e:
            print(f"✗ Error: {str(e)[:100]}")
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            return {}

    def parse_and_clean_json(self, output_text: str) -> Dict:
        try:
            if "json" in output_text:
                json_text = output_text.split("json")[1].split("")[0]
            elif "" in output_text:
                json_text = output_text.split("")[1].split("")[0]
            else:
                json_text = output_text

            json_text = json_text.strip()

            start_idx = json_text.find("{")
            end_idx = json_text.rfind("}") + 1
            if start_idx != -1 and end_idx > start_idx:
                json_text = json_text[start_idx:end_idx]

            json_text = re.sub(r',\s*}', '}', json_text)
            json_text = re.sub(r',\s*]', ']', json_text)

            data = json.loads(json_text)
            data = self.clean_extracted_data(data)

            return data

        except json.JSONDecodeError:
            return {}

    def clean_extracted_data(self, data: Dict) -> Dict:
        if not data:
            return data

        soft_skills = [
            'leadership', 'communication', 'teamwork', 'problem-solving',
            'problem solving', 'critical thinking', 'time management',
            'collaboration', 'adaptability', 'creativity', 'analytical',
        ]

        if 'technical_skills' in data:
            if isinstance(data['technical_skills'], list):
                seen = set()
                unique_skills = []
                for skill in data['technical_skills']:
                    if skill and skill.lower() not in [s.lower() for s in soft_skills]:
                        if skill.lower() not in seen:
                            seen.add(skill.lower())
                            unique_skills.append(skill)
                data['technical_skills'] = unique_skills
            elif isinstance(data['technical_skills'], dict):
                all_skills = []
                for category, skills in data['technical_skills'].items():
                    if isinstance(skills, list):
                        all_skills.extend(skills)
                seen = set()
                unique_skills = []
                for skill in all_skills:
                    if skill and skill.lower() not in [s.lower() for s in soft_skills]:
                        if skill.lower() not in seen:
                            seen.add(skill.lower())
                            unique_skills.append(skill)
                data['technical_skills'] = unique_skills

        if 'soft_skills' in data:
            del data['soft_skills']

        if 'projects' in data and isinstance(data['projects'], list):
            for project in data['projects']:
                if isinstance(project, dict):
                    empty_fields = [k for k, v in project.items() if v is None or v == "" or v == []]
                    for field in empty_fields:
                        del project[field]

        if 'education' in data and isinstance(data['education'], list):
            for edu in data['education']:
                if isinstance(edu, dict):
                    empty_fields = [k for k, v in edu.items() if v is None or v == ""]
                    for field in empty_fields:
                        del edu[field]

        if 'experience' in data and isinstance(data['experience'], list):
            for exp in data['experience']:
                if isinstance(exp, dict):
                    empty_fields = [
                        k for k, v in exp.items()
                        if v is None or v == "" or (isinstance(v, list) and len(v) == 0)
                    ]
                    for field in empty_fields:
                        if field != 'responsibilities':
                            del exp[field]

                    if 'responsibilities' in exp and isinstance(exp['responsibilities'], list):
                        exp['responsibilities'] = list(dict.fromkeys(exp['responsibilities']))

        return data

    def merge_pages_carefully(self, pages: List[Dict]) -> Dict:
        if not pages:
            return {}
        if len(pages) == 1:
            return pages[0]

        merged = pages[0].copy() if pages[0] else {}

        for page in pages[1:]:
            if not page:
                continue

            for field in ['personal_info', 'contact_info']:
                if field in page and isinstance(page[field], dict):
                    if field not in merged:
                        merged[field] = {}
                    for key, value in page[field].items():
                        if value and (key not in merged[field] or not merged[field][key]):
                            merged[field][key] = value

            list_fields = ['education', 'experience', 'projects', 'certifications', 'languages']
            for field in list_fields:
                if field in page and isinstance(page[field], list):
                    if field not in merged:
                        merged[field] = []

                    for item in page[field]:
                        is_duplicate = False

                        if isinstance(item, dict):
                            for existing in merged[field]:
                                if isinstance(existing, dict):
                                    if field == 'education':
                                        if (
                                            item.get('degree') == existing.get('degree') and
                                            item.get('institution') == existing.get('institution')
                                        ):
                                            is_duplicate = True
                                            break
                                    elif field == 'experience':
                                        if (
                                            item.get('job_title') == existing.get('job_title') and
                                            item.get('company') == existing.get('company')
                                        ):
                                            is_duplicate = True
                                            break
                                    elif field == 'projects':
                                        if item.get('name') == existing.get('name'):
                                            is_duplicate = True
                                            break
                        else:
                            if item in merged[field]:
                                is_duplicate = True

                        if not is_duplicate:
                            merged[field].append(item)

            if 'technical_skills' in page:
                if 'technical_skills' not in merged:
                    merged['technical_skills'] = []

                if isinstance(page['technical_skills'], list):
                    for skill in page['technical_skills']:
                        if skill and skill not in merged['technical_skills']:
                            merged['technical_skills'].append(skill)

        merged = self.clean_extracted_data(merged)
        return merged

    def extract_single_cv(self, pdf_path: Path) -> Dict:
        try:
            print(f"\n📄 {pdf_path.name}")

            images = self.pdf_to_images(str(pdf_path))
            print(f"   Pages: {len(images)}")

            all_page_data = []

            for idx, image in enumerate(images, 1):
                print(f"   [{idx}/{len(images)}]", end=" ", flush=True)

                page_data = self.extract_from_image(image, page_num=idx)

                if page_data:
                    all_page_data.append(page_data)

                del image
                gc.collect()
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()

            print("✓")

            if not all_page_data:
                return {}

            final_data = self.merge_pages_carefully(all_page_data)

            final_data['_metadata'] = {
                'source_file': pdf_path.name,
                'total_pages': len(images),
                'extraction_timestamp': datetime.now().isoformat()
            }

            json_path = self.output_dir / f"{pdf_path.stem}.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(final_data, f, indent=2, ensure_ascii=False)

            name = final_data.get('personal_info', {}).get('name', 'N/A')
            skills_count = len(final_data.get('technical_skills', []))
            print(f"   ✓ {name} | Skills: {skills_count}")

            del all_page_data, images
            gc.collect()

            return final_data

        except Exception as e:
            print(f"   ✗ Error: {str(e)[:100]}")
            return {}

    def extract_batch(self, input_path: str, max_files: Optional[int] = None) -> Dict:
        path = Path(input_path)

        if not path.exists():
            raise FileNotFoundError(f"Path not found: {input_path}")

        if path.is_file() and path.suffix.lower() == '.pdf':
            pdf_files = [path]
        elif path.is_dir():
            pdf_files = sorted(list(path.glob("*.pdf")))
            if max_files:
                pdf_files = pdf_files[:max_files]
        else:
            raise ValueError(f"Invalid path: must be a PDF file or directory")

        if not pdf_files:
            return {"total": 0, "successful": 0, "failed": 0, "data": []}

        print("\n" + "=" * 60)
        print(" CV EXTRACTION")
        print("=" * 60)
        print(f"Files: {len(pdf_files)}")
        print(f"Output: {self.output_dir.absolute()}")
        print("=" * 60)

        all_results = []
        successful = 0
        failed_files = []

        for i, pdf_file in enumerate(pdf_files, 1):
            print(f"\n[{i}/{len(pdf_files)}]", end=" ")

            result = self.extract_single_cv(pdf_file)

            if result and result.get('personal_info'):
                all_results.append(result)
                successful += 1
            else:
                failed_files.append(pdf_file.name)

            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

        if all_results:
            combined_json_path = self.output_dir / "all_cvs_combined.json"
            with open(combined_json_path, 'w', encoding='utf-8') as f:
                json.dump(all_results, f, indent=2, ensure_ascii=False)

        print("\n" + "=" * 60)
        print(f" SUCCESS: {successful}/{len(pdf_files)}")
        print(f" FAILED: {len(failed_files)}")
        print(f" Output: {self.output_dir.absolute()}/")
        print("=" * 60)

        if failed_files:
            print(f"\n✗ Failed files:")
            for file in failed_files[CV_FOLDER = r"C:\\Users\\alsha\\OneDrive\\Documents\\resume"
                                      

            MAX_FILES = 5

            print("\n" + "=" * 60)
            print(" Starting Precise CV Extraction")
            print("=" * 60)

            extractor = PreciseCVExtractor()

            results = extractor.extract_batch(CV_FOLDER, max_files=MAX_FILES)

            print("\nProcess completed!")
            print(f"Check results at: extracted_cvs_precise/")

            if results['successful'] > 0:
                print(f"\nSuccessfully processed {results['successful']} CVs")
                print("Files created:")
                print("  - Individual JSON for each CV")
                print("  - all_cvs_combined.json (all CVs in one file)"):5]:
                print(f"  - {file}")

        return {
            "total": len(pdf_files),
            "successful": successful,
            "failed": len(pdf_files) - successful,
            "data": all_results,
            "failed_files": failed_files
        }
