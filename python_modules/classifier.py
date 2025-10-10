import base64
import requests
import json
import zipfile
import io
from pathlib import Path
from .config import Config

class ImageClassifier:
    def __init__(self):
        self.api_key = Config.NVIDIA_API_KEY
        self.api_url = Config.NVIDIA_API_URL
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    def classify_image(self, image_path, task=None):
        """
        Classify an image using NVIDIA Florence-2
        
        Args:
            image_path: Path to the image file
            task: Classification task (default: from config)
            
        Returns:
            str: Classification result
        """
        task = task or Config.CLASSIFICATION_TASK
        
        print(f"🤖 Classifying: {Path(image_path).name}")
        print(f"🔍 Task: {task}")
        
        try:
            # Read and encode image
            with open(image_path, 'rb') as f:
                image_data = f.read()
            
            # Check file size
            file_size_kb = len(image_data) / 1024
            print(f"📦 Image size: {file_size_kb:.1f}KB")
            
            if file_size_kb > 5000:  # 5MB limit
                raise ValueError(f"Image too large: {file_size_kb:.1f}KB (max: 5MB)")
            
            # Encode to base64
            base64_image = base64.b64encode(image_data).decode('utf-8')
            
            # Determine content type
            content_type = self._get_content_type(image_path)
            
            # Create request payload
            content = f'{task}<img src="data:{content_type};base64,{base64_image}" />'
            payload = {
                "messages": [
                    {
                        "role": "user",
                        "content": content
                    }
                ]
            }
            
            # Make API request
            print("📡 Sending request to NVIDIA API...")
            
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=payload,
                timeout=300
            )
            
            print(f"📥 Response Status: {response.status_code}")
            
            # Check response
            if response.status_code == 200:
                response_content_type = response.headers.get('content-type', '').lower()
                print(f"📄 Response Content-Type: {response_content_type}")
                
                # Handle JSON response
                if 'application/json' in response_content_type:
                    result = response.json()
                    classification = result['choices'][0]['message']['content']
                
                # Handle ZIP response (common for Florence-2)
                elif 'application/zip' in response_content_type or 'application/octet-stream' in response_content_type:
                    print("📦 Extracting ZIP response...")
                    classification = self._extract_from_zip(response.content, task)
                
                else:
                    raise Exception(f"Unexpected content type: {response_content_type}")
                
                # Remove task prefix if present
                if classification.startswith(task):
                    classification = classification[len(task):].strip()
                
                print(f"✅ Classification successful")
                print(f"📝 Result: {classification[:100]}...")
                return classification
            else:
                error_msg = response.text
                print(f"❌ API Error {response.status_code}")
                
                # Provide helpful error messages
                if response.status_code == 401:
                    raise Exception("Authentication failed - check your NVIDIA API key")
                elif response.status_code == 403:
                    raise Exception("Access forbidden - API key may not have permission")
                elif response.status_code == 413:
                    raise Exception("Image too large - reduce quality in config")
                elif response.status_code == 429:
                    raise Exception("Rate limit exceeded - slow down requests")
                elif response.status_code == 500:
                    raise Exception("NVIDIA API server error - try again later")
                else:
                    raise Exception(f"API Error {response.status_code}: {error_msg[:200]}")
                    
        except FileNotFoundError:
            raise Exception(f"Image file not found: {image_path}")
        except requests.exceptions.Timeout:
            raise Exception("API request timed out - try again")
        except requests.exceptions.ConnectionError:
            raise Exception("Failed to connect to NVIDIA API - check internet connection")
        except Exception as e:
            if "Classification failed:" in str(e):
                raise
            raise Exception(f"Classification failed: {str(e)}")
    
    def _extract_from_zip(self, zip_content, task):
        """
        Extract classification result from ZIP response
        
        Args:
            zip_content: ZIP file content as bytes
            task: The task prefix to look for
            
        Returns:
            str: Extracted classification text
        """
        try:
            # Read ZIP file from bytes
            with zipfile.ZipFile(io.BytesIO(zip_content)) as zip_file:
                # List files in ZIP
                file_list = zip_file.namelist()
                print(f"📋 Files in ZIP: {file_list}")
                
                # Look for .response file (contains JSON)
                response_file = None
                for filename in file_list:
                    if filename.endswith('.response'):
                        response_file = filename
                        break
                
                if not response_file:
                    raise Exception("No .response file found in ZIP")
                
                # Extract and parse JSON
                print(f"📄 Reading: {response_file}")
                with zip_file.open(response_file) as f:
                    json_content = f.read().decode('utf-8')
                    result = json.loads(json_content)
                    
                    # Extract classification from JSON
                    if 'choices' in result and len(result['choices']) > 0:
                        classification = result['choices'][0]['message']['content']
                        print(f"✅ Extracted from ZIP successfully")
                        return classification
                    else:
                        raise Exception("Invalid JSON structure in ZIP")
                        
        except zipfile.BadZipFile:
            raise Exception("Response is not a valid ZIP file")
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse JSON from ZIP: {e}")
        except Exception as e:
            raise Exception(f"Failed to extract from ZIP: {e}")
    
    def _get_content_type(self, image_path):
        """Determine image content type from file extension"""
        ext = Path(image_path).suffix.lower()
        content_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.bmp': 'image/bmp'
        }
        return content_types.get(ext, 'image/jpeg')
    
    def save_result(self, image_path, classification, output_dir):
        """Save classification result to JSON file"""
        from datetime import datetime
        
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        image_name = Path(image_path).stem
        result_file = output_dir / f"{image_name}_classification.json"
        
        result_data = {
            "timestamp": datetime.now().isoformat(),
            "image_file": Path(image_path).name,
            "image_path": str(image_path),
            "classification": classification,
            "processed_at": datetime.now().isoformat()
        }
        
        with open(result_file, 'w') as f:
            json.dump(result_data, f, indent=2)
        
        print(f"💾 Result saved to: {result_file.name}")
        return str(result_file)