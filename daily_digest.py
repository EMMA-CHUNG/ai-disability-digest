#!/usr/bin/env python3
"""
AI & Disability Daily Digest
Automatically search, summarize and send daily digest emails
Using Google Gemini API (Free)
"""

import os
import feedparser
import requests
from datetime import datetime, timedelta
import google.generativeai as genai
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json

# ====== Configuration ======
# These will be read from GitHub Secrets or environment variables
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
EMAIL_FROM = os.environ.get('EMAIL_FROM', '')
EMAIL_TO = os.environ.get('EMAIL_TO', '')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD', '')  # Gmail App Password

# RSS Source List
RSS_SOURCES = [
    # AI News
    {
        'url': 'https://news.google.com/rss/search?q=artificial+intelligence+disability&hl=en-US&gl=US&ceid=US:en',
        'name': 'Google News - AI & Disability'
    },
    {
        'url': 'https://news.google.com/rss/search?q=AI+assistive+technology&hl=en-US&gl=US&ceid=US:en',
        'name': 'Google News - AI Assistive Tech'
    },
    {
        'url': 'https://news.google.com/rss/search?q=machine+learning+accessibility&hl=en-US&gl=US&ceid=US:en',
        'name': 'Google News - ML Accessibility'
    },
    # arXiv AI papers (optional)
    {
        'url': 'http://export.arxiv.org/rss/cs.AI',
        'name': 'arXiv - Artificial Intelligence'
    },
]

# ====== Core Functions ======

def fetch_articles():
    """Fetch articles from all RSS sources"""
    all_articles = []
    today = datetime.now()
    yesterday = today - timedelta(days=1)
    
    print(f"📰 Fetching articles... {today.strftime('%Y-%m-%d')}")
    
    for source in RSS_SOURCES:
        try:
            print(f"  - Fetching: {source['name']}")
            feed = feedparser.parse(source['url'])
            
            for entry in feed.entries[:10]:  # Max 10 articles per source
                # Check if article is recent
                pub_date = None
                if hasattr(entry, 'published_parsed'):
                    pub_date = datetime(*entry.published_parsed[:6])
                
                # Only get articles from last 2 days
                if pub_date and pub_date < yesterday:
                    continue
                
                article = {
                    'title': entry.get('title', 'No Title'),
                    'link': entry.get('link', ''),
                    'summary': entry.get('summary', '')[:300],  # Limit length
                    'source': source['name'],
                    'published': pub_date.strftime('%Y-%m-%d') if pub_date else 'Recent'
                }
                all_articles.append(article)
                
        except Exception as e:
            print(f"  ⚠️  Error: {source['name']} - {str(e)}")
            continue
    
    print(f"✅ Fetched {len(all_articles)} articles total")
    return all_articles


def filter_relevant_articles(articles):
    """Filter relevant articles - ensure they contain AI and Disability keywords"""
    keywords = [
        'disability', 'disabilities', 'accessible', 'accessibility',
        'assistive', 'inclusive', 'inclusion', 'impairment',
        'blind', 'deaf', 'wheelchair', 'autism', 'cognitive'
    ]
    
    ai_keywords = ['ai', 'artificial intelligence', 'machine learning', 'deep learning', 'neural']
    
    relevant = []
    for article in articles:
        text = (article['title'] + ' ' + article['summary']).lower()
        
        # Must contain both AI and Disability keywords
        has_ai = any(kw in text for kw in ai_keywords)
        has_disability = any(kw in text for kw in keywords)
        
        if has_ai and has_disability:
            relevant.append(article)
    
    print(f"🔍 After filtering: {len(relevant)} relevant articles")
    return relevant


def generate_digest_with_gemini(articles):
    """Generate digest using Gemini API"""
    if not articles:
        return None
    
    print("🤖 Generating digest with Gemini...")
    
    # Configure Gemini API
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-pro')
    
    # Prepare article list
    articles_text = "\n\n".join([
        f"Article {i+1}:\nTitle: {article['title']}\nLink: {article['link']}\nSummary: {article['summary']}\nSource: {article['source']}"
        for i, article in enumerate(articles[:15])  # Max 15 articles
    ])
    
    # Prompt
    prompt = f"""
You are a professional tech news editor specializing in AI and disability topics.

Here are today's collected articles:

{articles_text}

Please compile these articles into a professional daily digest with this format:

# 🤖 AI & Disability Daily Digest
📅 {datetime.now().strftime('%B %d, %Y')}

## 🔥 Today's Highlights
[Select the 1-2 most important articles and write detailed 100-150 word summaries explaining why they matter]

## 📰 Important News (ranked by importance)
[List other important articles, each including:]
- **[Title]** ([Original Link](link))
  - 📝 [50-80 word summary]
  - 🔑 Keywords: [3-5 relevant keywords]

## 💡 Tech Trends Analysis
[From today's articles, summarize 2-3 technical trends or observations]

## 📊 Today's Statistics
- Articles analyzed: {len(articles)}
- Main areas: [list main application areas]
- Focus topics: [list trending keywords]

---
💌 This is an automatically generated digest. Sources: Google News, arXiv, etc.

Please write in professional but accessible English and ensure all links are correct.
"""
    
    try:
        response = model.generate_content(prompt)
        digest = response.text
        print("✅ Digest generated successfully!")
        return digest
        
    except Exception as e:
        print(f"❌ Gemini API error: {str(e)}")
        return None


def create_html_email(digest_content):
    """Convert Markdown digest to beautiful HTML email"""
    
    # Simple Markdown to HTML conversion
    html_content = digest_content
    
    # Convert headers
    html_content = html_content.replace('# ', '<h1>').replace('\n## ', '</h1>\n<h2>').replace('\n### ', '</h2>\n<h3>')
    
    # Convert links [text](url)
    import re
    html_content = re.sub(r'\[([^\]]+)\]\(([^\)]+)\)', r'<a href="\2">\1</a>', html_content)
    
    # Convert bold
    html_content = re.sub(r'\*\*([^\*]+)\*\*', r'<strong>\1</strong>', html_content)
    
    # Convert lists
    html_content = html_content.replace('\n- ', '<br>• ')
    
    # Add styling
    styled_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica Neue', sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }}
        .container {{
            background: white;
            border-radius: 16px;
            padding: 40px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #667eea;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
            font-size: 28px;
        }}
        h2 {{
            color: #764ba2;
            margin-top: 30px;
            font-size: 22px;
        }}
        h3 {{
            color: #555;
            font-size: 18px;
        }}
        a {{
            color: #667eea;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #eee;
            color: #999;
            font-size: 14px;
            text-align: center;
        }}
        .emoji {{
            font-size: 1.2em;
        }}
    </style>
</head>
<body>
    <div class="container">
        {html_content}
        <div class="footer">
            <p>📧 This email was automatically generated and sent</p>
            <p>🤖 Compiled by Google Gemini AI | 🔄 Updated daily</p>
            <p>💡 Sources: Google News, arXiv, and professional websites</p>
        </div>
    </div>
</body>
</html>
"""
    return styled_html


def send_email(subject, html_content):
    """Send HTML email"""
    print("📧 Preparing to send email...")
    
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = EMAIL_FROM
    msg['To'] = EMAIL_TO
    
    # Add HTML content
    html_part = MIMEText(html_content, 'html', 'utf-8')
    msg.attach(html_part)
    
    try:
        # Use Gmail SMTP
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL_FROM, EMAIL_PASSWORD)
            server.send_message(msg)
        
        print("✅ Email sent successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Email sending failed: {str(e)}")
        return False


def main():
    """Main program"""
    print("\n" + "="*60)
    print("🚀 AI & Disability Daily Digest Generator")
    print("="*60 + "\n")
    
    # 1. Fetch articles
    articles = fetch_articles()
    
    if not articles:
        print("⚠️  No articles found, exiting")
        return
    
    # 2. Filter relevant articles
    relevant_articles = filter_relevant_articles(articles)
    
    if not relevant_articles:
        print("⚠️  No relevant articles found, exiting")
        return
    
    # 3. Generate digest
    digest = generate_digest_with_gemini(relevant_articles)
    
    if not digest:
        print("❌ Digest generation failed")
        return
    
    # 4. Convert to HTML
    html_content = create_html_email(digest)
    
    # 5. Send email
    today = datetime.now().strftime('%Y-%m-%d')
    subject = f"🤖 AI & Disability Daily Digest - {today}"
    
    success = send_email(subject, html_content)
    
    if success:
        print("\n" + "="*60)
        print("✨ Complete! Today's digest has been sent to your inbox")
        print("="*60 + "\n")
    else:
        print("\n❌ Sending failed, please check configuration")


if __name__ == "__main__":
    main()
