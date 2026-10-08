"""PawMarket - dog marketplace.

Start the app:      python run.py
Rebuild demo data:  python seed.py --reset
"""
import os

from app import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
