#!/usr/bin/env python3
"""
AI & Disability Daily Digest - Version 2.0 (Official SDK)
Search window: 30 Days | Sources: Google News, Reddit, arXiv
Model: Gemini 1.5 Flash
"""

import os
import feedparser
import requests
from datetime import datetime, timedelta
from google import genai  # Brand new SDK
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import re

# ====== 1. Configuration ======
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
EMAIL_FROM = os.environ.get('EMAIL_FROM', '')
EMAIL_TO = os.environ.get('EMAIL_TO', '')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD', '') # Must be a 16-digit App Password

# Expanded RSS Sources
RSS_SOURCES = [
    # Google News Niche Searches (30 day window)
    {'name': 'Google News - AI & Disability', 'url': 'https://news.google.com/rss/search?q=%22artificial+intelligence%22+disability+when:30d&hl=en-US&gl=US&ceid=US:en'},
    {'name': 'Google News - AI & Accessibility', 'url': 'https://news.google.com/rss/search?q=AI+%22accessibility%22+OR+a11y+when:30d&hl=en-US&gl=US&ceid=US:en'},
    {'name': 'Google News - AI Vision/Blind', 'url': 'https://news.google.com/rss/search?q=AI+blind+OR+%22visually+impaired%22+when:30d&hl=en-US&gl=US&ceid=US:en'},
    {'name': 'Google News - AI Hearing/Deaf', 'url': 'https://news.google.com/rss/search?q=AI+deaf+OR+%22hearing+loss%22+when:30d&hl=en-US&gl=US&ceid=US:en'},
    {'name': 'Google News - AI Neurodiversity', 'url': 'https://news.google.com/rss/search?q=AI+autism+OR+dyslexia+OR+cognitive+when:30d&hl=en-US&gl=US&ceid=US:en'},
    
    # Reddit Communities (Free RSS - Provides real-world discussion)
    {'name': 'Reddit - Accessibility', 'url': 'https://www.reddit.com/r/accessibility/search.rss?q=AI&restrict_sr=on&sort=relevance&t=month'},
    {'name': 'Reddit - Disability', 'url': 'https://www.reddit.com/r/disability/search.rss?q=AI&restrict_sr=on&sort=relevance&t=month'},
    {'name': 'Reddit - Blind', 'url': 'https://www.reddit.com/r/blind/search.rss?q=AI&restrict_sr=on&sort=relevance&t=month'},
    
    # Academic/Research
    {'name': 'arXiv - AI Research', 'url': 'http://export.arxiv.org/rss/cs.AI'},
]

# ====== 2. Fetching Logic ======
def fetch_articles():
    """Fetch articles from all RSS sources (Last 30 days)"""
    all_articles = []
    seen_links = set()
    today = datetime.now()
    start_date = today - timedelta(days=30)
    
    print(f"🚀 STARTING SEARCH (Window: {start_date.strftime('%Y-%m-%d')} to Today)")
    
    for source in RSS_SOURCES:
        try:
            print(f"  - Fetching: {source['name']}")
            # Reddit requires a User-Agent or it blocks the request
            feed = feedparser.parse(source['url'], agent='AI-Disability-Digest-Bot/1.0')
            
            for entry in feed.entries[:40]: # Check top 40 items per source
                link = entry.get('link', '')
                if link in seen_links: continue
                
                pub_date = None
                if hasattr(entry, 'published_parsed'):
                    pub_date = datetime(*entry.published_parsed[:6])
                
                # Verify the article is within the 30-day window
                if pub_date and pub_date < start_date:
                    continue
                
                article = {
                    'title': entry.get('title', 'No Title'),
                    'link': link,
                    'summary': entry.get('summary', '')[:500],
                    'source': source['name'],
                    'published': pub_date.strftime('%Y-%m-%d') if pub_date else 'Recent'
                }
                all_articles.append(article)
                seen_links.add(link)
                
        except Exception as e:
            print(f"  ⚠️ Error in {source['name']}: {str(e)}")
            
    print(f"✅ Total articles collected in pool: {len(all_articles)}")
    return all_articles

# ====== 3. Filtering Logic ======
def filter_relevant_articles(articles):
    """Ensure articles mention at least one AI term AND one Disability term"""
    disability_keywords = [
        'disability', 'disabilities', 'accessible', 'accessibility', 'a11y',
        'assistive', 'inclusive', 'inclusion', 'impairment', 'blind', 'blindness',
        'deaf', 'deafness', 'hearing loss', 'visually impaired', 'wheelchair', 
        'autism', 'autistic', 'neurodiverse', 'neurodiversity', 'cognitive', 
        'dyslexia', 'mobility', 'paralysis', 'prosthetic', 'special needs'
    ]
    
    ai_keywords = [
        'ai', 'artificial intelligence', 'machine learning', 'deep learning', 
        'neural', 'generative ai', 'genai', 'chatgpt', 'llm', 'large language model',
        'gemini', 'robotics', 'automation', 'computer vision', 'speech-to-text',
        'text-to-speech', 'nlp', 'natural language processing'
    ]
    
    relevant = []
    for article in articles:
        content = (article['title'] + ' ' + article['summary']).lower()
        
        # Check if title or summary contains keywords from both groups
        has_ai = any(f" {kw} " in f" {content} " or kw in article['title'].lower() for kw in ai_keywords)
        has_disability = any(f" {kw} " in f" {content} " or kw in article['title'].lower() for kw in disability_keywords)
        
        if has_ai and has_disability:
            relevant.append(article)
    
    print(f"🔍 Matches after strict filtering: {len(relevant)}")
    return relevant

# ====== 4. AI Synthesis ======
def generate_digest_with_gemini(articles):
    """Generate professional summary using Gemini 1.5 Flash"""
    if not articles: return None
    
    print("🤖 Synthesizing digest with Gemini 1.5 Flash...")
    
    # Initialize the New SDK Client
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    # Prepare text for AI (Limit to top 15 most recent/relevant)
    articles_text = "\n\n".join([
        f"Source: {a['source']}\nTitle: {a['title']}\nLink: {a['link']}\nSummary: {a['summary']}"
        for a in articles[:15] 
    ])
    
    prompt = f"""
    You are an expert editor specializing in AI and Assistive Technology.
    Please write a professional, high-quality daily digest based on these articles:
    
    {articles_text}

    STRUCTURE:
    1. Header: # 🤖 AI & Disability Daily Digest
    2. Today's Date: {datetime.now().strftime('%B %d, %Y')}
    3. Section: ## 🔥 Featured Breakthroughs (Choose the 2 most impactful stories and write a detailed paragraph for each)
    4. Section: ## 📰 Global News (List the other stories with [Link] and a 1-sentence summary)
    5. Section: ## 💡 The Big Picture (Write 2-3 sentences on the overall trend today)
    
    Style: Professional, encouraging, and technically accurate.
    """
    
    try:
        # Use new SDK syntax
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt
        )
        return response.text
    except Exception as e:
        print(f"❌ Gemini Error: {str(e)}")
        return None

# ====== 5. Emailing ======
def create_html_email(content):
    """Basic Markdown to HTML Converter for Email"""
    html = content
    html = html.replace('# ', '<h1>').replace('\n## ', '</h1><br><h2>').replace('\n### ', '</h2><h3>')
    html = re.sub(r'\[([^\]]+)\]\(([^\)]+)\)', r'<a href="\2">\1</a>', html)
    html = re.sub(r'\*\*([^\*]+)\*\*', r'<strong>\1</strong>', html)
    html = html.replace('\n- ', '<br>• ')
    
    return f"""
    <html>
    <body style="font-family: 'Segoe UI', sans-serif; line-height: 1.6; color: #333; max-width: 700px; margin: auto; padding: 20px;">
        <div style="background-color: #ffffff; padding: 40px; border-radius: 12px; border: 1px solid #eee; box-shadow: 0 4px 10px rgba(0,0,0,0.05);">
            {html}
            <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; font-size: 11px; color: #888; text-align: center;">
                <p>🤖 AI-Generated Daily Digest | Window: 30 Days</p>
                <p>Sources: Google News, Reddit, arXiv</p>
            </div>
        </div>
    </body>
    </html>
    """

def send_email(subject, html_content):
    """Send HTML email via Gmail SMTP"""
    print(f"📧 Sending digest to {EMAIL_TO}...")
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = EMAIL_FROM
    msg['To'] = EMAIL_TO
    msg.attach(MIMEText(html_content, 'html'))
    
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL_FROM, EMAIL_PASSWORD)
            server.send_message(msg)
        print("✨ Success! Email delivered.")
        return True
    except Exception as e:
        print(f"❌ Email Error: {str(e)}")
        return False

# ====== 6. Main Orchestrator ======
def main():
    print("\n" + "="*60)
    print("🚀 AI & DISABILITY DIGEST GENERATOR v2.0")
    print("="*60)
    
    # Step 1: Get Raw Pool
    raw_pool = fetch_articles()
    if not raw_pool:
        print("❌ Search returned 0 results. Check internet or RSS links.")
        return
        
    # Step 2: Apply Filters
    final_list = filter_relevant_articles(raw_pool)
    if not final_list:
        print("⚠️  No articles matched the AI + Disability criteria in the last 30 days.")
        return
        
    # Step 3: AI Summary
    digest_text = generate_digest_with_gemini(final_list)
    if not digest_text: return
    
    # Step 4: Final Email
    html_body = create_html_email(digest_text)
    subject = f"🤖 AI & Disability Digest: {len(final_list)} New Insights"
    send_email(subject, html_body)

if __name__ == "__main__":
    main()
