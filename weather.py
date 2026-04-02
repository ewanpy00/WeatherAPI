import argparse
import os
from pathlib import Path

import requests
from dotenv import load_dotenv


OPENWEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"


def _load_env() -> None:
    base_dir = Path(__file__).resolve().parent
    load_dotenv(dotenv_path=base_dir / ".env")


def _get_friendly_error(status_code: int, payload: object) -> str:
    if status_code == 404:
        return "Город не найден. Проверьте написание (и страну при необходимости)."
    if status_code == 401:
        return "Неавторизовано: проверьте API-ключ (API_KEY) в .env."
    if status_code == 429:
        return "Слишком много запросов к API. Попробуйте позже."
    if 500 <= status_code:
        return "Внутренняя ошибка сервиса погоды. Попробуйте позже."

    if isinstance(payload, dict):
        message = payload.get("message") or payload.get("error")
        if message:
            return str(message)
    return f"Ошибка API (HTTP {status_code})."


def fetch_weather(city: str) -> tuple[float, str]:
    _load_env()

    api_key = os.getenv("API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "Не найден API_KEY в файле .env. Проверьте корректность .env"
        )

    params = {
        "q": city,
        "appid": api_key,
        "units": "metric",
        "lang": "ru",
    }

    try:
        resp = requests.get(OPENWEATHER_URL, params=params, timeout=15)
    except requests.RequestException as e:
        raise RuntimeError(f"Не удалось подключиться к API погоды: {e}") from e

    try:
        payload = resp.json()
    except ValueError:
        payload = resp.text

    if resp.status_code != 200:
        raise RuntimeError(_get_friendly_error(resp.status_code, payload))

    try:
        temp_c = float(payload["main"]["temp"])
        weather_list = payload.get("weather") or []
        description = weather_list[0].get("description") if weather_list else ""
    except (KeyError, TypeError, ValueError) as e:
        raise RuntimeError("API вернул неожиданный формат данных о погоде.") from e

    description = (description or "").strip()
    return temp_c, description


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Показывает текущую погоду для указанного города (OpenWeatherMap)."
    )
    parser.add_argument(
        "city",
        nargs="+",
        help="Название города (например, 'Moscow' или 'New York', можно в кавычках).",
    )
    args = parser.parse_args()

    city_name = " ".join(args.city)

    try:
        temp_c, description = fetch_weather(city_name)

        output = f"Погода в городе {city_name}: {temp_c:.1f} C"
        if description:
            output += f" - {description}"

        print(output)
        return 0

    except RuntimeError as e:
        print(f"Ошибка: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
