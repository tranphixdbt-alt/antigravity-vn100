import re

with open("valuation/views/select_ticker.py", "r") as f:
    content = f.read()

# Remove the inner function and replace it
new_content = content.replace('''        @st.cache_data(ttl=10800) # cache 3 giờ
        def load_macro_bulletin():
            from valuation.data_access.macro_news import generate_macro_bulletin
            return generate_macro_bulletin()''', '')

header = '''
@st.cache_data(ttl=10800) # cache 3 giờ
def load_macro_bulletin():
    from valuation.data_access.macro_news import generate_macro_bulletin
    return generate_macro_bulletin()

'''
new_content = new_content.replace('def render_select_ticker(db_read: Session, db_write: Session = None):', header + 'def render_select_ticker(db_read: Session, db_write: Session = None):')

with open("valuation/views/select_ticker.py", "w") as f:
    f.write(new_content)
