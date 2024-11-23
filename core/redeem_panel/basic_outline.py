from flask import Flask, request, render_template, redirect, url_for, flash
import sqlite3

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Needed for flash messages
html_file = "index.html"
DATABASE = 'redeempanel.db'

# Database setup
def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            boost_key TEXT NOT NULL,
            server_invite_link TEXT NOT NULL,
            nickname TEXT,
            bio TEXT
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/', methods=['GET', 'POST'])
def redeem_boost():
    if request.method == 'POST':
        boost_key = request.form.get('boost_key')
        server_invite_link = request.form.get('server_invite_link')
        nickname = request.form.get('nickname', None)
        bio = request.form.get('bio', None)
        
        # Validate required fields
        if not boost_key or not server_invite_link:
            flash('Boost Key and Server Invite Link are required!', 'error')
            return redirect(url_for('redeem_boost'))
        
        # Save to database
        try:
            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO submissions (boost_key, server_invite_link, nickname, bio)
                VALUES (?, ?, ?, ?)
            ''', (boost_key, server_invite_link, nickname, bio))
            conn.commit()
            conn.close()
            
            flash('Boost redeemed successfully!', 'success')
            return redirect(url_for('redeem_boost'))
        except Exception as e:
            flash(f'An error occurred: {e}', 'error')
            return redirect(url_for('redeem_boost'))
    
    return render_template(html_file)

if __name__ == '__main__':
    init_db()  # Initialize the database
    app.run(debug=True)
