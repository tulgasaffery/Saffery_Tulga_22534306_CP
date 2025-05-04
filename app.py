#TULGA SAFFERY - 22534306 - ITS FOR PRIMARY MATHEMATICS
#PLEASE READ THE .README FILE TO UNDERSTAND HOW TO RUN EVERYTHING SMOOTHLY

#OPEN TERMINAL
#SHELL COMMANDS TO SET UP VIRTUAL ENVIRONMENT AND INSTALL DEPENDENCIES
#1. python --version
#2. cd "C:\Users\tulga\OneDrive - MMU\BSc COMPUTER SCIENCE\3rd Year\Semester 2\Synoptic Project\Saffery_Tulga_22534306_CP" (place in double quotations as spaces in directory)
#3. python -m venv venv
#4. Set-ExecutionPolicy Bypass -Scope Process
#5. ./venv/Scripts/Activate.ps1
#6. Press ctrl + shift + p -> select interpreter in the editor (venv)
#7. pip install flask
#8. pip freeze > requirements.txt
#9. pip install -r requirements.txt
#10. install pandas: pip install pandas
#11. Once Finished Working with code: In terminal -> deactivate (will leave the virtual environment)

import sys
from flask import Flask, render_template, request, redirect, url_for, session, flash
import pandas as pd

# define the order in which difficulty levels should progress
DIFFICULTY_ORDER = ['easy', 'medium', 'hard']

#Achievement specifications with counts or streak thresholds, labels, and badges images
ACHIEVEMENTS = {
    'first_blood':{'count':1,'label':"First Blood!", 'badge':"first_blood.png"},
    'five_total':{'count':5,'label':"5 correct answers!", 'badge':"five_in_a_row.png"},
    'ten_total':{'count':10,'label':"10 correct answers!", 'badge':"ten_in_a_row.png"},
    #streak-based achievements: 5 in a row!
    'streak_5':{'streak':5,'label':"5 in a row!", 'badge':"streak_master.png"},
}

#Initalise Flask Application
app = Flask(__name__)
#Secret key for session encryption
app.secret_key = 'synopticproject'

# PATH to the CSV QuestionBank
QUESTION_FILE = 'questionbank.csv'

# Load the question bank safely, handling missing or empty file errors
try:
    df = pd.read_csv(QUESTION_FILE, sep=';', encoding='utf-8-sig', dtype=str) #semicolon-seperated values, handle BOM if present, load all columns as string to avoid mixed types
except FileNotFoundError:
    app.logger.error("Question File not found: %s", QUESTION_FILE)
    sys.exit(f"ERROR: Could not find {QUESTION_FILE}.")
except pd.errors.EmptyDataError:
    app.logger.error("Question File is empty: %s", QUESTION_FILE)
    sys.exit(f"ERROR: {QUESTION_FILE} is empty.")


#Normalise column headers: strip whitetease, drop BOM Characters, convert to lowercase
df.columns = (
    df.columns
      .str.strip()
      .str.replace('^\ufeff','', regex=True)
      .str.lower()
)

##Normalise data in key columns: strip whitetease and convert to lowercase strings
for col in ['questionid','question','answer','topic','difficulty','year','explanation']:
    if col in df.columns:
        df[col] = df[col].astype(str).str.strip().str.lower()

#Ensure that certain session variables are initialized before each request
@app.before_request
def ensure_session():
    session.setdefault('correct_count', 0)  #total correct answers so far
    session.setdefault('asked_ids', [])     #list of question IDS already asked
    session.setdefault('streak', 0)         #current correct answer streak
    session.setdefault('achievements', [])  # unlocked achievement keys
    session.setdefault('times', [])         # response times for each question

# Homepage route: shows initial landing page
@app.route('/')
def index():
    # If no answers given yet, clear any achievements from session
    if session.get('correct_count', 0) == 0:
        session['achievements'] = []
    return render_template('index.html')


# Route to select topic (and optionally difficulty), starting a new quiz
@app.route('/select', methods=['GET','POST'])
def choose_filters():
    if request.method == 'POST':
        # Store chosen topic in session
        session['topic'] = request.form['topic'].lower()
        # Determine which difficulties are available in the data
        avail = [d for d in DIFFICULTY_ORDER if d in df['difficulty'].unique()]
        session['difficulties'] = avail
        session['difficulty_index'] = 0     #start at easiest
        session['difficulty'] = avail[0]    
        session['asked_ids'] = []           # reset asked questions
        session['correct_count'] = 0        # reset score
        session['streak'] = 0               # reset streak
        session['achievements'] = []        # reset unlocked achievements
        return redirect(url_for('question'))
    
    # GET request: render selection form with available topics and difficulties
    topics = sorted(df['topic'].unique())
    difficulties = sorted(df['difficulty'].unique())
    return render_template('select.html', topics=topics, difficulties=difficulties)

# Route to display a question based on current session filters and difficulty
@app.route('/question')
def question():
    # Ensure filters are set; otherwise redirect to selection page
    if 'difficulties' not in session or 'difficulty_index' not in session:
        return redirect(url_for('choose_filters'))

    diffs = session['difficulties']
    idx = session['difficulty_index']
    current = diffs[idx]
    session['difficulty'] = current # store current difficulty level

    # Filter DataFrame for questions not yet asked, matching topic and difficulty
    mask = (
        ~df['questionid'].isin(session['asked_ids'])
        & (df['topic'] == session['topic'])
        & (df['difficulty'] == current)
    )
    subset = df[mask]

    # If no questions left for this difficulty/topic, render 'done' page
    if subset.empty:
        return render_template('done.html', total=session['correct_count'], topic=session['topic'].title(), difficulty=current.title())

    # Randomly sample one question row and store its ID in session
    qrow = subset.sample(n=1).iloc[0]
    session['current_q'] = qrow['questionid']
    session['asked_ids'].append(qrow['questionid'])

    # Render the question template
    return render_template(
        'question.html',
        question=qrow['question'],
        topic=qrow['topic'].title(),
        difficulty=current.title()
    )

# Route to process submitted answers
@app.route('/answer', methods=['POST'])
def answer():
    # Record the time spent (in seconds) answering this question
    time_spent = float(request.form.get('time_spent', 0))
    session['times'].append(time_spent) #record time and add to session[times]

    # Get user's submitted answer, normalize
    user_ans = request.form.get('answer','').strip().lower()
    qid = session.get('current_q')
    qrec = df[df['questionid'] == qid].iloc[0] if qid else None

    # If question record not found, reset quiz
    if qrec is None:
        flash("Session error: question not found. Let's restart.", 'error')
        return redirect(url_for('select'))

    # Check correctness and update session metrics
    correct = (user_ans == qrec['answer'])
    if correct:
        session['correct_count'] += 1
        session['streak'] += 1
        flash(f"Correct! You took {time_spent:.1f} seconds", 'success')
    else:
        session['streak'] = 0
        flash(f"Incorrect. (took {time_spent:.1f} seconds). {qrec.get('explanation','')}", 'warning')

    # Handle achievement unlocking
    newly = []
    for key, spec in ACHIEVEMENTS.items():
        if key in session['achievements']:
            continue # skip if already unlocked
            
        # Unlock total-correct achievements
        if spec.get('count') and session['correct_count'] >= spec['count']:
            session['achievements'].append(key)
            newly.append(spec['label'])

        # Unlock streak-based achievements
        elif spec.get('streak') and session['streak'] >= spec['streak']:
            session['achievements'].append(key)
            newly.append(spec['label'])

    # Notify user of newly unlocked achievements
    for label in newly:
        flash(f"Achievement unlocked: {label}", 'success')
    #end achievements logic


    # Adaptive difficulty: increase or decrease based on streak and correctness
    diffs = session['difficulties']
    idx = session['difficulty_index']
    if session['streak'] >= 5 and idx < len(diffs)-1:
        # level up after a 5-answer streak
        idx += 1
        session['streak'] = 0
        session['difficulty_index'] = idx
        session['difficulty'] = diffs[idx]
        flash(f"Well done! Moving up to {diffs[idx].title()} questions.", 'info')
    elif not correct and idx > 0:
        # level down after an incorrect answer
        idx -= 1
        session['difficulty_index'] = idx
        session['difficulty'] = diffs[idx]
        flash(f"Switching down to {diffs[idx].title()} for more practice", 'info')
    # Redirect to next question
    return redirect(url_for('question'))

# Route to reset the quiz entirely (clears session filters and stats)
@app.route('/reset')
def reset():
    for key in ('topic','difficulty','asked_ids','correct_count','current_q','streak','difficulties','difficulty_index','achievements'):
        session.pop(key, None)
    return redirect(url_for('index'))

# Make the achievements config available to all templates
@app.context_processor
def inject_achievements():
    return dict(ACHIEVEMENTS=ACHIEVEMENTS)

# Compute and inject the average response time into all templates
@app.context_processor
def inject_progress():
    times = session.get('times', [])
    avg = None
    if times:
        avg = sum(times) / len(times)
    return dict(average_time = avg)  # will be None if no times recorded

# Run the app in debug mode when this script is executed directly
if __name__ == '__main__':
    app.run() #remove debug=True before deployment (production mode)

#DEPLOYMENT:
#WILL BE USING RENDER TO DEPLOY WEBSITE APPLICATION
#CREATED VIRTUAL ENVIRONMENT
#python -m venv venv
#./venv/Scripts/Activate.ps1
#install packages
#flask
#pip install pandas
#gunicorn - needed to run app on render - pip install gunicorn
#pip freeze > requirements.txt (do when deploying)
