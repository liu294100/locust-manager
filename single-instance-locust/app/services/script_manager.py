# -*- coding: utf-8 -*-
"""脚本文件管理服务"""

import os

ALLOWED_EXTENSIONS = {'py'}


def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_directory_tree():
    """获取scripts目录的完整树形结构"""

    def scan_directory(path, relative_path=""):
        items = []
        if not os.path.exists(path):
            return items
        try:
            for item in sorted(os.listdir(path)):
                item_path = os.path.join(path, item)
                item_relative = os.path.join(relative_path, item) if relative_path else item

                if os.path.isdir(item_path):
                    children = scan_directory(item_path, item_relative)
                    display_name = "临时文件" if item == "tmp" and relative_path == "" else item
                    items.append({
                        'name': display_name,
                        'path': item_relative,
                        'type': 'directory',
                        'children': children,
                        'has_scripts': (
                            any(c['type'] == 'file' for c in children) or
                            any(c.get('has_scripts', False) for c in children if c['type'] == 'directory')
                        )
                    })
                elif item.endswith('.py'):
                    items.append({
                        'name': item,
                        'path': item_relative,
                        'type': 'file'
                    })
        except PermissionError:
            pass
        return items

    scripts_dir = os.path.join(os.getcwd(), 'scripts')
    tree = scan_directory(scripts_dir)

    # 添加根目录的脚本文件
    root_scripts = []
    if os.path.exists(scripts_dir):
        for item in os.listdir(scripts_dir):
            item_path = os.path.join(scripts_dir, item)
            if os.path.isfile(item_path) and item.endswith('.py'):
                root_scripts.append({'name': item, 'path': item, 'type': 'file'})

    if root_scripts:
        tree.insert(0, {
            'name': '根目录', 'path': '', 'type': 'directory',
            'children': root_scripts, 'has_scripts': True
        })

    return tree


def get_available_scripts():
    """获取可用的Locust脚本列表，按目录分组"""
    scripts_by_dir = {}
    scripts_dir = os.path.join(os.getcwd(), 'scripts')

    if os.path.exists(scripts_dir):
        root_scripts = [f for f in os.listdir(scripts_dir)
                        if os.path.isfile(os.path.join(scripts_dir, f)) and f.endswith('.py')]
        if root_scripts:
            scripts_by_dir['根目录'] = root_scripts

        for subdir in os.listdir(scripts_dir):
            subdir_path = os.path.join(scripts_dir, subdir)
            if os.path.isdir(subdir_path):
                subdir_scripts = [f for f in os.listdir(subdir_path) if f.endswith('.py')]
                if subdir == 'tmp':
                    scripts_by_dir['临时文件'] = subdir_scripts
                elif subdir_scripts:
                    scripts_by_dir[subdir] = subdir_scripts

    if '临时文件' not in scripts_by_dir:
        scripts_by_dir['临时文件'] = []

    return scripts_by_dir


def get_scripts_in_directory(directory):
    """获取指定目录下的脚本列表"""
    scripts = []
    if directory == '根目录':
        base = os.path.join(os.getcwd(), 'scripts')
    elif directory == '临时文件':
        base = os.path.join(os.getcwd(), 'scripts', 'tmp')
    else:
        base = os.path.join(os.getcwd(), 'scripts', directory)

    if os.path.exists(base):
        if directory == '根目录':
            scripts = [f for f in os.listdir(base)
                       if os.path.isfile(os.path.join(base, f)) and f.endswith('.py')]
        else:
            scripts = [f for f in os.listdir(base) if f.endswith('.py')]

    return scripts
