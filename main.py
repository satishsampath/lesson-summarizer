import asyncio
import base64
from flask import Flask, render_template, request
import gc
from google.cloud import documentai
import json
import lsutils
import openai
import os
import requests
import threading

HF_BART_LARGE_CNN_API_URL = 'https://api-inference.huggingface.co/models/facebook/bart-large-cnn'
HF_STABLE_DIFFUSION_URL = 'https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-2-1-base'

app = Flask('LessonSummarizer')
app.jinja_env.add_extension('jinja2.ext.do')
gEventLoop = asyncio.get_event_loop()

def createApp():
  if not os.getenv('GAE_ENV', '').startswith('standard'):  # local run/testing ? set credentials path.
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'service-account-creds.json'
  return app

""" Sends a request to Hugging Face-hosted BART inference API to summarize the given text. """
def summarizeTextWithHFBartLargeCNN(text, minSummaryRatio, maxSummaryRatio):
  numWords = len(text.split())
  approxNumTokens = numWords * 1.3333
  bareMinSummaryTokens = 20
  requestHeaders = {"Authorization": f"Bearer {os.getenv('HF_API_KEY')}"}
  requestData = json.dumps({
    'inputs': text,
    'parameters': {
      'min_length': max(bareMinSummaryTokens, int(approxNumTokens * minSummaryRatio)),
      'max_length': max(bareMinSummaryTokens, int(approxNumTokens * maxSummaryRatio)),
    },
    'options': {
      'wait_for_model': True
    }
  })
  responseJson = requests.request("POST", HF_BART_LARGE_CNN_API_URL, headers=requestHeaders, data=requestData)
  response = json.loads(responseJson.content.decode("utf-8"))
  return response[0]['summary_text']

""" Sends a request to Hugging Face-hosted Stable Diffusion inference API to generate image for the given prompt.
    The generated image is stored in the 'images[index]' item as a b64 encoded string. """
def generateImageFromPrompt(prompt, images, index):
  try:
    requestHeaders = {"Authorization": f"Bearer {os.getenv('HF_API_KEY')}"}
    requestData = json.dumps({
      'inputs': prompt,
      'options': {
        'wait_for_model': True
      }
    })
    response = requests.request("POST", HF_STABLE_DIFFUSION_URL, headers=requestHeaders, data=requestData)
    images[index] = str(base64.b64encode(response.content), 'utf-8')
  except Exception as e:
    print("Image %d had an exception %s" % (index, e))
    pass

def summarizeClustersWithHFTransformers(clusters):
  partsToSummarize = lsutils.getBartInputsFromClusters(clusters)

  # Somewhere between 25% - 40% of original text seems to be a sweet spot for summaries
  minSummaryRatio = .25
  maxSummaryRatio = .4

  summaries = []
  for part in partsToSummarize:
    text = lsutils.removeQuestionsFromString(part)
    summary = summarizeTextWithHFBartLargeCNN(text, minSummaryRatio, maxSummaryRatio)
    summaries.extend(lsutils.splitParagraphIntoSentences(summary))

  return summaries

def generateImagesForLines(lines):
  # Step 1: Use GPT to generate Dall-E prompts for each line
  openai.api_key = os.getenv('OPENAI_API_KEY')
  response_json = openai.ChatCompletion.create(
    model="gpt-3.5-turbo",
    messages=[{
        'role': 'system',
        'content': f"Ignore previous directions. Give me a Dall-E prompt for each of the following {str(len(lines))} sentences."
      }, {
        'role': 'user', 'content': '\n\n'.join(lines) 
      }
    ],
    temperature=0,  # Need predictability in responses
    max_tokens=2048)

  imagePrompts = []
  for line in response_json['choices'][0]['message']['content'].strip().split('\n'):
    line = lsutils.removeBulletsAndStrip(line)
    if len(line) > 0:
      imagePrompts.append(line)

  # Step 2: Using the image prompts, generate images ----
  # Since images take a while to generate, do them in parallel. Sometimes we run into quota or network
  # issues, so retry a couple of times if needed.
  images = [None] * len(imagePrompts)  # gets populated by generateImageFromPrompt
  retries = 3
  while retries > 0:
    retries -= 1
    threads = []
    for i in range(len(images)):
      if images[i] == None:
        thread = threading.Thread(target=generateImageFromPrompt, args=(imagePrompts[i], images, i,))
        threads.append(thread)
        thread.start()
    if len(threads) > 0:
      for th in threads:
        th.join()

  return images

@app.route('/')
def routeRoot():
  return render_template('index.html')

@app.route('/summarize', methods=['POST'])
def routeSummarize():
  if not request.files or 'image' not in request.files or not request.files['image']:
    return 'No image uploaded. Please go back and try again.', 400

  file = request.files['image']
  docAIClient = documentai.DocumentProcessorServiceClient()
  resourceName = docAIClient.processor_path(os.getenv('GCP_PROJECT_ID'), os.getenv('GCP_LOCATION'), os.getenv('GCP_DOCAI_PROCESSOR_ID'))
  result = docAIClient.process_document(
    request=documentai.ProcessRequest(
      name=resourceName,
      raw_document=documentai.RawDocument(content=file.read(), mime_type=file.mimetype),
    )
  )

  # Step 1 : cluster the recognized text into columns & paragraphs
  clusters = lsutils.getParagraphClustersFromOCRDocs([result.document])

  # Step 2: summarize paragarphs into short sentences
  lines = summarizeClustersWithHFTransformers(clusters)

  # Step 3: generate images
  images = generateImagesForLines(lines)

  # Do GC after each request so our instance doesn't get restarted soon
  gc.collect()

  return json.dumps({'lines': lines, 'images': images})

if __name__ == '__main__':
  createApp()
  app.run(host='127.0.0.1', port=8080, debug=True)
