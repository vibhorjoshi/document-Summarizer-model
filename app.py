from flask import Flask, render_template, request
import spacy
from spacy.lang.en.stop_words import STOP_WORDS
from heapq import nlargest
from bs4 import BeautifulSoup
import speech_recognition as sr
from moviepy.editor import VideoFileClip
from pydub import AudioSegment
from googletrans import Translator,LANGUAGES
from transformers import pipeline
import os


nlp = spacy.load("en_core_web_sm")
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

summarizer = pipeline("summarization", model="t5-base", revision="main")


def txt_summarizer(raw_docx):
    stopwords = list(STOP_WORDS)
    docx = nlp(raw_docx)
    
    word_frequencies = {}
    for word in docx:
        if word.text.lower() not in stopwords:
            if word.text.lower() not in word_frequencies.keys():
                word_frequencies[word.text.lower()] = 1
            else:
                word_frequencies[word.text.lower()] += 1
    
    maximum_frequency = max(word_frequencies.values())
    for word in word_frequencies.keys():
        word_frequencies[word] = (word_frequencies[word] / maximum_frequency)
    
    sentence_list = [sentence for sentence in docx.sents]
    
    sentence_scores = {}
    for sent in sentence_list:
        for word in sent:
            if word.text.lower() in word_frequencies.keys():
                if sent not in sentence_scores.keys():
                    sentence_scores[sent] = word_frequencies[word.text.lower()]
                else:
                    sentence_scores[sent] += word_frequencies[word.text.lower()]
    
    summarized_sentences = nlargest(7, sentence_scores, key=sentence_scores.get)
    final_sentences = [w.text for w in summarized_sentences]
    summary = ' '.join(final_sentences)
    
    return summary

@app.route('/')
def home():
    return render_template('index.html')


@app.route('/summarize', methods=['POST'])
def summarize():
    raw_doc = request.form["text"]
    print("Received input:", raw_doc)  # Check if the input is received
    summary = txt_summarizer(raw_doc)
    return render_template('index.html',text=raw_doc,summary=summary)

@app.route('/summarize1', methods=['POST'])
def summarize1():
    uploaded_file = request.files['file']
    soup = BeautifulSoup(uploaded_file, 'html.parser')

    # Remove all <a> tags (links)
    for a_tag in soup.find_all('a'):
        a_tag.extract()

    # Remove all <img> tags (images)
    for img_tag in soup.find_all('img'):
        img_tag.extract()

    # Extract text from modified HTML
    text = soup.get_text(separator='\n', strip=True)
    
    summary = txt_summarizer(text)
    return render_template('index.html', summary1=summary)
        

@app.route('/summarize2', methods=['POST'])
def summarize2():
    uploaded_file = request.files['file']


    # Transcribe the exported audio file
    recognizer = sr.Recognizer()


    with sr.AudioFile(uploaded_file) as source:
        audio_data = recognizer.record(source)  # Record the entire audio file

    text = recognizer.recognize_google(audio_data)
    summary = txt_summarizer(text)
    
    return render_template('index.html', summary2=summary)

@app.route('/summarize_translate', methods=['POST'])
def summarize_translate():
    if request.method == 'POST':
        text = request.form['text']
        target_language = request.form['target_language']

        # Perform summarization
        summary = summarizer(text, max_length=150, min_length=30, do_sample=False)
        summarized_text = summary[0]['summary_text']

        # Perform translation with error handling
        translator = Translator()
        try:
            translation = translator.translate(summarized_text, dest=target_language)
            translated_text = translation.text
        except Exception as e:
            translated_text = f"Translation Error: {str(e)}"

        return render_template('index.html', summarized_text=summarized_text, translated_text=translated_text)



@app.route('/upload', methods=['POST'])
def upload_file():
    if request.method == 'POST':
        video_file = request.files['video']
        if video_file:
            video_path = os.path.join(app.config['UPLOAD_FOLDER'], video_file.filename)
            video_file.save(video_path)

            audio_path = os.path.join(app.config['UPLOAD_FOLDER'], 'audio.wav')

            try:
                video = VideoFileClip(video_path)
                audio = video.audio
                audio.write_audiofile(audio_path)
            except Exception as e:
                return f'Error extracting audio: {str(e)}'

            # Transcribe audio to text using SpeechRecognition
            transcribed_text = transcribe_audio(audio_path)

            # Perform text summarization
            summarized_text = summarize_text(transcribed_text)

            return render_template('index.html', summarized_text=summarized_text)

    return 'Upload failed'
def transcribe_audio(audio_path):
    recognizer = sr.Recognizer()
    audio_file = sr.AudioFile(audio_path)
    with audio_file as source:
        audio_data = recognizer.record(source)
        transcribed_text = recognizer.recognize_google(audio_data)
    return transcribed_text

def summarize_text(text):
    summary = summarizer(text, max_length=150, min_length=30, do_sample=False)
    summarized_text = summary[0]['summary_text']
    return summarized_text


    
if __name__ == '__main__':
    app.run(debug=True)
