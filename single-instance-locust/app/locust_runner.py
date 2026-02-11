# -*- coding: utf-8 -*-
"""
Locust 启动包装器
解决 Anaconda 环境下 zope namespace package 冲突问题
"""
import os
import sys
import site


def fix_zope_namespace():
    """修复 zope namespace package 路径"""
    user_site = site.getusersitepackages()
    if not user_site or not os.path.isdir(user_site):
        return

    user_zope = os.path.join(user_site, 'zope')
    if not os.path.isdir(user_zope):
        return

    # 确保 user site-packages 在 sys.path 中
    if user_site not in sys.path:
        sys.path.insert(0, user_site)

    # 修复 zope.__path__
    try:
        import zope
        if user_zope not in getattr(zope, '__path__', []):
            zope.__path__.insert(0, user_zope)
    except ImportError:
        # zope 还没被导入，添加到 path 后自然能找到
        pass


if __name__ == '__main__':
    fix_zope_namespace()

    # 移除自身参数，把剩余参数传给 locust
    from locust.main import main
    main()
