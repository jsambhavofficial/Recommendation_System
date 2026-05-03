# AI Course Recommendation System & Career Assistant

An intelligent web application that provides personalized course recommendations and career guidance using Machine Learning (LinearSVC, TF-IDF) and Google's Gemini AI. 

## 🛠️ Technologies Used

- **Frontend**: HTML5, CSS3, JavaScript
- **Backend**: Python, Flask
- **Machine Learning**: Scikit-Learn (TF-IDF Vectorizer, LinearSVC, Cosine Similarity)
- **Natural Language Processing**: PySpellChecker
- **AI / LLM Integration**: Google Gemini API (`google-generativeai`)
- **Database**: SQLite (for storing user sessions and chat histories)
- **Data Manipulation**: Pandas, NumPy

## 📦 Dependencies

To run this project, you need to have Python installed. The required Python packages are:

- `flask` (Web framework)
- `pandas` (Data processing)
- `numpy` (Numerical operations)
- `scikit-learn` (Machine learning algorithms)
- `pyspellchecker` (Spelling correction for queries)
- `python-dotenv` (Environment variable management)
- `google-genai` (Google Gemini API wrapper)

You can install all of them using a single command:
```bash
pip install flask pandas numpy scikit-learn pyspellchecker python-dotenv google-genai
```

## Vercel Deployment

This project is configured for Vercel's Python serverless runtime.

1. Push this repository to GitHub.
2. Import the repository in Vercel.
3. Add these environment variables in Vercel Project Settings:
```env
GEMINI_API_KEY=your_api_key_here
SECRET_KEY=use_a_long_random_secret
```
4. Deploy. Vercel will use `vercel.json` and `requirements.txt`.

Note: SQLite on Vercel is temporary because serverless storage is ephemeral. Login and chat history may reset between function instances. For production persistence, use an external database such as Neon Postgres, Supabase, or Turso.

## ⚙️ Installation & Setup

Follow these steps to get the project running on your local machine:

### 1. Clone the Repository
```bash
git clone https://github.com/jsambhavofficial/Recommendation_System.git
cd Recommendation_System
```

### 2. Set Up a Virtual Environment (Recommended)
```bash
python -m venv venv
# On Windows
venv\Scripts\activate
# On macOS/Linux
source venv/bin/activate
```

### 3. Install Required Dependencies
```bash
pip install flask pandas numpy scikit-learn pyspellchecker python-dotenv google-genai
```

### 4. Configure Environment Variables
1. Create a `.env` file in the root directory (you can copy `.env.example`).
2. Add your Google Gemini API key to the file. You can get a free API key from [Google AI Studio](https://aistudio.google.com/apikey).
```env
GEMINI_API_KEY=your_api_key_here
```

### 5. Run the Application
Start the Flask backend server:
```bash
python app.py
```

### 6. Access the Web App
Open your web browser and navigate to:
```
http://127.0.0.1:5000/
```

## 💡 Features
- **AI Career Counselor**: Ask anything about career paths, skills, and industry trends (powered by Gemini AI).
- **Smart Course Recommendations**: Type a domain or skill (e.g., "I want to learn machine learning"), and the ML engine will predict the best domain and return top-rated courses.
- **Learning Paths**: Automatically structured learning paths from beginner to advanced.
- **Typo Tolerance**: Built-in spell checking detects and corrects misspelled tech skills automatically.
- **Secure Authentication**: User sign-up, login, and encrypted chat session storage using SQLite.
