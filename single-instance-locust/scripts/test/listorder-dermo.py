from locust import HttpUser, task, between

class TraderUser(HttpUser):
    wait_time = between(1, 3)  # 模拟用户请求间隔（1-3秒）

    @task
    def get_order_list(self):
        url = "/api/v1/www/order/list"
        headers = {
            "Authorization": "eyJhbGciOiJIUzI1NiJ9..,
            "Content-Type": "application/json"
        }
        payload = {
            "xxx1": "1111",
            "xxx2": "2222"

        with self.client.post(url, headers=headers, json=payload, catch_response=True, name=url) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Unexpected status code {response.status_code}: {response.text}")
