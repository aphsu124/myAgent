import os
import sys
import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, 'scripts'))

from flask import Flask, render_template, jsonify
from modules.token_tracker import get_today_summary, get_month_summary, get_month_total_cost

app = Flask(__name__, template_folder='templates')

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/api/usage')
def api_usage():
    month_name = datetime.date.today().strftime('%m月')
    return jsonify({
        'today':       get_today_summary(),
        'month':       get_month_summary(),
        'month_total': get_month_total_cost(),
        'month_name':  month_name,
    })

if __name__ == '__main__':
    print("🖥️  Jarvis Monitor 儀表板啟動：http://localhost:5001")
    app.run(host='127.0.0.1', port=5001, debug=False)
