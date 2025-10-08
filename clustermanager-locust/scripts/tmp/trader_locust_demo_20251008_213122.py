from locust import HttpUser, task, between
import random
import json
import time
import hmac
import hashlib
from gevent.lock import Semaphore

# 可配置：签名相关头字段名称，如后端要求变更为 X-SECRET-ID/X-TIMESTAMP/X-SIGN 等，可在此修改
SIGN_SECRET_ID_HEADER = "secretId"
SIGN_TIMESTAMP_HEADER = "timestamp"
SIGN_SIGNATURE_HEADER = "signature"
SECRET_FETCH_PATH = "/chief-trader-x/top/secret/once/fetch"

accounts = [
    {"username": "910055", "password": "123456", "account_id": "M910055", "account_type": "M"},
    {"username": "910018", "password": "123456", "account_id": "M910018", "account_type": "M"},
    {"username": "910019", "password": "123456", "account_id": "M910019", "account_type": "M"}
]

class TraderUser(HttpUser):
    wait_time = between(1, 3)
    # 全局（进程内）登录缓存：同一个账号只登录一次，所有虚拟用户共享
    account_token_cache: dict = {}
    account_login_lock: Semaphore = Semaphore()

    def on_start(self):
        self.account = random.choice(accounts)
        self.ctx = {"account": self.account}
        username = self.account["username"]

        # 命中缓存则直接复用
        cached = TraderUser.account_token_cache.get(username)
        if cached:
            self.ctx.update(cached)
            return

        # 未命中则加锁登录（双检）
        with TraderUser.account_login_lock:
            cached = TraderUser.account_token_cache.get(username)
            if cached:
                self.ctx.update(cached)
                return

            login_url = "/sso-server/test/test-login"
            params = {"c": self.account["username"], "p": self.account["password"]}

            with self.client.get(login_url, params=params, catch_response=True) as resp:
                if resp.status_code == 200:
                    try:
                        data = resp.json()
                        token = data.get("accessToken")
                        if not token:
                            print(f"[ERROR] 登录成功但未返回accessToken: {resp.text}")
                            resp.failure("登录成功但未返回accessToken")
                        else:
                            # 写入缓存，后续同账号复用
                            base_headers = {"Authorization": token, "Content-Type": "application/json"}
                            cache_entry = {"token": token, "base_headers": base_headers}
                            TraderUser.account_token_cache[username] = cache_entry
                            self.ctx.update(cache_entry)
                            print(f"[INFO]用户名 {self.account['username']} 登录成功, 获得accessToken: {token}")
                    except Exception as e:
                        print(f"[ERROR] 登录返回解析失败: {resp.text}")
                        resp.failure(f"解析登录响应失败: {e}")
                else:
                    print(f"[ERROR] 登录失败, 状态码 {resp.status_code}, 返回报文: {resp.text}")
                    resp.failure(f"登录失败: {resp.text}")

    def _get_signature_headers(self, payload_dict: dict | None):
        """获取一次性密钥并生成签名头。
        规则：signature = HMAC_SHA256(sorted_json + timestamp, secret).hexdigest()
        其中 sorted_json 为对 body 进行 key 升序排序后 JSON.stringify 的结果（无空格），timestamp 为毫秒字符串。
        返回：{secretId, timestamp, signature} 字典；失败返回 None。
        """
        try:
            body_dict = payload_dict or {}
            # 对 body 进行 key 升序排序，并以与 JSON.stringify 相近的方式序列化（无空格、按 key 排序）
            sorted_json = json.dumps(body_dict, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            timestamp = str(int(time.time() * 1000))

            # 获取一次性密钥
            token = self.ctx.get("token") if hasattr(self, "ctx") else getattr(self, "token", None)
            if not token:
                print("[ERROR] 缺少登录 token，无法获取一次性密钥")
                return None

            headers = {"Authorization": token}
            with self.client.get(SECRET_FETCH_PATH, headers=headers, catch_response=True) as resp:
                if resp.status_code != 200:
                    print(f"[ERROR] 获取一次性密钥失败: {resp.status_code}, {resp.text}")
                    resp.failure("获取一次性密钥失败")
                    return None
                try:
                    data = resp.json()
                except Exception as e:
                    print(f"[ERROR] 一次性密钥响应解析失败: {resp.text}")
                    resp.failure(f"解析一次性密钥响应失败: {e}")
                    return None

            d = data.get("data") if isinstance(data, dict) else None
            secret_id = d.get("secretId") if isinstance(d, dict) else None
            secret = d.get("secret") if isinstance(d, dict) else None
            if not secret_id or not secret:
                print(f"[ERROR] 一次性密钥响应缺少字段: {data}")
                return None

            signature = hmac.new(secret.encode("utf-8"), (sorted_json + timestamp).encode("utf-8"), hashlib.sha256).hexdigest()
            return {
                SIGN_SECRET_ID_HEADER: secret_id,
                SIGN_TIMESTAMP_HEADER: timestamp,
                SIGN_SIGNATURE_HEADER: signature,
            }
        except Exception as e:
            print(f"[ERROR] 生成签名异常: {e}")
            return None

    
    @task(1)
    def query_orders(self):
        if not hasattr(self, "ctx") or not self.ctx.get("base_headers"):
            return
        headers = dict(self.ctx["base_headers"])  # 基础头从 dict 取出
        query_data = {
            "AccountID": self.account["account_id"],
            "AccountType": self.account["account_type"],
            "Exchange": "HK",
            "Symbol": ""
        }
        # 生成签名头
        sign_headers = self._get_signature_headers(query_data)
        if not sign_headers:
            print("[ERROR] 查询订单前生成签名失败，跳过本次请求")
            return
        headers.update(sign_headers)

        with self.client.post("/chief-trader-x/top/pc/order/listByAccountId", headers=headers,
                              data=json.dumps(query_data, separators=(",", ":")), catch_response=True) as resp:
            if resp.status_code != 200:
                print(f"[ERROR] 查询订单失败: {resp.status_code}, 返回报文: {resp.text}")
                resp.failure(f"查询订单失败: {resp.text}")
            else:
                try:
                    body = resp.json()
                except Exception:
                    resp.failure(f"查询订单响应非 JSON: {resp.text}")
                    return
                code = body.get("code")
                if code != 0:
                    msg = body.get("msg")
                    resp.failure(f"查询订单业务失败: code={code}, msg={msg}, body={body}")
                else:
                    resp.success()
