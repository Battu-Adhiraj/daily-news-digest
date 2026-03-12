# 🧠 AI Editor-in-Chief (Automated Daily Digest)

A fully automated, 100% cloud-based Python agent designed to cure information overload and bypass algorithmic doomscrolling. 

Every day, this agent wakes up, scrapes the internet for content from my favorite creators and global news sources, reads the raw transcripts, filters out the sensationalism, and uses Generative AI to deliver a calm, factual, and perfectly formatted HTML newsletter directly to my inbox.

## 🚀 The Problem & The Solution
**The Problem:** The modern internet optimizes for clickbait, outrage, and stress. Checking the news or YouTube for updates often leads to wasted time and spiked cortisol. 
**The Solution:** I built an "Editor-in-Chief." Instead of browsing feeds, I have an AI read the internet for me, strip out the emotion and sponsorships, and hand me a factual summary while I eat lunch.

## ⚙️ Architecture & Workflow
The pipeline runs entirely on the cloud for **$0/month** using the following steps:
1. **The Trigger (GitHub Actions):** A cron job spins up a virtual Ubuntu machine every day at exactly 12:00 PM IST.
2. **The Gatherer (Python):** - Bypasses standard YouTube API quotas by fetching hidden channel RSS feeds.
   - Extracts auto-generated text using `youtube-transcript-api`.
   - Parses top global news using `feedparser`.
   - Pulls trending Reddit discussions using `requests`.
3. **The Brain (Gemini API):** The raw data dump (thousands of words) is sent to the **Gemini 3 Flash** model. A strict system prompt forces the AI to cross-reference facts, neutralize emotional language, and generate a mobile-friendly HTML email.
4. **The Delivery (SMTP):** The script connects to a Gmail SMTP server and fires the beautifully formatted HTML newsletter directly to my inbox.

## 🛠️ Tech Stack
* **Language:** Python 3.11
* **AI Model:** Google Gemini 3 Flash Preview (`google-generativeai`)
* **Automation (CI/CD):** GitHub Actions
* **Data Extraction:** `youtube-transcript-api`, `feedparser`, `google-api-python-client`

## 👨‍💻 How to Fork and Run It Yourself
Want to build your own AI Editor? 
1. **Fork** this repository.
2. Go to **Settings > Secrets and variables > Actions** and add the following Repository Secrets:
   - `GEMINI_API_KEY` (Get it from Google AI Studio)
   - `YOUTUBE_API_KEY` (Get it from Google Cloud Console)
   - `SENDER_EMAIL` (Your bot's Gmail address)
   - `GMAIL_PASSWORD` (A 16-digit Google App Password, *not* your standard password)
   - `RECIPIENT_EMAIL` (Where you want the digest sent)
   - `YOUTUBE_CHANNELS` (A JSON array of channel IDs, e.g., `["UC123...", "UC456..."]`)
3. Go to the **Actions** tab in your repo and enable workflows. You can run it manually or let the daily cron schedule take over!

---
*Built to reclaim focus and optimize daily information intake.*
