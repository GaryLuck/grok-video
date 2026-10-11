import os
import sys
import time
import base64
import mimetypes
import requests

# Set your OpenRouter API Key
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

if OPENROUTER_API_KEY == "YOUR_OPENROUTER_API_KEY" or not OPENROUTER_API_KEY:
    print("❌ Error: Please set your OPENROUTER_API_KEY inside the script or environment variables.")
    sys.exit(1)

def get_image_data_url(image_path_or_url):
    """Converts a local image file to a base64 Data URL or returns a web URL."""
    if not image_path_or_url:
        return None
        
    if image_path_or_url.startswith(("http://", "https://")):
        return image_path_or_url

    if not os.path.exists(image_path_or_url):
        print(f"❌ Error: Local file '{image_path_or_url}' not found.")
        sys.exit(1)

    mime_type, _ = mimetypes.guess_type(image_path_or_url)
    if not mime_type:
        mime_type = "image/jpeg"

    with open(image_path_or_url, "rb") as img_file:
        b64_data = base64.b64encode(img_file.read()).decode("utf-8")
        
    return f"data:{mime_type};base64,{b64_data}"

def generate_grok_video():
    print("--- Grok Imagine Video 1.5 Lite Generation ---")
    prompt = input("📝 Enter your text prompt: ")
    image_input = input("🖼️ Enter local image path OR web image URL (Leave blank for text-only): ").strip()

    submit_url = "https://openrouter.ai/api/v1/videos"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "x-ai/grok-imagine-video-1.5-lite",
        "prompt": prompt,
        "aspect_ratio": "16:9",
        "duration": 5,
        "resolution": "720p"
    }

    # Add first-frame image if provided
    if image_input:
        image_data_url = get_image_data_url(image_input)
        payload["frame_images"] = [
            {
                "type": "image_url",
                "image_url": {"url": image_data_url},
                "frame_type": "first_frame"
            }
        ]

    # Step 1: Submit generation job
    print("\n🚀 Submitting video generation job to OpenRouter...")
    response = requests.post(submit_url, headers=headers, json=payload)
    
    # Check for HTTP errors (like 401 Unauthorized, 400 Bad Request)
    if response.status_code not in [200, 202]:
        print(f"❌ HTTP Submission Error ({response.status_code}): {response.text}")
        return

    job_data = response.json()
    job_id = job_data.get("id")
    polling_url = job_data.get("polling_url")
    initial_status = job_data.get("status")
    
    if not polling_url:
        print(f"❌ Error: Did not receive a polling URL from OpenRouter. Response: {job_data}")
        return

    print(f"✅ Job accepted! Job ID: {job_id} | Initial Status: {initial_status}")
    
    # Step 2: Poll job status using the provided polling URL
    print("⏳ Polling for video completion (checking every 15 seconds)...")
    
    while True:
        status_response = requests.get(polling_url, headers=headers)
        if status_response.status_code != 200:
            print(f"❌ Error polling job: {status_response.text}")
            return
            
        status_data = status_response.json()
        status = status_data.get("status")
        print(f"   Current status: {status}")

        if status == "completed":
            print("🎉 Video generation completed!")
            break
        elif status in ["failed", "cancelled", "expired"]:
            print(f"❌ Video generation stopped with status: {status}")
            if "error" in status_data:
                print(f"   Details: {status_data['error']}")
            return
            
        time.sleep(15)

    # Step 3: Download the video file
    # OpenRouter lets you stream binary bytes directly from the dedicated content path
    content_url = f"https://openrouter.ai/api/v1/videos/{job_id}/content?index=0"
    output_filename = f"grok_video_{job_id[-8:]}.mp4"
    
    print(f"📥 Downloading video file from OpenRouter...")
    video_response = requests.get(content_url, headers=headers, stream=True)
    
    if video_response.status_code == 200:
        with open(output_filename, "wb") as f:
            for chunk in video_response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"✨ Success! Your video is saved as: {os.path.abspath(output_filename)}")
    else:
        print(f"❌ Failed to download video file: {video_response.text}")

if __name__ == "__main__":
    generate_grok_video()
