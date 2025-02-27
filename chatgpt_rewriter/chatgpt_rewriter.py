# chatgpt_rewriter.py
import openai
import os
from dotenv import load_dotenv
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# Debugging step: Print statements for clarity
print("Initializing ChatGPT Rewriter...")

# Load environment variables from .env file
env_path = os.path.join(os.getcwd(), ".env")
if os.path.exists(env_path):
    print(f"Found .env file at: {env_path}")
    load_dotenv(env_path)
else:
    print("Error: .env file not found. Please ensure it exists and contains the OpenAI API key.")
    exit(1)

# Get the API key
api_key = os.getenv("OPENAI_API_KEY")

# Check if the key is loaded
if not api_key:
    print("Error: OpenAI API key not found in .env file. Ensure the key is saved in this format:")
    print("OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
    exit(1)
else:
    print("OpenAI API key successfully loaded.")

# Set the OpenAI API key
openai.api_key = api_key

# Test the OpenAI API connection
try:
    print("Testing OpenAI API connection...")
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "This is a test prompt. Please confirm the API is working."}
        ]
    )
    print("API test successful. Response received:")
    print(response.choices[0].message['content'])
except Exception as e:
    print(f"Error during API test: {e}")
    exit(1)

# Google Docs API Setup
SCOPES = ['https://www.googleapis.com/auth/documents']

def authenticate_google_docs():
    """Authenticate and return the Google Docs service."""
    token_path = os.path.join(os.getcwd(), 'token.json')
    client_secret_path = os.path.join(os.getcwd(), 'client_secret.json')

    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(client_secret_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, 'w') as token_file:
            token_file.write(creds.to_json())

    return build('docs', 'v1', credentials=creds)

def create_google_doc(service, title):
    """Create a new Google Doc with the given title and return its ID."""
    document = service.documents().create(body={"title": title}).execute()
    return document.get("documentId")

def append_to_google_doc(service, doc_id, content):
    """Append content to the specified Google Doc."""
    requests = [{"insertText": {"location": {"index": 1}, "text": content}}]
    service.documents().batchUpdate(documentId=doc_id, body={"requests": requests}).execute()

def process_google_doc(google_doc_url):
    """Fetch and process text from the specified Google Doc."""
    doc_id = google_doc_url.split('/d/')[1].split('/')[0]

    try:
        print("Authenticating Google Docs API...")
        service = authenticate_google_docs()

        print(f"Fetching content from Google Doc ID: {doc_id}")
        document = service.documents().get(documentId=doc_id).execute()

        # Get the original document name
        original_title = document.get("title", "Untitled Document")
        new_title = f"Rewrite - {original_title}"

        # Create a new document for the rewritten content
        print(f"Creating new Google Doc: {new_title}")
        new_doc_id = create_google_doc(service, new_title)

        # Extract content from the original document
        content = ""
        for element in document.get('body').get('content', []):
            if 'paragraph' in element:
                paragraphs = element['paragraph']['elements']
                for para in paragraphs:
                    if 'textRun' in para:
                        content += para['textRun']['content']

        print("Google Doc content successfully fetched.")
        rewritten_text = chatgpt_rewrite(content)
        print("Rewritten text:")
        print(rewritten_text)

        # Append rewritten content to the new Google Doc
        print(f"Appending rewritten text to Google Doc: {new_title}")
        append_to_google_doc(service, new_doc_id, rewritten_text)
        print(f"Rewritten content successfully saved to Google Doc: {new_title} ({new_doc_id})")

    except Exception as e:
        print(f"Error processing Google Doc: {e}")

def chatgpt_rewrite(text):
    """
    Sends the provided text to ChatGPT and gets a rewritten version.
    """
    prompt = (
        "Rewrite the given text to make it concise, engaging, and formatted for describing an image. "
        "Follow these guidelines:\n"
        "1. Treat the provided text as a description of an image; rewrite it as if explaining the image to someone who cannot see it.\n"
        "2. Use a tone that is direct, punchy, and captivating, aiming for virality in short-form video captions.\n"
        "3. Keep each description to one or two sentences, ensuring they are clear and easy to understand at a fourth-grade reading level.\n"
        "4. Avoid redundancy, but include essential context or key details that enhance the description.\n"
        "5. Assume the original text may not perfectly describe the image; focus on clarity, impact, and accuracy when rewriting.\n"
        "6. Retain dates or names only if they add significant context, and avoid describing visual details already evident from the image (e.g., colors, shapes).\n"
        "\nExample Input:\n"
        "The majestic Harpy eagle, one of the world’s largest birds that often grows to the height of a human.\n"
        "\nExample Output:\n"
        "The Harpy eagle, one of the world’s largest birds, often grows as tall as a person."
    )
    try:
        print("Sending text to ChatGPT for rewriting...")
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": f"{prompt}\n\nText to rewrite:\n{text}"}
            ]
        )
        rewritten_text = response['choices'][0]['message']['content'].strip()
        print("Rewritten text received from ChatGPT.")
        return rewritten_text
    except Exception as e:
        print(f"Error communicating with ChatGPT API: {e}")
        return None

def main():
    print("ChatGPT Rewriter script is running successfully!")
    while True:
        google_doc_url = input("Enter the Google Doc URL (or press Ctrl+C to exit): ").strip()
        if google_doc_url:
            process_google_doc(google_doc_url)
        else:
            print("Invalid URL. Please try again.")

if __name__ == "__main__":
    main()
