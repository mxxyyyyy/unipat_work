
from html.parser import HTMLParser
import re

class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []
        self.skip = False
    def handle_starttag(self, tag, attrs):
        if tag in ('style', 'script'):
            self.skip = True
    def handle_endtag(self, tag):
        if tag in ('style', 'script'):
            self.skip = False
    def handle_data(self, data):
        if not self.skip:
            self.text.append(data)

with open('briefing_note.html', 'r') as f:
    html = f.read()

extractor = TextExtractor()
extractor.feed(html)
text = ' '.join(extractor.text)
text = re.sub(r'\s+', ' ', text).strip()
words = len(text.split())
print(f"Body text word count: {words}")

# Also print first 200 chars to verify
print("\nFirst 200 chars of extracted text:")
print(text[:200])
