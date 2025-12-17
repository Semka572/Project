# ------------------------------------------------------------
# UI Templates Module (fixed version)
# ------------------------------------------------------------

# ---------------------- LOGIN PAGE ----------------------
LOGIN_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Login</title>
    <style>
        body { font-family: Arial; background: #f0f0f0; }
        .box {
            width: 300px; margin: 120px auto; background: #fff;
            padding: 20px; border-radius: 10px; box-shadow: 0 0 10px #aaa;
        }
        input { width: 100%; padding: 8px; margin-top: 8px; }
        button { width: 100%; padding: 10px; margin-top: 12px; }
        a { text-decoration: none; }
    </style>
</head>
<body>
    <div class="box">
        <h2>Login</h2>
        <form method="POST">
            <input name="username" placeholder="Username" required>
            <input name="password" type="password" placeholder="Password" required>
            <button type="submit">Log in</button>
        </form>
        <p>New user? <a href="/register">Register</a></p>
    </div>
</body>
</html>
"""

# ---------------------- REGISTER PAGE ----------------------
REGISTER_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Register</title>
    <style>
        body { font-family: Arial; background: #f0f0f0; }
        .box {
            width: 300px; margin: 120px auto; background: #fff;
            padding: 20px; border-radius: 10px; box-shadow: 0 0 10px #aaa;
        }
        input { width: 100%; padding: 8px; margin-top: 8px; }
        button { width: 100%; padding: 10px; margin-top: 12px; }
        a { text-decoration: none; }
    </style>
</head>
<body>
    <div class="box">
        <h2>Register</h2>
        <form method="POST">
            <input name="username" placeholder="Username" required>
            <input name="password" type="password" placeholder="Password" required>
            <button type="submit">Register</button>
        </form>
        <p><a href="/login">Back to login</a></p>
    </div>
</body>
</html>
"""

# ---------------------- STUDENT LIST PAGE ----------------------
STUDENTS_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Students</title>
    <style>
        body { font-family: Arial; background: #e5e5e5; }
        .container {
            width: 600px; margin: auto; background: #fff;
            margin-top: 40px; padding: 20px;
            border-radius: 10px; box-shadow: 0 0 10px #aaa;
        }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { padding: 8px; border-bottom: 1px solid #ccc; text-align: left; }
        button { padding: 6px 12px; }
        a { text-decoration: none; }
    </style>
</head>
<body>
    <div class="container">
        <h2>Your Students</h2>

        <form action="/add_student" method="POST">
            <input name="name" placeholder="Student name" required>
            <button>Add Student</button>
        </form>

        <table>
            <tr>
                <th>Name</th>
                <th>Actions</th>
            </tr>
            {% for s in students %}
            <tr>
                <td>{{ s.name }}</td>
                <td>
                    <a href="/edit/{{ s.id }}">Edit</a> |
                    <a href="/predict/{{ s.id }}">Predict</a> |
                    <a href="/delete/{{ s.id }}">Delete</a>
                </td>
            </tr>
            {% endfor %}
        </table>

        <p><a href="/logout">Logout</a></p>
    </div>
</body>
</html>
"""

# ---------------------- EDIT STUDENT PAGE ----------------------
EDIT_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Edit {{ student.name }}</title>
    <style>
        body { font-family: Arial; background: #f0f0f0; }
        .box {
            width: 520px; 
            margin: 40px auto; 
            background: #fff;
            padding: 25px; 
            border-radius: 12px; 
            box-shadow: 0 0 10px #aaa;
        }
        label { 
            margin-top: 12px; 
            display: block; 
            font-size: 15px; 
            font-weight: bold;
        }
        input[type=number],
        input[type=text] {
            width: 100%; 
            padding: 8px; 
            margin-top: 6px;
        }
        .course-row {
            display: flex; 
            align-items: center; 
            margin-bottom: 8px;
        }
        .course-row label {
            width: 220px;
            font-weight: normal;
        }
        .course-row input[type=checkbox] {
            width: 18px; 
            height: 18px;
        }
        .course-row input[type=number] {
            width: 80px; 
            margin-left: 10px;
        }
        button {
            width: 100%; 
            padding: 12px; 
            margin-top: 20px;
            background: purple; 
            color: #fff; 
            border: none;
            border-radius: 8px;
        }
        a { 
            text-decoration: none; 
            margin-top: 12px; 
            display: block; 
            color: purple; 
        }
        h3 {
            margin-top: 30px;
        }
    </style>
</head>
<body>

    <div class="box">
        <h2>Edit {{ student.name }}</h2>

        <form method="POST">

            <!-- Academic performance block -->
            <h3>Academic Performance (Ga calculation)</h3>

            <label>Gcurrent (your current grade, 0–100)</label>
            <input type="number" name="Gcurrent" step="0.1" value="{{ student.Gcurrent or '' }}">

            <label>Gmin (minimum possible grade)</label>
            <input type="number" name="Gmin" step="0.1" value="{{ student.Gmin or '' }}">

            <label>Gmax (maximum possible grade)</label>
            <input type="number" name="Gmax" step="0.1" value="{{ student.Gmax or '' }}">


            <!-- Additional factors -->
            <h3>Additional Factors</h3>

            <label>Ls (LMS activity)</label>
            <input type="number" name="Ls" step="0.01" value="{{ student.Ls or '' }}">

            <label>Ph (Historical performance)</label>
            <input type="number" name="Ph" step="0.01" value="{{ student.Ph or '' }}">

            <label>Actual Outcome (0..1)</label>
            <input type="number" name="actual" step="0.01" value="{{ student.actual or '' }}">


            <!-- COURSES -->
            <h3>Courses</h3>

            {% for c in courses %}
            <div class="course-row">
                <input type="checkbox" name="course_{{c.id}}_enabled"
                       {% if c.enabled %}checked{% endif %}>
                <label>{{ c.name }}</label>
                <input type="number" min="0" max="100" step="1"
                       name="course_{{c.id}}_grade"
                       value="{{ c.grade if c.grade != None else '' }}">
            </div>
            {% endfor %}


            <button type="submit">Save</button>
        </form>

        <a href="/students">Back</a>
    </div>

</body>
</html>
"""


# ---------------------- PREDICTION PAGE ----------------------
PREDICTION_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Prediction for {{ student.name }}</title>
    <style>
        body {
            font-family: Arial;
            background: #f4f4f4;
        }
        .box {
            width: 420px;
            margin: 60px auto;
            background: #fff;
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 0 10px #bfbfbf;
        }
        h2 { margin-top: 0; }
        p { font-size: 18px; margin: 8px 0; }
        a { color: purple; text-decoration: none; font-size: 18px; }
        ul { font-size: 18px; padding-left: 20px; }
    </style>
</head>
<body>

    <div class="box">
        <h2>Prediction for {{ student.name }}</h2>

        <p><b>Initial Probability:</b> {{ p_initial }}</p>

        {% if p_adjusted %}
            <p><b>Adjusted Probability:</b> {{ p_adjusted }}</p>

            <h3>Adjusted Weights:</h3>
            <ul>
                <li>α = {{ weights.alpha }}</li>
                <li>β = {{ weights.beta }}</li>
                <li>γ = {{ weights.gamma }}</li>
                <li>δ = {{ weights.delta }}</li>
                <li>ε = {{ weights.epsilon }}</li>
            </ul>
        {% else %}
            <p><i>No actual value → weight adjustment unavailable.</i></p>
        {% endif %}

        <br>
        <p><a href="/students">Back</a></p>
    </div>

</body>
</html>
"""
