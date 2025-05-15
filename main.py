"""
Flask app to serve as the web interface for our Telegram bot.
Enables large file uploads up to 2GB that the Telegram API doesn't support directly.
"""
import os
import uuid
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from media_processor import MediaProcessor
from utils import get_file_extension, get_clean_filename

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")

# Configure upload settings
UPLOAD_FOLDER = 'temp_files'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'webm', 'flv', 'wmv'}
ALLOWED_AUDIO_EXTENSIONS = {'mp3', 'wav', 'ogg', 'm4a', 'aac', 'flac'}
MAX_CONTENT_LENGTH = 2 * 1024 * 1024 * 1024  # 2GB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Store uploaded files temporarily
video_files = {}
audio_files = {}

def allowed_video_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_VIDEO_EXTENSIONS

def allowed_audio_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_AUDIO_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload_video', methods=['GET', 'POST'])
def upload_video():
    if request.method == 'POST':
        # Check if a file was submitted
        if 'video' not in request.files:
            flash('No video file selected')
            return redirect(request.url)
        
        file = request.files['video']
        
        # If user doesn't select a file
        if file.filename == '':
            flash('No video file selected')
            return redirect(request.url)
        
        if file and file.filename and allowed_video_file(file.filename):
            # Generate unique ID for this upload
            upload_id = str(uuid.uuid4())
            
            # Secure the filename and save the file
            original_filename = secure_filename(file.filename)
            file_ext = get_file_extension(original_filename)
            filename = f"video_{upload_id}{file_ext}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Validate video file
            if not MediaProcessor.is_valid_video(filepath):
                flash('Invalid video file format')
                os.remove(filepath)
                return redirect(request.url)
            
            # Store file info
            video_files[upload_id] = {
                'path': filepath,
                'original_name': original_filename
            }
            
            flash('Video uploaded successfully!')
            return redirect(url_for('upload_audio', video_id=upload_id))
        else:
            flash('Invalid file type. Please upload a video file.')
            return redirect(request.url)
    
    return render_template('upload_video.html')

@app.route('/upload_audio/<video_id>', methods=['GET', 'POST'])
def upload_audio(video_id):
    if video_id not in video_files:
        flash('Video session expired or invalid. Please upload your video again.')
        return redirect(url_for('upload_video'))
    
    if request.method == 'POST':
        # Check if a file was submitted
        if 'audio' not in request.files:
            flash('No audio file selected')
            return redirect(request.url)
        
        file = request.files['audio']
        
        # If user doesn't select a file
        if file.filename == '':
            flash('No audio file selected')
            return redirect(request.url)
        
        if file and file.filename and allowed_audio_file(file.filename):
            # Secure the filename and save the file
            original_filename = secure_filename(file.filename)
            file_ext = get_file_extension(original_filename)
            filename = f"audio_{video_id}{file_ext}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Validate audio file
            if not MediaProcessor.is_valid_audio(filepath):
                flash('Invalid audio file format')
                os.remove(filepath)
                return redirect(request.url)
            
            # Store file info
            audio_files[video_id] = {
                'path': filepath,
                'original_name': original_filename
            }
            
            flash('Audio uploaded successfully!')
            return redirect(url_for('merge_files', session_id=video_id))
        else:
            flash('Invalid file type. Please upload an audio file.')
            return redirect(request.url)
    
    return render_template('upload_audio.html', video_id=video_id, 
                          video_name=video_files[video_id]['original_name'])

@app.route('/merge/<session_id>', methods=['GET', 'POST'])
def merge_files(session_id):
    if session_id not in video_files or session_id not in audio_files:
        flash('Upload session expired or invalid. Please start again.')
        return redirect(url_for('upload_video'))
    
    if request.method == 'POST':
        # Get custom filename if provided
        custom_filename = request.form.get('custom_filename', '')
        if custom_filename.strip() == '':
            # Use video filename as default
            base_name = os.path.splitext(video_files[session_id]['original_name'])[0]
            custom_filename = f"{base_name}_with_audio"
        else:
            custom_filename = get_clean_filename(custom_filename)
        
        # Get fast mode preference
        fast_mode = request.form.get('fast_mode', 'off') == 'on'
        
        # Set up paths
        video_path = video_files[session_id]['path']
        audio_path = audio_files[session_id]['path']
        output_filename = f"{custom_filename}.mp4"
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)
        
        # Perform the merge
        success = MediaProcessor.merge_video_audio(video_path, audio_path, output_path, fast_mode=fast_mode)
        
        if success:
            # Save the result to download page
            return redirect(url_for('download_result', filename=output_filename))
        else:
            flash('Failed to merge files. Please try again with different files.')
            return redirect(url_for('upload_video'))
    
    return render_template('merge.html', 
                          video_name=video_files[session_id]['original_name'],
                          audio_name=audio_files[session_id]['original_name'],
                          session_id=session_id)

@app.route('/download/<filename>')
def download_result(filename):
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(filepath):
        # Set headers for download
        return render_template('download.html', filename=filename)
    else:
        flash('File not found or processing error occurred.')
        return redirect(url_for('index'))

@app.route('/get_file/<filename>')
def get_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)