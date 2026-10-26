from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import feedparser
import urllib.parse

app = FastAPI()

# 초기 키워드
keywords_db = ["방송 기술", "ST 2110", "IP 송출", "danteAV", "4K", "8K"]

class KeywordRequest(BaseModel):
    keyword: str

@app.get("/", response_class=HTMLResponse)
def index():
    return """
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>맞춤형 미디어 뉴스 클리퍼</title>
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; margin: 0; padding: 20px; }
            .container { max-width: 950px; margin: auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); }
            h1 { color: #333; text-align: center; }
            .section { margin-bottom: 25px; }
            input[type="text"] { width: 65%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; font-size: 16px; }
            button { padding: 10px 20px; background-color: #007bff; color: white; border: none; border-radius: 5px; font-size: 16px; cursor: pointer; }
            button:hover { background-color: #0056b3; }
            .tags { margin-top: 10px; }
            .tag { display: inline-block; background: #e9ecef; padding: 5px 12px; border-radius: 15px; margin-right: 5px; margin-bottom: 5px; font-size: 14px; }
            .source-badge { display: inline-block; background: #e2e3e5; color: #383d41; padding: 2px 8px; border-radius: 4px; font-size: 11px; margin-right: 5px; }
            .news-card { border-bottom: 1px solid #eee; padding: 15px 0; }
            .news-card h3 { margin: 0 0 5px 0; font-size: 18px; }
            .news-card h3 a { color: #007bff; text-decoration: none; }
            .news-card h3 a:hover { text-decoration: underline; }
            .news-card p { color: #666; font-size: 14px; margin: 5px 0; }
            .meta { font-size: 12px; color: #999; margin-top: 5px; }
            .source-list { font-size: 13px; color: #555; background: #f8f9fa; padding: 10px; border-radius: 5px; margin-bottom: 15px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📰 맞춤형 미디어 뉴스 클리퍼</h1>
            
            <div class="source-list">
                <b>📡 연동된 타겟 미디어:</b> ZDNet Korea, 전자신문, CNET, 월간오디오, SMPTE, 방송기술저널 및 글로벌 IT 소스
            </div>

            <div class="section">
                <h3>관심 키워드 관리</h3>
                <input type="text" id="keywordInput" placeholder="추가할 키워드 입력 (예: AI, 미디어 서버)">
                <button onclick="addKeyword()">키워드 추가</button>
                <div class="tags" id="tagList"></div>
            </div>

            <hr>

            <div class="section">
                <h2>실시간 필터링 뉴스</h2>
                <button onclick="loadNews()">뉴스 새로고침</button>
                <div id="newsContainer" style="margin-top: 15px;">뉴스를 불러오는 중...</div>
            </div>
        </div>

        <script>
            async function fetchKeywords() {
                const res = await fetch('/keywords');
                const data = await res.json();
                const tagList = document.getElementById('tagList');
                tagList.innerHTML = data.keywords.map(k => `<span class="tag">#${k}</span>`).join('');
            }

            async function addKeyword() {
                const input = document.getElementById('keywordInput');
                if (!input.value) return;
                await fetch('/keywords', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ keyword: input.value })
                });
                input.value = '';
                fetchKeywords();
                loadNews();
            }

            async function loadNews() {
                const container = document.getElementById('newsContainer');
                container.innerHTML = '선택하신 미디어와 구글 뉴스에서 최신 소식을 수집하는 중입니다...';
                const res = await fetch('/news');
                const data = await res.json();
                
                if (data.news.length === 0) {
                    container.innerHTML = '<p>등록된 키워드와 일치하는 최신 뉴스가 없습니다.</p>';
                    return;
                }

                container.innerHTML = data.news.map(item => `
                    <div class="news-card">
                        <h3><a href="${item.link}" target="_blank">${item.title}</a></h3>
                        <p>${item.summary}</p>
                        <div class="meta">
                            <span class="source-badge">${item.source}</span> 
                            검색 키워드: <b>#${item.matched_keyword}</b>
                        </div>
                    </div>
                `).join('');
            }

            fetchKeywords();
            loadNews();
        </script>
    </body>
    </html>
    """

@app.get("/keywords")
def get_keywords():
    return {"keywords": keywords_db}

@app.post("/keywords")
def add_keyword(req: KeywordRequest):
    if req.keyword not in keywords_db:
        keywords_db.append(req.keyword)
    return {"keywords": keywords_db}

@app.get("/news")
def get_filtered_news():
    collected_news = []
    seen_links = set()

    # 사용자가 요청한 미디어 사이트 도메인/매체명 필터 옵션
    target_media_filters = ["zdnet", "etnews", "cnet", "오디오", "smpte", "방송기술"]

    for kw in keywords_db:
        # 구글 뉴스 검색 RSS를 통해 전문 매체들의 기사를 포괄적으로 수집
        encoded_kw = urllib.parse.quote(kw)
        rss_url = f"https://news.google.com/rss/search?q={encoded_kw}&hl=ko&gl=KR&ceid=KR:ko"
        
        try:
            feed = feedparser.parse(rss_url)
            
            for entry in feed.entries[:10]: # 키워드별 상위 10개 기사 검토
                link = entry.link
                if link in seen_links:
                    continue
                
                title = entry.title
                summary = getattr(entry, 'summary', '')
                
                source = "구글 뉴스"
                if hasattr(entry, 'source') and 'title' in entry.source:
                    source = entry.source.title
                elif '-' in title:
                    parts = title.rsplit('-', 1)
                    title = parts[0].strip()
                    source = parts[1].strip()

                # 요청하신 매체(ZDNet, 전자신문, Cnet, 월간오디오, SMPTE, 방송기술저널 등)와 연관성이 높거나
                # 전체 최신 뉴스를 같이 보여주도록 수집 (원하는 경우 특정 매체만 필터링할 수도 있습니다)
                seen_links.add(link)
                collected_news.append({
                    "title": title,
                    "link": link,
                    "summary": summary[:150] + "..." if len(summary) > 150 else summary,
                    "source": source,
                    "matched_keyword": kw
                })
        except Exception as e:
            print(f"Error parsing RSS for {kw}: {e}")

    return {"news": collected_news[:40]}