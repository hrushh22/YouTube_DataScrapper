import os
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from youtube_transcript_api import YouTubeTranscriptApi
import pandas as pd
import time
from datetime import datetime
import isodate
from dotenv import load_dotenv
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log'),
        logging.StreamHandler()
    ]
)

class YouTubeScraper:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        api_key = os.getenv('YOUTUBE_API_KEY')
        if not api_key:
            raise ValueError("YouTube API key not found in environment variables")
        
        self.youtube = build('youtube', 'v3', developerKey=api_key)
        self.results = []
        self.processed_videos = set()

    def search_videos(self, genre, max_results=500):
        """Search for videos of a specific genre."""
        logging.info(f"Starting search for genre: {genre}")
        
        try:
            # Initial search request
            request = self.youtube.search().list(
                part='id,snippet',
                q=genre,
                type='video',
                maxResults=50,  # YouTube API limit is 50 per request
                relevanceLanguage='en',
                videoDuration='medium'  # Filter for medium length videos
            )
            
            videos_processed = 0
            while request and videos_processed < max_results:
                try:
                    response = request.execute()
                    
                    # Process each video
                    for item in response['items']:
                        if videos_processed >= max_results:
                            break
                            
                        video_id = item['id']['videoId']
                        if video_id not in self.processed_videos:
                            video_data = self.get_video_details(video_id)
                            if video_data:
                                self.results.append(video_data)
                                self.processed_videos.add(video_id)
                                videos_processed += 1
                                logging.info(f"Processed video {videos_processed}/{max_results}")
                                
                                # Save progress every 50 videos
                                if videos_processed % 50 == 0:
                                    self.save_progress()
                            
                        # Respect API quotas
                        time.sleep(0.1)
                    
                    # Get next page of results
                    request = self.youtube.search().list_next(request, response)
                    
                except HttpError as e:
                    if e.resp.status in [403, 429]:  # Quota exceeded or rate limit
                        logging.error(f"API quota exceeded or rate limit reached: {e}")
                        time.sleep(60)  # Wait a minute before retrying
                        continue
                    else:
                        raise
                
        except Exception as e:
            logging.error(f"An error occurred during video search: {str(e)}")
            self.save_progress()  # Save what we have so far
            raise

    def get_video_details(self, video_id):
        """Get detailed information about a specific video."""
        try:
            # Get video details
            video_response = self.youtube.videos().list(
                part='snippet,contentDetails,statistics,recordingDetails,topicDetails',
                id=video_id
            ).execute()

            if not video_response['items']:
                return None

            video = video_response['items'][0]
            snippet = video['snippet']
            statistics = video['statistics']
            
            # Check for captions
            captions_available = False
            caption_text = ""
            try:
                transcript = YouTubeTranscriptApi.get_transcript(video_id)
                captions_available = True
                caption_text = ' '.join([entry['text'] for entry in transcript])
            except Exception as e:
                logging.debug(f"No captions available for video {video_id}: {str(e)}")

            # Build video data dictionary
            video_data = {
                'Video URL': f'https://www.youtube.com/watch?v={video_id}',
                'Title': snippet.get('title', ''),
                'Description': snippet.get('description', ''),
                'Channel Title': snippet.get('channelTitle', ''),
                'Keyword Tags': ','.join(snippet.get('tags', [])),
                'YouTube Video Category': snippet.get('categoryId', ''),
                'Topic Details': ','.join(video.get('topicDetails', {}).get('topicCategories', [])),
                'Video Published at': snippet.get('publishedAt', ''),
                'Video Duration': str(isodate.parse_duration(video['contentDetails']['duration'])),
                'View Count': statistics.get('viewCount', 0),
                'Comment Count': statistics.get('commentCount', 0),
                'Captions Available': captions_available,
                'Caption Text': caption_text,
                'Location of Recording': str(video.get('recordingDetails', {}))
            }
            
            return video_data
            
        except HttpError as e:
            logging.error(f'HTTP error occurred while getting video details: {str(e)}')
            return None
        except Exception as e:
            logging.error(f'Error occurred while getting video details: {str(e)}')
            return None

    def save_progress(self):
        """Save current progress to a temporary file."""
        temp_filename = f'youtube_data_temp_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        self.save_to_csv(temp_filename)
        logging.info(f"Progress saved to {temp_filename}")

    def save_to_csv(self, filename):
        """Save results to CSV file."""
        df = pd.DataFrame(self.results)
        df.to_csv(filename, index=False, encoding='utf-8')
        logging.info(f"Data saved to {filename}")

def main():
    try:
        # Initialize scraper
        scraper = YouTubeScraper()
        
        # Get genre from user
        genre = input("Enter the genre to search for: ")
        
        # Search for videos
        logging.info(f"Starting search for {genre} videos...")
        scraper.search_videos(genre)
        
        # Save final results
        output_file = f'youtube_{genre}_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        scraper.save_to_csv(output_file)
        logging.info(f"Process completed successfully. Final data saved to {output_file}")

    except Exception as e:
        logging.error(f"An error occurred in main: {str(e)}")
        raise

if __name__ == "__main__":
    main()