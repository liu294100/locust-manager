# -*- coding: utf-8 -*-
"""
cURL 命令解析器
将 curl 命令解析为结构化数据，并生成 Locust 压测脚本
"""

import re
import json
import shlex
from urllib.parse import urlparse, parse_qs, urlencode


def parse_curl(curl_cmd):
    """解析 curl 命令为结构化数据"""
    # 预处理：合并多行、去除反斜杠换行
    cmd = curl_cmd.strip()
    cmd = re.sub(r'\\\s*\n', ' ', cmd)  # Unix 续行
    cmd = re.sub(r'\^\s*\n', ' ', cmd)  # Windows cmd 续行
    cmd = re.sub(r'`\s*\n', ' ', cmd)   # PowerShell 续行
    cmd = cmd.replace('\n', ' ')
    cmd = re.sub(r'\s+', ' ', cmd).strip()

    # 去掉开头的 curl
    cmd = re.sub(r'^curl\s+', '', cmd, flags=re.IGNORECASE)

    result = {
        'method': 'GET',
        'url': '',
        'headers': {},
        'cookies': {},
        'data': None,
        'data_type': None,  # 'form', 'json', 'raw'
        'auth': None,
    }

    # 用 shlex 分词（处理引号）
    try:
        tokens = shlex.split(cmd, posix=True)
    except ValueError:
        # shlex 解析失败时尝试手动处理
        tokens = _manual_tokenize(cmd)

    i = 0
    while i < len(tokens):
        token = tokens[i]

        if token in ('-X', '--request') and i + 1 < len(tokens):
            result['method'] = tokens[i + 1].upper()
            i += 2
        elif token in ('-H', '--header') and i + 1 < len(tokens):
            header = tokens[i + 1]
            if ':' in header:
                key, val = header.split(':', 1)
                key = key.strip()
                val = val.strip()
                if key.lower() == 'cookie':
                    # 解析 cookie
                    for pair in val.split(';'):
                        pair = pair.strip()
                        if '=' in pair:
                            ck, cv = pair.split('=', 1)
                            result['cookies'][ck.strip()] = cv.strip()
                else:
                    result['headers'][key] = val
            i += 2
        elif token in ('-b', '--cookie') and i + 1 < len(tokens):
            cookie_str = tokens[i + 1]
            for pair in cookie_str.split(';'):
                pair = pair.strip()
                if '=' in pair:
                    ck, cv = pair.split('=', 1)
                    result['cookies'][ck.strip()] = cv.strip()
            i += 2
        elif token in ('-d', '--data', '--data-raw', '--data-binary') and i + 1 < len(tokens):
            raw_data = tokens[i + 1]
            result['data'] = raw_data
            # 判断数据类型
            content_type = result['headers'].get('Content-Type', result['headers'].get('content-type', ''))
            if 'application/json' in content_type:
                result['data_type'] = 'json'
            elif 'application/x-www-form-urlencoded' in content_type:
                result['data_type'] = 'form'
            else:
                # 尝试自动检测
                try:
                    json.loads(raw_data)
                    result['data_type'] = 'json'
                except (json.JSONDecodeError, TypeError):
                    if '=' in raw_data and '&' in raw_data:
                        result['data_type'] = 'form'
                    else:
                        result['data_type'] = 'raw'
            if result['method'] == 'GET':
                result['method'] = 'POST'
            i += 2
        elif token in ('-u', '--user') and i + 1 < len(tokens):
            result['auth'] = tokens[i + 1]
            i += 2
        elif token.startswith('-'):
            # 跳过其他带参数的选项
            if token in ('-o', '--output', '-A', '--user-agent', '-e', '--referer',
                         '--connect-timeout', '-m', '--max-time', '--retry'):
                i += 2
            else:
                i += 1
        else:
            # URL
            url = token.strip("'\"")
            if url.startswith('http://') or url.startswith('https://'):
                result['url'] = url
            i += 1

    return result


def _manual_tokenize(cmd):
    """手动分词，处理 shlex 无法解析的情况"""
    tokens = []
    current = ''
    in_quote = None
    i = 0
    while i < len(cmd):
        c = cmd[i]
        if in_quote:
            if c == in_quote:
                in_quote = None
            else:
                current += c
        elif c in ('"', "'"):
            in_quote = c
        elif c == ' ':
            if current:
                tokens.append(current)
                current = ''
        else:
            current += c
        i += 1
    if current:
        tokens.append(current)
    return tokens


def generate_locust_script(parsed, script_name='CurlTask'):
    """根据解析结果生成 Locust 压测脚本

    生成风格：headers/payload 作为 task 方法内的局部变量，
    使用 catch_response=True 配合 response.success()/failure() 模式。
    不设置 class 级别的 host，由启动参数或 Web UI 指定。
    """
    url_parsed = urlparse(parsed['url'])
    path = url_parsed.path or '/'
    query = url_parsed.query

    method = parsed['method'].lower()
    headers = parsed['headers']
    cookies = parsed['cookies']
    data = parsed['data']
    data_type = parsed['data_type']

    # 过滤掉浏览器自动附加的无关请求头，保留业务相关的（Authorization、Content-Type 等）
    skip_headers = {
        'host', 'content-length', 'connection', 'accept-encoding',
        'sec-fetch-dest', 'sec-fetch-mode', 'sec-fetch-site',
        'sec-ch-ua', 'sec-ch-ua-mobile', 'sec-ch-ua-platform',
        'upgrade-insecure-requests', 'origin', 'referer',
        'user-agent', 'accept', 'accept-language',
    }
    filtered_headers = {k: v for k, v in headers.items()
                        if k.lower() not in skip_headers}

    # 如果有 cookies，合并到 headers 的 Cookie 字段
    if cookies:
        cookie_str = '; '.join(f'{k}={v}' for k, v in cookies.items())
        filtered_headers['Cookie'] = cookie_str

    # 构建完整路径（含 query string）
    full_path = path
    if query:
        full_path = f'{path}?{query}'

    # 从 path 生成 task 方法名
    path_part = path.rstrip('/').split('/')[-1] if path.rstrip('/') else 'request'
    # 转为合法 Python 标识符
    task_method_name = re.sub(r'[^a-zA-Z0-9_]', '_', path_part).strip('_') or 'request'

    lines = []
    lines.append('# -*- coding: utf-8 -*-')
    lines.append('"""')
    lines.append('由 cURL 命令自动生成的 Locust 压测脚本')
    lines.append(f'目标: {method.upper()} {path}')
    lines.append('"""')
    lines.append('')
    lines.append('from locust import HttpUser, task, between')
    lines.append('')
    lines.append('')
    lines.append(f'class {script_name}User(HttpUser):')
    lines.append(f'    wait_time = between(1, 3)  # 模拟用户请求间隔（1-3秒）')
    lines.append('')
    lines.append('    @task')
    lines.append(f'    def {task_method_name}(self):')

    # headers
    if filtered_headers:
        lines.append('        headers = {')
        for k, v in filtered_headers.items():
            lines.append(f'            {repr(k)}: {repr(v)},')
        lines.append('        }')

    # payload / form data
    if data and data_type == 'json':
        try:
            parsed_json = json.loads(data)
            lines.append('        payload = {')
            for k, v in parsed_json.items():
                lines.append(f'            {repr(k)}: {repr(v)},')
            lines.append('        }')
        except (json.JSONDecodeError, TypeError, AttributeError):
            lines.append(f'        payload = {repr(data)}')
    elif data and data_type == 'form':
        lines.append('        payload = {')
        for pair in data.split('&'):
            if '=' in pair:
                k, v = pair.split('=', 1)
                lines.append(f'            {repr(k)}: {repr(v)},')
        lines.append('        }')
    elif data:
        lines.append(f'        payload = {repr(data)}')

    # 构建 self.client.xxx(...) 调用
    url_var = repr(full_path)
    lines.append('')
    lines.append(f'        with self.client.{method}(')
    lines.append(f'            {url_var},')
    if filtered_headers:
        lines.append('            headers=headers,')
    if data:
        if data_type == 'json':
            lines.append('            json=payload,')
        elif data_type == 'form':
            lines.append('            data=payload,')
        else:
            lines.append('            data=payload,')
    lines.append('            catch_response=True,')
    lines.append(f'            name={url_var},')
    lines.append('        ) as response:')
    lines.append('            if response.status_code == 200:')
    lines.append('                response.success()')
    lines.append('            else:')
    lines.append('                response.failure(')
    lines.append('                    f"Unexpected status code {response.status_code}: {response.text}"')
    lines.append('                )')
    lines.append('')

    return '\n'.join(lines)
