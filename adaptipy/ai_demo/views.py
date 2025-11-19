from django.http import JsonResponse
from django.shortcuts import render
import subprocess
import tempfile
import os
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

# Available topics for selection
TOPICS = ["loops", "strings", "arrays", "recursion", "conditionals", "variables"]

def generate_problem_with_solution(concept="loops"):
    """Use OpenAI to generate a problem with a known solution"""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You create Python coding problems that use PRINT statements. The expected output should match what print() would display."},
                {"role": "user", "content": f"""Create a simple Python problem about {concept} that uses print() statements.
                
                Return format:
                {{
                    "problem": "Clear problem description here",
                    "expected_output": "The exact output that print() would show"
                }}
                
                IMPORTANT: The expected output should be multiple lines if multiple print() statements are used.
                
                Example:
                {{
                    "problem": "Write a loop that prints even numbers from 1 to 10",
                    "expected_output": "2\\n4\\n6\\n8\\n10"
                }}"""}
            ],
            max_tokens=150,
            temperature=0.7
        )
        
        result_text = response.choices[0].message.content.strip()
        result = json.loads(result_text)
        
        problem = result.get('problem', 'Write a loop that prints even numbers from 1 to 10')
        expected_output = result.get('expected_output', '2\n4\n6\n8\n10')
        
        print(f"AI Generated - Problem: {problem}")
        print(f"AI Generated - Expected: {repr(expected_output)}")
        
        return problem, expected_output
        
    except Exception as e:
        print(f"OpenAI failed: {e}")
        # Simple fallback problems based on topic
        fallback_problems = {
            "loops": ("Write a loop that prints numbers 1 to 5", "1\n2\n3\n4\n5"),
            "strings": ("Print each character of 'hello' on separate lines", "h\ne\nl\nl\no"),
            "arrays": ("Create a list [1,2,3] and print each element", "1\n2\n3"),
            "recursion": ("Print numbers from 5 down to 1", "5\n4\n3\n2\n1"),
            "conditionals": ("Print 'even' if 4 is even, 'odd' otherwise", "even"),
            "variables": ("Create a variable x=10 and print it", "10")
        }
        return fallback_problems.get(concept, ("Write a loop that prints numbers 1 to 5", "1\n2\n3\n4\n5"))

def evaluate_code_quality(code, problem_description):
    """Use OpenAI to give vague hints without specific solutions"""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": """You are a helpful coding assistant. Give VERY VAGUE hints when students have errors.
                
                RULES:
                - NEVER give the solution or write code
                - NEVER point to specific lines
                - NEVER mention specific variable names
                - Keep hints to 1-2 sentences max
                - Be encouraging and positive
                
                Examples of good vague hints:
                - "Remember that indentation is important in Python"
                - "Check your syntax when writing loops and conditionals" 
                - "Make sure you're using the right data types"
                - "Think about the order of your operations"
                - "Double-check your variable assignments"
                - "Consider if you need any conditional statements"
                - "Remember what each loop iteration should do"
                
                Examples of BAD hints (too specific):
                - "You forgot a colon on line 3"
                - "Change 'x' to 'y'"
                - "Use a for loop instead of while"
                - "Add print statements here"
                """},
                {"role": "user", "content": f"""Problem: {problem_description}
                
                Student's code (which has an error):
                ```python
                {code}
                ```
                
                Please provide a brief, vague hint to help them think about the problem differently."""}
            ],
            max_tokens=100,
            temperature=0.3
        )
        
        feedback = response.choices[0].message.content.strip()
        return feedback
        
    except Exception as e:
        print(f"OpenAI evaluation failed: {e}")
        return "Keep trying! Review the basics and try again."

def check_user_code(code, expected_output):
    """Check if the user's code produces the expected output"""
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        result = subprocess.run(['python3', temp_file], capture_output=True, text=True, timeout=5)
        
        os.unlink(temp_file)
        
        user_output = result.stdout.strip()
        expected_clean = expected_output.strip()
        
        is_correct = result.returncode == 0 and user_output == expected_clean
        
        return is_correct, user_output
        
    except Exception as e:
        print(f"Code check exception: {e}")
        return False, ""

def coding_demo(request):
    result = None
    user_code = ""
    evaluation_feedback = None
    selected_topic = request.session.get('selected_topic', 'loops')
    
    if request.method == 'POST' and 'select_topic' in request.POST:
        selected_topic = request.POST.get('topic', 'loops')
        request.session['selected_topic'] = selected_topic
        # Clear current problem when topic changes
        if 'current_problem' in request.session:
            del request.session['current_problem']
        if 'current_expected_output' in request.session:
            del request.session['current_expected_output']
    
    if request.method == 'POST' and 'new_problem' in request.POST:
        if 'current_problem' in request.session:
            del request.session['current_problem']
        if 'current_expected_output' in request.session:
            del request.session['current_expected_output']
    
    if 'current_problem' not in request.session or 'current_expected_output' not in request.session:
        ai_problem, expected_output = generate_problem_with_solution(selected_topic)
        request.session['current_problem'] = ai_problem
        request.session['current_expected_output'] = expected_output
    else:
        ai_problem = request.session['current_problem']
        expected_output = request.session['current_expected_output']
    
    if request.method == 'POST' and 'code' in request.POST:
        user_code = request.POST.get('code', '')
        if user_code:
            is_correct, user_output = check_user_code(user_code, expected_output)
            if is_correct:
                result = f" Correct! Your output: {user_output}"
                if 'current_problem' in request.session:
                    del request.session['current_problem']
                if 'current_expected_output' in request.session:
                    del request.session['current_expected_output']
            else:
                result = f" Not quite right. Expected: {expected_output}, Got: {user_output if user_output else 'No output'}"
                evaluation_feedback = evaluate_code_quality(user_code, request.session['current_problem'])
    
    return render(request, 'coding_demo.html', {
        'result': result,
        'user_code': user_code,
        'ai_problem': ai_problem,
        'topics': TOPICS,
        'selected_topic': selected_topic,
        'evaluation_feedback': evaluation_feedback
    })

def recommend_problem(request):
    """Simple recommendation based on topic"""
    weak_area = request.GET.get('weakness', 'loops')
    return JsonResponse({
        'weakness': weak_area,
        'recommended_topic': weak_area,
        'message': f'Try practicing {weak_area} problems!'
    })