from lib/PipeImage import quick_video_stack
import sys

video_file = sys.argv[1]
stack_img, stack_file = quick_video_stack(video_file)
