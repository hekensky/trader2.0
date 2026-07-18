import os

from flask import Flask, render_template_string, request

from app.calculator import calculate_position_size_usdt

app = Flask(__name__)

HTML = """
<!doctype html>
<html>
  <head>
    <meta charset=\"utf-8\" />
    <title>PM Calculator</title>
    <style>
      body { font-family: Arial, sans-serif; max-width: 520px; margin: 40px auto; }
      input { display: block; width: 100%; padding: 8px; margin-bottom: 10px; }
      button { padding: 10px 14px; }
      .result { margin-top: 16px; padding: 12px; background: #f3f3f3; }
    </style>
  </head>
  <body>
    <h1>PM Calculator</h1>
    <form method=\"post\">
      <label>Entry price</label>
      <input name=\"entry_price\" value=\"100\" />
      <label>Stop loss price</label>
      <input name=\"stop_loss_price\" value=\"95\" />
      <label>Leverage</label>
      <input name=\"leverage\" value=\"10\" />
      <label>Risk USDT</label>
      <input name=\"risk_usdt\" value=\"100\" />
      <button type=\"submit\">Calculate</button>
    </form>
    {% if result %}
      <div class=\"result\">
        <p>Position size: {{ result.position_size }} USDT</p>
        <p>Margin: {{ result.margin }} USDT</p>
      </div>
    {% endif %}
  </body>
</html>
"""


@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    if request.method == "POST":
        entry_price = float(request.form.get("entry_price", 0))
        stop_loss_price = float(request.form.get("stop_loss_price", 0))
        leverage = float(request.form.get("leverage", 0))
        risk_usdt = float(request.form.get("risk_usdt", 0))
        position_size, margin = calculate_position_size_usdt(entry_price, stop_loss_price, leverage, risk_usdt)
        result = {"position_size": round(position_size, 2), "margin": round(margin, 2)}
    return render_template_string(HTML, result=result)


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(debug=True, host="0.0.0.0", port=port)
