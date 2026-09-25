import os, sqlite3, base64, requests, openai
from flask import Flask, render_template_string, request, redirect, url_for, abort
app = Flask(__name__)
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
DB = 'docs.db'
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS docs (id INTEGER PRIMARY KEY AUTOINCREMENT, repo_url TEXT, title TEXT, installation TEXT, maintenance TEXT, troubleshooting TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()
def gh_get(url):
    headers = {'Accept': 'application/vnd.github.v3+json'}
    if GITHUB_TOKEN:
        headers['Authorization'] = f'token {GITHUB_TOKEN}'
    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f'GitHub error: {e}')
        return None
def get_repo(owner, repo):
    return gh_get(f'https://api.github.com/repos/{owner}/{repo}')
def get_tree(owner, repo):
    url = f'https://api.github.com/repos/{owner}/{repo}/git/trees/main?recursive=1'
    data = gh_get(url)
    if data is None:
        url = f'https://api.github.com/repos/{owner}/{repo}/git/trees/master?recursive=1'
        data = gh_get(url)
    return data
def get_readme(owner, repo):
    data = gh_get(f'https://api.github.com/repos/{owner}/{repo}/readme')
    if data and 'content' in data:
        return base64.b64decode(data['content']).decode('utf-8')
    return None
def get_deps(owner, repo):
    files = ['requirements.txt', 'package.json', 'Pipfile', 'pom.xml']
    deps = {}
    for f in files:
        data = gh_get(f'https://api.github.com/repos/{owner}/{repo}/contents/{f}')
        if data and 'content' in data:
            deps[f] = base64.b64decode(data['content']).decode('utf-8')
    return deps
def generate(repo_info, readme, deps, tree):
    if not OPENAI_API_KEY:
        raise ValueError('OpenAI key missing')
    openai.api_key = OPENAI_API_KEY
    prompt = f'''Generate installation and maintenance documentation for the following project.

Repository: {repo_info.get('full_name', '')}
Description: {repo_info.get('description', '')}
'''
    if readme:
        prompt += f'''README:
{readme}
'''
    if deps:
        prompt += 'Dependency files:\\n'
        for f, c in deps.items():
            prompt += f'--- {f} ---\\n{c}\\n'
    prompt += '''
Please produce sections:
1. Installation Guide
2. Maintenance Schedule
3. Troubleshooting
'''
    try:
        resp = openai.ChatCompletion.create(
            model='gpt-3.5-turbo',
            messages=[{'role': 'system', 'content': 'You are a technical writer.'},
                      {'role': 'user', 'content': prompt}],
            temperature=0.7,
            max_tokens=1024
        )
        text = resp['choices'][0]['message']['content']
        inst, maint, troub = '', '', ''
        cur = None
        for line in text.splitlines():
            low = line.lower()
            if low.startswith('1. installation'):
                cur = 'inst'
                inst = ''
            elif low.startswith('2. maintenance'):
                cur = 'maint'
                maint = ''
            elif low.startswith('3. troubleshooting'):
                cur = 'troub'
                troub = ''
            else:
                if cur == 'inst':
                    inst += line + '\\n'
                elif cur == 'maint':
                    maint += line + '\\n'
                elif cur == 'troub':
                    troub += line + '\\n'
        return inst.strip(), maint.strip(), troub.strip()
    except Exception as e:
        print(f'OpenAI error: {e}')
        return None, None, None

@app.route('/')
def index():
    html = '''
    <!DOCTYPE html>
    <html lang='en'>
    <head>
        <meta charset='UTF-8'>
        <title>DocuGen</title>
        <link rel='stylesheet' href='/static/style.css'>
    </head>
    <body>
        <div class='container'>
            <h1>DocuGen</h1>
            <p>Generate installation and maintenance guides for GitHub repositories.</p>
            <form method='POST' action='/generate'>
                <label for='repo_url'>GitHub Repository URL:</label>
                <input type='text' id='repo_url' name='repo_url' placeholder='https://github.com/owner/repo' required>
                <input type='submit' value='Generate'>
            </form>
        </div>
    </body>
    </html>
    '''
    return render_template_string(html)

@app.route('/generate', methods=['POST'])
def generate():
    repo_url = request.form.get('repo_url', '').strip()
    if not repo_url:
        return render_template_string('''<p class='error'>Please enter a repository URL.</p>''')
    try:
        parts = repo_url.split('/')
        if len(parts) < 2:
            raise ValueError
        owner = parts[-2]
        repo = parts[-1]
        if repo.endswith('.git'):
            repo = repo[:-4]
    except:
        return render_template_string('''<p class='error'>Invalid repository URL.</p>''')
    repo_info = get_repo(owner, repo)
    if not repo_info:
        return render_template_string('''<p class='error'>Failed to fetch repository information.</p>''')
    readme = get_readme(owner, repo)
    deps = get_deps(owner, repo)
    tree = get_tree(owner, repo)
    inst, maint, troub = generate(repo_info, readme, deps, tree)
    if inst is None:
        return render_template_string('''<p class='error'>Failed to generate documentation.</p>''')
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''INSERT INTO docs (repo_url, title, installation, maintenance, troubleshooting) VALUES (?, ?, ?, ?, ?)''',
              (repo_url, repo_info.get('name', ''), inst, maint, troub))
    conn.commit()
    doc_id = c.lastrowid
    conn.close()
    return redirect(url_for('view_doc', doc_id=doc_id))

@app.route('/docs')
def list_docs():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('SELECT id, title, repo_url, created_at FROM docs ORDER BY created_at DESC')
    rows = c.fetchall()
    conn.close()
    html = '''
    <!DOCTYPE html>
    <html lang='en'>
    <head>
        <meta charset='UTF-8'>
        <title>DocuGen - All Guides</title>
        <link rel='stylesheet' href='/static/style.css'>
    </head>
    <body>
        <div class='container'>
            <h1>Generated Guides</h1>
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Title</th>
                        <th>Repository</th>
                        <th>Created</th>
                    </tr>
                </thead>
                <tbody>
                    {% for doc in docs %}
                    <tr>
                        <td>{{ doc[0] }}</td>
                        <td><a href='/docs/{{ doc[0] }}'>{{ doc[1] }}</a></td>
                        <td><a href='{{ doc[2] }}' target='_blank'>{{ doc[2] }}</a></td>
                        <td>{{ doc[3] }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
            <div class='back'>
                <a href='/'>← Back to home</a>
            </div>
        </div>
    </body>
    </html>
    '''
    return render_template_string(html, docs=rows)

@app.route('/docs/<int:doc_id>')
def view_doc(doc_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('SELECT * FROM docs WHERE id = ?', (doc_id,))
    row = c.fetchone()
    conn.close()
    if row is None:
        abort(404)
    html = '''
    <!DOCTYPE html>
    <html lang='en'>
    <head>
        <meta charset='UTF-8'>
        <title>DocuGen - {{ title }}</title>
        <link rel='stylesheet' href='/static/style.css'>
    </head>
    <body>
        <div class='container'>
            <h1>{{ title }}</h1>
            <p><strong>Repository:</strong> <a href='{{ repo_url }}' target='_blank'>{{ repo_url }}</a></p>
            <h2>Installation Guide</h2>
            <pre>{{ installation }}</pre>
            <h2>Maintenance Schedule</h2>
            <pre>{{ maintenance }}</pre>
            <h2>Troubleshooting</h2>
            <pre>{{ troubleshooting }}</pre>
            <div class='back'>
                <a href='/docs'>← Back to list</a>
            </div>
        </div>
    </body>
    </html>
    '''
    return render_template_string(html, title=row[2], repo_url=row[1], installation=row[3], maintenance=row[4], troubleshooting=row[5])

if __name__ == '__main__':
    init_db()
    app.run(debug=True)