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

NEWS_SOURCES = {
    "BBC": "http://feeds.bbc.co.uk/news/rss.xml",
    "Reuters": "https://feeds.reuters.com/reuters/topNews",
    "AP News": "https://apnews.com/hub/ap-top-news/rss",
    "The Guardian": "https://www.theguardian.com/world/rss",
    "Hacker News": "https://news.ycombinator.com/rss",
}

REDDIT_SUBREDDITS = ["news", "worldnews", "technology", "science"]


class YouTubeFetcher:
    def __init__(self, api_key):
        self.youtube = build('youtube', 'v3', developerKey=api_key)

    def get_channel_videos(self, channel_id, max_results=3):
        try:
            channel = self.youtube.channels().list(
                part='contentDetails', id=channel_id
            ).execute()
            if not channel['items']:
                return []
            uploads_id = channel['items'][0]['contentDetails']['relatedPlaylists']['uploads']
            videos = self.youtube.playlistItems().list(
                part='snippet', playlistId=uploads_id, maxResults=max_results
            ).execute()
            results = []
            for item in videos.get('items', []):
                snippet = item['snippet']
                pub_date = snippet['publishedAt'][:10]
                # Only include videos published today or yesterday
                results.append({
                    'title': snippet['title'],
                    'channel': snippet['channelTitle'],
                    'url': f"https://www.youtube.com/watch?v={snippet['resourceId']['videoId']}",
                    'published': pub_date,
                    'description': snippet['description'][:300]
                })
            return results
        except Exception as e:
            print(f"Error fetching channel {channel_id}: {e}")
            return []


class NewsFetcher:
    @staticmethod
    def get_rss_news(sources, max_items=5):
        all_news = []
        for source_name, feed_url in sources.items():
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:max_items]:
                    all_news.append({
                        'source': source_name,
                        'title': entry.get('title', 'No title'),
                        'url': entry.get('link', '#'),
                        'summary': entry.get('summary', '')[:300],
                    })
            except Exception as e:
                print(f"Error fetching {source_name}: {e}")
        return all_news

    @staticmethod
    def get_reddit_trending(subreddits, max_posts=5):
        posts = []
        headers = {'User-Agent': 'DailyDigestBot/1.0'}
        for subreddit in subreddits:
            try:
                url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={max_posts}"
                response = requests.get(url, headers=headers, timeout=10)
                data = response.json()
                for post in data['data']['children']:
                    p = post['data']
                    if not p.get('stickied'):
                        posts.append({
                            'source': f"r/{subreddit}",
                            'title': p['title'],
                            'url': f"https://reddit.com{p['permalink']}",
                            'score': p['score'],
                            'comments': p['num_comments']
                        })
            except Exception as e:
                print(f"Error fetching r/{subreddit}: {e}")
        return posts


class DigestGenerator:
    @staticmethod
    def generate_html(youtube_videos, news_items, reddit_posts):
        date_str = datetime.now().strftime("%A, %B %d, %Y")
        html = f"""
<html>
<head>
<style>
  body {{ font-family: Georgia, serif; max-width: 700px; margin: auto; background: #f9f9f9; color: #222; }}
  .header {{ background: #1a1a2e; color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
  .header h1 {{ margin: 0; font-size: 28px; }}
  .header p {{ margin: 5px 0 0; color: #aaa; }}
  .section {{ background: white; margin: 10px 0; padding: 20px; border-radius: 8px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }}
  .section h2 {{ margin-top: 0; color: #1a1a2e; border-bottom: 2px solid #e0e0e0; padding-bottom: 8px; }}
  .item {{ margin: 14px 0; padding: 12px; background: #f4f4f8; border-radius: 6px; }}
  .item a {{ color: #1a73e8; text-decoration: none; font-weight: bold; font-size: 15px; }}
  .item a:hover {{ text-decoration: underline; }}
  .meta {{ font-size: 12px; color: #888; margin-top: 4px; }}
  .summary {{ font-size: 13px; color: #444; margin-top: 6px; }}
  .footer {{ text-align: center; padding: 20px; color: #aaa; font-size: 12px; }}
</style>
</head>
<body>
  <div class="header">
    <h1>📰 Your Daily Digest</h1>
    <p>{date_str}</p>
  </div>
"""
        # YouTube section
        if youtube_videos:
            html += '<div class="section"><h2>🎬 New from Your YouTube Channels</h2>'
            for v in youtube_videos:
                html += f"""
      <div class="item">
        <a href="{v['url']}">{v['title']}</a>
        <div class="meta">{v['channel']} &bull; {v['published']}</div>
        <div class="summary">{v['description']}</div>
      </div>"""
            html += '</div>'

        # News section
        if news_items:
            html += '<div class="section"><h2>🌍 Top News</h2>'
            for n in news_items:
                html += f"""
      <div class="item">
        <a href="{n['url']}">{n['title']}</a>
        <div class="meta">{n['source']}</div>
        <div class="summary">{n['summary']}</div>
      </div>"""
            html += '</div>'

        # Reddit section
        if reddit_posts:
            html += '<div class="section"><h2>💬 Trending on Reddit</h2>'
            for r in reddit_posts:
                html += f"""
      <div class="item">
        <a href="{r['url']}">{r['title']}</a>
        <div class="meta">{r['source']} &bull; ⬆ {r['score']} &bull; 💬 {r['comments']}</div>
      </div>"""
            html += '</div>'

        html += '<div class="footer">Your automated daily digest &bull; Powered by GitHub Actions</div></body></html>'
        return html


class EmailSender:
    @staticmethod
    def send_email(recipient, subject, html_content, sender_email, password):
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = sender_email
            msg['To'] = recipient
            msg.attach(MIMEText(html_content, 'html'))
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(sender_email, password)
                server.sendmail(sender_email, recipient, msg.as_string())
            print(f"✅ Email sent to {recipient}")
        except Exception as e:
            print(f"❌ Email failed: {e}")
            raise


def main():
    youtube_api_key = os.environ['YOUTUBE_API_KEY']
    sender_email = os.environ['SENDER_EMAIL']
    gmail_password = os.environ['GMAIL_PASSWORD']
    recipient_email = os.environ['RECIPIENT_EMAIL']
    youtube_channels = json.loads(os.environ['YOUTUBE_CHANNELS'])

    print(f"🚀 Starting digest — {datetime.now()}")

    # YouTube
    print("📺 Fetching YouTube videos...")
    yt = YouTubeFetcher(youtube_api_key)
    all_videos = []
    for channel_id in youtube_channels:
        all_videos.extend(yt.get_channel_videos(channel_id, max_results=3))

    # News
    print("📰 Fetching news...")
    news = NewsFetcher.get_rss_news(NEWS_SOURCES, max_items=5)
    reddit = NewsFetcher.get_reddit_trending(REDDIT_SUBREDDITS, max_posts=5)

    # Generate & send
    print("✉️  Generating and sending email...")
    html = DigestGenerator.generate_html(all_videos, news, reddit)
    subject = f"📰 Daily Digest — {datetime.now().strftime('%B %d, %Y')}"
    EmailSender.send_email(recipient_email, subject, html, sender_email, gmail_password)

    print("✅ Done!")


if __name__ == '__main__':
    main()
```

---

### File 2: `requirements.txt`
```
google-api-python-client==2.100.0
google-auth-httplib2==0.2.0
google-auth-oauthlib==1.2.0
feedparser==6.0.10
requests==2.31.0
