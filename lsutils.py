import numpy as np
from sklearn.cluster import KMeans
import string

""" Removes all sentences that end with a question mark """
def removeQuestionsFromString(text):
  while True:
    qi = text.find('?')
    if qi == -1:
      break
    si = qi - 1
    while si > 0 and not ((text[si] == '.' or text[si] == '?' or text[si] == '!') and text[si+1] == ' '):
      si -= 1
    if si == 0:
      text = text[qi+1:]
    else:
      text = text[0:si+1] + text[qi+1:]
  return text

""" Remove bullet marks and spaces from the ends of the sentence """
def removeBulletsAndStrip(line):
  if len(line) > 3:
    if line[1] == '.': line = line[2:]
    elif line[2] == '.': line = line[3:]
  return line.strip()

""" Given a cluster of docAI returned paragraphs, organize them into an array of columns 
    like in a textbook/newspaper based on their relative positioning in the photo. """
def organizeParagraphsIntoColumns(clusters, xThreshold):
  organizedClusters = []
  for cluster in clusters:
    columns = []
    sortedParagraphs = sorted(cluster, key=lambda p: p['rectangle'][0][0])
    for paragraph in sortedParagraphs:
      rectangle = paragraph['rectangle']
      x = rectangle[0][0]
      # Check if the paragraph can be grouped with an existing column
      columnFound = False
      for column in columns:
        leastXDiff = 1000000;
        for p in column:
          leastXDiff = min(leastXDiff, abs(p['rectangle'][0][0]-x))
        if leastXDiff <= xThreshold:
          column.append(paragraph)
          columnFound = True
          break
      # If the paragraph cannot be grouped with any existing column, create a new column
      if not columnFound:
        columns.append([paragraph])
    # Sort each column vertically
    for i in range(len(columns)):
      columns[i] = sorted(columns[i], key=lambda p: p['rectangle'][0][1])
    organizedClusters.append(columns)
  return organizedClusters

""" Given a cluster of docAI returned paragraphs, cluster them into logical groups
    based on their position in the photo """
def clusterParagraphs(paragraphs):
  if len(paragraphs) <= 1:
    return [paragraphs]

  # Extract rectangle coordinates from paragraphs
  rectangles = [p['rectangle'] for p in paragraphs]

  # Calculate distances between rectangles
  distances = np.zeros((len(rectangles), len(rectangles)))
  for i in range(len(rectangles)):
    for j in range(i+1, len(rectangles)):
      distance = np.linalg.norm(np.array(rectangles[i]) - np.array(rectangles[j]))
      distances[i, j] = distance
      distances[j, i] = distance

  # Perform k-means clustering
  numClusters = 2  # Update this to the desired number of clusters
  kmeans = KMeans(n_clusters=numClusters, random_state=0, n_init=10)
  labels = kmeans.fit_predict(distances)

  # Organize paragraphs into clusters
  clusters = [[] for _ in range(numClusters)]
  for i, label in enumerate(labels):
    clusters[label].append(paragraphs[i])

  return clusters

""" From a list of DocAI response documents, extract all the paragraphs neatly arranged as columns
    as expected in a textbook/newspaper photo.
    Returns a list of clusters, each cluster has a list of columns, and each column has a list of paragraphs.
    Each paragraph has a 'text' and 'rectangle' attribute """
def getParagraphClustersFromOCRDocs(ocrDocs):
  clusters = []
  for doc in ocrDocs:
    for page in doc.pages:
      paragraphs = []
      for block in page.blocks:
        for seg in block.layout.text_anchor.text_segments:
          # ignore sentences that are too short. They are typically labels on images in the page
          if seg.end_index - seg.start_index > 50:
            v = block.layout.bounding_poly.normalized_vertices
            w = page.dimension.width
            h = page.dimension.height
            paragraphs.append({
              'rectangle': [
                ( int(v[0].x * w), int(v[0].y * h) ),
                ( int(v[1].x * w), int(v[1].y * h) ),
                ( int(v[2].x * w), int(v[2].y * h) ),
                ( int(v[3].x * w), int(v[3].y * h) ),
              ],
              'text': doc.text[seg.start_index:seg.end_index]
            })
      if len(paragraphs) > 0:
        clusters.extend(organizeParagraphsIntoColumns(clusterParagraphs(paragraphs), int(page.dimension.width * .1)))

  return clusters

""" Organize the given cluster of column/paragraphs into a list of text inputs to send
    for summarization to BART model """
def getBartInputsFromClusters(clusters):
  maxWordsPerRun = 384  # based on the 512 token limit of BART
  partsToSummarize = []
  text = ''
  for cluster in clusters:
    for column in cluster:
      for paragraph in column:
        paragraphText = paragraph['text'].replace('\n', ' ').strip()
        j = ' '
        if paragraphText[0].isupper() or (len(text) > 0 and text[-1] in string.punctuation):
          j = '\n\n'
        newText = text + j + paragraphText
        newTextWords = len(newText.split())
        if newTextWords < maxWordsPerRun:
          text = newText
        else:
          partsToSummarize.append(text)
          text = paragraphText
  if len(text) > 0:
    partsToSummarize.append(text)

  return partsToSummarize

def splitParagraphIntoSentences(text):
  sentences = []
  for line1 in text.split('.'):
    for line2 in line1.split('?'):
      for line3 in line2.split('!'):
        line3 = line3.strip()
        if len(line3) > 0:
          sentences.append(line3.strip())
  return sentences
