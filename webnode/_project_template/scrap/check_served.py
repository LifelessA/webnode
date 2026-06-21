import urllib.request

# Fetch the admin page
req = urllib.request.Request('http://localhost:8000/admin')
req.add_header('Cookie', 'admin_session=admin')
resp = urllib.request.urlopen(req)
html = resp.read().decode('utf-8', errors='replace')

with open('admin_served.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f"Total length: {len(html)}")
print(f"<script> count: {html.count('<script>')}")
print(f"<script src count: {html.count('<script src')}")
print(f"</script> count: {html.count('</script>')}")
print(f"</html> count: {html.count('</html>')}")
print(f"</body> count: {html.count('</body>')}")

# Check if there are any null bytes or weird characters
null_count = html.count('\x00')
print(f"Null bytes: {null_count}")

# Check last 200 chars
print(f"\n=== LAST 200 CHARS ===")
print(repr(html[-200:]))

# Check around script tags
idx = html.find('<script>')
if idx != -1:
    print(f"\n=== AROUND INLINE <script> (pos {idx}) ===")
    print(repr(html[idx-50:idx+50]))
