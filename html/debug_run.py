import sys
import traceback

sys.path.insert(0, '.')
from analyze_photos import main

try:
    main()
except Exception as e:
    print(f'ERROR: {e}')
    traceback.print_exc()
