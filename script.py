import logging
import os
from concurrent.futures import ThreadPoolExecutor

import requests

# Configure logging for k8s
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

BASE_URL = os.getenv("API_ENDPOINT", "http://localhost:8000")


def test_sort(max_size: int, time_out: float, increment: int):
    url = f"{BASE_URL}/sort"
    params = {"max_size": max_size, "time_out": time_out, "increment": increment}

    try:
        response = requests.get(url, params=params)
        logger.info(
            f"Sort test: Status: {response.status_code}, Response: {response.json()}"
        )
    except Exception as e:
        logger.error(f"Sort test: Error: {e}")


def test_latency():
    url = f"{BASE_URL}/latency"

    try:
        response = requests.get(url)
        logger.info(
            f"Latency test: Status: {response.status_code}, Response: {response.json()}"
        )
    except Exception as e:
        logger.error(f"Latency test: Error: {e}")


def test_calculate_pi(seconds: float):
    url = f"{BASE_URL}/calculate-pi"
    params = {"seconds": seconds}

    try:
        response = requests.get(url, params=params)
        logger.info(
            f"Calculate Pi test: Status: {response.status_code}, Response: {response.json()}"
        )
    except Exception as e:
        logger.error(f"Calculate Pi test: Error: {e}")


def test_sum_of_n_numbers(target: int):
    url = f"{BASE_URL}/sum-of-n-numbers"
    params = {"target": target}

    try:
        response = requests.get(url, params=params)
        logger.info(
            f"Sum of N Numbers test: Status: {response.status_code}, Response: {response.json()}"
        )
    except Exception as e:
        logger.error(f"Sum of N Numbers test: Error: {e}")


def test_object_creation_deletion(count: int):
    url = f"{BASE_URL}/object-creation-deletion"
    params = {"count": count}

    try:
        response = requests.get(url, params=params)
        logger.info(
            f"Object Creation/Deletion test: Status: {response.status_code}, Response: {response.json()}"
        )
    except Exception as e:
        logger.error(f"Object Creation/Deletion test: Error: {e}")


def read_config(file_path="config.txt"):
    config = {}
    if not os.path.exists(file_path):
        raise FileNotFoundError(
            f"Arquivo de configuração '{file_path}' não encontrado."
        )

    with open(file_path, "r") as file:
        for line in file:
            if "=" in line:
                key, value = line.strip().split("=", 1)
                config[key.strip()] = value.strip()
    return config


def run_tests_in_parallel(test_functions):
    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(func) for func in test_functions]
        for future in futures:
            try:
                future.result()
            except Exception as e:
                logger.error(f"Error in parallel execution: {e}")


if __name__ == "__main__":
    try:
        config = read_config("config.txt")
        trys = int(config.get("trys", 10))
        host = config.get("host", "8.8.8.8")
        requests_count = int(config.get("requests", 5))
        max_size = int(config.get("max_size", 10000))
        time_out = float(config.get("time_out", 0.5))
        increment = int(config.get("increment", 500))
        payload_size = int(config.get("payload_size", 32))
        pi_seconds = float(config.get("pi_seconds", 1))
        target = int(config.get("target", 100000000))
        object_count = int(config.get("object_count", 1000000))
        functions = config.get("functions", "all")

        test_functions = []

        for _ in range(requests_count):

            if functions == "all":
                test_functions.append(lambda: test_latency())
                test_functions.append(lambda: test_sort(max_size, time_out, increment))
                test_functions.append(lambda: test_calculate_pi(pi_seconds))
                test_functions.append(lambda: test_sum_of_n_numbers(target))
                test_functions.append(
                    lambda: test_object_creation_deletion(object_count)
                )

            if "latency" in functions:
                test_functions.append(lambda: test_latency())
            if "sort" in functions:
                test_functions.append(lambda: test_sort(max_size, time_out, increment))
            if "calculate_pi" in functions:
                test_functions.append(lambda: test_calculate_pi(pi_seconds))
            if "sum_of_n_numbers" in functions:
                test_functions.append(lambda: test_sum_of_n_numbers(target))
            if "object_creation_deletion" in functions:
                test_functions.append(
                    lambda: test_object_creation_deletion(object_count)
                )

        logger.info("Running tests in parallel...")
        run_tests_in_parallel(test_functions)

    except Exception as e:
        logger.error(f"Erro ao executar o script: {e}")
