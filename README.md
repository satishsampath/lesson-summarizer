# lesson-summarizer
Summarizes multi-page textbook lessons.

# Example
![Photo of an example summary](/static/images/example.jpg)

## Usage
1. On your **mobile phone**, ppen the live demo at [https://lesson-summarizer.uc.r.appspot.com/](https://lesson-summarizer.uc.r.appspot.com/).
2. Click the button to open the phone camera.
3. Take a photo of a textbook page.
4. Wait for the summary to show up on screen!

## Under the hood
#### Where are you hosting?
This is a python Flask-based web app running on Google Cloud platform.

#### What do you use for OCR / photo to text?
[Document AI API](https://cloud.google.com/python/docs/reference/documentai/latest) from Google Cloud. It works really well, even with photos that are poorly lit, up-side down or rotated.

#### What do you use for text summarization?
* [BART (large-sized model)](https://huggingface.co/facebook/bart-large-cnn), available as an inference API from Hugging Face 🤗. They have a very generous free tier which makes prototyping a lot of fun.
* Before summarization, the text from OCR is grouped into paragraphs, clustered into logical areas of the page, split into columns and combined where appropriate into larger paragraphs.

#### What do you use for image generation?
* [OpenAI GPT-3.5](https://platform.openai.com/docs/guides/chat) for generating an image prompt for each line of the summary
* [Stable Diffusion](https://huggingface.co/stabilityai/stable-diffusion-2-1-base) for the actual image generation, available as an inference API from Hugging Face 🤗. Dall-E produces nicer looking images for this use case, but their free tier allows only 5 image generations per minute which could be hit within a single textbook page.

#### How do I deploy to my own website?
* Setup a Google Cloud project
  * Add Cloud Document AI to your Google Cloud project, and create a OCR document processor to it (instructions can be googled up)
  * Google AppEngine would create a service account. Download the credentials into a service-account-creds.json file at the root of this repository
  * Add AppEngine python (standard environment) to your Google Cloud project
* Create an account with Hugging Face 🤗 and OpenAI. Create API keys for both and store them somewhere safe
* Clone this repo & set up your local environment
```
gh repo clone satishsampath/lesson-summarizer
cd lesson-summarizer
python -m venv env
pip install -r requirements.txt
source venv/bin/activate
```
* Create an 'env_variables.yaml' file with the following variables set
```
GCP_PROJECT_ID: (your Google Cloud project id)
GCP_LOCATION: "us"
GCP_DOCAI_PROCESSOR_ID: (your Document AI OCR processor id)
HF_API_KEY: (your Hugging Face 🤗 API key)
OPENAI_API_KEY: (your OpenAI API key)
```
* Deploy!
```
gcloud app deploy
```
