from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import feedparser
import urllib.parse

app = FastAPI()

# Initial keywords
keywords_db = ["Broadcast Tech", "ST 2110", "IP Transmission", "4K", "8K"]

# Initial linked target media list (mapping name and RSS query)
media_db = [
    {"name": "ZDNet Korea", "query": "site:zdnet.co.kr"},
    {"name": "ETNews", "query": "site:etnews.com"},
    {"name": "CNET", "query": "site:cnet.com"},
    {"name": "Monthly Audio", "query": "Monthly Audio"},
    {"name": "SMPTE", "query": "SMPTE"},
    {"name": "Broadcast Technology Journal", "query": "Broadcast Technology Journal"}
]

class KeywordRequest(BaseModel):
    keyword: str

class MediaRequest(BaseModel):
    name: str
    query: str

@app.get("/", response_class=HTMLResponse)
def index():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Custom Media News Clipper</title>
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; margin: 0; padding: 20px; }
            .container { max-width: 950px; margin: auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); }
            h1 { color: #333; text-align: center; }
            .section { margin-bottom: 25px; }
            input[type="text"] { width: 42%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; font-size: 15px; margin-right: 5px; }
            button { padding: 10px 18px; background-color: #007bff; color: white; border: none; border-radius: 5px; font-size: 15px; cursor: pointer; }
            button:hover { background-color: #0056b3; }
            .tags { margin-top: 10px; }
            .tag { 
                display: inline-flex; 
                align-items: center; 
                background: #e9ecef; 
                padding: 6px 12px; 
                border-radius: 16px; 
                margin-right: 6px; 
                margin-bottom: 6px; 
                font-size: 14px; 
            }
            .media-badge {
                display: inline-flex;
                align-items: center;
                background: #e2e3e5;
                color: #383d41;
                padding: 5px 10px;
                border-radius: 6px;
                font-size: 13px;
                margin-right: 6px;
                margin-bottom: 6px;
            }
            .delete-btn {
                background: none;
                border: none;
                margin-left: 6px;
                cursor: pointer;
                font-size: 14px;
                color: #868e96;
                padding: 0;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .delete-btn:hover {
                color: #fa5252;
            }
            .source-badge { display: inline-block; background: #e2e3e5; color: #383d41; padding: 2px 8px; border-radius: 4px; font-size: 11px; margin-right: 5px; }
            .news-card { border-bottom: 1px solid #eee; padding: 15px 0; }
            .news-card h3 { margin: 0 0 5px 0; font-size: 18px; }
            .news-card h3 a { color: #007bff; text-decoration: none; }
            .news-card h3 a:hover { text-decoration: underline; }
            .news-card p { color: #666; font-size: 14px; margin: 5px 0; }
            .meta { font-size: 12px; color: #999; margin-top: 5px; }
            .source-box { background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📰 Custom Media News Clipper</h1>
            
            <!-- Target Media Management Section -->
            <div class="source-box">
                <h3>📡 Target Media Management</h3>
                <div style="margin-bottom: 10px;">
                    <input type="text" id="mediaNameInput" placeholder="Media Name (e.g., Bloter)">
                    <input type="text" id="mediaQueryInput" placeholder="Search Query or Site (e.g., site:bloter.net)">
                    <button onclick="addMedia()" style="background-color: #28a745;">Add Media</button>
                </div>
                <div id="mediaList"></div>
            </div>

            <!-- Interest Keywords Management Section -->
            <div class="section">
                <h3>Keywords Management</h3>
                <input type="text" id="keywordInput" placeholder="Enter keyword to add (e.g., AI, Media Server)" style="width: 65%;" onkeypress="if(event.key === 'Enter') addKeyword()">
                <button onclick="addKeyword()">Add Keyword</button>
                <div class="tags" id="tagList"></div>
            </div>

            <hr>

            <div class="section">
                <h2>Real-Time Filtered News</h2>
                <button onclick="loadNews()">Refresh News</button>
                <div id="newsContainer" style="margin-top: 15px;">Loading news...</div>
            </div>
        </div>

        <script>
            async function fetchConfig() {
                const res = await fetch('/config');
                const data = await res.json();
                
                // Render Keywords
                const tagList = document.getElementById('tagList');
                tagList.innerHTML = data.keywords.map(k => `
                    <span class="tag">
                        #${k}
                        <button type="button" class="delete-btn" onclick="deleteKeyword('${k}')">×</button>
                    </span>
                `).join('');

                // Render Media
                const mediaList = document.getElementById('mediaList');
                mediaList.innerHTML = data.media.map(m => `
                    <span class="media-badge">
                        ${m.name} (${m.query})
                        <button type="button" class="delete-btn" onclick="deleteMedia('${m.name}')">×</button>
                    </span>
                `).join('');
            }

            async function addKeyword() {
                const input = document.getElementById('keywordInput');
                if (!input.value.trim()) return;
                await fetch('/keywords', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ keyword: input.value.trim() })
                });
                input.value = '';
                fetchConfig();
                loadNews();
            }

            async function deleteKeyword(keyword) {
                await fetch(`/keywords/${encodeURIComponent(keyword)}`, { method: 'DELETE' });
                fetchConfig();
                loadNews();
            }

            async function addMedia() {
                const nameInput = document.getElementById('mediaNameInput');
                const queryInput = document.getElementById('mediaQueryInput');
                if (!nameInput.value.trim() || !queryInput.value.trim()) {
                    alert('Please enter both the media name and search query.');
                    return;
                }
                await fetch('/media', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name: nameInput.value.trim(), query: queryInput.value.trim() })
                });
                nameInput.value = '';
                queryInput.value = '';
                fetchConfig();
                loadNews();
            }

            async function deleteMedia(name) {
                await fetch(`/media/${encodeURIComponent(name)}`, { method: 'DELETE' });
                fetchConfig();
                loadNews();
            }

            async function loadNews() {
                const container = document.getElementById('newsContainer');
                container.innerHTML = 'Collecting latest news matching your selected media and keywords...';
                const res = await fetch('/news');
                const data = await res.json();
                
                if (data.news.length === 0) {
                    container.innerHTML = '<p>No latest news found matching the registered criteria.</p>';
                    return;
                }

                container.innerHTML = data.news.map(item => `
                    <div class="news-card">
                        <h3><a href="${item.link}" target="_blank">${item.title}</a></h3>
                        <p>${item.summary}</p>
                        <div class="meta">
                            <span class="source-badge">${item.source}</span> 
                            Keyword: <b>#${item.matched_keyword}</b>
                        </div>
                    </div>
                `).join('');
            }

            fetchConfig();
            loadNews();
        </script>
    </body>
    </html>
    """

@app.get("/config")
def get_config():
    return {"keywords": keywords_db, "media": media_db}

@app.post("/keywords")
def add_keyword(req: KeywordRequest):
    if req.keyword not in keywords_db:
        keywords_db.append(req.keyword)
    return {"keywords": keywords_db}

@app.delete("/keywords/{keyword}")
def delete_keyword(keyword: str):
    if keyword in keywords_db:
        keywords_db.remove(keyword)
    return {"keywords": keywords_db}

@app.post("/media")
def add_media(req: MediaRequest):
    # Check for duplicates before adding
    if not any(m['name'] == req.name for m in media_db):
        media_db.append({"name": req.name, "query": req.query})
    return {"media": media_db}

@app.delete("/media/{name}")
def delete_media(name: str):
    global media_db
    media_db = [m for m in media_db if m['name'] != name]
    return {"media": media_db}

@app.get("/news")
def get_filtered_news():
    collected_news = []
    seen_links = set()

    for kw in keywords_db:
        for media in media_db:
            # Combine keyword and user-registered media (site query, etc.) to query Google News RSS
            combined_query = f"{kw} {media['query']}"
            encoded_query = urllib.parse.quote(combined_query)
            rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en&gl=US&ceid=US:en"
            
            try:
                feed = feedparser.parse(rss_url)
                
                for entry in feed.entries[:5]: # Review top 5 latest articles per media/keyword combination
                    link = entry.link
                    if link in seen_links:
                        continue
                    
                    title = entry.title
                    summary = getattr(entry, 'summary', '')
                    
                    source = media['name'] # Set display source to registered media name
                    if '-' in title:
                        parts = title.rsplit('-', 1)
                        # Clean up if the original title includes the media name
                        title = parts[0].strip()

                    seen_links.add(link)
                    collected_news.append({
                        "title": title,
                        "link": link,
                        "summary": summary[:150] + "..." if len(summary) > 150 else summary,
                        "source": source,
                        "matched_keyword": kw
                    })
            except Exception as e:
                print(f"Error parsing RSS for {combined_query}: {e}")

    return {"news": collected_news[:40]}
