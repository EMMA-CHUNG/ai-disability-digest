#!/usr/bin/env python3
"""
AI & Disability Daily Digest - ULTIMATE STABLE VERSION
Includes AI Fallback: If Gemini fails, you still get the news list.
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

# ====== 1. Configuration ======
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
EMAIL_FROM = os.environ.get('EMAIL_FROM', '')
EMAIL_TO = os.environ.get('EMAIL_TO', '')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD', '')

RSS_SOURCES = [
    {'name': 'Google News - AI & Disability', 'url': 'https://news.google.com/rss/search?q=%22artificial+intelligence%22+disability+when:30d&hl=en-US&gl=US&ceid=US:en'},
    {'name': 'Google News - AI & Accessibility', 'url': 'https://news.google.com/rss/search?q=AI+%22accessibility%22+OR+a11y+when:30d&hl=en-US&gl=US&ceid=US:en'},
    {'name': 'Google News - AI Vision/Blind', 'url': 'https://news.google.com/rss/search?q=AI+blind+OR+%22visually+impaired%22+when:30d&hl=en-US&gl=US&ceid=US:en'},
    {'name': 'Google News - AI Hearing/Deaf', 'url': 'https://news.google.com/rss/search?q=AI+deaf+OR+%22hearing+loss%22+when:30d&hl=en-US&gl=US&ceid=US:en'},
    {'name': 'Reddit - Accessibility', 'url': 'https://www.reddit.com/r/accessibility/search.rss?q=AI&restrict_sr=on&sort=relevance&t=month'},
    {'name': 'Reddit - Disability', 'url': 'https://www.reddit.com/r/disability/search.rss?q=AI&restrict_sr=on&sort=relevance&t=month'},
]

def fetch_articles():
    all_articles = []
    seen_links = set()
    start_date = datetime.now() - timedelta(days=30)
    print(f"🚀 SEARCHING (Last 30 Days)")
    for source in RSS_SOURCES:
        try:
            feed = feedparser.parse(source['url'], agent='AI-Digest-Bot/1.0')
            for entry in feed.entries[:30]:
                link = entry.get('link', '')
                if link in seen_links: continue
                all_articles.append({'title': entry.get('title', 'No Title'), 'link': link, 'summary': entry.get('summary', '')[:400], 'source': source['name']})
                seen_links.add(link)
        except Exception as e: print(f"  ⚠️ Error: {str(e)}")
    return all_articles

def filter_relevant_articles(articles):
    disability_keywords = ['disability', 'accessible', 'accessibility', 'a11y', 'assistive', 'blind', 'deaf', 'autism', 'mobility']
    ai_keywords = ['ai', 'artificial intelligence', 'machine learning', 'generative', 'chatgpt', 'gemini']
    relevant = []
    for article in articles:
        content = (article['title'] + ' ' + article['summary']).lower()
        if any(kw in content for kw in ai_keywords) and any(kw in content for kw in disability_keywords):
            relevant.append(article)
    print(f"🔍 Found {len(relevant)} matches.")
    return relevant

def generate_digest(articles):
    """Try Gemini; if it fails, return a basic list to ensure email sends."""
    if not articles: return None
    
    try:
        print("🤖 Attempting AI Synthesis (Gemini 1.5 Flash)...")
        genai.configure(api_key=GEMINI_API_KEY)
        # Using the specific "-latest" suffix often fixes 404 issues
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        
        text = "\n\n".join([f"Title: {a['title']}\nLink: {a['link']}" for a in articles[:10]])
        prompt = f"Summarize these AI & Disability news stories into a professional digest:\n\n{text}"
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"⚠️ AI Failed ({str(e)}). Switching to Simple List Mode...")
        # FALLBACK: Create a simple list if AI is broken
        fallback = "<h1>🤖 AI & Disability News List</h1><p>(AI Synthesis failed, here are the raw links):</p><ul>"
        for a in articles[:15]:
            fallback += f"<li><strong>{a['title']}</strong><br><a href='{a['link']}'>Read Article</a> (Source: {a['source']})</li><br>"
        fallback += "</ul>"
        return fallback

def send_email(subject, content):
    print(f"📧 Sending to {EMAIL_TO}...")
    msg = MIMEMultipart('alternative')
    msg['Subject'], msg['From'], msg['To'] = subject, EMAIL_FROM, EMAIL_TO
    
    # If the content already looks like HTML (from the fallback), use it. 
    # Otherwise, do a quick markdown conversion.
    if "<ul>" in content:
        html_body = content
    else:
        html_body = f"<html><body>{content.replace('# ', '<h1>').replace('**', '<strong>')}</body></html>"
        html_body = re.sub(r'\[([^\]]+)\]\(([^\)]+)\)', r'<a href="\2">\1</a>', html_body)

    msg.attach(MIMEText(html_body, 'html'))
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL_FROM, EMAIL_PASSWORD)
            server.send_message(msg)
        print("✨ Success! Check your inbox.")
    except Exception as e:
        print(f"❌ Email Error: {str(e)}")

def main():
    print("="*30)
    articles = fetch_articles()
    relevant = filter_relevant_articles(articles)
    
    if not relevant:
        print("⚠️ No matches found. Sending status email...")
        send_email("🤖 AI Digest: No New matches Today", "The script ran successfully but found 0 matching articles in the last 30 days.")
        return

    content = generate_digest(relevant)
    send_email(f"🤖 AI & Disability Digest: {len(relevant)} Stories", content)

if __name__ == "__main__":
    main()
