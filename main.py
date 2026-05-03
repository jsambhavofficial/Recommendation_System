import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.metrics.pairwise import cosine_similarity
from spellchecker import SpellChecker
import re
import json
import os

# Load career guidance database
_dir = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(_dir, 'career_guidance.json'), 'r', encoding='utf-8') as f:
    career_guidance = json.load(f)


# LOAD & CLEAN DATA
df = pd.read_csv(os.path.join(_dir, "course_recommendation_dataset.csv"))

df['Course_Name'] = df['course_name'].fillna('').str.lower()
df['Domain'] = df['course_domain'].fillna('').str.lower()
df['Level'] = df['course_level'].fillna('').str.lower()
df['Description'] = df['course_description'].fillna('').str.lower()

# Map the missing columns that the rest of the script expects
df['Organization'] = df['organisation'].fillna('')
df['Rating'] = df['course_rating'].fillna(0)
df['Certificate'] = 'yes'  # This dataset doesn't have this info, so we default to 'yes'

df['Description'] = df['Description'].str.replace('[^a-zA-Z ]', '', regex=True)

df['text'] = (
    df['Course_Name'] + " " + df['Description']
)

# TRAIN MODEL
vectorizer = TfidfVectorizer(
    ngram_range=(1,2),   # BEST BALANCE (Unigram + Bigram)
    stop_words='english',
    max_features=500
)

X = vectorizer.fit_transform(df['text'])
y = df['Domain']

model = LinearSVC(random_state=42)
model.fit(X, y)


# MULTI-DOMAIN DETECTION
def detect_domains(query_vec, threshold=0.0, max_domains=5):
    scores = model.decision_function(query_vec)[0]
    classes = model.classes_

    sorted_indices = np.argsort(scores)[::-1]

    selected_domains = []

    for idx in sorted_indices:
        if scores[idx] > threshold:
            selected_domains.append(classes[idx])
        if len(selected_domains) == max_domains:
            break

    if not selected_domains:
        selected_domains.append(classes[sorted_indices[0]])

    return selected_domains


# LEARNING PATH
learning_paths = {
    "web development": ["html", "css", "javascript", "react"],
    "data science": ["python", "statistics", "machine learning", "data visualization"],
    "machine learning": ["python", "statistics", "machine learning", "deep learning"],
    "cybersecurity": ["network", "security", "cryptography", "ethical hacking"],
    "cloud computing": ["aws", "azure", "kubernetes", "docker"],
    "mobile development": ["java", "swift", "kotlin", "react native"],
    "devops": ["linux", "git", "jenkins", "docker"],
    "database": ["sql", "nosql", "mongodb", "postgresql"],
    "artificial intelligence": ["python", "machine learning", "deep learning", "neural networks"],
    "business & management": ["leadership", "strategy", "project management", "finance"],
    "marketing & digital marketing": ["seo", "social media", "content marketing", "analytics"],
    "finance & accounting": ["accounting", "financial modeling", "economics", "investment"],
    "design & creative": ["photoshop", "illustrator", "ui", "ux"],
    "healthcare & medicine": ["anatomy", "biology", "healthcare", "nutrition"],
    "engineering": ["mechanics", "thermodynamics", "cad", "robotics"],
    "science": ["physics", "chemistry", "biology", "research"],
    "mathematics": ["algebra", "calculus", "statistics", "geometry"],
    "language learning": ["english", "spanish", "french", "grammar"],
    "education & teaching": ["pedagogy", "curriculum", "psychology", "teaching"],
    "arts & humanities": ["history", "philosophy", "literature", "art"],
    "psychology": ["cognitive", "behavioral", "counseling", "mental health"],
    "law": ["contracts", "criminal", "corporate", "ethics"],
    "architecture & urban planning": ["design", "autocad", "planning", "sustainability"],
    "agriculture & environment": ["sustainability", "ecology", "farming", "climate"],
    "sports & fitness": ["nutrition", "exercise", "training", "wellness"],
    "culinary arts & hospitality": ["cooking", "baking", "management", "hospitality"],
    "python": ["python basics", "python programming", "web development", "django"],
    "java": ["java basics", "object oriented programming", "spring", "projects"]
}

# INITIALIZE SPELL CHECKER WITH CUSTOM DICTIONARY
spell = SpellChecker()
all_text = " ".join(df['Course_Name'].tolist() + df['Domain'].tolist())
clean_text = re.sub(r'[^a-z ]', '', all_text)
tech_words = set(clean_text.split())

for path_skills in learning_paths.values():
    tech_words.update(path_skills)

spell.word_frequency.load_words(list(tech_words))

def query_correct(text):
    words = text.lower().split()
    corrected = []
    for w in words:
        clean_w = w.strip('.,!?;:')
        if clean_w in ['c++', 'c#', '.net', 'node.js', 'react.js']:
            corrected.append(clean_w)
        else:
            corrected.append(spell.correction(clean_w) or clean_w)
    return " ".join(corrected)



def extract_level(query):
    if "beginner" in query:
        return "beginner"
    elif "intermediate" in query:
        return "intermediate"
    elif "advanced" in query:
        return "advanced"
    return None


def extract_certificate(query):
    if "certificate" in query:
        return "yes"
    return None


# CONVERSATIONAL INTENTS (only handle simple greetings/gratitude locally)
def handle_conversational_intent(query):
    query = query.lower().strip()
    greetings = ["hi", "hello", "hey", "hii", "good morning", "good evening", "hi there"]
    gratitude = ["thank you", "thanks", "tysm", "thankyou", "thx"]

    # Check for exact matches or sentence starters
    if any(query == g or query.startswith(g + " ") for g in greetings):
        return "Hello! I am your AI Course & Career Assistant. Ask me about courses, career advice, salaries, or say 'help me choose a career'!"
    elif any(query == g or query.startswith(g + " ") for g in gratitude):
        return "You're very welcome! Let me know if you need any more course recommendations or career guidance."
    
    return None


# MAIN FUNCTION
def recommend_courses(user_query):

    # Step 1: spelling correction
    user_query = query_correct(user_query.lower())

    # EXPLICIT SKILL MATCHING (Fixing "python" and "java" issue)
    known_skills = ['python', 'java', 'c++', 'sql', 'javascript', 'react', 'html', 'css', 'docker', 'kubernetes', 'aws', 'machine learning', 'cybersecurity']
    detected_skills = [skill for skill in known_skills if skill in user_query.split() or skill in user_query]

    # Step 2: vectorize query
    query_vec = vectorizer.transform([user_query])

    # GIBBERISH DETECTION
    if query_vec.nnz == 0 and not detected_skills:
        print("\n[!] I could not understand your query. Please try different keywords.")
        return {}

    # Step 3: detect domains (ML Prediction)
    domains = detect_domains(query_vec)

    print(f"\nPredicted ML Domains: {[d.upper() for d in domains]}")
    if detected_skills:
        print(f"Detected Explicit Skills: {[s.upper() for s in detected_skills]}")

    # Step 4: filters
    level = extract_level(user_query)
    certificate = extract_certificate(user_query)

    final_results = {}
    level_order = {'beginner': 1, 'all levels': 2, 'intermediate': 3, 'advanced': 4}

    # CAREER INTENT DETECTION
    career_keywords = ["career", "job", "salary", "role", "work", "hire", "guidance"]
    career_intent = any(re.search(rf'\b{kw}s?\b', user_query) for kw in career_keywords)

    # RECOMMEND PER EXPLICIT SKILL (Creates a "PYTHON" or "JAVA" section)
    for skill in detected_skills:
        skill_df = df[df['text'].str.contains(rf'\b{skill}\b', regex=True)]
        if level:
            temp_df = skill_df[skill_df['Level'] == level]
            if not temp_df.empty: skill_df = temp_df
        if certificate:
            temp_df = skill_df[skill_df['Certificate'] == certificate]
            if not temp_df.empty: skill_df = temp_df
            
        if not skill_df.empty:
            skill_matrix = vectorizer.transform(skill_df['text'])
            similarities = cosine_similarity(query_vec, skill_matrix).flatten()
            
            temp_df = skill_df.copy()
            temp_df['sim'] = similarities
            temp_df = temp_df.sort_values(by=['sim', 'Rating'], ascending=[False, False])
            temp_df = temp_df.drop_duplicates(subset=['Course_Name'])
            
            final_results[skill.upper()] = {
                "recommendations": temp_df.head(3)[['Course_Name', 'Organization', 'Rating', 'Level']],
                "path": {},
                "guidance": career_guidance.get(skill.lower()) if career_intent else None
            }

    # RECOMMEND PER ML DOMAIN
    for domain in domains:
        if domain.upper() in final_results:
            continue
            
        domain_df = df[df['Domain'] == domain]
        if level:
            temp_df = domain_df[domain_df['Level'] == level]
            if not temp_df.empty: domain_df = temp_df

        if certificate:
            temp_df = domain_df[domain_df['Certificate'] == certificate]
            if not temp_df.empty: domain_df = temp_df

        if domain_df.empty:
            domain_df = df[df['Domain'] == domain]

        domain_matrix = vectorizer.transform(domain_df['text'])
        similarities = cosine_similarity(query_vec, domain_matrix).flatten()

        temp_df = domain_df.copy()
        temp_df['sim'] = similarities
        temp_df = temp_df.sort_values(by=['sim', 'Rating'], ascending=[False, False])
        temp_df = temp_df.drop_duplicates(subset=['Course_Name'])

        final_results[domain.upper()] = {
            "recommendations": temp_df.head(3)[['Course_Name', 'Organization', 'Rating', 'Level']],
            "path": {},
            "guidance": career_guidance.get(domain.lower()) if career_intent else None
        }

    # LEARNING PATH
    all_recs = [data["recommendations"] for data in final_results.values()]
    all_selected_courses = pd.concat(all_recs) if all_recs else pd.DataFrame()
    selected_names = set(all_selected_courses['Course_Name']) if not all_selected_courses.empty else set()

    for section in final_results.keys():
        section_lower = section.lower()
        if section_lower in learning_paths:
            for skill in learning_paths[section_lower]:
                skill_df = df[df['text'].str.contains(skill)]
                if not skill_df.empty:
                    skill_df = skill_df[~skill_df['Course_Name'].isin(selected_names)]
                    skill_df = skill_df.drop_duplicates(subset=['Course_Name'])
                    
                    # Sort by Level (Beginner to Advanced) -> Rating
                    skill_df['level_rank'] = skill_df['Level'].str.lower().map(level_order).fillna(5)
                    sorted_skill_df = skill_df.sort_values(by=['level_rank', 'Rating'], ascending=[True, False])
                    
                    final_results[section]["path"][skill] = sorted_skill_df.head(2)[['Course_Name', 'Rating', 'Level']]

    return final_results


if __name__ == "__main__":
    # TEST
    query = "i want to learn ai and cybersecurity"

    print(f"\nUser: {query}")

    conversational_response = handle_conversational_intent(query)

    if conversational_response:
        print(f"Bot: {conversational_response}")
    else:
        results = recommend_courses(query)

        for domain, data in results.items():
            print(f"\n========== COURSE RECOMMENDATIONS ==========")
            print(f"=== {domain.upper()} ===")
            print(data["recommendations"])

            if data["path"]:
                print("\n========== LEARNING PATH ==========")
                for skill, courses in data["path"].items():
                    print(f"\n{skill.upper()}:")
                    print(courses)
