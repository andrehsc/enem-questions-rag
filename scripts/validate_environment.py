#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Environment Validation Script for Developer Agents
Validates compliance with development guidelines
"""

import os
import sys
import subprocess
import logging
from pathlib import Path
from typing import List, Dict, Any

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class EnvironmentValidator:
    """Validates development environment compliance"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.issues = []
        
    def validate_docker_environment(self) -> bool:
        """Validate Docker containers are running"""
        logger.info("🐳 Validating Docker environment...")
        
        try:
            result = subprocess.run(['docker', 'ps'], capture_output=True, text=True)
            if result.returncode != 0:
                self.issues.append("❌ Docker não está executando")
                return False
                
            containers = result.stdout
            if 'teachershub-enem-postgres' not in containers:
                self.issues.append("❌ Container PostgreSQL não encontrado")
                return False
                
            logger.info("✅ Docker environment OK")
            return True
            
        except FileNotFoundError:
            self.issues.append("❌ Docker não está instalado")
            return False
    
    def validate_python_files_encoding(self) -> bool:
        """Validate Python files have proper UTF-8 headers"""
        logger.info("🎯 Validating Python file encodings...")
        
        python_files = list(self.project_root.rglob("*.py"))
        problematic_files = []
        
        for py_file in python_files:
            if '.venv' in str(py_file) or '__pycache__' in str(py_file):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Check for UTF-8 header
                if '# -*- coding: utf-8 -*-' not in content[:200]:
                    problematic_files.append(str(py_file))
                    
            except UnicodeDecodeError:
                problematic_files.append(f"{py_file} (encoding issue)")
        
        if problematic_files:
            self.issues.append(f"❌ Files without UTF-8 headers: {len(problematic_files)}")
            for file in problematic_files[:5]:  # Show first 5
                logger.warning(f"   - {file}")
            return False
        
        logger.info("✅ Python file encodings OK")
        return True
    
    def validate_reuse_opportunities(self) -> bool:
        """Check for potential code duplication"""
        logger.info("🔄 Checking for reuse opportunities...")
        
        # Check for duplicate imports/patterns
        scripts_dir = self.project_root / "scripts"
        test_files = list(self.project_root.rglob("test_*.py"))
        
        duplicate_patterns = []
        common_imports = {}
        
        for test_file in test_files:
            try:
                with open(test_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Count common patterns
                if 'psycopg2.connect' in content:
                    common_imports.setdefault('direct_db_connection', []).append(test_file.name)
                if 'uvicorn.run' in content:
                    common_imports.setdefault('direct_uvicorn', []).append(test_file.name)
                    
            except Exception as e:
                logger.warning(f"Could not analyze {test_file}: {e}")
        
        # Report potential reuse opportunities
        for pattern, files in common_imports.items():
            if len(files) > 1:
                logger.warning(f"🔄 Potential reuse opportunity - {pattern}: {files}")
        
        logger.info("✅ Reuse analysis completed")
        return True
    
    def validate_documentation(self) -> bool:
        """Validate documentation is up to date"""
        logger.info("📝 Validating documentation...")
        
        required_docs = [
            '.github/CONTRIBUTING.md',
            'docs/development/AGENT_GUIDELINES.md',
            'README.md'
        ]
        
        missing_docs = []
        for doc_path in required_docs:
            full_path = self.project_root / doc_path
            if not full_path.exists():
                missing_docs.append(doc_path)
        
        if missing_docs:
            self.issues.append(f"❌ Missing documentation: {missing_docs}")
            return False
        
        logger.info("✅ Documentation OK")
        return True
    
    def run_validation(self) -> Dict[str, Any]:
        """Run all validations and return report"""
        logger.info("🚀 Starting environment validation...")
        
        results = {
            'docker': self.validate_docker_environment(),
            'encoding': self.validate_python_files_encoding(),
            'reuse': self.validate_reuse_opportunities(),
            'documentation': self.validate_documentation()
        }
        
        # Generate report
        total_checks = len(results)
        passed_checks = sum(results.values())
        
        logger.info("=" * 60)
        logger.info("📊 VALIDATION REPORT")
        logger.info("=" * 60)
        logger.info(f"Checks passed: {passed_checks}/{total_checks}")
        
        if self.issues:
            logger.error("🚨 ISSUES FOUND:")
            for issue in self.issues:
                logger.error(f"   {issue}")
        else:
            logger.info("🎉 All validations passed!")
        
        return {
            'passed': passed_checks == total_checks,
            'results': results,
            'issues': self.issues
        }

def main():
    """Main validation function"""
    validator = EnvironmentValidator()
    report = validator.run_validation()
    
    # Exit with appropriate code
    sys.exit(0 if report['passed'] else 1)

if __name__ == "__main__":
    main()
