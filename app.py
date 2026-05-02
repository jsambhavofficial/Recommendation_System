from flask import Flask, request, jsonify, render_template
import pandas as pd
from main import handle_conversational_intent, recommend_courses

app = Flask(__name__, template_folder='.')

@app.route('/')
@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/chatbot')
def chatbot():
    return render_template('live.html')



def df_to_json(df):
    """Helper to convert Pandas DataFrame to list of dicts safely."""
    if df is None or df.empty:
        return []
    # Replace NaN with None so jsonify works
    return df.where(pd.notnull(df), None).to_dict(orient='records')

@app.route('/recommend', methods=['POST'])
def recommend():
    data = request.json
    query = data.get('query', '')
    
    # 1. Check for conversational intents first
    conv_response = handle_conversational_intent(query)
    if conv_response:
        return jsonify({"status": "greeting", "message": conv_response})
        
    # 2. Get recommendations
    results, path = recommend_courses(query)
    
    # 3. Handle empty results
    if not results and not path:
        return jsonify({"status": "off_topic", "message": "No relevant courses found."})
        
    # Convert learning path format
    json_path = {}
    if path:
        for skill, df in path.items():
            json_path[skill] = df_to_json(df)
            
    # 4. Handle multiple domains (Comparison mode triggered inside chat)
    if len(results) > 1:
        domains = list(results.keys())
        query_a = domains[0]
        query_b = domains[1]
        
        path_a = {
            "domain": query_a,
            "recommendations": df_to_json(results[query_a]),
            "learning_path": json_path # Add the learning path
        }
        
        path_b = {
            "domain": query_b,
            "recommendations": df_to_json(results[query_b]),
            "learning_path": {}
        }
        
        return jsonify({
            "status": "multi_domain",
            "query_a": query_a,
            "path_a": path_a,
            "query_b": query_b,
            "path_b": path_b
        })
        
    # 5. Handle single domain
    domain_name = list(results.keys())[0] if results else ""
    return jsonify({
        "status": "success",
        "domain": domain_name,
        "recommendations": df_to_json(results[domain_name]) if domain_name in results else [],
        "learning_path": json_path
    })




if __name__ == '__main__':
    print("[SUCCESS] CourseBot AI API is starting on http://127.0.0.1:5000 ...")
    app.run(debug=True, port=5000)
