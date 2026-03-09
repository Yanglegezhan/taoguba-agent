"""
JSON Schema验证器

本模块提供JSON数据格式验证功能，确保数据符合预定义的Schema规范。
"""

import json
import os
from typing import Dict, Any, List, Tuple
from pathlib import Path

try:
    from jsonschema import validate, ValidationError, Draft7Validator
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False
    print("Warning: jsonschema not installed. Schema validation will be skipped.")


class SchemaValidator:
    """JSON Schema验证器"""
    
    def __init__(self, schema_dir: str = None):
        """
        初始化验证器
        
        Args:
            schema_dir: Schema文件目录，默认为项目根目录下的schemas目录
        """
        if schema_dir is None:
            # 获取项目根目录
            current_file = Path(__file__)
            project_root = current_file.parent.parent.parent
            schema_dir = project_root / "schemas"
        
        self.schema_dir = Path(schema_dir)
        self.schemas: Dict[str, Dict[str, Any]] = {}
        
        # 加载所有schema文件
        self._load_schemas()
    
    def _load_schemas(self) -> None:
        """加载所有schema文件"""
        if not self.schema_dir.exists():
            print(f"Warning: Schema directory not found: {self.schema_dir}")
            return
        
        schema_files = {
            'gene_pool': 'gene_pool_schema.json',
            'baseline_expectation': 'baseline_expectation_schema.json',
            'decision_navigation': 'decision_navigation_schema.json'
        }
        
        for name, filename in schema_files.items():
            filepath = self.schema_dir / filename
            if filepath.exists():
                with open(filepath, 'r', encoding='utf-8') as f:
                    self.schemas[name] = json.load(f)
            else:
                print(f"Warning: Schema file not found: {filepath}")
    
    def validate_gene_pool(self, data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        验证基因池数据格式
        
        Args:
            data: 基因池数据字典
        
        Returns:
            (是否有效, 错误信息列表)
        """
        return self._validate(data, 'gene_pool')
    
    def validate_baseline_expectation(self, data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        验证基准预期数据格式
        
        Args:
            data: 基准预期数据字典
        
        Returns:
            (是否有效, 错误信息列表)
        """
        return self._validate(data, 'baseline_expectation')
    
    def validate_decision_navigation(self, data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        验证决策导航报告数据格式
        
        Args:
            data: 决策导航报告数据字典
        
        Returns:
            (是否有效, 错误信息列表)
        """
        return self._validate(data, 'decision_navigation')
    
    def _validate(self, data: Dict[str, Any], schema_name: str) -> Tuple[bool, List[str]]:
        """
        验证数据格式
        
        Args:
            data: 数据字典
            schema_name: Schema名称
        
        Returns:
            (是否有效, 错误信息列表)
        """
        if not JSONSCHEMA_AVAILABLE:
            return True, ["jsonschema not installed, validation skipped"]
        
        if schema_name not in self.schemas:
            return False, [f"Schema '{schema_name}' not found"]
        
        schema = self.schemas[schema_name]
        errors = []
        
        try:
            validate(instance=data, schema=schema)
            return True, []
        except ValidationError as e:
            errors.append(self._format_validation_error(e))
            
            # 收集所有验证错误
            validator = Draft7Validator(schema)
            for error in validator.iter_errors(data):
                if error != e:  # 避免重复
                    errors.append(self._format_validation_error(error))
            
            return False, errors
    
    def _format_validation_error(self, error: 'ValidationError') -> str:
        """
        格式化验证错误信息
        
        Args:
            error: 验证错误对象
        
        Returns:
            格式化的错误信息
        """
        path = '.'.join(str(p) for p in error.path) if error.path else 'root'
        return f"字段 '{path}': {error.message}"
    
    def validate_file(self, filepath: str, schema_name: str) -> Tuple[bool, List[str]]:
        """
        验证JSON文件格式
        
        Args:
            filepath: JSON文件路径
            schema_name: Schema名称（gene_pool, baseline_expectation, decision_navigation）
        
        Returns:
            (是否有效, 错误信息列表)
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return self._validate(data, schema_name)
        except json.JSONDecodeError as e:
            return False, [f"JSON解析错误: {str(e)}"]
        except FileNotFoundError:
            return False, [f"文件不存在: {filepath}"]
        except Exception as e:
            return False, [f"验证失败: {str(e)}"]


# 全局验证器实例
_validator = None


def get_validator() -> SchemaValidator:
    """获取全局验证器实例"""
    global _validator
    if _validator is None:
        _validator = SchemaValidator()
    return _validator


def validate_gene_pool_data(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """验证基因池数据格式（便捷函数）"""
    return get_validator().validate_gene_pool(data)


def validate_baseline_expectation_data(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """验证基准预期数据格式（便捷函数）"""
    return get_validator().validate_baseline_expectation(data)


def validate_decision_navigation_data(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """验证决策导航报告数据格式（便捷函数）"""
    return get_validator().validate_decision_navigation(data)


def validate_json_file(filepath: str, schema_name: str) -> Tuple[bool, List[str]]:
    """验证JSON文件格式（便捷函数）"""
    return get_validator().validate_file(filepath, schema_name)
