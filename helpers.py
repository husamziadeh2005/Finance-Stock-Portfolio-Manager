import requests

from flask import redirect, render_template, session
from functools import wraps


def apology(message, code=400):
    return render_template("apology.html", message=message, code=code), code


def login_required(function):
    @wraps(function)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return function(*args, **kwargs)

    return decorated_function


def lookup(symbol):
    symbol = symbol.strip().upper()
    if not symbol:
        return None

    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"

    try:
        response = requests.get(
            url,
            params={"interval": "1d", "range": "1d"},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()

        result = data.get("chart", {}).get("result")
        if not result:
            return None

        meta = result[0].get("meta", {})
        price = meta.get("regularMarketPrice")
        if price is None:
            return None

        name = meta.get("longName") or meta.get("shortName") or symbol

        return {
            "name": name,
            "price": float(price),
            "symbol": meta.get("symbol", symbol).upper(),
        }
    except (requests.RequestException, ValueError, KeyError, TypeError):
        return None


def usd(value):
    return f"${value:,.2f}"
