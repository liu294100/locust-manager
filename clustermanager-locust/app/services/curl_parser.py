# -*- coding: utf-8 -*-
"""
cURL 命令解析器
将 curl 命令解析为结构化数据，并生成 Locust 压测脚本
"""

import re
import json
import shlex
from urllib.parse import urlparse, parse_qs, urlencode


def _is_url(s):
    """判断字符串是否为 URL（含无协议的域名格式）"""
    cleaned = s.strip().strip("'\"")
    if cleaned.startswith('http://') or cleaned.startswith('https://'):
        return True
    # 匹配无协议的域名格式：xxx.xxx.xxx/path 或 localhost:port/path
    if re.match(r'^[a-zA-Z0-9][-a-zA-Z0-9]*(\.[a-zA-Z0-9][-a-zA-Z0-9]*)+[:/]', cleaned):
        return True
    if re.match(r'^localhost[:/]', cleaned):
        return True
    return False


def _normalize_url(url):
    """规范化 URL，确保有协议前缀"""
    url = url.strip().strip("'\"")
    if not url.startswith('http://') and not url.startswith('https://'):
        # 无协议前缀，默认加 https://
        url = 'https://' + url
    return url


def _extract_url(s):
    """从字符串中提取并规范化 URL"""
    return _normalize_url(s)


# 不带参数的 curl 选项（布尔开关），遇到这些只跳自身，不吃下一个 token
_NO_ARG_OPTIONS = {
    '-#', '--progress-bar', '-0', '--http1.0', '--http1.1', '--http2',
    '-4', '--ipv4', '-6', '--ipv6',
    '-f', '--fail', '--fail-early',
    '-g', '--globoff',
    '-i', '--include',
    '-I', '--head',
    '-k', '--insecure',
    '-l', '--list-only',
    '-L', '--location',
    '-n', '--netrc',
    '-N', '--no-buffer',
    '-s', '--silent',
    '-S', '--show-error',
    '-v', '--verbose',
    '--compressed',
    '--create-dirs',
    '--raw',
    '--ssl', '--ssl-reqd',
    '--tr-encoding',
    '--tcp-nodelay',
    '--tcp-fastopen',
    '--path-as-is',
    '--no-keepalive',
    '--no-sessionid',
    '--ntlm',
    '--basic', '--digest',
}

# 带一个参数的 curl 选项，遇到这些跳自身 + 下一个 token
_ONE_ARG_OPTIONS = {
    '-o', '--output',
    '-A', '--user-agent',
    '-e', '--referer',
    '-x', '--proxy',
    '-U', '--proxy-user',
    '-w', '--write-out',
    '-T', '--upload-file',
    '-r', '--range',
    '-t', '--telnet-option',
    '-z', '--time-cond',
    '--connect-timeout', '--max-time', '-m',
    '--retry', '--retry-delay', '--retry-max-time',
    '--resolve', '--cacert', '--capath',
    '--cert', '-E', '--key',
    '--ciphers', '--tls-max', '--tlsv1',
    '--interface', '--local-port',
    '--dns-servers', '--dns-interface',
    '--limit-rate', '--max-redirs',
    '--noproxy', '--proto',
    '--socks4', '--socks5',
    '-Y', '--speed-limit', '-y', '--speed-time',
}


def parse_curl(curl_cmd):
    """解析 curl 命令为结构化数据

    支持从浏览器 DevTools（Chrome/Firefox/Edge）、Postman、命令行等
    复制的各种 curl 格式，包括多行续行、各种引号风格。
    """
    # 预处理：合并多行
    cmd = curl_cmd.strip()
    cmd = re.sub(r'\\\s*\r?\n', ' ', cmd)  # Unix 续行
    cmd = re.sub(r'\^\s*\r?\n', ' ', cmd)  # Windows cmd 续行
    cmd = re.sub(r'`\s*\r?\n', ' ', cmd)   # PowerShell 续行
    cmd = cmd.replace('\r\n', ' ').replace('\n', ' ')
    cmd = re.sub(r'\s+', ' ', cmd).strip()

    # 去掉开头的 curl（兼容 curl.exe）
    cmd = re.sub(r'^curl(?:\.exe)?\s+', '', cmd, flags=re.IGNORECASE)

    result = {
        'method': 'GET',
        'url': '',
        'headers': {},
        'cookies': {},
        'data': None,
        'data_type': None,  # 'form', 'json', 'raw'
        'auth': None,
    }

    # ---- 第一步：先用正则直接提取 URL（最可靠的兜底） ----
    # 匹配带协议的 URL
    url_pattern = re.compile(
        r"""(?:^|\s|['"])"""
        r"""(https?://[^\s'"\\]+)""",
        re.IGNORECASE
    )
    url_match = url_pattern.search(cmd)
    if url_match:
        result['url'] = url_match.group(1).rstrip("'\"")
    else:
        # 匹配无协议的域名格式：xxx.xxx.xxx/path
        bare_url_pattern = re.compile(
            r"""(?:^|\s|['"])"""
            r"""([a-zA-Z0-9][-a-zA-Z0-9]*(?:\.[a-zA-Z0-9][-a-zA-Z0-9]*)+"""
            r"""(?::\d+)?/[^\s'"\\]*)""",
            re.IGNORECASE
        )
        bare_match = bare_url_pattern.search(cmd)
        if bare_match:
            result['url'] = 'https://' + bare_match.group(1).rstrip("'\"")

    # ---- 第二步：分词解析选项和参数 ----
    try:
        tokens = shlex.split(cmd, posix=True)
    except ValueError:
        # shlex 解析失败（常见于 Windows PowerShell 复制的 curl）
        tokens = _manual_tokenize(cmd)

    i = 0
    while i < len(tokens):
        token = tokens[i]

        # -X / --request
        if token in ('-X', '--request') and i + 1 < len(tokens):
            result['method'] = tokens[i + 1].upper()
            i += 2

        # -H / --header
        elif token in ('-H', '--header') and i + 1 < len(tokens):
            header = tokens[i + 1]
            if ':' in header:
                key, val = header.split(':', 1)
                key = key.strip()
                val = val.strip()
                if key.lower() == 'cookie':
                    for pair in val.split(';'):
                        pair = pair.strip()
                        if '=' in pair:
                            ck, cv = pair.split('=', 1)
                            result['cookies'][ck.strip()] = cv.strip()
                else:
                    result['headers'][key] = val
            i += 2

        # -b / --cookie
        elif token in ('-b', '--cookie') and i + 1 < len(tokens):
            cookie_str = tokens[i + 1]
            for pair in cookie_str.split(';'):
                pair = pair.strip()
                if '=' in pair:
                    ck, cv = pair.split('=', 1)
                    result['cookies'][ck.strip()] = cv.strip()
            i += 2

        # -d / --data / --data-raw / --data-binary / --data-urlencode
        elif token in ('-d', '--data', '--data-raw', '--data-binary',
                       '--data-urlencode') and i + 1 < len(tokens):
            raw_data = tokens[i + 1]
            result['data'] = raw_data
            # 判断数据类型
            content_type = result['headers'].get(
                'Content-Type', result['headers'].get('content-type', ''))
            if 'application/json' in content_type:
                result['data_type'] = 'json'
            elif 'application/x-www-form-urlencoded' in content_type:
                result['data_type'] = 'form'
            else:
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

        # -u / --user
        elif token in ('-u', '--user') and i + 1 < len(tokens):
            result['auth'] = tokens[i + 1]
            i += 2

        # --url（显式 URL 参数）
        elif token == '--url' and i + 1 < len(tokens):
            result['url'] = _extract_url(tokens[i + 1])
            i += 2

        # 无参数的布尔选项
        elif token in _NO_ARG_OPTIONS:
            i += 1

        # 已知的带参数选项
        elif token in _ONE_ARG_OPTIONS:
            i += 2

        # 其他以 - 开头的未知选项
        elif token.startswith('-'):
            # 如果下一个 token 是 URL，不要跳过它
            if i + 1 < len(tokens) and _is_url(tokens[i + 1]):
                i += 1
            # 如果下一个 token 也是选项或不存在，只跳自身
            elif i + 1 < len(tokens) and not tokens[i + 1].startswith('-'):
                i += 2  # 假设是带参数的未知选项
            else:
                i += 1

        # 非选项 token -> 可能是 URL
        else:
            url = _extract_url(token)
            if _is_url(token):
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

def generate_signed_locust_script(parsed, script_name='SignedCurlTask', secret_path='/api/secret/fetch'):
    """根据解析结果生成带 HMAC-SHA256 签名的 Locust 压测脚本

    签名流程（与 Postman pre-request script 一致）：
    1. 从 Authorization header 获取 token
    2. GET secret_path 获取 secretId + secret
    3. body JSON key 升序排序后 stringify（无空格）
    4. signature = HMAC_SHA256(sorted_json + timestamp, secret).hexdigest()
    5. 请求头附加 secretId / timestamp / signature
    """
    url_parsed = urlparse(parsed['url'])
    path = url_parsed.path or '/'
    query = url_parsed.query

    method = parsed['method'].lower()
    headers = parsed['headers']
    data = parsed['data']
    data_type = parsed['data_type']

    # 过滤浏览器自动附加的无关请求头
    skip_headers = {
        'host', 'content-length', 'connection', 'accept-encoding',
        'sec-fetch-dest', 'sec-fetch-mode', 'sec-fetch-site',
        'sec-ch-ua', 'sec-ch-ua-mobile', 'sec-ch-ua-platform',
        'upgrade-insecure-requests', 'origin', 'referer',
        'user-agent', 'accept', 'accept-language',
        # 签名相关头由脚本动态生成，不从 curl 中带入
        'secretid', 'timestamp', 'signature',
    }
    filtered_headers = {k: v for k, v in headers.items()
                        if k.lower() not in skip_headers}

    # cookies
    if parsed.get('cookies'):
        cookie_str = '; '.join(f'{k}={v}' for k, v in parsed['cookies'].items())
        filtered_headers['Cookie'] = cookie_str

    full_path = path
    if query:
        full_path = f'{path}?{query}'

    # task 方法名
    path_part = path.rstrip('/').split('/')[-1] if path.rstrip('/') else 'request'
    task_method_name = re.sub(r'[^a-zA-Z0-9_]', '_', path_part).strip('_') or 'request'

    # 构建 payload 代码
    payload_code = ''
    if data and data_type == 'json':
        try:
            parsed_json = json.loads(data)
            items = [f'            {repr(k)}: {repr(v)},' for k, v in parsed_json.items()]
            payload_code = '        payload = {\n' + '\n'.join(items) + '\n        }'
        except (json.JSONDecodeError, TypeError, AttributeError):
            payload_code = f'        payload = json.loads({repr(data)})'
    elif data:
        payload_code = f'        payload = {repr(data)}'

    # 构建 headers 字典代码
    headers_items = [f'            {repr(k)}: {repr(v)},' for k, v in filtered_headers.items()]
    headers_code = '        headers = {\n' + '\n'.join(headers_items) + '\n        }' if headers_items else '        headers = {}'

    # 构建请求调用参数
    request_kwargs = [f'            {repr(full_path)},']
    request_kwargs.append('            headers=headers,')
    if data:
        if data_type == 'json':
            request_kwargs.append('            data=data,')
        else:
            request_kwargs.append('            data=payload,')
    request_kwargs.append('            catch_response=True,')
    request_kwargs.append(f'            name={repr(full_path)},')
    request_call = '\n'.join(request_kwargs)

    script = f'''# -*- coding: utf-8 -*-
"""
由 cURL 命令自动生成的 Locust 压测脚本（带签名）
目标: {method.upper()} {path}
签名URI: {secret_path}

签名流程:
1. 获取一次性密钥 (GET {secret_path})
2. body JSON key 升序排序 -> stringify
3. signature = HMAC_SHA256(sorted_json + timestamp, secret)
4. 请求头附加 secretId / timestamp / signature
"""
import json
import time
import hmac
import hashlib
from locust import HttpUser, task, between


class {script_name}User(HttpUser):
    wait_time = between(1, 3)

    def _get_signature_headers(self, payload_dict, token):
        """获取一次性密钥并生成签名头

        Args:
            payload_dict: 请求体字典（用于签名计算）
            token: Authorization token

        Returns:
            dict: 包含 secretId, timestamp, signature 的字典；失败返回 None
        """
        try:
            body_dict = payload_dict if isinstance(payload_dict, dict) else {{}}
            sorted_json = json.dumps(body_dict, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            timestamp = str(int(time.time() * 1000))

            with self.client.get(
                {repr(secret_path)},
                headers={{"Authorization": token}},
                catch_response=True,
                name="[签名] 获取一次性密钥",
            ) as resp:
                if resp.status_code != 200:
                    resp.failure(f"获取密钥失败: {{resp.status_code}}")
                    return None
                data = resp.json()

            d = data.get("data") if isinstance(data, dict) else None
            secret_id = d.get("secretId") if isinstance(d, dict) else None
            secret = d.get("secret") if isinstance(d, dict) else None
            if not secret_id or not secret:
                print(f"[ERROR] 密钥响应缺少字段: {{data}}")
                return None

            signature = hmac.new(
                secret.encode("utf-8"),
                (sorted_json + timestamp).encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()

            return {{
                "secretId": secret_id,
                "timestamp": timestamp,
                "signature": signature,
            }}
        except Exception as e:
            print(f"[ERROR] 生成签名异常: {{e}}")
            return None

    @task
    def {task_method_name}(self):
{headers_code}
{payload_code if payload_code else '        payload = {}'}

        # 从 headers 中取 Authorization token 用于获取签名密钥
        token = headers.get("Authorization", "")

        # 获取签名头
        sign_headers = self._get_signature_headers(payload if isinstance(payload, dict) else {{}}, token)
        if not sign_headers:
            print("[WARN] 签名获取失败，跳过本次请求")
            return
        headers.update(sign_headers)
{"" if not data else ""}
        # 序列化 body（key 升序，与签名计算保持一致）
        data = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False) if isinstance(payload, dict) else payload

        with self.client.{method}(
{request_call}
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(
                    f"Unexpected status code {{response.status_code}}: {{response.text}}"
                )
'''
    return script



def generate_signed_locust_script(parsed, script_name='SignedCurlTask',
                                   secret_path='/api/secret/fetch'):
    """根据解析结果生成带 HMAC-SHA256 签名的 Locust 压测脚本

    签名流程（与 Postman pre-request script 一致）：
    1. 从 Authorization header 获取 token
    2. GET secret_path 获取 secretId + secret
    3. body JSON key 升序排序后 stringify（无空格）
    4. signature = HMAC_SHA256(sorted_json + timestamp, secret).hexdigest()
    5. 请求头附加 secretId / timestamp / signature
    """
    url_parsed = urlparse(parsed['url'])
    path = url_parsed.path or '/'
    query = url_parsed.query

    method = parsed['method'].lower()
    headers = parsed['headers']
    data = parsed['data']
    data_type = parsed['data_type']

    # 过滤浏览器自动附加的无关请求头
    skip_headers = {
        'host', 'content-length', 'connection', 'accept-encoding',
        'sec-fetch-dest', 'sec-fetch-mode', 'sec-fetch-site',
        'sec-ch-ua', 'sec-ch-ua-mobile', 'sec-ch-ua-platform',
        'upgrade-insecure-requests', 'origin', 'referer',
        'user-agent', 'accept', 'accept-language',
        # 签名相关头由脚本动态生成，不从 curl 中带入
        'secretid', 'timestamp', 'signature',
    }
    filtered_headers = {k: v for k, v in headers.items()
                        if k.lower() not in skip_headers}

    # cookies
    if parsed.get('cookies'):
        cookie_str = '; '.join(f'{k}={v}' for k, v in parsed['cookies'].items())
        filtered_headers['Cookie'] = cookie_str

    full_path = path
    if query:
        full_path = f'{path}?{query}'

    # task 方法名
    path_part = path.rstrip('/').split('/')[-1] if path.rstrip('/') else 'request'
    task_method_name = re.sub(r'[^a-zA-Z0-9_]', '_', path_part).strip('_') or 'request'

    # 构建 payload 代码行
    payload_lines = []
    if data and data_type == 'json':
        try:
            parsed_json = json.loads(data)
            payload_lines.append('        payload = {')
            for k, v in parsed_json.items():
                payload_lines.append(f'            {repr(k)}: {repr(v)},')
            payload_lines.append('        }')
        except (json.JSONDecodeError, TypeError, AttributeError):
            payload_lines.append(f'        payload = json.loads({repr(data)})')
    elif data:
        payload_lines.append(f'        payload = {repr(data)}')
    else:
        payload_lines.append('        payload = {}')
    payload_code = '\n'.join(payload_lines)

    # 构建 headers 字典代码
    if filtered_headers:
        h_items = [f'            {repr(k)}: {repr(v)},' for k, v in filtered_headers.items()]
        headers_code = '        headers = {\n' + '\n'.join(h_items) + '\n        }'
    else:
        headers_code = '        headers = {}'

    # 构建请求调用
    req_args = [f'            {repr(full_path)},']
    req_args.append('            headers=headers,')
    if data:
        req_args.append('            data=sorted_body,')
    req_args.append('            catch_response=True,')
    req_args.append(f'            name={repr(full_path)},')
    request_call = '\n'.join(req_args)

    script = '''# -*- coding: utf-8 -*-
"""
由 cURL 命令自动生成的 Locust 压测脚本（带签名）
目标: {method_upper} {path}
签名URI: {secret_path}

签名流程:
1. 获取一次性密钥 (GET {secret_path})
2. body JSON key 升序排序 -> stringify
3. signature = HMAC_SHA256(sorted_json + timestamp, secret)
4. 请求头附加 secretId / timestamp / signature
"""
import json
import time
import hmac
import hashlib
from locust import HttpUser, task, between


class {script_name}User(HttpUser):
    wait_time = between(1, 3)

    def _get_signature_headers(self, payload_dict, token):
        """获取一次性密钥并生成签名头"""
        try:
            body_dict = payload_dict if isinstance(payload_dict, dict) else {{}}
            sorted_json = json.dumps(body_dict, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            timestamp = str(int(time.time() * 1000))

            with self.client.get(
                {secret_path_repr},
                headers={{"Authorization": token}},
                catch_response=True,
                name="[签名] 获取一次性密钥",
            ) as resp:
                if resp.status_code != 200:
                    resp.failure(f"获取密钥失败: {{resp.status_code}}")
                    return None
                data = resp.json()

            d = data.get("data") if isinstance(data, dict) else None
            secret_id = d.get("secretId") if isinstance(d, dict) else None
            secret = d.get("secret") if isinstance(d, dict) else None
            if not secret_id or not secret:
                print(f"[ERROR] 密钥响应缺少字段: {{data}}")
                return None

            signature = hmac.new(
                secret.encode("utf-8"),
                (sorted_json + timestamp).encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()

            return {{
                "secretId": secret_id,
                "timestamp": timestamp,
                "signature": signature,
            }}
        except Exception as e:
            print(f"[ERROR] 生成签名异常: {{e}}")
            return None

    @task
    def {task_method_name}(self):
{headers_code}
{payload_code}

        # 从 headers 中取 Authorization token 用于获取签名密钥
        token = headers.get("Authorization", "")

        # 获取签名头
        sign_headers = self._get_signature_headers(
            payload if isinstance(payload, dict) else {{}}, token
        )
        if not sign_headers:
            print("[WARN] 签名获取失败，跳过本次请求")
            return
        headers.update(sign_headers)

        # 序列化 body（key 升序，与签名计算保持一致）
        sorted_body = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ) if isinstance(payload, dict) else str(payload)

        with self.client.{method}(
{request_call}
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(
                    f"Unexpected status code {{response.status_code}}: {{response.text}}"
                )
'''.format(
        method_upper=method.upper(),
        path=path,
        secret_path=secret_path,
        secret_path_repr=repr(secret_path),
        script_name=script_name,
        task_method_name=task_method_name,
        headers_code=headers_code,
        payload_code=payload_code,
        method=method,
        request_call=request_call,
    )

    return script
