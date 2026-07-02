from streamlit.testing.v1 import AppTest

def test_app():
    at = AppTest.from_file("streamlit_app.py", default_timeout=30)
    at.run()
    if at.exception:
        print("Exception:", at.exception)
    else:
        print("No exception on load.")
test_app()
