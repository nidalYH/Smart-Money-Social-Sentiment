#!/usr/bin/env python3
"""
Script to update all models for SQLite compatibility
"""
import os
import re

def update_model_file(file_path):
    """Update a single model file for SQLite compatibility"""
    if not os.path.exists(file_path):
        return
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Track if changes were made
    original_content = content
    
    # Add JSON import if not present
    if 'from sqlalchemy import JSON' not in content and 'JSONB' in content:
        content = content.replace(
            'from sqlalchemy.dialects.postgresql import UUID, JSONB',
            'from sqlalchemy.dialects.postgresql import UUID, JSONB\nfrom sqlalchemy import JSON'
        )
    
    # Replace UUID with String(36)
    content = re.sub(
        r'Column\(UUID\(as_uuid=True\), primary_key=True, default=uuid\.uuid4\)',
        'Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))',
        content
    )
    
    # Replace UUID foreign keys
    content = re.sub(
        r'Column\(UUID\(as_uuid=True\), ForeignKey\([^)]+\), nullable=False, index=True\)',
        lambda m: m.group(0).replace('UUID(as_uuid=True)', 'String(36)'),
        content
    )
    
    content = re.sub(
        r'Column\(UUID\(as_uuid=True\), nullable=False, index=True\)',
        'Column(String(36), nullable=False, index=True)',
        content
    )
    
    # Replace JSONB with JSON
    content = content.replace('JSONB', 'JSON')
    
    # Only write if changes were made
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated {file_path}")
    else:
        print(f"No changes needed for {file_path}")

def main():
    """Update all model files"""
    model_files = [
        'app/models/user.py',
        'app/models/whale.py',
        'app/models/sentiment.py',
        'app/models/signal.py',
        'app/models/alert.py',
        'app/models/token.py'
    ]
    
    for model_file in model_files:
        update_model_file(model_file)
    
    print("All model files updated for SQLite compatibility")

if __name__ == "__main__":
    main()
