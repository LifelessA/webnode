import json

# 1. Put your normal HTML inside triple quotes
raw_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Home</title>
</head>
<body class="deep-navy-bg">
    <h1>Welcome to Luxury Escapes</h1>
</body>
</html>"""

# 2. Put it inside a Python dictionary
data = {
    "html_code": raw_html
}

# 3. Convert the dictionary to a JSON string
# json.dumps automatically adds the \n and escapes the " marks!
json_result = json.dumps(data, indent=4)

print(json_result)