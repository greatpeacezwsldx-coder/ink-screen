import sys
import traceback
import time
from pathlib import Path

sys.path.insert(0, '.')
from analyze_photos import call_vlm, generate_side_caption

def main():
    img_path = Path('test/IMG_3241.JPG')
    print(f'处理: {img_path}')
    
    try:
        print('Step 1: call_vlm...')
        t1 = time.time()
        result, exif_info = call_vlm(img_path)
        print(f'Step 1 done ({time.time()-t1:.1f}s)')
        print(f'  caption: {str(result.get("caption",""))[:30]}')
        print(f'  type: {result.get("type","")}')
        print(f'  memory_score: {result.get("memory_score",0)}')
        print(f'  beauty_score: {result.get("beauty_score",0)}')
        
        print('Step 2: generate_side_caption...')
        t2 = time.time()
        side_caption = generate_side_caption(img_path)
        print(f'Step 2 done ({time.time()-t2:.1f}s)')
        print(f'  side_caption: {side_caption}')
        
        print('All steps completed successfully!')
        
    except Exception as e:
        print(f'ERROR: {e}')
        traceback.print_exc()

if __name__ == '__main__':
    main()
