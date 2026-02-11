# -*- coding: utf-8 -*-
"""主页面路由"""

from flask import Blueprint, render_template
from app.auth import login_required, get_current_user
from app.services.script_manager import get_available_scripts
from app.services.instance_manager import get_all_instances

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
@login_required
def index():
    """主页面"""
    scripts_by_dir = get_available_scripts()
    instances = get_all_instances()
    current_user = get_current_user()
    return render_template('index.html',
                           scripts_by_dir=scripts_by_dir,
                           instances=instances,
                           current_user=current_user)


@main_bp.route('/ok')
def health_check():
    """健康检测接口"""
    return 'ok'
