# -*- coding: utf-8 -*-
import ast

with open('kaipanla_crawler.py', 'r', encoding='utf-8') as f:
    tree = ast.parse(f.read())

for node in ast.walk(tree):
    if isinstance(node, ast.ClassDef) and node.name == 'KaipanlaCrawler':
        print(f"类 {node.name} 的方法:")
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                print(f"  - {item.name} (行 {item.lineno})")
