# -*- coding: utf-8 -*-
"""
config.py
Configuration loader - reads settings from .env file securely
"""

import configparser
from pathlib import Path

class Config:
    """Load and manage configuration from .env file"""
    
    def __init__(self, env_file='.env'):
        """
        Initialize configuration
        
        Args:
            env_file: Path to .env configuration file
        """
        self.config = configparser.ConfigParser()
        
        # Check if .env file exists
        env_path = Path(env_file)
        if not env_path.exists():
            raise FileNotFoundError(
                f"Configuration file not found: {env_file}\n"
                f"Please create .env file with your OpenAI API key"
            )
        
        # Read configuration
        self.config.read(env_file)
        
        # Validate required settings
        self._validate()
    
    def _validate(self):
        """Validate that required configuration exists"""
        
        # Check API key exists
        if not self.config.has_option('OpenAI', 'API_KEY'):
            raise ValueError("Missing required config: [OpenAI] API_KEY in .env file")
        
        # Check API key is not default placeholder
        api_key = self.config.get('OpenAI', 'API_KEY').strip()
        if not api_key or api_key == 'sk-proj-your-actual-api-key-here':
            raise ValueError(
                "Please set your actual OpenAI API key in .env file\n"
                "Replace 'sk-proj-your-actual-api-key-here' with your real key"
            )
        
        print("Configuration loaded successfully")
    
    @property
    def api_key(self):
        """Get OpenAI API key"""
        return self.config.get('OpenAI', 'API_KEY').strip()
    
    @property
    def model(self):
        """Get OpenAI model name"""
        return self.config.get('Settings', 'MODEL', fallback='gpt-4o')
    
    @property
    def temperature(self):
        """Get model temperature"""
        return self.config.getfloat('Settings', 'TEMPERATURE', fallback=0.1)
    
    @property
    def max_tokens(self):
        """Get max tokens for API calls"""
        return self.config.getint('Settings', 'MAX_TOKENS', fallback=4000)
    
    @property
    def output_dir(self):
        """Get output directory path"""
        dir_name = self.config.get('Paths', 'OUTPUT_DIR', fallback='cv_extraction_output')
        return Path(dir_name)
    
    @property
    def upload_dir(self):
        """Get upload directory path"""
        dir_name = self.config.get('Paths', 'UPLOAD_DIR', fallback='uploads')
        return Path(dir_name)
    
    def display_config(self):
        """Display current configuration (without showing API key)"""
        print("\nCurrent Configuration:")
        print("=" * 50)
        print(f"Model: {self.model}")
        print(f"Temperature: {self.temperature}")
        print(f"Max Tokens: {self.max_tokens}")
        print(f"Output Directory: {self.output_dir}")
        print(f"Upload Directory: {self.upload_dir}")
        print(f"API Key: {'*' * 20} (hidden)")
        print("=" * 50)