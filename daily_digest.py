#!/usr/bin/env python3
import os
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import feedparser
import requests
from googleapiclient.discovery import build
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi

NEWS_SOURCES = {
    "BBC": "http://feeds.bbc.co.uk/news/rss.xml",
    "Reuters": "https://feeds.reuters.com/reuters/topNews",
    "AP News": "https://apnews.com/hub/ap-top-news/rss",
    "The Guardian": "https://www.theguardian.com/world/rss",
}
REDDIT_SUBREDDITS = ["news", "worldnews", "technology"]

class DataGatherer:
    def __init__(self, youtube_api_key):
        self.youtube = build('youtube', 'v3', developerKey=youtube_api_key)

    def get_youtube_data(self, channel_ids, max_results=2):
        print("📺 Gathering YouTube Transcripts...")
        yt_data = []
        for channel_id in channel_ids:
            try:
                channel = self.youtube.channels().list(part='contentDetails', id=channel_id).execute()
                if not channel['items']: continue
                uploads_id = channel['items'][0]['contentDetails']['relatedPlaylists']['uploads']
                videos = self.youtube.playlistItems().list(part='snippet', playlistId=uploads_id, maxResults=max_results).execute()
                
                for item in videos.get('items', []):
                    snippet = item['snippet']
                    video_id = snippet['resourceId']['videoId']
                    title = snippet['title']
                    channel_name = snippet['channelTitle']
                    url = f"https://www.youtube.com/watch?v={video_id}"
                    
                    # Try to get transcript
                    transcript_text = "(No transcript available. Use title to infer context.)"
                    try:
                        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                        transcript = transcript_list.find_transcript(['en', 'hi', 'en-US', 'en-GB'])
                        transcript_data = transcript.fetch()
                        # Limit to first 10,000 characters per video to save processing time
                        transcript_text = " ".join([chunk['text'] for chunk in transcript_data])[:10000] 
                    except:
                        pass
                    
                    yt_data.append(f"Video: {title}\nChannel: {channel_name}\nURL: {url}\nTranscript/Context: {transcript_text}\n---")
            except Exception as e:
                print(f"Error fetching channel {channel_id}: {e}")
        return "\n".join(yt_data)

    def get_news_data(self):
        print("📰 Gathering News...")
        news_data = []
        for source, url in NEWS_SOURCES.items():
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:3]:
                    news_data.append(f"Source: {source}\nHeadline: {entry.get('title', '')}\nSummary: {entry.get('summary', '')}\nURL: {entry.get('link', '')}\n---")
            except: pass
        return "\n".join(news_data)

    def get_reddit_data(self):
        print("💬 Gathering Reddit...")
        reddit_data = []
        headers = {'User-Agent': 'DailyDigestBot/1.0'}
        for sub in REDDIT_SUBREDDITS:
            try:
                url = f"https://www.reddit.com/r/{sub}/hot.json?limit=3"
                res = requests.get(url, headers=headers, timeout=10).json()
                for post in res['data']['children']:
                    p = post['data']
                    if not p.get('stickied'):
                        reddit_data.append(f"Subreddit: r/{sub}\nTitle: {p['title']}\nScore: {p['score']}\nURL: https://reddit.com{p['permalink']}\n---")
            except: pass
        return "\n".join(reddit_data)


class AINewsletterEditor:
    def __init__(self, gemini_api_key):
        genai.configure(api_key=gemini_api_key)
        # Upgraded to the new Gemini 3 Flash model!
        self.model = genai.GenerativeModel('gemini-3-flash-preview')
        
    def generate_newsletter(self, youtube_raw, news_raw, reddit_raw):
        print("🧠 Sending everything to Gemini API to write the newsletter...")
        
        date_str = datetime.now().strftime("%A, %B %d, %Y")
        
        master_prompt = f"""
        You are an expert, calming, and objective newsletter editor. Your goal is to keep the reader informed without causing them stress. 
        I am going to provide you with a raw data dump of today's YouTube transcripts from their favorite channels, top RSS news articles, and trending Reddit posts.

        Your task is to write a cohesive, engaging, and highly readable daily digest email. 
        - Cross-reference the information! If a YouTube video talks about a topic that is also in the news, synthesize them into one cohesive summary.
        - Filter out all sponsorship reads, clickbait, sensationalism, and extreme political rhetoric. Focus on factual events.
        - Organize the newsletter logically. You don't have to list every single video or article if they are redundant or spammy. 

        OUTPUT FORMAT:
        You must output ONLY valid, beautifully styled HTML code. Do not use markdown blocks like ```html. 
        Start directly with <html> and end with </html>.
        Use a clean, modern email design with inline CSS. Use Georgia or a similar readable serif font. Make sure links to the original videos/articles are clearly clickable.
        Include a header that says "🧠 Your AI Daily Digest" and today's date: {date_str}.

        RAW DATA DUMP:
        ================
        [YOUTUBE DATA]
        {youtube_raw}

        [NEWS DATA]
        {news_raw}

        [REDDIT DATA]
        {reddit_raw}
        ================
        """
        
        response = self.model.generate_content(master_prompt)
        
        # Clean up the output in case Gemini accidentally includes markdown formatting
        html_output = response.text.strip()
        if html_output.startswith("```html"):
            html_output = html_output[7:]
        if html_output.endswith("```"):
            html_output = html_output[:-3]
            
        return html_output

def send_email(recipient, subject, html_content, sender_email, password):
    print("✉️  Sending the final HTML to your inbox...")
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = recipient
        msg.attach(MIMEText(html_content, 'html'))
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender_email, password)
            server.sendmail(sender_email, recipient, msg.as_string())
        print("✅ Success! Email sent.")
    except Exception as e:
        print(f"❌ Email failed: {e}")

def main():
    youtube_api_key = os.environ['YOUTUBE_API_KEY']
    gemini_api_key = os.environ['GEMINI_API_KEY']
    sender_email = os.environ['SENDER_EMAIL']
    gmail_password = os.environ['GMAIL_PASSWORD']
    recipient_email = os.environ['RECIPIENT_EMAIL']
    youtube_channels = json.loads(os.environ['YOUTUBE_CHANNELS'])

    print(f"🚀 Starting the Editor-in-Chief workflow — {datetime.now()}")

    # 1. Gather all the raw data
    gatherer = DataGatherer(youtube_api_key)
    youtube_text = gatherer.get_youtube_data(youtube_channels)
    news_text = gatherer.get_news_data()
    reddit_text = gatherer.get_reddit_data()

    # 2. Hand it all to Gemini
    editor = AINewsletterEditor(gemini_api_key)
    final_html_email = editor.generate_newsletter(youtube_text, news_text, reddit_text)

    # 3. Send the generated HTML
    subject = f"🧠 AI Daily Digest — {datetime.now().strftime('%B %d, %Y')}"
    send_email(recipient_email, subject, final_html_email, sender_email, gmail_password)

if __name__ == '__main__':
    main()
