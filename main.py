from flask import Flask, render_template

app = Flask('LessonSummarizer')
app.jinja_env.add_extension('jinja2.ext.do')

def createApp():
  if not os.getenv('GAE_ENV', '').startswith('standard'):  # local run/testing ? set credentials path.
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'service-account-creds.json'
  return app

@app.route('/')
def pageRoot():
  return render_template('index.html')

if __name__ == '__main__':
  createApp()
  app.run(host='127.0.0.1', port=8080, debug=True)
