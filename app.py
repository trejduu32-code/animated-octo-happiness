# app.py
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
import sqlite3
import random
import string
import uvicorn

app = FastAPI()

# --- Database setup ---
conn = sqlite3.connect("urls.db", check_same_thread=False)
c = conn.cursor()
c.execute('''
CREATE TABLE IF NOT EXISTS urls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    long_url TEXT NOT NULL,
    short_code TEXT NOT NULL UNIQUE
)
''')
conn.commit()

# --- Helper functions ---
def generate_code(length=6):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def shorten_url(long_url, custom_code=None):
    if custom_code:
        short_code = custom_code
    else:
        short_code = generate_code()

    # Ensure code is unique
    while c.execute("SELECT * FROM urls WHERE short_code=?", (short_code,)).fetchone():
        short_code = generate_code()
    
    c.execute("INSERT INTO urls (long_url, short_code) VALUES (?, ?)", (long_url, short_code))
    conn.commit()
    return short_code

def get_long_url(short_code):
    row = c.execute("SELECT long_url FROM urls WHERE short_code=?", (short_code,)).fetchone()
    return row[0] if row else None

def delete_url(short_code):
    c.execute("DELETE FROM urls WHERE short_code=?", (short_code,))
    conn.commit()

# --- Routes ---
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    urls = c.execute("SELECT short_code, long_url FROM urls ORDER BY id DESC").fetchall()
    host = request.url.scheme + "://" + request.url.netloc
    html = """
    <h1>🔗 URL Shortener</h1>
    <form method="post" action="/shorten">
        Long URL: <input name="long_url" size="50">
        Custom Code (optional): <input name="custom_code" size="10">
        <button type="submit">Shorten URL</button>
    </form>
    <hr>
    <h2>Existing URLs</h2>
    <ul>
    """
    for code, long_url in urls:
        html += f"""
        <li>
            <a href='{host}/{code}' target='_blank'>{host}/{code}</a> → {long_url}
            <button onclick="navigator.clipboard.writeText('{host}/{code}')">Copy</button>
            <form method="post" action="/delete" style="display:inline;">
                <input type="hidden" name="short_code" value="{code}">
                <button type="submit">Delete</button>
            </form>
        </li>
        """
    html += "</ul>"
    return html

@app.post("/shorten")
def shorten(request: Request, long_url: str = Form(...), custom_code: str = Form(None)):
    if not long_url:
        return HTMLResponse("<h3>Error: Please enter a valid URL</h3><a href='/'>Go Back</a>")
    
    short_code = shorten_url(long_url, custom_code if custom_code else None)
    host = request.url.scheme + "://" + request.url.netloc
    return HTMLResponse(f"""
        <h3>Short URL created!</h3>
        <a href='{host}/{short_code}' target='_blank'>{host}/{short_code}</a>
        <button onclick="navigator.clipboard.writeText('{host}/{short_code}')">Copy</button>
        <br><br>
        <a href='/'>Go Back</a>
    """)

@app.post("/delete")
def delete(short_code: str = Form(...)):
    delete_url(short_code)
    return RedirectResponse("/", status_code=303)

@app.get("/{short_code}")
def redirect_short_url(short_code: str):
    long_url = get_long_url(short_code)
    if long_url:
        return RedirectResponse(long_url)
    return HTMLResponse("<h3>URL not found</h3><a href='/'>Go Back</a>")

# --- Run the app ---
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
