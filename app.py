import os

from flask import Flask, flash, jsonify, redirect, render_template, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from database import execute
from helpers import apology, login_required, lookup, usd

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
app.jinja_env.filters["usd"] = usd

execute(
    """
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        symbol TEXT NOT NULL,
        shares INTEGER NOT NULL,
        price NUMERIC NOT NULL,
        transacted TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """
)


@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = "0"
    response.headers["Pragma"] = "no-cache"
    return response


@app.context_processor
def inject_user():
    user = None
    if session.get("user_id"):
        rows = execute(
            "SELECT username FROM users WHERE id = ?",
            (session["user_id"],),
            fetch=True,
        )
        if rows:
            user = rows[0]
    return {"current_user": user}


@app.route("/")
@login_required
def index():
    user_id = session["user_id"]

    stocks = execute(
        """
        SELECT symbol, SUM(shares) AS shares
        FROM transactions
        WHERE user_id = ?
        GROUP BY symbol
        HAVING SUM(shares) > 0
        """,
        (user_id,),
        fetch=True,
    )

    portfolio = []
    stocks_total = 0

    for stock in stocks:
        quote = lookup(stock["symbol"])
        if quote:
            shares = stock["shares"]
            price = quote["price"]
            total = shares * price
            stocks_total += total
            portfolio.append(
                {
                    "symbol": stock["symbol"],
                    "name": quote.get("name", stock["symbol"]),
                    "shares": shares,
                    "price": price,
                    "total": total,
                }
            )

    rows = execute(
        "SELECT cash FROM users WHERE id = ?",
        (user_id,),
        fetch=True,
    )
    cash = rows[0]["cash"]
    grand_total = cash + stocks_total

    for stock in portfolio:
        stock["allocation"] = (stock["total"] / grand_total * 100) if grand_total else 0

    portfolio.sort(key=lambda item: item["total"], reverse=True)

    recent_transactions = execute(
        """
        SELECT symbol, shares, price, transacted
        FROM transactions
        WHERE user_id = ?
        ORDER BY transacted DESC, id DESC
        LIMIT 5
        """,
        (user_id,),
        fetch=True,
    )

    return render_template(
        "index.html",
        portfolio=portfolio,
        cash=cash,
        stocks_total=stocks_total,
        grand_total=grand_total,
        positions_count=len(portfolio),
        recent_transactions=recent_transactions,
    )


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    if request.method == "POST":
        symbol = request.form.get("symbol", "").strip().upper()
        shares_input = request.form.get("shares")

        if not symbol:
            return apology("Please provide a stock symbol.")

        quote = lookup(symbol)
        if quote is None:
            return apology("We could not find that stock symbol.")

        if not shares_input:
            return apology("Please provide the number of shares.")

        try:
            shares = int(shares_input)
        except ValueError:
            return apology("Shares must be a positive whole number.")

        if shares <= 0:
            return apology("Shares must be a positive whole number.")

        price = quote["price"]
        total_cost = shares * price
        user = execute(
            "SELECT cash FROM users WHERE id = ?",
            (session["user_id"],),
            fetch=True,
        )
        cash = user[0]["cash"]

        if total_cost > cash:
            return apology("You do not have enough cash for this purchase.")

        execute(
            """
            INSERT INTO transactions (user_id, symbol, shares, price)
            VALUES (?, ?, ?, ?)
            """,
            (session["user_id"], quote["symbol"], shares, price),
        )
        execute(
            "UPDATE users SET cash = cash - ? WHERE id = ?",
            (total_cost, session["user_id"]),
        )

        flash(f"Bought {shares} share{'s' if shares != 1 else ''} of {quote['symbol']}.", "success")
        return redirect("/")

    return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    transactions = execute(
        """
        SELECT symbol, shares, price, transacted
        FROM transactions
        WHERE user_id = ?
        ORDER BY transacted DESC, id DESC
        """,
        (session["user_id"],),
        fetch=True,
    )
    return render_template("history.html", transactions=transactions)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        session.clear()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username:
            return apology("Please provide your username.", 403)
        if not password:
            return apology("Please provide your password.", 403)

        rows = execute(
            "SELECT * FROM users WHERE username = ?",
            (username,),
            fetch=True,
        )

        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], password):
            return apology("Invalid username or password.", 403)

        session["user_id"] = rows[0]["id"]
        flash("Welcome back!", "success")
        return redirect("/")

    if session.get("user_id"):
        return redirect("/")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    if request.method == "POST":
        symbol = request.form.get("symbol", "").strip().upper()
        if not symbol:
            return apology("Please provide a stock symbol.")

        stock = lookup(symbol)
        if stock is None:
            return apology("We could not find that stock symbol.")

        return render_template("quoted.html", stock=stock)

    return render_template("quote.html")


@app.route("/api/quote")
@login_required
def api_quote():
    symbol = request.args.get("symbol", "").strip().upper()
    if not symbol:
        return jsonify({"ok": False, "message": "Enter a symbol."}), 400

    stock = lookup(symbol)
    if stock is None:
        return jsonify({"ok": False, "message": "Stock not found."}), 404

    return jsonify({"ok": True, "stock": stock})


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirmation = request.form.get("confirmation", "")

        if not username:
            return apology("Please provide a username.")
        if len(username) < 3:
            return apology("Username must be at least 3 characters.")
        if not password:
            return apology("Please provide a password.")
        if len(password) < 6:
            return apology("Password must be at least 6 characters.")
        if password != confirmation:
            return apology("Passwords do not match.")

        existing_user = execute(
            "SELECT id FROM users WHERE username = ?",
            (username,),
            fetch=True,
        )
        if existing_user:
            return apology("That username already exists.")

        password_hash = generate_password_hash(password)
        user_id = execute(
            "INSERT INTO users (username, hash) VALUES (?, ?)",
            (username, password_hash),
        )

        session["user_id"] = user_id
        flash("Account created successfully.", "success")
        return redirect("/")

    if session.get("user_id"):
        return redirect("/")
    return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    user_id = session["user_id"]
    stocks = execute(
        """
        SELECT symbol, SUM(shares) AS shares
        FROM transactions
        WHERE user_id = ?
        GROUP BY symbol
        HAVING SUM(shares) > 0
        ORDER BY symbol
        """,
        (user_id,),
        fetch=True,
    )

    if request.method == "POST":
        symbol = request.form.get("symbol", "").strip().upper()
        shares_input = request.form.get("shares")

        if not symbol:
            return apology("Please select a stock.")
        if not shares_input:
            return apology("Please provide the number of shares.")

        try:
            shares = int(shares_input)
        except ValueError:
            return apology("Shares must be a positive whole number.")

        if shares <= 0:
            return apology("Shares must be a positive whole number.")

        owned = execute(
            """
            SELECT SUM(shares) AS shares
            FROM transactions
            WHERE user_id = ? AND symbol = ?
            """,
            (user_id, symbol),
            fetch=True,
        )

        if not owned or owned[0]["shares"] is None or owned[0]["shares"] < shares:
            return apology("You do not own enough shares.")

        quote = lookup(symbol)
        if quote is None:
            return apology("We could not retrieve the current stock price.")

        price = quote["price"]
        sale_total = shares * price

        execute(
            """
            INSERT INTO transactions (user_id, symbol, shares, price)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, quote["symbol"], -shares, price),
        )
        execute(
            "UPDATE users SET cash = cash + ? WHERE id = ?",
            (sale_total, user_id),
        )

        flash(f"Sold {shares} share{'s' if shares != 1 else ''} of {quote['symbol']}.", "success")
        return redirect("/")

    return render_template("sell.html", stocks=stocks)


@app.route("/addcash", methods=["GET", "POST"])
@login_required
def addcash():
    if request.method == "POST":
        amount_input = request.form.get("amount")

        if not amount_input:
            return apology("Please provide an amount.")

        try:
            amount = float(amount_input)
        except ValueError:
            return apology("Please enter a valid amount.")

        if amount <= 0:
            return apology("Amount must be positive.")
        if amount > 1000000:
            return apology("Amount is too large.")

        execute(
            "UPDATE users SET cash = cash + ? WHERE id = ?",
            (amount, session["user_id"]),
        )

        flash(f"Added {usd(amount)} to your cash balance.", "success")
        return redirect("/")

    return render_template("addcash.html")


if __name__ == "__main__":
    app.run(debug=True)
