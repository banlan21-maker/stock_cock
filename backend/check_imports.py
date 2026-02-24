try:
    import numpy
    print(f"numpy version: {numpy.__version__}")
except ImportError as e:
    print(f"numpy import failed: {e}")

try:
    import pandas
    print(f"pandas version: {pandas.__version__}")
except ImportError as e:
    print(f"pandas import failed: {e}")

try:
    import pykrx
    print(f"pykrx imported successfully")
except ImportError as e:
    print(f"pykrx import failed: {e}")
except Exception as e:
    print(f"pykrx import error: {e}")
