# from fastapi.testclient import TestClient
# from config import app
#
# client = TestClient(app)
#
#
# def test_read_main():
#     response = client.get("/")
#     assert response.status_code == 200
#
#
# def test_read_holidays():
#     response = client.get("/api/v1/read/holidays")
#     assert response.status_code == 200
#     assert response.json() is not None
#
#
# def test_read_login():
#     username = "superuser"
#     password = "i@9d1P5tg_"
#     response = client.post("/api/v1/login",
#                            data={
#                                "username": username,
#                                "password": password}
#                            )
#     assert response.status_code == 200
#     assert response.json() is not None
#
#
# def test_read_requests_actual():
#     response = client.post("/api/v1/read/requests/actual")
#     assert response.status_code == 200
#     assert response.json() is not None
#
#
# def test_read_requests_search():
#     response = client.get("/api/v1/read/search/=Иванов")
#     assert response.status_code == 200
#     assert response.json() is not None
#
#
# def test_read_passages_actual():
#     response = client.post("/api/v1/read/passages/actual")
#     assert response.status_code == 200
#     assert response.json() is not None
#
#
# def test_read_requests_actual_min():
#     response = client.post("/api/v1/read/requests/actual/min")
#     assert response.status_code == 200
#     assert response.json() is not None
