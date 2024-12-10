import requests
import argparse
import time
import os

BASE_URL_SORT = "http://localhost:8000"
BASE_URL_LATENCY = "http://localhost:8001"


def test_sort(max_size: int, time_out: float, increment: int):

    url = f"{BASE_URL_SORT}/sort"
    params = {"max_size": max_size, "time_out": time_out, "increment": increment}

    try:
        response = requests.get(url, params = params)
        print(f"Sort test: Status: {response.status_code}, Response: {response.json()}")
    except Exception as e:
        print(f"Sort test: Error: {e}")

def test_latency(tentativas: int, host: str):

    url = f"{BASE_URL_LATENCY}/latency"
    params = {"tentativas": tentativas, "host": host}

    try:
        response = requests.get(url, params=params)
        print(f"Latency test: Status: {response.status_code}, Response:{response.json()}")
    except Exception as e:
        print(f"Latency test: Error: {e}")

def read_config(file_path="config.txt"):

    config = {}
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Arquivo de configuração '{file_path}' não encontrado.")
    
    with open(file_path, "r") as file:
        for line in file:
            if "=" in line:
                key, value = line.strip().split("=", 1)
                config[key.strip()] = value.strip()
    return config



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Server tests for openTelemetry")
    parser.add_argument(
        "--config",
        type=str,
        default="config.txt",
        help="Caminho para o arquivo de configuração. Padrão: 'config.txt'"
    )
    args = parser.parse_args()

    try:
        config = read_config(args.config)
        trys = int(config.get("trys", 10))
        host = config.get("host", "8.8.8.8")
        requests_count = int(config.get("requests", 5))
        max_size = int(config.get("max_size", 10000))
        time_out = float(config.get("time_out", 0.5))
        increment = int(config.get("increment", 500))

        for _ in range(requests_count):
            test_latency(tentativas=trys, host=host)

        for _ in range(requests_count):
            test_sort(max_size, time_out, increment)

    except Exception as e:
        print(f"Erro ao executar o script: {e}")