#!/usr/bin/env python3
"""
AI & Disability Daily Digest - Enhanced Version
Search window: 30 Days | Sources: Google News, Reddit, arXiv
"""

import os
import feedparser
import requests
from datetime import datetime, timedelta
import google.generativeai as genai
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import re

# ====== Configuration ======
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
EMAIL_FROM = os.environ.get('EMAIL_FROM', '')
EMAIL_TO = os.environ.get('EMAIL_TO', '')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD', '') # Must be a 16-digit App Password

# RSS Sources (Expanded to Micro-Niches and Reddit)
RSS_SOURCES = [
    # Google News - AI + Specific Disability Areas (30 day window)
    {'name': 'Google News - AI & Disability', 'url': 'https://news.google.com/rss/search?q=%22artificial+intelligence%22+disability+when:30d&hl=en-US&gl=US&ceid=US:en'},
    {'name': 'Google News - AI & Accessibility', 'url': 'https://news.google.com/rss/search?q=AI+%22accessibility%22+OR+a11y+when:30d&hl=en-US&gl=US&ceid=US:en'},
    {'name': 'Google News - AI Vision/Blind', 'url': 'https://news.google.com/rss/search?q=AI+blind+OR+%22visually+impaired%22+when:30d&hl=en-US&gl=US&ceid=US:en'},
    {'name': 'Google News - AI Hearing/Deaf', 'url': 'https://news.google.com/rss/search?q=AI+deaf+OR+%22hearing+loss%22+when:30d&hl=en-US&gl=US&ceid=US:en'},
    {'name': 'Google News - AI Neurodiversity', 'url': 'https://news.google.com/rss/search?q=AI+autism+OR+dyslexia+OR+cognitive+when:30d&hl=en-US&gl=US&ceid=US:en'},
    
    # Reddit Communities (Free RSS)
    {'name': 'Reddit - Accessibility', 'url': 'https://www.reddit.com/r/accessibility/search.rss?q=AI&restrict_sr=on&sort=relevance&t=month'},
    {'name': 'Reddit - Disability', 'url': 'https://www.reddit.com/r/disability/search.rss?q=AI&restrict_sr=on&sort=relevance&t=month'},
    {'name': 'Reddit - Blind', 'url': 'https://www.reddit.com/r/blind/search.rss?q=AI&restrict_sr=on&sort=relevance&t=month'},
    
    # Research
    {'name': 'arXiv - AI Research', 'url': 'http://export.arxiv.org/rss/cs.AI'},
]

def fetch_articles():
    """Fetch articles from all RSS sources (Last 30 days)"""
    all_articles = []
    seen_links = set()
    today = datetime.now()
    # Increase window to 30 days to ensure a larger pool
    start_date = today - timedelta(days=30)
    
    print(f"📰 Starting search... (Window: {start_date.strftime('%Y-%m-%d')} to Today)")
    
    for source in RSS_SOURCES:
        try:
            print(f"  - Fetching: {source['name']}")
            # Adding a user-agent to prevent Reddit from blocking the script
            feed = feedparser.parse(source['url'], agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AI-Digest-Bot/1.0')
            
            for entry in feed.entries[:50]: # Check up to 50 articles per source
                link = entry.get('link', '')
                if link in seen_links: continue
                
                pub_date = None
                if hasattr(entry, 'published_parsed'):
                    pub_date = datetime(*entry.published_parsed[:6])
                
                # Filter by date
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
            
    print(f"✅ Total articles collected: {len(all_articles)}")
    return all_articles

def filter_relevant_articles(articles):
    """Filter articles that MUST contain one keyword from BOTH lists"""
    # Expanded keywords to catch more niche topics
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
        
        has_ai = any(f" {kw} " in f" {content} " or kw in article['title'].lower() for kw in ai_keywords)
        has_disability = any(f" {kw} " in f" {content} " or kw in article['title'].lower() for kw in disability_keywords)
        
        if has_ai and has_disability:
            relevant.append(article)
    
    print(f"🔍 Articles matching both AI & Disability filters: {len(relevant)}")
    return relevant

def generate_digest_with_gemini(articles):
    """Generate digest using Gemini API"""
    if not articles: return None
    
    print("🤖 AI is synthesizing the digest...")
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-pro')
    
    articles_text = "\n\n".join([
        f"Source: {a['source']}\nTitle: {a['title']}\nLink: {a['link']}\nSummary: {a['summary']}"
        for a in articles[:20] # Limit to top 20 for AI processing
    ])
    
    prompt = f"""
    You are an expert editor in AI and Assistive Technology. 
    Create a professional daily digest from these articles:
    {articles_text}

    Format requirements:
    1. A bold Header: # 🤖 AI & Disability Daily Digest
    2. Date: {datetime.now().strftime('%B %d, %Y')}
    3. section: ## 🔥 Top Breakthroughs (Detailed summary of the 2 best articles)
    4. section: ## 📰 Global News (Bulleted list of other articles with links and 1-sentence summaries)
    5. section: ## 💡 Future Implications (Your analysis of how this tech changes lives)
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"❌ Gemini Error: {str(e)}")
        return None

def create_html_email(content):
    """Converts Markdown to a pretty HTML Email"""
    # Basic Markdown to HTML conversion
    html = content
    html = html.replace('# ', '<h1>').replace('\n## ', '</h1><br><h2>').replace('\n### ', '</h2><h3>')
    html = re.sub(r'\[([^\]]+)\]\(([^\)]+)\)', r'<a href="\2">\1</a>', html)
    html = re.sub(r'\*\*([^\*]+)\*\*', r'<strong>\1</strong>', html)
    html = html.replace('\n- ', '<br>• ')
    
    return f"""
    <html>
    <body style="font-family: sans-serif; line-height: 1.6; color: #333; max-width: 700px; margin: auto; padding: 20px;">
        <div style="background-color: #f8f9fa; padding: 30px; border-radius: 15px; border-top: 5px solid #4285f4;">
            {html}
            <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
            <p style="font-size: 12px; color: #777; text-align: center;">
                Generated by Gemini AI | Sources: Google News, Reddit, arXiv | Filter: AI + Disability (30 Days)
            </p>
        </div>
    </body>
    </html>
    """

def send_email(subject, html_content):
    """Send the email via Gmail SMTP"""
    print(f"📧 Sending email to {EMAIL_TO}...")
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = EMAIL_FROM
    msg['To'] = EMAIL_TO
    msg.attach(MIMEText(html_content, 'html'))
    
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL_FROM, EMAIL_PASSWORD)
            server.send_message(msg)
        print("✨ Success! Email sent.")
        return True
    except Exception as e:
        print(f"❌ SMTP Error: {str(e)}")
        return False

def main():
    print("\n" + "="*50)
    print("🚀 STARTING AI & DISABILITY DIGEST PROCESS")
    print("="*50)
    
    raw_articles = fetch_articles()
    if not raw_articles:
        print("❌ No articles found in feeds.")
        return
        
    filtered = filter_relevant_articles(raw_articles)
    if not filtered:
        print("⚠️ No articles matched the 'AI + Disability' criteria today.")
        return
        
    digest_text = generate_digest_with_gemini(filtered)
    if not digest_text: return
    
    html_email = create_html_email(digest_text)
    subject = f"🤖 AI & Disability Digest: {len(filtered)} New Insights"
    send_email(subject, html_email)

if __name__ == "__main__":
    main()
