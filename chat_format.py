"""Safe display-only Markdown subset: bold, italic and literal code."""
import re
from tkinter import font
TOKEN=re.compile(r'(?P<fence>```[^\n`]*\n(?P<body>[\s\S]*?)```)|(?P<code>`(?P<inline>[^`\n]+)`)|(?P<bold>(?<!\*)\*\*(?P<strong>[^*\n]+?)\*\*(?!\*))|(?P<italic>(?<!\w)(?<!\*)\*(?P<em>[^*\n]+?)\*(?!\w)(?!\*))')
def spans(text):
    text=str(text);start=0
    for match in TOKEN.finditer(text):
        if match.start()>start:yield text[start:match.start()],None
        if match.group('fence') is not None:
            yield match.group('body'),'block'
        elif match.group('code') is not None:
            yield match.group('inline'),'code'
        else:
            tag='bold' if match.group('bold') is not None else 'italic'
            value=match.group('strong') if tag=='bold' else match.group('em')
            yield (value.strip(),tag) if value.strip() else (match.group(0),None)
        start=match.end()
    if start<len(text):yield text[start:],None

def pieces(text):
    # Compatibility helper used by the original bold tests.
    for value,tag in spans(text):yield value,tag=='bold'

def insert(widget,text):
    if not hasattr(widget,'_markdown_fonts'):
        base=font.Font(font=widget.cget('font'))
        bold=base.copy();bold.configure(weight='bold')
        italic=base.copy();italic.configure(slant='italic')
        mono=font.Font(family='Consolas',size=base.cget('size'))
        widget._markdown_fonts=(base,bold,italic,mono)
        widget.tag_configure('markdown_bold',font=bold)
        widget.tag_configure('markdown_italic',font=italic)
        widget.tag_configure('markdown_code',font=mono,background='#252a30',foreground='#b8dfed')
        widget.tag_configure('markdown_block',font=mono,background='#20252b',foreground='#d4e2eb',lmargin1=12,lmargin2=12,rmargin=12,spacing1=6,spacing3=6)
    for value,tag in spans(text):
        widget.insert('end',value,('markdown_'+tag,) if tag else ())
