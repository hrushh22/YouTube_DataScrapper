from googleapiclient.discovery import build
from dotenv import load_dotenv
import os

def test_api_key():
    # Load environment variables
    load_dotenv()
    api_key = os.getenv('YOUTUBE_API_KEY')
    
    if not api_key:
        print("Error: API key not found in .env file")
        return
    
    try:
        # Initialize the API client
        youtube = build('youtube', 'v3', developerKey=api_key)
        
        # Make a simple request
        request = youtube.videos().list(
            part='snippet',
            chart='mostPopular',
            maxResults=1
        )
        response = request.execute()
        
        print("API test successful!")
        print(f"Successfully retrieved video: {response['items'][0]['snippet']['title']}")
        
    except Exception as e:
        print(f"Error testing API key: {str(e)}")

if __name__ == "__main__":
    test_api_key()